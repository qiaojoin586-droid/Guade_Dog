/**
 * Web Speech API 的最小类型封装。
 *
 * TypeScript 的 lib.dom 目前只有 SpeechRecognitionResult* 相关类型，
 * 缺少 SpeechRecognition 构造器与事件类型，这里做本地声明，
 * 避免引入额外依赖，也避免与未来的 lib.dom 声明冲突。
 */

export interface VoiceRecognitionAlternative {
  transcript: string;
  confidence: number;
}

export interface VoiceRecognitionResult {
  readonly length: number;
  readonly isFinal: boolean;
  [index: number]: VoiceRecognitionAlternative;
}

export interface VoiceRecognitionResultList {
  readonly length: number;
  [index: number]: VoiceRecognitionResult;
}

export interface VoiceRecognitionEvent extends Event {
  readonly resultIndex: number;
  readonly results: VoiceRecognitionResultList;
}

export interface VoiceRecognitionErrorEvent extends Event {
  readonly error: string;
  readonly message: string;
}

export interface VoiceRecognition extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onstart: ((event: Event) => void) | null;
  onresult: ((event: VoiceRecognitionEvent) => void) | null;
  onerror: ((event: VoiceRecognitionErrorEvent) => void) | null;
  onend: ((event: Event) => void) | null;
}

type VoiceRecognitionCtor = new () => VoiceRecognition;

interface RecognitionWindow {
  SpeechRecognition?: VoiceRecognitionCtor;
  webkitSpeechRecognition?: VoiceRecognitionCtor;
}

/** 取浏览器语音识别构造器；不支持时返回 null。 */
export function getRecognitionCtor(): VoiceRecognitionCtor | null {
  if (typeof window === 'undefined') return null;
  const w = window as unknown as RecognitionWindow;
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

/** 当前浏览器是否支持语音识别。 */
export function isRecognitionSupported(): boolean {
  return getRecognitionCtor() !== null;
}
