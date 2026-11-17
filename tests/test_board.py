"""Board: status history, timeline and days-in-stage."""
import pandas as pd

from tracker import analytics, db


def _conn(tmp_path):
    return db.connect(tmp_path / "t.db")


def test_add_records_initial_status(tmp_path):
    c = _conn(tmp_path)
    a = db.add_application(c, "Acme", "Intern", status="Applied", date_applied="2026-11-01")
    h = db.load_status_history(c, a)
    assert list(h["status"]) == ["Applied"]
    assert h["changed_on"].iloc[0] == pd.Timestamp("2026-11-01")


def test_status_change_appends_and_same_status_does_not(tmp_path):
    c = _conn(tmp_path)
    a = db.add_application(c, "Acme", "Intern", status="Wishlist")
    db.update_application(c, a, status="Applied")
    db.update_application(c, a, status="Applied")
    db.update_application(c, a, notes="hi")
    assert list(db.load_status_history(c, a)["status"]) == ["Wishlist", "Applied"]


def test_delete_and_clear_remove_history(tmp_path):
    c = _conn(tmp_path)
    a = db.add_application(c, "Acme", "Intern")
    b = db.add_application(c, "Beta", "Intern")
    db.delete_application(c, a)
    assert set(db.load_status_history(c)["application_id"]) == {b}
    db.clear_all_data(c)
    assert db.load_status_history(c).empty


def test_timeline_falls_back_for_old_rows():
    empty = pd.DataFrame(columns=["application_id", "status", "changed_on"])
    tl = analytics.stage_timeline(empty, 1, "Interview", pd.Timestamp("2026-11-10"))
    assert tl == [("Interview", pd.Timestamp("2026-11-10"))]
    assert analytics.days_in_stage(tl, "2026-11-15") == 5
    assert analytics.days_in_stage([("Applied", pd.NaT)]) is None


def test_timeline_appends_untracked_current_status():
    h = pd.DataFrame({"application_id": [1], "status": ["Applied"],
                      "changed_on": [pd.Timestamp("2026-11-01")]})
    tl = analytics.stage_timeline(h, 1, "Offer")
    assert tl[-1] == ("Offer", None)
