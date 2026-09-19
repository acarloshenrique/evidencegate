"""T009 — API integration: full happy path over HTTP with a fake NeuraLake.

The judge panel is stubbed (FakeNL) so tests never spend real inference.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class FakeNL:
    def __init__(self):
        self.calls, self.total_cost = [], 0.0

    def complete(self, messages, model="auto", **kw):
        self.calls.append({"model": model})
        v = {"vote": "approve", "confidence": 0.9,
             "rationale": f"artefato atende a rubrica ({model})"}
        return {"content": json.dumps(v), "model_used": model, "cost": 0.0,
                "prompt_tokens": 0, "completion_tokens": 0}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EG_DB_PATH", str(tmp_path / "test.db"))
    from fastapi.testclient import TestClient

    from app.main import create_app
    with TestClient(create_app(nl=FakeNL())) as c:
        yield c


def _setup(client):
    p = client.post("/principals", json={
        "legal_name": "Meridian Holdings SA", "doc_id": "12.345.678/0001-90"})
    assert p.status_code == 200
    pid = p.json()["principal_id"]

    def mkagent(desc):
        r = client.post("/agents", json={
            "principal_id": pid, "card": {"description": desc},
            "manifest": {"capabilities": ["research"],
                         "fuses": {"max_tx_value": 50}}})
        assert r.status_code == 200
        return r.json()["agent_did"]

    return pid, mkagent("buyer"), mkagent("seller")


def test_happy_path_http(client):
    _, buyer, seller = _setup(client)

    card = client.get(f"/agents/{seller}/card").json()
    assert card["ok"] and not card["injection_flagged"]

    q = client.post("/quotes", json={
        "buyer_did": buyer, "seller_did": seller,
        "scope": "relatorio de mercado", "price": 20.0,
        "criteria": {"required_fields": ["report"],
                     "min_length": {"report": 50}}})
    assert q.status_code == 200
    qid = q.json()["quote_id"]

    e = client.post("/escrow", json={
        "quote_id": qid, "buyer_did": buyer,
        "idempotency_key": "k-1"})
    assert e.status_code == 200
    eid = e.json()["escrow_id"]

    # idempotent re-fund returns the same escrow
    e2 = client.post("/escrow", json={
        "quote_id": qid, "buyer_did": buyer,
        "idempotency_key": "k-1"})
    assert e2.json()["escrow_id"] == eid and e2.json()["idempotent"]

    d = client.post(f"/escrow/{eid}/deliver", json={
        "seller_did": seller,
        "evidence": {"report": "relatorio de mercado A2A " * 10,
                     "sources": ["a2a-protocol.org"]}})
    assert d.status_code == 200

    v = client.post(f"/escrow/{eid}/verify", json={"live": True})
    assert v.status_code == 200
    body = v.json()
    assert body["stage_a"]["passed"]
    assert body["verdict"] == "release" and body["state"] == "RELEASED"
    assert body["panel"]["approvals"] >= 2

    esc = client.get(f"/escrow/{eid}").json()
    assert esc["escrow"]["state"] == "RELEASED"
    assert any(x["reason"] == "release" for x in esc["ledger"])

    chain = client.get("/audit/verify").json()
    assert chain["ok"]


def test_stage_a_reject_retains_escrow(client):
    _, buyer, seller = _setup(client)
    qid = client.post("/quotes", json={
        "buyer_did": buyer, "seller_did": seller,
        "scope": "relatorio", "price": 10.0,
        "criteria": {"min_length": {"report": 500}}}).json()["quote_id"]
    eid = client.post("/escrow", json={
        "quote_id": qid, "buyer_did": buyer,
        "idempotency_key": "k-2"}).json()["escrow_id"]
    client.post(f"/escrow/{eid}/deliver", json={
        "seller_did": seller, "evidence": {"report": "lixo"}})
    v = client.post(f"/escrow/{eid}/verify", json={"live": True})
    body = v.json()
    assert not body["stage_a"]["passed"]
    assert body["verdict"] == "retain" and body["state"] == "REJECTED"
    assert body["panel"] is None  # no judge spend on deterministic failure

    d = client.post(f"/escrow/{eid}/dispute", json={
        "opener_did": seller, "reason": "criterio subjetivo"})
    assert d.status_code == 200
    a = client.post(f"/escrow/{eid}/arbitrate", json={
        "ruling": "buyer", "rationale": "entregavel abaixo da rubrica"})
    assert a.json()["state"] == "RESOLVED" and a.json()["ruling"] == "buyer"


def test_policy_denies_over_cap(client):
    _, buyer, seller = _setup(client)
    qid = client.post("/quotes", json={
        "buyer_did": buyer, "seller_did": seller,
        "scope": "relatorio", "price": 999.0,
        "criteria": {}}).json()["quote_id"]
    r = client.post("/escrow", json={
        "quote_id": qid, "buyer_did": buyer, "idempotency_key": "k-3"})
    assert r.status_code == 400 and "policy denied" in r.json()["detail"]


def test_unknown_escrow_404(client):
    assert client.get("/escrow/e-nope").status_code == 404
    assert client.post("/escrow/e-nope/verify",
                       json={"live": False}).status_code == 404
