"""
main.py — Orchestrates scrape → format → send.

Usage:
    # Normal run (sends to full contact list):
    python main.py

    # Preview only — writes preview.html and skips sending:
    python main.py --preview

    # Send test email to one address:
    python main.py --test-email you@example.com

    # Run for a specific date:
    python main.py --date 2026-04-07
"""

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

from scraper import scrape_menus
from formatter import format_email, build_subject
from sender import send_newsletter, send_test_email


def parse_args():
    parser = argparse.ArgumentParser(description="USC Dining Newsletter")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Write preview.html and exit without sending.",
    )
    parser.add_argument(
        "--test-email",
        metavar="ADDRESS",
        help="Send a test email to ADDRESS instead of the full list.",
    )
    parser.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        help="Fetch menus for this date instead of today.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    target_date = None
    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()

    print(f"[main] Scraping menus for {target_date or date.today()}...")
    menu_data = scrape_menus(target_date)

    has_any = any(bool(meals) for meals in menu_data["halls"].values())
    if not has_any:
        print("[main] No menu data found for today — skipping send.")
        sys.exit(0)

    print("[main] Formatting email...")
    html = format_email(menu_data)
    subject = build_subject(menu_data)

    if args.preview:
        out = Path("preview.html")
        out.write_text(html, encoding="utf-8")
        print(f"[main] Preview written to {out.resolve()} — no email sent.")
        return

    if args.test_email:
        print(f"[main] Sending test email to {args.test_email}...")
        send_test_email(html, subject, args.test_email)
        return

    print(f"[main] Sending newsletter: {subject!r}")
    send_newsletter(html, subject)
    print("[main] Done.")


if __name__ == "__main__":
    main()
