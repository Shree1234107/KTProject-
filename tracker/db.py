"""SQLite storage for internship applications."""
import datetime as _dt
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "tracker.db"

STATUSES = ["Wishlist", "Applied", "OA/Screen", "Interview", "Offer", "Rejected", "Withdrawn"]

COLUMNS = [
    "id", "company", "role", "location", "status",
    "date_applied", "deadline", "source", "notes",
    "referral_name", "referral_contact", "follow_up_date", "is_sample",
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
    follow_up_date TEXT,
    is_sample INTEGER NOT NULL DEFAULT 0
)
"""

_MIGRATIONS = [
    ("referral_name",    "ALTER TABLE applications ADD COLUMN referral_name TEXT DEFAULT ''"),
    ("referral_contact", "ALTER TABLE applications ADD COLUMN referral_contact TEXT DEFAULT ''"),
    ("follow_up_date",   "ALTER TABLE applications ADD COLUMN follow_up_date TEXT"),
    ("is_sample",        "ALTER TABLE applications ADD COLUMN is_sample INTEGER NOT NULL DEFAULT 0"),
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
                    follow_up_date=None, is_sample=False):
    if status not in STATUSES:
        raise ValueError(f"Invalid status: {status}")
    if not company.strip() or not role.strip():
        raise ValueError("Company and role are required")
    cur = conn.execute(
        "INSERT INTO applications "
        "(company, role, location, status, date_applied, deadline, source, notes, "
        "referral_name, referral_contact, follow_up_date, is_sample) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            company.strip(), role.strip(), location, status,
            str(date_applied) if date_applied else None,
            str(deadline) if deadline else None,
            source, notes,
            referral_name, referral_contact,
            str(follow_up_date) if follow_up_date else None,
            1 if is_sample else 0,
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


def load_sample_data(conn) -> int:
    """Insert ~15 realistic sample applications. Returns the count inserted."""
    today = _dt.date.today()
    td = _dt.timedelta

    rows = [
        # company, role, location, status, days_ago, source, ref_name, ref_contact, fu_offset
        ("Google",      "SWE Intern",             "Mountain View, CA",   "Interview", 45, "LinkedIn",    "Jane Smith",  "jane@google.com",   -1),
        ("Meta",        "Data Scientist Intern",   "Menlo Park, CA",      "Applied",   25, "LinkedIn",    "",            "",                   7),
        ("Amazon",      "SDE Intern",              "Seattle, WA",         "OA/Screen", 35, "Referral",    "Bob Lee",     "bob@amazon.com",    -3),
        ("Microsoft",   "PM Intern",               "Redmond, WA",         "Offer",     60, "Career fair", "",            "",                None),
        ("Apple",       "iOS Intern",              "Cupertino, CA",       "Rejected",  50, "LinkedIn",    "",            "",                None),
        ("Netflix",     "Backend Intern",          "Los Gatos, CA",       "Applied",   22, "Referral",    "Alice Chen",  "alice@netflix.com",  3),
        ("Stripe",      "Payments Intern",         "San Francisco, CA",   "Applied",   30, "LinkedIn",    "",            "",                  -5),
        ("Airbnb",      "Frontend Intern",         "San Francisco, CA",   "Withdrawn", 40, "LinkedIn",    "",            "",                None),
        ("Spotify",     "ML Intern",               "New York, NY",        "Applied",   21, "Website",     "",            "",                   0),
        ("Uber",        "Data Eng Intern",         "San Francisco, CA",   "Interview", 55, "Referral",    "Dave Kim",    "dave@uber.com",      1),
        ("Figma",       "Product Design Intern",   "San Francisco, CA",   "Interview", 38, "Career fair", "",            "",                   5),
        ("Palantir",    "Forward Deploy Intern",   "New York, NY",        "OA/Screen", 28, "Referral",    "Emma Wang",   "emma@palantir.com", -7),
        ("Databricks",  "Data Infra Intern",       "San Francisco, CA",   "Applied",   21, "LinkedIn",    "",            "",                   0),
        ("LinkedIn",    "SWE Intern",              "Sunnyvale, CA",       "Applied",   10, "Website",     "",            "",                  14),
        ("Cloudflare",  "Network Intern",          "Austin, TX",          "Wishlist",   0, "LinkedIn",    "",            "",                None),
    ]

    count = 0
    for company, role, location, status, days_ago, source, ref_name, ref_contact, fu_offset in rows:
        date_applied = (today - td(days=days_ago)) if days_ago > 0 else None
        follow_up = str(today + td(days=fu_offset)) if fu_offset is not None else None
        add_application(
            conn, company, role, location, status,
            date_applied=date_applied,
            source=source,
            notes="[sample]",
            referral_name=ref_name,
            referral_contact=ref_contact,
            follow_up_date=follow_up,
            is_sample=True,
        )
        count += 1
    return count


def clear_sample_data(conn) -> None:
    """Remove all sample rows (is_sample=1)."""
    conn.execute("DELETE FROM applications WHERE is_sample=1")
    conn.commit()


def clear_all_data(conn) -> None:
    """Remove every application row."""
    conn.execute("DELETE FROM applications")
    conn.commit()
