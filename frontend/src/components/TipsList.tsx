import "./TipsList.css";

interface Props {
  tips: string[];
}

export default function TipsList({ tips }: Props) {
  if (tips.length === 0) {
    return (
      <div className="tips-empty">
        <span>Your resume looks well-optimized for this role.</span>
      </div>
    );
  }

  return (
    <ul className="tips-list">
      {tips.map((tip, i) => (
        <li key={i} className="tip-item">
          <span className="tip-icon">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M8 1.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13zM8 5v4M8 10.5v.5" stroke="#2563eb" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </span>
          <span className="tip-text">{tip}</span>
        </li>
      ))}
    </ul>
  );
}
