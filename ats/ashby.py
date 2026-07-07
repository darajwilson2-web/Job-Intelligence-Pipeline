"""
ats/ashby.py — Ashby job board fetcher.

Ashby is popular with Series A-C startups: OpenAI, Perplexity, Ramp, Brex, Deel.

Find a company's board token:
  Visit their careers page → look for jobs.ashbyhq.com/TOKEN in the URL
  Test: https://api.ashbyhq.com/posting-api/job-board/TOKEN
"""

import logging
import re

import requests

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0 (job-search-script/2.0)"}


def _clean_html(text: str) -> str:
    return re.sub(r"<[^<]+?>", " ", text or "")


def fetch_ashby_jobs(board_token: str) -> list[dict]:
    """
    Fetch all open jobs for one Ashby board token.
    Returns raw dicts — filtering and scoring happen in main.py.
    """
    url = f"https://api.ashbyhq.com/posting-api/job-board/{board_token}"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        if resp.status_code == 404:
            logger.warning(f"[Ashby:{board_token}] Not found — check token")
            return []
        if resp.status_code == 403:
            logger.warning(f"[Ashby:{board_token}] Access denied (403)")
            return []
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"[Ashby:{board_token}] Skipped: {e}")
        return []

    jobs = []
    for item in data.get("jobs", []):
        title    = item.get("title", "") or ""
        location = item.get("location", "") or ""
        description = _clean_html(
            item.get("descriptionHtml", "") or
            item.get("description", "") or ""
        )
        jobs.append({
            "source":      f"Ashby:{board_token}",
            "title":       title,
            "company":     board_token,
            "location":    location,
            "url":         item.get("jobUrl", ""),
            "description": description,
            "posted":      item.get("publishedAt", ""),
        })
    return jobs
