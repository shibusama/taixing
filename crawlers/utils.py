# 爬虫公共工具模块 - 兼容层
# 从拆分后的子模块 re-export 所有公开接口
# 保持现有爬虫模块 `from .utils import ...` 的导入路径不变

from crawlers.http_utils import *   # fetch_html, fetch_json, fetch_html_cffi, HAS_CFFI, HEADERS, parse_date
from crawlers.file_utils import *   # load_json, save_json, update_meta, BASE_DIR, DATA_DIR
from crawlers.ai_fallback import *  # fetch_ai_fallback