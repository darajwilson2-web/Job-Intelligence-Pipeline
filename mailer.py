"""
mailer.py — Daily Email Digest
================================
Sends a formatted daily email with your top job matches.

SETUP (one-time, required):
  1. Turn on Gmail 2-Step Verification:
       myaccount.google.com → Security → 2-Step Verification → Turn On
  2. Create an App Password:
       myaccount.google.com → Security → App Passwords
       Name it: Job Agent Mailer
       Copy the 16-character password shown
  3. Set it as a Windows environment variable:
       Press Windows key → search "Edit environment variables"
       Click "Environment Variables"
       Under "User variables" click New:
         Variable name:   GMAIL_APP_PASSWORD
         Variable value:  your-16-character-password (no spaces)
       Click OK → OK → restart PyCharm

WHY environment variable? Storing passwords in code files is unsafe.
Environment variables keep your password secure and off GitHub.
"""

import os
import smtplib
import logging
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

# ── YOUR EMAIL SETTINGS ──────────────────────────────────────────────────
# Change SENDER_EMAIL and RECIPIENT_EMAIL to your Gmail address
SENDER_EMAIL    = "Darajwilson2@gmail.com"
RECIPIENT_EMAIL = "Darajwilson2@gmail.com"
SMTP_HOST       = "smtp.gmail.com"
SMTP_PORT       = 587
MIN_SCORE       = 10   # Only include jobs scoring this or higher in the email


# ── ROLE TYPE COLORS (for HTML email) ────────────────────────────────────
ROLE_COLORS = {
    "Compliance / Risk / Fraud":    "#FFD7E8",
    "EA / Business Partner":        "#D7E8FF",
    "Data / Analytics":             "#D7FFE8",
    "Operations Analytics":         "#FFF3D7",
    "Project / Program Coordinator":"#F0D7FF",
    "Other":                        "#F0F0F0",
}


def _get_app_password() -> str:
    """
    Reads Gmail App Password from environment variable.
    Raises a clear error if not set, with setup instructions.
    """
    pwd = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not pwd:
        raise EnvironmentError(
            "GMAIL_APP_PASSWORD environment variable is not set.\n"
            "To fix this:\n"
            "  1. Press Windows key → search 'Edit environment variables'\n"
            "  2. Click Environment Variables\n"
            "  3. Under User variables → New\n"
            "     Name:  GMAIL_APP_PASSWORD\n"
            "     Value: your 16-character Gmail App Password\n"
            "  4. Click OK → restart PyCharm"
        )
    return pwd


def _build_html(jobs: list, new_count: int, total_count: int) -> str:
    """Build a clean HTML email with job cards."""
    today    = date.today().strftime("%A, %B %d, %Y")
    job_rows = ""

    for j in jobs[:15]:  # Max 15 jobs in email
        # Handle both Job dataclass and plain dict
        if hasattr(j, 'title'):
            title     = j.title
            company   = j.company
            score     = j.score
            role_type = j.role_type
            work_type = j.work_type
            sector    = j.sector
            url       = j.url
            matched   = ", ".join(j.matched_keywords[:5]) if j.matched_keywords else ""
        else:
            title     = j.get("title", "")
            company   = j.get("company", "")
            score     = j.get("score", 0)
            role_type = j.get("role_type", "")
            work_type = j.get("work_type", "")
            sector    = j.get("sector", "")
            url       = j.get("url", "")
            matched   = j.get("matched_keywords", "")
            if isinstance(matched, list):
                matched = ", ".join(matched[:5])

        norm_score = min(100, round((score / 40) * 100))
        color      = ROLE_COLORS.get(role_type, "#F0F0F0")
        work_emoji = {"Remote": "🌐", "Contract": "📋", "In-Office / Hybrid": "🏢"}.get(work_type, "💼")

        job_rows += f"""
        <tr>
          <td style="background:{color};padding:12px;border-radius:6px;margin-bottom:8px;display:block;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td width="60" style="vertical-align:middle;text-align:center;">
                  <div style="background:#1A365D;color:white;border-radius:50%;width:48px;height:48px;
                              line-height:48px;text-align:center;font-size:18px;font-weight:bold;
                              margin:auto;">{norm_score}</div>
                  <div style="font-size:10px;color:#666;text-align:center;">/100</div>
                </td>
                <td style="padding-left:12px;vertical-align:middle;">
                  <div style="font-weight:bold;font-size:15px;color:#1A365D;">{title}</div>
                  <div style="color:#475569;font-size:13px;">{company} &nbsp;·&nbsp; {work_emoji} {work_type} &nbsp;·&nbsp; {sector}</div>
                  <div style="color:#94A3B8;font-size:12px;margin-top:4px;">🏷 {matched}</div>
                </td>
                <td width="80" style="text-align:right;vertical-align:middle;">
                  <a href="{url}" style="background:#0D9488;color:white;padding:8px 14px;
                     border-radius:4px;text-decoration:none;font-size:13px;font-weight:bold;">
                     Apply →
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr><td style="height:8px;"></td></tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:Calibri,Arial,sans-serif;max-width:680px;margin:0 auto;padding:20px;background:#F8FAFC;">

      <!-- Header -->
      <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
        <tr>
          <td style="background:#1A365D;padding:20px 24px;border-radius:8px 8px 0 0;">
            <div style="color:white;font-size:22px;font-weight:bold;">💼 Job Intelligence Digest</div>
            <div style="color:#94A3B8;font-size:13px;margin-top:4px;">{today}</div>
          </td>
        </tr>
        <tr>
          <td style="background:#0D9488;padding:12px 24px;border-radius:0 0 8px 8px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="color:white;text-align:center;">
                  <div style="font-size:28px;font-weight:bold;">{new_count}</div>
                  <div style="font-size:12px;">New Today</div>
                </td>
                <td style="color:white;text-align:center;">
                  <div style="font-size:28px;font-weight:bold;">{total_count}</div>
                  <div style="font-size:12px;">Total Fetched</div>
                </td>
                <td style="color:white;text-align:center;">
                  <div style="font-size:28px;font-weight:bold;">{len(jobs[:15])}</div>
                  <div style="font-size:12px;">In This Email</div>
                </td>
                <td style="color:white;text-align:center;">
                  <div style="font-size:28px;font-weight:bold;">{min(100, round((max((j.score if hasattr(j,'score') else j.get('score',0)) for j in jobs) / 40) * 100)) if jobs else 0}</div>
                  <div style="font-size:12px;">Top Score</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>

      <!-- Jobs -->
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td style="font-size:16px;font-weight:bold;color:#1A365D;padding-bottom:12px;">
            🎯 Top Matches — Sorted by Score
          </td>
        </tr>
        {job_rows}
      </table>

      <!-- Footer -->
      <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:24px;">
        <tr>
          <td style="background:#1A365D;padding:16px 24px;border-radius:8px;text-align:center;">
            <div style="color:#94A3B8;font-size:12px;">
              Job Intelligence Pipeline &nbsp;·&nbsp; Dara J. Wilson &nbsp;·&nbsp;
              Powered by Python + SQLite + Greenhouse/Lever/Ashby APIs
            </div>
            <div style="color:#475569;font-size:11px;margin-top:4px;">
              Open your dashboard: streamlit run app.py → http://localhost:8501
            </div>
          </td>
        </tr>
      </table>

    </body>
    </html>
    """


def send_digest(jobs: list, new_count: int = None, total_count: int = None):
    """
    Send the daily email digest.
    Called automatically from main.py after every full run.

    Args:
        jobs:        List of Job objects or dicts, sorted by score descending
        new_count:   Number of genuinely new jobs today (optional)
        total_count: Total jobs fetched this run (optional)
    """
    if not jobs:
        logger.info("No jobs to email — skipping digest")
        return

    # Filter to min score
    qualified = [j for j in jobs
                 if (j.score if hasattr(j, 'score') else j.get('score', 0)) >= MIN_SCORE]
    if not qualified:
        logger.info(f"No jobs scored >= {MIN_SCORE} — skipping digest")
        return

    new_count   = new_count   or len(jobs)
    total_count = total_count or len(jobs)
    today_str   = date.today().strftime("%Y-%m-%d")

    try:
        password = _get_app_password()
    except EnvironmentError as e:
        logger.error(f"Cannot send email: {e}")
        raise

    # Build message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🎯 Job Digest {today_str} — {len(qualified)} Matches | Top Score: {min(100, round((max((j.score if hasattr(j,'score') else j.get('score',0)) for j in qualified)/40)*100))}/100"
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECIPIENT_EMAIL

    html_body = _build_html(qualified, new_count, total_count)
    msg.attach(MIMEText(html_body, "html"))

    # Send via Gmail TLS
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SENDER_EMAIL, password)
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())

    logger.info(f"Email digest sent: {len(qualified)} jobs → {RECIPIENT_EMAIL}")


# ── STANDALONE TEST ───────────────────────────────────────────────────────
if __name__ == "__main__":
    """Run this directly to test the email without running the full pipeline."""
    import sqlite3
    from pathlib import Path

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    db_path = Path("output/jobs.db")
    if not db_path.exists():
        print("No database found. Run main.py first, then test mailer.")
        exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM jobs WHERE score >= ? ORDER BY score DESC LIMIT 15",
        (MIN_SCORE,)
    ).fetchall()
    conn.close()

    jobs = [dict(r) for r in rows]
    print(f"Sending test email with {len(jobs)} jobs...")
    send_digest(jobs, new_count=len(jobs), total_count=len(jobs))
    print("Done — check your inbox!")
