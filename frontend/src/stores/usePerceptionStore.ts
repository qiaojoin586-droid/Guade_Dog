/**
 * 感知服务状态管理。
 *
 * 管理 OCR、天气、提醒等生活服务数据。
 */

import { create } from 'zustand';

interface PerceptionState {
  weather: {
    temperature: number | null;
    condition: string | null;
    city: string | null;
  } | null;
  lastOCRResult: string | null;

  setWeather: (weather: PerceptionState['weather']) => void;
  setLastOCRResult: (text: string | null) => void;
  reset: () => void;
}

export const usePerceptionStore = create<PerceptionState>((set) => ({
  weather: null,
  lastOCRResult: null,

  setWeather: (weather) => set({ weather }),
  setLastOCRResult: (lastOCRResult) => set({ lastOCRResult }),
  reset: () => set({ weather: null, lastOCRResult: null }),
}));
