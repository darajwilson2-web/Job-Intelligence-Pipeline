


import streamlit as st
import pandas as pd
import sqlite3
import os

# Set page layout to wide
st.set_page_config(page_title="Job Intelligence Dashboard", layout="wide")

st.title("💼 Job Intelligence Dashboard")
st.markdown("Browse, filter, track pipeline status, and view metrics from your daily runs.")

db_path = os.path.join("output", "jobs.db")

if not os.path.exists(db_path):
    st.error(f"❌ Database not found at `{db_path}`. Please run your scraper first to generate your job data.")
else:
    try:
        # Connect to the local SQLite database
        conn = sqlite3.connect(db_path, timeout=10)
        df = pd.read_sql_query("SELECT * FROM jobs", conn)
        conn.close()

        # Handle formatting data types
        if "score" in df.columns:
            df["score"] = pd.to_numeric(df["score"], errors="coerce")
        if "first_seen" in df.columns:
            df = df.sort_values(by="first_seen", ascending=False)

        # --- SIDEBAR FILTERS ---
        st.sidebar.header("🔍 Filter Jobs")
        search_query = st.sidebar.text_input("Search keywords (Title, Company, Description):", "")

        role_options = ["All"] + list(df["role_type"].dropna().unique()) if "role_type" in df.columns else ["All"]
        selected_role = st.sidebar.selectbox("Role Type:", role_options)

        work_options = ["All"] + list(df["work_type"].dropna().unique()) if "work_type" in df.columns else ["All"]
        selected_work = st.sidebar.selectbox("Work Type:", work_options)

        status_options = ["All", "Applied", "Not Applied", "Favorite"]
        selected_status = st.sidebar.selectbox("Pipeline Status:", status_options)

        # --- FILTER LOGIC ---
        filtered_df = df.copy()
        if selected_role != "All":
            filtered_df = filtered_df[filtered_df["role_type"] == selected_role]
        if selected_work != "All":
            filtered_df = filtered_df[filtered_df["work_type"] == selected_work]
        if selected_status == "Applied":
            filtered_df = filtered_df[filtered_df["applied"] == 1]
        elif selected_status == "Not Applied":
            filtered_df = filtered_df[(filtered_df["applied"] == 0) | (filtered_df["applied"].isna())]
        elif selected_status == "Favorite":
            filtered_df = filtered_df[filtered_df["favorite"] == 1]

        if search_query:
            filtered_df = filtered_df[
                filtered_df["title"].str.contains(search_query, case=False, na=False) |
                filtered_df["company"].str.contains(search_query, case=False, na=False) |
                filtered_df["description"].str.contains(search_query, case=False, na=False)
                ]

        # --- MAIN METRICS VISUALS ---
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Matched Jobs", len(df))
        col2.metric("Filtered Matches", len(filtered_df))

        latest_date = df["first_seen"].max() if "first_seen" in df.columns and not df.empty else "2026-07-07"
        col3.metric("Latest Run Date", str(latest_date))

        st.markdown("---")

        # --- ADVANCED ANALYTICS SECTION ---
        st.subheader("📊 Visual Analytics")
        a_col1, a_col2 = st.columns(2)

        with a_col1:
            if "work_type" in filtered_df.columns and not filtered_df.empty:
                work_counts = filtered_df["work_type"].value_counts().reset_index()
                work_counts.columns = ["Work Type", "Openings"]
                st.markdown("**Distribution of Work Location Strategy**")
                st.bar_chart(data=work_counts, x="Work Type", y="Openings", color="#2e7d32")
            else:
                st.info("No work type metrics available.")

        with a_col2:
            if "score" in filtered_df.columns and not filtered_df.dropna(subset=["score"]).empty:
                st.markdown("**Match Quality Score Spread (Targeting >70)**")
                score_df = filtered_df.dropna(subset=["score"])
                st.area_chart(data=score_df, y="score", color="#1565c0")
            else:
                st.info("No AI match score distributions available yet.")

        st.markdown("---")

        # --- JOB LISTINGS DISPLAY ---
        st.subheader("📋 Core Postings & Pipeline Update Portal")
        if filtered_df.empty:
            st.warning("No jobs match your selected filters.")
        else:
            for idx, row in filtered_df.iterrows():
                company = row.get('company', 'Unknown Company')
                title = row.get('title', 'Untitled Position')
                work_type = row.get('work_type', 'N/A')
                job_url = row.get('url', '')

                # Dynamic title tags based on state
                fav_badge = "⭐ " if row.get('favorite') == 1 else ""
                app_badge = "✅ [Applied] " if row.get('applied') == 1 else ""

                with st.expander(f"{fav_badge}{app_badge}🏢 {company} — 🎯 {title} ({work_type})"):
                    m_col1, m_col2 = st.columns([2, 1])

                    with m_col1:
                        st.markdown(
                            f"**Category:** {row.get('role_type', 'N/A')} | **Sector:** {row.get('sector', 'General')}")
                        st.markdown(
                            f"**First Detected:** {row.get('first_seen', 'N/A')} | **Last Active:** {row.get('last_seen', 'N/A')}")
                        if 'score' in row and pd.notna(row['score']):
                            st.markdown(f"🎯 **AI Optimization Score:** `{row['score']}/100`")

                        st.markdown("**Job Description Excerpt:**")
                        desc_text = row.get('description', 'No description available.')
                        st.caption(desc_text if len(desc_text) < 500 else desc_text[:500] + "...")

                        if job_url:
                            st.link_button("👉 Launch Application Portal", job_url)

                    with m_col2:
                        st.markdown("#### Pipeline Actions")

                        # Use database states as defaults
                        is_applied = bool(row.get('applied'))
                        is_fav = bool(row.get('favorite'))
                        current_notes = str(row.get('notes') or "")

                        # Interactive components
                        chk_app = st.checkbox("Mark as Applied", value=is_applied, key=f"app_{job_url}_{idx}")
                        chk_fav = st.checkbox("Add to Favorites", value=is_fav, key=f"fav_{job_url}_{idx}")
                        txt_notes = st.text_input("Application Notes:", value=current_notes,
                                                  key=f"note_{job_url}_{idx}")

                        # Check if state has shifted to execute database save
                        if (chk_app != is_applied) or (chk_fav != is_fav) or (txt_notes != current_notes):
                            conn = sqlite3.connect(db_path)
                            c = conn.cursor()
                            c.execute(
                                """
                                UPDATE jobs 
                                SET applied = ?, favorite = ?, notes = ? 
                                WHERE url = ?
                                """,
                                (1 if chk_app else 0, 1 if chk_fav else 0, txt_notes, job_url)
                            )
                            conn.commit()
                            conn.close()
                            st.toast(f"💾 Changes for {company} synchronized!")
                            st.rerun()

    except Exception as e:
        st.error(f"💥 Dashboard Rendering Error: {e}")