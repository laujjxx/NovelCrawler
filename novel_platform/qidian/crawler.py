"""
起点中文网排行榜爬虫
支持两种模式：
1. API 模式（默认）— 直接调用起点内部 API 和移动版页面，速度快
2. 浏览器模式 — 使用 Playwright，需要手动过验证码
"""
import asyncio
import json
import re
from typing import Any, Dict, List, Optional

import httpx
from playwright.async_api import Page

from base.base_crawler import BaseCrawler
from config.base_config import (
    MAX_CHAPTERS,
    MAX_NOVELS_PER_RANK,
    QIDIAN_BASE_URL,
    QIDIAN_RANK_URL,
    QIDIAN_RANK_TYPES,
    REQUEST_DELAY,
)
from novel_platform.qidian.model import ChapterInfo, NovelDetail, NovelInfo
from novel_platform.qidian.parser import (
    parse_chapter_list,
    parse_novel_detail,
    parse_rank_page,
)
from tools.utils import async_sleep, clean_text, setup_logger

logger = setup_logger("qidian_crawler")

# 起点内部 API 端点
QIDIAN_RANK_API = "https://www.qidian.com/majax/rank/{rank_type}"
QIDIAN_BOOK_API = "https://m.qidian.com/majax/book/info/{book_id}"
QIDIAN_CATALOG_API = "https://m.qidian.com/majax/book/category/{book_id}"


class QidianCrawler(BaseCrawler):
    """起点中文网爬虫"""

    platform_name = "qidian"

    def __init__(self, use_browser: bool = False):
        """
        Args:
            use_browser: 是否使用浏览器模式（需要手动过验证码）
        """
        super().__init__(use_browser=use_browser)

    def _default_headers(self) -> Dict[str, str]:
        """起点移动端 User-Agent，反爬较弱"""
        return {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/16.0 Mobile/15E148 Safari/604.1"
            ),
            "Referer": "https://m.qidian.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def get_rank_types(self) -> Dict[str, str]:
        return QIDIAN_RANK_TYPES

    # ==================== 排行榜爬取 ====================

    async def crawl_rank_list(
        self, rank_type: str, page_num: int = 1
    ) -> List[Dict[str, Any]]:
        """爬取排行榜"""
        if self.use_browser:
            return await self._crawl_rank_browser(rank_type, page_num)
        return await self._crawl_rank_web(rank_type, page_num)

    def _parse_book_data(
        self, book: dict, rank_type: str, rank: int
    ) -> Dict[str, Any]:
        """解析 API / 移动版页面返回的书籍数据（内部使用）"""
        book_id = str(book.get("bookId", book.get("bid", "")))

        # 字数：可能是数字或带"万字"的字符串
        wc_raw = book.get("wordCount", book.get("cnt", 0))
        if isinstance(wc_raw, str):
            m = re.search(r"([\d.]+)\s*万", wc_raw)
            if m:
                word_count = int(float(m.group(1)) * 10000)
            else:
                m2 = re.search(r"([\d.]+)", wc_raw)
                word_count = int(float(m2.group(1))) if m2 else 0
        else:
            word_count = int(wc_raw) if wc_raw else 0

        # 排名数值（如 "13.06万月票"）
        rank_cnt = book.get("rankCnt", "")

        return {
            "book_id": book_id,
            "title": re.sub(
                r"<[^>]+>",
                "",
                book.get("bookName", book.get("bName", "")),
            ).strip(),
            "author": re.sub(
                r"<[^>]+>",
                "",
                book.get("authorName", book.get("bAuth", "")),
            ).strip(),
            "category": book.get("cat", book.get("catName", "")),
            "sub_category": book.get("subCat", ""),
            "word_count": word_count,
            "latest_chapter": book.get("lastChapter", book.get("lcName", "")),
            "rank": book.get("rankNum", rank),
            "rank_type": rank_type,
            "rank_count": rank_cnt,
            "description": book.get("desc", book.get("introduction", "")),
            "book_url": f"https://book.qidian.com/info/{book_id}/",
            "cover_url": book.get("coverUrl", book.get("cover", "")),
            "is_serializing": book.get("bookStatus", "") == "连载",
            "monthly_ticket": book.get("monthTicket", 0),
            "recommend_ticket": book.get("recTicket", 0),
            "collection_count": book.get("collectCount", 0),
        }

    async def _crawl_rank_web(
        self, rank_type: str, page_num: int = 1
    ) -> List[Dict[str, Any]]:
        """
        通过爬取移动版网页获取排行榜数据
        移动版页面在 <script> 标签中内嵌 JSON 数据，多层降级解析
        """
        novels = []
        url = f"https://m.qidian.com/rank/{rank_type}"
        if page_num > 1:
            url += f"/page/{page_num}"

        self.logger.info(f"正在爬取移动版网页: {url}")

        try:
            resp = await self._http_client.get(url)
            if resp.status_code != 200:
                self.logger.warning(f"网页返回状态码: {resp.status_code}")
                return novels

            html = resp.text

            # 三层降级解析
            # 方式1: __INITIAL_STATE__ JSON
            novels = self._parse_from_initial_state(html, rank_type)
            # 方式2: 移动版新版 pageProps JSON
            if not novels:
                novels = self._parse_mobile_page_data(html, rank_type)
            # 方式3: 正则提取 HTML 链接
            if not novels:
                novels = self._parse_html_books(html, rank_type)

            self.logger.info(f"网页解析到 {len(novels)} 本小说 (rank_type={rank_type})")
        except httpx.TimeoutException as e:
            self.logger.error(f"网页请求超时 [{rank_type}]: {e}")
        except httpx.HTTPStatusError as e:
            self.logger.error(
                f"网页请求错误 [{e.response.status_code}][{rank_type}]: {e}"
            )
        except Exception as e:
            self.logger.error(f"网页请求失败 [{rank_type}]: {e}")

        return novels[:MAX_NOVELS_PER_RANK]

    def _parse_from_initial_state(
        self, html: str, rank_type: str
    ) -> List[Dict[str, Any]]:
        """从 __INITIAL_STATE__ 解析书籍数据"""
        novels = []
        json_match = re.search(
            r"window\.__INITIAL_STATE__\s*=\s*({.*?});?\s*</script>",
            html,
            re.DOTALL,
        )
        if not json_match:
            return novels

        try:
            state = json.loads(json_match.group(1))
            books = state.get("rankBooks", {}).get("records", [])
            for idx, book in enumerate(books, 1):
                novel = self._parse_book_data(book, rank_type, idx)
                if novel.get("title"):
                    novels.append(novel)
        except json.JSONDecodeError:
            self.logger.warning("__INITIAL_STATE__ JSON 解析失败")
        return novels

    def _parse_mobile_page_data(
        self, html: str, rank_type: str
    ) -> List[Dict[str, Any]]:
        """
        解析起点移动版页面内嵌的 JSON 数据
        数据格式: <script>{"pageContext":..., "pageProps": {"pageData": {"records": [...]}}}</script>
        """
        novels = []
        scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.DOTALL)
        for script in reversed(scripts):
            script = script.strip()
            if not script.startswith("{"):
                continue
            try:
                data = json.loads(script)
                page_data = (
                    data.get("pageContext", {})
                    .get("pageProps", {})
                    .get("pageData", {})
                )
                records = page_data.get("records", [])
                if records:
                    for idx, book in enumerate(records, 1):
                        novel = self._parse_book_data(book, rank_type, idx)
                        if novel.get("title"):
                            novels.append(novel)
                    break
            except json.JSONDecodeError:
                continue
        return novels

    def _parse_html_books(self, html: str, rank_type: str) -> List[Dict[str, Any]]:
        """从 HTML 中用正则提取书籍信息（最终降级方案）"""
        novels = []
        pattern = (
            r'<a[^>]*href="[^"]*book\.qidian\.com/info/(\d+)/?"[^>]*>(.*?)</a>'
        )
        matches = re.findall(pattern, html, re.DOTALL)
        seen = set()
        for idx, (book_id, title_html) in enumerate(matches, 1):
            if book_id in seen:
                continue
            seen.add(book_id)
            title = re.sub(r"<[^>]+>", "", title_html).strip()
            if not title:
                continue
            novels.append(
                {
                    "book_id": book_id,
                    "title": title,
                    "rank": idx,
                    "rank_type": rank_type,
                    "book_url": f"https://book.qidian.com/info/{book_id}/",
                }
            )
        return novels

    # ==================== 浏览器模式排行 ====================

    async def _crawl_rank_browser(
        self, rank_type: str, page_num: int = 1
    ) -> List[Dict[str, Any]]:
        """浏览器模式爬取排行榜"""
        page = await self._browser.get_page()
        url = f"{QIDIAN_RANK_URL}{rank_type}/"
        if page_num > 1:
            url += f"page/{page_num}/"

        self.logger.info(f"正在访问排行榜: {url}")

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
        except Exception as e:
            self.logger.error(f"页面加载失败: {e}")
            return []

        novels_raw = await parse_rank_page(page, rank_type)
        self.logger.info(f"从 [{rank_type}] 榜解析到 {len(novels_raw)} 本小说")
        return novels_raw[:MAX_NOVELS_PER_RANK]

    # ==================== 详情爬取 ====================

    async def crawl_novel_detail(self, book_id: str) -> Dict[str, Any]:
        """爬取小说详情"""
        if self.use_browser:
            return await self._crawl_detail_browser(book_id)
        return await self._crawl_detail_web(book_id)

    async def _crawl_detail_web(self, book_id: str) -> Dict[str, Any]:
        """通过移动版网页获取小说详情（多层降级）"""
        detail = {}
        url = f"https://m.qidian.com/book/{book_id}/"
        self.logger.info(f"正在获取小说详情: {url}")

        try:
            resp = await self._http_client.get(url)
            if resp.status_code != 200:
                self.logger.warning(f"详情页返回状态码: {resp.status_code}")
                return detail

            html = resp.text

            # 方式1: __INITIAL_STATE__
            json_match = re.search(
                r"window\.__INITIAL_STATE__\s*=\s*({.*?});?\s*</script>",
                html,
                re.DOTALL,
            )
            if json_match:
                try:
                    state = json.loads(json_match.group(1))
                    book_info = state.get("bookInfo", state.get("book", {}))
                    detail = self._parse_detail_from_api(book_info, book_id)
                except json.JSONDecodeError:
                    pass

            # 方式2: 移动版 pageProps JSON
            if not detail:
                scripts = re.findall(
                    r"<script[^>]*>(.*?)</script>", html, re.DOTALL
                )
                for script in reversed(scripts):
                    script = script.strip()
                    if not script.startswith("{"):
                        continue
                    try:
                        data = json.loads(script)
                        page_data = (
                            data.get("pageContext", {})
                            .get("pageProps", {})
                            .get("pageData", {})
                        )
                        book_info = page_data.get("bookInfo", {})
                        if book_info:
                            detail = self._parse_mobile_detail(
                                book_info, page_data, book_id
                            )
                            break
                    except json.JSONDecodeError:
                        continue

            # 方式3: HTML 正则回退
            if not detail:
                detail = self._parse_detail_from_html(html, book_id)

            self.logger.info(f"详情获取完成: {detail.get('title', book_id)}")
        except httpx.TimeoutException as e:
            self.logger.error(f"详情请求超时 [{book_id}]: {e}")
        except httpx.HTTPStatusError as e:
            self.logger.error(
                f"详情请求错误 [{e.response.status_code}][{book_id}]: {e}"
            )
        except Exception as e:
            self.logger.error(f"详情获取失败 [{book_id}]: {e}")

        return detail

    def _parse_word_count(self, wc_raw) -> int:
        """统一字数解析逻辑"""
        if isinstance(wc_raw, str):
            m = re.search(r"([\d.]+)\s*万", wc_raw)
            if m:
                return int(float(m.group(1)) * 10000)
            m2 = re.search(r"([\d.]+)", wc_raw)
            return int(float(m2.group(1))) if m2 else 0
        return int(wc_raw) if wc_raw else 0

    def _parse_mobile_detail(
        self, book_info: dict, page_data: dict, book_id: str
    ) -> Dict[str, Any]:
        """解析移动版详情页的 bookInfo 数据"""
        if not book_info:
            return {}

        # 标签
        tags = []
        for label in book_info.get("bookLabels", []):
            if isinstance(label, dict):
                tags.append(label.get("tagName", label.get("name", "")))
            elif isinstance(label, str):
                tags.append(label)

        upd_info = page_data.get("updInfo", {})

        return {
            "book_id": book_id,
            "title": book_info.get("bookName", book_info.get("bName", "")),
            "author": book_info.get("authorName", book_info.get("bAuth", "")),
            "category": book_info.get("chanName", book_info.get("cat", "")),
            "sub_category": book_info.get("subCateName", book_info.get("subCat", "")),
            "tags": tags,
            "word_count": self._parse_word_count(
                book_info.get("wordCount", book_info.get("cnt", 0))
            ),
            "description": re.sub(
                r"<[^>]+>",
                "",
                book_info.get("desc", book_info.get("introduction", "")),
            ).strip(),
            "status": book_info.get(
                "actionStatus", book_info.get("bookStatus", "")
            ),
            "score": book_info.get("score", 0),
            "click_count": book_info.get("clickTotal", 0),
            "recommend_count": book_info.get("recomAll", 0),
            "collection_count": book_info.get("collectCount", 0),
            "latest_chapter": upd_info.get("updChapterName", ""),
            "update_time": book_info.get("updTime", ""),
            "book_url": f"https://book.qidian.com/info/{book_id}/",
        }

    def _parse_detail_from_api(self, info: dict, book_id: str) -> Dict[str, Any]:
        """从 API 数据解析详情"""
        if not info:
            return {}
        return {
            "book_id": book_id,
            "title": re.sub(
                r"<[^>]+>",
                "",
                info.get("bookName", info.get("bName", "")),
            ).strip(),
            "author": re.sub(
                r"<[^>]+>",
                "",
                info.get("authorName", info.get("bAuth", "")),
            ).strip(),
            "category": info.get("cat", info.get("catName", "")),
            "sub_category": info.get("subCat", ""),
            "tags": info.get("tags", []),
            "word_count": info.get("wordCount", 0),
            "description": re.sub(
                r"<[^>]+>",
                "",
                info.get("desc", info.get("introduction", "")),
            ).strip(),
            "status": info.get("bookStatus", ""),
            "score": info.get("score", 0),
            "click_count": info.get("clickCount", 0),
            "recommend_count": info.get("recCount", 0),
            "collection_count": info.get("collectCount", 0),
            "latest_chapter": info.get("lastChapter", ""),
            "update_time": info.get("updateTime", ""),
            "book_url": f"https://book.qidian.com/info/{book_id}/",
        }

    def _parse_detail_from_html(self, html: str, book_id: str) -> Dict[str, Any]:
        """从 HTML 正则解析详情（降级方案）"""
        detail = {
            "book_id": book_id,
            "book_url": f"https://book.qidian.com/info/{book_id}/",
        }

        # 书名
        m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL)
        if m:
            detail["title"] = re.sub(r"<[^>]+>", "", m.group(1)).strip()

        # 作者
        m = re.search(
            r'class="[^"]*author[^"]*"[^>]*>.*?<a[^>]*>(.*?)</a>',
            html,
            re.DOTALL,
        )
        if m:
            detail["author"] = clean_text(m.group(1))

        # 简介
        m = re.search(
            r'class="[^"]*intro[^"]*"[^>]*>(.*?)</(?:div|p|section)',
            html,
            re.DOTALL,
        )
        if m:
            detail["description"] = clean_text(
                re.sub(r"<[^>]+>", "", m.group(1))
            )

        # 字数
        m = re.search(r"([\d.]+)\s*万字", html)
        if m:
            detail["word_count"] = int(float(m.group(1)) * 10000)

        return detail

    # ==================== 浏览器模式详情 ====================

    async def _crawl_detail_browser(self, book_id: str) -> Dict[str, Any]:
        """浏览器模式获取详情"""
        page = await self._browser.get_page()
        url = f"https://book.qidian.com/info/{book_id}/"

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(1500)
        except Exception as e:
            self.logger.error(f"详情页加载失败 [{book_id}]: {e}")
            return {}

        detail = await parse_novel_detail(page)
        detail["book_id"] = book_id
        detail["book_url"] = url
        return detail

    # ==================== 章节目录 ====================

    async def crawl_chapter_list(
        self, book_id: str, max_chapters: int = MAX_CHAPTERS
    ) -> List[Dict[str, Any]]:
        """爬取章节目录"""
        if self.use_browser:
            return await self._crawl_chapters_browser(book_id, max_chapters)
        return await self._crawl_chapters_web(book_id, max_chapters)

    async def _crawl_chapters_web(
        self, book_id: str, max_chapters: int
    ) -> List[Dict[str, Any]]:
        """通过移动版网页获取章节目录"""
        chapters = []
        url = f"https://m.qidian.com/book/{book_id}/catalog/"
        self.logger.info(f"正在获取章节目录: {book_id}")

        try:
            resp = await self._http_client.get(url)
            if resp.status_code != 200:
                self.logger.warning(f"目录页返回状态码: {resp.status_code}")
                return chapters

            html = resp.text

            # __INITIAL_STATE__ 方式
            json_match = re.search(
                r"window\.__INITIAL_STATE__\s*=\s*({.*?});?\s*</script>",
                html,
                re.DOTALL,
            )
            if json_match:
                try:
                    state = json.loads(json_match.group(1))
                    volumes = state.get("catalogData", state.get("volumes", []))
                    if isinstance(volumes, dict):
                        volumes = volumes.get("volumes", [])
                    for vol in volumes:
                        vol_name = vol.get("volumeName", vol.get("vName", ""))
                        ch_list = vol.get("chapters", vol.get("cs", []))
                        for ch in ch_list:
                            if len(chapters) >= max_chapters:
                                break
                            chapters.append(
                                {
                                    "chapter_id": str(
                                        ch.get("chapterId", ch.get("cid", ""))
                                    ),
                                    "title": ch.get(
                                        "chapterName", ch.get("cName", "")
                                    ),
                                    "volume_name": vol_name,
                                    "word_count": ch.get(
                                        "wordCount", ch.get("cnt", 0)
                                    ),
                                    "is_vip": ch.get("isVip", 0) == 1,
                                    "url": (
                                        "https://read.qidian.com/chapter/"
                                        f"{ch.get('chapterId', ch.get('cid', ''))}/"
                                    ),
                                }
                            )
                except json.JSONDecodeError:
                    pass

            # 正则回退
            if not chapters:
                chapters = self._parse_chapters_from_html(html, max_chapters)

            self.logger.info(f"获取到 {len(chapters)} 个章节")
        except httpx.TimeoutException as e:
            self.logger.error(f"目录请求超时 [{book_id}]: {e}")
        except httpx.HTTPStatusError as e:
            self.logger.error(
                f"目录请求错误 [{e.response.status_code}][{book_id}]: {e}"
            )
        except Exception as e:
            self.logger.error(f"目录获取失败 [{book_id}]: {e}")

        return chapters[:max_chapters]

    def _parse_chapters_from_html(
        self, html: str, max_chapters: int
    ) -> List[Dict[str, Any]]:
        """从 HTML 正则提取章节（降级方案）"""
        chapters = []
        pattern = r'<a[^>]*href="[^"]*chapter/(\d+)/?"[^>]*>(.*?)</a>'
        matches = re.findall(pattern, html, re.DOTALL)
        for ch_id, title_html in matches[:max_chapters]:
            title = re.sub(r"<[^>]+>", "", title_html).strip()
            if title:
                chapters.append(
                    {
                        "chapter_id": ch_id,
                        "title": title,
                        "volume_name": "",
                        "url": f"https://read.qidian.com/chapter/{ch_id}/",
                        "is_vip": False,
                    }
                )
        return chapters

    async def _crawl_chapters_browser(
        self, book_id: str, max_chapters: int
    ) -> List[Dict[str, Any]]:
        """浏览器模式获取章节"""
        page = await self._browser.get_page()
        url = f"https://book.qidian.com/info/{book_id}/"

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(1500)
        except Exception as e:
            self.logger.error(f"目录页加载失败 [{book_id}]: {e}")
            return []

        return await parse_chapter_list(page, max_chapters)
