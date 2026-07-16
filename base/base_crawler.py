"""
爬虫基类 — 定义通用爬取流程，支持浏览器/API 双模式
"""
import abc
import asyncio
from typing import Any, Dict, List, Optional

import httpx

from config.base_config import MAX_CONCURRENCY, REQUEST_DELAY
from tools.utils import async_sleep, setup_logger


class BaseCrawler(abc.ABC):
    """
    爬虫基类
    子类需要实现:
        - platform_name: 平台名称
        - crawl_rank_list(): 爬取排行榜
        - crawl_novel_detail(): 爬取小说详情
        - crawl_chapter_list(): 爬取章节目录
    """

    platform_name: str = "base"

    def __init__(self, use_browser: bool = False):
        self.logger = setup_logger(self.__class__.__name__)
        self.use_browser = use_browser
        self._http_client: Optional[httpx.AsyncClient] = None
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
        # Playwright 浏览器管理器（仅在 use_browser=True 时初始化）
        self._browser = None

    async def start(self) -> None:
        """启动爬虫"""
        if self.use_browser:
            # 延迟导入，避免非浏览器模式也需要 Playwright
            from tools.browser import BrowserManager
            self._browser = BrowserManager(self.platform_name)
            await self._browser.start()
        self._http_client = httpx.AsyncClient(
            headers=self._default_headers(),
            timeout=30.0,
            follow_redirects=True,
        )
        self.logger.info(
            f"[{self.platform_name}] 爬虫已启动 (模式: {'浏览器' if self.use_browser else 'API'})"
        )

    async def close(self) -> None:
        """关闭爬虫"""
        try:
            if self._browser:
                await self._browser.close()
        except Exception as e:
            self.logger.warning(f"关闭浏览器失败: {e}")
        if self._http_client:
            await self._http_client.aclose()
        self.logger.info(f"[{self.platform_name}] 爬虫已关闭")

    def _default_headers(self) -> Dict[str, str]:
        """子类可重写以自定义请求头"""
        return {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/16.0 Mobile/15E148 Safari/604.1"
            ),
        }

    async def _throttled_request(self, coro):
        """带限流的请求包装"""
        async with self._semaphore:
            result = await coro
            await async_sleep(REQUEST_DELAY)
            return result

    # ==================== 抽象方法 ====================

    @abc.abstractmethod
    async def crawl_rank_list(
        self, rank_type: str, page_num: int = 1
    ) -> List[Dict[str, Any]]:
        """爬取排行榜"""
        raise NotImplementedError

    @abc.abstractmethod
    async def crawl_novel_detail(self, book_id: str) -> Dict[str, Any]:
        """爬取小说详情"""
        raise NotImplementedError

    @abc.abstractmethod
    async def crawl_chapter_list(
        self, book_id: str, max_chapters: int = 100
    ) -> List[Dict[str, Any]]:
        """爬取章节目录"""
        raise NotImplementedError

    # ==================== 共享方法 ====================

    def get_rank_types(self) -> Dict[str, str]:
        """返回该平台支持的榜单类型，子类可重写"""
        return {}

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
        """
        爬取排行榜并获取 Top N 小说的详情 —— 公共实现
        子类只需实现 crawl_rank_list 和 crawl_novel_detail
        """
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
                merged = self._merge_details(novel, detail)
                results.append(merged)
            except Exception as e:
                self.logger.warning(f"获取详情失败 [{book_id}]: {e}")
                results.append(novel)

            await async_sleep(REQUEST_DELAY)

        return results

    def _merge_details(
        self, novel: Dict[str, Any], detail: Dict[str, Any]
    ) -> Dict[str, Any]:
        """合并排行榜数据和详情数据"""
        import re

        merged = {**novel}
        for k, v in detail.items():
            if v or k not in merged:
                merged[k] = v
        # 保留排行榜的字数（详情页可能没有）
        if not merged.get("word_count") and novel.get("word_count"):
            merged["word_count"] = novel["word_count"]
        # 清理 HTML 标签
        if merged.get("description"):
            merged["description"] = re.sub(r"<[^>]+>", "", merged["description"]).strip()
            merged["description"] = re.sub(r"\s+", " ", merged["description"]).strip()
        return merged

    async def run(self, rank_types: Optional[List[str]] = None) -> Dict[str, List]:
        """
        运行完整爬取流程
        Args:
            rank_types: 要爬取的榜单类型列表，None 则爬取全部
        Returns:
            各榜单的数据 {rank_type: [novel_info, ...]}
        """
        await self.start()
        results = {}
        try:
            types = rank_types or list(self.get_rank_types().values())
            for rank_type in types:
                self.logger.info(f"开始爬取 [{rank_type}] 榜...")
                novels = await self.crawl_rank_list(rank_type)
                results[rank_type] = novels
                self.logger.info(f"[{rank_type}] 榜爬取完成, 共 {len(novels)} 本")
        finally:
            await self.close()
        return results

    # ==================== 上下文管理器 ====================

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
