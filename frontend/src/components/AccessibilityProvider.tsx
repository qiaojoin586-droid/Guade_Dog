/**
 * 无障碍上下文提供者（占位）。
 *
 * 提供全局无障碍配置（大字号、高对比度等）。
 */

import { createContext, useContext } from 'react';

interface AccessibilityContext {
  highContrast: boolean;
  fontSize: 'large' | 'xlarge';
}

const defaultContext: AccessibilityContext = {
  highContrast: false,
  fontSize: 'large',
};

const AccessibilityCtx = createContext(defaultContext);

export function AccessibilityProvider({ children }: { children: React.ReactNode }) {
  // TODO: 从 useSettingsStore 读取配置
  return (
    <AccessibilityCtx.Provider value={defaultContext}>
      {children}
    </AccessibilityCtx.Provider>
  );
}

export function useAccessibility() {
  return useContext(AccessibilityCtx);
}
