"""
多币种汇率查询工具
基于 frankfurter.app 免费API（无需注册）
"""
from langchain_core.tools import tool
import requests
import logging

logger = logging.getLogger(__name__)


@tool
def get_exchange_rate_multi(base: str, targets: str) -> str:
    """
    查询多币种汇率：同时查询多种货币汇率。
    输入示例：base=CNY, targets=HKD,USD,JPY
    注意：此工具为多币种版，原有的 exchange_rate 工具仍可使用（单币种版）
    """
    base_upper = base.upper().strip()
    target_list = [t.strip().upper() for t in targets.split(",") if t.strip()]

    if not target_list:
        return "请至少指定一种目标货币"

    try:
        url = "https://api.frankfurter.app/latest"
        params = {
            "from": base_upper,
            "to": ",".join(target_list),
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        rates = data.get("rates", {})
        result_lines = [f"=== 汇率查询：1 {base_upper} ==="]
        for currency, rate in rates.items():
            result_lines.append(f"  {currency}：{rate:.4f}")

        return "\n".join(result_lines)

    except Exception as e:
        logger.error("多币种汇率查询失败|error=%s", e)
        return f"汇率查询失败：{e}"
