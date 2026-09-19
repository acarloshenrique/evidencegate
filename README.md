# EvidenceGate - ambiente local

Base de desenvolvimento para o MVP proposto no relatório do hackathon. Esta preparação inclui apenas infraestrutura e verificação do ambiente; agentes, política de aceite e razão de créditos ainda serão implementados.

## Iniciar

Abra PowerShell nesta pasta e execute, sem precisar ativar o virtualenv:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- Saúde: http://127.0.0.1:8000/health
- Documentação interativa: http://127.0.0.1:8000/docs
- Painel de auditoria: http://127.0.0.1:8000/dashboard/
- Parar: Ctrl+C.

## Dashboard (T010)

O painel ao vivo fica em `web/` (React 19 + Vite + Tailwind 4 + shadcn/ui) e consome os
endpoints `/metrics`, `/escrows`, `/escrow/{id}`, `/audit` e `/agents`. Ele é só leitura:
mostra ledger, trilha hash-encadeada, votos do painel de juízes e custo por decisão.

```powershell
cd web
npm install
npm run build      # gera web/dist — o backend passa a servir /dashboard/
npm run dev        # alternativa: dev server em :5173 com proxy pra API em :8000
```

Sem `web/dist`, `/dashboard` cai no painel single-file legado (também disponível em
`/dashboard/legacy`). Para popular o banco com casos de demonstração sem gastar crédito
de inferência:

```powershell
.\.venv\Scripts\python.exe scripts\seed_dashboard.py
```

### Testar a conexão do front com a API

Dois modos de execução:

1. **Mesma origem (modo demo)** — o uvicorn serve o build e a API na mesma porta, sem CORS
   no caminho. `npm run build` e abra http://127.0.0.1:8000/dashboard/.
2. **Dev com hot reload** — dois terminais: uvicorn em :8000 e `npm run dev` em :5173. O Vite
   faz proxy de `/metrics`, `/escrows`, `/escrow`, `/audit`, `/agents`, `/health` e `/report`
   (ver `web/vite.config.ts`). API em outra porta: defina `$env:EG_API_URL` antes do `npm run dev`.

O próprio painel indica o estado da conexão no canto superior direito: `LIVE · 1.5s` quando
o polling responde, `BACKEND OFFLINE` quando os fetches falham. Conferindo por fora:

```powershell
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/metrics     # chain.ok, custo de inferência, chamadas
curl http://127.0.0.1:8000/escrows     # vazio significa banco sem casos, não falha de conexão
```

Painel vazio com badge verde = API no ar e banco sem dados; rode o seed. Gráfico de custo
vazio é esperado offline — ele só enche com verificação `live=true` (juízes reais).

### Criar uma linha no painel pela API

Cada linha da tabela é um escrow, e escrow nasce de um quote. Fluxo mínimo:
`POST /principals` → `POST /agents` (comprador e vendedor) → `POST /quotes` → `POST /escrow`.

```powershell
$api = 'http://127.0.0.1:8000'
$p = Invoke-RestMethod "$api/principals" -Method Post -ContentType application/json `
     -Body '{"legal_name":"Meridian SA","doc_id":"12.345.678/0001-90"}'

function New-Agent($desc) {
  $body = @{ principal_id = $p.principal_id; card = @{ description = $desc }
             manifest = @{ capabilities = @('research'); fuses = @{ max_tx_value = 50 } } } |
          ConvertTo-Json -Depth 5
  (Invoke-RestMethod "$api/agents" -Method Post -ContentType application/json -Body $body).agent_did
}
$buyer  = New-Agent 'agente comprador'
$seller = New-Agent 'agente vendedor'

$q = Invoke-RestMethod "$api/quotes" -Method Post -ContentType application/json -Body (@{
  buyer_did = $buyer; seller_did = $seller; price = 20.0
  scope = 'relatorio de mercado'
  criteria = @{ required_fields = @('report'); min_length = @{ report = 100 } } } | ConvertTo-Json -Depth 5)

$e = Invoke-RestMethod "$api/escrow" -Method Post -ContentType application/json -Body (@{
  quote_id = $q.quote_id; buyer_did = $buyer; idempotency_key = "k-$(Get-Random)" } | ConvertTo-Json)
$e.escrow_id    # a linha já aparece em /dashboard/ como FUNDED
```

Avançando o caso:

```powershell
Invoke-RestMethod "$api/escrow/$($e.escrow_id)/deliver" -Method Post -ContentType application/json -Body (@{
  seller_did = $seller
  evidence = @{ report = ('conteudo do relatorio ' * 20); tests_passed = $true } } | ConvertTo-Json -Depth 5)

Invoke-RestMethod "$api/escrow/$($e.escrow_id)/verify" -Method Post -ContentType application/json -Body '{"live":false}'
```

Detalhes que mordem:

- `live:false` roda só o stage A determinístico; se passar, o caso para em `pending_panel` sem
  votos. `live:true` chama os três juízes e exige `NEURALAKE_API_KEY` no `.env` (503 sem ela).
- `price` acima de `EG_MAX_TX` (default 50) é barrado pela policy antes de travar fundos:
  HTTP 400 e evento `policy.denied` na trilha.
- `idempotency_key` repetida devolve o mesmo escrow — não cria linha nova.
- `/escrow/{id}/dispute` e `/escrow/{id}/arbitrate` levam o caso pelo caminho de disputa.
- `/docs` expõe todos esses endpoints com formulário interativo.

## Dependências e reprodução

Python 3.12; dependências declaradas em `pyproject.toml` e versões exatas em `uv.lock`. O ambiente `.venv` é exclusivo deste projeto. Usamos instalação por cópia para evitar dependência de hardlinks no OneDrive.

```powershell
$env:UV_CACHE_DIR = Join-Path (Get-Location) '.uv-cache'
uv sync --locked --link-mode copy
.\.venv\Scripts\python.exe scripts\verify_environment.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
```

Os scripts `scripts/setup.ps1` e `scripts/start.ps1` oferecem os mesmos atalhos quando a política local permite scripts. Não é necessário mudar a política de execução do Windows: os comandos diretos acima funcionam sem ativação.

Bibliotecas: FastAPI/Uvicorn (API); Pydantic/Settings (validação e configuração); OpenAI/HTTPX (cliente compatível com NeuraLake); pypdf/ReportLab (documentos); Jinja2/python-multipart (interface e uploads); structlog/tenacity (logs e retries); pytest/pytest-asyncio/Ruff (verificação). SQLite vem com o Python. A interface mínima pode ser servida pelo próprio backend; npm e navegador automatizado não são necessários para esta base.

## NeuraLake

Copie `.env.example` para `.env` e preencha a chave localmente quando for integrar o produto. A base atual não carrega nem usa essa chave. Não envie segredos por chat ou commit. O smoke check usa um transporte HTTP simulado e não consome créditos; disponibilidade da API, credencial, roteamento e Cross Memory ainda precisam de teste real.

Docker não é necessário para executar este ambiente local. A imagem de implantação será definida junto com a implementação do MVP.

## Referências

- [Ambientes isolados com uv](https://docs.astral.sh/uv/pip/environments/)
- [Lock e sincronização com uv](https://docs.astral.sh/uv/reference/cli/)
- [FastAPI](https://fastapi.tiangolo.com/)
