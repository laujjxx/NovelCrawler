"""
基础结构分析 — 不依赖 LLM，纯统计计算
"""
import re
from collections import Counter
from typing import Any, Dict, List

from tools.utils import setup_logger


logger = setup_logger("structure_analyzer")


def analyze_structure(
    detail: Dict[str, Any],
    chapters: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    对小说进行基础结构分析（纯统计，不需要 LLM）
    Args:
        detail: 小说详情字典
        chapters: 章节列表
    Returns:
        结构分析结果
    """
    result = {}

    # ===== 基本信息 =====
    result["book_id"] = detail.get("book_id", "")
    result["title"] = detail.get("title", "")
    result["author"] = detail.get("author", "")
    result["category"] = detail.get("category", "")
    result["status"] = detail.get("status", "")

    # ===== 字数统计 =====
    total_words = detail.get("word_count", 0)
    chapter_count = len(chapters)
    result["word_count"] = total_words
    result["chapter_count"] = chapter_count

    if chapter_count > 0 and total_words > 0:
        result["avg_chapter_words"] = round(total_words / chapter_count)
    else:
        result["avg_chapter_words"] = 0

    # ===== 卷结构分析 =====
    volumes = Counter()
    for ch in chapters:
        vol = ch.get("volume_name", "默认卷")
        if vol:
            volumes[vol] += 1
    result["volume_count"] = len(volumes)
    result["volumes"] = dict(volumes.most_common(20))

    # ===== VIP 章节比例 =====
    vip_count = sum(1 for ch in chapters if ch.get("is_vip", False))
    result["vip_chapter_count"] = vip_count
    result["vip_ratio"] = round(vip_count / chapter_count, 3) if chapter_count > 0 else 0

    # ===== 章节标题分析 =====
    chapter_titles = [ch.get("title", "") for ch in chapters if ch.get("title")]
    result["chapter_title_patterns"] = _analyze_title_patterns(chapter_titles)

    # ===== 更新频率估算 =====
    update_time = detail.get("update_time", "")
    result["update_time"] = update_time
    result["update_frequency"] = _estimate_frequency(total_words, chapter_count, detail)

    # ===== 评分和热度 =====
    result["score"] = detail.get("score", 0)
    result["click_count"] = detail.get("click_count", 0)
    result["recommend_count"] = detail.get("recommend_count", 0)
    result["collection_count"] = detail.get("collection_count", 0)
    result["fan_value"] = detail.get("fan_value", 0)

    # ===== 标签 =====
    result["tags"] = detail.get("tags", [])

    # ===== 生成摘要 =====
    result["summary"] = _generate_summary(result)

    return result


def _analyze_title_patterns(titles: List[str]) -> Dict[str, Any]:
    """分析章节标题的模式"""
    if not titles:
        return {}

    patterns = {
        "has_numbering": 0,      # 带数字编号的标题
        "has_brackets": 0,       # 带括号的标题
        "has_question": 0,       # 疑问句标题
        "avg_length": 0,         # 平均标题长度
    }

    total_len = 0
    for t in titles:
        total_len += len(t)
        if re.search(r"第[一二三四五六七八九十百千\d]+章", t):
            patterns["has_numbering"] += 1
        if re.search(r"[【\[（(]", t):
            patterns["has_brackets"] += 1
        if "?" in t or "？" in t:
            patterns["has_question"] += 1

    patterns["avg_length"] = round(total_len / len(titles), 1) if titles else 0
    patterns["has_numbering_ratio"] = round(
        patterns["has_numbering"] / len(titles), 3
    ) if titles else 0

    return patterns


def _estimate_frequency(
    total_words: int, chapter_count: int, detail: Dict
) -> str:
    """估算更新频率"""
    avg_words = total_words / chapter_count if chapter_count > 0 else 0

    # 根据平均章节字数推断
    if avg_words >= 3000:
        return "日更3000+（勤奋作者）"
    elif avg_words >= 2000:
        return "日更2000+（正常更新）"
    elif avg_words >= 1000:
        return "日更1000+（轻度更新）"
    else:
        return "不定期更新"


def _generate_summary(data: Dict[str, Any]) -> str:
    """生成文字摘要"""
    parts = []
    title = data.get("title", "未知")
    author = data.get("author", "未知")
    parts.append(f"《{title}》by {author}")

    wc = data.get("word_count", 0)
    if wc >= 10000:
        parts.append(f"共 {wc / 10000:.1f} 万字")
    else:
        parts.append(f"共 {wc} 字")

    parts.append(f"{data.get('chapter_count', 0)} 章")
    parts.append(f"均章 {data.get('avg_chapter_words', 0)} 字")

    if data.get("category"):
        parts.append(f"类型: {data['category']}")

    if data.get("score"):
        parts.append(f"评分: {data['score']}")

    if data.get("status"):
        parts.append(f"状态: {data['status']}")

    return " | ".join(parts)
