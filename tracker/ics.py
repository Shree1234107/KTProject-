"""RFC 5545 ICS calendar builder for the internship tracker.

Pure function — no I/O, no Streamlit, no external dependencies.
Call :func:`build_ics` from app.py.
"""
from __future__ import annotations

import datetime as _dt

import pandas as pd

_CRLF = "\r\n"
_FOLD_WIDTH = 75  # octets, per RFC 5545 §3.1


# ---------------------------------------------------------------------------
# RFC 5545 text helpers
# ---------------------------------------------------------------------------

def _escape(value: str) -> str:
    """Escape a property value for ICS (backslash, semicolon, comma, newlines)."""
    value = value.replace("\\", "\\\\")
    value = value.replace(";", "\\;")
    value = value.replace(",", "\\,")
    value = value.replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n")
    return value


def _fold(line: str) -> str:
    """Fold a long property line at 75 octets (RFC 5545 §3.1).

    Returns a string with embedded CRLF+SPACE fold markers but no trailing CRLF.
    When joined with the rest of the calendar via CRLF, the result is valid ICS.
    """
    encoded = line.encode("utf-8")
    if len(encoded) <= _FOLD_WIDTH:
        return line

    parts: list[str] = []
    pos = 0
    first = True
    while pos < len(encoded):
        limit = _FOLD_WIDTH if first else _FOLD_WIDTH - 1  # -1 for leading space
        chunk = encoded[pos: pos + limit]
        # Back off to a valid UTF-8 boundary
        while chunk and True:
            try:
                chunk.decode("utf-8")
                break
            except UnicodeDecodeError:
                chunk = chunk[:-1]
        if not chunk:
            chunk = encoded[pos: pos + 1]  # advance at least one byte
        parts.append(chunk.decode("utf-8"))
        pos += len(chunk)
        first = False

    return _CRLF.join((" " if i > 0 else "") + part for i, part in enumerate(parts))


def _fmt_date(d) -> str:
    """Format a date or Timestamp as YYYYMMDD."""
    if isinstance(d, _dt.datetime):
        return d.strftime("%Y%m%d")
    if isinstance(d, _dt.date):
        return d.strftime("%Y%m%d")
    return str(d).replace("-", "")[:8]


def _dtstamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_ics(
    applications_df: pd.DataFrame,
    stages_df: pd.DataFrame,
    today,
    include_followups: bool = True,
    include_deadlines: bool = True,
    include_interviews: bool = True,
    include_past: bool = False,
) -> str:
    """Build an RFC-5545 compliant ICS calendar string.

    Args:
        applications_df: Full applications DataFrame from db.load_applications.
        stages_df: Full stages DataFrame from db.load_stages.
        today: Reference date (string, date, or Timestamp).
        include_followups: Emit events for follow-up dates.
        include_deadlines: Emit events for application deadlines.
        include_interviews: Emit events for Scheduled/Pending interview stages.
        include_past: When False, skip events whose date is before today.

    Returns:
        ICS text with CRLF line endings.
    """
    today_d: _dt.date = pd.Timestamp(today).date()
    stamp = _dtstamp()

    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//KTProject//Internship Tracker//EN",
        "CALSCALE:GREGORIAN",
    ]

    # Active applications only (no Rejected / Withdrawn follow-ups or deadlines)
    if applications_df.empty:
        active_apps = applications_df
    else:
        active_apps = applications_df[
            ~applications_df["status"].isin({"Rejected", "Withdrawn"})
        ]

    def _add_event(uid: str, dtstart: _dt.date, summary: str, description: str = "") -> None:
        dtstart_d = dtstart if isinstance(dtstart, _dt.date) else dtstart.date()
        dtend_d   = dtstart_d + _dt.timedelta(days=1)
        lines.append("BEGIN:VEVENT")
        lines.append(_fold(f"UID:{_escape(uid)}"))
        lines.append(f"DTSTAMP:{stamp}")
        lines.append(f"DTSTART;VALUE=DATE:{_fmt_date(dtstart_d)}")
        lines.append(f"DTEND;VALUE=DATE:{_fmt_date(dtend_d)}")
        lines.append(_fold(f"SUMMARY:{_escape(summary)}"))
        if description:
            lines.append(_fold(f"DESCRIPTION:{_escape(description)}"))
        lines.append("END:VEVENT")

    # --- Follow-up dates ---
    if include_followups and not active_apps.empty and "follow_up_date" in active_apps.columns:
        fu_rows = active_apps.dropna(subset=["follow_up_date"])
        for row in fu_rows.itertuples():
            fu_date: _dt.date = (
                row.follow_up_date.date()
                if hasattr(row.follow_up_date, "date")
                else row.follow_up_date
            )
            if not include_past and fu_date < today_d:
                continue
            uid = f"app-{row.id}-followup@ktproject"
            summary = f"Follow up: {row.company} - {row.role}"
            desc_parts = [f"Status: {row.status}"]
            if getattr(row, "source", ""):
                desc_parts.append(f"Source: {row.source}")
            notes = str(getattr(row, "notes", "") or "").strip()
            if notes:
                desc_parts.append(f"Notes: {notes}")
            _add_event(uid, fu_date, summary, "\n".join(desc_parts))

    # --- Application deadlines ---
    if include_deadlines and not active_apps.empty and "deadline" in active_apps.columns:
        dl_rows = active_apps.dropna(subset=["deadline"])
        for row in dl_rows.itertuples():
            dl_date: _dt.date = (
                row.deadline.date()
                if hasattr(row.deadline, "date")
                else row.deadline
            )
            if not include_past and dl_date < today_d:
                continue
            uid = f"app-{row.id}-deadline@ktproject"
            summary = f"Deadline: {row.company} - {row.role}"
            desc_parts = [f"Status: {row.status}"]
            notes = str(getattr(row, "notes", "") or "").strip()
            if notes:
                desc_parts.append(f"Notes: {notes}")
            _add_event(uid, dl_date, summary, "\n".join(desc_parts))

    # --- Interview stages (Scheduled or Pending only) ---
    if include_interviews and stages_df is not None and not stages_df.empty:
        sched = stages_df[stages_df["outcome"].isin({"Scheduled", "Pending"})]
        sched = sched.dropna(subset=["stage_date"])
        if not sched.empty and not applications_df.empty:
            # Build a lookup of active (non-Rejected/Withdrawn) applications
            active_map = applications_df[
                ~applications_df["status"].isin({"Rejected", "Withdrawn"})
            ].set_index("id")[["company", "role", "status"]].to_dict("index")

            for row in sched.itertuples():
                app_info = active_map.get(int(row.application_id))
                if not app_info:
                    continue
                st_date: _dt.date = (
                    row.stage_date.date()
                    if hasattr(row.stage_date, "date")
                    else row.stage_date
                )
                if not include_past and st_date < today_d:
                    continue
                uid = f"stage-{row.id}@ktproject"
                company = app_info["company"]
                role    = app_info["role"]
                summary = f"Interview ({row.stage}): {company} - {role}"
                desc_parts = [
                    f"Stage: {row.stage}",
                    f"Outcome: {row.outcome}",
                    f"Application status: {app_info['status']}",
                ]
                notes = str(getattr(row, "notes", "") or "").strip()
                if notes:
                    desc_parts.append(f"Notes: {notes}")
                _add_event(uid, st_date, summary, "\n".join(desc_parts))

    lines.append("END:VCALENDAR")
    return _CRLF.join(lines) + _CRLF


def event_ics(uid: str, summary: str, day, time_str: str | None = None,
              minutes: int = 60, description: str = "") -> str:
    """One calendar event. With a time it's a timed (local, floating) event; else all-day."""
    d = pd.Timestamp(day).date()
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0",
             "PRODID:-//KTProject//Internship Tracker//EN", "CALSCALE:GREGORIAN",
             "BEGIN:VEVENT", _fold(f"UID:{_escape(uid)}"), f"DTSTAMP:{_dtstamp()}"]
    if time_str:
        hh, mm = str(time_str)[:5].split(":")
        start = _dt.datetime.combine(d, _dt.time(int(hh), int(mm)))
        end = start + _dt.timedelta(minutes=minutes)
        lines += [f"DTSTART:{start:%Y%m%dT%H%M%S}", f"DTEND:{end:%Y%m%dT%H%M%S}",
                  "BEGIN:VALARM", "TRIGGER:-PT30M", "ACTION:DISPLAY",
                  _fold(f"DESCRIPTION:{_escape(summary)}"), "END:VALARM"]
    else:
        lines += [f"DTSTART;VALUE=DATE:{_fmt_date(d)}",
                  f"DTEND;VALUE=DATE:{_fmt_date(d + _dt.timedelta(days=1))}"]
    lines.append(_fold(f"SUMMARY:{_escape(summary)}"))
    if description:
        lines.append(_fold(f"DESCRIPTION:{_escape(description)}"))
    lines += ["END:VEVENT", "END:VCALENDAR"]
    return _CRLF.join(lines) + _CRLF
