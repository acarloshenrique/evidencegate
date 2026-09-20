# PITCH — EvidenceGate: a ameaça é bloqueada, a missão continua

Roteiro de quatro minutos. Tela principal: `/dashboard`, aba **Missão autônoma**.
Execute o cenário com injection uma vez. Números desta implementação: **11 decisões,
3 handoffs concluídos, 1 substituição, 0 intervenções após o início**.
São métricas de uma missão local determinística; não de agentes LLM distribuídos.

## 0:00–0:30 — A dor

> “Quando um agente contrata outro, uma identidade válida não garante uma entrega
> confiável. Um fornecedor pode tentar redirecionar a missão ou contornar a política.
> EvidenceGate conecta detecção de ameaças à execução: bloqueia o fornecedor suspeito
> e permite que o fluxo continue com evidências verificáveis.”

## 0:30–1:30 — A missão

Selecione **Ataque durante a triagem** e clique em **Executar missão**.

> “Defini um orçamento de 30 créditos de sandbox. O coordenador encadeia três
> especialistas: coleta, triagem e relatório. Cada entrega vira entrada da próxima,
> com contrato, identidade e hash. Daqui em diante, não escolho fornecedores,
> aprovo entregas ou intervenho nas decisões.”

Mostre as três entregas concluídas. Identifique a execução como local e os sinais
como sintéticos. Não há espera artificial para produzir efeito de tempo real.

## 1:30–2:30 — O ataque e a recuperação

Aponte os eventos **block** e **replace** na etapa **triage**.

> “O candidato mais barato contém uma instrução para ignorar a política. A checagem
> bloqueia esse cartão antes da contratação. O coordenador escolhe um fornecedor
> elegível e prossegue. O candidato bloqueado não recebe contrato nem pagamento.
> A missão termina com três entregas verificadas e 20 créditos comprometidos.”

Mostre os indicadores: 11 decisões explícitas, três handoffs concluídos, uma
substituição e zero intervenções depois do início. Abra o JSON da missão se
pedirem prova: recibo anterior, hash de entrada, hash do artefato e escrow.

## 2:30–3:15 — Eficiência e fundamento técnico

> “Essas tarefas têm critérios objetivos. Por isso, a verificação não precisa
> chamar um modelo: a rubrica fica travada antes da entrega. Para tarefas subjetivas,
> o núcleo existente tem painel de juízes. A confiança é o mecanismo que permite
> continuar a operação, com identidade e trilha criptográfica verificáveis.”

Não diga “custo total zero”: zero chamadas de inferência nessa missão não elimina
custos de infraestrutura. Não confunda eventos de log com decisões autônomas.

## 3:15–4:00 — Produto e fechamento

> “Nossa hipótese de cliente é a empresa que opera agentes contratando serviços
> externos. O valor é reduzir contratações indevidas e o trabalho de investigar cada
> incidente, sem colocar uma pessoa em toda transação. O piloto deve medir perdas
> evitadas, falsos positivos, tempo de recuperação e custo por missão concluída.”

> “EvidenceGate: a ameaça é bloqueada, a missão continua.”

## Respostas curtas para o júri

- **Isso é A2A remoto?** Não nesta entrega: são executores locais especializados,
  com identidades e handoffs rastreados. Transporte remoto e conformidade com o
  protocolo A2A são o próximo passo; não estão sendo simulados nos números.
- **São onze raciocínios de LLM?** Não. São onze escolhas explícitas do workflow,
  regidas por política. O contador não mede raciocínio interno.
- **O ataque é real?** É uma entrada maliciosa controlada em um cenário sintético.
  A checagem, o bloqueio e o fluxo alternativo são executados pelo código.
- **Qualquer injection é detectada?** Não. O filtro atual usa padrões e tem limites.
- **A verba foi transferida?** Apenas lançamentos no ledger de sandbox.
- **E se a entrega for inválida?** O escrow fica retido e as etapas seguintes não
  executam; os testes cobrem esse caminho.
- **E se o processo cair?** A chave não repete efeitos. A missão interrompida exige
  inspeção; recuperação automática por checkpoints ainda não está implementada.
- **Por que não cem decisões?** Porque preferimos mostrar os onze pontos de decisão
  desta missão e seus recibos. Repetir uma demo aumenta volume, não profundidade.

## Plano de palco

1. Banco de sandbox, um worker, demo habilitada e build atualizado.
2. Teste a missão antes da apresentação; deixe a aba e os quatro indicadores prontos.
3. Use voz só depois de ensaiar com microfone, Agora e NeuraLake reais. Sem microfone,
   use texto; sem inferência configurada, apresente o relatório e os recibos da missão.
4. Se perguntarem sobre os pesos do júri, confira o regulamento oficial antes de
   citar percentuais. Este roteiro prioriza autonomia observável e execução verificável.
