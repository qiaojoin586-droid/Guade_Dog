"""感知天气服务测试（mock httpx，不触网）。"""

from types import SimpleNamespace

import httpx
import pytest

from app.agents.perception.service import weather


def _fake_settings(key: str = "test-key", host: str = "abc123.qweatherapi.com"):
    return SimpleNamespace(QWEATHER_API_KEY=key, QWEATHER_API_HOST=host)


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeClient:
    """按调用顺序返回预置响应，并记录每次请求的 url/params。"""

    def __init__(self, payloads):
        self._payloads = list(payloads)
        self.calls: list[tuple[str, dict]] = []

    async def get(self, url, params=None):
        self.calls.append((url, dict(params or {})))
        if not self._payloads:
            raise AssertionError(f"意外多余的请求: {url}")
        return _FakeResponse(self._payloads.pop(0))


class _FakeCM:
    def __init__(self, client):
        self._client = client

    async def __aenter__(self):
        return self._client

    async def __aexit__(self, *exc):
        return False


def _mock_client(monkeypatch, payloads):
    fake = _FakeClient(payloads)
    monkeypatch.setattr(weather.httpx, "AsyncClient", lambda **kw: _FakeCM(fake))
    return fake


# ===== get_now_weather =====


@pytest.mark.asyncio
async def test_get_now_weather_success(monkeypatch):
    """正常路径: 实时天气 + 紫外线,且使用项目专属 Host 与 LocationID。"""
    monkeypatch.setattr(weather, "get_settings", lambda: _fake_settings())
    fake = _mock_client(monkeypatch, [
        {"code": "200", "now": {"temp": "28", "text": "晴", "humidity": "55"}},
        {"code": "200", "daily": [{"level": "4"}]},  # 指数接口字段为 level
    ])

    result = await weather.get_now_weather("北京")

    assert result["city"] == "北京"
    assert result["temperature"] == 28
    assert result["condition"] == "晴"
    assert result["humidity"] == 55
    assert result["uv_index"] == 4
    assert "28度" in result["tts_text"]
    assert "短袖" in result["dressing_advice"]
    # 走项目专属 Host + API KEY 简单认证 + LocationID(项目 Host 不接受城市名)
    assert fake.calls[0][0] == "https://abc123.qweatherapi.com/v7/weather/now"
    assert fake.calls[0][1]["key"] == "test-key"
    assert fake.calls[0][1]["location"] == "101010100"
    assert fake.calls[1][0] == "https://abc123.qweatherapi.com/v7/indices/1d"
    assert fake.calls[1][1]["location"] == "101010100"
    assert fake.calls[1][1]["type"] == "5"


@pytest.mark.asyncio
async def test_get_now_weather_empty_city(monkeypatch):
    """城市为空 → ValueError(调用方转追问文案)。"""
    monkeypatch.setattr(weather, "get_settings", lambda: _fake_settings())
    with pytest.raises(ValueError):
        await weather.get_now_weather("   ")


@pytest.mark.asyncio
async def test_get_now_weather_missing_key(monkeypatch):
    """未配置 QWEATHER_API_KEY → QWeatherError。"""
    monkeypatch.setattr(weather, "get_settings", lambda: _fake_settings(key=""))
    with pytest.raises(weather.QWeatherError):
        await weather.get_now_weather("北京")


@pytest.mark.asyncio
async def test_get_now_weather_api_error_code(monkeypatch):
    """和风返回非 200 code(如 403 Invalid Host)→ QWeatherError 且不抛裸异常。"""
    monkeypatch.setattr(weather, "get_settings", lambda: _fake_settings())
    _mock_client(monkeypatch, [{"code": "403"}])

    with pytest.raises(weather.QWeatherError) as exc_info:
        await weather.get_now_weather("北京")
    assert "403" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_now_weather_missing_temp(monkeypatch):
    """响应缺少温度字段 → QWeatherError(不返回伪温度)。"""
    monkeypatch.setattr(weather, "get_settings", lambda: _fake_settings())
    _mock_client(monkeypatch, [{"code": "200", "now": {"text": "晴", "humidity": None}}])

    with pytest.raises(weather.QWeatherError):
        await weather.get_now_weather("北京")


@pytest.mark.asyncio
async def test_get_now_weather_uv_failure_degrades(monkeypatch):
    """紫外线指数查询失败 → uv_index=None,整体不失败。"""
    monkeypatch.setattr(weather, "get_settings", lambda: _fake_settings())
    _mock_client(monkeypatch, [
        {"code": "200", "now": {"temp": "15", "text": "多云", "humidity": None}},
        {"code": "404"},  # 指数接口失败
    ])

    result = await weather.get_now_weather("北京")

    assert result["temperature"] == 15
    assert result["uv_index"] is None
    assert result["humidity"] is None  # 源数据缺失 → None,不伪造 0


# ===== 城市名 → LocationID 解析 =====


def test_resolve_location_known_city():
    assert weather._resolve_location("北京") == "101010100"
    assert weather._resolve_location("北京市") == "101010100"  # 兼容带「市」后缀
    assert weather._resolve_location("深圳") == "101280601"


def test_resolve_location_coords_passthrough():
    """经纬度坐标(和风格式 lng,lat)直接透传。"""
    assert weather._resolve_location("116.41,39.92") == "116.41,39.92"


def test_resolve_location_unknown_city_returns_none():
    """内置表未覆盖 → None(调用方走 GeoAPI 动态解析)。"""
    assert weather._resolve_location("商丘市") is None
    assert weather._resolve_location("  ") is None


@pytest.mark.asyncio
async def test_get_now_weather_unknown_city_lookup_fail(monkeypatch):
    """GeoAPI 解析失败(未订阅/查无此城)→ ValueError,且不发无效天气请求。"""
    monkeypatch.setattr(weather, "get_settings", lambda: _fake_settings())
    fake = _mock_client(monkeypatch, [{"code": "404"}])

    with pytest.raises(ValueError) as exc_info:
        await weather.get_now_weather("不存在的小县城")
    assert "暂不支持" in str(exc_info.value)
    assert len(fake.calls) == 1  # 只有 GeoAPI 查询
    assert "city/lookup" in fake.calls[0][0]


@pytest.mark.asyncio
async def test_get_now_weather_geolookup_city(monkeypatch):
    """内置表外的地级市(商丘)→ GeoAPI 解析 LocationID 后查询,并缓存。"""
    monkeypatch.setattr(weather, "get_settings", lambda: _fake_settings())
    fake = _mock_client(monkeypatch, [
        {"code": "200", "location": [{"name": "商丘", "id": "101181001"}]},
        {"code": "200", "now": {"temp": "24", "text": "多云", "humidity": "60"}},
        {"code": "200", "daily": [{"level": "3"}]},
    ])

    result = await weather.get_now_weather("商丘市")

    assert result["city"] == "商丘"  # 使用 GeoAPI 返回的规范城市名
    assert result["temperature"] == 24
    assert fake.calls[0][0].endswith("/geo/v2/city/lookup")
    assert fake.calls[1][1]["location"] == "101181001"

    # 第二次查询走缓存,不再发 GeoAPI 请求
    fake2 = _mock_client(monkeypatch, [
        {"code": "200", "now": {"temp": "25", "text": "晴", "humidity": "50"}},
        {"code": "200", "daily": [{"level": "2"}]},
    ])
    result2 = await weather.get_now_weather("商丘市")
    assert result2["temperature"] == 25
    assert len(fake2.calls) == 2  # 只有 weather + uv


@pytest.mark.asyncio
async def test_get_json_http_error_includes_body(monkeypatch):
    """HTTP 4xx 时错误信息带上和风官方响应体,便于排查。"""

    class _BadResponse:
        status_code = 400
        text = '{"error":{"title":"Invalid Parameter"}}'

        def raise_for_status(self):
            raise httpx.HTTPStatusError(
                "400", request=httpx.Request("GET", "https://x"), response=self,
            )

    class _ErrClient:
        async def get(self, url, params=None):
            return _BadResponse()

    class _ErrCM:
        async def __aenter__(self):
            return _ErrClient()

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(weather.httpx, "AsyncClient", lambda **kw: _ErrCM())
    with pytest.raises(weather.QWeatherError) as exc_info:
        await weather._get_json(_ErrClient(), "/v7/weather/now", "h.qweatherapi.com", "k", location="101010100")
    assert "Invalid Parameter" in str(exc_info.value)


# ===== 穿衣建议规则 =====


def test_dressing_advice_rules():
    assert "短袖" in weather._dressing_advice(30)
    assert "薄长袖" in weather._dressing_advice(22)
    assert "外套" in weather._dressing_advice(15)
    assert "厚外套" in weather._dressing_advice(5)
    assert "羽绒服" in weather._dressing_advice(-5)


@pytest.mark.asyncio
async def test_uv_strong_appends_sunscreen_hint(monkeypatch):
    """紫外线 ≥6 时播报文案追加防晒提示。"""
    monkeypatch.setattr(weather, "get_settings", lambda: _fake_settings())
    _mock_client(monkeypatch, [
        {"code": "200", "now": {"temp": "30", "text": "晴", "humidity": "40"}},
        {"code": "200", "daily": [{"level": "7"}]},
    ])

    result = await weather.get_now_weather("三亚")
    assert result["uv_index"] == 7
    assert "防晒" in result["tts_text"]


# ===== /perception/weather 接口 =====


@pytest.fixture
def client():
    from app.main import create_app

    from app.dependencies import get_current_user

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_weather_endpoint_success(client, monkeypatch):
    """接口正常路径: 返回统一成功体,request_id 非空。"""
    from app.agents.perception import api as perception_api

    async def fake_now(city):
        return {
            "city": city,
            "temperature": 28,
            "condition": "晴",
            "humidity": 55,
            "uv_index": 4,
            "dressing_advice": "天气炎热，建议穿短袖",
            "tts_text": "北京现在晴，气温28度。",
        }

    monkeypatch.setattr(perception_api, "get_now_weather", fake_now)
    r = await client.get("/api/v1/perception/weather", params={"city": "北京"})

    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["data"]["temperature"] == 28
    assert body["request_id"] != ""  # request_id 链路已修复


@pytest.mark.asyncio
async def test_weather_endpoint_empty_city(client):
    """空城市 → 40001 错误体,request_id 非空。"""
    r = await client.get("/api/v1/perception/weather", params={"city": "  "})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 40001
    assert body["request_id"] != ""


@pytest.mark.asyncio
async def test_weather_endpoint_unknown_city(client, monkeypatch):
    """不支持的城市 → 40001,message 为服务给出的提示。"""
    from app.agents.perception import api as perception_api

    async def fake_now(city):
        raise ValueError(f"暂不支持查询「{city}」，请查询直辖市或省会等主要城市")

    monkeypatch.setattr(perception_api, "get_now_weather", fake_now)
    r = await client.get("/api/v1/perception/weather", params={"city": "不存在的小县城"})
    body = r.json()
    assert body["code"] == 40001
    assert "暂不支持" in body["message"]


@pytest.mark.asyncio
async def test_weather_endpoint_requires_auth():
    """未携带 token 访问 /perception/weather → 401/40101。"""
    from app.main import create_app

    app = create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as anon:
        r = await anon.get("/api/v1/perception/weather", params={"city": "北京"})
    assert r.status_code == 401
    assert r.json()["code"] == 40101
