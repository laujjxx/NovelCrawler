"""
AI 人物关系分析
"""
from typing import Any, Dict, List

from base.base_analyzer import BaseAnalyzer


CHARACTER_SYSTEM_PROMPT = """你是一位资深的网文分析专家和角色设计师。
你需要根据提供的小说信息，分析其人物设定和关系网络。
请用 JSON 格式返回分析结果，包含以下字段：
{
    "summary": "一句话总结人物设定特点",
    "protagonist": {
        "name": "主角名（如果能推断）",
        "type": "主角类型（如：废柴逆袭/天才型/重生者/穿越者/系统流等）",
        "personality": "性格特点",
        "ability": "能力设定",
        "growth_arc": "成长弧线描述"
    },
    "supporting_characters": [
        {
            "name": "角色名",
            "role": "角色定位（如：导师/对手/伙伴/恋人等）",
            "importance": "重要程度（核心/重要/次要）",
            "description": "简要描述"
        }
    ],
    "relationship_web": [
        {"from": "角色A", "to": "角色B", "relation": "关系描述"}
    ],
    "antagonist": {
        "name": "反派名（如果能推断）",
        "type": "反派类型",
        "motivation": "动机"
    },
    "character_design_score": 8.0,
    "character_diversity": "角色多样性评价",
    "character_growth": "角色成长性评价",
    "common_archetypes": ["使用了哪些常见角色原型"],
    "unique_design": ["独特的人设创新点"],
    "suggestions": ["人物设计改进建议"]
}"""


class CharacterAnalyzer(BaseAnalyzer):
    """人物关系 AI 分析器"""

    SYSTEM_PROMPT = CHARACTER_SYSTEM_PROMPT
    ANALYSIS_TYPE = "character_analysis"
    MAX_CHAPTERS_IN_PROMPT = 50  # 人物分析需要更多章节上下文

    async def analyze(self, novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析小说的人物设定和关系"""
        detail = novel_data.get("detail", {})
        chapters = novel_data.get("chapters", [])

        extra_instruction = (
            "请根据简介和章节目录推断该小说的人物设定和关系网络。"
            "注意：你可能无法获取所有角色信息，请基于已有信息做合理推断，"
            "对于不确定的信息请标注'推断'。"
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
