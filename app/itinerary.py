import json
import logging
import re

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


class RouteStop(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=180)


class RouteOption(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=240)
    destination: str = Field(min_length=1, max_length=80)
    stops: list[RouteStop] = Field(min_length=2, max_length=8)


class RoutePlan(BaseModel):
    routes: list[RouteOption] = Field(default_factory=list, max_length=3)


def extract_routes(llm, question: str, answer: str) -> list[RouteOption]:
    """Turn an existing answer into route choices without changing that answer."""
    prompt = (
        "你是旅行回答的结构化整理器，只提取下面回答中明确推荐的路线和地点。"
        "不要补造景点、坐标、交通耗时或开放时间。"
        "如果回答没有至少两个明确地点构成的路线，返回空 routes。"
        "最多输出3条路线，每条2到8个地点；destination 是城市名。"
        "地点要是回答中出现过、可在地图搜索的单一地点；不要用‘三件套’等集合名称。"
        "只返回 JSON 对象，不要 Markdown，格式："
        '{"routes":[{"title":"路线名称","description":"推荐理由和安排概要",'
        '"destination":"城市","stops":[{"name":"可地图搜索的具体地点名",'
        '"description":"该站的简短说明"}]}]}。\n'
        f"用户问题：{question}\nAgent 回答：{answer}"
    )
    try:
        content = llm.invoke(prompt).content
        if not isinstance(content, str):
            return []
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.I)
        return RoutePlan.model_validate(json.loads(cleaned)).routes
    except (ValueError, ValidationError, AttributeError, TypeError):
        return []
    except Exception:
        logger.exception("路线结构化失败，保留原始回答")
        return []
