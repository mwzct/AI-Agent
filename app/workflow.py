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

from app.llm import llm
from app.tools import add, multiply
from app.RAG import search_knowledge_base

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

tools = [add, multiply, search_knowledge_base]
llm_with_tools = llm.bind_tools(tools)

def assistant(state: AgentState, config: RunnableConfig,) -> dict:
    messages = list(state["messages"])

    configurable = config.get("configurable", {})
    memory_context = configurable.get("memory_context", "")

    system_content = (
        "你是一个可靠的中文 AI 智能旅行规划助手。"
        "你的工作如下："
        "- 根据出发地、目的地、日期、预算等成旅行方案"
        "- 结合用户偏好推荐景点、餐饮和交通"
        "- 对行程进行按天拆分，并说明时间、距离和安排理由"
        "- 基于本地目的地资料回答攻略问题，并标注信息来源"
        "- 在用户授权后记住稳定的旅行偏好，例如节奏、预算倾向和饮食限制"
        "当用户提供目的地信息时，优先调用 search_knowledge_base 工具检索相关资料。"
        "回答问题时，应以检索结果为依据。"
        "如果检索结果不足以回答问题，再联网搜索，不要编造资料。"
        "最终使用中文清晰地回答。"
    )

    if memory_context:
        system_content += (
                "以下是从长期记忆数据库中读取的用户信息。"
                "这些信息仅作为回答背景，如果与用户当前明确提供的信息冲突，以当前信息为准。\n"
                + memory_context
            )

    system_message = SystemMessage(content=system_content)
    message = [system_message] + messages

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