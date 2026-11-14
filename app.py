"""Internship Tracker & Dashboard Analyzer. Run: streamlit run app.py"""
import datetime as dt
import html as _html

import pandas as pd
import streamlit as st

from tracker import analytics, db, theme
from tracker.ats import ui as ats_ui

st.set_page_config(page_title="Internship Tracker", layout="wide")
theme.inject()

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
# Sidebar — sample data controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Sample & data")
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

    st.divider()
    _confirm = st.checkbox("I understand this cannot be undone")
    if st.button("Clear ALL data", disabled=not _confirm):
        db.clear_all_data(conn)
        st.rerun()

# ---------------------------------------------------------------------------
# Main tabs
# ---------------------------------------------------------------------------
st.title("Internship Tracker")
tab_dash, tab_board, tab_apps, tab_add, tab_rem, tab_ats = st.tabs(
    ["Dashboard", "Board", "Applications", "Add", "Reminders", "Resume Matcher"]
)

df = db.load_applications(conn)
_today = dt.date.today()
_today_str = str(_today)

# ---------------------------------------------------------------------------
# Shared HTML builders (called from Dashboard and Board tabs)
# ---------------------------------------------------------------------------

def _stat_tile(n: int, label: str, value: str, cur, prev, is_rate: bool) -> str:
    """Build one stat tile HTML string with trend indicator."""
    if cur is None or prev is None:
        trend_html = '<span class="trend-none">no trend yet</span>'
    else:
        diff = cur - prev
        if is_rate:
            mag = f"{abs(diff * 100):.1f}pp"
        else:
            mag = str(abs(int(round(diff))))
        if diff > 0:
            trend_html = f'<span class="trend-up">&#9650; {mag} vs prev 30d</span>'
        elif diff < 0:
            trend_html = f'<span class="trend-down">&#9660; {mag} vs prev 30d</span>'
        else:
            trend_html = f'<span class="trend-flat">&#8212; {mag} vs prev 30d</span>'
    return (
        f'<div class="stat-tile stat-tile-{n}">'
        f'<div class="stat-tile-label">{label}</div>'
        f'<div class="stat-tile-value">{value}</div>'
        f'<div class="stat-tile-trend">{trend_html}</div>'
        f'</div>'
    )


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
        ("Applied",    f["applied"],    "fn-c0", 100.0),
        ("Responded",  f["responded"],  "fn-c1", f["pct_responded"]  * 100),
        ("Interviewed",f["interviewed"],"fn-c2", f["pct_interviewed"] * 100),
        ("Offer",      f["offered"],    "fn-c3", f["pct_offered"]     * 100),
    ]
    convs = [
        f"{f['pct_responded']:.0%} of applied",
        f"{f['pct_interviewed']:.0%} of applied",
        f"{f['pct_offered']:.0%} of applied",
    ]

    p = ['<div class="funnel">']
    for i, (lbl, cnt, cls, pct) in enumerate(stages):
        # ensure at least a sliver for non-zero counts
        w = max(pct, 2.0) if cnt > 0 else 0.0
        p.append(
            f'<div class="funnel-step">'
            f'<div class="funnel-step-label">{lbl}</div>'
            f'<div class="funnel-bar-wrap">'
            f'<div class="funnel-bar {cls}" style="width:{w:.1f}%">{cnt}</div>'
            f'</div></div>'
        )
        if i < len(stages) - 1:
            p.append(f'<div class="funnel-conv">{convs[i]}</div>')
    p.append('</div>')
    return "".join(p)


def _goal_progress_html(wp: dict) -> str:
    """Build the weekly goal progress bar HTML."""
    pct = min(wp["count"] / wp["goal"] * 100, 100.0) if wp["goal"] > 0 else 0.0
    return (
        '<div class="goal-wrap">'
        f'<div class="goal-track"><div class="goal-fill" style="width:{pct:.1f}%"></div></div>'
        f'<div class="goal-label">{wp["count"]} of {wp["goal"]} this week</div>'
        '</div>'
    )


def _board_card_html(row, today_d: dt.date) -> str:
    """Build the HTML for a single board card (no buttons)."""
    days_ago_str = ""
    if pd.notna(row.date_applied):
        days_ago_str = f"{(today_d - row.date_applied.date()).days}d ago"

    deadline_str = ""
    if pd.notna(row.deadline):
        deadline_str = f"Due {row.deadline.strftime('%b %d')}"

    fu_str = ""
    if hasattr(row, "follow_up_date") and pd.notna(row.follow_up_date):
        fu_str = f"Follow up {row.follow_up_date.strftime('%b %d')}"

    meta = ", ".join(x for x in [row.location, days_ago_str] if x)
    dates = " · ".join(x for x in [deadline_str, fu_str] if x)

    return (
        '<div class="board-card">'
        f'<div class="board-card-company">{_html.escape(row.company)}</div>'
        f'<div class="board-card-role">{_html.escape(row.role)}</div>'
        + (f'<div class="board-card-meta">{_html.escape(meta)}</div>' if meta else "")
        + (f'<div class="board-card-dates">{_html.escape(dates)}</div>' if dates else "")
        + "</div>"
    )


def _render_board_cards(group: pd.DataFrame, status_name: str) -> None:
    """Render board cards (HTML + buttons) for a group of rows."""
    for row in group.itertuples():
        st.markdown(_board_card_html(row, _today), unsafe_allow_html=True)

        nxt = analytics.next_status(status_name)
        prv = analytics.prev_status(status_name)
        # Build button list: next (if applicable), reject (if not already rejected), back
        btns: list[tuple[str, str]] = []
        if nxt is not None:
            btns.append(("Next stage", f"nxt_{row.id}"))
        if status_name != "Rejected":
            btns.append(("Reject", f"rej_{row.id}"))
        if prv is not None:
            btns.append(("Back", f"bck_{row.id}"))

        if btns:
            bcols = st.columns(len(btns))
            for bc, (label, key) in zip(bcols, btns):
                if bc.button(label, key=key):
                    if label == "Next stage":
                        updates: dict = {"status": nxt}
                        if status_name == "Wishlist" and pd.isna(row.date_applied):
                            updates["date_applied"] = _today_str
                        db.update_application(conn, int(row.id), **updates)
                    elif label == "Reject":
                        db.update_application(conn, int(row.id), status="Rejected")
                    else:  # Back
                        db.update_application(conn, int(row.id), status=prv)
                    st.rerun()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
with tab_dash:
    if df.empty:
        st.info("No applications yet. Add one in the Add tab.")
    else:
        s = analytics.summary(df)
        pc = analytics.period_comparison(df, today=_today_str)
        c_now = pc["current"]
        c_prev = pc["previous"]

        # --- Feature 5: stat tile header row ---
        tiles = "".join([
            _stat_tile(1, "Total", str(s["total"]),
                       c_now["total"] if c_now else None,
                       c_prev["total"] if c_prev else None, False),
            _stat_tile(2, "Response rate", f"{s['response_rate']:.0%}",
                       c_now["response_rate"] if c_now else None,
                       c_prev["response_rate"] if c_prev else None, True),
            _stat_tile(3, "Interview rate", f"{s['interview_rate']:.0%}",
                       c_now["interview_rate"] if c_now else None,
                       c_prev["interview_rate"] if c_prev else None, True),
            _stat_tile(4, "Offers", str(s["offers"]),
                       c_now["offers"] if c_now else None,
                       c_prev["offers"] if c_prev else None, False),
            _stat_tile(5, "Active", str(s["active"]), None, None, False),
        ])
        st.markdown(f'<div class="stat-row">{tiles}</div>', unsafe_allow_html=True)

        # --- Feature 4: weekly goal ---
        with st.expander("Weekly goal", expanded=True):
            goal_stored = int(db.get_setting(conn, "weekly_goal", "10"))
            new_goal = st.number_input(
                "Target applications per week", min_value=1, value=goal_stored, step=1,
                key="goal_input",
            )
            if new_goal != goal_stored:
                db.set_setting(conn, "weekly_goal", str(new_goal))

            wp = analytics.weekly_progress(df, int(new_goal), today=_today_str)
            gs = analytics.goal_streak(df, int(new_goal), today=_today_str)
            st.markdown(_goal_progress_html(wp), unsafe_allow_html=True)
            st.markdown(
                f'<div class="goal-streak">'
                f'Current streak: <span class="goal-streak-num">{gs["current"]}</span> '
                f'week{"s" if gs["current"] != 1 else ""} &nbsp;·&nbsp; '
                f'Longest: <span class="goal-streak-num">{gs["longest"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # --- Existing pipeline + weekly chart ---
        left, right = st.columns(2)
        left.subheader("Pipeline")
        left.bar_chart(analytics.status_counts(df), color="#2563eb")
        right.subheader("Applications per week")
        weekly = analytics.applications_per_week(df)
        if weekly.empty:
            right.caption("Add application dates to see this chart.")
        else:
            right.line_chart(weekly, color="#2563eb")

        # --- Feature 2: heatmap ---
        st.subheader("Activity — last 26 weeks")
        apd = analytics.applications_per_day(df, today=_today_str)
        st.markdown(_heatmap_html(apd, _today), unsafe_allow_html=True)

        # --- Feature 3: funnel ---
        st.subheader("Pipeline funnel")
        st.markdown(_funnel_html(analytics.funnel(df)), unsafe_allow_html=True)

        # --- Existing: by source, referred vs cold, deadlines ---
        st.subheader("Where are responses coming from?")
        src = analytics.by_source(df)
        if src.empty:
            st.caption("Add a source to applications to see this.")
        else:
            st.dataframe(src, use_container_width=True, hide_index=True)

        st.subheader("Referred vs. Cold")
        rc = analytics.referral_comparison(df)
        if rc["referred"]["submitted"] == 0 and rc["cold"]["submitted"] == 0:
            st.caption("No referral data yet — add a referral name when logging applications.")
        else:
            rc_rows = []
            for label, g in [("Referred", rc["referred"]), ("Cold", rc["cold"])]:
                rc_rows.append({
                    "Type": label,
                    "Applications": g["count"],
                    "Submitted": g["submitted"],
                    "Response rate": f"{g['response_rate']:.0%}",
                    "Interview rate": f"{g['interview_rate']:.0%}",
                })
            st.dataframe(pd.DataFrame(rc_rows), use_container_width=True, hide_index=True)

        st.subheader("Deadlines in the next 14 days")
        dl = analytics.upcoming_deadlines(df)
        if dl.empty:
            st.caption("Nothing due soon.")
        else:
            st.dataframe(dl, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Board (Kanban)
# ---------------------------------------------------------------------------
with tab_board:
    df_board = db.load_applications(conn)
    BOARD_COLS = ["Wishlist", "Applied", "OA/Screen", "Interview", "Offer", "Rejected"]

    if df_board.empty:
        st.info("No applications yet. Add one in the Add tab.")
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
                    use_container_width=True,
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
        st.dataframe(view, use_container_width=True, hide_index=True)

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
        new_applied     = eb.date_input("Date applied",      value=_to_date(cur.get("date_applied")),  key=f"da{choice}")
        new_deadline    = ea.date_input("Deadline",          value=_to_date(cur.get("deadline")),       key=f"dl{choice}")
        new_ref_name    = eb.text_input("Referral name",     cur.get("referral_name", ""), key=f"rn{choice}")
        new_ref_contact = ea.text_input("Referral contact",  cur.get("referral_contact", ""), key=f"rc{choice}")
        new_follow_up   = eb.date_input("Follow-up date",    value=_to_date(cur.get("follow_up_date")), key=f"fu{choice}")
        new_notes       = st.text_area("Notes",              cur.get("notes", ""),         key=f"no{choice}")

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
        notes       = st.text_area("Notes")
        if st.form_submit_button("Add application"):
            try:
                db.add_application(
                    conn, company, role, location, status, applied, deadline, source, notes,
                    referral_name=ref_name,
                    referral_contact=ref_contact,
                    follow_up_date=str(follow_up) if follow_up else None,
                )
                st.success("Added!")
                st.rerun()
            except ValueError as e:
                st.error(f"Error: {e}")

# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------
with tab_rem:
    rem = analytics.reminders(df, today=_today_str)
    stale = analytics.stale_applications(df, today=_today_str)

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
                        st.rerun()
                    if c4.button("+3d", key=f"s3_{row.id}"):
                        db.update_application(conn, int(row.id),
                                              follow_up_date=str(_today + dt.timedelta(days=3)))
                        st.rerun()
                    if c5.button("+7d", key=f"s7_{row.id}"):
                        db.update_application(conn, int(row.id),
                                              follow_up_date=str(_today + dt.timedelta(days=7)))
                        st.rerun()

        if not stale.empty:
            st.subheader(f"No reply after 21+ days ({len(stale)})")
            st.dataframe(
                stale[["company", "role", "days_waiting"]].rename(
                    columns={"days_waiting": "Days waiting"}),
                use_container_width=True,
                hide_index=True,
            )

# ---------------------------------------------------------------------------
# Resume Matcher
# ---------------------------------------------------------------------------
with tab_ats:
    ats_ui.render()
