# Compliance Report — escrow e-aaaf83cbb81e

| seq | ts | actor | action | detalhe |
|---|---|---|---|---|
| 11 | 1789844164 | did:key:z6MkeZkMn3gps3HQ | escrow.funded | {"amount": 20.0, "escrow_id": "e-aaaf83cbb81e", "from": "QUOTED", "idempotency": "fund-1"} |
| 12 | 1789844164 | did:key:z6MknEhixJPgquSo | escrow.delivered | {"escrow_id": "e-aaaf83cbb81e", "evidence_hash": "2376c30cda3808826a05a06baf823dbe61e2a14d2a445ffe3af3f866b1a96a12", "fr |
| 13 | 1789844199 | did:key:z-evidencegate-a | verify.panel | {"approvals": 2, "avg_confidence": 0.65, "escrow_id": "e-aaaf83cbb81e", "judges": ["reasoning", "reasoning-pro", "code"] |
| 14 | 1789844199 | did:key:z-evidencegate-r | escrow.verified | {"escrow_id": "e-aaaf83cbb81e", "from": "DELIVERED", "panel": {"approvals": 2, "avg_confidence": 0.65, "escalate_to_huma |
| 15 | 1789844199 | did:key:z-evidencegate-r | escrow.released | {"amount": 20.0, "escrow_id": "e-aaaf83cbb81e", "from": "VERIFIED"} |
| 16 | 1789844199 | did:key:z-evidencegate-r | agent.reputation | {"delta": 2, "did": "did:key:z6MknEhixJPgquSosJX42NaZfpK4YbZMYxq82BFc3tdfBXZs", "escrow_id": "e-aaaf83cbb81e", "reason": |

**Trilha íntegra:** SIM
**Eventos:** 6 · **Event hash head:** `678324e095f1d2bd...`