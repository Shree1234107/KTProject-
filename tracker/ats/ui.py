"""Streamlit UI for the Resume Matcher tab.

Call :func:`render` from app.py inside the ``with tab_ats:`` block.
This module handles all display logic; it never does text processing itself.
"""
from __future__ import annotations

import html as _html

import streamlit as st

from tracker import ats
from tracker.ats import report

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SECTION_LABELS = [
    ("summary", "Summary"),
    ("experience", "Experience"),
    ("education", "Education"),
    ("skills", "Skills"),
]

_INPUT_MODES = ("Upload PDF", "Paste text", "Try the demo")

# Chip CSS classes: (category, matched) → class suffix
_CHIP_CLASSES: dict[tuple[str, bool], str] = {
    ("Technical", True): "chip-m-tech",
    ("Certifications", True): "chip-m-cert",
    ("Soft skills", True): "chip-m-soft",
    ("Technical", False): "chip-x-tech",
    ("Certifications", False): "chip-x-miss",
    ("Soft skills", False): "chip-x-soft",
}

_CSS = """
<style>
/* ---- keyword chips ---- */
.chip {
    display: inline-block;
    padding: 3px 11px;
    margin: 2px 3px 2px 0;
    border-radius: 999px;
    font-size: .82rem;
    font-weight: 500;
    line-height: 1.6;
}
/* matched */
.chip-m-tech  { background: #dbeafe; color: #1d4ed8; }
.chip-m-cert  { background: #ede9fe; color: #5b21b6; }
.chip-m-soft  { background: #dcfce7; color: #166534; }
/* missing */
.chip-x-tech  { background: #fee2e2; color: #991b1b; }
.chip-x-cert  { background: #fce7f3; color: #9d174d; }
.chip-x-soft  { background: #ffedd5; color: #9a3412; }

/* ---- large score display ---- */
.ats-score-num  { font-size: 3.5rem; font-weight: 800; line-height: 1; margin: 0; }
.ats-score-denom { font-size: .9rem; color: #64748b; margin: 0; }
.ats-score-band  { font-size: 1.1rem; font-weight: 600; margin: .2rem 0 0; }
.ats-score-green { color: #16a34a; }
.ats-score-blue  { color: #2563eb; }
.ats-score-orange { color: #ea580c; }
</style>
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _score_color_class(score: float) -> str:
    if score >= 70:
        return "ats-score-green"
    if score >= 50:
        return "ats-score-blue"
    return "ats-score-orange"


def _chip(text: str, css_class: str, suffix: str = "") -> str:
    """Return a single HTML chip span with escaped content."""
    escaped = _html.escape(text)
    label = f"{escaped}{_html.escape(suffix)}" if suffix else escaped
    return f'<span class="chip {css_class}">{label}</span>'


def _keyword_section(
    category: str,
    matched: list[str],
    missing: list[dict],
) -> None:
    """Render one category block of matched + missing chips."""
    if not matched and not missing:
        return

    chips: list[str] = []
    for kw in matched:
        cls = _CHIP_CLASSES.get((category, True), "chip-m-tech")
        chips.append(_chip(kw, cls))
    for item in missing:
        cls = _CHIP_CLASSES.get((category, False), "chip-x-tech")
        chips.append(_chip(item["keyword"], cls, f" ×{item['count']}"))

    n_matched = len(matched)
    n_missing = len(missing)
    parts = []
    if n_matched:
        parts.append(f"{n_matched} matched")
    if n_missing:
        parts.append(f"{n_missing} missing")
    summary = " · ".join(parts)

    st.markdown(f"**{category}** <small style='color:#94a3b8'>({summary})</small>",
                unsafe_allow_html=True)
    st.markdown("".join(chips) or "—", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Results rendering
# ---------------------------------------------------------------------------

def _render_results(res: dict) -> None:
    """Render the full results panel from an ats.analyze* result dict."""
    score = res["overall_score"]
    band = report.score_band(score)
    color_cls = _score_color_class(score)

    st.divider()

    # --- Score + stats row ---
    score_col, stats_col = st.columns([1, 2])

    with score_col:
        st.markdown(
            f'<div style="text-align:center">'
            f'<p class="ats-score-num {color_cls}">{score:.0f}</p>'
            f'<p class="ats-score-denom">/ 100</p>'
            f'<p class="ats-score-band {color_cls}">{_html.escape(band)}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.progress(min(int(score), 100))

    with stats_col:
        m1, m2, m3 = st.columns(3)
        m1.metric("Keyword coverage", f"{res['keyword_coverage_score']:.0f}%")
        m2.metric("Content similarity", f"{res['cosine_similarity_score']:.0f}%")
        m3.metric("Word count", f"{res['resume_word_count']}")

        # Section checks
        sec_cols = st.columns(4)
        for col, (key, label) in zip(sec_cols, _SECTION_LABELS):
            icon = "✅" if res["section_checks"][key] else "❌"
            col.markdown(f"{icon} {label}")

    # --- Tips ---
    tips = res["tips"] or ["No major issues flagged — nice match!"]
    st.subheader("Do these first")
    for tip in tips[:3]:
        st.info(tip, icon="💡")
    if len(tips) > 3:
        with st.expander(f"See {len(tips) - 3} more tip{'s' if len(tips) - 3 > 1 else ''}"):
            for tip in tips[3:]:
                st.info(tip, icon="💡")

    # --- Keywords by category ---
    st.subheader("Keywords by category")
    groups = report.group_by_category(res["matched_keywords"], res["missing_keywords"])
    for cat in report.CATEGORIES:
        _keyword_section(cat, groups[cat]["matched"], groups[cat]["missing"])

    st.caption(
        "⚠️ Only add skills you actually have — "
        "misrepresenting experience can backfire in technical interviews."
    )

    # --- Download ---
    md_report = report.build_report(res)
    st.download_button(
        label="📥 Download report (.md)",
        data=md_report.encode("utf-8"),
        file_name="ats_report.md",
        mime="text/markdown",
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def render() -> None:
    """Render the full Resume Matcher tab. Call this from app.py."""
    st.markdown(_CSS, unsafe_allow_html=True)
    st.header("Resume Matcher")
    st.caption(
        "Score your resume against a job description — estimates only, not a real ATS. "
        "Nothing is stored."
    )

    # --- Input mode ---
    mode = st.radio(
        "Resume input",
        _INPUT_MODES,
        horizontal=True,
        label_visibility="collapsed",
    )

    # Auto-populate JD when switching to demo mode for the first time
    prev_mode = st.session_state.get("_ats_mode_prev", "")
    if mode == "Try the demo" and prev_mode != "Try the demo":
        st.session_state["ats_jd"] = ats.sample_job_description()
    st.session_state["_ats_mode_prev"] = mode

    if "ats_jd" not in st.session_state:
        st.session_state["ats_jd"] = ""

    left, right = st.columns(2)

    # Resume side
    pdf_file = None
    paste_text = ""
    with left:
        if mode == "Upload PDF":
            st.markdown("**Resume PDF**")
            pdf_file = st.file_uploader(
                "Resume PDF",
                type="pdf",
                label_visibility="collapsed",
            )
            st.caption("PDF only · max 5 MB")
        elif mode == "Paste text":
            paste_text = st.text_area(
                "Paste your resume text",
                height=240,
                placeholder="Paste your full resume text here…",
            )
            if paste_text and len(paste_text.strip()) < ats.MIN_RESUME_CHARS:
                st.warning(
                    f"Paste at least {ats.MIN_RESUME_CHARS} characters of your resume."
                )
        else:
            st.info(
                "**Demo mode** — using the sample resume (Jane Doe, Software Engineer). "
                "The sample job description has been loaded on the right; feel free to edit it.",
                icon="🧪",
            )

    # Job description side
    with right:
        st.markdown("**Job description**")
        jd_text: str = st.text_area(
            "Job description",
            key="ats_jd",
            height=240,
            placeholder="Paste the full job description here…",
            label_visibility="collapsed",
        )
        if jd_text and len(jd_text.strip()) < ats.MIN_JD_CHARS:
            st.warning(f"Paste at least {ats.MIN_JD_CHARS} characters.")

    # --- Action buttons ---
    btn_left, btn_right, _ = st.columns([1, 1, 4])
    analyze_clicked = btn_left.button("Analyze", type="primary")
    clear_clicked = btn_right.button("Clear results")

    if clear_clicked:
        st.session_state.pop("ats_result", None)
        st.session_state.pop("ats_error", None)
        st.rerun()

    # --- Run analysis ---
    if analyze_clicked:
        error_msg: str | None = None
        result: dict | None = None

        with st.spinner("Analyzing…"):
            try:
                if mode == "Upload PDF":
                    if pdf_file is None:
                        raise ValueError("Please upload a resume PDF.")
                    result = ats.analyze(pdf_file.getvalue(), jd_text)
                elif mode == "Paste text":
                    if len(paste_text.strip()) < ats.MIN_RESUME_CHARS:
                        raise ValueError(
                            f"Resume text is too short — "
                            f"paste at least {ats.MIN_RESUME_CHARS} characters of your resume."
                        )
                    result = ats.analyze_text(paste_text, jd_text)
                else:  # demo
                    result = ats.analyze_text(ats.sample_resume_text(), jd_text)
            except ValueError as exc:
                error_msg = str(exc)

        if error_msg:
            st.session_state.pop("ats_result", None)
            st.session_state["ats_error"] = error_msg
        else:
            st.session_state["ats_result"] = result
            st.session_state.pop("ats_error", None)

    # --- Show persisted error ---
    if err := st.session_state.get("ats_error"):
        st.error(err)

    # --- Show persisted results ---
    if res := st.session_state.get("ats_result"):
        _render_results(res)
