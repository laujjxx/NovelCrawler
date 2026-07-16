"""
起点中文网数据模型
提供类型安全的数据容器，支持从 dict 构造和序列化
"""
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class NovelInfo:
    """小说基本信息（排行榜级别）"""

    book_id: str = ""
    title: str = ""
    author: str = ""
    category: str = ""
    word_count: int = 0
    latest_chapter: str = ""
    rank: int = 0
    rank_type: str = ""
    cover_url: str = ""
    book_url: str = ""
    description: str = ""
    is_serializing: bool = True
    monthly_ticket: int = 0
    recommend_ticket: int = 0
    collection_count: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NovelInfo":
        """从字典构造，忽略多余字段"""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NovelDetail:
    """小说详细信息"""

    book_id: str = ""
    title: str = ""
    author: str = ""
    category: str = ""
    sub_category: str = ""
    tags: List[str] = field(default_factory=list)
    word_count: int = 0
    description: str = ""
    status: str = ""
    score: float = 0.0
    click_count: int = 0
    recommend_count: int = 0
    collection_count: int = 0
    fan_value: int = 0
    first_chapter_url: str = ""
    latest_chapter: str = ""
    latest_chapter_url: str = ""
    update_time: str = ""
    create_time: str = ""
    book_url: str = ""
    cover_url: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NovelDetail":
        """从字典构造，忽略多余字段"""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def word_count_display(self) -> str:
        """字数显示（如 '123.4万字'）"""
        if self.word_count >= 10000:
            return f"{self.word_count / 10000:.1f}万字"
        return f"{self.word_count}字"


@dataclass
class ChapterInfo:
    """章节信息"""

    chapter_id: str = ""
    title: str = ""
    volume_name: str = ""
    word_count: int = 0
    is_vip: bool = False
    update_time: str = ""
    url: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChapterInfo":
        """从字典构造，忽略多余字段"""
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def to_dict(self) -> dict:
        return asdict(self)


# ==================== 工厂函数 ====================


def make_novel_info(data: Dict[str, Any]) -> NovelInfo:
    """从爬虫返回的字典创建 NovelInfo 模型"""
    return NovelInfo.from_dict(data)


def make_novel_detail(data: Dict[str, Any]) -> NovelDetail:
    """从爬虫返回的字典创建 NovelDetail 模型"""
    return NovelDetail.from_dict(data)


def make_chapter_info(data: Dict[str, Any]) -> ChapterInfo:
    """从爬虫返回的字典创建 ChapterInfo 模型"""
    return ChapterInfo.from_dict(data)


def make_chapter_list(data_list: List[Dict[str, Any]]) -> List[ChapterInfo]:
    """批量创建章节模型列表"""
    return [ChapterInfo.from_dict(d) for d in data_list]
