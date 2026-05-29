"""
高德地图 API 客户端 — POI 搜索 + 天气 + 路径规划 + 空间距离计算
"""
import logging, math, os, time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

logger = logging.getLogger(__name__)
GAODE_KEY = os.getenv("GAODE_KEY", "")
BASE_URL = "https://restapi.amap.com/v3"
_MIN_INTERVAL = 0.2


# ══════════════════════════════════════════════════════════════════
#  数据模型
# ══════════════════════════════════════════════════════════════════

@dataclass
class POI:
    name: str; category: str; poi_type: str = ""; address: str = ""
    city: str = ""; district: str = ""; longitude: float = 0.0; latitude: float = 0.0
    rating: str = ""; cost: str = ""; photos: list = field(default_factory=list)
    tel: str = ""; business_area: str = ""


@dataclass
class WeatherInfo:
    city: str; date: str; day_weather: str; night_weather: str
    day_temp: str; night_temp: str; day_wind: str; night_wind: str


@dataclass
class RouteInfo:
    origin: str; destination: str; mode: str
    distance_meters: int = 0; duration_seconds: int = 0; cost_yuan: float = 0.0


@dataclass
class CityData:
    city: str
    attractions: list = field(default_factory=list)
    hotels: list = field(default_factory=list)
    restaurants: list = field(default_factory=list)
    weather: list = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════
#  HTTP + 限流
# ══════════════════════════════════════════════════════════════════

_last_call_time = 0.0


def _rate_limit():
    global _last_call_time
    elapsed = time.time() - _last_call_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_call_time = time.time()


def _get(endpoint, params, retries=2):
    params["key"] = GAODE_KEY
    for attempt in range(retries + 1):
        _rate_limit()
        try:
            resp = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != "1":
                logger.warning("高德API异常|endpoint=%s|info=%s", endpoint, data.get("info"))
                return {}
            return data
        except Exception as e:
            logger.warning("高德API失败|endpoint=%s|attempt=%d|error=%s", endpoint, attempt + 1, e)
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))
    return {}


# ══════════════════════════════════════════════════════════════════
#  POI 搜索
# ══════════════════════════════════════════════════════════════════

CATEGORY_TYPE_MAP = {
    "attraction": "风景名胜|公园广场|博物馆|展览馆|海滩|动物园|植物园|水族馆|游乐园",
    "hotel": "",
    "restaurant": "",
}


def _parse_poi(raw, category, city):
    biz = raw.get("biz_ext", {}) or {}
    loc = (raw.get("location") or "").split(",")
    return POI(
        name=raw.get("name", "未知"), category=category,
        poi_type=raw.get("type", ""), address=raw.get("address", ""),
        city=raw.get("cityname", city), district=raw.get("adname", ""),
        longitude=float(loc[0]) if len(loc) >= 2 else 0.0,
        latitude=float(loc[1]) if len(loc) >= 2 else 0.0,
        rating=biz.get("rating", ""), cost=biz.get("cost", ""),
        tel=raw.get("tel", "") or biz.get("tel", ""),
        business_area=raw.get("business_area", ""),
    )


def search_poi(city, keywords="", category="attraction", offset=15):
    types = CATEGORY_TYPE_MAP.get(category, "")
    query = f"{keywords} {city}" if keywords else city
    data = _get("place/text", {"keywords": query.strip(), "city": city,
                                "types": types, "offset": min(offset, 25), "extensions": "all"})
    results = [_parse_poi(p, category, city) for p in data.get("pois", [])]
    logger.info("POI搜索|city=%s|category=%s|results=%d", city, category, len(results))
    return results


def search_nearby(lng, lat, category="restaurant", radius=3000, offset=10):
    types = CATEGORY_TYPE_MAP.get(category, "")
    data = _get("place/around", {"location": f"{lng},{lat}", "types": types,
                                  "radius": radius, "offset": min(offset, 25), "extensions": "all"})
    return [_parse_poi(p, category, "") for p in data.get("pois", [])]


# ══════════════════════════════════════════════════════════════════
#  天气
# ══════════════════════════════════════════════════════════════════

def get_weather(city, forecast_days=3):
    geo = _get("geocode/geo", {"address": city})
    geocodes = geo.get("geocodes", [])
    if not geocodes:
        return []
    adcode = geocodes[0].get("adcode", "")
    data = _get("weather/weatherInfo", {"city": adcode, "extensions": "all"})
    forecasts = data.get("forecasts", [])
    if not forecasts:
        return []
    return [WeatherInfo(
        city=forecasts[0].get("city", city), date=f.get("date", ""),
        day_weather=f.get("dayweather", ""), night_weather=f.get("nightweather", ""),
        day_temp=f.get("daytemp", ""), night_temp=f.get("nighttemp", ""),
        day_wind=f.get("daywind", ""), night_wind=f.get("nightwind", ""),
    ) for f in forecasts[0].get("casts", [])[:forecast_days]]


# ══════════════════════════════════════════════════════════════════
#  路径规划
# ══════════════════════════════════════════════════════════════════

def plan_route(origin, destination, mode="driving"):
    if mode == "transit":
        endpoint, params = "direction/transit/integrated", {"origin": origin, "destination": destination, "city": origin}
    else:
        endpoint, params = "direction/driving", {"origin": origin, "destination": destination, "strategy": 0}
    data = _get(endpoint, params)
    route = data.get("route", {})
    paths = route.get("transits" if mode == "transit" else "paths", [])
    return [RouteInfo(origin=origin, destination=destination, mode=mode,
                       distance_meters=int(p.get("distance", 0) or 0),
                       duration_seconds=int(p.get("duration", 0) or 0),
                       cost_yuan=float(p.get("cost", 0) or 0) if mode == "transit" else 0.0)
            for p in paths[:3]]


# ══════════════════════════════════════════════════════════════════
#  空间距离（从 document_builder 合并）
# ══════════════════════════════════════════════════════════════════

def haversine_distance(lng1, lat1, lng2, lat2):
    """Haversine 球面距离（米）"""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ══════════════════════════════════════════════════════════════════
#  批量获取
# ══════════════════════════════════════════════════════════════════

def batch_fetch_city_data(city, keywords=None, max_pois=15):
    if keywords is None:
        keywords = ["景点"]
    city_data = CityData(city=city)
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {}
        futures["weather"] = pool.submit(get_weather, city, 3)

        def _fetch_attractions():
            all_attrs = {}
            with ThreadPoolExecutor(max_workers=len(keywords)) as kw_pool:
                kw_futures = {kw: kw_pool.submit(search_poi, city, kw, "attraction", max_pois) for kw in keywords}
            for kw, f in kw_futures.items():
                try:
                    for p in f.result(timeout=20):
                        if p.name not in all_attrs:
                            all_attrs[p.name] = p
                except Exception:
                    pass
            return list(all_attrs.values())

        futures["attractions"] = pool.submit(_fetch_attractions)
        futures["hotels"] = pool.submit(search_poi, city, "酒店", "hotel", max_pois)
        futures["restaurants"] = pool.submit(search_poi, city, "餐厅", "restaurant", max_pois)

        for name, f in futures.items():
            try:
                result = f.result(timeout=30)
                setattr(city_data, name, result or ([] if name != "weather" else getattr(city_data, name)))
            except Exception as e:
                logger.error("批量获取失败|field=%s|error=%s", name, e)
    return city_data
