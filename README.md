# 金融研报智能分析助手

基于 LLM + LangGraph 的金融研报智能分析系统，支持自然语言查询股票数据、财务分析、代码执行可视化和实时市场资讯检索。项目由 FastAPI 后端和 Vue 3 前端组成。

## 功能特性

- **多智能体协作**：Router（意图识别）→ Planner（任务规划）→ Executor（工具执行）→ Reflection（反思优化）→ Critic（答案生成）
- **Text2SQL**：自然语言转 SQL，查询本地 SQLite 数据库中的股票信息、财务数据、行情和研报记录
- **代码执行器**：受限 Python 执行环境，支持 pandas、numpy、matplotlib 做数据分析和图表生成
- **实时搜索**：接入博查 API 获取最新市场资讯和新闻
- **可视化前端**：Vue 3 + Vite 聊天界面，展示回答、推理步骤、反思过程和股票概览
- **状态持久化**：基于 LangGraph MemorySaver 支持多轮对话

## 项目结构

```text
finance_agent/
├── backend/
│   ├── agents/
│   │   ├── graph.py          # LangGraph 工作流定义
│   │   └── nodes.py          # Router/Planner/Executor/Reflection/Critic 节点
│   ├── api/
│   │   └── routes.py         # FastAPI 路由
│   ├── database/
│   │   ├── models.py         # SQLAlchemy ORM 模型
│   │   ├── init_db.py        # 数据库初始化和模拟数据
│   │   └── finance_db        # SQLite 数据库文件
│   ├── services/
│   │   └── llm.py            # LLM 服务封装（DashScope / OpenAI 兼容）
│   ├── tools/
│   │   ├── text2sql.py       # 自然语言转 SQL 工具
│   │   ├── code_executor.py  # Python 代码执行工具
│   │   └── web_search.py     # 网络搜索工具
│   ├── app_config.py         # 配置管理
│   ├── main.py               # FastAPI 应用入口
│   └── requirements.txt      # 后端依赖
├── frontend/
│   ├── src/
│   │   ├── App.vue           # 主聊天界面
│   │   ├── main.js           # Vue 应用入口
│   │   └── style.css         # 全局样式
│   ├── package.json          # 前端依赖和脚本
│   └── vite.config.js        # Vite 配置
└── README.md
```

## 快速开始

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

在 `backend/.env` 中配置：

```env
DASHSCOPE_API_KEY=your_dashscope_api_key
BOCHAAI_API_KEY=your_bochaai_api_key
```

### 3. 初始化数据库

```bash
cd backend
python -c "from database.init_db import init_database; init_database()"
```

### 4. 启动后端

```bash
cd backend
python main.py
```

后端默认运行在 `http://localhost:8000`，API 文档地址为 `http://localhost:8000/docs`。

### 5. 安装并启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:8080`。

## 常用命令

```bash
# 后端：运行 Agent 测试
cd backend
python agents/graph.py

# 前端：生产构建
cd frontend
npm run build

# 前端：预览构建结果
cd frontend
npm run preview
```

## 示例查询

```text
市值最大的5只银行股是哪些？
分析贵州茅台的财务状况
最近新能源行业有什么新闻？
```

## API 概览

- `GET /health`：健康检查
- `POST /api/chat`：主对话接口
- `POST /api/chat/stream`：流式对话接口
- `POST /api/sql/query`：Text2SQL 查询
- `POST /api/code/execute`：Python 代码执行
- `POST /api/search`：网络搜索
- `GET /api/stocks`：获取股票列表
- `GET /api/stocks/{stock_code}`：获取单只股票详情
- `GET /api/financials/{stock_code}`：获取股票财务数据
- `GET /api/reports`：获取研报列表
- `GET /api/schema`：获取数据库结构
- `GET /api/industries`：获取行业列表

## 技术栈

| 模块 | 技术 |
|------|------|
| 后端 API | FastAPI, Uvicorn |
| Agent 工作流 | LangGraph, LangChain |
| 大模型 | DashScope qwen-max（OpenAI compatible client） |
| 数据库 | SQLite, SQLAlchemy ORM |
| 搜索 | Bocha API, httpx |
| 数据分析 | pandas, numpy, matplotlib |
| 前端 | Vue 3, Vite, Fetch API |
| 配置 | Pydantic Settings, python-dotenv |

## 数据库表结构

- **stocks**：股票基本信息，包括股票代码、名称、行业、市值、PE/PB 等
- **financials**：财务数据，包括营收、净利润、ROE、毛利率、资产负债率等
- **market_data**：行情数据，包括 OHLC、成交量、成交额、涨跌幅等
- **research_reports**：研报信息，包括标题、机构、评级、目标价、摘要和风险提示等
- **analysis_history**：分析历史记录

## 工作流说明

```text
用户输入
  ↓
Router：识别意图
  ↓
Planner：制定计划
  ↓
Executor：调用 text2sql / code_executor / web_search
  ↓
Reflection：评估结果是否完整
  ↓
Critic：生成最终回答
```

1. **Router**：判断意图类型（data_query / analysis / research / general）
2. **Planner**：制定执行计划，分析类任务通常拆成 text2sql + code_executor 两步
3. **Executor**：按计划调用工具并收集结果
4. **Reflection**：评估结果完整性，必要时继续迭代，默认最多 3 轮
5. **Critic**：整合工具结果和反思记录，生成专业中文回答

