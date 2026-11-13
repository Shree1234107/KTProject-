import datetime as dt

import pandas as pd
import pytest

from tracker import analytics, db


@pytest.fixture
def conn(tmp_path):
    return db.connect(tmp_path / "t.db")


def seed(conn):
    db.add_application(conn, "A", "SWE Intern", status="Applied", date_applied=dt.date(2026, 1, 5), source="LinkedIn")
    db.add_application(conn, "B", "DS Intern", status="Interview", date_applied=dt.date(2026, 1, 6), source="LinkedIn")
    db.add_application(conn, "C", "PM Intern", status="Rejected", date_applied=dt.date(2026, 1, 13), source="Referral")
    db.add_application(conn, "D", "SWE Intern", status="Offer", date_applied=dt.date(2026, 1, 14))


# ---------------------------------------------------------------------------
# Existing tests (unchanged)
# ---------------------------------------------------------------------------

def test_crud(conn):
    i = db.add_application(conn, "X", "Y")
    db.update_application(conn, i, status="Offer")
    assert db.load_applications(conn).iloc[0]["status"] == "Offer"
    db.delete_application(conn, i)
    assert db.load_applications(conn).empty


def test_validation(conn):
    with pytest.raises(ValueError):
        db.add_application(conn, "", "Y")
    with pytest.raises(ValueError):
        db.add_application(conn, "X", "Y", status="Bogus")


def test_summary(conn):
    seed(conn)
    s = analytics.summary(db.load_applications(conn))
    assert s["total"] == 4 and s["offers"] == 1 and s["active"] == 2
    assert s["response_rate"] == 0.75
    assert s["interview_rate"] == 0.5


def test_empty_summary(conn):
    assert analytics.summary(db.load_applications(conn))["response_rate"] == 0.0


def test_weekly_and_source(conn):
    seed(conn)
    df = db.load_applications(conn)
    assert analytics.applications_per_week(df).sum() == 4
    assert analytics.by_source(df).iloc[0]["source"] == "LinkedIn"


def test_deadlines(conn):
    db.add_application(conn, "Z", "R", status="Applied", deadline=dt.date(2026, 1, 10))
    df = db.load_applications(conn)
    assert len(analytics.upcoming_deadlines(df, today="2026-01-05")) == 1
    assert analytics.upcoming_deadlines(df, today="2026-03-01").empty


# ---------------------------------------------------------------------------
# Feature 1: referral tracking
# ---------------------------------------------------------------------------

def test_referral_add_and_edit(conn):
    i = db.add_application(conn, "ACME", "Eng", referral_name="Alice", referral_contact="alice@acme.com")
    df = db.load_applications(conn)
    row = df[df["id"] == i].iloc[0]
    assert row["referral_name"] == "Alice"
    assert row["referral_contact"] == "alice@acme.com"

    db.update_application(conn, i, referral_name="Bob", referral_contact="bob@acme.com")
    df2 = db.load_applications(conn)
    row2 = df2[df2["id"] == i].iloc[0]
    assert row2["referral_name"] == "Bob"


def test_referral_comparison_basic(conn):
    # 2 referred: 1 Interview (responded + interviewed), 1 Applied (neither)
    db.add_application(conn, "R1", "Eng", status="Interview", referral_name="Bob")
    db.add_application(conn, "R2", "Eng", status="Applied",   referral_name="Carol")
    # 2 cold: 1 Rejected (responded), 1 Applied (neither)
    db.add_application(conn, "C1", "Eng", status="Rejected")
    db.add_application(conn, "C2", "Eng", status="Applied")

    df = db.load_applications(conn)
    rc = analytics.referral_comparison(df)

    assert rc["referred"]["count"] == 2
    assert rc["cold"]["count"] == 2
    assert rc["referred"]["response_rate"] == 0.5
    assert rc["cold"]["response_rate"] == 0.5
    assert rc["referred"]["interview_rate"] == 0.5
    assert rc["cold"]["interview_rate"] == 0.0


def test_referral_comparison_no_data(conn):
    rc = analytics.referral_comparison(db.load_applications(conn))
    assert rc["referred"]["count"] == 0
    assert rc["cold"]["response_rate"] == 0.0


def test_update_application_validates_company_role(conn):
    i = db.add_application(conn, "X", "Y")
    with pytest.raises(ValueError, match="Company"):
        db.update_application(conn, i, company="")
    with pytest.raises(ValueError, match="Role"):
        db.update_application(conn, i, role="   ")
