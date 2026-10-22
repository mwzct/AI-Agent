from types import SimpleNamespace

from langchain_core.messages import HumanMessage

from app.itinerary import extract_routes
from app import workflow as workflow_mod


class FakeLLM:
    def __init__(self, content):
        self.content = content

    def invoke(self, prompt):
        return SimpleNamespace(content=self.content)


def test_extract_routes_from_json_fence():
    content = '''```json
{"routes":[{"title":"上海经典步行线","description":"适合初次到访", "destination":"上海", "stops":[{"name":"外滩","description":"看江景"},{"name":"豫园","description":"逛老城"}]}]}
```'''
    routes = extract_routes(FakeLLM(content), "上海玩两天", "外滩到豫园")

    assert len(routes) == 1
    assert routes[0].destination == "上海"
    assert [stop.name for stop in routes[0].stops] == ["外滩", "豫园"]


def test_extract_routes_falls_back_on_bad_or_incomplete_data():
    assert extract_routes(FakeLLM("not json"), "你好", "你好") == []
    assert extract_routes(FakeLLM('{"routes":[{"title":"路线","destination":"上海","stops":[{"name":"外滩"}]}]}'), "上海", "外滩") == []


def test_retrieval_context_is_a_graph_state_channel(monkeypatch):
    monkeypatch.setattr(workflow_mod, "retrieve_documents", lambda question: f"本轮资料：{question}")
    result = workflow_mod.retrieve({"messages": [HumanMessage(content="上海两天怎么玩")]})

    assert result["knowledge_context"] == "本轮资料：上海两天怎么玩"
    assert "knowledge_context" in workflow_mod.workflow.channels
