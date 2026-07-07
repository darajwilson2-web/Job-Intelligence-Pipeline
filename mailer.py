


import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def send_daily_digest():
    # --- CONFIGURATION (Change these to your personal details) ---
    SENDER_EMAIL = "darajwilson2@gmail.com"
    SENDER_PASSWORD = "wvkd gaer hwwe ozgz"  # Generated via Google Account App Passwords
    RECEIVER_EMAIL = "darajwilson2@gmail.com"

    db_path = "output/jobs.db"
    today_str = datetime.today().strftime('%Y-%m-%d')

    # Connect and grab jobs found today that have high scores
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Adjust this query to match your specific scoring/filtering criteria
    cursor.execute("""
        SELECT company, title, work_type, score, url 
        FROM jobs 
        WHERE first_seen LIKE ? AND score >= 70
        ORDER BY score DESC
    """, (f"%{today_str}%",))

    jobs = cursor.fetchall()
    conn.close()

    if not jobs:
        print("No high-matching jobs discovered today. Digest skipped.")
        return

    # Build Email Content
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"🚀 Morning Intel: {len(jobs)} High-Value Job Matches Found ({today_str})"

    body = f"Good morning! Your automated agent ran successfully and captured {len(jobs)} stellar leads matching your criteria:\n\n"

    for idx, job in enumerate(jobs, 1):
        company, title, work_type, score, url = job
        body += f"{idx}. {title} at {company} ({work_type})\n"
        body += f"   🎯 Match Score: {score}/100\n"
        body += f"   🔗 Application Link: {url}\n\n"

    body += "\nLaunch your local Streamlit dashboard (`streamlit run app.py`) to manage tracking notes or apply!"
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.close()
        print("Daily automated digest dispatched successfully!")
    except Exception as e:
        print(f"Failed to transmit digest: {e}")


if __name__ == "__main__":
    send_daily_digest()