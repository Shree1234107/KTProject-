"""Internship Tracker & Dashboard Analyzer. Run: streamlit run app.py"""
import datetime as dt

import streamlit as st

from tracker import analytics, ats, db

st.set_page_config(page_title="Internship Tracker", page_icon="📋", layout="wide")
conn = db.connect()

st.title("📋 Internship Tracker")
tab_dash, tab_apps, tab_add, tab_ats = st.tabs(["Dashboard", "Applications", "Add", "Resume Matcher"])

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

with tab_ats:
    st.markdown(
        """<style>
        .chip{display:inline-block;padding:3px 12px;margin:3px 4px 3px 0;border-radius:999px;font-size:.85rem}
        .chip.ok{background:#dcfce7;color:#166534}.chip.miss{background:#ffedd5;color:#9a3412}
        </style>""",
        unsafe_allow_html=True,
    )
    st.header("Resume Matcher")
    st.caption("Upload a resume PDF and paste a job description. Estimates only, not a real ATS. Nothing is stored.")
    left, right = st.columns(2)
    pdf = left.file_uploader("Resume (PDF, max 5 MB)", type="pdf")
    use_demo = left.checkbox("Use the demo resume instead")
    if "ats_jd" not in st.session_state:
        st.session_state["ats_jd"] = ""
    if right.button("Load demo job description"):
        st.session_state["ats_jd"] = ats.sample_job_description()
    jd_text = right.text_area("Job description", key="ats_jd", height=260)

    if st.button("Analyze resume", type="primary"):
        try:
            if use_demo:
                result = ats.analyze_text(ats.sample_resume_text(), jd_text)
            elif pdf is not None:
                result = ats.analyze(pdf.getvalue(), jd_text)
            else:
                raise ValueError("Upload a resume PDF, or tick the demo resume.")
            st.session_state["ats_result"] = result
        except ValueError as e:
            st.session_state.pop("ats_result", None)
            st.error(str(e))

    res = st.session_state.get("ats_result")
    if res:
        st.divider()
        m = st.columns(3)
        m[0].metric("Overall match", f"{res['overall_score']:.0f} / 100")
        m[1].metric("Keyword coverage", f"{res['keyword_coverage_score']:.0f}%")
        m[2].metric("Content similarity", f"{res['cosine_similarity_score']:.0f}%")
        st.progress(min(int(res["overall_score"]), 100))
        st.subheader("Sections found")
        sc = st.columns(4)
        for col, (name, label) in zip(sc, [("summary", "Summary"), ("experience", "Experience"), ("education", "Education"), ("skills", "Skills")]):
            col.write(("✅ " if res["section_checks"][name] else "❌ ") + label)
        k1, k2 = st.columns(2)
        k1.subheader(f"Matched ({len(res['matched_keywords'])})")
        k1.markdown("".join(f'<span class="chip ok">{k}</span>' for k in res["matched_keywords"]) or "None", unsafe_allow_html=True)
        k2.subheader(f"Missing ({len(res['missing_keywords'])})")
        k2.markdown(
            "".join(f'<span class="chip miss">{i["keyword"]} ×{i["count"]}</span>' for i in res["missing_keywords"]) or "None",
            unsafe_allow_html=True,
        )
        st.subheader("Improvement tips")
        for tip in res["tips"] or ["Nothing to flag. Nice match."]:
            st.info(tip)
