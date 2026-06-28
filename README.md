# NovelCrawler — 小说扫榜拆书工具

基于 [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 架构模式打造的小说排行榜爬取 + AI 拆书分析工具。

## 功能特性

### 📊 扫榜
- 爬取起点中文网各类排行榜（月票榜、推荐票榜、收藏榜、畅销榜、新书榜、完本榜）
- 获取排行榜小说基本信息（书名、作者、字数、分类等）
- 支持批量获取小说详情页数据

### 📖 拆书分析

#### 基础结构分析（无需 LLM）
- 总字数、章节数、平均章节字数
- 卷结构分析
- VIP 章节比例
- 章节标题模式分析
- 更新频率估算
- 评分和热度数据

#### AI 深度分析（需要 LLM API）
- 🎨 **写作风格分析** — 叙事视角、语言风格、对话质量、节奏感
- 📈 **情节节奏分析** — 故事结构、钩子/爽点分布、转折点、常见套路
- 👥 **人物关系分析** — 主角设定、配角定位、关系网络、角色原型

## 快速开始

### 1. 安装依赖

```bash
cd D:\NovelCrawler
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置 AI 分析（可选）

```bash
# 设置 LLM API（支持 OpenAI 兼容接口）
set LLM_API_KEY=your-api-key
set LLM_API_BASE=https://api.openai.com/v1
set LLM_MODEL=gpt-4o-mini
```

### 3. 使用命令

```bash
# 扫榜 — 爬取月票榜
python main.py rank

# 扫榜 — 爬取推荐票榜前20本并获取详情
python main.py rank --type tuijian --top 20

# 查看小说详情
python main.py detail https://book.qidian.com/info/12345/

# 拆书分析（基础+AI）
python main.py analyze https://book.qidian.com/info/12345/

# 只做基础分析（跳过 AI）
python main.py analyze 12345 --skip-ai

# 完整流程：扫榜 + 拆解 Top 10
python main.py full --top 10

# 列出支持的榜单
python main.py list-ranks
```

## 项目结构

```
NovelCrawler/
├── main.py                     # CLI 入口
├── config/
│   └── base_config.py          # 全局配置
├── base/
│   ├── base_crawler.py         # 爬虫基类
│   └── base_analyzer.py        # AI 分析器基类
├── novel_platform/
│   └── qidian/                 # 起点中文网
│       ├── crawler.py          # 排行榜爬虫
│       ├── parser.py           # 页面解析器
│       └── model.py            # 数据模型
├── analyzer/
│   ├── structure_analyzer.py   # 基础结构分析
│   ├── style_analyzer.py       # AI 写作风格分析
│   ├── plot_analyzer.py        # AI 情节节奏分析
│   └── character_analyzer.py   # AI 人物关系分析
├── store/
│   └── csv_store.py            # CSV/JSON 存储
├── tools/
│   ├── browser.py              # Playwright 浏览器管理
│   └── utils.py                # 工具函数
└── output/
    ├── rank/                   # 排行榜数据输出
    └── analysis/               # 拆书分析报告
```

## 输出文件

| 文件 | 说明 |
|------|------|
| `output/rank/qidian_yuepiao_2026-06-28.csv` | 月票榜数据 |
| `output/rank/qidian_novel_12345.json` | 小说详情 |
| `output/analysis/qidian_12345_analysis_2026-06-28.json` | 拆书分析报告 |
| `output/analysis/qidian_analysis_summary_2026-06-28.csv` | 批量分析汇总 |

## 扩展其他平台

项目架构支持后续扩展，添加新平台只需：

1. 在 `novel_platform/` 下创建新目录（如 `fanqie/`）
2. 实现 `model.py`、`parser.py`、`crawler.py`
3. 在 `config/base_config.py` 中添加平台配置

## 注意事项

- ⚠️ 本工具仅供学习和研究使用
- 🕷️ 请遵守目标网站的 robots.txt 和使用条款
- ⏱️ 已内置请求间隔，避免对目标网站造成压力
- 🔒 Cookie 文件保存在 `cookies/` 目录，请勿泄露
