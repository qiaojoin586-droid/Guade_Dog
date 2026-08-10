/**
 * 语音交互 Hook（双轨降级骨架）。
 *
 * 探测 SpeechRecognition 可用性：
 * - 可用：使用浏览器 Web Speech API
 * - 不可用：降级到占位实现
 *
 * 参见前端文档 §7.2。
 */

import { useCallback, useEffect } from 'react';
import { useVoiceStore, type VoiceStatus } from '../stores/useVoiceStore';

/**
 * 检测当前浏览器是否支持语音识别。
 */
export function isSpeechSupported(): boolean {
  return typeof window !== 'undefined' && ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window);
}

interface UseSpeechReturn {
  status: VoiceStatus;
  transcript: string;
  isSupported: boolean;
  startListening: () => void;
  stopListening: () => void;
}

export function useSpeech(): UseSpeechReturn {
  const { status, transcript, isSupported, setStatus, setTranscript: _setTranscript, setPermission } = useVoiceStore();

  useEffect(() => {
    const supported = isSpeechSupported();
    useVoiceStore.setState({ isSupported: supported });
    if (!supported) {
      setPermission('denied');
    }
  }, [setPermission]);

  const startListening = useCallback(() => {
    if (!isSupported) {
      setStatus('error');
      return;
    }
    // TODO: 实现 Web Speech API 调用逻辑
    setStatus('listening');
  }, [isSupported, setStatus]);

  const stopListening = useCallback(() => {
    // TODO: 实现停止录音逻辑
    setStatus('idle');
  }, [setStatus]);

  return {
    status,
    transcript,
    isSupported,
    startListening,
    stopListening,
  };
}
