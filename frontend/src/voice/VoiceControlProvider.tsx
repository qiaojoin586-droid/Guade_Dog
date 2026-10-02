/**
 * 全局语音控制中枢。
 *
 * 一次语音的完整链路：
 *   麦克风 → Web Speech 识别 → /conversation/command → 播报 + 执行 action
 *
 * action 与界面的映射：
 *   navigation.start → 播放 video/ 视频（摄像头模拟）+ 播报路线
 *   vision.capture   → 展示 images/ 图片（拍照模拟）+ 播报写死的识别结果
 *   sos.confirm      → 播报后开启 10 秒倒计时，超时自动求救
 *
 * 播报期间会主动暂停识别，避免把自己的播报声识别成用户指令。
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';

import CameraSimulation from '../components/CameraSimulation';
import { useVoiceRecorder } from '../hooks/useVoiceRecorder';
import {
  sendCommand,
  type CommandResult,
  type CommandToolData,
  type CommandTrigger,
} from '../services/commandService';
import { getBrowserLocation } from '../services/navigationService';
import { speechToText } from '../services/speechService';
import { speak, stopSpeaking, warmUpVoices } from '../services/tts';
import { isNegativeReply, isPositiveReply, normalizeUtterance } from '../utils/voiceText';
import { getRecognitionCtor, type VoiceRecognition } from './recognition';

/** 语音识别通道：browser=浏览器实时识别，server=录音上传讯飞 ASR */
export type VoiceMode = 'browser' | 'server';

export interface OverlayState {
  mode: 'navigation' | 'vision';
  src: string;
  title: string;
  subtitle?: string;
}

export interface ChatLine {
  role: 'user' | 'assistant';
  text: string;
}

interface VoiceControlValue {
  supported: boolean;
  /** 当前识别通道（浏览器实时 / 录音上传） */
  mode: VoiceMode;
  listening: boolean;
  busy: boolean;
  /** 实时识别到的文字（含临时结果） */
  transcript: string;
  /** 最近一次助手回复 */
  reply: string;
  error: string;
  /** 是否处于 SOS 10 秒确认窗口 */
  sosPending: boolean;
  lines: ChatLine[];
  startListening: () => void;
  stopListening: () => void;
  runCommand: (text: string, trigger?: CommandTrigger) => Promise<void>;
  simulateShake: () => void;
  closeOverlay: () => void;
  clearError: () => void;
}

const VoiceControlContext = createContext<VoiceControlValue | null>(null);

const DEFAULT_VIDEO = '/video/navigation.mp4';
const DEFAULT_IMAGE = '/images/test.jpg';

const VOICE_MODE_KEY = 'guide-dog:voice-mode';

export function VoiceControlProvider({ children }: { children: ReactNode }) {
  // 浏览器不支持实时识别，或本会话已判定实时识别不可用（国内网络），直接用录音上传通道
  const [mode, setMode] = useState<VoiceMode>(() => {
    try {
      if (sessionStorage.getItem(VOICE_MODE_KEY) === 'server') return 'server';
    } catch {
      // 隐私模式下 sessionStorage 可能不可用
    }
    return getRecognitionCtor() ? 'browser' : 'server';
  });

  const supported = useMemo(() => {
    const hasRecognition = getRecognitionCtor() !== null;
    const hasRecorder =
      typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia;
    return hasRecognition || hasRecorder;
  }, []);

  const recorder = useVoiceRecorder();

  const [listening, setListening] = useState(false);
  const [busy, setBusy] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [reply, setReply] = useState('');
  const [error, setError] = useState('');
  const [sosPending, setSosPending] = useState(false);
  const [overlay, setOverlay] = useState<OverlayState | null>(null);
  const [lines, setLines] = useState<ChatLine[]>([]);

  const recognitionRef = useRef<VoiceRecognition | null>(null);
  const wantListeningRef = useRef(false);
  const speakingRef = useRef(false);
  const busyRef = useRef(false);
  const sosRef = useRef(false);
  const sosTimerRef = useRef<number | null>(null);
  // 指令序号：后到的指令作废前一条的后续动作，避免旧流程覆盖新播报
  const seqRef = useRef(0);

  const runCommandRef = useRef<(text: string, trigger?: CommandTrigger) => Promise<void>>(
    async () => {},
  );
  const handleFinalRef = useRef<(text: string) => void>(() => {});
  // 供事件回调读取最新值，避免闭包过期
  const modeRef = useRef<VoiceMode>(mode);
  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);
  const speakTextRef = useRef<(text: string) => Promise<void>>(async () => {});

  const pushLine = useCallback((role: 'user' | 'assistant', text: string) => {
    setLines((prev) => [...prev.slice(-9), { role, text }]);
  }, []);

  /** 播报：先暂停识别，播完再恢复，避免自问自答。 */
  const speakText = useCallback(async (text: string) => {
    const content = text.trim();
    if (!content) return;

    speakingRef.current = true;
    try {
      recognitionRef.current?.abort();
    } catch {
      // 忽略
    }

    try {
      await speak(content);
    } finally {
      speakingRef.current = false;
      // 只有浏览器实时识别才需要播完自动续听；录音模式由用户手动点按
      if (wantListeningRef.current && modeRef.current === 'browser') {
        window.setTimeout(() => {
          if (wantListeningRef.current && !speakingRef.current) {
            try {
              recognitionRef.current?.start();
            } catch {
              // 已在运行则忽略
            }
          }
        }, 350);
      }
    }
  }, []);

  useEffect(() => {
    speakTextRef.current = speakText;
  }, [speakText]);

  const clearSosWindow = useCallback(() => {
    sosRef.current = false;
    setSosPending(false);
    if (sosTimerRef.current !== null) {
      window.clearTimeout(sosTimerRef.current);
      sosTimerRef.current = null;
    }
  }, []);

  const startSosWindow = useCallback(
    (timeoutMs: number) => {
      clearSosWindow();
      sosRef.current = true;
      setSosPending(true);
      sosTimerRef.current = window.setTimeout(() => {
        sosRef.current = false;
        setSosPending(false);
        sosTimerRef.current = null;
        void runCommandRef.current('', 'sos_timeout');
      }, timeoutMs);
    },
    [clearSosWindow],
  );

  /** 执行后端返回的 action；seq 变化说明已有更新的指令，旧流程立即停止。 */
  const applyResult = useCallback(
    async (result: CommandResult, seq: number) => {
      const isCurrent = () => seq === seqRef.current;
      const data: CommandToolData = result.tool_data ?? {};
      setReply(result.text);
      pushLine('assistant', result.text);

      switch (result.action) {
        case 'sos.confirm': {
          // 先播报询问，再开始 10 秒倒计时；
          // 播报最多等 6 秒（避免语音服务异常时倒计时迟迟不启动）
          await Promise.race([
            speakText(result.text),
            new Promise((resolve) => window.setTimeout(resolve, 6_000)),
          ]);
          if (isCurrent()) startSosWindow(data.timeout_ms ?? 10_000);
          return;
        }
        case 'sos.sent':
        case 'sos.canceled': {
          clearSosWindow();
          await speakText(result.text);
          return;
        }
        case 'navigation.start': {
          await speakText(result.text);
          if (!isCurrent()) return;
          setOverlay({
            mode: 'navigation',
            src: data.video || DEFAULT_VIDEO,
            title: `正在前往${data.label || data.destination || '目的地'}`,
            subtitle: '摄像头已打开（演示：播放本地视频模拟画面）',
          });
          if (data.followup_text) {
            await new Promise((resolve) =>
              window.setTimeout(resolve, data.followup_delay_ms ?? 1_800),
            );
            if (!isCurrent()) return;
            setReply(data.followup_text);
            pushLine('assistant', data.followup_text);
            await speakText(data.followup_text);
          }
          return;
        }
        case 'navigation.stop': {
          setOverlay(null);
          await speakText(result.text);
          return;
        }
        case 'vision.capture': {
          await speakText(result.text);
          if (!isCurrent()) return;
          setOverlay({
            mode: 'vision',
            src: data.image || DEFAULT_IMAGE,
            title: '正在识别',
            subtitle: '摄像头已拍照（演示：使用本地图片模拟）',
          });
          if (data.result_text) {
            await new Promise((resolve) =>
              window.setTimeout(resolve, data.followup_delay_ms ?? 1_600),
            );
            if (!isCurrent()) return;
            setReply(data.result_text);
            pushLine('assistant', data.result_text);
            await speakText(data.result_text);
          }
          return;
        }
        default: {
          await speakText(result.text);
        }
      }
    },
    [clearSosWindow, pushLine, speakText, startSosWindow],
  );

  /** 发送一条指令（语音或按钮触发）。 */
  const runCommand = useCallback(
    async (text: string, trigger: CommandTrigger = '') => {
      const content = text.trim();
      if (!content && !trigger) return;

      // 求救事件（抖动/超时）必须能打断正在进行的播报，不能被 busy 挡掉
      const isTrigger = trigger !== '';
      if (busyRef.current && !isTrigger) return;

      const seq = seqRef.current + 1;
      seqRef.current = seq;
      if (isTrigger) stopSpeaking();

      busyRef.current = true;
      setBusy(true);
      setError('');
      if (content) {
        setTranscript(content);
        pushLine('user', content);
      }

      try {
        // 天气/定位类问题需要坐标：只在相关说法时取一次，避免每条指令都等定位
        const needLocation = /天气|气温|温度|下雨|位置|在哪|多远|距离|附近|周边/.test(content);
        const coords = needLocation
          ? await getBrowserLocation({ timeoutMs: 2500, enableHighAccuracy: false })
          : null;

        const result = await sendCommand(content, trigger, coords);
        if (seq !== seqRef.current) return;
        await applyResult(result, seq);
      } catch (err: unknown) {
        if (seq !== seqRef.current) return;
        const message =
          (err as { response?: { data?: { message?: string } } })?.response?.data?.message ??
          '网络异常，请稍后再说一次';
        setError(message);
        setReply(message);
        pushLine('assistant', message);
        await speakText(message);
      } finally {
        if (seq === seqRef.current) {
          busyRef.current = false;
          setBusy(false);
        }
      }
    },
    [applyResult, pushLine, speakText],
  );

  useEffect(() => {
    runCommandRef.current = runCommand;
  }, [runCommand]);

  /** 一句识别结束后：SOS 窗口内只认“需要/不需要”，其余忽略。 */
  const handleFinal = useCallback(
    (raw: string) => {
      const text = normalizeUtterance(raw);
      if (!text) return;

      if (sosRef.current) {
        if (isNegativeReply(text)) {
          clearSosWindow();
          void runCommand('', 'sos_cancel');
          return;
        }
        if (isPositiveReply(text)) {
          clearSosWindow();
          void runCommand('', 'sos_timeout');
          return;
        }
        setTranscript(text);
        return;
      }

      void runCommand(text);
    },
    [clearSosWindow, runCommand],
  );

  useEffect(() => {
    handleFinalRef.current = handleFinal;
  }, [handleFinal]);

  /** 初始化常驻识别器（continuous 模式，结束自动重启）。 */
  useEffect(() => {
    warmUpVoices();
    const Ctor = getRecognitionCtor();
    if (!Ctor) return;

    const rec = new Ctor();
    rec.lang = 'zh-CN';
    rec.continuous = true;
    rec.interimResults = true;
    rec.maxAlternatives = 1;

    rec.onstart = () => setListening(true);

    rec.onend = () => {
      setListening(false);
      if (wantListeningRef.current && !speakingRef.current) {
        window.setTimeout(() => {
          if (wantListeningRef.current && !speakingRef.current) {
            try {
              rec.start();
            } catch {
              // 忽略重复启动
            }
          }
        }, 400);
      }
    };

    rec.onerror = (event) => {
      if (event.error === 'no-speech' || event.error === 'aborted') return;
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        wantListeningRef.current = false;
        setListening(false);
        setError('麦克风权限被拒绝，请在浏览器地址栏允许使用麦克风');
        return;
      }
      if (event.error === 'network') {
        // Chrome 的实时识别依赖境外服务，国内网络会直接失败：自动切到录音上传讯飞 ASR
        wantListeningRef.current = false;
        setListening(false);
        modeRef.current = 'server';
        setMode('server');
        try {
          sessionStorage.setItem(VOICE_MODE_KEY, 'server');
        } catch {
          // 忽略
        }
        const message =
          '浏览器语音服务连不上（Chrome 实时识别依赖境外网络）。已自动切换为录音识别：点一下麦克风开始录音，说完再点一下结束。';
        setError(message);
        void speakTextRef.current(message);
        return;
      }
      setError('语音识别出错，请再说一次');
    };

    rec.onresult = (event) => {
      let finalText = '';
      let interimText = '';
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        const content = result[0]?.transcript ?? '';
        if (result.isFinal) finalText += content;
        else interimText += content;
      }
      if (interimText) setTranscript(interimText);
      if (finalText) {
        setTranscript(finalText);
        handleFinalRef.current(finalText);
      }
    };

    recognitionRef.current = rec;

    return () => {
      wantListeningRef.current = false;
      try {
        rec.abort();
      } catch {
        // 忽略
      }
      recognitionRef.current = null;
      if (sosTimerRef.current !== null) window.clearTimeout(sosTimerRef.current);
      stopSpeaking();
    };
  }, []);

  /** 录音上传识别（server 模式：讯飞 ASR）。 */
  const transcribeByServer = useCallback(
    async (blob: Blob) => {
      setBusy(true);
      try {
        const { text } = await speechToText(blob);
        const clean = normalizeUtterance(text);
        if (!clean) {
          const message = '没听清，请再说一次';
          setError(message);
          void speakTextRef.current(message);
          return;
        }
        setTranscript(clean);
        await runCommandRef.current(clean);
      } catch (err: unknown) {
        const message =
          (err as { response?: { data?: { message?: string } } })?.response?.data?.message ??
          '录音识别失败，请再说一次';
        setError(message);
        void speakTextRef.current(message);
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  const startListening = useCallback(() => {
    setError('');

    // 录音模式：点一下开始录音
    if (mode === 'server') {
      setListening(true);
      void recorder.start();
      return;
    }

    const rec = recognitionRef.current;
    if (!rec) {
      // 没有实时识别能力，退回录音模式
      setMode('server');
      modeRef.current = 'server';
      setListening(true);
      void recorder.start();
      return;
    }
    wantListeningRef.current = true;
    try {
      rec.start();
      setListening(true);
    } catch {
      // 已经在监听
      setListening(true);
    }
  }, [mode, recorder]);

  const stopListening = useCallback(() => {
    // 录音模式：结束录音并上传识别
    if (mode === 'server') {
      setListening(false);
      void (async () => {
        const blob = await recorder.stop();
        if (blob) await transcribeByServer(blob);
      })();
      return;
    }

    wantListeningRef.current = false;
    try {
      recognitionRef.current?.abort();
    } catch {
      // 忽略
    }
    stopSpeaking();
    setListening(false);
  }, [mode, recorder, transcribeByServer]);

  const simulateShake = useCallback(() => {
    void runCommand('', 'shake');
  }, [runCommand]);

  const closeOverlay = useCallback(() => {
    const wasNavigation = overlay?.mode === 'navigation';
    setOverlay(null);
    stopSpeaking();
    if (wasNavigation) {
      void speakText('已结束导航。');
    }
  }, [overlay, speakText]);

  const clearError = useCallback(() => setError(''), []);

  // 录音设备异常（如麦克风被拒）直接提示
  useEffect(() => {
    if (recorder.error) {
      setError(recorder.error);
      setListening(false);
    }
  }, [recorder.error]);

  const value = useMemo<VoiceControlValue>(
    () => ({
      supported,
      mode,
      listening,
      busy,
      transcript,
      reply,
      error,
      sosPending,
      lines,
      startListening,
      stopListening,
      runCommand,
      simulateShake,
      closeOverlay,
      clearError,
    }),
    [
      supported,
      mode,
      listening,
      busy,
      transcript,
      reply,
      error,
      sosPending,
      lines,
      startListening,
      stopListening,
      runCommand,
      simulateShake,
      closeOverlay,
      clearError,
    ],
  );

  return (
    <VoiceControlContext.Provider value={value}>
      {children}
      {overlay && (
        <CameraSimulation
          mode={overlay.mode}
          src={overlay.src}
          title={overlay.title}
          subtitle={overlay.subtitle}
          onClose={closeOverlay}
        />
      )}
    </VoiceControlContext.Provider>
  );
}

export function useVoiceControl(): VoiceControlValue {
  const ctx = useContext(VoiceControlContext);
  if (!ctx) {
    throw new Error('useVoiceControl 必须在 VoiceControlProvider 内使用');
  }
  return ctx;
}
