"""Popula o banco da API com casos de demonstração para o dashboard (T010).

Roda offline, com um juiz falso e determinístico — nenhum crédito da NeuraLake
é gasto, e por isso o custo de inferência aparece como zero no painel. Para ver
custo real, rode a verificação com `live=true` contra a NeuraLake de verdade.

Uso:
    .venv/Scripts/python.exe scripts/seed_dashboard.py [--db data/evidencegate.db]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TOKENS = {"reasoning": (1180, 240), "reasoning-pro": (1180, 310), "code": (1180, 190)}


class FakeNL:
    """Juiz determinístico: aprova o artefato bom, rejeita o fraudulento."""

    def __init__(self):
        self.calls: list[dict] = []
        self.total_cost = 0.0
        self.good_evidence = True

    def complete(self, messages, model="auto", **kw):
        prompt_tokens, completion_tokens = TOKENS.get(model, (900, 200))
        call = {"model_requested": model, "model_used": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens, "cost": 0.0}
        self.calls.append(call)
        verdict = {"vote": "approve" if self.good_evidence else "reject",
                   "confidence": 0.91 if self.good_evidence else 0.83,
                   "rationale": ("artefato atende a rubrica travada no quote"
                                 if self.good_evidence else
                                 "numeros da evidencia nao batem com a fonte citada"),
                   "failed_criteria": [] if self.good_evidence else ["sources"]}
        return {"content": json.dumps(verdict), **call}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/evidencegate.db")
    args = ap.parse_args()

    import os

    os.environ["EG_DB_PATH"] = args.db
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)

    from fastapi.testclient import TestClient

    from app.main import create_app

    nl = FakeNL()
    with TestClient(create_app(nl=nl)) as c:
        pid = c.post("/principals", json={
            "legal_name": "Meridian Holdings SA",
            "doc_id": "12.345.678/0001-90"}).json()["principal_id"]

        def agent(desc: str, caps: list[str]) -> str:
            return c.post("/agents", json={
                "principal_id": pid, "card": {"description": desc},
                "manifest": {"capabilities": caps,
                             "fuses": {"max_tx_value": 50}}}).json()["agent_did"]

        buyer = agent("agente comprador de pesquisa", ["research"])
        seller = agent("agente analista de mercado", ["research", "report"])
        fraudster = agent("agente vendedor low-cost", ["research"])

        def quote(sell: str, scope: str, criteria: dict, price: float) -> str:
            return c.post("/quotes", json={
                "buyer_did": buyer, "seller_did": sell, "scope": scope,
                "criteria": criteria, "price": price}).json()["quote_id"]

        def fund(qid: str, key: str) -> str:
            return c.post("/escrow", json={
                "quote_id": qid, "buyer_did": buyer,
                "idempotency_key": key}).json()["escrow_id"]

        # 1) caminho feliz — painel 3 juízes aprova, escrow libera
        q1 = quote(seller, "relatorio de mercado: adocao de A2A no setor bancario",
                   {"required_fields": ["report", "sources"],
                    "min_length": {"report": 200}}, 20.0)
        e1 = fund(q1, "seed-1")
        c.post(f"/escrow/{e1}/deliver", json={
            "seller_did": seller,
            "evidence": {"report": "Panorama de adocao do protocolo A2A. " * 12,
                         "sources": ["a2a-protocol.org", "bis.org/publ"],
                         "tests_passed": True}})
        c.post(f"/escrow/{e1}/verify", json={"live": True})

        # 2) fraude — stage A barra antes de gastar juiz, disputa resolve pro buyer
        q2 = quote(fraudster, "sumario de risco de contraparte",
                   {"required_fields": ["report", "sources"],
                    "min_length": {"report": 300}}, 15.0)
        e2 = fund(q2, "seed-2")
        c.post(f"/escrow/{e2}/deliver", json={
            "seller_did": fraudster, "evidence": {"report": "resumo curto"}})
        c.post(f"/escrow/{e2}/verify", json={"live": True})
        c.post(f"/escrow/{e2}/dispute", json={
            "opener_did": fraudster, "reason": "criterio de aceite subjetivo demais"})
        c.post(f"/escrow/{e2}/arbitrate", json={
            "ruling": "buyer", "rationale": "rubrica travada no quote nao foi atendida"})

        # 3) painel divergente — juiz de codigo rejeita, maioria 2-de-3 libera
        q3 = quote(seller, "auditoria de dependencias do pipeline de dados",
                   {"required_fields": ["report"], "min_length": {"report": 120}}, 30.0)
        e3 = fund(q3, "seed-3")
        c.post(f"/escrow/{e3}/deliver", json={
            "seller_did": seller,
            "evidence": {"report": "Auditoria das 42 dependencias diretas. " * 8,
                         "tests_passed": True}})
        c.post(f"/escrow/{e3}/verify", json={"live": True})

        # 4) caso em aberto — financiado, aguardando entrega
        q4 = quote(seller, "benchmark de custo por decisao entre provedores",
                   {"required_fields": ["report"], "min_length": {"report": 150}}, 12.0)
        e4 = fund(q4, "seed-4")

        chain = c.get("/audit/verify").json()

    print(f"escrows: {e1} (feliz), {e2} (fraude), {e3} (painel), {e4} (aberto)")
    print(f"chamadas de juiz simuladas: {len(nl.calls)} · cadeia ok: {chain['ok']}")
    print(f"banco: {args.db} — abra http://127.0.0.1:8000/dashboard/")


if __name__ == "__main__":
    main()
