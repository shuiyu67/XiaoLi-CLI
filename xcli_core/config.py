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


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('xiaoli_cli.log', encoding='utf-8'),
        logging.StreamHandler()  # 同时输出到控制台
    ]
)
logger = logging.getLogger(__name__)
