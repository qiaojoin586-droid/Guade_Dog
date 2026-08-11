/**
 * 语音服务: ASR 识别 / LLM 对话 / TTS 播报。
 *
 * 后端路由: /api/v1/speech/asr, /api/v1/speech/tts, /api/v1/conversation/chat
 * (api 实例 baseURL 已带 /api/v1,自动附带 JWT)
 */

import api from './api';

export interface AsrResult {
  text: string;
  confidence: number;
}

export interface ChatResult {
  text: string;
  tool_called: string | null;
}

/** 上传录音,返回识别文本 */
export async function speechToText(audioBlob: Blob): Promise<AsrResult> {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'voice.webm');
  // 必须声明 multipart: api 实例默认 Content-Type 是 application/json,
  // 不覆盖的话 axios 会把 FormData 序列化成 JSON,服务端解析 multipart 时 422
  const { data } = await api.post('/speech/asr', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data.data;
}

/** 识别文本进 LLM,返回回复(工具调用为后端日志占位) */
export async function sendToLLM(text: string): Promise<ChatResult> {
  const { data } = await api.post('/conversation/chat', { text });
  return data.data;
}

/** 文本合成语音并播放(自动播放被浏览器拦截时静默忽略) */
export async function textToSpeech(text: string): Promise<void> {
  const res = await api.post('/speech/tts', { text }, { responseType: 'blob' });
  const url = URL.createObjectURL(res.data as Blob);
  const audio = new Audio(url);
  audio.onended = () => URL.revokeObjectURL(url);
  try {
    await audio.play();
  } catch {
    // 自动播放限制: 静默失败,用户可再次触发
  }
}
