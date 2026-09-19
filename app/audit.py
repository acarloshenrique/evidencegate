"""Append-only, hash-chained audit trail (L5).

Each event: sha256( seq || ts || actor || action || payload || prev_hash ).
verify_chain() re-derives every hash — flip one character anywhere in history
and verification FAILS pointing at the first adulterated entry (Kessa model:
the verifier re-derives, it doesn't trust the log).
"""

import json
from typing import Any

from .crypto import canonical_json, sha256
from .db import Database

GENESIS = "0" * 64


class AuditTrail:
    def __init__(self, db: Database):
        self.db = db

    def _last_hash(self) -> str:
        row = self.db.execute("SELECT event_hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        return row["event_hash"] if row else GENESIS

    @staticmethod
    def _event_hash(seq: int, ts: float, actor: str, action: str, payload: str, prev: str) -> str:
        return sha256(canonical_json({
            "seq": seq, "ts": ts, "actor": actor, "action": action,
            "payload": payload, "prev_hash": prev,
        }))

    def append(self, actor_did: str, action: str, payload: dict[str, Any]) -> dict:
        payload_c = canonical_json(payload).decode()
        prev = self._last_hash()
        ts = self.db.now()
        with self.db.tx():
            cur = self.db.execute("SELECT COALESCE(MAX(seq),0)+1 AS s FROM events")
            seq = cur.fetchone()["s"]
            eh = self._event_hash(seq, ts, actor_did, action, payload_c, prev)
            self.db.execute(
                "INSERT INTO events(ts,actor_did,action,payload,payload_hash,prev_hash,event_hash)"
                " VALUES(?,?,?,?,?,?,?)",
                (ts, actor_did, action, payload_c, sha256(payload_c), prev, eh),
            )
        return {"seq": seq, "ts": ts, "actor": actor_did, "action": action,
                "event_hash": eh, "prev_hash": prev}

    def verify_chain(self) -> dict:
        """Re-derive the whole chain. Returns ok or the first tampered entry."""
        prev = GENESIS
        for row in self.db.execute("SELECT * FROM events ORDER BY seq"):
            expected = self._event_hash(
                row["seq"], row["ts"], row["actor_did"], row["action"], row["payload"], prev)
            if expected != row["event_hash"] or row["prev_hash"] != prev:
                return {"ok": False, "tampered_seq": row["seq"],
                        "expected": expected, "stored": row["event_hash"]}
            if sha256(row["payload"]) != row["payload_hash"]:
                return {"ok": False, "tampered_seq": row["seq"], "detail": "payload_hash mismatch"}
            prev = row["event_hash"]
        return {"ok": True, "length": prev != GENESIS and self.db.execute(
            "SELECT COUNT(*) c FROM events").fetchone()["c"] or 0}

    def for_escrow(self, escrow_id: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM events WHERE payload LIKE ? ORDER BY seq",
            (f"%{escrow_id}%",)).fetchall()
        return [dict(r) | {"payload": json.loads(r["payload"])} for r in rows]
