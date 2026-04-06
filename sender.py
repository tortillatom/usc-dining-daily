"""
sender.py — Sends the newsletter via Gmail SMTP.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

GMAIL_SMTP = "smtp.gmail.com"
GMAIL_PORT = 587


def _gmail_address() -> str:
    addr = os.environ.get("GMAIL_ADDRESS", "")
    if not addr:
        raise EnvironmentError("GMAIL_ADDRESS environment variable is not set.")
    return addr


def _gmail_app_password() -> str:
    pw = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not pw:
        raise EnvironmentError("GMAIL_APP_PASSWORD environment variable is not set.")
    return pw


def _beehiiv_key() -> str:
    key = os.environ.get("BEEHIIV_API_KEY", "")
    if not key:
        raise EnvironmentError("BEEHIIV_API_KEY environment variable is not set.")
    return key


def _pub_id() -> str:
    pub_id = os.environ.get("BEEHIIV_PUB_ID", "")
    if not pub_id:
        raise EnvironmentError("BEEHIIV_PUB_ID environment variable is not set.")
    return pub_id


def get_subscribers() -> list[str]:
    """Fetch all active subscriber emails from Beehiiv."""
    import requests
    emails = []
    cursor = None
    headers = {"Authorization": f"Bearer {_beehiiv_key()}"}

    while True:
        params = {"limit": 100, "status": "active"}
        if cursor:
            params["after"] = cursor

        resp = requests.get(
            f"https://api.beehiiv.com/v2/publications/{_pub_id()}/subscriptions",
            headers=headers,
            params=params,
            timeout=15,
        )
        if not resp.ok:
            raise RuntimeError(f"Beehiiv subscriber fetch failed ({resp.status_code}): {resp.text}")

        data = resp.json()
        emails.extend(sub["email"] for sub in data.get("data", []))

        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")

    return emails


def _build_message(html_content: str, subject: str, to_email: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"USC Dining Daily <{_gmail_address()}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_content, "html"))
    return msg


def _smtp_connection():
    conn = smtplib.SMTP(GMAIL_SMTP, GMAIL_PORT)
    conn.ehlo()
    conn.starttls()
    conn.login(_gmail_address(), _gmail_app_password())
    return conn


def send_newsletter(html_content: str, subject: str) -> bool:
    """Fetch all Beehiiv subscribers and send the newsletter via Gmail SMTP."""
    subscribers = get_subscribers()
    if not subscribers:
        print("[sender] No active subscribers — nothing to send.")
        return True

    print(f"[sender] Sending to {len(subscribers)} subscribers...")
    failed = []

    with _smtp_connection() as conn:
        for email in subscribers:
            try:
                msg = _build_message(html_content, subject, email)
                conn.sendmail(_gmail_address(), email, msg.as_string())
            except Exception as e:
                print(f"[sender] WARNING: failed for {email}: {e}")
                failed.append(email)

    print(f"[sender] Done. {len(subscribers) - len(failed)}/{len(subscribers)} delivered.")
    return True


def send_test_email(html_content: str, subject: str, to_email: str) -> bool:
    """Send a single test email via Gmail SMTP."""
    with _smtp_connection() as conn:
        msg = _build_message(html_content, subject, to_email)
        conn.sendmail(_gmail_address(), to_email, msg.as_string())
    print(f"[sender] Test email sent to {to_email}.")
    return True
