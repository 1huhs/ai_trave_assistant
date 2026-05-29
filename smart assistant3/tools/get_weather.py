"""
天气查询工具 — 基于 wttr.in 免费 API
调用方：LangChain Agent → 用户问"XX天气怎么样"时自动调用
"""
import requests
from langchain_core.tools import tool
import logging
logger = logging.getLogger(__name__)


@tool
def get_weather(city: str):
    """查询指定城市的天气，参数 city 为城市名称（中文或英文）"""
    try:
        weather_map = {
            "Sunny": "晴", "Clear": "晴", "Partly cloudy": "多云",
            "Cloudy": "阴天", "Overcast": "阴", "Mist": "薄雾", "Fog": "雾",
            "Light rain": "小雨", "Moderate rain": "中雨", "Heavy rain": "大雨",
            "Rain": "雨", "Light snow": "小雪", "Moderate snow": "中雪",
            "Heavy snow": "大雪", "Snow": "雪", "Thunderstorm": "雷雨",
            "Patchy rain possible": "局部有雨", "Patchy snow possible": "局部有雪"
        }
        url = f"https://wttr.in/{city}?format=j1"
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        current = data["current_condition"][0]
        tem = current["temp_C"]
        humidity = current["humidity"]
        weather_en = current["weatherDesc"][0]["value"]
        weather_cn = weather_map.get(weather_en, weather_en)
        wind = current["windspeedKmph"]
        return f"{city}的天气是{weather_cn}，温度{tem}°C，湿度{humidity}%，风速{wind}km/h。"
    except Exception as e:
        logger.error("get_weather查询失败|error=%s", e)
        return f"查询天气时出错：{e}"
