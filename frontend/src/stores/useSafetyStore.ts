/**
 * 安全状态管理。
 *
 * 管理 SOS 状态、紧急联系人等信息。
 */

import { create } from 'zustand';

type SOSStatus = 'none' | 'pending' | 'dispatched' | 'acknowledged' | 'resolved';

interface SafetyState {
  sosStatus: SOSStatus;
  emergencyContacts: Array<{ id: string; name: string; phone: string }>;

  setSOSStatus: (status: SOSStatus) => void;
  setEmergencyContacts: (contacts: Array<{ id: string; name: string; phone: string }>) => void;
  reset: () => void;
}

export const useSafetyStore = create<SafetyState>((set) => ({
  sosStatus: 'none',
  emergencyContacts: [],

  setSOSStatus: (sosStatus) => set({ sosStatus }),
  setEmergencyContacts: (emergencyContacts) => set({ emergencyContacts }),
  reset: () => set({ sosStatus: 'none' }),
}));
