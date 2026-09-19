import { BadgeCheck } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { Agent } from '@/lib/api'
import { shortDid } from '@/lib/format'
import { cn } from '@/lib/utils'

export function AgentsPanel({ agents }: { agents: Agent[] }) {
  return (
    <Card className="gap-3">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm font-semibold uppercase tracking-widest">
          <BadgeCheck className="size-3.5" /> Agentes registrados
        </CardTitle>
        <CardDescription>
          Reputação só se move em escrow liquidado — review não verificada não pontua.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-56 pr-3">
          <div className="space-y-2">
            {agents.map((a) => (
              <div key={a.did} className="rounded-lg border p-3">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[11px]">{shortDid(a.did, 22)}</span>
                  <span
                    className={cn(
                      'ml-auto font-mono text-sm tabular-nums',
                      a.reputation > 0 && 'text-emerald-400',
                      a.reputation < 0 && 'text-rose-400',
                    )}
                  >
                    {a.reputation > 0 ? '+' : ''}
                    {a.reputation}
                  </span>
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {a.capabilities.map((c) => (
                    <Badge key={c} variant="secondary" className="font-mono text-[10px]">
                      {c}
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
            {agents.length === 0 && (
              <p className="text-sm text-muted-foreground">Nenhum agente registrado.</p>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
