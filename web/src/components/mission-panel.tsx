import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, CheckCircle2, Play, ShieldCheck, ShieldX } from 'lucide-react'
import { useRef, useState } from 'react'

import { api } from '@/lib/api'

const steps = ['Coleta de sinais', 'Triagem de ameaças', 'Relatório de inteligência']

export function MissionPanel() {
  const cache = useQueryClient()
  const [selected, setSelected] = useState<string | null>(null)
  const [scenario, setScenario] = useState('injection')
  const pending = useRef<{ idempotency_key: string; budget: number; scenario: string } | null>(null)
  const list = useQuery({ queryKey: ['missions'], queryFn: api.missions, refetchInterval: 1500 })
  const id = selected ?? list.data?.missions[0]?.id
  const mission = useQuery({ queryKey: ['mission', id], queryFn: () => api.mission(id!),
    enabled: Boolean(id), refetchInterval: 1500 })
  const run = useMutation({ mutationFn: api.runMission, onSuccess: (result) => {
    setSelected(result.id)
    if (result.status !== 'RUNNING') pending.current = null
    cache.setQueryData(['mission', result.id], result)
    void cache.invalidateQueries()
  } })
  const execute = () => {
    pending.current ??= { idempotency_key: crypto.randomUUID(), budget: 30, scenario }
    run.mutate(pending.current)
  }
  const data = mission.data
  const m = data?.metrics
  const receipts = data?.events.filter(e => e.action === 'mission.handoff.completed') ?? []
  const decisions = data?.events.filter(e => e.action === 'mission.decision') ?? []

  return <section className="space-y-5" aria-label="Missão autônoma">
    <div className="rounded-xl border border-indigo-400/30 bg-gradient-to-br from-indigo-500/10 to-transparent p-6 sm:p-8">
      <div className="mb-4 flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-indigo-300">
        <ShieldCheck className="size-4" /> Threat intelligence para agentes
      </div>
      <h2 className="max-w-3xl text-3xl font-medium tracking-tight sm:text-4xl">
        A ameaça é bloqueada.<br />A missão continua.
      </h2>
      <p className="mt-4 max-w-2xl text-sm leading-relaxed text-muted-foreground">
        O coordenador contrata especialistas, verifica cada entrega e substitui um fornecedor
        com AgentCard malicioso. Você define a missão; o fluxo executa as decisões seguintes.
      </p>
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <select aria-label="Cenário da missão" value={scenario} disabled={run.isPending || run.isError}
          onChange={e => setScenario(e.target.value)} className="rounded-lg border bg-background px-3 py-2 text-sm">
          <option value="injection">Ataque durante a triagem</option>
          <option value="clean">Fornecedores sem injection</option>
        </select>
        <button onClick={execute} disabled={run.isPending || !list.data?.demo_enabled}
          className="flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground disabled:opacity-50">
          <Play className="size-4" />{run.isPending ? 'Executando missão…' : run.isError ? 'Retomar solicitação' : 'Executar missão'}
        </button>
        <span className="text-xs text-muted-foreground">Orçamento: 30 créditos de sandbox</span>
      </div>
      <p className="mt-4 text-xs leading-relaxed text-muted-foreground">
        Demo local determinística · dados sintéticos · sem pagamentos reais ou chamadas a LLM.
        Handoffs entre executores no mesmo processo; transporte A2A remoto ainda não implementado.
      </p>
      {list.data && !list.data.demo_enabled && <p className="mt-3 text-sm text-amber-300">Execução da demo desativada neste servidor.</p>}
      {(run.isError || list.isError || mission.isError) && <p role="alert" className="mt-3 text-sm text-rose-300">
        {run.error?.message ?? 'Não foi possível atualizar a missão. Verifique a conexão.'}
      </p>}
    </div>
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-live="polite">
      {[[m?.decisions, 'Decisões da missão'], [m?.handoffs_completed, 'Handoffs concluídos'],
        [m?.automatic_replacements, 'Substituições automáticas'], [m?.human_interventions, 'Intervenções após início']].map(([n, label]) =>
        <div key={String(label)} className="rounded-xl border bg-card p-5">
          <div className="font-mono text-4xl font-semibold text-emerald-300">{n ?? '—'}</div>
          <div className="mt-2 text-xs text-muted-foreground">{label}</div>
        </div>)}
    </div>
    {data ? <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm">
          {data.status === 'COMPLETED' ? <CheckCircle2 className="size-5 text-emerald-400" /> : <ShieldX className="size-5 text-amber-400" />}
          {data.status === 'COMPLETED' ? 'Missão concluída' : data.status === 'FAILED' ? 'Missão interrompida' : 'Missão em execução'}
          <span className="text-muted-foreground">· {data.spent} / {data.budget} créditos comprometidos</span>
        </div>
        <select aria-label="Histórico de missões" value={data.id} onChange={e => setSelected(e.target.value)}
          className="max-w-full rounded border bg-background px-3 py-2 font-mono text-xs">
          {list.data?.missions.map(item => <option key={item.id} value={item.id}>{item.id} · {item.status}</option>)}
        </select>
      </div>
      {data.error && <p role="alert" className="rounded-lg border border-rose-500/40 p-4 text-sm text-rose-300">{data.error}</p>}
      <div className="grid gap-3 md:grid-cols-3">
        {steps.map((label, i) => <div key={label} className="rounded-xl border bg-card p-5">
          <div className="flex items-center justify-between text-xs text-muted-foreground"><span>0{i + 1}</span><ArrowRight className="size-4" /></div>
          <h3 className="mt-4 font-medium">{label}</h3>
          <p className="mt-2 text-xs text-muted-foreground">{receipts[i] ? 'Entrega verificada e liquidada' : 'Aguardando entrega verificada'}</p>
          {receipts[i] && <p className="mt-3 break-all font-mono text-[10px] text-emerald-300" title={String(receipts[i].payload?.artifact_hash)}>
            SHA-256 {String(receipts[i].payload?.artifact_hash).slice(0, 24)}…</p>}
        </div>)}
      </div>
      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <div className="rounded-xl border bg-card p-5">
          <h3 className="font-medium">Decisões e evidências</h3>
          <ol className="mt-4 space-y-3">
            {decisions.map(event => <li key={event.seq} className="border-l-2 border-indigo-400/30 pl-3 text-xs leading-relaxed">
              <span className={event.payload?.choice === 'block' ? 'text-rose-300' : 'text-indigo-300'}>
                #{event.seq} · {String(event.payload?.step)} · {String(event.payload?.choice)}</span>
              <p className="mt-1 text-muted-foreground">{String(event.payload?.reason)}</p>
            </li>)}
          </ol>
        </div>
        <div className="rounded-xl border bg-card p-5">
          <h3 className="font-medium">Resultado da missão</h3>
          {data.result ? <>
            <p className="mt-4 text-sm">{data.result.threat_count} indicadores sinalizados no conjunto sintético.</p>
            <ul className="mt-4 space-y-2 break-all font-mono text-xs text-muted-foreground">
              {data.result.indicators.map((indicator, i) => <li key={indicator}>{indicator}<br />Fonte: {data.result?.source_ids[i]}</li>)}
            </ul>
          </> : <p className="mt-4 text-sm text-muted-foreground">O resultado aparece após todas as entregas serem verificadas.</p>}
          <p className="mt-6 text-xs leading-relaxed text-muted-foreground">Contagem derivada da trilha: uma decisão explícita por escolha; um handoff somente após entrega verificada. Eventos técnicos e cliques de início não são decisões autônomas.</p>
          <a href={`/missions/${data.id}`} target="_blank" rel="noreferrer" className="mt-4 inline-block text-sm text-indigo-300 underline">Abrir evidências em JSON</a>
        </div>
      </div>
    </> : <p className="py-8 text-center text-sm text-muted-foreground">Execute uma missão para observar decisões, contratos e evidências.</p>}
  </section>
}
