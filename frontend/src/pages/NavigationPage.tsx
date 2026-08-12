/**
 * 导航页面。
 *
 * 功能：
 * 1. 定位按钮 — 获取当前位置并播报
 * 2. 目的地输入 + 规划按钮 — 规划步行路线并播报
 * 3. 路线摘要卡片 — 展示距离/耗时/前几步
 *
 * TTS 播报使用浏览器 SpeechSynthesis API。
 */

import { useState, useCallback } from 'react';
import { getCurrentLocation, planRoute, getBrowserLocation } from '../services/navigationService';
import { useNavigationStore } from '../stores/useNavigationStore';
import type { LocationResult, RouteResult } from '../types';

/** 调浏览器 TTS 播报文字 */
function speak(text: string): void {
  if (!window.speechSynthesis) return;
  // 取消正在播放的语音，避免堆积
  window.speechSynthesis.cancel();
  const utt = new SpeechSynthesisUtterance(text);
  utt.lang = 'zh-CN';
  utt.rate = 0.9;
  window.speechSynthesis.speak(utt);
}

export default function NavigationPage() {
  const {
    locationResult, routeResult, loading, error,
    setLocationResult, setRouteResult, setLoading, setError,
  } = useNavigationStore();

  const [destination, setDestination] = useState('');

  // ---------- 定位 ----------
  const handleLocate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result: LocationResult = await getCurrentLocation();
      setLocationResult(result);
      speak(result.tts_text);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '定位失败';
      setError(msg);
      speak(msg);
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, setLocationResult]);

  // ---------- 路线规划 ----------
  const handleRoute = useCallback(async () => {
    if (!destination.trim()) {
      setError('请输入目的地');
      speak('请输入目的地');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const coords = await getBrowserLocation();
      const result: RouteResult = await planRoute(destination.trim(), coords);
      setRouteResult(result);
      speak(result.tts_text);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '路线规划失败';
      setError(msg);
      speak(msg);
    } finally {
      setLoading(false);
    }
  }, [destination, setLoading, setError, setRouteResult]);

  // ---------- 渲染 ----------
  return (
    <div className="min-h-screen px-6 py-8 max-w-lg mx-auto space-y-8">
      {/* 标题 */}
      <h1 className="text-3xl font-bold text-center">🗺️ 导航</h1>

      {/* ── 错误提示 ── */}
      {error && (
        <div
          role="alert"
          className="bg-red-100 border border-red-400 text-red-800 rounded-xl px-5 py-4 text-lg"
        >
          ⚠️ {error}
        </div>
      )}

      {/* ── 当前位置 ── */}
      <section className="space-y-4">
        <button
          onClick={handleLocate}
          disabled={loading}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400
                     text-white text-xl font-semibold py-5 rounded-2xl
                     transition-colors focus:outline-none focus:ring-4 focus:ring-blue-300"
          aria-label="获取当前位置"
        >
          {loading ? '⏳ 定位中…' : '📍 我在哪里'}
        </button>

        {locationResult && (
          <div className="bg-green-50 border border-green-300 rounded-xl px-5 py-4 text-lg space-y-1">
            <p className="text-green-800 font-semibold">📍 当前位置</p>
            <p className="text-gray-800">{locationResult.address}</p>
            <p className="text-sm text-gray-500">
              定位方式: {locationResult.source === 'gps' ? 'GPS 精确定位' : '网络粗定位'}
            </p>
          </div>
        )}
      </section>

      {/* ── 目的地规划 ── */}
      <section className="space-y-4">
        <label className="block text-lg font-semibold text-gray-700" htmlFor="dest-input">
          🎯 目的地
        </label>
        <div className="flex gap-3">
          <input
            id="dest-input"
            type="text"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleRoute(); }}
            placeholder="例如：天安门"
            className="flex-1 text-lg px-4 py-3 border-2 border-gray-300 rounded-xl
                       focus:outline-none focus:border-blue-500"
          />
          <button
            onClick={handleRoute}
            disabled={loading}
            className="bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-400
                       text-white text-lg font-semibold px-6 py-3 rounded-xl
                       transition-colors focus:outline-none focus:ring-4 focus:ring-emerald-300"
            aria-label="开始导航"
          >
            {loading ? '⏳' : '🧭 导航'}
          </button>
        </div>

        {routeResult && (
          <div className="bg-emerald-50 border border-emerald-300 rounded-xl px-5 py-4 space-y-3">
            {/* 总览 */}
            <div className="flex justify-between items-center">
              <p className="text-emerald-800 font-bold text-xl">🧭 路线规划</p>
              <p className="text-gray-600">
                <span className="font-semibold text-emerald-700">{routeResult.summary.distance_m} 米</span>
                {' · '}
                <span className="font-semibold text-emerald-700">{routeResult.summary.duration_min} 分钟</span>
              </p>
            </div>

            {/* 起终点 */}
            <div className="text-gray-700 text-base space-y-1">
              {routeResult.summary.start_address && (
                <p>🚩 起点: {routeResult.summary.start_address}</p>
              )}
              <p>🏁 终点: {routeResult.summary.end_address}</p>
            </div>

            {/* 前几步 */}
            <details>
              <summary className="text-gray-600 cursor-pointer hover:text-gray-800">
                查看全部 {routeResult.steps.length} 步路线
              </summary>
              <ol className="mt-3 space-y-2 text-base text-gray-700">
                {routeResult.steps.map((s, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-gray-400 font-mono">{i + 1}.</span>
                    <span>{s.instruction}</span>
                    <span className="text-gray-400 text-sm ml-auto">{s.distance_m}m</span>
                  </li>
                ))}
              </ol>
            </details>

            {/* 播报文案 */}
            <div className="bg-white rounded-lg px-4 py-3 text-gray-700 italic">
              📢 {routeResult.tts_text}
            </div>
          </div>
        )}
      </section>

      {/* ── 底部提示 ── */}
      <p className="text-center text-sm text-gray-400">
        语音导航请使用主页麦克风按钮
      </p>
    </div>
  );
}
