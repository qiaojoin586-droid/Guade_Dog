/**
 * 导航服务 API。
 *
 * 对接后端 Navigation Agent 的 REST 端点。
 */

import api, { getVoiceTextForError } from './api';
import type { LocationResult, RouteResult } from '../types';

/** 后端返回结构可能是成功 {code:200, data:...} 或失败 {code:4xxxx, message:...} */
interface ApiBody<T> {
  code: number;
  data?: T;
  message?: string;
}

/** 从响应中取 data; 失败时把 message 或错误码映射文案作为异常抛出 */
function unwrap<T>(body: ApiBody<T>): T {
  if (body.code === 200 && body.data !== undefined) {
    return body.data;
  }
  const msg = body.message || getVoiceTextForError(body.code);
  throw new Error(msg);
}

/**
 * 获取浏览器 GPS 坐标（包装为 Promise）。
 * 失败时返回 null，调用方负责降级提示。
 * 返回的 accuracy 为浏览器自报的定位精度(米)——桌面浏览器无 GPS 芯片,
 * 用 WiFi/网络推算,accuracy 可能很大甚至跨市错误,后端会据此调整播报措辞。
 *
 * @param opts - timeoutMs 超时毫秒；enableHighAccuracy 是否高精度。
 *   语音对话场景用短超时+低精度（maximumAge 60s 复用缓存，不重复触发定位）。
 */
function getBrowserLocation(
  opts: { timeoutMs?: number; enableHighAccuracy?: boolean } = {},
): Promise<{ lat: number; lng: number; accuracy?: number } | null> {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve(null);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) =>
        resolve({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        }),
      () => resolve(null),
      {
        enableHighAccuracy: opts.enableHighAccuracy ?? true,
        timeout: opts.timeoutMs ?? 10000,
        maximumAge: 60000,
      },
    );
  });
}

/**
 * 获取当前位置（逆地理编码）。
 *
 * 流程: 浏览器 GPS → 后端逆地理编码 → 返回地址 + 播报文案。
 * GPS 被拒/超时时传空参数，后端用 IP 粗定位兜底。
 */
export async function getCurrentLocation(): Promise<LocationResult> {
  const coords = await getBrowserLocation();
  const params = coords
    ? `?lat=${coords.lat}&lng=${coords.lng}`
    : '';
  const { data } = await api.get<ApiBody<LocationResult>>(`/navigation/location${params}`);
  return unwrap(data);
}

/**
 * 规划步行路线。
 *
 * @param destination - 目的地地址或名称
 * @param origin - 起点坐标，不传则后端用 IP 粗定位兜底
 */
export async function planRoute(
  destination: string,
  origin?: { lat: number; lng: number } | null,
): Promise<RouteResult> {
  const body: { destination: string; origin?: { lat: number; lng: number } } = { destination };
  if (origin) {
    body.origin = origin;
  }
  const { data } = await api.post<ApiBody<RouteResult>>('/navigation/route', body);
  return unwrap(data);
}

/**
 * 获取浏览器 GPS 坐标（不调后端，仅拿坐标）。
 */
export { getBrowserLocation };

/**
 * 周边 POI 查询（预留，下期实现）。
 */
export async function searchNearbyPOI(query: string, location?: { lat: number; lng: number }) {
  const { data } = await api.get('/navigation/poi', { params: { query, ...location } });
  return data.data;
}
