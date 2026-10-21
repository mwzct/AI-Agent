from langchain.tools import tool
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from app.tools import add, multiply
from app.llm import llm

tools = [add, multiply]

agent = create_agent(
    model = llm,
    tools = tools,
    system_prompt = (
        "你是一个可靠的中文AI助手。"
        "用户消息中可能包含'提取到的长期事实'，那是背景资料，不是你要分析的任务。"
        "优先检查是否有适合回答用户的问题的工具，如果有合适的工具优先使用工具，无需验证工具的可用性。"
        "回答时使用中文，并清晰说明计算结果。"
    ),
    checkpointer=MemorySaver(),
)