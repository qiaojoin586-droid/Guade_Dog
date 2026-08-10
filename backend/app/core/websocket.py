"""WebSocket 连接管理器（占位实现）。

骨架阶段只提供接口签名与基本结构，不建立真实连接。
后续由 Conversation 负责人完善心跳、重连、广播等逻辑。
"""

from __future__ import annotations

from fastapi import WebSocket


class ConnectionManager:
    """管理活跃的 WebSocket 连接。"""

    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        """接受并注册一个新的 WebSocket 连接。"""
        await websocket.accept()
        self._connections[session_id] = websocket

    async def disconnect(self, session_id: str) -> None:
        """移除指定会话的连接。"""
        self._connections.pop(session_id, None)

    async def send_text(self, session_id: str, message: str) -> None:
        """向指定会话发送文本消息。"""
        ws = self._connections.get(session_id)
        if ws:
            await ws.send_text(message)

    async def broadcast(self, message: str) -> None:
        """向所有活跃连接广播消息。"""
        for ws in self._connections.values():
            await ws.send_text(message)


# 全局单例
manager = ConnectionManager()
