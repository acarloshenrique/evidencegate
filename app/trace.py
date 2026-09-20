"""Provenance graph: the accountability chain KYC -> KYA -> action.

Derives the semantic layer the auditor asks for — who stands behind each
agent and what exactly it did — from the relational store. Nodes are typed
entities (principal, agent, quote, escrow, judge); edges are typed
relationships with Portuguese labels and payload data (amount, vote,
confidence, action). Same facts, graph-shaped: KYC_BACKS, SIGNED_QUOTE,
FUNDED, JUDGED_BY, VOTE, MONEY, LOGGED.

A real Neo4j backend can sit behind this same API later — the contract is
the product, not the store.
"""

import json
from typing import Any

# node types -> display metadata (color follows the design system dark track)
NODE_META = {
    "principal": {"label": "Principal (KYC)", "color": "#fbbf24"},
    "agent": {"label": "Agente (KYA)", "color": "#665efd"},
    "quote": {"label": "Quote", "color": "#38bdf8"},
    "escrow": {"label": "Escrow", "color": "#34d399"},
    "judge": {"label": "Juiz", "color": "#f96bee"},
    "event": {"label": "Evento", "color": "#8b98b8"},
}

ESCROW_STATE_COLORS = {
    "RELEASED": "#34d399", "RESOLVED": "#38bdf8", "VERIFIED": "#34d399",
    "FUNDED": "#38bdf8", "DELIVERED": "#38bdf8", "QUOTED": "#8b98b8",
    "REJECTED": "#f87171", "DISPUTED": "#f87171", "ARBITRATED": "#fbbf24",
}

EDGE_LABELS = {
    "KYC_BACKS": "responde por",
    "KYA": "identidade de",
    "QUOTED_BUY": "contratou",
    "SIGNED_QUOTE": "assinou rubrica",
    "FUNDED": "travou fundos em",
    "JUDGED_BY": "julgado por",
    "VOTE": "votou",
    "MONEY": "movimentou",
    "LOGGED": "registrou",
}


def _short_did(did: str) -> str:
    return did[:18] + "…" if len(did) > 21 else did


def _node(nid: str, ntype: str, label: str, data: dict[str, Any]) -> dict:
    meta = NODE_META[ntype]
    color = meta["color"]
    if ntype == "escrow":
        color = ESCROW_STATE_COLORS.get(data.get("state"), meta["color"])
    return {"id": nid, "type": ntype, "type_label": meta["label"],
            "label": label, "color": color, "data": data}


def build_graph(db) -> dict[str, Any]:
    """Whole-system provenance graph."""
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    eid = [0]

    def edge(src: str, dst: str, etype: str, data: dict | None = None) -> None:
        eid[0] += 1
        edges.append({"id": f"e{eid[0]}", "src": src, "dst": dst,
                      "type": etype, "label": EDGE_LABELS.get(etype, etype),
                      "data": data or {}})

    principals = {r["id"]: r for r in db.execute(
        "SELECT * FROM principals").fetchall()}
    for p in principals.values():
        nodes[p["id"]] = _node(p["id"], "principal", p["legal_name"],
                               {"doc_hash": p["doc_hash"][:12] + "…"})

    agents = {r["did"]: r for r in db.execute(
        "SELECT did,principal_id,reputation,manifest,status FROM agents"
    ).fetchall()}
    for a in agents.values():
        caps = json.loads(a["manifest"]).get("capabilities", [])
        nodes[a["did"]] = _node(a["did"], "agent", _short_did(a["did"]),
                                {"reputation": a["reputation"],
                                 "capabilities": caps, "status": a["status"]})
        if a["principal_id"] in nodes:
            edge(a["principal_id"], a["did"], "KYC_BACKS")

    quotes = {r["id"]: r for r in db.execute(
        "SELECT * FROM quotes").fetchall()}
    for q in quotes.values():
        nodes[q["id"]] = _node(q["id"], "quote",
                               f"{q['scope'][:34]} · ${q['price']}",
                               {"price": q["price"], "scope": q["scope"],
                                "quote_hash": q["quote_hash"][:12] + "…"})
        if q["buyer_did"] in nodes:
            edge(q["buyer_did"], q["id"], "QUOTED_BUY")
        if q["seller_did"] in nodes:
            edge(q["seller_did"], q["id"], "SIGNED_QUOTE")

    escrows = {r["id"]: r for r in db.execute(
        "SELECT * FROM escrows").fetchall()}
    for e in escrows.values():
        label = f"{e['state']} · {e['id'][:14]}"
        nodes[e["id"]] = _node(e["id"], "escrow", label,
                               {"state": e["state"], "verdict": e["verdict"],
                                "dispute": e["dispute"],
                                "evidence_hash": (e["evidence_hash"] or "")[:12]})
        if e["quote_id"] in nodes:
            edge(e["quote_id"], e["id"], "FUNDED")

    for v in db.execute(
            "SELECT escrow_id,judge,vote,confidence FROM judge_votes").fetchall():
        jid = f"judge:{v['judge']}"
        if jid not in nodes:
            nodes[jid] = _node(jid, "judge", v["judge"],
                               {"capability": v["judge"]})
        if v["escrow_id"] in nodes:
            edge(v["escrow_id"], jid, "JUDGED_BY")
            edge(jid, v["escrow_id"], "VOTE",
                 {"vote": v["vote"], "confidence": v["confidence"]})

    for led in db.execute(
            "SELECT account,delta,reason,escrow_id FROM ledger").fetchall():
        if led["escrow_id"] in nodes and led["account"] in nodes:
            if led["delta"] < 0:   # money leaving the account into escrow
                edge(led["account"], led["escrow_id"], "MONEY",
                     {"delta": led["delta"], "reason": led["reason"]})
            else:              # escrow paying out
                edge(led["escrow_id"], led["account"], "MONEY",
                     {"delta": led["delta"], "reason": led["reason"]})

    for ev in db.execute(
            "SELECT seq,actor_did,action,payload FROM events").fetchall():
        payload = json.loads(ev["payload"])
        target = (payload.get("escrow_id") or payload.get("quote_id"))
        if ev["actor_did"] in nodes and target in nodes:
            edge(ev["actor_did"], target, "LOGGED",
                 {"action": ev["action"], "seq": ev["seq"]})

    return {"nodes": list(nodes.values()), "edges": edges}


def trace_entity(db, entity_id: str) -> dict[str, Any]:
    """Focused lineage for one entity: its neighborhood + facts."""
    graph = build_graph(db)
    node = next((n for n in graph["nodes"] if n["id"] == entity_id), None)
    if node is None:
        return {"found": False, "id": entity_id, "neighbors": [], "edges": []}
    rel_edges = [e for e in graph["edges"]
                 if e["src"] == entity_id or e["dst"] == entity_id]
    neighbor_ids = {e["src"] for e in rel_edges} | {e["dst"] for e in rel_edges}
    neighbors = [n for n in graph["nodes"] if n["id"] in neighbor_ids]
    facts: dict[str, Any] = {"node": node, "neighbors": neighbors,
                            "edges": rel_edges, "found": True}
    if node["type"] == "agent":
        esc = db.execute(
            "SELECT e.id,e.state,e.verdict,q.price,q.scope FROM escrows e "
            "JOIN quotes q ON e.quote_id=q.id WHERE q.buyer_did=? OR q.seller_did=?",
            (entity_id, entity_id)).fetchall()
        facts["escrows"] = [dict(r) for r in esc]
        bal = db.execute("SELECT amount FROM balances WHERE account=?",
                         (entity_id,)).fetchone()
        facts["balance"] = bal["amount"] if bal else 0.0
    if node["type"] == "escrow":
        facts["events"] = [dict(r) for r in db.execute(
            "SELECT seq,ts,actor_did,action FROM events WHERE payload LIKE ? "
            "ORDER BY seq", (f"%{entity_id}%",)).fetchall()]
        facts["votes"] = [dict(r) for r in db.execute(
            "SELECT judge,vote,confidence,rationale FROM judge_votes "
            "WHERE escrow_id=?", (entity_id,)).fetchall()]
    return facts
