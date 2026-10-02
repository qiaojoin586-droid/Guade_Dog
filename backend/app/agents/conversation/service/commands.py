"""语音指令大脑（演示版：回复写死，不调用真实导航/救援/识别业务）。

为什么不用 LLM：
- 盲人操作的可靠性优先，演示阶段必须“说什么就做什么”，不能因外部模型抖动而失效；
- 本模块把“AI 的判断”固化成规则 + 地址簿真实查询，回复文案全部写死，方便联调。

前端约定（CommandResult.action）：
- navigation.start  打开摄像头模拟画面（video/ 目录视频）并播报 data.followup_text
- navigation.stop   关闭画面
- sos.confirm       启动 10 秒确认窗口，超时未否认则发送 trigger="sos_timeout"
- sos.sent / sos.canceled
- vision.capture    打开摄像头模拟画面（images/ 目录图片）并播报 data.result_text
- address.saved / address.deleted / address.list / address.missing
- none              仅播报 text
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.addresses.schemas import AddressCreate, AddressUpdate
from app.addresses.service import (
    create_address,
    delete_address,
    find_by_alias,
    find_by_alias_exact,
    find_home,
    list_addresses,
    update_address,
)

logger = logging.getLogger(__name__)

# 素材路径（相对于前端站点根目录，由 Vite 中间件映射到仓库根的 video/ 与 images/）
VIDEO_PATH = "/video/navigation.mp4"
IMAGE_PATH = "/images/test.jpg"

# ---------- 写死的播报文案 ----------

SOS_CONFIRM_TEXT = (
    "检测到剧烈抖动。需要紧急求救吗？十秒内说“不需要”可以取消，不回答我将自动求救。"
)
SOS_SENT_TEXT = (
    "我已经联系救援队，并拨打了110和120，同时已将电话打给了您的紧急联系人。"
    "请保持冷静，救援马上就到。"
)
SOS_CANCELED_TEXT = "好的，已为您取消求救。如果身体不适，请随时告诉我。"

NAV_START_TEXT = "正在为您规划路线。"
NAV_FOLLOWUP_TEMPLATE = (
    "路线规划完成，摄像头已打开，现在带您前往{target}。请沿当前道路直行。"
)
NAV_STOP_TEXT = "已结束导航。"

VISION_START_TEXT = "正在打开摄像头拍照，请稍候。"
# 识别结果写死（演示阶段不调用真实视觉模型）
VISION_RESULTS = {
    "medicine": "识别完成。这是一盒阿莫西林胶囊，属于抗生素类药品，用于细菌感染。请按医生嘱咐的剂量服用，不要自行加量。",
    "currency": "识别完成。这是一张一百元人民币，请放心使用。",
    "general": "识别完成。这是一瓶矿泉水。",
}

HELP_TEXT = (
    "您可以说：我要去公司；我要回家；今天天气怎么样；帮我识别这个药品；这是多少钱；"
    "添加地址，公司，详细地址；删除公司地址；查看常用地址；我遇到危险了。"
)

FALLBACK_TEXT = (
    "这个指令我还没学会。您可以这样说：我要去公司，我要回家，"
    "帮我识别这个药品，这是多少钱，添加常用地址。"
)

ADDRESS_EMPTY_TEXT = (
    "您还没有添加常用地址。可以说：添加地址，公司，北京市朝阳区某某路一号。"
)
HOME_MISSING_TEXT = (
    "您还没有设置家庭地址。请说：添加地址，家，您的详细地址。"
)
ADDRESS_GUIDE_TEXT = (
    "请这样说：添加地址，公司，北京市朝阳区某某路一号。"
)

# ---------- 正则 ----------

_NEGATIVE_WORDS = ("不需要", "不用", "不要", "取消", "没事", "我很好", "没有危险", "停止求救")
_SOS_WORDS = ("救命", "救我", "求救", "报警", "有危险", "我不安全", "遇到危险", "出事了", "摔倒了")

_VISION_TRIGGER = (
    "识别", "看看", "看一下", "拍一下", "拍照", "认一下", "这是什么", "念一下", "读一下",
    "多少钱", "面额", "几张",
)
_VISION_TARGETS = (
    "药", "钱", "钞票", "人民币", "纸币", "假币", "说明书", "字", "瓶子", "东西",
    "物体", "面前", "这个", "手上的",
)

_NAV_RE = re.compile(
    r"^(?:请|麻烦)?(?:帮我|给我)?"
    r"(?:导航到|导航去|导航|带我去|带我到|我要去|我想去|我要到|我想到|我想回|我要回|去往|前往|怎么去|怎么走|去|到)"
    r"(?P<dest>.+)$"
)
_HOME_WORDS = ("家", "回家", "我家", "家里", "家中")

_ADD_ADDRESS_RE = re.compile(
    r"^(?:请|帮我)?(?:添加|新增|保存|记住|设置|录入)(?:一个|一下)?(?:常用)?地址"
    r"[，,、：:\s]*(?P<label>[^，,、：:\s]+)[，,、：:\s]+(?P<addr>.+)$"
)
_SET_ADDRESS_RE = re.compile(
    r"^把(?P<label>.+?)的?地址(?:设为|设置为|改成|改为|修改为|更新为)[，,：:\s]*(?P<addr>.+)$"
)
_DELETE_ADDRESS_RE = re.compile(
    r"^(?:请|帮我)?(?:删除|删掉|移除|去掉)(?:我的)?(?:常用)?地址[，,、：:\s]*(?P<label>.+)$"
)
_DELETE_ADDRESS_RE2 = re.compile(
    r"^(?:请|帮我)?(?:删除|删掉|移除|去掉)(?P<label>.+?)(?:的)?地址$"
)
_LIST_ADDRESS_HINT = ("哪些", "列表", "查看", "所有", "全部", "保存了", "有几个", "地址簿")


@dataclass
class CommandResult:
    """一次语音指令的处理结果。"""

    text: str
    action: str = "none"
    tool: str | None = None
    data: dict = field(default_factory=dict)


def _clean(text: str) -> str:
    """去掉标点与空格，便于规则匹配（不改动地址原文）。"""
    return re.sub(r"[\s，,。.！!？?、：:；;“”‘’\"']", "", text.strip())


def _strip_tail(text: str) -> str:
    """去掉目的地尾部的语气词。"""
    return re.sub(r"(吧|啊|呢|了|呀|哈)+$", "", text.strip())


def _sos_confirm() -> CommandResult:
    """进入 10 秒确认窗口。"""
    return CommandResult(
        text=SOS_CONFIRM_TEXT,
        action="sos.confirm",
        tool="safety.sos",
        data={
            "timeout_ms": 10_000,
            "cancel_words": list(_NEGATIVE_WORDS),
            "fake": True,
        },
    )


def _sos_sent() -> CommandResult:
    """确认求救（演示：固定文案，不接真实救援）。"""
    logger.warning("【模拟 SOS】已触发求救（演示阶段未接入真实救援）")
    return CommandResult(
        text=SOS_SENT_TEXT,
        action="sos.sent",
        tool="safety.sos",
        data={"fake": True, "channels": ["120", "110", "紧急联系人"]},
    )


def _sos_canceled() -> CommandResult:
    """取消求救。"""
    logger.info("【模拟 SOS】用户取消求救")
    return CommandResult(text=SOS_CANCELED_TEXT, action="sos.canceled", tool="safety.sos")


async def _address_list(db: AsyncSession, user_id: int) -> CommandResult:
    """播报地址簿。"""
    items = await list_addresses(db, user_id)
    if not items:
        return CommandResult(text=ADDRESS_EMPTY_TEXT, action="address.list", tool="address.list", data={"addresses": []})

    parts = [f"{item.label}，{item.address}" for item in items]
    text = f"您一共保存了{len(items)}个常用地址：" + "；".join(parts) + "。"
    return CommandResult(
        text=text,
        action="address.list",
        tool="address.list",
        data={"addresses": [{"id": i.id, "label": i.label, "address": i.address} for i in items]},
    )


async def _address_add(db: AsyncSession, user_id: int, label: str, address: str) -> CommandResult:
    """新增地址（真实入库）。"""
    label, address = _strip_tail(label), _strip_tail(address)
    try:
        # 复用 schema 做长度/空值校验
        item = await create_address(db, user_id, AddressCreate(label=label, address=address))
    except ValueError as exc:
        return CommandResult(text=str(exc), action="address.missing", tool="address.create")

    return CommandResult(
        text=f"已为您保存常用地址：{item.label}，{item.address}。以后您说“我要去{item.label}”，我就带您过去。",
        action="address.saved",
        tool="address.create",
        data={"id": item.id, "label": item.label, "address": item.address},
    )


async def _address_update(db: AsyncSession, user_id: int, label: str, address: str) -> CommandResult:
    """修改地址（真实入库）。"""
    label, address = _strip_tail(label), _strip_tail(address)
    item = await find_by_alias_exact(db, user_id, label)
    if item is None:
        matched = await find_by_alias(db, user_id, label)
        if matched is None:
            return CommandResult(
                text=f"我没有找到“{label}”这个地址。{ADDRESS_GUIDE_TEXT}",
                action="address.missing",
                tool="address.update",
            )
        item = matched

    try:
        updated = await update_address(db, user_id, item.id, AddressUpdate(address=address))
    except ValueError as exc:
        return CommandResult(text=str(exc), action="address.missing", tool="address.update")

    return CommandResult(
        text=f"已把{updated.label}的地址更新为{updated.address}。",
        action="address.saved",
        tool="address.update",
        data={"id": updated.id, "label": updated.label, "address": updated.address},
    )


async def _address_delete(db: AsyncSession, user_id: int, label: str) -> CommandResult:
    """删除地址（真实入库）。"""
    label = _strip_tail(label)
    item = await find_by_alias_exact(db, user_id, label) or await find_by_alias(db, user_id, label)
    if item is None:
        return CommandResult(
            text=f"我没有找到“{label}”这个地址。",
            action="address.missing",
            tool="address.delete",
        )
    await delete_address(db, user_id, item.id)
    return CommandResult(
        text=f"已删除常用地址：{item.label}。",
        action="address.deleted",
        tool="address.delete",
        data={"id": item.id, "label": item.label},
    )


async def _navigation(db: AsyncSession, user_id: int, dest: str) -> CommandResult:
    """导航：地址簿优先匹配，命中别名就用真实地址；回复全部写死。"""
    dest = _strip_tail(dest)
    is_home = dest in _HOME_WORDS

    item = await find_home(db, user_id) if is_home else await find_by_alias(db, user_id, dest)

    if item is None:
        if is_home:
            return CommandResult(
                text=HOME_MISSING_TEXT,
                action="address.missing",
                tool="navigation.start",
                data={"is_home": True},
            )
        target_label = dest
        target_address = dest
        matched = False
    else:
        target_label = item.label
        target_address = item.address
        matched = True

    followup = NAV_FOLLOWUP_TEMPLATE.format(target=target_label)
    return CommandResult(
        text=NAV_START_TEXT,
        action="navigation.start",
        tool="navigation.start",
        data={
            "destination": target_address,
            "label": target_label,
            "is_home": is_home,
            "matched_address": matched,
            "camera": "simulated",
            "video": VIDEO_PATH,
            "followup_text": followup,
            "followup_delay_ms": 1800,
            "fake": True,
        },
    )


def _vision_category(text: str) -> str:
    """按关键词判断识别类别。"""
    if any(word in text for word in ("钱", "钞票", "人民币", "纸币", "假币", "多少面额")):
        return "currency"
    if any(word in text for word in ("药", "说明书", "胶囊", "药片", "药盒")):
        return "medicine"
    return "general"


async def handle(
    text: str,
    user_id: int,
    db: AsyncSession,
    trigger: str = "",
) -> CommandResult:
    """解析一条语音指令并返回可播报结果。

    Args:
        text: 语音识别文本
        user_id: 当前用户ID（地址簿查询用）
        db: 数据库会话
        trigger: 前端事件触发（shake=剧烈抖动，sos_timeout=10秒未回应，sos_cancel=用户否认）
    """
    # ---------- 1. 前端事件触发 ----------
    if trigger == "shake":
        return _sos_confirm()
    if trigger == "sos_timeout":
        return _sos_sent()
    if trigger == "sos_cancel":
        return _sos_canceled()

    raw = text.strip()
    clean = _clean(raw)
    if not clean:
        return CommandResult(text="我没有听清，请再说一次。")

    # ---------- 2. 紧急求救（最高优先级） ----------
    if any(word in clean for word in _SOS_WORDS):
        return _sos_confirm()

    # ---------- 3. 结束导航（先于短句否认，避免“取消导航”被当成取消求救） ----------
    if re.search(r"(结束|停止|退出|关闭|取消)导航", clean):
        return CommandResult(text=NAV_STOP_TEXT, action="navigation.stop")

    # ---------- 4. 帮助 ----------
    if any(word in clean for word in ("帮助", "能做什么", "能干什么", "怎么用", "你会什么")):
        return CommandResult(text=HELP_TEXT, action="help")

    # ---------- 5. 短句否认（SOS 确认窗口内的“不需要”） ----------
    if (
        len(clean) <= 8
        and any(word in clean for word in _NEGATIVE_WORDS)
        and not any(word in clean for word in ("导航", "地址", "识别", "天气", "提醒"))
    ):
        return _sos_canceled()

    # ---------- 6. 安全助手：拍照识别 ----------
    if any(word in clean for word in _VISION_TRIGGER) and any(
        word in clean for word in _VISION_TARGETS
    ):
        category = _vision_category(clean)
        return CommandResult(
            text=VISION_START_TEXT,
            action="vision.capture",
            tool=f"safety.{category}.recognize",
            data={
                "category": category,
                "image": IMAGE_PATH,
                "result_text": VISION_RESULTS[category],
                "followup_delay_ms": 1600,
                "fake": True,
            },
        )

    # ---------- 7. 地址簿增删改查（真实入库） ----------
    if "地址" in raw:
        match = _SET_ADDRESS_RE.match(raw)
        if match:
            return await _address_update(db, user_id, match.group("label"), match.group("addr"))

        match = _ADD_ADDRESS_RE.match(raw)
        if match:
            return await _address_add(db, user_id, match.group("label"), match.group("addr"))

        match = _DELETE_ADDRESS_RE.match(raw) or _DELETE_ADDRESS_RE2.match(raw)
        if match:
            return await _address_delete(db, user_id, match.group("label"))

        if any(word in clean for word in _LIST_ADDRESS_HINT) or clean in ("地址", "常用地址", "地址簿"):
            return await _address_list(db, user_id)

        if re.match(r"^(?:请|帮我)?(?:添加|新增|保存|记住|设置|录入).*地址$", raw):
            return CommandResult(text=ADDRESS_GUIDE_TEXT, action="address.missing", tool="address.create")

    # ---------- 8. 导航 ----------
    match = _NAV_RE.match(clean)
    if match:
        dest = match.group("dest")
        if dest:
            return await _navigation(db, user_id, dest)

    # ---------- 9. 兜底：交给 LLM + 工具链（天气/定位/距离/提醒/闲聊） ----------
    # 规则大脑只负责演示版固定流程，其余意图不在这里硬编码，
    # 由 conversation/api.py 转投 chat()（LLM 判定意图并调用工具）。
    logger.info("规则未命中，转 LLM 处理 text_len=%d", len(raw))
    return CommandResult(text="", action="fallback")
