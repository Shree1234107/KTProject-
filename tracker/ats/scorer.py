"""Scoring engine: keyword coverage + TF-IDF cosine similarity blend."""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .keywords import keywords_in_text

KEYWORD_WEIGHT = 0.60
COSINE_WEIGHT = 0.40


def compute_cosine_similarity(text_a: str, text_b: str) -> float:
    """Compute TF-IDF cosine similarity between two text strings.

    Args:
        text_a: First document (cleaned resume text).
        text_b: Second document (cleaned job description text).

    Returns:
        Similarity score in [0, 1].
    """
    if not text_a.strip() or not text_b.strip():
        return 0.0

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=5000,
        sublinear_tf=True,
    )
    tfidf_matrix = vectorizer.fit_transform([text_a, text_b])
    score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    return float(score)


def compute_scores(
    cleaned_resume: str,
    cleaned_jd: str,
    jd_keywords: list[dict],
) -> dict:
    """Compute the overall match score and keyword breakdown.

    Args:
        cleaned_resume: Lowercased, cleaned resume text.
        cleaned_jd: Lowercased, cleaned job description text.
        jd_keywords: Output of :func:`~tracker.ats.keywords.extract_keywords`.

    Returns:
        Dict with:
        - ``overall_score`` (float 0-100)
        - ``keyword_coverage_score`` (float 0-100)
        - ``cosine_similarity_score`` (float 0-100)
        - ``matched_keywords`` (list[str])
        - ``missing_keywords`` (list[dict] with keyword/count, sorted by count desc)
    """
    matched, missing = keywords_in_text(cleaned_resume, jd_keywords)

    total_keywords = len(jd_keywords)
    if total_keywords > 0:
        keyword_coverage = len(matched) / total_keywords
    else:
        keyword_coverage = 0.0

    cosine_sim = compute_cosine_similarity(cleaned_resume, cleaned_jd)

    overall = (keyword_coverage * KEYWORD_WEIGHT + cosine_sim * COSINE_WEIGHT) * 100
    overall = min(100.0, round(overall, 1))

    return {
        "overall_score": overall,
        "keyword_coverage_score": round(keyword_coverage * 100, 1),
        "cosine_similarity_score": round(cosine_sim * 100, 1),
        "matched_keywords": matched,
        "missing_keywords": sorted(missing, key=lambda x: -x["count"]),
    }
