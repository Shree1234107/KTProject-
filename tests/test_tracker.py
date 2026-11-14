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
    db.add_application(conn, "R1", "Eng", status="Interview", referral_name="Bob")
    db.add_application(conn, "R2", "Eng", status="Applied",   referral_name="Carol")
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


# ---------------------------------------------------------------------------
# Feature 2: follow-up reminders
# ---------------------------------------------------------------------------

def _make_reminder_df():
    today = pd.Timestamp("2026-06-01")
    return pd.DataFrame({
        "id":             [1,            2,            3],
        "company":        ["A",          "B",          "C"],
        "role":           ["R",          "R",          "R"],
        "status":         ["Applied",    "Applied",    "Applied"],
        "follow_up_date": [
            today - pd.Timedelta(days=1),
            today,
            today + pd.Timedelta(days=5),
        ],
    })


def test_reminders_groups():
    df = _make_reminder_df()
    result = analytics.reminders(df, today="2026-06-01")
    assert len(result["overdue"]) == 1 and result["overdue"].iloc[0]["company"] == "A"
    assert len(result["due_today"]) == 1 and result["due_today"].iloc[0]["company"] == "B"
    assert len(result["upcoming"]) == 1 and result["upcoming"].iloc[0]["company"] == "C"


def test_reminders_ignores_rejected_withdrawn():
    today = pd.Timestamp("2026-06-01")
    df = pd.DataFrame({
        "id": [1, 2],
        "company": ["X", "Y"],
        "role": ["R", "R"],
        "status": ["Rejected", "Withdrawn"],
        "follow_up_date": [today - pd.Timedelta(days=1), today - pd.Timedelta(days=1)],
    })
    result = analytics.reminders(df, today="2026-06-01")
    assert result["overdue"].empty
    assert result["due_today"].empty
    assert result["upcoming"].empty


def test_reminders_no_column():
    df = pd.DataFrame({"id": [1], "company": ["X"], "status": ["Applied"]})
    result = analytics.reminders(df, today="2026-06-01")
    assert result["overdue"].empty and result["due_today"].empty and result["upcoming"].empty


def test_stale_applications():
    today = pd.Timestamp("2026-06-01")
    df = pd.DataFrame({
        "id": [1, 2],
        "company": ["A", "B"],
        "role": ["R", "R"],
        "status": ["Applied", "Applied"],
        "date_applied": [
            today - pd.Timedelta(days=25),
            today - pd.Timedelta(days=10),
        ],
    })
    result = analytics.stale_applications(df, today="2026-06-01", days=21)
    assert len(result) == 1
    assert result.iloc[0]["company"] == "A"


def test_stale_has_days_waiting_column():
    today = pd.Timestamp("2026-06-01")
    df = pd.DataFrame({
        "id": [1],
        "company": ["A"],
        "role": ["R"],
        "status": ["Applied"],
        "date_applied": [today - pd.Timedelta(days=30)],
    })
    result = analytics.stale_applications(df, today="2026-06-01", days=21)
    assert "days_waiting" in result.columns
    assert result.iloc[0]["days_waiting"] == 30


# ---------------------------------------------------------------------------
# Feature 3: sample data
# ---------------------------------------------------------------------------

def test_load_sample_data(conn):
    n = db.load_sample_data(conn)
    assert n >= 15
    df = db.load_applications(conn)
    assert len(df) == n
    assert df["is_sample"].astype(bool).all()


def test_clear_sample_data(conn):
    db.add_application(conn, "RealCo", "Eng")  # a real row
    db.load_sample_data(conn)
    db.clear_sample_data(conn)
    df = db.load_applications(conn)
    assert not df["is_sample"].astype(bool).any(), "sample rows still present"
    assert len(df) == 1  # real row survived
    assert df.iloc[0]["company"] == "RealCo"


def test_clear_all_data(conn):
    db.add_application(conn, "X", "Y")
    db.load_sample_data(conn)
    db.clear_all_data(conn)
    assert db.load_applications(conn).empty


# ---------------------------------------------------------------------------
# Feature: Kanban board — next_status / prev_status
# ---------------------------------------------------------------------------

def test_next_status():
    assert analytics.next_status("Wishlist")  == "Applied"
    assert analytics.next_status("Applied")   == "OA/Screen"
    assert analytics.next_status("OA/Screen") == "Interview"
    assert analytics.next_status("Interview") == "Offer"
    assert analytics.next_status("Offer")     is None
    assert analytics.next_status("Rejected")  is None
    assert analytics.next_status("Withdrawn") is None
    assert analytics.next_status("Bogus")     is None


def test_prev_status():
    assert analytics.prev_status("Wishlist")  is None
    assert analytics.prev_status("Applied")   == "Wishlist"
    assert analytics.prev_status("OA/Screen") == "Applied"
    assert analytics.prev_status("Interview") == "OA/Screen"
    assert analytics.prev_status("Offer")     == "Interview"
    assert analytics.prev_status("Rejected")  is None
    assert analytics.prev_status("Withdrawn") is None


# ---------------------------------------------------------------------------
# Feature: Application heatmap — applications_per_day
# ---------------------------------------------------------------------------

def test_applications_per_day_empty():
    df = pd.DataFrame(columns=["status", "date_applied"])
    result = analytics.applications_per_day(df, today="2026-06-01")
    assert result == {}


def test_applications_per_day_wishlist_excluded():
    df = pd.DataFrame({
        "id": [1],
        "status": ["Wishlist"],
        "date_applied": [pd.Timestamp("2026-05-20")],
    })
    result = analytics.applications_per_day(df, today="2026-06-01", weeks=26)
    assert result == {}


def test_applications_per_day_outside_window():
    df = pd.DataFrame({
        "id": [1],
        "status": ["Applied"],
        "date_applied": [pd.Timestamp("2020-01-01")],  # far outside 26 weeks
    })
    result = analytics.applications_per_day(df, today="2026-06-01", weeks=26)
    assert result == {}


def test_applications_per_day_counts():
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "status": ["Applied", "Applied", "Interview"],
        "date_applied": [
            pd.Timestamp("2026-05-20"),
            pd.Timestamp("2026-05-20"),
            pd.Timestamp("2026-05-21"),
        ],
    })
    result = analytics.applications_per_day(df, today="2026-06-01", weeks=26)
    import datetime
    assert result[datetime.date(2026, 5, 20)] == 2
    assert result[datetime.date(2026, 5, 21)] == 1


# ---------------------------------------------------------------------------
# Feature: Funnel chart — funnel()
# ---------------------------------------------------------------------------

def test_funnel_empty():
    f = analytics.funnel(pd.DataFrame(columns=["status"]))
    assert f["applied"] == 0
    assert f["pct_responded"] == 0.0


def test_funnel_basic(conn):
    db.add_application(conn, "A", "R", status="Applied")
    db.add_application(conn, "B", "R", status="OA/Screen")
    db.add_application(conn, "C", "R", status="Interview")
    db.add_application(conn, "D", "R", status="Offer")
    db.add_application(conn, "E", "R", status="Rejected")
    db.add_application(conn, "W", "R", status="Wishlist")  # excluded
    df = db.load_applications(conn)
    f = analytics.funnel(df)
    assert f["applied"]     == 5   # A B C D E (not W)
    assert f["responded"]   == 4   # B C D E
    assert f["interviewed"] == 2   # C D
    assert f["offered"]     == 1   # D
    assert abs(f["pct_responded"] - 0.8) < 1e-9


def test_funnel_no_division_by_zero():
    df = pd.DataFrame({"status": ["Wishlist", "Wishlist"]})
    f = analytics.funnel(df)
    assert f["applied"] == 0 and f["pct_offered"] == 0.0


# ---------------------------------------------------------------------------
# Feature: Weekly goal — weekly_progress, goal_streak, settings
# ---------------------------------------------------------------------------

def test_weekly_progress_counts_this_week():
    # Monday 2026-06-01
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "status": ["Applied", "Applied", "Wishlist"],
        "date_applied": [
            pd.Timestamp("2026-06-01"),  # this week
            pd.Timestamp("2026-06-03"),  # this week
            pd.Timestamp("2026-06-01"),  # Wishlist — excluded
        ],
    })
    wp = analytics.weekly_progress(df, goal=5, today="2026-06-04")  # Thursday
    assert wp["count"] == 2
    assert wp["met"] is False


def test_weekly_progress_met():
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "status": ["Applied", "Applied", "Applied"],
        "date_applied": [
            pd.Timestamp("2026-06-01"),
            pd.Timestamp("2026-06-02"),
            pd.Timestamp("2026-06-03"),
        ],
    })
    wp = analytics.weekly_progress(df, goal=3, today="2026-06-04")
    assert wp["met"] is True


def test_goal_streak_basic():
    # Provide 3 consecutive weeks with enough apps
    df = pd.DataFrame({
        "id": range(6),
        "status": ["Applied"] * 6,
        "date_applied": [
            pd.Timestamp("2026-05-18"),  # 2 weeks ago Mon
            pd.Timestamp("2026-05-19"),
            pd.Timestamp("2026-05-25"),  # last week Mon
            pd.Timestamp("2026-05-26"),
            pd.Timestamp("2026-06-01"),  # this week Mon
            pd.Timestamp("2026-06-02"),
        ],
    })
    result = analytics.goal_streak(df, goal=2, today="2026-06-04")
    assert result["current"] == 3
    assert result["longest"] >= 3


def test_goal_streak_broken():
    # Gap in the middle (week of May 25 has only 1 app, goal is 2)
    df = pd.DataFrame({
        "id": range(5),
        "status": ["Applied"] * 5,
        "date_applied": [
            pd.Timestamp("2026-05-18"),  # 2 weeks ago — 2 apps
            pd.Timestamp("2026-05-19"),
            pd.Timestamp("2026-05-25"),  # last week — 1 app (not met)
            pd.Timestamp("2026-06-01"),  # this week — 2 apps (met)
            pd.Timestamp("2026-06-02"),
        ],
    })
    result = analytics.goal_streak(df, goal=2, today="2026-06-04")
    # Current streak: this week met (1), last week not met → streak = 1
    assert result["current"] == 1


def test_goal_streak_empty():
    df = pd.DataFrame(columns=["status", "date_applied"])
    result = analytics.goal_streak(df, goal=5, today="2026-06-01")
    assert result["current"] == 0 and result["longest"] == 0


def test_settings_get_set(conn):
    assert db.get_setting(conn, "weekly_goal", "10") == "10"
    db.set_setting(conn, "weekly_goal", "7")
    assert db.get_setting(conn, "weekly_goal", "10") == "7"
    # Update existing key
    db.set_setting(conn, "weekly_goal", "15")
    assert db.get_setting(conn, "weekly_goal") == "15"


# ---------------------------------------------------------------------------
# Feature: Period comparison — period_comparison
# ---------------------------------------------------------------------------

def test_period_comparison_no_data():
    df = pd.DataFrame(columns=["status", "date_applied"])
    pc = analytics.period_comparison(df, today="2026-06-01")
    assert pc["has_trend"] is False
    assert pc["current"] is None and pc["previous"] is None


def test_period_comparison_only_current():
    df = pd.DataFrame({
        "id": [1],
        "status": ["Applied"],
        "date_applied": [pd.Timestamp("2026-05-20")],  # within last 30 days of 2026-06-01
    })
    pc = analytics.period_comparison(df, today="2026-06-01", days=30)
    assert pc["has_trend"] is False   # no data in previous window
    assert pc["current"] is not None
    assert pc["current"]["total"] == 1


def test_period_comparison_both_windows():
    df = pd.DataFrame({
        "id": [1, 2],
        "status": ["Applied", "Interview"],
        "date_applied": [
            pd.Timestamp("2026-05-20"),  # current window (last 30d from 2026-06-01)
            pd.Timestamp("2026-04-15"),  # previous window (30-60d ago)
        ],
    })
    pc = analytics.period_comparison(df, today="2026-06-01", days=30)
    assert pc["has_trend"] is True
    assert pc["current"]["total"] == 1
    assert pc["previous"]["total"] == 1
