"""Tests for PDF extraction and text cleaning utilities."""

import io
import textwrap

import pytest

from app.extractor import check_sections, clean_text, extract_text_from_pdf


class TestCleanText:
    def test_lowercases(self):
        assert clean_text("Hello World") == "hello world"

    def test_collapses_spaces(self):
        assert clean_text("a   b\t\tc") == "a b c"

    def test_strips_control_chars(self):
        result = clean_text("hello\x00world")
        assert "\x00" not in result

    def test_collapses_excessive_newlines(self):
        text = "line1\n\n\n\n\nline2"
        result = clean_text(text)
        assert "\n\n\n" not in result

    def test_preserves_double_newline(self):
        text = "paragraph1\n\nparagraph2"
        result = clean_text(text)
        assert "\n\n" in result

    def test_empty_string(self):
        assert clean_text("") == ""


class TestCheckSections:
    RESUME = textwrap.dedent("""\
        Summary
        Experienced software engineer.

        Experience
        Company A — 2020-2023

        Education
        B.S. Computer Science, 2020

        Skills
        Python, JavaScript
    """)

    def test_all_sections_found(self):
        result = check_sections(self.RESUME)
        assert result["summary"] is True
        assert result["experience"] is True
        assert result["education"] is True
        assert result["skills"] is True

    def test_missing_summary(self):
        text = "Experience\nSoftware Engineer\n\nEducation\nBS CS\n\nSkills\nPython"
        result = check_sections(text)
        assert result["summary"] is False
        assert result["experience"] is True

    def test_objective_counts_as_summary(self):
        text = "Objective\nTo obtain a software engineering role.\n\nExperience\n..."
        result = check_sections(text)
        assert result["summary"] is True

    def test_empty_resume(self):
        result = check_sections("")
        assert all(v is False for v in result.values())


class TestExtractTextFromPDF:
    def test_raises_on_empty_bytes(self):
        with pytest.raises(Exception):
            extract_text_from_pdf(b"not a pdf")

    def test_raises_value_error_on_no_text(self, tmp_path):
        """A minimal valid PDF with no text content raises ValueError."""
        # Minimal PDF structure with one empty page
        minimal_pdf = (
            b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
            b"xref\n0 4\n"
            b"0000000000 65535 f \n"
            b"0000000009 00000 n \n"
            b"0000000058 00000 n \n"
            b"0000000115 00000 n \n"
            b"trailer<</Size 4/Root 1 0 R>>\n"
            b"startxref\n190\n%%EOF"
        )
        with pytest.raises(ValueError, match="No extractable text"):
            extract_text_from_pdf(minimal_pdf)
