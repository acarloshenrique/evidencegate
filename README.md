# EvidenceGate

**Quando agentes pagam agentes, quem confere o trabalho?**

Camada de confiança para a economia de agentes: escrow cuja liquidação é
condicionada a verificação independente, identidade criptográfica real e
trilha de auditoria tamper-evident.

A2A permite que agentes conversem. x402/AP2 permitem que paguem. Nenhum
dos dois responde se a entrega foi boa — e settlement é final, sem
chargeback. O EvidenceGate é a peça que falta: o dinheiro só sai do
escrow quando um painel de juízes confirma que a entrega cumpre a
rubrica travada no contrato.

## Demo ao vivo (Oracle Cloud)

| Superfície | URL |
|---|---|
| Landing | https://evidencegate.163-192-115-82.sslip.io/ |
| Dashboard (escrows, trilha, custo/decisão) | https://evidencegate.163-192-115-82.sslip.io/dashboard |
| Auditor de voz (Agora ConvoAI) | https://evidencegate.163-192-115-82.sslip.io/voice |
| API docs | https://evidencegate.163-192-115-82.sslip.io/docs |

## Arquitetura

```
KYC principal ──► KYA agent (Ed25519, did:key, AgentCard assinado)
        │
        ▼
descoberta + policy (caps, allowlist, sanitização anti-injection)
        │
        ▼
quote com rubrica imutável (hash assinado pelo seller)
        │
        ▼
escrow  QUOTED → FUNDED → DELIVERED → VERIFIED → RELEASED
                            │             │
                            └── REJECTED → DISPUTED → ARBITRATED → RESOLVED
        │
        ▼
verificação em 2 estágios
  A: checks determinísticos (schema, hash, conteúdo, testes) — grátis
  B: painel 2-de-3 cross-model (commit-reveal) — fail-closed
        │
        ▼
trilha de auditoria hash-chained — verify_chain() re-deriva e
aponta o seq exato de qualquer adulteração
```

Decisões de design que importam:

- **Juiz nunca vê chain-of-thought do agente** — mata o ataque de
  "convencer o juiz" (Gaming the Judge: CoT manipulado infla FP ~90%).
- **Policy em código, não em prompt** — assinatura prova autorização;
  intenção é enforceada fora do LLM (confused deputy).
- **Fail-closed** — juiz indisponível/malformado vira `reject` com
  confiança 0; maioria 2-de-3 decide mesmo com um juiz caído.
- **Reputação só muda após settlement** — sem inflação por promessa.
- **Custo de verificação ∝ risco** — determinístico primeiro; LLM só
  no que passa; humano no que fica abaixo do threshold.

## Endpoints principais

`POST /principals` `POST /agents` `POST /agents/verify-card`
`POST /quotes` `POST /escrows` `POST /escrows/{id}/fund`
`POST /escrows/{id}/deliver` `POST /escrows/{id}/verify`
`POST /escrows/{id}/dispute` `POST /escrows/{id}/arbitrate`
`GET /escrows` `GET /audit/events` `GET /audit/verify`
`GET /report/compliance` `GET /metrics` `GET /dashboard` `GET /voice`
`POST /chat/completions` (OpenAI-compatible, SSE — ponte Agora ConvoAI)

## Rodando local

```bash
uv sync --locked
uv run pytest -q            # 13 testes, sem custo de LLM
uv run ruff check .
uv run python scripts/demo.py          # juízes mockados
uv run python scripts/demo.py --live   # juízes reais NeuraLake (~$0.01)
uv run uvicorn app.main:app --port 8000
```

## Documentos

- `PITCH.md` — roteiro de 4 min mapeado nos critérios do júri
- `STATUS.md` — feito / fazendo / falta (demo e produção)
- `BOARD.md` — tarefas, donos e critérios de "pronto" (metodologia squad)
- `docs/` — PRD, dossiê antifraude, deep research A2A, metodologia,
  checklist de produção, auditor de produção, kit de pitch

## Dashboard React

O console de auditoria (`/dashboard`) vive em `web/` (React 19 + Vite +
Tailwind 4 + shadcn/ui): tabela de escrows, detalhe do caso (rubrica,
evidencia, votos commit-reveal, ledger, eventos), timeline da trilha com
marcacao de tamper, custo por chamada e reputacao dos agentes. Build em
`web/dist` servido pela mesma origem; sem build, `/dashboard` cai no
console single-file. `scripts/seed_dashboard.py` popula casos de demo
sem gastar credito.
