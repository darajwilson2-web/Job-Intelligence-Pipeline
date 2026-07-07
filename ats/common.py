"""
ats/common.py — Public job board fetchers.
These boards require no API key or login.

Sources:
  - RemoteOK        (remoteok.com/api)
  - Remotive        (remotive.com/api/remote-jobs)
  - WeWorkRemotely  (weworkremotely.com RSS feeds)
"""

import logging
import re

import requests

logger = logging.getLogger(__name__)

try:
    import feedparser
    _FEEDPARSER_AVAILABLE = True
except ImportError:
    _FEEDPARSER_AVAILABLE = False
    logger.warning("feedparser not installed — WeWorkRemotely will be skipped. Run: pip install feedparser")

_HEADERS = {"User-Agent": "Mozilla/5.0 (job-search-script/2.0)"}


def _clean_html(text: str) -> str:
    return re.sub(r"<[^<]+?>", " ", text or "")


# ---------------------------------------------------------------------------
# REMOTEOK
# ---------------------------------------------------------------------------

def fetch_remoteok() -> list[dict]:
    """RemoteOK public API — no key required."""
    jobs = []
    try:
        resp = requests.get(
            "https://remoteok.com/api",
            headers=_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"[RemoteOK] Skipped: {e}")
        return jobs

    for item in data[1:]:  # First item is metadata
        title = item.get("position", "") or ""
        if not title:
            continue
        jobs.append({
            "source":      "RemoteOK",
            "title":       title,
            "company":     item.get("company", ""),
            "location":    item.get("location", "Remote"),
            "url":         item.get("url", ""),
            "description": _clean_html(item.get("description", "") or ""),
            "posted":      item.get("date", ""),
        })
    return jobs


# ---------------------------------------------------------------------------
# REMOTIVE
# ---------------------------------------------------------------------------

def fetch_remotive(title_filters: list[str] | None = None) -> list[dict]:
    """
    Remotive public API.
    Runs multiple searches to cover all target role categories.
    """
    title_filters = title_filters or []
    jobs = []

    search_terms = [
        # Primary: Compliance / Risk / Fraud
        "fraud analyst",
        "compliance analyst",
        "risk analyst",
        # Secondary: EA / Business Partner
        "executive assistant",
        "chief of staff",
        # Data / Analytics
        "data analyst",
        "operations analyst",
        "business operations",
        # Coordinator
        "project coordinator",
    ]

    seen_urls: set[str] = set()

    for term in search_terms:
        try:
            resp = requests.get(
                "https://remotive.com/api/remote-jobs",
                params={"search": term},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"[Remotive:{term}] Skipped: {e}")
            continue

        for item in data.get("jobs", []):
            url = item.get("url", "")
            if url in seen_urls:
                continue
            seen_urls.add(url)

            title = item.get("title", "") or ""
            jobs.append({
                "source":      "Remotive",
                "title":       title,
                "company":     item.get("company_name", ""),
                "location":    item.get("candidate_required_location", "Remote"),
                "url":         url,
                "description": _clean_html(item.get("description", "") or ""),
                "posted":      item.get("publication_date", ""),
            })

    return jobs


# ---------------------------------------------------------------------------
# WE WORK REMOTELY
# ---------------------------------------------------------------------------

def fetch_weworkremotely() -> list[dict]:
    """WeWorkRemotely RSS feeds — pulls from multiple categories."""
    if not _FEEDPARSER_AVAILABLE:
        return []

    feeds = [
        "https://weworkremotely.com/categories/remote-data-analytics-jobs.rss",
        "https://weworkremotely.com/categories/remote-management-finance-jobs.rss",
        "https://weworkremotely.com/categories/remote-executive-assistant-jobs.rss",
    ]

    jobs = []
    seen_urls: set[str] = set()

    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            logger.warning(f"[WeWorkRemotely] Skipped {feed_url}: {e}")
            continue

        for entry in feed.entries:
            url = entry.get("link", "")
            if url in seen_urls:
                continue
            seen_urls.add(url)

            jobs.append({
                "source":      "WeWorkRemotely",
                "title":       entry.get("title", "") or "",
                "company":     "",
                "location":    "Remote",
                "url":         url,
                "description": _clean_html(entry.get("summary", "") or ""),
                "posted":      entry.get("published", ""),
            })

    return jobs
