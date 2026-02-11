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

telegram_router = APIRouter(
    prefix="/telegram",
    dependencies=[telegram_webhook_authentication]
)

def produce_response(text: str) -> str:
    response = main_agent.invoke({"messages": [HumanMessage(content=text)]},
                                 RunnableConfig(callbacks=[langfuse_callback_handler]))
    return response.content

def send_telegram_message(chat_id: int, text: str) -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    resp = requests.post(url, json=payload, timeout=10)
    logger.debug(f"📤 Telegram message sent: {resp.json()}")

def process_and_respond(chat_id: int, text: str) -> None:
    """Background task: produce response and send it via Telegram."""
    logger.info(f"🤖 Processing message for chat_id={chat_id}")
    response_text = produce_response(text)
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
