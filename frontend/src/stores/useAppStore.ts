/**
 * 全局应用状态管理。
 *
 * 管理用户信息、全局配置等。
 * 支持刷新后从 localStorage 恢复登录状态。
 */

import { create } from 'zustand';
import api from '../services/api';
import { clearTokens, getAccessToken } from '../services/tokenStorage';

interface UserInfo {
  id: string;
  name: string;
  role: 'blind' | 'family' | 'admin';
  phone?: string;
  email?: string;
  avatar_url?: string;
}

interface AppState {
  user: UserInfo | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  setUser: (user: UserInfo | null) => void;
  setLoading: (loading: boolean) => void;
  logout: () => void;
  /** 从 localStorage token 恢复会话（刷新页面时调用一次）。 */
  restoreSession: () => Promise<void>;
}

export const useAppStore = create<AppState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  setUser: (user) => set({ user, isAuthenticated: !!user }),
  setLoading: (isLoading) => set({ isLoading }),
  logout: () => {
    clearTokens();
    set({ user: null, isAuthenticated: false });
  },

  restoreSession: async () => {
    const token = getAccessToken();
    if (!token) {
      set({ isLoading: false });
      return;
    }
    try {
      const { data } = await api.get('/users/me');
      if (data.code === 200) {
        const p = data.data;
        set({
          user: {
            id: String(p.user_id),
            name: p.name,
            role: p.role,
            phone: p.phone || undefined,
            email: p.email || undefined,
            avatar_url: p.avatar_url || undefined,
          },
          isAuthenticated: true,
          isLoading: false,
        });
      } else {
        // token 无效，清除
        clearTokens();
        set({ user: null, isAuthenticated: false, isLoading: false });
      }
    } catch (err: any) {
      if (err.response?.status === 401) {
        // token 过期且刷新失败（拦截器已尝试刷新），清空会话
        clearTokens();
        set({ user: null, isAuthenticated: false, isLoading: false });
      } else {
        // 网络/服务端错误：保留 token，避免误登出；进入未认证状态由用户重试
        set({ user: null, isAuthenticated: false, isLoading: false });
      }
    }
  },
}));
