"""Tests for tracker.ats: keyword extraction, scoring, tips, report, and validation."""
import pytest

from tracker import ats
from tracker.ats.extractor import check_sections, clean_text
from tracker.ats.keywords import extract_keywords, keywords_in_text
from tracker.ats.report import build_report, group_by_category, score_band
from tracker.ats.scorer import compute_scores
from tracker.ats.tips import generate_tips

JD = (
    "We need a backend engineer with Python, Kubernetes (k8s), Apache Kafka "
    "and good communication. Interest in the REST API space is a plus."
)


def kws(text: str) -> dict[str, int]:
    return {k["keyword"]: k["count"] for k in extract_keywords(clean_text(text))}


# ---------------------------------------------------------------------------
# Keyword extraction
# ---------------------------------------------------------------------------

def test_whole_word_matching_avoids_false_positives():
    found = kws(JD)
    assert "go" not in found  # "good"
    assert "rest" in found or "rest api" in found or "rest apis" in found
    assert "interest" not in found


def test_alias_normalized_and_counted():
    assert kws(JD)["kubernetes"] == 2  # "Kubernetes" + "k8s"


def test_longer_phrase_collapsed_into_shorter_skill():
    found = kws(JD)
    assert "kafka" in found and "apache kafka" not in found


def test_extract_keywords_has_category_field():
    results = extract_keywords(clean_text(JD))
    for item in results:
        assert "category" in item, f"Missing category on {item}"
        assert item["category"] in ("Technical", "Certifications", "Soft skills")


def test_keywords_in_text_uses_aliases():
    matched, missing = keywords_in_text(
        "i run k8s clusters",
        [{"keyword": "kubernetes", "count": 1}, {"keyword": "python", "count": 1}],
    )
    # matched is now list[dict] with keyword + category
    assert len(matched) == 1 and matched[0]["keyword"] == "kubernetes"
    assert missing[0]["keyword"] == "python"


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def test_scores_between_0_and_100():
    r = clean_text("python and kubernetes engineer")
    jd = clean_text(JD)
    s = compute_scores(r, jd, extract_keywords(jd))
    assert 0 <= s["overall_score"] <= 100
    # matched_keywords is now list[dict]
    assert any(k["keyword"] == "python" for k in s["matched_keywords"])


# ---------------------------------------------------------------------------
# Tips
# ---------------------------------------------------------------------------

def test_tips_never_claim_skills_and_flag_gaps():
    tips = generate_tips(
        "short resume",
        [{"keyword": "kafka", "count": 3}],
        check_sections("short resume"),
    )
    assert any("if you have experience" in t and "kafka" in t for t in tips)
    assert any("Skills section" in t for t in tips)


# ---------------------------------------------------------------------------
# report.py — pure functions
# ---------------------------------------------------------------------------

def test_score_band_strong():
    assert score_band(70) == "Strong match"
    assert score_band(100) == "Strong match"


def test_score_band_decent():
    assert score_band(50) == "Decent"
    assert score_band(69.9) == "Decent"


def test_score_band_needs_work():
    assert score_band(0) == "Needs work"
    assert score_band(49.9) == "Needs work"


def test_group_by_category_routes_correctly():
    matched = [
        {"keyword": "python", "category": "Technical"},
        {"keyword": "communication", "category": "Soft skills"},
    ]
    missing = [
        {"keyword": "pmp", "count": 1, "category": "Certifications"},
        {"keyword": "docker", "count": 2, "category": "Technical"},
    ]
    groups = group_by_category(matched, missing)
    assert "python" in groups["Technical"]["matched"]
    assert "communication" in groups["Soft skills"]["matched"]
    assert groups["Certifications"]["missing"][0]["keyword"] == "pmp"
    assert groups["Technical"]["missing"][0]["keyword"] == "docker"
    # unmentioned categories are still present but empty
    assert groups["Certifications"]["matched"] == []


def test_group_by_category_unknown_category_falls_back_to_technical():
    matched = [{"keyword": "widget", "category": "Unknown"}]
    groups = group_by_category(matched, [])
    assert "widget" in groups["Technical"]["matched"]


def test_build_report_contains_key_fields():
    result = {
        "overall_score": 65.0,
        "keyword_coverage_score": 60.0,
        "cosine_similarity_score": 70.0,
        "resume_word_count": 300,
        "matched_keywords": [{"keyword": "python", "category": "Technical"}],
        "missing_keywords": [
            {"keyword": "terraform", "count": 2, "category": "Technical"},
            {"keyword": "pmp", "count": 1, "category": "Certifications"},
        ],
        "section_checks": {
            "summary": True, "experience": True, "education": True, "skills": False
        },
        "tips": ["Add a Skills section."],
    }
    md = build_report(result)
    assert "65" in md
    assert "terraform" in md
    assert "python" in md
    assert "pmp" in md
    assert "Add a Skills section" in md
    assert "Only add skills you actually have" in md


def test_build_report_escapes_html_in_keywords():
    result = {
        "overall_score": 50.0,
        "keyword_coverage_score": 50.0,
        "cosine_similarity_score": 50.0,
        "resume_word_count": 200,
        "matched_keywords": [],
        "missing_keywords": [{"keyword": "<script>", "count": 1, "category": "Technical"}],
        "section_checks": {"summary": True, "experience": True, "education": True, "skills": True},
        "tips": [],
    }
    md = build_report(result)
    assert "<script>" not in md
    assert "&lt;script&gt;" in md


# ---------------------------------------------------------------------------
# End-to-end and validation
# ---------------------------------------------------------------------------

def test_analyze_text_demo_end_to_end():
    res = ats.analyze_text(ats.sample_resume_text(), ats.sample_job_description())
    assert 0 < res["overall_score"] <= 100
    assert res["matched_keywords"] and res["tips"]
    assert not any(
        " our " in f" {k['keyword']} " for k in res["missing_keywords"]
    )  # no sentence-fragment keywords


def test_validation_errors():
    # PDF too large
    with pytest.raises(ValueError, match="5 MB"):
        ats.analyze(b"x" * (5 * 1024 * 1024 + 1), JD)

    # Resume too short (new MIN_RESUME_CHARS check)
    with pytest.raises(ValueError, match="too short"):
        ats.analyze_text("short resume", ats.sample_job_description())

    # JD too short
    with pytest.raises(ValueError, match="50 characters"):
        ats.analyze_text("a" * 150, "too short")

    # No recognizable skills in JD (long enough resume and JD, but no skills)
    with pytest.raises(ValueError, match="recognizable skills"):
        ats.analyze_text("a" * 150, "x " * 40)


def test_validation_min_resume_chars_boundary():
    """Exactly MIN_RESUME_CHARS characters should not raise."""
    # Use sample JD so we don't trigger the skills error
    jd = ats.sample_job_description()
    # Just under the limit → should raise
    with pytest.raises(ValueError, match="too short"):
        ats.analyze_text("a" * (ats.MIN_RESUME_CHARS - 1), jd)
    # Exactly at the limit — may raise for skills/JD reasons, but NOT for length
    try:
        ats.analyze_text("a" * ats.MIN_RESUME_CHARS, jd)
    except ValueError as e:
        assert "too short" not in str(e)
