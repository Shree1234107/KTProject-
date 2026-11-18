# KTProject — Internship Tracker & Dashboard Analyzer

Track internship and job applications and analyze your search: pipeline by status, response and interview rates, applications per week, best sources and upcoming deadlines. It also includes a **Resume Matcher** that scores your resume against a job posting.

Everything runs on your own computer at http://localhost:8501. There are no accounts, hosting or API keys, and each person keeps their own local database.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```
Data is stored locally in `data/tracker.db` (git-ignored, never commit it). To pick up a teammate's latest work, run `git pull` before each session.

## Look and feel

**Palette — whites and blues only:**

| Variable | Hex | Use |
|---|---|---|
| `--c-white` | `#ffffff` | Page background |
| `--c-bg-1` | `#f8fafc` | Sidebar, metric cards, form background |
| `--c-bg-2` | `#f1f5f9` | Secondary surfaces |
| `--c-border` | `#e2e8f0` | All borders and dividers |
| `--c-blue-600` | `#2563eb` | Primary actions, matched chips, left-border accent |
| `--c-blue-700` | `#1d4ed8` | Hover state for primary |
| `--c-blue-900` | `#1e3a8a` | "Strong match" label text |
| `--c-text` | `#0f1f3d` | Body text (WCAG AA contrast on white) |
| `--c-text-sec` | `#475a7a` | Secondary labels, captions |

**Where the CSS lives:** `tracker/styles.py` (the `CSS` string, plus a `TOKENS` palette dict shared with the charts). `styles.setup()` injects it once at startup, right after `st.set_page_config` in `app.py`. The Resume Matcher tab (`tracker/ats/ui.py`) contains no inline `<style>` blocks or inline color values.

**To change a color:** update `TOKENS` and the matching CSS variable in section 0 of `tracker/styles.py`. All occurrences in the UI update automatically — no hunting through Python files.

**Design rules:** square corners everywhere (`border-radius: 0`), 1 px solid borders in `--c-border`, flat (no shadows, no gradients), system-ui font stack (no network font load). Section headings are small uppercase labels. Metrics use tabular numbers. All alerts use a 3 px blue left border regardless of severity; errors show an "Error:" prefix in the message text.

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
| Interview stages | Log each round (recruiter screen, online assessment, technical, behavioral, take-home, onsite/final) with date and outcome (Scheduled, Passed, Failed, Pending); pass rate by stage on the Dashboard | Built |
| To-dos & Mac Reminders | Add your own reminders ("Send a thank-you note to Mansfield", Thu 10 AM), optionally tied to a job. On a Mac, turn on two-way sync with the Reminders app: to-dos, follow-ups, application deadlines and scheduled interviews appear on your Mac and iPhone, and ticking one off there marks it done here | Built |
| Follow-up reminders | Follow-up date per application; a Reminders tab listing overdue, due today and upcoming items, with mark done and snooze 3 or 7 days; flags applications with no reply after 21+ days | Built |
| Kanban board | One column per status. Each card shows progress dots and days in its stage, a one-click "Move to [next stage]" button, a "Change stage" menu to jump to any stage with that job's stage history, and a "Contacts & notes" panel. Cards idle past a set number of days (Settings, default 21) are flagged "Quiet N days · follow up?" | Built |
| Contacts & notes | Any number of contacts per job (name, role, email or LinkedIn, last contacted) and dated notes, on the Board and in the Applications tab | Built |
| Activity heatmap | GitHub-style 26-week calendar grid on the Dashboard; cell shading by application count per day | Built |
| Funnel chart | Horizontal bars Applied → Responded → Interviewed → Offer with conversion rates | Built |
| Weekly goal | Persistent weekly application target; progress bar; current and longest streak | Built |
| Stat tiles | Big-number header row with CSS count-up animation (0 → value, ~900 ms, ease-out) and trend indicators vs the previous 30 days; also animates the Resume Matcher score | Built |
| Sample data | A button that loads demo data so a fresh clone has something to show | Built |
| ICS export | Download follow-ups, deadlines, and scheduled interviews as an RFC 5545 .ics file; open in Apple Calendar or import in Google Calendar | Built |

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
| Link scores to applications | Save a match score against a tracked application; view score history and trend chart in the Applications tab; latest score shown on Board cards | Built |

To add skills or aliases, edit `tracker/ats/data/skills.json`.

### Cover Letter tab

Write a cover letter for one job from your resume, your own template and the job description, then download it as a PDF. Your resume and template are saved locally so you enter them once.

| Feature | What it does | Status |
|---|---|---|
| Fill my template (no AI) | Replaces `{company}`, `{role}`, `{hiring_manager}`, `{skills}` and `{date}` in your template. `{skills}` lists skills that are in both your resume and the job description | Built |
| Write with AI (Ollama) | A model running in [Ollama](https://ollama.com) (free) writes a tailored letter in your template's style, using only experience from your resume. Local models keep everything on your computer; models ending in `:cloud` send text to Ollama's servers | Built |
| Upload a template | Load your template from a Word (.docx), PDF, .txt or .md file instead of pasting it; it is saved for next time | Built |
| Edit and download | Edit the letter on the page, then download a US Letter PDF named `Cover_Letter_Company_Role.pdf` | Built |

To use AI: install Ollama, open it, and download a model that fits your computer's memory (for example `ollama pull llama3.2:3b`, a 2 GB model that runs well on a 16 GB laptop), then reload the app.

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

### Completed
- **Interview stages** *(built)*: log each round with date and outcome; pass rate by stage chart on the Dashboard.
- **ICS export** *(built)*: download follow-ups, deadlines and scheduled interviews as an RFC 5545 .ics calendar file.
- **Resume Matcher + tracker link** *(built)*: save a match score against an application; score history and trend chart in the Applications tab; latest score tag on Board cards.

### Open decisions
Branches with PRs or pushing straight to `main`, Plotly or built-in charts, extra fields (salary, job link, recruiter email).

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
