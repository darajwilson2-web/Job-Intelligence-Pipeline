"""
ats/workday.py — Workday job board fetcher.

Workday uses dynamic subdomains: company.wd{1-12}.myworkdayjobs.com
We try wd1 through wd12 to find the right one.

Used by: Atrium Health, Novant Health, Humana, Aetna,
         Wells Fargo, Bank of America, Truist, Mecklenburg County.

Find a company's subdomain:
  Visit their careers page → note the subdomain before .myworkdayjobs.com
  e.g. atriumhealth.wd5.myworkdayjobs.com → subdomain is "atriumhealth"
"""

import logging

import requests

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent":   "Mozilla/5.0 (job-search-script/2.0)",
    "Content-Type": "application/json",
}

_SEARCH_PAYLOAD = {
    "limit":      20,
    "offset":     0,
    "searchText": "analyst coordinator assistant compliance fraud risk",
}


def fetch_workday_jobs(company_name: str, subdomain: str,
                       careers_path: str = "Careers") -> list[dict]:
    """
    Fetch jobs from a Workday board.
    Tries wd1 through wd12 to find the active subdomain.
    Returns raw dicts — filtering and scoring happen in main.py.
    """
    for n in range(1, 13):
        url = (
            f"https://{subdomain}.wd{n}.myworkdayjobs.com"
            f"/wday/cxs/{subdomain}/{careers_path}/jobs"
        )
        try:
            resp = requests.post(
                url,
                json=_SEARCH_PAYLOAD,
                headers=_HEADERS,
                timeout=10,
            )
            if resp.status_code in (400, 403, 404):
                continue
            resp.raise_for_status()
            data = resp.json()
            postings = data.get("jobPostings", [])
            if not postings:
                continue

            logger.info(f"[Workday:{company_name}] Found {len(postings)} postings (wd{n})")
            jobs = []
            for item in postings:
                title    = item.get("title", "") or ""
                location = item.get("locationsText", "") or ""
                ext_path = item.get("externalPath", "")
                job_url  = (
                    f"https://{subdomain}.wd{n}.myworkdayjobs.com{ext_path}"
                    if ext_path else url
                )
                jobs.append({
                    "source":      f"Workday:{company_name}",
                    "title":       title,
                    "company":     company_name,
                    "location":    location,
                    "url":         job_url,
                    "description": item.get("briefDescription", "") or "",
                    "posted":      item.get("postedOn", ""),
                })
            return jobs

        except Exception:
            continue  # Try next wd number

    logger.warning(f"[Workday:{company_name}] No active board found (tried wd1–wd12)")
    return []
