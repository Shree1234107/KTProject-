"""Rule-based, actionable improvement tips for resume optimization."""

import re

WEAK_ACTION_VERBS = {
    "worked", "helped", "assisted", "did", "made", "got", "tried",
    "used", "handled", "dealt", "involved", "participated", "contributed",
    "responsible for", "duties included",
}

STRONG_ACTION_VERBS = [
    "achieved", "accelerated", "architected", "automated", "built",
    "championed", "created", "delivered", "designed", "developed",
    "drove", "engineered", "established", "executed", "expanded",
    "generated", "implemented", "improved", "increased", "launched",
    "led", "managed", "mentored", "optimized", "overhauled", "owned",
    "pioneered", "reduced", "refactored", "released", "scaled", "shipped",
    "simplified", "spearheaded", "streamlined", "transformed", "unified",
]

MIN_WORDS = 200
MAX_WORDS = 1200
QUANTIFICATION_PATTERN = re.compile(r"\b\d+\s*(%|percent|x\b|times|million|billion|k\b|users|requests)")
TOP_N_MISSING = 5


def generate_tips(
    resume_text: str,
    missing_keywords: list[dict],
    section_checks: dict[str, bool],
) -> list[str]:
    """Generate specific, actionable improvement tips for the resume.

    Args:
        resume_text: Cleaned, lowercased resume text.
        missing_keywords: Output from :func:`~tracker.ats.scorer.compute_scores` —
            list of ``{keyword, count}`` dicts sorted by importance.
        section_checks: Output of :func:`~tracker.ats.extractor.check_sections`.

    Returns:
        List of tip strings. Never fabricate skills; all suggestions are
        phrased with "if applicable" or "if you have experience".
    """
    tips: list[str] = []

    # --- Missing keyword tips ---
    top_missing = missing_keywords[:TOP_N_MISSING]
    for item in top_missing:
        kw = item["keyword"]
        count = item["count"]
        noun = "time" if count == 1 else "times"
        tips.append(
            f"Consider adding '{kw}' (mentioned {count} {noun} in the job description)"
            " if you have experience with it."
        )

    # --- Section tips ---
    if not section_checks.get("summary"):
        tips.append(
            "Add a Summary or Objective section at the top of your resume to "
            "provide a quick overview of your profile."
        )
    if not section_checks.get("experience"):
        tips.append(
            "Add a Work Experience section to highlight your professional history."
        )
    if not section_checks.get("education"):
        tips.append(
            "Add an Education section listing your degrees, institutions, and graduation years."
        )
    if not section_checks.get("skills"):
        tips.append(
            "Add a dedicated Skills section so ATS systems can quickly match your "
            "technical competencies."
        )

    # --- Length tips ---
    word_count = len(resume_text.split())
    if word_count < MIN_WORDS:
        tips.append(
            f"Your resume appears very short ({word_count} words). "
            "Consider expanding your experience descriptions and adding measurable achievements."
        )
    elif word_count > MAX_WORDS:
        tips.append(
            f"Your resume is quite long ({word_count} words). "
            "Consider condensing it to 1-2 pages to improve readability."
        )

    # --- Quantified achievements ---
    if not QUANTIFICATION_PATTERN.search(resume_text):
        tips.append(
            "Strengthen your impact by adding quantified achievements "
            "(e.g., 'reduced latency by 40%', 'scaled to 1M+ users')."
        )

    # --- Weak action verbs ---
    found_weak = [v for v in WEAK_ACTION_VERBS if re.search(r"\b" + re.escape(v) + r"\b", resume_text)]
    if found_weak:
        examples = ", ".join(f"'{v}'" for v in found_weak[:3])
        alternatives = ", ".join(f"'{v}'" for v in STRONG_ACTION_VERBS[:4])
        tips.append(
            f"Replace weak action verbs ({examples}) with stronger alternatives "
            f"like {alternatives}."
        )

    return tips
