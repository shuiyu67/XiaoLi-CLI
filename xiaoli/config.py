"""配置管理 - 加载/保存/默认值"""
import os
import json
import logging

logger = logging.getLogger(__name__)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(PROJECT_DIR, "config.json")

# 默认配置
DEFAULTS = {
    "system": {
        "default_engine": "ollama",
        "max_history": 999999,
        "code_execution_timeout": 30,
        "max_file_size": 52428800,
    },
    "api": {"engines": {}},
    "plugins": {},
}

_cache = None


def load() -> dict:
    """加载配置（带缓存）"""
    global _cache
    if _cache is not None:
        return _cache
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            _cache = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        _cache = DEFAULTS.copy()
    return _cache


def save(config: dict = None):
    """保存配置"""
    global _cache
    cfg = config or _cache or DEFAULTS
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        _cache = cfg
    except Exception as e:
        logger.error(f"保存配置失败: {e}")


def get(key: str, default=None):
    """获取系统配置项"""
    cfg = load()
    return cfg.get("system", {}).get(key, default)


def set(key: str, value):
    """设置系统配置项"""
    cfg = load()
    if "system" not in cfg:
        cfg["system"] = {}
    cfg["system"][key] = value
    save(cfg)


def reload():
    """强制重新加载"""
    global _cache
    _cache = None
    return load()
