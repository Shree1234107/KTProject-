"""Career Assistant: a chatbot that knows your internship search.

How it works:
1. ``system_prompt`` turns your tracker data (applications, statuses,
   interviews, to-dos) into a short briefing for the model, so its answers are
   about YOUR search, not generic advice.
2. The conversation is a list of dictionaries, ``{"role": ..., "content": ...}``,
   kept in st.session_state by app.py so it survives Streamlit reruns.
3. ``stream_reply`` sends the system prompt + the conversation to a model
   running in Ollama on this computer and yields the reply piece by piece, so
   it appears as it's written.

The model runs locally through Ollama, so there is no API key. The Ollama
address can be changed with the OLLAMA_URL environment variable.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.error
import urllib.request
from collections.abc import Iterator

import pandas as pd

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

# Statuses that mean the application is still in play.
ACTIVE = ("Applied", "OA/Screen", "Interview", "Offer")

ROLE = (
    "You are Career Assistant, a friendly, practical internship-search coach built "
    "into the user's Internship Tracker. You help with: what to do next on each "
    "application, follow-up timing, interview prep (likely questions, STAR answers, "
    "questions to ask), networking messages, and staying organized.\n"
    "Rules:\n"
    "- An application with status Applied (or later) has already been submitted; "
    "never tell the user to submit it again.\n"
    "- Use the TRACKER DATA below when the question is about their applications. "
    "Don't invent applications, dates, contacts or results that aren't there.\n"
    "- If you don't know something, say so and suggest how to find out.\n"
    "- Be concise: short paragraphs or bullet points, plain language.\n"
    "- Never make up facts about the user's experience; ask them instead."
)


def _fmt(value) -> str:
    """Readable date for the briefing, or '' for missing values."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return ""
    return str(pd.Timestamp(value).date())


def tracker_summary(apps: pd.DataFrame, tasks: pd.DataFrame | None = None,
                    today: dt.date | None = None, limit: int = 40) -> str:
    """Plain-text briefing of the user's search for the system prompt."""
    today = today or dt.date.today()
    if apps is None or apps.empty:
        return "The user hasn't added any applications yet."
    real = apps[apps.get("is_sample", 0) != 1] if "is_sample" in apps else apps
    counts = real["status"].value_counts()
    lines = [f"Today is {today:%A, %B %d, %Y}.",
             f"{len(real)} applications: "
             + ", ".join(f"{n} {s}" for s, n in counts.items()) + "."]
    # Active applications first, most recent first.
    order = real.assign(_active=real["status"].isin(ACTIVE)).sort_values(
        ["_active", "date_applied"], ascending=[False, False])
    for _, a in order.head(limit).iterrows():
        bits = [f"{a['company']} — {a['role']} ({a['status']})"]
        if _fmt(a.get("date_applied")):
            bits.append(f"applied {_fmt(a['date_applied'])}")
        if _fmt(a.get("deadline")):
            bits.append(f"deadline {_fmt(a['deadline'])}")
        if _fmt(a.get("follow_up_date")):
            bits.append(f"follow up {_fmt(a['follow_up_date'])}")
        if isinstance(a.get("notes"), str) and a["notes"].strip():
            bits.append("notes: " + a["notes"].strip().replace("\n", " ")[:120])
        lines.append("- " + "; ".join(bits))
    if tasks is not None and not tasks.empty:
        open_tasks = tasks[tasks["done"] == 0]
        if not open_tasks.empty:
            lines.append("Open to-dos:")
            for _, t in open_tasks.head(15).iterrows():
                due = f" (due {_fmt(t['due_date'])})" if _fmt(t.get("due_date")) else ""
                job = t.get("company")
                job = f" [for {job}]" if isinstance(job, str) and job.strip() else " [not tied to a job]"
                lines.append(f"- {t['title']}{job}{due}")
    return "\n".join(lines)


def system_prompt(apps: pd.DataFrame, tasks: pd.DataFrame | None = None) -> str:
    """The instructions + tracker briefing sent as the first message."""
    return f"{ROLE}\n\nTRACKER DATA:\n{tracker_summary(apps, tasks)}"


def build_messages(system: str, history: list[dict]) -> list[dict]:
    """System message first, then the chat history (each {"role", "content"})."""
    return [{"role": "system", "content": system}] + [
        {"role": m["role"], "content": m["content"]} for m in history
    ]


def stream_reply(model: str, messages: list[dict], timeout: float = 300) -> Iterator[str]:
    """Send the conversation to Ollama and yield the reply as it streams in.

    Raises RuntimeError with a readable message if Ollama can't answer.
    """
    body = json.dumps({"model": model, "messages": messages, "stream": True,
                       "think": False}).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            for raw in r:  # Ollama sends one JSON object per line
                if not raw.strip():
                    continue
                chunk = json.loads(raw)
                if chunk.get("error"):
                    raise RuntimeError(chunk["error"])
                piece = chunk.get("message", {}).get("content", "")
                if piece:
                    yield piece
                if chunk.get("done"):
                    break
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Ollama error: {e.read().decode(errors='ignore')[:200]}") from e
    except (urllib.error.URLError, OSError) as e:
        raise RuntimeError("Couldn't reach Ollama. Is the Ollama app open?") from e
