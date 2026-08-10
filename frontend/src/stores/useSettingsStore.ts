/**
 * 设置状态管理。
 *
 * 管理用户偏好设置（语音速度、主题等）。
 */

import { create } from 'zustand';

interface SettingsState {
  voiceSpeed: number;
  voiceVolume: number;
  highContrast: boolean;
  fontSize: 'large' | 'xlarge';

  setVoiceSpeed: (speed: number) => void;
  setVoiceVolume: (volume: number) => void;
  setHighContrast: (enabled: boolean) => void;
  setFontSize: (size: 'large' | 'xlarge') => void;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  voiceSpeed: 1.0,
  voiceVolume: 1.0,
  highContrast: false,
  fontSize: 'large',

  setVoiceSpeed: (voiceSpeed) => set({ voiceSpeed }),
  setVoiceVolume: (voiceVolume) => set({ voiceVolume }),
  setHighContrast: (highContrast) => set({ highContrast }),
  setFontSize: (fontSize) => set({ fontSize }),
}));
