# NovelCrawler — 小说扫榜拆书工具 📚

一个基于 Python 的小说排行榜爬取 + AI 拆书分析工具，支持多平台，帮助网文作者和编辑快速了解市场趋势、拆解热门作品。

## ✨ 功能特性

### 📊 扫榜
- 爬取各平台排行榜数据（书名、作者、字数、分类、简介等）
- 支持批量获取小说详情
- 数据导出为 CSV / JSON 格式，方便 Excel 分析

### 🤖 AI 拆书分析
- 🎨 **写作风格分析** — 叙事视角、语言风格、节奏感、优缺点
- 📈 **情节节奏分析** — 故事结构、钩子设置、爽点分布、常见套路
- 👥 **人物关系分析** — 主角设定、配角定位、关系网络
- 支持任何 OpenAI 兼容接口（DeepSeek、通义千问、Ollama 等）

### 🌐 支持平台（已接入）
| 平台 | 状态 | 榜单 |
|------|------|------|
| 起点中文网 | ✅ | 月票榜、推荐票榜、收藏榜、畅销榜、新书榜、完本榜 |
| 番茄小说 | ✅ | 热门榜、推荐榜 |

## 🚀 快速开始

### 1. 安装依赖

```bash
cd NovelCrawler
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

支持的 API 服务：OpenAI、DeepSeek、通义千问、Ollama（本地）、小米 MiMo 等任何兼容 OpenAI 格式的接口。

### 3. 使用命令

```bash
# 列出所有支持的榜单
python main.py list-ranks

# 扫起点月票榜 Top 10
python main.py -p qidian rank --top 10

# 扫番茄热门榜
python main.py -p fanqie rank --top 10

# 拆书分析（基础 + AI）
python main.py -p qidian analyze 1035420986

# 只做基础分析（不调 AI）
python main.py -p fanqie analyze fanqie:6753575799414066190 --skip-ai

# 扫榜 + 自动拆解 Top 10
python main.py -p qidian full --top 10
```

## 📁 项目结构

```
NovelCrawler/
├── main.py                          # CLI 入口
├── config/
│   └── base_config.py               # 全局配置
├── base/
│   ├── base_crawler.py              # 爬虫基类
│   └── base_analyzer.py             # AI 分析器基类
├── novel_platform/
│   ├── qidian/                      # 起点中文网
│   │   ├── crawler.py               # 排行榜爬虫
│   │   ├── parser.py                # 页面解析器
│   │   └── model.py                 # 数据模型
│   └── fanqie/                      # 番茄小说
│       └── crawler.py               # API 爬虫
├── analyzer/
│   ├── structure_analyzer.py        # 基础结构分析（纯统计）
│   ├── style_analyzer.py            # AI 写作风格分析
│   ├── plot_analyzer.py             # AI 情节节奏分析
│   └── character_analyzer.py        # AI 人物关系分析
├── store/
│   └── csv_store.py                 # CSV / JSON 存储
├── tools/
│   ├── browser.py                   # Playwright 浏览器管理
│   └── utils.py                     # 工具函数
└── output/                          # 输出目录
    ├── rank/                        # 排行榜数据
    └── analysis/                    # 拆书分析报告
```

## 🔧 扩展新平台

项目架构支持快速扩展新平台，只需：

1. 在 `novel_platform/` 下创建新目录
2. 实现 `crawler.py`（继承 `BaseCrawler` 或独立实现）
3. 在 `config/base_config.py` 添加平台配置
4. 在 `main.py` 的 `PLATFORMS` 字典中注册

## ⚠️ 免责声明

**本工具仅供学习和研究使用。**

1. 本项目不提供任何小说正文内容的下载或存储功能
2. 本项目仅爬取公开可访问的排行榜元数据（书名、作者、字数、分类等）
3. 使用本工具时请遵守目标网站的服务条款和 robots.txt 规则
4. 请合理控制爬取频率，避免对目标服务器造成不必要的负担
5. 本工具所获取的数据仅供个人学习研究使用，**不得用于任何商业用途**
6. 使用本工具产生的一切法律责任由使用者自行承担
7. 本项目开发者不对因使用本工具而产生的任何直接或间接损失负责

**如果您是相关平台的权利人并认为本项目侵犯了您的权益，请联系删除。**
