"""Tests for tip generation."""

import pytest

from app.tips import generate_tips


ALL_SECTIONS = {"summary": True, "experience": True, "education": True, "skills": True}
NO_SECTIONS = {"summary": False, "experience": False, "education": False, "skills": False}


class TestGenerateTips:
    def test_missing_keyword_tip_contains_keyword(self):
        missing = [{"keyword": "kubernetes", "count": 4}]
        tips = generate_tips("python developer", missing, ALL_SECTIONS)
        assert any("kubernetes" in t for t in tips)

    def test_missing_keyword_tip_contains_count(self):
        missing = [{"keyword": "kubernetes", "count": 4}]
        tips = generate_tips("python developer", missing, ALL_SECTIONS)
        assert any("4 times" in t for t in tips)

    def test_missing_keyword_singular_count(self):
        missing = [{"keyword": "terraform", "count": 1}]
        tips = generate_tips("python developer", missing, ALL_SECTIONS)
        assert any("1 time" in t for t in tips)

    def test_tip_uses_if_applicable_phrasing(self):
        missing = [{"keyword": "rust", "count": 2}]
        tips = generate_tips("python developer", missing, ALL_SECTIONS)
        keyword_tips = [t for t in tips if "rust" in t]
        assert all("if" in t.lower() for t in keyword_tips)

    def test_missing_summary_section(self):
        sections = {**ALL_SECTIONS, "summary": False}
        tips = generate_tips("some resume text with many words " * 30, [], sections)
        assert any("summary" in t.lower() or "objective" in t.lower() for t in tips)

    def test_missing_skills_section(self):
        sections = {**ALL_SECTIONS, "skills": False}
        tips = generate_tips("some resume text with many words " * 30, [], sections)
        assert any("skills" in t.lower() for t in tips)

    def test_short_resume_tip(self):
        short_resume = "python developer with 2 years experience"
        tips = generate_tips(short_resume, [], ALL_SECTIONS)
        assert any("short" in t.lower() or "expand" in t.lower() for t in tips)

    def test_no_short_resume_tip_for_adequate_resume(self):
        # 7 words * 50 = 350 words, well above MIN_WORDS=200
        adequate = ("python developer with extensive cloud engineering experience " * 50).strip()
        tips = generate_tips(adequate, [], ALL_SECTIONS)
        short_tips = [t for t in tips if "short" in t.lower()]
        assert len(short_tips) == 0

    def test_quantification_tip_when_missing(self):
        resume = "led a team and improved the system using python and aws"
        tips = generate_tips(resume, [], ALL_SECTIONS)
        assert any("quantif" in t.lower() or "%" in t or "number" in t.lower() for t in tips)

    def test_no_quantification_tip_when_present(self):
        resume = "reduced latency by 40% and scaled the system to 1 million users using python"
        tips = generate_tips(resume, [], ALL_SECTIONS)
        quant_tips = [t for t in tips if "quantif" in t.lower()]
        assert len(quant_tips) == 0

    def test_weak_verb_tip(self):
        resume = "worked with python and helped the team to deliver features"
        tips = generate_tips(resume, [], ALL_SECTIONS)
        assert any("verb" in t.lower() or "worked" in t or "helped" in t for t in tips)

    def test_all_sections_present_no_section_tips(self):
        resume = "experienced engineer " * 50
        tips = generate_tips(resume, [], ALL_SECTIONS)
        section_tips = [t for t in tips if "section" in t.lower()]
        assert len(section_tips) == 0

    def test_max_five_missing_keyword_tips(self):
        missing = [{"keyword": f"skill{i}", "count": i + 1} for i in range(10)]
        tips = generate_tips("some resume " * 50, missing, ALL_SECTIONS)
        keyword_tips = [t for t in tips if "if you have experience" in t]
        assert len(keyword_tips) <= 5
