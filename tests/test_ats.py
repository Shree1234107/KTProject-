import pytest

from tracker import ats
from tracker.ats.extractor import check_sections, clean_text
from tracker.ats.keywords import extract_keywords, keywords_in_text
from tracker.ats.scorer import compute_scores
from tracker.ats.tips import generate_tips

JD = "We need a backend engineer with Python, Kubernetes (k8s), Apache Kafka and good communication. Interest in the REST API space is a plus."


def kws(text):
    return {k["keyword"]: k["count"] for k in extract_keywords(clean_text(text))}


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


def test_keywords_in_text_uses_aliases():
    matched, missing = keywords_in_text("i run k8s clusters", [{"keyword": "kubernetes", "count": 1}, {"keyword": "python", "count": 1}])
    assert matched == ["kubernetes"] and missing[0]["keyword"] == "python"


def test_scores_between_0_and_100():
    r = clean_text("python and kubernetes engineer")
    jd = clean_text(JD)
    s = compute_scores(r, jd, extract_keywords(jd))
    assert 0 <= s["overall_score"] <= 100 and "python" in s["matched_keywords"]


def test_tips_never_claim_skills_and_flag_gaps():
    tips = generate_tips("short resume", [{"keyword": "kafka", "count": 3}], check_sections("short resume"))
    assert any("if you have experience" in t and "kafka" in t for t in tips)
    assert any("Skills section" in t for t in tips)


def test_analyze_text_demo_end_to_end():
    res = ats.analyze_text(ats.sample_resume_text(), ats.sample_job_description())
    assert 0 < res["overall_score"] <= 100
    assert res["matched_keywords"] and res["tips"]
    assert not any(" our " in f" {k['keyword']} " for k in res["missing_keywords"])  # no sentence-fragment keywords


def test_validation_errors():
    with pytest.raises(ValueError):
        ats.analyze_text("resume", "too short")
    with pytest.raises(ValueError):
        ats.analyze(b"x" * (5 * 1024 * 1024 + 1), JD)
    with pytest.raises(ValueError):
        ats.analyze_text("resume text", "x " * 40)  # no recognizable skills
