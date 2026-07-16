"""
番茄小说爬虫
使用番茄公开 API 获取排行榜和书籍详情
"""
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from base.base_crawler import BaseCrawler
from config.base_config import MAX_NOVELS_PER_RANK, REQUEST_DELAY
from tools.utils import async_sleep, clean_text, setup_logger

logger = setup_logger("fanqie_crawler")

# 番茄 API 端点
FANQIE_API_RANK = "https://fanqienovel.com/api/rank/list"
FANQIE_API_BOOK = "https://fanqienovel.com/api/book/info"
FANQIE_PAGE_URL = "https://fanqienovel.com/page/{book_id}"

# 番茄排行榜类型
FANQIE_RANK_TYPES = {
    "热门榜": "hot",
    "推荐榜": "recommend",
}


class FanqieCrawler(BaseCrawler):
    """番茄小说爬虫 — API 模式（不需要浏览器）"""

    platform_name = "fanqie"

    def __init__(self):
        super().__init__(use_browser=False)

    def _default_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/16.0 Mobile/15E148 Safari/604.1"
            ),
            "Referer": "https://fanqienovel.com/",
        }

    def get_rank_types(self) -> Dict[str, str]:
        return FANQIE_RANK_TYPES

    # ==================== 排行榜爬取 ====================

    async def crawl_rank_list(
        self, rank_type: str = "hot", page_num: int = 1
    ) -> List[Dict[str, Any]]:
        """爬取番茄排行榜"""
        novels = []
        self.logger.info(f"正在爬取番茄排行榜 [{rank_type}]")

        try:
            resp = await self._http_client.get(FANQIE_API_RANK)
            if resp.status_code == 200:
                data = resp.json()
                books = data.get("data", {}).get("list", [])
                for idx, book in enumerate(books, 1):
                    novel = self._parse_rank_book(book, rank_type, idx)
                    if novel.get("title"):
                        novels.append(novel)
                self.logger.info(f"排行榜获取到 {len(novels)} 本小说")
            else:
                self.logger.warning(f"排行榜 API 返回: {resp.status_code}")
        except httpx.TimeoutException as e:
            self.logger.error(f"排行榜请求超时: {e}")
        except httpx.HTTPStatusError as e:
            self.logger.error(f"排行榜 API 错误 [{e.response.status_code}]: {e}")
        except Exception as e:
            self.logger.error(f"排行榜请求失败: {e}")

        return novels[:MAX_NOVELS_PER_RANK]

    def _parse_rank_book(
        self, book: dict, rank_type: str, rank: int
    ) -> Dict[str, Any]:
        """解析排行榜书籍数据"""
        book_id = str(book.get("bookId", ""))
        return {
            "book_id": book_id,
            "title": book.get("bookName", ""),
            "author": book.get("author", ""),
            "description": book.get("abstract", ""),
            "cover_url": book.get("thumbUri", ""),
            "rank": rank,
            "rank_type": rank_type,
            "book_url": f"https://fanqienovel.com/page/{book_id}",
        }

    # ==================== 详情爬取 ====================

    async def crawl_novel_detail(self, book_id: str) -> Dict[str, Any]:
        """获取小说详情"""
        detail = {}
        url = f"{FANQIE_API_BOOK}?bookId={book_id}"
        self.logger.info(f"正在获取详情: {book_id}")

        try:
            resp = await self._http_client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                info = data.get("data", {})
                if info:
                    detail = self._parse_detail(info)
                    self.logger.info(
                        f"详情获取完成: {detail.get('title', book_id)}"
                    )
            else:
                self.logger.warning(f"详情 API 返回: {resp.status_code}")
        except httpx.TimeoutException as e:
            self.logger.error(f"详情请求超时 [{book_id}]: {e}")
        except httpx.HTTPStatusError as e:
            self.logger.error(
                f"详情 API 错误 [{e.response.status_code}][{book_id}]: {e}"
            )
        except Exception as e:
            self.logger.error(f"详情请求失败 [{book_id}]: {e}")

        # 补充页面数据
        if not detail.get("description"):
            try:
                page_data = await self._crawl_page(book_id)
                detail.update(
                    {k: v for k, v in page_data.items() if v and not detail.get(k)}
                )
            except Exception:
                pass

        return detail

    def _parse_detail(self, info: dict) -> Dict[str, Any]:
        """解析详情 API 数据"""
        # 字数
        word_num = info.get("wordNumber", 0)
        if isinstance(word_num, str):
            m = re.search(r"([\d.]+)\s*万", word_num)
            if m:
                word_num = int(float(m.group(1)) * 10000)
            else:
                m2 = re.search(r"[\d.]+", word_num)
                word_num = int(float(m2.group(0))) if m2 else 0

        # 分类
        category = info.get("category", "")
        category_v2 = info.get("categoryV2", "")

        # 状态
        status_raw = info.get("status", "")
        creation_status = info.get("creationStatus", "")
        if (
            "完结" in str(status_raw)
            or "完结" in str(creation_status)
            or info.get("completeCategory")
        ):
            status = "完结"
        else:
            status = "连载中"

        # 更新时间
        last_publish = info.get("lastPublishTime", "")
        if last_publish and str(last_publish).isdigit():
            try:
                last_publish = datetime.fromtimestamp(
                    int(last_publish)
                ).strftime("%Y-%m-%d %H:%M")
            except (ValueError, OSError):
                pass

        return {
            "book_id": str(info.get("bookId", "")),
            "title": info.get("bookName", ""),
            "author": info.get("authorName", info.get("author", "")),
            "author_id": str(info.get("authorId", "")),
            "category": (
                category
                or (category_v2.split("/")[1] if "/" in str(category_v2) else "")
            ),
            "sub_category": (
                category_v2.split("/")[-1] if "/" in str(category_v2) else ""
            ),
            "word_count": int(word_num) if word_num else 0,
            "description": info.get("abstract", info.get("description", "")),
            "status": status,
            "read_count": info.get("readCount", 0),
            "latest_chapter": info.get("lastChapterTitle", ""),
            "update_time": last_publish,
            "cover_url": info.get("thumbUri", info.get("thumbUrl", "")),
            "book_url": f"https://fanqienovel.com/page/{info.get('bookId', '')}",
        }

    async def _crawl_page(self, book_id: str) -> Dict[str, Any]:
        """从页面 HTML 提取 JSON-LD 结构化数据"""
        result = {}
        url = FANQIE_PAGE_URL.format(book_id=book_id)
        try:
            resp = await self._http_client.get(url)
            if resp.status_code == 200:
                html = resp.text
                m = re.search(
                    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
                    html,
                    re.DOTALL,
                )
                if m:
                    try:
                        ld = json.loads(m.group(1))
                        if ld.get("author"):
                            authors = ld["author"]
                            if isinstance(authors, list) and authors:
                                result["author"] = authors[0].get("name", "")
                        if ld.get("description"):
                            result["description"] = clean_text(ld["description"])
                    except (json.JSONDecodeError, KeyError):
                        pass
        except (httpx.TimeoutException, httpx.HTTPStatusError):
            self.logger.debug(f"页面爬取失败: {book_id}")
        except Exception as e:
            self.logger.debug(f"页面爬取异常 [{book_id}]: {e}")
        return result

    # ==================== 章节爬取 ====================

    async def crawl_chapter_list(
        self, book_id: str, max_chapters: int = 100
    ) -> List[Dict[str, Any]]:
        """
        番茄小说暂未提供公开的章节目录 API
        返回空列表，AI 分析依赖详情数据
        """
        self.logger.info(f"番茄平台暂不支持章节目录获取 [{book_id}]")
        return []
