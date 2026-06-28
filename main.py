"""
NovelCrawler — 小说扫榜拆书工具

用法:
    python main.py rank                             # 默认起点月票榜
    python main.py rank -p fanqie                   # 番茄热门榜
    python main.py rank -p qidian --type tuijian    # 起点推荐票榜
    python main.py rank --top 10                    # 爬取并获取前10本详情
    python main.py detail <book_url_or_id>          # 查看小说详情
    python main.py analyze <book_url_or_id>         # 拆书分析
    python main.py full --top 10                    # 扫榜 + 自动拆解 Top 10
    python main.py list-ranks                       # 列出支持的榜单类型
"""
import argparse
import asyncio
import json
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.base_config import QIDIAN_RANK_TYPES, FANQIE_RANK_TYPES
from tools.utils import extract_book_id, setup_logger

logger = setup_logger("main")

# 平台注册表
PLATFORMS = {
    "qidian": {
        "name": "起点中文网",
        "rank_types": QIDIAN_RANK_TYPES,
        "default_rank": "yuepiao",
    },
    "fanqie": {
        "name": "番茄小说",
        "rank_types": FANQIE_RANK_TYPES,
        "default_rank": "hot",
    },
}


def _get_crawler(platform: str):
    """根据平台名返回对应的爬虫实例"""
    if platform == "fanqie":
        from novel_platform.fanqie.crawler import FanqieCrawler
        return FanqieCrawler()
    else:
        from novel_platform.qidian.crawler import QidianCrawler
        return QidianCrawler()


def _resolve_book_id(book_input: str) -> tuple:
    """
    解析用户输入，返回 (platform, book_id)
    支持格式:
      - 123456789 (纯数字 → 默认起点)
      - fanqie:12345 (平台:ID)
      - https://book.qidian.com/info/12345/ (URL)
      - https://fanqienovel.com/page/12345 (URL)
    """
    if not book_input:
        return ("", "")

    book_input = book_input.strip()

    # 平台:ID 格式
    if ":" in book_input and not book_input.startswith("http"):
        parts = book_input.split(":", 1)
        return (parts[0], parts[1])

    # URL 格式
    if "qidian" in book_input:
        return ("qidian", extract_book_id(book_input) or "")
    if "fanqie" in book_input:
        m = re.search(r"/page/(\d+)", book_input) or re.search(r"/(\d+)", book_input)
        return ("fanqie", m.group(1) if m else "")

    # 纯数字
    if book_input.isdigit():
        return ("qidian", book_input)

    return ("", "")


async def cmd_rank(args):
    """扫榜命令"""
    from store.csv_store import save_rank_csv, save_rank_json, save_novel_detail

    platform = args.platform
    pinfo = PLATFORMS.get(platform)
    if not pinfo:
        print(f"❌ 不支持的平台: {platform}")
        return

    rank_types_map = pinfo["rank_types"]

    # 确定榜单类型
    if args.type:
        if args.type in rank_types_map:
            rank_type = rank_types_map[args.type]
        elif args.type in rank_types_map.values():
            rank_type = args.type
        else:
            print(f"❌ 未知的榜单类型: {args.type}")
            print(f"支持的类型: {list(rank_types_map.keys())}")
            return
    else:
        rank_type = pinfo["default_rank"]

    crawler = _get_crawler(platform)
    await crawler.start()

    try:
        print(f"\n{'='*50}")
        print(f"📊 [{pinfo['name']}] 正在爬取: {args.type or rank_type}")
        print(f"{'='*50}")

        if args.top and args.top > 0:
            novels = await crawler.crawl_rank_with_details(rank_type, top_n=args.top)
            for novel in novels:
                if novel.get("book_id"):
                    save_novel_detail(novel, platform)
        else:
            novels = await crawler.crawl_rank_list(rank_type)

        if not novels:
            print(f"  ⚠️ 未获取到数据，请检查网络")
            return

        csv_path = save_rank_csv(novels, platform, rank_type)
        json_path = save_rank_json(novels, platform, rank_type)

        print(f"\n✅ 共获取 {len(novels)} 本小说")
        print(f"📄 CSV: {csv_path}")
        print(f"📄 JSON: {json_path}")
        print(f"\n{'排名':<4} {'书名':<20} {'作者':<12} {'字数':>8}")
        print("-" * 50)
        for novel in novels[:20]:
            rank = novel.get("rank", "?")
            title = novel.get("title", "未知")[:18]
            author = novel.get("author", "未知")[:10]
            wc = novel.get("word_count", 0)
            wc_str = f"{wc/10000:.1f}万" if wc >= 10000 else str(wc)
            print(f"{rank:<4} {title:<20} {author:<12} {wc_str:>8}")
    finally:
        await crawler.close()


async def cmd_detail(args):
    """查看小说详情"""
    from store.csv_store import save_novel_detail

    platform, book_id = _resolve_book_id(args.book)
    if not platform:
        platform = args.platform
    if not book_id:
        print("❌ 请提供有效的书号或链接")
        return

    crawler = _get_crawler(platform)
    await crawler.start()

    try:
        detail = await crawler.crawl_novel_detail(book_id)
        if not detail:
            print(f"❌ 未获取到小说详情 [{book_id}]")
            return

        save_novel_detail(detail, platform)

        print(f"\n{'='*50}")
        print(f"📖 《{detail.get('title', '未知')}》")
        print(f"{'='*50}")
        print(f"  平台: {PLATFORMS.get(platform, {}).get('name', platform)}")
        print(f"  作者: {detail.get('author', '未知')}")
        print(f"  分类: {detail.get('category', '未知')} {detail.get('sub_category', '')}")
        if detail.get("tags"):
            print(f"  标签: {', '.join(detail['tags'])}")
        print(f"  状态: {detail.get('status', '未知')}")
        print(f"  字数: {detail.get('word_count', 0)}")
        if detail.get("score"):
            print(f"  评分: {detail['score']}")
        if detail.get("read_count"):
            print(f"  阅读: {detail['read_count']}")
        if detail.get("recommend_count"):
            print(f"  推荐: {detail['recommend_count']}")
        print(f"\n📝 简介:")
        desc = detail.get("description", "无简介")
        print(f"  {desc[:200]}")
        if detail.get("latest_chapter"):
            print(f"\n📌 最新: {detail['latest_chapter']}")
    finally:
        await crawler.close()


async def cmd_analyze(args):
    """拆书分析"""
    from analyzer.structure_analyzer import analyze_structure
    from analyzer.style_analyzer import StyleAnalyzer
    from analyzer.plot_analyzer import PlotAnalyzer
    from analyzer.character_analyzer import CharacterAnalyzer
    from store.csv_store import save_analysis_report

    platform, book_id = _resolve_book_id(args.book)
    if not platform:
        platform = args.platform
    if not book_id:
        print("❌ 请提供有效的书号或链接")
        return

    print(f"\n📡 正在爬取小说数据 [{platform}:{book_id}]...")
    crawler = _get_crawler(platform)
    await crawler.start()

    try:
        detail = await crawler.crawl_novel_detail(book_id)
    finally:
        await crawler.close()

    if not detail:
        print(f"❌ 未获取到小说数据")
        return

    chapters = []  # 番茄没有章节 API，起点后续可补充

    print(f"✅ 数据爬取完成: 《{detail.get('title', book_id)}》")

    # 基础结构分析
    print(f"\n📊 正在进行基础结构分析...")
    structure = analyze_structure(detail, chapters)
    print(f"  {structure.get('summary', '')}")

    # AI 分析
    ai_results = {}
    novel_data = {"detail": detail, "chapters": chapters}

    if not args.skip_ai:
        from config.base_config import LLM_API_KEY
        if not LLM_API_KEY:
            print("\n⚠️ 未设置 LLM_API_KEY 环境变量，跳过 AI 分析")
        else:
            print(f"\n🎨 正在分析写作风格...")
            style = StyleAnalyzer()
            ai_results["writing_style"] = await style.analyze(novel_data)
            print(f"  {ai_results['writing_style'].get('summary', '')}")

            print(f"\n📈 正在分析情节节奏...")
            plot = PlotAnalyzer()
            ai_results["plot_structure"] = await plot.analyze(novel_data)
            print(f"  {ai_results['plot_structure'].get('summary', '')}")

            print(f"\n👥 正在分析人物关系...")
            character = CharacterAnalyzer()
            ai_results["character_analysis"] = await character.analyze(novel_data)
            print(f"  {ai_results['character_analysis'].get('summary', '')}")

    report = {
        "platform": platform,
        "book_id": book_id,
        "title": detail.get("title", ""),
        "author": detail.get("author", ""),
        "structure_analysis": structure,
        "ai_analysis": ai_results,
    }

    report_path = save_analysis_report(book_id, report, platform)
    print(f"\n📄 分析报告已保存: {report_path}")
    _print_analysis_summary(report)


async def cmd_full(args):
    """扫榜 + 自动拆解 Top N"""
    from analyzer.structure_analyzer import analyze_structure
    from analyzer.style_analyzer import StyleAnalyzer
    from store.csv_store import save_rank_csv, save_analysis_report, save_analysis_csv

    platform = args.platform
    pinfo = PLATFORMS.get(platform)
    if not pinfo:
        print(f"❌ 不支持的平台: {platform}")
        return

    top_n = args.top or 10
    rank_type = pinfo["default_rank"]

    crawler = _get_crawler(platform)
    await crawler.start()

    try:
        print(f"\n📊 [{pinfo['name']}] 正在爬取排行榜 Top {top_n}...")
        novels = await crawler.crawl_rank_with_details(rank_type, top_n=top_n)

        if not novels:
            print("❌ 未获取到数据")
            return

        save_rank_csv(novels, platform, rank_type)

        analyses = []
        for i, novel in enumerate(novels):
            book_id = novel.get("book_id", "")
            title = novel.get("title", "未知")
            print(f"\n{'='*50}")
            print(f"📖 [{i+1}/{len(novels)}] 正在分析: 《{title}》")
            print(f"{'='*50}")

            try:
                detail = await crawler.crawl_novel_detail(book_id)
                structure = analyze_structure(detail, [])
                print(f"  📊 {structure.get('summary', '')}")

                from config.base_config import LLM_API_KEY
                ai_results = {}
                if LLM_API_KEY:
                    novel_data = {"detail": detail, "chapters": []}
                    try:
                        style = StyleAnalyzer()
                        ai_results["writing_style"] = await style.analyze(novel_data)
                        print(f"  🎨 {ai_results['writing_style'].get('summary', '')}")
                    except Exception as e:
                        logger.warning(f"风格分析失败: {e}")

                report = {
                    "platform": platform,
                    "book_id": book_id,
                    "title": title,
                    "author": novel.get("author", ""),
                    "structure_analysis": structure,
                    "ai_analysis": ai_results,
                }
                save_analysis_report(book_id, report, platform)

                analyses.append({
                    "book_id": book_id,
                    "title": title,
                    "author": novel.get("author", ""),
                    "category": novel.get("category", ""),
                    "word_count": detail.get("word_count", 0),
                    "update_frequency": structure.get("update_frequency", ""),
                    "writing_style": ai_results.get("writing_style", {}).get("summary", ""),
                    "plot_pace": ai_results.get("plot_structure", {}).get("summary", ""),
                    "highlights": ai_results.get("plot_structure", {}).get("common_patterns", []),
                })
            except Exception as e:
                logger.error(f"分析失败 [{title}]: {e}")

        if analyses:
            csv_path = save_analysis_csv(analyses, platform)
            print(f"\n✅ 分析汇总已保存: {csv_path}")
    finally:
        await crawler.close()


async def cmd_list_ranks(args):
    """列出支持的榜单"""
    print(f"\n📊 支持的排行榜类型:")
    print(f"{'平台':<8} {'名称':<10} {'标识':<12}")
    print("-" * 35)
    for pid, pinfo in PLATFORMS.items():
        for name, code in pinfo["rank_types"].items():
            print(f"{pid:<8} {name:<10} {code:<12}")


def _print_analysis_summary(report: dict):
    """打印分析报告摘要"""
    structure = report.get("structure_analysis", {})
    ai = report.get("ai_analysis", {})
    platform = report.get("platform", "")
    pname = PLATFORMS.get(platform, {}).get("name", platform)

    print(f"\n{'='*60}")
    print(f"📋 拆书分析报告: 《{report.get('title', '未知')}》 [{pname}]")
    print(f"{'='*60}")

    print(f"\n📊 基础数据:")
    print(f"  字数: {structure.get('word_count', 0)}")
    print(f"  状态: {structure.get('status', '')}")

    if ai.get("writing_style"):
        ws = ai["writing_style"]
        print(f"\n🎨 写作风格:")
        print(f"  {ws.get('summary', '')}")
        if ws.get("strengths"):
            print(f"  优点: {', '.join(ws['strengths'][:3])}")

    if ai.get("plot_structure"):
        ps = ai["plot_structure"]
        print(f"\n📈 情节结构:")
        print(f"  {ps.get('summary', '')}")
        if ps.get("common_patterns"):
            print(f"  套路: {', '.join(ps['common_patterns'][:3])}")

    if ai.get("character_analysis"):
        ca = ai["character_analysis"]
        print(f"\n👥 人物设定:")
        print(f"  {ca.get('summary', '')}")


def main():
    parser = argparse.ArgumentParser(
        description="NovelCrawler — 小说扫榜拆书工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "-p", "--platform", type=str, default="qidian",
        choices=list(PLATFORMS.keys()),
        help="选择平台 (默认: qidian)"
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # rank
    rank_p = subparsers.add_parser("rank", help="扫榜")
    rank_p.add_argument("--type", "-t", type=str, default=None, help="榜单类型")
    rank_p.add_argument("--top", "-n", type=int, default=0, help="获取前N本详情")

    # detail
    detail_p = subparsers.add_parser("detail", help="查看小说详情")
    detail_p.add_argument("book", help="书号或链接 (如 12345 或 fanqie:12345)")

    # analyze
    analyze_p = subparsers.add_parser("analyze", help="拆书分析")
    analyze_p.add_argument("book", help="书号或链接")
    analyze_p.add_argument("--skip-ai", action="store_true", help="跳过AI分析")

    # full
    full_p = subparsers.add_parser("full", help="扫榜+自动拆解")
    full_p.add_argument("--top", "-n", type=int, default=10, help="分析前N本")

    # list-ranks
    subparsers.add_parser("list-ranks", help="列出支持的榜单")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cmd_map = {
        "rank": cmd_rank,
        "detail": cmd_detail,
        "analyze": cmd_analyze,
        "full": cmd_full,
        "list-ranks": cmd_list_ranks,
    }

    cmd_func = cmd_map.get(args.command)
    if cmd_func:
        asyncio.run(cmd_func(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
