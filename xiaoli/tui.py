"""
小狸 Pro-CLI TUI v2 - 对标 Claude Code / OpenCode
现代化终端界面，支持代码高亮、工具时间线、文件浏览
"""
import asyncio
import os
import sys
import time
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical, VerticalScroll, Container
    from textual.widgets import (
        Header, Footer, Input, Static, Rule, Label,
        DataTable, ProgressBar, TabbedContent, TabPane
    )
    from textual.binding import Binding
    from textual.reactive import reactive, var
    from textual.message import Message
    from textual import work, on
    from rich.text import Text
    from rich.markdown import Markdown as RichMarkdown
    from rich.syntax import Syntax
    from rich.panel import Panel
    from rich.table import Table
    from rich.tree import Tree as RichTree
    from rich.columns import Columns
    from rich.align import Align
    from rich.box import ROUNDED, HEAVY, DOUBLE
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False


# ──────────────────────────────────────────────
# 主题色
# ──────────────────────────────────────────────

class Theme:
    BG = "#0d1117"
    BG_LIGHT = "#161b22"
    BG_INPUT = "#0d1117"
    BORDER = "#30363d"
    BORDER_FOCUS = "#58a6ff"
    TEXT = "#c9d1d9"
    TEXT_DIM = "#484f58"
    TEXT_MUTED = "#8b949e"
    ACCENT = "#58a6ff"
    SUCCESS = "#3fb950"
    WARNING = "#d29922"
    ERROR = "#f85149"
    USER = "#79c0ff"
    AI = "#c9d1d9"
    TOOL = "#56d364"
    TOOL_ERR = "#f85149"
    CODE_BG = "#161b22"
    LINK = "#58a6ff"


# ──────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────

CSS = f"""
Screen {{
    background: {Theme.BG};
}}

#app-container {{
    height: 100%;
    width: 100%;
}}

/* ── 主聊天区 ── */
#main {{
    width: 1fr;
    height: 1fr;
}}

#chat-scroll {{
    height: 1fr;
    background: {Theme.BG};
    scrollbar-color: {Theme.BORDER};
    scrollbar-color-hover: {Theme.TEXT_MUTED};
    padding: 0 1;
}}

#input-area {{
    height: auto;
    min-height: 4;
    max-height: 10;
    padding: 1 1 0 1;
}}

#user-input {{
    height: auto;
    min-height: 3;
    background: {Theme.BG_INPUT};
    border: tall {Theme.BORDER};
    color: {Theme.TEXT};
    padding: 0 1;
}}

#user-input:focus {{
    border: tall {Theme.BORDER_FOCUS};
}}

#input-hint {{
    height: 1;
    color: {Theme.TEXT_DIM};
    padding: 0 1;
    text-size: 80%;
}}

/* ── 侧边栏 ── */
#sidebar {{
    width: 32;
    min-width: 32;
    height: 1fr;
    background: {Theme.BG_LIGHT};
    border-left: wide {Theme.BORDER};
    display: block;
}}

#sidebar.hidden {{
    display: none;
    width: 0;
    min-width: 0;
}}

.sidebar-header {{
    width: 100%;
    text-align: center;
    color: {Theme.ACCENT};
    text-style: bold;
    padding: 1 0 0 0;
    text-size: 90%;
}}

.sidebar-section {{
    height: auto;
    padding: 0 1;
    margin: 0 0 1 0;
}}

.engine-item {{
    padding: 0 1;
    color: {Theme.TEXT_MUTED};
    text-size: 85%;
}}

.engine-item-active {{
    padding: 0 1;
    color: {Theme.SUCCESS};
    text-style: bold;
    text-size: 85%;
}}

.tool-item {{
    padding: 0 0 0 1;
    color: {Theme.TEXT_MUTED};
    text-size: 80%;
}}

.tool-item-name {{
    color: {Theme.TEXT};
    text-style: bold;
}}

/* ── 状态栏 ── */
#status-bar {{
    height: 1;
    width: 100%;
    dock: bottom;
    background: {Theme.BG_LIGHT};
    color: {Theme.TEXT_MUTED};
    padding: 0 1;
    text-size: 80%;
}}

/* ── 消息样式 ── */
.msg-user {{
    color: {Theme.USER};
    padding: 1 0 0 1;
    text-style: bold;
}}

.msg-ai {{
    color: {Theme.AI};
    padding: 0 1;
}}

.msg-system {{
    color: {Theme.ACCENT};
    padding: 0 1;
    text-size: 85%;
}}

.msg-tool-ok {{
    color: {Theme.TOOL};
    padding: 0 1;
    text-size: 85%;
}}

.msg-tool-err {{
    color: {Theme.TOOL_ERR};
    padding: 0 1;
    text-size: 85%;
}}

.msg-thinking {{
    color: {Theme.TEXT_DIM};
    text-style: italic;
    padding: 0 1;
}}

.msg-error {{
    color: {Theme.ERROR};
    padding: 0 1;
}}

.msg-dim {{
    color: {Theme.TEXT_DIM};
    padding: 0 1;
    text-size: 85%;
}}

.msg-welcome {{
    color: {Theme.ACCENT};
    padding: 0 1;
    text-style: bold;
}}

/* ── 代码块 ── */
.code-block {{
    background: {Theme.CODE_BG};
    border: wide {Theme.BORDER};
    padding: 0 1;
    margin: 0 2 0 2;
    text-size: 85%;
}}

/* ── Tab ── */
Tab {{
    background: {Theme.BG};
}}

Tab.-active {{
    background: {Theme.BG_LIGHT};
}}

TabbedContent > Tabs {{
    background: {Theme.BG};
}}
"""


# ──────────────────────────────────────────────
# 消息组件
# ──────────────────────────────────────────────

class ChatMessage(Static):
    """单条聊天消息"""
    def __init__(self, content, msg_type="ai", **kwargs):
        self.msg_type = msg_type
        super().__init__(content, **kwargs)


# ──────────────────────────────────────────────
# 桥接
# ──────────────────────────────────────────────

class TUIBridge:
    def __init__(self, app_instance):
        self.app = app_instance

    def engines(self) -> list:
        return self.app.engine_mgr.names()

    def current_engine(self) -> str:
        return self.app.engine_mgr.current_name()

    def tools(self) -> list:
        if self.app.tool_mgr and hasattr(self.app.tool_mgr, '_tools'):
            return list(self.app.tool_mgr._tools.values())
        return []

    def history(self) -> list:
        return self.app.history.get()

    def switch_engine(self, name: str) -> bool:
        return self.app._switch_model(name)


# ──────────────────────────────────────────────
# 主应用
# ──────────────────────────────────────────────

class XiaoliTUI(App):
    """小狸 TUI v2"""

    CSS = CSS
    TITLE = "🐱 小狸 Pro-CLI"
    SUB_TITLE = "智能编程助手 v5.0"

    BINDINGS = [
        Binding("ctrl+c", "quit", "退出", show=True),
        Binding("ctrl+l", "clear", "清屏", show=True),
        Binding("ctrl+n", "new_chat", "新对话", show=True),
        Binding("f1", "toggle_sidebar", "侧栏", show=True),
        Binding("f2", "toggle_tools", "工具", show=True),
        Binding("escape", "cancel", "取消", show=False),
    ]

    sidebar_visible = var(True)
    is_generating = var(False)

    def __init__(self, app_instance):
        super().__init__()
        self.app_inst = app_instance
        self.bridge = TUIBridge(app_instance)
        self._tool_calls = []  # 工具调用历史

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="app-container"):
            # 主聊天区
            with Vertical(id="main"):
                yield VerticalScroll(id="chat-scroll")
                with Vertical(id="input-area"):
                    yield Input(
                        placeholder="  输入消息... (Enter 发送, /help 帮助)",
                        id="user-input"
                    )
                    yield Static(
                        "  Tab 补全 | ↑↓ 历史 | Ctrl+L 清屏 | F1 侧栏",
                        id="input-hint"
                    )
            # 侧边栏
            with Vertical(id="sidebar"):
                yield Static("⚙️  引擎", classes="sidebar-header")
                yield Vertical(id="engine-list", classes="sidebar-section")
                yield Rule(line_style="heavy")
                yield Static("🔧 工具", classes="sidebar-header")
                yield Vertical(id="tool-list", classes="sidebar-section")
                yield Rule(line_style="heavy")
                yield Static("📊 状态", classes="sidebar-header")
                yield Vertical(id="status-info", classes="sidebar-section")
        yield Static(" 就绪 | ollama | Ctrl+C 退出", id="status-bar")

    def on_mount(self):
        self._render_welcome()
        self._update_sidebar()
        self.query_one("#user-input").focus()

    # ── 渲染 ──

    def _render_welcome(self):
        scroll = self.query_one("#chat-scroll")
        lines = [
            ("", "msg-dim"),
            ("  ╔══════════════════════════════════════════════╗", "msg-welcome"),
            ("  ║                                              ║", "msg-welcome"),
            ("  ║   🐱 小狸 Pro-CLI v5.0                       ║", "msg-welcome"),
            ("  ║   智能编程助手 · 对标 Claude Code              ║", "msg-welcome"),
            ("  ║                                              ║", "msg-welcome"),
            ("  ╚══════════════════════════════════════════════╝", "msg-welcome"),
            ("", "msg-dim"),
            ("  💡 代码编辑 · 代码搜索 · Git 集成 · 多引擎", "msg-system"),
            ("  📝 输入 /help 查看命令 | /model 切换引擎", "msg-system"),
            (f"  🔧 当前引擎: {self.bridge.current_engine()} | 工具: {len(self.bridge.tools())} 个", "msg-system"),
            ("", "msg-dim"),
        ]
        for text, cls in lines:
            scroll.mount(Static(text, classes=cls))

    def _update_sidebar(self):
        # 引擎列表
        engine_container = self.query_one("#engine-list")
        engine_container.remove_children()
        current = self.bridge.current_engine()
        for name in self.bridge.engines():
            if name == current:
                engine_container.mount(Static(f"  ▸ {name}", classes="engine-item-active"))
            else:
                engine_container.mount(Static(f"    {name}", classes="engine-item"))

        # 工具列表
        tool_container = self.query_one("#tool-list")
        tool_container.remove_children()
        for tool in self.bridge.tools():
            name = tool.get('name', '?')
            tool_container.mount(Static(f"  • {name}", classes="tool-item"))

        # 状态信息
        status_container = self.query_one("#status-info")
        status_container.remove_children()
        status_container.mount(Static(f"  对话: {len(self.bridge.history())} 条", classes="tool-item"))
        status_container.mount(Static(f"  工具: {len(self.bridge.tools())} 个", classes="tool-item"))
        status_container.mount(Static(f"  引擎: {len(self.bridge.engines())} 个", classes="tool-item"))

    def _update_status(self, text: str):
        bar = self.query_one("#status-bar")
        engine = self.bridge.current_engine()
        bar.update(f" {text} | {engine} | {len(self.bridge.history())} 条对话")

    def _append(self, widget):
        scroll = self.query_one("#chat-scroll")
        scroll.mount(widget)
        scroll.scroll_end(animate=False)

    def _add(self, text, cls="msg-dim"):
        self._append(Static(text, classes=cls))

    # ── 消息类型 ──

    def _user_msg(self, text):
        self._add(f"  👤 {text}", "msg-user")

    def _ai_msg(self, text):
        # 检测代码块并高亮
        if "```" in text:
            self._render_with_code(text)
        else:
            self._add(f"  ✦ {text}", "msg-ai")

    def _render_with_code(self, text):
        """渲染包含代码块的消息"""
        import re
        parts = re.split(r'```(\w*)\n(.*?)```', text, flags=re.DOTALL)
        i = 0
        while i < len(parts):
            if i % 3 == 0:
                # 普通文本
                if parts[i].strip():
                    for line in parts[i].strip().split('\n'):
                        self._add(f"  ✦ {line}", "msg-ai")
            elif i % 3 == 1:
                # 语言标识
                pass
            elif i % 3 == 2:
                # 代码块
                code = parts[i]
                lang = parts[i-1] if i > 1 else ""
                try:
                    syntax = Syntax(code, lang or "python", theme="monokai",
                                    line_numbers=True, word_wrap=True)
                    self._append(Panel(syntax, border_style=f"dim {Theme.BORDER}",
                                       box=ROUNDED, padding=(0, 1)))
                except:
                    for line in code.split('\n'):
                        self._add(f"    {line}", "msg-dim")
            i += 1

    def _tool_ok(self, name, args):
        self._add(f"  ✅ {name}: {args[:60]}", "msg-tool-ok")

    def _tool_err(self, name, args):
        self._add(f"  ❌ {name}: {args[:60]}", "msg-tool-err")

    def _thinking(self):
        self._add("  💭 思考中...", "msg-thinking")

    def _system(self, text):
        self._add(f"  ℹ️  {text}", "msg-system")

    def _error(self, text):
        self._add(f"  ⚠️  {text}", "msg-error")

    # ── 命令处理 ──

    @on(Input.Submitted, "#user-input")
    def on_input(self, event):
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""

        if text.startswith('/'):
            self._handle_command(text)
            return

        self._user_msg(text)
        self._thinking()
        self.is_generating = True
        self._update_status("🔄 思考中...")
        self.run_worker(self._generate(text), exclusive=True)

    def _handle_command(self, cmd):
        parts = cmd[1:].split(maxsplit=1)
        name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        cmds = {
            'help': lambda: self._show_help(),
            'quit': lambda: self.exit(),
            'q': lambda: self.exit(),
            'exit': lambda: self.exit(),
            'cli': lambda: self._switch_cli(),
            'clear': lambda: self.action_clear(),
            'cls': lambda: self.action_clear(),
            'model': lambda: self._switch_model(args),
            'engine': lambda: self._switch_model(args),
            'about': lambda: self._system("🐱 小狸 Pro-CLI v5.0 - 智能编程助手"),
            'status': lambda: self._show_status(),
            'tools': lambda: self._show_tools(),
            'engines': lambda: self._show_engines(),
        }

        handler = cmds.get(name)
        if handler:
            handler()
        else:
            self._error(f"未知命令: /{name}，输入 /help 查看帮助")

    def _show_help(self):
        help_text = """  📖 命令:
  /help          帮助信息
  /quit          退出
  /cli           切换命令行模式
  /model <引擎>  切换 AI 引擎
  /engines       列出引擎
  /tools         列出工具
  /status        系统状态
  /clear         清屏

  ⌨️  快捷键:
  Ctrl+C   退出    Ctrl+L   清屏
  Ctrl+N   新对话  F1       侧栏
  Escape   取消生成"""
        self._system(help_text)

    def _switch_cli(self):
        self._system("切换到命令行模式...")
        self.app_inst.tui_callback = None
        self.exit()

    def _switch_model(self, name):
        name = name.strip()
        if not name:
            self._show_engines()
            return
        if self.bridge.switch_engine(name):
            self._system(f"已切换到: {name}")
            self._update_sidebar()
        else:
            self._error(f"未找到引擎: {name}")

    def _show_engines(self):
        current = self.bridge.current_engine()
        lines = ["  可用引擎:"]
        for name in self.bridge.engines():
            marker = "▸" if name == current else " "
            lines.append(f"  {marker} {name}")
        self._system('\n'.join(lines))

    def _show_tools(self):
        tools = self.bridge.tools()
        lines = [f"  可用工具 ({len(tools)} 个):"]
        for t in tools:
            name = t.get('name', '?')
            desc = t.get('description', '')[:40]
            lines.append(f"  • {name}: {desc}")
        self._system('\n'.join(lines))

    def _show_status(self):
        self._system(f"""  系统状态:
  引擎: {self.bridge.current_engine()}
  引擎数: {len(self.bridge.engines())}
  工具数: {len(self.bridge.tools())}
  对话数: {len(self.bridge.history())}""")

    # ── 生成 ──

    async def _generate(self, user_input):
        try:
            self.call_after_refresh(self._remove_thinking)

            def tui_output(msg):
                self.call_after_refresh(self._write_raw, msg)

            original = self.app_inst.tui_callback
            self.app_inst.tui_callback = tui_output

            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, self.app_inst.process_conversation, user_input
                )
            finally:
                self.app_inst.tui_callback = original

        except Exception as e:
            self.call_after_refresh(self._error, str(e))
        finally:
            self.is_generating = False
            self.call_after_refresh(lambda: self._update_status("就绪"))
            self.call_after_refresh(self._update_sidebar)

    def _remove_thinking(self):
        scroll = self.query_one("#chat-scroll")
        for child in reversed(list(scroll.children)):
            if '思考中' in str(getattr(child, 'renderable', '')):
                child.remove()
                break

    def _write_raw(self, msg):
        if '✅' in msg or 'OK 工具' in msg:
            self._add(f"  {msg}", "msg-tool-ok")
        elif '❌' in msg or 'X 工具' in msg or '错误' in msg:
            self._add(f"  {msg}", "msg-tool-err")
        elif '✦' in msg:
            self._add(f"  {msg}", "msg-ai")
        elif '工具' in msg and ('调用' in msg or '执行' in msg):
            self._add(f"  {msg}", "msg-tool-ok")
        else:
            self._add(f"  {msg}", "msg-dim")

    # ── 动作 ──

    def action_clear(self):
        scroll = self.query_one("#chat-scroll")
        scroll.remove_children()
        self._render_welcome()

    def action_new_chat(self):
        self.app_inst.history.clear()
        self.action_clear()
        self._system("已开始新对话")

    def action_toggle_sidebar(self):
        sidebar = self.query_one("#sidebar")
        sidebar.visible = not sidebar.visible

    def action_toggle_tools(self):
        self.action_toggle_sidebar()

    def action_cancel(self):
        if self.is_generating:
            self._system("已取消")
            self.is_generating = False


# ──────────────────────────────────────────────
# 启动
# ──────────────────────────────────────────────

def run_tui(app_instance):
    if not TEXTUAL_AVAILABLE:
        print("⚠️  Textual 未安装")
        print("   pip install textual rich")
        return
    XiaoliTUI(app_instance).run()
