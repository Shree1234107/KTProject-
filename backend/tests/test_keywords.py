"""Tests for keyword extraction and normalization."""

import pytest

from app.keywords import _is_stopword_phrase, extract_keywords, keywords_in_text, normalize_keyword


class TestNormalizeKeyword:
    ALIASES = {"js": "javascript", "ts": "typescript", "k8s": "kubernetes", "ml": "machine learning"}

    def test_expands_alias(self):
        assert normalize_keyword("js", self.ALIASES) == "javascript"
        assert normalize_keyword("k8s", self.ALIASES) == "kubernetes"

    def test_passthrough_unknown(self):
        assert normalize_keyword("python", self.ALIASES) == "python"

    def test_strips_whitespace(self):
        assert normalize_keyword("  ml  ", self.ALIASES) == "machine learning"


class TestIsStopwordPhrase:
    def test_all_stopwords_is_true(self):
        assert _is_stopword_phrase("you and we") is True

    def test_technical_phrase_is_false(self):
        assert _is_stopword_phrase("machine learning pipeline") is False

    def test_empty_is_true(self):
        assert _is_stopword_phrase("") is True


class TestExtractKeywords:
    JD = """
    we are looking for a senior software engineer with strong python and
    machine learning experience. kubernetes and docker are required.
    knowledge of postgresql and redis is a plus. ci/cd with github actions.
    strong communication skills required. kubernetes kubernetes kubernetes.
    """

    def test_returns_list_of_dicts(self):
        result = extract_keywords(self.JD)
        assert isinstance(result, list)
        assert all("keyword" in item and "count" in item for item in result)

    def test_finds_python(self):
        result = extract_keywords(self.JD)
        kws = [item["keyword"] for item in result]
        assert "python" in kws

    def test_finds_kubernetes(self):
        result = extract_keywords(self.JD)
        kws = [item["keyword"] for item in result]
        assert "kubernetes" in kws

    def test_finds_machine_learning(self):
        result = extract_keywords(self.JD)
        kws = [item["keyword"] for item in result]
        assert "machine learning" in kws

    def test_sorted_by_count_desc(self):
        result = extract_keywords(self.JD)
        counts = [item["count"] for item in result]
        assert counts == sorted(counts, reverse=True)

    def test_kubernetes_highest_count(self):
        result = extract_keywords(self.JD)
        top_kw = result[0]["keyword"]
        assert top_kw == "kubernetes"

    def test_empty_jd(self):
        result = extract_keywords("")
        assert isinstance(result, list)


class TestKeywordsInText:
    KEYWORDS = [
        {"keyword": "python", "count": 3},
        {"keyword": "kubernetes", "count": 2},
        {"keyword": "machine learning", "count": 1},
        {"keyword": "terraform", "count": 1},
    ]

    RESUME = "experience with python and machine learning. some kubernetes work too."

    def test_matched_keywords(self):
        matched, _ = keywords_in_text(self.RESUME, self.KEYWORDS)
        assert "python" in matched
        assert "machine learning" in matched
        assert "kubernetes" in matched

    def test_missing_keywords(self):
        _, missing = keywords_in_text(self.RESUME, self.KEYWORDS)
        kws = [m["keyword"] for m in missing]
        assert "terraform" in kws

    def test_missing_retains_count(self):
        _, missing = keywords_in_text(self.RESUME, self.KEYWORDS)
        terraform = next(m for m in missing if m["keyword"] == "terraform")
        assert terraform["count"] == 1
