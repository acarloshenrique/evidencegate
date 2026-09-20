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

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .audit import AuditTrail
from .crypto import b58decode, b58encode
from .db import Database
from .escrow import EscrowEngine, EscrowError
from .explain import explain_chain, explain_event
from .policy import Policy, PolicyEngine
from .registry import Registry, sanitize_untrusted
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
from .trace import build_graph, trace_entity
from .verify import JudgePanel, stage_a

_AGORA_AGENT_URL = os.getenv("AGORA_AGENT_URL", "http://localhost:8010")

# Audit actions taken by agents/system with no human in the loop. KYC onboarding
# (principal.registered) is the only human step and is not a decision.
_HUMAN_ACTIONS = ("human.",)
_NON_DECISIONS = ("principal.registered", "agent.registered")


def _autonomy(events: list[dict]) -> dict:
    """Derived from the audit trail, never stored: autonomous decisions vs human
    interventions, and how many verifications stage A settled with zero tokens."""
    decisions = human = stage_a_only = panels = 0
    for e in events:
        action = e["action"]
        if action.startswith(_HUMAN_ACTIONS):
            human += 1
        elif action == "verify.panel":
            panels += 1
            decisions += len(e["payload"].get("judges", [])) + 1  # votes + verdict
        elif action not in _NON_DECISIONS:
            decisions += 1
        if action == "escrow.rejected" and "stage_a" in (e["payload"].get("panel") or {}):
            stage_a_only += 1
    return {"autonomy": {"decisions": decisions, "human_interventions": human},
            "stage_a": {"resolved_free": stage_a_only,
                        "verifications": stage_a_only + panels}}


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
            self._nl = NeuraLake(db=self.db)
        return self._nl

    def seller_sk(self, did: str) -> bytes:
        row = self.db.execute(
            "SELECT sk_b58 FROM agent_keys WHERE did=?", (did,)).fetchone()
        if not row:
            raise HTTPException(404, f"no custodial key for agent {did}")
        return b58decode(row["sk_b58"])


_WEB = Path(__file__).resolve().parent / "web"


def _page(name: str) -> HTMLResponse:
    return HTMLResponse((_WEB / name).read_text(encoding="utf-8"))


def create_app(nl: Any = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db_path = os.getenv("EG_DB_PATH", "data/evidencegate.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        app.state.svc = Services(db_path, nl=nl)
        yield

    app = FastAPI(title="EvidenceGate", version="0.1.0", lifespan=lifespan)

    # O dashboard React roda em http://localhost:5173 durante o desenvolvimento;
    # em produção ele é servido por este mesmo processo (mesma origem).
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def svc(request: Request) -> Services:
        return request.app.state.svc

    app.mount("/static", StaticFiles(directory=_WEB), name="static")

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
        agents = s.registry.list_agents(capability)
        for a in agents:
            card = a.get("card") or {}
            flagged = False
            for v in card.values():
                if isinstance(v, str):
                    _, f = sanitize_untrusted(v)
                    flagged = flagged or f
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict):
                            _, f = sanitize_untrusted(
                                str(item.get("description", "")))
                            flagged = flagged or f
            a["injection_flagged"] = flagged
        return {"agents": agents}

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
        """Visão completa de um caso: escrow + quote (rubrica travada) + razão +
        votos do painel + trilha. É o que o auditor precisa ver numa tela só."""
        row = s.db.execute("SELECT * FROM escrows WHERE id=?",
                           (escrow_id,)).fetchone()
        if not row:
            raise HTTPException(404, "unknown escrow")
        escrow = dict(row)
        if escrow.get("evidence"):
            escrow["evidence"] = json.loads(escrow["evidence"])
        quote = s.db.execute("SELECT * FROM quotes WHERE id=?",
                             (row["quote_id"],)).fetchone()
        quote = dict(quote) if quote else None
        if quote:
            quote["criteria"] = json.loads(quote["criteria"])
        ledger = [dict(r) for r in s.db.execute(
            "SELECT account,delta,reason,ts FROM ledger WHERE escrow_id=? ORDER BY id",
            (escrow_id,))]
        votes = [dict(r) for r in s.db.execute(
            "SELECT judge,commit_hash,vote,confidence,rationale,revealed "
            "FROM judge_votes WHERE escrow_id=?", (escrow_id,))]
        return {"escrow": escrow, "quote": quote, "ledger": ledger,
                "votes": votes,
                "events": explain_chain(s.audit.for_escrow(escrow_id))}

    # --- audit / report -----------------------------------------------------
    @app.get("/audit")
    def audit_events(escrow_id: str | None = None, s: Services = Depends(svc)):
        if escrow_id:
            return {"events": explain_chain(s.audit.for_escrow(escrow_id))}
        rows = s.db.execute(
            "SELECT seq,ts,actor_did,action,payload,payload_hash,prev_hash,"
            "event_hash FROM events ORDER BY seq").fetchall()
        events = [dict(r) | {"payload": json.loads(r["payload"])}
                  for r in rows]
        return {"events": explain_chain(events)}

    @app.get("/audit/verify")
    def audit_verify(s: Services = Depends(svc)):
        return s.audit.verify_chain()

    @app.get("/report")
    def report(escrow_id: str, s: Services = Depends(svc)):
        return compliance_report(s.audit, escrow_id)

    @app.get("/explain")
    def explain(s: Services = Depends(svc)):
        """Every event explained from its own data — deterministic, no LLM."""
        return {"events": explain_chain(s.audit.events())}

    @app.get("/explain/{seq}")
    def explain_one(seq: int, s: Services = Depends(svc)):
        ev = next((e for e in s.audit.events() if e["seq"] == seq), None)
        if not ev:
            return {"error": "not found"}
        return {**ev, **explain_event(ev)}

    @app.get("/escrows")
    def list_escrows(s: Services = Depends(svc)):
        rows = s.db.execute(
            "SELECT e.id,e.state,e.created_at,q.price,q.scope,q.buyer_did,q.seller_did "
            "FROM escrows e JOIN quotes q ON e.quote_id=q.id "
            "ORDER BY e.created_at DESC").fetchall()
        return {"escrows": [dict(r) for r in rows]}

    @app.get("/trace/graph")
    def trace_graph(s: Services = Depends(svc)):
        """Grafo de proveniencia: KYC -> KYA -> quote -> escrow -> votos ->
        dinheiro -> eventos. Arestas tipadas = camada semantica da trilha."""
        return build_graph(s.db)

    @app.get("/trace/{entity_id}")
    def trace_one(entity_id: str, s: Services = Depends(svc)):
        out = trace_entity(s.db, entity_id)
        if not out["found"]:
            raise HTTPException(404, "entidade desconhecida")
        return out

    @app.get("/ledger")
    def ledger_events(s: Services = Depends(svc)):
        rows = s.db.execute(
            "SELECT account,delta,reason,escrow_id,ts FROM ledger "
            "ORDER BY ts DESC LIMIT 100").fetchall()
        return {"ledger": [dict(r) for r in rows]}

    @app.get("/metrics")
    def metrics(s: Services = Depends(svc)):
        # persisted calls are the source of truth — survives restarts;
        # in-memory list is the fallback for clients without a db (tests).
        agg = s.db.execute(
            "SELECT COUNT(*) c, COALESCE(SUM(cost),0.0) t "
            "FROM inference_calls").fetchone()
        if agg["c"]:
            calls = [dict(r) for r in s.db.execute(
                "SELECT model_requested,model_used,prompt_tokens,"
                "completion_tokens,cost FROM inference_calls "
                "ORDER BY id DESC LIMIT 20").fetchall()]
            return {"inference_cost": agg["t"],
                    "inference_calls": agg["c"],
                    "calls": calls,
                    "chain": s.audit.verify_chain(),
                    **_autonomy(s.audit.events())}
        calls = getattr(s._nl, "calls", [])
        return {"inference_cost": getattr(s._nl, "total_cost", 0.0),
                "inference_calls": len(calls),
                "calls": calls[-20:],
                "chain": s.audit.verify_chain(),
                **_autonomy(s.audit.events())}

    @app.get("/", response_class=HTMLResponse)
    def landing():
        return _page("landing.html")

    @app.get("/design", response_class=HTMLResponse)
    def design():
        return _page("design.html")

    @app.get("/dashboard/legacy", response_class=HTMLResponse)
    def dashboard_legacy():
        """Console single-file — fallback quando nao ha build React."""
        return _page("dashboard.html")

    # --- voice bridge (Agora ConvoAI BYOK -> CUSTOM_LLM_URL) -----------------
    @app.post("/chat/completions")
    def chat_completions(body: dict[str, Any], s: Services = Depends(svc)):
        """OpenAI-compatible endpoint: the voice agent answers auditor questions
        grounded in live registry/escrow state, never on hallucination."""
        escrows = s.db.execute(
            "SELECT e.id,e.state,q.price,q.seller_did FROM escrows e "
            "JOIN quotes q ON e.quote_id=q.id "
            "ORDER BY e.updated_at DESC LIMIT 10").fetchall()
        agents = s.registry.list_agents()
        # spoken names: a TTS reading a did:key aloud is unusable. A flagged
        # card is attacker-controlled text — it never reaches this prompt.
        names = {}
        for a in agents:
            a["injection_flagged"] = sanitize_untrusted(
                json.dumps(a.get("card") or {}, ensure_ascii=False))[1]
            names[a["did"]] = (
                "agente barrado por injection" if a["injection_flagged"]
                else (a.get("card") or {}).get("description") or "agente sem nome")
        events = s.audit.events()
        threats = [
            {"evento": e["action"],
             "agente": names.get(e["payload"].get("did", ""), ""),
             "detalhe": (e["payload"].get("panel") or {}).get("stage_a", {}).get("failures")
             or e["payload"].get("reason") or e["payload"].get("ruling") or ""}
            for e in events
            if e["action"] in ("agent.injection_flagged", "agent.card_invalid",
                               "agent.revoked", "policy.denied", "escrow.rejected",
                               "escrow.disputed", "escrow.arbitrated")][-8:]
        ctx = {
            "escrows": [{"estado": r["state"], "valor": r["price"],
                         "vendedor": names.get(r["seller_did"], "")} for r in escrows],
            "agentes": [{"nome": names[a["did"]], "reputacao": a["reputation"],
                         "injection_flagged": a["injection_flagged"]} for a in agents],
            "ameacas_e_bloqueios": threats,
            "trilha": s.audit.verify_chain(),
            **_autonomy(events),
        }
        system = (
            "Voce e o auditor de voz do EvidenceGate, camada antifraude para "
            "transacoes entre agentes. Sua resposta sera FALADA: portugues, no "
            "maximo duas frases, sem listas. Nunca leia DIDs, hashes ou ids — "
            "chame os agentes pelo nome. Entrega rejeitada, disputa, injection "
            "e policy negada CONTAM como fraude ou ataque barrado. Responda "
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
        cid = "chatcmpl-" + uuid.uuid4().hex[:24]
        created = int(time.time())
        if body.get("stream"):
            # Agora CustomLLM requires SSE; upstream is non-streaming so we
            # emit the full completion as chunked deltas.
            def sse():
                chunk = {"id": cid, "object": "chat.completion.chunk",
                         "created": created, "model": r["model_used"],
                         "choices": [{"index": 0, "finish_reason": None,
                                      "delta": {"role": "assistant",
                                                "content": r["content"]}}]}
                end = {"id": cid, "object": "chat.completion.chunk",
                       "created": created, "model": r["model_used"],
                       "choices": [{"index": 0, "finish_reason": "stop",
                                    "delta": {}}]}
                yield f"data: {json.dumps(chunk)}\n\n"
                yield f"data: {json.dumps(end)}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(sse(), media_type="text/event-stream")
        return {
            "id": cid,
            "object": "chat.completion",
            "created": created,
            "model": r["model_used"],
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant",
                                     "content": r["content"]}}],
            "usage": {"prompt_tokens": r["prompt_tokens"],
                      "completion_tokens": r["completion_tokens"],
                      "total_tokens": r["prompt_tokens"] + r["completion_tokens"]},
        }

    # --- voice demo (Agora RTC client + agent control proxy) -----------------
    @app.get("/voice", response_class=HTMLResponse)
    def voice_page():
        return _page("voice.html")

    @app.get("/voice/config")
    def voice_config(channel: str = "", uid: int = 0):
        params = {}
        if channel:
            params["channel"] = channel
        if uid:
            params["uid"] = uid
        try:
            r = httpx.get(f"{_AGORA_AGENT_URL}/get_config",
                          params=params, timeout=10)
            return r.json()
        except httpx.HTTPError as e:
            raise HTTPException(502, f"agent server: {e}") from e

    @app.post("/voice/start")
    def voice_start(body: dict[str, Any]):
        try:
            r = httpx.post(f"{_AGORA_AGENT_URL}/startAgent",
                           json=body, timeout=15)
            return r.json()
        except httpx.HTTPError as e:
            raise HTTPException(502, f"agent server: {e}") from e

    @app.post("/voice/stop")
    def voice_stop(body: dict[str, Any]):
        try:
            r = httpx.post(f"{_AGORA_AGENT_URL}/stopAgent",
                           json=body, timeout=15)
            return r.json()
        except httpx.HTTPError as e:
            raise HTTPException(502, f"agent server: {e}") from e

    # Dashboard React (web/): buildado em web/dist, servido na mesma origem da API.
    # Sem build presente, /dashboard cai no console single-file.
    if _WEB_DIST.is_dir():
        app.mount("/dashboard",
                  StaticFiles(directory=_WEB_DIST, html=True), name="dashboard")
    else:
        app.get("/dashboard", response_class=HTMLResponse)(dashboard_legacy)

    return app


_WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"


app = create_app()
