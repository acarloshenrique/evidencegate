import { useQuery } from '@tanstack/react-query'
import { Radio, ShieldCheck, ShieldX } from 'lucide-react'
import { useState } from 'react'

import { AgentsPanel } from '@/components/agents-panel'
import { AuditTrailPanel } from '@/components/audit-trail'
import { CostPanel } from '@/components/cost-panel'
import { EscrowDetailSheet } from '@/components/escrow-detail'
import { EscrowTable } from '@/components/escrow-table'
import { StatCards } from '@/components/stat-cards'
import { Badge } from '@/components/ui/badge'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

const POLL_MS = 1500

export default function App() {
  const [selected, setSelected] = useState<string | null>(null)

  const metrics = useQuery({ queryKey: ['metrics'], queryFn: api.metrics, refetchInterval: POLL_MS })
  const escrows = useQuery({ queryKey: ['escrows'], queryFn: api.escrows, refetchInterval: POLL_MS })
  const audit = useQuery({ queryKey: ['audit'], queryFn: api.audit, refetchInterval: POLL_MS })
  const agents = useQuery({ queryKey: ['agents'], queryFn: api.agents, refetchInterval: 5000 })

  const offline = metrics.isError && escrows.isError
  const chain = metrics.data?.chain

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-20 border-b bg-background/80 backdrop-blur">
        <div className="mx-auto flex max-w-[110rem] flex-wrap items-center gap-3 px-6 py-3">
          <div>
            <h1 className="text-sm font-semibold tracking-tight">
              EvidenceGate <span className="text-muted-foreground">· auditoria ao vivo</span>
            </h1>
            <p className="text-xs text-muted-foreground">
              Camada de confiança para transações entre agentes — verificação é a condição de
              liquidação.
            </p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            {chain && (
              <Badge
                variant="outline"
                className={cn(
                  'gap-1 font-mono text-[10px]',
                  chain.ok
                    ? 'border-emerald-500/40 text-emerald-300'
                    : 'border-rose-500/40 text-rose-300',
                )}
              >
                {chain.ok ? <ShieldCheck className="size-3" /> : <ShieldX className="size-3" />}
                {chain.ok ? 'CADEIA ÍNTEGRA' : `ADULTERADA @${chain.tampered_seq}`}
              </Badge>
            )}
            <Badge
              variant="outline"
              className={cn(
                'gap-1.5 font-mono text-[10px]',
                offline ? 'border-rose-500/40 text-rose-300' : 'text-muted-foreground',
              )}
            >
              <Radio className={cn('size-3', !offline && 'animate-pulse text-emerald-400')} />
              {offline ? 'BACKEND OFFLINE' : `LIVE · ${POLL_MS / 1000}s`}
            </Badge>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[110rem] space-y-4 px-6 py-5">
        <StatCards metrics={metrics.data} escrows={escrows.data?.escrows ?? []} />

        <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
          <div className="space-y-4">
            <EscrowTable
              escrows={escrows.data?.escrows ?? []}
              selected={selected}
              onSelect={setSelected}
            />
            <CostPanel calls={metrics.data?.calls ?? []} />
          </div>
          <div className="space-y-4">
            <AuditTrailPanel
              events={audit.data?.events ?? []}
              chain={chain}
              onSelectEscrow={setSelected}
            />
            <AgentsPanel agents={agents.data?.agents ?? []} />
          </div>
        </div>
      </main>

      <EscrowDetailSheet
        escrowId={selected}
        onOpenChange={(open) => !open && setSelected(null)}
      />
    </div>
  )
}
