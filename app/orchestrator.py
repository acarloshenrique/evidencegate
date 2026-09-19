"""Orchestrator — the buyer agent running the full A2A cycle without a human.

discover -> evaluate -> hire -> fund -> (seller delivers) -> verify -> settle.

Every decision emits rationale into the audit trail. The orchestrator reasons
via model="auto" (NeuraLake router) — the efficiency story — but the choice can
also be injected deterministically for tests.
"""

import json
from collections.abc import Callable

from .audit import AuditTrail
from .db import Database
from .escrow import EscrowEngine
from .neuralake import NeuraLake
from .registry import Registry

ORCH_DID = "did:key:z-evidencegate-orchestrator"


class Orchestrator:
    def __init__(self, db: Database, audit: AuditTrail, registry: Registry,
                 escrow: EscrowEngine, nl: NeuraLake,
                 chooser: Callable[[list[dict], dict], dict] | None = None):
        self.db, self.audit, self.reg, self.esc, self.nl = db, audit, registry, escrow, nl
        self._chooser = chooser

    def discover(self, capability: str) -> list[dict]:
        """Verified, sanitized cards only — discovery never trusts free text."""
        candidates = []
        for a in self.reg.list_agents(capability):
            view = self.reg.introspect_card(a["did"])
            if view["ok"]:
                candidates.append({**a, "card": view["card"],
                                   "injection_flagged": view["injection_flagged"]})
        self.audit.append(ORCH_DID, "orchestrator.discover",
                          {"capability": capability,
                           "candidates": [c["did"] for c in candidates],
                           "flagged": [c["did"] for c in candidates
                                       if c["injection_flagged"]]})
        return candidates

    def evaluate(self, objective: str, candidates: list[dict],
                 price_est: dict[str, float]) -> dict:
        """Pick a seller by reputation x price x fit — rationale is logged either way.

        Injection-flagged candidates never reach the picker: a poisoned card is
        evidence for the trail, not an option on the table (defense §2.1).
        """
        candidates = [c for c in candidates if not c["injection_flagged"]]
        if not candidates:
            raise ValueError("no eligible candidates after filtering")
        if self._chooser:
            pick = self._chooser(candidates, price_est)
            rationale = pick.pop("rationale", "injected choice")
        else:
            brief = [{"did": c["did"], "reputation": c["reputation"],
                      "capabilities": c["capabilities"],
                      "price": price_est.get(c["did"])} for c in candidates]
            r = self.nl.complete(
                [{"role": "user", "content":
                  "Objetivo: " + objective + "\nCandidatos (verificados): "
                  + json.dumps(brief, ensure_ascii=False)
                  + "\nEscolha UM did para contratar. Responda JSON: "
                    '{"did":"...","rationale":"..."}'}],
                model="auto", max_tokens=300)
            try:
                from .verify import JudgePanel
                pick = JudgePanel._extract_json(r["content"])
                rationale = pick.get("rationale", "")
            except Exception:
                pick = {"did": max(candidates, key=lambda c: c["reputation"])["did"]}
                rationale = "fallback: highest reputation"
        self.audit.append(ORCH_DID, "orchestrator.evaluate",
                          {"chosen": pick["did"], "rationale": rationale,
                           "scores": {c["did"]: c["reputation"]
                                      for c in candidates}})
        return {"did": pick["did"], "rationale": rationale}
