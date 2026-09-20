# STATUS — EvidenceGate

> Atualizado por Devin (agente do Jazz). Fonte da verdade: `BOARD.md` (tarefas),
> `PITCH.md` (roteiro do demoday), `docs/` (spec completa).

## O que é

Camada de confiança/verificação para a economia agent-to-agent:
escrow onde **verificação é condição de settlement**, identidade criptográfica
KYC→KYA, policy em código, painel de juízes multi-modelo e trilha de auditoria
hash-chained. Não é demo de hackathon — é a fundação da startup.

## Ambiente

| Item | Onde |
|---|---|
| Repo | github.com/acarloshenrique/evidencegate — branch `feature/devin-core-trust-layer` |
| Deploy live | Oracle Cloud (Fsalvego/us-chicago-1) — **http://163.192.115.82:8000** |
| Dashboard | http://163.192.115.82/dashboard (polling 1.5s) |
| Serviço | systemd `evidencegate.service` na `jazz-oracle` (naia-oracle-arsenal) |
| Worktrees | `/root/hackathon-neuralake/evidencegate-devin` (hermes) · `~/evidencegate` (jazz-oracle) |
| Secrets | `.env` nos dois hosts (nunca no git — `.gitignore`) |

## Feito (13/13 testes · ruff limpo · demo live $0.0106)

- [x] Cripto real: Ed25519, `did:key`, canonical JSON, sign/verify, AgentCards assinados
- [x] Audit trail append-only hash-chained — `verify_chain()` re-deriva e aponta o seq adulterado
- [x] Registry: principals KYC + agentes KYA + introspecção anti-injection + reputação (só muda com outcome settled)
- [x] Policy engine em código: caps, allowlist, threshold humano, escopo decrescente
- [x] Escrow: `QUOTED→FUNDED→DELIVERED→VERIFIED→RELEASED` + `REJECTED→DISPUTED→ARBITRATED→RESOLVED`, funding idempotente
- [x] Verifier: stage A determinístico + painel 3 juizes (`reasoning`/`reasoning-pro`/`code`), commit-reveal, 2-de-3, **fail-closed** (juiz caído nunca aprova — provado ao vivo num 504)
- [x] Orquestrador autônomo: discover→evaluate→hire→verify→settle, filtra injection-flagged antes do evaluate
- [x] API FastAPI: 16 endpoints + `POST /chat/completions` OpenAI-compatible (ponte voz)
- [x] Dashboard ao vivo: KPIs custo/chamadas/integridade, pipeline visual de estados, trilha
- [x] Demo live validado: happy RELEASED · lixo DISPUTED→RESOLVED c/ reembolso · tamper detectado
- [x] Docs no repo: spec inteira em `docs/` + PITCH.md + BOARD.md

## Fazendo

- [ ] T012 Voz Agora ConvoAI → `/chat/completions` (CUSTOM_LLM_URL já apontado pro endpoint público; falta subir o agent server do recipe e testar a chamada)
- [ ] T013 Ensaio do pitch (roteiro pronto; backup offline se NeuraLake cair)

## Falta pro demoday (domingo 11h code freeze)

- [ ] Validar demo live 1x mais (juiz `reasoning` é instável — painel tolera, mas ensaiar o discurso do fail-closed)
- [ ] Merge `feature/devin-core-trust-layer` → `main` via integrador (Carlos)
- [ ] Gravar vídeo 60s (dashboard + demo + tamper test)
- [ ] Decidir se voz entra no pitch ao vivo ou vira "o que vem depois"

## Falta pra virar produção (pós-hackathon, do checklist/auditor)

- [ ] **Custódia de chaves**: hoje `agent_keys` no SQLite (custodial). Produção: KMS/HSM por principal, ou chaves ficam com o agente e o servidor só verifica
- [ ] **Authn/Authz na API**: endpoints hoje abertos — precisa auth por principal + assinatura Ed25519 em cada request (já temos a infra de chaves)
- [ ] **Persistência multi-tenant**: SQLite → Postgres; isolamento por principal
- [ ] **Settlement real**: adapters x402/AP2/Base testnet — o state machine já isola a interface
- [ ] **ERC-8004 on-chain**: registries Identity/Reputation/Validation pluggáveis (design já separado)
- [ ] **Observabilidade**: OTel `gen_ai.*` export, métricas por decisão (dashboard já mostra custo)
- [ ] **Anomaly detection (L6)**: velocity, delegation graph, scope drift, sybil cluster detection
- [ ] **Escalonamento humano**: `escalate_to_human` existe no painel — falta o fluxo real de fila/console
- [ ] **Rate limiting + hardening**: parser de juiz já é defensivo; falta WAF/limits na borda
- [ ] **Testes de caos**: juiz down, DB down, replay, concorrência no escrow

## Avisos

- `feature/t009-fastapi-core` no origin é uma ramificação congelada do meu trabalho (zero commits novos) — provavelmente criada por engano; pode apagar depois do merge.
- Juiz `reasoning` da NeuraLake é lento/instável (~550s/504 em think longo); mitigado com system prompt de think breve + max_tokens 3000 + retry. `reasoning-pro` e `code` sólidos.
- Cross Memory não é exposto na API pública — implementamos case-state sharing próprio entre juízes (mesma tese, honesto no pitch).
