"""
Travel Planner — 偏好解析 → 规则筛选 → LLM 生成行程
"""
import logging, os, sys
from dataclasses import dataclass, field
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import config
from pydantic import SecretStr
from .gaode_client import batch_fetch_city_data, CityData, POI, haversine_distance

logger = logging.getLogger(__name__)
_llm_cache = None


def _get_llm():
    global _llm_cache
    if _llm_cache is None:
        from langchain_openai import ChatOpenAI
        _llm_cache = ChatOpenAI(model=config.DEEP_SEEK_MODEL, api_key=SecretStr(config.DEEP_SEEK_API_KEY),
                                base_url=config.DEEP_SEEK_BASE_URL, temperature=0)
    return _llm_cache


# ══════════════════════════════════════════════════════════════════
#  偏好解析
# ══════════════════════════════════════════════════════════════════

@dataclass
class TravelPreference:
    city: str = ""; days: int = 3; budget: str = "中等"; style: str = ""
    interests: list = field(default_factory=list); dislikes: list = field(default_factory=list)
    pace: str = "适中"; raw_query: str = ""


def parse_preferences(query):
    llm = _get_llm()
    prompt = f"""你是一个旅行偏好解析器。提取结构化偏好，输出严格JSON。
字段：city(城市), days(天数,默认3), budget(经济/中等/豪华), style(亲子/蜜月/独自/朋友/商务/家庭),
interests(列表), dislikes(列表), pace(轻松/适中/紧凑)
用户输入: {query}
JSON:"""
    try:
        result = llm.invoke(prompt)
        import json
        text = result.content.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
        data = json.loads(text.strip())
        return TravelPreference(city=data.get("city", ""), days=int(data.get("days", 3)),
                                budget=data.get("budget", "中等"), style=data.get("style", ""),
                                interests=data.get("interests", []), dislikes=data.get("dislikes", []),
                                pace=data.get("pace", "适中"), raw_query=query)
    except Exception as e:
        logger.warning("偏好解析失败|error=%s", e)
        return TravelPreference(raw_query=query)


# ══════════════════════════════════════════════════════════════════
#  规则筛选
# ══════════════════════════════════════════════════════════════════

STYLE_MATCH = {
    "亲子": ["动物园", "游乐园", "水族馆", "博物馆", "植物园", "主题公园"],
    "蜜月": ["海滩", "风景名胜", "度假村"],
    "家庭": ["动物园", "游乐园", "植物园", "公园广场", "博物馆"],
    "朋友": ["游乐园", "滑雪场", "海滩"],
}
BUDGET_MAX_PRICE = {"经济": 300, "中等": 800, "豪华": 99999}
BUDGET_MAX_COST = {"经济": 50, "中等": 150, "豪华": 99999}


def _first_type(poi): return (poi.poi_type or "").split(";")[0]


def _filter_attractions(city_data, pref, top_k=6):
    if not city_data.attractions: return []
    scored = []
    for p in city_data.attractions:
        score = 0.0
        for interest in pref.interests:
            if interest.lower() in p.name.lower() or interest.lower() in p.poi_type.lower():
                score += 3.0
        style_types = STYLE_MATCH.get(pref.style, [])
        if any(st in _first_type(p) for st in style_types): score += 2.0
        try: score += float(p.rating) * 2.0
        except: pass
        scored.append((p, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    seen, selected = set(), []
    for poi, s in scored:
        pt = _first_type(poi)
        if pt not in seen or len(selected) < top_k // 2:
            selected.append(poi); seen.add(pt)
        if len(selected) >= top_k: break
    return selected[:top_k]


def _filter_hotels(city_data, pref, attractions, top_k=4):
    if not city_data.hotels: return []
    max_price = BUDGET_MAX_PRICE.get(pref.budget, 800)
    avg_lng = sum(p.longitude for p in attractions) / len(attractions) if attractions else 0
    avg_lat = sum(p.latitude for p in attractions) / len(attractions) if attractions else 0
    scored = []
    for p in city_data.hotels:
        try: cost = float(p.cost) if p.cost else 999999
        except: cost = 999999
        if cost > max_price: continue
        score = 0.0
        if avg_lng and avg_lat and p.longitude:
            dist = haversine_distance(avg_lng, avg_lat, p.longitude, p.latitude)
            score = max(0, 10.0 - dist / 500.0)
        try: score += float(p.rating) * 1.5
        except: pass
        scored.append((p, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [p for p, _ in scored[:top_k]]


def _filter_restaurants(city_data, pref, attractions, top_k=6):
    if not city_data.restaurants: return []
    max_cost = BUDGET_MAX_COST.get(pref.budget, 150)
    avg_lng = sum(p.longitude for p in attractions) / len(attractions) if attractions else 0
    avg_lat = sum(p.latitude for p in attractions) / len(attractions) if attractions else 0
    scored = []
    for p in city_data.restaurants:
        try: cost = float(p.cost) if p.cost else 999999
        except: cost = 999999
        if cost > max_cost: continue
        score = 0.0
        if avg_lng and avg_lat and p.longitude:
            dist = haversine_distance(avg_lng, avg_lat, p.longitude, p.latitude)
            score = max(0, 10.0 - dist / 300.0)
        try: score += float(p.rating) * 1.5
        except: pass
        scored.append((p, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    seen, selected = set(), []
    for poi, s in scored:
        pt = _first_type(poi)
        if pt not in seen or len(selected) < top_k // 2:
            selected.append(poi); seen.add(pt)
        if len(selected) >= top_k: break
    return selected[:top_k]


# ══════════════════════════════════════════════════════════════════
#  主管线
# ══════════════════════════════════════════════════════════════════

@dataclass
class TravelPlan:
    preference: TravelPreference; city_data: Optional[CityData] = None
    attractions: list = field(default_factory=list); hotels: list = field(default_factory=list)
    restaurants: list = field(default_factory=list); itinerary_text: str = ""; error: str = ""


def plan_trip(query):
    plan = TravelPlan(preference=TravelPreference(raw_query=query))
    pref = parse_preferences(query)
    plan.preference = pref
    if not pref.city:
        plan.error = "未能识别目标城市，请明确城市名称（如'去北京玩3天'）。"
        return plan

    keywords = [k for k in pref.interests if k] or ["景点"]
    if pref.style: keywords.append(pref.style)
    city_data = batch_fetch_city_data(pref.city, keywords=keywords, max_pois=15)
    plan.city_data = city_data
    if not city_data.attractions and not city_data.hotels and not city_data.restaurants:
        plan.error = f"在{pref.city}未获取到旅行数据。"
        return plan

    plan.attractions = _filter_attractions(city_data, pref, top_k=6)
    plan.hotels = _filter_hotels(city_data, pref, plan.attractions, top_k=4)
    plan.restaurants = _filter_restaurants(city_data, pref, plan.attractions, top_k=6)
    plan.itinerary_text = _generate_itinerary(plan, city_data)
    return plan


def _generate_itinerary(plan, city_data):
    pref = plan.preference

    def _fmt(title, pois, show_cost=True):
        if not pois: return f"## {title}\n（暂无）\n"
        lines = [f"## {title}"]
        for p in pois:
            line = f"- **{p.name}**"
            if p.rating: line += f" {p.rating}分"
            if show_cost and p.cost: line += f" ¥{p.cost}"
            if p.district: line += f" 📍{p.district}"
            lines.append(line)
        return "\n".join(lines)

    weather_lines = [f"- {w.date}: {w.day_weather} {w.day_temp}°C" for w in city_data.weather]
    weather_text = "\n".join(weather_lines) if weather_lines else "暂无"
    avoid = f"规避：{'、'.join(pref.dislikes)}\n" if pref.dislikes else ""

    llm = _get_llm()
    prompt = f"""你是资深旅行规划师。基于真实 POI 数据生成{pref.days}天{pref.city}行程。
用户偏好：{pref.city} {pref.days}天 {pref.budget} {pref.style} {', '.join(pref.interests)} {pref.pace}
{avoid}
天气：{weather_text}
{_fmt('景点', plan.attractions)}
{_fmt('酒店', plan.hotels)}
{_fmt('餐厅', plan.restaurants)}
格式：行程总览 → 第N天(上午/午餐/下午/晚餐/住宿) → 预算估算 → 旅行贴士。
规则：只用上面列出的真实POI，考虑天气，匹配预算({pref.budget})，符合节奏({pref.pace})。"""
    try:
        return llm.invoke(prompt).content
    except Exception as e:
        return f"行程生成失败: {e}"
