"""L4 Escrow — verification as the settlement condition.

States: QUOTED -> FUNDED -> DELIVERED -> VERIFIED -> RELEASED
                            \\-> REJECTED -> DISPUTED -> ARBITRATED -> RESOLVED

x402 settles finally with no chargeback; EvidenceGate makes settlement
conditional on independent verification. Idempotent funding, explicit
atomicity — no ambiguous intermediate states (kills §2.7 payment hijack).
"""

import json
import uuid
from typing import Any

from .audit import AuditTrail
from .crypto import canonical_json, hash_obj, sign
from .db import Database
from .policy import Decision, PolicyEngine
from .registry import REGISTRY_DID, Registry

ESCROW_STATES = ("QUOTED", "FUNDED", "DELIVERED", "VERIFIED", "RELEASED",
                 "REJECTED", "DISPUTED", "ARBITRATED", "RESOLVED")

_TRANSITIONS = {
    "QUOTED": {"FUNDED"},
    "FUNDED": {"DELIVERED"},
    "DELIVERED": {"VERIFIED", "REJECTED"},
    "VERIFIED": {"RELEASED"},
    "REJECTED": {"DISPUTED"},
    "DISPUTED": {"ARBITRATED"},
    "ARBITRATED": {"RESOLVED"},
    "RELEASED": set(),
    "RESOLVED": set(),
}


class EscrowError(Exception):
    pass


class EscrowEngine:
    def __init__(self, db: Database, audit: AuditTrail, registry: Registry,
                 policy: PolicyEngine):
        self.db, self.audit, self.registry, self.policy = db, audit, registry, policy

    # --- helpers ---------------------------------------------------------
    def _state(self, escrow_id: str) -> str:
        row = self.db.execute("SELECT state FROM escrows WHERE id=?", (escrow_id,)).fetchone()
        if not row:
            raise EscrowError(f"unknown escrow {escrow_id}")
        return row["state"]

    def _move(self, escrow_id: str, to: str, actor: str, payload: dict) -> None:
        cur = self._state(escrow_id)
        if to not in _TRANSITIONS[cur]:
            raise EscrowError(f"illegal transition {cur} -> {to}")
        self.db.execute("UPDATE escrows SET state=?, updated_at=? WHERE id=?",
                        (to, self.db.now(), escrow_id))
        self.audit.append(actor, f"escrow.{to.lower()}",
                          {"escrow_id": escrow_id, "from": cur, **payload})

    def _ledger(self, account: str, delta: float, reason: str, escrow_id: str) -> None:
        self.db.execute(
            "INSERT INTO ledger(account,delta,reason,escrow_id,ts) VALUES(?,?,?,?,?)",
            (account, delta, reason, escrow_id, self.db.now()))
        self.db.execute(
            "INSERT INTO balances(account,amount) VALUES(?,?) "
            "ON CONFLICT(account) DO UPDATE SET amount=amount+?",
            (account, delta, delta))

    def balance(self, account: str) -> float:
        row = self.db.execute("SELECT amount FROM balances WHERE account=?",
                              (account,)).fetchone()
        return row["amount"] if row else 0.0

    # --- flow ------------------------------------------------------------
    def create_quote(self, buyer_did: str, seller_did: str, scope: str,
                     criteria: dict[str, Any], price: float, deadline: float,
                     seller_sk: bytes) -> dict:
        """Seller signs the quote — rubrica fica TRAVADA aqui, imutável depois."""
        quote = {"buyer": buyer_did, "seller": seller_did, "scope": scope,
                 "criteria": criteria, "price": price, "deadline": deadline}
        qh = hash_obj(quote)
        sig = sign(seller_sk, canonical_json({"quote_hash": qh}))
        qid = "q-" + uuid.uuid4().hex[:12]
        self.db.execute(
            "INSERT INTO quotes(id,buyer_did,seller_did,scope,criteria,price,deadline,"
            "quote_hash,signature,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (qid, buyer_did, seller_did, scope, json.dumps(criteria), price, deadline,
             qh, sig, self.db.now()))
        self.audit.append(seller_did, "quote.created",
                          {"quote_id": qid, "buyer": buyer_did, "price": price,
                           "quote_hash": qh})
        return {"quote_id": qid, "quote_hash": qh}

    def accept_and_fund(self, quote_id: str, buyer_did: str,
                        idempotency_key: str) -> dict:
        """Policy check in code BEFORE locking funds (RF-9). Idempotent."""
        row = self.db.execute("SELECT * FROM quotes WHERE id=?", (quote_id,)).fetchone()
        if not row:
            raise EscrowError("unknown quote")
        if row["buyer_did"] != buyer_did:
            raise EscrowError("quote belongs to another buyer")
        decision: Decision = self.policy.check_payment(
            buyer_did, row["seller_did"], row["price"])
        if not decision.allow:
            self.audit.append(REGISTRY_DID, "policy.denied",
                              {"quote_id": quote_id, "reason": decision.reason,
                               "escalate": decision.escalate})
            raise EscrowError(f"policy denied: {decision.reason}")
        existing = self.db.execute(
            "SELECT id FROM escrows WHERE idempotency=?", (idempotency_key,)).fetchone()
        if existing:
            return {"escrow_id": existing["id"], "idempotent": True}
        eid = "e-" + uuid.uuid4().hex[:12]
        with self.db.tx():
            self.db.execute(
                "INSERT INTO escrows(id,quote_id,state,idempotency,created_at,updated_at)"
                " VALUES(?,?,'QUOTED',?,?,?)",
                (eid, quote_id, idempotency_key, self.db.now(), self.db.now()))
            self.db.execute("UPDATE quotes SET status='accepted' WHERE id=?", (quote_id,))
        self._ledger(buyer_did, -row["price"], "fund", eid)
        self._ledger(f"escrow:{eid}", +row["price"], "lock", eid)
        self._move(eid, "FUNDED", buyer_did,
                   {"amount": row["price"], "idempotency": idempotency_key})
        return {"escrow_id": eid, "state": "FUNDED"}

    def deliver(self, escrow_id: str, seller_did: str,
                evidence: dict[str, Any]) -> dict:
        row = self.db.execute(
            "SELECT q.seller_did FROM escrows e JOIN quotes q ON e.quote_id=q.id"
            " WHERE e.id=?", (escrow_id,)).fetchone()
        if row["seller_did"] != seller_did:
            raise EscrowError("only the contracted seller can deliver")
        eh = hash_obj(evidence)
        self.db.execute("UPDATE escrows SET evidence=?, evidence_hash=? WHERE id=?",
                        (json.dumps(evidence), eh, escrow_id))
        self._move(escrow_id, "DELIVERED", seller_did, {"evidence_hash": eh})
        return {"evidence_hash": eh}

    def settle_verdict(self, escrow_id: str, verdict: str,
                       panel_summary: dict) -> dict:
        """Called by the verifier. release -> seller paid; retain -> refund + dispute path."""
        row = self.db.execute(
            "SELECT q.* FROM escrows e JOIN quotes q ON e.quote_id=q.id WHERE e.id=?",
            (escrow_id,)).fetchone()
        price, buyer, seller = row["price"], row["buyer_did"], row["seller_did"]
        if verdict == "release":
            self._move(escrow_id, "VERIFIED", REGISTRY_DID, {"panel": panel_summary})
            self._ledger(f"escrow:{escrow_id}", -price, "release", escrow_id)
            self._ledger(seller, +price, "release", escrow_id)
            self._move(escrow_id, "RELEASED", REGISTRY_DID, {"amount": price})
            self.registry.adjust_reputation(seller, +2, "release", escrow_id)
            return {"state": "RELEASED"}
        self._move(escrow_id, "REJECTED", REGISTRY_DID, {"panel": panel_summary})
        return {"state": "REJECTED"}

    def dispute(self, escrow_id: str, opener_did: str, reason: str) -> dict:
        self.db.execute("UPDATE escrows SET dispute=? WHERE id=?", (reason, escrow_id))
        self._move(escrow_id, "DISPUTED", opener_did, {"reason": reason})
        return {"state": "DISPUTED"}

    def arbitrate(self, escrow_id: str, ruling: str, rationale: str) -> dict:
        """Final ruling from the dispute tribunal. 'buyer' refunds, 'seller' pays out."""
        self._move(escrow_id, "ARBITRATED", REGISTRY_DID,
                   {"ruling": ruling, "rationale": rationale})
        row = self.db.execute(
            "SELECT q.* FROM escrows e JOIN quotes q ON e.quote_id=q.id WHERE e.id=?",
            (escrow_id,)).fetchone()
        price, buyer, seller = row["price"], row["buyer_did"], row["seller_did"]
        if ruling == "buyer":
            self._ledger(f"escrow:{escrow_id}", -price, "refund", escrow_id)
            self._ledger(buyer, +price, "refund", escrow_id)
            self.registry.adjust_reputation(seller, -3, "dispute_upheld", escrow_id)
        else:
            self._ledger(f"escrow:{escrow_id}", -price, "release", escrow_id)
            self._ledger(seller, +price, "release", escrow_id)
            self.registry.adjust_reputation(seller, +1, "dispute_overturned", escrow_id)
        self._move(escrow_id, "RESOLVED", REGISTRY_DID, {"ruling": ruling})
        return {"state": "RESOLVED", "ruling": ruling}
