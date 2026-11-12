"""Tests for the scoring engine."""

import pytest

from app.scorer import compute_cosine_similarity, compute_scores


class TestComputeCosineSimilarity:
    def test_identical_texts_score_one(self):
        text = "python machine learning kubernetes docker aws"
        score = compute_cosine_similarity(text, text)
        assert score > 0.99

    def test_empty_text_returns_zero(self):
        assert compute_cosine_similarity("", "some text") == 0.0
        assert compute_cosine_similarity("some text", "") == 0.0

    def test_unrelated_texts_low_score(self):
        resume = "baking bread sourdough flour yeast dough oven"
        jd = "python kubernetes aws docker microservices"
        score = compute_cosine_similarity(resume, jd)
        assert score < 0.3

    def test_similar_texts_high_score(self):
        resume = "python developer with aws and kubernetes experience"
        jd = "looking for python developer with kubernetes and aws skills"
        score = compute_cosine_similarity(resume, jd)
        assert score > 0.25

    def test_score_in_range(self):
        a = "python django rest api postgresql"
        b = "django python api postgres react"
        score = compute_cosine_similarity(a, b)
        assert 0.0 <= score <= 1.0


class TestComputeScores:
    KEYWORDS = [
        {"keyword": "python", "count": 5},
        {"keyword": "kubernetes", "count": 4},
        {"keyword": "docker", "count": 3},
        {"keyword": "terraform", "count": 1},
    ]

    def test_all_matched_gives_high_score(self):
        resume = "python kubernetes docker terraform expert with years of experience"
        jd = "python kubernetes docker terraform required"
        scores = compute_scores(resume, jd, self.KEYWORDS)
        assert scores["overall_score"] > 60

    def test_nothing_matched_gives_low_score(self):
        resume = "baking cooking recipe pastry"
        jd = "python kubernetes docker terraform required"
        scores = compute_scores(resume, jd, self.KEYWORDS)
        assert scores["overall_score"] < 30

    def test_matched_keywords_present(self):
        resume = "python developer with docker and kubernetes experience"
        scores = compute_scores(resume, "python docker kubernetes", self.KEYWORDS)
        assert "python" in scores["matched_keywords"]
        assert "docker" in scores["matched_keywords"]

    def test_missing_keywords_sorted_by_count(self):
        resume = "java developer"
        jd = "python kubernetes docker terraform"
        scores = compute_scores(resume, jd, self.KEYWORDS)
        counts = [kw["count"] for kw in scores["missing_keywords"]]
        assert counts == sorted(counts, reverse=True)

    def test_overall_score_in_range(self):
        resume = "python kubernetes"
        jd = "python kubernetes docker"
        scores = compute_scores(resume, jd, self.KEYWORDS)
        assert 0 <= scores["overall_score"] <= 100

    def test_empty_keywords_list(self):
        scores = compute_scores("some resume text", "some jd text", [])
        assert scores["keyword_coverage_score"] == 0.0
        assert scores["matched_keywords"] == []
