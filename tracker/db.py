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

_HISTORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS status_history (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL,
    status         TEXT NOT NULL,
    changed_on     TEXT NOT NULL
)
"""

CONTACT_ROLES = ["Recruiter", "Referral", "Hiring manager", "Interviewer", "Other"]

_CONTACTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL,
    name           TEXT NOT NULL,
    role           TEXT NOT NULL DEFAULT 'Other',
    contact        TEXT DEFAULT '',
    last_contacted TEXT,
    is_sample      INTEGER NOT NULL DEFAULT 0
)
"""

_NOTES_SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL,
    note_date      TEXT NOT NULL,
    body           TEXT NOT NULL,
    is_sample      INTEGER NOT NULL DEFAULT 0
)
"""

_TASKS_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER,
    title          TEXT NOT NULL,
    due_date       TEXT NOT NULL,
    due_time       TEXT,
    done           INTEGER NOT NULL DEFAULT 0,
    created_on     TEXT NOT NULL
)
"""

# One row per item mirrored into the Mac Reminders app.
_MAC_LINKS_SCHEMA = """
CREATE TABLE IF NOT EXISTS mac_links (
    key         TEXT PRIMARY KEY,
    reminder_id TEXT NOT NULL,
    title       TEXT NOT NULL,
    due         TEXT NOT NULL,
    state       TEXT NOT NULL DEFAULT 'open'
)
"""

_MIGRATIONS = [
    ("referral_name",    "ALTER TABLE applications ADD COLUMN referral_name TEXT DEFAULT ''"),
    ("referral_contact", "ALTER TABLE applications ADD COLUMN referral_contact TEXT DEFAULT ''"),
    ("follow_up_date",   "ALTER TABLE applications ADD COLUMN follow_up_date TEXT"),
    ("is_sample",        "ALTER TABLE applications ADD COLUMN is_sample INTEGER NOT NULL DEFAULT 0"),
    ("stage_time",       "ALTER TABLE stages ADD COLUMN stage_time TEXT"),
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
    conn.execute(_HISTORY_SCHEMA)
    conn.execute(_CONTACTS_SCHEMA)
    conn.execute(_NOTES_SCHEMA)
    conn.execute(_TASKS_SCHEMA)
    conn.execute(_MAC_LINKS_SCHEMA)
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
    _record_status(conn, cur.lastrowid, status,
                   date_applied if status != "Wishlist" and date_applied else None)
    conn.commit()
    return cur.lastrowid


def _record_status(conn, app_id, status, on=None) -> None:
    """Append one row to status_history (caller commits)."""
    conn.execute(
        "INSERT INTO status_history (application_id, status, changed_on) VALUES (?,?,?)",
        (int(app_id), status, str(on) if on else str(_dt.date.today())),
    )


def load_status_history(conn, application_id=None) -> pd.DataFrame:
    """Status changes, oldest first. One row per move."""
    sql = "SELECT application_id, status, changed_on FROM status_history"
    params: tuple = ()
    if application_id is not None:
        sql += " WHERE application_id=?"
        params = (int(application_id),)
    df = pd.read_sql_query(sql + " ORDER BY changed_on, id", conn, params=params)
    df["changed_on"] = pd.to_datetime(df["changed_on"], errors="coerce")
    return df


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
    old = None
    if "status" in fields:
        r = conn.execute("SELECT status FROM applications WHERE id=?", (app_id,)).fetchone()
        old = r["status"] if r else None
    sets = ", ".join(f"{k}=?" for k in fields)
    conn.execute(f"UPDATE applications SET {sets} WHERE id=?", (*fields.values(), app_id))
    if "status" in fields and old is not None and fields["status"] != old:
        _record_status(conn, app_id, fields["status"])
    conn.commit()


def delete_application(conn, app_id):
    conn.execute("DELETE FROM tasks WHERE application_id=?", (app_id,))
    conn.execute("DELETE FROM contacts WHERE application_id=?", (app_id,))
    conn.execute("DELETE FROM notes WHERE application_id=?", (app_id,))
    conn.execute("DELETE FROM status_history WHERE application_id=?", (app_id,))
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
              notes="", is_sample=False, stage_time=None):
    """Insert an interview stage. Returns the new stage id."""
    row = conn.execute("SELECT id FROM applications WHERE id=?", (application_id,)).fetchone()
    if not row:
        raise ValueError(f"Application {application_id} not found")
    if stage not in STAGE_TYPES:
        raise ValueError(f"Invalid stage type: {stage}")
    if outcome not in STAGE_OUTCOMES:
        raise ValueError(f"Invalid outcome: {outcome}")
    cur = conn.execute(
        "INSERT INTO stages (application_id, stage, stage_date, outcome, notes, is_sample, stage_time) "
        "VALUES (?,?,?,?,?,?,?)",
        (application_id,
         stage,
         str(stage_date) if stage_date else None,
         outcome, notes, 1 if is_sample else 0,
         str(stage_time)[:5] if stage_time else None),
    )
    conn.commit()
    return cur.lastrowid


def update_stage(conn, stage_id, **fields):
    """Update one or more fields of a stage row."""
    allowed = {"stage", "stage_date", "outcome", "notes", "stage_time"}
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
    conn.execute("DELETE FROM status_history WHERE application_id IN "
                 "(SELECT id FROM applications WHERE is_sample=1)")
    for t in ("contacts", "notes"):
        conn.execute(f"DELETE FROM {t} WHERE application_id IN "
                     "(SELECT id FROM applications WHERE is_sample=1)")
    conn.execute("DELETE FROM stages WHERE is_sample=1")
    conn.execute("DELETE FROM match_scores WHERE is_sample=1")
    conn.execute("DELETE FROM applications WHERE is_sample=1")
    conn.commit()


def clear_all_data(conn) -> None:
    """Remove every row from applications, stages and match_scores."""
    conn.execute("DELETE FROM stages")
    conn.execute("DELETE FROM status_history")
    conn.execute("DELETE FROM tasks")
    conn.execute("DELETE FROM contacts")
    conn.execute("DELETE FROM notes")
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


# ---------------------------------------------------------------------------
# Contacts and dated notes (any number per application)
# ---------------------------------------------------------------------------

def add_contact(conn, application_id, name, role="Other", contact="",
                last_contacted=None) -> int:
    if not str(name).strip():
        raise ValueError("Contact name is required")
    if role not in CONTACT_ROLES:
        raise ValueError(f"Invalid role: {role}")
    cur = conn.execute(
        "INSERT INTO contacts (application_id, name, role, contact, last_contacted) "
        "VALUES (?,?,?,?,?)",
        (int(application_id), name.strip(), role, contact.strip(),
         str(last_contacted) if last_contacted else None),
    )
    conn.commit()
    return cur.lastrowid


def update_contact(conn, contact_id, **fields) -> None:
    allowed = {"name", "role", "contact", "last_contacted"}
    bad = set(fields) - allowed
    if bad:
        raise ValueError(f"Unknown fields: {bad}")
    if "role" in fields and fields["role"] not in CONTACT_ROLES:
        raise ValueError(f"Invalid role: {fields['role']}")
    if not fields:
        return
    if "last_contacted" in fields and fields["last_contacted"]:
        fields["last_contacted"] = str(fields["last_contacted"])
    sets = ", ".join(f"{k}=?" for k in fields)
    conn.execute(f"UPDATE contacts SET {sets} WHERE id=?", (*fields.values(), int(contact_id)))
    conn.commit()


def delete_contact(conn, contact_id) -> None:
    conn.execute("DELETE FROM contacts WHERE id=?", (int(contact_id),))
    conn.commit()


def load_contacts(conn, application_id=None) -> pd.DataFrame:
    sql = "SELECT * FROM contacts"
    params: tuple = ()
    if application_id is not None:
        sql += " WHERE application_id=?"
        params = (int(application_id),)
    df = pd.read_sql_query(sql + " ORDER BY id", conn, params=params)
    df["last_contacted"] = pd.to_datetime(df["last_contacted"], errors="coerce")
    return df


def add_note(conn, application_id, body, note_date=None) -> int:
    if not str(body).strip():
        raise ValueError("Note is empty")
    cur = conn.execute(
        "INSERT INTO notes (application_id, note_date, body) VALUES (?,?,?)",
        (int(application_id), str(note_date or _dt.date.today()), body.strip()),
    )
    conn.commit()
    return cur.lastrowid


def delete_note(conn, note_id) -> None:
    conn.execute("DELETE FROM notes WHERE id=?", (int(note_id),))
    conn.commit()


def load_notes(conn, application_id=None) -> pd.DataFrame:
    """Notes, newest first."""
    sql = "SELECT * FROM notes"
    params: tuple = ()
    if application_id is not None:
        sql += " WHERE application_id=?"
        params = (int(application_id),)
    df = pd.read_sql_query(sql + " ORDER BY note_date DESC, id DESC", conn, params=params)
    df["note_date"] = pd.to_datetime(df["note_date"], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# To-dos ("send a thank-you note Thursday") and Mac Reminders links
# ---------------------------------------------------------------------------

def add_task(conn, title, due_date, application_id=None, due_time=None) -> int:
    if not str(title).strip():
        raise ValueError("Say what the reminder is for")
    if not due_date:
        raise ValueError("Pick a date")
    cur = conn.execute(
        "INSERT INTO tasks (application_id, title, due_date, due_time, created_on) "
        "VALUES (?,?,?,?,?)",
        (int(application_id) if application_id else None, title.strip(), str(due_date),
         str(due_time)[:5] if due_time else None, str(_dt.date.today())),
    )
    conn.commit()
    return cur.lastrowid


def set_task_done(conn, task_id, done=True) -> None:
    conn.execute("UPDATE tasks SET done=? WHERE id=?", (1 if done else 0, int(task_id)))
    conn.commit()


def delete_task(conn, task_id) -> None:
    conn.execute("DELETE FROM tasks WHERE id=?", (int(task_id),))
    conn.commit()


def load_tasks(conn, include_done=False) -> pd.DataFrame:
    sql = ("SELECT t.*, a.company, a.role FROM tasks t "
           "LEFT JOIN applications a ON a.id = t.application_id")
    if not include_done:
        sql += " WHERE t.done = 0"
    df = pd.read_sql_query(sql + " ORDER BY t.due_date, t.due_time, t.id", conn)
    df["due_date"] = pd.to_datetime(df["due_date"], errors="coerce")
    return df


def load_mac_links(conn) -> dict:
    rows = conn.execute("SELECT * FROM mac_links").fetchall()
    return {r["key"]: dict(r) for r in rows}


def save_mac_link(conn, key, reminder_id, title, due, state="open") -> None:
    conn.execute(
        "INSERT OR REPLACE INTO mac_links (key, reminder_id, title, due, state) VALUES (?,?,?,?,?)",
        (key, reminder_id, title, due, state),
    )
    conn.commit()


def set_mac_link_state(conn, key, state) -> None:
    conn.execute("UPDATE mac_links SET state=? WHERE key=?", (state, key))
    conn.commit()


# ---------------------------------------------------------------------------
# Backup and restore (the whole database as one file)
# ---------------------------------------------------------------------------

def backup_bytes(conn) -> bytes:
    """Everything in the tracker as a single SQLite file."""
    conn.commit()
    return conn.serialize()


def restore_from_bytes(conn, data: bytes, keep_copy_dir=None) -> str | None:
    """Replace all data with a backup file's contents.

    Checks the file is a tracker backup first. When ``keep_copy_dir`` is given,
    the current data is saved there as ``tracker-before-restore-<time>.db``
    and that path is returned.
    """
    if not data.startswith(b"SQLite format 3\x00"):
        raise ValueError("That isn't a tracker backup file (.db).")
    src = sqlite3.connect(":memory:")
    try:
        src.deserialize(data)
        tables = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    except sqlite3.DatabaseError as e:
        raise ValueError("That backup file is damaged.") from e
    if "applications" not in tables:
        raise ValueError("That file isn't a tracker backup (no applications table).")

    saved = None
    if keep_copy_dir is not None:
        d = Path(keep_copy_dir)
        d.mkdir(parents=True, exist_ok=True)
        saved = str(d / f"tracker-before-restore-{_dt.datetime.now():%Y%m%d-%H%M%S}.db")
        Path(saved).write_bytes(backup_bytes(conn))

    conn.commit()
    src.backup(conn)          # overwrite in place; the app's connection stays valid
    src.close()
    # An older backup may lack newer tables/columns.
    for schema in (SCHEMA, _SETTINGS_SCHEMA, _STAGES_SCHEMA, _MATCH_SCORES_SCHEMA,
                   _HISTORY_SCHEMA, _CONTACTS_SCHEMA, _NOTES_SCHEMA, _TASKS_SCHEMA,
                   _MAC_LINKS_SCHEMA):
        conn.execute(schema)
    _migrate(conn)
    return saved
