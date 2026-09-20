import { Badge } from '@/components/ui/badge'
import type { EscrowState } from '@/lib/api'
import { cn } from '@/lib/utils'

/** Cor conta a história do caso: verde liquidou, vermelho travou, azul em curso. */
const TONE: Record<EscrowState, string> = {
  QUOTED: 'bg-sky-500/10 text-sky-300 border-sky-500/30',
  FUNDED: 'bg-sky-500/10 text-sky-300 border-sky-500/30',
  DELIVERED: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30',
  VERIFIED: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
  RELEASED: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40',
  REJECTED: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
  DISPUTED: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
  ARBITRATED: 'bg-violet-500/10 text-violet-300 border-violet-500/30',
  RESOLVED: 'bg-teal-500/15 text-teal-300 border-teal-500/40',
}

export function StateBadge({ state, className }: { state: EscrowState; className?: string }) {
  return (
    <Badge
      variant="outline"
      className={cn('font-mono text-[10px] tracking-widest', TONE[state], className)}
    >
      {state}
    </Badge>
  )
}
