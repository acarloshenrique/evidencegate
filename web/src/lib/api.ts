/**
 * Cliente do backend EvidenceGate (app/main.py).
 *
 * O painel é só leitura: ele observa o que a camada de confiança gravou —
 * ledger, trilha hash-encadeada e custo de inferência por decisão. Nada aqui
 * muda estado; auditor não opera o escrow, audita.
 */

export type ChainStatus =
  | { ok: true; length: number }
  | { ok: false; tampered_seq: number; expected?: string; stored?: string; detail?: string }

export interface InferenceCall {
  model_requested: string
  model_used: string
  prompt_tokens: number
  completion_tokens: number
  cost: number
}

export interface Metrics {
  inference_cost: number
  inference_calls: number
  calls: InferenceCall[]
  chain: ChainStatus
}

export const ESCROW_STATES = [
  'QUOTED',
  'FUNDED',
  'DELIVERED',
  'VERIFIED',
  'RELEASED',
  'REJECTED',
  'DISPUTED',
  'ARBITRATED',
  'RESOLVED',
] as const

export type EscrowState = (typeof ESCROW_STATES)[number]

export interface EscrowRow {
  id: string
  state: EscrowState
  created_at: number
  price: number
  scope: string
  buyer_did: string
  seller_did: string
}

export interface AuditEvent {
  seq: number
  ts: number
  actor_did: string
  action: string
  payload_hash: string
  prev_hash: string
  event_hash: string
  payload?: Record<string, unknown>
}

export interface LedgerEntry {
  account: string
  delta: number
  reason: string
  ts: number
}

export interface JudgeVote {
  judge: string
  commit_hash: string
  vote: 'approve' | 'reject' | null
  confidence: number | null
  rationale: string | null
  revealed: number
}

export interface Quote {
  id: string
  buyer_did: string
  seller_did: string
  scope: string
  criteria: Record<string, unknown>
  price: number
  deadline: number
  quote_hash: string
  signature: string
  status: string
  created_at: number
}

export interface EscrowDetail {
  escrow: {
    id: string
    quote_id: string
    state: EscrowState
    evidence: Record<string, unknown> | null
    evidence_hash: string | null
    verdict: string | null
    dispute: string | null
    created_at: number
    updated_at: number
  }
  quote: Quote | null
  ledger: LedgerEntry[]
  votes: JudgeVote[]
  events: AuditEvent[]
}

export interface Agent {
  did: string
  reputation: number
  capabilities: string[]
  fuses: Record<string, unknown>
  card: Record<string, unknown>
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(path, { headers: { accept: 'application/json' } })
  if (!r.ok) throw new Error(`${path} -> HTTP ${r.status}`)
  return (await r.json()) as T
}

export const api = {
  metrics: () => get<Metrics>('/metrics'),
  escrows: () => get<{ escrows: EscrowRow[] }>('/escrows'),
  audit: () => get<{ events: AuditEvent[] }>('/audit'),
  agents: () => get<{ agents: Agent[] }>('/agents'),
  escrow: (id: string) => get<EscrowDetail>(`/escrow/${id}`),
  health: () => get<{ status: string; service: string }>('/health'),
}
