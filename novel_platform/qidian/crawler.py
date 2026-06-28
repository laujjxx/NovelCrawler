"""
起点中文网排行榜爬虫
支持两种模式：
1. API 模式（默认）— 直接调用起点内部 API，速度快
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
        super().__init__()
        self.use_browser = use_browser
        self._http_client: Optional[httpx.AsyncClient] = None

    async def start(self) -> None:
        """启动爬虫"""
        if self.use_browser:
            await super().start()
        else:
            # 使用移动端 User-Agent，起点移动端反爬较弱
            self._http_client = httpx.AsyncClient(
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                        "Version/16.0 Mobile/15E148 Safari/604.1"
                    ),
                    "Referer": "https://m.qidian.com/",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
                timeout=30.0,
                follow_redirects=True,
            )
        self.logger.info(f"[{self.platform_name}] 爬虫已启动 (模式: {'浏览器' if self.use_browser else 'API'})")

    async def close(self) -> None:
        """关闭爬虫"""
        if self.use_browser:
            await super().close()
        if self._http_client:
            await self._http_client.aclose()
        self.logger.info(f"[{self.platform_name}] 爬虫已关闭")

    def get_rank_types(self) -> Dict[str, str]:
        return QIDIAN_RANK_TYPES

    async def crawl_rank_list(
        self, rank_type: str, page_num: int = 1
    ) -> List[Dict[str, Any]]:
        """爬取排行榜"""
        if self.use_browser:
            return await self._crawl_rank_browser(rank_type, page_num)
        return await self._crawl_rank_api(rank_type, page_num)

    async def _crawl_rank_api(
        self, rank_type: str, page_num: int = 1
    ) -> List[Dict[str, Any]]:
        """
        爬取排行榜 — 直接爬取移动版网页（最可靠的方式）
        移动版页面内嵌 JSON 数据，结构清晰
        """
        self.logger.info(f"正在爬取排行榜 [{rank_type}] page={page_num}")
        novels = await self._crawl_rank_web(rank_type, page_num)
        return novels[:MAX_NOVELS_PER_RANK]

    def _parse_api_book(
        self, book: dict, rank_type: str, rank: int
    ) -> Dict[str, Any]:
        """解析 API / 移动版页面返回的书籍数据"""
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
            "title": re.sub(r'<[^>]+>', '', book.get("bookName", book.get("bName", ""))).strip(),
            "author": re.sub(r'<[^>]+>', '', book.get("authorName", book.get("bAuth", ""))).strip(),
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
        移动版页面在 <script> 标签中内嵌 JSON 数据
        """
        novels = []
        url = f"https://m.qidian.com/rank/{rank_type}"
        if page_num > 1:
            url += f"/page/{page_num}"

        self.logger.info(f"正在爬取移动版网页: {url}")

        try:
            resp = await self._http_client.get(url)
            if resp.status_code == 200:
                html = resp.text

                # 方式1: 查找 __INITIAL_STATE__
                json_match = re.search(
                    r'window\.__INITIAL_STATE__\s*=\s*({.*?});?\s*</script>',
                    html, re.DOTALL
                )
                if json_match:
                    try:
                        state = json.loads(json_match.group(1))
                        books = (state.get("rankBooks", {})
                                     .get("records", []))
                        for idx, book in enumerate(books, 1):
                            novel = self._parse_api_book(book, rank_type, idx)
                            if novel.get("title"):
                                novels.append(novel)
                    except json.JSONDecodeError:
                        self.logger.warning("JSON 解析失败")

                # 方式2: 移动版新版 — 数据在最后一个 <script> 中
                if not novels:
                    novels = self._parse_mobile_page_data(html, rank_type)

                # 方式3: 正则提取链接
                if not novels:
                    novels = self._parse_html_books(html, rank_type)

                self.logger.info(f"网页解析到 {len(novels)} 本小说")
            else:
                self.logger.warning(f"网页返回状态码: {resp.status_code}")
        except Exception as e:
            self.logger.error(f"网页请求失败: {e}")

        return novels

    def _parse_mobile_page_data(
        self, html: str, rank_type: str
    ) -> List[Dict[str, Any]]:
        """
        解析起点移动版页面内嵌的 JSON 数据
        数据格式: <script>{"pageContext":..., "pageProps": {"pageData": {"records": [...]}}}</script>
        """
        novels = []
        # 找到最后一个 <script> 标签中的 JSON
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        for script in reversed(scripts):
            script = script.strip()
            if not script.startswith('{'):
                continue
            try:
                data = json.loads(script)
                page_data = (data.get("pageContext", {})
                                  .get("pageProps", {})
                                  .get("pageData", {}))
                records = page_data.get("records", [])
                if records:
                    for idx, book in enumerate(records, 1):
                        novel = self._parse_api_book(book, rank_type, idx)
                        if novel.get("title"):
                            novels.append(novel)
                    break
            except json.JSONDecodeError:
                continue
        return novels

    def _parse_html_books(self, html: str, rank_type: str) -> List[Dict[str, Any]]:
        """从 HTML 中用正则提取书籍信息"""
        novels = []
        # 匹配 book.qidian.com/info/xxx/ 链接
        pattern = r'<a[^>]*href="[^"]*book\.qidian\.com/info/(\d+)/?"[^>]*>(.*?)</a>'
        matches = re.findall(pattern, html, re.DOTALL)
        seen = set()
        for idx, (book_id, title_html) in enumerate(matches, 1):
            if book_id in seen:
                continue
            seen.add(book_id)
            title = re.sub(r'<[^>]+>', '', title_html).strip()
            if not title:
                continue
            novels.append({
                "book_id": book_id,
                "title": title,
                "rank": idx,
                "rank_type": rank_type,
                "book_url": f"https://book.qidian.com/info/{book_id}/",
            })
        return novels

    async def _crawl_rank_browser(
        self, rank_type: str, page_num: int = 1
    ) -> List[Dict[str, Any]]:
        """浏览器模式爬取排行榜"""
        page = await self.browser.get_page()
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
        novels_raw = novels_raw[:MAX_NOVELS_PER_RANK]
        self.logger.info(f"从 [{rank_type}] 榜解析到 {len(novels_raw)} 本小说")
        return novels_raw

    async def crawl_novel_detail(self, book_id: str) -> Dict[str, Any]:
        """爬取小说详情"""
        if self.use_browser:
            return await self._crawl_detail_browser(book_id)
        return await self._crawl_detail_api(book_id)

    async def _crawl_detail_api(self, book_id: str) -> Dict[str, Any]:
        """通过 API 获取小说详情"""
        detail = {}

        # 尝试移动版页面
        url = f"https://m.qidian.com/book/{book_id}/"
        self.logger.info(f"正在获取小说详情: {url}")

        try:
            resp = await self._http_client.get(url)
            if resp.status_code == 200:
                html = resp.text

                # 方式1: __INITIAL_STATE__
                json_match = re.search(
                    r'window\.__INITIAL_STATE__\s*=\s*({.*?});?\s*</script>',
                    html, re.DOTALL
                )
                if json_match:
                    try:
                        state = json.loads(json_match.group(1))
                        book_info = state.get("bookInfo", state.get("book", {}))
                        detail = self._parse_detail_from_api(book_info, book_id)
                    except json.JSONDecodeError:
                        pass

                # 方式2: 移动版页面内嵌 JSON（pageProps.pageData.bookInfo）
                if not detail:
                    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
                    for script in reversed(scripts):
                        script = script.strip()
                        if not script.startswith('{'):
                            continue
                        try:
                            data = json.loads(script)
                            page_data = (data.get("pageContext", {})
                                              .get("pageProps", {})
                                              .get("pageData", {}))
                            book_info = page_data.get("bookInfo", {})
                            if book_info:
                                detail = self._parse_mobile_detail(book_info, page_data, book_id)
                                break
                        except json.JSONDecodeError:
                            continue

                # 方式3: 从 HTML 正则解析
                if not detail:
                    detail = self._parse_detail_from_html(html, book_id)

                self.logger.info(f"详情获取完成: {detail.get('title', book_id)}")
        except Exception as e:
            self.logger.error(f"详情获取失败 [{book_id}]: {e}")

        return detail

    def _parse_mobile_detail(
        self, book_info: dict, page_data: dict, book_id: str
    ) -> Dict[str, Any]:
        """解析移动版详情页的 bookInfo 数据"""
        if not book_info:
            return {}

        # 字数解析
        wc_raw = book_info.get("wordCount", book_info.get("cnt", 0))
        if isinstance(wc_raw, str):
            m = re.search(r"([\d.]+)\s*万", wc_raw)
            if m:
                word_count = int(float(m.group(1)) * 10000)
            else:
                m2 = re.search(r"([\d.]+)", wc_raw)
                word_count = int(float(m2.group(1))) if m2 else 0
        else:
            word_count = int(wc_raw) if wc_raw else 0

        # 标签
        tags = []
        for label in book_info.get("bookLabels", []):
            if isinstance(label, dict):
                tags.append(label.get("tagName", label.get("name", "")))
            elif isinstance(label, str):
                tags.append(label)

        # 最新章节
        upd_info = page_data.get("updInfo", {})
        recent_chapters = page_data.get("recentChapters", [])

        return {
            "book_id": book_id,
            "title": book_info.get("bookName", book_info.get("bName", "")),
            "author": book_info.get("authorName", book_info.get("bAuth", "")),
            "category": book_info.get("chanName", book_info.get("cat", "")),
            "sub_category": book_info.get("subCateName", book_info.get("subCat", "")),
            "tags": tags,
            "word_count": word_count,
            "description": re.sub(r'<[^>]+>', '', book_info.get("desc", book_info.get("introduction", ""))).strip(),
            "status": book_info.get("actionStatus", book_info.get("bookStatus", "")),
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
            "title": re.sub(r'<[^>]+>', '', info.get("bookName", info.get("bName", ""))).strip(),
            "author": re.sub(r'<[^>]+>', '', info.get("authorName", info.get("bAuth", ""))).strip(),
            "category": info.get("cat", info.get("catName", "")),
            "sub_category": info.get("subCat", ""),
            "tags": info.get("tags", []),
            "word_count": info.get("wordCount", 0),
            "description": re.sub(r'<[^>]+>', '', info.get("desc", info.get("introduction", ""))).strip(),
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
        """从 HTML 解析详情"""
        detail = {"book_id": book_id, "book_url": f"https://book.qidian.com/info/{book_id}/"}

        # 书名
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
        if m:
            detail["title"] = re.sub(r'<[^>]+>', '', m.group(1)).strip()

        # 作者
        m = re.search(r'class="[^"]*author[^"]*"[^>]*>.*?<a[^>]*>(.*?)</a>', html, re.DOTALL)
        if m:
            detail["author"] = clean_text(m.group(1))

        # 简介
        m = re.search(r'class="[^"]*intro[^"]*"[^>]*>(.*?)</(?:div|p|section)', html, re.DOTALL)
        if m:
            detail["description"] = clean_text(re.sub(r'<[^>]+>', '', m.group(1)))

        # 字数
        m = re.search(r'([\d.]+)\s*万字', html)
        if m:
            detail["word_count"] = int(float(m.group(1)) * 10000)

        return detail

    async def _crawl_detail_browser(self, book_id: str) -> Dict[str, Any]:
        """浏览器模式获取详情"""
        page = await self.browser.get_page()
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

    async def crawl_chapter_list(
        self, book_id: str, max_chapters: int = MAX_CHAPTERS
    ) -> List[Dict[str, Any]]:
        """爬取章节目录"""
        if self.use_browser:
            return await self._crawl_chapters_browser(book_id, max_chapters)
        return await self._crawl_chapters_api(book_id, max_chapters)

    async def _crawl_chapters_api(
        self, book_id: str, max_chapters: int
    ) -> List[Dict[str, Any]]:
        """通过 API 获取章节目录"""
        chapters = []
        url = f"https://m.qidian.com/book/{book_id}/catalog/"
        self.logger.info(f"正在获取章节目录: {book_id}")

        try:
            resp = await self._http_client.get(url)
            if resp.status_code == 200:
                html = resp.text
                json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});?\s*</script>', html, re.DOTALL)
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
                                chapters.append({
                                    "chapter_id": str(ch.get("chapterId", ch.get("cid", ""))),
                                    "title": ch.get("chapterName", ch.get("cName", "")),
                                    "volume_name": vol_name,
                                    "word_count": ch.get("wordCount", ch.get("cnt", 0)),
                                    "is_vip": ch.get("isVip", 0) == 1,
                                    "url": f"https://read.qidian.com/chapter/{ch.get('chapterId', ch.get('cid', ''))}/",
                                })
                    except json.JSONDecodeError:
                        pass

                # 从 HTML 正则提取
                if not chapters:
                    chapters = self._parse_chapters_from_html(html, max_chapters)

                self.logger.info(f"获取到 {len(chapters)} 个章节")
        except Exception as e:
            self.logger.error(f"目录获取失败 [{book_id}]: {e}")

        return chapters[:max_chapters]

    def _parse_chapters_from_html(self, html: str, max_chapters: int) -> List[Dict[str, Any]]:
        """从 HTML 正则提取章节"""
        chapters = []
        pattern = r'<a[^>]*href="[^"]*chapter/(\d+)/?"[^>]*>(.*?)</a>'
        matches = re.findall(pattern, html, re.DOTALL)
        for ch_id, title_html in matches[:max_chapters]:
            title = re.sub(r'<[^>]+>', '', title_html).strip()
            if title:
                chapters.append({
                    "chapter_id": ch_id,
                    "title": title,
                    "volume_name": "",
                    "url": f"https://read.qidian.com/chapter/{ch_id}/",
                    "is_vip": False,
                })
        return chapters

    async def _crawl_chapters_browser(
        self, book_id: str, max_chapters: int
    ) -> List[Dict[str, Any]]:
        """浏览器模式获取章节"""
        page = await self.browser.get_page()
        url = f"https://book.qidian.com/info/{book_id}/"

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(1500)
        except Exception as e:
            self.logger.error(f"目录页加载失败 [{book_id}]: {e}")
            return []

        return await parse_chapter_list(page, max_chapters)

    async def crawl_full_novel(self, book_id: str) -> Dict[str, Any]:
        """爬取完整小说信息（详情 + 目录）"""
        detail = await self.crawl_novel_detail(book_id)
        chapters = await self.crawl_chapter_list(book_id)
        return {
            "detail": detail,
            "chapters": chapters,
            "chapter_count": len(chapters),
        }

    async def crawl_rank_with_details(
        self, rank_type: str, top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """爬取排行榜并获取 Top N 小说的详情"""
        novels = await self.crawl_rank_list(rank_type)
        if not novels:
            return []

        results = []
        for novel in novels[:top_n]:
            book_id = novel.get("book_id", "")
            if not book_id:
                results.append(novel)
                continue

            self.logger.info(
                f"正在获取详情 [{novel.get('rank', '?')}/{top_n}]: "
                f"{novel.get('title', book_id)}"
            )

            try:
                detail = await self.crawl_novel_detail(book_id)
                # 合并：详情覆盖排行榜数据，但保留排行榜中有而详情中没有的字段
                merged = {**novel}
                for k, v in detail.items():
                    if v or k not in merged:
                        merged[k] = v
                # 保留排行榜的字数（详情页可能没有）
                if not merged.get("word_count") and novel.get("word_count"):
                    merged["word_count"] = novel["word_count"]
                # 清理 HTML 标签
                if merged.get("description"):
                    merged["description"] = re.sub(r'<[^>]+>', '', merged["description"]).strip()
                    merged["description"] = re.sub(r'\s+', ' ', merged["description"]).strip()
                results.append(merged)
            except Exception as e:
                self.logger.warning(f"获取详情失败 [{book_id}]: {e}")
                results.append(novel)

            await async_sleep(REQUEST_DELAY)

        return results
