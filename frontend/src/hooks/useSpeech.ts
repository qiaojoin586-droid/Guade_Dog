/**
 * 语音交互 Hook（Web Speech API）。
 *
 * 单句识别 + 全局语音状态机：idle → listening → idle。
 * 常驻语音控制请使用 VoiceControlProvider。
 */

import { useCallback, useEffect } from 'react';
import { getRecognitionCtor } from '../voice/recognition';
import { useVoiceStore, type VoiceStatus } from '../stores/useVoiceStore';
import { useSpeechInput } from './useSpeechInput';

/** 当前浏览器是否支持语音识别。 */
export function isSpeechSupported(): boolean {
  return getRecognitionCtor() !== null;
}

interface UseSpeechReturn {
  status: VoiceStatus;
  transcript: string;
  isSupported: boolean;
  startListening: () => void;
  stopListening: () => void;
}

export function useSpeech(): UseSpeechReturn {
  const { status, transcript, setStatus, setTranscript, setPermission } = useVoiceStore();

  useEffect(() => {
    const supported = isSpeechSupported();
    useVoiceStore.setState({ isSupported: supported });
    setPermission(supported ? 'granted' : 'denied');
  }, [setPermission]);

  const input = useSpeechInput((text) => {
    setTranscript(text);
    setStatus('idle');
  });

  const startListening = useCallback(() => {
    setStatus('listening');
    input.start();
  }, [input, setStatus]);

  const stopListening = useCallback(() => {
    input.stop();
    setStatus('idle');
  }, [input, setStatus]);

  return {
    status,
    transcript,
    isSupported: isSpeechSupported(),
    startListening,
    stopListening,
  };
}
