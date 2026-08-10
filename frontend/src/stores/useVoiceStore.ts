/**
 * 语音交互状态机。
 *
 * 状态: idle → listening → processing → speaking → idle
 * 异常: error → idle
 */

import { create } from 'zustand';

export type VoiceStatus = 'idle' | 'listening' | 'processing' | 'speaking' | 'error';
export type Permission = 'prompt' | 'granted' | 'denied' | 'unknown';

interface VoiceState {
  status: VoiceStatus;
  permission: Permission;
  transcript: string;
  isSupported: boolean;

  setStatus: (status: VoiceStatus) => void;
  setPermission: (permission: Permission) => void;
  setTranscript: (text: string) => void;
  reset: () => void;
}

export const useVoiceStore = create<VoiceState>((set) => ({
  status: 'idle',
  permission: 'unknown',
  transcript: '',
  isSupported: false,

  setStatus: (status) => set({ status }),
  setPermission: (permission) => set({ permission }),
  setTranscript: (transcript) => set({ transcript }),
  reset: () => set({ status: 'idle', transcript: '' }),
}));
