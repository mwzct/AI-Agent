# 智能旅行规划助手

这是一个基于 FastAPI、LangGraph、LangChain 和 SQLite 的中文对话代理原型。项目目前完成了基础运行骨架：接收用户消息、调用大语言模型、按需调用工具、读取本地知识库，并保存少量长期用户偏好。现阶段的 `add`、`multiply` 等工具只是运行链路示例，不代表最终的旅行服务能力。

## 项目目标

项目后续将逐步演进为“智能旅行规划助手”，帮助用户完成：

- 根据出发地、目的地、日期、预算等成旅行方案
- 结合用户偏好推荐景点、餐饮和交通
- 对行程进行按天拆分，并说明时间、距离和安排理由
- 基于本地目的地资料回答攻略问题，并标注信息来源
- 在用户授权后记住稳定的旅行偏好，例如节奏、预算倾向和饮食限制

## 当前架构

```text
HTTP 客户端
    |
    v
FastAPI /chat
    |
    +--> 长期记忆提取 -> agent_memories.sqlite
    |
    +--> LangGraph 工作流
    |       |
    |       +--> 大语言模型
    |       +--> 示例计算工具
    |       +--> 本地 TF-IDF 知识库检索
    |
    +--> LangGraph 检查点 -> agent_checkpoints.sqlite
```

主要文件：

| 文件 | 作用 |
| --- | --- |
| `app/main.py` | FastAPI 应用、请求模型、`/health` 和 `/chat` 接口 |
| `app/workflow.py` | LangGraph 状态、模型调用和工具路由 |
| `app/llm.py` | 从环境变量读取模型、密钥和兼容 OpenAI 的服务地址 |
| `app/tools.py` | 当前的示例工具，后续替换为旅行领域工具 |
| `app/RAG.py` | 读取 `knowledge/` 下的 Markdown/TXT 并做 TF-IDF 检索 |
| `app/long_term_memory.py` | 提取和保存用户长期事实或偏好 |
| `tests/` | 当前已有的记忆提取和工作流单元测试 |

## 本地运行

建议使用项目自带的虚拟环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

准备 `.env`（不要提交到 Git），至少配置模型所需的密钥；如果使用兼容 OpenAI API 的服务，还可以配置：

```dotenv
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://your-compatible-endpoint/v1
LLM_MODEL=your-model
```

启动服务：

```powershell
uvicorn app.main:app --reload
```

接口示例：

```http
GET /health

POST /chat
Content-Type: application/json

{
  "message": "我计划 5 月去杭州玩 3 天，喜欢慢节奏和本地美食，请先给我一个行程思路。",
  "thread_id": "demo-user-001"
}
```

`thread_id` 用于维持 LangGraph 会话检查点；当前长期记忆数据库没有用户隔离，生产环境不能直接复用这种设计。

## 知识库使用方式

把经过整理的目的地资料放到 `knowledge/` 目录下，支持 `.md` 和 `.txt` 文件。适合放入：景点介绍、区域关系、交通常识、季节性建议和本地美食资料。当前索引在模块导入时一次性建立，新增或修改文件后需要重启服务才能生效。

建议后续为每条资料补充来源、更新时间、适用季节和城市字段，并在回答中保留来源，避免把过期攻略当成事实。

## 面向旅行助手的迭代路线

### 第一阶段：修复基础可靠性

- 修复 RAG 导入和检索返回逻辑，补齐空目录与无命中测试
- 将模型调用和外部工具调用封装为可超时、可重试的服务
- 将长期记忆改为按用户标识隔离，并增加查看、删除和纠错能力
- 增加 API、工作流和错误路径测试

### 第二阶段：替换为旅行领域工具

- `destination_search`：目的地和景点资料检索
- `route_planner`：城市内交通和景点顺序规划
- `weather_lookup`：按日期查询天气
- `opening_hours`：查询营业时间和闭馆日
- `budget_estimator`：按人数、天数和交通方式估算预算
- `itinerary_editor`：新增、删除、替换某一天的安排

所有外部工具都应返回来源、查询时间、置信度和失败状态；实时数据与本地知识库内容要明确区分。

### 第三阶段：形成可用的规划体验

- 用结构化的旅行需求模型收集目的地、日期、预算、偏好和限制条件
- 输出包含每日时间段、交通衔接、预计耗时、预算和备选方案的行程
- 支持用户逐轮修改，而不是每次重新生成整份计划
- 对高风险信息（签证、天气预警、营业状态、价格）要求确认来源或提示人工核验
- 增加评测集，检查事实性、行程可执行性、预算一致性和个性化程度