/**
 * Cliente do backend EvidenceGate (app/main.py).
 *
 * Consultas de auditoria e comando explícito para iniciar missões de sandbox.
 * O backend executa e registra as decisões; a interface exibe a evidência.
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
  autonomy?: { decisions: number; human_interventions: number }
  stage_a?: { resolved_free: number; verifications: number }
  mission_autonomy?: MissionMetrics
}

export interface MissionMetrics {
  decisions: number
  handoffs_completed: number
  threats_blocked: number
  automatic_replacements: number
  missions_completed: number
  missions_failed: number
  human_interventions: number
}

export interface Mission {
  id: string
  status: 'RUNNING' | 'COMPLETED' | 'FAILED'
  budget: number
  spent: number
  scenario: 'injection' | 'clean'
  error?: string
  result?: { threat_count: number; indicators: string[]; source_ids: string[] }
  metrics: MissionMetrics
  events: AuditEvent[]
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
  summary?: string
  why?: string
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

export interface TraceNode {
  id: string
  type: 'principal' | 'agent' | 'quote' | 'escrow' | 'judge' | 'event'
  type_label: string
  label: string
  color: string
  data: Record<string, any>
}

export interface TraceEdge {
  id: string
  src: string
  dst: string
  type: string
  label: string
  data: Record<string, any>
}

export interface TraceGraph {
  nodes: TraceNode[]
  edges: TraceEdge[]
}

export interface TraceFacts {
  found: boolean
  node: TraceNode
  neighbors: TraceNode[]
  edges: TraceEdge[]
  escrows?: Array<{ id: string; state: string; verdict: string | null; price: number; scope: string }>
  balance?: number
  events?: AuditEvent[]
  votes?: JudgeVote[]
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
  missions: () => get<{ missions: Mission[]; demo_enabled: boolean }>('/missions'),
  mission: (id: string) => get<Mission>(`/missions/${encodeURIComponent(id)}`),
  runMission: async (body: { idempotency_key: string; budget: number; scenario: string }) => {
    const response = await fetch('/missions/run', { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
    if (!response.ok) throw new Error((await response.json()).detail ?? 'Falha ao executar missão')
    return response.json() as Promise<Mission>
  },
  metrics: () => get<Metrics>('/metrics'),
  escrows: () => get<{ escrows: EscrowRow[] }>('/escrows'),
  audit: () => get<{ events: AuditEvent[] }>('/audit'),
  agents: () => get<{ agents: Agent[] }>('/agents'),
  escrow: (id: string) => get<EscrowDetail>(`/escrow/${id}`),
  traceGraph: () => get<TraceGraph>('/trace/graph'),
  trace: (id: string) => get<TraceFacts>(`/trace/${encodeURIComponent(id)}`),
  health: () => get<{ status: string; service: string }>('/health'),
}
