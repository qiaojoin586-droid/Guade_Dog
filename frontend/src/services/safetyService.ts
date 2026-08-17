/**
 * 安全服务 API。
 *
 * 本期能力：药品识别 / 健康问答 / 钞票识别（见《安全模块开发思路.md》）。
 * 图片通过 FormData 上传，不落盘、不留存。
 */

import api from './api';

// ===== 本期：药品识别 / 健康问答 / 钞票识别 =====

export async function recognizeMedicine(file: Blob) {
  const form = new FormData();
  form.append('image', file);
  const { data } = await api.post('/safety/medicine/recognize', form);
  return data.data;
}

export async function askHealth(question: string) {
  const { data } = await api.post('/safety/health/ask', { question });
  return data.data;
}

export async function recognizeCurrency(file: Blob) {
  const form = new FormData();
  form.append('image', file);
  const { data } = await api.post('/safety/currency/recognize', form);
  return data.data;
}

// ===== 下期预留：SOS / 家属 =====

export async function triggerSOS(params: { trigger_type: string; location?: { lat: number; lng: number } }) {
  // TODO: 实现 SOS 触发接口调用
  const { data } = await api.post('/safety/sos', params);
  return data.data;
}

export async function getFamilyList() {
  // TODO: 实现家属列表接口调用
  const { data } = await api.get('/family/list');
  return data.data;
}