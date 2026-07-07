"""
database.py — SQLite-backed job history and application tracker.

Replaces history.json with a proper database that supports:
  - Fast URL deduplication
  - Querying by status, score, company, date
  - Application tracking with notes
  - Favorites
  - No duplicates across daily runs

Usage:
    db = JobDatabase("output/jobs.db")
    new_jobs = db.filter_new(all_jobs)   # Only jobs not seen before
    db.upsert_many(all_jobs)             # Save/update all jobs
    db.mark_applied("https://...")       # Track an application
    db.mark_favorite("https://...")      # Star a job
"""

import sqlite3
import logging
from datetime import date
from pathlib import Path
from typing import List, Optional

from models import Job, JobRecord

logger = logging.getLogger(__name__)


CREATE_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS jobs (
    url         TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    company     TEXT NOT NULL,
    location    TEXT,
    source      TEXT,
    score       INTEGER DEFAULT 0,
    role_type   TEXT,
    work_type   TEXT,
    sector      TEXT,
    first_seen  TEXT NOT NULL,
    last_seen   TEXT NOT NULL,
    applied     INTEGER DEFAULT 0,
    favorite    INTEGER DEFAULT 0,
    status      TEXT DEFAULT 'new',
    notes       TEXT DEFAULT ''
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_status   ON jobs(status);",
    "CREATE INDEX IF NOT EXISTS idx_score    ON jobs(score DESC);",
    "CREATE INDEX IF NOT EXISTS idx_company  ON jobs(company);",
    "CREATE INDEX IF NOT EXISTS idx_seen     ON jobs(last_seen);",
]


class JobDatabase:
    def __init__(self, db_path: str = "output/jobs.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(CREATE_JOBS_TABLE)
            for idx in CREATE_INDEXES:
                conn.execute(idx)
        logger.debug(f"Database ready at {self.db_path}")

    # ------------------------------------------------------------------
    # CORE OPERATIONS
    # ------------------------------------------------------------------

    def filter_new(self, jobs: List[Job]) -> List[Job]:
        """
        Return only jobs whose URL has never been seen before.
        Use this to get a daily digest of genuinely new postings.
        """
        with self._connect() as conn:
            existing = {
                row["url"]
                for row in conn.execute("SELECT url FROM jobs")
            }
        new = [j for j in jobs if j.url not in existing]
        logger.info(f"filter_new: {len(jobs)} total → {len(new)} new")
        return new

    def upsert_many(self, jobs: List[Job]):
        """
        Insert new jobs or update last_seen for existing ones.
        Never creates duplicates.
        """
        today = date.today().isoformat()
        with self._connect() as conn:
            for job in jobs:
                conn.execute("""
                    INSERT INTO jobs
                        (url, title, company, location, source, score,
                         role_type, work_type, sector, first_seen, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(url) DO UPDATE SET
                        last_seen  = excluded.last_seen,
                        score      = excluded.score,
                        title      = excluded.title,
                        location   = excluded.location
                """, (
                    job.url, job.title, job.company, job.location,
                    job.source, job.score, job.role_type, job.work_type,
                    job.sector, today, today,
                ))
        logger.info(f"Upserted {len(jobs)} jobs into database")

    # ------------------------------------------------------------------
    # APPLICATION TRACKING
    # ------------------------------------------------------------------

    def mark_applied(self, url: str, notes: str = ""):
        """Mark a job as applied. Call this when you submit an application."""
        with self._connect() as conn:
            conn.execute("""
                UPDATE jobs
                SET applied = 1, status = 'applied', notes = ?
                WHERE url = ?
            """, (notes, url))
        logger.info(f"Marked as applied: {url}")

    def mark_favorite(self, url: str):
        """Star a job for easy filtering later."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE jobs SET favorite = 1 WHERE url = ?", (url,)
            )

    def update_status(self, url: str, status: str, notes: str = ""):
        """
        Update job status. Valid values:
          new | reviewed | applied | interviewing | rejected | offer
        """
        valid = {"new", "reviewed", "applied", "interviewing", "rejected", "offer"}
        if status not in valid:
            raise ValueError(f"Invalid status '{status}'. Choose from: {valid}")
        with self._connect() as conn:
            conn.execute(
                "UPDATE jobs SET status = ?, notes = ? WHERE url = ?",
                (status, notes, url)
            )

    def add_note(self, url: str, note: str):
        """Append a note to a job record."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE jobs SET notes = notes || ? WHERE url = ?",
                (f"\n{note}", url)
            )

    # ------------------------------------------------------------------
    # QUERIES
    # ------------------------------------------------------------------

    def get_new_today(self) -> List[dict]:
        """All jobs first seen today."""
        today = date.today().isoformat()
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE first_seen = ? ORDER BY score DESC",
                (today,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_applied(self) -> List[dict]:
        """All jobs you've applied to."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE applied = 1 ORDER BY last_seen DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_favorites(self) -> List[dict]:
        """All starred jobs."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE favorite = 1 ORDER BY score DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_top(self, limit: int = 20, min_score: int = 5) -> List[dict]:
        """Top scoring jobs you haven't applied to yet."""
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT * FROM jobs
                WHERE applied = 0 AND score >= ?
                ORDER BY score DESC, last_seen DESC
                LIMIT ?
            """, (min_score, limit)).fetchall()
        return [dict(r) for r in rows]

    def summary(self) -> dict:
        """Print a summary of your job search pipeline."""
        with self._connect() as conn:
            total    = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            new_     = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='new'").fetchone()[0]
            applied  = conn.execute("SELECT COUNT(*) FROM jobs WHERE applied=1").fetchone()[0]
            favs     = conn.execute("SELECT COUNT(*) FROM jobs WHERE favorite=1").fetchone()[0]
            today    = date.today().isoformat()
            today_ct = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE first_seen=?", (today,)
            ).fetchone()[0]
        return {
            "total_seen":    total,
            "new_today":     today_ct,
            "unreviewed":    new_,
            "applied":       applied,
            "favorites":     favs,
        }
