import cytoscape from 'cytoscape'
import { Network, ShieldCheck } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import type { TraceFacts, TraceGraph, TraceNode } from '@/lib/api'

const EDGE_COLORS: Record<string, string> = {
  KYC_BACKS: '#fbbf24',
  QUOTED_BUY: '#38bdf8',
  SIGNED_QUOTE: '#38bdf8',
  FUNDED: '#38bdf8',
  JUDGED_BY: '#8b98b8',
  MONEY: '#34d399',
  LOGGED: 'rgba(139,152,184,.35)',
}

function voteColor(vote?: string) {
  return vote === 'approve' ? '#34d399' : vote === 'reject' ? '#f87171' : '#8b98b8'
}

export function TracePanel() {
  const ref = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)
  const [graph, setGraph] = useState<TraceGraph | null>(null)
  const [facts, setFacts] = useState<TraceFacts | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.traceGraph()
      .then(setGraph)
      .catch((e) => setError(String(e)))
  }, [])

  useEffect(() => {
    if (!graph || !ref.current) return
    const cy = cytoscape({
      container: ref.current,
      elements: [
        ...graph.nodes.map((n: TraceNode) => ({
          data: { id: n.id, label: n.label, type: n.type },
          style: {
            'background-color': n.color,
            label: 'data(label)',
            'font-size': 8,
            color: '#8b98b8',
            'text-valign': 'bottom',
            'text-margin-y': 4,
            width: n.type === 'escrow' ? 22 : n.type === 'agent' ? 18 : 13,
            height: n.type === 'escrow' ? 22 : n.type === 'agent' ? 18 : 13,
            'border-width': 1.5,
            'border-color': 'rgba(255,255,255,.25)',
          },
        })),
        ...graph.edges.map((e) => ({
          data: { id: e.id, source: e.src, target: e.dst, label: e.label },
          style: {
            width: e.type === 'LOGGED' ? 0.8 : 1.5,
            'line-color':
              e.type === 'VOTE'
                ? voteColor(e.data?.vote as string | undefined)
                : (EDGE_COLORS[e.type] ?? '#8b98b8'),
            'target-arrow-shape': 'triangle',
            'target-arrow-color':
              e.type === 'VOTE'
                ? voteColor(e.data?.vote as string | undefined)
                : (EDGE_COLORS[e.type] ?? '#8b98b8'),
            'arrow-scale': 0.7,
            'curve-style': 'bezier',
            opacity: e.type === 'LOGGED' ? 0.35 : 0.85,
          },
        })),
      ],
      layout: { name: 'cose', animate: false, nodeRepulsion: 9000, idealEdgeLength: 90 },
      wheelSensitivity: 0.3,
    })
    cy.on('tap', 'node', (evt) => {
      const id = evt.target.id()
      api.trace(id).then(setFacts).catch(() => setFacts(null))
    })
    cyRef.current = cy
    ;(window as unknown as { __cy?: cytoscape.Core }).__cy = cy
    return () => cy.destroy()
  }, [graph])

  const types = graph
    ? [...new Map(graph.nodes.map((n) => [n.type, n])).values()]
    : []

  return (
    <Card className="gap-3">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm font-semibold uppercase tracking-widest">
          <Network className="size-3.5" /> Rastreio — proveniência
        </CardTitle>
        <CardDescription>
          KYC → KYA → quote → escrow → votos → dinheiro → eventos. Clique num
          nó para ver a ficha da entidade.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {error && <div className="text-xs text-rose-300">{error}</div>}
        <div
          ref={ref}
          className="h-[440px] w-full rounded-lg border bg-[#0a0e1e]"
        />
        <div className="flex flex-wrap gap-2">
          {types.map((t) => (
            <Badge key={t.type} variant="outline" className="gap-1.5 text-[10px]">
              <span
                className="inline-block size-2 rounded-full"
                style={{ background: t.color }}
              />
              {t.type_label}
            </Badge>
          ))}
        </div>

        {facts && (
          <div className="rounded-lg border bg-accent/40 p-3 text-xs">
            <div className="mb-2 flex items-center gap-2">
              <Badge variant="outline" className="text-[10px]">
                {facts.node.type_label}
              </Badge>
              <span className="font-medium">{facts.node.label}</span>
              <span className="text-muted-foreground">{facts.node.id.slice(0, 26)}…</span>
            </div>
            <div className="grid gap-1.5 text-muted-foreground sm:grid-cols-2">
              {facts.node.type === 'agent' && (
                <>
                  <div>reputação: <span className="tnum text-foreground">{facts.node.data.reputation?.toFixed?.(1) ?? '—'}</span></div>
                  <div>saldo: <span className="tnum text-foreground">${facts.balance?.toFixed?.(2) ?? '0.00'}</span></div>
                  <div>escrows ligados: <span className="text-foreground">{facts.escrows?.length ?? 0}</span></div>
                  <div>capacidades: {(facts.node.data.capabilities ?? []).join(', ') || '—'}</div>
                </>
              )}
              {facts.node.type === 'escrow' && (
                <>
                  <div>estado: <span className="text-foreground">{facts.node.data.state}</span></div>
                  <div>veredicto: <span className="text-foreground">{facts.node.data.verdict ?? '—'}</span></div>
                  <div>votos: {(facts.votes ?? []).map((v) => `${v.judge}:${v.vote}`).join(' · ') || '—'}</div>
                  <div>eventos: <span className="text-foreground">{facts.events?.length ?? 0}</span></div>
                </>
              )}
              {facts.node.type === 'principal' && (
                <>
                  <div>doc hash: <span className="tnum text-foreground">{facts.node.data.doc_hash}</span></div>
                  <div>ligações: <span className="text-foreground">{facts.edges.length}</span></div>
                </>
              )}
              {facts.node.type === 'quote' && (
                <>
                  <div>escopo: <span className="text-foreground">{facts.node.data.scope}</span></div>
                  <div>preço: <span className="tnum text-foreground">${facts.node.data.price}</span></div>
                  <div>hash: <span className="tnum text-foreground">{facts.node.data.quote_hash}</span></div>
                </>
              )}
              {facts.node.type === 'judge' && (
                <div>capacidade: <span className="text-foreground">{facts.node.data.capability}</span></div>
              )}
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {facts.edges.slice(0, 12).map((e) => (
                <Badge key={e.id} variant="outline" className="text-[10px] text-muted-foreground">
                  {e.src === facts.node.id ? '→' : '←'} {e.label}
                </Badge>
              ))}
            </div>
            {facts.node.type === 'agent' && facts.node.data.status === 'active' && (
              <div className="mt-2 flex items-center gap-1.5 text-emerald-300">
                <ShieldCheck className="size-3" /> vínculo KYC ativo — accountability cadeia completa
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
