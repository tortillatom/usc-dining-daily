"""
formatter.py — Renders scraped menu data into an HTML email via Jinja2.
"""

import os
from datetime import date, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).parent / "templates"

# Map API preference slugs → display label + emoji
PREFERENCE_LABELS = {
    "vegan": ("Vegan", "🌱"),
    "vegetarian": ("Vegetarian", "🥦"),
    "halal-ingredients": ("Halal", "☪"),
}

MEAL_ORDER = ["Breakfast", "Brunch", "Lunch", "Dinner"]

# Signature station per hall.
# Fields: (fallback_label, station_pattern, dynamic_bar_subsection)
# dynamic_bar_subsection=True: scan Hot Line for an item ending with "BAR"
# (e.g. "RICE BOWL BAR", "WING BAR") — use that as the label and show items after it.
HALL_HIGHLIGHTS = {
    "Everybody's Kitchen": ("Bar",    "hot line", True),
    "Parkside":            ("Bistro", "bistro",   True),
    "USC Village":         ("Expo",   "expo",     False),
}


def _find_highlight(hall_name: str, meals: dict) -> dict | None:
    """
    Search Lunch then Dinner for the hall's signature station.
    Returns {"label": str, "items": list} or None if nothing found.

    For EVK, scans Hot Line for an inline "* BAR" header item, uses its
    title-cased name as the label, and returns only the items after it.
    """
    if hall_name not in HALL_HIGHLIGHTS:
        return None
    fallback_label, station_pattern, dynamic_bar = HALL_HIGHLIGHTS[hall_name]

    for preferred_meal in ["Lunch", "Dinner"]:
        if preferred_meal not in meals:
            continue
        for station_name, station_data in meals[preferred_meal].items():
            if station_pattern.lower() not in station_name.lower():
                continue
            entries = station_data["entries"]
            subtitle = station_data.get("subtitle", "")
            if not dynamic_bar:
                label = subtitle if subtitle else fallback_label
                return {"label": label, "entries": entries}
            # Find the first item whose name ends with "BAR" — it's the daily bar header
            for i, entry in enumerate(entries):
                if entry["item"].strip().upper().endswith("BAR"):
                    label = entry["item"].strip().title()
                    return {"label": label, "entries": entries[i + 1:]}
            # No bar section today — fall back to showing full station
            label = subtitle if subtitle else fallback_label
            return {"label": label, "entries": entries}
    return None


def _ordered_meals(meals: dict) -> list[tuple[str, dict]]:
    """Return meals in canonical breakfast→dinner order."""
    ordered = [(m, meals[m]) for m in MEAL_ORDER if m in meals]
    extras = [(m, meals[m]) for m in meals if m not in MEAL_ORDER]
    return ordered + extras


def format_email(menu_data: dict) -> str:
    """
    Render the HTML email from scraped menu data.

    Args:
        menu_data: Output of scraper.scrape_menus()

    Returns:
        A complete HTML string ready to send.
    """
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )

    # Make helpers available inside templates
    env.globals["preference_labels"] = PREFERENCE_LABELS
    env.globals["ordered_meals"] = _ordered_meals
    env.globals["hall_highlights"] = HALL_HIGHLIGHTS
    env.globals["find_highlight"] = _find_highlight

    template = env.get_template("email.html")

    # Parse date for the subject / header
    raw_date = menu_data.get("date", date.today().isoformat())
    parsed_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
    friendly_date = parsed_date.strftime("%A, %B %-d")  # e.g. "Sunday, April 6"

    return template.render(
        date=friendly_date,
        halls=menu_data.get("halls", {}),
        meal_order=MEAL_ORDER,
        logo_url=os.environ.get("LOGO_URL", ""),
    )


def build_subject(menu_data: dict) -> str:
    """Return the email subject line."""
    raw_date = menu_data.get("date", date.today().isoformat())
    parsed_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
    friendly_date = parsed_date.strftime("%A, %B %-d")
    return f"USC Dining — {friendly_date}"


if __name__ == "__main__":
    from scraper import scrape_menus

    data = scrape_menus()
    html = format_email(data)
    out_path = Path("preview.html")
    out_path.write_text(html)
    print(f"Preview written to {out_path.resolve()}")
