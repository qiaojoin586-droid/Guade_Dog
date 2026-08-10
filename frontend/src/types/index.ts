/**
 * TypeScript 类型定义。
 */

// ===== Agent 协议类型 =====

export interface AgentRequest {
  session_id: string;
  user_id: string;
  intent: string;
  params: Record<string, unknown>;
  context: Record<string, unknown>;
}

export interface AgentResponse {
  text: string;
  action: string | null;
  data: Record<string, unknown> | null;
  needs_followup: boolean;
}

// ===== API 响应格式 =====

export interface ApiResponse<T = unknown> {
  code: number;
  data: T;
  request_id: string;
}

export interface ApiError {
  code: number;
  message: string;
  detail?: unknown;
  request_id: string;
}

// ===== 用户 =====

export interface User {
  id: string;
  name: string;
  role: 'blind' | 'family' | 'admin';
  phone?: string;
  email?: string;
}

// ===== 导航 =====

export interface Location {
  lat: number;
  lng: number;
  accuracy?: number;
}

export interface RouteInfo {
  origin: string;
  destination: string;
  distance: number;
  duration: number;
  geojson: object;
}

// ===== 天气 =====

export interface WeatherInfo {
  temperature: number;
  condition: string;
  humidity: number;
  uv_index: number;
  dressing_advice: string;
}
