from deepagents import create_deep_agent, CompiledSubAgent
from logging import getLogger
from langchain_xai import ChatXAI
from hephaestus.langfuse_handler import langfuse_callback_handler
from agents.yahoo_finance import financial_analyst_agent
from tools.pizza_index import get_pentagon_restaurants_activity_spike
from tools.telegram_feeds import check_telegram_channels
from langgraph.graph import END, StateGraph, START
from typing_extensions import TypedDict, Annotated
import operator
from langchain_core.messages import AnyMessage, RemoveMessage, AIMessage

logger = getLogger(__name__)

model = ChatXAI(model="grok-4-1-fast-reasoning", temperature=1, callbacks=[langfuse_callback_handler])


tools = [get_pentagon_restaurants_activity_spike, check_telegram_channels]
subagents = [CompiledSubAgent(name="financial-analyst", description="A financial analyst agent that can help with financial analysis", runnable=financial_analyst_agent)]

class MainAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]

main_agent = create_deep_agent(
    model=model,
    system_prompt="You are an OSINT gatheting and analyzing assistant.",
    tools=tools,
    subagents=subagents)


# def mark_final(state: MainAgentState) -> MainAgentState:
#     """Marks the last message with is_final: True metadata 🏁"""
#     last_msg = state["messages"][-1]
#     new_last_msg = AIMessage(content=last_msg.content, response_metadata=last_msg.response_metadata)
#     logger.info(f"new_last_msg: {new_last_msg.id}, last_msg: {last_msg.id}")
#     return {"messages": [RemoveMessage(id=last_msg.id), new_last_msg]}

# # Build the 2-node wrapper graph
# graph_builder = StateGraph(MainAgentState)

# graph_builder.add_node("agent", _main_agent)
# graph_builder.add_node("finalize", mark_final)

# graph_builder.add_edge(START, "agent")
# graph_builder.add_edge("agent", "finalize")
# graph_builder.add_edge("finalize", END)

# main_agent = graph_builder.compile()