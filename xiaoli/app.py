"""主应用 - 薄编排层，协调各模块"""
import os
import sys
import re
import time
import uuid
import threading
import logging
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import Fore, Style, init

from . import __version__
from .config import get as cfg_get, set as cfg_set
from .display import Display
from .engines import EngineManager
from .conversation import parse_response, process_thinking, process_code_blocks, extract_tool_calls
from .conversation.history import History
from .sandbox import Sandbox
from . import prompt as prompt_builder

logger = logging.getLogger(__name__)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_FILE_SIZE = 52428800


class App:
    """小狸 Pro-CLI 主应用"""

    def __init__(self):
        init(autoreset=True)
        self.user_id = str(uuid.getnode())
        self.dir = PROJECT_DIR

        # 插件命令注册表（必须在 _init_tools 之前）
        self.liugin_commands = {}
        self.engine_commands = {}
        self.current_dir = os.getcwd()
        self.user_input_queue = {}
        self.chat_history_dir = os.path.join(self.dir, "chat_history")
        self.is_clawli = False
        self.tui_callback = None

        # 子系统
        self.engine_mgr = EngineManager()
        self.display = Display(self.user_id)
        self.sandbox = Sandbox(timeout=cfg_get('code_execution_timeout', 30))
        self.history = History(os.path.join(self.dir, "chat_history"))

        # 工具
        self.tool_mgr = None
        self.liugin_manager = None
        self._init_tools()
        if self.tool_mgr:
            self.liugin_manager = self.tool_mgr

        # 引擎
        self._init_engines()

    def register_liugin_command(self, command, handler):
        """注册插件命令"""
        self.liugin_commands[command] = handler

    def unregister_liugin_command(self, command):
        """注销插件命令"""
        self.liugin_commands.pop(command, None)

    def register_engine_command(self, command, handler):
        """注册引擎命令"""
        self.engine_commands[command] = handler

    def handle_plugin_message(self, message, **kwargs):
        """处理插件消息"""
        return self.handle_liugin_message(message, **kwargs)

    def _init_engines(self):
        """初始化引擎"""
        engines_dir = os.path.join(self.dir, "ai_engines")
        self.engine_mgr.load_all(engines_dir)

        default = cfg_get('default_engine', 'ollama')
        if not self.engine_mgr.set_default(default) and self.engine_mgr.engines:
            first = next(iter(self.engine_mgr.engines))
            self.engine_mgr.set_default(first)

        if self.engine_mgr.current:
            self.engine_mgr.current.cli = self

        # 共享历史
        for eng in self.engine_mgr.engines.values():
            eng.shared_conversation_history = self.history.messages
            eng.max_history = self.history.max

    def _init_tools(self):
        """初始化工具"""
        try:
            from unified_tool_manager import UnifiedToolManager
            self.tool_mgr = UnifiedToolManager(self)
            plugins_dir = os.path.join(self.dir, "plugins")
            skills_dir = os.path.join(self.dir, "skills")
            self.tool_mgr.initialize(plugins_dir, skills_dir)
        except ImportError:
            logger.warning("UnifiedToolManager 不可用")

    def run(self):
        """启动 CLI 主循环"""
        self.display.banner(
            self.engine_mgr.current_name(),
            self.engine_mgr.names(),
            self.user_id
        )
        self._loop()

    def _loop(self):
        """CLI 主循环"""
        while True:
            try:
                user_input = input(f"\n{Fore.WHITE}> {Style.RESET_ALL}").strip()
                if not user_input:
                    continue

                # 命令处理
                if user_input.startswith('/'):
                    if self._handle_command(user_input):
                        continue

                # @文件路径
                if '@' in user_input:
                    processed = self._process_file_refs(user_input)
                    if processed != user_input:
                        user_input = processed

                # 对话
                self.process_conversation(user_input)

            except KeyboardInterrupt:
                print(f"\n{Fore.GREEN}再见!{Style.RESET_ALL}")
                break
            except Exception as e:
                print(f"{Fore.RED}错误: {e}{Style.RESET_ALL}")

    def _handle_command(self, cmd: str) -> bool:
        """处理命令，返回 True 表示已处理"""
        parts = cmd[1:].split(maxsplit=1)
        name = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        commands = {
            'quit': lambda a: sys.exit(0),
            'help': lambda a: self._show_help(a),
            'about': lambda a: self._show_about(),
            'cli': lambda a: self.run(),
            'model': lambda a: self._switch_model(a),
            'engine': lambda a: self._engine_cmd(a),
            'chat': lambda a: self._chat_cmd(a),
            'remote': lambda a: self._remote_cmd(a),
            'file.read': lambda a: self._file_read(a),
            'thinking': lambda a: self._handle_thinking(a),
        }

        handler = commands.get(name)
        if handler:
            handler(args)
            return True

        # 插件命令
        if name in self.liugin_commands:
            try:
                result = self.liugin_commands[name](args)
                if result:
                    self.display.out(Display._trunc(result, 5))
            except Exception as e:
                self.err(f"插件命令失败: {e}")
            return True

        return False

    def _switch_model(self, name: str):
        name = name.strip()
        if self.engine_mgr.switch(name):
            self.engine_mgr.current.cli = self
            self.engine_mgr.current.shared_conversation_history = self.history.messages
            cfg_set('default_engine', name)
            self.ok(f"已切换到: {name}")
        else:
            self.err(f"未找到引擎: {name}")

    def _engine_cmd(self, args: str):
        parts = args.split(maxsplit=1)
        cmd = parts[0] if parts else ""
        rest = parts[1] if len(parts) > 1 else ""

        if cmd == 'list':
            for name in self.engine_mgr.names():
                cur = " (当前)" if name == self.engine_mgr.current_name() else ""
                print(f"  {name}{cur}")
        elif cmd == 'switch' and rest:
            self._switch_model(rest)
        else:
            print("用法: /engine list | /engine switch <名称>")

    def _chat_cmd(self, args: str):
        parts = args.split(maxsplit=1)
        cmd = parts[0] if parts else ""
        rest = parts[1] if len(parts) > 1 else ""

        if cmd == 'save' and rest:
            self.history.save(rest)
        elif cmd == 'list':
            self.history.list_saved()
        elif cmd == 'open' and rest:
            self.history.load(rest)
            for eng in self.engine_mgr.engines.values():
                eng.shared_conversation_history = self.history.messages
        else:
            print("用法: /chat save/list/open <名称>")

    def _file_read(self, args: str):
        parts = args.split(maxsplit=1)
        if not parts:
            print("用法: /file.read <路径> [行数]")
            return

        path = parts[0]
        max_lines = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None

        if not os.path.exists(path):
            print(f"{Fore.RED}文件不存在: {path}{Style.RESET_ALL}")
            return

        with open(path, 'r', encoding='utf-8') as f:
            if max_lines:
                lines = [f.readline() for _ in range(max_lines)]
                content = ''.join(lines)
                print(f"📄 {path} (前 {max_lines} 行):\n{content}")
            else:
                content = f.read()
                if len(content) > 10000:
                    content = content[:10000] + "\n... (截断)"
                print(f"📄 {path}:\n{content}")

    def _handle_thinking(self, args: str):
        processed = process_thinking(args, self.engine_mgr.current)
        processed = process_code_blocks(processed)
        uid = f"[用户ID: {self.user_id}]"
        for line in processed.split('\n'):
            print(f"✦ {line}")
        print(uid)

    def _show_help(self, args: str = ""):
        if args:
            self._show_tool_help(args)
            return

        tools = []
        if self.tool_mgr and hasattr(self.tool_mgr, '_tools'):
            tools = list(self.tool_mgr._tools.keys())

        print(f"""
{Fore.CYAN}小狸 Pro-CLI v{__version__} 帮助{Style.RESET_ALL}

{Fore.WHITE}基本命令:{Style.RESET_ALL}
  /help              帮助信息
  /quit              退出
  /cli               切换到命令行模式
  /model <引擎>      切换引擎
  /engine list       列出引擎
  /chat save/list/open  聊天记录
  /file.read <路径>  读取文件
  /about             关于

{Fore.WHITE}编码工具:{Style.RESET_ALL}
  code_editor        精准代码编辑
  code_search        代码搜索理解
  git_tools          Git 版本控制
  cmd_executor       Shell 命令
  file_manager       文件管理

{Fore.WHITE}已加载工具 ({len(tools)}):{Style.RESET_ALL}""")

        for t in tools:
            print(f"  • {t}")

    def _show_tool_help(self, name: str):
        if self.tool_mgr and hasattr(self.tool_mgr, '_tools'):
            tool = self.tool_mgr._tools.get(name)
            if tool:
                print(f"\n{Fore.GREEN}{name}{Style.RESET_ALL}: {tool.get('description', '')}")
                if 'usage' in tool:
                    print(tool['usage'])
                return
        print(f"{Fore.RED}未找到: {name}{Style.RESET_ALL}")

    def _show_about(self):
        path = os.path.join(self.dir, "about.txt")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                for ch in f.read():
                    sys.stdout.write(ch)
                    sys.stdout.flush()
                    time.sleep(0.04 if ch in '，。！？\n' else 0.02)
            print()

    def _run_tui(self):
        """启动 TUI 模式，不可用时降级到 CLI"""
        try:
            from xiaoli.tui import run_tui, TEXTUAL_AVAILABLE
            if not TEXTUAL_AVAILABLE:
                raise ImportError("Textual 未安装")
            self.display.info("正在启动 TUI 模式...")
            run_tui(self)
        except ImportError:
            self.display.warn("Textual 未安装，TUI 不可用")
            self.display.info("安装命令: pip install textual rich")
            self.display.info("已切换到命令行模式")
            self.run()
        except Exception as e:
            self.err(f"TUI 启动失败: {e}")
            self.display.info("已切换到命令行模式")
            self.run()

    def _remote_cmd(self, args: str):
        try:
            from ai_cli import AICLI
            # 复用原有的远程命令处理
            temp = AICLI.__new__(AICLI)
            temp.is_clawli_mode = self.is_clawli
            temp._handle_remote_command(args)
        except Exception as e:
            self.err(f"远程命令失败: {e}")

    def process_conversation(self, user_input: str):
        """核心对话循环"""
        self.history.add("user", user_input)

        tool_prompts = self._get_tool_prompts()
        has_search = any(t.get('name') == 'tool_search'
                         for t in (self.tool_mgr._tools.values() if self.tool_mgr and hasattr(self.tool_mgr, '_tools') else []))

        sys_prompt = prompt_builder.build(
            tool_prompts=tool_prompts,
            has_tool_search=has_search,
            is_clawli=self.is_clawli
        )

        loop_count = 0
        current = user_input

        while loop_count < 20:
            response = self._generate(current, sys_prompt)
            processed = process_thinking(response, self.engine_mgr.current)
            processed = process_code_blocks(processed)

            text, json_data = parse_response(processed)

            if json_data:
                if text:
                    self.history.add("assistant", text)
                    self.display.ai(text)

                if isinstance(json_data, dict):
                    action = json_data.get('action')
                    if action == 'use_tool':
                        self._run_tool(json_data)
                        break
                    if action == 'continue':
                        content = json_data.get('content', '')
                        if content:
                            self.history.add("assistant", content)
                            self.display.ai(content, is_continue=True)
                        loop_count += 1
                        continue
                    if json_data.get('continue') or json_data.get('need_continue'):
                        msg = json_data.get('message', '')
                        if msg:
                            self.history.add("assistant", msg)
                            self.display.ai(msg, is_continue=True)
                        loop_count += 1
                        continue
                    # 有 message 字段
                    msg = json_data.get('message', '')
                    if msg:
                        self.history.add("assistant", msg)
                        self.display.ai(msg)
                        break

                elif isinstance(json_data, list):
                    tool_calls = [i for i in json_data
                                  if isinstance(i, dict) and i.get('action') == 'use_tool']
                    if tool_calls:
                        self._run_tools_batch(tool_calls)
                        break
                    cont = [i for i in json_data
                            if isinstance(i, dict) and (i.get('continue') or i.get('need_continue'))]
                    if cont:
                        msg = cont[0].get('message', '')
                        if msg:
                            self.history.add("assistant", msg)
                            self.display.ai(msg, is_continue=True)
                        loop_count += 1
                        continue

                self.display.ai(text or processed)
                break
            else:
                display = text or processed
                self.history.add("assistant", display)
                self.display.ai(display)
                break

    def _generate(self, user_input: str, sys_prompt: str) -> str:
        """生成 AI 响应（带动画）"""
        if self.tui_callback:
            resp = self.engine_mgr.generate(user_input, sys_prompt)
            if resp:
                self.history.add("assistant", resp)
            return resp

        stop = threading.Event()
        sentences = self._load_sentences()
        anim = threading.Thread(target=self.display.thinking, args=(sentences, stop), daemon=True)
        anim.start()

        try:
            resp = self.engine_mgr.generate(user_input, sys_prompt)
            if resp:
                self.display.typeprint(resp, Fore.CYAN)
                self.history.add("assistant", resp)
            return resp
        finally:
            stop.set()
            anim.join()

    def _run_tool(self, data: dict):
        """执行单个工具"""
        name = data.get('tool', '未知')
        args = data.get('args', '')
        uid = self.user_id

        # ESC 取消（仅 Windows）
        try:
            import msvcrt
            canceled = False
            for i in range(25):
                if msvcrt.kbhit() and msvcrt.getch() == b'\x1b':
                    canceled = True
                    break
                spin = '⊶' if i % 2 == 0 else '⊷'
                disp_args = args[:27] + "..." if len(args) > 30 else args
                sys.stdout.write(f"\r   正在执行: {spin} {name} {disp_args} (ESC取消)")
                sys.stdout.flush()
                time.sleep(0.2)
            sys.stdout.write("\r" + " " * 60 + "\r")
            if canceled:
                print(f"{Fore.YELLOW}已取消{Style.RESET_ALL}")
                return
        except ImportError:
            pass

        result = self._execute_tool(data)
        is_err = isinstance(result, str) and (result.startswith("错误") or result.startswith("工具执行错误"))
        if is_err:
            self.display.tool_err(name, args, result)
        else:
            self.display.tool_ok(name, args, result)

        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        self.history.add("assistant", f"工具结果 ({ts}):\n{result}")
        self.process_conversation(f"工具执行结果 ({ts}):\n{result}")

    def _run_tools_batch(self, calls: list):
        """批量并发执行工具"""
        self.display.info(f"批量执行 {len(calls)} 个工具")

        with ThreadPoolExecutor(max_workers=min(len(calls), 10)) as pool:
            futures = {pool.submit(self._execute_tool, c): i for i, c in enumerate(calls)}
            results = []
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    results.append((idx, future.result()))
                except Exception as e:
                    results.append((idx, f"错误: {e}"))

        results.sort(key=lambda x: x[0])
        ts = time.strftime("%Y-%m-%d %H:%M:%S")

        for i, (idx, result) in enumerate(results):
            name = calls[idx].get('tool', '未知')
            args = calls[idx].get('args', '')
            is_err = isinstance(result, str) and result.startswith("错误")
            if is_err:
                self.display.tool_err(name, args, result)
            else:
                self.display.tool_ok(name, args, result)

        all_results = "\n".join([f"工具{i + 1}: {r}" for i, (_, r) in enumerate(results)])
        self.history.add("assistant", f"批量结果 ({ts}):\n{all_results}")
        self.process_conversation(f"批量工具结果 ({ts}):\n{all_results}")

    def _execute_tool(self, data: dict) -> str:
        """调用统一工具管理器执行"""
        name = data.get('tool', '')
        args = data.get('args', '')
        arguments = data.get('arguments')

        try:
            if self.tool_mgr and hasattr(self.tool_mgr, 'execute'):
                if arguments and isinstance(arguments, dict):
                    result = self.tool_mgr.execute(name, args, **arguments)
                else:
                    result = self.tool_mgr.execute(name, args)
                if isinstance(result, dict):
                    return result.get('result', str(result))
                return str(result) if result else "无结果"
        except Exception as e:
            return f"工具执行错误: {e}"

        return f"未找到工具: {name}"

    def _get_tool_prompts(self) -> str:
        """获取工具提示词"""
        if not self.tool_mgr or not hasattr(self.tool_mgr, '_tools'):
            return ""

        lines = []
        for name, tool in self.tool_mgr._tools.items():
            desc = tool.get('description', '')
            lines.append(f"- {name}: {desc}")
        return '\n'.join(lines)

    def _load_sentences(self) -> list:
        path = os.path.join(self.dir, "love.txt")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return [l.strip() for l in f if l.strip()]
            except:
                pass
        return ["AI正在思考中...", "请稍等片刻..."]

    def _process_file_refs(self, text: str) -> str:
        """处理 @文件路径 语法"""
        pattern = r'@"([^"]+)"|@([^\s]+)'
        matches = list(re.finditer(pattern, text))
        if not matches:
            return text

        image_exts = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}
        parts = []
        last = 0

        for m in matches:
            if m.start() > last:
                parts.append(text[last:m.start()])

            path = (m.group(1) or m.group(2) or '').strip()
            if not path:
                continue
            path = os.path.normpath(os.path.expanduser(path))

            if os.path.isdir(path):
                try:
                    files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
                    parts.append(f"\n[目录: {path} - {len(files)} 个文件]\n" + '\n'.join(files[:20]))
                except Exception as e:
                    parts.append(f"[错误: {e}]")

            elif os.path.isfile(path):
                ext = os.path.splitext(path)[1].lower()
                if ext in image_exts:
                    parts.append(f"[图片: {path}]")
                else:
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        if len(content) > MAX_FILE_SIZE:
                            parts.append(f"[错误: 文件过大]")
                        else:
                            parts.append(f"\n[文件: {path}]\n{content}\n")
                            self.display.ok(f"已读取: {path}")
                    except UnicodeDecodeError:
                        try:
                            with open(path, 'r', encoding='gbk') as f:
                                parts.append(f"\n[文件: {path}]\n{f.read()}\n")
                        except:
                            parts.append(f"[错误: 无法读取 {path}]")
                    except Exception as e:
                        parts.append(f"[错误: {e}]")
            else:
                parts.append(f"[错误: 不存在 {path}]")

            last = m.end()

        if last < len(text):
            parts.append(text[last:])

        return ''.join(parts)

    def handle_liugin_message(self, message: str, **kwargs) -> str:
        """处理插件转发的消息（如 QQ）"""
        sys_prompt = "你是一个智能助手，简洁友好地回复。不要提及你是AI。"
        if self.engine_mgr.current:
            resp = self.engine_mgr.generate(message, sys_prompt)
            return resp or "抱歉，暂时无法回复。"
        return "AI 引擎未初始化"

    def ok(self, msg):
        self.display.ok(msg)

    def err(self, msg):
        self.display.err(msg)

    def cleanup(self):
        """清理资源"""
        self.display.warn("正在清理资源...")
        self.display.ok("资源清理完成")
