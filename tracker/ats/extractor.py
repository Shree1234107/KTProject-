"""PDF text extraction and text cleaning utilities."""

import io
import re

import pdfplumber


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract plain text from a PDF file's bytes.

    Args:
        pdf_bytes: Raw bytes of the PDF file.

    Returns:
        Extracted text string.

    Raises:
        ValueError: If the PDF contains no extractable text (scanned/image PDF).
    """
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages_text = []
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                pages_text.append(page_text)

    full_text = "\n".join(pages_text).strip()

    if not full_text:
        raise ValueError(
            "No extractable text found in this PDF. "
            "It may be a scanned or image-only document. "
            "Please upload a text-based PDF."
        )

    return full_text


def clean_text(text: str) -> str:
    """Normalize whitespace, remove control characters, and lowercase.

    Args:
        text: Raw extracted text.

    Returns:
        Cleaned, lowercased text suitable for NLP processing.
    """
    # Remove non-printable control chars (keep newlines/spaces)
    text = re.sub(r"[^\x20-\x7E\n\t]", " ", text)
    # Collapse multiple spaces/tabs into one space
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse 3+ newlines into two
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip().lower()


def check_sections(raw_text: str) -> dict[str, bool]:
    """Detect whether common resume sections are present.

    Args:
        raw_text: Raw (not lowercased) resume text.

    Returns:
        Dict with bool flags for summary, experience, education, skills.
    """
    lower = raw_text.lower()

    summary_patterns = [r"\bsummary\b", r"\bobjective\b", r"\bprofile\b", r"\babout\b"]
    experience_patterns = [r"\bexperience\b", r"\bwork history\b", r"\bemployment\b"]
    education_patterns = [r"\beducation\b", r"\bdegree\b", r"\buniversity\b", r"\bcollege\b"]
    skills_patterns = [r"\bskills\b", r"\btechnical skills\b", r"\bcompetencies\b"]

    def any_match(patterns: list[str], text: str) -> bool:
        return any(re.search(p, text) for p in patterns)

    return {
        "summary": any_match(summary_patterns, lower),
        "experience": any_match(experience_patterns, lower),
        "education": any_match(education_patterns, lower),
        "skills": any_match(skills_patterns, lower),
    }
