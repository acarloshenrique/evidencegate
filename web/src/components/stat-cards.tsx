import { Activity, CircleDollarSign, Link2, Lock, ShieldCheck, ShieldX } from 'lucide-react'
import type { ReactNode } from 'react'

import { Card, CardContent } from '@/components/ui/card'
import type { EscrowRow, Metrics } from '@/lib/api'
import { money, usd6 } from '@/lib/format'
import { cn } from '@/lib/utils'

function Stat({
  icon,
  label,
  value,
  hint,
  tone,
}: {
  icon: ReactNode
  label: string
  value: string
  hint?: string
  tone?: 'ok' | 'bad' | 'warn'
}) {
  return (
    <Card className="gap-0 py-4">
      <CardContent className="px-4">
        <div className="flex items-center gap-2 text-muted-foreground">
          {icon}
          <span className="text-[11px] font-medium uppercase tracking-widest">{label}</span>
        </div>
        <div
          className={cn(
            'mt-2 font-mono text-2xl font-semibold tabular-nums',
            tone === 'ok' && 'text-emerald-400',
            tone === 'bad' && 'text-rose-400',
            tone === 'warn' && 'text-amber-400',
          )}
        >
          {value}
        </div>
        {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  )
}

export function StatCards({
  metrics,
  escrows,
}: {
  metrics?: Metrics
  escrows: EscrowRow[]
}) {
  const cost = metrics?.inference_cost ?? 0
  const calls = metrics?.inference_calls ?? 0
  const chain = metrics?.chain
  const settled = escrows.filter((e) => e.state === 'RELEASED' || e.state === 'RESOLVED')
  const locked = escrows
    .filter((e) => !['RELEASED', 'RESOLVED'].includes(e.state))
    .reduce((sum, e) => sum + e.price, 0)
  // Custo por decisão liquidada: o número que decide se isso roda em produção.
  const perDecision = settled.length ? cost / settled.length : 0
  const autonomy = metrics?.autonomy
  const stageA = metrics?.stage_a
  const freePct = stageA?.verifications
    ? Math.round((stageA.resolved_free / stageA.verifications) * 100)
    : 0

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
      <Card className="gap-0 py-5 sm:col-span-2 xl:col-span-5">
        <CardContent className="flex flex-wrap items-baseline gap-x-10 gap-y-3 px-5">
          <div>
            <span className="font-mono text-5xl font-semibold tabular-nums text-emerald-400">
              {autonomy?.decisions ?? '…'}
            </span>
            <span className="ml-3 text-sm text-muted-foreground">decisões autônomas</span>
          </div>
          <div>
            <span className="font-mono text-5xl font-semibold tabular-nums">
              {autonomy?.human_interventions ?? '…'}
            </span>
            <span className="ml-3 text-sm text-muted-foreground">intervenções humanas</span>
          </div>
          <div>
            <span className="font-mono text-5xl font-semibold tabular-nums text-amber-400">
              {stageA ? `${freePct}%` : '…'}
            </span>
            <span className="ml-3 text-sm text-muted-foreground">
              das verificações resolvidas sem gastar token
              {stageA ? ` (${stageA.resolved_free} de ${stageA.verifications})` : ''}
            </span>
          </div>
        </CardContent>
      </Card>
      <Stat
        icon={chain?.ok === false ? <ShieldX className="size-3.5" /> : <ShieldCheck className="size-3.5" />}
        label="Trilha"
        value={chain === undefined ? '…' : chain.ok ? 'ÍNTEGRA' : `@seq ${chain.tampered_seq}`}
        hint={
          chain === undefined
            ? 'verificando cadeia'
            : chain.ok
              ? `${chain.length} eventos re-derivados`
              : 'hash não bate — cadeia adulterada'
        }
        tone={chain === undefined ? undefined : chain.ok ? 'ok' : 'bad'}
      />
      <Stat
        icon={<CircleDollarSign className="size-3.5" />}
        label="Custo de inferência"
        value={usd6(cost)}
        hint={`${calls} chamadas aos juízes`}
        tone="warn"
      />
      <Stat
        icon={<Activity className="size-3.5" />}
        label="Custo por decisão"
        value={usd6(perDecision)}
        hint={`${settled.length} casos liquidados`}
      />
      <Stat
        icon={<Lock className="size-3.5" />}
        label="Valor travado"
        value={money(locked)}
        hint={`${escrows.length} escrows no total`}
      />
      <Stat
        icon={<Link2 className="size-3.5" />}
        label="Escrows abertos"
        value={String(escrows.length - settled.length)}
        hint="aguardando entrega ou veredito"
      />
    </div>
  )
}
