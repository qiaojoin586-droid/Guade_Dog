/**
 * 路由配置。
 *
 * /app     — 视障端主界面
 * /family  — 家属端
 * /auth    — 认证（登录/注册）
 */

import { Route, Navigate } from 'react-router-dom';
import MainPage from '../pages/MainPage';
import NavigationPage from '../pages/NavigationPage';
import SafetyPage from '../pages/SafetyPage';
import SettingsPage from '../pages/SettingsPage';
import AddressPage from '../pages/AddressPage';
import FamilyDashboard from '../pages/family/Dashboard';
import LoginPage from '../pages/auth/LoginPage';
import { useAppStore } from '../stores/useAppStore';

// 认证守卫：未登录时重定向到登录页
function AuthGuard({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAppStore((s) => s.isAuthenticated);
  if (!isAuthenticated) {
    return <Navigate to="/auth/login" replace />;
  }
  return <>{children}</>;
}

export default function AppRoutes() {
  return (
    <>
      {/* 视障端路由 */}
      <Route
        path="/app"
        element={
          <AuthGuard>
            <MainPage />
          </AuthGuard>
        }
      />
      <Route
        path="/app/navigation"
        element={
          <AuthGuard>
            <NavigationPage />
          </AuthGuard>
        }
      />
      <Route
        path="/app/safety"
        element={
          <AuthGuard>
            <SafetyPage />
          </AuthGuard>
        }
      />
      <Route
        path="/app/addresses"
        element={
          <AuthGuard>
            <AddressPage />
          </AuthGuard>
        }
      />
      <Route
        path="/app/settings"
        element={
          <AuthGuard>
            <SettingsPage />
          </AuthGuard>
        }
      />

      {/* 家属端路由 */}
      <Route
        path="/family"
        element={
          <AuthGuard>
            <FamilyDashboard />
          </AuthGuard>
        }
      />

      {/* 认证路由：验证码登录后自动建号，注册页不再使用 */}
      <Route path="/auth/login" element={<LoginPage />} />
      <Route path="/auth/register" element={<Navigate to="/auth/login" replace />} />
    </>
  );
}
