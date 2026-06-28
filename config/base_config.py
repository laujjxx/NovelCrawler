"""
NovelCrawler 全局配置
"""
import os

# ==================== 基础路径 ====================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
RANK_DIR = os.path.join(OUTPUT_DIR, "rank")
ANALYSIS_DIR = os.path.join(OUTPUT_DIR, "analysis")

# ==================== 浏览器配置 ====================
# Playwright 浏览器类型: chromium / firefox / webkit
BROWSER_TYPE = "chromium"
# 是否使用无头模式（True=不显示浏览器窗口）
# 起点有验证码，需要设为 False 手动过验证
HEADLESS = False
# 代理设置（留空则不使用代理，系统有代理 127.0.0.1:7897 时可取消注释）
PROXY_SERVER = os.environ.get("PROXY_SERVER", "http://127.0.0.1:7897")
# 浏览器 User-Agent
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
# 浏览器视口大小
VIEWPORT = {"width": 1920, "height": 1080}
# 页面加载超时（毫秒）
PAGE_TIMEOUT = 30000
# Cookie 文件路径（登录后保存的 Cookie）
COOKIE_DIR = os.path.join(BASE_DIR, "cookies")

# ==================== 爬虫配置 ====================
# 并发数
MAX_CONCURRENCY = 3
# 请求间隔（秒）— 避免被反爬
REQUEST_DELAY = 2.0
# 每个榜单最多爬取的小说数量
MAX_NOVELS_PER_RANK = 50
# 爬取小说详情时最多获取的章节数
MAX_CHAPTERS = 100

# ==================== 番茄小说配置 ====================
FANQIE_BASE_URL = "https://fanqienovel.com"
FANQIE_RANK_API = "https://fanqienovel.com/api/rank/list"
FANQIE_BOOK_API = "https://fanqienovel.com/api/book/info"

FANQIE_RANK_TYPES = {
    "热门榜": "hot",
    "推荐榜": "recommend",
}

# ==================== 纵横中文网配置（暂不可用） ====================
ZONGHENG_BASE_URL = "https://www.zongheng.com"

# ==================== 起点中文网配置 ====================
QIDIAN_BASE_URL = "https://www.qidian.com"
QIDIAN_RANK_URL = "https://www.qidian.com/rank/"
QIDIAN_BOOK_URL = "https://book.qidian.com/info/{book_id}/"

# 起点排行榜类型映射
QIDIAN_RANK_TYPES = {
    "月票榜": "yuepiao",
    "推荐票榜": "tuijian",
    "收藏榜": "shoucang",
    "畅销榜": "changxiao",
    "新书榜": "xinshu",
    "完本榜": "wanben",
}

# ==================== AI 分析配置 ====================
# LLM API 配置（支持 OpenAI 兼容接口）
LLM_API_BASE = os.environ.get("LLM_API_BASE", "https://api.xiaomimimo.com/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "mimo-v2.5-pro")
# 每次分析的最大 Token
LLM_MAX_TOKENS = 4000
# 分析温度（0=确定性, 1=创造性）
LLM_TEMPERATURE = 0.3

# ==================== 日志配置 ====================
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
