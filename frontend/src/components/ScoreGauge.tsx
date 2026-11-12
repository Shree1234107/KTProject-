import "./ScoreGauge.css";

interface Props {
  score: number;
  keywordScore: number;
  cosineScore: number;
}

function getScoreColor(score: number): string {
  if (score >= 70) return "#16a34a";
  if (score >= 45) return "#2563eb";
  return "#ea580c";
}

function getScoreLabel(score: number): string {
  if (score >= 70) return "Strong Match";
  if (score >= 45) return "Moderate Match";
  return "Needs Work";
}

export default function ScoreGauge({ score, keywordScore, cosineScore }: Props) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.min(score / 100, 1);
  const dash = pct * circumference;
  const color = getScoreColor(score);

  return (
    <div className="gauge-container">
      <div className="gauge-ring-wrap">
        <svg className="gauge-ring" viewBox="0 0 128 128" width="160" height="160">
          <circle
            cx="64" cy="64" r={radius}
            fill="none" stroke="var(--blue-100)"
            strokeWidth="12"
          />
          <circle
            cx="64" cy="64" r={radius}
            fill="none"
            stroke={color}
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={`${dash} ${circumference}`}
            transform="rotate(-90 64 64)"
            style={{ transition: "stroke-dasharray 0.6s ease" }}
          />
        </svg>
        <div className="gauge-inner">
          <span className="gauge-score" style={{ color }}>{score}</span>
          <span className="gauge-out-of">/100</span>
        </div>
      </div>
      <div className="gauge-label" style={{ color }}>{getScoreLabel(score)}</div>
      <div className="gauge-breakdown">
        <div className="gauge-sub">
          <span className="gauge-sub-label">Keyword Coverage</span>
          <span className="gauge-sub-val">{keywordScore}%</span>
          <div className="gauge-bar">
            <div className="gauge-bar-fill" style={{ width: `${keywordScore}%`, background: color }} />
          </div>
        </div>
        <div className="gauge-sub">
          <span className="gauge-sub-label">Content Similarity</span>
          <span className="gauge-sub-val">{cosineScore}%</span>
          <div className="gauge-bar">
            <div className="gauge-bar-fill" style={{ width: `${cosineScore}%`, background: color }} />
          </div>
        </div>
      </div>
    </div>
  );
}
