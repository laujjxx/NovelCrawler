"""
CSV/JSON 数据存储
"""
import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, List

from config.base_config import ANALYSIS_DIR, RANK_DIR
from tools.utils import ensure_dir, get_today_str, save_json, setup_logger

logger = setup_logger("csv_store")

# CSV 中需要导出的字段（排行榜）
RANK_CSV_FIELDS = [
    "rank",
    "book_id",
    "title",
    "author",
    "category",
    "word_count",
    "latest_chapter",
    "rank_type",
    "description",
    "book_url",
    "is_serializing",
    "monthly_ticket",
    "recommend_ticket",
    "collection_count",
]

# 小说详情的字段
DETAIL_FIELDS = [
    "book_id",
    "title",
    "author",
    "category",
    "sub_category",
    "tags",
    "word_count",
    "description",
    "status",
    "score",
    "click_count",
    "recommend_count",
    "collection_count",
    "fan_value",
    "latest_chapter",
    "update_time",
    "book_url",
]


def save_rank_csv(
    novels: List[Dict[str, Any]],
    platform: str,
    rank_type: str,
) -> str:
    """
    保存排行榜数据为 CSV
    Args:
        novels: 小说信息列表
        platform: 平台名称（如 'qidian'）
        rank_type: 榜单类型
    Returns:
        保存的文件路径
    """
    ensure_dir(RANK_DIR)
    filename = f"{platform}_{rank_type}_{get_today_str()}.csv"
    filepath = os.path.join(RANK_DIR, filename)

    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RANK_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for novel in novels:
            # 处理列表类型字段
            row = dict(novel)
            if isinstance(row.get("tags"), list):
                row["tags"] = "|".join(row["tags"])
            writer.writerow(row)

    logger.info(f"排行榜已保存: {filepath} ({len(novels)} 条)")
    return filepath


def save_rank_json(
    novels: List[Dict[str, Any]],
    platform: str,
    rank_type: str,
) -> str:
    """
    保存排行榜数据为 JSON
    """
    ensure_dir(RANK_DIR)
    filename = f"{platform}_{rank_type}_{get_today_str()}.json"
    filepath = os.path.join(RANK_DIR, filename)
    save_json(novels, filepath)
    logger.info(f"排行榜 JSON 已保存: {filepath} ({len(novels)} 条)")
    return filepath


def save_novel_detail(
    detail: Dict[str, Any],
    platform: str = "qidian",
) -> str:
    """
    保存小说详情为 JSON
    """
    ensure_dir(RANK_DIR)
    book_id = detail.get("book_id", "unknown")
    filename = f"{platform}_novel_{book_id}.json"
    filepath = os.path.join(RANK_DIR, filename)
    save_json(detail, filepath)
    logger.info(f"小说详情已保存: {filepath}")
    return filepath


def save_analysis_report(
    book_id: str,
    analysis: Dict[str, Any],
    platform: str = "qidian",
) -> str:
    """
    保存拆书分析报告为 JSON
    """
    ensure_dir(ANALYSIS_DIR)
    filename = f"{platform}_{book_id}_analysis_{get_today_str()}.json"
    filepath = os.path.join(ANALYSIS_DIR, filename)
    save_json(analysis, filepath)
    logger.info(f"分析报告已保存: {filepath}")
    return filepath


def save_analysis_csv(
    analyses: List[Dict[str, Any]],
    platform: str = "qidian",
) -> str:
    """
    批量保存分析摘要为 CSV（方便 Excel 查看）
    """
    ensure_dir(ANALYSIS_DIR)
    filename = f"{platform}_analysis_summary_{get_today_str()}.csv"
    filepath = os.path.join(ANALYSIS_DIR, filename)

    fields = [
        "book_id",
        "title",
        "author",
        "category",
        "word_count",
        "chapter_count",
        "avg_chapter_words",
        "update_frequency",
        "score",
        "writing_style",
        "plot_pace",
        "highlights",
    ]

    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for item in analyses:
            row = dict(item)
            # 将嵌套字段展平为字符串
            if isinstance(row.get("writing_style"), dict):
                row["writing_style"] = row["writing_style"].get("summary", str(row["writing_style"]))
            if isinstance(row.get("plot_pace"), dict):
                row["plot_pace"] = row["plot_pace"].get("summary", str(row["plot_pace"]))
            if isinstance(row.get("highlights"), list):
                row["highlights"] = " | ".join(row["highlights"][:3])
            writer.writerow(row)

    logger.info(f"分析摘要 CSV 已保存: {filepath}")
    return filepath
