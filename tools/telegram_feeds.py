import asyncio
from logging import getLogger

from langchain_core.tools import tool
from telethon import TelegramClient

from hephaestus.settings import settings

logger = getLogger(__name__)

auths = settings.telegram.auths.model_dump()


async def _check_telegram_channels() -> list:
    """Uses the session file from settings only—never calls start() (no interactive login)."""
    messages = []
    client = TelegramClient(**auths)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            logger.error(
                "📵 Telegram session is not authorized. Log in once with Telethon locally so "
                "%s.session is created, then use that file here—this tool does not prompt for creds.",
                auths.get("session", "session"),
            )
            return messages

        for channel in settings.telegram.channels:
            entity = await client.get_entity(channel)
            if entity is None:
                logger.warning("⚠️ Channel %s not found", channel)
                continue

            async for m in client.iter_messages(entity, limit=10):
                # Skip service messages (joins, pins) unless you want them
                if m.message is None and not m.media:
                    continue
                messages.append({
                    'channel': channel,
                    'text': m.message,
                    'date': m.date.strftime('%Y-%m-%d %H:%M:%S'),
                })
    except Exception:
        logger.exception("📵 Telegram channel check failed")
        raise
    finally:
        await client.disconnect()

    return messages

@tool
def check_telegram_channels() -> list[str]:
    """Check the latest messages from the Telegram channels"""
    return asyncio.run(_check_telegram_channels())
