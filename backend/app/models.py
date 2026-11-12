"""Pydantic models for API request/response."""

from pydantic import BaseModel, Field


class SectionChecks(BaseModel):
    summary: bool
    experience: bool
    education: bool
    skills: bool


class MissingKeyword(BaseModel):
    keyword: str
    count: int = Field(description="Occurrences in the job description")


class MatchResult(BaseModel):
    overall_score: float = Field(ge=0, le=100)
    keyword_coverage_score: float = Field(ge=0, le=100)
    cosine_similarity_score: float = Field(ge=0, le=100)
    matched_keywords: list[str]
    missing_keywords: list[MissingKeyword]
    section_checks: SectionChecks
    tips: list[str]
    resume_word_count: int
