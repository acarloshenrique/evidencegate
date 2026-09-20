"""Explainability — every action explained FROM DATA, never by an LLM.

Deterministic templates: same event -> same explanation. The rationale a
model produced (orchestrator.evaluate) is labeled model-generated and shown
next to the data the decision can be independently checked against.
"""
from __future__ import annotations

from typing import Any


def _votes_str(votes: list[dict[str, Any]]) -> str:
    return ", ".join(
        f"{v['judge']}={v['vote']} conf={v['confidence']}" for v in votes)


def explain_event(ev: dict[str, Any]) -> dict[str, Any]:
    """Return {summary, why, refs} grounded in the event payload."""
    p = ev.get("payload") or {}
    a = ev.get("action", "")
    refs: dict[str, Any] = {}

    if a == "principal.registered":
        summary = f"principal '{p.get('legal_name')}' registrado"
        why = ("Gate de KYC: toda acao de agente precisa responder a um "
               "principal juridico. O documento e guardado como hash "
               f"({p.get('doc_hash', '')[:16]}...), nunca em claro.")
    elif a == "agent.registered":
        summary = f"agente {p.get('did', '')[:24]}... registrado"
        why = ("DID proprio com chave custodiada e AgentCard assinado. "
               "Reputacao inicial teto 5.0 — cap anti-sybil: um agente novo "
               "nao pode comprar confianca.")
    elif a == "agent.card_invalid":
        summary = f"card de {p.get('did', '')[:24]}... invalido"
        why = ("Assinatura Ed25519 ou canonicalizacao falhou. O sistema "
               "nunca confia em texto livre: sem assinatura valida, o card "
               "nao vale nada.")
    elif a == "agent.injection_flagged":
        summary = f"prompt injection em {p.get('did', '')[:24]}... sanitizado"
        why = ("O card continha instrucoes escondidas tentando manipular "
               "juizes/compradores. A injecao foi removida do card servido e "
               "o agente ficou flaggeado — flag desce a confianca no "
               "discovery sem precisar banir.")
    elif a == "agent.reputation":
        refs = {"delta": p.get("delta"), "reason": p.get("reason"),
                "escrow_id": p.get("escrow_id")}
        summary = f"reputacao de {p.get('did', '')[:24]}... {p.get('delta'):+}"
        why = ("Reputacao so muda com outcome VERIFICADO "
               f"('{p.get('reason')}'). Review sem verificacao nao pontua — "
               "impossivel inflar nota trocando elogios entre sybils.")
    elif a == "agent.revoked":
        summary = f"agente {p.get('did', '')[:24]}... revogado"
        why = f"Motivo: {p.get('reason')}. DID morto — nao assina mais nada."
    elif a == "quote.created":
        refs = {"quote_id": p.get("quote_id"),
                "quote_hash": p.get("quote_hash"), "price": p.get("price")}
        summary = f"quote {p.get('quote_id')} assinada (${p.get('price')})"
        why = ("A rubrica de aceite ficou TRAVADA em quote_hash "
               f"{p.get('quote_hash', '')[:16]}... ANTES do trabalho "
               "comecar. O seller assinou Ed25519 — ninguem pode mover a "
               "trave depois de entregar.")
    elif a == "policy.denied":
        refs = {"quote_id": p.get("quote_id"), "reason": p.get("reason"),
                "escalate": p.get("escalate")}
        summary = f"policy negou pagamento: {p.get('reason')}"
        why = ("O policy engine roda em CODIGO, fora do LLM, ANTES de "
               "travar dinheiro. A recusa nao e opiniao de modelo — e regra "
               "deterministica. " +
               ("Escala para humano." if p.get("escalate")
                else "Sem escalacao."))
    elif a == "escrow.funded":
        refs = {"escrow_id": p.get("escrow_id"), "amount": p.get("amount")}
        summary = f"escrow {p.get('escrow_id')} fundado (${p.get('amount')})"
        why = ("Fundos travados em escrow NEUTRO depois da policy passar. "
               "O comprador nao paga o seller direto — paga o contrato. "
               "O dinheiro so se move por veredicto verificavel.")
    elif a == "escrow.delivered":
        refs = {"escrow_id": p.get("escrow_id"),
                "evidence_hash": p.get("evidence_hash")}
        summary = f"evidencia entregue em {p.get('escrow_id')}"
        why = (f"O que os juizes avaliam e o ARTEFATO (hash "
               f"{p.get('evidence_hash', '')[:16]}...), nao a promessa. "
               "Entrega sem evidencia nao chega na banca.")
    elif a == "verify.panel":
        votes = (p.get("votes") or
                 [{"judge": j, "vote": "?", "confidence": "?"}
                  for j in p.get("judges", [])])
        refs = {"verdict": p.get("verdict"), "votes": votes,
                "approvals": p.get("approvals"),
                "avg_confidence": p.get("avg_confidence")}
        summary = (f"painel: {p.get('verdict')} "
                   f"({p.get('approvals')}/3, conf media "
                   f"{p.get('avg_confidence', 0):.2f})")
        why = ("Quorum 2-de-3 com commit-reveal: cada juiz vota sem ver o "
               f"voto dos outros ({_votes_str(votes)}). Juiz que falhou "
               "vira reject com conf 0 — fail-closed, a banca decide mesmo "
               "com um juiz caido. " +
               ("Escala para humano por baixa confianca."
                if p.get("escalate_to_human") else ""))
    elif a == "escrow.verified":
        refs = {"escrow_id": p.get("escrow_id"), "panel": p.get("panel")}
        summary = f"{p.get('escrow_id')} verificado"
        why = ("Stage A (deterministico, custo zero) barrou falhas "
               "objetivas antes de gastar inferencia; o painel avaliou o "
               "subjetivo. Duas camadas = barato E rigoroso.")
    elif a == "escrow.released":
        refs = {"escrow_id": p.get("escrow_id"), "amount": p.get("amount")}
        summary = f"${p.get('amount')} liberados de {p.get('escrow_id')}"
        why = ("Liquidacao atomica no ledger interno: o dinheiro so sai "
               "porque o quorum aprovou com evidencia conferida. Zero "
               "humano no caminho do settlement.")
    elif a in ("escrow.rejected", "escrow.retained"):
        refs = {"escrow_id": p.get("escrow_id"),
                "failures": p.get("failures")}
        fails = p.get("failures") or []
        summary = f"{p.get('escrow_id')} retido"
        why = ("Stage A falhou deterministicamente: " +
               ("; ".join(fails) if fails else "evidencia nao atendeu.") +
               " O dinheiro fica travado — o comprador nao paga trabalho "
               "ruim por descuido.")
    elif a == "escrow.disputed":
        refs = {"escrow_id": p.get("escrow_id"), "reason": p.get("reason")}
        summary = f"{p.get('escrow_id')} em disputa"
        why = (f"Motivo: {p.get('reason')}. O humano entra pela EXCECAO, "
               "nao pelo caminho — e a excecao tambem fica na trilha.")
    elif a in ("escrow.arbitrated", "escrow.resolved"):
        refs = {"escrow_id": p.get("escrow_id"), "ruling": p.get("ruling")}
        summary = f"{p.get('escrow_id')} arbitrado: {p.get('ruling')}"
        why = ("Arbitro humano decidiu com a trilha inteira na mesa "
               "(votos, rubrica, hashes). A decisao e registrada como "
               "evento — ate a excecao e auditavel.")
    elif a == "escrow.refunded":
        refs = {"escrow_id": p.get("escrow_id"), "amount": p.get("amount")}
        summary = f"${p.get('amount')} devolvidos de {p.get('escrow_id')}"
        why = ("Reembolso apos rejeicao/disputa: o dinheiro volta ao "
               "comprador, nunca some.")
    elif a == "orchestrator.discover":
        flagged = p.get("flagged") or []
        refs = {"capability": p.get("capability"),
                "candidates": p.get("candidates"), "flagged": flagged}
        summary = (f"discovery '{p.get('capability')}': "
                   f"{len(p.get('candidates') or [])} candidatos")
        why = ("So entram cards com assinatura verificada e conteudo "
               "sanitizado. " +
               (f"{len(flagged)} flaggeado(s) por injection — visiveis, "
                "nao escondidos." if flagged else "Nenhum flaggeado."))
    elif a == "orchestrator.evaluate":
        scores = p.get("scores") or {}
        refs = {"chosen": p.get("chosen"), "scores": scores,
                "rationale_model": p.get("rationale")}
        summary = f"contratado {p.get('chosen', '')[:24]}..."
        why = ("O rationale e prosa do MODELO — pode errar. O que garante "
               "e que os scores de TODOS os candidatos estao neste payload "
               f"{dict(list(scores.items())[:3])} — a escolha e conferivel "
               "contra os dados, nao contra a confianca do texto.")
    else:
        summary = a or "evento"
        why = "Evento da trilha hash-chained — seq e hash permitem "
        "reprovar a ordem e detectar adulteracao."
        refs = p

    return {"summary": summary, "why": why.strip(), "refs": refs,
            "explainer": "deterministic-template"}


def explain_chain(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**ev, **explain_event(ev)} for ev in events]
