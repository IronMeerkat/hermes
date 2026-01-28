from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable, RunnableConfig
from langchain.messages import HumanMessage, AIMessageChunk
from typing import cast

import chainlit as cl

from agents.main_agent import main_agent
from hephaestus.logging import init_logger
from hephaestus.langfuse_handler import langfuse_callback_handler
from logging import getLogger

init_logger()

logger = getLogger(__name__)


logger.info("Starting Hermes demo")

# @cl.on_chat_start
# async def on_chat_start():

#     runnable = main_agent | StrOutputParser()
#     cl.user_session.set("runnable", main_agent)


@cl.on_message
async def on_message(cl_message: cl.Message):
    config = {"configurable": {"thread_id": cl.context.session.id}}
    callbacks = [cl.LangchainCallbackHandler(), langfuse_callback_handler]
    final_answer = cl.Message(content="")

    for msg, metadata in main_agent.stream({"messages": [HumanMessage(content=cl_message.content)]}, stream_mode="messages", config=RunnableConfig(callbacks=callbacks, **config)):
        if isinstance(msg, AIMessageChunk):
            await final_answer.stream_token(msg.content)

    await final_answer.send()