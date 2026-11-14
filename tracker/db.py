"""SQLite storage for internship applications."""
import datetime as _dt
import json as _json
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "tracker.db"

_SETTINGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
"""

STATUSES = ["Wishlist", "Applied", "OA/Screen", "Interview", "Offer", "Rejected", "Withdrawn"]

STAGE_TYPES = [
    "Recruiter screen", "Online assessment", "Technical",
    "Behavioral", "Take-home", "Onsite/Final", "Other",
]

STAGE_OUTCOMES = ["Scheduled", "Passed", "Failed", "Pending"]

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

_STAGES_SCHEMA = """
CREATE TABLE IF NOT EXISTS stages (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL,
    stage          TEXT NOT NULL,
    stage_date     TEXT,
    outcome        TEXT NOT NULL DEFAULT 'Scheduled',
    notes          TEXT DEFAULT '',
    is_sample      INTEGER NOT NULL DEFAULT 0
)
"""

_MATCH_SCORES_SCHEMA = """
CREATE TABLE IF NOT EXISTS match_scores (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id   INTEGER NOT NULL,
    scanned_at       TEXT NOT NULL,
    overall_score    REAL NOT NULL,
    keyword_score    REAL NOT NULL,
    similarity_score REAL NOT NULL,
    matched_count    INTEGER NOT NULL DEFAULT 0,
    missing_count    INTEGER NOT NULL DEFAULT 0,
    top_missing      TEXT DEFAULT '[]',
    resume_label     TEXT DEFAULT '',
    is_sample        INTEGER NOT NULL DEFAULT 0
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
    conn.execute(_SETTINGS_SCHEMA)
    conn.execute(_STAGES_SCHEMA)
    conn.execute(_MATCH_SCORES_SCHEMA)
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
    conn.execute("DELETE FROM stages WHERE application_id=?", (app_id,))
    conn.execute("DELETE FROM match_scores WHERE application_id=?", (app_id,))
    conn.execute("DELETE FROM applications WHERE id=?", (app_id,))
    conn.commit()


def load_applications(conn):
    df = pd.read_sql_query("SELECT * FROM applications ORDER BY id DESC", conn)
    for col in ("date_applied", "deadline", "follow_up_date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# Interview stages
# ---------------------------------------------------------------------------

def add_stage(conn, application_id, stage, stage_date=None, outcome="Scheduled",
              notes="", is_sample=False):
    """Insert an interview stage. Returns the new stage id."""
    row = conn.execute("SELECT id FROM applications WHERE id=?", (application_id,)).fetchone()
    if not row:
        raise ValueError(f"Application {application_id} not found")
    if stage not in STAGE_TYPES:
        raise ValueError(f"Invalid stage type: {stage}")
    if outcome not in STAGE_OUTCOMES:
        raise ValueError(f"Invalid outcome: {outcome}")
    cur = conn.execute(
        "INSERT INTO stages (application_id, stage, stage_date, outcome, notes, is_sample) "
        "VALUES (?,?,?,?,?,?)",
        (application_id,
         stage,
         str(stage_date) if stage_date else None,
         outcome, notes, 1 if is_sample else 0),
    )
    conn.commit()
    return cur.lastrowid


def update_stage(conn, stage_id, **fields):
    """Update one or more fields of a stage row."""
    allowed = {"stage", "stage_date", "outcome", "notes"}
    bad = set(fields) - allowed
    if bad:
        raise ValueError(f"Unknown stage fields: {bad}")
    if "stage" in fields and fields["stage"] not in STAGE_TYPES:
        raise ValueError(f"Invalid stage type: {fields['stage']}")
    if "outcome" in fields and fields["outcome"] not in STAGE_OUTCOMES:
        raise ValueError(f"Invalid outcome: {fields['outcome']}")
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    conn.execute(f"UPDATE stages SET {sets} WHERE id=?", (*fields.values(), stage_id))
    conn.commit()


def delete_stage(conn, stage_id):
    conn.execute("DELETE FROM stages WHERE id=?", (stage_id,))
    conn.commit()


def load_stages(conn, application_id=None):
    """Load stages, optionally filtered to one application."""
    if application_id is not None:
        df = pd.read_sql_query(
            "SELECT * FROM stages WHERE application_id=? ORDER BY stage_date, id",
            conn, params=(application_id,),
        )
    else:
        df = pd.read_sql_query(
            "SELECT * FROM stages ORDER BY application_id, stage_date, id",
            conn,
        )
    if "stage_date" in df.columns:
        df["stage_date"] = pd.to_datetime(df["stage_date"], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# Resume match scores
# ---------------------------------------------------------------------------

def add_match_score(conn, application_id, overall_score, keyword_score,
                    similarity_score, matched_count, missing_count,
                    top_missing, resume_label, is_sample=False):
    """Save a resume matcher result against an application."""
    row = conn.execute("SELECT id FROM applications WHERE id=?", (application_id,)).fetchone()
    if not row:
        raise ValueError(f"Application {application_id} not found")
    scanned_at = _dt.datetime.now().isoformat()
    conn.execute(
        "INSERT INTO match_scores "
        "(application_id, scanned_at, overall_score, keyword_score, similarity_score, "
        "matched_count, missing_count, top_missing, resume_label, is_sample) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (application_id, scanned_at, float(overall_score), float(keyword_score),
         float(similarity_score), int(matched_count), int(missing_count),
         _json.dumps(list(top_missing)), str(resume_label), 1 if is_sample else 0),
    )
    conn.commit()


def load_match_scores(conn, application_id=None):
    """Load match scores, optionally filtered to one application."""
    if application_id is not None:
        df = pd.read_sql_query(
            "SELECT * FROM match_scores WHERE application_id=? ORDER BY scanned_at DESC",
            conn, params=(application_id,),
        )
    else:
        df = pd.read_sql_query(
            "SELECT * FROM match_scores ORDER BY scanned_at DESC",
            conn,
        )
    if "scanned_at" in df.columns:
        df["scanned_at"] = pd.to_datetime(df["scanned_at"], errors="coerce")
    return df


def delete_match_score(conn, score_id):
    conn.execute("DELETE FROM match_scores WHERE id=?", (score_id,))
    conn.commit()


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

def _sample_app_id(conn, company):
    """Return the most recently inserted sample application id for *company*."""
    row = conn.execute(
        "SELECT id FROM applications WHERE company=? AND is_sample=1 ORDER BY id DESC LIMIT 1",
        (company,),
    ).fetchone()
    return row["id"] if row else None


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

    # Sample interview stages
    google_id = _sample_app_id(conn, "Google")
    if google_id:
        add_stage(conn, google_id, "Recruiter screen",
                  str(today - td(days=42)), "Passed", is_sample=True)
        add_stage(conn, google_id, "Technical",
                  str(today - td(days=30)), "Passed", is_sample=True)
        add_stage(conn, google_id, "Onsite/Final",
                  str(today + td(days=5)), "Scheduled", is_sample=True)

    amazon_id = _sample_app_id(conn, "Amazon")
    if amazon_id:
        add_stage(conn, amazon_id, "Recruiter screen",
                  str(today - td(days=32)), "Passed", is_sample=True)
        add_stage(conn, amazon_id, "Technical",
                  str(today - td(days=22)), "Failed", is_sample=True)

    microsoft_id = _sample_app_id(conn, "Microsoft")
    if microsoft_id:
        add_stage(conn, microsoft_id, "Recruiter screen",
                  str(today - td(days=58)), "Passed", is_sample=True)
        add_stage(conn, microsoft_id, "Technical",
                  str(today - td(days=48)), "Passed", is_sample=True)
        add_stage(conn, microsoft_id, "Behavioral",
                  str(today - td(days=42)), "Passed", is_sample=True)
        add_stage(conn, microsoft_id, "Onsite/Final",
                  str(today - td(days=35)), "Passed", is_sample=True)

    uber_id = _sample_app_id(conn, "Uber")
    if uber_id:
        add_stage(conn, uber_id, "Recruiter screen",
                  str(today - td(days=52)), "Passed", is_sample=True)
        add_stage(conn, uber_id, "Technical",
                  str(today + td(days=3)), "Scheduled", is_sample=True)

    figma_id = _sample_app_id(conn, "Figma")
    if figma_id:
        add_stage(conn, figma_id, "Recruiter screen",
                  str(today - td(days=35)), "Passed", is_sample=True)
        add_stage(conn, figma_id, "Technical",
                  str(today + td(days=7)), "Scheduled", is_sample=True)

    # Sample match scores
    amazon_id2 = _sample_app_id(conn, "Amazon")
    if amazon_id2:
        add_match_score(conn, amazon_id2, 65.0, 62.0, 70.0, 11, 5,
                        ["kubernetes", "terraform", "graphql", "redis", "kafka"],
                        "demo resume", is_sample=True)
        add_match_score(conn, amazon_id2, 72.0, 68.0, 78.0, 15, 4,
                        ["kubernetes", "terraform", "docker", "graphql"],
                        "demo resume v2", is_sample=True)

    meta_id = _sample_app_id(conn, "Meta")
    if meta_id:
        add_match_score(conn, meta_id, 85.0, 82.0, 90.0, 20, 2,
                        ["pytorch", "mlops"],
                        "demo resume", is_sample=True)

    return count


def clear_sample_data(conn) -> None:
    """Remove all sample rows (is_sample=1)."""
    conn.execute("DELETE FROM stages WHERE is_sample=1")
    conn.execute("DELETE FROM match_scores WHERE is_sample=1")
    conn.execute("DELETE FROM applications WHERE is_sample=1")
    conn.commit()


def clear_all_data(conn) -> None:
    """Remove every row from applications, stages and match_scores."""
    conn.execute("DELETE FROM stages")
    conn.execute("DELETE FROM match_scores")
    conn.execute("DELETE FROM applications")
    conn.commit()


# ---------------------------------------------------------------------------
# Settings (key/value persistence)
# ---------------------------------------------------------------------------

def get_setting(conn, key: str, default: str = "") -> str:
    """Return the stored value for *key*, or *default* if not set."""
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn, key: str, value: str) -> None:
    """Upsert a key/value pair into the settings table."""
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, value),
    )
    conn.commit()
