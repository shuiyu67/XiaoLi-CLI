import os
import sys
import importlib.util
import uuid
import shutil
from colorama import init, Fore, Style

from .constants import (
    DEFAULT_MAX_HISTORY, WEBSOCKET_AVAILABLE, CLAWLI_SERVER_AVAILABLE,
    UNIFIED_TOOL_MANAGER_AVAILABLE, TEXTUAL_AVAILABLE,
)
from .config import get_system_config, set_system_config, logger
from .plugin_manager import LiuginManager

# 可选导入
try:
    import clawli_server
except ImportError:
    clawli_server = None

try:
    from unified_tool_manager import UnifiedToolManager
except ImportError:
    UnifiedToolManager = None


class BaseAICLI:
    """AI CLI 基类 - 初始化、引擎/插件加载、资源管理"""

    def __init__(self):
        # 初始化colorama
        init(autoreset=True)

        # 确保插件管理器使用正确的路径
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
            first_engine_name = next(iter(self.engines))
            self.current_engine = self.engines[first_engine_name]
            print(f"{Fore.GREEN}使用默认AI引擎: {first_engine_name}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}警告: 没有可用的AI引擎，请检查ai_engines目录{Style.RESET_ALL}")
            self.current_engine = None
        if self.current_engine:
            self.current_engine.cli = self  # 设置引用以便访问插件

        # 初始化安全层
        from .safety import get_safety
        get_safety().set_cli(self)

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
        ]
        self.code_execution_history = []
        self.liugin_code_requests = {}
        self.user_input_queue = {}
        self.is_clawli_mode = False  # Clawli 远程模式标志
        self._clawli_monitor_thread = None
        self._clawli_monitor_running = False
        # TUI 输出回调（用于 TUI 模式下的实时输出）
        self.tui_output_callback = None
        # 初始化用户ID（基于机器硬件动态生成）
        self.user_id = str(uuid.getnode())

    # ── 资源清理 ──

    def cleanup_resources(self):
        """清理资源，确保在程序退出时正确关闭所有资源"""
        print(f"{Fore.YELLOW}正在清理资源...{Style.RESET_ALL}")
        self._stop_clawli_monitor()
        if CLAWLI_SERVER_AVAILABLE and clawli_server:
            clawli_server.stop_server()
        print(f"{Fore.GREEN}资源清理完成{Style.RESET_ALL}")

    def __del__(self):
        """析构函数，确保资源被清理"""
        self.cleanup_resources()

    # ── 引擎管理 ──

    def _get_default_engine_name(self):
        """从配置文件获取默认引擎名称"""
        try:
            default_engine = get_system_config('default_engine')
            if default_engine:
                return default_engine
            return 'ollama'
        except Exception as e:
            print(f"{Fore.YELLOW}读取引擎配置失败，使用默认引擎: {e}{Style.RESET_ALL}")
            return 'ollama'

    def load_ai_engines(self):
        """动态加载AI引擎插件"""
        print(f"{Fore.GREEN}正在加载AI引擎插件...{Style.RESET_ALL}")
        ai_engines_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ai_engines")
        if os.path.exists(ai_engines_dir):
            for filename in os.listdir(ai_engines_dir):
                if filename.endswith('.py') and filename != '__init__.py':
                    engine_path = os.path.join(ai_engines_dir, filename)
                    engine_name = filename[:-3]
                    try:
                        spec = importlib.util.spec_from_file_location(engine_name, engine_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        class_name = self._find_engine_class(module, engine_name)
                        if class_name and hasattr(module, class_name):
                            engine_instance = getattr(module, class_name)()
                            engine_instance.cli = self
                            engine_key = getattr(engine_instance, 'name', engine_name)
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
        possible_names = [
            engine_name.capitalize() + "AI",
            engine_name.replace('_', '').replace('-', '').capitalize() + "AI",
            engine_name.replace('_', '').capitalize() + "AI",
            engine_name.replace('_engine', '').capitalize() + "AI",
            engine_name.replace('-', '').replace('_', '').capitalize() + "AI",
            engine_name.replace('-', '').capitalize() + "AI",
            ''.join(word.capitalize() for word in engine_name.replace('-', ' ').replace('_', ' ').split()) + "AI",
            ''.join(word.capitalize() for word in engine_name.replace('_engine', '').replace('-', ' ').replace('_', ' ').split()) + "AI",
        ]
        for name in possible_names:
            if hasattr(module, name):
                return name
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (hasattr(attr, '__class__') and
                isinstance(attr, type) and
                attr_name.endswith('AI') and
                hasattr(attr, 'generate_response')):
                return attr_name
        return None

    def load_liugins(self, liugins_dir=None, skills_dir=None):
        """加载liugin和技能"""
        print(f"{Fore.GREEN}正在加载工具...{Style.RESET_ALL}")

        if self._use_unified_manager:
            self.liugin_manager.initialize(liugins_dir or "plugins", skills_dir or "skills")
        else:
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

    # ── 命令注册 ──

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

    def _get_engine_commands_help(self):
        """获取引擎命令帮助信息"""
        help_lines = []
        for cmd, handler in self.engine_commands.items():
            if cmd == 'list':
                help_lines.append(f"  /engine {cmd:<10} - 查看可用的AI引擎")
            elif cmd == 'switch':
                help_lines.append(f"  /engine {cmd:<10} - 切换AI引擎")
            else:
                help_lines.append(f"  /engine {cmd:<10} - 执行{cmd}命令")
        return '\n'.join(help_lines) if help_lines else "  无可用引擎管理命令"

    # ── 引擎切换 ──

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
            old_engine = self.current_engine
            self.current_engine = self.engines[engine_name]

            if hasattr(self.current_engine, 'cli'):
                self.current_engine.cli = self

            if hasattr(self.current_engine, 'shared_conversation_history'):
                self.current_engine.shared_conversation_history = self.shared_conversation_history
                self.current_engine.max_history = self.max_history

            if old_engine != self.current_engine and self.shared_conversation_history:
                print(f"{Fore.CYAN}已切换到AI引擎: {engine_name}，正在传递对话历史...{Style.RESET_ALL}")

                context_message = {
                    "role": "system",
                    "content": f"引擎切换通知：现在由{engine_name}引擎继续之前的对话。以下是之前的对话历史：\n"
                }

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
            engine.shared_conversation_history = self.shared_conversation_history
            engine.max_history = self.max_history

    def handle_engine_command(self, command):
        """处理引擎特定命令"""
        if not hasattr(self.current_engine, 'handle_command'):
            return False
        engine_name = getattr(self.current_engine, 'name', '')
        if engine_name and command.startswith(engine_name + ' '):
            actual_command = command[len(engine_name) + 1:].strip()
            return self.current_engine.handle_command(actual_command)
        return self.current_engine.handle_command(command)

    # ── 插件消息处理 ──

    def handle_liugin_message(self, message: str, **kwargs) -> str:
        """处理插件转发的消息（如 QQ 群 @ 消息）"""
        try:
            print(f"{Fore.CYAN}[插件消息] {message[:100]}...{Style.RESET_ALL}")

            system_prompt = """你是一个智能助手，正在通过 QQ 机器人与用户交流。
请简洁、友好地回复用户的消息。回复时注意：
1. 回复要简洁明了，适合 QQ 群聊场景
2. 不要提及你是 AI 或机器人
3. 直接回答问题，不要加多余的前缀"""

            if self.current_engine:
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
