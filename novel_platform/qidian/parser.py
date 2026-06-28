"""
起点中文网页面解析器
使用 Playwright 渲染页面后解析 DOM
"""
import re
from typing import Any, Dict, List, Optional

from playwright.async_api import Page

from tools.utils import clean_text, parse_word_count, setup_logger
from novel_platform.qidian.model import ChapterInfo, NovelDetail, NovelInfo

logger = setup_logger("qidian_parser")


async def parse_rank_page(
    page: Page, rank_type: str
) -> List[Dict[str, Any]]:
    """
    解析排行榜页面，提取小说列表
    Args:
        page: Playwright 页面对象（已导航到排行榜页）
        rank_type: 榜单类型标识
    Returns:
        小说基本信息列表
    """
    novels = []

    # 等待列表加载 — 起点排行榜使用多种布局，尝试常见的选择器
    selectors = [
        ".rank-list .book-mid-info",       # 经典排行榜布局
        ".rank-body .book-list li",        # 新版排行榜布局
        "[class*='rank'] .book-item",      # 通用匹配
        "ul.book-rank-list > li",          # 备选
    ]

    book_elements = []
    for sel in selectors:
        book_elements = await page.query_selector_all(sel)
        if book_elements:
            logger.debug(f"使用选择器 '{sel}' 找到 {len(book_elements)} 本书")
            break

    if not book_elements:
        # 回退：尝试直接解析整个页面内容
        logger.warning("未找到排行榜列表元素，尝试回退解析")
        return await _fallback_parse_rank(page, rank_type)

    for idx, elem in enumerate(book_elements, 1):
        try:
            novel = await _parse_rank_item(elem, rank_type, idx)
            if novel and novel.get("title"):
                novels.append(novel)
        except Exception as e:
            logger.warning(f"解析第 {idx} 本书失败: {e}")

    return novels


async def _parse_rank_item(
    element, rank_type: str, rank: int
) -> Optional[Dict[str, Any]]:
    """解析排行榜中的单本书"""
    data = {"rank": rank, "rank_type": rank_type}

    # 书名和链接
    title_el = await element.query_selector("h2 a, .book-name a, a.title, h4 a")
    if title_el:
        data["title"] = clean_text(await title_el.inner_text())
        href = await title_el.get_attribute("href") or ""
        if href.startswith("//"):
            href = "https:" + href
        data["book_url"] = href
        # 提取 book_id
        match = re.search(r"/info/(\d+)", href) or re.search(r"/(\d+)/?$", href)
        if match:
            data["book_id"] = match.group(1)

    # 作者
    author_el = await element.query_selector(
        ".author a, a.name, .book-author a, span.author"
    )
    if author_el:
        data["author"] = clean_text(await author_el.inner_text())

    # 分类/类型
    category_el = await element.query_selector(
        ".type, .category, .tag, span.class"
    )
    if category_el:
        data["category"] = clean_text(await category_el.inner_text())

    # 简介（排行榜可能截断）
    desc_el = await element.query_selector(
        ".intro, .description, .book-desc, p.intro"
    )
    if desc_el:
        data["description"] = clean_text(await desc_el.inner_text())

    # 最新章节
    chapter_el = await element.query_selector(
        ".update a, .latest-chapter a, a.chapter"
    )
    if chapter_el:
        data["latest_chapter"] = clean_text(await chapter_el.inner_text())

    # 字数 — 通常包含 "万字" 字样
    word_el = await element.query_selector(
        ".word-count, .total, span.words, .book-state"
    )
    if word_el:
        word_text = await word_el.inner_text()
        data["word_count"] = parse_word_count(word_text)

    return data


async def _fallback_parse_rank(
    page: Page, rank_type: str
) -> List[Dict[str, Any]]:
    """
    回退解析：直接从页面提取所有 book.qidian.com 链接
    """
    novels = []
    links = await page.query_selector_all('a[href*="book.qidian.com/info"]')
    seen = set()
    for idx, link in enumerate(links, 1):
        href = await link.get_attribute("href") or ""
        match = re.search(r"/info/(\d+)", href)
        if not match:
            continue
        book_id = match.group(1)
        if book_id in seen:
            continue
        seen.add(book_id)
        title = clean_text(await link.inner_text())
        if not title:
            continue
        novels.append({
            "book_id": book_id,
            "title": title,
            "rank": idx,
            "rank_type": rank_type,
            "book_url": href if href.startswith("http") else f"https://book.qidian.com/info/{book_id}/",
        })
    return novels


async def parse_novel_detail(page: Page) -> Dict[str, Any]:
    """
    解析小说详情页
    前提: page 已导航到 https://book.qidian.com/info/{book_id}/
    """
    detail = {}

    # 书名
    title_el = await page.query_selector("h1, .book-info h1, h2.book-title")
    if title_el:
        detail["title"] = clean_text(await title_el.inner_text())

    # 作者
    author_el = await page.query_selector(
        ".writer, a.writer, .book-info .author a, h1 + a"
    )
    if author_el:
        detail["author"] = clean_text(await author_el.inner_text())

    # 分类 / 子分类
    cat_el = await page.query_selector(
        ".book-info .tag, a.tag, .book-cell .type"
    )
    if cat_el:
        cat_text = clean_text(await cat_el.inner_text())
        parts = re.split(r"[·/|]", cat_text)
        detail["category"] = parts[0].strip() if parts else cat_text
        if len(parts) > 1:
            detail["sub_category"] = parts[1].strip()

    # 标签（多个）
    tag_els = await page.query_selector_all(
        ".book-info .tag, .book-tag a, span.tag"
    )
    tags = []
    for tag_el in tag_els:
        t = clean_text(await tag_el.inner_text())
        if t and t not in tags:
            tags.append(t)
    detail["tags"] = tags

    # 简介
    desc_el = await page.query_selector(
        ".book-intro p, .book-info-detail .intro, p.intro, .book-dec p"
    )
    if desc_el:
        detail["description"] = clean_text(await desc_el.inner_text())

    # 连载状态
    status_el = await page.query_selector(
        ".book-state span, .blue, .book-info .tag"
    )
    if status_el:
        status_text = clean_text(await status_el.inner_text())
        if "完结" in status_text or "完本" in status_text:
            detail["status"] = "完结"
        elif "连载" in status_text:
            detail["status"] = "连载中"

    # 统计数据面板（点击/推荐/收藏/评分等）
    stat_els = await page.query_selector_all(
        ".book-info .count em, .book-data p em, .nums .num, em.count"
    )
    stat_labels = await page.query_selector_all(
        ".book-info .count cite, .book-data p cite, .nums cite, cite"
    )
    for i, em_el in enumerate(stat_els):
        try:
            val_text = clean_text(await em_el.inner_text())
            val = parse_word_count(val_text) if "万" in val_text else _safe_int(val_text)
            label = ""
            if i < len(stat_labels):
                label = clean_text(await stat_labels[i].inner_text())
            if "点击" in label:
                detail["click_count"] = val
            elif "推荐" in label:
                detail["recommend_count"] = val
            elif "收藏" in label:
                detail["collection_count"] = val
            elif "粉丝" in label:
                detail["fan_value"] = val
        except Exception:
            pass

    # 评分
    score_el = await page.query_selector(
        ".score em, .book-score em, .grade em"
    )
    if score_el:
        score_text = clean_text(await score_el.inner_text())
        detail["score"] = _safe_float(score_text)

    # 最新章节
    latest_el = await page.query_selector(
        ".book-info .lastChapter a, .last-chapter a, a.latest"
    )
    if latest_el:
        detail["latest_chapter"] = clean_text(await latest_el.inner_text())
        href = await latest_el.get_attribute("href") or ""
        if href.startswith("//"):
            href = "https:" + href
        detail["latest_chapter_url"] = href

    return detail


async def parse_chapter_list(
    page: Page, max_chapters: int = 100
) -> List[Dict[str, Any]]:
    """
    解析章节目录
    前提: page 已导航到小说详情页（目录通常在同一页展开）
    """
    chapters = []

    # 尝试点击"查看全部目录"或类似按钮
    catalog_btn = await page.query_selector(
        "a[href*='Catalog'], .catalog-btn, .j-catalogWrap"
    )
    if catalog_btn:
        try:
            await catalog_btn.click()
            await page.wait_for_timeout(2000)
        except Exception:
            pass

    # 解析卷和章节
    volume_els = await page.query_selector_all(
        ".volume-wrap .volume, .catalog-volume, div.volume"
    )

    if volume_els:
        for vol_el in volume_els:
            vol_name_el = await vol_el.query_selector("h3, .volume-name, h2")
            vol_name = clean_text(await vol_name_el.inner_text()) if vol_name_el else ""
            ch_els = await vol_el.query_selector_all("li a, .chapter-name a, a.chapter")
            for ch_el in ch_els:
                if len(chapters) >= max_chapters:
                    break
                ch_title = clean_text(await ch_el.inner_text())
                ch_url = await ch_el.get_attribute("href") or ""
                if ch_url.startswith("//"):
                    ch_url = "https:" + ch_url
                chapters.append({
                    "title": ch_title,
                    "volume_name": vol_name,
                    "url": ch_url,
                    "is_vip": "vip" in ch_url.lower() or "收费" in ch_title,
                })
    else:
        # 回退：直接获取所有章节链接
        ch_links = await page.query_selector_all(
            "#catalog li a, .catalog-content a, a[href*='chapter']"
        )
        for ch_el in ch_links[:max_chapters]:
            ch_title = clean_text(await ch_el.inner_text())
            ch_url = await ch_el.get_attribute("href") or ""
            if ch_url.startswith("//"):
                ch_url = "https:" + ch_url
            chapters.append({
                "title": ch_title,
                "volume_name": "",
                "url": ch_url,
                "is_vip": False,
            })

    return chapters[:max_chapters]


def _safe_int(text: str) -> int:
    """安全转换为整数"""
    text = re.sub(r"[^\d.]", "", text)
    try:
        return int(float(text))
    except (ValueError, TypeError):
        return 0


def _safe_float(text: str) -> float:
    """安全转换为浮点数"""
    text = re.sub(r"[^\d.]", "", text)
    try:
        return float(text)
    except (ValueError, TypeError):
        return 0.0
