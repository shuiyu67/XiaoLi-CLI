"""TUI 界面模块 — 基于 elia 开源项目架构重写

原项目: https://github.com/darrenburns/elia (Apache-2.0)
核心组件: Chatbox(Markdown渲染) + ResponseStatus(LoadingIndicator) + @work(thread=True)流式
"""

from .constants import TEXTUAL_AVAILABLE

if TEXTUAL_AVAILABLE:
    import re
    import os
    from functools import partial
    from dataclasses import dataclass
    from textual.app import App, ComposeResult, SystemCommand
    from textual.containers import Horizontal, Vertical, VerticalScroll, Container
    from textual.widgets import Header, Static, Rule, TextArea, Footer, LoadingIndicator, Label
    from textual.widgets.option_list import Option
    from textual.reactive import var, reactive
    from textual.binding import Binding
    from textual import on, work, events
    from textual.message import Message
    from textual.widget import Widget
    from textual.css.query import NoMatches
    from textual.command import CommandPalette, CommandList
    from textual.screen import Screen
    from rich.console import RenderableType
    from rich.markdown import Markdown
    from rich.syntax import Syntax
    from rich.text import Text
    from rich.align import Align
    from typing import Iterable

    # ═══════════════════════════════════════════════════
    #  主题色
    # ═══════════════════════════════════════════════════

    class _Theme:
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
        AI = "#f0f6fc"
        TOOL = "#56d364"
        CODE_BG = "#161b22"
        GLOW = "#1f6feb"
        THINKING = "#8b949e"

    # ═══════════════════════════════════════════════════
    #  CSS（融合 elia 样式 + 项目主题色）
    # ═══════════════════════════════════════════════════

    _TUI_CSS = f"""
    Screen {{
        background: {_Theme.BG};
    }}

    #app-container {{
        height: 1fr;
        width: 100%;
        layout: vertical;
    }}

    #chat-scroll {{
        height: 1fr;
        background: {_Theme.BG};
        scrollbar-color: {_Theme.BORDER};
        scrollbar-color-hover: {_Theme.TEXT_MUTED};
        padding: 0 1;
    }}

    /* ── 输入区域 (elia PromptInput 风格) ── */
    #input-area {{
        height: auto;
        min-height: 5;
        max-height: 14;
        padding: 0 1 1 1;
    }}

    #input-wrapper {{
        height: auto;
        min-height: 4;
        max-height: 12;
        background: {_Theme.BG_INPUT};
        border: round {_Theme.BORDER};
        padding: 0;
        transition: border-color 300ms in_out_cubic;
    }}

    #input-wrapper:focus-within {{
        border: round {_Theme.BORDER_FOCUS};
        background: {_Theme.BG};
    }}

    #user-input {{
        height: auto;
        min-height: 3;
        max-height: 10;
        background: transparent;
        color: {_Theme.TEXT};
        padding: 0 1;
        border: none;
    }}

    #user-input:focus {{
        background: transparent;
    }}

    #user-input .text-area--cursor {{
        color: {_Theme.ACCENT};
    }}

    #user-input .text-area--cursor-line {{
        background: {_Theme.BG_LIGHT} 50%;
    }}

    #user-input .text-area--selection {{
        background: {_Theme.GLOW} 40%;
    }}

    #input-hint {{
        height: 1;
        color: {_Theme.TEXT_DIM};
        padding: 0 1;
        opacity: 0;
        transition: opacity 500ms in_out_cubic;
    }}

    #input-hint.visible {{
        opacity: 1;
    }}

    /* ── 命令提示浮层 — 在输入框上方，display:none 时不占空间 ── */
    #command-hint {{
        layer: overlay;
        display: none;
        height: auto;
        max-height: 10;
        width: 1fr;
        margin: 0 1 1 1;
        padding: 0 1;
        background: {_Theme.BG_LIGHT} 98%;
        border: round {_Theme.ACCENT};
        overflow-y: auto;
    }}
    .cmd-hint-cmd {{
        color: {_Theme.ACCENT};
        text-style: bold;
    }}
    .cmd-hint-desc {{
        color: {_Theme.TEXT_DIM};
    }}

    /* ── 安全审查确认浮层 ── */
    #confirm-overlay {{
        dock: top;
        layer: overlay;
        display: none;
        height: auto;
        max-height: 16;
        width: 60;
        min-width: 40;
        margin: 2 4;
        padding: 1 2;
        background: {_Theme.BG};
        border: heavy {_Theme.ERROR};
        overflow-y: auto;
    }}
    #confirm-overlay.visible {{
        display: block;
    }}

    /* ── 辅助中心 ── 背景遮罩 + 居中卡片 */
    #settings-backdrop {{
        layer: overlay;
        width: 100%;
        height: 100%;
        display: none;
        background: {_Theme.BG} 70%;
        offset: 0 0;
        opacity: 0;
        transition: opacity 220ms out_cubic;
    }}
    #settings-backdrop.visible {{
        display: block;
        opacity: 1;
    }}
    #settings-backdrop.hiding {{
        opacity: 0;
        transition: opacity 180ms in_cubic;
    }}

    #settings-overlay {{
        layer: overlay;
        dock: top;
        display: none;
        height: auto;
        max-height: 28;
        width: 76;
        min-width: 56;
        margin: 2 4;
        padding: 1 2;
        background: {_Theme.BG_LIGHT} 98%;
        border: round {_Theme.ACCENT} 80%;
        overflow-y: auto;
        offset: 0 -12;
        opacity: 0;
        transition: offset 320ms out_cubic, opacity 280ms out_cubic;
    }}
    #settings-overlay.visible {{
        display: block;
        offset: 0 0;
        opacity: 1;
    }}
    #settings-overlay.hiding {{
        offset: 0 -12;
        opacity: 0;
        transition: offset 240ms in_cubic, opacity 200ms in_cubic;
    }}
    .settings-title {{
        color: {_Theme.ACCENT};
        text-style: bold;
        text-align: center;
        padding: 0 0 1 0;
    }}
    .settings-section {{
        color: {_Theme.TEXT_MUTED};
        text-style: bold;
        padding: 1 0 0 0;
    }}
    .settings-line {{
        color: {_Theme.TEXT};
        padding: 0 1;
    }}
    .settings-hint {{
        color: {_Theme.TEXT_DIM};
        text-style: italic;
        padding: 1 0 0 0;
    }}
    .settings-key {{
        color: {_Theme.WARNING};
        text-style: bold;
    }}
    .settings-val {{
        color: {_Theme.SUCCESS};
        text-style: bold;
    }}

    /* ── 帮助浮层 ── 背景遮罩 + 居中卡片 */
    #help-backdrop {{
        layer: overlay;
        width: 100%;
        height: 100%;
        display: none;
        background: {_Theme.BG} 70%;
        offset: 0 0;
        opacity: 0;
        transition: opacity 220ms out_cubic;
    }}
    #help-backdrop.visible {{
        display: block;
        opacity: 1;
    }}
    #help-backdrop.hiding {{
        opacity: 0;
        transition: opacity 180ms in_cubic;
    }}

    #help-overlay {{
        layer: overlay;
        dock: top;
        display: none;
        height: auto;
        max-height: 32;
        width: 80;
        min-width: 60;
        margin: 1 2;
        padding: 1 2;
        background: {_Theme.BG_LIGHT} 98%;
        border: round {_Theme.ACCENT} 80%;
        overflow-y: auto;
        offset: 0 -12;
        opacity: 0;
        transition: offset 320ms out_cubic, opacity 280ms out_cubic;
    }}
    #help-overlay.visible {{
        display: block;
        offset: 0 0;
        opacity: 1;
    }}
    #help-overlay.hiding {{
        offset: 0 -12;
        opacity: 0;
        transition: offset 240ms in_cubic, opacity 200ms in_cubic;
    }}

    /* ── 侧栏 ── 横向滑入滑出 + 淡入淡出 */
    #sidebar {{
        width: 32;
        min-width: 32;
        height: 1fr;
        dock: right;
        background: {_Theme.BG_LIGHT};
        border-left: tall {_Theme.BORDER};
        /* 用 opacity 控制可见性，offset 制造滑入滑出感 */
        opacity: 0;
        offset: 16 0;
        display: none;
        transition: offset 320ms out_cubic, opacity 280ms out_cubic;
    }}

    #sidebar.visible {{
        display: block;
        opacity: 1;
        offset: 0 0;
    }}

    #sidebar.hiding {{
        opacity: 0;
        offset: 16 0;
        transition: offset 240ms in_cubic, opacity 200ms in_cubic;
    }}

    .sidebar-header {{
        width: 100%;
        text-align: center;
        color: {_Theme.ACCENT};
        text-style: bold;
        padding: 1 0 0 0;
    }}

    .sidebar-section {{
        height: auto;
        padding: 0 1;
        margin: 0 0 1 0;
    }}

    .engine-item {{
        padding: 0 1;
        color: {_Theme.TEXT_MUTED};
    }}

    .engine-item-active {{
        padding: 0 1;
        color: {_Theme.SUCCESS};
        text-style: bold;
    }}

    .tool-item {{
        padding: 0 0 0 1;
        color: {_Theme.TEXT_MUTED};
    }}

    /* ── 可切换背景效果 — 通过 #chat-scroll 的 class 切换 ──
       Textual CSS 不支持 gradient 函数，改用纯色色调切换
       bg-grid:  深蓝灰
       bg-stars: 深紫
       bg-glow:  深蓝
       默认(无 class): 原始深黑
    */
    #chat-scroll.bg-grid {{
        background: #11161e;
    }}
    #chat-scroll.bg-stars {{
        background: #16121f;
    }}
    #chat-scroll.bg-glow {{
        background: #0f1620;
    }}

    /* ── 状态栏 ── */
    #status-bar {{
        height: 1;
        width: 100%;
        dock: bottom;
        background: {_Theme.BG_LIGHT};
        color: {_Theme.TEXT_MUTED};
        padding: 0 1;
    }}

    #status-bar.pulse {{
        color: {_Theme.WARNING};
        background: {_Theme.GLOW} 40%;
        transition: color 150ms, background 150ms;
    }}

    /* ── Footer ── */
    Footer {{
        background: {_Theme.BG_LIGHT};
        color: {_Theme.TEXT_MUTED};
        border-top: tall {_Theme.BORDER};
    }}

    Footer > .key {{
        background: {_Theme.BG};
        color: {_Theme.ACCENT};
    }}

    /* ── 消息样式 ── */
    .msg-system {{
        color: {_Theme.ACCENT};
        padding: 0 1;
    }}

    .msg-tool-ok {{
        color: {_Theme.SUCCESS};
        padding: 0 1;
    }}

    .msg-tool-err {{
        color: {_Theme.ERROR};
        padding: 0 1;
    }}

    .msg-error {{
        color: {_Theme.ERROR};
        padding: 0 1;
    }}

    .msg-dim {{
        color: {_Theme.TEXT_DIM};
        padding: 0 1;
    }}

    .msg-welcome {{
        color: {_Theme.ACCENT};
        padding: 0 1;
        text-style: bold;
    }}

    /* ── ResponseStatus (elia 原版) ── */
    ResponseStatus {{
        dock: top;
        align-horizontal: right;
        display: none;
        layer: overlay;
        height: 2;
        width: auto;
        margin-top: 1;
        margin-right: 2;
    }}
    ResponseStatus Label {{
        width: auto;
        color: {_Theme.WARNING};
    }}
    ResponseStatus LoadingIndicator {{
        width: auto;
        color: {_Theme.ACCENT};
        height: 1;
        margin-top: 1;
        dock: right;
    }}
    ResponseStatus.-awaiting-response LoadingIndicator {{
        color: {_Theme.ACCENT};
    }}
    ResponseStatus.-agent-responding LoadingIndicator {{
        color: {_Theme.WARNING};
    }}

    /* ── Chatbox (elia 原版样式) ── */
    Chatbox {{
        height: auto;
        width: 1fr;
        max-width: 1fr;
        margin: 0 1;
        padding: 0 2;
    }}
    Chatbox.assistant-message {{
        border: round {_Theme.ACCENT};
    }}
    Chatbox.assistant-message.response-in-progress {{
        background: {_Theme.ACCENT} 3%;
    }}
    Chatbox.human-message {{
        border: round {_Theme.BORDER};
    }}

    /* ── ThinkingBox：深度思考专用 widget（独立显示，灰色斜体） ── */
    ThinkingBox {{
        height: auto;
        width: 1fr;
        max-width: 1fr;
        margin: 0 1;
        padding: 0 2;
        border: round {_Theme.TEXT_DIM};
        background: {_Theme.BG_LIGHT};
        color: {_Theme.TEXT_DIM};
    }}
    ThinkingBox > .thinking-title {{
        color: {_Theme.TEXT_MUTED};
        text-style: bold italic;
        padding: 0 0 1 0;
    }}
    ThinkingBox > .thinking-body {{
        color: {_Theme.TEXT_DIM};
        text-style: italic;
    }}

    /* ── 引擎切换浮层 ── */
    EngineSwitchBanner {{
        layer: overlay;
        dock: top;
        height: 7;
        width: auto;
        min-width: 44;
        max-width: 72;
        content-align: center middle;
        text-align: center;
        background: {_Theme.BG_LIGHT} 96%;
        color: {_Theme.ACCENT};
        text-style: bold;
        border: round {_Theme.ACCENT} 80%;
        border-title-color: {_Theme.ACCENT};
        border-title-background: {_Theme.BG_LIGHT};
        border-title-style: bold;
        padding: 1 6;
        margin: 2 0;
        offset: 0 -8;
        opacity: 0;
        transition: offset 380ms out_cubic, opacity 380ms out_cubic;
    }}
    EngineSwitchBanner.show {{
        offset: 0 0;
        opacity: 1;
    }}
    EngineSwitchBanner.hide {{
        offset: 0 -8;
        opacity: 0;
        transition: offset 280ms in_cubic, opacity 280ms in_cubic;
    }}
    """

    # ═══════════════════════════════════════════════════
    #  桥接 TUI ↔ AICLI
    # ═══════════════════════════════════════════════════

    class _TUIBridge:
        """桥接 TUI ↔ AICLI"""
        def __init__(self, cli):
            self.cli = cli
        def engines(self) -> list:
            return list(self.cli.engines.keys())
        def current_engine(self) -> str:
            return self.cli.get_current_engine_name()
        def tools(self) -> list:
            return self.cli.liugin_manager.tools
        def history(self) -> list:
            return self.cli.shared_conversation_history
        def switch_engine(self, name: str) -> bool:
            if name in self.cli.engines:
                self.cli.switch_engine(name)
                return True
            return False

    # ═══════════════════════════════════════════════════
    #  Chatbox — 直接复制自 elia，适配为无 litellm 依赖
    #  原项目: https://github.com/darrenburns/elia/blob/main/elia_chat/widgets/chatbox.py
    # ═══════════════════════════════════════════════════

    class Chatbox(Widget, can_focus=True):
        """支持 Markdown 渲染的聊天消息组件 — 流式追加

        render() 返回 Rich Markdown 对象，实现真正的代码高亮和格式化。
        append_chunk() 用于流式追加文本，只刷新布局不重建 widget。
        """

        def __init__(
            self,
            role: str = "assistant",
            content: str = "",
            name: str | None = None,
            id: str | None = None,
            classes: str | None = None,
            disabled: bool = False,
        ) -> None:
            super().__init__(name=name, id=id, classes=classes, disabled=disabled)
            self.role = role
            self.content = content

        def on_mount(self) -> None:
            if self.role == "assistant":
                self.add_class("assistant-message")
                self.border_title = "小狸"
            else:
                self.add_class("human-message")
                self.border_title = "你"

        def render(self) -> RenderableType:
            if not self.content:
                return ""
            if self.role == "user":
                return Syntax(
                    self.content,
                    lexer="markdown",
                    word_wrap=True,
                    background_color=_Theme.BG,
                )
            return Markdown(self.content, code_theme="monokai")

        def append_chunk(self, chunk: str) -> None:
            """流式追加文本 — 来自 elia 的原版实现"""
            self.content += chunk
            self.refresh(layout=True)

    # ═══════════════════════════════════════════════════
    #  ThinkingBox — 深度思考专用 widget（独立于 AI 回答框）
    # ═══════════════════════════════════════════════════

    class ThinkingBox(Widget, can_focus=False):
        """深度思考专用 widget — 灰色斜体，独立显示在 AI 回答框之前

        用于显示深度思考模型（如 DeepSeek-R1、QwQ）的推理过程，
        与最终回答在视觉上分开。
        """

        def __init__(
            self,
            content: str = "",
            name: str | None = None,
            id: str | None = None,
            classes: str | None = None,
        ) -> None:
            super().__init__(name=name, id=id, classes=classes)
            self.content = content

        def render(self) -> RenderableType:
            if not self.content:
                return ""
            return Markdown(
                f"💭 **深度思考**\n\n{self.content}",
                code_theme="monokai",
            )

        def append_chunk(self, chunk: str) -> None:
            """流式追加思考内容"""
            self.content += chunk
            self.refresh(layout=True)

    # ═══════════════════════════════════════════════════
    #  ResponseStatus — 直接复制自 elia
    #  原项目: https://github.com/darrenburns/elia/blob/main/elia_chat/widgets/agent_is_typing.py
    # ═══════════════════════════════════════════════════

    class ResponseStatus(Vertical):
        """响应状态指示器 — 使用 Textual 内置 LoadingIndicator

        两种状态:
        - awaiting-response: 等待 AI 响应（思考中）
        - agent-responding: AI 正在输出（流式中）
        """
        message: reactive[str] = reactive(" 思考中", recompose=False)

        def compose(self) -> ComposeResult:
            yield Label(f" {self.message}", id="rs-label")
            yield LoadingIndicator()

        def watch_message(self, new_value: str) -> None:
            try:
                self.query_one("#rs-label").update(f" {new_value}")
            except NoMatches:
                pass

        def set_awaiting_response(self) -> None:
            self.message = " 思考中"
            self.add_class("-awaiting-response")
            self.remove_class("-agent-responding")
            self.display = True

        def set_agent_responding(self) -> None:
            self.message = " 输出中"
            self.add_class("-agent-responding")
            self.remove_class("-awaiting-response")

        def hide(self) -> None:
            self.display = False

    # ═══════════════════════════════════════════════════
    #  辅助组件
    # ═══════════════════════════════════════════════════

    class EngineSwitchBanner(Static):
        """引擎切换浮层 — 居中悬浮卡片，多行带色彩层次"""
        DEFAULT_CSS = ""

        def __init__(self, old_engine: str, new_engine: str, **kwargs):
            from rich.text import Text
            # 三行布局：标题行 + 切换行 + 状态行，用 Rich Text 上色
            title = Text("⚡ 引擎切换", style=f"bold {self._acc()}", justify="center")
            arrow = Text("  →  ", style="dim")
            old_t = Text(old_engine, style="dim strike")
            new_t = Text(new_engine, style=f"bold {self._acc()}")
            switch_line = Text.assemble(old_t, arrow, new_t)
            hint = Text("切换中…", style="dim italic", justify="center")
            content = Text.assemble(title, "\n", switch_line, "\n", hint)
            super().__init__(content, **kwargs)

        @staticmethod
        def _acc():
            return "#58a6ff"

    class SendTextArea(TextArea):
        """回车发送消息，Ctrl+J 换行的输入框"""
        async def _on_key(self, event):
            # 命令提示导航：上下键 / Tab（提示可见时）
            hint_visible = False
            try:
                hint = self.app.query_one("#command-hint")
                hint_visible = hint.display and bool(hint._items)
                if hint_visible:
                    if event.key == "up":
                        event.prevent_default()
                        hint.move_selection(-1)
                        return
                    elif event.key == "down":
                        event.prevent_default()
                        hint.move_selection(1)
                        return
                    elif event.key == "tab":
                        event.prevent_default()
                        cmd = hint.get_selected_command()
                        if cmd:
                            self.text = cmd + " "
                            self.cursor_location = (0, len(self.text))
                        return
                    elif event.key == "escape":
                        event.prevent_default()
                        self.app._hide_command_hint()
                        return
            except Exception:
                pass

            # 输入历史导航：上下键（提示不可见时）
            if not hint_visible and event.key in ("up", "down"):
                history = getattr(self.app, '_input_history', [])
                if history:
                    event.prevent_default()
                    idx = getattr(self.app, '_history_idx', -1)
                    if event.key == "up":
                        if idx == -1:
                            idx = len(history) - 1
                        else:
                            idx = max(0, idx - 1)
                        self.text = history[idx]
                    else:  # down
                        if idx == -1:
                            return  # 已在最新，无操作
                        idx += 1
                        if idx >= len(history):
                            idx = -1
                            self.text = ""
                        else:
                            self.text = history[idx]
                    self.app._history_idx = idx
                    self.cursor_location = (0, len(self.text))
                    return

            # 换行：Shift+回车 / Ctrl+J / Alt+回车
            # （多数 Windows 终端不区分 Shift+Enter 与 Enter，故提供 Ctrl+J 作为可靠替代）
            if event.key in ("shift+enter", "alt+enter", "ctrl+j"):
                event.prevent_default()
                event.stop()
                self.insert("\n")
                self.app.call_after_refresh(self.app._update_command_hint, self.text)
                self.app._history_idx = -1
                return

            # 回车（无修饰键）：发送消息
            if event.key in ("enter", "\r", "\n"):
                event.prevent_default()
                try:
                    self.app.action_send_message()
                except Exception:
                    pass
                return
            # 其他按键交由父类处理后，刷新命令提示
            await super()._on_key(event)
            self.app.call_after_refresh(self.app._update_command_hint, self.text)
            # 任意编辑键重置历史浏览位置
            self.app._history_idx = -1

    class CommandHint(Widget, can_focus=False):
        """命令提示浮层 — 输入 / 时显示可用命令"""

        BUILTIN_COMMANDS = [
            ("help",    "帮助信息"),
            ("quit",    "退出程序"),
            ("cli",     "切换到 CLI 模式"),
            ("model",   "切换 AI 引擎"),
            ("engine",  "切换 AI 引擎"),
            ("engines", "列出可用引擎"),
            ("tools",   "列出已加载工具"),
            ("status",  "系统状态"),
            ("clear",   "清屏"),
            ("safe",    "切换安全模式"),
            ("diff",    "切换文件修改展示模式"),
            ("chat",    "对话历史管理 (save/list/open)"),
            ("settings","打开辅助中心"),
            ("profile", "引擎配置档案管理 (save/use/del)"),
            ("about",   "关于"),
        ]

        def __init__(self):
            super().__init__(id="command-hint")
            self._items = []
            self._selected = 0

        def update_hints(self, text: str):
            """根据输入文本更新提示列表"""
            if not text.startswith('/'):
                self._items = []
                self.display = False
                self.refresh()
                return

            query = text[1:].split(maxsplit=1)[0].lower() if len(text) > 1 else ""

            items = []
            # 内置命令
            for cmd, desc in self.BUILTIN_COMMANDS:
                if not query or cmd.startswith(query):
                    items.append((cmd, desc))
            # 插件命令
            cli = self.app.cli if hasattr(self.app, 'cli') else None
            if cli and hasattr(cli, 'liugin_commands'):
                for cmd_name in cli.liugin_commands:
                    if not query or cmd_name.startswith(query):
                        items.append((cmd_name, "插件命令"))

            # 去重
            seen = set()
            unique = []
            for cmd, desc in items:
                if cmd not in seen:
                    seen.add(cmd)
                    unique.append((cmd, desc))

            self._items = unique[:10]
            self._selected = 0
            self.display = len(self._items) > 0
            self.refresh()

        def move_selection(self, delta: int):
            if not self._items:
                return
            self._selected = (self._selected + delta) % len(self._items)
            self.refresh()

        def get_selected_command(self) -> str:
            if not self._items:
                return ""
            return "/" + self._items[self._selected][0]

        def render(self) -> RenderableType:
            if not self._items:
                return ""
            lines = []
            for i, (cmd, desc) in enumerate(self._items):
                marker = "▸ " if i == self._selected else "  "
                lines.append(f"{marker}[cmd-hint-cmd]/{cmd}[/]  [cmd-hint-desc]{desc}[/]")
            return "\n".join(lines)

    # ═══════════════════════════════════════════════════
    #  中文化命令面板 (CommandPalette)
    # ═══════════════════════════════════════════════════

    class _CNCommandPalette(CommandPalette):
        """中文化命令面板 — 覆盖占位符、绑定描述与"未找到匹配项"文本"""

        # 覆盖绑定描述为中文（Footer 与帮助面板会显示）
        BINDINGS = [
            Binding("ctrl+end, shift+end", "command_list('last')", "跳到底部", show=False),
            Binding("ctrl+home, shift+home", "command_list('first')", "跳到顶部", show=False),
            Binding("down", "cursor_down", "下一条命令", show=False),
            Binding("escape", "escape", "退出命令面板"),
            Binding("pagedown", "command_list('page_down')", "下一页", show=False),
            Binding("pageup", "command_list('page_up')", "上一页", show=False),
            Binding("up", "command_list('cursor_up')", "上一条命令", show=False),
        ]

        def __init__(self, **kwargs) -> None:
            kwargs.setdefault("placeholder", "搜索命令…")
            super().__init__(**kwargs)

        def _start_no_matches_countdown(self, search_value: str) -> None:
            """覆盖父类方法，将 "No matches found" 替换为中文"""
            self._stop_no_matches_countdown()

            def _show_no_matches() -> None:
                if search_value:
                    command_list = self.query_one(CommandList)
                    command_list.add_option(
                        Option(
                            Align.center(Text("未找到匹配项", style="not bold")),
                            disabled=True,
                            id=self._NO_MATCHES,
                        )
                    )
                    self._list_visible = True
                else:
                    self._list_visible = False

            self._no_matches_timer = self.set_timer(
                self._NO_MATCHES_COUNTDOWN,
                _show_no_matches,
            )

    # ═══════════════════════════════════════════════════
    #  TUI 主应用
    # ═══════════════════════════════════════════════════

    class XiaoliTUI(App):
        """小狸 TUI — 基于 elia 架构"""
        CSS = _TUI_CSS
        TITLE = " 小狸 Pro-CLI"
        SUB_TITLE = "智能编程助手"

        BINDINGS = [
            Binding("ctrl+c", "quit", "退出", show=True),
            Binding("ctrl+l", "clear", "清屏", show=True),
            Binding("ctrl+n", "new_chat", "新对话", show=True),
            Binding("ctrl+enter", "send_message", "发送", show=False),
            Binding("f1", "toggle_sidebar", "侧栏", show=True),
            Binding("f2", "switch_engine", "引擎", show=True),
            Binding("ctrl+p", "toggle_settings", "辅助中心", show=True),
            Binding("f9", "toggle_settings", "辅助中心", show=False),
            Binding("question_mark", "toggle_help", "帮助", show=True),
            Binding("escape", "cancel", "取消", show=True),
        ]

        sidebar_visible = var(False)
        is_generating = var(False)
        # 背景效果：0=墨黑 1=深蓝灰 2=深紫 3=深蓝
        _BG_CLASSES = ["", "bg-grid", "bg-stars", "bg-glow"]
        _BG_LABELS = ["墨黑", "深蓝灰", "深紫", "深蓝"]

        def __init__(self, cli):
            super().__init__()
            self.cli = cli
            self.bridge = _TUIBridge(cli)
            self._thinking_widget = None
            self._cancel_requested = False  # 取消标志
            self._current_worker = None     # 当前 worker 引用
            self._confirm_event = None      # 安全审查确认 Event
            self._confirm_result = False    # 安全审查确认结果
            self._bg_idx = 0                # 预设背景效果索引
            self._bg_image_path = ""        # 自定义背景图片路径
            self._bg_custom_color = ""      # 从图片提取的背景色（hex）
            self._input_history = []        # 输入历史（最新在末尾）
            self._history_idx = -1          # -1 表示当前未在浏览历史

        # ── 命令面板中文化 ──

        def action_command_palette(self) -> None:
            """覆盖默认命令面板，使用中文版"""
            if self.use_command_palette and not CommandPalette.is_open(self):
                self.push_screen(_CNCommandPalette(id="--command-palette"))

        def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
            """覆盖系统命令为中文"""
            if not self.ansi_color:
                yield SystemCommand(
                    "主题",
                    "切换当前主题",
                    self.action_change_theme,
                )
            yield SystemCommand(
                "退出",
                "退出应用程序",
                self.action_quit,
            )
            if screen.query("HelpPanel"):
                yield SystemCommand(
                    "快捷键",
                    "隐藏快捷键帮助面板",
                    self.action_hide_help_panel,
                )
            else:
                yield SystemCommand(
                    "快捷键",
                    "显示快捷键与命令帮助",
                    self.action_show_help_panel,
                )
            if screen.maximized is not None:
                yield SystemCommand(
                    "最小化",
                    "最小化当前控件并恢复原始尺寸",
                    screen.action_minimize,
                )
            elif screen.focused is not None and screen.focused.allow_maximize:
                yield SystemCommand(
                    "最大化",
                    "最大化当前控件",
                    screen.action_maximize,
                )
            yield SystemCommand(
                "截图",
                "保存当前屏幕的 SVG 截图",
                lambda: self.set_timer(0.1, self.deliver_screenshot),
            )

        def search_themes(self) -> None:
            """覆盖主题搜索面板，使用中文占位符"""
            from textual.theme import ThemeProvider
            self.push_screen(
                _CNCommandPalette(
                    providers=[ThemeProvider],
                    placeholder="搜索主题…",
                ),
            )

        def action_show_help_panel(self) -> None:
            """打开帮助浮层（覆盖 Textual 默认侧边栏 HelpPanel）"""
            self._show_help_panel()

        def action_hide_help_panel(self) -> None:
            """关闭帮助浮层"""
            self._hide_help_panel()

        # ── 布局 ──

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Vertical(id="app-container"):
                yield ResponseStatus(id="response-status")
                yield VerticalScroll(id="chat-scroll")
                yield Static("", id="confirm-overlay")
                yield Static("", id="settings-backdrop")
                yield Static("", id="settings-overlay")
                yield Static("", id="help-backdrop")
                yield Static("", id="help-overlay")
                with Vertical(id="input-area"):
                    yield CommandHint()
                    with Container(id="input-wrapper"):
                        yield SendTextArea(
                            placeholder="  输入消息... (回车发送, Ctrl+J 换行, / 命令提示)",
                            id="user-input",
                            soft_wrap=True,
                            tab_behavior="indent",
                        )
                    yield Static(
                        "  回车发送  Ctrl+J 换行  Esc 取消  F2 引擎  F1 侧栏  Ctrl+P 辅助中心  Ctrl+C 退出",
                        id="input-hint"
                    )
                with Vertical(id="sidebar"):
                    yield Static("  引擎", classes="sidebar-header")
                    yield Vertical(id="engine-list", classes="sidebar-section")
                    yield Rule(line_style="heavy")
                    yield Static(" 工具", classes="sidebar-header")
                    yield Vertical(id="tool-list", classes="sidebar-section")
                    yield Rule(line_style="heavy")
                    yield Static(" 状态", classes="sidebar-header")
                    yield Vertical(id="status-info", classes="sidebar-section")
            yield Static(" 就绪", id="status-bar")
            yield Footer()

        def on_mount(self):
            self._render_welcome()
            self.query_one("#user-input").focus()
            def _show_hint():
                try:
                    self.query_one("#input-hint").add_class("visible")
                except Exception:
                    pass
            self.set_timer(0.5, _show_hint)
            # 应用持久化的背景效果
            try:
                from .config import get_system_config
                saved = get_system_config('tui_background', 0)
                self._bg_idx = saved if 0 <= saved < len(self._BG_CLASSES) else 0
                # 自定义图片背景
                self._bg_image_path = get_system_config('tui_bg_image', '') or ''
                if self._bg_image_path:
                    self._extract_color_from_image()
            except Exception:
                self._bg_idx = 0
            self._apply_background()
            self._update_status("就绪")

        def on_key(self, event):
            """全局按键处理：辅助中心 / 帮助浮层 / 安全审查确认浮层可见时拦截按键"""
            try:
                # 辅助中心可见时，拦截所有按键
                settings = self.query_one("#settings-overlay")
                if settings.display and settings.has_class("visible"):
                    key = event.key.lower() if hasattr(event, 'key') else ""
                    if key == "escape":
                        event.prevent_default()
                        event.stop()
                        self._hide_settings()
                    elif key in ("1", "2", "3", "4", "5", "6"):
                        event.prevent_default()
                        event.stop()
                        self._cycle_setting(int(key))
                    else:
                        # 其他按键也拦截，避免触发输入框等
                        event.prevent_default()
                        event.stop()
                    return
            except Exception:
                pass
            try:
                # 帮助浮层可见时，仅 Esc 关闭，其余按键拦截
                help_overlay = self.query_one("#help-overlay")
                if help_overlay.display and help_overlay.has_class("visible"):
                    key = event.key.lower() if hasattr(event, 'key') else ""
                    if key == "escape":
                        event.prevent_default()
                        event.stop()
                        self._hide_help_panel()
                    else:
                        event.prevent_default()
                        event.stop()
                    return
            except Exception:
                pass
            try:
                overlay = self.query_one("#confirm-overlay")
                if overlay.display and self._confirm_event:
                    key = event.key.lower() if hasattr(event, 'key') else ""
                    if key == 'y':
                        event.prevent_default()
                        event.stop()
                        self._confirm_result = True
                        self._confirm_event.set()
                        self._hide_confirm()
                    elif key in ('n', 'escape'):
                        event.prevent_default()
                        event.stop()
                        self._confirm_result = False
                        self._confirm_event.set()
                        self._hide_confirm()
            except Exception:
                pass

        # ── 欢迎界面 ──

        def _render_welcome(self):
            scroll = self.query_one("#chat-scroll")
            engine = self.bridge.current_engine()
            tools = len(self.bridge.tools())
            lines = [
                ("", "msg-dim"),
                ("  -----------------------------------------------", "msg-welcome"),
                ("    小狸 Pro-CLI v6.1.0", "msg-welcome"),
                ("    智能编程助手 · TUI 模式", "msg-welcome"),
                ("  -----------------------------------------------", "msg-welcome"),
                ("", "msg-dim"),
                (f"  引擎: {engine}  |  工具: {tools} 个", "msg-system"),
                ("", "msg-dim"),
                ("  /help 查看命令  /model 切换引擎  /clear 清屏", "msg-dim"),
                ("", "msg-dim"),
            ]
            for text, cls in lines:
                scroll.mount(Static(text, classes=cls))
            scroll.scroll_end(animate=False)

        # ── 消息操作 ──

        def _append(self, widget):
            scroll = self.query_one("#chat-scroll")
            scroll.mount(widget)
            scroll.scroll_end(animate=False)

        def _smart_scroll_end(self):
            """线程安全的智能滚动 — 在主线程中执行"""
            try:
                scroll = self.query_one("#chat-scroll")
                if scroll.scroll_y >= scroll.max_scroll_y - 5:
                    scroll.scroll_end(animate=False)
            except Exception:
                pass

        def _mount_first_chunk(self, widget):
            """挂载首个流式 chunk 的 widget（主线程中执行，保证原子性）"""
            self._remove_thinking()
            self._append(widget)
            try:
                self.query_one("#response-status").set_agent_responding()
            except Exception:
                pass
            self._update_status(" 输出中...")

        def _mount_thinking_widget(self, widget):
            """挂载 ThinkingBox — 在聊天区追加（主线程中执行）"""
            try:
                scroll = self.query_one("#chat-scroll")
                scroll.mount(widget)
                scroll.scroll_end(animate=False)
            except Exception:
                pass

        def _remove_thinking_widget(self, widget):
            """移除空的 ThinkingBox"""
            try:
                if widget and widget.is_mounted:
                    widget.remove()
            except Exception:
                pass

        def _add(self, text, cls="msg-dim"):
            self._append(Static(text, classes=cls))

        def _user_msg(self, text):
            """用户消息 — 使用 Chatbox (elia 模式)，CSS + on_mount 自动处理滑入动画"""
            widget = Chatbox(role="user", content=text)
            self._append(widget)

        def _ai_msg(self, text):
            """AI 消息 — 使用 Chatbox 渲染 Markdown"""
            self._append(Chatbox(role="assistant", content=text))

        def _system(self, text):
            self._add(f"  {text}", "msg-system")

        def _error(self, text):
            self._add(f"  [错误] {text}", "msg-error")

        # ── 思考指示器 (elia ResponseStatus 模式) ──

        def _show_thinking(self):
            """显示思考状态 — 仅右上角 ResponseStatus 浮层

            不再往 chat-scroll 里 mount LoadingIndicator，
            因为无 CSS 约束的 LoadingIndicator 会撑满整个聊天区（视觉上全屏）。
            右上角 ResponseStatus（2 行高小浮层）+ 状态栏文字已足够。
            """
            if self._thinking_widget:
                try:
                    self._thinking_widget.remove()
                except Exception:
                    pass
                self._thinking_widget = None
            try:
                rs = self.query_one("#response-status")
                rs.set_awaiting_response()
            except Exception:
                pass

        def _remove_thinking(self):
            """移除思考状态"""
            try:
                self.query_one("#response-status").hide()
            except Exception:
                pass
            if self._thinking_widget:
                try:
                    self._thinking_widget.remove()
                except Exception:
                    pass
                self._thinking_widget = None

        def _show_typing_indicator(self):
            """兼容旧接口"""
            pass

        def _remove_typing_indicator(self):
            """兼容旧接口"""
            pass

        # ── 侧栏 ──

        def _update_sidebar(self):
            engine_container = self.query_one("#engine-list")
            engine_container.remove_children()
            current = self.bridge.current_engine()
            for name in self.bridge.engines():
                if name == current:
                    engine_container.mount(Static(f"  > {name}", classes="engine-item-active"))
                else:
                    engine_container.mount(Static(f"    {name}", classes="engine-item"))

            tool_container = self.query_one("#tool-list")
            tool_container.remove_children()
            for tool in self.bridge.tools():
                name = tool.get('name', '?')
                tool_container.mount(Static(f"  - {name}", classes="tool-item"))

            status_container = self.query_one("#status-info")
            status_container.remove_children()
            status_container.mount(Static(f"  对话: {len(self.bridge.history())} 条", classes="tool-item"))
            status_container.mount(Static(f"  工具: {len(self.bridge.tools())} 个", classes="tool-item"))
            status_container.mount(Static(f"  引擎: {len(self.bridge.engines())} 个", classes="tool-item"))

        def _update_status(self, text: str):
            try:
                self.query_one("#status-bar").update(f" {text}")
            except Exception:
                pass

        # ── 输入动作 ──

        def _update_command_hint(self, text: str):
            """更新命令提示浮层（输入 / 时触发）"""
            try:
                hint = self.query_one("#command-hint")
                hint.update_hints(text)
            except Exception:
                pass

        def _hide_command_hint(self):
            """隐藏命令提示浮层"""
            try:
                hint = self.query_one("#command-hint")
                hint.display = False
                hint._items = []
                hint.refresh()
            except Exception:
                pass

        def _show_confirm(self, risk_info: str):
            """显示工具调用安全审查确认浮层"""
            try:
                overlay = self.query_one("#confirm-overlay")
                overlay.update(risk_info)
                overlay.add_class("visible")
                overlay.display = True
            except Exception:
                pass

        def _hide_confirm(self):
            """隐藏确认浮层"""
            try:
                overlay = self.query_one("#confirm-overlay")
                overlay.remove_class("visible")
                overlay.display = False
                overlay.update("")
            except Exception:
                pass

        def action_send_message(self):
            """回车发送消息"""
            if self.is_generating:
                return

            text_area = self.query_one("#user-input")
            text = text_area.text.strip()
            if not text:
                return

            # 记录到输入历史（去重：与最后一条相同则不记）
            if not self._input_history or self._input_history[-1] != text:
                self._input_history.append(text)
                if len(self._input_history) > 100:
                    self._input_history.pop(0)
            self._history_idx = -1

            text_area.clear()
            self._hide_command_hint()

            if text.startswith('/'):
                self._handle_command(text)
                return

            self._user_msg(text)
            self.is_generating = True
            self._cancel_requested = False  # 重置取消标志
            self._cancel_generation = getattr(self, '_cancel_generation', 0) + 1  # 新 worker 代次
            self._current_worker = self.run_worker(partial(self._generate, text), thread=True, exclusive=True)

        # ── 命令处理 ──

        def _handle_command(self, cmd):
            parts = cmd[1:].split(maxsplit=1)
            name = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

            cmds = {
                'help': lambda: self._show_help_panel(),
                'quit': lambda: self.exit(),
                'q': lambda: self.exit(),
                'exit': lambda: self.exit(),
                'cli': lambda: self._switch_cli(),
                'clear': lambda: self.action_clear(),
                'cls': lambda: self.action_clear(),
                'model': lambda: self._switch_model(args),
                'engine': lambda: self._switch_model(args),
                'about': lambda: self._system(" 小狸 Pro-CLI v6.1.0 - 智能编程助手"),
                'status': lambda: self._show_status(),
                'tools': lambda: self._show_tools(),
                'engines': lambda: self._show_engines(),
                'tui': lambda: self._system("已在 TUI 模式中"),
                'manual': lambda: self._handle_manual(args),
                'safe': lambda: self._handle_safe(args),
                'diff': lambda: self._handle_diff_mode(args),
                'chat': lambda: self._handle_chat(args),
                'bg': lambda: self._handle_background(args),
                'settings': lambda: self._show_settings(),
                'profile': lambda: self._handle_profile(args),
            }

            handler = cmds.get(name)
            if handler:
                handler()
            else:
                if name in self.cli.liugin_commands:
                    try:
                        result = self.cli.liugin_commands[name](args)
                        if result:
                            self._system(result[:500])
                    except Exception as e:
                        self._error(f"插件命令失败: {e}")
                else:
                    self._error(f"未知命令: /{name}，输入 /help 查看帮助")

        def _handle_safe(self, args):
            """切换安全模式：off=无限制(跳过审查) / on=普通 / manual=人工确认"""
            from xcli_core.safety import get_safety, MODE_UNRESTRICTED, MODE_NORMAL, MODE_MANUAL
            safety = get_safety()
            arg = args.strip().lower() if args else ""
            if arg in ('off', 'unrestricted', '无限制'):
                safety.set_mode(MODE_UNRESTRICTED)
                self._system("  安全模式: 无限制 (跳过工具审查)")
            elif arg in ('on', 'normal', '普通'):
                safety.set_mode(MODE_NORMAL)
                self._system("  安全模式: 普通 (AI 识别风险)")
            elif arg in ('manual', '人工', 'all'):
                safety.set_mode(MODE_MANUAL)
                self._system("  安全模式: 人工确认 (所有工具调用需确认)")
            else:
                mode_name = safety.cycle_mode()
                self._system(f"  安全模式: {mode_name}")

        def _handle_diff_mode(self, args):
            """切换文件修改展示模式：popup=弹窗 / inline=终端内 / off=关闭"""
            arg = args.strip().lower() if args else ""
            # 找到 code_editor 插件
            editor = None
            if hasattr(self.cli, 'liugin_manager'):
                for tool in self.cli.liugin_manager.tools:
                    if tool.get('name') == 'code_editor':
                        editor = tool.get('instance')
                        break
            if not editor:
                self._error("未找到代码编辑器插件")
                return

            if arg in ('popup', '弹窗'):
                editor.diff_popup_enabled = True
                editor.diff_popup_mode = True
                self._system("  文件修改展示: 弹窗模式（新终端窗口）")
            elif arg in ('inline', '内联', '终端', 'ssh'):
                editor.diff_popup_enabled = True
                editor.diff_popup_mode = False
                self._system("  文件修改展示: 终端内显示（SSH 兼容）")
            elif arg in ('off', '关', '关闭'):
                editor.diff_popup_enabled = False
                self._system("  文件修改展示: 已关闭")
            else:
                # 无参数：循环切换
                if not editor.diff_popup_enabled:
                    editor.diff_popup_enabled = True
                    editor.diff_popup_mode = False
                    self._system("  文件修改展示: 终端内显示")
                elif editor.diff_popup_mode is False:
                    editor.diff_popup_mode = True
                    self._system("  文件修改展示: 弹窗模式")
                elif editor.diff_popup_mode is True:
                    editor.diff_popup_enabled = False
                    self._system("  文件修改展示: 已关闭")
                else:
                    editor.diff_popup_mode = False
                    self._system("  文件修改展示: 终端内显示")

        def _handle_chat(self, args):
            """对话历史管理: save <名称> / list / open <名称|序号>"""
            if not getattr(self.cli, 'memory_manager', None):
                self._error("记忆系统未初始化")
                return

            parts = args.strip().split(maxsplit=1)
            sub = parts[0].lower() if parts else ""
            arg = parts[1].strip() if len(parts) > 1 else ""

            if sub == 'save':
                if not arg:
                    self._error("请提供名称。用法: /chat save <名称>")
                    return
                self.cli.memory_manager.auto_save_chat(
                    self.cli.shared_conversation_history,
                    label=arg
                )
                self._system(f"  聊天记录已保存: {arg}")

            elif sub == 'list':
                chats = self.cli.memory_manager.list_chats(limit=30)
                if not chats:
                    self._system("  没有已保存的聊天记录")
                    return
                lines = ["  已保存的聊天记录:"]
                for i, c in enumerate(chats, 1):
                    lines.append(f"  {i}. {c['name']} ({c['time']}, {c['size_kb']}KB)")
                self._system("\n".join(lines))

            elif sub == 'open':
                if not arg:
                    self._error("请提供名称或序号。用法: /chat open <名称|序号>")
                    return
                name = arg
                # 支持序号加载
                if name.isdigit():
                    chats = self.cli.memory_manager.list_chats(limit=50)
                    idx = int(name) - 1
                    if 0 <= idx < len(chats):
                        name = chats[idx]['name'].replace('.json', '')
                    else:
                        self._error(f"序号 {arg} 超出范围")
                        return
                conversation = self.cli.memory_manager.load_chat(name)
                if conversation is None and not name.endswith('.json'):
                    conversation = self.cli.memory_manager.load_chat(name + '.json')
                if conversation is None:
                    self._error(f"聊天记录 '{name}' 不存在")
                    return

                # 替换历史并同步给引擎
                self.cli.shared_conversation_history = conversation
                self.cli._set_shared_conversation_history()

                # 重绘聊天区
                scroll = self.query_one("#chat-scroll")
                scroll.remove_children()
                for msg in conversation:
                    role = msg.get('role', '')
                    content = msg.get('content', '')
                    if not content:
                        continue
                    if role == 'user':
                        self._user_msg(content)
                    elif role == 'assistant':
                        self._ai_msg(content)
                    # system/tool 消息跳过，避免噪音
                self._system(f"  已加载聊天记录: {name}（{len(conversation)} 条）")

            else:
                self._error("用法: /chat save <名称> | /chat list | /chat open <名称|序号>")

        # ── 辅助中心浮层 / 引擎配置档案 ──

        def _mask_key(self, key):
            """脱敏 API Key 用于显示"""
            if not key:
                return "(空)"
            if len(key) <= 8:
                return key[:2] + "***"
            return key[:4] + "***" + key[-4:]

        def _get_setting_state(self):
            """收集辅助中心所有选项的状态，返回 dict 供显示和切换使用"""
            from .safety import get_safety, MODE_UNRESTRICTED, MODE_NORMAL, MODE_MANUAL
            from .notification import get_notification_manager
            from .config import get_system_config

            # 安全模式
            safety = get_safety()
            safety_modes = [(MODE_UNRESTRICTED, "无限制"), (MODE_NORMAL, "普通"), (MODE_MANUAL, "人工确认")]
            safety_idx = safety.mode if 0 <= safety.mode <= 2 else 1
            safety_label = safety_modes[safety_idx][1]

            # 通知开关
            nm = get_notification_manager()
            notify_label = "开启" if nm.enabled else "关闭"

            # diff 模式
            diff_editor = None
            if hasattr(self.cli, 'liugin_manager'):
                for tool in self.cli.liugin_manager.tools:
                    if tool.get('name') == 'code_editor':
                        diff_editor = tool.get('instance')
                        break
            diff_modes = [("off", "关闭"), ("inline", "终端内"), ("popup", "弹窗")]
            diff_idx = 0
            if diff_editor:
                if not diff_editor.diff_popup_enabled:
                    diff_idx = 0
                elif diff_editor.diff_popup_mode is False:
                    diff_idx = 1
                else:
                    diff_idx = 2
            diff_label = diff_modes[diff_idx][1]
            diff_available = diff_editor is not None

            # max_history（从 config 读取真实值，未配置则用默认 50）
            max_history_val = get_system_config('max_history', 50)
            # 历史档位
            history_options = [20, 50, 100, 999999]
            try:
                history_idx = history_options.index(max_history_val) if max_history_val in history_options else 1
            except (ValueError, TypeError):
                history_idx = 1
            history_label = "无限制" if max_history_val >= 999999 else str(max_history_val)

            return {
                'safety': {'idx': safety_idx, 'label': safety_label, 'options': safety_modes, 'available': True},
                'notify': {'idx': 0 if nm.enabled else 1, 'label': notify_label,
                           'options': [(True, "开启"), (False, "关闭")], 'available': True},
                'diff': {'idx': diff_idx, 'label': diff_label, 'options': diff_modes, 'available': diff_available},
                'history': {'idx': history_idx, 'label': history_label,
                            'options': [(v, "无限制" if v >= 999999 else str(v)) for v in history_options],
                            'available': True, 'values': history_options},
                'background': {'idx': self._bg_idx, 'label': self._BG_LABELS[self._bg_idx],
                               'options': list(enumerate(self._BG_LABELS)), 'available': True},
                'bg_custom': {
                    'active': bool(self._bg_custom_color),
                    'label': (os.path.basename(self._bg_image_path) if self._bg_image_path else "无"),
                    'color': self._bg_custom_color,
                },
            }

        def _build_settings_text(self):
            """构建辅助中心浮层的显示内容 — 全部功能 + 基础设置"""
            from rich.text import Text
            from .config import get_profiles, get_system_config

            engine = self.bridge.current_engine()
            engine_name = getattr(engine, 'name', 'unknown')
            base_url = getattr(engine, 'base_url', '')
            api_key = getattr(engine, 'api_key', '')
            model = getattr(engine, 'model', '')

            state = self._get_setting_state()

            t = Text()
            t.append(Text("⚙  辅助中心\n", style=f"bold {_Theme.ACCENT}", justify="center"))
            t.append(Text("─" * 56 + "\n", style="dim"))

            # ── 基础设置 ──
            t.append(Text("【基础设置】\n", style=f"bold {_Theme.TEXT_MUTED}"))

            # 1. 安全模式
            s = state['safety']
            t.append(Text("  ", style=""))
            t.append(Text("[1]", style=f"bold {_Theme.WARNING}"))
            t.append(Text(" 安全模式      ", style=_Theme.TEXT))
            t.append(Text(s['label'], style=f"bold {_Theme.SUCCESS}"))
            if s['available']:
                t.append(Text("  (无限制/普通/人工)", style="dim"))
            t.append(Text("\n", style=""))

            # 2. 通知开关
            n = state['notify']
            t.append(Text("  ", style=""))
            t.append(Text("[2]", style=f"bold {_Theme.WARNING}"))
            t.append(Text(" 任务完成通知  ", style=_Theme.TEXT))
            t.append(Text(n['label'], style=f"bold {_Theme.SUCCESS}"))
            t.append(Text("  (开启/关闭)", style="dim"))
            t.append(Text("\n", style=""))

            # 3. 对话历史条数
            h = state['history']
            t.append(Text("  ", style=""))
            t.append(Text("[3]", style=f"bold {_Theme.WARNING}"))
            t.append(Text(" 对话历史条数  ", style=_Theme.TEXT))
            t.append(Text(h['label'], style=f"bold {_Theme.SUCCESS}"))
            t.append(Text("  (20/50/100/无限)", style="dim"))
            t.append(Text("\n", style=""))

            # 4. diff 展示
            d = state['diff']
            t.append(Text("  ", style=""))
            t.append(Text("[4]", style=f"bold {_Theme.WARNING}"))
            t.append(Text(" 文件修改展示  ", style=_Theme.TEXT))
            if d['available']:
                t.append(Text(d['label'], style=f"bold {_Theme.SUCCESS}"))
                t.append(Text("  (关闭/终端内/弹窗)", style="dim"))
            else:
                t.append(Text("(不可用)", style="dim"))
            t.append(Text("\n", style=""))

            # 5. 预设背景
            bg = state['background']
            t.append(Text("  ", style=""))
            t.append(Text("[5]", style=f"bold {_Theme.WARNING}"))
            t.append(Text(" 预设背景      ", style=_Theme.TEXT))
            t.append(Text(bg['label'], style=f"bold {_Theme.SUCCESS}"))
            t.append(Text("  (墨黑/深蓝灰/深紫/深蓝)", style="dim"))
            t.append(Text("\n", style=""))

            # 6. 自定义背景
            bc = state['bg_custom']
            t.append(Text("  ", style=""))
            t.append(Text("[6]", style=f"bold {_Theme.WARNING}"))
            t.append(Text(" 自定义背景    ", style=_Theme.TEXT))
            if bc['active']:
                t.append(Text(bc['label'], style=f"bold {_Theme.SUCCESS}"))
                t.append(Text(f"  ({bc['color']})", style="dim"))
            else:
                t.append(Text("无", style="dim"))
            t.append(Text("  用 /bg 命令设置", style="dim"))
            t.append(Text("\n", style=""))

            t.append(Text("\n【引擎配置】\n", style=f"bold {_Theme.TEXT_MUTED}"))
            t.append(Text(f"  当前引擎: ", style="dim"))
            t.append(Text(f"{engine_name}\n", style=f"bold {_Theme.ACCENT}"))
            t.append(Text(f"  地址: ", style="dim"))
            t.append(Text(f"{base_url or '(未设置)'}\n", style=_Theme.TEXT))
            t.append(Text(f"  模型: ", style="dim"))
            t.append(Text(f"{model or '(未设置)'}\n", style=_Theme.TEXT))
            t.append(Text(f"  密钥: ", style="dim"))
            t.append(Text(f"{self._mask_key(api_key)}\n", style=_Theme.TEXT))

            # 已存档案
            profiles = get_profiles(engine_name)
            if profiles:
                t.append(Text("\n  配置档案 (用 /profile use <名称|序号> 切换):\n", style=f"bold {_Theme.TEXT_MUTED}"))
                for i, p in enumerate(profiles, 1):
                    mark = " ←" if (p.get('base_url') == base_url and p.get('model') == model) else ""
                    t.append(Text(f"    {i}. {p.get('name', '未命名')}{mark}", style=_Theme.TEXT))
                    t.append(Text(f"  ({p.get('model', '')})\n", style="dim"))

            # 操作提示
            t.append(Text("\n" + "─" * 56 + "\n", style="dim"))
            t.append(Text("  数字键 ", style="dim"))
            t.append(Text("1-6", style=f"bold {_Theme.WARNING}"))
            t.append(Text(" 切换选项  |  ", style="dim"))
            t.append(Text("Esc", style=f"bold {_Theme.WARNING}"))
            t.append(Text(" 关闭\n", style="dim"))
            return t

        def action_toggle_settings(self):
            """Ctrl+P: 切换辅助中心显示/隐藏"""
            overlay = self.query_one("#settings-overlay")
            if overlay.has_class("visible"):
                self._hide_settings()
            else:
                self._show_settings()

        def _show_settings(self):
            """显示辅助中心：先显示背景遮罩，再滑入卡片"""
            backdrop = self.query_one("#settings-backdrop")
            overlay = self.query_one("#settings-overlay")
            overlay.update(self._build_settings_text())
            backdrop.styles.display = "block"
            overlay.styles.display = "block"
            backdrop.remove_class("hiding")
            overlay.remove_class("hiding")

            def _show():
                backdrop.add_class("visible")
                overlay.add_class("visible")

            self.call_after_refresh(_show)

        def _hide_settings(self):
            """隐藏辅助中心：先滑出卡片，再淡出遮罩"""
            backdrop = self.query_one("#settings-backdrop")
            overlay = self.query_one("#settings-overlay")
            overlay.remove_class("visible")
            overlay.add_class("hiding")
            backdrop.remove_class("visible")
            backdrop.add_class("hiding")

            def _finish_hide():
                overlay.remove_class("hiding")
                overlay.styles.display = "none"
                backdrop.remove_class("hiding")
                backdrop.styles.display = "none"

            self.set_timer(0.26, _finish_hide)

        # ── 帮助浮层 ──

        def action_toggle_help(self):
            """?: 切换帮助浮层显示/隐藏"""
            overlay = self.query_one("#help-overlay")
            if overlay.has_class("visible"):
                self._hide_help_panel()
            else:
                self._show_help_panel()

        def _show_help_panel(self):
            """显示帮助浮层：先显示背景遮罩，再滑入卡片"""
            backdrop = self.query_one("#help-backdrop")
            overlay = self.query_one("#help-overlay")
            overlay.update(self._build_help_text())
            backdrop.styles.display = "block"
            overlay.styles.display = "block"
            backdrop.remove_class("hiding")
            overlay.remove_class("hiding")

            def _show():
                backdrop.add_class("visible")
                overlay.add_class("visible")

            self.call_after_refresh(_show)

        def _hide_help_panel(self):
            """隐藏帮助浮层：先滑出卡片，再淡出遮罩"""
            backdrop = self.query_one("#help-backdrop")
            overlay = self.query_one("#help-overlay")
            overlay.remove_class("visible")
            overlay.add_class("hiding")
            backdrop.remove_class("visible")
            backdrop.add_class("hiding")

            def _finish_hide():
                overlay.remove_class("hiding")
                overlay.styles.display = "none"
                backdrop.remove_class("hiding")
                backdrop.styles.display = "none"

            self.set_timer(0.26, _finish_hide)

        def _build_help_text(self):
            """构建帮助浮层内容 — 全中文，含命令、快捷键、操作说明"""
            from rich.text import Text
            t = Text()
            t.append(Text("📖  帮助\n", style=f"bold {_Theme.ACCENT}", justify="center"))
            t.append(Text("─" * 56 + "\n", style="dim"))

            # ── 快捷键 ──
            t.append(Text("【快捷键】\n", style=f"bold {_Theme.TEXT_MUTED}"))
            t.append(Text("  Ctrl+C     退出        Ctrl+L     清屏\n", style=_Theme.TEXT))
            t.append(Text("  Ctrl+N     新对话      Ctrl+P     辅助中心\n", style=_Theme.TEXT))
            t.append(Text("  回车       发送消息    Ctrl+J    换行\n", style=_Theme.TEXT))
            t.append(Text("  F1         侧栏        F2         切换引擎\n", style=_Theme.TEXT))
            t.append(Text("  F9         辅助中心    Esc        取消/关闭浮层\n", style=_Theme.TEXT))
            t.append(Text("  ?          帮助        Tab        缩进\n", style=_Theme.TEXT))

            # ── 命令 ──
            t.append(Text("\n【命令】（在输入框输入 / 触发）\n", style=f"bold {_Theme.TEXT_MUTED}"))
            t.append(Text("  /help          帮助信息\n", style=_Theme.TEXT))
            t.append(Text("  /quit          退出\n", style=_Theme.TEXT))
            t.append(Text("  /cli           切换命令行模式\n", style=_Theme.TEXT))
            t.append(Text("  /model <引擎>  切换 AI 引擎\n", style=_Theme.TEXT))
            t.append(Text("  /engines       列出引擎\n", style=_Theme.TEXT))
            t.append(Text("  /tools         列出工具\n", style=_Theme.TEXT))
            t.append(Text("  /status        系统状态\n", style=_Theme.TEXT))
            t.append(Text("  /clear         清屏\n", style=_Theme.TEXT))

            # ── 安全与展示 ──
            t.append(Text("\n【安全与展示】\n", style=f"bold {_Theme.TEXT_MUTED}"))
            t.append(Text("  /safe [off|on|manual]      切换安全模式\n", style=_Theme.TEXT))
            t.append(Text("  /diff [popup|inline|off]   切换文件修改展示模式\n", style=_Theme.TEXT))
            t.append(Text("  /bg <图片路径|off|list>    自定义背景（提取主色调）\n", style=_Theme.TEXT))

            # ── 对话历史 ──
            t.append(Text("\n【对话历史】\n", style=f"bold {_Theme.TEXT_MUTED}"))
            t.append(Text("  /chat save <名称>     保存当前对话\n", style=_Theme.TEXT))
            t.append(Text("  /chat list            列出已保存对话\n", style=_Theme.TEXT))
            t.append(Text("  /chat open <名称|序号> 加载历史对话\n", style=_Theme.TEXT))

            # ── 引擎配置 ──
            t.append(Text("\n【引擎配置】\n", style=f"bold {_Theme.TEXT_MUTED}"))
            t.append(Text("  /settings             打开辅助中心\n", style=_Theme.TEXT))
            t.append(Text("  /profile save <名称>  保存当前 地址/密钥/模型 为档案\n", style=_Theme.TEXT))
            t.append(Text("  /profile use <名称|序号> 切换到指定配置档案\n", style=_Theme.TEXT))
            t.append(Text("  /profile del <名称>   删除配置档案\n", style=_Theme.TEXT))

            # ── 操作提示 ──
            t.append(Text("\n" + "─" * 56 + "\n", style="dim"))
            t.append(Text("  按 ", style="dim"))
            t.append(Text("Esc", style=f"bold {_Theme.WARNING}"))
            t.append(Text(" 关闭\n", style="dim"))
            return t

        def _cycle_setting(self, idx):
            """数字键切换辅助中心选项"""
            from .safety import get_safety, MODE_UNRESTRICTED, MODE_NORMAL, MODE_MANUAL
            from .notification import get_notification_manager
            from .config import set_system_config

            state = self._get_setting_state()

            if idx == 1:
                # 安全模式循环
                safety = get_safety()
                new_idx = (state['safety']['idx'] + 1) % 3
                mode_map = [MODE_UNRESTRICTED, MODE_NORMAL, MODE_MANUAL]
                safety.set_mode(mode_map[new_idx])
                label = state['safety']['options'][new_idx][1]
                self._update_status(f"安全模式: {label}")
            elif idx == 2:
                # 通知开关循环
                nm = get_notification_manager()
                nm.enabled = not nm.enabled
                self._update_status(f"通知: {'开启' if nm.enabled else '关闭'}")
            elif idx == 3:
                # 对话历史条数循环
                new_idx = (state['history']['idx'] + 1) % 4
                new_val = state['history']['values'][new_idx]
                set_system_config('max_history', new_val)
                # 同步到 cli 实例和所有引擎
                self.cli.max_history = new_val
                if hasattr(self.cli, '_set_shared_conversation_history'):
                    self.cli._set_shared_conversation_history()
                label = "无限制" if new_val >= 999999 else str(new_val)
                self._update_status(f"历史条数: {label}")
            elif idx == 4:
                # diff 模式循环
                if not state['diff']['available']:
                    self._error("代码编辑器未加载，无法切换文件对比模式")
                    return
                new_idx = (state['diff']['idx'] + 1) % 3
                editor = None
                if hasattr(self.cli, 'liugin_manager'):
                    for tool in self.cli.liugin_manager.tools:
                        if tool.get('name') == 'code_editor':
                            editor = tool.get('instance')
                            break
                if editor is None:
                    return
                if new_idx == 0:  # off
                    editor.diff_popup_enabled = False
                elif new_idx == 1:  # inline
                    editor.diff_popup_enabled = True
                    editor.diff_popup_mode = False
                else:  # popup
                    editor.diff_popup_enabled = True
                    editor.diff_popup_mode = True
                label = state['diff']['options'][new_idx][1]
                self._update_status(f"文件对比: {label}")
            elif idx == 5:
                # 预设背景循环
                self._bg_idx = (state['background']['idx'] + 1) % len(self._BG_CLASSES)
                # 切换预设时清除自定义色（避免自定义覆盖预设）
                self._bg_custom_color = ""
                self._apply_background()
                label = self._BG_LABELS[self._bg_idx]
                self._update_status(f"背景: {label}")
                try:
                    set_system_config('tui_background', self._bg_idx)
                except Exception:
                    pass
            elif idx == 6:
                # 自定义背景切换：有自定义则关闭，无则提示用 /bg 命令
                if self._bg_custom_color:
                    self._bg_image_path = ""
                    self._bg_custom_color = ""
                    try:
                        set_system_config('tui_bg_image', '')
                    except Exception:
                        pass
                    self._apply_background()
                    self._update_status("已清除自定义背景")
                else:
                    self._system("用 /bg <图片路径> 设置自定义背景，/bg off 清除")
            else:
                return

            # 刷新辅助中心卡片内容
            overlay = self.query_one("#settings-overlay")
            if overlay.has_class("visible"):
                overlay.update(self._build_settings_text())

        # ── 背景效果 ──
        def _apply_background(self):
            """根据 _bg_idx / 自定义色 给 #chat-scroll 切换背景
            优先级：自定义图片色 > 预设色调
            """
            try:
                scroll = self.query_one("#chat-scroll")
                # 移除所有预设背景 class
                for cls in self._BG_CLASSES:
                    if cls:
                        scroll.remove_class(cls)
                # 移除自定义背景的内联样式
                try:
                    scroll.styles.background = _Theme.BG
                except Exception:
                    pass
                # 自定义图片色优先
                if self._bg_custom_color:
                    try:
                        scroll.styles.background = self._bg_custom_color
                    except Exception:
                        pass
                else:
                    cur = self._BG_CLASSES[self._bg_idx]
                    if cur:
                        scroll.add_class(cur)
            except Exception:
                pass

        def _extract_color_from_image(self):
            """从 _bg_image_path 提取主色调，暗化后作为背景色
            暗化系数 0.18，避免图片过亮影响文字阅读
            """
            if not self._bg_image_path:
                self._bg_custom_color = ""
                return
            try:
                from .constants import PIL_AVAILABLE
                if not PIL_AVAILABLE:
                    self._bg_custom_color = ""
                    self._error("背景图片需要 Pillow 库")
                    return
                from PIL import Image
                import os
                if not os.path.isfile(self._bg_image_path):
                    self._bg_custom_color = ""
                    self._error(f"背景图片不存在: {self._bg_image_path}")
                    return
                with Image.open(self._bg_image_path) as img:
                    img = img.convert("RGB")
                    # 缩小到 40x40 加速计算
                    img.thumbnail((40, 40))
                    pixels = list(img.getdata())
                    if not pixels:
                        self._bg_custom_color = ""
                        return
                    # 计算平均色
                    r = sum(p[0] for p in pixels) // len(pixels)
                    g = sum(p[1] for p in pixels) // len(pixels)
                    b = sum(p[2] for p in pixels) // len(pixels)
                    # 暗化到 18% 亮度，保证文字可读
                    r = int(r * 0.18)
                    g = int(g * 0.18)
                    b = int(b * 0.18)
                    self._bg_custom_color = f"#{r:02x}{g:02x}{b:02x}"
            except Exception as e:
                self._bg_custom_color = ""
                self._error(f"提取背景色失败: {e}")

        def _handle_background(self, args):
            """/bg 命令：设置自定义图片背景或清除
            用法: /bg <图片路径>   设置背景（提取主色调）
                  /bg off         清除自定义，回到预设
                  /bg list        显示当前背景状态
            """
            from .config import set_system_config
            arg = args.strip()
            if not arg or arg.lower() == "list":
                # 显示状态
                if self._bg_custom_color:
                    name = os.path.basename(self._bg_image_path) if self._bg_image_path else ""
                    self._system(f"当前背景: 自定义 ({name})  颜色: {self._bg_custom_color}")
                else:
                    self._system(f"当前背景: 预设 ({self._BG_LABELS[self._bg_idx]})")
                return
            if arg.lower() == "off":
                self._bg_image_path = ""
                self._bg_custom_color = ""
                try:
                    set_system_config('tui_bg_image', '')
                except Exception:
                    pass
                self._apply_background()
                self._update_status("背景: 已清除自定义")
                # 刷新辅助中心
                try:
                    overlay = self.query_one("#settings-overlay")
                    if overlay.has_class("visible"):
                        overlay.update(self._build_settings_text())
                except Exception:
                    pass
                return
            # 设置图片路径
            path = arg.strip().strip('"').strip("'")
            # 展开 ~ 和环境变量
            path = os.path.expanduser(os.path.expandvars(path))
            if not os.path.isfile(path):
                self._error(f"图片文件不存在: {path}")
                return
            self._bg_image_path = path
            self._extract_color_from_image()
            if self._bg_custom_color:
                self._apply_background()
                try:
                    set_system_config('tui_bg_image', path)
                except Exception:
                    pass
                name = os.path.basename(path)
                self._update_status(f"背景: {name}")
                self._system(f"已设置背景: {name}  颜色: {self._bg_custom_color}")
            # 刷新辅助中心
            try:
                overlay = self.query_one("#settings-overlay")
                if overlay.has_class("visible"):
                    overlay.update(self._build_settings_text())
            except Exception:
                pass

        def _handle_profile(self, args):
            """引擎配置档案管理: save/use/del/list"""
            from .config import get_profiles, save_profile, delete_profile

            parts = args.strip().split(maxsplit=1)
            sub = parts[0].lower() if parts else ""
            arg = parts[1].strip() if len(parts) > 1 else ""

            engine = self.bridge.current_engine()
            engine_name = getattr(engine, 'name', 'unknown')

            if sub in ('', 'list'):
                # 显示辅助中心浮层（等同于 /settings）
                self._show_settings()
                return

            if sub == 'save':
                if not arg:
                    self._error("请提供档案名称。用法: /profile save <名称>")
                    return
                profile = {
                    "name": arg,
                    "base_url": getattr(engine, 'base_url', ''),
                    "api_key": getattr(engine, 'api_key', ''),
                    "model": getattr(engine, 'model', ''),
                }
                save_profile(engine_name, profile)
                self._system(f"  已保存配置档案: {arg}（引擎: {engine_name}）")
                # 如果辅助中心浮层可见则刷新
                overlay = self.query_one("#settings-overlay")
                if overlay.has_class("visible"):
                    overlay.update(self._build_settings_text())

            elif sub == 'use':
                if not arg:
                    self._error("请提供档案名称或序号。用法: /profile use <名称|序号>")
                    return
                profiles = get_profiles(engine_name)
                if not profiles:
                    self._error(f"引擎 {engine_name} 没有已保存的配置档案")
                    return
                target = None
                if arg.isdigit():
                    idx = int(arg) - 1
                    if 0 <= idx < len(profiles):
                        target = profiles[idx]
                    else:
                        self._error(f"序号 {arg} 超出范围（共 {len(profiles)} 个档案）")
                        return
                else:
                    for p in profiles:
                        if p.get('name') == arg:
                            target = p
                            break
                    if not target:
                        self._error(f"未找到档案: {arg}")
                        return

                # 应用配置到引擎实例
                if hasattr(engine, 'apply_config'):
                    engine.apply_config(
                        base_url=target.get('base_url'),
                        api_key=target.get('api_key'),
                        model=target.get('model'),
                    )
                    self._system(f"  已切换到配置档案: {target.get('name')}（{engine_name}）")
                    self._update_status(f"引擎: {engine_name} | {target.get('model', '')}")
                    self._update_sidebar()
                    # 刷新辅助中心浮层
                    overlay = self.query_one("#settings-overlay")
                    if overlay.has_class("visible"):
                        overlay.update(self._build_settings_text())
                else:
                    self._error(f"引擎 {engine_name} 不支持配置切换")

            elif sub in ('del', 'delete'):
                if not arg:
                    self._error("请提供档案名称。用法: /profile del <名称>")
                    return
                profiles = get_profiles(engine_name)
                exists = any(p.get('name') == arg for p in profiles)
                if not exists:
                    self._error(f"未找到档案: {arg}")
                    return
                delete_profile(engine_name, arg)
                self._system(f"  已删除配置档案: {arg}")
                overlay = self.query_one("#settings-overlay")
                if overlay.has_class("visible"):
                    overlay.update(self._build_settings_text())

            else:
                self._error("用法: /profile save <名称> | use <名称|序号> | del <名称> | list")

        def _handle_manual(self, args):
            if 'manual' not in self.cli.engines:
                self._error("手动引擎未加载")
                return
            if not args:
                if self.bridge.switch_engine('manual'):
                    self._system("已切换到手动引擎")
                    self._update_sidebar()
                else:
                    self._error("切换失败")
            else:
                result = self.cli.engines['manual'].handle_command(args)
                if result:
                    self._system(result)

        def _switch_cli(self):
            self._system("切换到命令行模式...")
            self.cli.tui_output_callback = None
            self.cli._cli_requested = True
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
                marker = ">" if name == current else " "
                lines.append(f"  {marker} {name}")
            self._system('\n'.join(lines))

        def _show_tools(self):
            tools = self.bridge.tools()
            lines = [f"  可用工具 ({len(tools)} 个):"]
            for t in tools:
                name = t.get('name', '?')
                desc = t.get('description', '')[:40]
                lines.append(f"  - {name}: {desc}")
            self._system('\n'.join(lines))

        def _show_status(self):
            status_lines = [
                f"  系统状态:",
                f"  引擎: {self.bridge.current_engine()}",
                f"  引擎数: {len(self.bridge.engines())}",
                f"  工具数: {len(self.bridge.tools())}",
                f"  对话数: {len(self.bridge.history())}",
            ]
            self._system('\n'.join(status_lines))

        # ── AI 生成 (elia @work + call_from_thread 模式) ──

        def _generate(self, user_input):
            """流式生成 — 基于 elia 的 stream_agent_response 模式

            在线程中运行同步的 cli_core，
            通过 call_from_thread() 线程安全地更新 UI。
            """
            _stream_state = {
                "widget": None,
                "thinking_widget": None,
                "text": "",
                "thinking_text": "",
                "thinking_removed": False,
                "first_chunk": True,
            }

            def tui_output(msg):
                # 引擎切换等操作可能在主线程调用，需做线程判断
                import threading as _t
                if self._thread_id == _t.get_ident():
                    self._write_raw(msg)
                else:
                    self.call_from_thread(self._write_raw, msg)

            original_cb = self.cli.tui_output_callback
            self.cli.tui_output_callback = tui_output

            def tui_stream(chunk, kind="content"):
                """流式回调 — kind: 'content' | 'thinking'"""
                if self._cancel_requested:
                    return
                if kind == "thinking":
                    _stream_state["thinking_text"] += chunk
                    if _stream_state["thinking_widget"] is None:
                        tw = ThinkingBox(content="")
                        _stream_state["thinking_widget"] = tw
                        self.call_from_thread(self._mount_thinking_widget, tw)
                    self.call_from_thread(
                        _stream_state["thinking_widget"].append_chunk, chunk
                    )
                    self.call_from_thread(self._smart_scroll_end)
                    return
                # kind == "content"
                if _stream_state["first_chunk"]:
                    _stream_state["first_chunk"] = False
                    _stream_state["thinking_removed"] = True
                    widget = Chatbox(
                        role="assistant",
                        content=chunk,
                        classes="response-in-progress",
                    )
                    _stream_state["widget"] = widget
                    _stream_state["text"] = chunk
                    self.call_from_thread(self._mount_first_chunk, widget)
                    return

                _stream_state["text"] += chunk
                widget = _stream_state["widget"]
                if widget:
                    self.call_from_thread(widget.append_chunk, chunk)
                    self.call_from_thread(self._smart_scroll_end)

            original_stream_cb = getattr(self.cli, 'tui_stream_callback', None)
            self.cli.tui_stream_callback = tui_stream

            # 新增：思考专用回调（独立于内容流）
            def tui_thinking(chunk):
                tui_stream(chunk, kind="thinking")

            original_thinking_cb = getattr(self.cli, 'tui_thinking_callback', None)
            self.cli.tui_thinking_callback = tui_thinking

            # 每轮 AI 生成前: 重新显示思考指示器 (工具调用后 AI 继续)
            def tui_before_generate():
                _stream_state["thinking_removed"] = False
                _stream_state["text"] = ""
                _stream_state["thinking_text"] = ""
                _stream_state["widget"] = None
                _stream_state["thinking_widget"] = None
                _stream_state["first_chunk"] = True
                self.call_from_thread(self._show_thinking)
                self.call_from_thread(lambda: self._update_status(" 思考中..."))

            original_before_cb = getattr(self.cli, 'tui_before_generate_callback', None)
            self.cli.tui_before_generate_callback = tui_before_generate

            # 工具调用审查确认 — 跨线程 Event 实现
            import threading as _threading
            self._confirm_event = _threading.Event()

            def tui_confirm(risk_info):
                """worker 线程调用：显示风险信息并等待用户确认"""
                self._confirm_event.clear()
                self._confirm_result = False
                self.call_from_thread(self._show_confirm, risk_info)
                self._confirm_event.wait(timeout=120)
                return self._confirm_result

            original_confirm_cb = getattr(self.cli, 'tui_confirm_callback', None)
            self.cli.tui_confirm_callback = tui_confirm

            # 记录当前 worker 的代次，用于 finally 中判断是否已被取消/替换
            my_generation = getattr(self, '_cancel_generation', 0)

            try:
                self.cli.process_conversation(user_input)
            except Exception as e:
                # 被取消时不报错
                if not self._cancel_requested:
                    self.call_from_thread(self._error, str(e))
            finally:
                # 只有当前 worker 未被取消/替换时，才恢复回调和状态
                current_generation = getattr(self, '_cancel_generation', 0)
                if current_generation == my_generation:
                    self.cli.tui_output_callback = original_cb
                    self.cli.tui_stream_callback = original_stream_cb
                    self.cli.tui_thinking_callback = original_thinking_cb
                    self.cli.tui_before_generate_callback = original_before_cb
                    self.cli.tui_confirm_callback = original_confirm_cb
                    # 移除 response-in-progress 样式
                    if _stream_state["widget"]:
                        self.call_from_thread(
                            _stream_state["widget"].remove_class, "response-in-progress"
                        )
                    # 清理空的思考 widget
                    if _stream_state["thinking_widget"] is not None and not _stream_state["thinking_text"]:
                        self.call_from_thread(self._remove_thinking_widget,
                                              _stream_state["thinking_widget"])
                    self.call_from_thread(self._remove_thinking)
                    self.call_from_thread(lambda: self._update_status("就绪"))
                    self.call_from_thread(lambda: setattr(self, 'is_generating', False))
                    self.call_from_thread(self._update_sidebar)

        _RICH_TAG_RE = re.compile(r'\[/?[a-zA-Z][^\[\]]*?\]')

        def _write_raw(self, msg):
            """输出原始消息 — 去掉 Rich 标记"""
            # 使用 rich 自身的标记解析（最准确，保留中文方括号）
            try:
                from rich.text import Text
                clean = Text.from_markup(msg).plain
            except Exception:
                # 降级：手动正则剥离
                prev = None
                clean = msg
                while prev != clean:
                    prev = clean
                    clean = self._RICH_TAG_RE.sub('', clean)
            if 'OK' in clean or ('工具' in clean and ('调用' in clean or '执行' in clean)):
                self._add(f"  {clean}", "msg-tool-ok")
            elif 'ERROR' in clean or '错误' in clean or '安全' in clean or '拒绝' in clean:
                self._add(f"  {clean}", "msg-tool-err")
            else:
                self._add(f"  {clean}", "msg-dim")

        # ── 动作 ──

        def action_clear(self):
            if self.is_generating:
                return
            scroll = self.query_one("#chat-scroll")
            scroll.remove_children()
            self._render_welcome()

        def action_new_chat(self):
            if self.is_generating:
                return
            # 清空前自动保存当前对话（如果有内容且记忆系统可用）
            history = self.cli.shared_conversation_history
            if history and getattr(self.cli, 'memory_manager', None):
                try:
                    # 用第一条用户消息作为标签
                    label = ""
                    for m in history:
                        if m.get('role') == 'user' and m.get('content'):
                            label = m['content'][:30]
                            break
                    self.cli.memory_manager.auto_save_chat(history, label=label or "未命名对话")
                except Exception:
                    pass
            history.clear()
            self.action_clear()
            self._system("已开始新对话（旧对话已自动保存）")

        def action_toggle_sidebar(self):
            sidebar = self.query_one("#sidebar")
            if sidebar.has_class("visible"):
                # 隐藏：先播放滑出动画，结束后再 display:none 释放布局空间
                sidebar.remove_class("visible")
                sidebar.add_class("hiding")
                self.sidebar_visible = False

                def _finish_hide():
                    sidebar.remove_class("hiding")
                    sidebar.styles.display = "none"

                self.set_timer(0.26, _finish_hide)
            else:
                # 显示：先 display:block 占位，下一帧再加 visible 类触发滑入
                sidebar.styles.display = "block"
                self._update_sidebar()

                def _show():
                    sidebar.add_class("visible")

                self.call_after_refresh(_show)
                self.sidebar_visible = True

        def action_switch_engine(self):
            """F2: 引擎切换 — 居中浮层丝滑滑入滑出"""
            engines = self.bridge.engines()
            if len(engines) <= 1:
                self._system("只有一个引擎，无法切换")
                return
            current = self.bridge.current_engine()
            try:
                idx = engines.index(current)
                next_idx = (idx + 1) % len(engines)
                next_engine = engines[next_idx]
            except ValueError:
                next_engine = engines[0]

            # 清理旧 banner
            for old in self.query("EngineSwitchBanner"):
                old.remove()

            # 先挂载并显示 banner，再执行切换（营造过渡感）
            banner = EngineSwitchBanner(current, next_engine)
            self.mount(banner)
            status = self.query_one("#status-bar")

            def _show():
                banner.add_class("show")
                status.add_class("pulse")
                self._update_status(f"切换中: {current} → {next_engine}")

            def _do_switch():
                # banner 显示后再真正切换引擎
                if not self.bridge.switch_engine(next_engine):
                    self._error(f"切换引擎失败: {next_engine}")
                    banner.remove_class("show")
                    banner.add_class("hide")
                    self.set_timer(0.3, lambda: banner.remove())
                    status.remove_class("pulse")
                    self._update_status("就绪")
                    return
                self._update_status(f"已切换: {next_engine}")

            def _hide():
                banner.remove_class("show")
                banner.add_class("hide")

            def _cleanup():
                banner.remove()
                status.remove_class("pulse")
                self._update_status("就绪")
                self._update_sidebar()

            self.call_after_refresh(_show)
            self.set_timer(0.25, _do_switch)  # banner 滑入快完成时执行切换
            self.set_timer(1.4, _hide)         # 显示 1.15s 后开始滑出
            self.set_timer(1.75, _cleanup)     # 滑出完成后清理

        def action_cancel(self):
            if not self.is_generating:
                return
            self._cancel_requested = True
            self._system("正在取消...")
            # 通知引擎中断（设置 _cancelled 标志，流式循环会检查并退出）
            engine = getattr(self.cli, 'current_engine', None)
            if engine and hasattr(engine, 'cancel'):
                try:
                    engine.cancel()
                except Exception:
                    pass
            # 释放确认等待（如果在工具审查确认期间取消）
            if self._confirm_event:
                self._confirm_event.set()
            # 隐藏确认浮层
            self._hide_confirm()
            # 取消 worker（标记取消，线程会在下次检查点退出）
            if self._current_worker:
                try:
                    self._current_worker.cancel()
                except Exception:
                    pass
                self._current_worker = None
            # 生成唯一 ID 标记本次取消，防止旧 worker finally 覆盖新 worker 状态
            self._cancel_generation = getattr(self, '_cancel_generation', 0) + 1
            # UI 收尾
            self._finish_cancel()

        def _finish_cancel(self):
            """主线程中完成取消的 UI 收尾"""
            self._remove_thinking()
            self._update_status("已取消")
            self.is_generating = False
            self._update_sidebar()

else:
    class XiaoliTUI:
        """Textual 未安装时的占位类"""
        def __init__(self, *args, **kwargs):
            pass
        def run(self, *args, **kwargs):
            print("TUI 模式不可用：Textual 库未安装")
            print("请运行: pip install textual rich")
