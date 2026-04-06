"""
sender.py — Sends the newsletter via the Beehiiv API v2.

All Beehiiv-specific logic is isolated here. To swap providers later,
implement the same interface in a new file and update main.py's import.
"""

import os
import requests

BEEHIIV_API_BASE = "https://api.beehiiv.com/v2"


def _api_key() -> str:
    key = os.environ.get("BEEHIIV_API_KEY", "")
    if not key:
        raise EnvironmentError("BEEHIIV_API_KEY environment variable is not set.")
    return key


def _pub_id() -> str:
    pub_id = os.environ.get("BEEHIIV_PUB_ID", "")
    if not pub_id:
        raise EnvironmentError("BEEHIIV_PUB_ID environment variable is not set.")
    return pub_id


def _headers() -> dict:
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_api_key()}",
    }


def send_newsletter(html_content: str, subject: str) -> bool:
    """
    Create a Beehiiv post and send it immediately to all subscribers.

    Args:
        html_content: Fully-rendered HTML string.
        subject:      Email subject line.

    Returns:
        True on success, raises on failure.
    """
    url = f"{BEEHIIV_API_BASE}/publications/{_pub_id()}/posts"

    payload = {
        "subject_line": subject,
        "content": html_content,
        "status": "confirmed",   # sends immediately
        "audience": "all",
        "content_tags": [],
    }

    resp = requests.post(url, json=payload, headers=_headers(), timeout=30)
    if not resp.ok:
        raise RuntimeError(
            f"Beehiiv post creation failed ({resp.status_code}): {resp.text}"
        )

    post_id = resp.json().get("data", {}).get("id", "?")
    print(f"[sender] Post {post_id!r} sent: {subject!r}")
    return True


def send_test_email(html_content: str, subject: str, to_email: str) -> bool:
    """
    Send a one-off test email to a single address via Beehiiv's send test endpoint.
    """
    url = f"{BEEHIIV_API_BASE}/publications/{_pub_id()}/posts"

    # Create as draft first, then we just print a preview notice —
    # Beehiiv doesn't have a single-address transactional send on free tier,
    # so we create a draft you can preview in the Beehiiv dashboard.
    payload = {
        "subject_line": subject,
        "content": html_content,
        "status": "draft",
        "audience": "all",
        "content_tags": [],
    }

    resp = requests.post(url, json=payload, headers=_headers(), timeout=30)
    if not resp.ok:
        raise RuntimeError(
            f"Beehiiv draft creation failed ({resp.status_code}): {resp.text}"
        )

    post_id = resp.json().get("data", {}).get("id", "?")
    print(f"[sender] Draft created (ID: {post_id}). Preview it at app.beehiiv.com")
    return True
