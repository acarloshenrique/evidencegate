export function shortDid(did: string, head = 18): string {
  if (did.length <= head + 6) return did
  return `${did.slice(0, head)}…${did.slice(-4)}`
}

export function shortHash(hash: string | null | undefined, n = 10): string {
  return hash ? hash.slice(0, n) : '—'
}

export function money(value: number, digits = 2): string {
  return `$${value.toFixed(digits)}`
}

export function usd6(value: number): string {
  return `$${value.toFixed(6)}`
}

export function clock(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString('pt-BR')
}

export function datetime(ts: number): string {
  return new Date(ts * 1000).toLocaleString('pt-BR')
}

export function ago(ts: number): string {
  const s = Math.max(0, Math.floor(Date.now() / 1000 - ts))
  if (s < 60) return `${s}s atrás`
  if (s < 3600) return `${Math.floor(s / 60)}min atrás`
  if (s < 86400) return `${Math.floor(s / 3600)}h atrás`
  return `${Math.floor(s / 86400)}d atrás`
}
