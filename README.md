# KTProject — Internship Tracker & Dashboard Analyzer

Track internship and job applications and analyze your search: pipeline by status, response and interview rates, applications per week, best sources and upcoming deadlines. It also includes a **Resume Matcher** that scores your resume against a job posting.

Everything runs on your own computer at http://localhost:8501. There are no accounts, hosting or API keys, and each person keeps their own local database.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```
Data is stored locally in `data/tracker.db` (git-ignored, never commit it). To pick up a teammate's latest work, run `git pull` before each session.

## Test
```bash
pytest
```

## Features

Status key: **Built** = works today, **Planned** = agreed in the project plan, **Proposed** = suggested, not yet agreed.

### Application tracker

| Feature | What it does | Status |
|---|---|---|
| Log applications | Company, role, location, source, status, dates, notes | Built |
| Edit, filter and delete | Search by company or role, filter by status, update a status or notes, delete an entry | Built |
| Dashboard | Totals, active count, response rate, interview rate and offers; pipeline by status; applications per week; responses by source; deadlines in the next 14 days | Built |
| Referral tracking | Referrer name and contact per application; compare referred vs. cold response rates | Built |
| Interview stages | Log each round (recruiter screen, online assessment, technical, behavioral, take-home, onsite/final) with date and outcome (Scheduled, Passed, Failed, Pending) | Planned |
| Follow-up reminders | Follow-up date per application; a Reminders tab listing overdue, due today and upcoming items, with mark done and snooze 3 or 7 days; flags applications with no reply after 21+ days | Built |
| Response-rate visuals | Funnel (Applied, Responded, Interviewed, Offer), response rate by source, referred vs. cold, pass rate per stage, applications per week | Planned |
| Sample data | A button that loads demo data so a fresh clone has something to show | Built |
| ICS export | Download reminders as a calendar file to import by hand | Proposed |

Statuses: Wishlist, Applied, OA/Screen, Interview, Offer, Rejected, Withdrawn.

Definitions the dashboard uses:
- **Response rate** = applications that reached OA/Screen, Interview, Offer or Rejected, or have a logged interview stage, divided by submitted applications. Wishlist items are not counted as submitted.
- **Interview rate** = applications at Interview or Offer, or with a logged stage, divided by submitted applications.

### Resume Matcher (the fourth tab)

Score a resume against a job description and get specific tips. Runs locally; nothing is uploaded or stored. The score is an estimate, not a real ATS.

| Feature | What it does | Status |
|---|---|---|
| Three input modes | Upload a PDF, paste resume text, or try the built-in demo resume and job description | Built |
| Input checks | Clear errors for no file, a PDF over 5 MB, a scanned PDF with no text, a resume under 100 characters, a job description under 50 characters, or a posting with no recognizable skills | Built |
| Match score | 0–100, made of 60% keyword coverage and 40% TF-IDF content similarity, with the label Strong match (70+), Decent (50–69) or Needs work (under 50) | Built |
| Keyword matching | Matches skills from a bundled list on whole words (so "go" never matches "good"), understands aliases like `k8s` → Kubernetes and `js` → JavaScript, and counts how often the job mentions each skill | Built |
| Keywords by category | Matched and missing skills grouped as Technical, Certifications or Soft skills, with missing ones ranked by how often the job mentions them | Built |
| Section check | Detects Summary, Experience, Education and Skills sections | Built |
| Improvement tips | "Do these first" shows the top 3, with the rest expandable. Tips cover missing keywords, missing sections, resume length, quantified results and weak action verbs, and are always phrased as "if you have experience" | Built |
| Download report | Export the result as a Markdown file | Built |
| Link scores to applications | Save a match score against a tracked application | Proposed |

To add skills or aliases, edit `tracker/ats/data/skills.json`.

## Roadmap

### In the app today
- **Dashboard:** totals, active count, response rate, interview rate, offers; pipeline by status; applications per week; responses by source; deadlines in the next 14 days.
- **Applications:** list with status filter and company/role search; update a status or notes; delete.
- **Add:** form with company, role, location, source, status, date applied, deadline and notes.
- **Resume Matcher:** upload a PDF, paste text or use the demo; match score and label, keywords by category, section check, tips, report download.

### Up next
1. **Referral tracking** *(built)*: referrer name and contact on each application, plus a referred vs. cold comparison of response and interview rates on the Dashboard.
2. **Follow-up reminders** *(built)*: a follow-up date per application and a Reminders tab with Overdue, Due today and Upcoming groups, mark done, snooze 3 or 7 days, and a "no reply after 21+ days" flag.
3. **Edit every field** *(built)*: full edit form covering all fields with validation.
4. **CSV export** *(built)*: download the filtered Applications view as a CSV.
5. **Sample data** *(built)*: "Load sample data" button in the sidebar populates 15 realistic entries; "Remove sample data" and confirmed "Clear ALL data" buttons are also there.

### Later
- **Interview stages** *(planned)*: log each round with date and outcome.
- **Response-rate visuals** *(planned)*: funnel, rate by source, pass rate per stage.
- **ICS export** *(proposed)*: download reminders as a calendar file.
- **Resume Matcher + tracker link** *(proposed)*: save a match score against an application.
- Open decisions from the plan: branches with PRs or pushing straight to `main`, Plotly or built-in charts, and any extra fields (salary, job link, recruiter email).

## Layout
- `app.py` — Streamlit UI (Dashboard / Applications / Add / Reminders / Resume Matcher tabs)
- `tracker/db.py` — SQLite storage and CRUD
- `tracker/analytics.py` — dashboard metrics (pure pandas, tested)
- `tracker/ats/` — Resume Matcher
  - `ui.py` — the tab's Streamlit interface (no text processing)
  - `__init__.py` — entry points `analyze()` (PDF) and `analyze_text()`
  - `extractor.py` (PDF text and section detection), `keywords.py`, `scorer.py`, `tips.py`, `report.py`
  - `data/` — `skills.json` and the demo resume and job description
- `tests/` — pytest tests for storage, analytics and the Resume Matcher
- `.streamlit/config.toml` — caps uploads at 5 MB
- `backend/`, `frontend/` — an earlier standalone version of the Resume Matcher (FastAPI + React). It has been replaced by the Streamlit tab and is no longer part of the app.

## Workflow
Each contributor works in their own fork on a feature branch and opens PRs to `main`.

Working agreements from the project plan:
- Pull before you start and before you push.
- Small, focused commits with a clear message.
- Avoid editing the same file at the same time. Agree who owns which sections of `app.py`, `tracker/db.py` and `tracker/analytics.py` before coding.
- Run `pytest` before pushing, and add tests for any new function.
