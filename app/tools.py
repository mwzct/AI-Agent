import os

from langchain.tools import tool
from langchain_tavily import TavilySearch

search_client = TavilySearch(
    max_results=5,
    topic="general",
    search_api_key=os.getenv("TAVILY_API_KEY"),
)

@tool
def web_search(query: str) -> str:
    """搜索互联网，获取最新网页信息。

    当用户询问最新新闻、天气预报、旅游攻略、
    景点最新开放信息等需要联网查询的内容时调用。
    query: 需要搜索的内容。
    """
    result = search_client.invoke({"query": query})
    return str(result)