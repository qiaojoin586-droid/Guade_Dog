/**
 * 摄像头模拟画面（导航 / 拍照识别）。
 *
 * 演示阶段不打开真实摄像头：
 * - 导航：循环播放 video/ 目录下的视频，模拟行走画面；
 * - 识别：展示 images/ 目录下的图片，模拟刚拍到的画面。
 *
 * 素材缺失时给出明确提示，不白屏。
 */

import { useState } from 'react';

interface CameraSimulationProps {
  mode: 'navigation' | 'vision';
  src: string;
  title: string;
  subtitle?: string;
  onClose: () => void;
}

export default function CameraSimulation({
  mode,
  src,
  title,
  subtitle,
  onClose,
}: CameraSimulationProps) {
  const [missing, setMissing] = useState(false);

  return (
    <div
      className="fixed inset-0 z-[60] bg-black flex flex-col"
      role="dialog"
      aria-modal="true"
      aria-label={`${mode === 'navigation' ? '导航画面' : '拍照画面'}模拟`}
    >
      {/* 顶部信息条 */}
      <div className="px-4 sm:px-6 py-3 sm:py-4 bg-black/70 text-white">
        <p className="text-xl sm:text-2xl font-bold">{title}</p>
        {subtitle && <p className="text-sm sm:text-base text-gray-300 mt-1">{subtitle}</p>}
      </div>

      {/* 画面 */}
      <div className="flex-1 relative overflow-hidden bg-black">
        {missing ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center px-6 sm:px-8">
            <div className="w-16 h-16 sm:w-24 sm:h-24 rounded-full border-4 border-white/30 flex items-center justify-center mb-4 sm:mb-6">
              <span className="text-2xl sm:text-4xl text-white/70">?</span>
            </div>
            <p className="text-white text-lg sm:text-2xl font-bold mb-2 sm:mb-3">未找到演示素材</p>
            <p className="text-gray-300 text-sm sm:text-lg leading-relaxed break-all">
              请把文件放到：
              <br />
              <span className="text-yellow-300 font-mono">{src}</span>
            </p>
          </div>
        ) : mode === 'navigation' ? (
          <video
            className="w-full h-full object-cover"
            src={src}
            autoPlay
            muted
            loop
            playsInline
            aria-hidden="true"
            onError={() => setMissing(true)}
          />
        ) : (
          <img
            className="w-full h-full object-contain bg-black"
            src={src}
            alt="摄像头拍摄到的画面"
            onError={() => setMissing(true)}
          />
        )}

        {/* 装饰取景框 */}
        <div className="absolute inset-3 sm:inset-6 border-2 border-white/30 rounded-2xl sm:rounded-3xl pointer-events-none" />

        <div className="absolute top-4 sm:top-6 left-1/2 -translate-x-1/2 px-4 sm:px-5 py-1.5 sm:py-2 rounded-full bg-red-600 text-white text-xs sm:text-base font-semibold whitespace-nowrap">
          {mode === 'navigation' ? '导航中 · 摄像头（模拟）' : '已拍照 · 摄像头（模拟）'}
        </div>
      </div>

      {/* 底部操作 */}
      <div className="px-4 sm:px-6 py-4 sm:py-6 bg-black/70">
        <button
          type="button"
          onClick={onClose}
          className="w-full py-4 sm:py-5 rounded-2xl bg-white text-black text-xl sm:text-2xl font-bold
                     focus:outline-none focus:ring-4 focus:ring-white/50"
          aria-label={mode === 'navigation' ? '结束导航' : '关闭画面'}
        >
          {mode === 'navigation' ? '结束导航' : '关闭画面'}
        </button>
      </div>
    </div>
  );
}
