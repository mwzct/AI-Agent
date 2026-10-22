# 行迹 · 智能旅行规划助手

行迹是一个正在开发中的中文旅行规划助手。你可以在浏览器里描述目的地、天数和偏好；后端检索本地攻略、调用 Agent 生成建议，并把回答中的行程整理成可选择的路线卡片。选择卡片后，地图会标出沿途地点。

项目目前是**功能原型**：地图连线不是导航路线，景点开放时间、票价、交通耗时等信息需要另行核实，也不提供预订服务。

## 现在可以做什么

1. 在客户端提问或使用快捷示例，围绕同一个会话继续追问。
2. Agent 每轮先检索 `knowledge/` 中的本地资料，再生成中文回答；必要时可以调用本地检索或 Tavily 联网搜索工具。
3. 后端从回答中提取最多 3 条路线，每条包含简介和 2～8 个站点。没有明确路线或提取失败时，仍返回原文字回答，路线列表为空。
4. 点击路线卡片的“选择并查看地图”，在 OpenStreetMap 地图上显示定位成功的站点和访问顺序示意线。
5. 用 `thread_id` 维持对话上下文。项目还有一个长期记忆雏形，会尝试保存用户表达的稳定偏好。

上海是目前主要的示例知识库目的地；其他城市的回答效果取决于新增资料和联网搜索结果。

## 快速开始

在项目根目录执行。若已有 `.venv`，可直接使用；若需新建环境，当前仓库还没有版本锁定的依赖文件，可先安装所需包：

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install fastapi uvicorn langchain langchain-openai langchain-tavily langgraph langgraph-checkpoint-sqlite scikit-learn python-dotenv pytest
```

在项目根目录创建 `.env`，填入你自己的密钥和模型地址，不要提交该文件。下面是使用 DeepSeek 兼容接口时的示例；若使用别的服务，请相应修改模型名和地址。

```dotenv
OPENAI_API_KEY=your-model-api-key
OPENAI_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
TAVILY_API_KEY=your-tavily-api-key
```

`OPENAI_BASE_URL` 未设置时，模型客户端使用默认服务地址；`LLM_MODEL` 未设置时默认为 `deepseek-chat`。联网搜索需要有效的 Tavily 密钥。

启动 FastAPI：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

打开 [客户端](http://127.0.0.1:8000/) 开始对话，或访问 [API 文档](http://127.0.0.1:8000/docs)。前端由 FastAPI 直接托管，不需要单独启动前端服务。首次运行会在项目目录中创建 SQLite 数据库文件。

## 使用示例

在页面输入“我想去上海玩两天，第一次去，请推荐一个节奏轻松的行程”。有明确路线时，页面会在文字回答下面展示路线卡片；点击其中一张，右侧地图会定位其站点。找不到的地点会跳过，并在地图状态中提示。

也可以直接调用接口：

```http
POST /chat
Content-Type: application/json

{
  "message": "我想去上海玩两天，喜欢城市漫步和本地美食",
  "thread_id": "travel-demo-001"
}
```

响应结构如下（内容仅为格式示例，不是固定行程）：

```json
{
  "answer": "两天可以分别安排浦西和浦东……",
  "routes": [
    {
      "title": "浦西经典线",
      "description": "适合初次到访，步行和地铁结合。",
      "destination": "上海",
      "stops": [
        {"name": "豫园", "description": "逛园林和老街。"},
        {"name": "外滩", "description": "欣赏黄浦江景。"}
      ]
    }
  ]
}
```

`answer` 始终是文字；`routes` 可能是空数组。路线整理会在 Agent 回答之后**额外调用一次模型**，因此会增加耗时和调用成本。`GET /health` 返回服务健康状态。

## 实现方式

```text
浏览器 client/
   │  提问、展示回答和路线卡片
   ▼
FastAPI /chat ── 提取/读取长期记忆 ── agent_memories.sqlite
   │
   ▼
LangGraph：本地检索 → Agent ↔ 知识库/Tavily 工具
   │                          └─ 会话检查点 → agent_checkpoints.sqlite
   ▼
路线结构化：从最终回答提取路线 JSON
   │
   └─ 返回 answer + routes → 用户选择卡片 → 浏览器定位地点并绘制地图
```

| 位置 | 职责 |
| --- | --- |
| `client/` | 页面、路线卡片、地图交互 |
| `app/main.py` | FastAPI 页面托管、`/chat` 和 `/health` |
| `app/workflow.py` | 系统提示词、每轮检索、Agent 工具调用和会话状态 |
| `app/RAG.py` | 加载本地文档、TF-IDF 检索 |
| `app/itinerary.py` | 提取并校验路线数据 |
| `app/tools.py` | Tavily 联网搜索 |
| `app/long_term_memory.py` | 长期记忆提取和 SQLite 存取 |
| `knowledge/` | Markdown/TXT 目的地资料 |
| `tests/` | 基础单元测试 |

## 知识库、地图与会话注意事项

- 本地知识库支持 `knowledge/` 下的 `.md` 和 `.txt` 文件。`app/RAG.py` 首次导入时建立索引；**修改资料后要重启服务**，只刷新浏览器或更换 `thread_id` 不会更新索引。
- 工作流每轮检索最新用户消息，并把结果交给 Agent。省略目的地的追问（如“第二天呢？”）可能检索不准；TF-IDF 命中也不等于事实正确。
- 地图在浏览器端加载 Leaflet、OpenStreetMap 瓦片，并向 Nominatim 发送地点名称进行定位，需要联网。虚线仅表示站点顺序，**不是步行、驾车或公共交通的实际路径**。公开定位服务有使用限制，不适合直接承担大规模生产流量。
- 客户端的 `thread_id` 保存在当前标签页的 `sessionStorage`。刷新页面会清空可见消息，但同一标签页仍可沿用服务端对话上下文；点击重置只会创建新编号，**不会删除**旧检查点或长期记忆。
- 长期记忆目前不按用户隔离，也没有授权、查看和删除流程。不要在多人或生产环境中直接使用，更不要输入敏感个人信息。

## 测试与后续工作

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

现有测试覆盖记忆提取、Agent 基础回答、路线 JSON 校验和检索状态字段；浏览器地图交互已做过一次上海路线的人工验证，但尚无自动化端到端测试。

下一步优先考虑：补齐并锁定依赖、按用户隔离长期记忆、让省略式追问也能构造准确检索词、支持知识库热更新，以及接入可验证的路线/交通数据和结构化行程编辑。当前模型生成的建议与第三方地图定位结果都需要用户核对。
