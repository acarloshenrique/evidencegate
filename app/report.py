"""Compliance report — the artifact a bank's compliance officer reads.

Every decision: who acted, which model, why, at what cost — re-derivable from
the hash-chained trail, exportable as markdown/JSON (NIST AI RMF-mappable).
"""

from typing import Any

from .audit import AuditTrail
from .explain import explain_event


def compliance_report(audit: AuditTrail, escrow_id: str) -> dict[str, Any]:
    events = audit.for_escrow(escrow_id)
    lines = [
        f"# Compliance Report — escrow {escrow_id}",
        "",
        "| seq | ts | actor | acao | por que |",
        "|---|---|---|---|---|",
    ]
    for e in events:
        ex = explain_event(e)
        e["explanation"] = ex
        why = (ex["summary"] + " — " + ex["why"]).replace("|", "/")
        lines.append(f"| {e['seq']} | {e['ts']:.0f} | {e['actor_did'][:24]} | "
                     f"{e['action']} | {why[:200]} |")
    chain = audit.verify_chain()
    integ = ("SIM" if chain["ok"]
             else "NAO — adulterada em seq " + str(chain.get("tampered_seq")))
    tail = (f"**Eventos:** {len(events)} · **Event hash head:** "
            f"`{events[-1]['event_hash'][:16]}...`" if events else "")
    lines += ["", f"**Trilha íntegra:** {integ}", tail]
    return {"markdown": "\n".join(x for x in lines if x is not None),
            "events": events, "chain_ok": chain["ok"]}
