# NeuraLake — The Launch Hackathon

**Documentação de estudo + pesquisa — 5 desafios A2A**
São Paulo · 19–20 set 2026 · gerado em 19/09 a partir do deck oficial `2026.09.19 NeuraLake_Launch_Hackathon_Challenges_vfinal (PT).pdf` + pesquisa de ecossistema.

---

## 0. TL;DR — o que você precisa saber em 60 segundos

- O hackathon é o **lançamento público da NeuraLake**, "o primeiro provider de inferência do mundo focado em B2A e A2A (agent-to-agent)".
- **Pergunta-guia do evento** (está embutida nos critérios de avaliação):
  > *"Seu produto se tornaria significativamente mais valioso se seu cliente principal fosse um agente de IA em vez de um humano?"*
  > *"The next trillion users won't be human."*
- **50 builders → 10 times de 5 → 5 desafios** (máx. 3 times por desafio). 2 dias de build contínuo, pitch de 4 min no demoday.
- O critério com mais peso é **Grau de autonomia A2A (30%)** + **Funciona de verdade (25%)**. Quase tudo que vale ponto envolve agente chamando agente **sem humano no loop** — com `model="auto"` e **Cross Memory** da NeuraLake dando pontos de eficiência (15%) e prêmio dedicado de US$ 1.000.
- **Code freeze domingo 11h00** → vídeo 60s + short deck → envio final GitHub 12h30 → demoday 13h30 (4 min pitch + 2 min Q&A).

---

## 1. A plataforma NeuraLake (leia antes de escolher desafio)

Fonte: `neuralake.com.br`, `api.html`, `pricing.html`, `bench.neuraserver.cloud` — extraído via scrapling em 19/09.

### 1.1 O que é

Provider de inferência **OpenAI-compatible** desenhado para economia de agentes. Em vez de um catálogo de 400+ modelos, a API expõe **5 capability endpoints** + `auto`, e um **router consciente de contexto** escolhe o modelo mais barato que completa a tarefa com confiabilidade.

```bash
# Base URL — drop-in do SDK OpenAI
https://api.neuralake.cloud/v1/chat/completions
Authorization: Bearer $NEURALAKE_API_KEY

# Python
from openai import OpenAI
client = OpenAI(
    base_url="https://api.neuralake.cloud/v1",
    api_key=os.environ["NEURALAKE_API_KEY"],
)
run = client.chat.completions.create(
    model="auto",          # text · code · reasoning · reasoning-pro · multimodal
    messages=history,
    stream=True,
)
```

### 1.2 Capability endpoints e preços (USD / 1M tokens)

| `model=` | Tier | Input | Output | Pra quê |
|---|---|---|---|---|
| `text` | Standard | $0.50 | $0.75 | Resumos, extração, chat simples, classificação, tagging |
| `code` | Developer | $1.00 | $1.00 | Geração de código, refatoração, review de arquitetura, testes |
| `reasoning` | Pro | $2.00 | $4.00 | Lógica multi-step, análise de contratos, compliance |
| `reasoning-pro` | Ultra | $2.00 | $4.50 | Matemática avançada, lógica de agente complexa, raciocínio autônomo profundo |
| `multimodal` | Vision & Docs | $1.50 | $1.50 | Parsing de documento, OCR, análise de screenshot |
| `auto` | Smart Route | dinâmico | dinâmico | Router escolhe a capability ótima por request; **cobra a taxa da capability roteada** — na prática barateia porque a maioria das requests cai nas mais baratas |

### 1.3 Cross Memory — o diferencial que dá prêmio

- APIs de inferência tradicionais são **stateless**: a cada handoff entre agentes/modelos você reenvia o histórico inteiro → o payload (e a conta) cresce a cada passo.
- **Cross Memory** é uma ponte de continuidade nativa entre modelos: carrega o estado ativo da tarefa (objetivo, contexto relevante, trabalho concluído, decisões, próxima ação esperada) para o modelo de destino. Cada modelo lê uma camada de estado compartilhada em vez do histórico completo.
- Números do marketing: **até 93% de economia de tokens** em workflows multi-modelo; benchmark real enterprise: **−79% de custo total de inferência**.
- Prova ao vivo no playground: trocar de `text` para `reasoning` no meio da tarefa e o segundo modelo se refere a "os cinco carros de corrida que listei antes" — sem sinal de que outro modelo começou o trabalho.
- **Playground beta:** `beta.neuraserver.cloud` · **Benchmark:** `bench.neuraserver.cloud` (dashboard com TTFT, custo/1M tokens, auditoria de roteamento `auto`, projeção financeira — útil pra gerar números pro pitch).
- Performance: **<200ms latência, zero cold start**, streaming SSE em todo endpoint. Multi-cloud (AWS/Azure/GCP/OCI), SOC 2 Type II, GDPR/LGPD.

### 1.4 Wonka (menção)

Fine-tuning "coming soon": você descreve o comportamento desejado, conecta dados privados, e o Wonka automatiza dataset → treino → avaliação → deploy. Compute cobrado pela sua cloud (AWS/Azure/GCP/OCI) + fee de plataforma. Provavelmente **não** usável no hackathon — mas citar no "o que viria depois" do pitch mostra visão.

### 1.5 Router — os 6 sinais avaliados por request

Task type · required modality · complexity · available context · expected output · execution cost — avaliados **antes** de qualquer compute ser gasto. Vale explicar no pitch como seu sistema se beneficia do roteamento.

---

## 2. Ferramentas do evento (do grupo + deck)

- **Créditos:** US$ 100 em créditos NeuraLake (60 dias) + créditos OCI patrocinados pela Oracle para cada time. Todos os participantes ganham certificado + canal da comunidade.
- **Agora Conversational AI** — Yan Belot (suporte técnico no grupo) mandou:
  - `docs.agora.io` — documentação oficial
  - `recipes.agora.io` — recipes de referência
  - `github.com/AgoraIO-Conversational-AI/recipe-agent-custom-llm` — **recipe BYOK (bring your own LLM)**
  - **Por que importa muito:** o ConvoAI Engine da Agora aceita qualquer endpoint **OpenAI-compatible** como LLM custom — ou seja, você aponta o estágio de LLM do agente de voz para `https://api.neuralake.cloud/v1` com `model="auto"`. Pipeline fica: **STT (Deepgram, managed) → NeuraLake (seu agente) → TTS (MiniMax, managed)**. É o caminho mais curto para um **agente de voz** no hackathon — e voz demo muito bem ao vivo.
  - Arquitetura do recipe: browser → Next.js → agent backend (porta 8000) → Agora ConvoAI Cloud → POST no seu `CUSTOM_LLM_URL` (precisa ser público — `ngrok http 8000`). Repo tem mock zero-key pra testar o pipeline inteiro antes de plugar a NeuraLake.
  - `server-custom-llm` (mesmo org no GitHub): proxy OpenAI-compatible com tool execution multi-pass, memória por canal e RAG — implementações em Python, Node e Go. Ideal se seu agente de voz precisar chamar outros agentes (A2A dentro do LLM stage!).

---

## 3. A transição que os desafios exploram

```
HOJE:    Human → Software → AI
AMANHÃ:  Human → Agent → Agent → Agent
```

O humano define **objetivo e orçamento**. Todo o resto — descobrir, avaliar, contratar, delegar, verificar e pagar — acontece **entre agentes**, com inferência roteada pela NeuraLake. Cada escolha de desafio é uma fatia diferente dessa cadeia.

---

## 4. DESAFIO 01 — The Autonomous Business

> *"Build a business that can operate primarily through agents"*

### O que o deck pede
- Sistema ponta a ponta: agentes recebem um objetivo, **decidem, acionam outros agentes e entregam um resultado de negócio**.
- Áreas possíveis: vendas, finanças, desenvolvimento de software, pesquisa, compras, operações de atendimento.
- **Restrição:** humanos definem o objetivo; agentes executam o fluxo.
- Meta: a demonstração mais clara da transição `Human → Software → AI` para `Human → Agent → Agent → Agent`.

### Por que esse desafio (segundo o deck)
É a demonstração mais visual da tese — ideal para times com perfil produto/negócio, e a fonte mais provável de **vídeos e cases para a semana de lançamento**.

### Pesquisa relacionada — como o mercado resolve isso hoje

**Frameworks de orquestração multi-agente (estado 2026):**

| Framework | Modelo mental | Quando usar | Obs. |
|---|---|---|---|
| **LangGraph** | Grafo/FSM com estado tipado, checkpoint por nó | Workflows branchy, long-running, precisa sobreviver a crash/interrupt humano | Líder de produção (~34–39M downloads/mês); usado por Klarna, Replit, Uber, LinkedIn; curva 1–2 sem |
| **CrewAI** | "Crew" de agentes por papel (role + goal + backstory) | Problema mapeia em time de especialistas; prototipagem rápida | ~5M downloads/mês, MCP first-class; aprende em horas |
| **OpenAI Agents SDK** | Handoff chains — agente delega para agente | Caminho mais rápido de zero a multi-agente funcional | Sucessor do Swarm; guardrails e tracing nativos; ~10M downloads/mês; agnóstico via LiteLLM |

**Padrão arquitetural recomendado para o desafio:** CEO/orchestrator agent recebe objetivo do humano → decompõe em tarefas → dispara sub-agentes especializados (cada um com sua capability NeuraLake ideal) → agrega resultado de negócio mensurável (receita simulada, relatório, código merged, campanha lançada).

### Ideias fortes para o demoday
- **"Startup em uma caixa":** humano dá "lance um SaaS de X" → agentes fazem pesquisa de mercado → geram código → QA → marketing copy → landing page deployada. Tudo auditável.
- **Operação de atendimento A2A:** agente de voz (Agora+NeuraLake) recebe chamada → aciona agente de análise → agente de resposta → agente de follow-up comercial.
- Mostrar o **fluxograma de handoffs ao vivo** (quem chamou quem, qual capability, custo acumulado em tempo real) — visual e direto nos critérios.

### Onde pontua
- Autonomia A2A 30%: cada handoff sem humano conta.
- Demo 25%: fluxo completo rodando ao vivo, não slides.
- Eficiência 15%: `model="auto"` + Cross Memory nos handoffs longos.

---

## 5. DESAFIO 02 — Agent Marketplace

> *"Build a marketplace where AI agents hire other AI agents"*

### O que o deck pede
- Um agente recebe objetivo mas **não tem todas as capacidades** → precisa autonomamente fazer o ciclo **Discover → Evaluate → Hire → Delegate → Verify** de outros agentes.
- **Restrição:** nenhum humano escolhe manualmente qual agente executa cada tarefa.
- Exemplo do deck: agente de startup contrata agentes de pesquisa, código, design e marketing — e depois **avalia o trabalho deles**.

### Por que esse desafio
Exercita descoberta e delegação entre agentes — o núcleo do A2A e a base do futuro **agent swarm da NeuraLake**.

### Pesquisa relacionada — os protocolos que já resolvem cada pedaço

**Descoberta (Discover):**
- **A2A Protocol (Google → Linux Foundation):** padrão aberto para agentes "opacos" interoperarem. Cada agente publica um **`AgentCard`** (JSON em `/.well-known/agent-card.json`) com skills, endpoint, transporte e auth. Transportes: JSON-RPC 2.0, gRPC ou REST sobre HTTP(S); sync, streaming SSE e push notifications para tarefas longas. **A2A ≠ concorrente do MCP** — MCP é agente→ferramenta; A2A é agente→agente. Refs: `a2a-protocol.org/latest`, `github.com/a2aproject/A2A`.
- **ERC-8004 "Trustless Agents"** (draft, autores de MetaMask/Ethereum Foundation/Google/Coinbase): 3 registries on-chain — **Identity** (ERC-721 com `tokenURI` → registration file com endpoints), **Reputation** (feedback signals padronizados), **Validation** (hooks p/ validadores: re-execução com stake, zkML, TEE oracles, juízes confiáveis). Feito exatamente pra "descobrir e confiar em agentes além de fronteiras organizacionais". Indexadores: `erc-8004.quicknode.com`, `8004.directory`.
- **Skyfire Seller Services:** seller agent publica serviços com preço + requisitos de identidade; buyer paga com tokens `kya`/`pay`/`kya-pay` em header HTTP. Modelo de catálogo já pronto.

**Avaliação + contratação (Evaluate → Hire):**
- **SmartMatch (Kroxy):** matching via IA por capacidade, reputação e preço — bom nome de componente pra copiar.
- **Score de reputação composto:** `erc-8004.quicknode.com` publica "reputation formula v1.3" — score com filtros sybil e sinais; `agntor` usa pilares com escrow real alimentando o trust score (+2 por escrow liberado, −3 por disputa, bônus por taxa de sucesso).

**Delegação + verificação (Delegate → Verify):** ver Desafio 05 — juízes LLM, escrow, trilhas de auditoria.

### Ideias fortes para o demoday
- **Registry local + AgentCards:** cada agente-vendedor do time publica AgentCard com skills/preço/capability; o agente-comprador faz discovery, ranqueia por score (reputação × preço × fit), contrata via A2A task, verifica com agente auditor e libera pagamento simulado.
- **Leilão reverso entre agentes:** comprador anuncia job → 3 agentes-vendedores fazem bid (preço + ETA + plano) → comprador escolhe por função de utilidade explicável.
- Marketplace com **dois lados rodando ao vivo** — vendedores de verdade executando (mesmo que com `model="text"`/`"code"` baratos) impressiona mais que mock.

### Onde pontua
- Autonomia A2A: o ciclo Discover→Verify **inteiro sem humano** é literalmente o critério.
- Confiança/explicabilidade 5% + tiebreak: justificar *por que* cada agente foi escolhido (logs de decisão).

---

## 6. DESAFIO 03 — Agent-to-Agent Economy

> *"Give AI agents a budget and let them spend it"*

### O que o deck pede
- Cada agente recebe **objetivo + orçamento limitado (simulado)** e pode **comprar serviços de outros agentes**.
- Exemplo: `CEO Agent → paga Research Agent → contrata Coding Agent → compra inferência → contrata QA Agent → entrega produto`.
- Desafio: **maximizar valor gerado por dólar/token gasto**, com o gasto **exibido em tempo real**.
- O humano fornece objetivo e orçamento. Todo o resto é A2A.

### Por que esse desafio
Coloca **custo por token no centro** — exatamente onde `model="auto"` e Cross Memory se destacam. Bom para parceiros de cloud/infra. (Prêmio dedicado: **"Best Agent Economy" — US$ 1.000 em créditos para o melhor valor gerado por token**.)

### Pesquisa relacionada — pagamentos entre agentes hoje

| Protocolo/infra | O que é | Como encaixa |
|---|---|---|
| **x402** (Coinbase → x402 Foundation) | Revive o HTTP `402 Payment Required`: server responde `PAYMENT-REQUIRED` header com requisitos → cliente assina `PAYMENT-SIGNATURE` (USDC gasless via EIP-3009, Base) → facilitator verifica e settle. SDKs TS/Python. Transporte-agnóstico: mapeia pra HTTP, MCP **e A2A**. | O "padrão de fato" pra agente pagar recurso/API por request. Mesmo simulado, implementar o **handshake 402** de verdade é elegante e barato de codar. |
| **AP2 — Agent Payments Protocol** (Google, 60+ parceiros: Mastercard, PayPal, Amex, Coinbase…) | Extensão de A2A/MCP pra pagamentos com **Mandates**: `Intent Mandate` (o que o humano autorizou) + `Cart/Checkout Mandate` + `Payment Mandate` — credenciais verificáveis (VDCs) assinadas, trilha de auditoria criptográfica não-repudiável. Payment-agnostic (cartão, stablecoin, PIX no roadmap). SDK Python: `github.com/google-agentic-commerce/ap2`. | Responde "quem autorizou o agente a gastar?" — o mandato assinado do humano **é** a estrutura de "objetivo + orçamento" do desafio. Mostrar mandate chain no pitch = confiança e explicabilidade. |
| **Skyfire** | Wallet agentic + identidade: tokens `kya` (know-your-agent), `pay`, `kya-pay`; políticas de gasto **por transação** (categoria, threshold); seller services com preço. | Referência de "policy engine" — gasto por transação evita agente descontrolado drenando orçamento. |
| **Payman** | Foco agente→humano (payouts), thresholds de aprovação human-in-the-loop, audit trail SOX. | Referência de graduated autonomy: abaixo de X o agente paga sozinho, acima pede humano. |
| **ACP — Agentic Commerce Protocol** (OpenAI + Stripe) | Checkout sessions REST entre agente e merchant (`POST /checkout_sessions`, update, complete), delegate payment token, merchant mantém PSP. | Padrão de "checkout agent-ready" pra quando o pagamento é com merchant real. |

**Padrões de budget/spend vistos na pesquisa:** spend cap on-chain (PolicyGuard do Arbiter — cap mensal, allowlist de workers, aprovação humana acima de threshold); escrow por job (Kroxy); autorização por mandato (AP2). **"Authorization pergunta 'esse pagamento devia ser autorizado'; verificação pergunta 'o trabalho foi bom' — você precisa dos dois"** (insight do Arbiter, ótimo quote pro pitch).

### Ideias fortes para o demoday
- **Ledger ao vivo:** dashboard mostrando cada transação A2A em tempo real — quem pagou quem, por quê, quantos tokens/capability, saldo restante, $/valor-gerado. O deck pede gasto em tempo real literalmente.
- **Otimizador de gasto:** o CEO agent tem $10 → precisa decidir entre agente-caro-rápido vs agente-barato-lento; mostrar o trade-off decidido com rationale logado.
- Dois runs comparativos: mesmo objetivo com `model="reasoning-pro"` fixo vs `model="auto"` → mostrar economia (usa o benchmark da NeuraLake como evidência).
- Handshake estilo **x402 simulado**: vendedor responde 402 com quote → comprador "assina" e reenvia → entrega → recibo. Fácil de implementar em HTTP puro, lê-se como o protocolo real.

### Onde pontua
- Eficiência 15% é o coração do desafio (métrica: valor/$ · valor/token).
- Autonomia: decisões de compra são agente→agente, humano só dá budget.

---

## 7. DESAFIO 04 — Agent-First Product

> *"Rebuild a product whose primary customer is an agent, not a human"*

### O que o deck pede
- Pegar produto/negócio existente (e-commerce, banco, SaaS, logística, saúde, jurídico) e **redesenhar para que um agente** — não uma pessoa — descubra, avalie, negocie, compre e use.
- **Sem dashboards, formulários ou onboarding para humanos:** ofertas **legíveis por máquina**, preços **negociáveis**, interfaces **chamáveis** ponta a ponta.
- **Mostrar a mesma jornada duas vezes:** humano hoje vs. agente pela interface agent-first.
- **Restrição:** o humano nunca toca na interface depois de definir o objetivo.

### Por que esse desafio
Responde diretamente à pergunta-guia e é **o mais acessível para quem já tem um negócio** — inclusive startups residentes (Cubo, Oracle for Startups).

### Pesquisa relacionada — o que "agent-readable" significa em 2026

- **ACP (OpenAI+Stripe):** o padrão mais concreto de "produto agent-first" — catálogo/feed + checkout sessions REST + delegate payment. `agenticcommerce.dev`, `github.com/agentic-commerce-protocol/agentic-commerce-protocol`. Instant Checkout no ChatGPT roda em cima disso.
- **AgentCard (A2A) + MCP servers:** o produto vira um servidor A2A/MCP — a "UI" é o card/capability schema, não HTML.
- **Ofertas legíveis por máquina:** JSON schemas de produto, preço, SLA, política de negociação — tipo `/.well-known/` (AgentCard, `llms.txt`, OpenAPI) em vez de páginas.
- **Negociação A2A:** preço negociável implica protocolo de quote/counter-quote — dá pra modelar como A2A task com rodadas (oferta → contra-oferta → aceite), tudo com rationale.
- **Lado do comprador:** agente com objetivo + constraints (orçamento, prazo, spec) consulta N "vitrines" agent-readable, compara em função de utilidade e fecha — ciclo idêntico ao Desafio 02 visto do lado do produto.
- **Voz como interface:** Agora ConvoAI BYOK → o "agente-cliente" pode literalmente **ligar** pro negócio (STT→LLM→TTS) — uma demo de agent-first product onde o cliente é um agente de voz negociando com um agente-vendedor é diferenciada e roda com NeuraLake no meio.

### Ideias fortes para o demoday
- **"API-only bank/SaaS":** refaça a jornada de abrir conta/contratar plano — humano leva 20 cliques e 2 dias; o agente faz discovery do catálogo JSON, negocia preço, assina mandate AP2 e consome o serviço em 40s.
- **Side-by-side no pitch:** mesma jornada nas duas telas (deck pede explicitamente) — vídeo do humano clicando vs. log do agente chamando endpoints.
- Escolher um domínio com **dor de onboarding real** (seguro, crédito, telecom, SaaS enterprise) — quanto pior a UX humana, maior o contraste.

### Onde pontua
- Valor de negócio 15%: pergunta-guia respondida na veia.
- Pitch 10%: o comparativo humano-vs-agente é a narrativa mais fácil de contar em 4 min.

---

## 8. DESAFIO 05 — Agent Trust & Verification

> *"When agents pay agents, who checks the work?"*

### O que o deck pede
- A **camada de confiança** das transações entre agentes: verificação do trabalho entregue, decisões explicáveis, **trilhas de auditoria, reputação, disputas ou escrow**.
- Toda decisão (qual agente foi contratado, qual modelo foi usado, por quê, a que custo) deve ser **registrada e explicável a um auditor humano**.
- Exemplo do deck: agente **Crítico/Auditor** que revisa o trabalho de outros agentes, pontua, **libera (ou retém) o pagamento** e gera relatório de compliance aceitável por um banco.
- Desafio: fazer uma empresa aceitar que agentes transacionem **sem humano no loop**.

### Por que esse desafio
É o que **bancos, indústria e clientes enterprise vão exigir** antes de adotar A2A. Ideal para times de dados, segurança e compliance — e para patrocinadores desses setores.

### Pesquisa relacionada — projetos reais de verificação entre agentes (ouro pro seu pitch)

| Projeto | Mecanismo | O que roubar |
|---|---|---|
| **Kroxy** (Devpost) | Marketplace onde agentes contratam agentes; USDC em escrow (`KroxyEscrow.sol`, Base); verificação autônoma (polling de quality conditions); disputa → **3 juízes LLM independentes (Claude, GPT-4o, Gemini) com commit-reveal on-chain, consenso 2-de-3**; reputação on-chain (`KroxyReputation.sol`); trilha de auditoria **hash-chained SHA-256** | Painel de juízes multi-modelo + commit-reveal + trilha hash-chained = o "relatório de compliance aceitável por um banco" |
| **Tribunal** (`kalashshah/tribunal`) | "Corte de IA verificável": disputa vira **julgamento** — cada lado tem **lawyer agent**, evidências passam por clerk, juiz (iNFT ERC-7857) delibera e vota; execução verificável via **REE (Gensyn)** — receipt criptográfico por inferência provando que o juiz não foi adulterado | Metáfora de tribunal com advogados-agente = narrativa de demo incrível; receipts de inferência = prova de integridade |
| **Arbiter** (`ansleyneojingyi/arbiter`) | Agente que contrata e paga via escrow (fork ERC-8183) **só liberado após avaliador independente verificar**; **PolicyGuard on-chain**: cap de gasto, allowlist de workers, aprovação humana acima de threshold; verificação em **2 estágios**: pre-check estrutural determinístico + painel de juízes LLM **cross-model, cross-infra** (Qwen + gpt-oss + DeepSeek) com rubrica travada | Separação autorização-vs-qualidade (quote acima); two-stage verify é implementável num fim de semana |
| **TrustThenVerify** (`trustthenverify.com`) | Agentes com chaves secp256k1 assinam tudo; escrow com política — critérios de aceite em inglês → **dual-LLM traduz pra constraints formais** → engine adversarial ("Argus") stress-testa as constraints antes de ir ao ar; verificação por hash match, schema, constraint solver, **quórum de 5 oráculos** ou confirmação do comprador; fundos via Stripe ou USDC em Base | Critérios de aceite → constraints formais + red-team das próprias regras |
| **agntor** | AI judge (Gemini) decide release/reject com confidence + reasoning; trust score recalculado a cada settlement | Loop escrow→score simples de explicar |
| **ERC-8004** | Reputation + Validation registries: feedback padronizado, validadores plugáveis (stake re-execução, zkML, TEE, juízes confiáveis) | Camada de reputação portátil entre organizações |
| **AP2 mandates** | VDCs assinados criam trilha criptográfica **não-repudiável** de autorização | "Quem autorizou" provado criptograficamente, não logado em texto |

**Padrões de verificação mapeados na pesquisa:**
1. **Determinística:** schema/hash check, testes rodando, constraint solver — barata, primeiro filtro.
2. **LLM-as-judge único:** rápido mas contestável (e se o juiz erra?).
3. **Painel multi-juiz cross-model:** 2-de-3 ou quórum de oráculos — robustez por diversidade de modelo/infra (o argumento mais vendável pra "banco").
4. **Commit-reveal:** juízes não veem o voto dos outros antes de votar — evita herding.
5. **Escrow + dispute flow:** libera se verificado → disputa se não → arbitragem → reputação atualizada.
6. **Audit trail hash-chained:** cada decisão (quem, qual modelo, por quê, custo) append-only com hash do anterior — o "relatório para auditor humano" literal do deck.
7. **Verifiable inference:** receipts criptográficos da execução do juiz (REE/TEE/zkML) — camada mais hardcore, cite como roadmap.

### Ideias fortes para o demoday
- **Auditor agent genérico:** intercepta qualquer handoff A2A do sistema → valida entregável contra spec → pontua → libera/retém pagamento → emite relatório de compliance (JSON + PDF) com rationale e custo por decisão.
- **Judge panel com modelos NeuraLake:** juízes em `reasoning` + `reasoning-pro` + `code` (cross-capability), commit-reveal simulado, 2-de-3 — tudo com Cross Memory carregando o caso entre juízes.
- **Policy layer:** regras de gasto (cap, allowlist, threshold humano) checadas **fora do prompt** — em código/on-chain simulado — porque "policy em prompt não é policy".
- Demo killer: mostrar um agente **trapaceiro** (entregável ruim de propósito) → auditor reprova → escrow retido → disputa → juízes arbitraram → relatório de compliance sai explicando cada decisão. Isso é literalmente o pedido do deck.

### Onde pontua
- Confiança/explicabilidade 5% direto + reforça Autonomia (o auditado é A2A puro) + eficiência (custo por decisão logado).
- Desempate "grau de autonomia A2A": trust layer é o que permite autonomia total.

---

## 9. Critérios de avaliação — como atacar cada um

Júri de 5 (executivo Oracle, founder NeuraLake, investidor, Cubo/early adopter, eng. sênior externo) · média simples · **desempate = grau de autonomia A2A** · People's Choice por voto do público via QR.

| Peso | Critério | O que mede | Tática |
|---|---|---|---|
| **30%** | Grau de autonomia A2A | Quantas decisões e handoffs acontecem **sem humano** | Conte handoffs no pitch ("7 decisões, 0 humanos depois do objetivo"). Qualquer clique humano no meio do fluxo perde ponto no critério mais pesado. |
| **25%** | Funciona de verdade | Fluxo completo **rodando ao vivo**, não slides | Demo ao vivo > vídeo > mock. Tenha fallback gravado, mas rode ao vivo — júri técnico detecta fake. |
| **15%** | Valor por token / eficiência | Uso de `model="auto"`, Cross Memory e roteamento | Use `auto` nos agentes + Cross Memory nos handoffs; mostre custo acumulado ao vivo; cite o benchmark (−79%). Disputa prêmio "Best use of auto + Cross Memory" (US$1.000). |
| **15%** | Valor de negócio | Produto mais valioso com agente como cliente? | Responda a pergunta-guia na primeira frase do pitch. |
| **10%** | Pitch e clareza | 4 min: problema → demo → o que viria depois | Estrutura exata do deck: problema (30s) → demo (2min30) → roadmap (1min). |
| **5%** | Confiança e explicabilidade | Logs, rationale das decisões, verificação entre agentes | Log estruturado por decisão: `{quem, qual_modelo, por_quê, custo, resultado}`. Mesmo fora do Desafio 05, um mini-audit-trail rende esse ponto quase de graça. |

**Prêmios especiais:** "Best use of auto + Cross Memory" (US$1.000 + menção no benchmark público) e "Best Agent Economy" (US$1.000 — melhor valor gerado por token). Os dois apontam pra mesma jogada: **mostrar custo em tempo real + Cross Memory de verdade**.

---

## 10. Arquitetura de referência "ganha-critérios" (compositiva)

Combinação que cobre os critérios independente do desafio escolhido:

```
Humano → [objetivo + orçamento] → Orchestrator Agent (model="auto")
   │
   ├─ Discover: registry de AgentCards (estilo A2A/.well-known)
   ├─ Evaluate: ranking por reputação×preço×fit (rationale logado)
   ├─ Hire: handshake 402 → quote → "pagamento" simulado (mandate)
   ├─ Delegate: sub-agentes em capabilities certas (text/code/reasoning)
   │      └─ Cross Memory carrega estado entre modelos
   ├─ Verify: auditor agent (two-stage: checks determinísticos → judge panel)
   └─ Settle + Audit: ledger hash-chained, relatório de compliance,
      dashboard de custo em tempo real
```

**Stack mínima sugerida:**
- Inferência: NeuraLake `model="auto"` em tudo (SDK OpenAI, base_url trocado — zero atrito com CrewAI/LangGraph/Agents SDK via LiteLLM ou base_url).
- Orquestração: OpenAI Agents SDK (mais rápido pra hackathon) ou CrewAI (papéis); LangGraph se precisar checkpoint/resume.
- Comms A2A: HTTP+JSON simples inspirado no protocolo A2A (AgentCard + tasks) — ou `a2a-sdk` oficial se quiser conformidade real.
- Voz (opcional, wow factor): Agora ConvoAI BYOK apontando pra NeuraLake.
- Pagamento: handshake 402 simulado (ou x402 real em testnet Base se alguém do time souber Solidity — provavelmente overkill pro tempo).
- Verificação: judge panel 2-de-3 com commit-reveal + audit trail hash-chained (SHA-256 append-only, ~40 linhas).
- Dashboard: streamlit/next simples — ledger e custo ao vivo.

---

## 11. Cronograma (do deck)

**Sábado 19/09:** 08h30 credenciamento · 09h abertura (Oracle + tese NeuraLake) · 10h apresentação dos desafios + início do build · 12h30–13h30 almoço · 14h–16h mentoria · 16h coffee · 19h30 pizza · 20h liberação do prédio.
**Domingo 20/09:** 08h30 café · 09h–11h hands-on + mentoria turno 2 + checkpoint pré-demo · **11h code freeze (repo + vídeo 60s + short deck)** · 12h30 envio final GitHub · 13h30 demoday (10 pitches × 4min + 2min Q&A) · 16h premiação.

---

## 12. Links úteis

**NeuraLake:** site `neuralake.com.br` · API `api.neuralake.cloud/v1` · playground `beta.neuraserver.cloud` · benchmark `bench.neuraserver.cloud` · contato celso.diniz@neuralake.com.br / katherine@neuralake.com.br
**Agora:** `docs.agora.io/en/ai` · `recipes.agora.io` · `github.com/AgoraIO-Conversational-AI/recipe-agent-custom-llm` · `server-custom-llm` (proxy com tools/RAG/memória)
**Protocolos:** A2A `a2a-protocol.org` + `github.com/a2aproject/A2A` · x402 `github.com/x402-foundation/x402` + `docs.cdp.coinbase.com/x402` · AP2 `ap2-protocol.org` + `github.com/google-agentic-commerce/ap2` · ACP `agenticcommerce.dev` + `github.com/agentic-commerce-protocol/agentic-commerce-protocol` · ERC-8004 `ercs.ethereum.org/ERCS/erc-8004` + `8004.directory`
**Trust/verificação (referências):** Kroxy (Devpost) · `github.com/kalashshah/tribunal` · `github.com/ansleyneojingyi/arbiter` · `trustthenverify.com` · Skyfire `docs.skyfire.xyz` · Payman
**Frameworks:** LangGraph · CrewAI · OpenAI Agents SDK (todos aceitam base_url custom → NeuraLake via LiteLLM ou SDK OpenAI)

---

*Fontes: deck oficial do evento (PDF do grupo), site/API/pricing/benchmark da NeuraLake (scrapling, 19/09), docs A2A/x402/AP2/ACP/ERC-8004, docs Agora ConvoAI, comparativos LangGraph/CrewAI/Agents SDK 2026, projetos de verificação A2A (Kroxy, Tribunal, Arbiter, TrustThenVerify, agntor).*
