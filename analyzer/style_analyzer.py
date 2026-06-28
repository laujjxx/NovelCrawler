"""
AI 写作风格分析
"""
from typing import Any, Dict, List

from base.base_analyzer import BaseAnalyzer
from tools.utils import truncate_text


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

    async def analyze(self, novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析小说的写作风格
        Args:
            novel_data: 包含 detail 和 chapters 的完整数据
        Returns:
            风格分析结果
        """
        detail = novel_data.get("detail", {})
        chapters = novel_data.get("chapters", [])

        # 构建分析 prompt
        user_prompt = self._build_prompt(detail, chapters)
        self.logger.info(f"正在分析写作风格: {detail.get('title', '未知')}")

        result = await self._call_llm_json(
            system_prompt=STYLE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        result["analysis_type"] = "writing_style"
        result["book_id"] = detail.get("book_id", "")
        result["title"] = detail.get("title", "")
        return result

    def _build_prompt(
        self, detail: Dict, chapters: List[Dict]
    ) -> str:
        """构建分析 prompt"""
        parts = [
            f"## 小说信息",
            f"- 书名: {detail.get('title', '未知')}",
            f"- 作者: {detail.get('author', '未知')}",
            f"- 类型: {detail.get('category', '未知')} {detail.get('sub_category', '')}",
            f"- 标签: {', '.join(detail.get('tags', []))}",
            f"- 总字数: {detail.get('word_count', 0)}",
            f"- 章节数: {len(chapters)}",
            f"- 状态: {detail.get('status', '未知')}",
            f"- 评分: {detail.get('score', '无')}",
            f"",
            f"## 简介",
            f"{detail.get('description', '无简介')}",
            f"",
            f"## 章节目录（前30章）",
        ]

        for i, ch in enumerate(chapters[:30]):
            parts.append(f"  {i+1}. {ch.get('title', '无标题')}")

        if len(chapters) > 30:
            parts.append(f"  ... 共 {len(chapters)} 章")

        parts.append("")
        parts.append("请根据以上信息分析该小说的写作风格。")

        return "\n".join(parts)
