import type { SectionChecks as SC } from "../types";
import "./SectionChecks.css";

interface Props {
  checks: SC;
  wordCount: number;
}

const SECTION_LABELS: { key: keyof SC; label: string }[] = [
  { key: "summary", label: "Summary / Objective" },
  { key: "experience", label: "Work Experience" },
  { key: "education", label: "Education" },
  { key: "skills", label: "Skills" },
];

export default function SectionChecks({ checks, wordCount }: Props) {
  return (
    <div className="section-checks">
      <div className="section-checks__grid">
        {SECTION_LABELS.map(({ key, label }) => (
          <div key={key} className={`section-pill ${checks[key] ? "section-pill--ok" : "section-pill--missing"}`}>
            <span className="section-pill__icon">{checks[key] ? "✓" : "✗"}</span>
            <span>{label}</span>
          </div>
        ))}
      </div>
      <p className="word-count">Resume word count: <strong>{wordCount}</strong></p>
    </div>
  );
}
