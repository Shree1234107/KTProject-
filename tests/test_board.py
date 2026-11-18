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


def test_is_stale_only_for_active_stages_past_threshold():
    assert analytics.is_stale("Applied", 21, 21)
    assert analytics.is_stale("Interview", 40, 21)
    assert not analytics.is_stale("Applied", 20, 21)
    assert not analytics.is_stale("Offer", 90, 21)
    assert not analytics.is_stale("Wishlist", 90, 21)
    assert not analytics.is_stale("Applied", None, 21)


def test_contacts_and_notes_roundtrip_and_cleanup(tmp_path):
    import pytest
    c = _conn(tmp_path)
    a = db.add_application(c, "Acme", "Intern")
    cid = db.add_contact(c, a, "Sam Lee", "Recruiter", "sam@acme.com", "2026-11-10")
    db.add_note(c, a, "first", "2026-11-01")
    db.add_note(c, a, "second", "2026-11-05")
    assert list(db.load_contacts(c, a)["name"]) == ["Sam Lee"]
    assert list(db.load_notes(c, a)["body"]) == ["second", "first"]  # newest first
    db.update_contact(c, cid, role="Hiring manager")
    assert db.load_contacts(c, a)["role"].iloc[0] == "Hiring manager"
    with pytest.raises(ValueError):
        db.add_contact(c, a, "  ")
    with pytest.raises(ValueError):
        db.add_note(c, a, " ")
    db.delete_application(c, a)
    assert db.load_contacts(c).empty and db.load_notes(c).empty
