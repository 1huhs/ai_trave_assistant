"""汇率查询工具 — Frankfurter API（免费，无需 Key）"""
from langchain_core.tools import tool
import requests


@tool
def get_exchange_rate(base: str, target: str):
    """查询两种货币之间的实时汇率，base 和 target 为货币代码（如 USD, CNY, JPY）"""
    try:
        url = f"https://api.frankfurter.app/latest?from={base.upper()}&to={target.upper()}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        result = data["rates"].get(target.upper())
        return f"1 {base.upper()} = {result} {target.upper()}"
    except Exception as e:
        return f"汇率查询失败：{e}"
