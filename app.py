"""
app.py — Job Intelligence Dashboard
=====================================
Streamlit UI for the Job Intelligence Pipeline.

FIXES APPLIED:
  - Score display corrected (6-40 scale, normalized to 100 for display)
  - Area chart replaced with proper score distribution histogram
  - HTML stripped from job descriptions
  - Sector filter added to sidebar
  - Minimum score slider added
  - KPI metrics expanded to 5 cards (added Applied + Favorites)
  - Pagination added (25 jobs per page)
  - Description loaded lazily (only inside expander)
  - Connection opened/closed cleanly per operation

HOW TO RUN:
    pip install streamlit pandas
    streamlit run app.py
"""

import html
import os
import re
import sqlite3

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title = "Job Intelligence Dashboard",
    page_icon  = "💼",
    layout     = "wide",
    initial_sidebar_state = "expanded",
)

DB_PATH   = os.path.join("output", "jobs.db")
PAGE_SIZE = 25
MAX_SCORE = 40   # Actual peak score in dataset — used for normalization


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def get_conn():
    return sqlite3.connect(DB_PATH, timeout=10)


def ensure_schema():
    """
    Add any missing columns to the jobs table.
    Safe to run on every startup — only adds columns that don't exist.
    This handles databases created before the description column was added.
    """
    columns_to_add = [
        ("description",         "TEXT DEFAULT ''"),
        ("matched_keywords",    "TEXT DEFAULT ''"),
        ("status",              "TEXT DEFAULT 'new'"),
        ("notes",               "TEXT DEFAULT ''"),
        ("favorite",            "INTEGER DEFAULT 0"),
        ("applied",             "INTEGER DEFAULT 0"),
        ("source",              "TEXT DEFAULT ''"),
        ("sector",              "TEXT DEFAULT ''"),
        ("work_type",           "TEXT DEFAULT ''"),
        ("role_type",           "TEXT DEFAULT ''"),
    ]
    with get_conn() as conn:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
        for col_name, col_def in columns_to_add:
            if col_name not in existing:
                conn.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_def}")
                conn.commit()


def clean_description(text: str, max_chars: int = 500) -> str:
    """Strip HTML tags and entities from ATS job descriptions."""
    if not text:
        return "No description available."
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = " ".join(text.split())          # collapse whitespace
    return text[:max_chars] + ("..." if len(text) > max_chars else "")


def normalize_score(score, max_score=MAX_SCORE) -> int:
    """Convert raw keyword score to 0-100 scale for display."""
    if not score or max_score == 0:
        return 0
    return min(100, round((score / max_score) * 100))


def score_color(raw_score) -> str:
    """Return a color hex based on score band."""
    if raw_score >= 40: return "#D4AF37"   # gold  — elite
    if raw_score >= 30: return "#2196F3"   # blue  — high
    if raw_score >= 20: return "#4CAF50"   # green — medium
    return "#94A3B8"                        # gray  — low


def score_label(raw_score) -> str:
    if raw_score >= 40: return "★ Elite"
    if raw_score >= 30: return "High"
    if raw_score >= 20: return "Medium"
    return "Low"


def load_jobs(filters: dict) -> pd.DataFrame:
    """
    Load jobs from SQLite with filtering done at the SQL level.
    Only loads columns needed for the list view — not description.
    Description is fetched individually when user opens an expander.
    """
    conditions = ["1=1"]
    params     = []

    if filters.get("role_type") and filters["role_type"] != "All":
        conditions.append("role_type = ?")
        params.append(filters["role_type"])

    if filters.get("sector") and filters["sector"] != "All":
        conditions.append("sector = ?")
        params.append(filters["sector"])

    if filters.get("work_type") and filters["work_type"] != "All":
        conditions.append("work_type = ?")
        params.append(filters["work_type"])

    if filters.get("min_score", 0) > 0:
        conditions.append("CAST(score AS INTEGER) >= ?")
        params.append(filters["min_score"])

    if filters.get("pipeline") == "Applied":
        conditions.append("applied = 1")
    elif filters.get("pipeline") == "Not Applied":
        conditions.append("(applied = 0 OR applied IS NULL)")
    elif filters.get("pipeline") == "Favorites":
        conditions.append("favorite = 1")

    where = " AND ".join(conditions)
    query = f"""
        SELECT url, title, company, location, work_type, role_type,
               sector, score, applied, favorite, notes,
               first_seen, last_seen, source, status
        FROM jobs
        WHERE {where}
        ORDER BY CAST(score AS INTEGER) DESC
    """

    with get_conn() as conn:
        df = pd.read_sql_query(query, conn, params=params)

    # Keyword search in Python (SQLite LIKE on large text is slow)
    if filters.get("keyword"):
        kw = filters["keyword"].lower()
        mask = (
            df["title"].str.lower().str.contains(kw, na=False) |
            df["company"].str.lower().str.contains(kw, na=False)
        )
        df = df[mask]

    if "score" in df.columns:
        df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0)

    return df


def fetch_description(url: str) -> str:
    """
    Fetch description for a single job — only called when expander opens.
    Gracefully handles databases where the description column does not exist.
    """
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT description FROM jobs WHERE url = ?", (url,)
            ).fetchone()
        return clean_description(row[0] if row else "")
    except sqlite3.OperationalError:
        # Column doesn't exist in this database version — return placeholder
        return "Description not available in this database. Re-run main.py to populate descriptions."


def fetch_summary() -> dict:
    """Fetch dashboard KPI counts."""
    with get_conn() as conn:
        total     = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        applied   = conn.execute("SELECT COUNT(*) FROM jobs WHERE applied=1").fetchone()[0]
        favorites = conn.execute("SELECT COUNT(*) FROM jobs WHERE favorite=1").fetchone()[0]
        last_run  = conn.execute("SELECT MAX(first_seen) FROM jobs").fetchone()[0] or "—"
        # Dynamically find the top platform by job count
        top_platform_row = conn.execute("""
            SELECT SUBSTR(source, 1, INSTR(source || ':', ':') - 1) AS platform,
                   COUNT(*) as cnt
            FROM jobs
            WHERE source IS NOT NULL AND source != ''
            GROUP BY platform
            ORDER BY cnt DESC
            LIMIT 1
        """).fetchone()
        top_platform = top_platform_row[0] if top_platform_row else "N/A"
        top_platform_count = top_platform_row[1] if top_platform_row else 0
    return {
        "total":          total,
        "applied":        applied,
        "favorites":      favorites,
        "last_run":       str(last_run)[:10],
        "top_platform":   top_platform,
        "top_platform_ct":top_platform_count,
    }


def get_distinct(column: str) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT DISTINCT {column} FROM jobs WHERE {column} IS NOT NULL AND {column} != '' ORDER BY {column}"
        ).fetchall()
    return [r[0] for r in rows]


def save_job_state(url: str, applied: bool, favorite: bool, notes: str):
    """Write pipeline state changes back to SQLite."""
    status = "applied" if applied else "new"
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET applied=?, favorite=?, notes=?, status=? WHERE url=?",
            (int(applied), int(favorite), notes, status, url),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# CHARTS
# ---------------------------------------------------------------------------

def render_charts(df: pd.DataFrame):
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📍 Work Location Distribution**")
        if "work_type" in df.columns and not df.empty:
            wc = df["work_type"].value_counts().reset_index()
            wc.columns = ["Work Type", "Openings"]
            st.bar_chart(data=wc, x="Work Type", y="Openings", color="#0D9488")
        else:
            st.info("No work type data available.")

    with col2:
        st.markdown("**📊 Match Score Distribution**")
        if "score" in df.columns and not df.dropna(subset=["score"]).empty:
            # Bin scores into ranges for a proper histogram
            score_data = df["score"].dropna().astype(int)
            bins = pd.cut(score_data, bins=[0,10,20,30,40,100],
                         labels=["1-10","11-20","21-30","31-40","40+"],
                         right=True)
            dist = bins.value_counts().sort_index().reset_index()
            dist.columns = ["Score Range", "Jobs"]
            st.bar_chart(data=dist, x="Score Range", y="Jobs", color="#1565C0")
            st.caption(f"Scores range from {int(score_data.min())} to {int(score_data.max())}  ·  Avg: {score_data.mean():.1f}")
        else:
            st.info("No score data available.")


# ---------------------------------------------------------------------------
# JOB CARDS
# ---------------------------------------------------------------------------

STATUS_OPTIONS = ["new", "reviewed", "applied", "interviewing", "rejected", "offer"]


def render_job_card(row, idx: int):
    """Render a single job expander with pipeline controls."""
    company  = row.get("company", "Unknown")
    title    = row.get("title",   "Untitled")
    work_type= row.get("work_type","N/A")
    url      = row.get("url",     "")
    score    = int(row.get("score", 0))
    norm     = normalize_score(score)
    is_app   = bool(row.get("applied"))
    is_fav   = bool(row.get("favorite"))

    fav_badge = "⭐ " if is_fav else ""
    app_badge = "✅ " if is_app else ""
    band      = score_label(score)

    label = f"{fav_badge}{app_badge}🏢 {company} — 🎯 {title} ({work_type})  [{band} · {norm}/100]"

    with st.expander(label):
        left_col, right_col = st.columns([2, 1])

        with left_col:
            # Meta row
            st.markdown(
                f"**Category:** {row.get('role_type','N/A')}  ·  "
                f"**Sector:** {row.get('sector','General')}  ·  "
                f"**Source:** {row.get('source','')}"
            )
            st.markdown(
                f"**Location:** {row.get('location','N/A')}  ·  "
                f"**First Seen:** {str(row.get('first_seen',''))[:10]}  ·  "
                f"**Last Active:** {str(row.get('last_seen',''))[:10]}"
            )

            # Score display
            score_col1, score_col2 = st.columns([1, 3])
            with score_col1:
                st.markdown(
                    f"<div style='background:{score_color(score)};color:white;"
                    f"border-radius:8px;padding:12px;text-align:center;"
                    f"font-size:24px;font-weight:bold'>{norm}</div>"
                    f"<div style='text-align:center;font-size:11px;color:#666'>out of 100</div>",
                    unsafe_allow_html=True,
                )
            with score_col2:
                st.markdown(f"**{band} Match**")
                st.caption(
                    f"Raw keyword score: {score}  ·  "
                    f"Normalized to 100-point scale based on peak score of {MAX_SCORE}"
                )

            # Description — fetched lazily, HTML stripped
            st.markdown("**📄 Job Description:**")
            description = fetch_description(url)
            st.caption(description)

            if url:
                st.link_button("👉 Apply Now", url)

        with right_col:
            st.markdown("#### ⚙️ Pipeline Controls")
            current_notes = str(row.get("notes") or "")

            chk_app = st.checkbox(
                "✅ Mark as Applied",
                value=is_app,
                key=f"app_{idx}_{url[-20:]}",
            )
            chk_fav = st.checkbox(
                "⭐ Add to Favorites",
                value=is_fav,
                key=f"fav_{idx}_{url[-20:]}",
            )
            txt_notes = st.text_area(
                "Application Notes:",
                value=current_notes,
                height=100,
                placeholder="Recruiter name, interview date, contact info...",
                key=f"notes_{idx}_{url[-20:]}",
            )

            # Only write to DB if something changed
            if (chk_app != is_app) or (chk_fav != is_fav) or (txt_notes != current_notes):
                save_job_state(url, chk_app, chk_fav, txt_notes)
                st.toast(f"💾 Saved changes for {company}")
                st.rerun()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    st.title("💼 Job Intelligence Dashboard")
    st.caption("Browse, filter, track pipeline status, and view analytics from your daily job ingestion runs.")

    # Database check
    if not os.path.exists(DB_PATH):
        st.error(
            f"❌ Database not found at `{DB_PATH}`. "
            "Run `python main.py` to generate your job data."
        )
        return

    # Ensure all expected columns exist — safe migration
    try:
        ensure_schema()
    except Exception as e:
        st.warning(f"⚠️ Schema check warning: {e}")

    try:
        summary = fetch_summary()
    except Exception as e:
        st.error(f"💥 Could not connect to database: {e}")
        return

    # ── KPI CARDS ────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("📋 Total Jobs",    summary["total"])
    k2.metric("📬 Applied",       summary["applied"])
    k3.metric("⭐ Favorites",     summary["favorites"])
    k4.metric("🗓 Last Run",      summary["last_run"])
    k5.metric("🏆 Top Platform",  summary["top_platform"],
              delta=f"{summary['top_platform_ct']} jobs")
    st.divider()

    # ── SIDEBAR FILTERS ──────────────────────────────────────────────────
    with st.sidebar:
        st.header("🔍 Filter Jobs")

        keyword = st.text_input("Keyword search:", placeholder="fraud, SQL, remote, coinbase...")

        role_types = ["All"] + get_distinct("role_type")
        role_type  = st.selectbox("Role Type:", role_types)

        sectors    = ["All"] + get_distinct("sector")
        sector     = st.selectbox("Sector:", sectors)

        work_types = ["All"] + get_distinct("work_type")
        work_type  = st.selectbox("Work Type:", work_types)

        pipeline   = st.selectbox("Pipeline Status:", ["All", "Applied", "Not Applied", "Favorites"])

        st.divider()
        min_score  = st.slider("Minimum Score", 0, MAX_SCORE, 0,
                               help=f"Filter to jobs scoring at or above this threshold (max: {MAX_SCORE})")

        st.divider()
        st.caption("💡 Tips")
        st.caption("• Compliance/Risk/Fraud scores highest")
        st.caption("• Score 30+ = strong match")
        st.caption("• Click ✅ to track applications")
        st.caption("• Click ⭐ to save favorites")

    filters = {
        "keyword":   keyword,
        "role_type": role_type,
        "sector":    sector,
        "work_type": work_type,
        "pipeline":  pipeline,
        "min_score": min_score,
    }

    # ── LOAD & FILTER ────────────────────────────────────────────────────
    try:
        df = load_jobs(filters)
    except Exception as e:
        st.error(f"💥 Error loading jobs: {e}")
        return

    # ── CHARTS ───────────────────────────────────────────────────────────
    st.subheader("📊 Visual Analytics")
    render_charts(df)
    st.divider()

    # ── JOB LIST ─────────────────────────────────────────────────────────
    total_jobs = len(df)
    st.subheader(f"📋 Job Listings  ({total_jobs} matches)")

    if total_jobs == 0:
        st.warning("No jobs match your selected filters. Try broadening your search or lower the minimum score.")
        return

    # Pagination
    total_pages = max(1, (total_jobs + PAGE_SIZE - 1) // PAGE_SIZE)
    if total_pages > 1:
        page = st.number_input(
            f"Page (1–{total_pages})",
            min_value=1, max_value=total_pages, value=1,
        ) - 1
        st.caption(f"Showing {page*PAGE_SIZE+1}–{min((page+1)*PAGE_SIZE, total_jobs)} of {total_jobs} jobs")
    else:
        page = 0

    page_df = df.iloc[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]

    for idx, (_, row) in enumerate(page_df.iterrows()):
        render_job_card(row, page * PAGE_SIZE + idx)


if __name__ == "__main__":
    main()
