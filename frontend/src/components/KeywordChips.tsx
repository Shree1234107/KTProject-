import type { MatchResult } from "../types";
import "./KeywordChips.css";

interface Props {
  matched: MatchResult["matched_keywords"];
  missing: MatchResult["missing_keywords"];
}

export default function KeywordChips({ matched, missing }: Props) {
  return (
    <div className="keywords-section">
      <div className="kw-group">
        <h3 className="kw-title kw-title--matched">
          <span className="kw-badge kw-badge--matched">{matched.length}</span>
          Matched Keywords
        </h3>
        <div className="chip-list">
          {matched.length === 0 ? (
            <p className="kw-empty">No keywords matched.</p>
          ) : (
            matched.map((kw) => (
              <span key={kw} className="chip chip--matched">{kw}</span>
            ))
          )}
        </div>
      </div>

      <div className="kw-group">
        <h3 className="kw-title kw-title--missing">
          <span className="kw-badge kw-badge--missing">{missing.length}</span>
          Missing Keywords
          <span className="kw-hint">(ranked by JD importance)</span>
        </h3>
        <div className="chip-list">
          {missing.length === 0 ? (
            <p className="kw-empty">Great — no major keywords missing!</p>
          ) : (
            missing.map(({ keyword, count }) => (
              <span key={keyword} className="chip chip--missing" title={`Mentioned ${count}× in JD`}>
                {keyword}
                <span className="chip-count">×{count}</span>
              </span>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
