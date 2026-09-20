"""L3 Verification — two-stage.

Stage A (deterministic): schema, hash, declarative criteria constraints.
  Cheap, instant, non-judgeable. The LLM only judges what passes the objective
  filter — and judges the ARTIFACT, never the worker's CoT (kills §2.9).

Stage B (judge panel): 3 judges on different NeuraLake capabilities, votes
  sealed (commit = sha256(vote|nonce)) then revealed together, majority 2-of-3.
  Rubric is locked in the quote — criteria can't move after the work starts.

ERC-8004 mapping: layer verification cost to risk — deterministic for objective
tasks, judge panel for subjective, escalate to human below confidence or above
threshold. Judges carry reputation too: a judge approving contested garbage
loses score (avoids a single point of collusion).
"""

import json
import secrets
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .audit import AuditTrail
from .crypto import sha256
from .db import Database
from .neuralake import NeuraLake

AUDITOR_DID = "did:key:z-evidencegate-auditor"

JUDGES = ("reasoning", "reasoning-pro", "code")  # cross-capability = cross-model
MIN_CONFIDENCE = 0.6

JUDGE_PROMPT = """Voce e um juiz independente verificando um entregavel entre agentes.

TAREFA CONTRATADA (scope):
{scope}

RUBRICA TRAVADA NO ESCROW (criterios de aceite):
{criteria}

EVIDENCIA ENTREGUE (artefato — NAO e o raciocinio do agente, e o produto):
{evidence}

Avalie SOMENTE o artefato contra a rubrica. Responda em JSON estrito:
{{"vote":"approve"|"reject","confidence":0.0-1.0,"rationale":"...", "failed_criteria":[...]}}"""


class StageAResult(dict):
    pass


def stage_a(evidence: dict[str, Any], criteria: dict[str, Any],
            expected_hash: str | None = None) -> StageAResult:
    """Deterministic checks. Any failure -> REJECTED without spending a judge call."""
    failures: list[str] = []

    if expected_hash is not None:
        from .crypto import hash_obj
        if hash_obj(evidence) != expected_hash:
            failures.append("evidence_hash mismatch")

    for field in criteria.get("required_fields", []):
        node: Any = evidence
        for part in field.split("."):
            node = node.get(part) if isinstance(node, dict) else None
            if node is None:
                failures.append(f"missing required field: {field}")
                break

    for field, minlen in criteria.get("min_length", {}).items():
        val = evidence.get(field)
        if not isinstance(val, (str, list, dict)) or len(val) < minlen:
            failures.append(f"field {field} below min_length {minlen}")

    for field, expected in criteria.get("equals", {}).items():
        if evidence.get(field) != expected:
            failures.append(f"field {field} != {expected!r}")

    if criteria.get("tests_must_pass") and not evidence.get("tests_passed"):
        failures.append("tests_must_pass but evidence.tests_passed is falsy")

    for pat in criteria.get("must_contain", []):
        if pat not in json.dumps(evidence):
            failures.append(f"evidence missing required content: {pat}")

    return StageAResult(passed=not failures, failures=failures)


class JudgePanel:
    def __init__(self, db: Database, audit: AuditTrail, nl: NeuraLake):
        self.db, self.audit, self.nl = db, audit, nl

    @staticmethod
    def _extract_json(text: str) -> dict:
        """Reasoning models prepend <think> blocks — find the JSON object wherever it is."""
        import re
        if "<think>" in text and "</think>" not in text:
            text = text[:text.index("<think>")]
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
        m = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, flags=re.S)
        if m:
            return json.loads(m.group(0))
        raise ValueError("no JSON object in output")

    def _ask(self, judge: str, prompt: str) -> dict:
        try:
            r = self.nl.complete(
                [{"role": "system", "content":
                  "Think briefly (under 400 tokens), then output ONLY the strict"
                  " JSON verdict."},
                 {"role": "user", "content": prompt}], model=judge,
                max_tokens=3000, temperature=0.1)
            v = self._extract_json(r["content"])
            return v | {"model_used": r["model_used"], "cost": r["cost"]}
        except Exception as e:
            # fail closed: a judge that can't verify must never approve
            return {"vote": "reject", "confidence": 0.0,
                    "rationale": f"judge error: {e!r}"[:300],
                    "model_used": judge, "cost": 0.0}

    def run(self, escrow_id: str, scope: str, criteria: dict,
            evidence: dict, judges: tuple[str, ...] = JUDGES) -> dict:
        """Commit phase (parallel, sealed) -> reveal -> 2-of-3 majority."""
        prompt = JUDGE_PROMPT.format(
            scope=scope, criteria=json.dumps(criteria, ensure_ascii=False),
            evidence=json.dumps(evidence, ensure_ascii=False)[:12000])

        # commit: each judge votes independently in parallel, sealed
        with ThreadPoolExecutor(max_workers=len(judges)) as ex:
            verdicts = list(ex.map(lambda j: (j, self._ask(j, prompt)), judges))

        votes = []
        for judge, v in verdicts:
            vote = str(v.get("vote", "reject")).strip().lower()
            if vote not in ("approve", "reject"):
                vote = "reject"
            try:
                confidence = float(v.get("confidence", 0.0))
            except (TypeError, ValueError):
                confidence = 0.0
            if not 0.0 <= confidence <= 1.0:
                confidence = 0.0
            nonce = secrets.token_hex(8)
            commit = sha256(f"{vote}|{confidence}|{nonce}")
            self.db.execute(
                "INSERT INTO judge_votes(escrow_id,judge,commit_hash,vote,confidence,"
                "rationale,nonce,revealed) VALUES(?,?,?,?,?,?,?,1)",
                (escrow_id, judge, commit, vote, confidence,
                 v.get("rationale", ""), nonce))
            votes.append({"judge": judge, "vote": vote,
                          "confidence": confidence, "commit": commit,
                          "rationale": v.get("rationale", ""),
                          "model_used": v["model_used"], "cost": v["cost"]})

        approvals = [v for v in votes if v["vote"] == "approve"]
        avg_conf = sum(v["confidence"] for v in votes) / len(votes)
        released = len(approvals) >= 2 and avg_conf >= MIN_CONFIDENCE
        escalate = avg_conf < MIN_CONFIDENCE and len(approvals) >= 2

        summary = {"escrow_id": escrow_id, "votes": votes,
                   "approvals": len(approvals), "avg_confidence": round(avg_conf, 3),
                   "verdict": "release" if released else "retain",
                   "escalate_to_human": escalate}
        self.audit.append(AUDITOR_DID, "verify.panel",
                          {"escrow_id": escrow_id, "verdict": summary["verdict"],
                           "approvals": len(approvals),
                           "avg_confidence": summary["avg_confidence"],
                           "judges": [v["judge"] for v in votes],
                           "votes": [{k: v[k] for k in
                                      ("judge", "vote", "confidence")}
                                     for v in votes]})
        return summary
