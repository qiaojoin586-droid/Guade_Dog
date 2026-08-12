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

// ===== 语音 =====

export interface AsrResult {
  text: string;
  confidence: number;
}

export interface ChatResult {
  text: string;
  tool_called: string | null;
}

// ===== 导航 =====

export interface Location {
  lat: number;
  lng: number;
  accuracy?: number;
}

/** 当前位置（逆地理编码返回） */
export interface LocationResult {
  coords: { lat: number; lng: number };
  address: string;
  city: string;
  source: 'gps' | 'ip';
  tts_text: string;
}

/** 单步路线指令 */
export interface RouteStepItem {
  instruction: string;
  distance_m: number;
}

/** 路线总览 */
export interface RouteSummary {
  distance_m: number;
  duration_min: number;
  start_address: string;
  end_address: string;
}

/** 路线规划返回 */
export interface RouteResult {
  summary: RouteSummary;
  steps: RouteStepItem[];
  tts_text: string;
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
