# Job Intelligence Platform

Finds, scores, and tracks Compliance/Risk/Fraud, Executive Assistant,
and Data Analytics remote job postings — automatically, daily.

## What's New vs the Original Scripts

| Old | New |
|-----|-----|
| Same 200 jobs every day | `history.json` → **SQLite** tracks seen jobs — only new ones shown |
| Edit Python to change keywords | Edit **`config.yaml`** — no code needed |
| ~3 min runtime | **Concurrent fetching** — ~30 seconds |
| CSV only | **CSV + color-coded Excel** |
| Plain dicts | **Typed `Job` dataclass** — catches bugs early |
| `print()` everywhere | **Structured logging** to console + file |
| No application tracking | **SQLite tracker** — mark applied, favorite, add notes |

## Setup (one time)

```bash
pip install -r requirements.txt
```

## Daily Usage

```bash
# Full run — fetch everything, show all qualifying jobs
python main.py

# Only show jobs you haven't seen before
python main.py --new-only

# Show your top 20 unreviewed jobs from the database
python main.py --top

# Pipeline summary — how many seen, applied, favorites
python main.py --summary
```

## Application Tracking

```bash
# Mark a job as applied
python main.py --mark-applied "https://job-boards.greenhouse.io/affirm/jobs/..."

# Mark applied with notes
python main.py --mark-applied "https://..." --notes "Submitted via LinkedIn, referral from Jane"

# See all jobs you've applied to
python main.py --applied
```

## Customizing Your Search

Open `config.yaml` and edit:

- `title_filters` — job titles to search for
- `keywords` — scoring weights (higher = more important)
- `min_score` — raise to see fewer, more relevant results
- `greenhouse_companies` / `lever_companies` / `ashby_companies` — companies to track

**You never need to touch any Python files.**

## Output Files

| File | Description |
|------|-------------|
| `output/jobs_YYYY-MM-DD.csv` | Today's results |
| `output/jobs_YYYY-MM-DD.xlsx` | Color-coded Excel version |
| `output/jobs.db` | SQLite database — full history + tracker |
| `output/run.log` | Detailed log of every run |

## Project Structure

```
job_fetcher/
├── main.py          # Entry point — orchestrates everything
├── config.yaml      # Your search preferences — edit this
├── models.py        # Job dataclass
├── database.py      # SQLite history + application tracker
├── filters.py       # Location, title, contract filtering
├── scoring.py       # Keyword scoring + role/sector detection
├── exporters.py     # CSV + Excel export
├── requirements.txt
├── README.md
└── ats/
    ├── common.py    # RemoteOK, Remotive, WeWorkRemotely
    ├── greenhouse.py
    ├── lever.py
    ├── ashby.py
    └── workday.py
```

## Automate Daily (Windows Task Scheduler)

Set Task Scheduler to run daily at 7 AM:
- Program: path to `python.exe`
- Arguments: `path\to\job_fetcher\main.py --new-only`
- Start in: `path\to\job_fetcher\`
