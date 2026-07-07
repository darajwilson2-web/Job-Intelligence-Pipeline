"""
ats/lever.py — Lever job board fetcher.

Lever is used by: Netflix, Palantir, Carta, Checkr, Samsara, Gusto.

Find a company's board token:
  Visit their careers page → look for jobs.lever.co/TOKEN in the URL
  Test: https://api.lever.co/v0/postings/TOKEN?mode=json
"""

import logging
import re

import requests

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0 (job-search-script/2.0)"}


def _clean_html(text: str) -> str:
    return re.sub(r"<[^<]+?>", " ", text or "")


def fetch_lever_jobs(board_token: str) -> list[dict]:
    """
    Fetch all open jobs for one Lever board token.
    Returns raw dicts — filtering and scoring happen in main.py.
    """
    url = f"https://api.lever.co/v0/postings/{board_token}"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15,
                            params={"mode": "json"})
        if resp.status_code == 404:
            logger.warning(f"[Lever:{board_token}] Not found — check token")
            return []
        if resp.status_code == 403:
            logger.warning(f"[Lever:{board_token}] Access denied (403) — board may be private")
            return []
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"[Lever:{board_token}] Skipped: {e}")
        return []

    jobs = []
    for item in data:
        title      = item.get("text", "") or ""
        categories = item.get("categories", {}) or {}
        location   = categories.get("location", "")
        description = _clean_html(
            item.get("descriptionPlain", "") or
            item.get("description", "") or ""
        )
        jobs.append({
            "source":      f"Lever:{board_token}",
            "title":       title,
            "company":     board_token,
            "location":    location,
            "url":         item.get("hostedUrl", ""),
            "description": description,
            "posted":      str(item.get("createdAt", "")),
        })
    return jobs
