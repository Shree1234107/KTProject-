import datetime as dt

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
