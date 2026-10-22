# 行迹：智能旅行规划助手

行迹是一个中文旅行规划对话原型。浏览器客户端负责收集问题和展示回答；FastAPI 接收请求，调用 LangGraph Agent，并返回文字结果。工作流包含本地资料检索节点，模型也可以按需调用知识库检索或 Tavily 联网搜索工具。

目前它适合演示和迭代旅行问答流程，**还不是可直接依赖的订票或实时行程服务**。行程、价格、开放时间等信息仍需核实。

## 已实现的功能

- 浏览器聊天界面：输入问题、快捷填入示例问题、查看回复与请求错误、开始新会话。
- `POST /chat`：接受消息和 `thread_id`，返回文字回答和可选路线；`GET /health` 用于健康检查。
- LangGraph 工作流：每轮先执行本地检索节点并把结果交给模型；模型可按需继续调用本地检索或联网搜索。
- 路线结构化：额外调用一次模型，从本轮回答中提取最多 3 条路线及各站点；提取失败时只返回原文字回答。
- 地图预览：选择路线后，在 OpenStreetMap 底图上逐个定位并标记地点，以虚线表示访问顺序。
- 本地知识库：读取 `knowledge/` 下的 Markdown/TXT，使用字符级 TF-IDF 检索并返回片段及文件来源。目前仓库中的资料主要关于上海。
- 会话检查点：SQLite 保存同一 `thread_id` 的对话上下文。
- 长期记忆雏形：每次提问前尝试从消息中提取稳定事实或偏好，保存到 SQLite，并将最近的记忆提供给 Agent。

## 请求流程

```text
浏览器 client/  -- POST /chat -->  FastAPI app/main.py
                                    |-- 提取、读取长期记忆 -> agent_memories.sqlite
                                    `-- LangGraph app/workflow.py
                                          |-- 检索 knowledge/ 的当前内存索引
                                          |-- 调用大语言模型
                                          |-- 按需调用知识库或 Tavily 搜索
                                          `-- 保存会话 -> agent_checkpoints.sqlite
                         <-- {"answer": "...", "routes": [...]} --
```

| 路径 | 作用 |
| --- | --- |
| `client/` | 无构建步骤的 HTML/CSS/JavaScript 客户端 |
| `app/main.py` | 托管客户端，提供 `/health`、`/chat` |
| `app/workflow.py` | 检索节点、Agent、工具路由、会话检查点与系统提示词 |
| `app/RAG.py` | 加载文档、切分、构建 TF-IDF 索引及检索 |
| `app/tools.py` | Tavily 联网搜索工具 |
| `app/llm.py` | 模型客户端配置 |
| `app/long_term_memory.py` | 长期记忆提取与 SQLite 存取 |
| `app/itinerary.py` | 从回答中提取并校验路线卡片数据 |
| `knowledge/` | 本地目的地资料 |
| `tests/` | 现有少量单元测试 |

## 本地运行

在项目根目录使用已有的 `.venv`；若重新创建环境，当前仓库**尚无锁定的依赖清单**，需要安装 FastAPI、Uvicorn、LangChain、LangGraph、LangGraph SQLite checkpointer、LangChain OpenAI/Tavily、scikit-learn、python-dotenv 等依赖，并按实际环境固定版本。

在项目根目录准备 `.env`，不要提交密钥。项目读取以下变量：

```dotenv
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://your-compatible-endpoint/v1
LLM_MODEL=deepseek-chat
TAVILY_API_KEY=your-tavily-key
```

`OPENAI_BASE_URL` 可省略，届时使用 OpenAI 兼容客户端的默认地址；`LLM_MODEL` 默认 `deepseek-chat`。启用联网搜索需要有效的 Tavily 密钥。应用初始化时会创建 SQLite 数据库文件。

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

打开 `http://127.0.0.1:8000/` 使用客户端；`http://127.0.0.1:8000/docs` 查看 API 文档。客户端与 API 由同一 FastAPI 服务提供，无需单独启动前端开发服务器。

接口调用示例：

```http
POST /chat
Content-Type: application/json

{
  "message": "我想去上海玩两天，喜欢城市漫步和本地美食",
  "thread_id": "travel-demo-001"
}
```

成功响应包含 `answer` 和 `routes`。`routes` 每项包含 `title`、`description`、`destination`、`stops`，每个站点有 `name`、`description`；普通问答或提取失败时 `routes` 为空数组。请求失败时接口返回错误状态，客户端显示错误提示。路线整理会额外消耗一次模型请求。

## 知识库与会话

把 UTF-8 编码的 `.md` 或 `.txt` 文件放入 `knowledge/`。索引在 `app/RAG.py` **首次导入时**构建：新增或修改资料后需要重启服务；仅刷新浏览器或更换 `thread_id` 不会更新已加载的索引。

工作流每轮都会重新查询**当前进程中的索引**，并通过 `knowledge_context` 状态字段传入模型。不过检索问题直接使用最新一条用户消息，像“第二天呢？”这样的省略式追问可能匹配不到目的地。TF-IDF 也不保证每次都找出真正相关的资料，回答中的来源应人工核对。

地图依赖浏览器加载 Leaflet 和 OpenStreetMap 瓦片。点击路线卡片后，客户端按不超过每秒一次的速度查询 Nominatim 公开地理编码服务；找不到的站点不会被标记。地图上的虚线是站点顺序示意，**不是真实道路导航**。地点名称会发送到第三方定位服务，部署前应核对其使用政策与隐私要求。

客户端把 `thread_id` 保存在当前标签页的 `sessionStorage` 中；右上角重置按钮会生成新编号并清空页面消息，**不会删除**服务端旧检查点或长期记忆。刷新页面会清空可见消息，但同一标签页仍可沿用原会话编号与服务端上下文。

长期记忆目前没有用户身份隔离，所有会话共享同一记忆库；提取也不是以用户明确授权为前提。因此不要在多人或生产环境中直接使用，也不要输入敏感个人信息。

## 当前限制与下一步

- 尚无路线距离计算、天气、营业时间、票价或预订接口；联网搜索结果也不能替代官方实时信息。
- 路线卡片依赖模型从文字中提取地点，不保证每次生成，也不保证地理编码一定命中；仍需核对地点准确性。
- 客户端没有结构化日程编辑、历史会话列表或来源的独立展示。
- 增加可刷新索引机制、会话感知的检索问题构造，以及更可靠的相关性判断。
- 为长期记忆增加用户隔离、明确授权和查看/删除能力。
- 补齐依赖清单，以及 API、RAG、工作流和客户端的测试。当前 `tests/` 覆盖记忆提取、一次 Agent 回答、路线 JSON 校验和检索状态字段，尚未覆盖浏览器地图交互的自动化测试。

运行现有测试：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
