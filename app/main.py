from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pathlib import Path

from app.llm import llm
from app.workflow import workflow
from app.long_term_memory import init_memory_db, extract_and_save_memories, get_memories
from app.itinerary import RouteOption, extract_routes

app = FastAPI(
    title="My AI Agent",
    description="这是一个基于DeepSeek、LangChain、LangGraph和FastAPI的中文AI助手。",
    version="0.1.0",
)

CLIENT_DIR = Path(__file__).resolve().parent.parent / "client"
app.mount("/client", StaticFiles(directory=CLIENT_DIR), name="client")

@app.get("/", include_in_schema=False)
def client入口():
    return FileResponse(CLIENT_DIR / "index.html")

init_memory_db()

class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=4000,
        description="用户发送的消息。",
    )

    thread_id:str = Field(
        min_length=1,
        max_length=100,
        description="会话编号。",
    )

class ChatResponse(BaseModel):
    answer: str
    routes: list[RouteOption] = Field(default_factory=list)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        extract_and_save_memories(llm, request.message)

        memories = get_memories(limit=10)
        memory_context = "\n".join(
            f"-{memory}" for memory in memories
        )
        
        result = workflow.invoke(
            {"messages": [{"role": "user", "content": request.message,}]},
            config={
                "configurable": {
                    "thread_id": request.thread_id,
                    "memory_context": memory_context,
                    "recursion_limit": 20,
                }
            }
        )

        messages = result["messages"]
        answer = None

        for message in reversed(messages):
            if message.type == "ai" and not getattr(
                message, "tool_calls", None            
            ):
                answer = message.content
                break

        if answer is None:
            raise RuntimeError("Agent没有生成最终回答")

        if not isinstance(answer, str):
            answer = str(answer)

        routes = extract_routes(llm, request.message, answer)
        return ChatResponse(answer=answer, routes=routes)
    
    except Exception as exc:
        print(f"Agent执行失败:{type(exc).__name__}: {exc}")

        raise HTTPException(
            status_code=500,
            detail="Agent执行失败，请检查服务端日志。"
        )from exc
