/**
 * 单句语音输入 Hook（用于登录页说手机号/验证码等表单场景）。
 *
 * 一次性识别：说完自动结束，不常驻监听。
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { getRecognitionCtor, type VoiceRecognition } from '../voice/recognition';

// 同一时刻只允许一个识别实例（登录页有两个麦克风按钮）
let activeRecognition: VoiceRecognition | null = null;

interface UseSpeechInputReturn {
  listening: boolean;
  error: string;
  start: () => void;
  stop: () => void;
}

export function useSpeechInput(onResult: (text: string) => void): UseSpeechInputReturn {
  const [listening, setListening] = useState(false);
  const [error, setError] = useState('');
  const recognitionRef = useRef<VoiceRecognition | null>(null);
  const callbackRef = useRef(onResult);

  useEffect(() => {
    callbackRef.current = onResult;
  }, [onResult]);

  const stop = useCallback(() => {
    const rec = recognitionRef.current;
    if (rec) {
      try {
        rec.stop();
      } catch {
        // 已停止时忽略
      }
    }
    setListening(false);
  }, []);

  const start = useCallback(() => {
    const Ctor = getRecognitionCtor();
    if (!Ctor) {
      setError('当前浏览器不支持语音输入，请使用电脑版 Chrome 或 Edge');
      return;
    }
    setError('');

    try {
      activeRecognition?.abort();
    } catch {
      // 忽略
    }

    const rec = new Ctor();
    activeRecognition = rec;
    recognitionRef.current = rec;
    rec.lang = 'zh-CN';
    rec.continuous = false;
    rec.interimResults = true;
    rec.maxAlternatives = 1;

    rec.onstart = () => setListening(true);
    rec.onresult = (event) => {
      let text = '';
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        if (result.isFinal) text += result[0]?.transcript ?? '';
      }
      if (text) callbackRef.current(text);
    };
    rec.onerror = (event) => {
      if (event.error === 'no-speech' || event.error === 'aborted') return;
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        setError('麦克风权限被拒绝，请允许使用麦克风');
        return;
      }
      if (event.error === 'network') {
        setError('浏览器语音服务不可用，请直接输入手机号或验证码');
        return;
      }
      setError('语音识别失败，请再试一次');
    };
    rec.onend = () => {
      setListening(false);
      if (activeRecognition === rec) activeRecognition = null;
    };

    try {
      rec.start();
    } catch {
      setError('语音识别启动失败，请再试一次');
    }
  }, []);

  useEffect(() => {
    return () => {
      const rec = recognitionRef.current;
      if (rec) {
        try {
          rec.abort();
        } catch {
          // 忽略
        }
      }
    };
  }, []);

  return { listening, error, start, stop };
}
