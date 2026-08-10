/**
 * WebSocket Hook（自动重连 + 心跳骨架）。
 *
 * 自动重连策略：指数退避，最大间隔 ≤ 3s。
 * 心跳：定期发送 ping 保持连接。
 */

import { useCallback, useEffect, useRef, useState } from 'react';

type WSStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

interface UseWebSocketOptions {
  url: string;
  onMessage?: (data: string) => void;
  heartbeatInterval?: number;
  maxReconnectDelay?: number;
}

interface UseWebSocketReturn {
  status: WSStatus;
  send: (message: string) => void;
  connect: () => void;
  disconnect: () => void;
}

export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
  const { url, onMessage: _onMessage, heartbeatInterval: _heartbeatInterval = 30000, maxReconnectDelay: _maxReconnectDelay = 3000 } = options;
  const [status, setStatus] = useState<WSStatus>('disconnected');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const heartbeatTimerRef = useRef<ReturnType<typeof setInterval>>();

  const connect = useCallback(() => {
    // TODO: 实现 WebSocket 连接、自动重连、心跳逻辑
    setStatus('connecting');
  }, [url]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    clearInterval(heartbeatTimerRef.current);
    clearTimeout(reconnectTimerRef.current);
    setStatus('disconnected');
  }, []);

  const send = useCallback((message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    }
  }, []);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return { status, send, connect, disconnect };
}
