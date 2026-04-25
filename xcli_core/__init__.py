"""
xcli_core - 小狸 Pro-CLI 核心模块

从 ai_cli.py 拆分优化的模块化架构。
"""

from .constants import *
from .sandbox import *
from .config import *
from .plugin_manager import LiuginManager
from .cli_core import AICLI, main


def ask_user_confirmation(prompt="确认执行？", default=False):
    """请求用户确认（兼容性存根，供插件调用）"""
    try:
        suffix = " [Y/n] " if default else " [y/N] "
        response = input(prompt + suffix).strip().lower()
        if not response:
            return default
        return response in ('y', 'yes', '是', '确认')
    except (EOFError, KeyboardInterrupt):
        return False


__all__ = [
    'AICLI',
    'LiuginManager',
    'main',
    'load_config',
    'save_config',
    'get_system_config',
    'set_system_config',
    'ask_user_confirmation',
]
