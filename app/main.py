"""Endpoint local para verificar o ambiente; o fluxo de negocio ainda sera implementado."""

from fastapi import FastAPI

app = FastAPI(title="EvidenceGate", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "evidencegate", "stage": "environment-ready"}
