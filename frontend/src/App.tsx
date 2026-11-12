import "./App.css";

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <div className="header-inner">
          <div className="logo">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <rect width="28" height="28" rx="8" fill="#2563eb" />
              <path d="M7 9h14M7 14h9M7 19h11" stroke="white" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <span>ATS Matcher</span>
          </div>
          <p className="tagline">Know how your resume stacks up</p>
        </div>
      </header>
      <main className="app-main">
        <p className="placeholder-text">Upload form coming soon…</p>
      </main>
    </div>
  );
}
