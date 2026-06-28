"""
通用工具函数
"""
import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from config.base_config import LOG_FORMAT, LOG_LEVEL


def setup_logger(name: str) -> logging.Logger:
    """创建一个格式化的 Logger"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    return logger


def get_today_str() -> str:
    """返回今天的日期字符串，如 2026-06-28"""
    return datetime.now().strftime("%Y-%m-%d")


def clean_text(text: str) -> str:
    """清理文本中的多余空白字符"""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_word_count(text: str) -> int:
    """
    解析字数文本，如 '123.4万字' -> 1234000
    """
    text = clean_text(text)
    text = text.replace(",", "").replace("，", "")
    match = re.search(r"([\d.]+)\s*万", text)
    if match:
        return int(float(match.group(1)) * 10000)
    match = re.search(r"([\d.]+)", text)
    if match:
        return int(float(match.group(1)))
    return 0


def ensure_dir(path: str) -> str:
    """确保目录存在，不存在则创建"""
    os.makedirs(path, exist_ok=True)
    return path


def save_json(data: Any, filepath: str, ensure_ascii: bool = False) -> None:
    """保存 JSON 文件"""
    ensure_dir(os.path.dirname(filepath))
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=ensure_ascii, indent=2)


def load_json(filepath: str) -> Any:
    """加载 JSON 文件"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cookie(cookies: List[Dict], name: str, cookie_dir: str) -> None:
    """保存 Cookie 到文件"""
    ensure_dir(cookie_dir)
    filepath = os.path.join(cookie_dir, f"{name}_cookies.json")
    save_json(cookies, filepath)


def load_cookie(name: str, cookie_dir: str) -> Optional[List[Dict]]:
    """从文件加载 Cookie"""
    filepath = os.path.join(cookie_dir, f"{name}_cookies.json")
    if os.path.exists(filepath):
        return load_json(filepath)
    return None


def truncate_text(text: str, max_len: int = 500) -> str:
    """截断文本到指定长度"""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def extract_book_id(url: str) -> Optional[str]:
    """
    从起点 URL 中提取 bookId
    例: https://book.qidian.com/info/12345/ -> 12345
    """
    match = re.search(r"/info/(\d+)", url)
    if match:
        return match.group(1)
    match = re.search(r"/(\d+)/?$", url)
    if match:
        return match.group(1)
    return None


async def async_sleep(seconds: float) -> None:
    """异步等待"""
    import asyncio
    await asyncio.sleep(seconds)
