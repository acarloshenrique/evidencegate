import { Link2, ShieldAlert } from 'lucide-react'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { AuditEvent, ChainStatus } from '@/lib/api'
import { clock, shortDid, shortHash } from '@/lib/format'
import { cn } from '@/lib/utils'

/** Ações que mexem em dinheiro ou veredito merecem destaque na leitura rápida. */
const ACCENT: Record<string, string> = {
  'escrow.released': 'text-emerald-400',
  'escrow.resolved': 'text-emerald-400',
  'escrow.rejected': 'text-rose-400',
  'escrow.disputed': 'text-amber-400',
  'policy.denied': 'text-rose-400',
  'verify.panel': 'text-sky-400',
  'agent.reputation': 'text-violet-400',
  'card.injection_flagged': 'text-rose-400',
}

export function AuditTrailPanel({
  events,
  chain,
  onSelectEscrow,
  className,
}: {
  events: AuditEvent[]
  chain?: ChainStatus
  onSelectEscrow?: (id: string) => void
  className?: string
}) {
  const tamperedSeq = chain && !chain.ok ? chain.tampered_seq : null
  const recent = [...events].reverse()

  return (
    <Card className={cn('gap-3', className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm font-semibold uppercase tracking-widest">
          <Link2 className="size-3.5" /> Trilha hash-encadeada
        </CardTitle>
        <CardDescription>
          Cada evento sela o anterior. O verificador re-deriva a cadeia — não confia no log.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[28rem] pr-3">
          <ol className="relative space-y-3 border-l border-border pl-4">
            {recent.map((e) => {
              const escrowId = String(
                (e.payload?.escrow_id as string | undefined) ?? '',
              )
              const tampered = tamperedSeq !== null && e.seq >= tamperedSeq
              return (
                <li key={e.event_hash} className="relative">
                  <span
                    className={cn(
                      'absolute -left-[21px] top-1.5 size-2 rounded-full ring-2 ring-background',
                      tampered ? 'bg-rose-500' : 'bg-muted-foreground/60',
                    )}
                  />
                  <div className="flex items-baseline gap-2">
                    <span className="font-mono text-[11px] text-muted-foreground">#{e.seq}</span>
                    <button
                      type="button"
                      disabled={!escrowId || !onSelectEscrow}
                      onClick={() => escrowId && onSelectEscrow?.(escrowId)}
                      className={cn(
                        'font-mono text-xs font-medium',
                        ACCENT[e.action] ?? 'text-foreground',
                        escrowId && onSelectEscrow && 'hover:underline',
                      )}
                    >
                      {e.action}
                    </button>
                    {tampered && (
                      <span className="flex items-center gap-1 text-[10px] font-semibold text-rose-400">
                        <ShieldAlert className="size-3" /> ADULTERADO
                      </span>
                    )}
                    <span className="ml-auto text-[10px] text-muted-foreground">{clock(e.ts)}</span>
                  </div>
                  <div className="font-mono text-[10px] text-muted-foreground">
                    {shortDid(e.actor_did, 22)}
                  </div>
                  <div className="font-mono text-[10px] text-muted-foreground/70">
                    {shortHash(e.prev_hash, 8)} → {shortHash(e.event_hash, 8)}
                  </div>
                </li>
              )
            })}
            {recent.length === 0 && (
              <li className="text-sm text-muted-foreground">Trilha vazia.</li>
            )}
          </ol>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
