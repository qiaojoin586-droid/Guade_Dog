import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../stores/useAppStore';
import api from '../services/api';
import { useVoiceControl } from '../voice/VoiceControlProvider';

const navItems = [
  { id: 'profile', label: '个人资料', icon: 'user' },
  { id: 'voice', label: '语音模块', icon: 'mic' },
  { id: 'navigation', label: '导航避障', icon: 'location' },
  { id: 'addresses', label: '常用地址', icon: 'address' },
  { id: 'safety', label: '安全求救', icon: 'shield' },
  { id: 'life', label: '生活服务', icon: 'grid' },
  { id: 'policy', label: '政策咨询', icon: 'doc' },
];

// 三个便捷问题（临时保留，等价于用户说出这句话）
const quickActions = [
  { label: '我要回家', text: '我要回家' },
  { label: '识别药品', text: '帮我识别这个药品' },
  { label: '紧急求救', text: '我遇到危险了' },
];

function NavIcon({ type }: { type: string }) {
  const cls = 'w-5 h-5';
  switch (type) {
    case 'user':
      return (
        <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
      );
    case 'mic':
      return (
        <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
        </svg>
      );
    case 'location':
      return (
        <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      );
    case 'shield':
      return (
        <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
      );
    case 'grid':
      return (
        <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
        </svg>
      );
    case 'address':
      return (
        <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
        </svg>
      );
    case 'doc':
      return (
        <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      );
    default:
      return null;
  }
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 6) return '凌晨好';
  if (hour < 12) return '上午好';
  if (hour < 14) return '中午好';
  if (hour < 18) return '下午好';
  return '晚上好';
}

function formatTime(): string {
  const now = new Date();
  return now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false });
}

export default function MainPage() {
  const navigate = useNavigate();
  const { user, logout, setUser } = useAppStore();
  const [activeNav, setActiveNav] = useState('voice');
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // 全程语音：识别、指令分发、播报统一交给全局语音中枢
  const {
    mode,
    listening,
    busy: processing,
    transcript: userText,
    reply: assistantText,
    error: recorderError,
    startListening,
    stopListening,
    runCommand,
    simulateShake,
  } = useVoiceControl();

  const micHint = mode === 'server'
    ? listening
      ? '正在录音，说完再点一下'
      : '点一下开始录音'
    : listening
      ? '请说话，说完自动回应'
      : '点一下麦克风开始';

  // 临时测试输入框（联调用，后续删除）
  const [testText, setTestText] = useState('');

  // 加载用户完整资料
  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const { data } = await api.get('/users/me');
        if (data.code === 200) {
          const p = data.data;
          setUser({
            id: String(p.user_id),
            name: p.name,
            role: p.role,
            phone: p.phone || undefined,
            email: p.email || undefined,
            avatar_url: p.avatar_url || undefined,
          });
        }
      } catch {
        // token 过期等由拦截器处理
      }
    };
    fetchProfile();
  }, [setUser]);

  const handleLogout = () => {
    stopListening();
    logout(); // store 已清除 localStorage token
    navigate('/auth/login');
  };

  const handleQuickAction = (text: string) => {
    void runCommand(text);
  };

  // 临时测试：输入框里打字，等价于说这句话
  const handleTestSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const text = testText.trim();
    if (!text) return;
    setTestText('');
    void runCommand(text);
  };

  // 剧烈的手机抖动 = 遭遇危险（临时用按钮模拟）
  const handleSOS = () => {
    simulateShake();
  };

  const handleProfileUpdated = useCallback(
    (profile: { name: string; phone?: string; email?: string; avatar_url?: string }) => {
      setUser({
        ...user!,
        name: profile.name,
        phone: profile.phone || undefined,
        email: profile.email || undefined,
        avatar_url: profile.avatar_url || undefined,
      });
      setShowProfileModal(false);
    },
    [user, setUser],
  );

  const handleNavClick = (id: string) => {
    setDrawerOpen(false);
    if (id === 'profile') {
      setShowProfileModal(true);
    } else if (id === 'safety') {
      navigate('/app/safety');
    } else if (id === 'addresses') {
      navigate('/app/addresses');
    } else {
      setActiveNav(id);
    }
  };

  const navButtonList = navItems.map((item) => (
    <button
      key={item.id}
      onClick={() => handleNavClick(item.id)}
      className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl text-base font-medium transition-all ${
        activeNav === item.id ? 'bg-[#1a4a8a] text-white shadow-md' : 'text-gray-600 hover:bg-gray-50'
      }`}
    >
      <NavIcon type={item.icon} />
      {item.label}
    </button>
  ));

  const actionButtonList = (
    <>
      <button
        onClick={handleLogout}
        className="w-full flex items-center gap-3 px-3 py-3 rounded-xl text-base text-gray-500 hover:bg-gray-50 transition-all"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
        </svg>
        退出登录
      </button>
      <button
        onClick={handleSOS}
        className="w-full flex items-center justify-center gap-2 px-3 py-3 rounded-xl text-base font-semibold bg-red-500 hover:bg-red-600 text-white transition-all shadow-md"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        模拟剧烈抖动求救
      </button>
    </>
  );

  return (
    <div className="min-h-[100dvh] bg-gray-50">
      {/* 桌面侧边栏（lg 及以上显示） */}
      <aside className="hidden lg:flex w-56 bg-white border-r border-gray-100 flex-col fixed inset-y-0 left-0 z-20">
        <div className="px-5 py-5 flex items-center gap-3">
          <div className="w-9 h-9 bg-[#1a4a8a] rounded-full" />
          <span className="text-lg font-bold text-gray-900">导盲AI</span>
        </div>

        <nav className="flex-1 px-3 py-2 space-y-1">
          <p className="px-3 py-2 text-xs text-gray-400 font-medium">功能模块</p>
          {navButtonList}
        </nav>

        <div className="px-3 pb-4 space-y-2">{actionButtonList}</div>
      </aside>

      {/* 移动端抽屉菜单 */}
      {drawerOpen && (
        <div className="lg:hidden fixed inset-0 z-[55]" role="dialog" aria-modal="true" aria-label="功能菜单">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setDrawerOpen(false)}
            aria-hidden="true"
          />
          <div className="absolute inset-y-0 left-0 w-72 max-w-[85vw] bg-white shadow-2xl flex flex-col">
            <div className="px-5 py-4 flex items-center justify-between border-b border-gray-100">
              <span className="text-lg font-bold text-gray-900">功能模块</span>
              <button
                type="button"
                onClick={() => setDrawerOpen(false)}
                aria-label="关闭菜单"
                className="px-3 py-2 rounded-lg bg-gray-100 text-gray-700 text-base font-semibold
                           focus:outline-none focus:ring-4 focus:ring-gray-300"
              >
                关闭
              </button>
            </div>
            <nav className="flex-1 overflow-y-auto px-3 py-3 space-y-1">{navButtonList}</nav>
            <div className="px-3 pb-4 space-y-2 border-t border-gray-100 pt-3">{actionButtonList}</div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="lg:ml-56">
        {/* Header */}
        <header className="hidden lg:flex flex-wrap items-center justify-between gap-3 bg-white border-b border-gray-100 px-4 sm:px-6 lg:px-8 py-3 sm:py-4">
          <div className="min-w-0">
            <h1 className="text-xl sm:text-2xl font-bold text-gray-900 truncate">
              {getGreeting()}，{user?.name || '欢迎回来'}
            </h1>
            <p className="text-sm text-gray-400 mt-0.5">语音就绪，请说出您的需求</p>
          </div>
          <div className="hidden md:flex items-center gap-3 lg:gap-4">
            <div className="flex items-center gap-2 px-3 lg:px-4 py-2 bg-gray-50 rounded-full text-sm text-gray-600">
              <span className="text-lg">☀️</span>
              <span>晴 28°C</span>
            </div>
            <div className="flex items-center gap-2 px-3 lg:px-4 py-2 bg-gray-50 rounded-full text-sm text-gray-600">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{formatTime()}</span>
            </div>
            <div className="flex items-center gap-2 px-3 lg:px-4 py-2 bg-gray-50 rounded-full text-sm">
              <span className="w-2.5 h-2.5 bg-green-500 rounded-full" />
              <span className="text-gray-600">在线</span>
            </div>
            <div className="hidden lg:flex items-center gap-2 px-4 py-2 bg-gray-50 rounded-full text-sm text-gray-600">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.858 15.355-5.858 21.213 0" />
              </svg>
              <span>WiFi</span>
            </div>
          </div>
        </header>

        {/* Content：移动端全屏铺满（竖屏长方形），桌面端内嵌卡片 */}
        <div className="p-0 lg:p-8">
          <div className="bg-gradient-to-br from-[#0d2847] to-[#1a4a8a] rounded-none lg:rounded-3xl p-4 sm:p-6 lg:p-8
                          text-white relative overflow-hidden flex flex-col
                          h-[100dvh] lg:h-auto">
            {/* Decorative */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2" />
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-white/5 rounded-full translate-y-1/2 -translate-x-1/2" />

            {/* 移动端顶部：与侧边栏顶对齐的标题栏（同底色，保证全屏铺满） */}
            <div className="lg:hidden relative z-10 flex items-center justify-between gap-3 mb-2">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-white/20 rounded-full" />
                <div>
                  <span className="text-base font-bold">导盲AI</span>
                  <span className="ml-2 text-xs text-blue-100/70">语音就绪</span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setDrawerOpen(true)}
                aria-label="打开功能菜单"
                aria-expanded={drawerOpen}
                className="px-4 py-2 rounded-xl bg-white/15 hover:bg-white/25 text-white text-base font-semibold
                           focus:outline-none focus:ring-4 focus:ring-white/40"
              >
                菜单
              </button>
            </div>

            <div className="relative z-10 flex-1 min-h-0 overflow-y-auto lg:overflow-visible flex flex-col pb-24 lg:pb-0">
              <div className="flex-1 flex flex-col justify-center lg:flex-row lg:items-center gap-3 sm:gap-6">
              {/* 中：麦克风（主导，移动端排第一） */}
              <div className="order-first lg:order-none flex-1 flex flex-col items-center justify-center py-1 lg:py-2">
                <button
                  type="button"
                  onClick={listening ? stopListening : startListening}
                  className={`relative w-36 h-36 sm:w-44 sm:h-44 lg:w-48 lg:h-48 rounded-full flex items-center justify-center shadow-2xl shadow-blue-900/40
                    transition-transform hover:scale-105 cursor-pointer focus:outline-none focus:ring-4 lg:focus:ring-8
                    ${listening ? 'bg-red-100 scale-105 focus:ring-red-300/40' : 'bg-white focus:ring-white/40'}`}
                  aria-label={
                    listening
                      ? mode === 'server'
                        ? '结束录音并识别'
                        : '停止语音控制'
                      : mode === 'server'
                        ? '开始录音'
                        : '开始语音控制'
                  }
                  aria-pressed={listening}
                >
                  {listening && (
                    <span className="absolute inset-0 rounded-full bg-red-400/40 animate-ping" aria-hidden="true" />
                  )}
                  <svg
                    className="w-16 h-16 sm:w-20 sm:h-20 lg:w-24 lg:h-24 text-[#1a4a8a]"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                    />
                  </svg>
                </button>

                <div className="mt-3 lg:mt-5 inline-flex items-center gap-2 px-4 lg:px-5 py-1.5 lg:py-2 bg-white/10 rounded-full text-sm sm:text-base">
                  <span
                    className={`w-2.5 h-2.5 rounded-full ${
                      listening ? 'bg-red-400 animate-pulse' : processing ? 'bg-yellow-400 animate-pulse' : 'bg-green-400'
                    }`}
                  />
                  {listening ? (processing ? '正在处理…' : '正在聆听…') : '语音待机'}
                </div>
                <p className="mt-2 lg:mt-3 text-lg sm:text-xl lg:text-2xl font-semibold text-center" aria-live="polite">
                  {micHint}
                </p>
                <p className="mt-1 text-xs sm:text-sm text-blue-100/70 text-center">
                  {mode === 'server'
                    ? '录音识别模式：点一下开始，说完再点一下'
                    : '例如：我要回家、帮我识别这个药品'}
                </p>
              </div>

              {/* 左：我说的（缩小，移动端排第二） */}
              <div className="order-2 lg:order-first w-full lg:w-60 shrink-0 rounded-2xl bg-white/10 p-3 lg:p-4 min-h-[64px] lg:h-[132px] overflow-y-auto">
                <p className="text-sm font-semibold text-blue-200 mb-1">我 说</p>
                <p className="text-base leading-relaxed break-words">
                  {userText || <span className="text-blue-100/50">说出您的需求</span>}
                </p>
              </div>

              {/* 右：助手回复（缩小，移动端排第三） */}
              <div className="order-3 w-full lg:w-60 shrink-0 rounded-2xl bg-white/15 p-3 lg:p-4 min-h-[64px] lg:h-[132px] overflow-y-auto">
                <p className="text-sm font-semibold text-blue-200 mb-1">助 手</p>
                <p className="text-base leading-relaxed break-words" aria-live="assertive">
                  {assistantText || <span className="text-blue-100/50">回复会显示在这里</span>}
                </p>
                {recorderError && (
                  <p className="mt-2 text-sm text-red-100" role="alert">
                    {recorderError}
                  </p>
                )}
              </div>
            </div>

            {/* 三个便捷问题（临时保留） */}
            <div className="relative z-10 mt-3 lg:mt-7 flex flex-wrap items-center justify-center gap-2 sm:gap-4">
              {quickActions.map((action) => (
                <button
                  key={action.label}
                  type="button"
                  onClick={() => handleQuickAction(action.text)}
                  className="px-4 sm:px-6 py-2 sm:py-3 bg-white/10 hover:bg-white/20 rounded-full text-base sm:text-lg font-medium transition-all
                             focus:outline-none focus:ring-4 focus:ring-white/40"
                >
                  「{action.label}」
                </button>
              ))}
            </div>

            {/* 临时测试输入框：打字等价于说话，联调完删除 */}
            <form onSubmit={handleTestSubmit} className="relative z-10 mt-3 lg:mt-6 mx-auto w-full max-w-2xl">
              <label htmlFor="test-input" className="hidden sm:block text-sm text-blue-100/70 mb-2">
                临时测试输入框（输入指令后点发送，等价于说这句话）
              </label>
              <div className="flex flex-col sm:flex-row gap-2">
                <input
                  id="test-input"
                  value={testText}
                  onChange={(e) => setTestText(e.target.value)}
                  placeholder="临时测试：输入指令，例如 我要回家"
                  className="flex-1 min-w-0 px-3 sm:px-4 py-2.5 sm:py-3 rounded-xl bg-white text-[#0a1628] text-base sm:text-lg placeholder-gray-400
                             focus:outline-none focus:ring-4 focus:ring-white/50"
                />
                <button
                  type="submit"
                  disabled={processing || !testText.trim()}
                  className="px-6 py-2.5 sm:py-3 rounded-xl bg-white text-[#1a4a8a] text-base sm:text-lg font-bold
                             disabled:opacity-50 disabled:cursor-not-allowed
                             focus:outline-none focus:ring-4 focus:ring-white/50"
                >
                  发送
                </button>
              </div>
            </form>
            </div>
          </div>
        </div>
      </main>

      {/* Profile Edit Modal */}
      {showProfileModal && (
        <ProfileModal
          user={user!}
          onClose={() => setShowProfileModal(false)}
          onUpdated={handleProfileUpdated}
        />
      )}
    </div>
  );
}

// ===== 个人资料编辑弹窗 =====

interface ProfileModalProps {
  user: { id: string; name: string; role: string; phone?: string; email?: string; avatar_url?: string };
  onClose: () => void;
  onUpdated: (profile: { name: string; phone?: string; email?: string; avatar_url?: string }) => void;
}

function ProfileModal({ user, onClose, onUpdated }: ProfileModalProps) {
  const [name, setName] = useState(user.name || '');
  const [phone, setPhone] = useState(user.phone || '');
  const [email, setEmail] = useState(user.email || '');
  const [avatarUrl, setAvatarUrl] = useState(user.avatar_url || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // 表单验证
  const validate = (): string | null => {
    if (!name.trim()) return '姓名不能为空';
    if (phone && !/^1[3-9]\d{9}$/.test(phone)) return '手机号格式不正确';
    if (email && !/^[\w.-]+@[\w.-]+\.\w+$/.test(email)) return '邮箱格式不正确';
    return null;
  };

  const handleSave = async () => {
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setError('');
    setSaving(true);

    try {
      const payload: Record<string, string> = { name: name.trim() };
      if (phone.trim()) payload.phone = phone.trim();
      if (email.trim()) payload.email = email.trim();
      if (avatarUrl.trim()) payload.avatar_url = avatarUrl.trim();

      const { data } = await api.put('/users/me', payload);
      if (data.code === 200) {
        setSuccess('资料更新成功');
        setTimeout(() => {
          onUpdated({
            name: name.trim(),
            phone: phone.trim() || undefined,
            email: email.trim() || undefined,
            avatar_url: avatarUrl.trim() || undefined,
          });
        }, 600);
      } else {
        setError(data.message || '更新失败');
      }
    } catch (err: any) {
      setError(err.response?.data?.message || '网络错误，请稍后重试');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="bg-gradient-to-r from-[#0d2847] to-[#1a4a8a] px-6 py-5 flex items-center justify-between">
          <h2 className="text-xl font-bold text-white">个人资料</h2>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors"
            aria-label="关闭"
          >
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Avatar Preview */}
        <div className="flex justify-center -mt-6">
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-[#1a4a8a] to-[#3b82f6] flex items-center justify-center text-white text-2xl font-bold border-4 border-white shadow-lg">
            {avatarUrl ? (
              <img src={avatarUrl} alt="" className="w-full h-full rounded-full object-cover" />
            ) : (
              (name?.[0] || '?')
            )}
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-6 space-y-5">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm">{error}</div>
          )}
          {success && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-xl text-green-600 text-sm">{success}</div>
          )}

          {/* 姓名 */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1.5">姓名</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-base focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              placeholder="请输入姓名"
            />
          </div>

          {/* 手机号 */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1.5">手机号</label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-base focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              placeholder="请输入手机号"
            />
          </div>

          {/* 邮箱 */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1.5">邮箱</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-base focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              placeholder="请输入邮箱地址"
            />
          </div>

          {/* 头像URL */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1.5">头像链接</label>
            <input
              type="url"
              value={avatarUrl}
              onChange={(e) => setAvatarUrl(e.target.value)}
              className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-base focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              placeholder="请输入头像图片链接（可选）"
            />
          </div>

          {/* 角色（只读） */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1.5">角色</label>
            <div className="px-4 py-3 bg-gray-100 border border-gray-200 rounded-xl text-gray-500 text-base">
              {user.role === 'blind' ? '视障用户' : user.role === 'family' ? '家属' : '管理员'}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 pb-6 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-3 border border-gray-200 text-gray-600 rounded-xl text-base font-medium hover:bg-gray-50 transition-all"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex-1 py-3 bg-[#1a4a8a] hover:bg-[#153d75] text-white rounded-xl text-base font-semibold transition-all disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}
