"""Tamper demo — safe: corrupts a COPY of the db, verify_chain points at it.

Run on the server:  python3 scripts/tamper_demo.py
It copies data/evidencegate.db to /tmp, flips one character in an old
event's payload, and shows the hash chain catching it at the exact seq.
The real database is never touched.
"""

import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.audit import AuditTrail
from app.db import Database

SRC = Path("data/evidencegate.db")

def main():
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC
    copy = Path(tempfile.mkdtemp()) / "tampered.db"
    sqlite3.connect(db_path).execute(
        "VACUUM INTO ?", (str(copy),))   # db may be WAL-mode: VACUUM INTO
                                        # produces a complete standalone copy

    # 1. chain is intact before the attack
    trail = AuditTrail(Database(copy))
    ok = trail.verify_chain()
    print(f"antes do ataque:  ok={ok['ok']} length={ok['length']}")

    # 2. the attack: flip one character deep inside an early event payload
    raw = sqlite3.connect(copy)
    row = raw.execute(
        "SELECT seq,payload FROM events WHERE seq>2 ORDER BY seq LIMIT 1"
    ).fetchone()
    if row is None:
        print("trilha vazia — sem eventos para adulterar.")
        return
    seq, payload = row
    mid = len(payload) // 2
    forged = payload[:mid] + ("1" if payload[mid] != "1" else "2") + payload[mid+1:]
    raw.execute("UPDATE events SET payload=? WHERE seq=?", (forged, seq))
    raw.commit()
    print(f"ataque: alterado 1 caractere no payload do evento seq={seq}")

    # 3. detection
    after = trail.verify_chain()
    print(f"depois:  ok={after['ok']}  cadeia quebra no seq={after.get('tampered_seq')}")
    assert not after["ok"] and after.get("tampered_seq") == seq
    print("\nverify_chain apontou exatamente onde a adulteracao aconteceu.")

if __name__ == "__main__":
    main()
