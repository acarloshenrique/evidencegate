"""Smoke check offline de bibliotecas e integracoes locais, sem consumir creditos."""

import asyncio
import importlib
import io
import json
import sqlite3
import sys
from importlib.metadata import version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    packages = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "pydantic": "pydantic",
        "pydantic-settings": "pydantic_settings",
        "openai": "openai",
        "httpx": "httpx",
        "pypdf": "pypdf",
        "reportlab": "reportlab",
        "jinja2": "jinja2",
        "python-multipart": "python_multipart",
        "structlog": "structlog",
        "tenacity": "tenacity",
        "pytest": "pytest",
        "pytest-asyncio": "pytest_asyncio",
    }
    for dist, module in packages.items():
        importlib.import_module(module)
        print(f"OK {dist} {version(dist)}")

    from httpx import ASGITransport, AsyncClient, Client, MockTransport, Request, Response
    from openai import OpenAI
    from pypdf import PdfReader
    from reportlab.pdfgen.canvas import Canvas

    from app.main import app

    async def check_api() -> None:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            result = await client.get("/health")
            assert result.status_code == 200
            assert result.json()["status"] == "ok"
            assert (await client.get("/openapi.json")).status_code == 200

    asyncio.run(check_api())
    print("OK FastAPI: health e OpenAPI")

    with sqlite3.connect(":memory:") as db:
        db.execute("CREATE TABLE events (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        db.execute("INSERT INTO events VALUES (?, ?)", ("smoke", json.dumps({"status": "ok"})))
        assert db.execute("SELECT count(*) FROM events").fetchone()[0] == 1
    print(f"OK SQLite {sqlite3.sqlite_version}: gravacao e leitura")

    output = io.BytesIO()
    pdf = Canvas(output)
    pdf.drawString(72, 750, "EvidenceGate environment check")
    pdf.save()
    output.seek(0)
    assert "EvidenceGate" in PdfReader(output).pages[0].extract_text()
    print("OK PDF: geracao e extracao em memoria")

    def mock_provider(request: Request) -> Response:
        assert request.url.path == "/v1/chat/completions"
        assert json.loads(request.content)["model"] == "auto"
        return Response(
            200,
            json={
                "id": "offline-check",
                "object": "chat.completion",
                "created": 0,
                "model": "auto",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    with OpenAI(
        api_key="offline-test-not-a-real-key",
        base_url="https://api.neuralake.cloud/v1",
        http_client=Client(transport=MockTransport(mock_provider)),
    ) as client:
        response = client.chat.completions.create(
            model="auto", messages=[{"role": "user", "content": "check"}]
        )
        assert response.choices[0].message.content == "ok"
    print("OK cliente de inferencia: transporte simulado; nenhuma chamada real")
    print("AMBIENTE VALIDADO. A API real ainda depende de credencial e teste autenticado.")


if __name__ == "__main__":
    main()
