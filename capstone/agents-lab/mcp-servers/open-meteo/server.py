# -*- coding: utf-8 -*-
"""날씨 MCP 서버 — 내 PC 에서 돈다.

Open-Meteo 공개 API 로 지명을 찾고 날씨를 받아 온다. 열쇠가 필요 없다.
API 호출 자체는 인터넷을 쓰지만, 이 서버를 띄우는 데에는 표준 라이브러리만 쓴다.

MCP 의 stdio 전송 — 표준 입력으로 JSON 한 줄을 받고 표준 출력으로 JSON 한 줄을
돌려준다. 그 밖의 것은 절대 출력하지 않는다. 디버그 출력을 stdout 에 흘리면
프로토콜이 깨진다.

    initialize                 인사. 서버가 자기를 소개한다
    tools/list                 무엇을 할 수 있는지 알려준다  ← "광고"
    tools/call                 실제로 하나를 실행한다
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "open-meteo", "version": "1.0.0"}
TIMEOUT = 10

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO 날씨 코드 → 한글 설명 (Open-Meteo 문서 기준)
WEATHER_CODE = {
    0: "맑음", 1: "대체로 맑음", 2: "부분적으로 흐림", 3: "흐림",
    45: "안개", 48: "서리 안개",
    51: "약한 이슬비", 53: "이슬비", 55: "강한 이슬비",
    56: "약한 어는 이슬비", 57: "어는 이슬비",
    61: "약한 비", 63: "비", 65: "강한 비",
    66: "약한 어는비", 67: "어는비",
    71: "약한 눈", 73: "눈", 75: "강한 눈", 77: "싸락눈",
    80: "약한 소나기", 81: "소나기", 82: "강한 소나기",
    85: "약한 눈소나기", 86: "강한 눈소나기",
    95: "뇌우", 96: "약한 우박 동반 뇌우", 99: "강한 우박 동반 뇌우",
}


# ── Open-Meteo 호출 ───────────────────────────────────────────────────

def _get(url, params):
    query = urllib.parse.urlencode(params)
    with urllib.request.urlopen("%s?%s" % (url, query), timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def _geocode(name):
    data = _get(GEOCODE_URL, {"name": name, "count": 5, "language": "ko", "format": "json"})
    return data.get("results") or []


def _place_label(place, fallback):
    parts = [place.get("name", fallback)]
    if place.get("admin1"):
        parts.append(place["admin1"])
    if place.get("country"):
        parts.append(place["country"])
    return ", ".join(p for p in parts if p)


# ── 도구 ──────────────────────────────────────────────────────────────

def tool_search_location(args):
    query = (args.get("query") or "").strip()
    if not query:
        return "찾을 지명을 넣어 주세요."
    try:
        results = _geocode(query)
    except (urllib.error.URLError, ValueError, OSError) as exc:
        return "지명을 찾지 못했습니다: %s" % str(exc)[:150]
    if not results:
        return "'%s' 에 해당하는 지명을 찾지 못했습니다." % query
    return "\n".join(
        "- %s (위도 %.4f, 경도 %.4f)" % (
            _place_label(r, query), r.get("latitude", 0.0), r.get("longitude", 0.0))
        for r in results)


def tool_forecast(args):
    location = (args.get("location") or "").strip()
    if not location:
        return "지명을 넣어 주세요."
    try:
        results = _geocode(location)
    except (urllib.error.URLError, ValueError, OSError) as exc:
        return "지명을 찾지 못했습니다: %s" % str(exc)[:150]
    if not results:
        return "'%s' 에 해당하는 지명을 찾지 못했습니다." % location

    place = results[0]
    try:
        forecast = _get(FORECAST_URL, {
            "latitude": place.get("latitude"), "longitude": place.get("longitude"),
            "current": "temperature_2m,relative_humidity_2m,precipitation,"
                       "weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                    "precipitation_probability_max",
            "timezone": "auto", "forecast_days": 3,
        })
    except (urllib.error.URLError, ValueError, OSError) as exc:
        return "예보를 받지 못했습니다: %s" % str(exc)[:150]

    label = _place_label(place, location)
    cur = forecast.get("current") or {}
    lines = ["%s 지금 날씨" % label,
             "- %s, %.1f°C (습도 %s%%, 바람 %s km/h)" % (
                 WEATHER_CODE.get(cur.get("weather_code"), "알 수 없음"),
                 cur.get("temperature_2m", 0.0),
                 cur.get("relative_humidity_2m", "?"),
                 cur.get("wind_speed_10m", "?"))]

    daily = forecast.get("daily") or {}
    dates = daily.get("time") or []
    codes = daily.get("weather_code") or []
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    rains = daily.get("precipitation_probability_max") or []
    if dates:
        lines.append("")
        lines.append("일별 예보")
        for i, date in enumerate(dates):
            lines.append("- %s: %s, %.0f~%.0f°C, 강수확률 %s%%" % (
                date,
                WEATHER_CODE.get(codes[i] if i < len(codes) else None, "알 수 없음"),
                lows[i] if i < len(lows) else 0.0,
                highs[i] if i < len(highs) else 0.0,
                rains[i] if i < len(rains) else "?"))
    return "\n".join(lines)


TOOLS = [
    {
        "name": "weather_search_location",
        "description": "지명으로 위치 후보를 찾는다. 같은 이름의 지역이 여럿일 때 먼저 확인할 때 쓴다. "
                       "지명 검색은 로마자(영문)만 인식한다 — 한글 지명이면 로마자로 바꿔서 넣는다 "
                       "(예: 서울 → Seoul).",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "찾을 지명 (로마자)"}},
            "required": ["query"],
        },
        "run": tool_search_location,
    },
    {
        "name": "weather_forecast",
        "description": "지명의 현재 날씨와 앞으로 3일 예보를 알려준다. 열쇠 없이 Open-Meteo "
                       "공개 API 를 쓴다. 같은 이름의 지역이 여럿이면 첫 결과를 쓴다. "
                       "지명 검색은 로마자(영문)만 인식한다 — 한글 지명이면 로마자로 바꿔서 넣는다 "
                       "(예: 서울 → Seoul, 부산 → Busan).",
        "inputSchema": {
            "type": "object",
            "properties": {"location": {"type": "string",
                                        "description": "지명, 로마자로 (예: Seoul, Busan)"}},
            "required": ["location"],
        },
        "run": tool_forecast,
    },
]


# ── JSON-RPC ──────────────────────────────────────────────────────────

def handle(message):
    """요청 하나를 처리한다. 알림(id 없음)이면 None 을 돌려준다."""
    method = message.get("method")
    mid = message.get("id")

    if method == "initialize":
        result = {"protocolVersion": PROTOCOL_VERSION,
                  "capabilities": {"tools": {}},
                  "serverInfo": SERVER_INFO}
    elif method == "tools/list":
        result = {"tools": [{"name": t["name"],
                             "description": t["description"],
                             "inputSchema": t["inputSchema"]} for t in TOOLS]}
    elif method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name")
        tool = next((t for t in TOOLS if t["name"] == name), None)
        if tool is None:
            return {"jsonrpc": "2.0", "id": mid,
                    "error": {"code": -32602, "message": "그런 도구가 없습니다: %s" % name}}
        try:
            text = tool["run"](params.get("arguments") or {})
        except Exception as exc:                        # noqa: BLE001
            text = "도구를 실행하지 못했습니다: %s" % str(exc)[:200]
        result = {"content": [{"type": "text", "text": text}]}
    elif mid is None:
        return None                                     # 알림에는 답하지 않는다
    else:
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": -32601, "message": "모르는 요청입니다: %s" % method}}

    if mid is None:
        return None
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def main():
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            continue
        reply = handle(message)
        if reply is not None:
            sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
