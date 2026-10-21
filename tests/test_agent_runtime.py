from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage

import app.long_term_memory as long_term_memory
import app.workflow as workflow_mod


def test_extract_and_save_memories(tmp_path, monkeypatch):
    db_path = tmp_path / "agent_memories.sqlite"
    monkeypatch.setattr(long_term_memory, "DB_PATH", db_path)
    long_term_memory.init_memory_db()

    class FakeLLM:
        def invoke(self, prompt):
            return SimpleNamespace(content='["用户叫小王，喜欢打篮球"]')

    long_term_memory.extract_and_save_memories(FakeLLM(), "我叫小王，我喜欢打篮球")

    assert long_term_memory.get_memories(limit=10) == ["用户叫小王，喜欢打篮球"]


def test_assistant_without_memory_context(monkeypatch):
    class FakeLLM:
        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            return AIMessage(content="你好，我可以直接回答。")

    monkeypatch.setattr(workflow_mod, "llm_with_tools", FakeLLM())

    result = workflow_mod.assistant(
        {"messages": [HumanMessage(content="你好")]},
        {"configurable": {}},
    )

    assert result["messages"][0].content == "你好，我可以直接回答。"
