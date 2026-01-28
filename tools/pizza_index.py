import time
import warnings
from datetime import datetime
from logging import getLogger

from langchain_core.tools import tool
import livepopulartimes
import pandas as pd
from pytz import timezone
import requests

from hephaestus.langfuse_handler import langfuse
from hephaestus.settings import settings


logger = getLogger(__name__)

# Suppress warnings
# warnings.filterwarnings("ignore")

# Pentagon coordinates
PENTAGON_LAT = 38.8719
PENTAGON_LNG = -77.0563
RADIUS_METERS = 3000  # 3km radius

def get_current_hour_baseline(populartimes_data: list | None) -> int | None:
    """Extract the baseline busyness for current day/hour from populartimes data."""
    if not populartimes_data:
        return None

    now = datetime.now()
    day_index = now.weekday()  # 0 = Monday
    hour = now.hour

    try:
        day_data = populartimes_data[day_index]
        if day_data and "data" in day_data:
            hourly_data = day_data["data"]
            if 0 <= hour < len(hourly_data):
                return hourly_data[hour]
    except (IndexError, KeyError, TypeError) as e:
        logger.exception(f"⚠️ Could not extract baseline for current hour: {e}")

    return None


def search_nearby_restaurants(api_key: str, lat: float, lng: float, radius: int) -> list[dict]:
    """
    Search for restaurants using Google Places API Nearby Search.

    Returns list of places with place_id, name, address, etc.
    """
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

    all_places = []
    next_page_token = None

    while True:
        params = {
            "location": f"{lat},{lng}",
            "radius": radius,
            "type": "restaurant",
            "key": api_key,
        }

        if next_page_token:
            params["pagetoken"] = next_page_token
            time.sleep(2)  # Required delay between page requests

        response = requests.get(url, params=params)
        data = response.json()

        if data.get("status") != "OK" and data.get("status") != "ZERO_RESULTS":
            logger.error(f"❌ Places API error: {data.get('status')} - {data.get('error_message', '')}")
            break

        results = data.get("results", [])
        all_places.extend(results)

        logger.debug(f"   📥 Found {len(results)} restaurants (total: {len(all_places)})")

        next_page_token = data.get("next_page_token")
        if not next_page_token:
            break

    return all_places


def fetch_popularity_for_place(api_key: str, place: dict) -> dict | None:
    """
    Fetch popularity data for a single place using LivePopularTimes.

    Uses place_id for more reliable lookups.

    Returns enriched place dict with popularity data.
    """
    name = place.get("name", "")
    address = place.get("vicinity", "") or place.get("formatted_address", "")
    place_id = place.get("place_id")

    if not place_id:
        logger.warning(f"⚠️ No place_id for {name}, skipping")
        return None

    try:
        # Add small delay to avoid rate limiting
        time.sleep(0.3)

        # Use place_id for more reliable lookups
        popularity_data = livepopulartimes.get_populartimes_by_place_id(api_key, place_id)

        if popularity_data:
            # Merge with original place data
            return {
                "name": popularity_data.get("name") or name,
                "address": popularity_data.get("address") or address,
                "place_id": place_id,
                "rating": popularity_data.get("rating") or place.get("rating"),
                "rating_n": popularity_data.get("rating_n"),
                "current_popularity": popularity_data.get("current_popularity"),
                "populartimes": popularity_data.get("populartimes"),
                "time_spent": popularity_data.get("time_spent"),
            }
    except Exception as e:
        logger.exception(f"⚠️ Failed to get popularity for {name} ({place_id}): {e}")

    # Return basic info even if popularity fetch failed
    return {
        "name": name,
        "address": address,
        "place_id": place_id,
        "rating": place.get("rating"),
        "current_popularity": None,
        "populartimes": None,
    }


def fetch_pentagon_restaurants(max_restaurants: int = 30) -> list[dict]:
    """
    Fetch restaurants within 3km of the Pentagon with their busyness data.

    Uses a two-phase approach:
    1. Get list of restaurants from Google Places API
    2. Fetch popularity data for each using LivePopularTimes (web scraping)

    Args:
        max_restaurants: Maximum number of restaurants to fetch popularity for

    Returns:
        List of restaurant dictionaries with popularity data.
    """
    api_key = settings.GOOGLE_MAPS_API_KEY

    if not api_key:
        logger.error("❌ GOOGLE_MAPS_API_KEY not configured in settings!")
        raise ValueError("GOOGLE_MAPS_API_KEY is required")

    logger.debug(f"🔍 Phase 1: Searching for restaurants within {RADIUS_METERS}m of the Pentagon...")

    # Phase 1: Get list of restaurants from Google Places API
    places = search_nearby_restaurants(api_key, PENTAGON_LAT, PENTAGON_LNG, RADIUS_METERS)
    logger.debug(f"✅ Found {len(places)} restaurants total")

    if not places:
        return []

    # Limit to top-rated restaurants for efficiency
    places_with_rating = [p for p in places if p.get("rating")]
    places_with_rating.sort(key=lambda x: (x.get("rating", 0), x.get("user_ratings_total", 0)), reverse=True)
    places_to_fetch = places_with_rating[:max_restaurants]

    logger.debug(f"🔄 Phase 2: Fetching popularity data for top {len(places_to_fetch)} restaurants...")

    # Phase 2: Fetch popularity data using LivePopularTimes (by place_id)
    enriched_places = []

    for i, place in enumerate(places_to_fetch):

        result = fetch_popularity_for_place(api_key, place)
        if result:
            enriched_places.append(result)

    logger.debug(f"✅ Got data for {len(enriched_places)} restaurants")

    return enriched_places


@tool
def pentagon_activity_spike():
    """
    Pentagon Overtime Signal (Restaurant Activity Spike Index).
    """
    logger.info("🍕 Starting Pentagon Restaurant Busyness Index...")


    # Define DC timezone (Eastern Time)
    eastern = timezone("America/New_York")
    now = datetime.now(eastern)
    # Define normal work hours: 8am to 6pm (exclusive of 6pm)
    if now.hour < 8 or now.hour >= 18 or now.weekday() >= 5:
        return "Not relevant"

    try:
        places = fetch_pentagon_restaurants(max_restaurants=30)
        df = pd.DataFrame(places)
        activity_spike = df['current_popularity'].astype(float) / df['populartimes'].astype(float)

        return str(activity_spike.mean())

    except Exception as e:
        logger.exception(f"❌ Script failed: {e}")
        return "ERROR"

pentagon_activity_spike.description = langfuse.get_prompt("pizzaint-description").prompt
