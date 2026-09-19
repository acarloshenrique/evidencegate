"""EvidenceGate API — HTTP surface over the trust layer core.

Every mutating endpoint writes to the append-only audit trail; verification
(judge panel) is the settlement condition for escrow release. The API never
trusts agent-supplied free text — AgentCards are verified + sanitized at
introspection time (see registry.introspect_card).

Voice bridge: POST /chat/completions is OpenAI-compatible so the Agora
ConvoAI BYOK recipe can point CUSTOM_LLM_URL straight at this service.
"""

import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request

from .audit import AuditTrail
from .crypto import b58decode, b58encode
from .db import Database
from .escrow import EscrowEngine, EscrowError
from .policy import Policy, PolicyEngine
from .registry import Registry
from .report import compliance_report
from .schemas import (
    AgentIn,
    AgentOut,
    ArbitrateIn,
    CardVerifyIn,
    DeliverIn,
    DeliverOut,
    DisputeIn,
    EscrowCreatedOut,
    EscrowCreateIn,
    PrincipalIn,
    PrincipalOut,
    QuoteIn,
    QuoteOut,
    StateOut,
    VerifyIn,
    VerifyOut,
)
from .verify import JudgePanel, stage_a


class Services:
    """Bundle of core services + custodial agent keys (hackathon-grade custody:

    keys live in a dedicated table so the server can sign quotes on behalf of
    registered sellers; production splits this into KMS/HSM per principal).
    """

    def __init__(self, db_path: str | Path, nl: Any = None):
        self.db = Database(db_path)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS agent_keys"
            "(did TEXT PRIMARY KEY, sk_b58 TEXT NOT NULL)")
        self.audit = AuditTrail(self.db)
        self.registry = Registry(self.db, self.audit)
        self.policy = PolicyEngine(
            self.db,
            Policy(max_tx_value=float(os.getenv("EG_MAX_TX", "50")),
                   session_cap=float(os.getenv("EG_SESSION_CAP", "200")),
                   human_threshold=float(os.getenv("EG_HUMAN_THRESHOLD", "100"))))
        self.escrow = EscrowEngine(self.db, self.audit, self.registry, self.policy)
        self._nl = nl

    @property
    def nl(self):
        if self._nl is None:
            from .neuralake import NeuraLake
            if not os.getenv("NEURALAKE_API_KEY"):
                raise HTTPException(503, "NeuraLake credentials not configured")
            self._nl = NeuraLake()
        return self._nl

    def seller_sk(self, did: str) -> bytes:
        row = self.db.execute(
            "SELECT sk_b58 FROM agent_keys WHERE did=?", (did,)).fetchone()
        if not row:
            raise HTTPException(404, f"no custodial key for agent {did}")
        return b58decode(row["sk_b58"])


def create_app(nl: Any = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db_path = os.getenv("EG_DB_PATH", "data/evidencegate.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        app.state.svc = Services(db_path, nl=nl)
        yield

    app = FastAPI(title="EvidenceGate", version="0.1.0", lifespan=lifespan)

    def svc(request: Request) -> Services:
        return request.app.state.svc

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "evidencegate"}

    # --- identity ---------------------------------------------------------
    @app.post("/principals", response_model=PrincipalOut)
    def register_principal(body: PrincipalIn, s: Services = Depends(svc)):
        return {"principal_id": s.registry.register_principal(
            body.legal_name, body.doc_id)}

    @app.post("/agents", response_model=AgentOut)
    def register_agent(body: AgentIn, s: Services = Depends(svc)):
        did, sk = s.registry.issue_agent(body.principal_id, body.card, body.manifest)
        s.db.execute("INSERT INTO agent_keys(did,sk_b58) VALUES(?,?)",
                     (did, b58encode(sk)))
        card = s.registry.verify_card(did)["card"]
        sig = s.db.execute("SELECT card_sig FROM agents WHERE did=?",
                           (did,)).fetchone()["card_sig"]
        return {"agent_did": did, "card": card, "card_sig": sig,
                "secret_key_b58": b58encode(sk), "manifest": body.manifest}

    @app.get("/agents")
    def list_agents(capability: str | None = None, s: Services = Depends(svc)):
        return {"agents": s.registry.list_agents(capability)}

    @app.get("/agents/{did}/card")
    def get_card(did: str, s: Services = Depends(svc)):
        res = s.registry.introspect_card(did)
        if not res["ok"]:
            raise HTTPException(404, res["reason"])
        return res

    @app.post("/cards/verify")
    def verify_card(body: CardVerifyIn, s: Services = Depends(svc)):
        return s.registry.verify_card(body.did)

    # --- escrow -----------------------------------------------------------
    @app.post("/quotes", response_model=QuoteOut)
    def create_quote(body: QuoteIn, s: Services = Depends(svc)):
        deadline = body.deadline or (time.time() + 3600)
        return s.escrow.create_quote(
            body.buyer_did, body.seller_did, body.scope, body.criteria,
            body.price, deadline, s.seller_sk(body.seller_did))

    @app.post("/escrow", response_model=EscrowCreatedOut)
    def fund(body: EscrowCreateIn, s: Services = Depends(svc)):
        try:
            return s.escrow.accept_and_fund(
                body.quote_id, body.buyer_did, body.idempotency_key)
        except EscrowError as e:
            raise HTTPException(400, str(e)) from e

    @app.post("/escrow/{escrow_id}/deliver", response_model=DeliverOut)
    def deliver(escrow_id: str, body: DeliverIn, s: Services = Depends(svc)):
        try:
            return s.escrow.deliver(escrow_id, body.seller_did, body.evidence)
        except EscrowError as e:
            raise HTTPException(400, str(e)) from e

    @app.post("/escrow/{escrow_id}/verify", response_model=VerifyOut)
    def verify(escrow_id: str, body: VerifyIn, s: Services = Depends(svc)):
        row = s.db.execute(
            "SELECT e.evidence, e.evidence_hash, q.scope, q.criteria "
            "FROM escrows e JOIN quotes q ON e.quote_id=q.id WHERE e.id=?",
            (escrow_id,)).fetchone()
        if not row:
            raise HTTPException(404, "unknown escrow")
        if not row["evidence"]:
            raise HTTPException(400, "nothing delivered")
        evidence = json.loads(row["evidence"])
        criteria = json.loads(row["criteria"])
        a = stage_a(evidence, criteria, row["evidence_hash"])
        if not a["passed"]:
            state = s.escrow.settle_verdict(escrow_id, "retain", {"stage_a": a})
            return {"escrow_id": escrow_id, "stage_a": a, "panel": None,
                    "verdict": "retain", "state": state["state"]}
        if not body.live:
            return {"escrow_id": escrow_id, "stage_a": a, "panel": None,
                    "verdict": "pending_panel",
                    "state": s.escrow._state(escrow_id)}
        panel = JudgePanel(s.db, s.audit, s.nl)
        summary = panel.run(escrow_id, row["scope"], criteria, evidence)
        verdict = summary["verdict"]
        state = s.escrow.settle_verdict(escrow_id, verdict, summary)
        return {"escrow_id": escrow_id, "stage_a": a, "panel": summary,
                "verdict": verdict, "state": state["state"]}

    @app.post("/escrow/{escrow_id}/dispute", response_model=StateOut)
    def dispute(escrow_id: str, body: DisputeIn, s: Services = Depends(svc)):
        try:
            return {"escrow_id": escrow_id,
                    **s.escrow.dispute(escrow_id, body.opener_did, body.reason)}
        except EscrowError as e:
            raise HTTPException(400, str(e)) from e

    @app.post("/escrow/{escrow_id}/arbitrate", response_model=StateOut)
    def arbitrate(escrow_id: str, body: ArbitrateIn, s: Services = Depends(svc)):
        try:
            return {"escrow_id": escrow_id,
                    **s.escrow.arbitrate(escrow_id, body.ruling, body.rationale)}
        except EscrowError as e:
            raise HTTPException(400, str(e)) from e

    @app.get("/escrow/{escrow_id}")
    def get_escrow(escrow_id: str, s: Services = Depends(svc)):
        row = s.db.execute("SELECT * FROM escrows WHERE id=?",
                           (escrow_id,)).fetchone()
        if not row:
            raise HTTPException(404, "unknown escrow")
        ledger = [dict(r) for r in s.db.execute(
            "SELECT account,delta,reason,ts FROM ledger WHERE escrow_id=?",
            (escrow_id,))]
        return {"escrow": dict(row), "ledger": ledger}

    # --- audit / report -----------------------------------------------------
    @app.get("/audit")
    def audit_events(escrow_id: str | None = None, s: Services = Depends(svc)):
        if escrow_id:
            return {"events": s.audit.for_escrow(escrow_id)}
        rows = s.db.execute(
            "SELECT seq,ts,actor_did,action,payload_hash,prev_hash,event_hash "
            "FROM events ORDER BY seq").fetchall()
        return {"events": [dict(r) for r in rows]}

    @app.get("/audit/verify")
    def audit_verify(s: Services = Depends(svc)):
        return s.audit.verify_chain()

    @app.get("/report")
    def report(escrow_id: str, s: Services = Depends(svc)):
        return compliance_report(s.audit, escrow_id)

    # --- voice bridge (Agora ConvoAI BYOK -> CUSTOM_LLM_URL) -----------------
    @app.post("/chat/completions")
    def chat_completions(body: dict[str, Any], s: Services = Depends(svc)):
        """OpenAI-compatible endpoint: the voice agent answers auditor questions
        grounded in live registry/escrow state, never on hallucination."""
        escrows = s.db.execute(
            "SELECT id,state FROM escrows ORDER BY updated_at DESC LIMIT 10").fetchall()
        agents = s.registry.list_agents()
        ctx = {
            "escrows": [{"id": r["id"], "state": r["state"]} for r in escrows],
            "agents": [{"did": a["did"], "reputation": a["reputation"],
                        "capabilities": a["capabilities"]} for a in agents],
        }
        system = (
            "Voce e o auditor de voz do EvidenceGate, camada de confianca "
            "para transacoes entre agentes. Responda em portugues, curto, "
            "apenas com base no ESTADO REAL abaixo — nunca invente.\n\n"
            f"ESTADO ATUAL:\n{json.dumps(ctx, ensure_ascii=False)}")
        messages = [{"role": "system", "content": system}]
        for m in body.get("messages", []):
            role = m.get("role")
            if role in ("user", "assistant"):
                content = m.get("content")
                if isinstance(content, list):
                    content = " ".join(
                        c.get("text", "") for c in content
                        if isinstance(c, dict))
                messages.append({"role": role, "content": str(content)})
        r = s.nl.complete(messages, model=body.get("model", "auto"),
                          max_tokens=int(body.get("max_tokens", 512)))
        return {
            "id": "chatcmpl-" + uuid.uuid4().hex[:24],
            "object": "chat.completion",
            "created": int(time.time()),
            "model": r["model_used"],
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant",
                                     "content": r["content"]}}],
            "usage": {"prompt_tokens": r["prompt_tokens"],
                      "completion_tokens": r["completion_tokens"],
                      "total_tokens": r["prompt_tokens"] + r["completion_tokens"]},
        }

    return app


app = create_app()
