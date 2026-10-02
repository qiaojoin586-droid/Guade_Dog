import { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAppStore } from './stores/useAppStore';

import MainPage from './pages/MainPage';
import NavigationPage from './pages/NavigationPage';
import SafetyPage from './pages/SafetyPage';
import SettingsPage from './pages/SettingsPage';
import AddressPage from './pages/AddressPage';
import FamilyDashboard from './pages/family/Dashboard';
import LoginPage from './pages/auth/LoginPage';
import VoiceDock from './components/VoiceDock';
import { VoiceControlProvider } from './voice/VoiceControlProvider';

// 认证守卫：未登录时重定向到登录页
function AuthGuard({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAppStore((s) => s.isAuthenticated);
  if (!isAuthenticated) {
    return <Navigate to="/auth/login" replace />;
  }
  return <>{children}</>;
}

function App() {
  const isAuthenticated = useAppStore((s) => s.isAuthenticated);
  const isLoading = useAppStore((s) => s.isLoading);
  const restoreSession = useAppStore((s) => s.restoreSession);

  // 启动时从 localStorage 恢复登录状态（仅执行一次）
  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  // 会话恢复中，显示加载画面
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-200 border-t-[#1a4a8a] rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-500 text-sm">正在加载...</p>
        </div>
      </div>
    );
  }

  return (
    <VoiceControlProvider>
      <Routes>
      {/* 根路由：根据登录状态重定向 */}
      <Route
        path="/"
        element={
          isAuthenticated ? (
            <Navigate to="/app" replace />
          ) : (
            <Navigate to="/auth/login" replace />
          )
        }
      />

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

      {/* 认证路由：手机号验证码登录，未注册手机号自动建号，注册页不再使用 */}
      <Route path="/auth/login" element={<LoginPage />} />
      <Route path="/auth/register" element={<Navigate to="/auth/login" replace />} />
      </Routes>

      {/* 登录后才出现的常驻语音控制条（各页面自行预留底部空间） */}
      {isAuthenticated && <VoiceDock />}
    </VoiceControlProvider>
  );
}

export default App;
