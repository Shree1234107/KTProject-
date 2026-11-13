"""Resume Matcher: score a resume PDF against a job description.

Public entry point is :func:`analyze`. The Streamlit UI calls it
and never does any text processing itself.
"""
from __future__ import annotations

from pathlib import Path

from .extractor import check_sections, clean_text, extract_text_from_pdf
from .keywords import extract_keywords
from .scorer import compute_scores
from .tips import generate_tips

__all__ = [
    "analyze",
    "analyze_text",
    "sample_job_description",
    "sample_resume_text",
    "MIN_JD_CHARS",
    "MIN_RESUME_CHARS",
]

MIN_JD_CHARS = 50
MIN_RESUME_CHARS = 100
MAX_PDF_BYTES = 5 * 1024 * 1024
_DATA = Path(__file__).parent / "data"


def analyze(pdf_bytes: bytes, job_description: str) -> dict:
    """Run the full match on a resume PDF.

    Args:
        pdf_bytes: Raw bytes of the uploaded PDF file.
        job_description: Pasted job description text.

    Returns:
        Result dict (same as :func:`analyze_text`).

    Raises:
        ValueError: for an oversized or text-less PDF, or a too-short job description.
    """
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise ValueError("That PDF is larger than 5 MB.")
    return analyze_text(extract_text_from_pdf(pdf_bytes), job_description)


def analyze_text(raw_resume: str, job_description: str) -> dict:
    """Run the full match on resume text already extracted from a PDF or pasted.

    Args:
        raw_resume: Raw resume text (not yet cleaned/lowercased).
        job_description: Pasted job description text.

    Returns:
        Dict with overall_score, keyword_coverage_score, cosine_similarity_score,
        matched_keywords, missing_keywords, section_checks, tips, resume_word_count.

    Raises:
        ValueError: resume too short, JD too short, or no recognizable skills found.
    """
    if len(raw_resume.strip()) < MIN_RESUME_CHARS:
        raise ValueError(
            f"Resume text is too short — paste at least {MIN_RESUME_CHARS} characters of your resume."
        )
    if len(job_description.strip()) < MIN_JD_CHARS:
        raise ValueError(f"Paste a fuller job description (at least {MIN_JD_CHARS} characters).")

    cleaned_resume = clean_text(raw_resume)
    cleaned_jd = clean_text(job_description)

    keywords = extract_keywords(cleaned_jd)
    if not keywords:
        raise ValueError(
            "No recognizable skills were found in that job description. "
            "Try pasting the full posting, including the requirements section."
        )
    scores = compute_scores(cleaned_resume, cleaned_jd, keywords)
    sections = check_sections(raw_resume)
    tips = generate_tips(cleaned_resume, scores["missing_keywords"], sections)
    return {
        **scores,
        "section_checks": sections,
        "tips": tips,
        "resume_word_count": len(cleaned_resume.split()),
    }


def sample_job_description() -> str:
    """Demo job description so a fresh clone has something to try."""
    return (_DATA / "sample_jd.txt").read_text(encoding="utf-8")


def sample_resume_text() -> str:
    """Demo resume text used in the Try the demo input mode."""
    return (_DATA / "sample_resume.txt").read_text(encoding="utf-8")
