import pandas as pd
from tracker import db, ics, macreminders as mac


def test_stage_time_saved_and_used_by_mac(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    aid = db.add_application(conn, "Mansfield", "Intern", status="Interview")
    sid = db.add_stage(conn, aid, db.STAGE_TYPES[0], "2030-01-05", "Scheduled", "", stage_time="14:30")
    st_df = db.load_stages(conn)
    assert st_df.loc[st_df.id == sid, "stage_time"].iloc[0] == "14:30"
    items = mac.desired_items(db.load_applications(conn), db.load_tasks(conn), st_df, {"st"}, "2030-01-01")
    assert items[f"st:{sid}"]["due"] == "2030-01-05T14:30:00"


def test_event_ics_timed_and_all_day():
    t = ics.event_ics("u1", "Interview, Acme", "2030-01-05", "14:30")
    assert "DTSTART:20300105T143000" in t and "DTEND:20300105T153000" in t and "VALARM" in t
    a = ics.event_ics("u2", "Interview", "2030-01-05")
    assert "DTSTART;VALUE=DATE:20300105" in a and "VALARM" not in a
