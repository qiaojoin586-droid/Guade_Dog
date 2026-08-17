import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../stores/useAppStore';
import api from '../services/api';
import { useVoiceRecorder } from '../hooks/useVoiceRecorder';
import { sendToLLM, speechToText, textToSpeech } from '../services/speechService';

const navItems = [
  { id: 'profile', label: '个人资料', icon: 'user' },
  { id: 'voice', label: '语音模块', icon: 'mic' },
  { id: 'navigation', label: '导航避障', icon: 'location' },
  { id: 'safety', label: '安全求救', icon: 'shield' },
  { id: 'life', label: '生活服务', icon: 'grid' },
  { id: 'policy', label: '政策咨询', icon: 'doc' },
];

const quickActions = [
  { label: '导航到家', intent: 'navigation_home' },
  { label: '今天天气', intent: 'weather' },
  { label: '紧急求救', intent: 'sos' },
];

// 快捷指令 → 发送给 LLM 的文本
const QUICK_ACTION_TEXT: Record<string, string> = {
  navigation_home: '导航回家',
  weather: '今天天气怎么样',
  sos: '紧急求救',
};

const featureCards = [
  {
    id: 'voice',
    title: '语音模块',
    desc: '语音交互引擎，支持唤醒、指令解析与多语言播报',
    color: 'bg-blue-50',
    iconColor: 'text-blue-600',
    iconBg: 'bg-blue-100',
  },
  {
    id: 'navigation',
    title: '导航避障',
    desc: '实时导航定位，视觉避障分析，安全通行判断',
    color: 'bg-orange-50',
    iconColor: 'text-orange-600',
    iconBg: 'bg-orange-100',
  },
  {
    id: 'safety',
    title: '安全求救',
    desc: '一键SOS报警，家属联动监控，药品识别与健康问答',
    color: 'bg-red-50',
    iconColor: 'text-red-600',
    iconBg: 'bg-red-100',
  },
  {
    id: 'life',
    title: '生活服务',
    desc: '文字提取翻译、天气播报、物体场景识别与语音提醒',
    color: 'bg-emerald-50',
    iconColor: 'text-emerald-600',
    iconBg: 'bg-emerald-100',
  },
  {
    id: 'policy',
    title: '政策咨询',
    desc: '政策查询解读，智能追问引导，图片文字提取朗读',
    color: 'bg-purple-50',
    iconColor: 'text-purple-600',
    iconBg: 'bg-purple-100',
  },
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

function CardIcon({ type }: { type: string }) {
  const cls = 'w-7 h-7';
  switch (type) {
    case 'voice':
      return (
        <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
        </svg>
      );
    case 'navigation':
      return (
        <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      );
    case 'safety':
      return (
        <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
      );
    case 'life':
      return (
        <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
        </svg>
      );
    case 'policy':
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

  // 语音闭环: 按住说话 → ASR → LLM → 工具调用(后端日志占位) → 回复展示/播报
  const { isRecording, error: recorderError, start: startRecording, stop: stopRecording } =
    useVoiceRecorder();
  const [userText, setUserText] = useState('');
  const [assistantText, setAssistantText] = useState('');
  const [processing, setProcessing] = useState(false);

  const handleTextInput = async (text: string) => {
    setUserText(text);
    setAssistantText('正在思考...');
    try {
      const result = await sendToLLM(text);
      setAssistantText(result.text || '好的');
      if (result.text) {
        textToSpeech(result.text).catch(() => {});
      }
    } catch (err: any) {
      setAssistantText(err.response?.data?.message || '请求失败，请重试');
    }
  };

  const processVoice = async (blob: Blob) => {
    setProcessing(true);
    try {
      const { text } = await speechToText(blob);
      if (!text) {
        setAssistantText('没听清，请再说一次');
        return;
      }
      await handleTextInput(text);
    } catch (err: any) {
      setAssistantText(err.response?.data?.message || '语音识别失败，请重试');
    } finally {
      setProcessing(false);
    }
  };

  const handleMicPress = () => {
    startRecording();
  };

  const handleMicRelease = async () => {
    const blob = await stopRecording();
    if (blob) await processVoice(blob);
  };

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
    logout(); // store 已清除 localStorage token
    navigate('/auth/login');
  };

  const handleQuickAction = (intent: string) => {
    handleTextInput(QUICK_ACTION_TEXT[intent] || intent);
  };

  const handleSOS = () => {
    // TODO: 触发 SOS 求救
    console.log('SOS triggered');
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

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-gray-100 flex flex-col fixed h-full z-20">
        {/* Logo */}
        <div className="px-5 py-5 flex items-center gap-3">
          <div className="w-9 h-9 bg-[#1a4a8a] rounded-full" />
          <span className="text-lg font-bold text-gray-900">导盲AI</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-2 space-y-1">
          <p className="px-3 py-2 text-xs text-gray-400 font-medium">功能模块</p>
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => {
                if (item.id === 'profile') {
                  setShowProfileModal(true);
                } else if (item.id === 'safety') {
                  navigate('/app/safety');
                } else {
                  setActiveNav(item.id);
                }
              }}
              className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl text-base font-medium transition-all ${
                activeNav === item.id
                  ? 'bg-[#1a4a8a] text-white shadow-md'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <NavIcon type={item.icon} />
              {item.label}
            </button>
          ))}
        </nav>

        {/* Bottom */}
        <div className="px-3 pb-4 space-y-2">
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
            紧急求救 SOS
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 ml-56">
        {/* Header */}
        <header className="bg-white border-b border-gray-100 px-8 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {getGreeting()}，{user?.name || '欢迎回来'}
            </h1>
            <p className="text-sm text-gray-400 mt-0.5">语音就绪，请说出您的需求</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-4 py-2 bg-gray-50 rounded-full text-sm text-gray-600">
              <span className="text-lg">☀️</span>
              <span>晴 28°C</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 bg-gray-50 rounded-full text-sm text-gray-600">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{formatTime()}</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 bg-gray-50 rounded-full text-sm">
              <span className="w-2.5 h-2.5 bg-green-500 rounded-full" />
              <span className="text-gray-600">在线</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 bg-gray-50 rounded-full text-sm text-gray-600">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.858 15.355-5.858 21.213 0" />
              </svg>
              <span>WiFi</span>
            </div>
          </div>
        </header>

        {/* Content */}
        <div className="p-8 space-y-8">
          {/* Voice Interaction Area */}
          <div className="bg-gradient-to-br from-[#0d2847] to-[#1a4a8a] rounded-3xl p-10 text-white text-center relative overflow-hidden">
            {/* Decorative */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2" />
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-white/5 rounded-full translate-y-1/2 -translate-x-1/2" />

            <div className="relative z-10">
              {/* Status */}
              <div className="inline-flex items-center gap-2 px-5 py-2 bg-white/10 backdrop-blur rounded-full text-sm mb-10">
                <span className={`w-2.5 h-2.5 rounded-full ${isRecording ? 'bg-red-400 animate-pulse' : processing ? 'bg-yellow-400 animate-pulse' : 'bg-green-400'}`} />
                {isRecording ? '正在录音...' : processing ? '正在识别...' : '待机中'}
              </div>

              {/* Mic Button: 按住说话,松手识别 */}
              <button
                onPointerDown={handleMicPress}
                onPointerUp={handleMicRelease}
                onPointerLeave={handleMicRelease}
                onPointerCancel={handleMicRelease}
                disabled={processing}
                className={`w-28 h-28 bg-white rounded-full flex items-center justify-center mx-auto mb-10 shadow-2xl shadow-blue-900/30 transition-transform hover:scale-105 ${
                  isRecording ? 'scale-105 bg-red-100' : ''
                } ${processing ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}`}
                aria-label={isRecording ? '停止录音' : '按住说话'}
              >
                <svg className="w-12 h-12 text-[#1a4a8a]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
              </button>

              {/* Quick Actions */}
              <div className="flex items-center justify-center gap-4 mb-8">
                {quickActions.map((action) => (
                  <button
                    key={action.intent}
                    onClick={() => handleQuickAction(action.intent)}
                    className="px-6 py-3 bg-white/10 backdrop-blur hover:bg-white/20 rounded-full text-base font-medium transition-all"
                  >
                    「{action.label}」
                  </button>
                ))}
              </div>

              {/* Hint */}
              <p className="text-xl text-blue-100/80">
                {isRecording ? '正在聆听，松开结束' : '按住麦克风说话，松手自动识别'}
              </p>

              {/* Transcript: 我说什么 + 助手回复 */}
              {(userText || assistantText || recorderError) && (
                <div className="mt-8 space-y-3 text-left max-w-md mx-auto w-full">
                  {userText && (
                    <div className="bg-white/10 backdrop-blur rounded-xl px-4 py-3 text-sm leading-relaxed">
                      <span className="text-blue-200 font-medium mr-2">我:</span>
                      <span className="text-white">{userText}</span>
                    </div>
                  )}
                  {assistantText && (
                    <div className="bg-white/15 backdrop-blur rounded-xl px-4 py-3 text-sm leading-relaxed">
                      <span className="text-blue-200 font-medium mr-2">助手:</span>
                      <span className="text-white">{assistantText}</span>
                    </div>
                  )}
                  {recorderError && (
                    <div className="bg-red-500/20 backdrop-blur rounded-xl px-4 py-3 text-sm text-red-100">
                      {recorderError}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Quick Function Cards */}
          <div>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-900">快捷功能</h2>
              <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">查看全部</button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {featureCards.map((card) => (
                <button
                  key={card.id}
                  onClick={() => {
                    if (card.id === 'safety') {
                      navigate('/app/safety');
                    } else {
                      setActiveNav(card.id);
                    }
                  }}
                  className={`${card.color} rounded-2xl p-6 text-left hover:shadow-lg transition-all group`}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className={`w-12 h-12 ${card.iconBg} rounded-full flex items-center justify-center ${card.iconColor}`}>
                      <CardIcon type={card.id} />
                    </div>
                    <svg className="w-5 h-5 text-gray-300 group-hover:text-gray-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                  <h3 className="text-lg font-bold text-gray-900 mb-1">{card.title}</h3>
                  <p className="text-sm text-gray-500 leading-relaxed">{card.desc}</p>
                </button>
              ))}
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
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">
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
