from langchain.messages import (
    AnyMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
)
from typing_extensions import TypedDict, Annotated
import operator

from langchain.tools import tool
from langchain_anthropic import ChatAnthropic
from hephaestus.langfuse_handler import langfuse_callback_handler

from tools.yahoo_finance import finance_tools
from langchain.agents import create_agent


_model = ChatAnthropic(model="claude-sonnet-4-5", temperature=0.1)

# model = _model.bind_tools(finance_tools)


# class FinanceAnalystState(TypedDict):
#     messages: Annotated[list[AnyMessage], operator.add]
#     llm_calls: int

financial_analyst_agent = create_agent(
    model=_model,
    tools=finance_tools)

@tool
def financial_analyst_tool(query: str) -> str:
    """A financial analyst agent that can help with financial analysis"""
    return financial_analyst_agent.invoke({"input": query})["output"]

financial_analyst_tool.name = "financial_analyst"
financial_analyst_tool.description = "A financial analyst agent that can help with financial analysis"