/**
 * 登录页：手机号 + 验证码（未注册手机号自动建号）。
 *
 * 无障碍设计：
 * - 手机号、验证码都可以直接用嘴说，不需要看屏幕；
 * - 错误和关键提示都会语音播报；
 * - 验证码不发送真实短信，只打印在后端控制台（演示阶段）。
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useSpeechInput } from '../../hooks/useSpeechInput';
import api from '../../services/api';
import { setTokens } from '../../services/tokenStorage';
import { speak } from '../../services/tts';
import { useAppStore } from '../../stores/useAppStore';
import { extractDigits } from '../../utils/voiceText';
import { useVoiceControl } from '../../voice/VoiceControlProvider';

const PHONE_RE = /^1[3-9]\d{9}$/;

export default function LoginPage() {
  const navigate = useNavigate();
  const setUser = useAppStore((s) => s.setUser);
  const { startListening } = useVoiceControl();

  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [countdown, setCountdown] = useState(0);
  const [sending, setSending] = useState(false);
  const [logging, setLogging] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const countdownRef = useRef<number | null>(null);
  const spokenRef = useRef(false);
  const submittingRef = useRef(false);

  // ── 页面进入时先说一遍怎么用（浏览器可能拦自动播放，失败静默） ──
  useEffect(() => {
    if (!spokenRef.current) {
      spokenRef.current = true;
      void speak('请说出您的手机号，我会自动发送验证码，然后请说出六位验证码。');
    }
    return () => {
      if (countdownRef.current !== null) window.clearInterval(countdownRef.current);
    };
  }, []);

  const startCountdown = useCallback((seconds: number) => {
    setCountdown(seconds);
    if (countdownRef.current !== null) window.clearInterval(countdownRef.current);
    countdownRef.current = window.setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          if (countdownRef.current !== null) window.clearInterval(countdownRef.current);
          countdownRef.current = null;
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }, []);

  /** 获取验证码（语音说出手机号后自动调用）。 */
  const requestCode = useCallback(
    async (targetPhone: string): Promise<boolean> => {
      setError('');
      setNotice('');
      if (!PHONE_RE.test(targetPhone)) {
        const message = '请先输入或说出十一位手机号。';
        setError(message);
        void speak(message);
        return false;
      }

      setSending(true);
      try {
        const { data } = await api.post('/auth/sms/send', { phone: targetPhone });
        if (data.code === 200) {
          startCountdown(data.data?.resend_after ?? 60);
          const message = '验证码已生成。请查看后端控制台里的六位数字，然后直接说出来。';
          setNotice(message);
          void speak(message);
          return true;
        }
        const message = data.message || '获取验证码失败';
        setError(message);
        void speak(message);
        return false;
      } catch (err: unknown) {
        const message =
          (err as { response?: { data?: { message?: string } } })?.response?.data?.message ??
          '网络异常，请稍后重试';
        setError(message);
        void speak(message);
        return false;
      } finally {
        setSending(false);
      }
    },
    [startCountdown],
  );

  /** 登录（语音说出验证码后自动调用）。 */
  const doLogin = useCallback(
    async (targetPhone: string, targetCode: string) => {
      if (submittingRef.current) return;
      setError('');
      setNotice('');

      if (!PHONE_RE.test(targetPhone)) {
        const message = '手机号格式不正确，请重新输入或说出手机号。';
        setError(message);
        void speak(message);
        return;
      }
      if (targetCode.length < 4) {
        const message = '请先说出手里的验证码。';
        setError(message);
        void speak(message);
        return;
      }

      submittingRef.current = true;
      setLogging(true);
      try {
        const { data } = await api.post('/auth/login/code', {
          phone: targetPhone,
          code: targetCode,
        });
        if (data.code === 200) {
          const {
            access_token,
            refresh_token,
            user_id,
            name,
            role,
            phone: userPhone,
            email,
            avatar_url,
          } = data.data;
          setTokens(access_token, refresh_token, true);
          setUser({
            id: String(user_id),
            name,
            role: role as 'blind' | 'family' | 'admin',
            phone: userPhone || undefined,
            email: email || undefined,
            avatar_url: avatar_url || undefined,
          });
          navigate('/app');
          // 登录后直接进入聆听状态，盲人用户不用再找麦克风按钮
          void speak('登录成功。请说出您的需求。').then(() => startListening());
        } else {
          const message = data.message || '登录失败';
          setError(message);
          void speak(message);
        }
      } catch (err: unknown) {
        const message =
          (err as { response?: { data?: { message?: string } } })?.response?.data?.message ??
          '网络错误，请稍后重试';
        setError(message);
        void speak(message);
      } finally {
        submittingRef.current = false;
        setLogging(false);
      }
    },
    [navigate, setUser, startListening],
  );

  // ── 语音输入手机号：识别到 11 位后自动发验证码 ──
  const phoneSpeech = useSpeechInput((text) => {
    const digits = extractDigits(text);
    if (digits.length === 11 && PHONE_RE.test(digits)) {
      setPhone(digits);
      setError('');
      void requestCode(digits);
      return;
    }
    const message =
      digits.length > 0
        ? `我只听到 ${digits.length} 位数字，请再说一次完整的手机号。`
        : '我没有听清手机号，请再说一次。';
    setError(message);
    void speak(message);
  });

  // ── 语音输入验证码：识别到后自动登录 ──
  const codeSpeech = useSpeechInput((text) => {
    const digits = extractDigits(text);
    if (digits.length >= 4) {
      const value = digits.slice(0, 6);
      setCode(value);
      setError('');
      void doLogin(phone, value);
      return;
    }
    const message = '我没有听清验证码，请再说一次六位数字。';
    setError(message);
    void speak(message);
  });

  const handleSendCode = () => {
    void requestCode(phone);
  };

  const handleLogin = (event: React.FormEvent) => {
    event.preventDefault();
    void doLogin(phone, code.trim());
  };

  return (
    <div className="min-h-screen flex">
      {/* 左侧品牌区 */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-[#0a1628] via-[#0d2847] to-[#1a4a8a] flex-col justify-center px-16 text-white relative overflow-hidden">
        <div className="absolute top-20 left-20 w-72 h-72 bg-blue-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-blue-400/8 rounded-full blur-3xl" />

        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-16">
            <div className="w-12 h-12 bg-white/15 backdrop-blur rounded-full flex items-center justify-center">
              <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
            </div>
            <span className="text-2xl font-bold tracking-wide">导盲AI</span>
          </div>

          <h1 className="text-5xl font-bold leading-tight mb-4">
            智能导盲
            <br />
            温暖同行
          </h1>
          <p className="text-lg text-blue-200/80 mb-20">为视障用户打造的智能语音助手</p>

          <div className="space-y-8 text-lg">
            <p>· 说手机号就能登录，不用记密码</p>
            <p>· 说“我要去公司”，自动规划路线</p>
            <p>· 说“帮我识别这个药品”，语音播报结果</p>
            <p>· 遇到危险，手机剧烈抖动即可求救</p>
          </div>
        </div>
      </div>

      {/* 右侧登录表单 */}
      <div className="w-full lg:w-1/2 flex items-center justify-center px-4 sm:px-6 py-8 sm:py-12 bg-white">
        <div className="w-full max-w-lg">
          <h2 className="text-2xl sm:text-4xl font-bold text-gray-900 mb-2">手机号登录</h2>
          <p className="text-base sm:text-xl text-gray-500 mb-6 sm:mb-10">
            输入手机号获取验证码，首次登录自动注册
          </p>

          {error && (
            <div
              className="mb-6 p-4 bg-red-50 border-2 border-red-300 rounded-2xl text-red-700 text-lg"
              role="alert"
              aria-live="assertive"
            >
              {error}
            </div>
          )}
          {notice && (
            <div
              className="mb-6 p-4 bg-green-50 border-2 border-green-300 rounded-2xl text-green-800 text-lg"
              role="status"
              aria-live="polite"
            >
              {notice}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-7">
            {/* 手机号 */}
            <div>
              <label htmlFor="phone" className="block text-lg sm:text-xl font-semibold text-gray-800 mb-2 sm:mb-3">
                手机号
              </label>
              <div className="flex gap-2 sm:gap-3">
                <input
                  id="phone"
                  type="tel"
                  inputMode="numeric"
                  autoComplete="tel"
                  value={phone}
                  onChange={(e) => setPhone(extractDigits(e.target.value).slice(0, 11))}
                  placeholder="请输入或说出 11 位手机号"
                  className="flex-1 min-w-0 px-3 sm:px-5 py-4 sm:py-5 bg-gray-50 border-2 border-gray-300 rounded-2xl
                             text-lg sm:text-2xl tracking-wider
                             focus:outline-none focus:border-[#1a4a8a] focus:ring-4 focus:ring-blue-200"
                  aria-describedby="phone-hint"
                  autoFocus
                />
                <button
                  type="button"
                  onClick={phoneSpeech.listening ? phoneSpeech.stop : phoneSpeech.start}
                  className={`w-16 sm:w-20 flex-shrink-0 rounded-2xl text-white flex flex-col items-center justify-center
                    focus:outline-none focus:ring-4 focus:ring-blue-300 transition-colors
                    ${phoneSpeech.listening ? 'bg-red-500 animate-pulse' : 'bg-[#1a4a8a] hover:bg-[#153d75]'}`}
                  aria-label={phoneSpeech.listening ? '停止语音输入手机号' : '语音输入手机号'}
                  aria-pressed={phoneSpeech.listening}
                >
                  <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                    />
                  </svg>
                  <span className="text-xs mt-1">说号码</span>
                </button>
              </div>
              <p id="phone-hint" className="mt-2 text-base text-gray-500">
                点击右侧麦克风，直接说出一串数字即可
              </p>
            </div>

            {/* 验证码 */}
            <div>
              <label htmlFor="code" className="block text-lg sm:text-xl font-semibold text-gray-800 mb-2 sm:mb-3">
                验证码
              </label>
              <div className="flex gap-2 sm:gap-3">
                <input
                  id="code"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  value={code}
                  onChange={(e) => setCode(extractDigits(e.target.value).slice(0, 6))}
                  placeholder="6 位数字"
                  className="flex-1 min-w-0 px-3 sm:px-5 py-4 sm:py-5 bg-gray-50 border-2 border-gray-300 rounded-2xl
                             text-lg sm:text-2xl tracking-[0.3em]
                             focus:outline-none focus:border-[#1a4a8a] focus:ring-4 focus:ring-blue-200"
                />
                <button
                  type="button"
                  onClick={codeSpeech.listening ? codeSpeech.stop : codeSpeech.start}
                  className={`w-16 sm:w-20 flex-shrink-0 rounded-2xl text-white flex flex-col items-center justify-center
                    focus:outline-none focus:ring-4 focus:ring-blue-300 transition-colors
                    ${codeSpeech.listening ? 'bg-red-500 animate-pulse' : 'bg-[#1a4a8a] hover:bg-[#153d75]'}`}
                  aria-label={codeSpeech.listening ? '停止语音输入验证码' : '语音输入验证码'}
                  aria-pressed={codeSpeech.listening}
                >
                  <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                    />
                  </svg>
                  <span className="text-xs mt-1">说验证码</span>
                </button>
              </div>
              <button
                type="button"
                onClick={handleSendCode}
                disabled={sending || countdown > 0}
                className="mt-2 sm:mt-3 w-full py-3 sm:py-4 rounded-2xl bg-gray-100 hover:bg-gray-200 disabled:opacity-60 text-gray-800
                           text-base sm:text-lg font-semibold focus:outline-none focus:ring-4 focus:ring-gray-300"
              >
                {countdown > 0 ? `${countdown} 秒后重发` : sending ? '发送中…' : '获取验证码'}
              </button>
              <p className="mt-2 text-sm sm:text-base text-gray-500">
                演示阶段不发送真实短信，验证码会打印在后端控制台
              </p>
              {(phoneSpeech.error || codeSpeech.error) && (
                <p className="mt-2 text-base text-red-600" role="alert">
                  {phoneSpeech.error || codeSpeech.error}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={logging}
              className="w-full py-4 sm:py-5 bg-[#1a4a8a] hover:bg-[#153d75] text-white text-xl sm:text-2xl font-bold rounded-2xl
                         transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed
                         shadow-lg shadow-blue-900/20 focus:outline-none focus:ring-4 focus:ring-blue-300"
            >
              {logging ? '登录中…' : '登 录'}
            </button>
          </form>

          <p className="mt-10 text-center text-base text-gray-400">
            首次使用该手机号将自动创建账号，无需注册
          </p>
        </div>
      </div>
    </div>
  );
}
