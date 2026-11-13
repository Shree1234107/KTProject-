"""Keyword extraction and matching for the resume matcher.

Keywords come from a bundled, extendable skills list (``data/skills.json``),
matched on whole words so "go" never matches inside "good". Aliases such as
"k8s" or "js" are normalized to their canonical names. No spaCy model or
network access is needed.

Each returned keyword dict now carries a ``category`` field
(``"Technical"``, ``"Certifications"``, or ``"Soft skills"``) so the UI can
group and colour-code chips without touching the logic layer.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

_DATA_PATH = Path(__file__).parent / "data" / "skills.json"
_WORD_CHARS = r"a-z0-9+#"

# Map skills.json section keys → display category names
_SECTION_TO_CATEGORY: dict[str, str] = {
    "tech_skills": "Technical",
    "soft_skills": "Soft skills",
    "certifications": "Certifications",
}


@lru_cache(maxsize=1)
def load_skills() -> dict:
    """Load and cache the bundled skills data."""
    with open(_DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _phrase_regex(phrase: str) -> re.Pattern[str]:
    """Whole-word regex that also works for terms like 'c++', 'c#' and 'ci/cd'."""
    return re.compile(rf"(?<![{_WORD_CHARS}]){re.escape(phrase)}(?![{_WORD_CHARS}])")


def normalize_keyword(keyword: str, aliases: dict[str, str]) -> str:
    """Expand a shorthand alias (e.g. 'k8s') to its canonical form."""
    keyword = keyword.strip().lower()
    return aliases.get(keyword, keyword)


def _alias_forms(skills: dict) -> dict[str, list[str]]:
    """Map each canonical term to the aliases that should also count as a hit."""
    forms: dict[str, list[str]] = {}
    for alias, canonical in skills.get("aliases", {}).items():
        forms.setdefault(canonical, []).append(alias)
    return forms


def _term_category_map(skills: dict) -> dict[str, str]:
    """Return a mapping of canonical term (lowercased) → display category."""
    mapping: dict[str, str] = {}
    for section_key, category in _SECTION_TO_CATEGORY.items():
        for term in skills.get(section_key, []):
            mapping[term.lower()] = category
    return mapping


def _count(text: str, term: str, extra: list[str]) -> int:
    return sum(len(_phrase_regex(t).findall(text)) for t in [term, *extra])


def extract_keywords(cleaned_jd: str) -> list[dict]:
    """Extract skills from a cleaned (lowercased) job description.

    Returns a list of ``{"keyword", "count", "category"}`` dicts sorted by
    count (desc) then alphabetically. A longer skill that merely contains a
    shorter one ("apache kafka" vs "kafka") is kept only once, as the shorter.
    """
    skills = load_skills()
    cat_map = _term_category_map(skills)
    all_terms = set(cat_map.keys())
    forms = _alias_forms(skills)

    counts: dict[str, int] = {}
    for term in all_terms:
        n = _count(cleaned_jd, term, forms.get(term, []))
        if n:
            counts[term] = n

    # Drop "apache kafka" when "kafka" is also a keyword, etc.
    for longer in sorted(counts, key=len, reverse=True):
        for shorter in counts:
            if shorter != longer and _phrase_regex(shorter).search(longer):
                counts[shorter] = max(counts[shorter], counts[longer])
                counts.pop(longer, None)
                break

    return [
        {
            "keyword": kw,
            "count": n,
            "category": cat_map.get(kw, "Technical"),
        }
        for kw, n in sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    ]


def keywords_in_text(
    resume_text: str, keywords: list[dict]
) -> tuple[list[dict], list[dict]]:
    """Split JD keywords into (matched, missing) based on the resume text.

    Args:
        resume_text: Cleaned, lowercased resume text.
        keywords: List of ``{"keyword", "count", "category"}`` dicts (category
            is optional and defaults to ``"Technical"`` for backward compat).

    Returns:
        A tuple ``(matched, missing)`` where:
        - ``matched`` is a list of ``{"keyword", "category"}`` dicts.
        - ``missing`` is a list of ``{"keyword", "count", "category"}`` dicts
          sorted by count descending (importance ranking).
    """
    forms = _alias_forms(load_skills())
    matched: list[dict] = []
    missing: list[dict] = []
    for item in keywords:
        kw = item["keyword"]
        category = item.get("category", "Technical")
        hit = any(_phrase_regex(t).search(resume_text) for t in [kw, *forms.get(kw, [])])
        if hit:
            matched.append({"keyword": kw, "category": category})
        else:
            missing.append(item)
    return matched, missing


def keyword_counter(text: str, keywords: list[dict]) -> Counter:
    """How often each keyword appears in ``text`` (handy for debugging)."""
    forms = _alias_forms(load_skills())
    return Counter({k["keyword"]: _count(text, k["keyword"], forms.get(k["keyword"], [])) for k in keywords})
