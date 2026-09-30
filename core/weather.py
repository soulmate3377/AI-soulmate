# core/weather.py
#
# 城市天气查询（Open-Meteo，无需 Key）
# 供 EchoLover 感知"她住的城市的此刻天气"
# 带内存缓存，默认一小时刷新一次；
# 网络失败返回 None，绝不影响聊天

import json
import time
import urllib.parse
import urllib.request


_GEO_URL = (
    "https://geocoding-api.open-meteo.com"
    "/v1/search?name={name}&count=1"
    "&language=zh&format=json"
)

_FORECAST_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude={lat}&longitude={lon}"
    "&current=temperature_2m,weather_code"
    "&timezone=auto"
)


# WMO weather code → 中文描述
_CODES = {
    0: "晴",
    1: "大致晴",
    2: "多云",
    3: "阴",
    45: "雾",
    48: "雾",
    51: "毛毛雨",
    53: "毛毛雨",
    55: "毛毛雨",
    56: "冻雨",
    57: "冻雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "阵雨",
    81: "阵雨",
    82: "暴雨",
    85: "阵雪",
    86: "阵雪",
    95: "雷阵雨",
    96: "雷阵雨伴冰雹",
    99: "雷阵雨伴冰雹",
}


# city -> (timestamp, data)
_cache = {}


def get_weather(city, ttl=3600):


    city = (city or "").strip()

    if not city:

        return None


    now = time.time()

    hit = _cache.get(city)

    if hit and now - hit[0] < ttl:

        return hit[1]


    try:

        data = _fetch(city)

    except Exception:

        data = None


    if data:

        _cache[city] = (now, data)

    elif hit:

        # 刷新失败时用旧数据顶着

        return hit[1]


    return data


def _fetch(city):


    geo_url = _GEO_URL.format(
        name=urllib.parse.quote(city)
    )

    with urllib.request.urlopen(
        geo_url, timeout=8
    ) as r:

        geo = json.load(r)


    results = geo.get("results") or []

    if not results:

        return None


    lat = results[0]["latitude"]

    lon = results[0]["longitude"]


    fc_url = _FORECAST_URL.format(
        lat=lat, lon=lon
    )

    with urllib.request.urlopen(
        fc_url, timeout=8
    ) as r:

        forecast = json.load(r)


    current = forecast.get("current") or {}

    temp = current.get("temperature_2m")

    code = current.get("weather_code")


    if temp is None:

        return None


    return {
        "city": city,
        "temperature": temp,
        "weather": _CODES.get(code, "阴"),
    }
