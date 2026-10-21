import json
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "agent_memories.sqlite"

def init_memory_db():
    with sqlite3.connect(str(DB_PATH), timeout=10) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories(
                id INTEGER PRIMARY KEY AUTOINCREMENT,     
                memory TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

def extract_and_save_memories(llm, user_message: str):
    """从用户信息中提取长期事实并保存。"""
    
    prompt = f"""
        你是一个长期记忆提取器。

        请从下面的用户消息中，提取适合未来对话使用的、
        用户明确表达的长期事实、偏好或目标。

        规则：
        1. 只提取用户明确陈述的事实，不要推测。
        2. 忽略普通问题、临时任务和假设情境。
        3. 不要保存密码、API密钥、身份证号、健康等敏感信息。
        4. 每条记忆用简短的中文独立表达。
        5. 如果没有适合保存的内容，返回空数组。
        6. 只输出合法 JSON 数组，不要添加解释或 Markdown。

        示例：
        用户消息：我叫小王，我喜欢打篮球。
        输出：["用户叫小王,喜欢打篮球"]

        用户信息：
        {json.dumps(user_message, ensure_ascii=False)}

        请输出JSON数组：
    """

    try:
        response = llm.invoke(prompt)
        raw = response.content

        if not isinstance(raw, str):
            return

        raw = raw.strip()

        if raw.startswith("```"):
            lines = raw.splitlines()
            filtered_lines = [
                line for line in lines
                if not line.strip().startswith("```")
            ]
            raw = "\n".join(filtered_lines).strip()

        facts = json.loads(raw)

        if not isinstance(facts, list):
            return

        with sqlite3.connect(str(DB_PATH), timeout=10) as conn:
            for fact in facts[:5]:
                if not isinstance(fact, str):
                    continue

                fact = fact.strip()

                if not fact or len(fact) > 200:
                    continue

                conn.execute(
                    "INSERT OR IGNORE INTO memories (memory) VALUES (?)",
                    (fact,),
                )

        logger.info("长期记忆提取成功，候选数量：%s", len(facts))

    except Exception:
        logger.exception("长期记忆提取失败")

def get_memories(limit: int = 10) -> list[str]:
    """读取长期记忆"""

    with sqlite3.connect(str(DB_PATH), timeout=10) as conn:
        rows = conn.execute(
            """
            SELECT memory
            FROM memories
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [row[0] for row in reversed(rows)]