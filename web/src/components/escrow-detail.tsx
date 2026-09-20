import { useQuery } from '@tanstack/react-query'
import { Check, Gavel, X } from 'lucide-react'

import { StateBadge } from '@/components/state-badge'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import { api, type JudgeVote } from '@/lib/api'
import { clock, datetime, money, shortDid, shortHash } from '@/lib/format'
import { cn } from '@/lib/utils'

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <div className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
        {label}
      </div>
      <div className="text-sm">{children}</div>
    </div>
  )
}

function Json({ value }: { value: unknown }) {
  return (
    <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all rounded-md border bg-muted/40 p-3 font-mono text-[11px] leading-relaxed">
      {JSON.stringify(value, null, 2)}
    </pre>
  )
}

function VoteCard({ vote }: { vote: JudgeVote }) {
  const approved = vote.vote === 'approve'
  const confidence = vote.confidence ?? 0
  return (
    <div className="rounded-lg border p-3">
      <div className="flex items-center gap-2">
        <Badge variant="outline" className="font-mono text-[10px]">
          {vote.judge}
        </Badge>
        <span
          className={cn(
            'flex items-center gap-1 text-xs font-semibold',
            approved ? 'text-emerald-400' : 'text-rose-400',
          )}
        >
          {approved ? <Check className="size-3" /> : <X className="size-3" />}
          {vote.vote ?? 'selado'}
        </span>
        <span className="ml-auto font-mono text-xs tabular-nums text-muted-foreground">
          {(confidence * 100).toFixed(0)}%
        </span>
      </div>
      <Progress value={confidence * 100} className="mt-2 h-1" />
      {vote.rationale && (
        <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{vote.rationale}</p>
      )}
      <div className="mt-2 font-mono text-[10px] text-muted-foreground/70">
        commit {shortHash(vote.commit_hash, 16)}
      </div>
    </div>
  )
}

export function EscrowDetailSheet({
  escrowId,
  onOpenChange,
}: {
  escrowId: string | null
  onOpenChange: (open: boolean) => void
}) {
  const { data, isLoading } = useQuery({
    queryKey: ['escrow', escrowId],
    queryFn: () => api.escrow(escrowId as string),
    enabled: !!escrowId,
    refetchInterval: 2000,
  })

  return (
    <Sheet open={!!escrowId} onOpenChange={onOpenChange}>
      <SheetContent className="w-full gap-0 sm:max-w-xl">
        {isLoading || !data ? (
          <div className="space-y-3 p-6">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
        ) : (
          <>
            <SheetHeader>
              <SheetTitle className="flex items-center gap-2 font-mono text-base">
                {data.escrow.id}
                <StateBadge state={data.escrow.state} />
              </SheetTitle>
              <SheetDescription>{data.quote?.scope}</SheetDescription>
            </SheetHeader>
            <ScrollArea className="h-full">
              <div className="space-y-5 px-4 pb-10">
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Valor">
                    <span className="font-mono tabular-nums">
                      {money(data.quote?.price ?? 0)}
                    </span>
                  </Field>
                  <Field label="Painel">
                    {data.votes.length
                      ? `${data.votes.filter((v) => v.vote === 'approve').length}/${data.votes.length} approve`
                      : 'sem painel (stage A)'}
                  </Field>
                  <Field label="Buyer">
                    <span className="font-mono text-[11px]">
                      {shortDid(data.quote?.buyer_did ?? '—', 20)}
                    </span>
                  </Field>
                  <Field label="Seller">
                    <span className="font-mono text-[11px]">
                      {shortDid(data.quote?.seller_did ?? '—', 20)}
                    </span>
                  </Field>
                  <Field label="Criado">{datetime(data.escrow.created_at)}</Field>
                  <Field label="Atualizado">{datetime(data.escrow.updated_at)}</Field>
                </div>

                <Separator />

                <div className="space-y-2">
                  <div className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                    Rubrica travada no quote
                  </div>
                  <div className="font-mono text-[10px] text-muted-foreground">
                    quote_hash {shortHash(data.quote?.quote_hash, 24)} · assinada pelo seller antes
                    do trabalho
                  </div>
                  <Json value={data.quote?.criteria ?? {}} />
                </div>

                {data.escrow.evidence && (
                  <div className="space-y-2">
                    <div className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                      Evidência entregue
                    </div>
                    <div className="font-mono text-[10px] text-muted-foreground">
                      evidence_hash {shortHash(data.escrow.evidence_hash, 24)}
                    </div>
                    <Json value={data.escrow.evidence} />
                  </div>
                )}

                {data.votes.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                      <Gavel className="size-3" /> Painel de juízes · commit-reveal 2-de-3
                    </div>
                    <div className="space-y-2">
                      {data.votes.map((v) => (
                        <VoteCard key={v.judge} vote={v} />
                      ))}
                    </div>
                  </div>
                )}

                {data.escrow.dispute && (
                  <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-sm">
                    <div className="text-[10px] font-medium uppercase tracking-widest text-amber-400">
                      Disputa
                    </div>
                    <p className="mt-1 text-muted-foreground">{data.escrow.dispute}</p>
                  </div>
                )}

                <div className="space-y-2">
                  <div className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                    Razão (ledger)
                  </div>
                  <div className="divide-y rounded-lg border">
                    {data.ledger.map((l, i) => (
                      <div key={i} className="flex items-center gap-3 px-3 py-2 text-xs">
                        <span className="font-mono text-[11px] text-muted-foreground">
                          {shortDid(l.account, 18)}
                        </span>
                        <span className="text-muted-foreground">{l.reason}</span>
                        <span
                          className={cn(
                            'ml-auto font-mono tabular-nums',
                            l.delta >= 0 ? 'text-emerald-400' : 'text-rose-400',
                          )}
                        >
                          {l.delta >= 0 ? '+' : '−'}
                          {money(Math.abs(l.delta))}
                        </span>
                      </div>
                    ))}
                    {data.ledger.length === 0 && (
                      <div className="px-3 py-2 text-xs text-muted-foreground">
                        Nenhum lançamento.
                      </div>
                    )}
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                    Eventos deste caso
                  </div>
                  <div className="space-y-1">
                    {data.events.map((e) => (
                      <div key={e.event_hash} className="flex items-baseline gap-2 text-xs">
                        <span className="font-mono text-[11px] text-muted-foreground">
                          #{e.seq}
                        </span>
                        <span className="font-mono">{e.action}</span>
                        <span className="ml-auto text-[10px] text-muted-foreground">
                          {clock(e.ts)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </ScrollArea>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
