# EvidenceGate - ambiente local

Base de desenvolvimento para o MVP proposto no relatório do hackathon. Esta preparação inclui apenas infraestrutura e verificação do ambiente; agentes, política de aceite e razão de créditos ainda serão implementados.

## Iniciar

Abra PowerShell nesta pasta e execute, sem precisar ativar o virtualenv:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- Saúde: http://127.0.0.1:8000/health
- Documentação interativa: http://127.0.0.1:8000/docs
- Parar: Ctrl+C.

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
