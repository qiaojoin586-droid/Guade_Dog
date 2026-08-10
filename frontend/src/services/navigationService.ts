/**
 * 导航服务 API（占位）。
 */

import api from './api';

export async function planRoute(origin: string, destination: string) {
  // TODO: 实现路线规划接口调用
  const { data } = await api.post('/navigation/route', { origin, destination });
  return data.data;
}

export async function getCurrentLocation() {
  // TODO: 实现位置获取接口调用
  const { data } = await api.get('/navigation/location');
  return data.data;
}

export async function searchNearbyPOI(query: string, location?: { lat: number; lng: number }) {
  // TODO: 实现 POI 查询接口调用
  const { data } = await api.get('/navigation/poi', { params: { query, ...location } });
  return data.data;
}
