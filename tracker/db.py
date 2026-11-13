"""SQLite storage for internship applications."""
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "tracker.db"

STATUSES = ["Wishlist", "Applied", "OA/Screen", "Interview", "Offer", "Rejected", "Withdrawn"]

COLUMNS = [
    "id", "company", "role", "location", "status",
    "date_applied", "deadline", "source", "notes",
    "referral_name", "referral_contact", "follow_up_date",
]

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
    notes TEXT DEFAULT '',
    referral_name TEXT DEFAULT '',
    referral_contact TEXT DEFAULT '',
    follow_up_date TEXT
)
"""

_MIGRATIONS = [
    ("referral_name",    "ALTER TABLE applications ADD COLUMN referral_name TEXT DEFAULT ''"),
    ("referral_contact", "ALTER TABLE applications ADD COLUMN referral_contact TEXT DEFAULT ''"),
    ("follow_up_date",   "ALTER TABLE applications ADD COLUMN follow_up_date TEXT"),
]


def _migrate(conn: sqlite3.Connection) -> None:
    for _col, sql in _MIGRATIONS:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass
    conn.commit()


def connect(path=None):
    p = Path(path) if path else DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    _migrate(conn)
    return conn


def add_application(conn, company, role, location="", status="Applied",
                    date_applied=None, deadline=None, source="", notes="",
                    referral_name="", referral_contact="",
                    follow_up_date=None):
    if status not in STATUSES:
        raise ValueError(f"Invalid status: {status}")
    if not company.strip() or not role.strip():
        raise ValueError("Company and role are required")
    cur = conn.execute(
        "INSERT INTO applications "
        "(company, role, location, status, date_applied, deadline, source, notes, "
        "referral_name, referral_contact, follow_up_date) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            company.strip(), role.strip(), location, status,
            str(date_applied) if date_applied else None,
            str(deadline) if deadline else None,
            source, notes,
            referral_name, referral_contact,
            str(follow_up_date) if follow_up_date else None,
        ),
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
    if "company" in fields and not str(fields["company"]).strip():
        raise ValueError("Company cannot be empty")
    if "role" in fields and not str(fields["role"]).strip():
        raise ValueError("Role cannot be empty")
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
    for col in ("date_applied", "deadline", "follow_up_date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df
