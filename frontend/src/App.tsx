import { useState } from "react";
import type { AppState, MatchResult } from "./types";
import UploadForm from "./components/UploadForm";
import ScoreGauge from "./components/ScoreGauge";
import KeywordChips from "./components/KeywordChips";
import TipsList from "./components/TipsList";
import SectionChecks from "./components/SectionChecks";
import "./App.css";

export default function App() {
  const [state, setState] = useState<AppState>({ status: "idle" });

  const handleResult = (result: MatchResult) =>
    setState({ status: "success", result });

  const handleError = (message: string) =>
    setState({ status: "error", message });

  const handleLoading = (loading: boolean) => {
    if (loading) setState({ status: "loading" });
  };

  const reset = () => setState({ status: "idle" });

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-inner">
          <div className="logo">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <rect width="28" height="28" rx="8" fill="#2563eb" />
              <path d="M7 9h14M7 14h9M7 19h11" stroke="white" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <span>ATS Resume Matcher</span>
          </div>
          <p className="tagline">Know how your resume stacks up</p>
        </div>
      </header>

      <main className="app-main">
        {state.status === "idle" && (
          <div className="page-idle">
            <div className="hero">
              <h1 className="hero-title">Score your resume against any job</h1>
              <p className="hero-sub">
                Upload your PDF resume and paste a job description. We'll analyze keyword
                coverage, content similarity, and give you specific tips to improve your match.
              </p>
              <div className="disclaimer">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <circle cx="7" cy="7" r="6" stroke="#94a3b8" strokeWidth="1.3"/>
                  <path d="M7 5v3M7 9.5v.3" stroke="#94a3b8" strokeWidth="1.3" strokeLinecap="round"/>
                </svg>
                This is an estimate, not a real ATS system. Scores are indicative only.
              </div>
            </div>
            <div className="card">
              <UploadForm
                onResult={handleResult}
                onError={handleError}
                onLoading={handleLoading}
                isLoading={false}
              />
            </div>
          </div>
        )}

        {state.status === "loading" && (
          <div className="page-idle">
            <div className="hero">
              <h1 className="hero-title">Score your resume against any job</h1>
              <p className="hero-sub">
                Upload your PDF resume and paste a job description. We'll analyze keyword
                coverage, content similarity, and give you specific tips to improve your match.
              </p>
              <div className="disclaimer">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <circle cx="7" cy="7" r="6" stroke="#94a3b8" strokeWidth="1.3"/>
                  <path d="M7 5v3M7 9.5v.3" stroke="#94a3b8" strokeWidth="1.3" strokeLinecap="round"/>
                </svg>
                This is an estimate, not a real ATS system. Scores are indicative only.
              </div>
            </div>
            <div className="card">
              <UploadForm
                onResult={handleResult}
                onError={handleError}
                onLoading={handleLoading}
                isLoading={true}
              />
            </div>
          </div>
        )}

        {state.status === "error" && (
          <div className="page-idle">
            <div className="hero">
              <h1 className="hero-title">Score your resume against any job</h1>
            </div>
            <div className="error-banner">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <circle cx="9" cy="9" r="8" stroke="#dc2626" strokeWidth="1.5"/>
                <path d="M9 5v5M9 12v.5" stroke="#dc2626" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
              <span>{state.message}</span>
            </div>
            <div className="card">
              <UploadForm
                onResult={handleResult}
                onError={handleError}
                onLoading={handleLoading}
                isLoading={false}
              />
            </div>
          </div>
        )}

        {state.status === "success" && (
          <div className="page-results">
            <div className="results-top-bar">
              <h2 className="results-heading">Analysis Results</h2>
              <button className="btn-secondary" onClick={reset}>← Analyze Another</button>
            </div>

            <div className="results-grid">
              <div className="card results-score-card">
                <h3 className="card-title">Overall Score</h3>
                <ScoreGauge
                  score={state.result.overall_score}
                  keywordScore={state.result.keyword_coverage_score}
                  cosineScore={state.result.cosine_similarity_score}
                />
              </div>

              <div className="card">
                <h3 className="card-title">Resume Sections</h3>
                <SectionChecks
                  checks={state.result.section_checks}
                  wordCount={state.result.resume_word_count}
                />
              </div>
            </div>

            <div className="card">
              <h3 className="card-title">Keywords</h3>
              <KeywordChips
                matched={state.result.matched_keywords}
                missing={state.result.missing_keywords}
              />
            </div>

            <div className="card">
              <h3 className="card-title">Improvement Tips</h3>
              <TipsList tips={state.result.tips} />
            </div>
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>ATS Resume Matcher · NLP-powered · No files stored · Scores are estimates only</p>
      </footer>
    </div>
  );
}
