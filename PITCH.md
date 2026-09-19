# PITCH — EvidenceGate (4 min, mapeado nos critérios)

Critérios do júri: Autonomia A2A 30% · Funciona de verdade 25% · Eficiência 15% · Valor de negócio 15% · Pitch 10% · Confiança 5%

Tela durante todo o pitch: **dashboard ao vivo** (`/dashboard`) mostrando escrows, trilha hash-chained e custo de inferência acumulado.

---

## (0:00–0:30) A pergunta que abre — hook + problema

> "Ano que vem, agentes de IA vão contratar e pagar outros agentes sem humano no loop. Já existe protocolo pra eles se acharem — A2A. Já existe pra se pagarem — x402, AP2. Mas responde essa: **quando um agente paga outro agente, quem confere se o trabalho presta?** Ninguém. Settlement é final, sem chargeback. É exatamente esse o buraco que a gente tapa."

Frase-âncora (repetir no fecho): **"Fé pública programável pra economia de agentes."**

## (0:30–1:30) Fluxo feliz AO VIVO (funciona de verdade 25% + autonomia 30%)

Rodar `demo.py --live` (ou replay gravado como backup). Narrar em cima do dashboard:

> "Um CEO-agent com orçamento contrata sozinho: **descobre** candidatos no registry — reparem, o de reputação inflada tá marcado INJECTION FLAGGED, o AgentCard dele tinha prompt injection escondido e foi barrado antes da avaliação. Ele **escolhe**, fecha **quote com rubrica travada** — critérios de aceite viram hash, ninguém move a trave depois. Escrow **funded**. Vendedor **entrega** — o artefato passa pelo stage A, checagem determinística grátis. Aí o **painel de juízes**: três modelos diferentes da NeuraLake votando em segredo — commit-reveal — maioria 2-de-3. Aprovaram. **Escrow released**, reputação do vendedor sobe. Zero humano depois do orçamento."

Apontar pro contador de custo: **"Tudo isso por um centavo de inferência."**

## (1:30–2:40) O ATAQUE (o teatro + a substância)

> "Agora o que interessa pro banco. Segunda transação: o entregável é lixo. Stage A já barra de graça — e mesmo assim os três juízes rejeitam. Escrow **retido**. Buyer abre **disputa** — o tribunal arbitra, ruling pro buyer, **reembolso automático**, reputação do vendedor despenca. E olha a trilha: cada evento é encadeado por hash — eu adultero um caractere de um evento antigo…" *(tamper test ao vivo)* "…`verify_chain` aponta exatamente onde. Isso é compliance report que auditor lê, não log que operador finge."

Frase de impacto: **"O juiz julga o artefato, nunca o raciocínio do agente — porque CoT manipulado infla falso positivo em 90%."**

## (2:40–3:20) Por que isso é empresa, não feature (valor de negócio 15%)

> "ERC-8004 já separou identity / reputation / validation em três registries — a gente implementou os três localmente, pluggable pra on-chain depois. A pergunta 'esse agente tinha autorização, naquele escopo?' é o que banco, seguradora e compliance vão exigir antes de deixar agente mover dinheiro. A gente é a camada que responde isso com prova criptográfica — não com log."

## (3:20–4:00) NeuraLake + fecho (eficiência 15% + pitch 10%)

> "Tudo roda na NeuraLake: o orquestrador usa `auto` — o router escolhe a capability mais barata por request. Os juízes são `reasoning-pro` e `code` — cross-model de verdade. E o auditor compartilha **case state** entre juízes em vez de reenviar histórico — é a lógica do Cross Memory aplicada ao domínio: menos token, mais contexto. Quando agentes pagam agentes, quem confere o trabalho? **EvidenceGate. Fé pública programável.**"

---

## Perguntas prováveis do júri (resposta de 1 frase cada)

- **"E se o juiz errar/cair?"** → Fail-closed: juiz que não verifica nunca aprova; 2-de-3 tolera 1 caído — nosso live run provou isso na prática (um juiz 504'd e o painel decidiu mesmo assim).
- **"Juiz LLM decidindo dinheiro não é frágil?"** → Por isso two-stage: determinístico decide o objetivável; juiz só vê o subjetivo, com rubrica travada antes do trabalho.
- **"E sybil / reputação inflada?"** → Reputação só muda com outcome settled — review não verificado não move score; identidade é Ed25519 atada a principal KYC.
- **"Por que não on-chain?"** → A camada de verificação é o problema; settlement pluga em x402/AP2/Base depois — registry já é compatível com ERC-8004.
- **"Cross Memory?"** → Estado do caso compartilhado entre juízes sem reenviar histórico — medimos custo/decisão ao vivo no dashboard.

## Regras de palco

- Demo live primeiro; se a NeuraLake cair, roda `demo.py` offline (fake determinístico) e mostra a trilha — nunca travar a apresentação esperando rede.
- Se apertar tempo: corta a seção 2.40, NUNCA corta o ataque nem o tamper test.
