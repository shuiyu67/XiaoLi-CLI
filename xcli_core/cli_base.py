import os
import importlib.util
import uuid
from colorama import init, Fore, Style
from .cli_display import emit

from .constants import (
    DEFAULT_MAX_HISTORY, CLAWLI_SERVER_AVAILABLE,
    UNIFIED_TOOL_MANAGER_AVAILABLE,
)
from .config import get_system_config, set_system_config, logger
from .verbose import vprint
from .plugin_manager import LiuginManager
from .process_protection import get_protection, enable_process_protection

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

        # 初始化进程保护（单实例 + 优先级 + PPL保护 + 看门狗）
        self.protection_results = enable_process_protection(
            priority_level="above_normal",
            watchdog=True,
            restart_on_crash=False,
        )
        self._protection = get_protection()

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
        self.load_models()
        # 从配置文件获取默认引擎设置
        default_engine_name = self._get_default_engine_name()
        # 设置默认引擎，优先使用配置文件指定的引擎
        if default_engine_name in self.engines:
            self.current_engine = self.engines[default_engine_name]
            vprint(f"{Fore.GREEN}使用配置的默认AI引擎: {default_engine_name}{Style.RESET_ALL}")
        elif self.engines:
            first_engine_name = next(iter(self.engines))
            self.current_engine = self.engines[first_engine_name]
            vprint(f"{Fore.GREEN}使用默认AI引擎: {first_engine_name}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}警告: 没有已配置的模型，请用 /model add 添加（OpenAI 兼容格式）{Style.RESET_ALL}")
            self.current_engine = None
        if self.current_engine:
            self.current_engine.cli = self  # 设置引用以便访问插件
            # 记录当前模型（openai 引擎注册表名，其它引擎取 model 值）
            try:
                self.current_model = self.current_engine.current_model_name()
            except Exception:
                self.current_model = getattr(self.current_engine, 'model', None)
        else:
            self.current_model = None

        # 初始化安全层
        from .safety import get_safety
        get_safety().set_cli(self)

        # 创建聊天记录目录
        self.chat_history_dir = os.path.join(project_dir, "chat_history")
        if not os.path.exists(self.chat_history_dir):
            os.makedirs(self.chat_history_dir)
        # 初始化会话管理器（opencode 式 /resume 持久化）
        self.init_session_manager()
        # Plan 模式状态（只读规划 → 审批 → 执行）
        self.plan_mode = False
        self.current_plan = ""
        # Agents 管理器（opencode 式 @委派，加载 agents/ 目录下的 *.md）
        self.agent_manager = None
        try:
            from .agent_manager import AgentManager
            self.agent_manager = AgentManager()
            agents_dir = os.path.join(project_dir, "agents")
            os.makedirs(agents_dir, exist_ok=True)
            self.agent_manager.load_dir(agents_dir)
        except Exception:
            self.agent_manager = None

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
        # 清理进程保护
        if hasattr(self, '_protection') and self._protection:
            try:
                self._protection.disable_all()
            except Exception:
                pass
        self._stop_clawli_monitor()
        if CLAWLI_SERVER_AVAILABLE and clawli_server:
            clawli_server.stop_server()
        print(f"{Fore.GREEN}资源清理完成{Style.RESET_ALL}")

    def __del__(self):
        """析构函数，确保资源被清理"""
        self.cleanup_resources()

    # ── 引擎管理 ──

    def _get_default_engine_name(self):
        """默认模型名：模型注册表的 current 指针"""
        try:
            from xcli_core import model_registry
            models, current = model_registry.list_models()
            if current:
                return current
            return models[0]["name"] if models else "default"
        except Exception as e:
            print(f"{Fore.YELLOW}读取模型注册表失败: {e}{Style.RESET_ALL}")
            return "default"

    def load_models(self):
        """从模型注册表装配模型连接。

        引擎架构已删除（多引擎加载/类名嗅探/MODEL_FIELDS 都没了）：
        一切模型皆 OpenAI 格式，每个已配置模型 = 一条 ModelConnection。
        """
        vprint(f"{Fore.GREEN}正在加载已配置模型...{Style.RESET_ALL}")
        self.engines = {}
        try:
            from xcli_core.model_conn import ModelConnection
            from xcli_core import model_registry
            models, _current = model_registry.list_models()
        except Exception as e:
            logger.error(f"加载模型注册表失败: {e}")
            print(f"{Fore.RED}加载模型注册表失败: {e}{Style.RESET_ALL}")
            return
        for m in models:
            try:
                conn = ModelConnection(m.get("name", "default"), m)
                conn.cli = self
                if conn.name not in self.engines:
                    self.engines[conn.name] = conn
                    vprint(f"{Fore.GREEN}已加载模型: {conn.name} ({conn.model}){Style.RESET_ALL}")
            except Exception as e:
                logger.error(f"装配模型连接失败 {m.get('name')}: {e}")
                print(f"{Fore.RED}装配模型连接失败 {m.get('name')}: {e}{Style.RESET_ALL}")
        vprint(f"{Fore.GREEN}总共加载了 {len(self.engines)} 个模型{Style.RESET_ALL}")

    # 兼容旧调用面（引擎架构已删，语义 = 按注册表装载模型）


    def load_liugins(self, liugins_dir=None, skills_dir=None):
        """加载liugin和技能"""
        vprint(f"{Fore.GREEN}正在加载工具...{Style.RESET_ALL}")

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
                                vprint(f"{Fore.GREEN}已加载liugin: {liugin_name}{Style.RESET_ALL}")
                        except Exception as e:
                            print(f"{Fore.RED}加载liugin失败 {filename}: {e}{Style.RESET_ALL}")
            vprint(f"{Fore.GREEN}总共加载了 {len(self.liugin_manager.tools)} 个工具插件{Style.RESET_ALL}")

        vprint(f"{Fore.GREEN}工具加载完成!{Style.RESET_ALL}")

    # ── 命令注册 ──

    def register_liugin_command(self, command, handler):
        """注册插件命令"""
        self.liugin_commands[command] = handler
        vprint(f"{Fore.GREEN}已注册插件命令: {command}{Style.RESET_ALL}")

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

    # ── 模型管理（OpenAI 引擎多模型切换）──

    def handle_model_command(self, args):
        """处理 /model 命令族（模型注册表：增删改查/切换，全部 OpenAI 格式）。"""
        eng = self.current_engine
        if eng is None:
            print(f"{Fore.RED}没有可用的模型连接{Style.RESET_ALL}")
            return

        if not args or args == 'list':
            self._model_list(eng)
            return

        parts = args.split(' ', 1)
        cmd = parts[0]
        rest = parts[1].strip() if len(parts) > 1 else ''
        if cmd == 'add':
            self._model_add_interactive(eng)
        elif cmd in ('rm', 'remove', 'del'):
            if not rest:
                print(f"{Fore.RED}用法: /model rm <名称>{Style.RESET_ALL}")
                return
            if eng.remove_model(rest):
                print(f"{Fore.GREEN}已删除模型: {rest}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}未找到模型: {rest}{Style.RESET_ALL}")
        elif cmd in ('set', 'switch'):
            self._model_switch(eng, rest)
        else:
            # 无子命令：/model <名称> 视为切换
            self._model_switch(eng, cmd)

    def _model_list(self, eng):
        models, current = eng.list_registry_models()
        if not models:
            print(f"{Fore.YELLOW}尚未配置任何模型，用 /model add 添加{Style.RESET_ALL}")
            return
        print(f"{Fore.GREEN}已配置的模型（OpenAI 兼容格式）:{Style.RESET_ALL}")
        for m in models:
            mark = f"{Fore.CYAN} *{Style.RESET_ALL}" if m.get('name') == current else ""
            caps = "".join(c for c, on in (("图", m.get('image_input')), ("视", m.get('video_input')),
                                           ("音", m.get('audio_input'))) if on) or "文本"
            print(f"  {m.get('name')}{mark}  ({m.get('model')} @ {m.get('base_url') or '无 base_url'})"
                  f"  [入{m.get('max_input')}/出{m.get('max_output')} {caps}]")
        print(f"{Fore.CYAN}当前: {current} ｜ /model <名称> 切换 ｜ /model add 新增 ｜ "
              f"/model rm <名称> 删除{Style.RESET_ALL}")

    def _model_switch(self, eng, name):
        if not name:
            print(f"{Fore.RED}用法: /model <名称>  或 /model 查看列表{Style.RESET_ALL}")
            return
        if eng.set_registry_model(name):
            self.current_model = name
            print(f"{Fore.GREEN}已切换到模型: {name}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}未找到模型: {name}（/model 查看可用）{Style.RESET_ALL}")

    def _model_add_interactive(self, eng):
        print(f"{Fore.CYAN}添加模型（OpenAI 兼容格式；* 为必填）{Style.RESET_ALL}")
        try:
            name = input(f"{Fore.CYAN}* 名称(用于切换, 如 gpt4o): {Style.RESET_ALL}").strip()
            if not name:
                print(f"{Fore.RED}名称不能为空{Style.RESET_ALL}")
                return
            base_url = input(f"{Fore.CYAN}* base_url(如 https://api.openai.com/v1，"
                             f"本地 Ollama 填 http://localhost:11434/v1): {Style.RESET_ALL}").strip()
            api_key = input(f"{Fore.CYAN}  api_key(本地服务可留空): {Style.RESET_ALL}").strip()
            model = input(f"{Fore.CYAN}* model(如 gpt-4o / deepseek-chat / gemma4:31b): {Style.RESET_ALL}").strip()
            if not model:
                print(f"{Fore.RED}model 不能为空{Style.RESET_ALL}")
                return
            max_input = input(f"{Fore.CYAN}* 最大输入(token, 如 32768): {Style.RESET_ALL}").strip()
            max_output = input(f"{Fore.CYAN}* 最大输出(token, 如 4096): {Style.RESET_ALL}").strip()
            if not max_input.isdigit() or not max_output.isdigit():
                print(f"{Fore.RED}最大输入/最大输出必须是整数{Style.RESET_ALL}")
                return
            def _yes(q):
                return input(f"{Fore.CYAN}{q} (y/N): {Style.RESET_ALL}").strip().lower() in ('y', 'yes')
            image_input = _yes("* 支持图片输入?")
            video_input = _yes("* 支持视频输入?")
            audio_input = _yes("* 支持音频输入?")
        except (EOFError, KeyboardInterrupt):
            print(f"{Fore.YELLOW}\n已取消添加{Style.RESET_ALL}")
            return
        eng.add_model({
            "name": name, "base_url": base_url, "api_key": api_key, "model": model,
            "max_input": int(max_input), "max_output": int(max_output),
            "image_input": image_input, "video_input": video_input, "audio_input": audio_input,
        })
        eng.set_registry_model(name)
        self.current_model = name
        print(f"{Fore.GREEN}已添加并切换到模型: {name}{Style.RESET_ALL}")

    # ── Provider 抽象层（opencode 式原生多 Provider）──
    def handle_providers_command(self, args):
        """处理 /providers 命令：列出已注册 Provider 与配置状态。

        /providers           列出全部内置 Provider 及是否已配置 key
        /providers <名称>    显示该 Provider 的连接参数（base_url / model / 协议）
        """
        from xcli_core.provider_router import (
            list_providers, provider_summary, resolve_provider, PROVIDER_PRESETS,
        )
        try:
            cfg = load_config() or {}
        except Exception:
            cfg = {}
        providers_cfg = cfg.get("providers", {}) if isinstance(cfg, dict) else {}

        if args:
            name = args.split()[0]
            preset = PROVIDER_PRESETS.get(name)
            if not preset:
                emit(self, f"{Fore.RED}未知 Provider: {name}（/providers 查看可用）{Style.RESET_ALL}")
                return
            r = resolve_provider(name, providers_cfg)
            emit(self, f"{Fore.GREEN}Provider: {preset['label']} ({name}){Style.RESET_ALL}")
            emit(self, f"  协议族: {r['protocol']}")
            emit(self, f"  base_url: {r['base_url']}")
            emit(self, f"  默认模型: {r['model']}")
            emit(self, f"  已配置 key: {'是' if r['api_key'] else '否'}")
            emit(self, f"{Fore.CYAN}在 config.json 的 providers.{name} 填入 {{api_key, base_url, model}} 即可启用；"
                  f"OpenAI 兼容族经现有 openai 引擎直接可用。{Style.RESET_ALL}")
            return

        emit(self, f"{Fore.GREEN}已注册 Provider（opencode 式多 Provider）:{Style.RESET_ALL}")
        for name in list_providers():
            s = provider_summary(name, providers_cfg)
            if not s:
                continue
            mark = f"{Fore.GREEN}✓ 已配置{Style.RESET_ALL}" if s["configured"] else f"{Fore.YELLOW}· 未配置{Style.RESET_ALL}"
            emit(self, f"  {s['name']:<10} {s['label']:<22} [{s['protocol']:<9}] {mark}")
        emit(self, f"{Fore.CYAN}/providers <名称> 查看连接参数 ｜ 在 config.json 的 providers 段填入 key 启用{Style.RESET_ALL}")

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
        """处理引擎特定命令（支持跨引擎调用，如 /engine.manual status）"""
        # 先检查是否指定了引擎名（如 "manual status" → 引擎=manual, 命令=status）
        parts = command.split(' ', 1)
        target_name = parts[0]
        rest = parts[1] if len(parts) > 1 else ""

        # 如果目标名是某个已加载的引擎，直接调用该引擎
        if target_name in self.engines:
            target_engine = self.engines[target_name]
            if hasattr(target_engine, 'handle_command'):
                return target_engine.handle_command(rest)

        # 否则当作当前引擎的命令
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
