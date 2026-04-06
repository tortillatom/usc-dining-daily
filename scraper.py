"""
scraper.py — Fetches USC dining hall menus from the hospitality.usc.edu REST API.

No browser automation needed: the site exposes a clean WordPress REST endpoint.
Endpoint: GET /wp-json/hsp-api/v1/get-res-dining-menus/{venue}?y=YYYY&m=M&d=D
"""

import requests
from datetime import date, datetime
from typing import Optional

BASE_URL = "https://hospitality.usc.edu/wp-json/hsp-api/v1/get-res-dining-menus"

VENUES = {
    "Everybody's Kitchen": "evk",
    "Parkside": "parkside",
    "USC Village": "university-village",
}


def fetch_hall(venue_slug: str, target_date: date) -> dict:
    """Fetch raw menu JSON for one dining hall on a given date."""
    params = {
        "y": target_date.year,
        "m": target_date.month,
        "d": target_date.day,
    }
    url = f"{BASE_URL}/{venue_slug}"
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def parse_meal(meal: dict) -> Optional[dict]:
    """
    Convert one meal entry from the API into a normalised dict.
    Returns None if the meal has no stations (i.e. not served that day).

    Returns:
        {
            "name": "Lunch",
            "stations": {
                "Station Name": [
                    {
                        "item": "Grilled Chicken",
                        "preferences": ["halal-ingredients", "vegetarian"],
                    },
                    ...
                ]
            }
        }
    """
    stations_raw = meal.get("stations")
    if not stations_raw:
        return None

    stations: dict[str, dict] = {}
    for station in stations_raw:
        name = station.get("station", "Other")
        subtitle = station.get("subtitle", "") or ""
        items = [
            {
                "item": entry["item"],
                "preferences": entry.get("preferences", []),
                "allergens": entry.get("allergens", []),
            }
            for entry in station.get("menu", [])
        ]
        if items:
            stations[name] = {"subtitle": subtitle, "entries": items}

    if not stations:
        return None

    return {"name": meal["name"], "stations": stations}


def scrape_menus(target_date: Optional[date] = None) -> dict:
    """
    Scrape all three dining halls for the given date (defaults to today).

    Returns:
        {
            "date": "2026-04-05",
            "halls": {
                "Everybody's Kitchen": {
                    "Brunch": {
                        "Fresh from the Farm": [
                            {"item": "Plain Greek Yogurt", "preferences": [...], "allergens": [...]},
                            ...
                        ]
                    },
                    "Lunch": {...},
                },
                "Parkside": {...},
                "USC Village": {...},
            }
        }
    """
    if target_date is None:
        target_date = date.today()

    result = {
        "date": target_date.isoformat(),
        "halls": {},
    }

    for hall_name, venue_slug in VENUES.items():
        try:
            raw = fetch_hall(venue_slug, target_date)
        except requests.RequestException as exc:
            print(f"[scraper] WARNING: Could not fetch {hall_name}: {exc}")
            result["halls"][hall_name] = {}
            continue

        meals: dict[str, dict] = {}
        for meal_entry in raw.get("meals", []):
            parsed = parse_meal(meal_entry)
            if parsed:
                meals[parsed["name"]] = parsed["stations"]

        result["halls"][hall_name] = meals

    return result


if __name__ == "__main__":
    import json

    data = scrape_menus()
    print(json.dumps(data, indent=2))
