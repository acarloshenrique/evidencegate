# BOARD — EvidenceGate (Desafio 05 · NeuraLake Hackathon)

Regras (livro-metodologia-squad): 1 tarefa = 1 branch/worktree · dono fixo · marca **peguei** ANTES de mexer ·
só o Integrador rotativo faz merge `--no-ff` na `main` · merge em ordem de dependência · `git worktree remove` após merge.

Integrador atual: **Carlos** (rotaciona a cada ciclo de merge, ~1h30)

---

## Pronto

```
ID: T001
Título: Core cripto — canonical JSON, SHA-256, base58, did:key Ed25519, sign/verify
Dono: Jazz + Devin
Worktree: ../evidencegate-devin
Branch: feature/devin-core-trust-layer
Depende de: —
Pronto quando: roundtrip sign/verify passa; mensagem alterada falha verificação (test_crypto_roundtrip)
```

```
ID: T002
Título: Audit trail append-only hash-chained + verify_chain()
Dono: Jazz + Devin
Worktree: ../evidencegate-devin
Branch: feature/devin-core-trust-layer
Depende de: T001
Pronto quando: adulterar 1 campo de evento passado -> verify_chain FAIL apontando seq (test_audit_tamper_detection)
```

```
ID: T003
Título: Registry — principals KYC + agentes KYA + AgentCard assinado + sanitização + reputação
Dono: Jazz + Devin
Worktree: ../evidencegate-devin
Branch: feature/devin-core-trust-layer
Depende de: T001, T002
Pronto quando: card adulterado por terceiro falha assinatura; card com injection é flagado na trilha (test_card_signature_and_injection)
```

```
ID: T004
Título: Policy engine em código — caps, allowlist, threshold humano, escopo decrescente
Dono: Jazz + Devin
Worktree: ../evidencegate-devin
Branch: feature/devin-core-trust-layer
Depende de: T002
Pronto quando: tx acima do cap é bloqueada antes de travar fundos, evento policy.denied na trilha (test_policy_blocks_over_cap)
```

```
ID: T005
Título: Escrow state machine + ledger — QUOTED→FUNDED→DELIVERED→VERIFIED→RELEASED / REJECTED→DISPUTED→ARBITRATED→RESOLVED
Dono: Jazz + Devin
Worktree: ../evidencegate-devin
Branch: feature/devin-core-trust-layer
Depende de: T003, T004
Pronto quando: fluxo feliz paga seller +2 rep; fraude reembolsa buyer −3 rep; funding idempotente; transição ilegal levanta erro (test_happy_path_and_idempotency, test_fraud_path_dispute)
```

```
ID: T006
Título: Verifier two-stage — stage A determinístico + judge panel 3 capabilities commit-reveal 2-de-3
Dono: Jazz + Devin
Worktree: ../evidencegate-devin
Branch: feature/devin-core-trust-layer
Depende de: T005
Pronto quando: stage A rejeita sem chamar juiz; painel 2-1 libera; votos gravados com commit hash (test_panel_commit_reveal_majority)
```

## Fazendo

```
ID: T007
Título: Robustez dos juízes reais — parser <think>, fail-closed por juiz, retry 504
Dono: Jazz + Devin
Worktree: ../evidencegate-devin
Branch: feature/devin-core-trust-layer
Depende de: T006
Pronto quando: demo --live roda 3 juízes reais com vote parseado e confidence > 0 em reasoning e reasoning-pro
```

## A fazer

```
ID: T008
Título: Orquestrador + demo end-to-end (feliz + ataque + tamper test) + compliance report
Dono: Jazz + Devin
Depende de: T007
Pronto quando: scripts/demo.py --live roda sem exceção, custo total < $0.10, compliance_report.md exportado
```

```
ID: T009
Título: API FastAPI expondo registry/quote/escrow/verify/audit (app/main.py)
Dono: Jazz + Devin  [peguei]
Worktree: ../evidencegate-devin
Branch: feature/devin-core-trust-layer
Depende de: T005, T006
Pronto quando: /docs mostra endpoints; teste de integração cobre fluxo feliz via HTTP
FEITO: 16 endpoints, POST /chat/completions OpenAI-compatible (ponte voz Agora), testes 13/13, ruff limpo
```

```
ID: T010
Título: Dashboard ao vivo — ledger, trilha, custo por decisão
Dono: Jazz + Devin  [feito]
Depende de: T009
FEITO (v2): merge do dashboard React do Kauan (t010-live-dashboard) —
  app shell com sidebar (Visao geral/Escrows/Auditoria/Agentes/Custos),
  tabela + detalhe do caso (rubrica, evidencia, votos, ledger, eventos),
  timeline com tamper-seq, custo por chamada, reputacao. Tokens do design
  system aplicados (indigo/navy/Inter). /dashboard/legacy = single-file.
  API: /ledger, list_escrows com votos, agents com flag. seed_dashboard.py
  populou 4 casos + 1 verify LIVE real (reasoning falhou -> fail-closed,
  2-de-3 RELEASED, /bin/bash.003).
FEITO (v2 React): web/ com React 19 + Vite + Tailwind 4 + shadcn/ui, polling 1.5s via react-query.
  Painéis: stat cards (trilha íntegra, custo total, custo por decisão liquidada, valor travado),
  tabela de escrows -> sheet do caso (rubrica travada + evidência + votos commit-reveal + ledger + eventos),
  timeline da trilha hash-encadeada com marcação de adulteração, gráfico de custo por chamada de juiz, agentes+reputação.
  Backend: CORS dev, GET /escrow/{id} agora devolve quote/votes/events, /dashboard serve web/dist (legado em /dashboard/legacy).
  scripts/seed_dashboard.py popula casos de demo offline. pytest 13/13, ruff limpo, npm run build limpo.
```

```
ID: T011
Título: Cross Memory no auditor — estado do caso compartilhado entre juízes
Dono: Jazz + Devin  [pesquisado]
Depende de: T007
Status: API pública NÃO expõe parâmetro de memória (frontend beta.neuraserver.cloud só manda campos OpenAI padrão; probes com session_id e memória implícita não recordam). Nosso painel JÁ implementa o equivalente: cada juiz recebe case state (scope+criteria+evidence), nunca histórico — economia real de tokens vs. reenviar contexto. Perguntar o parâmetro aos mentores NeuraLake no evento; pitch pode reivindicar "cross-model case state" como implementação própria.
```

```
ID: T012
Título: Voz Agora ConvoAI → NeuraLake (agora-recipe apontando CUSTOM_LLM_URL pro nosso backend)
Dono: Jazz + Devin  [em curso]
Depende de: T009
Status: QUASE COMPLETO. Agent server systemd (porta 8010) + /chat/completions com SSE streaming + pagina /voice (RTC client) + HTTPS https://evidencegate.163-192-115-82.sslip.io. startAgent retornou agent_id real via REST. Falta so: teste humano com mic — abrir /voice, falar, ouvir auditor.
```

```
ID: T014
Titulo: Grafo de proveniencia / rastreio semantico (KYC->KYA->quote->escrow->votos->dinheiro->eventos)
Dono: Devin  [completo]
Depende de: T010
Pronto quando: /trace/graph + /trace/{id} servindo nos publicos + view "Rastreio" no dashboard React (cytoscape)
Status: COMPLETO. app/trace.py deriva nos tipados (principal, agente, quote, escrow, juiz) e arestas
semanticas (KYC_BACKS, SIGNED_QUOTE, FUNDED, JUDGED_BY, VOTE, MONEY, LOGGED). Deploy live: 15 nos,
54 arestas do seed+caso live. Neo4j fica como backend opcional atras do mesmo contrato de API.
```

```
ID: T013
Título: Pitch + vídeo 60s + short deck (code freeze domingo 11h)
Dono: Jazz
Depende de: T008
Pronto quando: roteiro mapeado nos 6 critérios do júri com prova concreta de cada
```

---

## Crítica adversarial (Parte 6) — status

| Premissa | Balde | Sobrevive? | Evidência |
|---|---|---|---|
| Banco aceita agente transacionando se houver trilha auditável | Desejável | Parcial | Deck diz literalmente que é o que enterprise vai exigir; falta validar com Cubo/Itaú no evento (mentoria) |
| Juiz LLM é confiável o suficiente pra decidir dinheiro | Factível | Sim, com two-stage + panel | Gaming the Judge (90% FP com CoT) → por isso juiz vê artefato, não CoT; 2-de-3 cross-capability |
| Rubrica travada evita mover a trave | Factível | Sim | quote_hash assinado antes do trabalho |
| Reputação resiste a sybil | Viável | Parcial | só escrow settled muda score; falta custo de criação de identidade e cluster detection (L6) |
| Custo por decisão cabe em produção | Viável | Sim | demo live: $0.009 / 7 chamadas |
| **Furo em produção**: juiz cai (504) | — | Corrigido | retry + fail-closed: juiz indisponível = reject, nunca approve |
| **Furo em produção**: reasoning gasta budget em `<think>` | — | Em correção (T007) | parser + max_tokens |
