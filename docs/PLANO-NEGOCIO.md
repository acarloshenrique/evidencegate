# EvidenceGate — Plano de Negócio

*Documento de estratégia comercial. Segue os frameworks do
`CHECKLIST-PRODUCAO.md` (ICP, posicionamento, pricing, unit economics).*

---

## 1. O que vendemos

Não vendemos agente, não vendemos pagamento, não vendemos modelo de IA.
Vendemos **a resposta para "quem confere o trabalho?"** — verificação e
settlement condicionado a prova, como serviço.

Três produtos, um só motor:

| Produto | O que é | Métrica de cobrança |
|---|---|---|
| **Verify API** | Cliente manda rubrica + evidência entregue; recebe veredicto com prova (votos do painel, confiança, Stage A, trilha). | Por decisão verificada |
| **Escrow verificado** | O dinheiro fica travado e só se move por veredicto. Settlement *é* a consequência da verificação, não um passo separado. | bps sobre o volume liquidado |
| **Audit & Compliance** | Trilha hash-chained, compliance report legível, grafo de proveniência, `/explain` — o artefato que compliance, auditor e regulador leem. | SaaS por tenant/mês (retenção) |

A oferta em uma frase: **"Integre em 30 minutos e nunca mais pague por
trabalho de agente sem prova."**

---

## 2. Posicionamento

> **Para empresas que vão deixar agentes transacionarem sem humano no loop,
> o EvidenceGate é a camada de verificação e settlement que só libera o
> pagamento quando o entregável prova que atende a rubrica contratada —
> diferente dos trilhos de pagamento (x402, AP2, cartão), que movem
> dinheiro sem conferir nada, e diferente de revisão humana, que não roda
> em velocidade de máquina, porque nosso veredicto é criptográfico,
> multi-juiz e custa centavos por decisão.**

**Categoria:** nova — *agent trust & verification*. Categoria nova custa
educação, mas o timing é o ativo: os trilhos (A2A, x402, AP2, ERC-8004)
estão sendo construídos AGORA por Google, Coinbase, Stripe, Mastercard —
e nenhum deles responde "o trabalho foi bom?". Insight que roubamos do
ecossistema: *"autorização pergunta se o pagamento devia ser autorizado;
verificação pergunta se o trabalho foi bom — você precisa dos dois."*
Eles são a primeira metade. Nós somos a segunda.

**A alternativa real** (o concorrente não é outro SaaS):

1. **Humano aprovando cada transação** — não escala, mata a tese A2A.
2. **Confiar no agente vendedor** — sybil, injection, entregável lixo.
3. **Construir internamente** — o argumento de venda: ninguém constrói
   sua própria Stripe. Juiz multi-modelo + commit-reveal + fail-closed +
   trilha tamper-evident não é projeto de sprint.

**Hierarquia de mensagem:**

- **Promessa:** o cofre só abre com prova.
- **Pilar 1 — Autonomia real:** settlement sem humano no caminho.
  Prova: 6 escrows liquidados ao vivo, zero clique.
- **Pilar 2 — Verificação que aguenta porrada:** painel cross-capability
  2-de-3 com fail-closed. Prova: juiz caiu ao vivo duas vezes, o sistema
  decidiu certo.
- **Pilar 3 — Auditoria que sobrevive a ataque:** trilha hash-chained +
  explicabilidade derivada dos dados. Prova: adultera 1 caractere, o
  verificador aponta o seq exato.

---

## 3. ICP (Ideal Customer Profile)

### ICP primário — o que paga primeiro
**Fintechs, bancos digitais e empresas enterprise pilotando pagamentos
agentic** (A2A/x402/AP2) — times de 50+ engenheiros, com budget de IA
aprovado, correndo o risco regulatório de "agente movendo dinheiro".

- **Decisor:** Head of AI Platform / VP de Engenharia + Chief Compliance
  Officer (a venda só fecha se os dois assinarem).
- **A dor com nome e sobrenome:** "meu agente vai pagar o agente de outra
  empresa e eu não tenho como provar pro board, pro auditor e pro BACEN
  que o trabalho foi conferido antes do dinheiro sair."
- **Momento de compra:** quando o piloto interno de agentic payments
  precisa ir pra produção — é aí que "alguém tem que conferir" vira
  bloqueio, não feature.

### ICP secundário
**Plataformas e marketplaces de agentes** (o próprio "swarm" da
NeuraLake, futuros mercados A2A) — precisam de trust nativo pra atrair
cliente enterprise. Aqui a gente entra como infra white-label.

### ICP terciário
**Auditores, seguradoras e compliance-as-a-service** — não operam o
fluxo, consomem a trilha. Receita menor, mas é o que legitima o registry.

### Quem paga e por quê
**O comprador do serviço paga** — porque o risco é dele. O vendedor tem
incentivo de pagar também (reputação verificável vende mais), o que abre
modelo two-sided depois. Mas o primeiro contrato é sempre de quem tem o
dinheiro em risco.

---

## 4. Modelo de negócio e pricing

**Métrica de valor:** decisão verificada — o cliente paga mais quando
verifica mais, e a conta é previsível. Take-rate como alternativa pra
cliente de volume alto (quem prefere % do que assinatura).

**Custo real medido:** $0.0047–$0.0118 por decisão (painel 3 juízes +
orquestrador). COGS seguro: **~$0.02/decisão** com retry.

### Planos (3, padrão que funciona)

| | **Verify (self-serve)** | **Settle** ⭐ recomendado | **Enterprise** |
|---|---|---|---|
| Verificações | $0.10/decisão | $0.05/decisão | contrato |
| Escrow verificado | — | 0.5–1% do volume | custom |
| Compliance reports | básico | completos + export | + auditor seat |
| Retenção da trilha | 30 dias | 1 ano | 7 anos |
| Políticas custom | — | sim | sim + policy engine dedicado |
| Juiz do próprio cliente (BYO judge) | — | — | sim |
| Arbitration desk | — | add-on | incluso |
| Deploy | cloud | cloud | VPC/self-host |
| Preço | uso, sem mensalidade | $999/mês + uso | anual |

**Trial:** 100 decisões grátis, sem cartão — o produto se prova na
primeira trilha adulterada que o cliente mesmo tenta fraudar.

**Arbitration desk** é a jóia escondida: a exceção humana não é custo —
é **serviço premium**. Disputa resolvida por árbitro com a trilha inteira
na mesa, cobrada por caso ou inclusa no Enterprise.

### Por que esse preço se sustenta
$0.10/decisão contra COGS de $0.02 = ~80% de margem. Mas o argumento não
é margem — é o custo do alternativo: uma única liquidação errada de
$1.000 custa 10.000 decisões nossas. O cliente não compara nosso preço
com o custo de inferência; compara com o custo do erro.

---

## 5. Unit economics (modelo base)

| Linha | Valor |
|---|---|
| COGS por decisão | ~$0.02 (LLM panel + infra, com retry) |
| Preço médio efetivo | $0.05–0.10/decisão |
| Margem bruta | ~80% |
| Cliente Growth típico | 20k decisões/mês → $1k uso + $999 base ≈ **$2k MRR** |
| Cliente Enterprise | $50–150k/ano (VPC + arbitration desk + SLA) |
| Take-rate alternativo | 1% de $1M liquidado/mês = $10k MRR num cliente só |

Alavancas de custo já provadas no produto: Stage A rejeita de graça antes
de gastar juiz; cache de veredicto por evidence_hash; modelo mais barato
pra primeira instância do painel.

---

## 6. Tem gente pra comprar? (demanda)

Sim — e o timing é o argumento:

- **AP2** tem Mastercard, PayPal, Amex, Coinbase assinando. **ACP** é
  OpenAI+Stripe. **x402** é Coinbase. **ERC-8004** é MetaMask/Ethereum
  Foundation/Google. Todo o dinheiro do mundo tá construindo os trilhos
  de pagamento agentic — e nenhum deles verifica o trabalho.
- Toda empresa que pilotar agentic payments vai bater na mesma parede:
  "como eu provo que o agente fez o trabalho antes de liberar o dinheiro?"
  — e a resposta não pode ser "humano olha cada um", senão não escala.
- O próprio desafio do hackathon foi escrito pela NeuraLake como
  **"fazer uma empresa aceitar que agentes transacionem sem um humano
  no loop"** — ou seja, o mercado está literalmente nomeando a dor.
- Analogia que o buyer entende: Pix tem MED, Visa tem chargeback,
  escrow.com existe há 25 anos — **toda rail de pagamento madura tem
  uma camada de disputa/verificação**. A rail A2A ainda não tem. É a gente.

**Quem pode dizer não:** enterprise grande pode construir internamente
(risco real — resposta: open-core + registry de reputação compartilhado,
que só faz sentido como rede, não como build interno).

---

## 7. Go-to-market

1. **Agora (hackathon):** demo viva + 6 escrows reais + vídeo narrado +
   material de banca. A meta não é o prêmio — é sair com 3 conversas de
   design partner (Cubo/Itaú na mentoria, NeuraLake como canal — eles
   precisam de trust layer pra vender A2A enterprise).
2. **Design partners (0–6 meses):** 3 pilotos com integração real —
   cobra-se pouco, exige-se feedback brutal. Sucesso = um case público.
3. **Self-serve GA (6–12 meses):** API key + docs + 100 decisões grátis.
   Dev integra em 30 min, primeira trilha vende sozinha.
4. **Network effect (12m+):** registry de reputação cruzando tenants —
   cada escrow settled melhora o score pra todos. Isso é o moat: dados
   de confiança que ninguém constrói sozinho.

**Estratégia de defesa:** open-core do verifier + registry compartilhado
+ export PROV-O/W3C — quem quiser sair leva os dados, mas perde a rede.
Padrão aberto é como a gente vira padrão.

---

## 8. O que NÃO somos (escopo honesto)

- **Não somos PSP** — não movemos dinheiro real; o escrow é
  orquestração/ledger. A ponte pra dinheiro real é x402/Stripe/PIX —
  integração, não competição.
- **Não somos marketplace de agentes** — verificamos quem transaciona em
  qualquer marketplace.
- **Não competimos com A2A/x402/AP2** — somos a camada que falta em cima
  deles. Quanto maior o volume deles, maior nosso mercado.
- **Não prometemos "juiz infalível"** — vendemos *evidência verificável* +
  processo. A disputa vai pro arbitration desk, e até ela deixa rastro.

## 9. Riscos honestos

| Risco | Resposta |
|---|---|
| "Quem garante o juiz de vocês?" | Painel cross-capability + trilha pública + BYO judge no Enterprise — o cliente pode botar o próprio modelo na bancada. |
| Passivo legal se o veredicto errar | Posicionamento: entregamos evidência, não garantia absoluta; disputa vai pro arbitration desk. Seguro E&O quando houver receita. |
| Juízes manipuláveis (Gaming the Judge) | Juiz avalia artefato, nunca o raciocínio do agente — CoT manipulado infla falso positivo em ~90%, por isso o design é o que é. |
| Concorrente (OpenAI/Stripe) faz igual | Eles fazem o rail; trust layer agnóstica de rail é neutra e portátil. E nosso moat é o registry, não o verificador. |
| Volume A2A demorar pra chegar | Camada funciona também para contratação humano→agente (mercado já existe hoje). |

---

*Próximos artefatos derivados deste plano: pricing page, one-pager de
venda pra design partner, deck de 8 slides.*
