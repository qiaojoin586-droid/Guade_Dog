"""和风天气 Web 服务客户端。

封装三个 API：
  - /geo/v2/city/lookup  城市名 → LocationID(GeoAPI,动态解析任意城市)
  - /v7/weather/now   实时天气（温度/天气现象/湿度）
  - /v7/indices/1d    生活指数（紫外线），失败时忽略该字段

认证: API KEY 简单认证（?key=xxx）。官方提示 2027-01-01 起 API KEY
认证每日调用量受限、SDK 5+ 不再支持，长期建议迁移 JWT 认证。

⚠ 每个和风项目有专属 API Host（控制台「项目管理」中查看，如
xxxx.qweatherapi.com），必须通过 QWEATHER_API_HOST 配置；
通用 devapi.qweather.com 会返回 403 Invalid Host。

⚠ 项目专属 Host 的天气接口只接受 LocationID 或经纬度坐标作为 location 参数
（城市名返回 400 Invalid Parameter）。城市名解析策略：
  1. 内置常用城市映射表直接命中(省一次 API 调用);
  2. 未命中 → GeoAPI /geo/v2/city/lookup 动态查询并缓存;
  3. GeoAPI 不可用(未订阅)或查无此城 → 报错提示,不瞎猜。
"""

from __future__ import annotations

import logging
import re

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

TIMEOUT = 8.0

# 紫外线指数 type=5
_UV_TYPE = "5"

# 常用城市 → LocationID（和风城市代码）。项目 Host 不接受城市名参数，
# 且 GeoAPI 查询接口可能未订阅，故内置映射表兜底。
CITY_LOCATION_MAP: dict[str, str] = {
    "北京": "101010100", "上海": "101020100", "天津": "101030100",
    "重庆": "101040100", "哈尔滨": "101050101", "长春": "101060101",
    "沈阳": "101070101", "大连": "101070201", "呼和浩特": "101080101",
    "石家庄": "101090101", "太原": "101100101", "西安": "101110101",
    "济南": "101120101", "青岛": "101120201", "乌鲁木齐": "101130101",
    "拉萨": "101140101", "西宁": "101150101", "兰州": "101160101",
    "银川": "101170101", "郑州": "101180101", "南京": "101190101",
    "无锡": "101190201", "苏州": "101190401", "武汉": "101200101",
    "杭州": "101210101", "宁波": "101210401", "温州": "101210701",
    "合肥": "101220101", "福州": "101230101", "厦门": "101230201",
    "南昌": "101240101", "长沙": "101250101", "贵阳": "101260101",
    "成都": "101270101", "广州": "101280101", "深圳": "101280601",
    "佛山": "101280800", "东莞": "101281601", "珠海": "101280701",
    "南宁": "101300101", "桂林": "101300501", "海口": "101310101",
    "三亚": "101310201", "昆明": "101290101", "丽江": "101291401",
    "大理": "101290201", "香港": "101320101", "澳门": "101330101",
    "台北": "101340101",
}

# 经纬度格式 "lng,lat"（和风要求的顺序），直接透传
_COORDS_RE = re.compile(r"^\d{1,3}(\.\d+)?,\d{1,2}(\.\d+)?$")


class QWeatherError(Exception):
    """和风天气 API 失败（未配置密钥/网络/鉴权/返回错误码）。"""


def _parse_int(value) -> int | None:
    """和风字段可能是 null/字符串数字，容错转 int；解析不出返回 None。"""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.strip()))
        except ValueError:
            return None
    return None


def _dressing_advice(temp: int) -> str:
    """按温度给出穿衣建议（规则化，无 LLM 成本且稳定）。"""
    if temp >= 28:
        return "天气炎热，建议穿短袖等清凉衣物，注意防暑"
    if temp >= 20:
        return "天气舒适，建议穿薄长袖或短袖"
    if temp >= 10:
        return "天气较凉，建议穿外套或毛衣"
    if temp >= 0:
        return "天气寒冷，建议穿厚外套和毛衣，注意保暖"
    return "天气严寒，建议穿羽绒服，尽量减少外出"


# GeoAPI 查询失败的城市名(项目未订阅 GeoAPI 时避免每次请求都重试)
_LOOKUP_MISS: set[str] = set()


def _resolve_location(city: str) -> str | None:
    """城市名/坐标 → 和风 location 参数(仅内置映射与坐标)。

    优先级: 内置映射表(去掉尾部「市」后再查) > 经纬度坐标直传。
    内置表查不到返回 None，由调用方走 GeoAPI 动态查询。
    """
    key = city.strip()
    if not key:
        return None
    if _COORDS_RE.match(key):
        return key
    if key in CITY_LOCATION_MAP:
        return CITY_LOCATION_MAP[key]
    # 兼容「北京市」「上海市」等带行政区后缀的写法
    if key.endswith("市") and key[:-1] in CITY_LOCATION_MAP:
        return CITY_LOCATION_MAP[key[:-1]]
    return None


async def _get_json(client: httpx.AsyncClient, path: str, host: str, key: str, **params) -> dict:
    """请求和风 API 并处理通用错误，返回响应 JSON。"""
    url = f"https://{host}{path}"
    params = {"key": key, **params}
    try:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()
    except httpx.TimeoutException as exc:
        raise QWeatherError("和风天气 API 请求超时") from exc
    except httpx.HTTPStatusError as exc:
        # 带上响应体里的官方错误信息（如 Invalid Parameter），便于定位
        raise QWeatherError(f"和风天气 API 返回 HTTP {exc.response.status_code}: {exc.response.text[:200]}") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise QWeatherError(f"和风天气 API 网络/解析错误: {exc}") from exc


async def _lookup_location_id(
    client: httpx.AsyncClient, host: str, key: str, city: str,
) -> tuple[str, str] | None:
    """GeoAPI 动态解析城市名 → (LocationID, 规范城市名)。

    成功后写入内置映射缓存,后续查询不再发请求;
    失败(未订阅 GeoAPI/查无此城)记入 _LOOKUP_MISS,返回 None。
    """
    if city in _LOOKUP_MISS:
        return None
    try:
        body = await _get_json(client, "/geo/v2/city/lookup", host, key, location=city)
    except QWeatherError:
        _LOOKUP_MISS.add(city)
        return None

    locations = body.get("location") or []
    if body.get("code") != "200" or not locations:
        _LOOKUP_MISS.add(city)
        return None
    location_id = locations[0].get("id")
    if not location_id:
        _LOOKUP_MISS.add(city)
        return None

    location_id = str(location_id)
    name = str(locations[0].get("name") or city)
    CITY_LOCATION_MAP[city] = location_id  # 缓存命中,省后续 API 调用
    return location_id, name


async def get_now_weather(city: str) -> dict:
    """查询城市实时天气，返回结构化结果（含播报文案）。

    Returns:
        {
            "city": 城市名,
            "temperature": 气温(℃),
            "condition": 天气现象("晴"),
            "humidity": 相对湿度(%) | None,
            "uv_index": 紫外线指数 | None,
            "dressing_advice": 穿衣建议,
            "tts_text": 可直接播报的文本,
        }

    Raises:
        ValueError: city 为空或解析不到对应城市。
        QWeatherError: 密钥缺失、API 失败或响应缺少温度字段。
    """
    city = (city or "").strip()
    if not city:
        raise ValueError("城市不能为空")

    settings = get_settings()
    key = settings.QWEATHER_API_KEY or ""
    if not key:
        raise QWeatherError("QWEATHER_API_KEY 未配置")
    host = (settings.QWEATHER_API_HOST or "devapi.qweather.com").strip()

    display_name = city
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        location = _resolve_location(city)
        if location is None:
            # 内置表未覆盖(如地级市商丘)→ GeoAPI 动态解析,全量城市可查
            resolved = await _lookup_location_id(client, host, key, city)
            if resolved is None:
                raise ValueError(
                    f"暂不支持查询「{city}」，请换个城市试试，或输入「城市名+区县」"
                )
            location, display_name = resolved

        body = await _get_json(client, "/v7/weather/now", host, key, location=location)
        if body.get("code") != "200":
            raise QWeatherError(f"和风天气返回错误 code={body.get('code')}")

        now = body.get("now") or {}
        temp = _parse_int(now.get("temp"))
        if temp is None:
            raise QWeatherError("和风天气响应缺少温度字段")

        uv_index = await _get_uv_index(client, host, key, location)

    humidity = _parse_int(now.get("humidity"))
    condition = str(now.get("text") or "未知")
    advice = _dressing_advice(temp)

    parts = [f"{display_name}现在{condition}", f"气温{temp}度"]
    if humidity is not None:
        parts.append(f"湿度百分之{humidity}")
    tts_text = "，".join(parts) + "。" + advice
    if uv_index is not None and uv_index >= 6:
        tts_text += "，紫外线较强，外出请注意防晒"

    return {
        "city": display_name,
        "temperature": temp,
        "condition": condition,
        "humidity": humidity,
        "uv_index": uv_index,
        "dressing_advice": advice,
        "tts_text": tts_text,
    }


async def _get_uv_index(client: httpx.AsyncClient, host: str, key: str, location: str) -> int | None:
    """查询今日紫外线指数；失败时忽略该字段（降级返回 None）。

    指数接口返回的字段是 level（如 "4"），部分老版本为 value，两者都兼容。
    """
    try:
        body = await _get_json(
            client, "/v7/indices/1d", host, key, location=location, type=_UV_TYPE,
        )
        if body.get("code") != "200":
            return None
        for item in body.get("daily") or []:
            value = _parse_int(item.get("level"))
            if value is None:
                value = _parse_int(item.get("value"))
            if value is not None:
                return value
    except QWeatherError:
        logger.warning("紫外线指数查询失败，忽略该字段", exc_info=True)
    return None
