"""
测试结构分析器 (analyzer/structure_analyzer.py)
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyzer.structure_analyzer import (
    _analyze_title_patterns,
    _estimate_frequency,
    _generate_summary,
    analyze_structure,
)


class TestAnalyzeTitlePatterns:
    def test_numbered_titles(self):
        titles = ["第一章 开局", "第二章 修炼", "第三章 突破"]
        result = _analyze_title_patterns(titles)
        assert result["has_numbering"] == 2
        assert result["has_numbering_ratio"] == 1.0

    def test_bracketed_titles(self):
        titles = ["【系统】激活", "（公告）重要通知"]
        result = _analyze_title_patterns(titles)
        assert result["has_brackets"] == 2

    def test_question_titles(self):
        titles = ["这是谁？", "Where am I?", "普通章节"]
        result = _analyze_title_patterns(titles)
        assert result["has_question"] == 2

    def test_avg_length(self):
        titles = ["第一章", "第二十二章", "第三百三十三章"]
        result = _analyze_title_patterns(titles)
        assert result["avg_length"] > 0

    def test_empty_list(self):
        result = _analyze_title_patterns([])
        assert result == {}

    def test_mixed_patterns(self):
        titles = [
            "第一章 【觉醒】这是谁？",
            "第二章 修炼之路",
            "第三篇（上）",
        ]
        result = _analyze_title_patterns(titles)
        assert result["has_numbering"] == 2
        assert result["has_brackets"] == 2
        assert result["has_question"] == 1


class TestEstimateFrequency:
    def test_daily_3000(self):
        result = _estimate_frequency(300000, 100, {})
        assert "3000" in result

    def test_daily_2000(self):
        result = _estimate_frequency(200000, 100, {})
        assert "2000" in result

    def test_daily_1000(self):
        result = _estimate_frequency(100000, 100, {})
        assert "1000" in result

    def test_no_chapters(self):
        result = _estimate_frequency(500000, 0, {})
        assert "不定期" in result


class TestGenerateSummary:
    def test_full_summary(self):
        data = {
            "title": "测试小说",
            "author": "测试作者",
            "word_count": 500000,
            "chapter_count": 100,
            "avg_chapter_words": 5000,
            "category": "玄幻",
            "score": 9.2,
            "status": "连载中",
        }
        summary = _generate_summary(data)
        assert "测试小说" in summary
        assert "测试作者" in summary
        assert "玄幻" in summary
        assert "9.2" in summary


class TestAnalyzeStructure:
    def test_basic_analysis(self):
        detail = {
            "book_id": "12345",
            "title": "测试小说",
            "author": "作者A",
            "category": "玄幻",
            "word_count": 500000,
            "status": "连载中",
            "score": 9.0,
            "tags": ["爽文", "系统流"],
        }
        chapters = [
            {"title": "第一章 开局", "volume_name": "第一卷", "is_vip": False},
            {"title": "第二章 修炼", "volume_name": "第一卷", "is_vip": False},
            {"title": "第三章 VIP章", "volume_name": "第一卷", "is_vip": True},
        ]
        result = analyze_structure(detail, chapters)

        assert result["book_id"] == "12345"
        assert result["word_count"] == 500000
        assert result["chapter_count"] == 3
        assert result["avg_chapter_words"] == 166667
        assert result["vip_chapter_count"] == 1
        assert result["vip_ratio"] == pytest.approx(0.333)
        assert "summary" in result

    def test_no_chapters(self):
        detail = {"book_id": "1", "title": "测试", "word_count": 10000}
        result = analyze_structure(detail, [])
        assert result["chapter_count"] == 0
        assert result["avg_chapter_words"] == 0

    def test_no_vip(self):
        detail = {"book_id": "2", "word_count": 300000}
        chapters = [
            {"title": "Ch1", "volume_name": "Vol1", "is_vip": False},
            {"title": "Ch2", "volume_name": "Vol1", "is_vip": False},
        ]
        result = analyze_structure(detail, chapters)
        assert result["vip_ratio"] == 0.0
