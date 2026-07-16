"""
测试数据模型: NovelInfo / NovelDetail / ChapterInfo
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from novel_platform.qidian.model import (
    ChapterInfo,
    NovelDetail,
    NovelInfo,
    make_chapter_info,
    make_chapter_list,
    make_novel_detail,
    make_novel_info,
)


class TestNovelInfo:
    def test_default_values(self):
        info = NovelInfo()
        assert info.book_id == ""
        assert info.word_count == 0
        assert info.is_serializing is True

    def test_from_dict(self):
        data = {
            "book_id": "12345",
            "title": "测试小说",
            "author": "测试作者",
            "word_count": 500000,
            "rank": 1,
            "rank_type": "yuepiao",
            "extra_field": "应该被忽略",
        }
        info = NovelInfo.from_dict(data)
        assert info.book_id == "12345"
        assert info.title == "测试小说"
        assert info.word_count == 500000
        assert info.rank == 1
        # extra_field 不应该出现在对象中
        assert not hasattr(info, "extra_field")

    def test_to_dict(self):
        info = NovelInfo(book_id="123", title="测试", word_count=10000)
        d = info.to_dict()
        assert d["book_id"] == "123"
        assert d["title"] == "测试"
        assert d["word_count"] == 10000

    def test_from_dict_partial(self):
        """部分字段缺失时使用默认值"""
        data = {"book_id": "123", "title": "部分字段"}
        info = NovelInfo.from_dict(data)
        assert info.book_id == "123"
        assert info.author == ""  # 默认值
        assert info.word_count == 0  # 默认值

    def test_factory_function(self):
        data = {"book_id": "999", "title": "工厂测试"}
        info = make_novel_info(data)
        assert isinstance(info, NovelInfo)
        assert info.book_id == "999"


class TestNovelDetail:
    def test_from_dict(self):
        data = {
            "book_id": "12345",
            "title": "详情测试",
            "author": "作者A",
            "category": "玄幻",
            "sub_category": "东方玄幻",
            "tags": ["爽文", "系统流"],
            "word_count": 1000000,
            "status": "连载中",
            "score": 9.2,
        }
        detail = NovelDetail.from_dict(data)
        assert detail.book_id == "12345"
        assert detail.tags == ["爽文", "系统流"]
        assert detail.score == 9.2

    def test_word_count_display(self):
        detail = NovelDetail(word_count=1234500)
        assert detail.word_count_display == "123.5万字"

        detail2 = NovelDetail(word_count=5000)
        assert detail2.word_count_display == "5000字"

        detail3 = NovelDetail(word_count=0)
        assert detail3.word_count_display == "0字"

    def test_factory_function(self):
        data = {"book_id": "888", "title": "详情工厂"}
        detail = make_novel_detail(data)
        assert isinstance(detail, NovelDetail)
        assert detail.book_id == "888"

    def test_default_tags_is_list(self):
        detail = NovelDetail()
        assert detail.tags == []
        # 确保修改 tags 不会影响其他实例
        detail.tags.append("测试")
        detail2 = NovelDetail()
        assert detail2.tags == []


class TestChapterInfo:
    def test_default_values(self):
        ch = ChapterInfo()
        assert ch.chapter_id == ""
        assert ch.is_vip is False
        assert ch.word_count == 0

    def test_from_dict(self):
        data = {
            "chapter_id": "ch001",
            "title": "第一章 开局",
            "volume_name": "第一卷",
            "word_count": 3000,
            "is_vip": True,
        }
        ch = ChapterInfo.from_dict(data)
        assert ch.chapter_id == "ch001"
        assert ch.title == "第一章 开局"
        assert ch.is_vip is True

    def test_to_dict(self):
        ch = ChapterInfo(chapter_id="c1", title="测试", is_vip=False)
        d = ch.to_dict()
        assert d["is_vip"] is False

    def test_factory_function(self):
        data = {"chapter_id": "c99", "title": "工厂章节"}
        ch = make_chapter_info(data)
        assert isinstance(ch, ChapterInfo)
        assert ch.chapter_id == "c99"

    def test_batch_factory(self):
        data_list = [
            {"chapter_id": "c1", "title": "第1章"},
            {"chapter_id": "c2", "title": "第2章", "is_vip": True},
        ]
        chapters = make_chapter_list(data_list)
        assert len(chapters) == 2
        assert all(isinstance(c, ChapterInfo) for c in chapters)
        assert chapters[1].is_vip is True
