"""Internship Tracker & Dashboard Analyzer. Run: streamlit run app.py"""
import datetime as dt

import streamlit as st

from tracker import analytics, db

st.set_page_config(page_title="Internship Tracker", page_icon="📋", layout="wide")
conn = db.connect()

st.title("📋 Internship Tracker")
tab_dash, tab_apps, tab_add = st.tabs(["Dashboard", "Applications", "Add"])

df = db.load_applications(conn)

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
        st.subheader("Deadlines in the next 14 days")
        dl = analytics.upcoming_deadlines(df)
        st.dataframe(dl, use_container_width=True, hide_index=True) if not dl.empty else st.caption("Nothing due soon.")

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
        new_status = st.selectbox("Status", db.STATUSES, index=db.STATUSES.index(cur["status"]), key=f"s{choice}")
        new_notes = st.text_area("Notes", cur["notes"], key=f"n{choice}")
        b1, b2, _ = st.columns([1, 1, 6])
        if b1.button("Save"):
            db.update_application(conn, int(choice), status=new_status, notes=new_notes)
            st.rerun()
        if b2.button("Delete"):
            db.delete_application(conn, int(choice))
            st.rerun()

with tab_add:
    with st.form("add", clear_on_submit=True):
        a, b = st.columns(2)
        company = a.text_input("Company *")
        role = b.text_input("Role *")
        location = a.text_input("Location")
        source = b.text_input("Source (LinkedIn, referral, career fair...)")
        status = a.selectbox("Status", db.STATUSES, index=1)
        applied = b.date_input("Date applied", dt.date.today())
        deadline = a.date_input("Deadline", value=None)
        notes = st.text_area("Notes")
        if st.form_submit_button("Add application"):
            try:
                db.add_application(conn, company, role, location, status, applied, deadline, source, notes)
                st.success("Added!")
                st.rerun()
            except ValueError as e:
                st.error(str(e))
