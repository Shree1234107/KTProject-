"""SQLite storage for internship applications."""
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "tracker.db"

STATUSES = ["Wishlist", "Applied", "OA/Screen", "Interview", "Offer", "Rejected", "Withdrawn"]

COLUMNS = ["id", "company", "role", "location", "status", "date_applied", "deadline", "source", "notes"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    location TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Applied',
    date_applied TEXT,
    deadline TEXT,
    source TEXT DEFAULT '',
    notes TEXT DEFAULT ''
)
"""


def connect(path=None):
    p = Path(path) if path else DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn


def add_application(conn, company, role, location="", status="Applied",
                    date_applied=None, deadline=None, source="", notes=""):
    if status not in STATUSES:
        raise ValueError(f"Invalid status: {status}")
    if not company.strip() or not role.strip():
        raise ValueError("Company and role are required")
    cur = conn.execute(
        "INSERT INTO applications (company, role, location, status, date_applied, deadline, source, notes) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (company.strip(), role.strip(), location, status,
         str(date_applied) if date_applied else None,
         str(deadline) if deadline else None, source, notes),
    )
    conn.commit()
    return cur.lastrowid


def update_application(conn, app_id, **fields):
    allowed = set(COLUMNS) - {"id"}
    bad = set(fields) - allowed
    if bad:
        raise ValueError(f"Unknown fields: {bad}")
    if "status" in fields and fields["status"] not in STATUSES:
        raise ValueError(f"Invalid status: {fields['status']}")
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    conn.execute(f"UPDATE applications SET {sets} WHERE id=?", (*fields.values(), app_id))
    conn.commit()


def delete_application(conn, app_id):
    conn.execute("DELETE FROM applications WHERE id=?", (app_id,))
    conn.commit()


def load_applications(conn):
    df = pd.read_sql_query("SELECT * FROM applications ORDER BY id DESC", conn)
    for col in ("date_applied", "deadline"):
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df
