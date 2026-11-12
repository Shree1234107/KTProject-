"""Keyword extraction and normalization from job descriptions."""

import json
import re
from collections import Counter
from pathlib import Path

import spacy

_nlp = None
_skills_data: dict | None = None

_DATA_PATH = Path(__file__).parent / "data" / "skills.json"


def _load_skills() -> dict:
    """Load and cache skills data from JSON."""
    global _skills_data
    if _skills_data is None:
        with open(_DATA_PATH) as f:
            _skills_data = json.load(f)
    return _skills_data


def _get_nlp():
    """Load and cache the spaCy model."""
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def normalize_keyword(keyword: str, aliases: dict[str, str]) -> str:
    """Expand a shorthand alias to its canonical form.

    Args:
        keyword: Raw keyword string (already lowercased).
        aliases: Mapping of abbreviation → canonical term.

    Returns:
        Canonical keyword string.
    """
    return aliases.get(keyword.strip(), keyword.strip())


def extract_keywords(cleaned_jd: str) -> list[dict]:
    """Extract and rank keywords from a cleaned job description.

    Combines three signals:
    1. Skill-list lookup (bundled JSON).
    2. spaCy named entities (ORG, PRODUCT, GPE, WORK_OF_ART, LAW).
    3. spaCy noun chunks (2-4 word technical phrases).

    Args:
        cleaned_jd: Lowercased, cleaned job description text.

    Returns:
        List of dicts with keys ``keyword`` (str) and ``count`` (int),
        sorted descending by count then alphabetically.
    """
    skills_data = _load_skills()
    aliases: dict[str, str] = skills_data.get("aliases", {})
    all_skills: list[str] = (
        skills_data.get("tech_skills", [])
        + skills_data.get("soft_skills", [])
        + skills_data.get("certifications", [])
    )

    # Token-level count in the JD
    jd_tokens = re.findall(r"[a-z0-9][a-z0-9/+#.\-]*", cleaned_jd)
    token_counts = Counter(jd_tokens)

    keyword_counts: dict[str, int] = {}

    def add_kw(kw: str, count: int) -> None:
        kw = normalize_keyword(kw.lower(), aliases).strip("- \t")
        if len(kw) < 2:
            return
        # Drop phrases that start with a non-alphanumeric character
        if not kw[0].isalnum():
            return
        if kw not in keyword_counts:
            keyword_counts[kw] = count
        else:
            keyword_counts[kw] = max(keyword_counts[kw], count)

    # 1. Skill-list scan: multi-word skills first, then single tokens
    for skill in sorted(all_skills, key=lambda s: -len(s)):
        if skill in cleaned_jd:
            # Count non-overlapping occurrences
            count = len(re.findall(re.escape(skill), cleaned_jd))
            add_kw(skill, count)

    # 2. spaCy entities & noun chunks
    nlp = _get_nlp()
    doc = nlp(cleaned_jd[:100_000])  # guard against very long text

    for ent in doc.ents:
        if ent.label_ in {"ORG", "PRODUCT", "GPE", "WORK_OF_ART", "LAW"}:
            kw = ent.text.lower().strip()
            count = token_counts.get(kw, 1)
            add_kw(kw, count)

    for chunk in doc.noun_chunks:
        text = chunk.text.lower().strip()
        words = text.split()
        # Keep 2-4 word technical-looking noun phrases
        if 2 <= len(words) <= 4 and not _is_stopword_phrase(text):
            count = len(re.findall(re.escape(text), cleaned_jd))
            if count > 0:
                add_kw(text, count)

    # Sort: highest count first, then alphabetically
    sorted_kws = sorted(keyword_counts.items(), key=lambda x: (-x[1], x[0]))
    return [{"keyword": kw, "count": cnt} for kw, cnt in sorted_kws]


_STOP_PHRASE_WORDS = {
    "you", "we", "our", "they", "their", "the", "a", "an",
    "this", "that", "these", "those", "it", "its", "which",
    "who", "what", "when", "where", "how", "why",
    "and", "or", "but", "if", "in", "on", "at", "to", "of",
    "for", "with", "about", "as", "by", "from", "into",
    "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "must",
    "can", "shall", "need", "am",
    "new", "good", "great", "strong", "excellent", "plus",
    "ability", "experience", "knowledge", "understanding",
    "familiarity", "proficiency", "skill", "skills",
}


def _is_stopword_phrase(phrase: str) -> bool:
    """Return True if the phrase is empty or consists entirely of common stop words."""
    words = set(phrase.lower().split())
    if not words:
        return True
    return words.issubset(_STOP_PHRASE_WORDS)


def keywords_in_text(resume_text: str, keywords: list[dict]) -> tuple[list[str], list[dict]]:
    """Check which keywords from the list appear in the resume.

    Args:
        resume_text: Cleaned, lowercased resume text.
        keywords: Output of :func:`extract_keywords`.

    Returns:
        Tuple of (matched_keywords, missing_keywords) where missing ones
        retain their count from the JD for importance ranking.
    """
    matched: list[str] = []
    missing: list[dict] = []

    for item in keywords:
        kw = item["keyword"]
        # Check both exact and partial (e.g. "kubernetes" in "kubernetes cluster")
        if re.search(r"\b" + re.escape(kw) + r"\b", resume_text):
            matched.append(kw)
        else:
            missing.append(item)

    return matched, missing
