"""
sender.py — Fetches subscribers from Beehiiv, sends emails via Resend.

Beehiiv: manages subscribers, signup page, web archive (free tier).
Resend:  handles actual email delivery via API (free tier, 3k/month).
"""

import os
import requests

RESEND_API_URL = "https://api.resend.com/emails"
BEEHIIV_API_BASE = "https://api.beehiiv.com/v2"


def _resend_key() -> str:
    key = os.environ.get("RESEND_API_KEY", "")
    if not key:
        raise EnvironmentError("RESEND_API_KEY environment variable is not set.")
    return key


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


def _sender_email() -> str:
    return os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")


def _sender_name() -> str:
    return os.environ.get("SENDER_NAME", "USC Dining Daily")


def get_subscribers() -> list[str]:
    """Fetch all active subscriber emails from Beehiiv."""
    emails = []
    cursor = None
    headers = {"Authorization": f"Bearer {_beehiiv_key()}"}

    while True:
        params = {"limit": 100, "status": "active"}
        if cursor:
            params["after"] = cursor

        resp = requests.get(
            f"{BEEHIIV_API_BASE}/publications/{_pub_id()}/subscriptions",
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


def _send_one(html_content: str, subject: str, to_email: str) -> None:
    """Send a single email via Resend."""
    payload = {
        "from": f"{_sender_name()} <{_sender_email()}>",
        "to": [to_email],
        "subject": subject,
        "html": html_content,
    }
    resp = requests.post(
        RESEND_API_URL,
        json=payload,
        headers={"Authorization": f"Bearer {_resend_key()}"},
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Resend failed for {to_email} ({resp.status_code}): {resp.text}")


def send_newsletter(html_content: str, subject: str) -> bool:
    """Fetch all Beehiiv subscribers and send the newsletter to each via Resend."""
    subscribers = get_subscribers()
    if not subscribers:
        print("[sender] No active subscribers — nothing to send.")
        return True

    print(f"[sender] Sending to {len(subscribers)} subscribers...")
    failed = []
    for email in subscribers:
        try:
            _send_one(html_content, subject, email)
        except RuntimeError as e:
            print(f"[sender] WARNING: {e}")
            failed.append(email)

    print(f"[sender] Done. {len(subscribers) - len(failed)}/{len(subscribers)} delivered.")
    return True


def send_test_email(html_content: str, subject: str, to_email: str) -> bool:
    """Send a single test email via Resend."""
    _send_one(html_content, subject, to_email)
    print(f"[sender] Test email sent to {to_email}.")
    return True
