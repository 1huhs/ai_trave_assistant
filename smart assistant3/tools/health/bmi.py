"""
BMI 计算与健康评估工具
"""
from langchain_core.tools import tool
import logging

logger = logging.getLogger(__name__)


@tool
def calculate_bmi(height_cm: float, weight_jin: float) -> str:
    """
    计算 BMI 并给出健康评估。
    输入：height_cm=身高(厘米), weight_jin=体重(斤)
    返回：BMI值、体重状态、健康建议
    """
    try:
        height_m = height_cm / 100.0
        weight_kg = weight_jin / 2.0
        bmi = weight_kg / (height_m ** 2)

        # 中国标准
        if bmi < 18.5:
            status = "偏瘦"
            advice = "建议适当增加营养摄入，加强力量训练增加肌肉"
        elif bmi < 24:
            status = "正常"
            advice = "体重正常，建议保持现有饮食和运动习惯"
        elif bmi < 28:
            status = "超重"
            advice = "建议控制饮食热量，每周至少150分钟中等强度运动"
        else:
            status = "肥胖"
            advice = "建议咨询医生制定专业减重计划，避免高强度运动伤关节"

        return (
            f"=== BMI 健康评估 ===\n"
            f"身高：{height_cm}cm | 体重：{weight_jin}斤({weight_kg:.1f}kg)\n"
            f"BMI：{bmi:.1f}\n"
            f"状态：{status}\n"
            f"建议：{advice}"
        )
    except Exception as e:
        logger.error("BMI计算失败|error=%s", e)
        return f"BMI计算失败：{e}"
