"""Tests for tracker.ics: RFC 5545 calendar builder."""
import pandas as pd
import pytest

from tracker.ics import build_ics

TODAY = "2026-06-01"
_EMPTY = pd.DataFrame()


def _apps(**overrides):
    defaults = {
        "id":             [1],
        "company":        ["ACME"],
        "role":           ["Eng Intern"],
        "status":         ["Applied"],
        "follow_up_date": [None],
        "deadline":       [None],
        "source":         [""],
        "notes":          [""],
    }
    defaults.update(overrides)
    return pd.DataFrame(defaults)


def _stages(**overrides):
    defaults = {
        "id":             [10],
        "application_id": [1],
        "stage":          ["Technical"],
        "stage_date":     [pd.Timestamp("2026-06-10")],
        "outcome":        ["Scheduled"],
        "notes":          [""],
    }
    defaults.update(overrides)
    return pd.DataFrame(defaults)


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------

def test_ics_valid_structure_empty():
    ics = build_ics(_EMPTY, _EMPTY, TODAY)
    assert ics.startswith("BEGIN:VCALENDAR\r\n")
    assert ics.rstrip("\r\n").endswith("END:VCALENDAR")
    assert "BEGIN:VEVENT" not in ics


def test_ics_begin_end_pairs_match():
    df = _apps(
        follow_up_date=[pd.Timestamp("2026-06-10")],
        deadline=[pd.Timestamp("2026-06-15")],
    )
    ics = build_ics(df, _EMPTY, TODAY)
    assert ics.count("BEGIN:VEVENT") == ics.count("END:VEVENT")
    assert ics.count("BEGIN:VEVENT") == 2


# ---------------------------------------------------------------------------
# CRLF line endings
# ---------------------------------------------------------------------------

def test_ics_crlf_line_endings():
    df = _apps(follow_up_date=[pd.Timestamp("2026-06-10")])
    ics = build_ics(df, _EMPTY, TODAY)
    # Split on CRLF; no line should contain a bare \n
    for line in ics.split("\r\n"):
        assert "\n" not in line


# ---------------------------------------------------------------------------
# DTSTART / DTEND
# ---------------------------------------------------------------------------

def test_ics_dtstart_dtend_followup():
    df = _apps(follow_up_date=[pd.Timestamp("2026-06-10")])
    ics = build_ics(df, _EMPTY, TODAY, include_deadlines=False, include_interviews=False)
    assert "DTSTART;VALUE=DATE:20260610" in ics
    assert "DTEND;VALUE=DATE:20260611" in ics


def test_ics_dtstart_dtend_deadline():
    df = _apps(deadline=[pd.Timestamp("2026-06-20")])
    ics = build_ics(df, _EMPTY, TODAY, include_followups=False, include_interviews=False)
    assert "DTSTART;VALUE=DATE:20260620" in ics
    assert "DTEND;VALUE=DATE:20260621" in ics


# ---------------------------------------------------------------------------
# Escaping
# ---------------------------------------------------------------------------

def test_ics_escapes_comma_in_summary():
    df = _apps(company=["Smith, Jones"], follow_up_date=[pd.Timestamp("2026-06-10")])
    ics = build_ics(df, _EMPTY, TODAY, include_deadlines=False, include_interviews=False)
    assert "Smith\\, Jones" in ics


def test_ics_escapes_semicolon_in_summary():
    df = _apps(role=["Dev; Lead"], follow_up_date=[pd.Timestamp("2026-06-10")])
    ics = build_ics(df, _EMPTY, TODAY, include_deadlines=False, include_interviews=False)
    assert "Dev\\; Lead" in ics


def test_ics_escapes_backslash():
    df = _apps(company=["A\\B"], follow_up_date=[pd.Timestamp("2026-06-10")])
    ics = build_ics(df, _EMPTY, TODAY, include_deadlines=False, include_interviews=False)
    assert "A\\\\B" in ics


# ---------------------------------------------------------------------------
# Line folding
# ---------------------------------------------------------------------------

def test_ics_folding_long_summary():
    # Company + role long enough to push SUMMARY past 75 octets
    df = _apps(
        company=["A" * 40],
        role=["B" * 40],
        follow_up_date=[pd.Timestamp("2026-06-10")],
    )
    ics = build_ics(df, _EMPTY, TODAY, include_deadlines=False, include_interviews=False)
    assert "\r\n " in ics  # at least one fold continuation line


def test_ics_short_lines_not_folded():
    df = _apps(follow_up_date=[pd.Timestamp("2026-06-10")])
    ics = build_ics(df, _EMPTY, TODAY, include_deadlines=False, include_interviews=False)
    for line in ics.split("\r\n"):
        assert len(line.encode("utf-8")) <= 75


# ---------------------------------------------------------------------------
# Stable UIDs
# ---------------------------------------------------------------------------

def test_ics_stable_uid():
    df = _apps(follow_up_date=[pd.Timestamp("2026-06-10")])
    ics1 = build_ics(df, _EMPTY, TODAY, include_deadlines=False, include_interviews=False)
    ics2 = build_ics(df, _EMPTY, TODAY, include_deadlines=False, include_interviews=False)
    uids1 = sorted(l for l in ics1.split("\r\n") if l.startswith("UID:"))
    uids2 = sorted(l for l in ics2.split("\r\n") if l.startswith("UID:"))
    assert uids1 == uids2


# ---------------------------------------------------------------------------
# Skipped statuses
# ---------------------------------------------------------------------------

def test_ics_skips_rejected_followup():
    df = _apps(status=["Rejected"], follow_up_date=[pd.Timestamp("2026-06-10")])
    ics = build_ics(df, _EMPTY, TODAY, include_deadlines=False, include_interviews=False)
    assert "BEGIN:VEVENT" not in ics


def test_ics_skips_withdrawn_deadline():
    df = _apps(status=["Withdrawn"], deadline=[pd.Timestamp("2026-06-15")])
    ics = build_ics(df, _EMPTY, TODAY, include_followups=False, include_interviews=False)
    assert "BEGIN:VEVENT" not in ics


# ---------------------------------------------------------------------------
# Past-date filtering
# ---------------------------------------------------------------------------

def test_ics_past_followup_filtered_by_default():
    df = _apps(follow_up_date=[pd.Timestamp("2026-05-01")])  # before TODAY
    ics = build_ics(df, _EMPTY, TODAY, include_deadlines=False,
                    include_interviews=False, include_past=False)
    assert "BEGIN:VEVENT" not in ics


def test_ics_past_followup_included_when_requested():
    df = _apps(follow_up_date=[pd.Timestamp("2026-05-01")])
    ics = build_ics(df, _EMPTY, TODAY, include_deadlines=False,
                    include_interviews=False, include_past=True)
    assert "BEGIN:VEVENT" in ics


def test_ics_today_date_is_included():
    df = _apps(follow_up_date=[pd.Timestamp(TODAY)])
    ics = build_ics(df, _EMPTY, TODAY, include_deadlines=False, include_interviews=False)
    assert "BEGIN:VEVENT" in ics


# ---------------------------------------------------------------------------
# Interview stages
# ---------------------------------------------------------------------------

def test_ics_interview_stage_scheduled():
    apps = _apps()
    stages = _stages(outcome=["Scheduled"])
    ics = build_ics(apps, stages, TODAY, include_followups=False, include_deadlines=False)
    assert "BEGIN:VEVENT" in ics
    assert "Interview (Technical)" in ics
    assert "20260610" in ics


def test_ics_interview_stage_pending():
    apps = _apps()
    stages = _stages(outcome=["Pending"])
    ics = build_ics(apps, stages, TODAY, include_followups=False, include_deadlines=False)
    assert "BEGIN:VEVENT" in ics


def test_ics_interview_stage_skips_passed():
    apps = _apps()
    stages = _stages(outcome=["Passed"])
    ics = build_ics(apps, stages, TODAY, include_followups=False, include_deadlines=False)
    assert "BEGIN:VEVENT" not in ics


def test_ics_interview_stage_skips_failed():
    apps = _apps()
    stages = _stages(outcome=["Failed"])
    ics = build_ics(apps, stages, TODAY, include_followups=False, include_deadlines=False)
    assert "BEGIN:VEVENT" not in ics


def test_ics_interview_stage_skips_rejected_app():
    apps = _apps(status=["Rejected"])
    stages = _stages(outcome=["Scheduled"])
    ics = build_ics(apps, stages, TODAY, include_followups=False, include_deadlines=False)
    assert "BEGIN:VEVENT" not in ics


def test_ics_interview_flag_off():
    apps = _apps()
    stages = _stages(outcome=["Scheduled"])
    ics = build_ics(apps, stages, TODAY,
                    include_followups=False, include_deadlines=False, include_interviews=False)
    assert "BEGIN:VEVENT" not in ics


# ---------------------------------------------------------------------------
# Flag combinations
# ---------------------------------------------------------------------------

def test_ics_all_flags_off_gives_empty():
    df = _apps(
        follow_up_date=[pd.Timestamp("2026-06-10")],
        deadline=[pd.Timestamp("2026-06-15")],
    )
    ics = build_ics(df, _stages(), TODAY,
                    include_followups=False, include_deadlines=False, include_interviews=False)
    assert "BEGIN:VEVENT" not in ics
