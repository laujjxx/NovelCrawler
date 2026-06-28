"""
Playwright 浏览器管理
"""
import asyncio
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from config.base_config import (
    BROWSER_TYPE,
    COOKIE_DIR,
    HEADLESS,
    PAGE_TIMEOUT,
    PROXY_SERVER,
    USER_AGENT,
    VIEWPORT,
)
from tools.utils import load_cookie, save_cookie, setup_logger

logger = setup_logger("browser")


class BrowserManager:
    """Playwright 浏览器上下文管理器"""

    def __init__(self, platform_name: str = "default"):
        self.platform_name = platform_name
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def start(self) -> Page:
        """启动浏览器并返回页面对象"""
        self._playwright = await async_playwright().start()

        # 选择浏览器类型
        launcher = getattr(self._playwright, BROWSER_TYPE)
        launch_args = {"headless": HEADLESS}
        if PROXY_SERVER:
            launch_args["proxy"] = {"server": PROXY_SERVER}
            logger.info(f"使用代理: {PROXY_SERVER}")
        self._browser = await launcher.launch(**launch_args)

        # 加载已保存的 Cookie
        cookies = load_cookie(self.platform_name, COOKIE_DIR)
        storage_state = None
        if cookies:
            storage_state = {"cookies": cookies}

        # 创建浏览器上下文
        self._context = await self._browser.new_context(
            viewport=VIEWPORT,
            user_agent=USER_AGENT,
            storage_state=storage_state,
        )

        # 设置默认超时
        self._context.set_default_timeout(PAGE_TIMEOUT)

        # 创建页面
        self._page = await self._context.new_page()
        logger.info(f"浏览器已启动 [{self.platform_name}], headless={HEADLESS}")
        return self._page

    async def get_page(self) -> Page:
        """获取当前页面，未启动则先启动"""
        if self._page is None:
            await self.start()
        return self._page

    async def save_cookies(self) -> None:
        """保存当前上下文的 Cookie"""
        if self._context:
            cookies = await self._context.cookies()
            save_cookie(cookies, self.platform_name, COOKIE_DIR)
            logger.info(f"Cookie 已保存 [{self.platform_name}]")

    async def new_page(self) -> Page:
        """在当前上下文中打开新标签页"""
        if self._context is None:
            await self.start()
        return await self._context.new_page()

    async def close(self) -> None:
        """关闭浏览器"""
        try:
            await self.save_cookies()
        except Exception as e:
            logger.warning(f"保存 Cookie 失败: {e}")
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info(f"浏览器已关闭 [{self.platform_name}]")

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
