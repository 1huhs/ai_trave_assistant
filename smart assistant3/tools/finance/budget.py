"""
旅行预算计算器
"""
from langchain_core.tools import tool
import logging

logger = logging.getLogger(__name__)


@tool
def calculate_budget(
    days: int = 2,
    hotel_per_night: float = 0,
    meals_per_day: float = 0,
    transport: float = 0,
    tickets: float = 0,
    currency_rate: float = 1.0,
) -> str:
    """
    计算旅行总预算。
    输入：days=天数, hotel_per_night=每晚住宿费, meals_per_day=每日餐饮费,
         transport=交通总费用, tickets=门票总费用, currency_rate=汇率(默认1)
    返回：分类明细+总预算
    """
    try:
        hotel_total = hotel_per_night * days
        meals_total = meals_per_day * days

        items = {
            "住宿": hotel_total,
            "餐饮": meals_total,
            "交通": transport,
            "门票": tickets,
        }
        subtotal = hotel_total + meals_total + transport + tickets
        extra = subtotal * 0.15  # 预留15%杂项
        total = subtotal + extra

        result = f"=== 旅行预算估算（{days}天）===\n"
        for name, amount in items.items():
            result += f"  {name}：¥{amount:.0f}"

            if currency_rate != 1.0:
                result += f"（约 {amount * currency_rate:.0f} 当地货币）"
            result += "\n"

        result += f"  杂项（15%）：¥{extra:.0f}\n"
        result += f"  {'─' * 30}\n"
        result += f"  💰 总预算：¥{total:.0f}"

        if currency_rate != 1.0:
            result += f"（约 {total * currency_rate:.0f} 当地货币）"

        logger.info("预算计算完成|days=%d|total=%.0f", days, total)
        return result

    except Exception as e:
        logger.error("预算计算失败|error=%s", e)
        return f"预算计算失败：{e}"
