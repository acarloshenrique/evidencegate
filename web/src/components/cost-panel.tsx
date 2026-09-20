import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from 'recharts'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart'
import type { InferenceCall } from '@/lib/api'
import { usd6 } from '@/lib/format'

/** Série única (custo em USD) — um só matiz, sem legenda, sem segundo eixo. */
const config = {
  cost: { label: 'Custo (USD)', color: 'var(--color-amber-400)' },
} satisfies ChartConfig

export function CostPanel({ calls }: { calls: InferenceCall[] }) {
  const data = calls.map((c, i) => ({
    label: `#${i + 1} ${c.model_requested}`,
    judge: c.model_requested,
    model: c.model_used,
    cost: c.cost,
    tokens: c.prompt_tokens + c.completion_tokens,
  }))

  return (
    <Card className="gap-3">
      <CardHeader>
        <CardTitle className="text-sm font-semibold uppercase tracking-widest">
          Custo por chamada de juiz
        </CardTitle>
        <CardDescription>
          Stage A rejeita de graça; só o que passa no filtro determinístico gasta juiz.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="py-10 text-center text-sm text-muted-foreground">
            Nenhuma chamada de inferência ainda — rode a verificação com{' '}
            <code className="font-mono">live=true</code>.
          </p>
        ) : (
          <ChartContainer config={config} className="h-56 w-full">
            <BarChart data={data} margin={{ left: 4, right: 4, top: 8 }}>
              <CartesianGrid vertical={false} strokeOpacity={0.15} />
              <XAxis
                dataKey="judge"
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                fontSize={11}
              />
              <YAxis
                tickLine={false}
                axisLine={false}
                width={78}
                fontSize={11}
                tickFormatter={(v: number) => usd6(v)}
              />
              <ChartTooltip
                content={
                  <ChartTooltipContent
                    labelKey="label"
                    formatter={(value, _name, item) => (
                      <div className="flex w-full flex-col gap-0.5">
                        <span className="font-mono">{usd6(Number(value))}</span>
                        <span className="text-[10px] text-muted-foreground">
                          {item.payload.model} · {item.payload.tokens} tokens
                        </span>
                      </div>
                    )}
                  />
                }
              />
              {/* Sem animação: o painel refaz o fetch a cada 1.5s e a animação
                  reiniciaria do zero a cada ciclo, deixando as barras rasteiras. */}
              <Bar
                dataKey="cost"
                fill="var(--color-cost)"
                radius={[4, 4, 0, 0]}
                barSize={22}
                isAnimationActive={false}
              />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  )
}
