# PRODUCT.md — EvidenceGate

> Inferred from the explicit brief and repository docs (PRD, PITCH, STATUS);
> assumptions are labeled. Interview skipped at owner's direction.

## What it is

Fé pública programável para a economia de agentes: escrow cuja liquidação é
condicionada a verificação independente, identidade criptográfica
(KYC principal → KYA agent, Ed25519/did:key, AgentCard assinado) e trilha de
auditoria append-only hash-chained.

## Thesis

A2A lets agents talk; x402/AP2 let them pay. Neither answers whether the
delivered work was good — and settlement is final. EvidenceGate is the missing
trust layer: money leaves escrow only when verification confirms the delivery
met the rubric locked in the quote.

## Audience

- **Near term (hackathon jury):** must see a working, honest system — not a
  toy — within a 4-minute pitch. Criteria: A2A autonomy, real functionality,
  efficiency, NeuraLake/Agora usage.
- **Real term:** teams operating agent-to-agent workflows who need
  accountability a bank or auditor accepts; enterprises that cannot let
  agents move money without tamper-evident records.

## Surfaces (web)

| Route | Mode | Job |
|---|---|---|
| `/` | Persuade | land the thesis, prove the system is live, route to dashboard/API |
| `/design` | Read | the design system itself — tokens, type, components, rules |
| `/dashboard` | Operate | live escrows, audit trail, cost, chain integrity |
| `/voice` | Operate | voice auditor (Agora ConvoAI → custom LLM) |

## Proof, not claims

- `/metrics`, `/escrows`, `/audit`, `/agents` are live data the landing and
  dashboard render; nothing is mocked on the marketing surface.
- Live demo cost ≈ $0.0106 / 7 calls — shown, not stated.

## Assumptions (labeled)

- Portuguese-first copy (team and jury are Brazilian).
- Stripe-inspired token set supplied by owner is the pinned palette/type
  direction; Apple-grade restraint and functional glass are the owner's
  explicit add-ons.
- Voice page remains Portuguese (STT is pt-BR, TTS is pt-BR voice).
