"""
sender.py — Sends the newsletter via the Brevo (Sendinblue) API v3.

All Brevo-specific logic is isolated here. To swap providers later,
implement the same interface in a new file and update main.py's import.
"""

import os
import requests

BREVO_API_URL = "https://api.brevo.com/v3/emailCampaigns"
BREVO_SEND_URL = "https://api.brevo.com/v3/emailCampaigns/{campaign_id}/sendNow"


def _api_key() -> str:
    key = os.environ.get("BREVO_API_KEY", "")
    if not key:
        raise EnvironmentError("BREVO_API_KEY environment variable is not set.")
    return key


def _list_id() -> int:
    list_id = os.environ.get("BREVO_LIST_ID", "")
    if not list_id:
        raise EnvironmentError("BREVO_LIST_ID environment variable is not set.")
    return int(list_id)


def _sender() -> dict:
    return {
        "name": os.environ.get("SENDER_NAME", "USC Dining Daily"),
        "email": os.environ.get("SENDER_EMAIL", "dining@example.com"),
    }


def send_newsletter(html_content: str, subject: str) -> bool:
    """
    Create a Brevo email campaign and send it immediately to the contact list.

    Args:
        html_content: Fully-rendered HTML string.
        subject:      Email subject line.

    Returns:
        True on success, raises on failure.
    """
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": _api_key(),
    }

    # Step 1 — Create the campaign
    campaign_payload = {
        "name": f"Auto: {subject}",
        "subject": subject,
        "sender": _sender(),
        "type": "classic",
        "htmlContent": html_content,
        "recipients": {
            "listIds": [_list_id()],
        },
        # Brevo will inject the unsubscribe link automatically when you use
        # their list-based campaigns — no manual token needed in the template.
    }

    create_resp = requests.post(BREVO_API_URL, json=campaign_payload, headers=headers, timeout=30)
    if not create_resp.ok:
        raise RuntimeError(
            f"Brevo campaign creation failed ({create_resp.status_code}): {create_resp.text}"
        )

    campaign_id = create_resp.json()["id"]
    print(f"[sender] Created campaign #{campaign_id}: {subject!r}")

    # Step 2 — Send immediately
    send_resp = requests.post(
        BREVO_SEND_URL.format(campaign_id=campaign_id),
        headers=headers,
        timeout=30,
    )
    if not send_resp.ok:
        raise RuntimeError(
            f"Brevo send failed ({send_resp.status_code}): {send_resp.text}"
        )

    print(f"[sender] Campaign #{campaign_id} dispatched successfully.")
    return True


def send_test_email(html_content: str, subject: str, to_email: str) -> bool:
    """
    Send a one-off test email to a single address (bypasses contact list).
    Useful for previewing locally before a real send.
    """
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": _api_key(),
    }

    payload = {
        "sender": _sender(),
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content,
    }

    resp = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        json=payload,
        headers=headers,
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(
            f"Brevo transactional send failed ({resp.status_code}): {resp.text}"
        )

    print(f"[sender] Test email sent to {to_email}.")
    return True
