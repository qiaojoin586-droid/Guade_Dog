/**
 * 语音指令服务：调用后端 /conversation/command（演示版规则大脑）。
 *
 * 后端返回 action，前端据此打开摄像头模拟画面或启动求救确认倒计时。
 */

import api from './api';

export type VoiceAction =
  | 'none'
  | 'help'
  | 'chat'
  | 'navigation.start'
  | 'navigation.stop'
  | 'sos.confirm'
  | 'sos.sent'
  | 'sos.canceled'
  | 'vision.capture'
  | 'address.saved'
  | 'address.deleted'
  | 'address.list'
  | 'address.missing';

export type VisionCategory = 'medicine' | 'currency' | 'general';

export interface CommandToolData {
  destination?: string;
  label?: string;
  is_home?: boolean;
  matched_address?: boolean;
  video?: string;
  image?: string;
  followup_text?: string;
  followup_delay_ms?: number;
  result_text?: string;
  category?: VisionCategory;
  timeout_ms?: number;
  cancel_words?: string[];
  addresses?: Array<{ id: number; label: string; address: string }>;
  id?: number;
  fake?: boolean;
}

export interface CommandResult {
  text: string;
  action: VoiceAction;
  tool_called: string | null;
  tool_data: CommandToolData | null;
}

export type CommandTrigger = '' | 'shake' | 'sos_timeout' | 'sos_cancel';

/**
 * 发送一条语音指令。
 * trigger 用于抖动/超时等前端事件；coords 供天气/定位类工具使用。
 */
export async function sendCommand(
  text: string,
  trigger: CommandTrigger = '',
  coords?: { lat: number; lng: number } | null,
): Promise<CommandResult> {
  const { data } = await api.post('/conversation/command', {
    text,
    trigger,
    coords: coords || undefined,
  });
  return data.data as CommandResult;
}
