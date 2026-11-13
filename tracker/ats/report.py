"""Pure functions for generating an ATS match report.

All functions are side-effect-free so they can be tested without Streamlit.
"""
from __future__ import annotations

import html as _html

CATEGORIES = ("Technical", "Certifications", "Soft skills")

# Ordered thresholds: first match wins (score >= threshold → label)
_BANDS: tuple[tuple[float, str], ...] = (
    (70.0, "Strong match"),
    (50.0, "Decent"),
)
_BAND_FALLBACK = "Needs work"


def score_band(score: float) -> str:
    """Return a human-readable label for a 0–100 match score.

    Args:
        score: Overall match score in [0, 100].

    Returns:
        ``"Strong match"`` (≥70), ``"Decent"`` (50–69), or ``"Needs work"`` (<50).
    """
    for threshold, label in _BANDS:
        if score >= threshold:
            return label
    return _BAND_FALLBACK


def group_by_category(
    matched: list[dict],
    missing: list[dict],
) -> dict[str, dict[str, list]]:
    """Group matched and missing keywords by their display category.

    Args:
        matched: List of ``{"keyword": str, "category": str}`` dicts.
        missing: List of ``{"keyword": str, "count": int, "category": str}`` dicts.

    Returns:
        ``{category: {"matched": [str, ...], "missing": [dict, ...]}}`` for each
        category in :data:`CATEGORIES`. Unknown categories are silently binned
        under ``"Technical"``.
    """
    groups: dict[str, dict[str, list]] = {
        cat: {"matched": [], "missing": []} for cat in CATEGORIES
    }

    for item in matched:
        cat = item.get("category", "Technical")
        dest = groups.get(cat, groups["Technical"])
        dest["matched"].append(item["keyword"])

    for item in missing:
        cat = item.get("category", "Technical")
        dest = groups.get(cat, groups["Technical"])
        dest["missing"].append(item)

    return groups


def build_report(result: dict) -> str:
    """Build a Markdown report string from an ATS analysis result.

    Args:
        result: The dict returned by :func:`~tracker.ats.analyze` or
            :func:`~tracker.ats.analyze_text`.

    Returns:
        A UTF-8 Markdown string suitable for a ``st.download_button``.
    """
    score: float = result["overall_score"]
    kw_score: float = result["keyword_coverage_score"]
    cos_score: float = result["cosine_similarity_score"]
    word_count: int = result.get("resume_word_count", 0)
    band: str = score_band(score)
    matched: list[dict] = result["matched_keywords"]
    missing: list[dict] = result["missing_keywords"]
    sections: dict[str, bool] = result["section_checks"]
    tips: list[str] = result["tips"]

    lines: list[str] = [
        "# ATS Resume Match Report",
        "",
        f"**Overall score:** {score:.0f} / 100 — {band}",
        f"**Keyword coverage:** {kw_score:.0f}%  "
        f"| **Content similarity:** {cos_score:.0f}%  "
        f"| **Word count:** {word_count}",
        "",
        "## Resume Sections",
    ]

    _SECTION_LABELS = [
        ("summary", "Summary"),
        ("experience", "Experience"),
        ("education", "Education"),
        ("skills", "Skills"),
    ]
    for key, label in _SECTION_LABELS:
        icon = "✅" if sections.get(key) else "❌"
        lines.append(f"- {icon} {label}")

    lines += ["", "## Improvement Tips"]
    for i, tip in enumerate(tips or ["No major issues found."], 1):
        lines.append(f"{i}. {tip}")

    groups = group_by_category(matched, missing)

    lines += ["", "## Missing Keywords (add only if applicable)"]
    has_missing = False
    for cat in CATEGORIES:
        cat_missing = groups[cat]["missing"]
        if cat_missing:
            has_missing = True
            lines.append(f"\n### {cat}")
            for item in cat_missing:
                escaped = _html.escape(item["keyword"])
                lines.append(f"- {escaped} (×{item['count']} in JD)")
    if not has_missing:
        lines.append("\nNone — all JD keywords found in your resume.")

    lines += ["", "## Matched Keywords"]
    has_matched = False
    for cat in CATEGORIES:
        cat_matched = groups[cat]["matched"]
        if cat_matched:
            has_matched = True
            lines.append(f"\n### {cat}")
            for kw in cat_matched:
                lines.append(f"- {_html.escape(kw)}")
    if not has_matched:
        lines.append("\nNone matched.")

    lines += [
        "",
        "---",
        "*This is an estimate, not a real ATS. Scores are indicative only.*",
        "*Only add skills you actually have.*",
    ]
    return "\n".join(lines)
