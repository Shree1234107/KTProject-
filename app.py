"""Internship Tracker & Dashboard Analyzer. Run: streamlit run app.py"""
import datetime as dt
from pathlib import Path
import base64
import html as _html

import pandas as pd
import streamlit as st

from tracker import analytics, assistant, charts, coverletter as cl, db, ics as _ics, macreminders as mac, styles
from tracker.ats import report as _ats_report
from tracker.ats import ui as ats_ui
from tracker.tiles import goal_line_html, stat_tile_html

st.set_page_config(
    page_title="Internship Tracker", layout="wide", initial_sidebar_state="collapsed",
)
styles.setup()

conn = db.connect()


def _to_date(ts):
    """pandas Timestamp/NaT → Python date or None (for st.date_input)."""
    try:
        if ts is None or pd.isna(ts):
            return None
    except (TypeError, ValueError):
        pass
    return ts.date() if hasattr(ts, "date") else ts


# ---------------------------------------------------------------------------
# Main tabs
# ---------------------------------------------------------------------------
_now = dt.date.today()
_head, _mode = st.columns([6, 1], vertical_alignment="center")
_head.markdown(
    '<div class="page-head">'
    '<h1>Internship Tracker</h1>'
    f'<span class="page-date">{_now:%b} {_now.day}, {_now:%Y}</span>'
    '</div>',
    unsafe_allow_html=True,
)
_dark_now = styles.is_dark()
if _mode.button("Light mode" if _dark_now else "Dark mode", key="mode_toggle",
                width="stretch", help="Switch between light and dark"):
    styles.set_appearance("Light" if _dark_now else "Dark")
tab_dash, tab_board, tab_apps, tab_add, tab_rem, tab_ats, tab_cl, tab_chat, tab_set = st.tabs(
    ["Dashboard", "Board", "Applications", "Add", "Reminders", "Resume Matcher",
     "Cover Letter", "Assistant", "Settings"]
)

df = db.load_applications(conn)
stages_df    = db.load_stages(conn)
_history_df  = db.load_status_history(conn)
_contacts_df = db.load_contacts(conn)
_resumes_df = db.load_resumes(conn)
_letters_df = db.load_letters(conn)
_app_resumes = db.app_resumes(conn)
_notes_df    = db.load_notes(conn)
all_scores_df = db.load_match_scores(conn)
_latest_scores = analytics.latest_match_scores(all_scores_df)
_score_by_app: dict = {}
if not _latest_scores.empty:
    _score_by_app = dict(zip(
        _latest_scores["application_id"].astype(int),
        _latest_scores["overall_score"],
    ))

_stale_days = int(db.get_setting(conn, "stale_days", "21"))
_today     = dt.date.today()
_today_str = str(_today)

# ---------------------------------------------------------------------------
# Shared HTML builders
# ---------------------------------------------------------------------------


def _heatmap_html(counts: dict, today: dt.date) -> str:
    """Build the HTML/CSS contribution-graph heatmap."""
    days_to_mon = today.weekday()
    this_mon = today - dt.timedelta(days=days_to_mon)
    start = this_mon - dt.timedelta(weeks=25)  # 26 weeks total

    DAY_LABELS = ["M", "T", "W", "T", "F", "S", "S"]

    weeks = [
        [start + dt.timedelta(weeks=w, days=d) for d in range(7)]
        for w in range(26)
    ]

    def _cls(d: dt.date, c: int) -> str:
        if d > today:
            return "hm-future"
        if c == 0: return "hm-0"
        if c == 1: return "hm-1"
        if c == 2: return "hm-2"
        if c == 3: return "hm-3"
        return "hm-4"

    p = ['<div class="heatmap-wrap">']

    # Month labels row
    p.append('<div class="heatmap-months"><div class="hm-day-spacer"></div>')
    prev_month = None
    for wk in weeks:
        m = wk[0].month
        label = wk[0].strftime("%b") if m != prev_month else ""
        prev_month = m
        p.append(f'<div class="hm-month-cell">{label}</div>')
    p.append('</div>')

    # Day rows
    for di, day_lbl in enumerate(DAY_LABELS):
        p.append(f'<div class="heatmap-row"><div class="hm-day-label">{day_lbl}</div>')
        for wk in weeks:
            d = wk[di]
            c = counts.get(d, 0)
            title = f"{d}: {c} application{'s' if c != 1 else ''}"
            p.append(f'<div class="hm-cell {_cls(d, c)}" title="{title}"></div>')
        p.append('</div>')

    # Legend
    p.append(
        '<div class="hm-legend">'
        '<span class="hm-legend-label">Less</span>'
        '<div class="hm-cell hm-0"></div>'
        '<div class="hm-cell hm-1"></div>'
        '<div class="hm-cell hm-2"></div>'
        '<div class="hm-cell hm-3"></div>'
        '<div class="hm-cell hm-4"></div>'
        '<span class="hm-legend-label">More</span>'
        '</div>'
    )
    p.append('</div>')
    return "".join(p)


def _funnel_html(f: dict) -> str:
    """Build the horizontal funnel chart HTML."""
    if f["applied"] == 0:
        return '<div class="funnel-empty">No submitted applications yet.</div>'

    stages = [
        ("Applied",     f["applied"],    "fn-c0", 100.0),
        ("Responded",   f["responded"],  "fn-c1", f["pct_responded"]   * 100),
        ("Interviewed", f["interviewed"],"fn-c2", f["pct_interviewed"]  * 100),
        ("Offer",       f["offered"],    "fn-c3", f["pct_offered"]      * 100),
    ]

    p = ['<div class="funnel">']
    for i, (lbl, cnt, cls, pct) in enumerate(stages):
        w = max(pct, 2.0) if cnt > 0 else 0.0
        p.append(
            f'<div class="funnel-step">'
            f'<div class="funnel-step-label">{lbl}</div>'
            f'<div class="funnel-bar-wrap">'
            f'<div class="funnel-bar {cls}" style="width:{w:.1f}%">{cnt}</div>'
            f'</div>'
        )
        if i == 1:
            p.append(
                f'<div class="funnel-conv">'
                f'<span class="funnel-conv-main">{f["pct_responded"]:.0%} of applied</span>'
                f'</div>'
            )
        elif i == 2:
            p.append(
                f'<div class="funnel-conv">'
                f'<span class="funnel-conv-main">{f["pct_interviewed"]:.0%} of applied</span>'
                f'<span class="funnel-conv-step">{f["pct_step_interviewed"]:.0%} of responded</span>'
                f'</div>'
            )
        elif i == 3:
            p.append(
                f'<div class="funnel-conv">'
                f'<span class="funnel-conv-main">{f["pct_offered"]:.0%} of applied</span>'
                f'<span class="funnel-conv-step">{f["pct_step_offered"]:.0%} of interviewed</span>'
                f'</div>'
            )
        p.append('</div>')
    p.append('</div>')
    return "".join(p)


def _html_table(
    headers: list,
    rows: list,
    numeric_cols: set | None = None,
    caption: str = "",
) -> str:
    """Build a themed HTML table string."""
    nc = numeric_cols or set()
    th_cells = "".join(
        f'<th class="num">{_html.escape(str(h))}</th>' if i in nc
        else f'<th>{_html.escape(str(h))}</th>'
        for i, h in enumerate(headers)
    )
    body = ""
    for row in rows:
        tds = "".join(
            f'<td class="num">{_html.escape(str(v))}</td>' if i in nc
            else f'<td>{_html.escape(str(v))}</td>'
            for i, v in enumerate(row)
        )
        body += f"<tr>{tds}</tr>"
    cap = (
        f'<p class="tracker-table-caption">{_html.escape(caption)}</p>'
        if caption else ""
    )
    return (
        '<div class="tracker-table-wrap">'
        f'<table class="tracker-table"><thead><tr>{th_cells}</tr></thead>'
        f'<tbody>{body}</tbody></table>'
        f'{cap}</div>'
    )


def _fmt_time(hhmm: str) -> str:
    return dt.datetime.strptime(str(hhmm)[:5], "%H:%M").strftime("%-I:%M %p")


def _stage_timeline_html(app_stages: pd.DataFrame) -> str:
    """Build the interview stages timeline HTML for a single application."""
    items: list[str] = []
    rows_list = list(app_stages.itertuples())
    for i, row in enumerate(rows_list):
        is_last = (i == len(rows_list) - 1)
        date_str = str(row.stage_date)[:10] if pd.notna(row.stage_date) else "—"
        outcome = row.outcome
        outcome_cls = {
            "Passed":    "stage-tag-passed",
            "Failed":    "stage-tag-failed",
        }.get(outcome, "stage-tag-sched")
        notes_html = ""
        notes_val = str(getattr(row, "notes", "") or "").strip()
        if notes_val:
            notes_html = f'<div class="stage-notes">{_html.escape(notes_val)}</div>'
        vline = "" if is_last else '<div class="stage-vline"></div>'
        items.append(
            f'<div class="stage-item">'
            f'<div class="stage-left"><div class="stage-marker"></div>{vline}</div>'
            f'<div class="stage-body">'
            f'<div class="stage-row">'
            f'<span class="stage-name">{_html.escape(str(row.stage))}</span>'
            f'<span class="stage-date">{_html.escape(date_str)}</span>'
            f'<span class="stage-tag {outcome_cls}">{_html.escape(outcome)}</span>'
            f'</div>'
            f'{notes_html}'
            f'</div>'
            f'</div>'
        )
    return f'<div class="stage-timeline">{"".join(items)}</div>'


def _stage_pass_bars_html(pass_rates: pd.DataFrame) -> str:
    """Build horizontal pass rate bars for the Dashboard stage section."""
    rows_html: list[str] = []
    for row in pass_rates.itertuples():
        pr = row.pass_rate
        fill_pct = round(pr * 100, 1) if pr is not None else 0.0
        pr_str = f"{fill_pct:.0f}%" if pr is not None else "—"
        counts_parts = []
        if row.passed:  counts_parts.append(f"{row.passed} passed")
        if row.failed:  counts_parts.append(f"{row.failed} failed")
        if row.pending: counts_parts.append(f"{row.pending} pending")
        counts_str = " · ".join(counts_parts)
        rows_html.append(
            f'<div class="stage-pass-row">'
            f'<span class="stage-pass-label">{_html.escape(str(row.stage))}</span>'
            f'<span class="stage-pass-pct">{pr_str}</span>'
            f'<div class="stage-pass-track">'
            f'<div class="stage-pass-fill" style="width:{fill_pct:.1f}%"></div>'
            f'</div>'
            f'<span class="stage-pass-counts">{_html.escape(counts_str)}</span>'
            f'</div>'
        )
    return f'<div class="stage-pass-bars">{"".join(rows_html)}</div>'


def _match_history_html(app_scores: pd.DataFrame) -> str:
    """Build the resume match score history table HTML."""
    rows_html: list[str] = []
    for row in app_scores.itertuples():
        date_str = str(row.scanned_at)[:10] if pd.notna(row.scanned_at) else "—"
        label    = str(row.resume_label or "—")
        score    = int(round(row.overall_score))
        band     = _ats_report.score_band(row.overall_score)
        rows_html.append(
            f'<div class="match-history-row">'
            f'<span class="match-history-date">{_html.escape(date_str)}</span>'
            f'<span class="match-history-label">{_html.escape(label)}</span>'
            f'<span class="match-history-score">{score}</span>'
            f'<span class="match-history-band">{_html.escape(band)}</span>'
            f'</div>'
        )
    return f'<div class="match-history">{"".join(rows_html)}</div>'


def _stepper_html(timeline, status: str, today_d: dt.date) -> str:
    """Five-dot progress line (Wishlist → Offer) plus 'stage · N days'."""
    pipe = analytics.PIPELINE
    closed = status not in pipe
    if closed:
        reached = [s for s, _ in timeline if s in pipe]
        idx = pipe.index(reached[-1]) if reached else -1
    else:
        idx = pipe.index(status)

    dots = []
    for i, name in enumerate(pipe):
        cls = "step-dot"
        if i < idx or (i == idx and closed):
            cls += " step-dot--done"
        elif i == idx:
            cls += " step-dot--now"
        dots.append(f'<span class="{cls}" title="{_html.escape(name)}"></span>')
    mod = " stepper--closed" if closed else ""

    days = analytics.days_in_stage(timeline, today_d)
    label = f"{status} at {pipe[idx]}" if closed and idx >= 0 else status
    when = ""
    if days is not None:
        when = " · today" if days == 0 else f" · {days} day{'s' if days != 1 else ''}"
    sr = f"{label}{when}" if idx < 0 else f"Stage {idx + 1} of {len(pipe)}: {label}{when}"
    return (
        f'<div class="stepper{mod}" role="img" aria-label="{_html.escape(sr)}">'
        f'<div class="step-dots" aria-hidden="true">{"".join(dots)}</div>'
        f'<div class="step-label" aria-hidden="true">{_html.escape(label)}'
        f'<span class="step-when">{_html.escape(when)}</span></div>'
        '</div>'
    )


def _count_html(row) -> str:
    n_c, n_n = _detail_counts(row)
    parts = []
    if n_c:
        parts.append(f"{n_c} contact{'s' if n_c != 1 else ''}")
    if n_n:
        parts.append(f"{n_n} note{'s' if n_n != 1 else ''}")
    return f'<div class="board-card-counts">{" · ".join(parts)}</div>' if parts else ""


def _board_card_html(row, today_d: dt.date, match_score: float | None = None,
                     timeline=None) -> str:
    """Build the HTML for a single board card (no buttons)."""
    deadline_str = ""
    if pd.notna(row.deadline):
        deadline_str = f"Due {row.deadline.strftime('%b %d')}"

    fu_str = ""
    if hasattr(row, "follow_up_date") and pd.notna(row.follow_up_date):
        fu_str = f"Follow up {row.follow_up_date.strftime('%b %d')}"

    meta  = row.location or ""
    dates = " · ".join(x for x in [deadline_str, fu_str] if x)

    match_tag = ""
    if match_score is not None:
        match_tag = (
            f'<div class="board-match-tag">Match {int(round(match_score))}</div>'
        )

    timeline = timeline or [(row.status, None)]
    days = analytics.days_in_stage(timeline, today_d)
    stale = analytics.is_stale(row.status, days, _stale_days)
    stale_tag = (
        f'<div class="board-stale-tag" title="No reply in {days} days. Time to follow up?">'
        f'Quiet {days}d · follow up?</div>'
        if stale else ""
    )
    return (
        f'<div class="board-card{" board-card--stale" if stale else ""}">'
        f'<div class="board-card-company">{_html.escape(row.company)}</div>'
        f'<div class="board-card-role">{_html.escape(row.role)}</div>'
        + (f'<div class="board-card-meta">{_html.escape(meta)}</div>'  if meta  else "")
        + _stepper_html(timeline, row.status, today_d)
        + (f'<div class="board-card-dates">{_html.escape(dates)}</div>' if dates else "")
        + match_tag
        + _count_html(row)
        + stale_tag
        + "</div>"
    )


def _move_to(app_id: int, new_status: str, date_applied) -> None:
    """Change status; stamp date_applied the first time a job leaves Wishlist."""
    updates: dict = {"status": new_status}
    if new_status not in ("Wishlist", "Withdrawn") and pd.isna(date_applied):
        updates["date_applied"] = _today_str
    db.update_application(conn, app_id, **updates)


def _fmt_d(d) -> str:
    return d.strftime("%b %d") if d is not None and pd.notna(d) else ""


def _old_notes(row) -> str:
    """The original single notes field, minus the sample-data marker."""
    txt = str(getattr(row, "notes", "") or "").strip()
    return "" if txt == "[sample]" else txt


def _detail_counts(row) -> tuple[int, int]:
    """(contacts, notes) for a job, counting the old referral and notes fields."""
    aid = int(row.id)
    n_c = int((_contacts_df["application_id"] == aid).sum()) if not _contacts_df.empty else 0
    n_n = int((_notes_df["application_id"] == aid).sum()) if not _notes_df.empty else 0
    if str(getattr(row, "referral_name", "") or "").strip():
        n_c += 1
    if _old_notes(row):
        n_n += 1
    return n_c, n_n


def _details_panel(row, prefix: str) -> None:
    """Contacts and dated notes for one job, with quick-add forms."""
    aid = int(row.id)
    contacts = _contacts_df[_contacts_df["application_id"] == aid] if not _contacts_df.empty else _contacts_df
    notes = _notes_df[_notes_df["application_id"] == aid] if not _notes_df.empty else _notes_df

    # --- Resume sent ---
    if not _resumes_df.empty:
        st.markdown('<div class="detail-head">Resume sent</div>', unsafe_allow_html=True)
        r_opts = [None] + list(_resumes_df["id"])
        r_names = dict(zip(_resumes_df["id"], _resumes_df["name"]))
        cur_r = _app_resumes.get(aid)
        picked = st.selectbox(
            "Resume sent", r_opts, index=r_opts.index(cur_r) if cur_r in r_opts else 0,
            format_func=lambda i: "Not set" if i is None else r_names[i],
            key=f"{prefix}_res_{aid}", label_visibility="collapsed",
        )
        if picked != cur_r:
            db.set_app_resume(conn, aid, picked)
            st.rerun()

    # --- Notes ---
    st.markdown('<div class="detail-head">Notes</div>', unsafe_allow_html=True)
    with st.form(f"{prefix}_addn_{aid}", clear_on_submit=True, border=False):
        body = st.text_area("New note", key=f"{prefix}_nb_{aid}", height=80,
                            placeholder="e.g. Recruiter said decision by Dec 1")
        if st.form_submit_button("Add note"):
            if not body.strip():
                st.error("Write something first.")
            else:
                db.add_note(conn, aid, body)
                st.rerun()
    for n in notes.itertuples():
        left, right = st.columns([5, 1], vertical_alignment="top")
        left.markdown(
            f'<div class="detail-row"><span class="detail-sub">{_fmt_d(n.note_date)}</span><br>'
            f'{_html.escape(n.body)}</div>',
            unsafe_allow_html=True,
        )
        if right.button("✕", key=f"{prefix}_deln_{n.id}", help="Delete note", type="tertiary"):
            db.delete_note(conn, int(n.id))
            st.rerun()
    old = _old_notes(row)
    if old:
        st.markdown(
            '<div class="detail-row"><span class="detail-sub">Earlier notes</span><br>'
            f'{_html.escape(old)}</div>',
            unsafe_allow_html=True,
        )
    elif notes.empty:
        st.caption("No notes yet.")

    # --- Cover letters ---
    letters = _letters_df[_letters_df["application_id"] == aid] if not _letters_df.empty else _letters_df
    if not letters.empty:
        st.markdown('<div class="detail-head">Cover letters</div>', unsafe_allow_html=True)
        for lt in letters.itertuples():
            a, b, c = st.columns([3, 2, 1], vertical_alignment="center")
            a.caption(f"Saved {_fmt_d(pd.Timestamp(lt.created_on))}")
            b.download_button("PDF", cl.to_pdf(lt.body), key=f"{prefix}_lpdf_{lt.id}",
                              file_name=cl.file_name(str(row.company), str(row.role)),
                              mime="application/pdf", type="tertiary")
            if c.button("✕", key=f"{prefix}_dell_{lt.id}", help="Delete letter", type="tertiary"):
                db.delete_letter(conn, int(lt.id))
                st.rerun()

    # --- Contacts ---
    st.markdown('<div class="detail-head">Contacts</div>', unsafe_allow_html=True)
    ref_name = str(getattr(row, "referral_name", "") or "").strip()
    if ref_name:
        ref_c = str(getattr(row, "referral_contact", "") or "").strip()
        st.markdown(
            f'<div class="detail-row"><b>{_html.escape(ref_name)}</b> · Referral'
            + (f'<br><span class="detail-sub">{_html.escape(ref_c)}</span>' if ref_c else "")
            + "</div>",
            unsafe_allow_html=True,
        )
    for c in contacts.itertuples():
        sub = " · ".join(x for x in [
            str(c.contact or ""),
            f"last contacted {_fmt_d(c.last_contacted)}" if _fmt_d(c.last_contacted) else "",
        ] if x)
        left, right = st.columns([5, 1], vertical_alignment="center")
        left.markdown(
            f'<div class="detail-row"><b>{_html.escape(c.name)}</b> · {_html.escape(c.role)}'
            + (f'<br><span class="detail-sub">{_html.escape(sub)}</span>' if sub else "")
            + "</div>",
            unsafe_allow_html=True,
        )
        if right.button("✕", key=f"{prefix}_delc_{c.id}", help=f"Remove {c.name}",
                        type="tertiary"):
            db.delete_contact(conn, int(c.id))
            st.rerun()
    if contacts.empty and not ref_name:
        st.caption("No contacts yet.")

    with st.expander("Add a contact"), st.form(f"{prefix}_addc_{aid}", clear_on_submit=True, border=False):
        name = st.text_input("Name", key=f"{prefix}_cn_{aid}")
        role = st.selectbox("Role", db.CONTACT_ROLES, key=f"{prefix}_cr_{aid}")
        how = st.text_input("Email or LinkedIn", key=f"{prefix}_ce_{aid}")
        last = st.date_input("Last contacted", value=None, key=f"{prefix}_cl_{aid}")
        if st.form_submit_button("Add contact"):
            if not name.strip():
                st.error("Add a name first.")
            else:
                db.add_contact(conn, aid, name, role, how, last)
                st.rerun()


def _render_board_cards(group: pd.DataFrame, status_name: str) -> None:
    """Render board cards: stepper card, one-click advance, Move popover."""
    for row in group.itertuples():
        app_id = int(row.id)
        timeline = analytics.stage_timeline(_history_df, app_id, row.status, row.date_applied)
        st.markdown(
            _board_card_html(row, _today, _score_by_app.get(app_id), timeline),
            unsafe_allow_html=True,
        )

        nxt = analytics.next_status(status_name)
        if nxt is not None:
            if st.button(f"Move to {nxt} →", key=f"nxt_{app_id}", width="stretch"):
                _move_to(app_id, nxt, row.date_applied)
                st.rerun()

        b_stage, b_det = st.container(key=f"bbtn_{app_id}").columns(2)
        with b_stage.popover("Change stage", width="stretch",
                             key=f"move_{app_id}_{row.status}"):
            picked = st.radio(
                f"Stage for {row.company}",
                db.STATUSES,
                index=db.STATUSES.index(row.status),
                key=f"pick_{app_id}_{row.status}",
            )
            if picked != row.status:
                _move_to(app_id, picked, row.date_applied)
                st.rerun()
            st.markdown(
                '<div class="stage-history"><div class="stage-history-head">History</div>'
                + "".join(
                    f'<div class="stage-history-row"><span>{_html.escape(s)}</span>'
                    f'<span>{d.strftime("%b %d") if d is not None and pd.notna(d) else "—"}</span></div>'
                    for s, d in timeline
                )
                + "</div>",
                unsafe_allow_html=True,
            )

        with b_det.popover("Contacts & notes", width="stretch", key=f"det_{app_id}"):
            _details_panel(row, "bd")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
with tab_dash:
    if df.empty:
        st.info("No applications yet. Add one in the Add tab.")
    else:
        s  = analytics.summary(df, stages_df)
        pc = analytics.period_comparison(df, today=_today_str, stages_df=stages_df)
        c_now  = pc["current"]
        c_prev = pc["previous"]

        def _t(key):
            return c_now[key]  if pc["has_trend"] and c_now  else None

        def _p(key):
            return c_prev[key] if pc["has_trend"] and c_prev else None

        tiles = "".join([
            stat_tile_html(1, "applications",   str(s["total"]),
                           _t("total"),          _p("total"),          False),
            stat_tile_html(2, "response rate",  f"{s['response_rate']:.0%}",
                           _t("response_rate"),  _p("response_rate"),  True),
            stat_tile_html(3, "interview rate", f"{s['interview_rate']:.0%}",
                           _t("interview_rate"), _p("interview_rate"), True),
            stat_tile_html(4, "offers",          str(s["offers"]),
                           _t("offers"),          _p("offers"),        False),
            stat_tile_html(5, "active",          str(s["active"]), None, None, False),
        ])
        st.markdown(f'<div class="stat-row">{tiles}</div>', unsafe_allow_html=True)

        # --- Weekly goal: one compact line ---
        goal_stored = int(db.get_setting(conn, "weekly_goal", "10"))
        wp = analytics.weekly_progress(df, goal_stored, today=_today_str)
        gs = analytics.goal_streak(df, goal_stored, today=_today_str)
        st.markdown(
            goal_line_html(wp["count"], goal_stored, gs["current"], gs["longest"])
            + '<p class="goal-hint">Change the weekly target in Settings.</p>',
            unsafe_allow_html=True,
        )

        # --- Pipeline + weekly chart ---
        left, right = st.columns(2, gap="large")
        left.subheader("Pipeline")
        left.altair_chart(
            charts.pipeline_chart(analytics.status_counts(df)),
            width="stretch", theme=None,
        )
        right.subheader("Applications per week")
        right.altair_chart(
            charts.weekly_chart(analytics.weekly_counts(df, today=_today_str), goal_stored),
            width="stretch", theme=None,
        )

        # --- Heatmap ---
        st.subheader("Activity — last 26 weeks")
        apd = analytics.applications_per_day(df, today=_today_str)
        st.markdown(_heatmap_html(apd, _today), unsafe_allow_html=True)

        # --- Funnel ---
        st.subheader("Pipeline funnel")
        st.markdown(_funnel_html(analytics.funnel(df, stages_df)), unsafe_allow_html=True)

        # --- Interview stage pass rates ---
        pr = analytics.stage_pass_rates(stages_df)
        if not pr.empty:
            st.subheader("Pass rate by stage")
            st.markdown(_stage_pass_bars_html(pr), unsafe_allow_html=True)

        # --- By source, referral comparison, deadlines ---
        st.subheader("Where are responses coming from?")
        rbs = analytics.response_by_source(df, stages_df)
        if not rbs.empty:
            st.caption("Response rate by source — share of submitted applications that heard back.")
            st.altair_chart(charts.response_rate_chart(rbs), width="stretch", theme=None)
        src = analytics.by_source(df)
        if src.empty:
            st.caption("Add a source to applications to see this.")
        else:
            src_rows = [
                [row.source, row.applications, row.advanced]
                for row in src.itertuples(index=False)
            ]
            st.markdown(
                _html_table(
                    ["Source", "Applications", "Moved forward"],
                    src_rows,
                    numeric_cols={1, 2},
                ),
                unsafe_allow_html=True,
            )

        st.subheader("How long until they reply?")
        frd = analytics.first_response_days(df, _history_df)
        if len(frd) < 2:
            st.caption("Shows once at least two jobs have heard back (a screen, interview, "
                       "offer or rejection).")
        else:
            st.markdown(
                f'<p class="ats-note">Typical wait for a first reply: '
                f'<b>{int(frd["days"].median())} days</b> '
                f'(fastest {int(frd["days"].min())}, slowest {int(frd["days"].max())}; '
                f'{len(frd)} jobs).</p>',
                unsafe_allow_html=True,
            )
            by = (frd.groupby("source")["days"].agg(["median", "count"])
                  .sort_values("median").reset_index())
            st.markdown(
                _html_table(["Source", "Typical days to reply", "Replies"],
                            [[r.source, int(r.median), int(r.count)] for r in by.itertuples()],
                            numeric_cols={1, 2}),
                unsafe_allow_html=True,
            )

        st.subheader("Referred vs. Cold")
        rc = analytics.referral_comparison(df, stages_df)
        if rc["referred"]["submitted"] == 0 and rc["cold"]["submitted"] == 0:
            st.caption("No referral data yet — add a referral name when logging applications.")
        else:
            rc_rows = []
            for label, g in [("Referred", rc["referred"]), ("Cold", rc["cold"])]:
                rc_rows.append([
                    label, g["count"], g["submitted"],
                    f'{g["response_rate"]:.0%}', f'{g["interview_rate"]:.0%}',
                ])
            st.markdown(
                _html_table(
                    ["Type", "Applications", "Submitted", "Response rate", "Interview rate"],
                    rc_rows,
                    numeric_cols={1, 2},
                ),
                unsafe_allow_html=True,
            )

        st.subheader("Deadlines in the next 14 days")
        dl = analytics.upcoming_deadlines(df)
        if dl.empty:
            st.caption("Nothing due soon.")
        else:
            st.dataframe(dl, width="stretch", hide_index=True)

# ---------------------------------------------------------------------------
# Board (Kanban)
# ---------------------------------------------------------------------------
with tab_board:
    df_board = db.load_applications(conn)
    BOARD_COLS = ["Wishlist", "Applied", "OA/Screen", "Interview", "Offer", "Rejected"]

    drag = st.toggle("Drag to move", key="board_drag",
                     help="Drag cards between columns to change their stage.")
    if df_board.empty:
        st.info("No applications yet. Add one in the Add tab.")
    elif drag:
        from streamlit_sortables import sort_items
        before, labels = [], {}
        for status_name in BOARD_COLS:
            items = []
            for r in df_board[df_board["status"] == status_name].itertuples():
                lab = f"{r.company} — {r.role}  #{r.id}"
                labels[lab] = (int(r.id), r.date_applied)
                items.append(lab)
            before.append({"header": status_name, "items": items})
        after = sort_items(before, multi_containers=True, direction="horizontal",
                           key=f"drag_{st.session_state.get('drag_n', 0)}")
        moved = False
        for col in after or []:
            for lab in col["items"]:
                aid, d_app = labels[lab]
                old_status = next(c["header"] for c in before if lab in c["items"])
                if old_status != col["header"]:
                    _move_to(aid, col["header"], d_app)
                    moved = True
        if moved:
            st.session_state["drag_n"] = st.session_state.get("drag_n", 0) + 1
            st.session_state["mac_dirty"] = True
            st.rerun()
        st.caption("Turn off “Drag to move” to see full cards, notes and buttons.")
    else:
        bcols = st.columns(len(BOARD_COLS))
        for col_st, status_name in zip(bcols, BOARD_COLS):
            group = df_board[df_board["status"] == status_name]
            with col_st:
                st.markdown(
                    f'<div class="board-col-header">'
                    f'{status_name} <span class="board-count">{len(group)}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if group.empty:
                    st.markdown('<div class="board-empty">No applications</div>',
                                unsafe_allow_html=True)
                    continue

                visible = group.head(8)
                extra = len(group) - 8
                _render_board_cards(visible, status_name)

                if extra > 0:
                    with st.expander(f"Show {extra} more"):
                        _render_board_cards(group.iloc[8:], status_name)

        # Withdrawn — collapsed expander below board
        withdrawn = df_board[df_board["status"] == "Withdrawn"]
        if not withdrawn.empty:
            with st.expander(f"Withdrawn ({len(withdrawn)})"):
                st.dataframe(
                    withdrawn[["company", "role", "location", "date_applied"]],
                    width="stretch",
                    hide_index=True,
                )

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
with tab_apps:
    if df.empty:
        st.caption("Nothing here yet.")
    else:
        f1, f2 = st.columns(2)
        statuses = f1.multiselect("Status", db.STATUSES)
        q = f2.text_input("Search company / role")
        view = df
        if statuses:
            view = view[view["status"].isin(statuses)]
        if q:
            m = view["company"].str.contains(q, case=False) | view["role"].str.contains(q, case=False)
            view = view[m]
        st.dataframe(view, width="stretch", hide_index=True)

        st.download_button(
            "Download CSV",
            data=view.to_csv(index=False).encode("utf-8"),
            file_name="applications.csv",
            mime="text/csv",
        )

        st.divider()
        st.subheader("Edit or delete")
        choice = st.selectbox(
            "Application", df["id"],
            format_func=lambda i: f"{df.loc[df.id == i, 'company'].iloc[0]} — {df.loc[df.id == i, 'role'].iloc[0]}",
        )
        cur = df[df["id"] == choice].iloc[0]
        ea, eb = st.columns(2)
        new_company     = ea.text_input("Company *",         cur["company"],               key=f"co{choice}")
        new_role        = eb.text_input("Role *",            cur["role"],                  key=f"ro{choice}")
        new_location    = ea.text_input("Location",          cur.get("location", ""),      key=f"lo{choice}")
        new_source      = eb.text_input("Source",            cur.get("source", ""),        key=f"so{choice}")
        new_status      = ea.selectbox("Status", db.STATUSES, index=db.STATUSES.index(cur["status"]), key=f"st{choice}")
        new_applied     = eb.date_input("Date applied",      value=_to_date(cur.get("date_applied")),   key=f"da{choice}")
        new_deadline    = ea.date_input("Deadline",          value=_to_date(cur.get("deadline")),        key=f"dl{choice}")
        new_ref_name    = eb.text_input("Referral name",     cur.get("referral_name", ""), key=f"rn{choice}")
        new_ref_contact = ea.text_input("Referral contact",  cur.get("referral_contact", ""), key=f"rc{choice}")
        new_follow_up   = eb.date_input("Follow-up date",    value=_to_date(cur.get("follow_up_date")),  key=f"fu{choice}")
        new_notes       = st.text_area("Earlier notes",      cur.get("notes", ""),         key=f"no{choice}")

        b1, b2, _ = st.columns([1, 1, 6])
        if b1.button("Save"):
            if not new_company.strip() or not new_role.strip():
                st.error("Error: Company and role cannot be empty.")
            else:
                db.update_application(
                    conn, int(choice),
                    company=new_company.strip(),
                    role=new_role.strip(),
                    location=new_location,
                    source=new_source,
                    status=new_status,
                    date_applied=str(new_applied) if new_applied else None,
                    deadline=str(new_deadline) if new_deadline else None,
                    referral_name=new_ref_name,
                    referral_contact=new_ref_contact,
                    follow_up_date=str(new_follow_up) if new_follow_up else None,
                    notes=new_notes,
                )
                st.rerun()
        if b2.button("Delete"):
            db.delete_application(conn, int(choice))
            st.rerun()

        # --- Contacts & notes ---
        st.divider()
        st.subheader("Contacts & notes")
        _details_panel(next(df[df["id"] == choice].itertuples()), "ap")

        # --- Interview stages ---
        st.divider()
        st.subheader("Interview stages")

        if not stages_df.empty and "application_id" in stages_df.columns:
            app_stages = stages_df[stages_df["application_id"] == int(choice)].copy()
        else:
            app_stages = pd.DataFrame()
        if not app_stages.empty:
            app_stages = app_stages.sort_values("stage_date", na_position="first")

        cur_status = cur["status"]
        if not app_stages.empty and cur_status in {"Wishlist", "Applied"}:
            st.markdown(
                '<div class="ats-note">Stages logged — consider updating the status '
                "to OA/Screen or Interview.</div>",
                unsafe_allow_html=True,
            )

        if app_stages.empty:
            st.caption("No interview stages logged yet.")
        else:
            st.markdown(_stage_timeline_html(app_stages), unsafe_allow_html=True)
            for stage_row in app_stages.itertuples():
                sc1, sc2, sc3, sc4 = st.columns([4, 1, 1, 1])
                s_label = str(stage_row.stage)
                s_time = getattr(stage_row, "stage_time", None)
                s_time = s_time if isinstance(s_time, str) and s_time else None
                if pd.notna(stage_row.stage_date):
                    s_label += f" — {str(stage_row.stage_date)[:10]}"
                    if s_time:
                        s_label += f" at {_fmt_time(s_time)}"
                sc1.caption(s_label)
                if pd.notna(stage_row.stage_date) and stage_row.outcome == "Scheduled":
                    sc1.download_button(
                        "📅 Add to calendar",
                        _ics.event_ics(
                            f"stage-{stage_row.id}@ktproject",
                            f"{stage_row.stage}: {cur['company']} — {cur['role']}",
                            stage_row.stage_date, s_time,
                            description=str(stage_row.notes or "")),
                        file_name=f"interview-{stage_row.id}.ics", mime="text/calendar",
                        key=f"sics_{stage_row.id}")
                if stage_row.outcome != "Passed":
                    if sc2.button("Pass", key=f"sp_{stage_row.id}"):
                        db.update_stage(conn, int(stage_row.id), outcome="Passed")
                        st.rerun()
                if stage_row.outcome != "Failed":
                    if sc3.button("Fail", key=f"sf_{stage_row.id}"):
                        db.update_stage(conn, int(stage_row.id), outcome="Failed")
                        st.rerun()
                if sc4.button("Del", key=f"sd_{stage_row.id}"):
                    db.delete_stage(conn, int(stage_row.id))
                    st.rerun()

        with st.expander("Add interview stage"):
            with st.form(f"add_stage_{choice}"):
                sg1, sg2 = st.columns(2)
                new_stage_type    = sg1.selectbox("Stage type", db.STAGE_TYPES,    key=f"stype_{choice}")
                new_stage_date    = sg2.date_input("Date", dt.date.today(),         key=f"sdate_{choice}")
                new_stage_outcome = sg1.selectbox("Outcome", db.STAGE_OUTCOMES,    key=f"sout_{choice}")
                new_stage_notes   = sg2.text_input("Notes", "",                     key=f"snotes_{choice}")
                has_time = sg1.checkbox("Set a time", key=f"shas_{choice}")
                new_stage_time = sg2.time_input("Time", dt.time(10, 0), step=900, key=f"stime_{choice}")
                if st.form_submit_button("Add stage"):
                    db.add_stage(conn, int(choice), new_stage_type, str(new_stage_date),
                                 new_stage_outcome, new_stage_notes,
                                 stage_time=new_stage_time.strftime("%H:%M") if has_time else None)
                    st.session_state["mac_dirty"] = True
                    st.rerun()

        # --- Resume match history ---
        if not all_scores_df.empty and "application_id" in all_scores_df.columns:
            app_scores = all_scores_df[all_scores_df["application_id"] == int(choice)].copy()
        else:
            app_scores = pd.DataFrame()

        if not app_scores.empty:
            st.divider()
            st.subheader("Resume match history")
            st.markdown(_match_history_html(app_scores), unsafe_allow_html=True)
            if len(app_scores) >= 2:
                st.altair_chart(
                    charts.score_history_chart(app_scores),
                    width="stretch", theme=None,
                )
            # Delete buttons
            for score_row in app_scores.itertuples():
                date_lbl = str(score_row.scanned_at)[:10]
                if st.button(f"Delete score from {date_lbl}", key=f"ds_{score_row.id}"):
                    db.delete_match_score(conn, int(score_row.id))
                    st.rerun()

# ---------------------------------------------------------------------------
# Add
# ---------------------------------------------------------------------------
with tab_add:
    with st.form("add", clear_on_submit=True):
        a, b = st.columns(2)
        company     = a.text_input("Company *")
        role        = b.text_input("Role *")
        location    = a.text_input("Location")
        source      = b.text_input("Source (LinkedIn, referral, career fair...)")
        status      = a.selectbox("Status", db.STATUSES, index=1)
        applied     = b.date_input("Date applied", dt.date.today())
        deadline    = a.date_input("Deadline", value=None)
        ref_name    = b.text_input("Referral name (optional)")
        ref_contact = a.text_input("Referral contact (optional)")
        follow_up   = b.date_input("Follow-up date (optional)", value=None)
        status_on   = a.date_input("Date it reached this status (for older jobs)", value=None,
                                   help="E.g. the day you were rejected or got the interview. "
                                        "Leave blank for new applications.")
        notes       = st.text_area("Notes")
        if st.form_submit_button("Add application"):
            try:
                db.add_application(
                    conn, company, role, location, status, applied, deadline, source, notes,
                    referral_name=ref_name,
                    referral_contact=ref_contact,
                    follow_up_date=str(follow_up) if follow_up else None,
                    status_date=status_on,
                )
                st.success("Added!")
                st.rerun()
            except ValueError as e:
                st.error(f"Error: {e}")

# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------
with tab_rem:
    # --- Mac Reminders: settings + automatic sync ---
    _mac_on = mac.available() and db.get_setting(conn, "mac_sync", "0") == "1"
    _mac_list = db.get_setting(conn, "mac_list", mac.DEFAULT_LIST)
    _mac_kinds = set(filter(None, db.get_setting(conn, "mac_kinds", "task,fu,dl,st").split(",")))

    def _mac_sync(show=False):
        try:
            with st.spinner("Syncing with Reminders on your Mac…"):
                r = mac.sync(conn, _mac_list, _mac_kinds, today=_today_str)
            st.session_state["mac_status"] = (
                "ok", f"Synced with “{_mac_list}”: {r['created']} added, {r['updated']} updated, "
                      f"{r['pulled']} marked done from your Mac."
                + (f" {len(r['errors'])} couldn't be saved." if r["errors"] else ""))
        except mac.RemindersError as e:
            st.session_state["mac_status"] = ("error", str(e))
        st.session_state["mac_synced"] = True
        st.session_state.pop("mac_dirty", None)

    if _mac_on and (not st.session_state.get("mac_synced") or st.session_state.get("mac_dirty")):
        _mac_sync()
        st.rerun()  # show anything that was ticked off on the Mac

    def _changed():
        st.session_state["mac_dirty"] = True
        st.rerun()

    # --- New reminder ---
    st.subheader("New reminder")
    with st.form("new_task", clear_on_submit=True, border=False):
        t1, t2, t3 = st.columns([3, 1.2, 1])
        t_title = t1.text_input("What", placeholder="e.g. Send a thank-you note to Mansfield")
        t_date = t2.date_input("Date", value=_today + dt.timedelta(days=1))
        t_time = t3.time_input("Time", value=dt.time(9, 0), step=900)
        job_ids = [None] + (list(df["id"]) if not df.empty else [])
        t_job = st.selectbox(
            "Job (optional)", job_ids,
            format_func=lambda i: "—" if i is None else
            f"{df.loc[df.id == i, 'company'].iloc[0]} — {df.loc[df.id == i, 'role'].iloc[0]}",
        )
        if st.form_submit_button("Add reminder"):
            try:
                db.add_task(conn, t_title, t_date, t_job, t_time.strftime("%H:%M") if t_time else None)
                _changed()
            except ValueError as e:
                st.error(str(e))

    tasks_df = db.load_tasks(conn)
    if not tasks_df.empty:
        st.subheader(f"Your to-dos ({len(tasks_df)})")
        for t in tasks_df.itertuples():
            when = t.due_date.strftime("%a, %b %-d") + (
                f" · {dt.datetime.strptime(t.due_time, '%H:%M').strftime('%-I:%M %p')}"
                if t.due_time else "")
            late = t.due_date.date() < _today
            job = f" — {t.company}" if isinstance(t.company, str) and t.company else ""
            c1, c2, c3, c4 = st.columns([5, 2, 1, 1], vertical_alignment="center")
            c1.markdown(f"**{_html.escape(t.title)}**{_html.escape(job)}")
            c2.markdown(f'<span class="{"task-late" if late else "task-when"}">{when}</span>',
                        unsafe_allow_html=True)
            if c3.button("Done", key=f"tdone_{t.id}"):
                db.set_task_done(conn, int(t.id))
                _changed()
            if c4.button("✕", key=f"tdel_{t.id}", help="Delete", type="tertiary"):
                db.delete_task(conn, int(t.id))
                _changed()

    # --- Mac Reminders panel ---
    if mac.available():
        with st.expander("Mac Reminders" + (f" · syncing with “{_mac_list}”" if _mac_on else " · off")):
            on = st.toggle("Sync with the Reminders app on this Mac", value=_mac_on, key="mac_on")
            if on != _mac_on:
                db.set_setting(conn, "mac_sync", "1" if on else "0")
                st.session_state.pop("mac_synced", None)
                st.rerun()
            st.caption(
                "Reminders show up on your Mac and iPhone. Ticking one off there marks it "
                "done here the next time this tab syncs, and the other way round. "
                "The first time, macOS asks to let this app control Reminders."
            )
            if on:
                try:
                    names = mac.list_names()
                except mac.RemindersError as e:
                    names = []
                    st.error(str(e))
                opts = names if _mac_list in names else [_mac_list] + names
                new_list = st.selectbox("Reminders list", opts, index=opts.index(_mac_list),
                                        key="mac_list_pick",
                                        help="Pick an existing list, or keep the default to have one made.")
                if new_list != _mac_list:
                    db.set_setting(conn, "mac_list", new_list)
                    _changed()
                picked = st.multiselect(
                    "What to send", list(mac.KINDS), default=[k for k in mac.KINDS if k in _mac_kinds],
                    format_func=mac.KINDS.get, key="mac_kinds_pick")
                if set(picked) != _mac_kinds:
                    db.set_setting(conn, "mac_kinds", ",".join(picked))
                    _changed()
                if st.button("Sync now", key="mac_sync_now"):
                    _mac_sync()
                    st.rerun()
        status = st.session_state.get("mac_status")
        if _mac_on and status:
            (st.caption if status[0] == "ok" else st.error)(status[1])

    st.divider()
    rem   = analytics.reminders(df, today=_today_str)
    stale = analytics.stale_applications(df, today=_today_str, days=_stale_days)

    _has_any = any(not v.empty for v in rem.values()) or not stale.empty
    if not _has_any:
        st.info("No follow-ups scheduled.")
    else:
        for section_key, label in [
            ("overdue",   "Overdue"),
            ("due_today", "Due today"),
            ("upcoming",  "Upcoming (next 14 days)"),
        ]:
            group = rem[section_key]
            count = len(group)
            st.subheader(f"{label} ({count})")
            if group.empty:
                st.caption("None.")
            else:
                for row in group.itertuples():
                    c1, c2, c3, c4, c5 = st.columns([3, 2, 1, 1, 1])
                    c1.write(f"**{row.company}** — {row.role}")
                    fu_str = str(row.follow_up_date)[:10] if pd.notna(row.follow_up_date) else "—"
                    c2.write(fu_str)
                    if c3.button("Done", key=f"done_{row.id}"):
                        db.update_application(conn, int(row.id), follow_up_date=None)
                        _changed()
                    if c4.button("+3d", key=f"s3_{row.id}"):
                        db.update_application(conn, int(row.id),
                                              follow_up_date=str(_today + dt.timedelta(days=3)))
                        _changed()
                    if c5.button("+7d", key=f"s7_{row.id}"):
                        db.update_application(conn, int(row.id),
                                              follow_up_date=str(_today + dt.timedelta(days=7)))
                        _changed()

        if not stale.empty:
            st.subheader(f"No reply after {_stale_days}+ days ({len(stale)})")
            st.dataframe(
                stale[["company", "role", "days_waiting"]].rename(
                    columns={"days_waiting": "Days waiting"}),
                width="stretch",
                hide_index=True,
            )

    # --- ICS calendar export ---
    st.divider()
    st.subheader("Download calendar (.ics)")
    ic1, ic2, ic3, ic4 = st.columns(4)
    inc_fu   = ic1.checkbox("Follow-ups",    value=True,  key="ics_fu")
    inc_dl   = ic2.checkbox("Deadlines",     value=True,  key="ics_dl")
    inc_int  = ic3.checkbox("Interviews",    value=True,  key="ics_int")
    inc_past = ic4.checkbox("Include past",  value=False, key="ics_past")

    ics_text   = _ics.build_ics(df, stages_df, _today_str,
                                include_followups=inc_fu,
                                include_deadlines=inc_dl,
                                include_interviews=inc_int,
                                include_past=inc_past)
    event_count = ics_text.count("BEGIN:VEVENT")
    s_plural    = "s" if event_count != 1 else ""
    if event_count == 0:
        st.caption("No events match the selected filters.")
    else:
        st.caption(f"{event_count} event{s_plural} selected.")
    st.download_button(
        "Download calendar (.ics)",
        data=ics_text.encode("utf-8"),
        file_name="tracker.ics",
        mime="text/calendar",
        key="ics_download",
        disabled=(event_count == 0),
    )
    st.caption(
        "Open the .ics file to add events to Apple Calendar. "
        "In Google Calendar: Settings > Import & export > Import."
    )

# ---------------------------------------------------------------------------
# Resume Matcher
# ---------------------------------------------------------------------------
with tab_ats:
    ats_ui.render(conn)

# ---------------------------------------------------------------------------
# Cover Letter — resume + template + job description -> PDF
# ---------------------------------------------------------------------------
_CL_EXAMPLE = """{date}

Dear {hiring_manager},

I'm excited to apply for the {role} position at {company}. [Why this company interests you.]

[A paragraph about your most relevant experience.] I've built strong skills in {skills}, which line up with what your team is looking for.

[A closing line about what you'd bring and your availability.]

Thank you for your time and consideration.

Sincerely,
[Your name]"""


with tab_cl:
    st.caption(
        "Your resume and template are saved on this computer so you only enter them once. "
        "Nothing is sent anywhere unless you pick an Ollama cloud model."
    )

    # --- 1. Resume ---
    st.subheader("1. Your resume")
    saved_resume = db.get_setting(conn, "cl_resume", "")
    up = st.file_uploader("Upload your resume (PDF)", type=["pdf"], key="cl_pdf")
    if up is not None and st.session_state.get("cl_pdf_seen") != up.file_id:
        try:
            from tracker.ats.extractor import extract_text_from_pdf
            saved_resume = extract_text_from_pdf(up.getvalue()).strip()
            db.set_setting(conn, "cl_resume", saved_resume)
            st.session_state["cl_pdf_seen"] = up.file_id
            st.session_state["cl_resume_text"] = saved_resume
        except Exception as e:  # pdfplumber errors vary
            st.error(f"Couldn't read that PDF: {e}")
    if not _resumes_df.empty:
        v_names = dict(zip(_resumes_df["id"], _resumes_df["name"]))
        v_pick = st.selectbox(
            "Use a saved version", [None] + list(_resumes_df["id"]),
            format_func=lambda i: "—" if i is None else v_names[i], key="cl_ver",
        )
        if v_pick is not None and st.session_state.get("cl_ver_seen") != v_pick:
            saved_resume = _resumes_df.loc[_resumes_df.id == v_pick, "body"].iloc[0]
            db.set_setting(conn, "cl_resume", saved_resume)
            st.session_state["cl_resume_text"] = saved_resume
        st.session_state["cl_ver_seen"] = v_pick
    resume_text = st.text_area(
        "Resume text (you can edit it)", value=saved_resume, height=160, key="cl_resume_text",
    )
    if resume_text != saved_resume:
        db.set_setting(conn, "cl_resume", resume_text)
    with st.popover("Save as a version", key="cl_save_ver"):
        st.caption("Name it so you can track which one you sent to each job "
                   "(pick it under Contacts & notes on the job).")
        v_name = st.text_input("Name", placeholder="e.g. Data analyst v2", key="cl_ver_name")
        if st.button("Save version", key="cl_ver_btn"):
            try:
                db.save_resume(conn, v_name, resume_text)
                st.toast(f"Saved “{v_name.strip()}”")
                st.rerun()
            except ValueError as e:
                st.error(str(e))
        if not _resumes_df.empty:
            st.divider()
            for r in _resumes_df.itertuples():
                a, b = st.columns([5, 1], vertical_alignment="center")
                a.caption(f"{r.name} · saved {r.created_on}")
                if b.button("✕", key=f"cl_delver_{r.id}", type="tertiary", help="Delete version"):
                    db.delete_resume(conn, int(r.id))
                    st.rerun()

    # --- 2. Template ---
    st.subheader("2. Your template")
    tpl_up = st.file_uploader(
        "Upload your template (Word, PDF or text file)",
        type=cl.TEMPLATE_TYPES, key="cl_tpl_file",
    )
    if tpl_up is not None and st.session_state.get("cl_tpl_seen") != tpl_up.file_id:
        st.session_state["cl_tpl_seen"] = tpl_up.file_id
        try:
            new_tpl = cl.template_from_file(tpl_up.name, tpl_up.getvalue())
            db.set_setting(conn, "cl_template", new_tpl)
            db.set_setting(conn, "cl_template_docx",
                           base64.b64encode(tpl_up.getvalue()).decode()
                           if tpl_up.name.lower().endswith(".docx") else "")
            st.session_state["cl_template_text"] = new_tpl
            st.success(f"Loaded your template from {tpl_up.name}. You can edit it below.")
        except ValueError as e:
            st.error(str(e))
    saved_tpl = db.get_setting(conn, "cl_template", "") or _CL_EXAMPLE
    st.markdown(
        '<div class="cl-placeholders">'
        + "".join(f"<span><code>{_html.escape(k)}</code> {_html.escape(v)}</span>"
                  for k, v in cl.PLACEHOLDERS.items())
        + "</div>",
        unsafe_allow_html=True,
    )
    template = st.text_area("Template (or type / paste it here)", value=saved_tpl,
                            height=260, key="cl_template_text")
    if template.strip() and not cl.placeholders_in(template):
        st.caption(
            "This template has no {placeholders}. Write with AI will still follow its style. "
            "For Fill my template, swap the parts that change per job for "
            "{company}, {role} and so on."
        )
    if template != db.get_setting(conn, "cl_template", ""):
        db.set_setting(conn, "cl_template", template)

    # --- 3. Job ---
    st.subheader("3. The job")
    jd = st.text_area("Job description", height=220, key="cl_jd",
                      placeholder="Paste any job posting here. It doesn't need to be in your tracker.")
    with st.expander("Or fill in from a job in your tracker"):
        job_opts = [None] + (list(df["id"]) if not df.empty else [])
        pick = st.selectbox(
            "Job", job_opts,
            format_func=lambda i: "—" if i is None else
            f"{df.loc[df.id == i, 'company'].iloc[0]} — {df.loc[df.id == i, 'role'].iloc[0]}",
            key="cl_pick",
        )
    pick_row = df[df["id"] == pick].iloc[0] if pick is not None else None
    if pick is not None and _app_resumes.get(int(pick)):
        _rid = _app_resumes[int(pick)]
        _rn = _resumes_df.loc[_resumes_df.id == _rid, "name"]
        if not _rn.empty:
            st.caption(f"You sent **{_rn.iloc[0]}** to this job. Pick it above to use that text.")
    guessed = st.session_state.get("cl_guess", {}) if pick is None else {}
    j1, j2, j3 = st.columns(3)
    company = j1.text_input(
        "Company", key=f"cl_co_{pick}_{guessed.get('n', 0)}",
        value=pick_row["company"] if pick_row is not None else guessed.get("company", ""),
        placeholder="Found from the posting if blank",
    )
    role = j2.text_input(
        "Role", key=f"cl_ro_{pick}_{guessed.get('n', 0)}",
        value=pick_row["role"] if pick_row is not None else guessed.get("role", ""),
        placeholder="Found from the posting if blank",
    )
    manager = j3.text_input("Hiring manager (optional)", key=f"cl_hm_{pick}")

    # --- 4. Write ---
    st.subheader("4. Write the letter")
    models = cl.ollama_models()
    ways = ["Fill my template (no AI)"]
    if models:
        ways.insert(0, "Write with AI (Ollama)")
    way = st.radio("How", ways, horizontal=True, key="cl_way")
    model = None
    if way.startswith("Write with AI"):
        def _model_label(m):
            where = ("cloud: text leaves this computer" if m["cloud"]
                     else f"on this computer, {m['size_gb']} GB")
            return f"{m['name']} · {where}"
        labels = {m["name"]: _model_label(m) for m in models}
        saved_model = db.get_setting(conn, "cl_model", "")
        names = list(labels)
        model = st.selectbox("Model", names,
                             index=names.index(saved_model) if saved_model in names else 0,
                             format_func=labels.get, key="cl_model_pick")
        if model != saved_model:
            db.set_setting(conn, "cl_model", model)
    elif not models:
        st.caption("To write with AI, install and open Ollama (free, ollama.com), then reload this page.")

    voice = db.get_setting(conn, "cl_voice", "")
    if way.startswith("Write with AI"):
        with st.expander("Make it sound like me" + (" · sample saved" if voice.strip() else "")):
            st.caption("Paste something you wrote yourself: an old cover letter, an essay, "
                       "a LinkedIn post. The AI copies your tone and wording, not the facts.")
            _v = st.text_area("Your writing sample", value=voice, height=160,
                              key="cl_voice_in", label_visibility="collapsed")
            if _v != voice:
                db.set_setting(conn, "cl_voice", _v)
                voice = _v
        _terms = cl.shared_skills(resume_text, jd, limit=10)
        if _terms:
            st.caption("Posting keywords it will work in (you have these): " + ", ".join(_terms))

    if st.button("Write cover letter", type="primary", key="cl_go"):
        use_ai = way.startswith("Write with AI")
        # Company/role left blank: read them from the pasted posting.
        if jd.strip() and not (company.strip() and role.strip()):
            finder = model if use_ai else next((m["name"] for m in models if not m["cloud"]), None)
            if finder:
                with st.spinner("Finding the company and role in the posting…"):
                    g_co, g_ro = cl.guess_company_role(finder, jd)
                company = company.strip() or g_co
                role = role.strip() or g_ro
                if pick is None:
                    st.session_state["cl_guess"] = {
                        "company": company, "role": role,
                        "n": st.session_state.get("cl_guess", {}).get("n", 0) + 1,
                    }

        missing = [n for n, v in [("job description", jd), ("company", company), ("role", role)]
                   if not v.strip()]
        if use_ai and not resume_text.strip():
            missing.append("resume")
        if missing:
            st.error("Add the " + ", ".join(missing) + " first."
                     + (" (I couldn't find it in the posting.)"
                        if jd.strip() and ("company" in missing or "role" in missing) else ""))
        else:
            ok = True
            if use_ai:
                with st.spinner(f"Writing with {model}… this can take a minute or two."):
                    try:
                        st.session_state["cl_draft"] = cl.write_letter_from_template(
                            model, resume_text, jd, template, company, role, manager, voice)
                    except RuntimeError as e:
                        st.error(f"Ollama couldn't write the letter: {e}")
                        ok = False
            else:
                skills = cl.shared_skills(resume_text, jd)
                st.session_state["cl_draft"] = cl.fill_template(
                    template, cl.fields_for(company, role, manager, skills))
            if ok:
                st.session_state["cl_for"] = (company, role)
                st.session_state.pop("cl_edit", None)  # show the new draft, not the old edit
                st.rerun()

    # --- 5. Edit + download ---
    if st.session_state.get("cl_draft"):
        st.subheader("5. Review and download")
        draft = st.text_area("Your letter (edit anything before downloading)",
                             value=st.session_state["cl_draft"], height=380, key="cl_edit")
        if "{" in draft and "}" in draft:
            st.caption("Heads up: the letter still has a {placeholder} in it.")
        unbacked = cl.unbacked_skills(draft, resume_text, jd)
        if unbacked:
            st.warning(
                "Check before sending: the letter mentions "
                + ", ".join(unbacked)
                + ", which " + ("isn't" if len(unbacked) == 1 else "aren't")
                + " on your resume. Remove it or add it to your resume if it's true."
            )
        if models:
            with st.expander("Ask the AI to make it stronger"):
                _req = st.text_area(
                    "What should change?", key="cl_req", height=90,
                    placeholder="e.g. Make the opening less generic, mention my data project "
                                "first, cut it to 250 words, sound more confident",
                )
                r1, r2 = st.columns([1, 1])
                if r1.button("Revise letter", key="cl_rev", disabled=not _req.strip(),
                             width="stretch"):
                    _m = model or next((m["name"] for m in models if not m["cloud"]), models[0]["name"])
                    with st.spinner(f"Revising with {_m}…"):
                        try:
                            _new = cl.revise_letter(_m, draft, _req, resume_text, jd, voice)
                        except RuntimeError as e:
                            st.error(f"Ollama couldn't revise it: {e}")
                        else:
                            st.session_state["cl_prev"] = draft
                            st.session_state["cl_draft"] = _new
                            st.session_state.pop("cl_edit", None)
                            st.rerun()
                if st.session_state.get("cl_prev") and r2.button(
                        "Undo last revision", key="cl_undo", width="stretch"):
                    st.session_state["cl_draft"] = st.session_state.pop("cl_prev")
                    st.session_state.pop("cl_edit", None)
                    st.rerun()
        co, ro = st.session_state.get("cl_for", (company, role))
        _tpl_docx = db.get_setting(conn, "cl_template_docx", "")
        d1, d2, d3 = st.columns(3)
        d1.download_button(
            "Download PDF",
            data=cl.to_pdf(draft, title=f"Cover letter — {co}"),
            file_name=cl.file_name(co, ro),
            mime="application/pdf",
            key="cl_dl", width="stretch",
        )
        d2.download_button(
            "Download Word",
            data=cl.to_docx(draft, base64.b64decode(_tpl_docx) if _tpl_docx else None),
            file_name=cl.file_name(co, ro).replace(".pdf", ".docx"),
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="cl_dlw", width="stretch",
            help="Uses your Word template's fonts and layout" if _tpl_docx else None,
        )
        # Save to a job in the tracker (adding it first if it's new).
        match = pd.DataFrame()
        if pick is not None:
            match = df[df["id"] == pick]
        elif not df.empty and co:
            match = df[(df["company"].str.strip().str.lower() == str(co).strip().lower())
                       & (df["role"].str.strip().str.lower() == str(ro).strip().lower())]
        if not match.empty:
            if d3.button("Save to this job", key="cl_save", width="stretch"):
                db.save_letter(conn, int(match.iloc[0]["id"]), draft)
                st.toast(f"Saved to {co} — {ro}. Find it under Contacts & notes.")
                st.rerun()
        elif co and ro:
            if d3.button("Add job to tracker + save", key="cl_add", width="stretch",
                         help="Adds it to your Wishlist with the posting as a note"):
                new_id = db.add_application(conn, co, ro, status="Wishlist", date_applied=None)
                if jd.strip():
                    db.add_note(conn, new_id, "Job posting:\n" + jd.strip())
                db.save_letter(conn, new_id, draft)
                st.toast(f"Added {co} — {ro} to your Wishlist and saved the letter.")
                st.rerun()

# ---------------------------------------------------------------------------
# Assistant — chatbot that knows your search (runs on Ollama, no API key)
# ---------------------------------------------------------------------------
with tab_chat:
    st.subheader("Career Assistant")
    st.caption(
        "Ask about your applications, what to follow up on, interview prep or "
        "networking messages. It reads your tracker, and it runs on this computer "
        "through Ollama, so nothing leaves your Mac."
    )

    # The whole conversation lives in session_state as a list of
    # {"role": "user" | "assistant", "content": text}, so it survives reruns.
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    chat_models = [m for m in cl.ollama_models() if not m["cloud"]]
    if not chat_models:
        st.info("Open the Ollama app (free, ollama.com) and reload this page to chat.")
    else:
        names = [m["name"] for m in chat_models]
        saved = db.get_setting(conn, "cl_model", "")
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        chat_model = c1.selectbox(
            "Model", names, index=names.index(saved) if saved in names else 0,
            format_func=lambda n: f"{n} · {next(m['size_gb'] for m in chat_models if m['name'] == n)} GB",
            key="chat_model",
        )
        # Clear chat: empty the history and rerun so the page redraws empty.
        if c2.button("Clear chat", key="chat_clear", width="stretch",
                     disabled=not st.session_state.chat_messages):
            st.session_state.chat_messages = []
            st.rerun()

        if not st.session_state.chat_messages:
            st.caption("Try: \"What should I do this week?\" · \"Help me prep for my "
                       "Mansfield interview\" · \"Write a short thank-you note\"")

        # The conversation goes in this box, drawn above the input box.
        # st.chat_message gives user and assistant messages their own avatar and style.
        convo = st.container()
        for msg in st.session_state.chat_messages:
            with convo.chat_message(msg["role"]):
                st.markdown(msg["content"])

        prompt = st.chat_input("Ask Career Assistant…", key="chat_in")
        if prompt:
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            with convo.chat_message("user"):
                st.markdown(prompt)
            # System prompt is rebuilt each time, so it always has the latest data.
            system = assistant.system_prompt(df, db.load_tasks(conn))
            messages = assistant.build_messages(system, st.session_state.chat_messages)
            with convo.chat_message("assistant"):
                try:
                    reply = st.write_stream(assistant.stream_reply(chat_model, messages))
                except RuntimeError as e:
                    reply = None
                    st.error(str(e))
            if reply:
                st.session_state.chat_messages.append({"role": "assistant", "content": reply})
                st.rerun()  # redraw so the Clear button and hint update

# ---------------------------------------------------------------------------
# Settings — weekly target, sample data, clear all
# ---------------------------------------------------------------------------
with tab_set:
    st.subheader("Appearance")
    _look_now = "Dark" if styles.is_dark() else "Light"
    _look = st.segmented_control(
        "Theme", ["Light", "Dark", "Match my Mac"], default=_look_now,
        key="look_pick", help="Saved in this browser.",
    )
    if _look and _look != _look_now and not (_look == "Match my Mac" and st.session_state.get("look_sys")):
        st.session_state["look_sys"] = _look == "Match my Mac"
        styles.set_appearance("System" if _look == "Match my Mac" else _look)

    st.subheader("Weekly goal")
    goal_now = int(db.get_setting(conn, "weekly_goal", "10"))
    new_goal = st.number_input(
        "Target applications per week", min_value=1, value=goal_now, step=1,
        key="goal_input",
    )
    if new_goal != goal_now:
        db.set_setting(conn, "weekly_goal", str(new_goal))
        st.rerun()

    st.subheader("Follow-up nudges")
    stale_now = _stale_days
    new_stale = st.number_input(
        "Flag a job on the Board after this many days without moving",
        min_value=1, max_value=180, value=stale_now, step=1, key="stale_input",
        help="Applies to jobs in Applied, OA/Screen and Interview.",
    )
    if new_stale != stale_now:
        db.set_setting(conn, "stale_days", str(new_stale))
        st.rerun()

    st.subheader("Backup")
    st.caption(
        "One file with everything: jobs, stages, contacts, notes, to-dos, your saved "
        "resume and template, and these settings. Keep it somewhere safe, like iCloud Drive."
    )
    st.download_button(
        "Download backup", data=db.backup_bytes(conn),
        file_name=f"internship-tracker-backup-{_today_str}.db",
        mime="application/octet-stream", key="bk_dl",
    )
    with st.expander("Restore from a backup"):
        bk = st.file_uploader("Backup file (.db)", type=["db"], key="bk_up")
        sure = st.checkbox("Replace everything in the tracker with this backup", key="bk_sure")
        if st.button("Restore", disabled=bk is None or not sure, key="bk_go"):
            try:
                kept = db.restore_from_bytes(conn, bk.getvalue(),
                                             keep_copy_dir=db.DB_PATH.parent / "backups")
                st.session_state["bk_msg"] = (
                    "Restored. Your previous data was saved to "
                    f"data/backups/{Path(kept).name}." if kept else "Restored.")
                for k in ("mac_synced", "bk_sure"):
                    st.session_state.pop(k, None)
                st.rerun()
            except ValueError as e:
                st.error(str(e))
        if st.session_state.get("bk_msg"):
            st.success(st.session_state.pop("bk_msg"))

    st.subheader("Sample data")
    st.caption("Demo applications so a fresh copy has something to show. They are marked [sample].")
    if st.button("Load sample data"):
        n = db.load_sample_data(conn)
        st.info(f"Loaded {n} sample applications.")
        st.rerun()
    _df_check = db.load_applications(conn)
    if "is_sample" in _df_check.columns and _df_check["is_sample"].astype(bool).any():
        n_sample = int(_df_check["is_sample"].astype(bool).sum())
        if st.button(f"Remove sample data ({n_sample} rows)"):
            db.clear_sample_data(conn)
            st.rerun()

    st.subheader("Clear all data")
    st.caption("Deletes every application, stage and resume score in your local database.")
    _confirm = st.checkbox("I understand this cannot be undone")
    if st.button("Clear ALL data", disabled=not _confirm):
        db.clear_all_data(conn)
        st.rerun()
