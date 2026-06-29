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


# ── 引擎配置档案管理 ──
# 存储结构: config["engine_profiles"][engine_name] = [ {name, base_url, api_key, model}, ... ]

def get_profiles(engine_name):
    """获取指定引擎的所有配置档案"""
    config = load_config()
    return config.get("engine_profiles", {}).get(engine_name, [])


def save_profile(engine_name, profile):
    """保存/更新一个配置档案（按 name 去重，已存在则覆盖）"""
    config = load_config()
    if "engine_profiles" not in config:
        config["engine_profiles"] = {}
    profiles = config["engine_profiles"].setdefault(engine_name, [])
    # 按 name 去重
    for i, p in enumerate(profiles):
        if p.get("name") == profile.get("name"):
            profiles[i] = profile
            break
    else:
        profiles.append(profile)
    config["engine_profiles"][engine_name] = profiles
    save_config(config)


def delete_profile(engine_name, profile_name):
    """删除指定引擎的一个配置档案"""
    config = load_config()
    profiles = config.get("engine_profiles", {}).get(engine_name, [])
    profiles = [p for p in profiles if p.get("name") != profile_name]
    if "engine_profiles" not in config:
        config["engine_profiles"] = {}
    config["engine_profiles"][engine_name] = profiles
    save_config(config)


def apply_profile(engine_name, profile):
    """将档案应用到 config.json 的 api.engines 节点（下次启动或重载时生效）"""
    config = load_config()
    if "api" not in config:
        config["api"] = {}
    if "engines" not in config["api"]:
        config["api"]["engines"] = {}
    engine_cfg = config["api"]["engines"].setdefault(engine_name, {})
    if "base_url" in profile:
        engine_cfg["base_url"] = profile["base_url"]
    if "api_key" in profile:
        engine_cfg["api_key"] = profile["api_key"]
    if "model" in profile:
        engine_cfg["model"] = profile["model"]
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
