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
```

```
ID: T010
Título: Dashboard ao vivo — ledger, trilha, custo por decisão (HTML+SSE ou Streamlit)
Dono: (livre)
Depende de: T009
Pronto quando: roda o demo e a tela mostra estados do escrow e custo acumulado em tempo real
```

```
ID: T011
Título: Cross Memory no auditor — estado do caso compartilhado entre juízes
Dono: (livre)
Depende de: T007
Pronto quando: confirmar com NeuraLake o parâmetro; medir tokens com/sem e registrar economia no ledger
```

```
ID: T012
Título: Voz Agora ConvoAI → NeuraLake (agora-recipe apontando CUSTOM_LLM_URL pro nosso backend)
Dono: (livre)
Depende de: T009
Pronto quando: agente de voz responde status de um escrow por voz usando a NeuraLake como LLM
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
