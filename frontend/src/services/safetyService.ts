/**
 * 安全服务 API（占位）。
 */

import api from './api';

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
