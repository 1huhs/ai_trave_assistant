"""
Smart Agent v3 — ReAct 推理 + 双层记忆 + 执行轨迹 + 工具上下文 + 失败感知
===========================================================================
v3 新增：
  A1: Tool Context Bus — 工具间数据共享，Agent 感知已执行工具的结果
  A3: 失败感知规则 — 工具返回异常时自动重试/换方案
  A4: 执行状态追踪 — 避免重复调用已执行的工具
"""
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from langchain.agents import create_agent
import json, os, sys
sys.path.insert(0, str(os.path.dirname(os.path.dirname(__file__))))
import config
from tools.registry import auto_discover_tools
from agent.sqlite_memory import UserMemory
import logging, time

logger = logging.getLogger(__name__)


class SmartAgent:
    """ReAct Agent 核心类"""

    fallback_message = "抱歉，处理你的请求时遇到了问题，请稍后再试。"

    def __init__(self, user_id="default"):
        self.user_id = user_id
        self.memory = UserMemory(user_id=user_id)
        self.llm = ChatOpenAI(
            model=config.DEEP_SEEK_MODEL,
            base_url=config.DEEP_SEEK_BASE_URL,
            api_key=SecretStr(config.DEEP_SEEK_API_KEY),
            temperature=0,
            model_kwargs={"extra_body": {"thinking": {"type": "disabled"}}}
        )
        self.tools = auto_discover_tools()
        self.agent = create_agent(model=self.llm, tools=self.tools, system_prompt=self._build_system_prompt())
        saved_history = self.memory.load_conversations(limit=20)
        self.history_message = list(saved_history)
        self.execution_trace = []
        self._called_tools = set()  # [NEW] 当前请求中已调用的工具

    # ──────────── System Prompt [NEW: A3 failure-aware] ────────────

    def _build_system_prompt(self):
        tool_list = self._format_tools()
        return f"""你是一个智能 AI Agent，具备多步推理和多工具协调能力。

## 工作流程（ReAct 模式）
1. 思考（Thought）：分析用户需求，判断需要什么工具
2. 行动（Action）：调用工具获取信息
3. 观察（Observation）：解读工具返回结果，判断是否需要进一步行动
4. 回答：整合所有信息给出最终回复

## 可用工具
{tool_list}

## 多工具协调规则
- 旅行规划：用户提到国外城市 → 先调 get_exchange_rate 查汇率 → 再调 travel_planner
- 旅行规划：用户提到"周末""下周" → 先调 get_current_time 确认日期 → 再调 get_weather
- 旅行规划：用户比较两个城市 → 分别调 travel_planner 后对比总结
- 知识问题：优先用 search_answer 查本地知识库
- 计算需求：用 calculate 工具，不要自己算

## 失败处理规则 [NEW]
工具调用可能因网络波动失败。如果返回结果自动重试：
1. 换一种参数重试一次（如换个关键词）
2. 尝试使用其他能获取同样信息的工具替代
3. 两次重试仍失败后，告知用户并说明原因

## 重要规则
- 需要实时数据（天气、汇率、时间）时务必调用工具
- 需要背景知识时使用 search_answer
- 多个工具可以串联调用，基于上一步结果决定下一步
- 每次回复只做必要的事，不要过度询问或过度解释
"""

    def _format_tools(self):
        lines = []
        for t in self.tools:
            name = getattr(t, "name", "unknown")
            desc = getattr(t, "description", "")
            short = desc.split("\n")[0].strip()[:100]
            lines.append(f"  • **{name}**：{short}")
        return "\n".join(lines) if lines else "（无可用工具）"

    # ──────────── 记忆检索 ────────────

    def _format_memory(self):
        data = getattr(self.memory, "memory_data", None)
        if not data:
            return "（暂无历史记忆）"
        lines = []
        for category, items in data.items():
            lines.append(f"  [{category}] {'、'.join(items)}")
        return "\n".join(lines)

    def _build_memory_context(self, query: str) -> str:
        parts = []
        profile_mem = self.memory.search_relevant_memory(query, k=2)
        if profile_mem and profile_mem != "（暂无历史记忆）":
            formatted = "\n".join(f"  • {m}" for m in profile_mem)
            parts.append(f"## 用户画像（基于当前话题）\n{formatted}")
        conv_mem = self.memory.search_relevant_conversations(query, k=2)
        if conv_mem:
            formatted = "\n".join(f"  • {c}" for c in conv_mem)
            parts.append(f"## 相关历史对话\n{formatted}")
        return "\n\n".join(parts) if parts else ""

    # ──────────── 会话管理 ────────────

    def save_user_history_message(self, data):
        self.history_message.append(("user", data))
        self.memory.save_conversation("user", data)
        if len(self.history_message) > 20:
            self.history_message = self.history_message[-20:]

    def save_assistant_history_message(self, data):
        self.history_message.append(("assistant", data))
        self.memory.save_conversation("assistant", data)

    # ──────────── 核心推理 [NEW: A1/A4] ────────────

    def run(self, sr):
        self.execution_trace = []
        self._called_tools = set()
        self.memory.clear_tool_context()  # [A1] 新请求清空上下文

        self.execution_trace.append({"step": "INPUT", "content": sr})
        self.save_user_history_message(sr)

        memory_context = self._build_memory_context(sr)
        messages_for_agent = list(self.history_message)
        if memory_context:
            messages_for_agent.insert(0, ("system", f"以下是与此对话相关的用户背景信息：\n{memory_context}"))
            self.execution_trace.append({"step": "MEMORY", "content": memory_context[:200]})

        # [A1] 注入工具上下文
        tool_context = self.memory.get_tool_context()
        if tool_context:
            messages_for_agent.insert(0, ("system", f"前序工具执行记录：\n{tool_context}"))

        # [A4] 注入已调用工具列表
        if self._called_tools:
            called = ", ".join(sorted(self._called_tools))
            messages_for_agent.insert(0, ("system", f"[系统] 本请求中已调用的工具: {called}"))

        start_time = time.perf_counter()

        try:
            result = self.agent.invoke({"messages": messages_for_agent})
        except Exception as e:
            logger.error("Agent推理失败|user_id=%s|error=%s", self.user_id, e)
            return {"answer": self.fallback_message, "error": str(e)}

        invoke_ms = (time.perf_counter() - start_time) * 1000
        logger.info("Agent推理完成|user_id=%s|invoke_ms=%.0f", self.user_id, invoke_ms)

        self._extract_trace(result)

        answer = result["messages"][-1]
        self.execution_trace.append({"step": "ANSWER", "content": answer.content[:300]})

        # 长期记忆提取
        try:
            long_memory = self.extract_memory(user=sr, ai=answer.content)
            self.memory.save_memory(long_memory)
        except Exception as e:
            logger.warning("提取记忆失败|user_id=%s|error=%s", self.user_id, e)

        self.save_assistant_history_message(answer.content)
        return result

    def _extract_trace(self, result):
        messages = result.get("messages", [])
        for msg in messages:
            msg_type = getattr(msg, "type", "unknown")
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc.get("name", "unknown")
                    self._called_tools.add(tool_name)  # [A4] 记录已调用工具
                    self.execution_trace.append({
                        "step": "ACTION",
                        "tool": tool_name,
                        "args": tc.get("args", {}),
                    })
            if msg_type == "tool":
                tool_name = getattr(msg, "name", "unknown")
                result_text = str(getattr(msg, "content", ""))
                # [A1] 工具返回时写入上下文总线
                self.memory.set_tool_result(tool_name, result_text)
                self.execution_trace.append({
                    "step": "OBSERVATION",
                    "tool": tool_name,
                    "result": result_text[:200],
                })
            if msg_type == "ai" and hasattr(msg, "content") and msg.content:
                content = str(msg.content)
                if "Thought:" in content or "Action:" in content:
                    self.execution_trace.append({
                        "step": "THOUGHT",
                        "content": content[:300],
                    })

    def get_trace_summary(self):
        if not self.execution_trace:
            return "（无执行轨迹）"
        lines = ["=" * 50, "Agent 执行轨迹", "=" * 50]
        for i, step in enumerate(self.execution_trace):
            prefix = f"Step {i}: "
            if step["step"] == "INPUT":
                lines.append(f"{prefix}用户输入 → {step['content'][:80]}")
            elif step["step"] == "THOUGHT":
                lines.append(f"{prefix}思考 → {step['content'][:120]}")
            elif step["step"] == "ACTION":
                lines.append(f"{prefix}调用工具 → {step['tool']}({step['args']})")
            elif step["step"] == "OBSERVATION":
                lines.append(f"{prefix}工具返回 → {step['tool']}: {step['result'][:100]}")
            elif step["step"] == "ANSWER":
                lines.append(f"{prefix}最终回答 → {step['content'][:120]}")
        lines.append("=" * 50)
        return "\n".join(lines)

    # ──────────── 记忆提取 ────────────

    def extract_memory(self, user, ai):
        prompt = f"""你负责提取长期记忆。从用户输入和AI回复中提取个人信息、兴趣、计划。
返回JSON: {{"profile":[...], "interest":[...], "plan":[...]}}
用户: {user}
AI: {ai}"""
        try:
            result = self.llm.invoke(prompt)
            raw = result.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            for key in ["profile", "interest", "plan"]:
                if key not in data:
                    data[key] = []
            return data
        except Exception as e:
            logger.error("提取记忆失败|user_id=%s|error=%s", self.user_id, e)
            return {"profile": [], "interest": [], "plan": []}
