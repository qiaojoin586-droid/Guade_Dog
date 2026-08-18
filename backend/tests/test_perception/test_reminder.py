"""提醒服务测试: 中文时间解析 + Agent 提醒流程(不触网)。"""

from datetime import datetime, timedelta

import pytest

from app.agents.perception.agent import PerceptionAgent
from app.agents.perception.service import reminder
from app.core.agent_protocol import AgentRequest, AgentResponse

NOW = datetime(2026, 8, 19, 10, 30, 0)


@pytest.fixture(autouse=True)
async def _cleanup_tasks():
    """测试结束后取消未到期的提醒任务,避免悬挂 asyncio 任务。"""
    yield
    await reminder.cancel_all()


# ===== parse_reminder_time 时间解析 =====


def test_parse_relative_minutes():
    assert reminder.parse_reminder_time("5分钟后", now=NOW) == NOW + timedelta(minutes=5)


def test_parse_relative_hours():
    assert reminder.parse_reminder_time("2小时后", now=NOW) == NOW + timedelta(hours=2)


def test_parse_half_hour():
    """口语「半小时后」→ 30 分钟。"""
    assert reminder.parse_reminder_time("半小时后", now=NOW) == NOW + timedelta(minutes=30)


def test_parse_cn_numeral_hour():
    """口语「一小时后」→ 1 小时。"""
    assert reminder.parse_reminder_time("一小时后", now=NOW) == NOW + timedelta(hours=1)


def test_parse_cn_numeral_clock():
    """口语「下午三点」→ 15:00。"""
    assert reminder.parse_reminder_time("下午三点", now=NOW) == datetime(2026, 8, 19, 15, 0)


def test_parse_tomorrow_morning():
    assert reminder.parse_reminder_time("明天上午9点", now=NOW) == datetime(2026, 8, 20, 9, 0)


def test_parse_afternoon_with_minutes():
    assert reminder.parse_reminder_time("下午3点30分", now=NOW) == datetime(2026, 8, 19, 15, 30)


def test_parse_evening():
    assert reminder.parse_reminder_time("晚上8点", now=NOW) == datetime(2026, 8, 19, 20, 0)


def test_parse_hhmm():
    assert reminder.parse_reminder_time("15:30", now=NOW) == datetime(2026, 8, 19, 15, 30)


def test_parse_past_clock_rolls_to_tomorrow():
    """「8点」已过且未写日期 → 顺延到明天。"""
    assert reminder.parse_reminder_time("8点", now=NOW) == datetime(2026, 8, 20, 8, 0)


def test_parse_unparseable_returns_none():
    assert reminder.parse_reminder_time("随便说个时间", now=NOW) is None
    assert reminder.parse_reminder_time("", now=NOW) is None


# ===== format_due 口语化描述 =====


def test_format_due_today_afternoon():
    assert reminder.format_due(datetime(2026, 8, 19, 15, 30), now=NOW) == "今天下午3点30分"


def test_format_due_tomorrow_morning():
    assert reminder.format_due(datetime(2026, 8, 20, 9, 0), now=NOW) == "明天上午9点"


# ===== PerceptionAgent reminder 分支 =====


@pytest.mark.asyncio
async def test_agent_set_reminder_success():
    agent = PerceptionAgent()
    req = AgentRequest(
        session_id="s1",
        user_id="u1",
        intent="reminder",
        params={"content": "吃药", "time": "半小时后"},
        context={},
    )
    resp = await agent.handle(req)
    assert isinstance(resp, AgentResponse)
    assert "吃药" in resp.text
    assert resp.needs_followup is False
    assert resp.data["content"] == "吃药"
    assert resp.data["due"]


@pytest.mark.asyncio
async def test_agent_reminder_missing_content():
    """缺内容 → 追问。"""
    agent = PerceptionAgent()
    req = AgentRequest(
        session_id="s1",
        user_id="u1",
        intent="reminder",
        params={"time": "半小时后"},
        context={},
    )
    resp = await agent.handle(req)
    assert "内容" in resp.text
    assert resp.needs_followup is True


@pytest.mark.asyncio
async def test_agent_reminder_bad_time():
    """时间解析不出 → 追问并给出示例格式。"""
    agent = PerceptionAgent()
    req = AgentRequest(
        session_id="s1",
        user_id="u1",
        intent="reminder",
        params={"content": "吃药", "time": "xx"},
        context={},
    )
    resp = await agent.handle(req)
    assert "时间" in resp.text
    assert resp.needs_followup is True


@pytest.mark.asyncio
async def test_orchestrator_routes_reminder():
    """reminder 意图经 orchestrator 路由到 Perception Agent(不触网)。"""
    from app.agents import get_orchestrator

    orch = get_orchestrator()
    req = AgentRequest(
        session_id="s1",
        user_id="u1",
        intent="reminder",
        params={"content": "吃药", "time": "半小时后"},
        context={},
    )
    resp = await orch.route(req)
    assert isinstance(resp, AgentResponse)
    assert "吃药" in resp.text
    assert "提醒" in resp.text
