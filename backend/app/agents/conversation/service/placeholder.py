"""Conversation 业务占位。

后续按需求拆分为: vad.py / asr.py / tts.py / wake_word.py / conversation.py
"""


class ConversationService:
    """对话服务占位。"""

    async def process(self, text: str) -> str:
        """占位处理方法。"""
        raise NotImplementedError("Conversation 业务逻辑开发中")
