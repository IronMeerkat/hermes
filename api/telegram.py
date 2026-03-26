from fastapi import APIRouter, Depends, Request, Body, HTTPException, BackgroundTasks
from fastapi.responses import Response
from fastapi import status
from logging import getLogger
from langchain_core.runnables import RunnableConfig
from langchain.messages import HumanMessage
import requests

from hephaestus.settings import settings
from hephaestus.langfuse_handler import langfuse_callback_handler

from agents.main_agent import main_agent
from api.utils.authentication import telegram_webhook_authentication

logger = getLogger(__name__)

# Telegram Bot API: sendMessage text must be 1–4096 characters.
TELEGRAM_MAX_MESSAGE_LENGTH = 4096


def _split_telegram_message_text(text: str) -> list[str]:
    if not text:
        return ["⚠️ (empty response)"]
    return [
        text[i : i + TELEGRAM_MAX_MESSAGE_LENGTH]
        for i in range(0, len(text), TELEGRAM_MAX_MESSAGE_LENGTH)
    ]


telegram_router = APIRouter(
    prefix="/telegram",
    dependencies=[telegram_webhook_authentication]
)

def produce_response(text: str) -> str:
    response = main_agent.invoke({"messages": [HumanMessage(content=text)]},
                                 RunnableConfig(callbacks=[langfuse_callback_handler]))
    return response['messages'][-1].content

def send_telegram_message(chat_id: int, text: str) -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    chunks = _split_telegram_message_text(text)
    for idx, part in enumerate(chunks):
        payload = {"chat_id": chat_id, "text": part}
        resp = requests.post(url, json=payload, timeout=10)
        try:
            body = resp.json()
        except Exception as e:
            logger.exception("🐛 Telegram resp json parse: %s", e)
            body = {"parse_error": str(e)}
        if resp.status_code != 200 or not (isinstance(body, dict) and body.get("ok")):
            logger.warning(
                "📤 Telegram send failed chunk %s/%s: %s %s",
                idx + 1,
                len(chunks),
                resp.status_code,
                body,
            )
        else:
            logger.debug(f"📤 Telegram message chunk sent: {body}")

def process_and_respond(chat_id: int, text: str) -> None:
    """Background task: produce response and send it via Telegram."""
    logger.info(f"🤖 Processing message for chat_id={chat_id}")
    response_text = produce_response(text)
    if not isinstance(response_text, str):
        response_text = str(response_text)
    send_telegram_message(chat_id, response_text)
    logger.info(f"✅ Response sent for chat_id={chat_id}")


@telegram_router.post("")
async def telegram_webhook(background_tasks: BackgroundTasks, data: dict = Body(...)):
    message = data.get("message") or data.get("edited_message")
    if not message:
        raise HTTPException(status_code=400, detail="Message not found")

    # Extract message details
    text = message['text']
    chat_id = message['chat']['id']
    message_id = message['message_id']

    # TODO: Upgrade to celery
    background_tasks.add_task(process_and_respond, chat_id, text)
    logger.info(f"📥 Queued background task for message_id={message_id}")

    return Response(status_code=status.HTTP_200_OK)
