from langchain.messages import (
    AnyMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage)
from typing_extensions import TypedDict, Annotated
import operator
from pydantic import BaseModel
from typing import Literal

from langchain.tools import tool
from langchain_xai import ChatXAI
from hephaestus.langfuse_handler import langfuse_callback_handler
from logging import getLogger
from langgraph.graph import END, StateGraph, START

from agents.yahoo_finance import financial_analyst_tool
from tools.pizza_index import get_pentagon_restaurants_activity_spike
from tools.telegram_feeds import check_telegram_channels


logger = getLogger(__name__)

_model = ChatXAI(model="grok-4-1-fast-reasoning", temperature=1)

_tools = [financial_analyst_tool, get_pentagon_restaurants_activity_spike, check_telegram_channels]
tools_by_name = {tool.name: tool for tool in _tools}

model = _model.bind_tools(tools_by_name)

logger.info("Main model ready, creating agent")

class MainAgentState(BaseModel):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int = 0

def llm_call(state: MainAgentState):
    """LLM decides whether to call a tool or not"""

    return {
        "messages": [
            model.invoke(
                [
                    SystemMessage(
                        content="You are a helpful assistant tasked with performing arithmetic on a set of inputs."
                    )
                ]
                + state.messages
            )
        ],
        "llm_calls": state.llm_calls + 1
    }

def tool_node(state: MainAgentState):
    """Performs the tool call"""

    result = []
    for tool_call in state.messages[-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
    return {"messages": result}

def should_continue(state: MainAgentState) -> Literal["tool_node", END]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    messages = state.messages
    last_message = messages[-1]

    # If the LLM makes a tool call, then perform an action
    if last_message.tool_calls:
        return "tool_node"

    # Otherwise, we stop (reply to the user)
    return END


agent_builder = StateGraph(MainAgentState)

# Add nodes
agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("tool_node", tool_node)

# Add edges to connect nodes
agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges(
    "llm_call",
    should_continue,
    ["tool_node", END]
)
agent_builder.add_edge("tool_node", "llm_call")

# Compile the agent
main_agent = agent_builder.compile()