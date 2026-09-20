"""SQLite persistence layer. WAL mode, foreign keys on, one connection per Database."""

import sqlite3
import threading
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS principals (
    id          TEXT PRIMARY KEY,
    legal_name  TEXT NOT NULL,
    doc_hash    TEXT NOT NULL,            -- hash do doc legal (CNPJ/CPF), nunca em claro
    created_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS agents (
    did          TEXT PRIMARY KEY,
    principal_id TEXT NOT NULL REFERENCES principals(id),
    pubkey_b58   TEXT NOT NULL,
    card         TEXT NOT NULL,           -- AgentCard JSON assinado
    card_sig     TEXT NOT NULL,
    manifest     TEXT NOT NULL,           -- KYA manifest: capabilities, fuses
    reputation   REAL NOT NULL DEFAULT 0,
    status       TEXT NOT NULL DEFAULT 'active',   -- active | revoked
    created_at   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS quotes (
    id          TEXT PRIMARY KEY,
    buyer_did   TEXT NOT NULL,
    seller_did  TEXT NOT NULL,
    scope       TEXT NOT NULL,
    criteria    TEXT NOT NULL,            -- rubrica de aceite TRAVADA no quote
    price       REAL NOT NULL,
    deadline    REAL NOT NULL,
    quote_hash  TEXT NOT NULL,
    signature   TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'open',
    created_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS escrows (
    id           TEXT PRIMARY KEY,
    quote_id     TEXT NOT NULL REFERENCES quotes(id),
    state        TEXT NOT NULL,           -- ver ESCROW_STATES em escrow.py
    evidence     TEXT,                    -- artefato entregue (JSON)
    evidence_hash TEXT,
    verdict      TEXT,                    -- released | retained
    dispute      TEXT,                    -- razao da disputa, se houver
    idempotency  TEXT UNIQUE,             -- chave de idempotencia do funding
    created_at   REAL NOT NULL,
    updated_at   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS ledger (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    account    TEXT NOT NULL,             -- did ou 'escrow:<id>'
    delta      REAL NOT NULL,
    reason     TEXT NOT NULL,
    escrow_id  TEXT,
    ts         REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    seq          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           REAL NOT NULL,
    actor_did    TEXT NOT NULL,
    action       TEXT NOT NULL,
    payload      TEXT NOT NULL,           -- canonical JSON
    payload_hash TEXT NOT NULL,
    prev_hash    TEXT NOT NULL,
    event_hash   TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS judge_votes (
    escrow_id    TEXT NOT NULL,
    judge        TEXT NOT NULL,           -- capability usada (reasoning/reasoning-pro/code)
    commit_hash  TEXT NOT NULL,
    vote         TEXT,                    -- approve | reject (apos reveal)
    confidence   REAL,
    rationale    TEXT,
    nonce        TEXT,
    revealed     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (escrow_id, judge)
);

CREATE TABLE IF NOT EXISTS inference_calls (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              REAL NOT NULL,
    model_requested TEXT NOT NULL,
    model_used      TEXT NOT NULL,
    prompt_tokens   INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    cost            REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS balances (
    account TEXT PRIMARY KEY,
    amount  REAL NOT NULL DEFAULT 0
);
"""


class _Rows:
    """Result set materialized while the connection lock is held, so a second
    thread can never advance or reset a statement this caller is still reading."""

    def __init__(self, cur: sqlite3.Cursor):
        self.lastrowid, self.rowcount = cur.lastrowid, cur.rowcount
        self._rows = cur.fetchall() if cur.description else []

    def fetchone(self):
        return self._rows.pop(0) if self._rows else None

    def fetchall(self):
        rows, self._rows = self._rows, []
        return rows

    def __iter__(self):
        return iter(self.fetchall())


class Database:
    def __init__(self, path: str | Path = ":memory:"):
        # One connection is shared by every request thread (FastAPI threadpool,
        # dashboard polling, mission workers): all access goes through this lock.
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(SCHEMA)

    def execute(self, sql: str, params: tuple = ()) -> _Rows:
        with self._lock:
            return _Rows(self.conn.execute(sql, params))

    def tx(self):
        return self.conn  # context manager: commits on exit, rolls back on exception

    @staticmethod
    def now() -> float:
        return time.time()
