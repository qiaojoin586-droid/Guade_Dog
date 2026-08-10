/**
 * 导航状态管理。
 *
 * 管理当前导航会话、路线、位置等信息。
 */

import { create } from 'zustand';

interface NavigationState {
  isNavigating: boolean;
  currentLocation: { lat: number; lng: number } | null;
  destination: string | null;
  routeGeoJSON: object | null;

  setNavigating: (isNavigating: boolean) => void;
  setCurrentLocation: (location: { lat: number; lng: number } | null) => void;
  setDestination: (destination: string | null) => void;
  reset: () => void;
}

export const useNavigationStore = create<NavigationState>((set) => ({
  isNavigating: false,
  currentLocation: null,
  destination: null,
  routeGeoJSON: null,

  setNavigating: (isNavigating) => set({ isNavigating }),
  setCurrentLocation: (currentLocation) => set({ currentLocation }),
  setDestination: (destination) => set({ destination }),
  reset: () => set({ isNavigating: false, destination: null, routeGeoJSON: null }),
}));
