from tracker import analytics, db


def test_first_response_days_and_past_entry(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    db.add_application(conn, "A", "R", status="Rejected", date_applied="2026-09-01",
                       source="LinkedIn", status_date="2026-09-11")
    db.add_application(conn, "B", "R", status="Interview", date_applied="2026-09-01",
                       source="Referral", status_date="2026-09-05")
    db.add_application(conn, "C", "R", status="Applied", date_applied="2026-09-01")
    h = db.load_status_history(conn)
    assert len(h) == 5
    r = analytics.first_response_days(db.load_applications(conn), h)
    assert sorted(r["days"]) == [4, 10]
    assert set(r["source"]) == {"LinkedIn", "Referral"}
