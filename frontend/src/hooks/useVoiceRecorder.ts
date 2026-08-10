/**
 * 语音录音 Hook: 封装 getUserMedia + MediaRecorder。
 *
 * 用法(按住说话):
 *   const { isRecording, error, start, stop } = useVoiceRecorder();
 *   onPointerDown={start} onPointerUp={async () => {
 *     const blob = await stop();
 *     if (blob) { ... 上传识别 }
 *   }}
 */

import { useCallback, useRef, useState } from 'react';

/** 浏览器支持的录音格式优先级(Chrome/Edge 均支持 webm/opus) */
const MIME_TYPES = ['audio/webm;codecs=opus', 'audio/webm', ''];

function pickMimeType(): string | undefined {
  const supported = MIME_TYPES.find((t) => !t || MediaRecorder.isTypeSupported(t));
  return supported || undefined;
}

export function useVoiceRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  /** 开始录音(请求麦克风权限) */
  const start = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = pickMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
    } catch {
      setError('无法访问麦克风，请检查浏览器权限设置');
    }
  }, []);

  /** 停止录音,返回音频 Blob;未在录音时返回 null */
  const stop = useCallback((): Promise<Blob | null> => {
    return new Promise((resolve) => {
      const recorder = recorderRef.current;
      if (!recorder || recorder.state === 'inactive') {
        resolve(null);
        return;
      }
      const stream = recorder.stream;
      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        setIsRecording(false);
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        chunksRef.current = [];
        resolve(blob);
      };
      recorder.stop();
    });
  }, []);

  return { isRecording, error, start, stop };
}
