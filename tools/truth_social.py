"""
Truth Social API integration using truthbrush.

Fetches Trump's posts (truths) from Truth Social.

NOTE: Truth Social uses aggressive Cloudflare protection. If you encounter
403 errors, you may need to:
1. Use a residential proxy
2. Provide a pre-authenticated token via settings.truth_social.token
3. Run from a network that isn't flagged by Cloudflare
"""
from datetime import datetime, timedelta, timezone
from html import unescape
from logging import getLogger
import re

from hephaestus.settings import settings
from langchain_core.tools import tool
from truthbrush import Api

logger = getLogger(__name__)

# Trump's Truth Social username
TRUMP_USERNAME = "realDonaldTrump"


def _strip_html(content: str) -> str:
    """Strip HTML tags and unescape HTML entities from content."""
    clean = re.sub(r'<[^>]+>', '', content)
    return unescape(clean).strip()


def _get_truths_last_24h(username: str = TRUMP_USERNAME) -> list[str]:
    """
    Fetch all truths from a user in the last 24 hours.

    Args:
        username: Truth Social username to fetch posts from

    Returns:
        List of truth content strings from the last 24 hours

    Raises:
        ValueError: If credentials are not configured
        Exception: If API request fails (e.g., Cloudflare block)
    """
    logger.info(f"🔍 Fetching truths from @{username} for the last 24 hours...")

    # Get credentials from settings
    ts_config = settings.get("truth_social")
    if not ts_config:
        logger.error("❌ Truth Social settings not configured!")
        raise ValueError("truth_social section is required in settings")

    ts_user = ts_config.get("user")
    ts_password = ts_config.get("password")
    ts_token = ts_config.get("token")  # Optional pre-authenticated token

    # Initialize the API client
    if ts_token:
        logger.debug("🔑 Using pre-authenticated token")
        api = Api(token=ts_token)
    elif ts_user and ts_password:
        logger.debug(f"🔐 Authenticating as {ts_user}")
        api = Api(username=ts_user, password=ts_password)
    else:
        logger.error("❌ Truth Social credentials not configured!")
        raise ValueError("truth_social.user/password or truth_social.token required in settings")

    # Calculate cutoff time (24 hours ago) - must be timezone aware
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)

    recent_truths: list[str] = []

    try:
        # Fetch statuses - using created_after for efficient filtering
        logger.debug(f"📡 Pulling statuses for @{username} created after {cutoff_time}...")

        statuses = api.pull_statuses(username=username, created_after=cutoff_time)

        for status in statuses:
            # Extract the content
            content = status.get("content", "")
            if content:
                clean_content = _strip_html(content)

                if clean_content:
                    recent_truths.append(clean_content)
                    created_at = status.get("created_at", "unknown time")
                    logger.debug(f"✅ Found truth from {created_at}: {clean_content[:50]}...")

        logger.info(f"📊 Found {len(recent_truths)} truths from @{username} in the last 24 hours")

    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg or "Forbidden" in error_msg:
            logger.error(
                "❌ Blocked by Cloudflare (403 Forbidden). "
                "Truth Social uses aggressive bot protection. "
                "Try using a residential proxy or pre-authenticated token."
            )
        logger.exception(f"❌ Error fetching truths: {e}")
        raise

    return recent_truths


@tool
def get_trump_truths_last_24h() -> list[str]:
    """
    Get all of Donald Trump's Truth Social posts from the last 24 hours.

    Use this tool when you need to know what Trump has posted on Truth Social recently.
    This can be useful for tracking political statements, announcements, or policy hints.

    Returns:
        List of strings containing the text content of each truth from the last 24 hours.
        Returns an empty list if no truths were posted in that timeframe or if there's an error.
    """
    try:
        return _get_truths_last_24h(TRUMP_USERNAME)
    except Exception as e:
        logger.exception(f"❌ Failed to get Trump's truths: {e}")
        return []
