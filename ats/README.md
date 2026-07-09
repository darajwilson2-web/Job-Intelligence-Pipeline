<div align="center">

<img src="docs/images/banner.svg" alt="Job Intelligence Pipeline" width="100%">

<br><br>

![Tests](https://img.shields.io/badge/Tests-69%20Passing-0D9488?style=flat-square)
![ATS Score](https://img.shields.io/badge/ATS%20Score-100%25-1A365D?style=flat-square)
![Sources](https://img.shields.io/badge/Job%20Sources-30%2B-0D9488?style=flat-square)
![Platforms](https://img.shields.io/badge/ATS%20Platforms-4-1A365D?style=flat-square)
![Schedule](https://img.shields.io/badge/Auto%20Run-7%20AM%20Daily-0D9488?style=flat-square)

</div>

---

<h2 align="center">📸 Screenshots</h2>

### Streamlit Dashboard
<!-- Replace with your actual screenshot -->
![Streamlit Dashboard](docs/images/dashboard_screenshot.png)
> *Browse, filter, and track applications with live SQLite sync*

### Power BI Analytics
<!-- Replace with your actual screenshot -->
![Power BI Dashboard](docs/images/powerbi_screenshot.png)
> *Star-schema model with Fact_Jobs and Dim_ATS_Metrics tables*

### Daily Email Digest
<!-- Replace with your actual screenshot -->
![Email Digest](docs/images/email_screenshot.png)
> *Color-coded job cards with Apply buttons delivered every morning*

---

## 🏗 Architecture

<div align="center">
<img src="docs/images/architecture.svg" alt="Architecture Diagram" width="100%">
</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔄 **Concurrent fetching** | ThreadPoolExecutor queries 30+ sources in parallel — 3 min → 30 sec |
| 🧮 **Keyword scoring** | Weighted scoring engine with combo bonuses for hybrid-skill postings |
| 🗄 **SQLite persistence** | URL-based deduplication — never see the same job twice |
| 📊 **Application tracker** | Mark applied, favorite, add notes — saves instantly to database |
| 📧 **Daily email digest** | Color-coded HTML email with top matches via Gmail SMTP/TLS |
| 📈 **Streamlit dashboard** | Live charts, sidebar filters, job cards, KPI metrics |
| 📐 **Power BI integration** | Star schema: `Fact_Jobs` ──(1:N)── `Dim_ATS_Metrics` |
| ⚙️ **Zero-code config** | `config.yaml` — change titles, companies, keywords without touching Python |
| ✅ **69 unit tests** | `pytest` coverage for filters, scoring, and location detection |
| 🔒 **GitHub-safe** | `.gitignore` excludes database, logs, `.env`, `.idea/`, `__pycache__/` |

---

## 🚀 Quickstart

### Prerequisites
- Python 3.10+
- Windows (Task Scheduler automation)
- Gmail account with 2-Step Verification enabled

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/darajwilson2-web/Job-Intelligence-Pipeline.git
cd Job-Intelligence-Pipeline

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set Gmail App Password (Windows)
# Windows key → "Edit environment variables" → User variables → New
# Name: GMAIL_APP_PASSWORD   Value: your-16-char-app-password

# 5. Run your first job search
python main.py
```

---

## ⚙️ Configuration

All search preferences live in `config.yaml` — no Python knowledge needed:

```yaml
# Your location and preferences
your_city: "Charlotte, NC"
include_remote: true
include_contract: true
min_score: 3

# Target job titles
title_filters:
  - "fraud analyst"
  - "compliance analyst"
  - "risk analyst"
  - "executive assistant"
  - "data analyst"

# Companies to track (by ATS platform)
greenhouse_companies:
  - stripe
  - affirm
  - coinbase
  - gitlab

ashby_companies:
  - openai
  - ramp
  - deel
```

---

## 🖥 CLI Commands

```bash
# Full run — fetch, score, export, send email
python main.py

# Show only jobs not seen before
python main.py --new-only

# Show your top 20 unreviewed matches
python main.py --top

# Pipeline summary stats
python main.py --summary

# Mark a job as applied
python main.py --mark-applied "https://job-url-here" --notes "Applied via LinkedIn"

# List all applications submitted
python main.py --applied

# Launch the dashboard
streamlit run app.py
```

---

## 📊 Sample Output

```
============================================================
Run complete — 89 jobs exported
  New today:    23
  Total in DB:  312

By role type:
  Compliance / Risk / Fraud: 57
  EA / Business Partner: 10
  Data / Analytics: 22

By work type:
  Remote: 45
  In-Office / Hybrid: 32
  Contract: 12

Files saved:
  output/jobs_2026-07-08.csv
  output/jobs_2026-07-08.xlsx
  output/jobs.db  (full history + tracker)

📧 Sending daily email digest...
✅ Email digest sent successfully
============================================================
```

---

## 🗂 Project Structure

```
Job-Intelligence-Pipeline/
├── main.py              # Orchestrator — concurrent fetch, filter, score, export, email
├── config.yaml          # All user preferences — edit this, not the Python files
├── models.py            # Typed Job and JobRecord dataclasses
├── database.py          # SQLite persistence layer + application tracker
├── filters.py           # US location, title, and contract filtering (44 tests)
├── scoring.py           # Keyword scoring + combo bonuses + role/sector detection (25 tests)
├── exporters.py         # CSV + color-coded Excel export
├── app.py               # Streamlit dashboard with live SQLite sync
├── mailer.py            # Gmail SMTP/TLS daily digest
├── requirements.txt
├── README.md
├── .gitignore
├── ats/
│   ├── __init__.py
│   ├── common.py        # RemoteOK, Remotive, WeWorkRemotely
│   ├── greenhouse.py    # Greenhouse API (Stripe, Coinbase, GitLab...)
│   ├── lever.py         # Lever API (Netflix, Palantir, Carta...)
│   ├── ashby.py         # Ashby API (OpenAI, Ramp, Deel...)
│   └── workday.py       # Workday wd1–wd12 wildcard fetcher
├── tests/
│   ├── test_filters.py  # 44 filter tests
│   └── test_scoring.py  # 25 scoring tests
└── output/              # Generated files (excluded from Git)
    ├── jobs.db
    ├── jobs_YYYY-MM-DD.csv
    ├── jobs_YYYY-MM-DD.xlsx
    └── run.log
```

---

## 🛠 Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Concurrency | `ThreadPoolExecutor` |
| Database | SQLite 3 (via `sqlite3`) |
| Dashboard | Streamlit + Plotly |
| Analytics | Power BI Desktop |
| Email | `smtplib` + Gmail SMTP/TLS |
| Excel export | `openpyxl` |
| Config | PyYAML |
| HTTP | `requests` + `feedparser` |
| Testing | `pytest` (69 tests) |
| Version control | Git + GitHub |
| Automation | Windows Task Scheduler |

---

## 🔌 ATS Platform Coverage

| Platform | Companies |
|----------|-----------|
| **Greenhouse** | Stripe, Affirm, Robinhood, Coinbase, Airbnb, Instacart, GitLab, Elastic, Okta, Cloudflare, Datadog, HubSpot |
| **Lever** | Netflix, Palantir, Carta, Checkr, Samsara, Gusto |
| **Ashby** | OpenAI, Perplexity, Ramp, Brex, Deel, Anduril |
| **Workday** | Atrium Health, Novant Health, Humana, Aetna, Wells Fargo, Bank of America, Truist |
| **Public boards** | RemoteOK, Remotive, We Work Remotely |

---

## 🗓 Automation Setup (Windows Task Scheduler)

Two scheduled tasks run automatically every morning:

**Task 1 — Daily Job Intelligence Sync (7:00 AM)**
```
Program:   C:\Users\Owner\Documents\Job_Fetcher\.venv\Scripts\python.exe
Arguments: main.py
Start in:  C:\Users\Owner\Documents\Job_Fetcher
```

**Task 2 — Job Dashboard Startup (7:05 AM)**
```
Program:   C:\Users\Owner\Documents\Job_Fetcher\.venv\Scripts\streamlit.exe
Arguments: run app.py
Start in:  C:\Users\Owner\Documents\Job_Fetcher
```

---

## 🧪 Running Tests

```bash
# Run all 69 tests
python -m pytest tests/ -v

# Run filter tests only
python -m pytest tests/test_filters.py -v

# Run scoring tests only
python -m pytest tests/test_scoring.py -v
```

---

<div align="center">

---

</div>

<div align="center">

## 👩‍💻 About

**Dara J. Wilson** — Compliance, Risk & Fraud Analytics | Data Analytics | Executive Operations

📧 Darajwilson2@gmail.com &nbsp;·&nbsp; 💼 [linkedin.com/in/darajwilson](https://linkedin.com/in/darajwilson) &nbsp;·&nbsp; 📍 Charlotte, NC | Open to Remote

<br>

*Built with Python, curiosity, and zero tolerance for manual job searching.*

</div>
