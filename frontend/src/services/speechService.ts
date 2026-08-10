/**
 * 语音服务 API（占位）。
 */

import api from './api';

export async function speechToText(audioBlob: Blob): Promise<{ text: string; confidence: number }> {
  // TODO: 实现 ASR 接口调用
  const formData = new FormData();
  formData.append('audio', audioBlob);
  const { data } = await api.post('/speech/asr', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data.data;
}

export async function textToSpeech(text: string): Promise<{ audio_url: string }> {
  // TODO: 实现 TTS 接口调用
  const { data } = await api.post('/speech/tts', { text });
  return data.data;
}
