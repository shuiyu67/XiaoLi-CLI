"""
小狸 Pro-CLI TUI - 现代化终端界面
"""
import asyncio
import os
import sys
from datetime import datetime

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical, VerticalScroll
    from textual.widgets import Header, Footer, Input, Static, Rule, Label
    from textual.binding import Binding
    from textual.reactive import reactive
    from rich.text import Text
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    from rich.panel import Panel
    from rich.console import Group
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False


# ──────────────────────────────────────────────
# 样式常量
# ──────────────────────────────────────────────

CSS = """
Screen {
    background: #0a0e14;
    layers: base overlay;
}

#main-container {
    height: 100%;
    width: 100%;
}

#chat-area {
    width: 1fr;
    height: 1fr;
    padding: 0 1;
}

#chat-log {
    height: 1fr;
    background: #0a0e14;
    border: none;
    scrollbar-color: #3d5a80;
    scrollbar-color-hover: #5a8ab5;
}

#input-container {
    height: auto;
    min-height: 3;
    max-height: 8;
    padding: 0 0 1 0;
}

#user-input {
    height: auto;
    min-height: 3;
    background: #1a1e24;
    border: tall #3d5a80;
    color: #e0e0e0;
    padding: 0 1;
}

#user-input:focus {
    border: tall #5a8ab5;
}

#sidebar {
    width: 28;
    min-width: 28;
    height: 1fr;
    background: #0d1117;
    border-left: wide #1a2332;
    padding: 1 0;
}

#sidebar-title {
    width: 100%;
    text-align: center;
    color: #5a8ab5;
    text-style: bold;
    padding: 0 0 1 0;
}

#engine-list {
    height: auto;
    max-height: 12;
    background: #0d1117;
    padding: 0 1;
    margin: 0 0 1 0;
}

#engine-item {
    padding: 0 1;
    color: #8899aa;
}

#engine-item-active {
    padding: 0 1;
    color: #58d68d;
    text-style: bold;
}

#tool-list {
    height: 1fr;
    background: #0d1117;
    padding: 0 1;
    overflow-y: auto;
}

#tool-item {
    padding: 0 1;
    color: #6688aa;
    text-size: 90%;
}

#status-bar {
    height: 1;
    width: 100%;
    dock: bottom;
    background: #1a2332;
    color: #5a8ab5;
    padding: 0 1;
}

#welcome {
    width: 100%;
    text-align: center;
    color: #5a8ab5;
    padding: 2 0;
}

#version-info {
    width: 100%;
    text-align: center;
    color: #445566;
    padding: 0 0 2 0;
}

.user-msg {
    color: #e0e0e0;
    padding: 0 0 0 1;
    margin: 0 0 0 0;
}

.ai-msg {
    color: #c0d0e0;
    padding: 0 0 0 0;
}

.tool-msg-ok {
    color: #58d68d;
    padding: 0 0 0 1;
}

.tool-msg-err {
    color: #e74c3c;
    padding: 0 0 0 1;
}

.thinking-msg {
    color: #7f8c8d;
    text-style: italic;
}

.system-msg {
    color: #5a8ab5;
    padding: 0 0 0 1;
}

.error-msg {
    color: #e74c3c;
    padding: 0 0 0 1;
}

.dim {
    color: #556677;
}
"""


class ChatLog(VerticalScroll):
    """聊天日志区域"""
    pass


class Sidebar(Vertical):
    """侧边栏"""
    pass


class XiaoliTUI(App):
    """小狸 TUI 主应用"""

    CSS = CSS
    TITLE = "小狸 Pro-CLI"
    SUB_TITLE = "智能编程助手"

    BINDINGS = [
        Binding("ctrl+c", "quit", "退出", show=True),
        Binding("ctrl+l", "clear_chat", "清屏", show=True),
        Binding("ctrl+n", "new_chat", "新对话", show=True),
        Binding("f1", "toggle_sidebar", "侧栏", show=True),
    ]

    is_generating = reactive(False)

    def __init__(self, app_instance):
        super().__init__()
        self.app_inst = app_instance
        self.bridge = TUIBridge(app_instance)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-container"):
            with Vertical(id="chat-area"):
                yield ChatLog(id="chat-log")
                with Vertical(id="input-container"):
                    yield Input(
                        placeholder="  输入消息... (Enter 发送, /help 帮助)",
                        id="user-input"
                    )
            with Vertical(id="sidebar"):
                yield Static("⚙️ AI 引擎", id="sidebar-title")
                yield Vertical(id="engine-list")
                yield Rule(line_style="ascii")
                yield Static("🔧 可用工具", id="sidebar-title")
                yield Vertical(id="tool-list")
        yield Static(" 就绪", id="status-bar")

    def on_mount(self) -> None:
        self._render_welcome()
        self._update_engines()
        self._update_tools()
        self.query_one("#user-input").focus()

    def _render_welcome(self):
        chat = self.query_one("#chat-log")
        chat.mount(Static("", classes="dim"))
        chat.mount(Static("  ╔══════════════════════════════════════╗", classes="system-msg"))
        chat.mount(Static("  ║                                      ║", classes="system-msg"))
        chat.mount(Static("  ║   🐱 小狸 Pro-CLI v3.6               ║", classes="system-msg"))
        chat.mount(Static("  ║   智能编程助手                        ║", classes="system-msg"))
        chat.mount(Static("  ║                                      ║", classes="system-msg"))
        chat.mount(Static("  ╚══════════════════════════════════════╝", classes="system-msg"))
        chat.mount(Static("", classes="dim"))
        chat.mount(Static("  💡 快捷键: Ctrl+L 清屏 | Ctrl+N 新对话 | F1 侧栏", classes="dim"))
        chat.mount(Static("  📝 输入 /help 查看所有命令", classes="dim"))
        chat.mount(Static(f"  🔧 当前引擎: {self.bridge.get_current_engine_name()}", classes="dim"))
        chat.mount(Static("", classes="dim"))

    def _update_engines(self):
        container = self.query_one("#engine-list")
        container.remove_children()
        current = self.bridge.get_current_engine_name()
        for name in self.bridge.get_engines():
            cls = "engine-item-active" if name == current else "engine-item"
            prefix = "▸ " if name == current else "  "
            container.mount(Static(f"{prefix}{name}", id=f"engine-{name}", classes=cls))

    def _update_tools(self):
        container = self.query_one("#tool-list")
        container.remove_children()
        tools = self.bridge.get_tools()
        for tool in tools:
            name = tool.get('name', '?')
            container.mount(Static(f"  • {name}", classes="tool-item"))

    def _update_status(self, text: str):
        status = self.query_one("#status-bar")
        status.update(f" {text}")

    def _append_chat(self, widget):
        chat = self.query_one("#chat-log")
        chat.mount(widget)
        chat.scroll_end(animate=False)

    def _add_user_msg(self, text: str):
        self._append_chat(Static(f"  你: {text}", classes="user-msg"))

    def _add_ai_msg(self, text: str):
        # 尝试渲染 Markdown
        try:
            from rich.markdown import Markdown
            md = Markdown(text)
            self._append_chat(Static(md, classes="ai-msg"))
        except:
            self._append_chat(Static(f"  ✦ {text}", classes="ai-msg"))

    def _add_tool_ok(self, name: str, args: str):
        self._append_chat(Static(f"  ✅ {name}: {args[:50]}", classes="tool-msg-ok"))

    def _add_tool_err(self, name: str, args: str):
        self._append_chat(Static(f"  ❌ {name}: {args[:50]}", classes="tool-msg-err"))

    def _add_system(self, text: str):
        self._append_chat(Static(f"  ℹ️  {text}", classes="system-msg"))

    def _add_error(self, text: str):
        self._append_chat(Static(f"  ⚠️  {text}", classes="error-msg"))

    def _add_thinking(self):
        self._append_chat(Static("  💭 AI 正在思考...", classes="thinking-msg"))

    def on_input_submitted(self, event: Input.Submitted):
        user_input = event.value.strip()
        if not user_input:
            return

        event.input.value = ""

        # 命令处理
        if user_input.startswith('/'):
            self._handle_command(user_input)
            return

        # 显示用户消息
        self._add_user_msg(user_input)

        # 思考提示
        self._add_thinking()

        # 异步生成
        self.is_generating = True
        self._update_status("🔄 AI 思考中...")
        self.run_worker(self._generate(user_input), exclusive=True)

    def _handle_command(self, cmd: str):
        parts = cmd[1:].split(maxsplit=1)
        name = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        if name == 'help':
            self._show_help()
        elif name == 'quit':
            self.exit()
        elif name == 'cli':
            self._add_system("切换到 CLI 模式...")
            self.app_inst.tui_callback = None
            self.exit()
            self.app_inst.run()
        elif name == 'model' or name == 'engine':
            if args.startswith('switch '):
                args = args[7:]
            if self.bridge.switch_engine(args):
                self._add_system(f"已切换到引擎: {args}")
                self._update_engines()
            else:
                self._add_error(f"未找到引擎: {args}")
        elif name == 'clear':
            self.action_clear_chat()
        elif name == 'about':
            self._add_system("小狸 Pro-CLI v3.6 - 智能编程助手")
        elif name == 'chat':
            self._add_system("聊天记录功能请使用 CLI 模式")
        else:
            self._add_error(f"未知命令: /{name}，输入 /help 查看帮助")

    def _show_help(self):
        help_text = """  📖 命令列表:
  /help          - 帮助信息
  /quit          - 退出
  /cli           - 切换到命令行模式
  /model <引擎>  - 切换 AI 引擎
  /clear         - 清屏
  /about         - 关于

  ⌨️  快捷键:
  Ctrl+C  退出
  Ctrl+L  清屏
  Ctrl+N  新对话
  F1      切换侧栏"""
        self._add_system(help_text)

    async def _generate(self, user_input: str):
        try:
            # 清除思考提示
            self.call_after_refresh(self._remove_last_thinking)

            # 回调输出到 TUI
            def tui_output(msg):
                self.call_after_refresh(self._write_raw, msg)

            original_cb = self.app_inst.tui_callback
            self.app_inst.tui_callback = tui_output

            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, self.app_inst.process_conversation, user_input
                )
            finally:
                self.app_inst.tui_callback = original_cb

        except Exception as e:
            self.call_after_refresh(self._add_error, str(e))
        finally:
            self.is_generating = False
            self.call_after_refresh(self._update_status, "就绪")

    def _remove_last_thinking(self):
        """移除最后一条思考消息"""
        chat = self.query_one("#chat-log")
        children = list(chat.children)
        for child in reversed(children):
            if hasattr(child, 'renderable') and '思考' in str(getattr(child, 'renderable', '')):
                child.remove()
                break

    def _write_raw(self, message: str):
        """直接写入消息（来自回调）"""
        if '✅' in message or 'OK 工具' in message:
            self._append_chat(Static(f"  {message}", classes="tool-msg-ok"))
        elif '❌' in message or 'X 工具' in message or '错误' in message:
            self._append_chat(Static(f"  {message}", classes="tool-msg-err"))
        elif '✦' in message:
            self._append_chat(Static(f"  {message}", classes="ai-msg"))
        else:
            self._append_chat(Static(f"  {message}", classes="dim"))

    def action_clear_chat(self):
        chat = self.query_one("#chat-log")
        chat.remove_children()
        self._render_welcome()

    def action_new_chat(self):
        self.app_inst.history.clear()
        self.action_clear_chat()
        self._add_system("已开始新对话")

    def action_toggle_sidebar(self):
        sidebar = self.query_one("#sidebar")
        sidebar.visible = not sidebar.visible


class TUIBridge:
    """桥接 TUI 和 App"""

    def __init__(self, app_instance):
        self.app = app_instance

    def get_engines(self) -> list:
        return self.app.engine_mgr.names()

    def get_current_engine_name(self) -> str:
        return self.app.engine_mgr.current_name()

    def get_tools(self) -> list:
        if self.app.tool_mgr and hasattr(self.app.tool_mgr, '_tools'):
            return list(self.app.tool_mgr._tools.values())
        return []

    def get_conversation_history(self) -> list:
        return self.app.history.get()

    def switch_engine(self, name: str) -> bool:
        return self.app._switch_model(name) or False


def run_tui(app_instance):
    """启动 TUI"""
    if not TEXTUAL_AVAILABLE:
        print("⚠️  Textual 未安装，无法启动 TUI")
        print("   安装: pip install textual rich")
        return
    tui = XiaoliTUI(app_instance)
    tui.run()
