import operator
from logging import getLogger

from deepagents import create_deep_agent, CompiledSubAgent
from langchain_core.messages import AIMessage, AnyMessage, RemoveMessage
from langchain_xai import ChatXAI
from langgraph.graph import END, START, StateGraph
from typing_extensions import Annotated, TypedDict

from hephaestus.langfuse_handler import langfuse, langfuse_callback_handler

from agents.yahoo_finance import financial_analyst_agent
from tools.pizza_index import pentagon_activity_spike
from tools.telegram_feeds import check_telegram_channels

logger = getLogger(__name__)

model = ChatXAI(model="grok-4-1-fast-reasoning", temperature=1, callbacks=[langfuse_callback_handler])

financial_analyst_description = langfuse.get_prompt("financial-analyst-description").prompt
osing_prompt = langfuse.get_prompt("osint-prompt").prompt

tools = [pentagon_activity_spike, check_telegram_channels]
subagents = [
    CompiledSubAgent(name="financial-analyst",
                     description=financial_analyst_description,
                     runnable=financial_analyst_agent)
    ]

class MainAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]

main_agent = create_deep_agent(
    model=model,
    system_prompt=osing_prompt,
    tools=tools,
    subagents=subagents)
