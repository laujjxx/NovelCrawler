"""
AI 分析器基类 — 统一 LLM 调用接口
"""
import abc
import json
from typing import Any, Dict, List, Optional

import httpx

from config.base_config import (
    LLM_API_BASE,
    LLM_API_KEY,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_TEMPERATURE,
)
from tools.utils import setup_logger, truncate_text


class BaseAnalyzer(abc.ABC):
    """
    AI 分析器基类
    统一封装 LLM API 调用，子类只需实现具体的分析 prompt
    """

    # 子类需定义的常量
    SYSTEM_PROMPT: str = ""
    ANALYSIS_TYPE: str = ""
    MAX_CHAPTERS_IN_PROMPT: int = 30

    def __init__(self):
        self.logger = setup_logger(self.__class__.__name__)
        self.api_base = LLM_API_BASE.rstrip("/")
        self.api_key = LLM_API_KEY
        self.model = LLM_MODEL
        self.max_tokens = LLM_MAX_TOKENS
        self.temperature = LLM_TEMPERATURE

    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
    ) -> str:
        """
        调用 LLM API（OpenAI 兼容格式）
        """
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        if response_format:
            payload["response_format"] = {"type": response_format}

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return content.strip()
        except httpx.HTTPStatusError as e:
            self.logger.error(
                f"LLM API 请求失败 [{e.response.status_code}]: "
                f"{e.response.text[:500]}"
            )
            raise
        except httpx.TimeoutException as e:
            self.logger.error(f"LLM API 调用超时: {e}")
            raise
        except Exception as e:
            self.logger.error(f"LLM API 调用异常: {e}")
            raise

    async def _call_llm_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """调用 LLM 并解析 JSON 响应"""
        raw = await self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            response_format="json_object",
        )
        # 尝试从 markdown 代码块中提取 JSON
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            self.logger.warning(f"JSON 解析失败，返回原始文本: {raw[:200]}")
            return {"raw_text": raw}

    @abc.abstractmethod
    async def analyze(self, novel_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行分析"""
        raise NotImplementedError

    # ==================== 共享的 prompt 构建 ====================

    def _build_prompt(
        self,
        detail: Dict[str, Any],
        chapters: List[Dict[str, Any]],
        extra_instruction: str = "",
    ) -> str:
        """
        构建分析 prompt 的公共模板
        子类可重写或直接使用
        """
        parts = [
            "## 小说信息",
            f"- 书名: {detail.get('title', '未知')}",
            f"- 作者: {detail.get('author', '未知')}",
            f"- 类型: {detail.get('category', '未知')} {detail.get('sub_category', '')}",
            f"- 标签: {', '.join(detail.get('tags', []))}",
            f"- 总字数: {detail.get('word_count', 0)}",
            f"- 章节数: {len(chapters)}",
            f"- 状态: {detail.get('status', '未知')}",
            "",
            "## 简介",
            detail.get("description", "无简介"),
            "",
            f"## 章节目录（前{self.MAX_CHAPTERS_IN_PROMPT}章）",
        ]

        for i, ch in enumerate(chapters[: self.MAX_CHAPTERS_IN_PROMPT]):
            vol = ch.get("volume_name", "")
            prefix = f"[{vol}] " if vol else ""
            parts.append(f"  {i+1}. {prefix}{ch.get('title', '无标题')}")

        if len(chapters) > self.MAX_CHAPTERS_IN_PROMPT:
            parts.append(f"  ... 共 {len(chapters)} 章")

        if extra_instruction:
            parts.append("")
            parts.append(extra_instruction)

        return "\n".join(parts)

    async def _run_analysis(
        self,
        novel_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        执行分析的通用流程
        子类应调用此方法，传入 ANALYSIS_TYPE 和 SYSTEM_PROMPT
        """
        detail = novel_data.get("detail", {})
        chapters = novel_data.get("chapters", [])

        user_prompt = self._build_prompt(detail, chapters)
        self.logger.info(f"正在分析 [{self.ANALYSIS_TYPE}]: {detail.get('title', '未知')}")

        result = await self._call_llm_json(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        result["analysis_type"] = self.ANALYSIS_TYPE
        result["book_id"] = detail.get("book_id", "")
        result["title"] = detail.get("title", "")
        return result
