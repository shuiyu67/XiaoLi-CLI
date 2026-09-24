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

# ── 第三方依赖（全部 try/except 保护） ──

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    REQUESTS_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None
    OPENAI_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

# tkinter 仅在视频播放功能中使用，服务器环境可能不可用
try:
    import tkinter as tk
    from tkinter import ttk
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

# cv2 仅在视频播放功能中使用
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# 图像显示相关（可选）
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from ascii_magic import AsciiArt
    ASCII_MAGIC_AVAILABLE = True
except ImportError:
    ASCII_MAGIC_AVAILABLE = False

# WebSocket 服务端
try:
    import websocket_server
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

# Clawli 独立进程服务器
try:
    import clawli_server
    CLAWLI_SERVER_AVAILABLE = True
except ImportError:
    CLAWLI_SERVER_AVAILABLE = False

# 统一工具管理器 - 支持 Liugin 和 Skill 双协议
try:
    from unified_tool_manager import UnifiedToolManager
    UNIFIED_TOOL_MANAGER_AVAILABLE = True
except ImportError:
    UNIFIED_TOOL_MANAGER_AVAILABLE = False

# Textual TUI 支持
try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical, VerticalScroll
    from textual.widgets import Header, Footer, Input, RichLog, Static, Button, Tree, TextArea, Rule
    from textual.widgets.tree import TreeNode
    from textual.binding import Binding
    from textual.events import Mount
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    print(f"{Fore.YELLOW}Textual 未安装，TUI 模式不可用。请运行: pip install textual{Style.RESET_ALL}")
