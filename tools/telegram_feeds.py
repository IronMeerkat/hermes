from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl
from hephaestus.settings import settings

from langchain_core.tools import tool
from logging import getLogger

import asyncio

logger = getLogger(__name__)

auths = settings.telegram.auths.model_dump()

client = TelegramClient(**auths)

async def _check_telegram_channels() -> list:
    messages = []
    async for channel in settings.telegram.channels:
        entity = await client.get_entity(channel)
        if entity is None:
            logger.warning(f"Channel {channel} not found")
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

    return messages

@tool
def check_telegram_channels() -> list[str]:
    return asyncio.run(_check_telegram_channels())

