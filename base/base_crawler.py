"""
爬虫基类 — 定义通用爬取流程
"""
import abc
import asyncio
from typing import Any, Dict, List, Optional

from playwright.async_api import Page

from config.base_config import MAX_CONCURRENCY, REQUEST_DELAY
from tools.browser import BrowserManager
from tools.utils import async_sleep, setup_logger


class BaseCrawler(abc.ABC):
    """
    爬虫基类
    子类需要实现:
        - platform_name: 平台名称
        - crawl_rank_list(): 爬取排行榜
        - crawl_novel_detail(): 爬取小说详情
    """

    platform_name: str = "base"

    def __init__(self):
        self.logger = setup_logger(self.__class__.__name__)
        self.browser = BrowserManager(self.platform_name)
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    async def start(self) -> None:
        """启动爬虫（初始化浏览器）"""
        await self.browser.start()
        self.logger.info(f"[{self.platform_name}] 爬虫已启动")

    async def close(self) -> None:
        """关闭爬虫"""
        await self.browser.close()
        self.logger.info(f"[{self.platform_name}] 爬虫已关闭")

    async def _throttled_request(self, coro):
        """带限流的请求包装"""
        async with self._semaphore:
            result = await coro
            await async_sleep(REQUEST_DELAY)
            return result

    @abc.abstractmethod
    async def crawl_rank_list(
        self, rank_type: str, page_num: int = 1
    ) -> List[Dict[str, Any]]:
        """
        爬取排行榜
        Args:
            rank_type: 榜单类型
            page_num: 页码
        Returns:
            小说基本信息列表
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def crawl_novel_detail(self, book_id: str) -> Dict[str, Any]:
        """
        爬取小说详情
        Args:
            book_id: 小说ID
        Returns:
            小说详细信息
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def crawl_chapter_list(
        self, book_id: str, max_chapters: int = 100
    ) -> List[Dict[str, Any]]:
        """
        爬取章节目录
        Args:
            book_id: 小说ID
            max_chapters: 最大章节数
        Returns:
            章节列表
        """
        raise NotImplementedError

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

    def get_rank_types(self) -> Dict[str, str]:
        """
        返回该平台支持的榜单类型
        Returns:
            {显示名: 内部标识}
        """
        return {}

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
