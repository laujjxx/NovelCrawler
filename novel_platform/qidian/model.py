"""
起点中文网数据模型
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class NovelInfo:
    """小说基本信息（排行榜级别）"""
    book_id: str = ""
    title: str = ""
    author: str = ""
    category: str = ""  # 分类/类型
    word_count: int = 0  # 总字数
    latest_chapter: str = ""  # 最新章节名
    rank: int = 0  # 排名
    rank_type: str = ""  # 榜单类型
    cover_url: str = ""  # 封面图URL
    book_url: str = ""  # 小说链接
    description: str = ""  # 简介（排行榜可能截断）
    is_serializing: bool = True  # 是否连载中
    monthly_ticket: int = 0  # 月票数（月票榜特有）
    recommend_ticket: int = 0  # 推荐票数
    collection_count: int = 0  # 收藏数

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NovelDetail:
    """小说详细信息"""
    book_id: str = ""
    title: str = ""
    author: str = ""
    category: str = ""
    sub_category: str = ""  # 子分类
    tags: List[str] = field(default_factory=list)  # 标签
    word_count: int = 0
    description: str = ""  # 完整简介
    status: str = ""  # 连载中 / 完结
    score: float = 0.0  # 评分
    click_count: int = 0  # 总点击
    recommend_count: int = 0  # 总推荐
    collection_count: int = 0  # 总收藏
    fan_value: int = 0  # 粉丝值
    first_chapter_url: str = ""  # 第一章链接
    latest_chapter: str = ""
    latest_chapter_url: str = ""
    update_time: str = ""  # 最后更新时间
    create_time: str = ""  # 首发时间
    book_url: str = ""
    cover_url: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ChapterInfo:
    """章节信息"""
    chapter_id: str = ""
    title: str = ""
    volume_name: str = ""  # 所属卷名
    word_count: int = 0
    is_vip: bool = False  # 是否VIP章节
    update_time: str = ""
    url: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
