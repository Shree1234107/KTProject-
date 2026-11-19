import datetime as dt
import io
import json

import pandas as pd

from tracker import assistant

APPS = pd.DataFrame([
    {"company": "Acme", "role": "Finance Intern", "status": "Interview",
     "date_applied": "2026-11-01", "deadline": None, "follow_up_date": "2026-11-20",
     "notes": "Phone screen went well", "is_sample": 0},
    {"company": "Old Co", "role": "Analyst", "status": "Rejected",
     "date_applied": "2026-10-01", "deadline": None, "follow_up_date": None,
     "notes": None, "is_sample": 0},
    {"company": "Sample Inc", "role": "Demo", "status": "Applied",
     "date_applied": "2026-10-05", "deadline": None, "follow_up_date": None,
     "notes": None, "is_sample": 1},
])
TASKS = pd.DataFrame([{"title": "Send thank-you note", "due_date": "2026-11-20", "done": 0},
                      {"title": "Old task", "due_date": None, "done": 1}])


def test_summary_lists_real_apps_active_first_and_open_tasks():
    s = assistant.tracker_summary(APPS, TASKS, today=dt.date(2026, 11, 19))
    assert "2 applications" in s and "Sample Inc" not in s
    assert s.index("Acme") < s.index("Old Co")
    assert "follow up 2026-11-20" in s and "Phone screen went well" in s
    assert "Send thank-you note [not tied to a job] (due 2026-11-20)" in s and "Old task" not in s


def test_empty_tracker():
    assert "hasn't added" in assistant.tracker_summary(pd.DataFrame())


def test_build_messages_puts_system_first():
    hist = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    msgs = assistant.build_messages("SYS", hist)
    assert msgs[0] == {"role": "system", "content": "SYS"} and msgs[1:] == hist


def test_stream_reply_yields_pieces(monkeypatch):
    lines = [json.dumps({"message": {"content": p}, "done": False}).encode() + b"\n"
             for p in ("Hel", "lo")] + [b'{"done": true}\n']

    class Resp(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): pass

    seen = {}
    def fake_urlopen(req, timeout):
        seen["body"] = json.loads(req.data)
        return Resp(b"".join(lines))
    monkeypatch.setattr(assistant.urllib.request, "urlopen", fake_urlopen)
    assert "".join(assistant.stream_reply("m", [{"role": "user", "content": "x"}])) == "Hello"
    assert seen["body"]["stream"] is True and seen["body"]["model"] == "m"
