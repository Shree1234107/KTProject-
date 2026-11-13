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

## Resume Matcher (tab in the app)

Upload a resume PDF and paste a job description to get a keyword match score, matched/missing skills and improvement tips. It runs locally inside the same Streamlit app, with no accounts, keys or stored files.

- Code: `tracker/ats/` (`extractor.py`, `keywords.py`, `scorer.py`, `tips.py`, `data/skills.json`); entry point `ats.analyze()`. The UI in `app.py` does no text processing.
- Score = 60% keyword coverage + 40% TF-IDF cosine similarity. It is an estimate, not a real ATS.
- Add skills or aliases in `tracker/ats/data/skills.json`.
- Use "Use the demo resume" and "Load demo job description" to try it without your own files.
- Tests: `tests/test_ats.py`
