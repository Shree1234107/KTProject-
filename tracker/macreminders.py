"""Two-way sync with the Reminders app on macOS.

The tracker decides what *should* be in Reminders (``desired_items``), the
Mac says what *is* there (``fetch``), and ``plan_sync`` works out the
difference. Talking to Reminders goes through ``osascript -l JavaScript``,
which is built into macOS; nothing to install. The first time, macOS asks
for permission to control Reminders.

Rules:
* Something new in the tracker      -> a new reminder.
* Its title or date changes         -> the reminder is updated (and reopened).
* Ticked off in Reminders           -> done in the tracker (to-dos and follow-ups).
* Done or removed in the tracker    -> ticked off in Reminders.
* Deleted in Reminders              -> left alone until its date changes.
"""
from __future__ import annotations

import datetime as _dt
import json
import shutil
import subprocess
import sys

import pandas as pd

DEFAULT_LIST = "Internship Tracker"
KINDS = {
    "task": "To-dos you add",
    "fu": "Follow-ups",
    "dl": "Application deadlines",
    "st": "Scheduled interviews",
}

_JS = r"""
function run(argv) {
  const req = JSON.parse(argv[0]);
  const app = Application('Reminders');
  if (req.op === 'lists') return JSON.stringify(app.lists.name());
  if (app.lists.name().indexOf(req.list) < 0) app.lists.push(app.List({name: req.list}));
  const list = app.lists.byName(req.list);
  const out = {state: {}, created: {}, errors: []};
  if (req.op === 'fetch') {
    const ids = list.reminders.id(), done = list.reminders.completed();
    ids.forEach((id, i) => { out.state[id] = done[i]; });
    return JSON.stringify(out);
  }
  (req.update || []).forEach(u => {
    try {
      const r = list.reminders.byId(u.id);
      if (u.name !== undefined) r.name = u.name;
      if (u.body !== undefined) r.body = u.body;
      if (u.due) r.dueDate = new Date(u.due);
      if (u.completed !== undefined) r.completed = u.completed;
    } catch (e) { out.errors.push(String(e)); }
  });
  (req.create || []).forEach(c => {
    try {
      const r = app.Reminder({name: c.name, body: c.body || '', dueDate: new Date(c.due)});
      list.reminders.push(r);
      out.created[c.key] = r.id();
    } catch (e) { out.errors.push(String(e)); }
  });
  return JSON.stringify(out);
}
"""


class RemindersError(RuntimeError):
    pass


def available() -> bool:
    return sys.platform == "darwin" and shutil.which("osascript") is not None


def _run(req: dict, timeout: float = 120) -> object:
    try:
        proc = subprocess.run(
            ["osascript", "-l", "JavaScript", "-e", _JS, json.dumps(req)],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise RemindersError("Reminders took too long to answer. Try again.") from e
    if proc.returncode != 0:
        err = proc.stderr.strip()
        if "-1743" in err or "not authorized" in err.lower() or "not allowed" in err.lower():
            raise RemindersError(
                "macOS blocked access to Reminders. Allow it in System Settings → "
                "Privacy & Security → Automation, then try again.")
        raise RemindersError(err or "Couldn't talk to Reminders.")
    return json.loads(proc.stdout or "null")


def list_names() -> list[str]:
    return list(_run({"op": "lists"}) or [])


def fetch(list_name: str) -> dict[str, bool]:
    """{reminder_id: completed} for every reminder in the list (creating the list if needed)."""
    return dict(_run({"op": "fetch", "list": list_name})["state"])


def apply(list_name: str, create: list[dict], update: list[dict]) -> dict:
    if not create and not update:
        return {"created": {}, "errors": []}
    return _run({"op": "apply", "list": list_name, "create": create, "update": update})


# ---------------------------------------------------------------------------
# What should be in Reminders
# ---------------------------------------------------------------------------

def _due(d, time_str: str | None = None) -> str:
    d = pd.Timestamp(d).date()
    hh, mm = (time_str or "09:00")[:5].split(":")
    return f"{d.isoformat()}T{int(hh):02d}:{int(mm):02d}:00"


def _job(company, role) -> str:
    company = "" if pd.isna(company) else str(company)
    role = "" if pd.isna(role) else str(role)
    return " — ".join(x for x in (company, role) if x)


def desired_items(apps: pd.DataFrame, tasks: pd.DataFrame, stages: pd.DataFrame,
                  kinds: set[str], today=None) -> dict[str, dict]:
    """{key: {"name", "due", "body"}} for everything that should be a reminder."""
    today = pd.Timestamp(today or _dt.date.today()).normalize()
    out: dict[str, dict] = {}

    if "task" in kinds and not tasks.empty:
        for t in tasks[tasks["done"] == 0].itertuples():
            job = _job(getattr(t, "company", None), getattr(t, "role", None))
            out[f"task:{t.id}"] = {
                "name": t.title, "due": _due(t.due_date, t.due_time),
                "body": f"Job: {job}" if job else "",
            }

    if not apps.empty:
        active = apps[~apps["status"].isin({"Rejected", "Withdrawn"})]
        if "fu" in kinds:
            for a in active.dropna(subset=["follow_up_date"]).itertuples():
                out[f"fu:{a.id}"] = {"name": f"Follow up: {_job(a.company, a.role)}",
                                     "due": _due(a.follow_up_date), "body": ""}
        if "dl" in kinds:
            pre = active[active["status"].isin({"Wishlist", "Applied"})].dropna(subset=["deadline"])
            for a in pre[pre["deadline"] >= today].itertuples():
                out[f"dl:{a.id}"] = {"name": f"Deadline: {_job(a.company, a.role)}",
                                     "due": _due(a.deadline), "body": ""}

    if "st" in kinds and not stages.empty and not apps.empty:
        names = apps.set_index("id")[["company", "role"]]
        sched = stages[stages["outcome"] == "Scheduled"].copy()
        sched["d"] = pd.to_datetime(sched["stage_date"], errors="coerce")
        for s in sched.dropna(subset=["d"]).itertuples():
            if s.d < today or s.application_id not in names.index:
                continue
            n = names.loc[s.application_id]
            out[f"st:{s.id}"] = {
                "name": f"{s.stage}: {_job(n.company, n.role)}",
                "due": _due(s.d, getattr(s, "stage_time", None) or None), "body": "",
            }
    return out


# ---------------------------------------------------------------------------
# Working out the difference
# ---------------------------------------------------------------------------

def plan_sync(desired: dict[str, dict], links: dict[str, dict],
              remote: dict[str, bool]) -> dict:
    """Pure function: what to create/update in Reminders and what to mark done here.

    Returns {"create": [...], "update": [...], "done_here": [keys],
             "link_state": {key: state}}.
    """
    create, update, done_here, link_state = [], [], [], {}

    for key, link in links.items():
        rid = link["reminder_id"]
        want = desired.get(key)
        if rid not in remote:                      # deleted on the Mac
            if want and want["due"] != link["due"]:
                create.append({"key": key, **want})  # date changed: bring it back
            else:
                link_state[key] = "gone"
            continue
        completed_there = remote[rid]
        if want is None:                           # done/removed in the tracker
            if not completed_there:
                update.append({"id": rid, "completed": True})
            link_state[key] = "closed"
            continue
        changed = want["name"] != link["title"] or want["due"] != link["due"]
        if completed_there and not changed and link["state"] == "open":
            done_here.append(key)                  # ticked off on the Mac
            link_state[key] = "closed"
        elif changed:
            update.append({"id": rid, "name": want["name"], "due": want["due"],
                           "body": want["body"], "completed": False, "key": key})
            link_state[key] = "open"

    for key, want in desired.items():
        if key not in links:
            create.append({"key": key, **want})
    return {"create": create, "update": update, "done_here": done_here,
            "link_state": link_state}


def sync(conn, list_name: str, kinds: set[str], today=None) -> dict:
    """Run one two-way sync. Returns counts for a short status message."""
    from . import db  # local import: db doesn't need this module

    links = db.load_mac_links(conn)
    remote = fetch(list_name)

    # First pull: things ticked off on the Mac become done here.
    first = plan_sync(
        desired_items(db.load_applications(conn), db.load_tasks(conn),
                      db.load_stages(conn), kinds, today),
        links, remote)
    pulled = 0
    for key in first["done_here"]:
        kind, _, ident = key.partition(":")
        if kind == "task":
            db.set_task_done(conn, int(ident))
        elif kind == "fu":
            db.update_application(conn, int(ident), follow_up_date=None)
        pulled += 1
    for key, state in first["link_state"].items():
        db.set_mac_link_state(conn, key, state)

    # Then push what the tracker wants now.
    desired = desired_items(db.load_applications(conn), db.load_tasks(conn),
                            db.load_stages(conn), kinds, today)
    plan = plan_sync(desired, db.load_mac_links(conn), remote)
    res = apply(list_name, plan["create"],
                [{k: v for k, v in u.items() if k != "key"} for u in plan["update"]])
    for c in plan["create"]:
        rid = res.get("created", {}).get(c["key"])
        if rid:
            db.save_mac_link(conn, c["key"], rid, c["name"], c["due"], "open")
    for u in plan["update"]:
        if "key" in u:
            db.save_mac_link(conn, u["key"], u["id"], u["name"], u["due"], "open")
    for key, state in plan["link_state"].items():
        if key not in {u.get("key") for u in plan["update"]}:
            db.set_mac_link_state(conn, key, state)
    return {"pulled": pulled, "created": len(res.get("created", {})),
            "updated": len(plan["update"]), "errors": res.get("errors", [])}
