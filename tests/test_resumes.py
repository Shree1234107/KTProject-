import pytest
from tracker import db


def test_resume_versions(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    r1 = db.save_resume(conn, "Data v1", "python sql")
    assert db.save_resume(conn, "Data v1", "python sql tableau") == r1  # same name overwrites
    r2 = db.save_resume(conn, "SWE", "java")
    assert list(db.load_resumes(conn)["name"]) == ["Data v1", "SWE"]
    aid = db.add_application(conn, "Acme", "Intern")
    db.set_app_resume(conn, aid, r2)
    assert db.app_resumes(conn) == {aid: r2}
    db.delete_resume(conn, r2)
    assert db.app_resumes(conn) == {}
    with pytest.raises(ValueError):
        db.save_resume(conn, " ", "x")
