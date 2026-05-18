# 金融研报智能分析助手

基于 LLM + LangGraph 的金融研报智能分析系统，支持自然语言查询股票数据、财务分析和实时市场资讯。

## 功能特性

- **多智能体协作**：Router（意图识别）→ Planner（任务规划）→ Executor（工具执行）→ Reflection（反思优化）→ Critic（答案生成）
- **Text2SQL**：自然语言转 SQL 查询本地 SQLite 数据库（股票信息、财务数据、行情、研报）
- **代码执行器**：安全的 Python 沙箱，支持 pandas/numpy/matplotlib 进行数据分析和图表生成
- **实时搜索**：接入博查 API 获取最新市场资讯和新闻
- **状态持久化**：基于 LangGraph MemorySaver 支持多轮对话

## 项目结构

```
finance_agent/
├── agents/
│   ├── graph.py          # LangGraph 工作流定义
│   └── nodes.py          # Router/Planner/Executor/Reflection/Critic 节点
├── database/
│   ├── models.py         # SQLAlchemy ORM 模型
│   ├── init_db.py        # 数据库初始化 & 模拟数据
│   └── finance_db/       # SQLite 数据库文件
├── services/
│   └── llm.py            # LLM 服务封装（DashScope / OpenAI 兼容）
├── tools/
│   ├── text2sql.py       # 自然语言 → SQL 工具
│   ├── code_executor.py  # Python 代码执行工具
│   └── web_search.py     # 网络搜索工具
├── app_config.py         # 配置管理（Pydantic Settings）
└── requirements.txt     # 依赖列表
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```env
DASHSCOPE_API_KEY=your_dashscope_api_key
BOCHAAI_API_KEY=your_bochaai_api_key
```

### 3. 初始化数据库

```bash
python -c "from database.init_db import init_database; init_database()"
```

### 4. 运行测试

```bash
python agents/graph.py
```

## 示例查询

```
市值最大的5只银行股是哪些？
分析贵州茅台的财务状况
最近新能源行业有什么新闻？
```

## 技术栈

| 组件 | 技术 |
|------|------|
| AI 框架 | LangGraph, LangChain |
| 大模型 | DashScope (qwen-max) |
| 数据库 | SQLite, SQLAlchemy ORM |
| 搜索 | Bocha API, httpx |
| 数据分析 | pandas, numpy, matplotlib |
| 配置 | Pydantic Settings |

## 数据库表结构

- **stocks**：股票基本信息（市值、PE/PB、行业等）
- **financials**：财务数据（营收、利润、ROE、毛利率等）
- **market_data**：行情数据（OHLC、成交量、涨跌幅等）
- **research_reports**：研报信息（评级、目标价、分析师观点等）

## 工作流说明

```
用户输入 → Router（意图分类）
              ↓
         Planner（任务规划）
              ↓
         Executor（工具执行）
              ↓
         Reflection（反思是否继续）
              ↓
         Critic（生成最终答案）
```

1. **Router**：判断意图类型（data_query / analysis / research / general）
2. **Planner**：制定执行计划，对于分析类任务生成 text2sql + code_executor 两步计划
3. **Executor**：调用工具执行，支持 text2sql、code_executor、web_search
4. **Reflection**：评估结果完整性，决定是否继续迭代（最多 3 轮）
5. **Critic**：整合所有结果，生成最终专业回答