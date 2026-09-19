"""L2 Policy — enforced in code, never in the prompt.

"Authorization asks 'should this payment be authorized'; verification asks
'was the work good'. A system with only the first pays for garbage inside policy."

Delegation scope is strictly decreasing (caveat-chain style): a delegated agent
receives a sub-budget and sub-permissions of its delegator — never wider.
"""

from dataclasses import dataclass, field

from .db import Database


@dataclass
class Policy:
    max_tx_value: float = 50.0            # cap por transacao
    session_cap: float = 200.0            # cap por sessao/orcamento total
    human_threshold: float = 100.0        # acima disso escala pra humano
    allowlist: set[str] = field(default_factory=set)   # dids permitidos (vazio = todos)
    max_delegation_depth: int = 3


@dataclass
class Decision:
    allow: bool
    escalate: bool = False
    reason: str = ""


class PolicyEngine:
    def __init__(self, db: Database, policy: Policy | None = None):
        self.db = db
        self.policy = policy or Policy()

    def session_spend(self, buyer_did: str) -> float:
        row = self.db.execute(
            "SELECT COALESCE(SUM(-delta),0) s FROM ledger WHERE account=? AND reason IN"
            " ('fund','release')", (buyer_did,)).fetchone()
        return row["s"]

    def check_payment(self, buyer_did: str, seller_did: str, amount: float,
                      depth: int = 0) -> Decision:
        p = self.policy
        if depth > p.max_delegation_depth:
            return Decision(False, reason=f"delegation depth {depth} > {p.max_delegation_depth}")
        if p.allowlist and seller_did not in p.allowlist:
            return Decision(False, reason="seller not in allowlist")
        if amount > p.max_tx_value:
            if amount > p.human_threshold:
                return Decision(False, escalate=True,
                                reason=f"tx {amount} > human_threshold {p.human_threshold}")
            return Decision(False, reason=f"tx {amount} > max_tx {p.max_tx_value}")
        if self.session_spend(buyer_did) + amount > p.session_cap:
            return Decision(False, reason="session cap exceeded")
        return Decision(True)

    def delegate_scope(self, parent_fuses: dict, requested: dict) -> dict:
        """Sub-delegation can only narrow: min(budget), intersect(tools), +1 depth."""
        return {
            "max_tx_value": min(parent_fuses.get("max_tx_value", 0),
                                requested.get("max_tx_value", 0)),
            "allowed_tools": sorted(set(parent_fuses.get("allowed_tools", []))
                                    & set(requested.get("allowed_tools", []))),
            "depth": parent_fuses.get("depth", 0) + 1,
        }
