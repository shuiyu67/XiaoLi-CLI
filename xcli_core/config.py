import os
import json
import logging
from colorama import Fore, Style

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")


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
