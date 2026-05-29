"""
饮食建议工具
内置减肥/增肌/均衡饮食方案库
"""
from langchain_core.tools import tool
import logging

logger = logging.getLogger(__name__)

# 内置饮食知识库
_DIET_DB = {
    "减肥": {
        "原则": ["控制总热量", "少食多餐", "避免高糖高油"],
        "推荐食物": [
            "鸡胸肉、鱼肉、虾等高蛋白低脂肉类",
            "西兰花、菠菜、生菜等绿叶蔬菜",
            "燕麦、糙米、红薯等低GI主食",
            "苹果、蓝莓、柚子等低糖水果",
        ],
        "避免食物": [
            "奶茶、碳酸饮料、果汁",
            "油炸食品、肥肉、动物内脏",
            "蛋糕、饼干、冰淇淋",
        ],
        "示例餐单": "早餐：燕麦+水煮蛋+苹果 | 午餐：鸡胸肉+糙米饭+西兰花 | 晚餐：鱼肉+蔬菜沙拉",
    },
    "增肌": {
        "原则": ["蛋白质充足", "碳水适量", "训练后及时补充"],
        "推荐食物": [
            "牛肉、鸡胸肉、三文鱼（每餐150-200g）",
            "鸡蛋（每天2-3个）",
            "牛奶、酸奶、奶酪",
            "红薯、全麦面包、藜麦",
        ],
        "示例餐单": "早餐：全麦面包+3个鸡蛋+牛奶 | 午餐：牛肉+藜麦+蔬菜 | 训练后：蛋白粉+香蕉 | 晚餐：三文鱼+红薯",
    },
    "均衡": {
        "原则": ["多样化", "粗细搭配", "荤素搭配"],
        "推荐食物": [
            "每天12种以上食物，每周25种以上",
            "主食粗细搭配，蔬菜深色为主",
            "鱼肉、禽肉、蛋类、豆制品轮换",
        ],
    },
}


@tool
def get_diet_advice(goal: str, weight_kg: float = 0, bmi: float = 0) -> str:
    """
    获取饮食建议：根据用户目标（减肥/增肌/均衡）、体重和BMI给出饮食方案。
    输入示例：goal=减肥, weight_kg=115, bmi=35.5
    """
    goal = goal.strip()
    if goal not in _DIET_DB:
        goals = ", ".join(_DIET_DB.keys())
        return f"当前支持的目标：{goals}，请输入其中之一"

    info = _DIET_DB[goal]
    result = f"=== {goal}饮食方案 ===\n"

    result += f"\n📋 原则：\n" + "\n".join(f"  · {p}" for p in info["原则"])

    result += f"\n\n✅ 推荐食物：\n" + "\n".join(f"  · {f}" for f in info["推荐食物"])

    if "避免食物" in info:
        result += f"\n\n❌ 避免食物：\n" + "\n".join(f"  · {f}" for f in info["避免食物"])

    if "示例餐单" in info:
        result += f"\n\n📅 示例餐单：\n  {info['示例餐单']}"

    # 根据 BMI 个性化提示
    if bmi > 0 and goal == "减肥":
        if bmi > 35:
            result += "\n\n⚠️ 你的BMI较高，建议先咨询医生或营养师制定安全计划"
        daily_cal = max(1200, weight_kg * 20 - 500)
        result += f"\n\n📊 建议每日摄入约 {daily_cal:.0f} 大卡"

    logger.info("饮食建议生成|goal=%s", goal)
    return result
