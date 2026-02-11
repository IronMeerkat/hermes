
from fastapi import Request
from fastapi.exceptions import HTTPException
from fastapi import Body, Header, Depends

from hephaestus.settings import settings

token_header = Header('', alias="X-Telegram-Bot-Api-Secret-Token")

@Depends
async def telegram_webhook_authentication(tg_token: str = token_header):
    if tg_token != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid secret key")

