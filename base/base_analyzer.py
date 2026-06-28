"""
AI 分析器基类 — 统一 LLM 调用接口
"""
import abc
import json
from typing import Any, Dict, List, Optional

import httpx

from config.base_config import LLM_API_BASE, LLM_API_KEY, LLM_MAX_TOKENS, LLM_MODEL, LLM_TEMPERATURE
from tools.utils import setup_logger, truncate_text


class BaseAnalyzer(abc.ABC):
    """
    AI 分析器基类
    统一封装 LLM API 调用，子类只需实现具体的分析 prompt
    """

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
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            response_format: 响应格式（如 "json_object"）
        Returns:
            LLM 返回的文本
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
            self.logger.error(f"LLM API 请求失败 [{e.response.status_code}]: {e.response.text[:500]}")
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
        """
        调用 LLM 并解析 JSON 响应
        """
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
        """
        执行分析
        Args:
            novel_data: 小说数据（详情 + 章节等）
        Returns:
            分析结果字典
        """
        raise NotImplementedError
