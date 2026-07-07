"""
main.py — Job Intelligence Platform
=====================================
Fetches, scores, deduplicates, and exports remote job postings
across Compliance/Risk/Fraud, Executive Assistant, and Data Analytics roles.

HOW TO RUN:
    python main.py                    # Full run — fetch, score, export
    python main.py --new-only         # Only show jobs not seen before
    python main.py --top              # Show your top 20 unreviewed jobs
    python main.py --applied          # List all jobs you've applied to
    python main.py --mark-applied URL # Mark a job as applied
    python main.py --summary          # Pipeline summary stats

CONFIGURE:
    Edit config.yaml — no Python knowledge needed.
"""

import argparse
import logging
import sys
import yaml
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from models import Job
from database import JobDatabase
from filters import is_us_location, title_matches, contract_ok
from scoring import score_job, detect_role_type, detect_work_type, detect_sector
from exporters import export_csv, export_excel
from ats.greenhouse import fetch_greenhouse_jobs
from ats.lever import fetch_lever_jobs
from ats.ashby import fetch_ashby_jobs
from ats.workday import fetch_workday_jobs
from ats.common import fetch_remoteok, fetch_remotive, fetch_weworkremotely

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------
os.makedirs("output", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler("output/run.log", mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CONFIG LOADER
# ---------------------------------------------------------------------------
def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# CONCURRENT FETCHING
# ---------------------------------------------------------------------------
def fetch_all_jobs(cfg: dict) -> list[Job]:
    """
    Fetch from all sources concurrently using ThreadPoolExecutor.
    Network I/O is the bottleneck — parallelism cuts runtime from ~3 min to ~30s.
    """
    tasks = []

    # Public job boards
    tasks.append(("RemoteOK",         fetch_remoteok,         ()))
    tasks.append(("Remotive",         fetch_remotive,         (cfg.get("title_filters", []),)))
    tasks.append(("WeWorkRemotely",   fetch_weworkremotely,   ()))

    # Greenhouse
    for company in cfg.get("greenhouse_companies", []):
        tasks.append((f"Greenhouse:{company}", fetch_greenhouse_jobs, (company,)))

    # Lever
    for company in cfg.get("lever_companies", []):
        tasks.append((f"Lever:{company}", fetch_lever_jobs, (company,)))

    # Ashby
    for company in cfg.get("ashby_companies", []):
        tasks.append((f"Ashby:{company}", fetch_ashby_jobs, (company,)))

    # Workday
    for entry in cfg.get("workday_companies", []):
        name, subdomain, path = entry
        tasks.append((f"Workday:{name}", fetch_workday_jobs, (name, subdomain, path)))

    all_raw = []
    logger.info(f"Fetching from {len(tasks)} sources concurrently...")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(fn, *args): label
            for label, fn, args in tasks
        }
        for future in as_completed(futures):
            label = futures[future]
            try:
                results = future.result()
                if results:
                    logger.info(f"  {label}: {len(results)} postings")
                    all_raw.extend(results)
            except Exception as e:
                logger.warning(f"  {label}: failed — {e}")

    logger.info(f"Total raw postings fetched: {len(all_raw)}")
    return all_raw


# ---------------------------------------------------------------------------
# PROCESSING PIPELINE
# ---------------------------------------------------------------------------
def process_jobs(raw_jobs: list, cfg: dict) -> list[Job]:
    """Filter, deduplicate, score, and classify all raw job dicts."""
    title_filters  = cfg.get("title_filters", [])
    keyword_weights = cfg.get("keywords", {})
    min_score      = cfg.get("min_score", 3)
    include_contract = cfg.get("include_contract", True)

    seen_urls = set()
    jobs = []

    for raw in raw_jobs:
        url   = raw.get("url", "")
        title = raw.get("title", "") or ""
        desc  = raw.get("description", "") or ""
        loc   = raw.get("location", "") or ""

        # Deduplicate
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        # Filter
        if not title_matches(title, title_filters):
            continue
        if not is_us_location(loc, title, desc):
            continue
        if not contract_ok(title, desc, include_contract):
            continue

        # Score
        score, matched = score_job(title, desc, keyword_weights)
        if score < min_score:
            continue

        job = Job(
            title       = title,
            company     = raw.get("company", ""),
            url         = url,
            source      = raw.get("source", ""),
            location    = loc,
            description = desc[:2000],
            posted      = raw.get("posted", ""),
            score       = score,
            matched_keywords = matched,
            role_type   = detect_role_type(title),
            work_type   = detect_work_type(title, desc, loc),
            sector      = detect_sector(title, desc, raw.get("company", "")),
        )
        jobs.append(job)

    jobs.sort(key=lambda j: j.score, reverse=True)
    logger.info(f"After filtering and scoring: {len(jobs)} qualifying jobs")
    return jobs


# ---------------------------------------------------------------------------
# CLI COMMANDS
# ---------------------------------------------------------------------------
def cmd_summary(db: JobDatabase):
    s = db.summary()
    print("\n📊  Job Search Pipeline Summary")
    print(f"   Total jobs tracked:  {s['total_seen']}")
    print(f"   New today:           {s['new_today']}")
    print(f"   Unreviewed:          {s['unreviewed']}")
    print(f"   Applied:             {s['applied']}")
    print(f"   Favorites:           {s['favorites']}")


def cmd_top(db: JobDatabase, cfg: dict):
    jobs = db.get_top(limit=20, min_score=cfg.get("min_score", 3))
    print(f"\n⭐  Top {len(jobs)} unreviewed jobs:\n")
    for j in jobs:
        print(f"  [{j['score']:>2}] {j['title']} @ {j['company']}  ({j['work_type']})")
        print(f"       {j['url']}\n")


def cmd_applied(db: JobDatabase):
    jobs = db.get_applied()
    print(f"\n📬  {len(jobs)} applications submitted:\n")
    for j in jobs:
        status = j.get("status", "applied")
        print(f"  {j['title']} @ {j['company']}  [{status}]")
        print(f"  Applied: {j['last_seen']}  |  Notes: {j.get('notes','')}\n")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Job Intelligence Platform")
    parser.add_argument("--new-only",     action="store_true", help="Only show jobs not seen before")
    parser.add_argument("--top",          action="store_true", help="Show top unreviewed jobs from database")
    parser.add_argument("--applied",      action="store_true", help="List applied jobs")
    parser.add_argument("--summary",      action="store_true", help="Show pipeline summary")
    parser.add_argument("--mark-applied", metavar="URL",       help="Mark a job URL as applied")
    parser.add_argument("--notes",        metavar="TEXT",      help="Notes to attach when marking applied")
    parser.add_argument("--config",       default="config.yaml", help="Path to config file")
    args = parser.parse_args()

    cfg = load_config(args.config)
    db  = JobDatabase("output/jobs.db")

    # Quick commands — no fetching needed
    if args.summary:
        cmd_summary(db)
        return

    if args.top:
        cmd_top(db, cfg)
        return

    if args.applied:
        cmd_applied(db)
        return

    if args.mark_applied:
        db.mark_applied(args.mark_applied, notes=args.notes or "")
        print(f"✅  Marked as applied: {args.mark_applied}")
        return

    # --------------- FULL RUN ---------------
    logger.info("=" * 60)
    logger.info("Job Intelligence Platform — starting run")
    logger.info("=" * 60)

    # 1. Fetch concurrently
    raw_jobs = fetch_all_jobs(cfg)

    # 2. Filter, score, classify
    all_jobs = process_jobs(raw_jobs, cfg)

    # 3. Determine new vs seen
    new_jobs = db.filter_new(all_jobs)

    # 4. Save everything to database
    db.upsert_many(all_jobs)

    # 5. Export — use new_only or all depending on flag
    export_jobs = new_jobs if args.new_only else all_jobs
    today = datetime.now().strftime("%Y-%m-%d")

    csv_path   = f"output/jobs_{today}.csv"
    excel_path = f"output/jobs_{today}.xlsx"

    export_csv(export_jobs, csv_path)
    export_excel(export_jobs, excel_path)

    # 6. Summary
    role_counts   = Counter(j.role_type  for j in export_jobs)
    work_counts   = Counter(j.work_type  for j in export_jobs)
    sector_counts = Counter(j.sector     for j in export_jobs)
    db_summary    = db.summary()

    logger.info(f"\n{'='*60}")
    logger.info(f"Run complete — {len(export_jobs)} jobs exported")
    logger.info(f"  New today:    {len(new_jobs)}")
    logger.info(f"  Total in DB:  {db_summary['total_seen']}")
    logger.info(f"\nBy role type:")
    for k, v in role_counts.most_common():
        logger.info(f"  {k}: {v}")
    logger.info(f"\nBy work type:")
    for k, v in work_counts.most_common():
        logger.info(f"  {k}: {v}")
    logger.info(f"\nBy sector:")
    for k, v in sector_counts.most_common():
        logger.info(f"  {k}: {v}")
    logger.info(f"\nFiles saved:")
    logger.info(f"  {csv_path}")
    logger.info(f"  {excel_path}")
    logger.info(f"  output/jobs.db  (full history + tracker)")
    logger.info(f"\nTip: Run  python main.py --top  to see your best unreviewed matches")


if __name__ == "__main__":
    main()
