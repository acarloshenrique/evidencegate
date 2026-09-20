import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { StateBadge } from '@/components/state-badge'
import type { EscrowRow } from '@/lib/api'
import { ago, money, shortDid } from '@/lib/format'
import { cn } from '@/lib/utils'

export function EscrowTable({
  escrows,
  selected,
  onSelect,
}: {
  escrows: EscrowRow[]
  selected: string | null
  onSelect: (id: string) => void
}) {
  return (
    <Card className="gap-3">
      <CardHeader>
        <CardTitle className="text-sm font-semibold uppercase tracking-widest">Escrows</CardTitle>
        <CardDescription>
          Verificação é a condição de liquidação — clique num caso para abrir a prova.
        </CardDescription>
      </CardHeader>
      <CardContent className="px-0">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="pl-6">Estado</TableHead>
              <TableHead>Escrow</TableHead>
              <TableHead>Escopo</TableHead>
              <TableHead>Seller</TableHead>
              <TableHead className="text-right">Valor</TableHead>
              <TableHead className="pr-6 text-right">Criado</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {escrows.map((e) => (
              <TableRow
                key={e.id}
                onClick={() => onSelect(e.id)}
                className={cn(
                  'cursor-pointer',
                  selected === e.id && 'bg-accent/60 hover:bg-accent/60',
                )}
              >
                <TableCell className="pl-6">
                  <StateBadge state={e.state} />
                </TableCell>
                <TableCell className="font-mono text-xs">{e.id}</TableCell>
                <TableCell className="max-w-[24rem] truncate text-sm">{e.scope}</TableCell>
                <TableCell className="font-mono text-[11px] text-muted-foreground">
                  {shortDid(e.seller_did, 14)}
                </TableCell>
                <TableCell className="text-right font-mono tabular-nums">
                  {money(e.price)}
                </TableCell>
                <TableCell className="pr-6 text-right text-xs text-muted-foreground">
                  {ago(e.created_at)}
                </TableCell>
              </TableRow>
            ))}
            {escrows.length === 0 && (
              <TableRow className="hover:bg-transparent">
                <TableCell colSpan={6} className="py-10 text-center text-sm text-muted-foreground">
                  Nenhum escrow ainda. Rode <code className="font-mono">scripts/demo.py</code>.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
