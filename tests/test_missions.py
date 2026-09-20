"""Mission outcome, provenance, budget and replay tests; no paid inference."""

import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.main import Services, create_app
from app.missions import MissionRequest, mission_metrics


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EG_DB_PATH", str(tmp_path / "missions.db"))
    monkeypatch.setenv("EG_ENABLE_MISSION_DEMO", "1")
    with TestClient(create_app()) as client:
        yield client


def run(client, key="mission-test-001", **kwargs):
    return client.post("/missions/run", json={"idempotency_key": key, **kwargs})


def test_attack_replacement_completes_with_verified_receipts(client):
    result = run(client).json()
    assert result["status"] == "COMPLETED"
    assert result["spent"] == 20 <= result["budget"]
    assert result["result"]["threat_count"] == 2
    m = result["metrics"]
    assert (m["decisions"], m["handoffs_completed"], m["human_interventions"]) == (11, 3, 0)
    assert (m["threats_blocked"], m["automatic_replacements"]) == (1, 1)
    blocked = next(
        e["payload"]["candidate"]
        for e in result["events"]
        if e["action"] == "mission.decision" and e["payload"]["choice"] == "block"
    )
    escrows = client.get("/escrows").json()["escrows"]
    assert len(escrows) == 3
    assert all(e["state"] == "RELEASED" and e["seller_did"] != blocked for e in escrows)
    dispatched = [
        e["payload"] for e in result["events"] if e["action"] == "mission.handoff.dispatched"
    ]
    completed = [
        e["payload"] for e in result["events"] if e["action"] == "mission.handoff.completed"
    ]
    for i in (1, 2):
        assert dispatched[i]["parent_receipt"]["artifact_hash"] == completed[i - 1]["artifact_hash"]
        assert dispatched[i]["from_agent"] == completed[i - 1]["to_agent"]
    metrics = client.get("/metrics").json()
    assert metrics["inference_calls"] == 0
    assert metrics["stage_a"] == {"resolved_free": 3, "verifications": 3}
    assert metrics["chain"]["ok"]
    # Every new metric is derived from evidence, independent of the response cache.
    assert metrics["mission_autonomy"] == m


def test_retries_do_not_add_events_or_funds_and_conflicts_are_rejected(client):
    first = run(client).json()
    before = client.get("/audit").json()
    assert run(client).json() == first
    assert client.get("/audit").json() == before
    assert run(client, budget=40).status_code == 409
    assert len(client.get("/escrows").json()["escrows"]) == 3


def test_budget_failure_before_any_funding(client):
    result = run(client, budget=19).json()
    assert result["status"] == "FAILED" and result["spent"] == 0
    assert result["metrics"]["handoffs_completed"] == 0
    assert not client.get("/escrows").json()["escrows"]


def test_clean_scenario_has_no_invented_attack(client):
    result = run(client, scenario="clean").json()
    assert result["status"] == "COMPLETED"
    assert result["metrics"]["threats_blocked"] == 0
    assert result["metrics"]["automatic_replacements"] == 0
    assert result["metrics"]["decisions"] == 10


def test_bad_delivery_stops_downstream_and_retains_payment(client):
    client.app.state.svc.missions.executors["triage"] = lambda _: {"threats": []}
    result = run(client).json()
    assert result["status"] == "FAILED"
    assert result["metrics"]["handoffs_completed"] == 1
    escrows = client.get("/escrows").json()["escrows"]
    assert sorted(e["state"] for e in escrows) == ["REJECTED", "RELEASED"]
    rejected = next(e for e in escrows if e["state"] == "REJECTED")
    detail = client.get("/escrow/" + rejected["id"]).json()
    assert not any(e["reason"] == "release" for e in detail["ledger"])
    assert client.get("/audit/verify").json()["ok"]


def test_policy_denial_and_tampered_chain_stop_funding(client):
    svc = client.app.state.svc
    svc.policy.policy.allowlist = {"nonexistent-agent"}
    assert run(client).json()["status"] == "FAILED"
    assert not client.get("/escrows").json()["escrows"]
    svc.db.execute("UPDATE events SET action='forged' WHERE seq=1")
    assert run(client, key="mission-tampered").json()["status"] == "FAILED"
    assert not client.get("/escrows").json()["escrows"]


def test_modified_receipt_prevents_next_handoff(client, monkeypatch):
    svc = client.app.state.svc
    append = svc.audit.append

    def tamper_after_receipt(actor, action, payload):
        event = append(actor, action, payload)
        if action == "mission.handoff.completed" and payload["step"] == "collect":
            svc.db.execute("UPDATE escrows SET evidence='{}' WHERE id=?", (payload["escrow_id"],))
        return event

    monkeypatch.setattr(svc.audit, "append", tamper_after_receipt)
    result = run(client).json()
    assert result["status"] == "FAILED"
    assert "adulterada" in result["error"]
    assert result["metrics"]["handoffs_completed"] == 1
    assert len(client.get("/escrows").json()["escrows"]) == 1


def test_replay_survives_restart_and_concurrent_requests(tmp_path):
    path = tmp_path / "mission.db"
    svc = Services(path)
    request = MissionRequest(idempotency_key="concurrent-001")
    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = list(pool.map(lambda _: svc.missions.run(request), range(2)))
    assert a["id"] == b["id"] and a["status"] == "COMPLETED"
    svc.db.conn.close()
    restarted = Services(path)
    assert restarted.missions.run(request)["id"] == a["id"]
    assert len(restarted.missions.list()) == 1
    assert restarted.audit.verify_chain()["ok"]
    restarted.db.conn.close()


def test_metric_deduplication_and_unknown_events(client):
    events = run(client).json()["events"]
    expected = mission_metrics(events)
    assert mission_metrics(events + events) == expected
    events.append({"action": "mission.debug", "payload": {"mission_id": "m-extra"}})
    assert mission_metrics(events) == expected


def test_demo_requires_opt_in_and_valid_request(client, monkeypatch):
    assert run(client, budget=0).status_code == 422
    assert client.get("/missions/missing").status_code == 404
    monkeypatch.delenv("EG_ENABLE_MISSION_DEMO")
    assert run(client).status_code == 403


def test_sse_chat_contract(client):
    class FakeChat:
        calls = []
        total_cost = 0

        def complete(self, messages, **kwargs):
            return {
                "content": "Dois indicadores na missão.",
                "model_used": "test",
                "prompt_tokens": 0,
                "completion_tokens": 0,
            }

    client.app.state.svc._nl = FakeChat()
    response = client.post(
        "/chat/completions",
        json={"stream": True, "messages": [{"role": "user", "content": "Qual resultado?"}]},
    )
    assert response.headers["content-type"].startswith("text/event-stream")
    frames = [x[6:] for x in response.text.splitlines() if x.startswith("data: ")]
    assert frames[-1] == "[DONE]"
    assert json.loads(frames[0])["choices"][0]["delta"]["content"] == "Dois indicadores na missão."
