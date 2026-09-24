# 常量定义
WEB_SERVER_DEFAULT_PORT = 8080
MAX_FILE_SIZE = 52428800  # 50MB
MAX_VIDEO_DURATION = 10000  # 10秒
VIDEO_FRAME_DELAY = 0.04  # 40毫秒
LOVE_FILE_PATH = "love.txt"
DEFAULT_MAX_HISTORY = 999999  # 无限制对话历史

# 版本号（v8.0 基于 v5.4.1 重新立项）
VERSION = "8.0.4"
VERSION_NAME = "小狸 Pro-CLI"

from colorama import Fore, Style

# ── 第三方依赖探测（启动链路优化：find_spec 只查 spec 不加载模块本体）──
# 历史问题：这里曾用 try/except 真 import requests/textual/numpy/websocket_server，
# 实测拖慢启动 ~1.3s（importtime: requests 605ms + textual 511ms + numpy 224ms +
# websocket_server 202ms）。现改为 find_spec 探测——标志位语义不变，模块本体
# 等到真正使用处（cli_base 的 UnifiedToolManager 实例化、tui 的 textual 等）再加载。
# 旧版 re-export 的符号（requests/np/OpenAI/…）全仓无人 import（pyflakes 实证），不再导出。
import importlib.util as _ilu


def _has_module(name):
    """探测包是否安装（不执行模块代码）"""
    try:
        return _ilu.find_spec(name) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


REQUESTS_AVAILABLE = _has_module('requests')
OPENAI_AVAILABLE = _has_module('openai')
NUMPY_AVAILABLE = _has_module('numpy')
TKINTER_AVAILABLE = _has_module('tkinter')
CV2_AVAILABLE = _has_module('cv2')
PIL_AVAILABLE = _has_module('PIL')
ASCII_MAGIC_AVAILABLE = _has_module('ascii_magic')
WEBSOCKET_AVAILABLE = _has_module('websocket_server')
CLAWLI_SERVER_AVAILABLE = _has_module('clawli_server')
UNIFIED_TOOL_MANAGER_AVAILABLE = _has_module('unified_tool_manager')

# Textual TUI 支持（tui.py 在 import 时自行加载 textual 本体）
TEXTUAL_AVAILABLE = _has_module('textual')
if not TEXTUAL_AVAILABLE:
    print(f"{Fore.YELLOW}Textual 未安装，TUI 模式不可用。请运行: pip install textual{Style.RESET_ALL}")
