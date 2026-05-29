# Smart Assistant v3

> 基于 ReAct 架构的多工具 AI Agent 框架，支持插件化工具扩展、双层记忆管理、混合检索和执行轨迹可视化。

## 架构概览

```
用户 → ReAct Agent → Tool Registry（自动发现）
                    ├── travel_planner    （旅行规划：高德 API + 规则筛选 + LLM）
                    ├── search_answer     （知识库：BM25 + 向量混合检索）
                    ├── get_weather       （wttr.in）
                    ├── get_exchange_rate （Frankfurter API）
                    ├── get_current_time  
                    ├── calculate          （AST 安全求值）
                    └── code_review/      （代码分析/优化/测试生成）
                    │
                    ├── 双层记忆（SQLite + Chroma）
                    ├── 工具上下文总线（Tool Context Bus）
                    └── 执行轨迹 + Benchmark
```

## 核心特性

- **ReAct 推理**：Thought → Action → Observation 循环，支持多工具串联
- **工具上下文总线**：同一请求中工具间自动共享数据，减少 Agent prompt 负担
- **双层记忆**：SQLite 结构化存储 + Chroma 语义检索，对话重启不丢
- **混合检索**：BM25 关键词 + 向量语义，双路召回去重
- **插件化工具**：`@tool` 装饰器 + importlib 自动扫描，新增工具零修改
- **执行轨迹**：每步推理可追溯，支持 Benchmark 量化评测

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 .env
cp .env.example .env
# 编辑 .env：填入 DEEP_SEEK_API_KEY, ZHIPU_API_KEY, GAODE_KEY

# 3. 放入知识库文档（可选）
# 将 .txt 文件放入 knowledge/ 目录

# 4. 运行
python main.py
```

## 项目结构

```
smart_assistant3/
├── config.py              # 全局配置
├── main.py                # 入口
├── agent/
│   ├── langchain_agent.py # ReAct Agent 核心
│   └── sqlite_memory.py   # 双层记忆 + 工具上下文总线
├── rag/
│   ├── load.py            # 知识库文档加载
│   ├── vector.py          # Chroma 向量存储
│   ├── hybrid_retriever.py # BM25 + 向量混合检索
│   └── query_enhancer.py  # LLM 查询扩展
├── tools/
│   ├── registry.py        # 工具自动发现
│   ├── knowledge.py       # 知识库检索
│   ├── travel1/           # 旅行规划
│   ├── code_review/       # 代码审查
│   └── *.py               # 其他工具
└── knowledge/             # 知识库文档
```

## 技术栈

LangChain 1.x · DeepSeek · Chroma · SQLite · FastAPI · Tkinter
