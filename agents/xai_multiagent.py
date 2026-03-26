import operator
from logging import getLogger

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from typing_extensions import Annotated, TypedDict
from xai_sdk import Client
from xai_sdk.chat import user
from xai_sdk.tools import web_search as xai_web_search, x_search

logger = getLogger(__name__)

grok_multi_agent_subagent_description = (
    "Deep research using xAI Grok multi-agent orchestration (web search + X, multiple coordinated agents). "
    "Use for multi-step, broad, or evidence-heavy questions that need cross-checking and synthesis. "
    "Slower and higher cost than a single tool or quick lookup; avoid for trivial one-line facts."
)


class GrokMultiAgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]


def _research_query_from_messages(messages: list[AnyMessage]) -> str:
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            c = m.content
            if isinstance(c, str):
                return c
            if isinstance(c, list):
                parts: list[str] = []
                for block in c:
                    if isinstance(block, dict) and block.get("type") == "text":
                        parts.append(str(block.get("text", "")))
                    elif isinstance(block, str):
                        parts.append(block)
                return "\n".join(parts) if parts else str(c)
            return str(c)
    raise ValueError("🔎 Grok multi-agent: no HumanMessage in state")


def _run_grok_multi_agent_research(research_query: str) -> str:
    client = Client()
    chat = client.chat.create(
        model="grok-4.20-multi-agent",
        tools=[xai_web_search(), x_search()],
        agent_count=4,
    )
    chat.append(user(research_query))
    response = chat.sample()
    text = response.content
    u = response.usage
    logger.info(
        f"🔎 Grok multi-agent research done ({u.prompt_tokens=}, {u.completion_tokens=})"
    )
    return text


def _grok_multi_agent_node(state: GrokMultiAgentState) -> dict:
    """Run xAI Grok multi-agent deep research (web + X) and append the synthesized answer.

    Use for multi-step, broad, or evidence-heavy questions where coordinated search and
    cross-checking help. Slower and more expensive than a quick web lookup.
    """
    query = _research_query_from_messages(state["messages"])
    try:
        text = _run_grok_multi_agent_research(query)
    except Exception as e:
        logger.exception(f"🔎 Grok multi-agent research failed: {e}")
        text = f"Multi-agent research failed: {e!s}"
    return {"messages": [AIMessage(content=text)]}


_builder = StateGraph(GrokMultiAgentState)
_builder.add_node("research", _grok_multi_agent_node)
_builder.add_edge(START, "research")
_builder.add_edge("research", END)

grok_multi_agent_research_agent = _builder.compile(name="grok-multi-agent-research")
