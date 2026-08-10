/**
 * Axios 实例与拦截器配置。
 *
 * - baseURL: /api/v1
 * - 请求拦截器: 自动附带 Authorization: Bearer token
 * - 响应拦截器: 401 → 调 /auth/refresh 重放一次
 * - 错误码 → 可播报文案映射表
 */

import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器：自动附带 JWT
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器：401 自动刷新 token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        // TODO: 调用 /auth/refresh 刷新 token
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
          throw new Error('无 refresh token');
        }
        // const { data } = await axios.post('/api/v1/auth/refresh', { refresh_token: refreshToken });
        // localStorage.setItem('access_token', data.access_token);
        // originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        // return api(originalRequest);
      } catch {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/auth/login';
      }
    }

    return Promise.reject(error);
  },
);

/**
 * 错误码 → 播报文案映射。
 */
export function getVoiceTextForError(code: number): string {
  const map: Record<number, string> = {
    40001: '没听清，请再说一次',
    40101: '请先登录',
    40102: '登录已过期，请重新登录',
    40201: '未找到，请换个说法',
    40301: '已收到您的求助，请等待响应',
    50001: '系统繁忙，请稍后重试',
    50011: '网络超时，正在切换离线模式',
    50021: '服务暂不可用，请稍后再试',
  };
  return map[code] || '出现了一些问题，请稍后再试';
}

export default api;
