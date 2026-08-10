/**
 * 感知服务 API（占位）。
 */

import api from './api';

export async function getWeather(city: string) {
  // TODO: 实现天气查询接口调用
  const { data } = await api.get('/perception/weather', { params: { city } });
  return data.data;
}

export async function recognizeOCR(imageBlob: Blob) {
  // TODO: 实现 OCR 接口调用
  const formData = new FormData();
  formData.append('image', imageBlob);
  const { data } = await api.post('/perception/ocr', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data.data;
}

export async function recognizeObject(imageBlob: Blob) {
  // TODO: 实现物体识别接口调用
  const formData = new FormData();
  formData.append('image', imageBlob);
  const { data } = await api.post('/perception/object', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data.data;
}
