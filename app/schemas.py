"""Request/response schemas for the EvidenceGate HTTP API (T009)."""

from typing import Any, Literal

from pydantic import BaseModel, Field


# --- requests ---------------------------------------------------------------
class PrincipalIn(BaseModel):
    legal_name: str = Field(min_length=1)
    doc_id: str = Field(min_length=1,
                        description="legal doc (CNPJ/CPF) — only its hash is stored")


class AgentIn(BaseModel):
    principal_id: str = Field(description="id returned by POST /principals")
    card: dict[str, Any] = Field(
        default_factory=dict,
        description="AgentCard free-form fields (description, skills, ...)")
    manifest: dict[str, Any] = Field(
        default_factory=dict,
        description="KYA manifest: capabilities + fuses")


class CardVerifyIn(BaseModel):
    did: str


class QuoteIn(BaseModel):
    buyer_did: str
    seller_did: str
    scope: str
    criteria: dict[str, Any] = Field(
        default_factory=dict,
        description="acceptance rubric — locked into quote_hash, immutable after")
    price: float = Field(gt=0)
    deadline: float | None = Field(default=None,
                                   description="unix ts; defaults to now + 1h")


class EscrowCreateIn(BaseModel):
    """Fund a quote -> creates the escrow atomically (FUNDED). Idempotent."""
    quote_id: str
    buyer_did: str
    idempotency_key: str


class DeliverIn(BaseModel):
    seller_did: str
    evidence: dict[str, Any]


class VerifyIn(BaseModel):
    live: bool = Field(
        default=True,
        description="true: run the judge panel on NeuraLake after stage A. "
                    "false: stage A only — no judge spend, no settle")


class DisputeIn(BaseModel):
    opener_did: str
    reason: str


class ArbitrateIn(BaseModel):
    ruling: Literal["buyer", "seller"]
    rationale: str


# --- responses --------------------------------------------------------------
class PrincipalOut(BaseModel):
    principal_id: str


class AgentOut(BaseModel):
    agent_did: str
    card: dict[str, Any]
    card_sig: str
    secret_key_b58: str = Field(
        description="custodial key — the server also keeps it to sign quotes")
    manifest: dict[str, Any]


class QuoteOut(BaseModel):
    quote_id: str
    quote_hash: str


class EscrowCreatedOut(BaseModel):
    escrow_id: str
    state: str | None = None
    idempotent: bool = False


class DeliverOut(BaseModel):
    evidence_hash: str


class VerifyOut(BaseModel):
    escrow_id: str
    stage_a: dict[str, Any]
    panel: dict[str, Any] | None = None
    verdict: str = Field(description="release | retain | pending_panel")
    state: str


class StateOut(BaseModel):
    escrow_id: str
    state: str
    ruling: str | None = None
