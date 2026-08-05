import os
import re
import json
import logging
from colorama import Fore, Style

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

# <input> 特殊语法：配置模型时可用它交互式询问用户并获取输入
#   <input>            → 用默认提示询问
#   <input:提示语>      → 用自定义提示语询问
_INPUT_PATTERN = re.compile(r"<input(?::([^>]*))?>")


def resolve_input_value(value, field_name="", default_prompt=None):
    """解析配置值中的 <input> 特殊语法，交互式询问用户并返回其输入。

    用法（写在 config.json 的字段值里）:
        "model": "<input>"                  → 启动时提示"请输入model: "
        "model": "<input:请输入模型名>"      → 启动时提示自定义文案
        也可以夹在字符串中间: "prefix<input>suffix"

    不含 <input> 的值原样返回；用户直接回车/中断时返回空串，由调用方兜底。
    """
    if not isinstance(value, str) or "<input" not in value:
        return value

    def _ask(match):
        label = (match.group(1) or "").strip()
        prompt = label or default_prompt or (f"请输入{field_name}" if field_name else "请输入")
        prompt = prompt.rstrip()
        if prompt and not prompt.endswith((":", "：", "?", "？", "!", "！", " ")):
            prompt += ": "
        try:
            answer = input(f"{Fore.CYAN}{prompt}{Style.RESET_ALL}").strip()
            return answer
        except (EOFError, KeyboardInterrupt):
            return ""

    return _INPUT_PATTERN.sub(_ask, value)


def load_config():
    """加载配置文件"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"api": {"engines": {}}, "system": {}, "plugins": {}}
    except json.JSONDecodeError:
        return {"api": {"engines": {}}, "system": {}, "plugins": {}}


def save_config(config):
    """保存配置文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存配置失败: {e}")


def get_system_config(key, default=None):
    """获取系统配置"""
    config = load_config()
    return config.get("system", {}).get(key, default)


def set_system_config(key, value):
    """设置系统配置"""
    config = load_config()
    if "system" not in config:
        config["system"] = {}
    config["system"][key] = value
    save_config(config)


# 配置日志：文件留全量 INFO，控制台默认只报 WARNING 以上（--verbose 时放开到 INFO）
try:
    from .verbose import is_verbose as _is_verbose
except ImportError:  # 被当作顶层模块单独导入时
    try:
        from verbose import is_verbose as _is_verbose
    except ImportError:
        def _is_verbose():
            return False

_file_handler = logging.FileHandler('xiaoli_cli.log', encoding='utf-8')
_file_handler.setLevel(logging.INFO)
_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.INFO if _is_verbose() else logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[_file_handler, _console_handler]
)

# 第三方库的心跳日志（httpx 每发一次请求就打一行）不上屏也不进日志文件
for _noisy in ('httpx', 'httpcore', 'urllib3', 'requests', 'openai', 'PIL', 'markdown_it'):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
