# 常量定义
WEB_SERVER_DEFAULT_PORT = 8080
MAX_FILE_SIZE = 52428800  # 50MB
MAX_VIDEO_DURATION = 10000  # 10秒
VIDEO_FRAME_DELAY = 0.04  # 40毫秒
LOVE_FILE_PATH = "love.txt"
DEFAULT_MAX_HISTORY = 999999  # 无限制对话历史
import os
import sys
import importlib.util
import json
import re
import requests
import shutil
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from colorama import init, Fore, Style
import tkinter as tk
from tkinter import ttk
import cv2
import numpy as np
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import socket
import webbrowser
from datetime import datetime
import logging
from PIL import Image
from ascii_magic import AsciiArt
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
import asyncio
from typing import Optional
from io import StringIO

try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical, VerticalScroll
    from textual.widgets import Header, Footer, Input, RichLog, Static, Button, Tree
    from textual.widgets.tree import TreeNode
    from textual.binding import Binding
    from textual.events import Mount
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    print(f"{Fore.YELLOW}Textual 未安装，TUI 模式不可用。请运行: pip install textual{Style.RESET_ALL}")


class TUIBridge:
    """桥接类：让 TUI 能够调用同步的 AICLI 方法"""

    def __init__(self, cli):
        self.cli = cli
        self._executor = ThreadPoolExecutor(max_workers=4)

    def get_engines(self) -> dict:
        return self.cli.engines

    def get_current_engine_name(self) -> str:
        return self.cli.get_current_engine_name()

    def get_tools(self) -> list:
        return self.cli.liugin_manager.tools

    def get_conversation_history(self) -> list:
        return self.cli.shared_conversation_history

    def switch_engine(self, engine_name: str) -> bool:
        if engine_name in self.cli.engines:
            self.cli.switch_engine(engine_name)
            return True
        return False


class TUIMainApp(App):
    """TUI 主应用"""

    CSS = """
    Screen { background: $surface; }
    #chat-log { height: 1fr; }
    #user-input { height: 3; }
    #right-panel { width: 30; }
    #status-bar { height: 1; dock: bottom; }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "退出"),
        Binding("ctrl+t", "switch_to_cli", "切换CLI"),
    ]

    def __init__(self, cli):
        super().__init__()
        self.cli = cli
        self.bridge = TUIBridge(cli)
        self.is_generating = False

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="chat-area"):
                yield RichLog(id="chat-log", wrap=True, max_lines=10000)
                yield Input(placeholder="输入消息后按 Enter 发送...", id="user-input")
            with Vertical(id="right-panel"):
                yield Static("[b]AI 引擎[/b]")
                yield Tree("引擎列表", id="engine-status")
                yield Static("[b]可用工具[/b]")
                yield RichLog(id="tools-log", wrap=True, max_lines=100)
        yield Static("", id="status-bar")

    def on_mount(self) -> None:
        self.title = "小狸 CLI - TUI"
        self._update_engine_tree()
        self._update_tools_list()
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write(f"[bold cyan]欢迎使用小狸 CLI TUI 模式![/bold cyan]")
        chat_log.write(f"[dim]当前引擎: {self.bridge.get_current_engine_name()}[/dim]")
        chat_log.write(f"[dim]输入 /cli 切换到 CLI 模式[/dim]")
        chat_log.write("")
        self.query_one("#user-input", Input).focus()
        self.update_status()

    def _update_engine_tree(self) -> None:
        tree = self.query_one("#engine-status", Tree)
        tree.reset("引擎列表")
        engines = self.bridge.get_engines()
        current = self.bridge.get_current_engine_name()

        for name in engines:
            node = tree.root.add(f"* {name}")
            if name == current:
                node.add("(当前)")
        tree.root.expand()

    def _update_tools_list(self) -> None:
        tools_log = self.query_one("#tools-log", RichLog)
        tools_log.clear()
        tools = self.bridge.get_tools()
        if tools:
            for tool in tools[:15]:
                name = tool.get('name', '未知')
                desc = tool.get('description', '')[:35]
                tools_log.write(f"- {name}: {desc}")
        else:
            tools_log.write("暂无工具")

    def update_status(self) -> None:
        status = self.query_one("#status-bar", Static)
        engine = self.bridge.get_current_engine_name()
        history_len = len(self.bridge.get_conversation_history())
        status.update(f"引擎: {engine} | {history_len} 条对话 | Ctrl+T: CLI | /cli: 切换模式")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        user_input = event.value.strip()
        if not user_input:
            return

        if user_input == '/cli':
            self.action_switch_to_cli()
            return

        if user_input.startswith('/engine switch '):
            engine_name = user_input[14:].strip()
            if self.bridge.switch_engine(engine_name):
                chat_log = self.query_one("#chat-log", RichLog)
                chat_log.write(f"[green]已切换到引擎: {engine_name}[/]")
                self._update_engine_tree()
                self.update_status()
            else:
                chat_log = self.query_one("#chat-log", RichLog)
                chat_log.write(f"[red]切换失败，引擎 '{engine_name}' 不存在[/]")
            return

        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write(f"[cyan]你:[/] {user_input}")
        chat_log.write("")
        event.input.value = ""
        chat_log.write("AI 正在思考...")
        self.run_worker(self._generate_response_async(user_input))

    async def _generate_response_async(self, user_input: str) -> None:
        """异步生成响应 - 通过回调输出到 TUI"""
        try:
            # 清除"正在思考"消息
            self.call_after_refresh(self._clear_thinking)

            # 包装回调以在主线程执行
            def safe_output(message):
                self.call_after_refresh(self._write_chat, message)

            # 临时设置 CLI 的输出回调
            original_callback = self.cli.tui_output_callback
            self.cli.tui_output_callback = safe_output

            try:
                # 在线程池中运行 CLI
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.cli.process_conversation, user_input)
            finally:
                # 恢复原始回调
                self.cli.tui_output_callback = original_callback

            self.call_after_refresh(self.update_status)
        except Exception as e:
            import traceback
            self.call_after_refresh(self._write_chat, f"[red]错误: {str(e)}[/]")
            self.call_after_refresh(self._write_chat, f"[dim]{traceback.format_exc()}[/]")
        finally:
            self.is_generating = False

    def _write_chat(self, message: str) -> None:
        """在主线程写入聊天日志"""
        try:
            chat_log = self.query_one("#chat-log", RichLog)
            # RichLog 支持 ANSI 颜色代码，直接写入
            chat_log.write(message)
        except Exception as e:
            print(f"写入聊天失败: {e}")

    def _clear_thinking(self) -> None:
        """清除'正在思考'消息"""
        try:
            chat_log = self.query_one("#chat-log", RichLog)
            # 移除最后一条"正在思考"消息
            children = list(chat_log.children)
            if children and "正在思考" in str(children[-1]):
                chat_log.remove_child(children[-1])
        except:
            pass

    def action_switch_to_cli(self) -> None:
        import subprocess
        import sys
        self.exit()
        # 启动新的 CLI 进程
        subprocess.Popen([sys.executable, __file__])
        # 退出当前进程
        os._exit(0)


# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

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

class LiuginManager:
    """插件管理器"""

    def __init__(self, liugins_dir="plugins"):
        self.liugins_dir = liugins_dir
        self.tools = []

    def get_enabled_liugins(self):
        """获取启用的插件列表"""
        # 检查环境变量中是否有启用的插件列表
        enabled_liugins_env = os.environ.get("XIAOLI_ENABLED_PLUGINS")
        if enabled_liugins_env is not None:
            # 特殊处理：空字符串表示不启用任何插件
            if enabled_liugins_env == "":
                return []
            return enabled_liugins_env.split(",")
        # 检查是否有插件配置文件
        project_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(project_dir, "plugins_config.py")
        if os.path.exists(config_file):
            try:
                # 读取配置文件
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_content = f.read()
                # 检查是否明确表示不启用任何插件
                if "# 不启用任何插件" in config_content:
                    return []
                # 解析启用的插件
                enabled_liugins = []
                for line in config_content.split('\n'):
                    if line.startswith('ENABLE_') and '= True' in line:
                        liugin_name = line.split('=')[0].replace('ENABLE_', '').strip().lower()
                        enabled_liugins.append(liugin_name)
                return enabled_liugins
            except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
                logger.error(f"读取插件配置文件失败: {e}")
                print(f"{Fore.RED}读取插件配置文件失败: {e}{Style.RESET_ALL}")
            except Exception as e:
                logger.error(f"读取插件配置时发生未知错误: {e}")
                print(f"{Fore.RED}读取插件配置文件失败: {e}{Style.RESET_ALL}")
        # 如果没有配置，则返回None表示加载所有插件
        return None

    def load_liugins(self):
        """加载liugin"""
        self.tools = []
        # 获取启用的插件列表
        enabled_liugins = self.get_enabled_liugins()
        # 加载工具插件
        if os.path.exists(self.liugins_dir):
            for filename in os.listdir(self.liugins_dir):
                if filename.endswith('.py') and filename != '__init__.py':
                    liugin_name = filename[:-3]  # 移除.py扩展名
                    # 如果有启用的插件列表，检查当前插件是否在其中
                    if enabled_liugins is not None and liugin_name.lower() not in enabled_liugins:
                        print(f"{Fore.YELLOW}跳过liugin: {liugin_name} (未启用){Style.RESET_ALL}")
                        continue
                    plugin_path = os.path.join(self.liugins_dir, filename)
                    try:
                        spec = importlib.util.spec_from_file_location(liugin_name, plugin_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        # 获取插件信息 - 兼容 Liugin 和 Plugin 两种类名
                        plugin_class = getattr(module, 'Liugin', None) or getattr(module, 'Plugin', None)
                        if plugin_class:
                            plugin_instance = plugin_class()
                            tool_info = plugin_instance.get_tool_info()
                            tool_info['handler'] = plugin_instance.handle
                            self.tools.append(tool_info)
                            print(f"{Fore.GREEN}已加载liugin: {liugin_name}{Style.RESET_ALL}")
                    except (ImportError, AttributeError, TypeError) as e:
                        logger.error(f"加载liugin失败 {filename}: {e}")
                        print(f"{Fore.RED}加载liugin失败 {filename}: {e}{Style.RESET_ALL}")
                    except FileNotFoundError as e:
                        logger.error(f"liugin文件未找到 {filename}: {e}")
                        print(f"{Fore.RED}liugin文件未找到 {filename}: {e}{Style.RESET_ALL}")
                    except Exception as e:
                        logger.error(f"加载liugin时发生未知错误 {filename}: {e}")
                        print(f"{Fore.RED}加载liugin失败 {filename}: {e}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}总共加载了 {len(self.tools)} 个工具插件{Style.RESET_ALL}")

    def search_tools(self, query, limit=5):
        """
        搜索工具，支持关键词匹配
        
        参数:
            query: 搜索关键词
            limit: 返回结果数量限制
            
        返回:
            匹配的工具列表，每个工具包含 name、description、usage
        """
        if not self.tools:
            return []
        
        query_lower = query.lower()
        matches = []
        
        for tool in self.tools:
            # 计算匹配分数
            score = 0
            tool_name = tool.get('name', '').lower()
            tool_desc = tool.get('description', '').lower()
            tool_keywords = [kw.lower() for kw in tool.get('keywords', [])]
            
            # 名称完全匹配
            if query_lower == tool_name:
                score += 100
            # 名称包含查询词
            if query_lower in tool_name:
                score += 50
            # 描述包含查询词
            if query_lower in tool_desc:
                score += 30
            # 关键词匹配
            for keyword in tool_keywords:
                if query_lower in keyword:
                    score += 20
                    break
            
            if score > 0:
                matches.append({
                    'score': score,
                    'name': tool.get('name', ''),
                    'description': tool.get('description', ''),
                    'usage': tool.get('usage', ''),
                    'keywords': tool.get('keywords', [])
                })
        
        # 按分数排序并返回前 limit 个
        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches[:limit]
    
    def get_tool_by_name(self, tool_name):
        """根据名称获取工具"""
        for tool in self.tools:
            if tool.get('name', '').lower() == tool_name.lower():
                return tool
        return None


class AICLI:
    """AI CLI主程序"""

    def __init__(self):
        # 初始化colorama
        init(autoreset=True)

        # 确保插件管理器使用正确的路径
        project_dir = os.path.dirname(os.path.abspath(__file__))
        liugins_dir = os.path.join(project_dir, "plugins")
        skills_dir = os.path.join(project_dir, "skills")
        
        # 使用统一工具管理器（支持 Liugin 和 Skill 双协议）
        if UNIFIED_TOOL_MANAGER_AVAILABLE:
            self.liugin_manager = UnifiedToolManager(self)
            self._use_unified_manager = True
        else:
            self.liugin_manager = LiuginManager(liugins_dir)
            self._use_unified_manager = False

        # 初始化引擎字典（先初始化为空字典）
        self.engines = {}

        # 初始化插件命令注册表
        self.liugin_commands = {}

        # 初始化系统引擎命令注册表
        self.engine_commands = {}
        # 注册默认的引擎命令
        self._register_engine_commands()
        # 动态加载AI引擎插件
        self.load_ai_engines()
        # 从配置文件获取默认引擎设置
        default_engine_name = self._get_default_engine_name()
        # 设置默认引擎，优先使用配置文件指定的引擎
        if default_engine_name in self.engines:
            self.current_engine = self.engines[default_engine_name]
            print(f"{Fore.GREEN}使用配置的默认AI引擎: {default_engine_name}{Style.RESET_ALL}")
        elif self.engines:
            # 如果配置的引擎不存在但有其他引擎，则使用第一个可用引擎
            first_engine_name = next(iter(self.engines))
            self.current_engine = self.engines[first_engine_name]
            print(f"{Fore.GREEN}使用默认AI引擎: {first_engine_name}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}警告: 没有可用的AI引擎，请检查ai_engines目录{Style.RESET_ALL}")
            self.current_engine = None
        if self.current_engine:
            self.current_engine.cli = self  # 设置引用以便访问插件
        # 创建聊天记录目录
        self.chat_history_dir = os.path.join(project_dir, "chat_history")
        if not os.path.exists(self.chat_history_dir):
            os.makedirs(self.chat_history_dir)
        
        # 获取 skills 目录路径
        skills_dir = os.path.join(project_dir, "skills")
        self.load_liugins(liugins_dir, skills_dir)
        # 初始化共享对话历史
        self.shared_conversation_history = []
        # 设置最大历史记录数
        self.max_history = DEFAULT_MAX_HISTORY
        # 为所有已加载的引擎设置共享对话历史
        self._set_shared_conversation_history()
        # 初始化代码执行相关功能
        self.code_execution_enabled = True
        self.code_execution_timeout = 30  # 默认超时30秒
        self.code_execution_memory_limit = 128 * 1024 * 1024  # 128MB内存限制
        self.code_execution_whitelist = [
            'json', 'math', 'datetime', 'random', 'collections',
            'itertools', 'functools', 'operator', 'typing', 're'
        ]  # 允许导入的安全模块白名单
        self.code_execution_history = []  # 代码执行历史记录
        self.liugin_code_requests = {}  # 插件代码执行请求队列
        self.user_input_queue = {}  # 用户输入队列，用于存储等待用户确认的操作
        self.is_clawli_mode = False  # Clawli 远程模式标志
        self._clawli_monitor_thread = None  # Clawli 消息监控线程
        self._clawli_monitor_running = False  # 监控线程运行标志
        # TUI 输出回调（用于 TUI 模式下的实时输出）
        self.tui_output_callback = None
        # 初始化用户ID（基于机器硬件动态生成）
        import uuid
        self.user_id = str(uuid.getnode())

    def _start_clawli_monitor(self):
        """启动 Clawli 消息监控线程"""
        if self._clawli_monitor_running:
            return
        
        self._clawli_monitor_running = True
        print(f"{Fore.CYAN}[Clawli] 消息监控线程已启动{Style.RESET_ALL}")
        
        def monitor_loop():
            while self._clawli_monitor_running and self.is_clawli_mode:
                try:
                    # 从独立进程服务器获取消息
                    if CLAWLI_SERVER_AVAILABLE:
                        messages = clawli_server.get_messages()
                        if messages:
                            print(f"[Clawli Monitor] 收到 {len(messages)} 条消息")
                        for msg in messages:
                            self._handle_clawli_message(msg)
                    import time
                    time.sleep(0.1)  # 100ms 检查间隔
                except Exception as e:
                    print(f"[Clawli Monitor] 错误: {e}")
        
        self._clawli_monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._clawli_monitor_thread.start()
    
    def _stop_clawli_monitor(self):
        """停止 Clawli 消息监控线程"""
        self._clawli_monitor_running = False
        if self._clawli_monitor_thread:
            self._clawli_monitor_thread.join(timeout=1)
            self._clawli_monitor_thread = None
    
    def _handle_clawli_message(self, msg: dict):
        """处理来自手机端的消息"""
        try:
            msg_type = msg.get("type", "")
            
            if msg_type == "message":
                content = msg.get("content", "")
                self._process_clawli_user_message(content)
            
            elif msg_type == "file":
                file_path = msg.get("path", "")
                text = msg.get("text", "")
                category = msg.get("category", "file")
                
                if category == "image":
                    # 图片走图像识别
                    self._process_clawli_image(file_path, text)
                else:
                    # 其他文件
                    self._process_clawli_user_message(f"@{file_path}\n{text}")
        
        except Exception as e:
            print(f"[Clawli] 处理消息错误: {e}")
    
    def _process_clawli_user_message(self, content: str):
        """处理 Clawli 用户消息"""
        if not self.current_engine:
            return
        
        # 添加 Clawli 标识
        full_content = f"{content}\n\n[此消息由 Clawli 手机端发送]"
        
        # 添加到历史
        self.shared_conversation_history.append({
            "role": "user",
            "content": full_content
        })
        
        # 调用 AI 处理
        system_prompt = self._build_system_prompt(self.get_liugin_usage_prompts())
        response = self.current_engine.generate_response(full_content, system_prompt=system_prompt)
        
        # 处理响应（可能包含工具调用）
        self._process_clawli_response(response)
    
    def _process_clawli_response(self, response: str):
        """处理 Clawli AI 响应"""
        text_content, json_data = self._parse_mixed_response(response)
        
        if json_data:
            # 处理工具调用
            tool_calls = self._extract_tool_calls(json_data)
            
            if tool_calls:
                for tool_data in tool_calls:
                    tool_name = tool_data.get('tool', '未知工具')
                    tool_args = tool_data.get('args', '')
                    
                    # 发送工具状态到手机
                    if CLAWLI_SERVER_AVAILABLE:
                        clawli_server.send_tool_status(tool_name, tool_args, "calling")
                    
                    result = self.process_tool_call(tool_data)
                    result_text = result.get('result', '无结果')
                    
                    # 发送结果状态到手机
                    if CLAWLI_SERVER_AVAILABLE:
                        clawli_server.send_tool_status(tool_name, tool_args, "success", result_text)
                
                # 添加到历史并继续处理
                self.shared_conversation_history.append({
                    "role": "assistant",
                    "content": response
                })
                
                # 继续处理
                tool_result_str = "\n".join([f"工具执行结果: {r}" for r in [result.get('result', '')]])
                self._process_clawli_user_message(f"{tool_result_str}\n请根据工具执行结果继续回答。")
                return
        
        # 普通响应
        final_response = text_content if text_content else response
        
        self.shared_conversation_history.append({
            "role": "assistant",
            "content": final_response
        })
        
        # 发送到手机
        if CLAWLI_SERVER_AVAILABLE:
            clawli_server.send_message(final_response)
    
    def _process_clawli_image(self, image_path: str, text: str):
        """处理 Clawli 图片消息"""
        try:
            # 检查图像识别引擎
            image_engine = getattr(self, 'image_engine', None)
            if not image_engine:
                try:
                    from image_engine import get_image_engine
                    image_engine = get_image_engine()
                except:
                    image_engine = None
            
            if image_engine:
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                
                result = image_engine.analyze(image_data, text or "请描述这张图片")
                self._process_clawli_user_message(f"@{image_path}\n图片内容: {result}\n\n{text}")
            else:
                self._process_clawli_user_message(f"@{image_path}\n{text}")
        
        except Exception as e:
            self._process_clawli_user_message(f"@{image_path}\n图片处理失败: {e}\n{text}")
    
    def _extract_tool_calls(self, json_data) -> list:
        """从 JSON 数据中提取工具调用列表（支持多种格式）"""
        tool_calls = []
        
        if isinstance(json_data, dict):
            # 格式1: 小狸自有格式 {"action": "use_tool", "tool": "...", "args": "..."}
            if json_data.get('action') == 'use_tool':
                tool_calls.append(json_data)
            # 格式2: 简化格式 {"tool": "...", "args": "..."}
            elif 'tool' in json_data and 'args' in json_data:
                tool_calls.append(json_data)
            # 格式3: OpenAI function_call 格式 {"function_call": {"name": "...", "arguments": "..."}}
            elif 'function_call' in json_data:
                fc = json_data['function_call']
                if isinstance(fc, dict):
                    args = fc.get('arguments', '')
                    # arguments 可能是 JSON 字符串，需要解析
                    if isinstance(args, str) and args.startswith('{'):
                        try:
                            args = json.loads(args)
                        except:
                            pass
                    tool_calls.append({
                        'tool': fc.get('name', ''),
                        'args': args if isinstance(args, str) else '',
                        'arguments': args if isinstance(args, dict) else None
                    })
            # 格式4: MCP/Anthropic 格式 {"name": "...", "arguments": {...}}
            elif 'name' in json_data and 'arguments' in json_data:
                args = json_data.get('arguments', '')
                # arguments 可能是 JSON 字符串，需要解析
                if isinstance(args, str) and args.startswith('{'):
                    try:
                        args = json.loads(args)
                    except:
                        pass
                tool_calls.append({
                    'tool': json_data.get('name', ''),
                    'args': args if isinstance(args, str) else '',
                    'arguments': args if isinstance(args, dict) else None
                })
            # 格式5: OpenAI tool_calls 格式 {"type": "function", "function": {...}}
            elif json_data.get('type') == 'function' and 'function' in json_data:
                func = json_data['function']
                args = func.get('arguments', '')
                if isinstance(args, str) and args.startswith('{'):
                    try:
                        args = json.loads(args)
                    except:
                        pass
                tool_calls.append({
                    'tool': func.get('name', ''),
                    'args': args if isinstance(args, str) else '',
                    'arguments': args if isinstance(args, dict) else None
                })
        elif isinstance(json_data, list):
            for item in json_data:
                if isinstance(item, dict):
                    if item.get('action') == 'use_tool':
                        tool_calls.append(item)
                    elif 'tool' in item and 'args' in item:
                        tool_calls.append(item)
                    elif 'name' in item and 'arguments' in item:
                        args = item.get('arguments', '')
                        # arguments 可能是 JSON 字符串，需要解析
                        if isinstance(args, str) and args.startswith('{'):
                            try:
                                args = json.loads(args)
                            except:
                                pass
                        tool_calls.append({
                            'tool': item.get('name', ''),
                            'args': args if isinstance(args, str) else '',
                            'arguments': args if isinstance(args, dict) else None
                        })
        
        return tool_calls if tool_calls else None

    def cleanup_resources(self):
        """清理资源，确保在程序退出时正确关闭所有资源"""
        print(f"{Fore.YELLOW}正在清理资源...{Style.RESET_ALL}")
        # 停止 Clawli 监控
        self._stop_clawli_monitor()
        # 停止 Clawli 服务器
        if CLAWLI_SERVER_AVAILABLE:
            clawli_server.stop_server()
        print(f"{Fore.GREEN}资源清理完成{Style.RESET_ALL}")

    def __del__(self):
        """析构函数，确保资源被清理"""
        self.cleanup_resources()

    def _process_code_blocks(self, text):
        """处理包含""" """语法的文本，将代码块部分显示为红色"""
        import re
        from colorama import Fore, Style
        # 使用正则表达式查找 """ """ 包围的内容
        # 模式匹配：""" 任意内容（非贪婪） """
        pattern = r'(""".*?""")'

        def replace_match(match):
            full_match = match.group(1)  # 整个匹配（包括 """ ）
            # 移除开头的"""和结尾的"""
            inner_content = full_match[3:-3]
            # 返回红色显示的内容
            return f'{Fore.RED}{inner_content}{Style.RESET_ALL}'
        # 执行替换
        result = re.sub(pattern, replace_match, text, flags=re.DOTALL)
        return result

    def _limit_output_lines(self, text, max_lines=2):
        """限制输出行数为指定的最大行数"""
        lines = text.split('\n')
        if len(lines) <= max_lines:
            return text
        # 只保留前max_lines行
        return '\n'.join(lines[:max_lines]) + f"\n... (已截断，共{len(lines)}行)"

    def _get_default_engine_name(self):
        """从配置文件获取默认引擎名称"""
        try:
            # 优先从配置文件读取默认引擎
            default_engine = get_system_config('default_engine')
            if default_engine:
                return default_engine
            # 如果配置文件中没有，使用默认值 ollama
            return 'ollama'
        except Exception as e:
            print(f"{Fore.YELLOW}读取引擎配置失败，使用默认引擎: {e}{Style.RESET_ALL}")
            return 'ollama'

    def load_ai_engines(self):
        """动态加载AI引擎插件"""
        print(f"{Fore.GREEN}正在加载AI引擎插件...{Style.RESET_ALL}")
        # AI引擎插件目录
        ai_engines_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_engines")
        # 加载AI引擎插件
        if os.path.exists(ai_engines_dir):
            for filename in os.listdir(ai_engines_dir):
                if filename.endswith('.py') and filename != '__init__.py':
                    engine_path = os.path.join(ai_engines_dir, filename)
                    engine_name = filename[:-3]  # 移除.py扩展名
                    try:
                        spec = importlib.util.spec_from_file_location(engine_name, engine_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        # 获取引擎类
                        # 改进：使用更通用的方法，不依赖硬编码的类名列表
                        class_name = self._find_engine_class(module, engine_name)
                        if class_name and hasattr(module, class_name):
                            engine_instance = getattr(module, class_name)()
                            engine_instance.cli = self  # 设置CLI引用
                            # 获取引擎名称
                            engine_key = getattr(engine_instance, 'name', engine_name)
                            # 检查引擎是否已存在，避免重复加载
                            if engine_key not in self.engines:
                                self.engines[engine_key] = engine_instance
                                print(f"{Fore.GREEN}已加载AI引擎: {engine_key} ({class_name}){Style.RESET_ALL}")
                            else:
                                print(f"{Fore.YELLOW}AI引擎 {engine_key} 已存在，跳过加载{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.YELLOW}AI引擎插件 {filename} 中未找到合适的引擎类{Style.RESET_ALL}")
                    except (ImportError, AttributeError, TypeError) as e:
                        logger.error(f"加载AI引擎插件失败 {filename}: {e}")
                        print(f"{Fore.RED}加载AI引擎插件失败 {filename}: {e}{Style.RESET_ALL}")
                    except FileNotFoundError as e:
                        logger.error(f"AI引擎liugin文件未找到 {filename}: {e}")
                        print(f"{Fore.RED}AI引擎liugin文件未找到 {filename}: {e}{Style.RESET_ALL}")
                    except Exception as e:
                        logger.error(f"加载AI引擎插件时发生未知错误 {filename}: {e}")
                        print(f"{Fore.RED}加载AI引擎插件失败 {filename}: {e}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}总共加载了 {len(self.engines)} 个AI引擎{Style.RESET_ALL}")

    def _find_engine_class(self, module, engine_name):
            """查找AI引擎类，使用动态方式避免硬编码类名"""
            # 首先尝试常见的命名模式
            possible_names = [
                engine_name.capitalize() + "AI",
                engine_name.replace('_', '').replace('-', '').capitalize() + "AI",
                engine_name.replace('_', '').capitalize() + "AI",
                engine_name.replace('_engine', '').capitalize() + "AI",
                # 添加更多命名模式以覆盖特殊情况
                engine_name.replace('-', '').replace('_', '').capitalize() + "AI",
                engine_name.replace('-', '').capitalize() + "AI",
                # 特殊处理：qwen3-coder-plus -> Qwen3CoderPlusAI
                ''.join(word.capitalize() for word in engine_name.replace('-', ' ').replace('_', ' ').split()) + "AI",
                # 特殊处理：qwen3-coder-plus_engine -> Qwen3CoderPlusAI（先处理_engine后缀）
                ''.join(word.capitalize() for word in engine_name.replace('_engine', '').replace('-', ' ').replace('_', ' ').split()) + "AI",
            ]
            # 检查模块中的所有类
            for name in possible_names:
                if hasattr(module, name):
                    return name
            # 如果常见命名模式不匹配，查找模块中的所有类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (hasattr(attr, '__class__') and
                    isinstance(attr, type) and
                    attr_name.endswith('AI') and
                    hasattr(attr, 'generate_response')):  # AI引擎类有generate_response方法
                    return attr_name
            return None

    def load_liugins(self, liugins_dir=None, skills_dir=None):
        """加载liugin和技能"""
        print(f"{Fore.GREEN}正在加载工具...{Style.RESET_ALL}")
        
        # 使用统一工具管理器
        if self._use_unified_manager:
            self.liugin_manager.initialize(liugins_dir or "plugins", skills_dir or "skills")
        else:
            # 兼容旧版 LiuginManager
            self.liugin_manager.tools = []
            enabled_liugins = self.liugin_manager.get_enabled_liugins()
            plugins_path = liugins_dir or self.liugin_manager.liugins_dir
            
            if os.path.exists(plugins_path):
                for filename in os.listdir(plugins_path):
                    if filename.endswith('.py') and filename != '__init__.py':
                        liugin_name = filename[:-3]
                        if enabled_liugins is not None and liugin_name.lower() not in enabled_liugins:
                            print(f"{Fore.YELLOW}跳过liugin: {liugin_name} (未启用){Style.RESET_ALL}")
                            continue
                        plugin_path = os.path.join(plugins_path, filename)
                        try:
                            spec = importlib.util.spec_from_file_location(liugin_name, plugin_path)
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            # 兼容 Liugin 和 Plugin 两种类名
                            plugin_class = getattr(module, 'Liugin', None) or getattr(module, 'Plugin', None)
                            if plugin_class:
                                plugin_instance = plugin_class()
                                if hasattr(plugin_instance, 'set_cli'):
                                    plugin_instance.set_cli(self)
                                tool_info = plugin_instance.get_tool_info()
                                tool_info['handler'] = plugin_instance.handle
                                self.liugin_manager.tools.append(tool_info)
                                print(f"{Fore.GREEN}已加载liugin: {liugin_name}{Style.RESET_ALL}")
                        except Exception as e:
                            print(f"{Fore.RED}加载liugin失败 {filename}: {e}{Style.RESET_ALL}")
            print(f"{Fore.GREEN}总共加载了 {len(self.liugin_manager.tools)} 个工具插件{Style.RESET_ALL}")
        
        print(f"{Fore.GREEN}工具加载完成!{Style.RESET_ALL}")

    def register_liugin_command(self, command, handler):
        """注册插件命令"""
        self.liugin_commands[command] = handler
        print(f"{Fore.GREEN}已注册插件命令: {command}{Style.RESET_ALL}")

    def unregister_liugin_command(self, command):
        """注销插件命令"""
        if command in self.liugin_commands:
            del self.liugin_commands[command]
            print(f"{Fore.GREEN}已注销插件命令: {command}{Style.RESET_ALL}")

    def _register_engine_commands(self):
        """注册默认引擎命令"""
        self.engine_commands['list'] = self._handle_engine_list
        self.engine_commands['switch'] = self._handle_engine_switch

    def register_engine_command(self, command, handler):
        """注册引擎命令"""
        self.engine_commands[command] = handler
        print(f"{Fore.GREEN}已注册引擎命令: {command}{Style.RESET_ALL}")

    def unregister_engine_command(self, command):
        """注销引擎命令"""
        if command in self.engine_commands:
            del self.engine_commands[command]
            print(f"{Fore.GREEN}已注销引擎命令: {command}{Style.RESET_ALL}")

    def _handle_engine_list(self, args):
        """处理引擎列表命令"""
        print(f"{Fore.GREEN}可用的AI引擎:{Style.RESET_ALL}")
        for engine_name in self.engines.keys():
            status = " (当前使用)" if engine_name == getattr(self.current_engine, 'name', 'spark') else ""
            print(f"{Fore.GREEN}  - {engine_name}{status}{Style.RESET_ALL}")

    def _handle_engine_switch(self, args):
        """处理引擎切换命令"""
        if args:
            engine_name = args.strip()
            self.switch_engine(engine_name)
        else:
            print(f"{Fore.RED}请提供引擎名称.用法: /engine switch <引擎名>{Style.RESET_ALL}")

    def _handle_remote_command(self, args):
        """处理远程连接命令
        
        本地模式: /remote start <端口> <密码>
        代理模式: /remote proxy <服务器:端口> <服务器密码> <PC端口> <PC密码>
        """
        if not WEBSOCKET_AVAILABLE:
            print(f"{Fore.RED}错误: websockets 库未安装{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}请运行: pip install websockets{Style.RESET_ALL}")
            return
        
        args = args.strip()
        
        if not args or args == '':
            # 显示帮助
            print(f"\n{Fore.CYAN}{'='*55}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}  远程连接命令帮助{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*55}{Style.RESET_ALL}")
            print(f"\n{Fore.WHITE}本地模式 (局域网直连):{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  /remote start <端口> <密码>{Style.RESET_ALL}")
            print(f"{Fore.WHITE}    端口: 监听端口 (默认9079){Style.RESET_ALL}")
            print(f"{Fore.WHITE}    密码: PC密码 (安卓端需要输入){Style.RESET_ALL}")
            print(f"\n{Fore.WHITE}代理模式 (无公网IP，通过中继服务器):{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  /remote proxy <服务器> <服务器密码> <PC端口> <PC密码>{Style.RESET_ALL}")
            print(f"{Fore.WHITE}    服务器: 中继服务器地址:端口{Style.RESET_ALL}")
            print(f"{Fore.WHITE}    服务器密码: 连接中继服务器的密码{Style.RESET_ALL}")
            print(f"{Fore.WHITE}    PC端口: 在服务器上使用的端口{Style.RESET_ALL}")
            print(f"{Fore.WHITE}    PC密码: 安卓端连接时需要验证{Style.RESET_ALL}")
            print(f"\n{Fore.WHITE}其他命令:{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  /remote stop     - 停止服务{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  /remote status   - 查看状态{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  /remote ip       - 查看本机IP{Style.RESET_ALL}")
            print(f"\n{Fore.CYAN}{'='*55}{Style.RESET_ALL}")
            print(f"\n{Fore.GREEN}示例:{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  /remote start 9079 mypassword{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  /remote proxy relay.example.com:9079 serverpwd 12345 pcpwd{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*55}{Style.RESET_ALL}\n")
            return
        
        parts = args.split()
        cmd = parts[0].lower()
        
        if cmd == 'start':
            # 本地模式: /remote start [端口] <密码>
            port = 9079
            password = ""
            
            if len(parts) == 2:
                # 只有一个参数，可能是端口或密码
                arg = parts[1]
                if arg.isdigit():
                    port = int(arg)
                    print(f"{Fore.RED}错误: 请设置PC密码{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}用法: /remote start {port} <密码>{Style.RESET_ALL}")
                    return
                else:
                    password = arg
            
            elif len(parts) >= 3:
                try:
                    port = int(parts[1])
                    password = parts[2]
                except ValueError:
                    password = parts[1]
            
            if not password:
                print(f"{Fore.RED}错误: 请设置PC密码{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}用法: /remote start <端口> <密码>{Style.RESET_ALL}")
                return
            
            if len(password) < 4:
                print(f"{Fore.RED}错误: 密码至少4个字符{Style.RESET_ALL}")
                return
            
            # 使用独立进程服务器
            if CLAWLI_SERVER_AVAILABLE:
                success = clawli_server.start_server("0.0.0.0", port, password)
                if success:
                    self.is_clawli_mode = True
                    # 启动消息监控线程
                    self._start_clawli_monitor()
            else:
                websocket_server.start_local_server(self, port, password)
            
        elif cmd == 'proxy':
            # 代理模式: /remote proxy <服务器> <服务器密码> <PC端口> <PC密码>
            if len(parts) < 5:
                print(f"{Fore.RED}参数不足{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}用法: /remote proxy <服务器> <服务器密码> <PC端口> <PC密码>{Style.RESET_ALL}")
                print(f"{Fore.WHITE}示例: /remote proxy relay.example.com:9079 serverpwd 12345 pcpwd{Style.RESET_ALL}")
                return
            
            server_addr = parts[1]
            server_password = parts[2]
            pc_port = 0
            pc_password = parts[4] if len(parts) > 4 else ""
            
            # 解析端口
            try:
                pc_port = int(parts[3])
                if pc_port < 10000 or pc_port > 19999:
                    print(f"{Fore.YELLOW}建议端口范围: 10000-19999{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}无效的端口号: {parts[3]}{Style.RESET_ALL}")
                return
            
            if not pc_password:
                print(f"{Fore.RED}错误: 请设置PC密码{Style.RESET_ALL}")
                return
            
            if len(pc_password) < 4:
                print(f"{Fore.RED}错误: PC密码至少4个字符{Style.RESET_ALL}")
                return
            
            # 解析服务器地址
            if ':' in server_addr:
                server_host, port_str = server_addr.rsplit(':', 1)
                try:
                    server_port = int(port_str)
                except ValueError:
                    print(f"{Fore.RED}无效的服务器端口: {port_str}{Style.RESET_ALL}")
                    return
            else:
                server_host = server_addr
                server_port = 9079
            
            # 连接代理
            print(f"{Fore.CYAN}正在连接中继服务器...{Style.RESET_ALL}")
            websocket_server.start_proxy_client(
                self, server_host, server_port, 
                server_password, pc_port, pc_password
            )
            
        elif cmd == 'stop':
            # 停止所有服务
            if CLAWLI_SERVER_AVAILABLE:
                clawli_server.stop_server()
                self.is_clawli_mode = False
            else:
                websocket_server.stop_all()
            print(f"{Fore.GREEN}远程服务已停止{Style.RESET_ALL}")
            
        elif cmd == 'status':
            # 查看状态
            if CLAWLI_SERVER_AVAILABLE:
                status = clawli_server.get_status()
            else:
                status = websocket_server.get_status()
            if status.get('running'):
                mode = status.get('mode', 'local')
                if mode == 'proxy':
                    print(f"{Fore.GREEN}远程服务状态: 运行中 (代理模式){Style.RESET_ALL}")
                    print(f"{Fore.WHITE}服务器: {Fore.YELLOW}{status.get('server', '未知')}{Style.RESET_ALL}")
                    print(f"{Fore.WHITE}PC端口: {Fore.YELLOW}{status.get('port', '未知')}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.GREEN}远程服务状态: 运行中 (本地模式){Style.RESET_ALL}")
                    print(f"{Fore.WHITE}本机IP: {Fore.YELLOW}{status.get('local_ip', '未知')}{Style.RESET_ALL}")
                    print(f"{Fore.WHITE}端口: {Fore.YELLOW}{status.get('port', 9079)}{Style.RESET_ALL}")
                    print(f"{Fore.WHITE}已连接客户端: {Fore.YELLOW}{status.get('connected_clients', 0)}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}远程服务状态: 未启动{Style.RESET_ALL}")
                print(f"{Fore.WHITE}使用 {Fore.CYAN}/remote start <端口> <密码>{Fore.WHITE} 启动本地服务{Style.RESET_ALL}")
                print(f"{Fore.WHITE}使用 {Fore.CYAN}/remote proxy ...{Fore.WHITE} 连接代理服务器{Style.RESET_ALL}")
            
        elif cmd == 'ip':
            # 显示本机IP
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                print(f"{Fore.GREEN}本机IP地址: {Fore.YELLOW}{local_ip}{Style.RESET_ALL}")
                print(f"{Fore.WHITE}在 Clawli 应用中输入此IP即可连接 (仅限局域网){Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}获取IP失败: {e}{Style.RESET_ALL}")
                
        else:
            print(f"{Fore.RED}未知命令: {cmd}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}可用命令: start, proxy, stop, status, ip{Style.RESET_ALL}")

    def _get_engine_commands_help(self):
        """获取引擎命令帮助信息"""
        help_lines = []
        for cmd, handler in self.engine_commands.items():
            if cmd == 'list':
                help_lines.append(f"  /engine {cmd:<10} - 查看可用的AI引擎")
            elif cmd == 'switch':
                help_lines.append(f"  /engine {cmd:<10} - 切换AI引擎")
            else:
                # 可以根据命令名生成通用帮助文本
                help_lines.append(f"  /engine {cmd:<10} - 执行{cmd}命令")
        return '\n'.join(help_lines) if help_lines else "  无可用引擎管理命令"

    def get_available_engines(self):
        """获取可用引擎列表"""
        return list(self.engines.keys())

    def get_current_engine_name(self):
        """获取当前引擎名称"""
        return getattr(self.current_engine, 'name', '未设置') if self.current_engine else '未设置'

    def get_liugin_manager(self):
        """获取插件管理器"""
        return self.liugin_manager

    def switch_engine(self, engine_name):
        """切换AI引擎"""
        if engine_name in self.engines:
            # 保存当前引擎
            old_engine = self.current_engine
            self.current_engine = self.engines[engine_name]

            # 确保引擎有CLI引用
            if hasattr(self.current_engine, 'cli'):
                self.current_engine.cli = self

            # 确保新引擎也使用共享的对话历史
            if hasattr(self.current_engine, 'shared_conversation_history'):
                self.current_engine.shared_conversation_history = self.shared_conversation_history
                self.current_engine.max_history = self.max_history

            # 当切换引擎时，向新引擎提供完整的对话历史作为上下文
            if old_engine != self.current_engine and self.shared_conversation_history:
                print(f"{Fore.CYAN}已切换到AI引擎: {engine_name}，正在传递对话历史...{Style.RESET_ALL}")

                # 添加一个系统消息到对话历史，告知上下文切换
                context_message = {
                    "role": "system",
                    "content": f"引擎切换通知：现在由{engine_name}引擎继续之前的对话。以下是之前的对话历史：\n"
                }

                # 显示历史对话给用户，以便新AI可以参考
                if self.shared_conversation_history:
                    print(f"{Fore.YELLOW}当前对话历史已传递给新引擎:{Style.RESET_ALL}")
                    for msg in self.shared_conversation_history[-self.max_history:]:
                        if isinstance(msg, dict) and "role" in msg and "content" in msg:
                            role = msg["role"]
                            content = msg["content"]
                            if role == "user":
                                print(f"{Fore.CYAN}用户: {content}{Style.RESET_ALL}")
                            elif role == "assistant":
                                print(f"{Fore.GREEN}AI: {content}{Style.RESET_ALL}")
                            elif role == "tool":
                                print(f"{Fore.MAGENTA}工具结果: {content}{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}已切换到AI引擎: {engine_name}{Style.RESET_ALL}")

            # 保存默认引擎配置
            try:
                set_system_config('default_engine', engine_name)
                print(f"{Fore.CYAN}已将 {engine_name} 设置为默认引擎{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.YELLOW}警告: 保存默认引擎配置失败: {e}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}未找到AI引擎: {engine_name}{Style.RESET_ALL}")

    def _set_shared_conversation_history(self):
        """为所有引擎设置共享对话历史"""
        for engine in self.engines.values():
            # 为每个引擎设置共享对话历史的引用
            engine.shared_conversation_history = self.shared_conversation_history
            engine.max_history = self.max_history

    def handle_engine_command(self, command):
        """处理引擎特定命令,例如Ollama引擎的模型切换"""
        if not hasattr(self.current_engine, 'handle_command'):
            return False  # 引擎不支持处理命令
        
        # 检查命令是否以引擎名称开头（如 "ollama streaming on"）
        # 如果是，则移除引擎名称前缀
        engine_name = getattr(self.current_engine, 'name', '')
        if engine_name and command.startswith(engine_name + ' '):
            actual_command = command[len(engine_name) + 1:].strip()
            return self.current_engine.handle_command(actual_command)
        
        # 否则直接处理命令
        return self.current_engine.handle_command(command)

    def handle_liugin_message(self, message: str, **kwargs) -> str:
        """
        处理插件转发的消息（如 QQ 群 @ 消息）
        
        Args:
            message: 插件转发的消息内容
            **kwargs: 额外的上下文信息（如 group_id, user_id 等）
        
        Returns:
            AI 的回复内容
        """
        try:
            print(f"{Fore.CYAN}[插件消息] {message[:100]}...{Style.RESET_ALL}")
            
            # 构建系统提示
            system_prompt = """你是一个智能助手，正在通过 QQ 机器人与用户交流。
请简洁、友好地回复用户的消息。回复时注意：
1. 回复要简洁明了，适合 QQ 群聊场景
2. 不要提及你是 AI 或机器人
3. 直接回答问题，不要加多余的前缀"""
            
            # 调用当前 AI 引擎处理
            if self.current_engine:
                # 使用 generate_response 方法（统一接口）
                response = self.current_engine.generate_response(message, system_prompt=system_prompt)
                
                if response:
                    print(f"{Fore.GREEN}[AI 回复] {response[:50]}...{Style.RESET_ALL}")
                    return response
                else:
                    return "抱歉，我暂时无法回复。"
            else:
                print(f"{Fore.RED}[插件消息] 没有可用的 AI 引擎{Style.RESET_ALL}")
                return "AI 引擎未初始化"
                
        except Exception as e:
            print(f"{Fore.RED}[插件消息] 处理失败: {e}{Style.RESET_ALL}")
            return f"处理消息时出错: {e}"

    def process_tool_call(self, tool_call_data):
        """处理工具调用(支持 Liugin 和 MCP 两种格式)"""
        try:
            tool_name = tool_call_data.get('tool')
            args = tool_call_data.get('args', '')
            
            # 检查是否是 MCP 格式调用（包含 arguments 对象）
            arguments = tool_call_data.get('arguments')
            
            # 使用 unified_tool_manager 的方法执行
            if UNIFIED_TOOL_MANAGER_AVAILABLE and hasattr(self.liugin_manager, 'execute'):
                if arguments and isinstance(arguments, dict):
                    # MCP 格式调用
                    result = self.liugin_manager.execute(tool_name, args, **arguments)
                else:
                    # Liugin 格式调用
                    result = self.liugin_manager.execute(tool_name, args)
                return result
            
            # 回退：直接调用 handler（旧逻辑）
            for tool in self.liugin_manager.tools:
                if tool['name'] == tool_name:
                    try:
                        result = tool['handler'](args)
                        if result is None:
                            result = "无结果"
                        return {"result": result}
                    except Exception as e:
                        return {"result": f"工具执行错误: {e}"}

            return {"result": f"未找到工具: {tool_name}"}

        except Exception as e:
            return {"result": f"处理工具调用时出错: {e}"}

    def process_tool_calls_concurrent(self, tool_calls_list):
        """并发批量执行工具调用，按顺序返回结果"""
        if not tool_calls_list:
            return []
        
        # 全局取消标志和线程锁
        cancel_event = threading.Event()
        history_lock = threading.Lock()
        
        def execute_single_tool(tool_data, index):
            """执行单个工具，带索引用于排序"""
            if cancel_event.is_set():
                return {"index": index, "result": "工具执行已取消"}
            
            try:
                result = self.process_tool_call(tool_data)
                tool_result = result.get('result', '无结果')
                # 线程安全地添加到对话历史
                with history_lock:
                    self.shared_conversation_history.append({
                        "role": "assistant",
                        "content": f"工具{index+1}执行结果:\n{tool_result}"
                    })
                return {"index": index, "result": tool_result}
            except Exception as e:
                error_msg = f"工具执行错误: {e}"
                with history_lock:
                    self.shared_conversation_history.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                return {"index": index, "result": error_msg}
        
        # ESC键检测辅助函数（Windows专用）
        def supports_esc_detection():
            """检查是否支持ESC键检测"""
            return sys.platform == 'win32'
        
        def check_key_input():
            """检查是否有键盘输入"""
            try:
                import msvcrt
                return msvcrt.kbhit()
            except:
                return False
        
        def get_key():
            """获取键盘输入"""
            try:
                import msvcrt
                return msvcrt.getch()
            except:
                return None
        
        # ESC键检测线程（仅Windows支持）
        def detect_esc_key():
            if supports_esc_detection():
                while not cancel_event.is_set() and not all(f.done() for f in futures):
                    if check_key_input():
                        key = get_key()
                        if key == b'\x1b':  # ESC键
                            cancel_event.set()
                            break
                    time.sleep(0.1)
        
        # 使用线程池并发执行
        with ThreadPoolExecutor(max_workers=min(len(tool_calls_list), 10)) as executor:
            # 提交所有任务
            futures = {executor.submit(execute_single_tool, tool_data, i): i 
                      for i, tool_data in enumerate(tool_calls_list)}
            
            # 启动ESC检测线程
            esc_thread = threading.Thread(target=detect_esc_key, daemon=True)
            esc_thread.start()
            
            # 收集结果
            results = []
            for future in as_completed(futures):
                if cancel_event.is_set():
                    # 如果被取消，等待所有任务完成（它们会返回取消信息）
                    for f in futures:
                        if not f.done():
                            f.cancel()
                    break
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    index = futures[future]
                    results.append({"index": index, "result": f"工具执行错误: {e}"})
            
            # 按索引排序，保持AI指定的顺序
            results.sort(key=lambda x: x['index'])
            
            return [r['result'] for r in results]

    def _execute_single_tool(self, tool_data):
        """执行单个工具（带延迟和ESC检测）"""
        import sys
        import time

        tool_name = tool_data.get('tool', '未知工具')
        tool_args = tool_data.get('args', '')
        if len(tool_args) > 30:
            tool_args_display = tool_args[:27] + "..."
        else:
            tool_args_display = tool_args

        # TUI 模式下不做延迟和 ESC 检测（无键盘输入）
        if not self.tui_output_callback:
            try:
                import msvcrt
                canceled = False
                spinners = ['⊶', '⊷']
                spinner_index = 0
                for i in range(25):
                    if msvcrt.kbhit():
                        key = msvcrt.getch()
                        if key == b'\x1b':
                            canceled = True
                            break
                    spinner = spinners[spinner_index % 2]
                    spinner_index += 1
                    loading_message = f"   正在执行: {spinner} {tool_name} {tool_args_display} (按ESC取消)"
                    sys.stdout.write(f"\r{loading_message}")
                    sys.stdout.flush()
                    time.sleep(0.2)
                sys.stdout.write("\r" + " " * 60 + "\r")
                sys.stdout.flush()
                if canceled:
                    print(f"{Fore.YELLOW}工具执行已取消（用户按ESC键）{Style.RESET_ALL}")
                    cancel_message = f"工具 {tool_name} 执行已被用户取消（按ESC键）。工具参数: {tool_args}"
                    self.shared_conversation_history.append({
                        "role": "assistant",
                        "content": cancel_message
                    })
                    return True
            except ImportError:
                pass

        # 调用工具
        tool_results = self.process_tool_call(tool_data)
        full_result = tool_results.get('result', '无结果')
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 显示工具结果
        self._display_tool_result(tool_name, tool_args, full_result, current_time)
        # 将工具结果作为新的输入传递给AI
        current_input = f"工具调用结果 (时间: {current_time}):\n{full_result}"
        # 添加到对话历史
        self.shared_conversation_history.append({
            "role": "assistant",
            "content": f"工具调用结果 (时间: {current_time}):\n{full_result}"
        })
        # 继续循环
        self.process_conversation(current_input)

    def _execute_concurrent_tools(self, tool_calls_list):
        """并发批量执行工具调用"""
        if not tool_calls_list:
            return
        
        import sys
        import msvcrt
        
        # 显示批量执行提示
        self._output(f"   正在批量执行 {len(tool_calls_list)} 个工具")
        
        # 并发执行所有工具
        results = self.process_tool_calls_concurrent(tool_calls_list)
        
        # 获取当前时间
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 显示每个工具的结果
        for i, (tool_data, result) in enumerate(zip(tool_calls_list, results)):
            tool_name = tool_data.get('tool', '未知工具')
            tool_args = tool_data.get('args', '')
            self._display_tool_result(tool_name, tool_args, result, current_time)
        
        # 将所有结果合并传递给AI
        all_results = "\n".join([f"工具{i+1}结果:\n{result}" for i, result in enumerate(results)])
        current_input = f"批量工具调用结果 (时间: {current_time}):\n{all_results}"
        
        # 添加到对话历史
        self.shared_conversation_history.append({
            "role": "assistant",
            "content": f"批量工具调用结果 (时间: {current_time}):\n{all_results}"
        })
        
        # 继续循环
        self.process_conversation(current_input)

    def request_code_execution(self, liugin_name, code, timeout=None, variables=None, context=None):
        """
        插件代码执行请求接口
        
        Args:
            liugin_name: 请求执行的插件名称
            code: 要执行的Python代码
            timeout: 超时时间（秒），默认使用配置的超时时间
            variables: 要传递给代码的变量字典
            context: 上下文信息（可选）
            
        Returns:
            {
                'success': bool,  # 执行是否成功
                'result': str,    # 执行结果或错误信息
                'stdout': str,    # 标准输出
                'stderr': str,    # 标准错误
                'execution_time': float,  # 执行时间（秒）
                'memory_usage': int  # 内存使用（字节）
            }
        """
        if not self.code_execution_enabled:
            return {
                'success': False,
                'result': '代码执行功能已禁用',
                'stdout': '',
                'stderr': '',
                'execution_time': 0,
                'memory_usage': 0
            }
        
        # 安全检查：验证代码不包含危险操作
        if not self._is_code_safe(code):
            return {
                'success': False,
                'result': '代码包含潜在危险操作，已阻止执行',
                'stdout': '',
                'stderr': '',
                'execution_time': 0,
                'memory_usage': 0
            }
        
        # 设置超时
        exec_timeout = timeout if timeout is not None else self.code_execution_timeout
        
        # 记录执行历史
        execution_id = f"{liugin_name}_{int(time.time())}"
        execution_record = {
            'id': execution_id,
            'liugin_name': liugin_name,
            'code': code,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'context': context
        }
        
        try:
            # 使用多进程安全执行代码
            result = self._execute_code_safely(code, exec_timeout, variables)
            
            # 更新执行记录
            execution_record.update({
                'success': result['success'],
                'execution_time': result['execution_time'],
                'memory_usage': result['memory_usage']
            })
            
            # 添加到历史记录（最多保留100条）
            self.code_execution_history.append(execution_record)
            if len(self.code_execution_history) > 100:
                self.code_execution_history.pop(0)
            
            # 记录日志
            if result['success']:
                logger.info(f"代码执行成功 - 插件: {liugin_name}, 耗时: {result['execution_time']:.3f}s")
            else:
                logger.warning(f"代码执行失败 - 插件: {liugin_name}, 错误: {result['result']}")
            
            return result
            
        except Exception as e:
            error_msg = f"代码执行异常: {str(e)}"
            logger.error(f"{error_msg} - 插件: {liugin_name}")
            return {
                'success': False,
                'result': error_msg,
                'stdout': '',
                'stderr': error_msg,
                'execution_time': 0,
                'memory_usage': 0
            }
    
    def _is_code_safe(self, code):
        """
        检查代码是否安全（使用 AST 语法分析）
        
        Args:
            code: 要检查的Python代码
            
        Returns:
            bool: 代码是否安全
        """
        import ast
        import re
        
        # 危险模块黑名单
        DANGEROUS_MODULES = {
            'os', 'sys', 'subprocess', 'shutil', 'socket', 'pickle',
            'marshal', 'ctypes', 'multiprocessing', 'threading',
            'signal', 'resource', 'posix', 'nt', 'builtins',
            'importlib', 'code', 'codeop', 'commands', 'popen2',
        }
        
        # 危险函数/属性黑名单
        DANGEROUS_FUNCTIONS = {
            'exec', 'eval', 'compile', 'execfile', 'open',
            'input', 'raw_input', 'globals', 'locals', 'vars',
            'dir', 'getattr', 'setattr', 'delattr', 'hasattr',
            '__import__', '__builtins__', '__class__', '__bases__',
            '__subclasses__', '__mro__', '__dict__', '__getattribute__',
        }
        
        # 危险属性名称模式
        DANGEROUS_ATTRS = {
            '__builtins__', '__class__', '__bases__', '__subclasses__',
            '__mro__', '__dict__', '__globals__', '__code__', '__closure__',
            '__name__', '__file__', '__package__', '__loader__',
        }
        
        # 首先进行快速字符串检查
        dangerous_string_patterns = [
            r'__',           # 双下划线属性访问
            r'\beval\b',
            r'\bexec\b',
            r'\bcompile\b',
            r'\bglobals\b',
            r'\blocals\b',
            r'\bgetattr\b',
            r'\bsetattr\b',
            r'\b__import__\b',
        ]
        
        for pattern in dangerous_string_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return False
        
        # 使用 AST 进行更精确的分析
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # 语法错误，拒绝执行
            return False
        
        class SafetyVisitor(ast.NodeVisitor):
            def __init__(self):
                self.is_safe = True
                self.violations = []
            
            def check_name(self, name, context=""):
                if name in DANGEROUS_FUNCTIONS or name in DANGEROUS_ATTRS:
                    self.is_safe = False
                    self.violations.append(f"危险名称: {name} ({context})")
            
            def visit_Import(self, node):
                for alias in node.names:
                    module_name = alias.name.split('.')[0]
                    if module_name in DANGEROUS_MODULES:
                        self.is_safe = False
                        self.violations.append(f"危险导入: {alias.name}")
                self.generic_visit(node)
            
            def visit_ImportFrom(self, node):
                if node.module:
                    module_name = node.module.split('.')[0]
                    if module_name in DANGEROUS_MODULES:
                        self.is_safe = False
                        self.violations.append(f"危险导入: from {node.module}")
                self.generic_visit(node)
            
            def visit_Call(self, node):
                if isinstance(node.func, ast.Name):
                    self.check_name(node.func.id, "函数调用")
                elif isinstance(node.func, ast.Attribute):
                    self.check_name(node.func.attr, "属性调用")
                self.generic_visit(node)
            
            def visit_Attribute(self, node):
                self.check_name(node.attr, "属性访问")
                self.generic_visit(node)
            
            def visit_Name(self, node):
                self.check_name(node.id, "名称引用")
                self.generic_visit(node)
        
        visitor = SafetyVisitor()
        visitor.visit(tree)
        
        if not visitor.is_safe:
            logger.warning(f"代码安全检查失败: {visitor.violations}")
        
        return visitor.is_safe
    
    def _execute_code_safely(self, code, timeout, variables=None):
        """
        在安全沙箱中执行代码
        
        Args:
            code: 要执行的Python代码
            timeout: 超时时间（秒）
            variables: 要传递的变量字典
            
        Returns:
            执行结果字典
        """
        import io
        import traceback
        from contextlib import redirect_stdout, redirect_stderr
        
        # 准备变量
        exec_vars = {}
        if variables:
            exec_vars.update(variables)
        
        # 添加安全的内置函数和模块
        safe_builtins = {
            'print': print,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            'range': range,
            'enumerate': enumerate,
            'zip': zip,
            'sorted': sorted,
            'sum': sum,
            'max': max,
            'min': min,
            'abs': abs,
            'round': round,
            'bool': bool,
            'type': type,
            'isinstance': isinstance,
            'hasattr': hasattr,
        }
        
        # 添加用户输入确认函数（仅在安全沙箱中允许）
        def ask_user_confirmation(prompt, operation_id):
            """
            在代码执行中请求用户确认
            
            参数:
                prompt: 提示信息
                operation_id: 操作ID
                
            返回:
                用户输入的确认信息
            """
            print(f"\n{Fore.YELLOW}{'='*60}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}⚠️  需要用户确认{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{'='*60}{Style.RESET_ALL}\n")
            print(f"{Fore.CYAN}{prompt}{Style.RESET_ALL}\n")
            print(f"{Fore.GREEN}操作ID: {operation_id}{Style.RESET_ALL}\n")
            print(f"{Fore.YELLOW}请输入您的选择（y/yes 允许，其他拒绝）：{Style.RESET_ALL} ", end='', flush=True)
            
            # 获取用户输入
            user_input = input().strip().lower()
            
            # 存储用户决定
            self.user_input_queue[operation_id] = user_input
            
            print(f"\n{Fore.YELLOW}{'='*60}{Style.RESET_ALL}\n")
            
            return user_input
        
        safe_builtins['ask_user_confirmation'] = ask_user_confirmation
        
        # 添加白名单模块
        for module_name in self.code_execution_whitelist:
            try:
                safe_builtins[module_name] = __import__(module_name)
            except ImportError:
                pass
        
        exec_vars.update(safe_builtins)
        
        # 创建输出捕获器
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        # 执行代码
        start_time = time.time()
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # 使用超时执行
                result = {'success': True, 'error': None}
                
                def execute_with_timeout():
                    try:
                        exec(code, exec_vars)
                    except Exception as e:
                        result['success'] = False
                        result['error'] = str(e)
                        result['traceback'] = traceback.format_exc()
                
                # 创建超时线程
                import threading
                exec_thread = threading.Thread(target=execute_with_timeout)
                exec_thread.daemon = True
                exec_thread.start()
                exec_thread.join(timeout=timeout)
                
                if exec_thread.is_alive():
                    return {
                        'success': False,
                        'result': f'代码执行超时（超过{timeout}秒）',
                        'stdout': stdout_capture.getvalue(),
                        'stderr': stderr_capture.getvalue(),
                        'execution_time': timeout,
                        'memory_usage': 0
                    }
                
                # 获取执行结果
                if result['success']:
                    # 尝试获取代码中的 'result' 变量
                    exec_result = exec_vars.get('result', None)
                    if exec_result is not None:
                        result_str = str(exec_result)
                    else:
                        result_str = '代码执行成功（无返回值）'
                    
                    return {
                        'success': True,
                        'result': result_str,
                        'stdout': stdout_capture.getvalue(),
                        'stderr': stderr_capture.getvalue(),
                        'execution_time': time.time() - start_time,
                        'memory_usage': 0  # 简化版暂不跟踪内存
                    }
                else:
                    return {
                        'success': False,
                        'result': f"代码执行错误: {result['error']}",
                        'stdout': stdout_capture.getvalue(),
                        'stderr': stderr_capture.getvalue() + '\n' + result['traceback'],
                        'execution_time': time.time() - start_time,
                        'memory_usage': 0
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'result': f"代码执行异常: {str(e)}",
                'stdout': stdout_capture.getvalue(),
                'stderr': stderr_capture.getvalue() + '\n' + traceback.format_exc(),
                'execution_time': time.time() - start_time,
                'memory_usage': 0
            }
    
    def get_code_execution_history(self, limit=10):
        """
        获取代码执行历史
        
        Args:
            limit: 返回的最大条数
            
        Returns:
            执行历史列表
        """
        return self.code_execution_history[-limit:]
    
    def clear_code_execution_history(self):
        """清空代码执行历史"""
        self.code_execution_history = []
        logger.info("代码执行历史已清空")
    
    def set_code_execution_timeout(self, timeout):
        """
        设置代码执行超时时间
        
        Args:
            timeout: 超时时间（秒）
        """
        if timeout > 0:
            self.code_execution_timeout = timeout
            logger.info(f"代码执行超时时间已设置为 {timeout} 秒")
    
    def set_code_execution_whitelist(self, modules):
        """
        设置允许导入的模块白名单
        
        Args:
            modules: 模块名称列表
        """
        self.code_execution_whitelist = modules
        logger.info(f"代码执行模块白名单已更新: {modules}")

    def _display_tool_result(self, tool_name, tool_args, full_result, current_time):
        """显示工具执行结果"""
        if full_result is None:
            full_result = "无结果"

        self._output("")
        user_id_display = f"[用户ID: {self.user_id}]"
        is_error = full_result.startswith("错误:") or full_result.startswith("错误：") or full_result.startswith("工具执行错误")

        if self.tui_output_callback:
            # TUI 模式：使用 Textual 标记
            if is_error:
                self._output(f"[red]  X 工具: {tool_name}[/]")
                self._output(f"[red]  参数: {tool_args} {user_id_display}[/]")
            else:
                self._output(f"[green]  OK 工具: {tool_name}[/]")
                self._output(f"[green]  参数: {tool_args} {user_id_display}[/]")
        else:
            # CLI 模式：使用 colorama
            if is_error:
                self._output(f"{Fore.RED}     X 工具: {tool_name}{Style.RESET_ALL}")
                self._output(f"{Fore.RED}     参数: {tool_args} {user_id_display}{Style.RESET_ALL}")
            else:
                self._output(f"{Fore.GREEN}     OK 工具: {tool_name}{Style.RESET_ALL}")
                self._output(f"{Fore.GREEN}     参数: {tool_args} {user_id_display}{Style.RESET_ALL}")

        display_result = self._limit_output_lines(full_result, max_lines=2)
        color_tag = "red" if is_error else "green"
        for line in display_result.split('\n'):
            if self.tui_output_callback:
                self._output(f"[{color_tag}]       {line}[/]")
            else:
                color = Fore.RED if is_error else Fore.GREEN
                self._output(f"{color}          {line}{Style.RESET_ALL}")

    def display_image_in_terminal(self, image_path, width=None):
        """在终端中显示图片（优先使用 ASCII 艺术，然后是系统查看器）
        
        Args:
            image_path: 图片文件路径
            width: 可选，指定ASCII图片的宽度（字符数）。如果为None，则自动适应终端宽度
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(image_path):
                print(f"{Fore.RED}错误: 图片文件不存在: {image_path}{Style.RESET_ALL}")
                return False
            
            # 检查文件扩展名
            valid_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']
            if not os.path.splitext(image_path)[1].lower() in valid_extensions:
                print(f"{Fore.RED}错误: 不支持的图片格式。支持的格式: {', '.join(valid_extensions)}{Style.RESET_ALL}")
                return False
            
            # 获取图片信息
            try:
                from PIL import Image
                with Image.open(image_path) as img:
                    img_size = img.size
                    img_format = img.format
                    file_size = os.path.getsize(image_path)
                    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}图片预览: {os.path.basename(image_path)}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
                    print(f"{Fore.GREEN}  格式: {img_format}{Style.RESET_ALL}")
                    print(f"{Fore.GREEN}  尺寸: {img_size[0]} x {img_size[1]} 像素{Style.RESET_ALL}")
                    print(f"{Fore.GREEN}  大小: {file_size / 1024:.2f} KB{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
            except ImportError:
                print(f"\n{Fore.CYAN}图片预览: {os.path.basename(image_path)}{Style.RESET_ALL}")
            
            # 方法1: 使用色块显示（高分辨率，彩色）
            try:
                from PIL import Image
                
                # 获取终端尺寸
                terminal_size = shutil.get_terminal_size()
                terminal_width = terminal_size.columns
                terminal_height = terminal_size.lines - 5  # 预留空间给信息
                
                # 如果未指定宽度，则使用终端宽度的100%
                if width is None:
                    width = min(250, terminal_width)
                
                # 读取图片
                with Image.open(image_path) as img:
                    # 调整大小以适应终端
                    img_width, img_height = img.size
                    
                    # 使用四分之一块，每个字符显示 2x2 像素
                    # 所以实际可以显示的像素是字符的 2 倍宽、2 倍高
                    pixel_width = width * 2
                    pixel_height = (terminal_height - 2) * 2
                    
                    # 计算缩放比例（保持宽高比）
                    scale = min(pixel_width / img_width, pixel_height / img_height)
                    # 适当放大，充分利用空间
                    scale = min(scale * 1.1, 1.0)
                    
                    new_width = int(img_width * scale)
                    new_height = int(img_height * scale)
                    
                    # 确保至少有一定的尺寸
                    new_width = max(new_width, 80)
                    new_height = max(new_height, 40)
                    
                    # 调整图片大小
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                    
                    # 转换为 RGB
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # 获取像素数据
                    pixels = img.load()
                    
                    print(f"{Fore.YELLOW}正在生成色块图片 ({new_width}x{new_height} 像素)...{Style.RESET_ALL}")
                    
                    # 使用四分之一块字符
                    # 每个字符显示 2x2 像素块
                    # 字符映射：
                    # 左上  右上
                    # 左下  右下
                    
                    block_chars = {
                        (False, False, False, False): ' ',  # 空
                        (True,  False, False, False): '▘',  # 左上
                        (False, True,  False, False): '▝',  # 右上
                        (True,  True,  False, False): '▀',  # 上半
                        (False, False, True,  False): '▖',  # 左下
                        (True,  False, True,  False): '▌',  # 左半
                        (False, True,  True,  False): '▞',  # 右上+左下
                        (True,  True,  True,  False): '▛',  # 除右下
                        (False, False, False, True):  '▗',  # 右下
                        (True,  False, False, True):  '▚',  # 左上+右下
                        (False, True,  False, True):  '▐',  # 右半
                        (True,  True,  False, True):  '▜',  # 除左下
                        (False, False, True,  True):  '▄',  # 下半
                        (True,  False, True,  True):  '▙',  # 除右上
                        (False, True,  True,  True):  '▟',  # 除左上
                        (True,  True,  True,  True):  '█',  # 全块
                    }
                    
                    # 遍历 2x2 像素块
                    for y in range(0, new_height, 2):
                        line = []
                        for x in range(0, new_width, 2):
                            # 获取 2x2 像素的颜色
                            # 左上
                            if y < new_height and x < new_width:
                                r1, g1, b1 = pixels[x, y]
                                has_tl = True
                            else:
                                r1, g1, b1 = 0, 0, 0
                                has_tl = False
                            
                            # 右上
                            if y < new_height and x + 1 < new_width:
                                r2, g2, b2 = pixels[x + 1, y]
                                has_tr = True
                            else:
                                r2, g2, b2 = 0, 0, 0
                                has_tr = False
                            
                            # 左下
                            if y + 1 < new_height and x < new_width:
                                r3, g3, b3 = pixels[x, y + 1]
                                has_bl = True
                            else:
                                r3, g3, b3 = 0, 0, 0
                                has_bl = False
                            
                            # 右下
                            if y + 1 < new_height and x + 1 < new_width:
                                r4, g4, b4 = pixels[x + 1, y + 1]
                                has_br = True
                            else:
                                r4, g4, b4 = 0, 0, 0
                                has_br = False
                            
                            # 计算平均颜色（用于前景色）
                            all_pixels = [(r1, g1, b1), (r2, g2, b2), (r3, g3, b3), (r4, g4, b4)]
                            avg_r = sum(p[0] for p in all_pixels) // 4
                            avg_g = sum(p[1] for p in all_pixels) // 4
                            avg_b = sum(p[2] for p in all_pixels) // 4
                            
                            # 获取对应的块字符
                            char = block_chars.get((has_tl, has_tr, has_bl, has_br), ' ')
                            
                            # 使用前景色显示
                            fg_color = f"\033[38;2;{avg_r};{avg_g};{avg_b}m"
                            reset = "\033[0m"
                            line.append(f"{fg_color}{char}{reset}")
                        
                        # 打印一行
                        print(''.join(line))
                    
                    print(f"{Fore.GREEN}✓ 已使用色块显示 ({new_width}x{new_height} 像素){Style.RESET_ALL}\n")
                    return True
                
            except ImportError:
                print(f"{Fore.YELLOW}未安装 ascii-magic 库，尝试使用系统默认图片查看器...{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.YELLOW}ASCII 艺术显示失败: {e}，尝试使用系统默认图片查看器...{Style.RESET_ALL}")
            
            # 方法2: 使用系统默认图片查看器（备用方案）
            import platform
            import subprocess
            
            system = platform.system()
            
            if system == 'Windows':
                os.startfile(image_path)
                print(f"{Fore.GREEN}✓ 已在系统默认图片查看器中打开{Style.RESET_ALL}\n")
            elif system == 'Darwin':  # macOS
                subprocess.run(['open', image_path])
                print(f"{Fore.GREEN}✓ 已在系统默认图片查看器中打开{Style.RESET_ALL}\n")
            else:  # Linux
                subprocess.run(['xdg-open', image_path])
                print(f"{Fore.GREEN}✓ 已在系统默认图片查看器中打开{Style.RESET_ALL}\n")
            
            return True
            
        except Exception as e:
            print(f"{Fore.RED}显示图片失败: {str(e)}{Style.RESET_ALL}")
            return False

    def save_chat_history(self, name):
        """保存当前聊天记录到文件"""
        try:
            # 创建聊天记录数据
            chat_data = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "conversation": self.shared_conversation_history.copy()  # 使用共享历史
            }
            # 生成保存路径
            file_path = os.path.join(self.chat_history_dir, f"{name}.json")
            # 写入聊天记录
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(chat_data, f, ensure_ascii=False, indent=2, default=str)
            print(f"{Fore.GREEN}聊天记录已保存为: {name}{Style.RESET_ALL}")
            return True
        except Exception as e:
            print(f"{Fore.RED}保存聊天记录失败: {e}{Style.RESET_ALL}")
            return False

    def list_chat_history(self):
        """列出所有已保存的聊天记录"""
        try:
            chat_files = [f for f in os.listdir(self.chat_history_dir) if f.endswith('.json')]
            if not chat_files:
                print(f"{Fore.YELLOW}没有已保存的聊天记录{Style.RESET_ALL}")
                return
            print(f"{Fore.GREEN}已保存的聊天记录:{Style.RESET_ALL}")
            for i, file in enumerate(chat_files, 1):
                # 获取文件修改时间
                file_path = os.path.join(self.chat_history_dir, file)
                mod_time = os.path.getmtime(file_path)
                mod_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mod_time))
                # 去掉.json扩展名显示
                chat_name = file[:-5]  # 移除".json"
                print(f"{Fore.GREEN}{i}. {chat_name} (保存时间: {mod_time_str}){Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}列出聊天记录失败: {e}{Style.RESET_ALL}")

    def load_chat_history(self, name):
        """加载指定的聊天记录"""
        try:
            file_path = os.path.join(self.chat_history_dir, f"{name}.json")
            if not os.path.exists(file_path):
                print(f"{Fore.RED}聊天记录 '{name}' 不存在{Style.RESET_ALL}")
                return False
            with open(file_path, 'r', encoding='utf-8') as f:
                chat_data = json.load(f)
            # 恢复聊天记录历史到共享历史
            self.shared_conversation_history = chat_data.get("conversation", [])  # 使用共享历史
            # 将共享对话历史传递给所有引擎
            self._set_shared_conversation_history()
            print(f"{Fore.GREEN}已加载聊天记录: {name}{Style.RESET_ALL}")
            # 显示加载的对话历史摘要
            if self.shared_conversation_history:
                print(f"{Fore.CYAN}加载了 {len(self.shared_conversation_history)} 条对话记录{Style.RESET_ALL}")
            return True
        except Exception as e:
            print(f"{Fore.RED}加载聊天记录失败: {e}{Style.RESET_ALL}")
            return False

    def show_help(self):
        """显示帮助信息"""
        help_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "HELP.md")
        if os.path.exists(help_file_path):
            try:
                with open(help_file_path, 'r', encoding='utf-8') as f:
                    help_content = f.read()
                print(help_content)
            except Exception as e:
                print(f"读取帮助文件失败: {e}")
                self._show_basic_help()
        else:
            self._show_basic_help()

    def show_liugin_help(self, liugin_name):
        """显示特定插件的帮助信息"""
        # 首先检查是否为AI引擎插件
        if liugin_name in self.engines:
            engine = self.engines[liugin_name]
            print(f"{Fore.GREEN}AI引擎 '{liugin_name}' 的帮助信息:{Style.RESET_ALL}")
            # 显示引擎名称
            engine_name = getattr(engine, 'name', liugin_name)
            print(f"{Fore.GREEN}引擎名称: {engine_name}{Style.RESET_ALL}")
            # 如果引擎有提供帮助信息的方法,调用它
            if hasattr(engine, 'get_help_info'):
                help_info = engine.get_help_info()
                if isinstance(help_info, str):
                    print(f"{Fore.GREEN}帮助信息:{Style.RESET_ALL}")
                    print(help_info)
                elif isinstance(help_info, dict):
                    for key, value in help_info.items():
                        print(f"{Fore.GREEN}{key}: {value}{Style.RESET_ALL}")
            else:
                # 显示引擎特定命令信息
                print(f"{Fore.GREEN}可用命令:{Style.RESET_ALL}")
                print(f"  /engine.{liugin_name} <命令> - 执行{liugin_name}引擎的特定命令")
                print(f"{Fore.GREEN}示例:{Style.RESET_ALL}")
                print(f"  /engine.{liugin_name} help - 查看{liugin_name}引擎的详细帮助")
            return
        # 查找匹配的插件
        for tool in self.liugin_manager.tools:
            # 检查插件名称是否匹配
            if tool.get('name') == liugin_name:
                # 显示插件帮助信息
                print(f"{Fore.GREEN}插件 '{liugin_name}' 的帮助信息:{Style.RESET_ALL}")
                # 显示插件描述
                description = tool.get('description', '无描述')
                print(f"{Fore.GREEN}描述: {description}{Style.RESET_ALL}")
                # 显示插件用法
                if 'usage' in tool:
                    print(f"{Fore.GREEN}用法:{Style.RESET_ALL}")
                    print(f"  {tool['usage']}")
                else:
                    print(f"{Fore.YELLOW}该插件未提供具体用法信息{Style.RESET_ALL}")
                # 显示插件关键词
                if 'keywords' in tool:
                    keywords = tool['keywords']
                    if isinstance(keywords, list):
                        print(f"{Fore.GREEN}关键词: {', '.join(keywords)}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.GREEN}关键词: {keywords}{Style.RESET_ALL}")
                return
        # 如果没有找到匹配的插件或引擎
        print(f"{Fore.RED}未找到插件或引擎 '{liugin_name}'{Style.RESET_ALL}")
        # 显示所有可用插件和引擎
        print(f"{Fore.YELLOW}可用AI引擎:{Style.RESET_ALL}")
        for engine_name in self.engines.keys():
            print(f"{Fore.YELLOW}  - {engine_name}{Style.RESET_ALL}")
        if self.liugin_manager.tools:
            print(f"{Fore.YELLOW}可用插件:{Style.RESET_ALL}")
            for tool in self.liugin_manager.tools:
                tool_name = tool.get('name', '未知插件')
                tool_description = tool.get('description', '无描述')
                print(f"{Fore.YELLOW}  - {tool_name}: {tool_description}{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}当前没有加载任何插件{Style.RESET_ALL}")

    def _show_basic_help(self):
        """显示基本帮助信息"""
        help_text = """
小狸 Pro-CLI 帮助信息
==================
基本命令:
  /help              - 显示此帮助信息
  /help <插件名>      - 显示特定插件的帮助信息
  /quit              - 退出程序
  /tui               - 切换到 TUI 模式
  /model <引擎名>     - 切换AI引擎 (当前支持: """
        # 动态添加可用引擎
        available_engines = []
        for engine_name in self.engines.keys():
            available_engines.append(engine_name)
        help_text += ", ".join(available_engines) + ")"
        help_text += r"""
文件操作命令:
  /file.read <文件名> [行数] - 直接读取文件内容, 可指定读取行数
  @文件路径                 - 发送时自动读取文件内容并拼接（支持多文件）
                           例如: 请分析这个文件 @c:\test.py
                           例如: @c:\test.py @c:\config.json 帮我分析
  @图片路径                 - 自动分析图片并获取描述（支持PNG/JPG/GIF等）
                           例如: 请描述这张图片 @c:\photo.png
                           例如: @c:\photo.png 这个图片里有什么？
图像分析命令:
  /image analyze <图片路径>  - 详细分析图片
  /image ocr <图片路径>     - OCR文字识别
  /image quick <图片路径>   - 快速描述
  /image model <模型名>     - 切换视觉模型
  /image models             - 列出可用模型
  /image engine <引擎名>    - 切换识别引擎
  /image engines            - 列出所有引擎
  /img <操作> <参数>        - 简写形式
引擎管理命令:
""" + self._get_engine_commands_help() + """
  /engine.<命令>     - 执行引擎特定命令(如Ollama引擎的模型切换)
插件命令:
  插件可以注册自定义命令, 使用 /<命令名> 的格式调用
聊天记录命令:
  /chat save <名称>   - 保存当前聊天记录
  /chat list         - 查看所有已保存的聊天记录
  /chat open <名称>   - 加载聊天记录
深度思考处理命令:
  /thinking <内容>    - 处理深度思考AI返回的内容, 只提取回复部分
插件工具:
  AI可以自动调用以下工具来帮助您:
"""
        # 显示可用的插件工具
        if self.liugin_manager.tools:
            for tool in self.liugin_manager.tools:
                tool_name = tool.get('name', '未知工具')
                tool_description = tool.get('description', '无描述')
                help_text += f"  {tool_name}: {tool_description}\n"
                if 'usage' in tool:
                    help_text += f"    用法: {tool['usage']}\n"
        else:
            help_text += "  当前没有可用的工具插件\n"
        help_text += """
使用说明:
  - 直接输入自然语言与AI对话
  - AI会根据您的请求自动决定是否需要调用工具
  - 工具调用结果会显示在屏幕上
  - 可以随时保存和加载聊天记录
  - 使用/thinking命令可以处理深度思考AI返回的内容, 只显示回复部分
"""
        print(help_text)

    def run_tui(self):
        """运行 TUI 模式"""
        if not TEXTUAL_AVAILABLE:
            print(f"{Fore.RED}TUI 模式不可用：Textual 库未安装{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}请运行: pip install textual{Style.RESET_ALL}")
            return
        app = TUIMainApp(self)
        app.run()

    def run(self):
        """运行 CLI"""
        # 获取机器码作为用户ID
        import uuid
        self.user_id = str(uuid.getnode())
        print(f"{Fore.GREEN}小狸 Pro-CLI 已启动!{Style.RESET_ALL}")
        print(f"{Fore.GREEN}用户ID: {self.user_id}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/help' 查看帮助信息{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/quit' 退出程序{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/tui' 切换到 TUI 模式{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/engine list' 查看可用AI引擎{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/engine switch <引擎名>' 切换AI引擎{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/file.read <文件名> [行数]' 直接读取文件内容{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '@文件路径' 自动读取文件内容并发送给AI{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '@图片路径' 自动分析图片并发送描述给AI{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/image engines' 查看图像识别引擎{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/chat save <名称>' 保存当前聊天记录{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/chat list' 查看所有已保存的聊天记录{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/chat open <名称>' 加载聊天记录{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/remote' 查看远程连接帮助{Style.RESET_ALL}")
        current_engine_name = getattr(self.current_engine, 'name', '未设置') if self.current_engine else '未设置'
        print(f"{Fore.GREEN}当前使用的AI引擎: {current_engine_name}{Style.RESET_ALL}")
        # 显示已加载的引擎
        loaded_engines = list(self.engines.keys())
        if len(loaded_engines) > 1:
            print(f"{Fore.GREEN}已加载的AI引擎: {', '.join(loaded_engines)}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'-' * 50}{Style.RESET_ALL}")
        # 运行 CLI 主循环
        self._run_cli_loop()

    def _process_file_paths(self, user_input):
        """处理用户输入中的 @文件路径 语法，读取文件内容并拼接
        
        格式: @文件路径
        例如: @c:\test.py
        
        返回: 处理后的文本内容
        """
        import re
        
        # 支持的图片格式
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg'}
        
        # 匹配 @文件路径 格式（支持带引号的路径和空格，以及Windows路径）
        # 匹配模式: @"路径" 或 @路径（包括反斜杠）
        # 注意：使用非贪婪匹配，避免匹配到后面的空格
        pattern = r'@"([^"]+)"|@([^\s]+)'
        matches = list(re.finditer(pattern, user_input))
        
        if not matches:
            return user_input
        
        result_parts = []
        last_pos = 0
        
        for match in matches:
            # 添加匹配位置之前的普通文本
            if match.start() > last_pos:
                result_parts.append(user_input[last_pos:match.start()])
            
            # 获取文件路径（引号或无引号）
            file_path = match.group(1) or match.group(2)
            
            # 检查file_path是否为None
            if not file_path:
                continue
            
            # 规范化路径（处理 Windows 路径）
            file_path = os.path.normpath(file_path)
            
            # 尝试读取文件
            try:
                if os.path.exists(file_path):
                    # 检查是否为目录
                    if os.path.isdir(file_path):
                        # 处理目录 - 列出目录中的文件（不包含子目录）
                        print(f"{Fore.CYAN}检测到目录: {file_path}{Style.RESET_ALL}")
                        
                        try:
                            # 获取目录中的所有文件和子目录
                            entries = os.listdir(file_path)
                            
                            # 只保留文件，过滤掉子目录
                            files = []
                            for entry in entries:
                                full_path = os.path.join(file_path, entry)
                                if os.path.isfile(full_path):
                                    files.append(entry)
                            
                            if not files:
                                result_parts.append(f"[目录: {file_path} 为空]")
                                print(f"{Fore.YELLOW}目录为空: {file_path}{Style.RESET_ALL}")
                            else:
                                # 格式化文件列表
                                file_list_text = f"\n[目录: {file_path} - 共 {len(files)} 个文件]\n"
                                file_list_text += "=" * 50 + "\n"
                                
                                for i, filename in enumerate(sorted(files), 1):
                                    full_path = os.path.join(file_path, filename)
                                    file_size = os.path.getsize(full_path)
                                    file_list_text += f"{i}. {filename} ({file_size} 字节)\n"
                                
                                file_list_text += "=" * 50 + "\n"
                                result_parts.append(file_list_text)
                                print(f"{Fore.GREEN}已列出目录内容: {file_path} ({len(files)} 个文件){Style.RESET_ALL}")
                        
                        except PermissionError:
                            result_parts.append(f"[错误: 无权限访问目录 {file_path}]")
                            print(f"{Fore.RED}无权限访问目录: {file_path}{Style.RESET_ALL}")
                        except Exception as e:
                            result_parts.append(f"[错误: 无法读取目录 {file_path} - {str(e)}]")
                            print(f"{Fore.RED}无法读取目录 {file_path}: {e}{Style.RESET_ALL}")
                    
                    # 检查是否为图片文件
                    else:
                        file_ext = os.path.splitext(file_path)[1].lower()
                        is_image = file_ext in image_extensions
                        
                        if is_image:
                            # 处理图片文件 - 先在终端显示图片
                            print(f"{Fore.CYAN}检测到图片文件: {file_path}{Style.RESET_ALL}")
                            
                            # 在终端显示图片预览
                            try:
                                self.display_image_in_terminal(file_path)
                            except Exception as e:
                                print(f"{Fore.YELLOW}图片预览失败: {e}{Style.RESET_ALL}")
                            
                            # 查找图像分析插件（通用方式）
                            image_plugin = None
                            for tool in self.liugin_manager.tools:
                                tool_name = tool.get('name', '').lower()
                                tool_desc = tool.get('description', '').lower()
                                # 通过名称或描述识别图像分析插件
                                if 'image' in tool_name or 'analyze' in tool_name or '图片' in tool_desc:
                                    image_plugin = tool
                                    break
                            
                            if image_plugin:
                                try:
                                    print(f"{Fore.YELLOW}正在分析图片...{Style.RESET_ALL}")
                                    image_result = image_plugin['handler'](f"analyze {file_path}")
                                    
                                    # 调试：打印图片分析结果
                                    if image_result:
                                        print(f"{Fore.MAGENTA}图片分析结果: {image_result[:100]}...{Style.RESET_ALL}" if len(image_result) > 100 else f"{Fore.MAGENTA}图片分析结果: {image_result}{Style.RESET_ALL}")
                                        # 将图片描述添加到结果
                                        result_parts.append(f" {image_result}")
                                        print(f"{Fore.GREEN}图片分析完成，已添加到输入{Style.RESET_ALL}")
                                    else:
                                        print(f"{Fore.YELLOW}图片分析返回空结果{Style.RESET_ALL}")
                                        result_parts.append(f" [图片: {file_path}]")
                                except Exception as e:
                                    result_parts.append(f"[错误: 图片分析失败 - {str(e)}]")
                                    print(f"{Fore.RED}图片分析失败: {e}{Style.RESET_ALL}")
                            else:
                                result_parts.append(f"[错误: 图像分析插件未加载]")
                                print(f"{Fore.RED}图像分析插件未加载{Style.RESET_ALL}")
                        
                        # 处理文本文件（非图片）
                        else:
                            # 检查文件大小
                            file_size = os.path.getsize(file_path)
                            if file_size > MAX_FILE_SIZE:
                                result_parts.append(f"[错误: 文件 {file_path} 超过大小限制 ({MAX_FILE_SIZE} 字节)]")
                                print(f"{Fore.YELLOW}警告: 文件 {file_path} 超过大小限制，已跳过{Style.RESET_ALL}")
                            else:
                                # 尝试读取文件内容
                                try:
                                    with open(file_path, 'r', encoding='utf-8') as f:
                                        file_content = f.read()
                                    # 添加文件内容到结果
                                    result_parts.append(f"\n[文件: {file_path}]\n{file_content}\n")
                                    print(f"{Fore.GREEN}已读取文件: {file_path} ({len(file_content)} 字符){Style.RESET_ALL}")
                                except UnicodeDecodeError:
                                    # 尝试其他编码
                                    try:
                                        with open(file_path, 'r', encoding='gbk') as f:
                                            file_content = f.read()
                                        result_parts.append(f"\n[文件: {file_path}]\n{file_content}\n")
                                        print(f"{Fore.GREEN}已读取文件: {file_path} ({len(file_content)} 字符) [GBK编码]{Style.RESET_ALL}")
                                    except Exception as e:
                                        result_parts.append(f"[错误: 无法读取文件 {file_path} - {str(e)}]")
                                        print(f"{Fore.RED}无法读取文件 {file_path}: {e}{Style.RESET_ALL}")
                                except Exception as e:
                                    result_parts.append(f"[错误: 无法读取文件 {file_path} - {str(e)}]")
                                    print(f"{Fore.RED}无法读取文件 {file_path}: {e}{Style.RESET_ALL}")
                else:
                    result_parts.append(f"[错误: 文件 {file_path} 不存在]")
                    print(f"{Fore.RED}文件不存在: {file_path}{Style.RESET_ALL}")
                
                last_pos = match.end()
            except Exception as e:
                result_parts.append(f"[错误: 处理文件路径时出错 - {str(e)}]")
                print(f"{Fore.RED}处理文件路径时出错: {e}{Style.RESET_ALL}")
                last_pos = match.end()
        
        # 添加最后的部分
        if last_pos < len(user_input):
            result_parts.append(user_input[last_pos:])
        
        # 合并所有部分
        return ''.join(result_parts)

    def _run_cli_loop(self):
        """运行 CLI 主循环"""
        while True:
            try:
                user_input = input(f"\n{Fore.WHITE}> {Style.RESET_ALL}").strip()
                # 处理命令
                if user_input == '/quit':
                    print(f"{Fore.GREEN}再见!{Style.RESET_ALL}")
                    break
                if user_input == '/help':
                    self.show_help()
                    continue
                if user_input.startswith('/help '):
                    # 处理 /help <插件名> 命令
                    liugin_name = user_input[6:].strip()  # 移除 '/help '
                    self.show_liugin_help(liugin_name)
                    continue
                # 处理引擎相关命令
                if user_input.startswith('/engine '):
                    engine_command = user_input[8:].strip()  # 移除 '/engine '
                    # 使用动态注册的引擎命令处理
                    parts = engine_command.split(' ', 1)
                    cmd = parts[0]
                    args = parts[1] if len(parts) > 1 else ''
                    if cmd in self.engine_commands:
                        self.engine_commands[cmd](args)
                    else:
                        available_commands = ', '.join(self.engine_commands.keys())
                        print(f"{Fore.RED}未知的引擎命令.可用命令: {available_commands}{Style.RESET_ALL}")
                    continue
                # 处理引擎特定命令(如Ollama引擎的模型切换)
                if user_input.startswith('/engine.'):
                    engine_command = user_input[8:].strip()  # 移除 '/engine.'
                    if not self.handle_engine_command(engine_command):
                        print(f"{Fore.RED}当前引擎不支持该命令或命令执行失败{Style.RESET_ALL}")
                    continue
                # 处理文件读取命令
                if user_input.startswith('/file.read '):
                    # 解析命令参数
                    args = user_input[11:].strip()  # 移除 '/file.read '
                    parts = args.split(' ', 2)
                    if len(parts) < 1:
                        print(f"{Fore.RED}请提供文件名.用法: /file.read <文件名> [行数]{Style.RESET_ALL}")
                        continue
                    filename = parts[0]
                    max_lines = None
                    if len(parts) >= 2:
                        try:
                            max_lines = int(parts[1])
                            if max_lines <= 0:
                                print(f"{Fore.RED}行数必须是正整数{Style.RESET_ALL}")
                                continue
                        except ValueError:
                            print(f"{Fore.RED}行数必须是正整数{Style.RESET_ALL}")
                            continue
                    # 调用文件管理插件读取文件
                    result = self._read_file_direct(filename, max_lines)
                    print(f"{Fore.GREEN}{result}{Style.RESET_ALL}")
                    continue
                # 处理聊天记录命令
                if user_input.startswith('/chat '):
                    chat_command = user_input[6:].strip()  # 移除 '/chat '
                    if chat_command.startswith('save '):
                        name = chat_command[5:].strip()  # 移除 'save '
                        if name:
                            self.save_chat_history(name)
                        else:
                            print(f"{Fore.RED}请提供聊天记录名称.用法: /chat save <名称>{Style.RESET_ALL}")
                        continue
                    elif chat_command == 'list':
                        self.list_chat_history()
                        continue
                    elif chat_command.startswith('open '):
                        name = chat_command[5:].strip()  # 移除 'open '
                        if name:
                            self.load_chat_history(name)
                        else:
                            print(f"{Fore.RED}请提供聊天记录名称.用法: /chat open <名称>{Style.RESET_ALL}")
                        continue
                    else:
                        print(f"{Fore.RED}未知的聊天命令.可用命令: save, list, open{Style.RESET_ALL}")
                        continue
                # 处理远程连接命令
                if user_input.startswith('/remote'):
                    remote_command = user_input[7:].strip()  # 移除 '/remote'
                    self._handle_remote_command(remote_command)
                    continue
                # 处理 /about 命令
                if user_input == '/about':
                    self._read_about_file()
                    continue
                # 处理 /tui 命令 - 切换到 TUI 模式
                if user_input == '/tui':
                    print(f"{Fore.CYAN}正在切换到 TUI 模式...{Style.RESET_ALL}")
                    self.run_tui()
                    print(f"{Fore.CYAN}已从 TUI 模式返回 CLI 模式{Style.RESET_ALL}")
                    continue
                # 处理插件命令
                if user_input.startswith('/'):
                    command_parts = user_input[1:].split(' ', 1)  # 移除 '/' 并分割命令和参数
                    command = command_parts[0]
                    args = command_parts[1] if len(command_parts) > 1 else ""
                    if command in self.liugin_commands:
                        try:
                            result = self.liugin_commands[command](args)
                            if result:
                                # 限制输出为5行
                                result = self._limit_output_lines(result, max_lines=5)
                                print(f"{Fore.GREEN}{result}{Style.RESET_ALL}")
                        except Exception as e:
                            print(f"{Fore.RED}插件命令执行失败: {e}{Style.RESET_ALL}")
                        continue
                # 处理深度思考AI回复命令
                if user_input.startswith('/thinking '):
                    # 专门处理深度思考AI返回的内容，只提取回复部分
                    thinking_input = user_input[10:].strip()  # 移除 '/thinking '
                    processed_response = self.process_thinking_response(thinking_input)
                    # 处理 """ """ 代码块语法
                    processed_response = self._process_code_blocks(processed_response)
                    # 显示处理后的回复内容并附带用户ID(蓝色)
                    terminal_size = shutil.get_terminal_size()
                    terminal_width = terminal_size.columns
                    user_id_display = f"[用户ID: {self.user_id}]"
                    # 分行处理响应,确保换行符正确显示
                    response_lines = processed_response.split('\n')
                    for i, line in enumerate(response_lines):
                        # 在第一行（AI响应）前添加符号并留空格
                        if i == 0:
                            line = "✦ " + line
                        if i == len(response_lines) - 1:  # 最后一行添加用户ID
                            print(f"{line} {user_id_display}")
                        else:
                            print(f"{line}")
                    continue
                
                # 处理 @文件路径 语法
                if '@' in user_input:
                    # 检查是否包含 @文件路径 语法
                    processed_input = self._process_file_paths(user_input)
                    # 如果输入被处理（包含文件路径），使用处理后的内容
                    if processed_input != user_input:
                        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
                        user_input = processed_input
                        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
                        # 调试：打印处理后的输入
                        print(f"{Fore.MAGENTA}处理后的输入: {user_input[:200]}...{Style.RESET_ALL}" if len(user_input) > 200 else f"{Fore.MAGENTA}处理后的输入: {user_input}{Style.RESET_ALL}")
                
                # 生成AI响应 - 实现完整的工具调用循环
                self.process_conversation(user_input)
            except KeyboardInterrupt:
                # 显示退出信息并附带用户ID
                terminal_size = shutil.get_terminal_size()
                terminal_width = terminal_size.columns
                user_id_display = f"[用户ID: {self.user_id}]"
                print(f"\n{Fore.GREEN}再见! {user_id_display}{Style.RESET_ALL}")
                break
            except Exception as e:
                # 显示错误信息并附带用户ID
                terminal_size = shutil.get_terminal_size()
                terminal_width = terminal_size.columns
                user_id_display = f"[用户ID: {self.user_id}]"
                print(f"{Fore.RED}发生错误: {e} {user_id_display}{Style.RESET_ALL}")

    def _output(self, message):
        """统一输出方法，支持 TUI 和 CLI 模式"""
        if self.tui_output_callback:
            # TUI 模式：发送到 TUI 显示
            self.tui_output_callback(message)
        else:
            # CLI 模式：直接打印
            print(message)

    def _display_response(self, content, is_continue=False):
        """统一显示 AI 响应，支持 TUI 和 CLI 模式"""
        user_id_display = f"[用户ID: {self.user_id}]"
        response_lines = content.split('\n')
        if self.tui_output_callback:
            # TUI 模式：使用 Textual 标记
            for i, line in enumerate(response_lines):
                if i == 0:
                    prefix = "[yellow]>[/] " if is_continue else "[cyan]>[/] "
                    line = prefix + line
                if i == len(response_lines) - 1:
                    self._output(f"{line} {user_id_display}")
                else:
                    self._output(line)
            self._output("")
        else:
            # CLI 模式：使用 colorama
            for i, line in enumerate(response_lines):
                if i == 0:
                    prefix = f"{Fore.YELLOW}✦{Style.RESET_ALL} " if is_continue else "✦ "
                    line = prefix + line
                if i == len(response_lines) - 1:
                    print(f"{line} {user_id_display}")
                else:
                    print(f"{line}")
            print()

    def process_conversation(self, user_input):
        """处理完整的对话循环, 支持工具调用循环和AI继续操作循环"""
        # 添加用户输入到共享对话历史
        self.shared_conversation_history.append({
            "role": "user",
            "content": user_input
        })
        # 获取插件提示词
        liugin_prompts = self.get_liugin_usage_prompts()
        loop_count = 0
        current_input = user_input
        max_loops = 20  # 最大循环次数，防止AI无限循环
        while loop_count < max_loops:
            # 生成AI响应,传递插件提示词
            # 添加等待动画
            response = self._generate_response_with_animation(current_input, liugin_prompts=liugin_prompts)
            # 使用新的深度思考内容处理方法
            processed_response = self.process_thinking_response(response)
            # 处理 """ """ 代码块语法
            processed_response = self._process_code_blocks(processed_response)
            # 检查是否需要调用工具或继续操作
            try:
                # 首先尝试解析混合响应（文本+JSON指令）
                text_content, json_data = self._parse_mixed_response(processed_response)
                # 如果解析到了JSON数据，则优先处理JSON指令
                if json_data:
                    # 如果有文本内容，先显示给用户
                    if text_content:
                        # 处理 """ """ 代码块语法
                        text_content = self._process_code_blocks(text_content)
                        # 将文本内容添加到对话历史
                        self.shared_conversation_history.append({
                            "role": "assistant",
                            "content": text_content
                        })
                        # 显示文本内容
                        self._display_response(text_content)

                    # 判断JSON数据类型
                    if isinstance(json_data, dict):
                        # 单个工具调用
                        response_data = json_data

                        if response_data.get('action') == 'use_tool':
                            # 执行单个工具
                            canceled = self._execute_single_tool(response_data)
                            if canceled:
                                # 工具被用户取消，跳出循环（通用处理）
                                break
                            # 工具正常执行，继续处理
                            break

                        # 检查是否AI需要继续思考/操作
                        if (response_data.get('continue') is True or
                              response_data.get('need_continue') is True or
                              response_data.get('think_more') is True):
                            # AI需要继续操作，获取message字段的内容
                            continue_message = response_data.get('message', '')
                            if continue_message:
                                # 使用message字段的内容作为AI的响应
                                processed_response = continue_message
                                # 将AI的响应添加到对话历史
                                self.shared_conversation_history.append({
                                    "role": "assistant",
                                    "content": processed_response
                                })
                                # 显示AI的中间响应
                                self._display_response(processed_response, is_continue=True)
                            # 继续循环，让AI继续思考
                            loop_count += 1
                        # 检查是否有message字段，如果有则显示
                        elif response_data.get('message'):
                            message = response_data.get('message')
                            # 如果有文本内容，先显示文本内容
                            if text_content:
                                text_content = self._process_code_blocks(text_content)
                                self.shared_conversation_history.append({
                                    "role": "assistant",
                                    "content": text_content
                                })
                                self._display_response(text_content)
                            # 将AI响应添加到对话历史
                            self.shared_conversation_history.append({
                                "role": "assistant",
                                "content": message
                            })
                            # 显示最终结果
                            self._display_response(message)
                            break
                        else:
                            # 如果有文本内容，显示文本内容
                            if text_content:
                                text_content = self._process_code_blocks(text_content)
                                self.shared_conversation_history.append({
                                    "role": "assistant",
                                    "content": text_content
                                })
                                self._display_response(text_content)
                            else:
                                # 如果没有文本内容，将JSON响应添加到对话历史
                                self.shared_conversation_history.append({
                                    "role": "assistant",
                                    "content": processed_response
                                })
                            # 显示最终结果
                            self._display_response(processed_response)
                            break

                    elif isinstance(json_data, list):
                        # 批量工具调用
                        tool_calls = [item for item in json_data if isinstance(item, dict) and item.get('action') == 'use_tool']
                        if tool_calls:
                            # 执行批量并发工具
                            self._execute_concurrent_tools(tool_calls)
                            break
                        # 如果list里没有use_tool，检查是否有continue相关字段
                        continue_items = [item for item in json_data if isinstance(item, dict) and
                                         (item.get('continue') is True or
                                          item.get('need_continue') is True or
                                          item.get('think_more') is True)]
                        if continue_items:
                            continue_message = continue_items[0].get('message', '')
                            if continue_message:
                                processed_response = continue_message
                                self.shared_conversation_history.append({
                                    "role": "assistant",
                                    "content": processed_response
                                })
                                self._display_response(processed_response, is_continue=True)
                            loop_count += 1
                        else:
                            # 没有工具调用也没有continue，显示文本并结束
                            if text_content:
                                self.shared_conversation_history.append({
                                    "role": "assistant",
                                    "content": text_content
                                })
                            self._display_response(text_content or processed_response)
                            break
                else:
                    # 没有解析到JSON数据，直接显示文本内容或原始响应
                    display_content = text_content if text_content else processed_response
                    # 将AI响应添加到对话历史
                    self.shared_conversation_history.append({
                        "role": "assistant",
                        "content": display_content
                    })
                    # 显示最终结果
                    self._display_response(display_content)
                    break
            except json.JSONDecodeError:
                # 当JSON解析失败时，尝试解析混合内容
                text_content, json_data = self._parse_mixed_response(processed_response)
                if json_data:
                    if text_content:
                        text_content = self._process_code_blocks(text_content)
                        self.shared_conversation_history.append({
                            "role": "assistant",
                            "content": text_content
                        })
                        self._display_response(text_content)

                    if isinstance(json_data, dict):
                        response_data = json_data
                        if response_data.get('action') == 'continue':
                            continue_content = response_data.get('content', '')
                            if continue_content:
                                self.shared_conversation_history.append({
                                    "role": "assistant",
                                    "content": continue_content
                                })
                                self._display_response(continue_content)
                            continue

                        if response_data.get('action') == 'use_tool':
                            canceled = self._execute_single_tool(response_data)
                            if canceled:
                                break
                            break

                        if (response_data.get('continue') is True or
                              response_data.get('need_continue') is True or
                              response_data.get('think_more') is True):
                            continue_message = response_data.get('message', '')
                            if continue_message:
                                processed_response = continue_message
                                self.shared_conversation_history.append({
                                    "role": "assistant",
                                    "content": processed_response
                                })
                                self._display_response(processed_response, is_continue=True)
                            loop_count += 1
                        else:
                            message = response_data.get('message', '')
                            if message:
                                self.shared_conversation_history.append({
                                    "role": "assistant",
                                    "content": message
                                })
                                self._display_response(message)
                                loop_count += 1
                            else:
                                if text_content:
                                    self.shared_conversation_history.append({
                                        "role": "assistant",
                                        "content": text_content
                                    })
                                self._display_response(text_content or processed_response)
                                break

                    elif isinstance(json_data, list):
                        tool_calls = [item for item in json_data if isinstance(item, dict) and item.get('action') == 'use_tool']
                        if tool_calls:
                            self._execute_concurrent_tools(tool_calls)
                            break
                        continue_items = [item for item in json_data if isinstance(item, dict) and
                                         (item.get('continue') is True or
                                          item.get('need_continue') is True or
                                          item.get('think_more') is True)]
                        if continue_items:
                            continue_message = continue_items[0].get('message', '')
                            if continue_message:
                                processed_response = continue_message
                                self.shared_conversation_history.append({
                                    "role": "assistant",
                                    "content": processed_response
                                })
                                self._display_response(processed_response, is_continue=True)
                            loop_count += 1
                        else:
                            if text_content:
                                self.shared_conversation_history.append({
                                    "role": "assistant",
                                    "content": text_content
                                })
                            self._display_response(text_content or processed_response)
                            break
                else:
                    display_content = text_content if text_content else processed_response
                    self.shared_conversation_history.append({
                        "role": "assistant",
                        "content": display_content
                    })
                    self._display_response(display_content)
                break
        else:
            # 循环次数达到上限
            self._output(f"AI 已达到最大循环次数 ({max_loops})，已停止自动处理")
            self.shared_conversation_history.append({
                "role": "assistant",
                "content": f"已达到最大处理次数 ({max_loops})，已自动停止。如需继续处理，请重新输入。"
            })

    def _generate_response_with_animation(self, current_input, liugin_prompts=None):
        """生成AI响应并显示等待动画"""
        # TUI 模式：不做动画，直接生成响应
        if self.tui_output_callback:
            system_prompt = self._build_system_prompt(liugin_prompts)
            if not self.current_engine:
                return "错误: 当前没有可用的AI引擎，请检查ai_engines目录中的引擎插件"
            response = self.current_engine.generate_response(current_input, system_prompt=system_prompt)
            if response and self.shared_conversation_history is not None:
                self.shared_conversation_history.append({
                    "role": "assistant",
                    "content": response
                })
            return response

        # CLI 模式：带动画和 ESC 检测
        import threading
        import time
        import sys
        import random
        import os
        animation_running = True
        esc_pressed = threading.Event()
        love_sentences = []
        love_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "love.txt")
        if os.path.exists(love_file_path):
            try:
                with open(love_file_path, 'r', encoding='utf-8') as f:
                    love_sentences = [line.strip() for line in f.readlines() if line.strip()]
            except Exception as e:
                print(f"读取love.txt文件时出错: {e}")
        if not love_sentences:
            love_sentences = ["AI正在思考中...", "请稍等片刻...", "正在处理您的请求..."]

        def check_for_esc():
            try:
                import msvcrt
                while animation_running:
                    if msvcrt.kbhit():
                        key = msvcrt.getch()
                        if ord(key) == 27:
                            esc_pressed.set()
                            break
                    time.sleep(0.1)
            except ImportError:
                pass

        def show_animation():
            last_change_time = time.time()
            current_sentence = random.choice(love_sentences)
            while animation_running:
                current_time = time.time()
                if current_time - last_change_time >= 5:
                    current_sentence = random.choice(love_sentences)
                    last_change_time = current_time
                animation_chars = "|/-\\"
                char_idx = int((current_time * 10) % len(animation_chars))
                if len(current_sentence) > 50:
                    display_sentence = current_sentence[:47] + "..."
                else:
                    display_sentence = current_sentence
                print(f"\r{Fore.MAGENTA}{display_sentence} {animation_chars[char_idx]}{Style.RESET_ALL}", end="", flush=True)
                time.sleep(0.1)

        animation_thread = threading.Thread(target=show_animation)
        animation_thread.daemon = True
        animation_thread.start()
        esc_thread = threading.Thread(target=check_for_esc)
        esc_thread.daemon = True
        esc_thread.start()
        try:
            system_prompt = self._build_system_prompt(liugin_prompts)
            if not self.current_engine:
                return "错误: 当前没有可用的AI引擎，请检查ai_engines目录中的引擎插件"

            response = self.current_engine.generate_response(current_input, system_prompt=system_prompt)
            if response:
                self._typeprint(response, Fore.CYAN)

            if esc_pressed.is_set():
                print(f"\n{Fore.YELLOW}[AI请求已取消]{Style.RESET_ALL}")
                return "[AI请求已取消]"

            if response and self.shared_conversation_history is not None:
                self.shared_conversation_history.append({
                    "role": "assistant",
                    "content": response
                })

            return response
        finally:
            animation_running = False
            animation_thread.join()
            esc_thread.join()
            print("\r" + " " * 50 + "\r", end="", flush=True)

    def _typeprint(self, text, color=None, delay=0.01):
        """逐字输出文本，实现打字机效果"""
        for char in text:
            if color:
                print(f"{color}{char}{Style.RESET_ALL}", end="", flush=True)
            else:
                print(char, end="", flush=True)
            time.sleep(delay)
        print()  # 输出完成后换行

    def process_thinking_response(self, response):
        """处理深度思考AI返回的内容, 分离思考和回复内容
        这个方法用于处理那些包含思考过程和回复内容的AI响应
        思考内容用当前引擎的特定标记包围，以灰色文本显示给用户但不处理
        """
        try:
            # 尝试解析JSON格式的响应
            response_data = json.loads(response)
            # 如果是工具调用，直接返回
            if isinstance(response_data, dict) and response_data.get('action') == 'use_tool':
                return response
            # 如果是其他JSON格式，尝试提取回复内容
            if isinstance(response_data, dict):
                # 假设回复内容在'answer'或'response'字段中
                if 'answer' in response_data:
                    extracted_content = response_data['answer']
                elif 'response' in response_data:
                    extracted_content = response_data['response']
                elif 'content' in response_data:
                    extracted_content = response_data['content']
                elif 'text' in response_data:
                    extracted_content = response_data['text']
                else:
                    # 如果没有找到特定字段，返回整个JSON的字符串表示
                    return json.dumps(response_data, ensure_ascii=False, indent=2)

                # 提取内容后，继续检查是否包含思考标记
                return self._process_content_with_thinking(extracted_content)
        except json.JSONDecodeError:
            # 不是JSON格式，直接处理
            return self._process_content_with_thinking(response)
    
    def _process_content_with_thinking(self, content):
        """处理包含思考标记的内容"""
        # 检查当前引擎是否定义了思考标记
        thinking_start_marker = getattr(self.current_engine, 'thinking_start_marker', None) if self.current_engine else None
        thinking_end_marker = getattr(self.current_engine, 'thinking_end_marker', None) if self.current_engine else None

        # 支持多种思考标记格式
        # 格式1: <thinking>...</thinking>
        # 格式2: <think/>
        # 格式3: 自定义标记

        # 检查 <think/> 格式（Qwen3等模型使用）
        if '<think/>' in content:
            parts = content.split('<think/>')
            if len(parts) >= 2:
                thinking_content = parts[0].strip()
                reply_content = parts[1].strip()
                # 显示思考内容为灰色斜体文本
                if thinking_content:
                    print(f"{Fore.LIGHTBLACK_EX}{Style.DIM}[思考: {thinking_content}]{Style.RESET_ALL}")
                # 返回回复内容
                return reply_content if reply_content else ""

        # 检查 <thinking>...</thinking> 格式
        if thinking_start_marker and thinking_end_marker and thinking_start_marker in content and thinking_end_marker in content:
            parts = content.split(thinking_start_marker)
            if len(parts) > 1:
                remaining = parts[1]
                if thinking_end_marker in remaining:
                    thinking_part, reply_part = remaining.split(thinking_end_marker, 1)
                    thinking_content = thinking_part.strip()
                    reply_content = reply_part.strip()
                    # 显示思考内容为灰色斜体文本
                    if thinking_content:
                        print(f"{Fore.LIGHTBLACK_EX}{Style.DIM}[思考: {thinking_content}]{Style.RESET_ALL}")
                    # 返回回复内容
                    return reply_content if reply_content else ""

        # 没有找到思考标记，返回原始内容
        return content

    def _build_system_prompt(self, liugin_prompts=None):
        """构建系统提示词 - 增强版，支持编程任务"""
        base_prompt = """你叫小狸，是一个强大的智能编程助手。你具备以下核心能力：

1. **精准代码编辑** - 使用 code_editor 工具进行搜索替换、多文件批量编辑
2. **代码搜索与理解** - 使用 code_search 工具跨文件搜索、提取符号、分析依赖
3. **Git 版本控制** - 使用 git_tools 工具管理代码版本
4. **Shell 命令执行** - 使用 cmd_executor 执行系统命令
5. **文件管理** - 使用 file_manager 管理文件和目录

你在说话时可以适当加上'nyan'来表现可爱性格，但不要过度使用。"""

        # 检查 tool_search 是否存在
        has_tool_search = any(t.get('name') == 'tool_search' for t in self.liugin_manager.tools)

        tool_search_rule = ""
        if has_tool_search:
            tool_search_rule = """【工具查询规则】
调用不熟悉的工具前，先用 tool_search 查询用法：
{"action": "use_tool", "tool": "tool_search", "args": "工具名"}
例外：ai_search、code_editor、code_search、git_tools 可以直接使用。"""

        if liugin_prompts:
            prompt = f"""{base_prompt}

{liugin_prompts}

{tool_search_rule}

【工具调用格式】
在回复中包含 JSON 指令来执行操作：

1. 纯 JSON: {{"action": "use_tool", "tool": "code_editor", "args": "edit file.py old <<<>>> new"}}
2. 文本+JSON: 好的，我来修改。{{"action": "use_tool", "tool": "code_editor", "args": "edit file.py old <<<>>> new"}}

【编程工作流】
1. 理解需求 → 用 code_search.structure 查看项目结构
2. 定位代码 → 用 code_search.find 或 code_search.regex 搜索
3. 查看上下文 → 用 code_editor.read_range 查看相关代码
4. 精准修改 → 用 code_editor.edit 替换代码（old <<<>>> new 分隔）
5. 验证变更 → 用 git_tools.diff 查看变更
6. 提交代码 → 用 git_tools.commit 提交

【code_editor 编辑格式】
edit 操作使用 <<<>>> 分隔旧代码和新代码：
{{"action": "use_tool", "tool": "code_editor", "args": "edit path/to/file.py
def old_function():
    pass
<<<>>>
def new_function():
    return True"}}

【批量编辑】
multi 操作支持一次修改多处：
{{"action": "use_tool", "tool": "code_editor", "args": "multi path/to/file.py [{{\\"old\\": \\"old1\\", \\"new\\": \\"new1\\"}}, {{\\"old\\": \\"old2\\", \\"new\\": \\"new2\\"}}]"}}

【搜索代码】
- 关键词搜索: {{"action": "use_tool", "tool": "code_search", "args": "find . keyword *.py"}}
- 正则搜索: {{"action": "use_tool", "tool": "code_search", "args": "regex . def\\\\s+\\\\w+ *.py"}}
- 查看结构: {{"action": "use_tool", "tool": "code_search", "args": "structure ."}}
- 查找调用: {{"action": "use_tool", "tool": "code_search", "args": "callers . function_name"}}

【Git 操作】
- 查看状态: {{"action": "use_tool", "tool": "git_tools", "args": "status"}}
- 查看变更: {{"action": "use_tool", "tool": "git_tools", "args": "diff"}}
- 提交代码: {{"action": "use_tool", "tool": "git_tools", "args": "commit 描述信息"}}
- 查看历史: {{"action": "use_tool", "tool": "git_tools", "args": "log --oneline 10"}}

【注意事项】
- code_editor.edit 的 old_text 必须与文件中的内容完全匹配（包括缩进）
- 如果 edit 失败，先用 read_range 查看实际内容再重试
- args 必须是字符串
- 可以一次返回多个 JSON 指令
- 使用 continue 补充回答: {{"action": "continue", "content": "补充内容"}}"""
        else:
            prompt = f"""{base_prompt}

{tool_search_rule}

【工具调用格式】
{{"action": "use_tool", "tool": "工具名", "args": "参数"}}

【核心工具】
- code_editor: edit/search/diff/insert/create/write/read_range
- code_search: find/regex/symbols/imports/structure/stats
- git_tools: status/diff/log/add/commit/branch
- cmd_executor: 执行 shell 命令
- file_manager: 文件管理

【code_editor.edit 格式】
{{"action": "use_tool", "tool": "code_editor", "args": "edit 文件路径
旧代码内容
<<<>>>
新代码内容"}}

【continue 格式】
{{"action": "continue", "content": "要补充的内容"}}"""

        return prompt

    def _read_file_direct(self, filename, max_lines=None):
        """直接读取文件内容, 支持指定行数"""
        try:
            # 检查文件是否存在
            if not os.path.exists(filename):
                return f"错误：文件 '{filename}' 不存在。"
            # 检查是否为文件（而非目录）
            if not os.path.isfile(filename):
                return f"错误：'{filename}' 不是一个文件。"
            # 读取文件内容
            with open(filename, 'r', encoding='utf-8') as f:
                if max_lines is not None:
                    # 读取指定行数
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            break
                        lines.append(line.rstrip('\n'))  # 保留行内容但移除换行符
                    content = '\n'.join(lines)
                    if len(lines) < max_lines:
                        info = f"(文件共{len(lines)}行)"
                    else:
                        info = f"(已读取前{max_lines}行)"
                    return f"文件 '{filename}' 的内容 {info}:\n{content}"
                else:
                    # 读取全部内容
                    content = f.read()
                    # 限制输出长度以避免过长的响应
                    MAX_CONTENT_LENGTH = 10000  # 定义为局部常量
                    if len(content) > MAX_CONTENT_LENGTH:
                        content = content[:10000] + f"\n... (内容已截断, 共{len(content)}字符)"
                    return f"文件 '{filename}' 的内容:\n{content}"
        except UnicodeDecodeError:
            # 如果UTF-8解码失败, 尝试二进制模式获取文件大小等信息
            file_size = os.path.getsize(filename)
            return f"文件 '{filename}' 是二进制文件, 大小: {file_size} 字节。无法直接读取文本内容。"
        except PermissionError as e:
            logger.error(f"权限错误，无法读取文件 '{filename}': {e}")
            return f"权限错误：无法读取文件 '{filename}'，可能需要管理员权限或文件被占用。"
        except OSError as e:
            logger.error(f"操作系统错误，无法读取文件 '{filename}': {e}")
            return f"操作系统错误：无法读取文件 '{filename}'，原因: {str(e)}"
        except Exception as e:
            logger.error(f"读取文件 '{filename}' 失败: {e}")
            return f"读取文件 '{filename}' 失败: {str(e)}"

    def _clean_json_response(self, response):
        """清理AI响应中的Markdown代码块标记"""
        # 移除开头的```json标记
        if response.startswith("```json"):
            response = response[7:]  # 移除"```json"
        elif response.startswith("```"):
            response = response[3:]  # 移除"```"
        # 移除结尾的```标记
        if response.endswith("```"):
            response = response[:-3]  # 移除"```"
        # 移除可能的前后空白字符
        return response.strip()

    def get_liugin_usage_prompts(self):
        """获取插件和技能提示词
        
        返回所有工具的基本信息，包括 Liugin 和 Skill 两种协议。
        对于 Skill 协议的工具，包含详细的指令内容。
        在 Clawli 模式下，额外提供 send_image 工具说明。
        """
        if not self.liugin_manager.tools:
            return "当前没有可用的工具插件."
        
        prompts = []
        prompts.append("可用的工具列表：\n")
        
        # 分离 Liugin 和 Skill
        plugins = []
        skills = []
        for tool in self.liugin_manager.tools:
            protocol = tool.get('protocol', 'liugin')
            if protocol == 'skill':
                skills.append(tool)
            else:
                plugins.append(tool)
        
        # Plugin 工具（基本信息）
        if plugins:
            prompts.append("## Plugin 工具（使用 tool_search 查询详细用法）：")
            for tool in plugins:
                tool_name = tool.get('name', '')
                tool_desc = tool.get('description', '')
                prompts.append(f"- {tool_name}: {tool_desc}")
        
        # Skill 工具（包含指令）
        if skills:
            prompts.append("\n## Agent Skills（已加载详细指令）：")
            for tool in skills:
                tool_name = tool.get('name', '')
                tool_desc = tool.get('description', '')
                prompts.append(f"\n### {tool_name}")
                prompts.append(f"描述: {tool_desc}")
                
                # 获取技能实例的指令
                instance = tool.get('instance')
                if instance:
                    instructions = getattr(instance, 'instructions', '')
                    if instructions:
                        # 限制长度，避免过长
                        if len(instructions) > 2000:
                            instructions = instructions[:2000] + "\n...(内容已截断)"
                        prompts.append(f"\n{instructions}")
        
        # Clawli 模式特殊工具提示
        if self.is_clawli_mode:
            prompts.append("\n## Clawli 远程模式专属工具：")
            prompts.append("""
### send_image - 发送图片到手机端
当用户请求发送图片到手机时，使用此工具：

```json
{
    "action": "use_tool",
    "tool": "send_image",
    "args": {
        "image_path": "图片文件的绝对路径",
        "caption": "图片说明文字（可选）"
    }
}
```

支持的图片格式：JPG、PNG、GIF、BMP、WEBP
""")
        
        return "\n".join(prompts)

    def _read_about_file(self):
        """读取并返回about.txt文件的内容，逐字显示"""
        try:
            # 获取项目根目录路径
            project_dir = os.path.dirname(os.path.abspath(__file__))
            about_file_path = os.path.join(project_dir, "about.txt")
            # 检查文件是否存在
            if not os.path.exists(about_file_path):
                return "错误：about.txt 文件不存在。"
            # 读取文件内容
            with open(about_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # 逐字显示内容
            import sys
            import time
            for char in content:
                sys.stdout.write(char)
                sys.stdout.flush()
                # 根据字符类型调整延迟时间
                if char in ['，', '。', '！', '？', ',', '.', '!', '?', '\n', '\r']:
                    # 标点符号和换行符延迟稍长
                    time.sleep(0.1)
                else:
                    # 其他字符延迟较短
                    time.sleep(VIDEO_FRAME_DELAY)  # 使用常量
            print()  # 确保最后换行
            return ""  # 因为内容已经逐字显示，所以返回空字符串
        except UnicodeDecodeError:
            return "错误：about.txt 文件编码格式不支持。"
        except Exception as e:
            return f"读取 about.txt 文件时发生错误: {str(e)}"

    def _parse_mixed_response(self, response):
        """
        解析混合响应，处理同时包含文本和JSON指令的内容
        返回格式: (text_content, json_data)
        其中text_content是普通文本部分，json_data是解析出的JSON指令（如果存在）
        json_data可以是单个dict，也可以是dict列表（批量工具调用）
        """
        import re
        import json as json_module
        response = response.strip()

        # 方法0: 处理 <tool_call>... 格式（缺少开头的 {）
        if response.startswith("<tool_call>"):
            # 移除 <tool_call> 标签，添加缺失的 {
            json_str = response[11:]  # 移除 <tool_call>
            json_str = "{" + json_str  # 添加缺失的 {
            try:
                parsed = json_module.loads(json_str)
                if isinstance(parsed, dict):
                    return "", parsed
            except json_module.JSONDecodeError:
                # 如果还是失败，尝试更多修复
                pass

        # 方法1: 尝试直接解析为纯JSON
        try:
            parsed = json_module.loads(response)
            if isinstance(parsed, list):
                return "", parsed
            elif isinstance(parsed, dict):
                return "", parsed
        except json_module.JSONDecodeError:
            pass
        
        # 方法2: 尝试修复JSON中的控制字符问题
        try:
            def fix_json_string(match):
                content = match.group(1)
                content = content.replace('\\', '\\\\')
                content = content.replace('\n', '\\n')
                content = content.replace('\r', '\\r')
                content = content.replace('\t', '\\t')
                content = content.replace('"', '\\"')
                return f'"{content}"'
            fixed_response = re.sub(r'"([^"]*(?:\n[^"]*)*)"', fix_json_string, response, flags=re.DOTALL)
            parsed = json_module.loads(fixed_response)
            if isinstance(parsed, list):
                return "", parsed
            elif isinstance(parsed, dict):
                return "", parsed
        except:
            pass
        
        # 方法3: 查找代码块中的JSON
        json_pattern = r"```(?:json)?\s*({.*?})\s*```"
        matches = re.findall(json_pattern, response, re.DOTALL)
        if matches:
            try:
                json_data = json_module.loads(matches[-1])
                if isinstance(json_data, (dict, list)):
                    text_content = re.sub(json_pattern, "", response, flags=re.DOTALL).strip()
                    text_content = re.sub(r"\n\s*\n", "\n\n", text_content).strip()
                    return text_content, json_data
            except json_module.JSONDecodeError:
                pass
        
        # 方法4: 查找每行独立的JSON对象
        lines_resp = response.split("\n")
        json_objects = []
        text_lines = []
        for line in lines_resp:
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    parsed = json_module.loads(line)
                    if isinstance(parsed, dict):
                        json_objects.append(parsed)
                        continue
                except json_module.JSONDecodeError:
                    pass
            text_lines.append(line)
        
        if json_objects:
            if len(json_objects) == 1:
                text_content = "\n".join(text_lines).strip()
                return text_content, json_objects[0]
            else:
                text_content = "\n".join(text_lines).strip()
                return text_content, json_objects
        
        # 方法5: 查找内联的JSON对象（使用计数器匹配嵌套括号）
        # 查找 {"action": "use_tool" 或 {"action": "continue" 或 {"action":"use_tool" 或 {"action":"continue"
        json_start_markers = [
            '{"action": "use_tool"', '{"action": "continue"',
            '{"action":"use_tool"', '{"action":"continue"',
            '{ "action": "use_tool"', '{ "action": "continue"',
            '{ "action":"use_tool"', '{ "action":"continue"'
        ]
        for marker in json_start_markers:
            json_start = response.find(marker)
            if json_start != -1:
                brace_count = 0
                in_json = False
                
                for i in range(json_start, len(response)):
                    char = response[i]
                    if char == '{':
                        if not in_json:
                            in_json = True
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if in_json and brace_count == 0:
                            json_str = response[json_start:i+1]
                            try:
                                json_data = json_module.loads(json_str)
                                if isinstance(json_data, dict) and json_data.get('action') in ['use_tool', 'continue']:
                                    text_content = response[:json_start].strip()
                                    return text_content, json_data
                            except json_module.JSONDecodeError:
                                pass
                            break
        
        # 方法6: 尝试查找任何以{开头并以}结尾的JSON对象（跨行）
        # 使用更通用的方法：找到所有可能的JSON对象
        potential_jsons = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
        for json_str in potential_jsons:
            try:
                json_data = json_module.loads(json_str)
                if isinstance(json_data, dict) and json_data.get('action') in ['use_tool', 'continue']:
                    json_start = response.find(json_str)
                    text_content = response[:json_start].strip()
                    return text_content, json_data
            except json_module.JSONDecodeError:
                continue
        
        # 方法7: 如果是连续多个JSON对象（批量调用）
        # 尝试解析整个响应为JSON数组
        try:
            # 清理可能的文本前缀
            cleaned = response.strip()
            # 找到最后一个完整的JSON对象开始（支持use_tool和continue）
            for action in ['use_tool', 'continue']:
                last_brace_pos = cleaned.rfind(f'{{"action": "{action}"')
                if last_brace_pos == -1:
                    last_brace_pos = cleaned.rfind(f'{{"action":"{action}"')
                if last_brace_pos != -1:
                    # 从这个位置开始提取所有JSON对象
                    json_part = cleaned[last_brace_pos:]
                    # 尝试解析为JSON数组
                    if json_part.startswith('['):
                        parsed = json_module.loads(json_part)
                        if isinstance(parsed, list):
                            text_content = cleaned[:last_brace_pos].strip()
                            return text_content, parsed
                    # 尝试解析为单个JSON
                    else:
                        parsed = json_module.loads(json_part)
                        if isinstance(parsed, dict):
                            text_content = cleaned[:last_brace_pos].strip()
                            return text_content, parsed
        except:
            pass
        
        # 如果都没有找到JSON，返回原始响应作为文本
        return response, None

    def start_video_player(self):
        """启动视频播放窗口"""
        # 在新线程中启动视频播放，避免阻塞主程序
        video_thread = threading.Thread(target=self._show_video_window, daemon=True)
        video_thread.start()

    def _show_video_window(self):
        """显示视频播放窗口"""
        try:
            # 创建tkinter窗口
            root = tk.Tk()
            # 设置为无边框窗口
            root.overrideredirect(True)
            # 获取屏幕尺寸
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            # 获取视频文件路径
            video_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Video_1765688252672.mp4")
            if not os.path.exists(video_path):
                # 如果视频文件不存在，显示提示信息
                # 设置一个较小的窗口用于显示错误信息
                error_width, error_height = 400, 100
                x = (screen_width // 2) - (error_width // 2)
                y = (screen_height // 2) - (error_height // 2)
                root.geometry(f"{error_width}x{error_height}+{x}+{y}")
                canvas = tk.Canvas(root, width=error_width, height=error_height)
                canvas.pack(fill=tk.BOTH, expand=True)
                canvas.create_text(error_width//2, error_height//2, text=f"视频文件不存在:\n{video_path}", fill="red", font=("Arial", 12))
                root.mainloop()
                return
            # 打开视频文件
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                error_width, error_height = 400, 100
                x = (screen_width // 2) - (error_width // 2)
                y = (screen_height // 2) - (error_height // 2)
                root.geometry(f"{error_width}x{error_height}+{x}+{y}")
                canvas = tk.Canvas(root, width=error_width, height=error_height)
                canvas.pack(fill=tk.BOTH, expand=True)
                canvas.create_text(error_width//2, error_height//2, text="无法打开视频文件", fill="red", font=("Arial", 12))
                root.mainloop()
                return
            # 获取视频的原始尺寸
            video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            # 计算窗口大小，保持原始比例，最大不超过屏幕的40% (之前是80%)
            max_width = int(screen_width * 0.4)
            max_height = int(screen_height * 0.4)
            # 计算缩放比例
            scale = min(max_width / video_width, max_height / video_height)
            window_width = int(video_width * scale)
            window_height = int(video_height * scale)
            # 居中定位
            x = (screen_width // 2) - (window_width // 2)
            y = (screen_height // 2) - (window_height // 2)
            root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            # 设置窗口为透明（仅在Windows上有效）
            root.wm_attributes("-transparentcolor", "black")
            # 创建画布用于显示视频帧
            canvas = tk.Canvas(root, width=window_width, height=window_height, highlightthickness=0, bg='black')
            canvas.pack(fill=tk.BOTH, expand=True)

            def update_frame():
                nonlocal cap  # 确保使用外层的cap变量
                try:
                    ret, frame = cap.read()
                    if ret:
                        # 保持原始比例缩放，使用更好的插值方法
                        frame = cv2.resize(frame, (window_width, window_height), interpolation=cv2.INTER_CUBIC)
                        # 将BGR转换为RGB
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        # 实现黑色背景抠图 - 将黑色像素改为指定的透明色
                        lower_black = np.array([0, 0, 0])
                        upper_black = np.array([30, 30, 30])
                        mask = cv2.inRange(frame_rgb, lower_black, upper_black)
                        # 创建透明色（白色或黑色区域，会被tkinter视为透明）
                        frame_rgb[mask > 0] = [0, 0, 0]  # 黑色区域保持黑色，会被视为透明
                        # 将numpy数组转换为PhotoImage
                        img = tk.PhotoImage(data=cv2.imencode('.ppm', frame_rgb)[1].tobytes())
                        canvas.delete("all")  # 清除画布
                        canvas.create_image(0, 0, anchor=tk.NW, image=img)
                        # 保持对图片的引用，防止被垃圾回收
                        canvas.image = img
                        # 继续播放下一帧
                        # 使用视频原始FPS
                        delay = int(1000 / fps) if fps > 0 else 33  # 默认约30fps
                        root.after(delay, update_frame)
                    else:
                        # 视频播放完毕，开始渐隐效果
                        cap.release()
                        self._fade_out(root)  # 调用渐隐方法
                except tk.TclError:
                    # 处理tkinter相关的错误，如窗口被意外关闭
                    cap.release()
                    try:
                        root.destroy()
                    except:
                        pass
                except Exception as e:
                    print(f"更新视频帧时出错: {e}")
                    cap.release()
                    try:
                        root.destroy()
                    except:
                        pass
            # 开始播放视频
            update_frame()
            # 运行窗口
            root.mainloop()
        except Exception as e:
            print(f"播放视频时出错: {e}")
            # 确保在出错时释放资源
            try:
                if 'cap' in locals() and cap.isOpened():
                    cap.release()
            except:
                pass
            # 确保窗口被正确关闭
            try:
                if 'root' in locals():
                    root.after(100, root.destroy)  # 延迟关闭窗口
            except:
                pass

    def _fade_out(self, root, duration=1000):
        """实现窗口渐隐效果"""
        # 获取当前透明度，如果没有设置则默认为1.0（完全不透明）
        try:
            alpha = float(root.wm_attributes("-alpha"))
        except:
            alpha = 1.0
        # 每次减少0.1的透明度，实现渐隐效果
        alpha -= 0.1
        if alpha <= 0:
            # 透明度降到0，关闭窗口
            try:
                root.destroy()
            except:
                pass  # 窗口可能已经被销毁
        else:
            # 设置新的透明度
            root.wm_attributes("-alpha", alpha)
            # 继续渐隐效果，每50毫秒执行一次
            root.after(50, self._fade_out, root, duration)


# ============================================================================
# Main Entry Point - CLI Mode
# ============================================================================
if __name__ == "__main__":
    import time
    import sys
    
    # 启动时逐行输出艺术字
    art_lines = [
        "█████████████████████████████████████████████████████████████████████████████████████████████████████",
        "█████████████████████████████████████████████████████████████████████████████████████████████████████",
        "█████████████████████████████████████████████████████████████████████████████████████████████████████",
        "█████████████████████████████████████████████████████████████████████████████████████████████████████",
        "█████████████████████████████████████████████████████████████████████████████████████████████████████",
        "███████████▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██████████████████",
        "██████████                                                                          ▓████████████████",
        "██████████                                                                           ▒███████████████",
        "██████████                                                                            ░██████████████",
        "██████████                                                                             ░█████████████",
        "██████████                                                                               ████████████",
        "██████████                                                                                ███████████",
        "██████████                                      ▒████████████████████████████████████████████████████",
        "██████████                                    ░██████████████████████████████████████████████████████",
        "██████████                                   ████████████████████████████████████████████████████████",
        "██████████                                 ▓█████████████████████████████████████████████████████████",
        "██████████                               ▒███████████████████████████████████████████████████████████",
        "██████████                              ███████████▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓██████████",
        "██████████                            ███████████▓▒▓▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒██████████",
        "██████████                          ▓██████████▓▒▒▓▒▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▒▒▒▓██████████",
        "██████████                        ░███████████▒▒▓▒▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▒██████████",
        "██████████                       ███████████▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▒▓▒▒▒▒▓▒▒▒▓▒▒▒▒▓▒▒▒▓▒▒▒▒▓▓▒██████████",
        "██████████                     ███████████▓▒▓▒▒▓▒▒▒▒▓▒▒▓▒▒▒▓▒▓▒▒▓▒▒▒▓▒▓▒▒▓▒▒▒▓▒▓▒▒▓▒▒▒▓▒▓▒▓██████████",
        "██████████                   ▓██████████▓▒▒▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▒▒▒▓▒▒▒▓██████████",
        "██████████                 ░██████████▓▒▒▓▒▓▒▒▓▒▒▒▒▓▒▒▓▒▓▒▓▒▒▒▓▒▒▓▒▓▒▒▒▓▒▒▓▒▓▒▒▒▓▒▒▓▒▓▒▒▒▓▓██████████",
        "██████████                ███████████▒▓▒▓▒▒▒▓▒▒▓▒▓▒▒▓▒▒▒▒▒▒▓▒▓▒▒▓▒▒▒▓▒▓▒▒▓▒▒▒▓▒▓▒▒▒▒▒▒▓▒▓▒▓██████████",
        "██████████              ███████████▒▒▒▒▒▒▓▒▓▒▒▓▒▒▒▓▒▒▓▒▓▒▓▒▒▒▒▓▒▒▒▓▒▒▒▒▒▓▒▒▓▒▒▒▒▒▓▒▓▒▓▒▒▒▓▓██████████",
        "██████████            ░██████████▒▓▒▓▒▓▒▓▒▒▒▓▒▒▒▓▒▒▓▒▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▓▒▓▒▒▒▒▓▒▓▒▓▒▒▓▒▒▒▓▒▒▒██████████",
        "██████████            █████████▓▒▒▒▓▒▒▓▒▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▓▒▒██████████",
        "██████████            █████████▒▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▓▒▒▒▓▒▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▒▒▒▓██████████",
        "██████████            ▓████████▒▓▒▓▒▒▓▒▒▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▒▒▓▒▒▓▒▒▓▒▓▒▒▒▓▒▒▓▒▒▓▓▒▒▒██████████",
        "██████████            █████████▒▒▒▒▓▒▒▒▓▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▓▒▒▓▒▓▒▒▓▒▓▒▒▒▓▒▓▒▒▓▒▒▒▒▒▓▒██████████",
        "██████████            █████████▒▓▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▒▓▒▒▓▒▒▓▒▒▓▒▒▒▓▒▒▓▒▒▓▒▓▒▒▓▒▓▒▒▓▒▓▒▒▓▓▒▒▒██████████",
        "██████████            ▓████████▒▒▓▒▒▓▒▒▓▒▒▒▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▓▒▒▓▒▓▒▒▒▓▒▓▒▒▓▓▒▒▒▓██████████",
        "██████████            █████████▒▓▒▒▒▒▓▒▒▒▓▒▓▒▒▓▒▒▓▒▒▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▒▒▓▒▓▒▒▓▓▒▒▒██████████",
        "██████████            █████████▒▒▓▒▓▒▒▓▒▓▒▒▒▓▒▒▒▓▒▒▓▒▒▓▒▒▓▒▓▒▒▓▒▓▒▒▓▒▓▒▒▓▒▓▒▒▒▓▒▓▒▒▓▓▒▒▒██████████",
        "██████████            ▓████████▒▓▒▒▒▓▒▒▒▒▓▒▓▒▒▓▒▒▒▓▒▒▓▒▒▒▒▒▒▓▒▒▒▓▒▒▒▓▒▒▓▒▓▒▒▒▒▓▒▓▒▒▒▓▒▓██████████",
        "██████████            █████████▒▒▓▒▓▒▒▓▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓██████████",
        "██████████            █████████▒▓▒▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▒▒▒▒██████████",
        "██████████            ▓████████▒▒▓▒▒▒▓▒▒▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▒▒▓▒▓▒▒▓▒▒▓▓▒▒██████████",
        "██████████            █████████▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▒▒▓▒▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▓██████████",
        "██████████            █████████▒▒▓▒▒▓▒▒▒▒▓▒▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▒▒██████████",
        "██████████            ▓████████▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▒▓▒▒▓▒▒▒▓▒▓▒▒▒▓▒▒▓▒▒▓▒▒▓▒▓▒▒▓▒▓▒▒▓▒▓▒▒▓██████████",
        "██████████            █████████▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▒▓▒▓▒▒▓▒▒▓▒▓▒▒▓▒▓▒▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▓██████████",
        "██████████            █████████▒▓▒▒▓▒▒▓▒▒▒▒▓▒▒▓▒▒▓▒▓▒▒▒▓▒▒▒▓▒▒▓▒▒▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▒▒▒▒▓██████████",
        "██████████            ▓████████▒▒▓▒▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▒▒▓▒▓▒▒▓▒▓▒▒▓▒▓▒▒▓▒▓▒▒▒▓▒▓▒▒▓▒▓▓▓▒▒▒██████████",
        "███████████           █████████▒▓▒▒▓▒▒▒▓▒▒▒▓▒▒▓▒▒▒▓▒▒▒▒▓▒▒▓▒▒▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▒▓▒▒▒▒▓▒▒██████████",
        "█████████████▓        █████████▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▒▓▒▒▒██████████",
        "█████████████████     ▓████████▒▓▒▒▓▒▒▒▓▒▒▓▒▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▓▒▓▓▒▒██████████",
        "███████████████████▒  █████████▒▒▓▒▒▒▓▒▒▓▒▒▓▒▓▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▒▓▒▒▓██████████",
        "█████████████████████████████████████████████████████████████████████████████████████████████████████",
        "█████████████████████████████████████████████████████████████████████████████████████████████████████",
        "█████████████████████████████████████████████████████████████████████████████████████████████████████",
        "█████████████████████████████████████████████████████████████████████████████████████████████████████",
        "█████████████████████████████████████████████████████████████████████████████████████████████████████",
        "█████████████████████████████████████████████████████████████████████████████████████████████████████"
    ]
    
    # 设置标准输出编码为 UTF-8
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    
    for line in art_lines:
        try:
            print(line, flush=True)
        except UnicodeEncodeError:
            print(line.encode('gbk', errors='ignore').decode('gbk'), flush=True)
        time.sleep(0.05)
    
    # 运行主程序
    cli = AICLI()
    cli.run()
