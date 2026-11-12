"""FastAPI application entry point."""

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.extractor import check_sections, clean_text, extract_text_from_pdf
from app.models import MatchResult

app = FastAPI(title="ATS Resume Matcher", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_PDF_BYTES = 5 * 1024 * 1024  # 5 MB


@app.get("/health")
def health() -> dict:
    """Return service health status."""
    return {"status": "ok", "service": "ats-resume-matcher"}


@app.post("/analyze", response_model=MatchResult)
async def analyze(
    resume: UploadFile = File(..., description="Resume PDF, max 5 MB"),
    job_description: str = Form(..., min_length=50, description="Job description text"),
) -> MatchResult:
    """Analyze a resume PDF against a job description.

    Args:
        resume: Uploaded PDF file.
        job_description: Pasted job description text.

    Returns:
        MatchResult with score, keywords, section checks, and tips.

    Raises:
        HTTPException 400: Invalid file type, file too large, or no extractable text.
    """
    if resume.content_type not in ("application/pdf", "application/octet-stream"):
        # Some browsers send octet-stream; also check filename extension
        filename = resume.filename or ""
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    pdf_bytes = await resume.read()

    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise HTTPException(status_code=400, detail="PDF exceeds the 5 MB size limit.")

    try:
        raw_text = extract_text_from_pdf(pdf_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    cleaned_resume = clean_text(raw_text)
    cleaned_jd = clean_text(job_description)
    sections = check_sections(raw_text)

    # Import here to avoid circular issues; heavy modules load lazily
    from app.keywords import extract_keywords
    from app.scorer import compute_scores
    from app.tips import generate_tips

    jd_keywords = extract_keywords(cleaned_jd)
    scores = compute_scores(cleaned_resume, cleaned_jd, jd_keywords)
    tips = generate_tips(
        resume_text=cleaned_resume,
        missing_keywords=scores["missing_keywords"],
        section_checks=sections,
    )

    from app.models import MissingKeyword, SectionChecks

    return MatchResult(
        overall_score=scores["overall_score"],
        keyword_coverage_score=scores["keyword_coverage_score"],
        cosine_similarity_score=scores["cosine_similarity_score"],
        matched_keywords=scores["matched_keywords"],
        missing_keywords=[MissingKeyword(**kw) for kw in scores["missing_keywords"]],
        section_checks=SectionChecks(**sections),
        tips=tips,
        resume_word_count=len(cleaned_resume.split()),
    )
