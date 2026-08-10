/**
 * 摄像头 Hook（占位骨架）。
 *
 * Phase 2+ 启用，骨架阶段只提供接口签名。
 */

import { useState } from 'react';

interface UseCameraReturn {
  isActive: boolean;
  startCamera: () => Promise<void>;
  stopCamera: () => void;
  captureFrame: () => Promise<Blob | null>;
}

export function useCamera(): UseCameraReturn {
  const [isActive, setIsActive] = useState(false);

  const startCamera = async () => {
    // TODO: 实现摄像头开启逻辑（getUserMedia）
    setIsActive(true);
  };

  const stopCamera = () => {
    // TODO: 实现摄像头关闭逻辑
    setIsActive(false);
  };

  const captureFrame = async (): Promise<Blob | null> => {
    // TODO: 实现帧捕获逻辑
    return null;
  };

  return { isActive, startCamera, stopCamera, captureFrame };
}
