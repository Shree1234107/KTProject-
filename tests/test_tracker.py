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
    assert f["pct_step_interviewed"] == 0.0
    assert f["pct_step_offered"] == 0.0


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
    assert abs(f["pct_step_interviewed"] - 0.5) < 1e-9   # 2/4
    assert abs(f["pct_step_offered"]     - 0.5) < 1e-9   # 1/2


def test_funnel_no_division_by_zero():
    df = pd.DataFrame({"status": ["Wishlist", "Wishlist"]})
    f = analytics.funnel(df)
    assert f["applied"] == 0 and f["pct_offered"] == 0.0
    assert f["pct_step_interviewed"] == 0.0 and f["pct_step_offered"] == 0.0


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


def test_period_comparison_below_threshold():
    # Both windows have data but fewer than 5 submitted apps each → no trend
    df = pd.DataFrame({
        "id": [1, 2],
        "status": ["Applied", "Interview"],
        "date_applied": [
            pd.Timestamp("2026-05-20"),  # current window (last 30d from 2026-06-01)
            pd.Timestamp("2026-04-15"),  # previous window (30-60d ago)
        ],
    })
    pc = analytics.period_comparison(df, today="2026-06-01", days=30)
    assert pc["has_trend"] is False   # < 5 submitted in each window
    assert pc["current"] is not None
    assert pc["current"]["total"] == 1
    assert pc["previous"] is not None
    assert pc["previous"]["total"] == 1


def test_period_comparison_has_trend_above_threshold():
    # 5+ submitted (non-Wishlist) apps in each window → has_trend True
    dates_curr = [pd.Timestamp("2026-05-20") + pd.Timedelta(days=i) for i in range(5)]
    dates_prev = [pd.Timestamp("2026-04-10") + pd.Timedelta(days=i) for i in range(5)]
    df = pd.DataFrame({
        "id": range(10),
        "status": ["Applied"] * 10,
        "date_applied": dates_curr + dates_prev,
    })
    pc = analytics.period_comparison(df, today="2026-06-01", days=30)
    assert pc["has_trend"] is True
    assert pc["current"]["total"] == 5
    assert pc["previous"]["total"] == 5


# ---------------------------------------------------------------------------
# Feature: Interview stages — db CRUD
# ---------------------------------------------------------------------------

def test_add_and_load_stage(conn):
    app_id = db.add_application(conn, "ACME", "Eng")
    stage_id = db.add_stage(conn, app_id, "Technical", "2026-06-01", "Passed", "Good interview")
    assert isinstance(stage_id, int)
    stages = db.load_stages(conn, app_id)
    assert len(stages) == 1
    row = stages.iloc[0]
    assert row["stage"] == "Technical"
    assert row["outcome"] == "Passed"
    assert row["notes"] == "Good interview"


def test_add_stage_defaults_to_scheduled(conn):
    app_id = db.add_application(conn, "ACME", "Eng")
    db.add_stage(conn, app_id, "Recruiter screen")
    stages = db.load_stages(conn, app_id)
    assert stages.iloc[0]["outcome"] == "Scheduled"


def test_update_stage(conn):
    app_id = db.add_application(conn, "ACME", "Eng")
    stage_id = db.add_stage(conn, app_id, "Technical", "2026-06-01", "Scheduled")
    db.update_stage(conn, stage_id, outcome="Passed")
    stages = db.load_stages(conn, app_id)
    assert stages.iloc[0]["outcome"] == "Passed"


def test_delete_stage(conn):
    app_id = db.add_application(conn, "ACME", "Eng")
    stage_id = db.add_stage(conn, app_id, "Technical", "2026-06-01", "Passed")
    db.delete_stage(conn, stage_id)
    assert db.load_stages(conn, app_id).empty


def test_load_stages_all(conn):
    id1 = db.add_application(conn, "ACME1", "Eng")
    id2 = db.add_application(conn, "ACME2", "Eng")
    db.add_stage(conn, id1, "Technical")
    db.add_stage(conn, id2, "Behavioral")
    all_stages = db.load_stages(conn)
    assert len(all_stages) == 2


def test_delete_application_cascades_stages(conn):
    app_id = db.add_application(conn, "ACME", "Eng")
    db.add_stage(conn, app_id, "Technical", "2026-06-01", "Passed")
    db.delete_application(conn, app_id)
    assert db.load_stages(conn).empty
    assert db.load_applications(conn).empty


def test_stage_validates_type(conn):
    app_id = db.add_application(conn, "ACME", "Eng")
    with pytest.raises(ValueError, match="Invalid stage type"):
        db.add_stage(conn, app_id, "InvalidType")


def test_stage_validates_outcome(conn):
    app_id = db.add_application(conn, "ACME", "Eng")
    with pytest.raises(ValueError, match="Invalid outcome"):
        db.add_stage(conn, app_id, "Technical", outcome="Done")


def test_stage_validates_app_exists(conn):
    with pytest.raises(ValueError, match="not found"):
        db.add_stage(conn, 999999, "Technical")


def test_update_stage_validates_type(conn):
    app_id = db.add_application(conn, "ACME", "Eng")
    stage_id = db.add_stage(conn, app_id, "Technical")
    with pytest.raises(ValueError, match="Invalid stage type"):
        db.update_stage(conn, stage_id, stage="Bogus")


def test_update_stage_validates_outcome(conn):
    app_id = db.add_application(conn, "ACME", "Eng")
    stage_id = db.add_stage(conn, app_id, "Technical")
    with pytest.raises(ValueError, match="Invalid outcome"):
        db.update_stage(conn, stage_id, outcome="Done")


def test_clear_sample_data_removes_stages(conn):
    app_id = db.add_application(conn, "RealCo", "Eng")
    db.add_stage(conn, app_id, "Technical", is_sample=False)
    db.load_sample_data(conn)
    db.clear_sample_data(conn)
    # Real app + its stage must survive
    assert len(db.load_applications(conn)) == 1
    stages = db.load_stages(conn)
    assert all(not bool(r["is_sample"]) for _, r in stages.iterrows())


def test_clear_all_data_removes_stages(conn):
    app_id = db.add_application(conn, "ACME", "Eng")
    db.add_stage(conn, app_id, "Technical")
    db.clear_all_data(conn)
    assert db.load_applications(conn).empty
    assert db.load_stages(conn).empty


# ---------------------------------------------------------------------------
# Feature: Interview stages — analytics
# ---------------------------------------------------------------------------

def test_summary_counts_stage_app_as_responded(conn):
    app_id = db.add_application(conn, "ACME", "Eng", status="Applied")
    db.add_stage(conn, app_id, "Recruiter screen", "2026-06-01", "Scheduled")
    df = db.load_applications(conn)
    stages = db.load_stages(conn)
    s = analytics.summary(df, stages)
    assert s["response_rate"] == 1.0


def test_summary_counts_stage_app_as_interviewed(conn):
    app_id = db.add_application(conn, "ACME", "Eng", status="Applied")
    db.add_stage(conn, app_id, "Technical", "2026-06-01", "Passed")
    df = db.load_applications(conn)
    stages = db.load_stages(conn)
    s = analytics.summary(df, stages)
    assert s["interview_rate"] == 1.0


def test_summary_no_double_counting_with_stages(conn):
    # App already at Interview: should still count exactly once
    app_id = db.add_application(conn, "ACME", "Eng", status="Interview")
    db.add_stage(conn, app_id, "Technical", "2026-06-01", "Passed")
    df = db.load_applications(conn)
    stages = db.load_stages(conn)
    s = analytics.summary(df, stages)
    assert s["response_rate"] == 1.0
    assert s["interview_rate"] == 1.0


def test_funnel_counts_stage_app(conn):
    # Applied-status app with a stage should count as responded AND interviewed
    app_id = db.add_application(conn, "ACME", "Eng", status="Applied")
    db.add_stage(conn, app_id, "Technical", "2026-06-01", "Passed")
    df = db.load_applications(conn)
    stages = db.load_stages(conn)
    f = analytics.funnel(df, stages)
    assert f["responded"] == 1
    assert f["interviewed"] == 1


def test_stage_pass_rates_empty():
    pr = analytics.stage_pass_rates(pd.DataFrame(columns=["stage", "outcome"]))
    assert pr.empty


def test_stage_pass_rates_basic():
    stages = pd.DataFrame({
        "stage":   ["Technical", "Technical", "Technical"],
        "outcome": ["Passed",    "Failed",    "Pending"],
    })
    pr = analytics.stage_pass_rates(stages)
    row = pr[pr["stage"] == "Technical"].iloc[0]
    assert row["passed"]  == 1
    assert row["failed"]  == 1
    assert row["pending"] == 1
    assert abs(row["pass_rate"] - 0.5) < 1e-9


def test_stage_pass_rates_undecided_only():
    stages = pd.DataFrame({
        "stage":   ["Recruiter screen"],
        "outcome": ["Scheduled"],
    })
    pr = analytics.stage_pass_rates(stages)
    row = pr[pr["stage"] == "Recruiter screen"].iloc[0]
    assert row["pass_rate"] is None
    assert row["pending"] == 1


def test_stage_pass_rates_respects_stage_type_order():
    stages = pd.DataFrame({
        "stage":   ["Onsite/Final", "Technical"],
        "outcome": ["Passed",       "Passed"],
    })
    pr = analytics.stage_pass_rates(stages)
    # Order should follow STAGE_TYPES (Technical before Onsite/Final)
    idx_tech   = pr[pr["stage"] == "Technical"].index[0]
    idx_onsite = pr[pr["stage"] == "Onsite/Final"].index[0]
    assert idx_tech < idx_onsite


# ---------------------------------------------------------------------------
# Feature: Resume match scores — db CRUD
# ---------------------------------------------------------------------------

def test_add_and_load_match_score(conn):
    app_id = db.add_application(conn, "ACME", "Eng")
    db.add_match_score(conn, app_id, 72.0, 68.0, 78.0, 15, 4,
                       ["kubernetes", "terraform"], "demo.pdf")
    scores = db.load_match_scores(conn, app_id)
    assert len(scores) == 1
    row = scores.iloc[0]
    assert row["overall_score"] == 72.0
    assert row["keyword_score"] == 68.0
    assert row["resume_label"] == "demo.pdf"


def test_delete_match_score(conn):
    app_id = db.add_application(conn, "ACME", "Eng")
    db.add_match_score(conn, app_id, 72.0, 68.0, 78.0, 15, 4, [], "demo")
    scores = db.load_match_scores(conn, app_id)
    score_id = int(scores.iloc[0]["id"])
    db.delete_match_score(conn, score_id)
    assert db.load_match_scores(conn, app_id).empty


def test_delete_application_cascades_match_scores(conn):
    app_id = db.add_application(conn, "ACME", "Eng")
    db.add_match_score(conn, app_id, 72.0, 68.0, 78.0, 15, 4, [], "demo")
    db.delete_application(conn, app_id)
    assert db.load_match_scores(conn).empty


def test_match_score_validates_app_exists(conn):
    with pytest.raises(ValueError, match="not found"):
        db.add_match_score(conn, 999999, 72.0, 68.0, 78.0, 15, 4, [], "demo")


def test_load_match_scores_all(conn):
    id1 = db.add_application(conn, "Co1", "Eng")
    id2 = db.add_application(conn, "Co2", "Eng")
    db.add_match_score(conn, id1, 60.0, 58.0, 64.0, 10, 5, [], "r1")
    db.add_match_score(conn, id2, 80.0, 78.0, 84.0, 18, 2, [], "r2")
    all_scores = db.load_match_scores(conn)
    assert len(all_scores) == 2


def test_clear_all_data_removes_match_scores(conn):
    app_id = db.add_application(conn, "ACME", "Eng")
    db.add_match_score(conn, app_id, 72.0, 68.0, 78.0, 15, 4, [], "demo")
    db.clear_all_data(conn)
    assert db.load_match_scores(conn).empty


def test_clear_sample_data_removes_sample_scores(conn):
    app_id = db.add_application(conn, "RealCo", "Eng")
    db.add_match_score(conn, app_id, 72.0, 68.0, 78.0, 15, 4, [], "demo", is_sample=False)
    db.load_sample_data(conn)
    db.clear_sample_data(conn)
    # Real score must survive
    scores = db.load_match_scores(conn)
    assert len(scores) == 1
    assert not bool(scores.iloc[0]["is_sample"])


# ---------------------------------------------------------------------------
# Feature: Resume match scores — analytics
# ---------------------------------------------------------------------------

def test_latest_match_scores_returns_most_recent():
    scores = pd.DataFrame({
        "application_id": [1, 1],
        "overall_score":  [60.0, 72.0],
        "scanned_at": [pd.Timestamp("2026-01-01"), pd.Timestamp("2026-02-01")],
    })
    latest = analytics.latest_match_scores(scores)
    assert len(latest) == 1
    assert latest.iloc[0]["overall_score"] == 72.0


def test_latest_match_scores_multiple_apps():
    scores = pd.DataFrame({
        "application_id": [1, 2, 1],
        "overall_score":  [60.0, 80.0, 72.0],
        "scanned_at": [
            pd.Timestamp("2026-01-01"),
            pd.Timestamp("2026-01-15"),
            pd.Timestamp("2026-02-01"),
        ],
    })
    latest = analytics.latest_match_scores(scores)
    assert len(latest) == 2
    score_map = dict(zip(latest["application_id"], latest["overall_score"]))
    assert score_map[1] == 72.0
    assert score_map[2] == 80.0


def test_latest_match_scores_empty():
    result = analytics.latest_match_scores(pd.DataFrame())
    assert result.empty


def test_weekly_counts_includes_empty_weeks():
    df = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "status": ["Applied", "Applied", "Wishlist", "Offer"],
        "date_applied": pd.to_datetime(["2026-11-10", "2026-11-12", "2026-11-11", "2026-10-20"]),
        "source": ["a", "b", "c", "d"],
    })
    wc = analytics.weekly_counts(df, today="2026-11-16", weeks=12)
    assert len(wc) == 12
    assert wc["week_start"].iloc[-1] == pd.Timestamp("2026-11-16")   # this Monday
    assert wc["week_start"].iloc[-2] == pd.Timestamp("2026-11-09")
    assert wc["count"].iloc[-2] == 2           # Wishlist not counted
    assert wc["count"].iloc[-1] == 0
    assert wc.loc[wc.week_start == pd.Timestamp("2026-10-19"), "count"].item() == 1
    assert wc["count"].sum() == 3


def test_response_by_source_ranks_by_rate():
    df = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "status": ["Interview", "Applied", "Rejected", "Applied", "Wishlist"],
        "date_applied": pd.to_datetime(["2026-11-01"] * 5),
        "source": ["Referral", "LinkedIn", "LinkedIn", "Website", "Referral"],
    })
    r = analytics.response_by_source(df)
    assert list(r["source"]) == ["Referral", "LinkedIn", "Website"]
    assert r.loc[0, "rate"] == 1.0 and r.loc[0, "submitted"] == 1   # Wishlist excluded
    assert r.loc[1, "responded"] == 1 and r.loc[1, "submitted"] == 2
    assert r.loc[2, "rate"] == 0.0


def test_response_by_source_empty():
    df = pd.DataFrame({"id": [1], "status": ["Applied"], "date_applied": [pd.NaT], "source": [""]})
    assert analytics.response_by_source(df).empty
