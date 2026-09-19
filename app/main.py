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
from fastapi.responses import HTMLResponse

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

    @app.get("/escrows")
    def list_escrows(s: Services = Depends(svc)):
        rows = s.db.execute(
            "SELECT e.id,e.state,e.created_at,q.price,q.scope,q.buyer_did,q.seller_did "
            "FROM escrows e JOIN quotes q ON e.quote_id=q.id "
            "ORDER BY e.created_at DESC").fetchall()
        return {"escrows": [dict(r) for r in rows]}

    @app.get("/metrics")
    def metrics(s: Services = Depends(svc)):
        calls = getattr(s._nl, "calls", [])
        return {"inference_cost": getattr(s._nl, "total_cost", 0.0),
                "inference_calls": len(calls),
                "calls": calls[-20:],
                "chain": s.audit.verify_chain()}

    @app.get("/", response_class=HTMLResponse)
    def landing():
        return _LANDING_HTML

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard():
        return _DASHBOARD_HTML

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


_DASHBOARD_HTML = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EvidenceGate — camada de confiança A2A</title>
<style>
*{box-sizing:border-box;margin:0}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#06080f;color:#e6edf7;
 min-height:100vh;padding:0}
header{background:linear-gradient(135deg,#0d1424 0%,#0a1f33 60%,#0d2b1f 100%);
 border-bottom:1px solid #1c2f4a;padding:22px 32px;display:flex;align-items:center;
 justify-content:space-between;flex-wrap:wrap;gap:12px}
.logo{font-size:22px;font-weight:800;letter-spacing:-.5px}
.logo em{font-style:normal;background:linear-gradient(90deg,#4ade80,#22d3ee);
 -webkit-background-clip:text;background-clip:text;color:transparent}
.tag{font-size:12px;color:#7d8ba3;margin-top:3px}
.live{display:flex;align-items:center;gap:8px;font-size:12px;color:#7d8ba3}
.dot{width:8px;height:8px;border-radius:50%;background:#4ade80;
 box-shadow:0 0 8px #4ade80;animation:pulse 1.5s infinite}
@keyframes pulse{50%{opacity:.4}}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
 gap:14px;padding:22px 32px 6px}
.kpi{background:#0c1322;border:1px solid #1c2f4a;border-radius:12px;padding:16px 18px}
.kpi .lbl{font-size:11px;color:#7d8ba3;text-transform:uppercase;letter-spacing:.08em}
.kpi .val{font-size:26px;font-weight:800;margin-top:6px}
.kpi .sub{font-size:11px;color:#5b6b84;margin-top:2px}
.green{color:#4ade80}.cyan{color:#22d3ee}.amber{color:#fbbf24}.red{color:#f87171}
.cols{display:grid;grid-template-columns:1.4fr 1fr;gap:18px;padding:18px 32px 32px}
@media(max-width:900px){.cols{grid-template-columns:1fr}}
.panel{background:#0c1322;border:1px solid #1c2f4a;border-radius:12px;padding:18px}
.panel h2{font-size:12px;color:#7d8ba3;text-transform:uppercase;letter-spacing:.1em;
 margin-bottom:14px;display:flex;justify-content:space-between}
.esc{background:#0f1830;border:1px solid #1e3a5f;border-radius:10px;
 padding:14px 16px;margin-bottom:12px}
.esc.attack{border-color:#7f1d1d;background:#1a0f14}
.esc-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.esc-id{font-family:ui-monospace,monospace;font-size:12px;color:#8fb3d9}
.esc-price{font-weight:800;color:#fbbf24}
.esc-scope{font-size:13px;color:#c4d2e6;margin-bottom:10px}
.pipe{display:flex;align-items:center;gap:0;margin:6px 0}
.step{flex:1;text-align:center;position:relative}
.step .pt{width:11px;height:11px;border-radius:50%;background:#22304a;
 margin:0 auto;border:2px solid #22304a}
.step .lb{font-size:9px;color:#5b6b84;margin-top:4px;text-transform:uppercase}
.step.done .pt{background:#4ade80;border-color:#4ade80;box-shadow:0 0 6px #4ade80aa}
.step.done .lb{color:#4ade80}
.step.cur .pt{background:#22d3ee;border-color:#22d3ee;
 box-shadow:0 0 10px #22d3ee;animation:pulse 1.2s infinite}
.step.cur .lb{color:#22d3ee}
.step.bad .pt{background:#f87171;border-color:#f87171}
.step.bad .lb{color:#f87171}
.step::before{content:'';position:absolute;top:5px;left:-50%;width:100%;
 height:2px;background:#22304a;z-index:-1}
.step:first-child::before{display:none}
.step.done::before{background:#4ade80}
.badge{font-size:10px;font-weight:700;padding:2px 8px;border-radius:8px;
 letter-spacing:.05em}
.b-ok{background:#12331f;color:#4ade80}
.b-warn{background:#33290f;color:#fbbf24}
.b-bad{background:#331315;color:#f87171}
.ev{font-family:ui-monospace,monospace;font-size:11.5px;color:#93a4bd;
 padding:6px 0;border-bottom:1px solid #141d30;display:flex;gap:10px}
.ev:last-child{border:0}
.ev .seq{color:#22d3ee;min-width:32px}
.ev .act{color:#e6edf7;min-width:150px}
.ev .meta{color:#5b6b84;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.flag{color:#f87171;font-weight:700}
.empty{color:#5b6b84;font-size:13px;padding:20px;text-align:center}
</style></head><body>
<header>
  <div>
    <div class="logo">⛨ <em>EvidenceGate</em></div>
    <div class="tag">fé pública programável para a economia de agentes · camada de confiança A2A
    </div>
  </div>
  <div class="live"><span class="dot"></span> AO VIVO · <span id="clock"></span></div>
</header>
<div class="kpis">
  <div class="kpi"><div class="lbl">Custo de inferência</div>
    <div class="val amber" id="cost">$0</div><div class="sub">NeuraLake, por decisão</div></div>
  <div class="kpi"><div class="lbl">Chamadas LLM</div>
    <div class="val cyan" id="ncalls">0</div><div class="sub">juízes + orquestrador</div></div>
  <div class="kpi"><div class="lbl">Trilha de auditoria</div>
    <div class="val" id="chain">—</div><div class="sub" id="chain_sub">hash chain</div></div>
  <div class="kpi"><div class="lbl">Escrows</div>
    <div class="val" id="nesc">0</div><div class="sub">verificação = condição de settle</div></div>
</div>
<div class="cols">
  <div class="panel"><h2>Escrows <span class="mono">state machine</span></h2>
    <div id="escrows"></div></div>
  <div>
  <div class="panel" style="margin-bottom:18px"><h2>Registry</h2><div id="agents"></div></div>
  <div class="panel"><h2>Audit trail <span class="mono">append-only · hash-chained</span></h2>
    <div id="trail"></div></div>
  </div>
</div>
<script>
const $=id=>document.getElementById(id);
async function j(u){try{return (await fetch(u)).json()}catch(e){return{}}}
const HAPPY=['QUOTED','FUNDED','DELIVERED','VERIFIED','RELEASED'];
const BAD=['REJECTED','DISPUTED','ARBITRATED','RESOLVED'];
function pipe(state){
  let steps=HAPPY.slice(),cur=HAPPY.indexOf(state);
  if(BAD.includes(state)){steps=['QUOTED','FUNDED','DELIVERED',state];cur=3;}
  return `<div class="pipe">`+steps.map((s,i)=>{
    const cls=i<cur?'done':(i===cur?(BAD.includes(s)?'bad':'cur'):'');
    return `<div class="step ${cls}"><div class="pt"></div><div class="lb">${s}</div></div>`;
  }).join('')+`</div>`;
}
async function tick(){
  const [m,e,a,g]=await Promise.all(
    [j('/metrics'),j('/escrows'),j('/audit'),j('/agents')]);
  $('clock').textContent=new Date().toLocaleTimeString('pt-BR');
  $('cost').textContent='$'+(m.inference_cost||0).toFixed(6);
  $('ncalls').textContent=m.inference_calls||0;
  const ok=m.chain&&m.chain.ok;
  $('chain').textContent=ok?'ÍNTEGRA':'ADULTERADA';
  $('chain').className='val '+(ok?'green':'red');
  $('chain_sub').textContent=ok?'hash chain verificada':
    'tamper detectado @seq '+(m.chain?m.chain.tampered_seq:'?');
  $('nesc').textContent=(e.escrows||[]).length;
  $('escrows').innerHTML=(e.escrows||[]).map(x=>`
    <div class="esc"><div class="esc-top">
      <span class="esc-id">${x.id}</span><span class="esc-price">$${x.price}</span></div>
      <div class="esc-scope">${x.scope||''}</div>${pipe(x.state)}
      <div class="mono" style="font-size:10px;color:#5b6b84">seller ${x.seller_did.slice(0,30)}…
      </div>
    </div>`).join('')||'<div class="empty">aguardando primeira transação…</div>';
  $('agents').innerHTML=(g.agents||[]).map(a=>`
    <div class="ev"><span class="act">${a.did.slice(0,24)}…</span>
    <span class="meta">rep ${a.reputation.toFixed(1)} · ${(a.capabilities||[]).join(',')}</span>
    </div>`
  ).join('')||'<div class="empty">registry vazio</div>';
  $('trail').innerHTML=(a.events||[]).slice(-16).reverse().map(x=>{
    const bad=/denied|invalid|flagged|disputed|rejected/i.test(x.action);
    return `<div class="ev"><span class="seq">#${x.seq}</span>
      <span class="act ${bad?'flag':''}">${x.action}</span>
      <span class="meta">${x.actor_did.slice(0,24)}… ⛓ ${x.event_hash.slice(0,10)}</span></div>`;
  }).join('')||'<div class="empty">trilha vazia</div>';
}
setInterval(tick,1500);tick();
</script></body></html>"""



_LANDING_HTML = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EvidenceGate — fé pública programável para a economia de agentes</title>
<meta name="description" content="Escrow condicionado a verificação, identidade
KYC→KYA e trilha de auditoria hash-chained para transações agent-to-agent.">
<meta property="og:title" content="EvidenceGate — quando agentes pagam agentes,
quem confere o trabalho?">
<meta property="og:description" content="A camada de confiança que falta na
economia A2A: verificação como condição de settlement.">
<meta property="og:type" content="website">
<style>
*{box-sizing:border-box;margin:0}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#06080f;color:#e6edf7}
.wrap{max-width:960px;margin:0 auto;padding:0 24px}
nav{display:flex;justify-content:space-between;align-items:center;
 padding:20px 0;border-bottom:1px solid #141d30}
.logo{font-weight:800;font-size:18px}
.logo em{font-style:normal;background:linear-gradient(90deg,#4ade80,#22d3ee);
 -webkit-background-clip:text;background-clip:text;color:transparent}
nav a{color:#7d8ba3;text-decoration:none;font-size:13px;margin-left:18px}
nav a:hover{color:#e6edf7}
.hero{text-align:center;padding:80px 0 60px}
h1{font-size:clamp(28px,5vw,44px);font-weight:800;letter-spacing:-1px;
 line-height:1.15}
h1 em{font-style:normal;background:linear-gradient(90deg,#4ade80,#22d3ee);
 -webkit-background-clip:text;background-clip:text;color:transparent}
.sub{font-size:clamp(15px,2.5vw,19px);color:#8b9ab5;max-width:640px;
 margin:20px auto 32px;line-height:1.6}
.cta{display:inline-block;background:linear-gradient(90deg,#16a34a,#0891b2);
 color:#fff;font-weight:700;padding:14px 32px;border-radius:10px;
 text-decoration:none;font-size:15px}
.cta2{display:inline-block;border:1px solid #1c2f4a;color:#8b9ab5;
 padding:14px 32px;border-radius:10px;text-decoration:none;font-size:15px;
 margin-left:12px}
.pillars{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));
 gap:18px;padding:20px 0 50px}
.pillar{background:#0c1322;border:1px solid #1c2f4a;border-radius:14px;
 padding:26px}
.pillar .ic{font-size:26px;margin-bottom:14px}
.pillar h3{font-size:16px;margin-bottom:8px}
.pillar p{font-size:13.5px;color:#8b9ab5;line-height:1.6}
section{padding:44px 0;border-top:1px solid #141d30}
h2{font-size:22px;font-weight:800;margin-bottom:8px}
h2 small{display:block;font-size:12px;color:#22d3ee;font-weight:600;
 text-transform:uppercase;letter-spacing:.1em;margin-bottom:8px}
.steps{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}
.step{background:#0c1322;border:1px solid #1c2f4a;border-radius:8px;
 padding:10px 14px;font-size:12.5px;color:#8b9ab5}
.step b{color:#4ade80;font-family:ui-monospace,monospace}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
 gap:14px;margin-top:18px}
.cell{background:#0c1322;border:1px solid #1c2f4a;border-radius:10px;
 padding:16px;font-size:13px;color:#8b9ab5}
.cell b{color:#e6edf7;display:block;margin-bottom:4px}
.faq{margin-top:14px}
.faq details{background:#0c1322;border:1px solid #1c2f4a;border-radius:10px;
 padding:14px 18px;margin-bottom:10px}
.faq summary{cursor:pointer;font-size:14px;font-weight:600}
.faq p{font-size:13px;color:#8b9ab5;margin-top:8px;line-height:1.6}
footer{border-top:1px solid #141d30;padding:28px 0;text-align:center;
 font-size:12px;color:#5b6b84}
</style></head><body><div class="wrap">
<nav><div class="logo">⛨ <em>EvidenceGate</em></div>
<div><a href="/dashboard">Dashboard ao vivo</a><a href="/docs">API</a></div></nav>
<div class="hero">
<h1>Quando agentes pagam agentes,<br><em>quem confere o trabalho?</em></h1>
<p class="sub">A2A resolveu a conversa. x402 e AP2 resolveram o pagamento.
Mas settlement é final — ninguém verifica se a entrega presta.
EvidenceGate é a camada de confiança que falta:
<strong>escrow condicionado a verificação independente.</strong></p>
<a class="cta" href="/dashboard">Ver a trilha ao vivo</a>
<a class="cta2" href="/docs">API docs</a>
</div>
<div class="pillars">
<div class="pillar"><div class="ic">🔏</div><h3>Identidade que responde</h3>
<p>Principal com KYC real, agente com KYA e AgentCard assinado em Ed25519/did:key.
Cartão adulterado ou com prompt injection é detectado antes da contratação.</p></div>
<div class="pillar"><div class="ic">⚖️</div><h3>Verificação antes do dinheiro</h3>
<p>Stage A determinístico filtra de graça. Painel de 3 juízes cross-model com
commit-reveal decide 2-de-3 — julgando o artefato, nunca o raciocínio.</p></div>
<div class="pillar"><div class="ic">⛓</div><h3>Trilha que auditor aceita</h3>
<p>Cada decisão num log append-only hash-chained. Um caractere adulterado e
o verificador aponta exatamente onde. Compliance report exportável.</p></div>
</div>
<section><h2><small>Como funciona</small>O ciclo completo, sem humano</h2>
<div class="steps">
<div class="step"><b>1</b> discover no registry</div>
<div class="step"><b>2</b> evaluate (reputação × preço)</div>
<div class="step"><b>3</b> quote + rubrica travada</div>
<div class="step"><b>4</b> escrow funded</div>
<div class="step"><b>5</b> entrega + evidence hash</div>
<div class="step"><b>6</b> stage A + painel de juízes</div>
<div class="step"><b>7</b> release ou disputa</div>
<div class="step"><b>8</b> reputação atualizada</div>
</div></section>
<section><h2><small>Defesas reais</small>Contra os ataques que a economia A2A vai sofrer</h2>
<div class="grid2">
<div class="cell"><b>AgentCard poisoning</b>Texto livre é data, nunca instrução — sanitização +
flag na trilha.</div>
<div class="cell"><b>Confused deputy</b>Policy em código: assinatura prova autorização, não
intenção.</div>
<div class="cell"><b>Gaming the judge</b>Juiz vê artefato, não CoT — CoT manipulado infla falso
positivo em 90%.</div>
<div class="cell"><b>Sybil / reputação</b>Score só muda com outcome settled — review não
verificado não conta.</div>
<div class="cell"><b>Payment hijack</b>Funding idempotente, transições guardadas, fail-closed.</div>
<div class="cell"><b>Log adulterado</b>Hash chain re-derivável — estilo Certificate
Transparency.</div>
</div></section>
<section><h2><small>Roadmap</small>Hackathon hoje, infraestrutura amanhã</h2>
<div class="grid2">
<div class="cell"><b>Agora (demo)</b>Escrow + verificação + trilha live, juízes reais na
NeuraLake, custo/decisão visível.</div>
<div class="cell"><b>Próximo</b>Adapters x402/AP2, registries ERC-8004
(identity/reputation/validation) on-chain, settlement em Base.</div>
<div class="cell"><b>Depois</b>Validação cripto-econômica (stake), TEE/zkML para prova de
inferência, federação de tribunais.</div>
</div></section>
<section><h2><small>Objeções</small>Perguntas que todo mundo faz</h2>
<div class="faq">
<details><summary>Juiz LLM decidindo dinheiro não é frágil?</summary>
<p>Por isso two-stage: o determinístico decide o objetivável de graça; o painel só julga o
subjetivo, com rubrica travada antes do trabalho e maioria 2-de-3. Juiz que não consegue
verificar nunca aprova — fail-closed.</p></details>
<details><summary>Por que não só blockchain?</summary>
<p>O problema não é o rail de pagamento — é a verificação. O state machine do escrow isola a
interface: pluga em x402, AP2 ou Base quando fizer sentido, sem reescrever nada.</p></details>
<details><summary>E se os juízes coludirem?</summary>
<p>Votos selados (commit-reveal) anti-herding, juízes em modelos diferentes, e juiz também tem
reputação: aprovar lixo contestado derruba o score dele.</p></details>
</div></section>
<footer>EvidenceGate · fé pública programável · desafio 05 — NeuraLake The Launch Hackathon</footer>
</div></body></html>"""
