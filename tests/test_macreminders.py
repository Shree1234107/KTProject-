"""Mac Reminders sync: what to send and how differences are resolved."""
import pandas as pd

from tracker import db
from tracker import macreminders as mac

W = {"name": "Thank-you note", "due": "2026-11-19T09:00:00", "body": ""}


def _link(rid="r1", title="Thank-you note", due="2026-11-19T09:00:00", state="open"):
    return {"reminder_id": rid, "title": title, "due": due, "state": state}


def test_new_item_is_created():
    p = mac.plan_sync({"task:1": W}, {}, {})
    assert p["create"] == [{"key": "task:1", **W}]


def test_ticked_off_on_mac_is_done_here():
    p = mac.plan_sync({"task:1": W}, {"task:1": _link()}, {"r1": True})
    assert p["done_here"] == ["task:1"] and not p["update"]


def test_done_here_ticks_off_on_mac():
    p = mac.plan_sync({}, {"task:1": _link()}, {"r1": False})
    assert p["update"] == [{"id": "r1", "completed": True}]
    assert p["link_state"]["task:1"] == "closed"


def test_snoozed_here_updates_and_reopens():
    later = {**W, "due": "2026-11-22T09:00:00"}
    p = mac.plan_sync({"fu:3": later}, {"fu:3": _link(due=W["due"])}, {"r1": True})
    assert p["update"][0]["due"] == later["due"] and p["update"][0]["completed"] is False
    assert not p["done_here"]


def test_deleted_on_mac_is_left_alone_unless_date_changes():
    p = mac.plan_sync({"task:1": W}, {"task:1": _link()}, {})
    assert not p["create"] and p["link_state"]["task:1"] == "gone"
    later = {**W, "due": "2026-11-25T09:00:00"}
    p = mac.plan_sync({"task:1": later}, {"task:1": _link()}, {})
    assert p["create"][0]["key"] == "task:1"


def test_desired_items_covers_each_kind(tmp_path):
    c = db.connect(tmp_path / "t.db")
    a = db.add_application(c, "Mansfield", "Logistics Analyst", status="Interview",
                           follow_up_date="2026-11-21", deadline="2026-11-30")
    b = db.add_application(c, "Acme", "Intern", status="Wishlist", deadline="2026-11-25")
    db.add_task(c, "Send a thank-you note", "2026-11-19", a, "10:30")
    db.add_stage(c, a, "Onsite/Final", "2026-11-24", "Scheduled")
    db.add_application(c, "Gone", "X", status="Rejected", follow_up_date="2026-11-21")
    items = mac.desired_items(db.load_applications(c), db.load_tasks(c), db.load_stages(c),
                              set(mac.KINDS), today="2026-11-18")
    assert items["task:1"]["name"] == "Send a thank-you note"
    assert items["task:1"]["due"] == "2026-11-19T10:30:00"
    assert "Mansfield" in items["task:1"]["body"]
    assert items[f"fu:{a}"]["name"] == "Follow up: Mansfield — Logistics Analyst"
    assert f"dl:{b}" in items and f"dl:{a}" not in items      # deadlines only before submitting
    assert any(k.startswith("st:") for k in items)
    assert not any("Gone" in v["name"] for v in items.values())
    only_tasks = mac.desired_items(db.load_applications(c), db.load_tasks(c), db.load_stages(c),
                                   {"task"}, today="2026-11-18")
    assert list(only_tasks) == ["task:1"]


def test_tasks_crud(tmp_path):
    c = db.connect(tmp_path / "t.db")
    t = db.add_task(c, "Email recruiter", "2026-11-20")
    assert len(db.load_tasks(c)) == 1
    db.set_task_done(c, t)
    assert db.load_tasks(c).empty and len(db.load_tasks(c, include_done=True)) == 1
    import pytest
    with pytest.raises(ValueError):
        db.add_task(c, " ", "2026-11-20")
