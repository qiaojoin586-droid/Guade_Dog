/**
 * 定位 Hook（占位骨架）。
 *
 * 使用浏览器 Geolocation API 获取用户位置。
 */

import { useCallback, useEffect, useState } from 'react';

interface LocationData {
  lat: number;
  lng: number;
  accuracy: number;
}

interface UseLocationReturn {
  location: LocationData | null;
  error: string | null;
  isLoading: boolean;
  refresh: () => void;
}

export function useLocation(): UseLocationReturn {
  const [location, setLocation] = useState<LocationData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const getLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setError('浏览器不支持定位');
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    // TODO: 实现真实定位逻辑
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        });
        setError(null);
        setIsLoading(false);
      },
      (err) => {
        setError(err.message);
        setIsLoading(false);
      },
    );
  }, []);

  useEffect(() => {
    getLocation();
  }, [getLocation]);

  return { location, error, isLoading, refresh: getLocation };
}
