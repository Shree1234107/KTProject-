import { describe, it, expect } from "vitest";
import type { MatchResult } from "../types";

// Pure helper functions derived from API response — no React imports needed

function getScoreLabel(score: number): string {
  if (score >= 70) return "Strong Match";
  if (score >= 45) return "Moderate Match";
  return "Needs Work";
}

function getScoreColor(score: number): string {
  if (score >= 70) return "#16a34a";
  if (score >= 45) return "#2563eb";
  return "#ea580c";
}

function countMissingSections(result: MatchResult): number {
  return Object.values(result.section_checks).filter((v) => !v).length;
}

describe("getScoreLabel", () => {
  it("returns Strong Match for 70+", () => {
    expect(getScoreLabel(70)).toBe("Strong Match");
    expect(getScoreLabel(100)).toBe("Strong Match");
  });
  it("returns Moderate Match for 45-69", () => {
    expect(getScoreLabel(45)).toBe("Moderate Match");
    expect(getScoreLabel(69)).toBe("Moderate Match");
  });
  it("returns Needs Work for below 45", () => {
    expect(getScoreLabel(0)).toBe("Needs Work");
    expect(getScoreLabel(44)).toBe("Needs Work");
  });
});

describe("getScoreColor", () => {
  it("is green for 70+", () => expect(getScoreColor(80)).toBe("#16a34a"));
  it("is blue for 45-69", () => expect(getScoreColor(50)).toBe("#2563eb"));
  it("is orange for below 45", () => expect(getScoreColor(20)).toBe("#ea580c"));
});

describe("countMissingSections", () => {
  const makeResult = (overrides: Partial<MatchResult["section_checks"]>): MatchResult => ({
    overall_score: 50,
    keyword_coverage_score: 50,
    cosine_similarity_score: 50,
    matched_keywords: [],
    missing_keywords: [],
    section_checks: {
      summary: true,
      experience: true,
      education: true,
      skills: true,
      ...overrides,
    },
    tips: [],
    resume_word_count: 300,
  });

  it("returns 0 when all sections present", () => {
    expect(countMissingSections(makeResult({}))).toBe(0);
  });
  it("counts missing sections correctly", () => {
    expect(countMissingSections(makeResult({ summary: false, skills: false }))).toBe(2);
  });
});
