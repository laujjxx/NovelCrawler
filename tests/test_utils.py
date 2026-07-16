"""
测试 tools/utils.py 中的工具函数
"""
import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.utils import (
    clean_text,
    ensure_dir,
    extract_book_id,
    get_today_str,
    load_json,
    parse_word_count,
    save_json,
    truncate_text,
)


class TestCleanText:
    def test_whitespace_collapse(self):
        assert clean_text("  hello   world  ") == "hello world"

    def test_newlines_and_tabs(self):
        assert clean_text("line1\nline2\t\tline3") == "line1 line2 line3"

    def test_empty_string(self):
        assert clean_text("") == ""

    def test_none(self):
        assert clean_text(None) == ""

    def test_chinese_text(self):
        assert clean_text("  你好  世界  ") == "你好 世界"


class TestParseWordCount:
    def test_plain_integer(self):
        assert parse_word_count("12345") == 12345

    def test_wan_unit(self):
        assert parse_word_count("123.4万字") == 1234000

    def test_wan_unit_with_space(self):
        assert parse_word_count("100 万字") == 1000000

    def test_comma_separated(self):
        assert parse_word_count("1,234万") == 12340000

    def test_decimal_wan(self):
        assert parse_word_count("0.5万字") == 5000

    def test_only_number_with_text(self):
        assert parse_word_count("共 5000 字") == 5000

    def test_empty_string(self):
        assert parse_word_count("") == 0

    def test_no_number(self):
        assert parse_word_count("无数据") == 0

    def test_chinese_comma(self):
        assert parse_word_count("1，234万") == 12340000


class TestExtractBookId:
    def test_standard_url(self):
        assert extract_book_id("https://book.qidian.com/info/12345/") == "12345"

    def test_short_id(self):
        assert extract_book_id("https://book.qidian.com/info/1/") == "1"

    def test_trailing_path(self):
        assert extract_book_id("https://book.qidian.com/info/1035420986/#Catalog") == "1035420986"

    def test_no_match(self):
        # The regex /(\d+)/?$ matches /123
    assert extract_book_id("https://example.com/novel/123") == "123"

    def test_empty_url(self):
        assert extract_book_id("") is None


class TestTruncateText:
    def test_short_text(self):
        assert truncate_text("hello", max_len=10) == "hello"

    def test_long_text(self):
        assert truncate_text("hello world", max_len=8) == "hello wo..."

    def test_exact_length(self):
        assert truncate_text("hello", max_len=5) == "hello"

    def test_empty(self):
        assert truncate_text("", max_len=5) == ""


class TestGetTodayStr:
    def test_format(self):
        today = get_today_str()
        parts = today.split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 4  # year
        assert len(parts[1]) == 2  # month


class TestEnsureDir:
    def test_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = os.path.join(tmpdir, "a", "b", "c")
            result = ensure_dir(new_dir)
            assert result == new_dir
            assert os.path.isdir(new_dir)

    def test_existing_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = ensure_dir(tmpdir)
            assert result == tmpdir


class TestSaveAndLoadJson:
    def test_roundtrip(self):
        data = {"key": "value", "list": [1, 2, 3], "nested": {"a": 1}}
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.json")
            save_json(data, filepath)
            assert os.path.exists(filepath)
            loaded = load_json(filepath)
            assert loaded == data

    def test_chinese_text(self):
        data = {"书名": "测试小说", "作者": "测试作者"}
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "chinese.json")
            save_json(data, filepath)
            loaded = load_json(filepath)
            assert loaded["书名"] == "测试小说"

    def test_ensure_ascii_false(self):
        data = {"key": "中文"}
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "ascii.json")
            save_json(data, filepath, ensure_ascii=False)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            assert "中文" in content
