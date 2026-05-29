"""TravelRAG Agent 工具入口 — 含工具建议链（A2）"""
import logging
from langchain_core.tools import tool
from .travel_planner import plan_trip

logger = logging.getLogger(__name__)


@tool
def travel_planner(query_txt: str):
    """
    智能旅行规划工具。输入旅行需求（自然语言），自动规划完整行程。

    适用场景：询问旅行规划、出行建议、行程安排，提到城市+天数。
    输入示例："带小孩去杭州玩2天，喜欢自然风景" / "成都4天美食之旅"

    完成后会建议：如涉及国外城市→查汇率，如涉及户外→查天气确认。
    """
    logger.info("Travel Planner|query=%s", query_txt[:100])
    try:
        plan = plan_trip(query_txt)
        if plan.error:
            return f"旅行规划失败：{plan.error}"

        # [A2] 工具建议链 — 告诉 Agent 可能需要什么后续工具
        suggestions = []
        if "国外" in query_txt or any(c in query_txt for c in ["日本", "东京", "泰国", "纽约"]):
            suggestions.append("建议调用 get_exchange_rate 查询当地货币汇率")
        if any(w in query_txt for w in ["户外", "爬山", "海滩", "自然"]):
            suggestions.append("行程包含户外景点，建议调用 get_weather 确认天气")

        result = plan.itinerary_text
        if suggestions:
            result += "\n\n---\n💡 建议后续操作:\n" + "\n".join(f"  • {s}" for s in suggestions)
        return result
    except Exception as e:
        logger.error("Travel Planner异常|error=%s", e)
        return f"旅行规划异常：{e}"
