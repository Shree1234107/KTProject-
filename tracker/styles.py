"""Shared visual setup for the Internship Tracker.

Everything about how the app looks lives here:
- TOKENS: the palette, used by both the CSS and (later) the Altair theme.
- CSS: the stylesheet injected into every page.
- setup(): call once in app.py, right after st.set_page_config.

To change a color, edit TOKENS and the matching variable in CSS section 0.
"""
from __future__ import annotations

import altair as alt
import streamlit as st

# Palette — keep in sync with CSS section 0 (":root").
TOKENS = {
    "page_bg": "#F6F3ED",
    "surface": "#FCFBF8",
    "surface_muted": "#EEEAE2",
    "text": "#292923",
    "muted": "#66655D",
    "rule": "#E3DED5",
    "olive": "#4E5947",
    "olive_hover": "#3D4737",
    "olive_mid": "#8A957F",
    "olive_light": "#C9D0BC",
    "negative": "#8A5A44",
    "serif": 'Georgia, "Times New Roman", serif',
    "sans": 'system-ui, -apple-system, "Segoe UI", sans-serif',
}

CSS = r"""
/* ================================================================
 * KTProject Internship Tracker visual theme
 * Warm editorial minimalist: ivory page, near-white surfaces,
 * dark olive accent. Flat — borders over shadows, no gradients.
 * Tested against Streamlit 1.67.0
 *
 * To change a color, update the design tokens in section 0 below.
 * The legacy --c-* names are aliases kept so every rule below picks
 * up the tokens without renaming. Data-testid selectors (e.g.
 * [data-testid="stButton"]) are stable across minor Streamlit
 * releases. Avoid targeting st-emotion-cache-* class names.
 * ================================================================ */

/* ------------------------------------------------------------------ */
/* 0. Design tokens                                                    */
/* ------------------------------------------------------------------ */
:root {
  /* Surfaces */
  --page-bg:       #F6F3ED;   /* warm ivory, whole viewport          */
  --surface:       #FCFBF8;   /* near-white content surfaces         */
  --surface-muted: #EEEAE2;   /* secondary surfaces, hovers          */
  --surface-hover: #F3EFE7;   /* subtle warm-neutral row hover       */
  --border:        #E3DED5;

  /* Text — contrast on --surface: primary ~14:1, secondary ~5.8:1  */
  --text-primary:   #292923;
  --text-secondary: #66655D;

  /* Accent — dark olive */
  --accent:       #4E5947;    /* ~7:1 on --surface                   */
  --accent-hover: #3D4737;
  --accent-soft:  #E7EBDD;
  --accent-faint: #F1F3EA;
  --olive-mid:    #8A957F;
  --olive-light:  #C9D0BC;
  --negative:     #8A5A44;   /* muted brown, ~5.5:1 on --surface */
  --serif: Georgia, "Times New Roman", serif;
  --accent-line:  #CDD4C0;
  --accent-mid:   #6B7761;    /* ≥4.5:1 on --surface, used as text   */
  --accent-deep:  #2F3829;

  /* Radii */
  --r-control: 6px;           /* buttons, inputs, tags               */
  --r-surface: 10px;          /* tables, cards, forms, expanders     */

  /* Spacing scale: 4, 8, 12, 16, 24, 32, 48 */
  --s-1: 4px;  --s-2: 8px;  --s-3: 12px; --s-4: 16px;
  --s-5: 24px; --s-6: 32px; --s-7: 48px;

  /* Legacy aliases (do not add new uses — reference tokens above) */
  --c-white:    var(--surface);
  --c-bg-1:     var(--surface);
  --c-bg-2:     var(--surface-muted);
  --c-border:   var(--border);
  --c-blue-50:  var(--accent-faint);
  --c-blue-100: var(--accent-soft);
  --c-blue-200: var(--accent-line);
  --c-blue-400: var(--accent-mid);
  --c-blue-600: var(--accent);
  --c-blue-700: var(--accent-hover);
  --c-blue-900: var(--accent-deep);
  --c-text:     var(--text-primary);
  --c-text-sec: var(--text-secondary);
}

/* ------------------------------------------------------------------ */
/* 1. Base: radii and font                                             */
/* ------------------------------------------------------------------ */

/* Controls get 6–8px corners; surfaces get 10px (see later sections) */
button,
input,
textarea,
[data-baseweb="select"] > div:first-child,
[data-baseweb="input"],
[data-baseweb="input"] > div,
[data-baseweb="tag"],
[data-baseweb="popover"],
[data-baseweb="popover"] > div {
  border-radius: var(--r-control) !important;
}

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stSidebar"],
button, input, textarea, select,
[data-baseweb="select"],
[data-baseweb="input"] {
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif !important;
}

/* ------------------------------------------------------------------ */
/* 2. Typography                                                        */
/* ------------------------------------------------------------------ */

body, p, li, label {
  color: var(--text-primary);
}

/* Main page heading — editorial serif, regular weight */
h1 {
  font-family: Georgia, "Times New Roman", serif !important;
  font-size: 36px !important;
  font-weight: 400 !important;
  line-height: 1.2 !important;
  color: var(--text-primary) !important;
  letter-spacing: -0.005em;
  padding: 0 0 var(--s-3) !important;
}

/* Section headers as small uppercase labels */
h2 {
  font-size: 1.0rem !important;
  font-weight: 700 !important;
  color: var(--c-text) !important;
  letter-spacing: 0.01em;
}

h3 {
  font-size: 0.72rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  color: var(--c-text-sec) !important;
  border-bottom: 1px solid var(--c-border);
  padding-bottom: 5px !important;
  margin-bottom: 10px !important;
}

/* Tabular numbers for metrics and scores */
[data-testid="stMetricValue"],
.ats-score-num {
  font-variant-numeric: tabular-nums;
}

/* ------------------------------------------------------------------ */
/* 3. Layout — main area and sidebar                                   */
/* ------------------------------------------------------------------ */

/* Warm ivory across the entire viewport, flat */
html, body,
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stHeader"],
[data-testid="stBottom"] > div {
  background: var(--page-bg) !important;
}

/* Centered content column, max ~1200px, 40px desktop padding */
[data-testid="stMainBlockContainer"],
.block-container {
  max-width: 1200px !important;
  margin: 0 auto !important;
  padding: var(--s-6) 40px var(--s-7) !important;
}

/* Sidebar: muted warm surface, right border */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div:first-child {
  background: var(--surface-muted) !important;
}

[data-testid="stSidebar"] {
  border-right: 1px solid var(--border) !important;
}

[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
  font-size: 0.65rem !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
  color: var(--c-text-sec) !important;
  border-bottom: 1px solid var(--c-border) !important;
  padding-bottom: 4px !important;
}

hr {
  border: none !important;
  border-top: 1px solid var(--c-border) !important;
}

/* ------------------------------------------------------------------ */
/* 4. Tabs                                                             */
/* ------------------------------------------------------------------ */

[data-baseweb="tab-list"] {
  background: transparent !important;
  border-bottom: 1px solid var(--c-border) !important;
  gap: 0 !important;
}

[data-baseweb="tab"] {
  background: transparent !important;
  border: none !important;
  border-radius: var(--r-control) var(--r-control) 0 0 !important;
  padding: var(--s-2) var(--s-4) !important;
  margin-right: var(--s-1) !important;
  font-size: 0.9rem !important;
  font-weight: 500 !important;
  color: var(--text-secondary) !important;
  transition: background 150ms, color 150ms;
}

[data-baseweb="tab"] p {
  font-size: 0.9rem !important;
  color: inherit !important;
}

[data-baseweb="tab"]:hover {
  background: var(--surface-muted) !important;
  color: var(--text-primary) !important;
}

/* Active tab: dark text, semibold, olive underline — not colour alone */
[data-baseweb="tab"][aria-selected="true"] {
  color: var(--text-primary) !important;
  font-weight: 600 !important;
}

[data-baseweb="tab"][aria-selected="true"] p {
  font-weight: 600 !important;
}

[data-baseweb="tab"]:focus-visible {
  outline: 2px solid var(--accent) !important;
  outline-offset: -2px !important;
}

/* Active tab bottom-line indicator */
[data-baseweb="tab-highlight"] {
  background: var(--accent) !important;
  height: 2px !important;
}

[data-baseweb="tab-border"] {
  background: transparent !important;
}

/* Tab content panel fade-in */
[data-testid="stTabsContent"] > div[role="tabpanel"] {
  animation: fade-up 250ms ease-out both;
}

/* ------------------------------------------------------------------ */
/* 5. Buttons                                                          */
/* ------------------------------------------------------------------ */

button {
  transition: background-color 150ms, border-color 150ms, color 150ms !important;
}

/* Primary buttons: solid blue */
[data-testid^="stBaseButton"][kind="primary"],
[data-testid="stFormSubmitButton"] button {
  background: var(--c-blue-600) !important;
  border: 1px solid var(--c-blue-600) !important;
  color: var(--c-white) !important;
}

[data-testid^="stBaseButton"][kind="primary"]:hover,
[data-testid="stFormSubmitButton"] button:hover {
  background: var(--c-blue-700) !important;
  border-color: var(--c-blue-700) !important;
}

/* Primary/submit button text stays light on olive */
[data-testid^="stBaseButton"][kind="primary"] p,
[data-testid="stFormSubmitButton"] button p {
  color: var(--surface) !important;
}

/* Secondary buttons: near-white with a subtle border */
[data-testid^="stBaseButton"][kind="secondary"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  color: var(--text-primary) !important;
}

[data-testid^="stBaseButton"][kind="secondary"]:hover {
  background: var(--surface-muted) !important;
  border-color: var(--accent-line) !important;
  color: var(--text-primary) !important;
}

[data-testid^="stBaseButton"]:disabled {
  opacity: 0.55 !important;
}

/* Focus outline: visible on keyboard nav */
button:focus-visible,
input:focus-visible,
textarea:focus-visible,
summary:focus-visible,
[role="checkbox"]:focus-visible,
[role="radio"]:focus-visible {
  outline: 2px solid var(--accent) !important;
  outline-offset: 2px !important;
}

/* Download buttons share secondary style */
[data-testid="stDownloadButton"] button {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  color: var(--text-primary) !important;
}

[data-testid="stDownloadButton"] button:hover {
  background: var(--surface-muted) !important;
  border-color: var(--accent-line) !important;
}

/* ------------------------------------------------------------------ */
/* 6. Text inputs, textareas, date inputs                             */
/* ------------------------------------------------------------------ */

[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input {
  border: 1px solid var(--c-border) !important;
  background: var(--c-white) !important;
  color: var(--c-text) !important;
  transition: border-color 150ms !important;
}

[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stDateInput"] input:focus {
  border-color: var(--c-blue-600) !important;
  box-shadow: none !important;
}

[data-testid="stTextArea"] textarea {
  border: 1px solid var(--c-border) !important;
  background: var(--c-white) !important;
  color: var(--c-text) !important;
  transition: border-color 150ms !important;
}

[data-testid="stTextArea"] textarea:focus {
  border-color: var(--c-blue-600) !important;
  box-shadow: none !important;
}

/* ------------------------------------------------------------------ */
/* 7. Selectbox and multiselect                                        */
/* ------------------------------------------------------------------ */

[data-baseweb="select"] > div:first-child,
[data-baseweb="input"] > div {
  border: 1px solid var(--c-border) !important;
  background: var(--c-white) !important;
  transition: border-color 150ms !important;
}

[data-baseweb="select"]:focus-within > div:first-child,
[data-baseweb="input"]:focus-within > div {
  border-color: var(--c-blue-600) !important;
  box-shadow: none !important;
}

/* Dropdown popup menu */
[data-baseweb="popover"] {
  border: 1px solid var(--c-border) !important;
  box-shadow: none !important;
}

[data-baseweb="menu"] {
  border: none !important;
  box-shadow: none !important;
}

[role="option"]:hover,
[role="option"][aria-selected="true"] {
  background: var(--c-blue-50) !important;
  color: var(--c-blue-700) !important;
}

/* Multiselect tags */
[data-baseweb="tag"] {
  background: var(--c-blue-100) !important;
  color: var(--c-blue-900) !important;
  border: 1px solid var(--c-blue-200) !important;
}

/* ------------------------------------------------------------------ */
/* 8. File uploader                                                    */
/* ------------------------------------------------------------------ */

[data-testid="stFileUploadDropzone"] {
  border: 1px dashed var(--c-blue-400) !important;
  background: var(--c-blue-50) !important;
  transition: border-color 150ms, background 150ms !important;
}

[data-testid="stFileUploadDropzone"]:hover {
  border-color: var(--c-blue-600) !important;
  background: var(--c-blue-100) !important;
}

/* ------------------------------------------------------------------ */
/* 9. Metrics                                                          */
/* ------------------------------------------------------------------ */

[data-testid="stMetric"] {
  border: 1px solid var(--c-border);
  background: var(--c-bg-1);
  padding: 12px 16px !important;
}

[data-testid="stMetricLabel"] {
  font-size: 0.7rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  color: var(--c-text-sec) !important;
}

[data-testid="stMetricValue"] {
  font-size: 1.5rem !important;
  font-weight: 700 !important;
  color: var(--c-blue-700) !important;
  font-variant-numeric: tabular-nums;
}

[data-testid="stMetricDelta"] {
  color: var(--c-blue-400) !important;
}

/* ------------------------------------------------------------------ */
/* 10. Alerts — all types become a blue left-border note box          */
/* ------------------------------------------------------------------ */

[data-testid="stAlert"],
[data-baseweb="notification"] {
  background: var(--accent-faint) !important;
  border: 1px solid var(--border) !important;
  border-left: 3px solid var(--accent) !important;
  border-radius: var(--r-control) !important;
  color: var(--text-primary) !important;
  box-shadow: none !important;
}

[data-testid="stAlert"] > div,
[data-baseweb="notification"] > div {
  background: transparent !important;
}

[data-testid="stAlert"] svg,
[data-baseweb="notification"] svg {
  fill: var(--c-blue-600) !important;
  color: var(--c-blue-600) !important;
}

/* ------------------------------------------------------------------ */
/* 11. Expanders                                                       */
/* ------------------------------------------------------------------ */

[data-testid="stExpander"] details,
[data-testid="stExpander"] {
  border-color: var(--border) !important;
  background: var(--surface) !important;
  border-radius: var(--r-surface) !important;
  box-shadow: none !important;
}

[data-testid="stExpander"] details {
  border: 1px solid var(--border) !important;
  overflow: hidden;
}

[data-testid="stExpander"] summary {
  font-size: 0.9rem !important;
  color: var(--text-primary) !important;
  padding: var(--s-3) var(--s-4) !important;
}

[data-testid="stExpander"] summary:hover {
  background: var(--surface-hover) !important;
  color: var(--text-primary) !important;
}

/* ------------------------------------------------------------------ */
/* 12. Progress bar                                                    */
/* ------------------------------------------------------------------ */

[data-testid="stProgress"] > div {
  background: var(--c-blue-100) !important;
  overflow: hidden;
}

[data-testid="stProgress"] > div > div {
  background: var(--c-blue-600) !important;
  animation: bar-grow 500ms ease-out both;
  transform-origin: left center;
}

/* ------------------------------------------------------------------ */
/* 13. Data tables                                                     */
/* ------------------------------------------------------------------ */

/* Application table (st.dataframe): almost-white surface, 10px radius.
   Cell colours, horizontal-only dividers and row hover are set through
   the [theme] dataframe options in .streamlit/config.toml, because the
   grid draws on a canvas that CSS cannot reach.                       */
[data-testid="stDataFrame"] {
  border: 1px solid var(--border) !important;
  border-radius: var(--r-surface) !important;
  background: var(--surface) !important;
  overflow: hidden;
}

[data-testid="stDataFrame"] > div {
  border: none !important;
}

/* ------------------------------------------------------------------ */
/* 14. Forms                                                           */
/* ------------------------------------------------------------------ */

[data-testid="stForm"] {
  border: 1px solid var(--border) !important;
  border-radius: var(--r-surface) !important;
  background: var(--surface) !important;
  padding: var(--s-5) !important;
  box-shadow: none !important;
}

/* Metric / stat / board surfaces share the 10px radius */
[data-testid="stMetric"],
.stat-tile,
.board-card {
  border-radius: var(--r-surface) !important;
}

[data-testid="stMetric"] {
  background: var(--surface) !important;
}

/* Small tags and chips use control radius */
.chip,
.stage-tag,
.board-match-tag,
.ats-score-band,
.section-present,
.section-missing {
  border-radius: 999px;
}

.ats-tip,
.ats-note,
.ats-warn {
  border-radius: var(--r-control);
}

.goal-track,
.goal-fill,
.funnel-bar-wrap,
.funnel-bar,
.stage-pass-track,
.stage-pass-fill,
[data-testid="stProgress"] > div,
[data-testid="stProgress"] > div > div {
  border-radius: 4px;
}

.hm-cell { border-radius: 3px; }

[data-testid="stFileUploadDropzone"],
[data-testid="stFileUploaderDropzone"] {
  border-radius: var(--r-surface) !important;
}

/* ------------------------------------------------------------------ */
/* 15. Resume Matcher custom components                                */
/* ------------------------------------------------------------------ */

/* Score display block */
.ats-score-box {
  padding: 12px 0 8px;
  animation: fade-up 250ms ease-out 0ms both;
}

.ats-score-num {
  font-size: 3.4rem !important;
  font-weight: 800 !important;
  line-height: 1 !important;
  margin: 0 !important;
  font-variant-numeric: tabular-nums;
}

.ats-score-denom {
  font-size: .85rem;
  color: var(--c-text-sec);
  margin: 0 !important;
}

/* Score band badge — inline square box */
.ats-score-band {
  display: inline-block;
  font-size: .82rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  padding: 2px 10px;
  margin-top: .35rem;
  border: 1px solid;
}

/* Three band levels — blues only, no green/red/orange */
.ats-score-strong.ats-score-num { color: var(--c-blue-900); }
.ats-score-decent.ats-score-num { color: var(--c-blue-700); }
.ats-score-low.ats-score-num    { color: var(--c-blue-400); }

.ats-score-strong.ats-score-band {
  color: var(--c-blue-900);
  background: var(--c-blue-100);
  border-color: var(--c-blue-200);
}
.ats-score-decent.ats-score-band {
  color: var(--c-blue-700);
  background: var(--c-blue-50);
  border-color: var(--c-blue-200);
}
.ats-score-low.ats-score-band {
  color: var(--c-blue-600);
  background: var(--c-white);
  border-color: var(--c-blue-200);
}

/* Section checks: "Present" / "Missing" inline labels */
.section-present {
  display: inline-block;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 1px 5px;
  margin-right: 5px;
  background: var(--c-blue-600);
  color: var(--c-white);
  border: 1px solid var(--c-blue-600);
}

.section-missing {
  display: inline-block;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 1px 5px;
  margin-right: 5px;
  background: var(--c-white);
  color: var(--c-blue-400);
  border: 1px solid var(--c-blue-200);
}

/* Tip boxes — blue left-border notes */
.ats-tip {
  background: var(--c-blue-50);
  border: 1px solid var(--c-blue-100);
  border-left: 3px solid var(--c-blue-600);
  padding: 10px 14px;
  margin: 5px 0;
  font-size: 0.88rem;
  color: var(--c-text);
  animation: fade-up 250ms ease-out 100ms both;
}

/* Demo mode and inline notes */
.ats-note {
  background: var(--c-blue-50);
  border: 1px solid var(--c-blue-100);
  border-left: 3px solid var(--c-blue-400);
  padding: 10px 14px;
  margin: 6px 0;
  font-size: 0.88rem;
  color: var(--c-text);
}

/* Inline warnings for short input */
.ats-warn {
  background: var(--c-bg-1);
  border: 1px solid var(--c-border);
  border-left: 3px solid var(--c-blue-600);
  padding: 7px 12px;
  margin: 4px 0;
  font-size: 0.82rem;
  color: var(--c-text-sec);
}

/* Keyword chips — square tags */
.chip {
  display: inline-block;
  padding: 2px 8px;
  margin: 2px 3px 2px 0;
  font-size: .78rem;
  font-weight: 500;
  line-height: 1.6;
  border: 1px solid;
  transition: opacity 150ms;
  animation: fade-up 200ms ease-out 180ms both;
}

.chip:hover {
  opacity: 0.75;
}

/* All matched chips: solid blue, white text */
.chip-m-tech,
.chip-m-cert,
.chip-m-soft {
  background: var(--c-blue-600);
  color: var(--c-white);
  border-color: var(--c-blue-600);
}

.chip-m-tech:hover,
.chip-m-cert:hover,
.chip-m-soft:hover {
  background: var(--c-blue-700);
  border-color: var(--c-blue-700);
}

/* All missing chips: white with blue border */
.chip-x-tech,
.chip-x-miss,
.chip-x-soft {
  background: var(--c-white);
  color: var(--c-blue-700);
  border-color: var(--c-blue-200);
}

.chip-x-tech:hover,
.chip-x-miss:hover,
.chip-x-soft:hover {
  background: var(--c-blue-50);
  border-color: var(--c-blue-400);
}

/* Category summary "(N matched · M missing)" */
.cat-summary {
  color: var(--c-text-sec);
  font-size: 0.82em;
}

/* ------------------------------------------------------------------ */
/* 16. Keyframe animations                                             */
/* ------------------------------------------------------------------ */

@keyframes fade-up {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes bar-grow {
  from { transform: scaleX(0); }
  to   { transform: scaleX(1); }
}

/* ------------------------------------------------------------------ */
/* 17. Accessibility: disable animations for users who prefer it      */
/* ------------------------------------------------------------------ */

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation: none !important;
    transition: none !important;
  }
}

/* ------------------------------------------------------------------ */
/* 18. Stat tiles (Dashboard header row)                               */
/* ------------------------------------------------------------------ */

.stat-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.stat-tile {
  flex: 1;
  border: 1px solid var(--c-border);
  background: var(--c-white);
  padding: 14px 16px;
  animation: fade-up 250ms ease-out both;
}

.stat-tile-1 { animation-delay: 0ms;   --count-delay: 0ms;   }
.stat-tile-2 { animation-delay: 60ms;  --count-delay: 60ms;  }
.stat-tile-3 { animation-delay: 120ms; --count-delay: 120ms; }
.stat-tile-4 { animation-delay: 180ms; --count-delay: 180ms; }
.stat-tile-5 { animation-delay: 240ms; --count-delay: 240ms; }

.stat-tile-label {
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--c-text-sec);
  margin-bottom: 4px;
}

.stat-tile-value {
  font-size: 2rem;
  font-weight: 800;
  color: var(--c-text);
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
  margin-bottom: 4px;
}

.stat-tile-trend {
  font-size: 0.72rem;
  font-weight: 600;
}

.trend-up   { color: var(--c-blue-700); }
.trend-down { color: var(--c-blue-400); }
.trend-flat { color: var(--c-text-sec); }
.trend-none { color: var(--c-text-sec); font-weight: 400; }

/* ------------------------------------------------------------------ */
/* 19. Kanban board                                                    */
/* ------------------------------------------------------------------ */

.board-col-header {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--c-text-sec);
  border-bottom: 2px solid var(--c-blue-600);
  padding-bottom: 6px;
  margin-bottom: 10px;
}

.board-count {
  font-size: 0.75rem;
  color: var(--c-blue-600);
  font-weight: 800;
  margin-left: 4px;
}

.board-card {
  border: 1px solid var(--c-border);
  background: var(--c-white);
  padding: 10px 12px;
  margin-bottom: 8px;
  animation: fade-up 200ms ease-out both;
}

.board-card-company {
  font-weight: 700;
  font-size: 0.85rem;
  color: var(--c-text);
}

.board-card-role {
  font-size: 0.8rem;
  color: var(--c-text);
  margin-top: 2px;
}

.board-card-meta {
  font-size: 0.7rem;
  color: var(--c-text-sec);
  margin-top: 4px;
}

.board-card-dates {
  font-size: 0.7rem;
  color: var(--c-blue-600);
  margin-top: 2px;
}

.board-empty {
  font-size: 0.78rem;
  color: var(--c-text-sec);
  padding: 6px 0;
}

/* ------------------------------------------------------------------ */
/* 20. Application heatmap                                             */
/* ------------------------------------------------------------------ */

.heatmap-wrap { overflow-x: auto; padding: 6px 0 10px; }

.heatmap-months,
.heatmap-row {
  display: flex;
  align-items: center;
  margin-bottom: 2px;
  flex-wrap: nowrap;
}

.hm-day-spacer { width: 18px; flex-shrink: 0; }

.hm-day-label {
  width: 18px;
  font-size: 0.6rem;
  color: var(--c-text-sec);
  flex-shrink: 0;
  line-height: 1;
}

.hm-month-cell {
  width: 18px;
  font-size: 0.6rem;
  color: var(--c-text-sec);
  flex-shrink: 0;
  margin-right: 3px;
  overflow: visible;
  white-space: nowrap;
}

.hm-cell {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
  margin-right: 3px;
  cursor: default;
  transition: opacity 150ms;
}

.hm-cell:hover { opacity: 0.65; }

.hm-0      { background: var(--c-bg-2); }
.hm-1      { background: var(--c-blue-100); }
.hm-2      { background: var(--c-blue-200); }
.hm-3      { background: var(--c-blue-400); }
.hm-4      { background: var(--c-blue-600); }
.hm-future { background: transparent; border: 1px dashed var(--c-border); }

.hm-legend {
  display: flex;
  align-items: center;
  gap: 3px;
  margin-top: 8px;
}

.hm-legend-label {
  font-size: 0.62rem;
  color: var(--c-text-sec);
  margin: 0 4px;
}

/* ------------------------------------------------------------------ */
/* 21. Funnel chart                                                    */
/* ------------------------------------------------------------------ */

.funnel { padding: 6px 0; }

.funnel-empty {
  color: var(--c-text-sec);
  font-size: 0.85rem;
  padding: 8px 0;
}

.funnel-step { margin-bottom: 4px; }

.funnel-step-label {
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--c-text-sec);
  margin-bottom: 3px;
}

.funnel-bar-wrap {
  background: var(--c-bg-2);
  height: 32px;
}

.funnel-bar {
  height: 100%;
  display: flex;
  align-items: center;
  padding: 0 10px;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--c-white);
  font-variant-numeric: tabular-nums;
  min-width: 32px;
  animation: bar-grow 500ms ease-out both;
  transform-origin: left;
}

.fn-c0 { background: var(--c-blue-700); }
.fn-c1 { background: var(--c-blue-600); }
.fn-c2 { background: var(--c-blue-400); }
.fn-c3 { background: var(--c-blue-200); color: var(--c-blue-900); }

.funnel-conv {
  padding: 2px 0 6px 6px;
}

.funnel-conv-main {
  display: block;
  font-size: 0.72rem;
  font-weight: 500;
  color: var(--c-text-sec);
}

.funnel-conv-step {
  display: block;
  font-size: 0.65rem;
  color: var(--c-blue-400);
  margin-top: 1px;
}

/* ------------------------------------------------------------------ */
/* 22. Weekly goal progress                                            */
/* ------------------------------------------------------------------ */

.goal-track {
  background: var(--c-blue-100);
  height: 14px;
  margin-bottom: 4px;
}

.goal-fill {
  background: var(--c-blue-600);
  height: 100%;
  animation: bar-grow 500ms ease-out both;
  transform-origin: left;
  min-width: 2px;
}

.goal-label {
  font-size: 0.8rem;
  color: var(--c-text-sec);
  font-variant-numeric: tabular-nums;
}

.goal-streak {
  font-size: 0.8rem;
  color: var(--c-text);
  margin-top: 4px;
}

.goal-streak-num {
  font-weight: 800;
  color: var(--c-blue-700);
  font-variant-numeric: tabular-nums;
}

/* ------------------------------------------------------------------ */
/* 23. Dashboard data tables                                           */
/* ------------------------------------------------------------------ */

.tracker-table-wrap {
  overflow-x: auto;
  margin-bottom: var(--s-1);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-surface);
}

.tracker-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
  color: var(--text-primary);
}

.tracker-table th {
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: var(--s-3) var(--s-4);
  text-align: left;
  border: none;
  border-bottom: 1px solid var(--border);
}

.tracker-table th.num { text-align: right; }

/* Quiet horizontal dividers only — no boxed cells */
.tracker-table td {
  padding: var(--s-3) var(--s-4);
  border: none;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}

.tracker-table tr:last-child td { border-bottom: none; }

.tracker-table tbody tr:hover td {
  background: var(--surface-hover);
}

/* First column (company / label) slightly more prominent */
.tracker-table td:first-child {
  font-weight: 600;
}

.tracker-table td.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.tracker-table-caption {
  font-size: 0.72rem;
  color: var(--c-text-sec);
  margin: 4px 0 0;
}

/* ------------------------------------------------------------------ */
/* 24. CSS count-up animation (stat tiles + ATS score)                 */
/* ------------------------------------------------------------------ */

/* Register --count-num as an animatable integer type.
   Browsers without @property support ignore this block; the animation
   still ends on the correct value (discrete jump at 50%), and the
   sr-only span always holds the real number for screen readers.       */
@property --count-num {
  syntax: "<integer>";
  initial-value: 0;
  inherits: false;
}

@keyframes count-up {
  from { --count-num: 0; }
  to   { --count-num: var(--target, 0); }
}

/* Visually hidden — accessible to screen readers and copy-paste */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* Animated counter element (aria-hidden, purely visual) */
.count-anim {
  display: inline-block;
  counter-reset: cu-num var(--count-num);
  animation: count-up 900ms ease-out both;
  animation-delay: var(--count-delay, 0ms);
}

.count-anim::before {
  content: counter(cu-num);
}

/* "%" suffix — rendered by CSS so it moves with the animated number */
.count-anim--pct::after {
  content: "%";
}

/* Reduced motion: section 17 sets animation:none!important on all elements;
   this additional rule makes the counter show the final target immediately
   rather than the initial-value 0 that @property would leave behind.    */
@media (prefers-reduced-motion: reduce) {
  .count-anim {
    counter-reset: cu-num var(--target, 0);
  }
}

/* ------------------------------------------------------------------ */
/* 25. Interview stages — timeline + pass rate bars + board match tag  */
/* ------------------------------------------------------------------ */

/* Timeline */
.stage-timeline { padding: 4px 0; }

.stage-item {
  display: flex;
  gap: 10px;
  margin-bottom: 0;
}

.stage-left {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 12px;
}

.stage-marker {
  width: 10px;
  height: 10px;
  background: var(--c-blue-600);
  flex-shrink: 0;
  margin-top: 4px;
}

.stage-vline {
  width: 2px;
  flex: 1;
  background: var(--c-blue-200);
  margin: 2px 0;
  min-height: 20px;
}

.stage-body {
  flex: 1;
  padding-bottom: 14px;
}

.stage-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 2px;
}

.stage-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--c-text);
}

.stage-date {
  font-size: 0.75rem;
  color: var(--c-text-sec);
  font-variant-numeric: tabular-nums;
}

.stage-tag {
  display: inline-block;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 1px 6px;
  border: 1px solid;
}

/* Status tags: text label + muted tint (never colour alone) */
.stage-tag-passed {
  background: var(--accent-soft);
  color: var(--accent-deep);
  border-color: var(--accent-line);
}

.stage-tag-failed {
  background: #F3E6E1;
  color: #6E3B2E;
  border-color: #E5CFC6;
}

.stage-tag-sched {
  background: var(--surface-muted);
  color: var(--text-primary);
  border-color: var(--border);
}

.stage-notes {
  font-size: 0.78rem;
  color: var(--c-text-sec);
  margin-top: 2px;
}

/* Pass rate bars */
.stage-pass-bars { padding: 4px 0; }

.stage-pass-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.stage-pass-label {
  font-size: 0.78rem;
  color: var(--c-text);
  width: 140px;
  flex-shrink: 0;
}

.stage-pass-pct {
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--c-blue-700);
  width: 36px;
  text-align: right;
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}

.stage-pass-track {
  flex: 1;
  background: var(--c-bg-2);
  height: 18px;
  min-width: 60px;
}

.stage-pass-fill {
  background: var(--c-blue-600);
  height: 100%;
  min-width: 2px;
}

.stage-pass-counts {
  font-size: 0.72rem;
  color: var(--c-text-sec);
  width: 180px;
  flex-shrink: 0;
}

/* Board card match score tag */
.board-match-tag {
  display: inline-block;
  font-size: 0.62rem;
  font-weight: 700;
  color: var(--c-blue-900);
  background: var(--c-blue-100);
  border: 1px solid var(--c-blue-200);
  padding: 1px 5px;
  margin-top: 4px;
  letter-spacing: 0.03em;
}

/* Resume match history in Applications tab */
.match-history { padding: 4px 0; }

.match-history-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 0;
  border-bottom: 1px solid var(--c-border);
  font-size: 0.82rem;
}

.match-history-row:last-child { border-bottom: none; }

.match-history-date {
  color: var(--c-text-sec);
  font-variant-numeric: tabular-nums;
  width: 90px;
  flex-shrink: 0;
}

.match-history-label {
  color: var(--c-text-sec);
  flex: 1;
  min-width: 80px;
}

.match-history-score {
  font-weight: 700;
  color: var(--c-blue-700);
  font-variant-numeric: tabular-nums;
}

.match-history-band {
  font-size: 0.7rem;
  color: var(--c-text-sec);
  margin-left: 4px;
}

/* ------------------------------------------------------------------ */
/* 26. Board card hierarchy                                            */
/* ------------------------------------------------------------------ */

.board-card {
  background: var(--surface);
  padding: var(--s-3) var(--s-4);
  transition: background 150ms;
}

.board-card:hover { background: var(--surface-hover); }

.board-card-company { font-size: 0.95rem; font-weight: 600; }
.board-card-role    { font-size: 0.85rem; color: var(--text-secondary); }
.board-card-dates   { color: var(--text-secondary); }

.board-col-header {
  border-bottom-color: var(--accent);
}

/* Stat tiles: calmer numerals */
.stat-tile        { background: var(--surface); padding: var(--s-4); }
.stat-tile-value  { font-weight: 600; }

/* Small uppercase section headings sit on a quiet divider */
h3 { border-bottom-color: var(--border) !important; }

/* Checkbox / radio checked state uses the olive accent */
[data-testid="stCheckbox"] [role="checkbox"][aria-checked="true"] > span,
[data-baseweb="checkbox"] input:checked + span {
  background-color: var(--accent) !important;
  border-color: var(--accent) !important;
}

/* ------------------------------------------------------------------ */
/* 27. Responsive — mobile                                             */
/* ------------------------------------------------------------------ */

@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"],
  .block-container {
    padding: var(--s-5) var(--s-4) var(--s-6) !important;
  }

  h1 {
    font-size: 28px !important;
  }

  .stat-row {
    flex-wrap: wrap;
  }

  .stat-tile {
    flex: 1 1 calc(50% - 12px);
  }

  [data-baseweb="tab"] {
    padding: var(--s-2) var(--s-3) !important;
  }
}

/* ------------------------------------------------------------------ */
/* 28. Field fill consistency — selects, dates, number steppers        */
/* ------------------------------------------------------------------ */

[data-baseweb="select"] > div,
[data-baseweb="base-input"],
[data-baseweb="base-input"] input,
[data-testid="stDateInput"] [data-baseweb="input"],
[data-testid="stNumberInput"] [data-baseweb="input"],
[data-testid="stNumberInput"] button {
  background: var(--surface) !important;
}

[data-testid="stNumberInput"] button:hover {
  background: var(--surface-muted) !important;
}

/* Streamlit 1.67 select / date markup (no data-baseweb on the field) */
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div,
[data-testid="stDateInputField"] {
  background: var(--surface) !important;
  border-color: var(--border) !important;
  border-radius: var(--r-control) !important;
}

[data-testid="stSelectbox"] > div > div:focus-within,
[data-testid="stMultiSelect"] > div > div:focus-within,
[data-testid="stDateInputField"]:focus-within {
  border-color: var(--accent) !important;
}

/* ------------------------------------------------------------------ */
/* 29. Tabs — Streamlit 1.67 react-aria markup ([data-testid=stTab])  */
/* ------------------------------------------------------------------ */

[role="tablist"] {
  gap: var(--s-1) !important;
  border-bottom: 1px solid var(--border) !important;
}

[data-testid="stTab"] {
  padding: var(--s-2) var(--s-4) !important;
  border-radius: var(--r-control) var(--r-control) 0 0 !important;
  color: var(--text-secondary) !important;
  transition: background 150ms, color 150ms;
}

[data-testid="stTab"] p {
  font-size: 0.9rem !important;
  color: inherit !important;
}

[data-testid="stTab"]:hover {
  background: var(--surface-muted) !important;
  color: var(--text-primary) !important;
}

/* Active tab: dark text + semibold + olive underline (not colour alone) */
[data-testid="stTab"][aria-selected="true"] {
  color: var(--text-primary) !important;
}

[data-testid="stTab"][aria-selected="true"] p {
  font-weight: 600 !important;
}

[data-testid="stTab"] .react-aria-SelectionIndicator {
  background: var(--accent) !important;
  height: 2px !important;
}

[data-testid="stTab"][data-focus-visible],
[data-testid="stTab"]:focus-visible {
  outline: 2px solid var(--accent) !important;
  outline-offset: -2px !important;
}

@media (max-width: 640px) {
  [data-testid="stTab"] { padding: var(--s-2) var(--s-3) !important; }
}

/* Clear Streamlit's fixed top header so the h1 is never overlapped */
[data-testid="stMainBlockContainer"],
.block-container {
  padding-top: 72px !important;
}

@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"],
  .block-container {
    padding-top: 64px !important;
  }
}

/* ------------------------------------------------------------------ */
/* 30. KPI row — printed-report style: no boxes, ruled, serif numbers */
/* ------------------------------------------------------------------ */

.stat-row {
  display: grid !important;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0 !important;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  margin: var(--s-2) 0 var(--s-7) !important;
}

.stat-row .stat-tile {
  border: none !important;
  border-left: 1px solid var(--border) !important;
  border-radius: 0 !important;
  background: transparent !important;
  padding: var(--s-5) var(--s-5) var(--s-5) !important;
}

.stat-row .stat-tile:first-child {
  border-left: none !important;
  padding-left: 0 !important;
}

.stat-row .stat-tile-value {
  font-family: var(--serif);
  font-size: 40px;
  font-weight: 400;
  line-height: 1;
  letter-spacing: -0.01em;
  color: var(--text-primary);
  margin: 0 0 var(--s-2);
}

.stat-row .stat-tile-label {
  font-size: 0.85rem;
  font-weight: 400;
  letter-spacing: 0;
  text-transform: lowercase;
  color: var(--text-secondary);
  margin: 0;
}

.stat-row .stat-tile-trend {
  font-size: 0.78rem;
  font-weight: 400;
  margin-top: var(--s-2);
  color: var(--text-secondary);
}

.stat-row .trend-up   { color: var(--accent); }
.stat-row .trend-down { color: var(--negative); }
.stat-row .trend-flat { color: var(--text-secondary); }

@media (max-width: 900px) {
  .stat-row { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .stat-row .stat-tile:nth-child(3n+1) { border-left: none !important; padding-left: 0 !important; }
  .stat-row .stat-tile:nth-child(n+4)  { border-top: 1px solid var(--border) !important; }
}

@media (max-width: 640px) {
  .stat-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .stat-row .stat-tile { padding: var(--s-4) var(--s-4) !important; }
  .stat-row .stat-tile:nth-child(3n+1) { border-left: 1px solid var(--border) !important; padding-left: var(--s-4) !important; }
  .stat-row .stat-tile:nth-child(odd)  { border-left: none !important; padding-left: 0 !important; }
  .stat-row .stat-tile:nth-child(n+3)  { border-top: 1px solid var(--border) !important; }
  .stat-row .stat-tile:nth-child(4)    { border-top: 1px solid var(--border) !important; }
  .stat-row .stat-tile-value { font-size: 32px; }
}

/* ------------------------------------------------------------------ */
/* 31. Weekly goal — one compact line with dots                       */
/* ------------------------------------------------------------------ */

.goal-line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--s-2) var(--s-5);
  font-size: 0.9rem;
  color: var(--text-primary);
}

.goal-title {
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-secondary);
}

.goal-dots {
  display: inline-flex;
  gap: 6px;
}

.goal-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 1px solid var(--olive-mid);
  background: transparent;
}

.goal-dot--on {
  background: var(--accent);
  border-color: var(--accent);
  animation: fade-up 200ms ease-out both;
}

.goal-count {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}

.goal-streak-text,
.goal-best {
  color: var(--text-secondary);
}

/* Space below the whole goal row (line + Edit goal button) */
[data-testid="stHorizontalBlock"]:has(.goal-line) {
  margin-bottom: var(--s-6);
}

/* "Edit goal" popover trigger: quiet text-style button */
[data-testid="stPopover"] button {
  background: transparent !important;
  border: 1px solid var(--border) !important;
  color: var(--text-secondary) !important;
  font-size: 0.8rem !important;
  min-height: 0 !important;
  padding: 4px 10px !important;
}

[data-testid="stPopover"] button:hover {
  background: var(--surface-muted) !important;
  color: var(--text-primary) !important;
}

@media (max-width: 640px) {
  .goal-line { gap: var(--s-2) var(--s-4); }
  .goal-dots { gap: 5px; }
  .goal-dot  { width: 9px; height: 9px; }
}

/* ------------------------------------------------------------------ */
/* 32. Charts — no toolbar, no chrome                                  */
/* ------------------------------------------------------------------ */

/* Hide the hover toolbar (fullscreen etc.) on charts only —
   dataframes keep their search / download toolbar. */
[data-testid="stElementContainer"]:has([data-testid="stVegaLiteChart"]) [data-testid="stElementToolbar"],
[data-testid="stVegaLiteChart"] details,
.vega-embed .vega-actions,
.vega-embed summary {
  display: none !important;
}

/* Clean tooltip in the report palette */
#vg-tooltip-element {
  background: var(--surface) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r-control) !important;
  box-shadow: none !important;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif !important;
  font-size: 12px !important;
  padding: 6px 10px !important;
}

#vg-tooltip-element table tr td.key { color: var(--text-secondary) !important; }

/* ------------------------------------------------------------------ */
/* 33. Page chrome & layout — printed-report finish (Stage 5)          */
/* ------------------------------------------------------------------ */

/* Hide Streamlit's header bar, toolbar, decoration line and footer */
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stSidebarCollapsedControl"],
footer {
  display: none !important;
}

/* Narrower report column; header is gone so less top padding */
[data-testid="stMainBlockContainer"],
.block-container {
  max-width: 1100px !important;
  padding-top: var(--s-7) !important;
}

/* Title row: serif title left, small muted date right */
.page-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--s-4);
  flex-wrap: wrap;
  margin-bottom: var(--s-4);
}

.page-head h1 {
  margin: 0 !important;
  padding: 0 !important;
}

.page-head h1 a { display: none !important; }   /* no anchor link icon */

.page-date {
  font-size: 0.85rem;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

/* Tabs: plain text, thin 1px olive underline on the active tab only */
[role="tablist"] {
  gap: var(--s-5) !important;
  border-bottom: 1px solid var(--border) !important;
}

[data-testid="stTab"] {
  padding: var(--s-2) 0 !important;
  background: transparent !important;
  border-radius: 0 !important;
}

[data-testid="stTab"]:hover {
  background: transparent !important;
  color: var(--text-primary) !important;
}

[data-testid="stTab"] .react-aria-SelectionIndicator {
  height: 1px !important;
  background: var(--accent) !important;
}

/* Section labels: 48px above (16px block gap + 32px), none for the first */
[data-testid="stHeading"]:has(h3) {
  margin-top: var(--s-6);
}

[role="tabpanel"] > div > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:first-child [data-testid="stHeading"],
[data-testid="stColumn"] [data-testid="stHeading"]:has(h3) {
  margin-top: 0;
}

/* Rows of columns (e.g. Pipeline | Applications per week) also get 48px */
[data-testid="stHorizontalBlock"]:has([data-testid="stVegaLiteChart"]) {
  margin-top: var(--s-6);
}

/* Settings: keep the goal box compact */
[data-testid="stNumberInput"] { max-width: 260px; }

/* Goal line hint */
.goal-hint,
[data-testid="stMarkdownContainer"] p.goal-hint {
  margin: var(--s-2) 0 0 !important;
  font-size: 0.78rem !important;
  color: var(--text-secondary) !important;
}

/* Inputs and buttons: 1px rule border */
button[data-testid^="stBaseButton"],
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] [data-baseweb="input"],
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div,
[data-testid="stDateInputField"] {
  border-width: 1px !important;
}

@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"],
  .block-container {
    padding-top: var(--s-6) !important;
  }
  [role="tablist"] { gap: var(--s-4) !important; }
  .page-head { flex-direction: column; gap: var(--s-1); }
}

/* ------------------------------------------------------------------ */
/* 34. Board stepper, advance button, stage history                    */
/* ------------------------------------------------------------------ */

.stepper { margin-top: 10px; }
.step-dot {
  width: 9px; height: 9px; border-radius: 50%;
  border: 1.5px solid var(--olive-light);
  background: var(--surface);
  flex: none;
}
.step-dots {
  display: flex; align-items: center; justify-content: space-between;
  position: relative; max-width: 120px;
}
.step-dots::before {
  content: ""; position: absolute; left: 4px; right: 4px; top: 50%;
  height: 1.5px; background: var(--olive-light); z-index: 0;
}
.step-dot { position: relative; z-index: 1; }
.step-dot--done { background: var(--olive-mid); border-color: var(--olive-mid); }
.step-dot--now  {
  background: var(--accent); border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}
.stepper--closed .step-dot--done { background: var(--negative); border-color: var(--negative); opacity: .55; }
.step-label {
  margin-top: 6px; font-size: 0.72rem; font-weight: 600; color: var(--accent);
}
.stepper--closed .step-label { color: var(--negative); }
.step-when { font-weight: 400; color: var(--text-secondary); }

/* Board buttons: compact, sit tight under their card */
[data-testid="stColumn"] [data-testid="stButton"] button,
[data-testid="stColumn"] [data-testid="stPopover"] button {
  min-height: 30px; padding: 2px 8px; font-size: 0.78rem;
}
.stage-history { margin-top: 10px; border-top: 1px solid var(--border); padding-top: 8px; }
.stage-history-head {
  font-size: 0.68rem; letter-spacing: .08em; text-transform: uppercase;
  color: var(--text-secondary); margin-bottom: 4px;
}
.stage-history-row {
  display: flex; justify-content: space-between; gap: 16px;
  font-size: 0.8rem; padding: 2px 0;
}
.stage-history-row span:last-child { color: var(--text-secondary); font-variant-numeric: tabular-nums; }

/* Stale cards: a quiet brown edge and a one-line nudge */
.board-card--stale { box-shadow: inset 3px 0 0 var(--negative); }
.board-stale-tag {
  margin-top: 8px; font-size: 0.72rem; color: var(--negative);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
/* Card buttons: stacked in the narrow desktop columns, side by side on phones */
[class*="st-key-bbtn_"] [data-testid="stHorizontalBlock"] {
  flex-direction: column; gap: 0.5rem;
}
[class*="st-key-bbtn_"] [data-testid="stColumn"] { width: 100% !important; flex: 1 1 auto !important; }
@media (max-width: 640px) {
  [class*="st-key-bbtn_"] [data-testid="stHorizontalBlock"] {
    flex-direction: row; flex-wrap: nowrap;
  }
  [class*="st-key-bbtn_"] [data-testid="stColumn"] { min-width: 0 !important; flex: 1 1 0 !important; }
}

/* ------------------------------------------------------------------ */
/* 35. Contacts & notes (Details panel)                                */
/* ------------------------------------------------------------------ */
.board-card-counts { margin-top: 6px; font-size: 0.72rem; color: var(--text-secondary); }
.detail-head {
  font-size: 0.68rem; letter-spacing: .08em; text-transform: uppercase;
  color: var(--text-secondary); margin: 6px 0 4px;
  border-bottom: 1px solid var(--border); padding-bottom: 4px;
}
.detail-row { font-size: 0.85rem; line-height: 1.4; padding: 3px 0; overflow-wrap: anywhere; }
.detail-sub { font-size: 0.75rem; color: var(--text-secondary); }
[data-testid="stPopoverBody"] { min-width: 300px; max-width: 380px; }

/* Hide Streamlit's "Press Enter to submit form" hints */
[data-testid="InputInstructions"] { display: none !important; }

/* ------------------------------------------------------------------ */
/* 36. Cover Letter tab                                                */
/* ------------------------------------------------------------------ */
.cl-placeholders {
  display: flex; flex-wrap: wrap; gap: 6px 16px;
  font-size: 0.78rem; color: var(--text-secondary); margin-bottom: 8px;
}
.cl-placeholders code {
  background: var(--accent-faint); color: var(--accent);
  padding: 1px 5px; border-radius: 4px; margin-right: 4px;
}

/* ------------------------------------------------------------------ */
/* 37. Reminders: to-dos                                               */
/* ------------------------------------------------------------------ */
.task-when { font-size: 0.82rem; color: var(--text-secondary); }
.task-late { font-size: 0.82rem; color: var(--negative); font-weight: 600; }
"""


ALTAIR_THEME = "ledger"


def _altair_theme() -> dict:
    """Printed-report chart style: no boxes, faint horizontal rules only."""
    t = TOKENS
    axis_common = {
        "domain": False,
        "ticks": False,
        "labelColor": t["muted"],
        "labelFont": t["sans"],
        "labelFontSize": 11,
        "labelPadding": 6,
        "titleColor": t["muted"],
        "titleFont": t["sans"],
        "titleFontSize": 11,
        "titleFontWeight": "normal",
    }
    return {
        "config": {
            "background": None,
            "padding": {"left": 0, "right": 8, "top": 8, "bottom": 0},
            "view": {"stroke": None},
            "font": t["sans"],
            "axis": {**axis_common, "grid": False},
            "axisY": {**axis_common, "grid": True, "gridColor": t["rule"],
                      "gridWidth": 1, "tickCount": 4},
            "axisX": {**axis_common, "grid": False, "labelAngle": 0},
            "bar": {"color": t["olive"]},
            "line": {"color": t["olive"], "strokeWidth": 1.5},
            "point": {"color": t["olive"], "filled": True, "size": 30},
            "rule": {"color": t["olive_mid"]},
            "text": {"color": t["muted"], "font": t["sans"], "fontSize": 11},
            "legend": {"disable": True},
        }
    }


def _register_altair_theme() -> None:
    """Register and enable the theme (Altair 5.5+ API, with a fallback)."""
    if hasattr(alt, "theme") and hasattr(alt.theme, "register"):
        alt.theme.register(ALTAIR_THEME, enable=True)(_altair_theme)
    else:  # older Altair
        alt.themes.register(ALTAIR_THEME, _altair_theme)
        alt.themes.enable(ALTAIR_THEME)


def setup() -> None:
    """Inject the shared stylesheet and enable the chart theme.

    Call once per run after st.set_page_config. Render charts with
    ``st.altair_chart(chart, theme=None)`` so Streamlit's own chart theme
    doesn't override this one.
    """
    _register_altair_theme()
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
