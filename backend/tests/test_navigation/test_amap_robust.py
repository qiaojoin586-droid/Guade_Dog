"""高德客户端健壮性测试：脏字段容错（不触网）。"""

import pytest

from app.agents.navigation.service.amap import AmapClient, _to_int


def test_to_int_various():
    """null/字符串数字/浮点/非法值 → 容错转 int,不抛 TypeError。"""
    assert _to_int(None) == 0
    assert _to_int("120") == 120
    assert _to_int(120.9) == 120
    assert _to_int(True) == 1
    assert _to_int("abc") == 0
    assert _to_int("12.5") == 0          # 非整数串 → 默认值
    assert _to_int(None, default=9) == 9


@pytest.mark.asyncio
async def test_walking_parses_null_and_string_fields(monkeypatch):
    """高德返回字段为 null/字符串数字时不抛异常（原 int(None) 会击穿成 500）。"""
    client = AmapClient(key="test-key")

    async def fake_get(path, params):
        return {
            "route": {
                "origin": "起点",
                "destination": "终点",
                "paths": [{
                    "distance": None,
                    "duration": "1800",
                    "steps": [
                        {
                            "instruction": "直行",
                            "distance": None,
                            "duration": "300",
                            "road": "中关村大街",
                            "action": "直行",
                        },
                        {
                            "instruction": "右转",
                            "distance": 250,
                            "duration": None,
                            "road": "",
                            "action": "右转",
                        },
                    ],
                }],
            }
        }

    monkeypatch.setattr(client, "_get", fake_get)
    result = await client.walking((39.9, 116.4), (39.9, 116.5))

    assert result.distance_m == 0
    assert result.duration_s == 1800
    assert result.steps[0].distance_m == 0
    assert result.steps[0].duration_s == 300
    assert result.steps[1].distance_m == 250
    assert result.steps[1].duration_s == 0
