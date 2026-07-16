"""
AI 写作风格分析
"""
from typing import Any, Dict, List

from base.base_analyzer import BaseAnalyzer


STYLE_SYSTEM_PROMPT = """你是一位资深的网文编辑和文学评论家。
你需要根据提供的小说信息，分析其写作风格特点。
请用 JSON 格式返回分析结果，包含以下字段：
{
    "summary": "一句话总结写作风格",
    "narrative_perspective": "叙事视角（第一人称/第三人称/上帝视角等）",
    "language_style": "语言风格特点（如：简洁明快/华丽细腻/幽默诙谐/沉重压抑等）",
    "dialogue_quality": "对话质量评价",
    "description_density": "描写密度（高/中/低）",
    "pace_feeling": "节奏感（快节奏/中等/慢节奏）",
    "strengths": ["优点1", "优点2", "优点3"],
    "weaknesses": ["不足1", "不足2"],
    "similar_authors": ["相似风格的知名作者1", "相似风格的知名作者2"],
    "target_audience": "目标读者群体",
    "style_score": 8.0
}"""


class StyleAnalyzer(BaseAnalyzer):
    """写作风格 AI 分析器"""

    SYSTEM_PROMPT = STYLE_SYSTEM_PROMPT
    ANALYSIS_TYPE = "writing_style"

    async def analyze(self, novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析小说的写作风格"""
        return await self._run_analysis(novel_data)
