"""Internship Tracker & Dashboard Analyzer. Run: streamlit run app.py"""
import datetime as dt

import pandas as pd
import streamlit as st

from tracker import analytics, db
from tracker.ats import ui as ats_ui

st.set_page_config(page_title="Internship Tracker", page_icon="📋", layout="wide")
conn = db.connect()


def _to_date(ts):
    """pandas Timestamp/NaT → Python date or None (for st.date_input)."""
    try:
        if ts is None or pd.isna(ts):
            return None
    except (TypeError, ValueError):
        pass
    return ts.date() if hasattr(ts, "date") else ts


st.title("📋 Internship Tracker")
tab_dash, tab_apps, tab_add, tab_rem, tab_ats = st.tabs(
    ["Dashboard", "Applications", "Add", "Reminders", "Resume Matcher"]
)

df = db.load_applications(conn)

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
with tab_dash:
    if df.empty:
        st.info("No applications yet. Add one in the Add tab.")
    else:
        s = analytics.summary(df)
        c = st.columns(5)
        c[0].metric("Total", s["total"])
        c[1].metric("Active", s["active"])
        c[2].metric("Response rate", f"{s['response_rate']:.0%}")
        c[3].metric("Interview rate", f"{s['interview_rate']:.0%}")
        c[4].metric("Offers", s["offers"])
        left, right = st.columns(2)
        left.subheader("Pipeline")
        left.bar_chart(analytics.status_counts(df))
        right.subheader("Applications per week")
        weekly = analytics.applications_per_week(df)
        if weekly.empty:
            right.caption("Add application dates to see this chart.")
        else:
            right.line_chart(weekly)
        st.subheader("Where are responses coming from?")
        src = analytics.by_source(df)
        st.dataframe(src, use_container_width=True, hide_index=True) if not src.empty else st.caption("Add a source to applications to see this.")

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
        st.dataframe(dl, use_container_width=True, hide_index=True) if not dl.empty else st.caption("Nothing due soon.")

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
                st.error("Company and role cannot be empty.")
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
                st.error(str(e))

# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------
with tab_rem:
    _today = dt.date.today()
    rem = analytics.reminders(df, today=str(_today))
    stale = analytics.stale_applications(df, today=str(_today))

    _has_any = any(not v.empty for v in rem.values()) or not stale.empty
    if not _has_any:
        st.info("No follow-ups scheduled.")
    else:
        for section_key, label in [("overdue", "⚠️ Overdue"), ("due_today", "📅 Due today"), ("upcoming", "🔜 Upcoming (next 14 days)")]:
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
                    if c3.button("✅ Done", key=f"done_{row.id}"):
                        db.update_application(conn, int(row.id), follow_up_date=None)
                        st.rerun()
                    if c4.button("⏩ +3d", key=f"s3_{row.id}"):
                        new_fu = str((_today + dt.timedelta(days=3)))
                        db.update_application(conn, int(row.id), follow_up_date=new_fu)
                        st.rerun()
                    if c5.button("⏩ +7d", key=f"s7_{row.id}"):
                        new_fu = str((_today + dt.timedelta(days=7)))
                        db.update_application(conn, int(row.id), follow_up_date=new_fu)
                        st.rerun()

        if not stale.empty:
            st.subheader(f"🕐 No reply after 21+ days ({len(stale)})")
            st.dataframe(
                stale[["company", "role", "days_waiting"]].rename(columns={"days_waiting": "Days waiting"}),
                use_container_width=True,
                hide_index=True,
            )

# ---------------------------------------------------------------------------
# Resume Matcher
# ---------------------------------------------------------------------------
with tab_ats:
    ats_ui.render()
