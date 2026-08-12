/**
 * 导航状态管理。
 *
 * 管理当前导航会话、路线、位置等信息。
 */

import { create } from 'zustand';
import type { LocationResult, RouteResult } from '../types';

interface NavigationState {
  isNavigating: boolean;
  currentLocation: { lat: number; lng: number } | null;
  /** 逆地理编码后的地址信息 */
  locationResult: LocationResult | null;
  destination: string | null;
  /** 路线规划结果 */
  routeResult: RouteResult | null;
  routeGeoJSON: object | null;
  /** 加载状态 */
  loading: boolean;
  error: string | null;

  setNavigating: (isNavigating: boolean) => void;
  setCurrentLocation: (location: { lat: number; lng: number } | null) => void;
  setLocationResult: (result: LocationResult | null) => void;
  setDestination: (destination: string | null) => void;
  setRouteResult: (result: RouteResult | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialState = {
  isNavigating: false,
  currentLocation: null as { lat: number; lng: number } | null,
  locationResult: null as LocationResult | null,
  destination: null as string | null,
  routeResult: null as RouteResult | null,
  routeGeoJSON: null as object | null,
  loading: false,
  error: null as string | null,
};

export const useNavigationStore = create<NavigationState>((set) => ({
  ...initialState,

  setNavigating: (isNavigating) => set({ isNavigating }),
  setCurrentLocation: (currentLocation) => set({ currentLocation }),
  setLocationResult: (locationResult) => set({ locationResult }),
  setDestination: (destination) => set({ destination }),
  setRouteResult: (routeResult) => set({ routeResult }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  reset: () => set(initialState),
}));
