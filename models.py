"""
models.py — Typed data structures for the job fetcher.
Using dataclasses means typos in field names raise errors immediately
instead of silently producing empty columns.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Job:
    # Core fields — required
    title:       str
    company:     str
    url:         str
    source:      str

    # Optional fields with defaults
    location:    str = ""
    description: str = ""
    posted:      str = ""

    # Computed fields — filled in by scoring/detection
    score:           int   = 0
    matched_keywords: list = field(default_factory=list)
    role_type:       str   = ""
    work_type:       str   = ""
    sector:          str   = ""

    # Truncate description for CSV export
    @property
    def description_short(self) -> str:
        return self.description[:2000]

    def to_dict(self) -> dict:
        """Convert to flat dict for CSV/Excel export."""
        return {
            "Score":            self.score,
            "Role Type":        self.role_type,
            "Work Type":        self.work_type,
            "Sector":           self.sector,
            "Title":            self.title,
            "Company":          self.company,
            "Location":         self.location,
            "Source":           self.source,
            "Matched Keywords": ", ".join(self.matched_keywords),
            "Posted":           self.posted,
            "URL":              self.url,
            "Description":      self.description_short,
        }


@dataclass
class JobRecord:
    """
    Persistent record stored in SQLite.
    Tracks a job's full lifecycle — from first seen to applied.
    """
    url:        str
    title:      str
    company:    str
    location:   str
    source:     str
    score:      int
    role_type:  str
    work_type:  str
    sector:     str

    # Tracking fields
    first_seen: str = field(default_factory=lambda: date.today().isoformat())
    last_seen:  str = field(default_factory=lambda: date.today().isoformat())
    applied:    bool = False
    favorite:   bool = False
    status:     str  = "new"   # new | reviewed | applied | rejected | offer
    notes:      str  = ""

    @classmethod
    def from_job(cls, job: Job) -> "JobRecord":
        """Create a JobRecord from a scored Job."""
        return cls(
            url       = job.url,
            title     = job.title,
            company   = job.company,
            location  = job.location,
            source    = job.source,
            score     = job.score,
            role_type = job.role_type,
            work_type = job.work_type,
            sector    = job.sector,
        )
