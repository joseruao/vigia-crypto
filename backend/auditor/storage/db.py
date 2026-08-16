from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'outros',
    hash TEXT,
    extracted_chars INTEGER,
    truncated INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER REFERENCES documents(id),
    type TEXT DEFAULT 'compra',
    supplier TEXT,
    supplier_nif TEXT,
    supplier_email TEXT,
    invoice_number TEXT,
    date TEXT,
    due_date TEXT,
    total REAL,
    vat REAL,
    currency TEXT DEFAULT 'EUR',
    payment_reference TEXT,
    raw_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS invoice_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER REFERENCES invoices(id),
    description TEXT,
    qty REAL,
    unit_price REAL,
    total REAL
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER REFERENCES documents(id),
    date TEXT,
    amount REAL,
    description TEXT,
    reference TEXT,
    supplier TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    documents_processed INTEGER DEFAULT 0,
    ai_calls INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS email_drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER REFERENCES audit_runs(id),
    supplier TEXT,
    supplier_email TEXT,
    product TEXT,
    current_price REAL,
    alternative_price REAL,
    savings REAL,
    subject TEXT,
    body TEXT,
    status TEXT DEFAULT 'rascunho',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER REFERENCES audit_runs(id),
    tipo TEXT NOT NULL,
    titulo TEXT NOT NULL,
    descricao TEXT,
    impacto_eur REAL,
    confianca TEXT,
    evidencia TEXT,
    documentos TEXT,
    estado TEXT DEFAULT 'novo',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER REFERENCES audit_runs(id),
    document_id INTEGER,
    model TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    reasoning_tokens INTEGER,
    total_tokens INTEGER,
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuditDB:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # --- reset (cada run é uma passagem limpa sobre input/) ---
    def reset_processing_data(self) -> None:
        """Apaga dados de processamento (docs/faturas/pagamentos/achados).
        Mantém audit_runs e ai_calls (histórico de transparência)."""
        for table in ("invoice_lines", "invoices", "payments", "email_drafts", "documents", "audit_findings"):
            self.conn.execute(f"DELETE FROM {table}")
        self.conn.commit()

    # --- runs ---
    def start_run(self) -> int:
        cur = self.conn.execute(
            "INSERT INTO audit_runs (started_at) VALUES (?)", (_now(),)
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def finish_run(self, run_id: int, documents_processed: int, ai_calls: int) -> None:
        self.conn.execute(
            "UPDATE audit_runs SET finished_at = ?, documents_processed = ?, ai_calls = ? WHERE id = ?",
            (_now(), documents_processed, ai_calls, run_id),
        )
        self.conn.commit()

    # --- documents ---
    def insert_document(self, filename: str, category: str, hash_: str, extracted_chars: int, truncated: bool) -> int:
        cur = self.conn.execute(
            "INSERT INTO documents (filename, category, hash, extracted_chars, truncated, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (filename, category, hash_, extracted_chars, int(truncated), _now()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    # --- invoices ---
    def insert_invoice(self, doc_id: int, data: dict[str, Any], type_: str = "compra") -> int:
        lines = data.pop("lines", None) or []
        cur = self.conn.execute(
            "INSERT INTO invoices (document_id, type, supplier, supplier_nif, supplier_email, invoice_number, "
            "date, due_date, total, vat, currency, payment_reference, raw_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                doc_id,
                type_,
                data.get("supplier"),
                data.get("supplier_nif"),
                data.get("supplier_email"),
                data.get("invoice_number"),
                data.get("date"),
                data.get("due_date"),
                data.get("total"),
                data.get("vat"),
                data.get("currency") or "EUR",
                data.get("payment_reference"),
                data.get("raw_json"),
                _now(),
            ),
        )
        invoice_id = int(cur.lastrowid)
        for line in lines:
            self.conn.execute(
                "INSERT INTO invoice_lines (invoice_id, description, qty, unit_price, total) VALUES (?, ?, ?, ?, ?)",
                (
                    invoice_id,
                    line.get("description"),
                    line.get("qty"),
                    line.get("unit_price"),
                    line.get("total"),
                ),
            )
        self.conn.commit()
        return invoice_id

    def all_invoices(self, type_: str | None = None) -> list[sqlite3.Row]:
        if type_ is None:
            return self.conn.execute("SELECT * FROM invoices ORDER BY date").fetchall()
        return self.conn.execute(
            "SELECT * FROM invoices WHERE type = ? ORDER BY date", (type_,)
        ).fetchall()

    def all_lines(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT il.*, i.supplier, i.supplier_email, i.type, i.invoice_number, i.date "
            "FROM invoice_lines il JOIN invoices i ON i.id = il.invoice_id "
            "WHERE il.description IS NOT NULL AND il.unit_price IS NOT NULL"
        ).fetchall()

    def invoice_lines(self, invoice_id: int) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM invoice_lines WHERE invoice_id = ? ORDER BY id", (invoice_id,)
        ).fetchall()

    # --- payments ---
    def insert_payment(self, doc_id: int, data: dict[str, Any]) -> int:
        cur = self.conn.execute(
            "INSERT INTO payments (document_id, date, amount, description, reference, supplier, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                doc_id,
                data.get("date"),
                data.get("amount"),
                data.get("description"),
                data.get("reference"),
                data.get("supplier"),
                _now(),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def all_payments(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM payments ORDER BY date").fetchall()

    # --- findings ---
    def insert_finding(self, run_id: int, f: dict[str, Any]) -> int:
        cur = self.conn.execute(
            "INSERT INTO audit_findings (run_id, tipo, titulo, descricao, impacto_eur, confianca, "
            "evidencia, documentos, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                f.get("tipo"),
                f.get("titulo"),
                f.get("descricao"),
                f.get("impacto_eur"),
                f.get("confianca"),
                f.get("evidencia"),
                f.get("documentos"),
                _now(),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def all_findings(self, run_id: int | None = None) -> list[sqlite3.Row]:
        if run_id is None:
            return self.conn.execute("SELECT * FROM audit_findings ORDER BY id").fetchall()
        return self.conn.execute(
            "SELECT * FROM audit_findings WHERE run_id = ? ORDER BY id", (run_id,)
        ).fetchall()

    def clear_findings(self, run_id: int | None = None) -> None:
        if run_id is None:
            self.conn.execute("DELETE FROM audit_findings")
        else:
            self.conn.execute("DELETE FROM audit_findings WHERE run_id = ?", (run_id,))
        self.conn.commit()

    # --- email drafts ---
    def insert_email_draft(self, run_id: int, d: dict[str, Any]) -> int:
        cur = self.conn.execute(
            "INSERT INTO email_drafts (run_id, supplier, supplier_email, product, current_price, "
            "alternative_price, savings, subject, body, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'rascunho', ?)",
            (
                run_id,
                d.get("supplier"),
                d.get("supplier_email"),
                d.get("product"),
                d.get("current_price"),
                d.get("alternative_price"),
                d.get("savings"),
                d.get("subject"),
                d.get("body"),
                _now(),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def all_email_drafts(self, status: str | None = None) -> list[sqlite3.Row]:
        if status is None:
            return self.conn.execute("SELECT * FROM email_drafts ORDER BY id").fetchall()
        return self.conn.execute(
            "SELECT * FROM email_drafts WHERE status = ? ORDER BY id", (status,)
        ).fetchall()

    def mark_email_sent(self, draft_id: int) -> None:
        self.conn.execute("UPDATE email_drafts SET status = 'enviado' WHERE id = ?", (draft_id,))
        self.conn.commit()

    # --- ai calls (transparência: o que foi enviado para fora) ---
    def log_ai_call(self, run_id: int, document_id: int | None, info: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO ai_calls (run_id, document_id, model, prompt_tokens, completion_tokens, "
            "reasoning_tokens, total_tokens, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                document_id,
                info.get("model"),
                info.get("prompt_tokens"),
                info.get("completion_tokens"),
                info.get("reasoning_tokens"),
                info.get("total_tokens"),
                _now(),
            ),
        )
        self.conn.commit()

    def ai_calls_count(self, run_id: int) -> int:
        return int(
            self.conn.execute("SELECT COUNT(*) FROM ai_calls WHERE run_id = ?", (run_id,)).fetchone()[0]
        )

    def total_ai_tokens(self) -> int:
        row = self.conn.execute("SELECT COALESCE(SUM(total_tokens), 0) FROM ai_calls").fetchone()
        return int(row[0])
