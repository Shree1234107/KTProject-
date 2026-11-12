# ATS Resume Matcher & Scorer

Upload a resume PDF and paste a job description to get a keyword match score, section analysis, and actionable improvement tips — all powered by NLP.

> **Disclaimer:** This is an estimate, not a real ATS system. Scores are indicative only and should not be treated as a prediction of actual ATS outcomes.

---

## Screenshot

<!-- Replace with an actual screenshot after first run -->
![ATS Resume Matcher UI](docs/screenshot-placeholder.png)

---

## Features

- **PDF upload** (drag-and-drop or file picker, max 5 MB, PDF only)
- **Keyword extraction** using spaCy NER + noun chunks + a bundled ~300-skill list with alias normalization (e.g. `JS → JavaScript`, `k8s → Kubernetes`)
- **Scoring** — a weighted blend:
  - 60% keyword coverage (what fraction of JD keywords appear in the resume)
  - 40% TF-IDF cosine similarity (overall content overlap)
- **Section checks** — detects Summary, Experience, Education, and Skills sections
- **Improvement tips** — rule-based, specific, and always phrased as "if applicable"
- No files stored; all processing is in-memory

---

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.11+, FastAPI, pdfplumber, spaCy (`en_core_web_sm`), scikit-learn |
| Frontend | React 18, Vite, TypeScript, plain CSS |
| Testing | pytest (backend), Vitest (frontend) |

---

## Project Structure

```
ats-resume-matcher/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app + /health + /analyze endpoints
│   │   ├── models.py        # Pydantic request/response models
│   │   ├── extractor.py     # PDF extraction, text cleaning, section detection
│   │   ├── keywords.py      # Keyword extraction and alias normalization
│   │   ├── scorer.py        # TF-IDF cosine similarity + keyword coverage blend
│   │   ├── tips.py          # Rule-based improvement tips
│   │   └── data/
│   │       └── skills.json  # ~300 tech/soft skills + alias map (easy to extend)
│   ├── tests/
│   │   ├── fixtures/        # sample_resume.txt, sample_jd.txt for demos
│   │   ├── test_extractor.py
│   │   ├── test_keywords.py
│   │   ├── test_scorer.py
│   │   └── test_tips.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── types.ts
│   │   ├── components/
│   │   │   ├── UploadForm.tsx
│   │   │   ├── ScoreGauge.tsx
│   │   │   ├── KeywordChips.tsx
│   │   │   ├── SectionChecks.tsx
│   │   │   └── TipsList.tsx
│   │   └── tests/
│   │       └── scoring.test.ts
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

---

## Setup

### Prerequisites

- Python 3.11+ (tested on 3.13)
- Node.js 18+

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn app.main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

The Vite dev server proxies `/api/*` to `http://localhost:8000`, so you only need to open `http://localhost:5173`.

---

## Running Tests

### Backend (52 tests)

```bash
cd backend
source .venv/bin/activate
python -m pytest -v
```

### Frontend (8 tests)

```bash
cd frontend
npm test
```

---

## Demo Without Your Own Files

Sample fixtures are included:

- `backend/tests/fixtures/sample_resume.txt` — a software engineer resume
- `backend/tests/fixtures/sample_jd.txt` — a Senior Backend Engineer job description

To test the endpoint directly:

```bash
# Convert sample resume to PDF first (requires any word processor),
# or use curl with multipart form:
curl -X POST http://localhost:8000/analyze \
  -F "resume=@your_resume.pdf" \
  -F "job_description=$(cat backend/tests/fixtures/sample_jd.txt)"
```

---

## How Scoring Works

### Overall Score (0–100)

```
overall = (keyword_coverage × 0.60 + cosine_similarity × 0.40) × 100
```

| Component | Weight | Description |
|---|---|---|
| Keyword coverage | 60% | Fraction of extracted JD keywords present in resume |
| TF-IDF cosine similarity | 40% | Vocabulary overlap using bigram TF-IDF vectors |

### Keyword Extraction Pipeline

1. **Skill-list scan** — multi-word skills first, then single tokens, against `skills.json`
2. **spaCy NER** — ORG, PRODUCT, GPE entities (tool names, company names)
3. **spaCy noun chunks** — 2–4 word technical phrases filtered for stop words
4. **Alias normalization** — `JS → JavaScript`, `k8s → Kubernetes`, `ML → machine learning`, etc.
5. **Deduplication + ranking** — by frequency in the job description

### Score Interpretation

| Range | Label |
|---|---|
| 70–100 | Strong Match |
| 45–69 | Moderate Match |
| 0–44 | Needs Work |

---

## Extending the Skills List

Edit `backend/app/data/skills.json`:

- Add to `tech_skills`, `soft_skills`, or `certifications` arrays
- Add aliases to the `aliases` object: `"abbreviation": "canonical term"`

---

## Limitations

- **Not a real ATS.** Real ATS systems use proprietary parsing and scoring logic. This app is a heuristic estimate.
- **Scanned PDFs not supported.** Image-only PDFs (no embedded text) will return an error.
- **English only.** spaCy model is English; non-English content will produce poor results.
- **Score variance.** Scores depend on the specific wording of both documents; small changes can shift results.
- **No file storage.** Uploaded PDFs are processed in-memory and never written to disk.
