/**
 * JWT Token 存储工具。
 *
 * 「记住我」勾选 → localStorage（关浏览器后仍保持登录）；
 * 未勾选 → sessionStorage（刷新页面保持，关闭浏览器/标签页即失效）。
 * 所有读取/清除操作同时覆盖两个存储位置，避免残留。
 */

const ACCESS_KEY = 'access_token';
const REFRESH_KEY = 'refresh_token';

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY) || sessionStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY) || sessionStorage.getItem(REFRESH_KEY);
}

/** 判断 token 当前存在的位置（localStorage 表示勾选过「记住我」）。 */
export function isPersistent(): boolean {
  return localStorage.getItem(ACCESS_KEY) !== null;
}

export function setTokens(accessToken: string, refreshToken: string, persistent: boolean): void {
  const store = persistent ? localStorage : sessionStorage;
  store.setItem(ACCESS_KEY, accessToken);
  store.setItem(REFRESH_KEY, refreshToken);
  // 刷新后生成的新 token 覆盖到原有存储位置
  if (!persistent) {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  }
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
}
