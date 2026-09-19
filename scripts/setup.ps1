$ErrorActionPreference = 'Stop'
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    $env:UV_CACHE_DIR = Join-Path (Get-Location) '.uv-cache'
    uv sync --locked --link-mode copy
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao sincronizar dependencias.' }
    & '.\.venv\Scripts\python.exe' 'scripts\verify_environment.py'
    if ($LASTEXITCODE -ne 0) { throw 'Falha na verificacao do ambiente.' }
} finally {
    Pop-Location
}
