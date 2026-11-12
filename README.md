# KTProject — Internship Tracker & Dashboard Analyzer

Track internship applications and analyze your search: pipeline by status, response/interview rates, applications per week, best sources, and upcoming deadlines.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```
Data is stored locally in `data/tracker.db` (git-ignored).

## Test
```bash
pytest
```

## Layout
- `tracker/db.py` — SQLite storage + CRUD
- `tracker/analytics.py` — dashboard metrics (pure pandas, tested)
- `app.py` — Streamlit UI (Dashboard / Applications / Add tabs)

## Workflow
Each contributor works in their own fork on a feature branch and opens PRs to `main`.
