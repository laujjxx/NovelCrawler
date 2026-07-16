"""
AI 情节节奏分析
"""
from typing import Any, Dict, List

from base.base_analyzer import BaseAnalyzer


PLOT_SYSTEM_PROMPT = """你是一位资深的网文策划和故事结构分析师。
你需要根据提供的小说信息，分析其情节结构和节奏。
请用 JSON 格式返回分析结果，包含以下字段：
{
    "summary": "一句话总结情节特点",
    "story_structure": "故事结构类型（如：线性叙事/多线并行/倒叙/插叙/环形结构等）",
    "conflict_type": "主要冲突类型（如：人与人/人与自然/人与社会/内心挣扎等）",
    "hook_points": [
        {"chapter": "章节名或位置", "description": "钩子/爽点描述"}
    ],
    "plot_rhythm": {
        "opening": "开头节奏评价（黄金三章分析）",
        "development": "发展段节奏",
        "climax": "高潮段处理",
        "overall": "整体节奏评价"
    },
    "turning_points": [
        {"chapter": "转折点位置", "description": "转折内容"}
    ],
    "pacing_score": 8.0,
    "tension_curve": "张力曲线描述（如：前30章逐步上升，中期波动，后期高潮迭起）",
    "common_patterns": ["使用了哪些常见套路/模板", "如：扮猪吃虎/打脸/升级流等"],
    "innovation_points": ["创新之处"],
    "suggestions": ["改进建议1", "改进建议2"]
}"""


class PlotAnalyzer(BaseAnalyzer):
    """情节节奏 AI 分析器"""

    SYSTEM_PROMPT = PLOT_SYSTEM_PROMPT
    ANALYSIS_TYPE = "plot_structure"
    MAX_CHAPTERS_IN_PROMPT = 50  # 情节分析需要更多章节

    async def analyze(self, novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析小说的情节结构和节奏"""
        detail = novel_data.get("detail", {})
        chapters = novel_data.get("chapters", [])

        extra_instruction = (
            "请根据章节目录和简介分析该小说的情节结构、节奏和套路。"
            "重点关注：黄金三章的钩子设置、主要转折点、爽点分布、常见套路的使用。"
        )
        user_prompt = self._build_prompt(detail, chapters, extra_instruction)
        self.logger.info(
            f"正在分析 [{self.ANALYSIS_TYPE}]: {detail.get('title', '未知')}"
        )

        result = await self._call_llm_json(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        result["analysis_type"] = self.ANALYSIS_TYPE
        result["book_id"] = detail.get("book_id", "")
        result["title"] = detail.get("title", "")
        return result
