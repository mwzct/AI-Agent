from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

import sqlite3
from pathlib import Path

from app.agent import llm
from app.tools import add, multiply

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

tools = [add, multiply]
llm_with_tools = llm.bind_tools(tools)

def assistant(state: AgentState, config: RunnableConfig,) -> dict:
    messages = list(state["messages"])

    configurable = config.get("configurable", {})
    memory_context = configurable.get("memory_context", "")
    message = messages

    if memory_context:
        memory_message = SystemMessage(
            content=(
                "以下是从长期记忆数据库中读取的用户信息。"
                "这些信息仅作为回答背景，如果与用户当前明确提供的信息冲突，以当前信息为准。\n"
                + memory_context
            )
        )
        message = [memory_message] + messages

    response = llm_with_tools.invoke(message)
    return {"messages": [response]}

builder = StateGraph(AgentState)

builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(tools))

builder.add_edge(START, "assistant")

builder.add_conditional_edges("assistant", tools_condition,)

builder.add_edge("tools", "assistant")

DB_PATH = Path(__file__).resolve().parent.parent / "agent_checkpoints.sqlite"

conn = sqlite3.connect(
    str(DB_PATH),
    check_same_thread=False,
)

memory = SqliteSaver(conn)
memory.setup()

workflow = builder.compile(checkpointer=memory)