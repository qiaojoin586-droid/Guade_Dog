"""Safety 业务占位。

后续按需求拆分为: sos_detector.py / location_tracker.py / family_notifier.py /
medicine_ocr.py / medicine_parser.py / health_knowledge.py / health_qa_agent.py
"""


class SafetyService:
    """安全服务占位。"""

    async def process(self, params: dict) -> dict:
        """占位处理方法。"""
        raise NotImplementedError("Safety 业务逻辑开发中")
