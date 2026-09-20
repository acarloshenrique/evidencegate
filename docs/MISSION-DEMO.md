# Missão de inteligência de ameaças

## O que esta entrega demonstra

Um coordenador executa três contratos dependentes: coleta de sinais, triagem e
relatório. Na triagem, um fornecedor mais barato apresenta injection no AgentCard.
O coordenador bloqueia esse candidato, seleciona outro e conclui a missão sem
intervenção depois do comando inicial.

Execução: agentes determinísticos locais, com identidades distintas e funções
especializadas, no mesmo processo. Os indicadores são sintéticos, sob `.invalid`.
Não há transporte A2A remoto, inferência ou movimentação financeira real nessa missão.
O ledger é o sandbox existente. Isso é uma demonstração verificável de orquestração,
não uma alegação de autonomia cognitiva ou conformidade com o protocolo A2A.

## Rodar

Na raiz do repositório, instale `uv sync --frozen`. Em `web/`, rode `npm ci` e
`npm run build`. Depois, no PowerShell, na raiz:

```powershell
$env:EG_ENABLE_MISSION_DEMO = '1'
$env:EG_DB_PATH = 'data/mission-demo.db'
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Abra `/dashboard`, selecione **Ataque durante a triagem**, clique em **Executar
missão** uma vez e mantenha os quatro indicadores em tela. Um novo clique depois
da conclusão cria outra missão; uma repetição de rede reutiliza a mesma chave.

Via API:

```http
POST /missions/run
Content-Type: application/json

{"idempotency_key":"pitch-mission-001","budget":30,"scenario":"injection"}
```

`GET /missions` lista execuções. `GET /missions/{id}` retorna estado, resultado,
eventos, hashes e métricas. `GET /metrics` contém `mission_autonomy` agregado.
`scenario=clean` executa sem fornecedor malicioso; orçamento abaixo de 20 interrompe
antes de qualquer funding. `/missions/run` retorna 403 sem a habilitação explícita.

## Evidência esperada por execução com ataque

| Indicador | Resultado | Regra de contagem |
|---|---:|---|
| Decisões | 11 | Um plano, três seleções, três autorizações, três aceitações e um bloqueio |
| Handoffs concluídos | 3 | Entrega recebida, validada e liquidada; despacho sozinho não conta |
| Substituições | 1 | Candidato bloqueado substituído por elegível na mesma etapa |
| Intervenções após início | 0 | Nenhum evento humano dentro da missão |
| Escrows liberados | 3 | Um por entrega válida |
| Créditos comprometidos | 20 / 30 | Preços fixados: 5 + 8 + 7 |
| Chamadas de inferência da missão | 0 | Nenhum modelo invocado; não implica infraestrutura gratuita |

O início é um comando humano. Os contadores se referem às decisões posteriores,
não à ausência de qualquer humano em toda a operação. O contador anterior
`autonomy.decisions` continua por compatibilidade e agora é identificado como
`legacy_audit_actions`; a interface o chama de ações automáticas na trilha.

Cada handoff contém `input_hash`, `artifact_hash`, DIDs de origem/destino e escrow.
A próxima etapa valida o recibo anterior contra o artefato persistido. Os critérios
objetivos são travados no quote antes da execução. Somente esses três contratos
determinísticos podem ser liquidados por essa verificação objetiva; o fluxo
subjetivo existente continua exigindo o painel.

## Falhas e limites operacionais

- Chave idempotente com outra configuração: 409. Chave repetida: mesma execução,
  sem eventos ou funding adicionais, inclusive após reinício.
- Entrega inválida: pagamento retido, missão interrompida; nenhuma etapa seguinte.
- Trilha adulterada, falta de orçamento ou política negada: interromper.
- Queda do processo no meio da missão: a execução permanece RUNNING para inspeção;
  não se repetem efeitos automaticamente. Recuperação por checkpoints é trabalho futuro.
- Usar um worker e banco de sandbox dedicado. Escritas HTTP são serializadas;
  coordenação entre processos e isolamento multi-tenant não fazem parte desta demo.
- Detecção de injection por padrões é um controle limitado, não detecção universal.
  Assinatura válida identifica o emissor; não prova que seu texto seja seguro.
- Os executores locais são síncronos, finitos e sem I/O externo. Substituir por
  workers remotos exige timeout, autenticação de transporte e recibos assinados.

## Voz e fallback

`/voice` solicita `getUserMedia`, enumera `audioinput` e só então cria um canal.
Usa o `MediaStreamTrack` aberto, sem persistir IDs de dispositivo. Permissão negada,
microfone ausente, desconexão ou timeout oferecem **Tentar novamente** e **Usar modo
texto**. O texto consome o SSE existente de `/chat/completions`; necessita do serviço
NeuraLake configurado, mas independe do microfone e do SDK Agora. A SDK carrega de
forma assíncrona para não bloquear o texto.

Tracks e clientes são encerrados em falhas. Recursos que chegam depois do timeout
são descartados; um start remoto tardio recebe stop. Se o stop de um agente conhecido
não for confirmado, novo start é bloqueado até a confirmação. Uma queda de rede sem
resposta de start ainda exige expiração/limpeza pelo servidor Agora.

Referência: [Agora createCustomAudioTrack](https://agoraio-extensions.github.io/agora-rtc-react/api-ref/interfaces/IAgoraRTC.html#createCustomAudioTrack).

## Validação

```powershell
uv run pytest -q
uv run ruff check .
node --test --test-isolation=none tests/voice.test.mjs
```

No diretório `web/`: `npm run build` e `npm run lint`.
Testes de voz usam dublês de dispositivos e SDK; não substituem ensaio com microfone,
rede WebRTC, servidor Agora e NeuraLake reais antes da apresentação.
