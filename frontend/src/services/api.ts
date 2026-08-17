/**
 * Axios 实例与拦截器配置。
 *
 * - baseURL: /api/v1
 * - 请求拦截器: 自动附带 Authorization: Bearer token
 * - 响应拦截器: 401 → 调 /auth/refresh 刷新后重放原请求；刷新失败 → 清 token 跳登录
 * - 错误码 → 可播报文案映射表
 */

import axios from 'axios';
import { clearTokens, getAccessToken, getRefreshToken, isPersistent, setTokens } from './tokenStorage';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 不带拦截器的裸实例：用于刷新请求本身，避免 401 时无限递归
const rawApi = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器：自动附带 JWT
api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器：401 自动刷新 token 并重放原请求
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = getRefreshToken();
        if (!refreshToken) {
          throw new Error('无 refresh token');
        }
        const { data } = await rawApi.post('/auth/refresh', { refresh_token: refreshToken });
        if (data.code !== 200 || !data.data?.access_token) {
          throw new Error('刷新 token 失败');
        }
        const { access_token, refresh_token } = data.data;
        setTokens(access_token, refresh_token || refreshToken, isPersistent());
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch {
        // 刷新失败（refresh token 过期/无效/网络错误）：清会话并回登录页
        clearTokens();
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
    40200: '识别失败，请换个角度重新拍摄',
    40300: '您描述的情况比较紧急，请立即拨打120急救电话，或请身边人协助就医',
    50020: '图像识别服务暂不可用，请稍后再试',
    40201: '未找到，请换个说法',
    40301: '已收到您的求助，请等待响应',
    50001: '系统繁忙，请稍后重试',
    50011: '网络超时，正在切换离线模式',
    50021: '服务暂不可用，请稍后再试',
  };
  return map[code] || '出现了一些问题，请稍后再试';
}

export default api;
