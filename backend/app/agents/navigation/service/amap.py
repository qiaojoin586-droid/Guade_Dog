"""高德地图 Web 服务客户端。

封装三个核心 API：
  - regeo:      逆地理编码（坐标 → 地址）
  - walking:    步行路径规划（起点 → 终点 → 路线步骤）
  - ip_location: IP 粗定位（降级链第 2 级）

高德文档: https://lbs.amap.com/api/webservice/summary/

注意事项:
  1. 高德 location 参数格式为 "经度,纬度"（与常见 lat,lng 顺序相反），本模块入参统一用 (lat, lng)，
     方法内部负责转换。
  2. 每次调用设 8s 超时，失败抛 AmapError，由调用方兜底。
  3. 数字签名(HMAC SHA1)预留开关位，当前未启用。
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://restapi.amap.com/v3"
TIMEOUT = 8.0


class AmapError(Exception):
    """高德 API 失败（超时/参数/key无效/status=0）。"""

    def __init__(self, message: str, code: str = "") -> None:
        super().__init__(message)
        self.code = code


# ============================================================
# 数据类
# ============================================================


@dataclass
class RegeoResult:
    """逆地理编码返回。"""

    formatted_address: str  # "北京市东城区东华门街道天安门"
    city: str               # "北京市"
    province: str           # "北京市"
    district: str           # "东城区"
    adcode: str             # 行政区划代码 "110101"


@dataclass
class WalkingStep:
    """步行路线单步。"""

    instruction: str   # "沿中关村大街向东北步行120米"
    distance_m: int    # 这一步的距离（米）
    duration_s: int    # 这一步的耗时（秒）
    road: str          # 道路名称
    action: str        # "直行" | "右转" | "左转" | "向左前方行走" | ...


@dataclass
class GeocodeResult:
    """地理编码返回。"""
    formatted_address: str  # "北京市东城区天安门"
    location: tuple[float, float]  # (lat, lng)
    adcode: str


@dataclass
class WalkingResult:
    """步行路线规划返回。"""

    distance_m: int          # 总距离（米）
    duration_s: int          # 总耗时（秒）
    origin_address: str      # 起点大致地址
    dest_address: str        # 终点大致地址
    steps: list[WalkingStep]


# ============================================================
# 客户端
# ============================================================


class AmapClient:
    """高德 Web 服务客户端。

    Args:
        key: 高德 Web 服务 API Key。
        enable_signature: 是否启用数字签名（当前预留，默认 False）。
        private_key: 数字签名私钥（启用签名时必传）。
    """

    def __init__(
        self,
        key: str,
        enable_signature: bool = False,
        private_key: str | None = None,
    ) -> None:
        self._key = key
        self._enable_sig = enable_signature
        self._private_key = private_key

    # ----------------------------------------------------------
    # 公开方法
    # ----------------------------------------------------------

    async def regeo(self, lat: float, lng: float) -> RegeoResult:
        """逆地理编码：经纬度 → 结构化地址。

        GET /v3/geocode/regeo
        """
        params = self._sign({"location": f"{lng},{lat}"})
        data = await self._get("/geocode/regeo", params)
        regeo = data.get("regeocode") or {}
        comp = regeo.get("addressComponent") or {}
        return RegeoResult(
            formatted_address=regeo.get("formatted_address", ""),
            city=self._first_str(comp.get("city")) or self._first_str(comp.get("province")),
            province=self._first_str(comp.get("province")),
            district=self._first_str(comp.get("district")),
            adcode=comp.get("adcode", ""),
        )

    async def geocode(self, address: str, city: str = "") -> GeocodeResult | None:
        """地理编码：地址文本 → 坐标。

        GET /v3/geocode/geo

        返回 None 表示解析不到。
        """
        params = self._sign({"address": address, "city": city})
        data = await self._get("/geocode/geo", params)
        geos = data.get("geocodes") or []
        if not geos:
            return None
        loc = geos[0].get("location", "")
        parts = loc.split(",")
        if len(parts) != 2:
            return None
        return GeocodeResult(
            formatted_address=geos[0].get("formatted_address", ""),
            location=(float(parts[1]), float(parts[0])),  # 转为 (lat, lng)
            adcode=geos[0].get("adcode", ""),
        )

    async def walking(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
    ) -> WalkingResult:
        """步行路径规划。

        GET /v3/direction/walking

        Args:
            origin: 起点坐标 (lat, lng)。
            destination: 终点坐标 (lat, lng)。
        """
        origin_str = f"{origin[1]},{origin[0]}"  # lng,lat
        dest_str = f"{destination[1]},{destination[0]}"

        params = self._sign({"origin": origin_str, "destination": dest_str})
        data = await self._get("/direction/walking", params)
        route = (data.get("route") or {}).get("paths") or []
        if not route:
            raise AmapError("步行路线规划返回空路径", code="NO_ROUTE")

        path = route[0]
        steps: list[WalkingStep] = []
        for s in path.get("steps", []):
            steps.append(WalkingStep(
                instruction=s.get("instruction", ""),
                distance_m=int(s.get("distance", 0)),
                duration_s=int(s.get("duration", 0)),
                road=self._first_str(s.get("road")),
                action=self._first_str(s.get("action")),
            ))

        return WalkingResult(
            distance_m=int(path.get("distance", 0)),
            duration_s=int(path.get("duration", 0)),
            origin_address=(data.get("route") or {}).get("origin", ""),
            dest_address=(data.get("route") or {}).get("destination", ""),
            steps=steps,
        )

    async def ip_location(self) -> RegeoResult | None:
        """IP 粗定位（降级链第 2 级）。

        GET /v3/ip —— 不传 ip 参数则使用请求方公网 IP。

        返回 None 表示 IP 定位也失败了（调用方继续降级）。
        """
        try:
            params = self._sign({})
            data = await self._get("/ip", params)
            # IP 定位返回字段与 regeo 不同，做一次适配
            province = self._first_str(data.get("province"))
            city = self._first_str(data.get("city"))
            adcode = data.get("adcode", "")
            if not province and not city:
                return None
            return RegeoResult(
                formatted_address=f"{province}{city}",
                city=city or province,
                province=province,
                district="",
                adcode=adcode,
            )
        except AmapError:
            logger.warning("IP 定位失败", exc_info=True)
            return None

    # ----------------------------------------------------------
    # 内部
    # ----------------------------------------------------------

    async def _get(self, path: str, params: dict) -> dict:
        """发 GET 请求，处理通用错误。"""
        url = f"{BASE_URL}{path}"
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                body = resp.json()
        except httpx.TimeoutException as exc:
            raise AmapError("高德 API 请求超时", code="TIMEOUT") from exc
        except httpx.HTTPError as exc:
            raise AmapError(f"高德 API 网络错误: {exc}", code="NETWORK") from exc

        status = body.get("status")
        if status != "1":
            info = body.get("info", "未知错误")
            logger.warning("高德 API 返回失败: status=%s info=%s", status, info)
            raise AmapError(f"高德 API 错误: {info}", code=str(body.get("infocode", "")))

        return body

    def _sign(self, params: dict) -> dict:
        """拼接 key；若启用数字签名则追加 sig 参数（当前预留）。"""
        params["key"] = self._key
        if self._enable_sig and self._private_key:
            raw = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            raw += self._private_key
            sig = hashlib.sha1(raw.encode()).hexdigest()
            params["sig"] = sig
        return params

    @staticmethod
    def _first_str(value) -> str:
        """高德部分字段返回 list 或 str，统一取第一个字符串。"""
        if value is None:
            return ""
        if isinstance(value, list):
            return str(value[0]) if value else ""
        return str(value) if value else ""
