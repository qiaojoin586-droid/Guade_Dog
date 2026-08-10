"""Navigation 业务占位。

后续按需求拆分为: location.py / route_planner.py / poi_search.py /
obstacle_detector.py / traffic_light.py / safety_judge.py / guidance_generator.py
"""


class NavigationService:
    """导航服务占位。"""

    async def process(self, params: dict) -> dict:
        """占位处理方法。"""
        raise NotImplementedError("Navigation 业务逻辑开发中")
