"""Streamlit UI for the Resume Matcher tab.

Call :func:`render` from app.py inside the ``with tab_ats:`` block.
This module handles all display logic; it never does text processing itself.
All colors and layout are defined in tracker/styles.py.
"""
from __future__ import annotations

import html as _html

import streamlit as st

from tracker import ats
from tracker.ats import report
from tracker.tiles import count_anim_html

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

# Chip CSS classes: (category, matched) → class name
# CSS makes all matched chips look the same (solid blue) and all missing
# chips look the same (white with blue border). Category is told apart
# by its section heading, not by color.
_CHIP_CLASSES: dict[tuple[str, bool], str] = {
    ("Technical", True):      "chip-m-tech",
    ("Certifications", True): "chip-m-cert",
    ("Soft skills", True):    "chip-m-soft",
    ("Technical", False):     "chip-x-tech",
    ("Certifications", False): "chip-x-miss",
    ("Soft skills", False):   "chip-x-soft",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _score_color_class(score: float) -> str:
    if score >= 70:
        return "ats-score-strong"
    if score >= 50:
        return "ats-score-decent"
    return "ats-score-low"


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
        chips.append(_chip(item["keyword"], cls, f" x{item['count']}"))

    n_matched = len(matched)
    n_missing = len(missing)
    parts = []
    if n_matched:
        parts.append(f"{n_matched} matched")
    if n_missing:
        parts.append(f"{n_missing} missing")
    summary = " · ".join(parts)

    st.markdown(
        f"**{category}** <small class='cat-summary'>({summary})</small>",
        unsafe_allow_html=True,
    )
    st.markdown("".join(chips) or "—", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Results rendering
# ---------------------------------------------------------------------------

def _render_results(res: dict, conn=None) -> None:
    """Render the full results panel from an ats.analyze* result dict."""
    score = res["overall_score"]
    band = report.score_band(score)
    color_cls = _score_color_class(score)

    st.divider()

    # --- Score + stats row ---
    score_col, stats_col = st.columns([1, 2])

    with score_col:
        st.markdown(
            f'<div class="ats-score-box">'
            f'<p class="ats-score-num {color_cls}">'
            f'{count_anim_html(int(round(score)))}'
            f'</p>'
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

        # Section checks — "Present" / "Missing" labels, no emoji
        sec_cols = st.columns(4)
        for col, (key, label) in zip(sec_cols, _SECTION_LABELS):
            present = res["section_checks"][key]
            cls = "section-present" if present else "section-missing"
            status = "Present" if present else "Missing"
            col.markdown(
                f'<span class="{cls}">{status}</span> {label}',
                unsafe_allow_html=True,
            )

    # --- Tips ---
    tips = res["tips"] or ["No major issues flagged — nice match!"]
    st.subheader("Do these first")
    for tip in tips[:3]:
        st.markdown(
            f'<div class="ats-tip">{_html.escape(tip)}</div>',
            unsafe_allow_html=True,
        )
    if len(tips) > 3:
        with st.expander(f"See {len(tips) - 3} more tip{'s' if len(tips) - 3 > 1 else ''}"):
            for tip in tips[3:]:
                st.markdown(
                    f'<div class="ats-tip">{_html.escape(tip)}</div>',
                    unsafe_allow_html=True,
                )

    # --- Keywords by category ---
    st.subheader("Keywords by category")
    groups = report.group_by_category(res["matched_keywords"], res["missing_keywords"])
    for cat in report.CATEGORIES:
        _keyword_section(cat, groups[cat]["matched"], groups[cat]["missing"])

    st.caption(
        "Note: Only add skills you actually have — "
        "misrepresenting experience can backfire in technical interviews."
    )

    _tailor_section(res, conn)

    # --- Download ---
    md_report = report.build_report(res)
    st.download_button(
        label="Download report (.md)",
        data=md_report.encode("utf-8"),
        file_name="ats_report.md",
        mime="text/markdown",
    )

    # --- Save to application ---
    if conn is not None:
        from tracker import db as _db
        st.divider()
        st.subheader("Save to application")
        apps_df = _db.load_applications(conn)
        if apps_df.empty:
            st.caption("Add an application to the tracker to save this score.")
        else:
            def _fmt_app(app_id: int) -> str:
                row = apps_df[apps_df["id"] == app_id]
                if row.empty:
                    return str(app_id)
                r = row.iloc[0]
                return f"{r['company']} — {r['role']} ({r['status']})"

            save_app_id = st.selectbox(
                "Application",
                apps_df["id"].tolist(),
                format_func=_fmt_app,
                key="ats_save_app",
            )
            resume_label = st.session_state.get("ats_resume_label", "")
            if st.button("Save score to application", key="ats_save_btn"):
                _db.add_match_score(
                    conn, int(save_app_id),
                    overall_score=res["overall_score"],
                    keyword_score=res["keyword_coverage_score"],
                    similarity_score=res["cosine_similarity_score"],
                    matched_count=len(res["matched_keywords"]),
                    missing_count=len(res["missing_keywords"]),
                    top_missing=[kw["keyword"] for kw in res["missing_keywords"][:5]],
                    resume_label=resume_label,
                )
                st.success(f"Score saved to {_fmt_app(int(save_app_id))}.")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def render(conn=None) -> None:
    """Render the full Resume Matcher tab. Call this from app.py."""
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
                st.markdown(
                    f'<div class="ats-warn">Note: Paste at least '
                    f'{ats.MIN_RESUME_CHARS} characters of your resume.</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div class="ats-note"><strong>Demo mode</strong> — using the sample resume '
                "(Jane Doe, Software Engineer). The sample job description has been loaded "
                "on the right; feel free to edit it.</div>",
                unsafe_allow_html=True,
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
            st.markdown(
                f'<div class="ats-warn">Note: Paste at least {ats.MIN_JD_CHARS} characters.</div>',
                unsafe_allow_html=True,
            )

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
                    from tracker.ats.extractor import extract_text_from_pdf
                    st.session_state["ats_resume_text"] = extract_text_from_pdf(pdf_file.getvalue())
                    st.session_state["ats_resume_label"] = pdf_file.name
                elif mode == "Paste text":
                    if len(paste_text.strip()) < ats.MIN_RESUME_CHARS:
                        raise ValueError(
                            f"Resume text is too short — "
                            f"paste at least {ats.MIN_RESUME_CHARS} characters of your resume."
                        )
                    result = ats.analyze_text(paste_text, jd_text)
                    st.session_state["ats_resume_text"] = paste_text
                    st.session_state["ats_resume_label"] = "pasted text"
                else:  # demo
                    result = ats.analyze_text(ats.sample_resume_text(), jd_text)
                    st.session_state["ats_resume_text"] = ats.sample_resume_text()
                    st.session_state["ats_resume_label"] = "demo resume"
            except ValueError as exc:
                error_msg = str(exc)

        if error_msg:
            st.session_state.pop("ats_result", None)
            st.session_state["ats_error"] = error_msg
        else:
            st.session_state["ats_result"] = result
            st.session_state["ats_jd_used"] = jd_text
            st.session_state.pop("ats_error", None)
            st.session_state.pop("ats_tailored", None)

    # --- Show persisted error ---
    if err := st.session_state.get("ats_error"):
        st.error(f"Error: {err}")

    # --- Show persisted results ---
    if res := st.session_state.get("ats_result"):
        _render_results(res, conn)


def _tailor_section(res: dict, conn=None) -> None:
    """AI rewrite of the resume for this posting, using only what's true."""
    from tracker import coverletter as cl, resumetailor as rt
    resume = st.session_state.get("ats_resume_text", "")
    jd = st.session_state.get("ats_jd_used", "")
    st.subheader("Tailor my resume to this job")
    models = cl.ollama_models()
    if not models:
        st.caption("To rewrite with AI, open Ollama (free, ollama.com), then reload this page.")
        return
    if not resume.strip() or not jd.strip():
        st.caption("Run Analyze first.")
        return
    saved = ""
    if conn is not None:
        from tracker import db as _db
        saved = _db.get_setting(conn, "cl_model", "")
    names = [m["name"] for m in models]
    default = saved if saved in names else next((m["name"] for m in models if not m["cloud"]), names[0])
    sizes = {m["name"]: ("cloud" if m["cloud"] else f"{m['size_gb']} GB") for m in models}
    model = st.selectbox("Model", names, index=names.index(default), key="ats_model",
                         format_func=lambda n: f"{n} · {sizes[n]}",
                         help="Bigger models write better; smaller ones are faster.")
    if conn is not None and model != saved:
        _db.set_setting(conn, "cl_model", model)

    missing = [kw["keyword"] for kw in res["missing_keywords"]]
    st.caption("The AI keeps your sections, layout and wording style, puts your most "
               "relevant experience first and uses the posting's words for it. It won't "
               "add anything you haven't done.")
    confirmed = st.multiselect(
        "Missing keywords you really do have (only these get added)", missing,
        key="ats_confirmed",
        help="Leave a keyword out if you can't back it up in an interview.",
    ) if missing else []
    request = st.text_area(
        "Anything else to change? (optional)", key="ats_req", height=80,
        placeholder="e.g. Lead with my research job, shorten to one page, stronger verbs",
    )
    draft = st.session_state.get("ats_tailored", "")
    b1, b2, _ = st.columns([1, 1, 2])
    go = b1.button("Rewrite my resume" if not draft else "Start over", type="primary",
                   key="ats_tailor", width="stretch")
    again = draft and b2.button("Revise this draft", key="ats_tailor_rev", width="stretch",
                                disabled=not request.strip())
    if go or again:
        with st.spinner(f"Rewriting with {model}… this can take a minute or two."):
            try:
                st.session_state["ats_tailored"] = rt.tailor_resume(
                    model, resume, jd, confirmed, request, current=draft if again else "")
            except RuntimeError as e:
                st.error(f"Ollama couldn't rewrite it: {e}")
            else:
                st.session_state.pop("ats_tailored_edit", None)
                st.rerun()
    if not draft:
        return
    text = st.text_area("Tailored resume (edit anything)", value=draft, height=420,
                        key="ats_tailored_edit")
    extra = rt.added_claims(text, resume, jd, confirmed)
    if extra:
        st.warning("Check before using: this mentions " + ", ".join(extra)
                   + ", which isn't on your original resume. Remove it unless it's true.")
    try:
        new_res = ats.analyze_text(text, jd)
        new_score = new_res["overall_score"]
        st.caption(f"Match score: {res['overall_score']:.0f} before → **{new_score:.0f}** after")
        before = {k["keyword"] for k in res["matched_keywords"]}
        gained = [k["keyword"] for k in new_res["matched_keywords"] if k["keyword"] not in before]
        still = [k["keyword"] for k in new_res["missing_keywords"]]
        if gained:
            st.caption("Posting keywords now on your resume: " + ", ".join(gained))
        if still:
            st.caption("Still missing (add only if true, using the box above): " + ", ".join(still))
    except ValueError:
        pass
    d1, d2, _ = st.columns([1, 1, 2])
    d1.download_button("Download Word", data=rt.to_docx(text), file_name="tailored-resume.docx",
                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                       key="ats_tl_docx", width="stretch")
    d2.download_button("Download text", data=text.encode(), file_name="tailored-resume.txt",
                       mime="text/plain", key="ats_tl_txt", width="stretch")
