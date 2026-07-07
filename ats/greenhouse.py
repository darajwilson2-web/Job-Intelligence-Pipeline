"""
ats/greenhouse.py — Greenhouse job board fetcher.

Greenhouse is used by: Stripe, Affirm, Robinhood, Coinbase, GitLab,
Airbnb, Instacart, Asana, Elastic, Okta, Cloudflare, Datadog, HubSpot.

Find a company's board token:
  Visit their careers page → look for boards.greenhouse.io/TOKEN in the URL
  Test: https://boards-api.greenhouse.io/v1/boards/TOKEN/jobs
"""

import logging
import re

import requests

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0 (job-search-script/2.0)"}


def _clean_html(text: str) -> str:
    return re.sub(r"<[^<]+?>", " ", text or "")


def fetch_greenhouse_jobs(board_token: str) -> list[dict]:
    """
    Fetch all open jobs for one Greenhouse board token.
    Returns raw dicts — filtering and scoring happen in main.py.
    """
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15,
                            params={"content": "true"})
        if resp.status_code == 404:
            logger.warning(f"[Greenhouse:{board_token}] Not found — check token")
            return []
        if resp.status_code == 403:
            logger.warning(f"[Greenhouse:{board_token}] Access denied (403) — board may be private")
            return []
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"[Greenhouse:{board_token}] Skipped: {e}")
        return []

    jobs = []
    for item in data.get("jobs", []):
        title    = item.get("title", "") or ""
        location = (item.get("location") or {}).get("name", "")
        jobs.append({
            "source":      f"Greenhouse:{board_token}",
            "title":       title,
            "company":     board_token,
            "location":    location,
            "url":         item.get("absolute_url", ""),
            "description": _clean_html(item.get("content", "") or ""),
            "posted":      item.get("updated_at", ""),
        })
    return jobs
