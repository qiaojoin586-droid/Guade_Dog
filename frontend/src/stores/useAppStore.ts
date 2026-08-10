/**
 * 全局应用状态管理。
 *
 * 管理用户信息、全局配置等。
 * 支持刷新后从 localStorage 恢复登录状态。
 */

import { create } from 'zustand';
import api from '../services/api';

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
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({ user: null, isAuthenticated: false });
  },

  restoreSession: async () => {
    const token = localStorage.getItem('access_token');
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
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        set({ user: null, isAuthenticated: false, isLoading: false });
      }
    } catch {
      // token 过期或网络错误，清除
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },
}));
