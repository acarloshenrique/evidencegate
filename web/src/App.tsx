import { useQuery } from '@tanstack/react-query'
import {
  Bot,
  Coins,
  Landmark,
  LayoutDashboard,
  Network,
  Radio,
  ScrollText,
  ShieldCheck,
  ShieldX,
} from 'lucide-react'
import { useState } from 'react'

import { AgentsPanel } from '@/components/agents-panel'
import { AuditTrailPanel } from '@/components/audit-trail'
import { CostPanel } from '@/components/cost-panel'
import { EscrowDetailSheet } from '@/components/escrow-detail'
import { EscrowTable } from '@/components/escrow-table'
import { MissionPanel } from '@/components/mission-panel'
import { StatCards } from '@/components/stat-cards'
import { TracePanel } from '@/components/trace-panel'
import { Badge } from '@/components/ui/badge'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

const POLL_MS = 1500

type View = 'missions' | 'overview' | 'escrows' | 'trace' | 'audit' | 'agents' | 'costs'

const NAV: { id: View; label: string; icon: typeof LayoutDashboard }[] = [
  { id: 'missions', label: 'Missão autônoma', icon: ShieldCheck },
  { id: 'overview', label: 'Visão geral', icon: LayoutDashboard },
  { id: 'escrows', label: 'Escrows', icon: Landmark },
  { id: 'trace', label: 'Rastreio', icon: Network },
  { id: 'audit', label: 'Auditoria', icon: ScrollText },
  { id: 'agents', label: 'Agentes', icon: Bot },
  { id: 'costs', label: 'Custos', icon: Coins },
]

const VIEW_TITLE: Record<View, string> = {
  missions: 'Missão autônoma · inteligência de ameaças',
  overview: 'Visão geral',
  escrows: 'Escrows',
  trace: 'Rastreio de proveniência',
  audit: 'Trilha de auditoria',
  agents: 'Registry de agentes',
  costs: 'Custos de inferência',
}

export default function App() {
  const [view, setView] = useState<View>('missions')
  const [selected, setSelected] = useState<string | null>(null)

  const metrics = useQuery({ queryKey: ['metrics'], queryFn: api.metrics, refetchInterval: POLL_MS })
  const escrows = useQuery({ queryKey: ['escrows'], queryFn: api.escrows, refetchInterval: POLL_MS })
  const audit = useQuery({ queryKey: ['audit'], queryFn: api.audit, refetchInterval: POLL_MS })
  const agents = useQuery({ queryKey: ['agents'], queryFn: api.agents, refetchInterval: 5000 })

  const offline = metrics.isError && escrows.isError
  const chain = metrics.data?.chain
  const escList = escrows.data?.escrows ?? []

  const selectEscrow = (id: string) => {
    setSelected(id)
  }

  const chainBadge = chain && (
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
  )

  const liveBadge = (
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
  )

  return (
    <div className="min-h-screen bg-background">
      {/* ---- sidebar (desktop) ---- */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r bg-sidebar lg:flex">
        <div className="flex items-center gap-2.5 px-5 pt-5 pb-4">
          <ShieldCheck className="size-5 text-primary" strokeWidth={1.6} />
          <div>
            <div className="text-sm font-medium tracking-tight">EvidenceGate</div>
            <div className="text-[11px] font-light text-muted-foreground">
              inteligência de ameaças
            </div>
          </div>
        </div>
        <nav className="flex-1 space-y-0.5 px-3 pt-2">
          {NAV.map((item) => (
            <button
              key={item.id}
              onClick={() => setView(item.id)}
              className={cn(
                'flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-light transition-colors',
                view === item.id
                  ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                  : 'text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground',
              )}
            >
              <item.icon className="size-4" strokeWidth={1.6} />
              {item.label}
            </button>
          ))}
        </nav>
        <div className="space-y-2.5 border-t px-5 py-4">
          <div className="flex flex-wrap gap-1.5">
            {chainBadge}
            {liveBadge}
          </div>
          <div className="flex gap-3 text-[11px] text-muted-foreground">
            <a href="/" className="hover:text-foreground">Home</a>
            <a href="/design" className="hover:text-foreground">Design</a>
            <a href="/voice" className="hover:text-foreground">Voz</a>
            <a href="/docs" className="hover:text-foreground">API</a>
          </div>
        </div>
      </aside>

      {/* ---- main column ---- */}
      <div className="flex min-h-screen flex-col lg:pl-60">
        <header className="sticky top-0 z-20 border-b bg-background/80 backdrop-blur">
          <div className="flex flex-wrap items-center gap-3 px-5 py-3">
            <div className="flex items-center gap-2.5 lg:hidden">
              <ShieldCheck className="size-4 text-primary" strokeWidth={1.6} />
              <span className="text-sm font-medium">EvidenceGate</span>
            </div>
            <h1 className="hidden text-sm font-medium tracking-tight lg:block">
              {VIEW_TITLE[view]}
            </h1>
            <div className="ml-auto flex items-center gap-2">
              {chainBadge}
              {liveBadge}
            </div>
          </div>
          {/* mobile nav */}
          <nav className="flex gap-1 overflow-x-auto px-3 pb-2 lg:hidden">
            {NAV.map((item) => (
              <button
                key={item.id}
                onClick={() => setView(item.id)}
                className={cn(
                  'flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-xs',
                  view === item.id
                    ? 'bg-accent text-accent-foreground'
                    : 'text-muted-foreground',
                )}
              >
                <item.icon className="size-3.5" strokeWidth={1.6} />
                {item.label}
              </button>
            ))}
          </nav>
        </header>

        <main className="flex-1 space-y-4 px-5 py-5">
          {view === 'missions' && <MissionPanel />}
          {view === 'overview' && (
            <>
              <StatCards metrics={metrics.data} escrows={escList} />
              <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
                <div className="space-y-4">
                  <EscrowTable escrows={escList} selected={selected} onSelect={selectEscrow} />
                  <CostPanel calls={metrics.data?.calls ?? []} />
                </div>
                <div className="space-y-4">
                  <AuditTrailPanel
                    events={audit.data?.events ?? []}
                    chain={chain}
                    onSelectEscrow={selectEscrow}
                  />
                  <AgentsPanel agents={agents.data?.agents ?? []} />
                </div>
              </div>
            </>
          )}
          {view === 'escrows' && (
            <>
              <StatCards metrics={metrics.data} escrows={escList} />
              <EscrowTable escrows={escList} selected={selected} onSelect={selectEscrow} />
            </>
          )}
          {view === 'audit' && (
            <AuditTrailPanel
              events={audit.data?.events ?? []}
              chain={chain}
              onSelectEscrow={selectEscrow}
            />
          )}
          {view === 'trace' && <TracePanel />}
        {view === 'agents' && <AgentsPanel agents={agents.data?.agents ?? []} />}
          {view === 'costs' && <CostPanel calls={metrics.data?.calls ?? []} />}
        </main>
      </div>

      <EscrowDetailSheet
        escrowId={selected}
        onOpenChange={(open) => !open && setSelected(null)}
      />
    </div>
  )
}
