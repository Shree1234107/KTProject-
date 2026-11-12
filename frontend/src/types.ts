export interface SectionChecks {
  summary: boolean;
  experience: boolean;
  education: boolean;
  skills: boolean;
}

export interface MatchResult {
  overall_score: number;
  keyword_coverage_score: number;
  cosine_similarity_score: number;
  matched_keywords: string[];
  missing_keywords: Array<{ keyword: string; count: number }>;
  section_checks: SectionChecks;
  tips: string[];
  resume_word_count: number;
}

export type AppState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; result: MatchResult }
  | { status: "error"; message: string };
