"""核心配置管理模块"""
import os
import json
import logging

logger = logging.getLogger(__name__)

# 常量
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
MAX_FILE_SIZE = 52428800  # 50MB
DEFAULT_MAX_HISTORY = 999999

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
        logger.error(f"保存配置失败: {e}")

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
