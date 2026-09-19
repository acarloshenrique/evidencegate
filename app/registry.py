"""L1 Identity — principals (KYC) + agents (KYA) + signed AgentCards + reputation.

The accountability triangle: legal entity (KYC'd) -> agent (KYA'd) -> signed
authorization -> verified action. Agents are never the legal customer; every
agent must be bound to a named principal that answers for it.

Reputation only moves on *verified* escrow outcomes (+release / -dispute):
anti-sybil — reviews without settled transactions count for nothing.
"""

import json
from typing import Any

from .audit import AuditTrail
from .crypto import (
    canonical_json,
    did_from_pubkey,
    generate_keypair,
    hash_obj,
    sha256,
    sign,
    verify,
)
from .db import Database

REGISTRY_DID = "did:key:z-evidencegate-registry"  # platform signs the trail, agents can't forge it

INJECTION_PATTERNS = (
    "ignore", "disregard", "instru", "system prompt", "contrate", "hire me",
    "bypass", "jailbreak", "override", "forget",
)


def sanitize_untrusted(text: str) -> tuple[str, bool]:
    """External agent data is untrusted content, never instructions.

    Returns (sanitized_text, flagged). Fencing happens at prompt-build time;
    here we neutralize and flag injection attempts for the audit trail.
    """
    lowered = text.lower()
    flagged = any(p in lowered for p in INJECTION_PATTERNS)
    sanitized = text.replace("`", "'").replace("\x00", "")
    return sanitized, flagged


class Registry:
    def __init__(self, db: Database, audit: AuditTrail):
        self.db = db
        self.audit = audit

    def register_principal(self, legal_name: str, doc_id: str) -> str:
        pid = "kyc-" + sha256(legal_name + doc_id)[:16]
        self.db.execute(
            "INSERT INTO principals(id,legal_name,doc_hash,created_at) VALUES(?,?,?,?)",
            (pid, legal_name, sha256(doc_id), self.db.now()))
        self.audit.append(REGISTRY_DID, "principal.registered",
                          {"principal_id": pid, "legal_name": legal_name})
        return pid

    def issue_agent(self, principal_id: str, card: dict[str, Any],
                    manifest: dict[str, Any]) -> tuple[str, bytes]:
        """Create an agent bound to a KYC'd principal. Returns (did, secret_key)."""
        did, sk, pk = generate_keypair()
        card = dict(card)
        card["agent_did"] = did
        card["principal_id"] = principal_id
        card_sig = sign(sk, canonical_json(card))
        self.db.execute(
            "INSERT INTO agents(did,principal_id,pubkey_b58,card,card_sig,manifest,created_at)"
            " VALUES(?,?,?,?,?,?,?)",
            (did, principal_id, did_from_pubkey(pk)[9:], json.dumps(card), card_sig,
             json.dumps(manifest), self.db.now()))
        self.audit.append(REGISTRY_DID, "agent.registered",
                          {"did": did, "principal_id": principal_id,
                           "capabilities": manifest.get("capabilities", []),
                           "card_hash": hash_obj(card)})
        return did, sk

    def verify_card(self, did: str) -> dict:
        """Verify an AgentCard signature against the registry pin (RF-1, kills 2.1 spoofing)."""
        row = self.db.execute("SELECT * FROM agents WHERE did=?", (did,)).fetchone()
        if not row:
            return {"ok": False, "reason": "unknown agent"}
        if row["status"] != "active":
            return {"ok": False, "reason": f"agent {row['status']}"}
        card = json.loads(row["card"])
        ok = verify(did, canonical_json(card), row["card_sig"])
        if not ok:
            self.audit.append(REGISTRY_DID, "agent.card_invalid", {"did": did})
        return {"ok": ok, "card": card, "manifest": json.loads(row["manifest"]),
                "reputation": row["reputation"]}

    def introspect_card(self, did: str) -> dict:
        """Discovery-time view: verified card with free text sanitized + flagged."""
        res = self.verify_card(did)
        if not res["ok"]:
            return res
        card = res["card"]
        flagged = False
        for field in ("description",):
            if field in card:
                card[field], f = sanitize_untrusted(str(card[field]))
                flagged = flagged or f
        for skill in card.get("skills", []):
            if "description" in skill:
                skill["description"], f = sanitize_untrusted(str(skill["description"]))
                flagged = flagged or f
        if flagged:
            self.audit.append(REGISTRY_DID, "agent.injection_flagged", {"did": did})
        return res | {"card": card, "injection_flagged": flagged}

    def adjust_reputation(self, did: str, delta: float, reason: str, escrow_id: str) -> None:
        """Score moves ONLY on settled outcomes — no score from unverified reviews (§2.4)."""
        assert reason in ("release", "dispute_upheld", "dispute_overturned",
                          "judge_contested", "judge_faulty")
        self.db.execute("UPDATE agents SET reputation = reputation + ? WHERE did=?",
                        (delta, did))
        self.audit.append(REGISTRY_DID, "agent.reputation",
                          {"did": did, "delta": delta, "reason": reason, "escrow_id": escrow_id})

    def revoke(self, did: str, reason: str) -> None:
        self.db.execute("UPDATE agents SET status='revoked' WHERE did=?", (did,))
        self.audit.append(REGISTRY_DID, "agent.revoked", {"did": did, "reason": reason})

    def list_agents(self, capability: str | None = None) -> list[dict]:
        rows = self.db.execute(
            "SELECT did,reputation,manifest,card FROM agents WHERE status='active'").fetchall()
        out = []
        for r in rows:
            m = json.loads(r["manifest"])
            if capability and capability not in m.get("capabilities", []):
                continue
            out.append({"did": r["did"], "reputation": r["reputation"],
                        "capabilities": m.get("capabilities", []),
                        "fuses": m.get("fuses", {}), "card": json.loads(r["card"])})
        return out
