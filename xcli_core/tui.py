"""TUI 界面模块 - Textual TUI 实现（opencode 高仿版）

布局对齐 opencode：
  ┌──────────────────────────────────────────────────────┐
  │ ◆ 小狸 Pro-CLI   <workspace>          <model> [PLAN] │ 顶栏
  ├────────────┬─────────────────────────────────────────┤
  │ SESSIONS   │  ❯ user                                 │
  │  ▸ s1      │    问题…                                 │
  │    s2      │  ● 小狸                                  │
  │ FILES      │    回答…                                 │
  │  📂 src    │  ⚙ code_editor edit foo.py          ✓  │
  │            ├─────────────────────────────────────────┤
  │            │ ┃ 输入消息…                    NORMAL   │ composer
  │            │   -- INSERT -- │ Esc 切模式 │ …          │ 模式提示
  ├────────────┴─────────────────────────────────────────┤
  │ 就绪 │ openai │ 12条对话 │ ▓▓▓░░ 1.2k/8k             │ 状态栏
  └──────────────────────────────────────────────────────┘

消息流用 role 标记（❯/●/⚙）而非气泡框，代码块保留 Syntax 高亮；
Vim 模态编辑逻辑全部在 vim_keys.py（纯函数可单测），本文件只做按键映射。
"""

from .constants import TEXTUAL_AVAILABLE, VERSION

if TEXTUAL_AVAILABLE:
    import re
    import asyncio
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical, VerticalScroll, Container
    from textual.widgets import Static, TextArea, Input
    from textual.screen import ModalScreen
    from textual.reactive import var
    from textual.binding import Binding
    from textual import on
    from .vim_keys import VimInputState
    import os
    from rich.syntax import Syntax
    from rich.panel import Panel
    from rich.box import ROUNDED

    # ── TUI 主题色（opencode 调性：极简暗色 + 低饱和点缀）──
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
        AI = "#c9d1d9"
        TOOL = "#56d364"
        TOOL_ERR = "#f85149"
        CODE_BG = "#161b22"
        GLOW = "#1f6feb"
        THINKING = "#8b949e"
        WELCOME_ACCENT = "#58a6ff"

    _TUI_CSS = f"""
    Screen {{
        background: {_Theme.BG};
        transition: background 300ms in_out_cubic;
    }}

    #app-container {{
        height: 100%;
        width: 100%;
    }}

    /* ── 左侧栏（opencode 式）── */
    #sidebar {{
        width: 30;
        min-width: 30;
        height: 1fr;
        background: {_Theme.BG_LIGHT};
        border-right: wide {_Theme.BORDER};
        display: block;
        transition: width 300ms in_out_cubic, opacity 300ms in_out_cubic;
        overflow: hidden;
    }}

    #sidebar.hidden {{
        width: 0;
        min-width: 0;
        opacity: 0;
        border: none;
        overflow: hidden;
    }}

    #sidebar-tabs {{
        height: 1;
        width: 100%;
        dock: top;
        background: {_Theme.BG};
        padding: 0;
    }}
    .sidebar-tab {{
        display: block;
        height: 1;
        padding: 0 1;
        color: {_Theme.TEXT_DIM};
        text-style: bold;
    }}
    .sidebar-tab:hover {{
        color: {_Theme.TEXT_MUTED};
    }}
    .sidebar-tab-active {{
        color: {_Theme.ACCENT};
        border-bottom: solid {_Theme.ACCENT};
    }}

    #sidebar-content {{
        height: 1fr;
        padding: 0 1;
    }}
    .panel-section {{
        padding: 1 0 0 0;
        border-bottom: solid {_Theme.BORDER};
    }}
    .panel-section.hidden {{
        display: none;
    }}
    .panel-title {{
        color: {_Theme.TEXT_DIM};
        padding: 0 0 1 0;
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
    .file-tree-item {{
        padding: 0 0 0 1;
        color: {_Theme.TEXT_MUTED};
    }}
    .file-tree-dir {{
        color: {_Theme.ACCENT};
        text-style: bold;
    }}
    .session-item {{
        padding: 0 0 0 1;
        color: {_Theme.TEXT_MUTED};
    }}
    .session-item-active {{
        color: {_Theme.SUCCESS};
        text-style: bold;
    }}
    .plan-badge {{
        color: {_Theme.WARNING};
        text-style: bold;
    }}

    /* ── 命令面板 ── */
    #pal-box {{
        width: 76;
        height: auto;
        max-height: 24;
        background: {_Theme.BG_LIGHT};
        border: tall {_Theme.BORDER_FOCUS};
        padding: 0 1 1 1;
        margin: 2 4;
    }}
    #pal-title {{
        color: {_Theme.TEXT_DIM};
        padding: 0 0 1 0;
    }}
    #pal-input {{
        background: {_Theme.BG};
        border: tall {_Theme.BORDER};
        margin: 0 0 1 0;
    }}
    #pal-list {{
        height: auto;
        max-height: 16;
        scrollbar-color: {_Theme.BORDER};
    }}
    .pal-item {{
        padding: 0 1;
        color: {_Theme.TEXT};
    }}
    .pal-sel {{
        background: {_Theme.GLOW} 45%;
        color: {_Theme.TEXT};
        text-style: bold;
    }}
    .pal-dim {{
        color: {_Theme.TEXT_DIM};
    }}

    /* ── 中间消息流 ── */
    #main {{
        width: 1fr;
        height: 1fr;
    }}

    #chat-scroll {{
        height: 1fr;
        background: {_Theme.BG};
        scrollbar-color: {_Theme.BORDER};
        scrollbar-color-hover: {_Theme.TEXT_MUTED};
        padding: 0 1;
    }}

    /* opencode 式 role 标记消息行 */
    .msg-user {{
        color: {_Theme.USER};
        padding: 1 0 0 1;
        text-style: bold;
    }}

    .msg-ai {{
        color: {_Theme.AI};
        padding: 0 1;
    }}

    .msg-system {{
        color: {_Theme.ACCENT};
        padding: 0 1;
    }}

    .msg-tool-ok {{
        color: {_Theme.TOOL};
        padding: 0 1;
    }}

    .msg-tool-err {{
        color: {_Theme.TOOL_ERR};
        padding: 0 1;
    }}

    .msg-thinking {{
        color: {_Theme.THINKING};
        text-style: italic;
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
        color: {_Theme.WELCOME_ACCENT};
        padding: 0 1;
        text-style: bold;
    }}

    .msg-welcome-line {{
        color: {_Theme.WELCOME_ACCENT};
        padding: 0 1;
        text-style: bold;
        opacity: 0;
        transition: opacity 400ms in_out_cubic;
    }}

    .msg-welcome-line.visible {{
        opacity: 1;
    }}

    .msg-system-line {{
        color: {_Theme.ACCENT};
        padding: 0 1;
        opacity: 0;
        transition: opacity 400ms in_out_cubic;
    }}

    .msg-system-line.visible {{
        opacity: 1;
    }}

    .thinking-indicator {{
        color: {_Theme.THINKING};
        text-style: italic;
        padding: 0 1;
    }}

    .code-block {{
        background: {_Theme.CODE_BG};
        border: wide {_Theme.BORDER};
        padding: 0 1;
        margin: 0 2 0 2;
    }}

    /* ── 底部 composer（opencode 式输入）── */
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
        border: tall {_Theme.BORDER};
        padding: 0;
        transition: border-color 300ms in_out_cubic;
    }}

    #input-wrapper:focus-within {{
        border: tall {_Theme.BORDER_FOCUS};
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

    /* ── 状态栏（opencode 式：左状态右模型）── */
    #status-bar {{
        height: 1;
        width: 100%;
        dock: bottom;
        background: {_Theme.BG_LIGHT};
        color: {_Theme.TEXT_MUTED};
        padding: 0 1;
        transition: color 300ms in_out_cubic;
    }}

    /* ── 顶栏 ── */
    #tui-header {{
        height: 1;
        width: 100%;
        dock: top;
        background: {_Theme.BG_LIGHT};
        color: {_Theme.TEXT_MUTED};
        padding: 0 1;
        border-bottom: solid {_Theme.BORDER};
    }}

    /* ── 精简欢迎 ── */
    .welcome-compact {{
        color: {_Theme.WELCOME_ACCENT};
        padding: 1 2;
        border-bottom: solid {_Theme.BORDER};
        text-style: bold;
    }}
    """

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

        def sessions(self) -> list:
            mgr = getattr(self.cli, 'session_manager', None)
            if mgr and hasattr(mgr, 'list_sessions'):
                try:
                    return mgr.list_sessions()
                except Exception:
                    return []
            return []

        def plan_mode(self) -> bool:
            return bool(getattr(self.cli, 'plan_mode', False))

        def current_plan(self) -> str:
            return getattr(self.cli, 'current_plan', '') or ""

        def cwd(self) -> str:
            return os.getcwd()


    # ═══════════════════════════════════════════════════
    #  动画辅助组件
    # ═══════════════════════════════════════════════════

    class ThinkingSpinner(Static):
        """动态思考指示器 - 旋转 + 脉冲"""
        FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        DOTS_FRAMES = ["   ", ".  ", ".. ", "..."]

        def __init__(self, **kwargs):
            super().__init__("", **kwargs)
            self._frame = 0
            self._dot_frame = 0
            self._running = False

        def on_mount(self):
            self._running = True
            self.set_interval(0.08, self._animate)

        def _animate(self):
            if not self._running:
                return
            spinner = self.FRAMES[self._frame % len(self.FRAMES)]
            dots = self.DOTS_FRAMES[self._dot_frame % len(self.DOTS_FRAMES)]
            self.update(f"  {spinner} 思考中{dots}")
            self._frame += 1
            if self._frame % 3 == 0:
                self._dot_frame += 1

        def stop(self):
            self._running = False


    class AnimatedWelcome(Static):
        """逐行动画显示的欢迎组件"""
        def __init__(self, lines, **kwargs):
            super().__init__("", **kwargs)
            self._lines = lines
            self._current = 0

        def on_mount(self):
            self.set_interval(0.12, self._show_next_line)

        def _show_next_line(self):
            if self._current < len(self._lines):
                current_text = self.renderable
                new_line = self._lines[self._current]
                if self._current == 0:
                    self.update(new_line)
                else:
                    self.update(str(current_text) + "\n" + new_line)
                self._current += 1


    class MessageBubble(Static):
        """带入场动画的消息行"""
        def __init__(self, text, **kwargs):
            super().__init__(text, **kwargs)
            self.styles.opacity = 0

        def on_mount(self):
            # textual >= 8: Widget.opacity 是只读属性，直接 animate 会抛
            # "property 'opacity' has no setter"。改为在 styles 上动画，失败则直接到位。
            try:
                self.styles.animate("opacity", value=1.0, duration=0.3, easing="out_cubic")
            except Exception:
                self.styles.opacity = 1.0


    class TypingIndicator(Static):
        """打字指示器 - 模拟 AI 正在打字"""
        FRAMES = ["●○○", "○●○", "○○●", "○●○"]

        def __init__(self, **kwargs):
            super().__init__("", **kwargs)
            self._frame = 0
            self._running = False

        def on_mount(self):
            self._running = True
            self.set_interval(0.3, self._tick)

        def _tick(self):
            if not self._running:
                return
            dots = self.FRAMES[self._frame % len(self.FRAMES)]
            self.update(f"  {dots} AI 正在输入")
            self._frame += 1

        def stop(self):
            self._running = False


    # ═══════════════════════════════════════════════════
    #  命令面板（opencode command_list 式：ctrl+p 模糊搜命令/工具/引擎/会话）
    # ═══════════════════════════════════════════════════

    def _fuzzy_score(query: str, text: str) -> int:
        """子序列模糊匹配打分：>0 = 命中。前缀命中 > 包含 > 子序列。"""
        if not query:
            return 1
        q, t = query.lower(), text.lower()
        if t.startswith(q):
            return 1000 - len(t)
        idx = t.find(q)
        if idx >= 0:
            return 500 - idx - len(t) // 10
        ti = 0
        for ch in q:
            ti = t.find(ch, ti)
            if ti < 0:
                return 0
            ti += 1
        return 100 - len(t) // 10

    class CommandPalette(ModalScreen):
        """全功能模糊命令面板（opencode ctrl+p）。
        items: [(label, desc, kind, payload)]，回车执行，Esc 关闭。"""
        BINDINGS = [
            Binding("escape", "dismiss", "关闭", show=False),
            Binding("up", "cursor_up", "↑", show=False),
            Binding("down", "cursor_down", "↓", show=False),
            Binding("enter", "select", "执行", show=False),
        ]

        def __init__(self, items, **kwargs):
            super().__init__(**kwargs)
            self._items = items
            self._filtered = list(items)
            self._cursor = 0
            self._closed = False   # 防 enter 双触发（Input.Submitted + binding）导致双重 dismiss

        def compose(self) -> ComposeResult:
            with Container(id="pal-box"):
                yield Static("  命令面板  │  输入模糊搜索  │  ↑↓ 选择  回车执行  Esc 关闭", id="pal-title")
                yield Input(placeholder="搜索命令 / 工具 / 引擎 / 会话…", id="pal-input")
                yield VerticalScroll(id="pal-list")

        def on_mount(self):
            self._render_list()
            self.query_one("#pal-input").focus()

        def _render_list(self):
            lst = self.query_one("#pal-list")
            lst.remove_children()
            if not self._filtered:
                lst.mount(Static("  (无匹配)", classes="pal-item pal-dim"))
                return
            for i, (label, desc, kind, _) in enumerate(self._filtered[:20]):
                cls = "pal-item pal-sel" if i == self._cursor else "pal-item"
                mark = {"cmd": "›", "tool": "⚙", "engine": "◈", "session": "≡"}.get(kind, "·")
                lst.mount(Static(f"  {mark} {label:<18} {desc[:42]}", classes=cls))
            lst.scroll_home(animate=False)

        @on(Input.Changed, "#pal-input")
        def _on_filter(self, event):
            q = event.value.strip()
            scored = []
            for item in self._items:
                s = _fuzzy_score(q, item[0] + " " + item[1])
                if s > 0:
                    scored.append((s, item))
            scored.sort(key=lambda x: -x[0])
            self._filtered = [it for _, it in scored]
            self._cursor = 0
            self._render_list()

        @on(Input.Submitted, "#pal-input")
        def _on_submit(self, event):
            self.action_select()

        def action_cursor_up(self):
            if self._filtered:
                self._cursor = (self._cursor - 1) % min(20, len(self._filtered))
                self._render_list()

        def action_cursor_down(self):
            if self._filtered:
                self._cursor = (self._cursor + 1) % min(20, len(self._filtered))
                self._render_list()

        def action_select(self):
            if self._closed:
                return
            self._closed = True
            if not self._filtered:
                self.dismiss(None)
                return
            pick = self._filtered[min(self._cursor, len(self._filtered) - 1)]
            self.dismiss(pick)

        def action_dismiss(self):
            if self._closed:
                return
            self._closed = True
            self.dismiss(None)

    # ═══════════════════════════════════════════════════
    #  自定义 TextArea：回车发送，Shift+回车换行
    # ═══════════════════════════════════════════════════

    class SendTextArea(TextArea):
        """回车发送消息，Shift+回车换行的输入框"""
        async def _on_key(self, event):
            if event.key in ("enter", "\r", "\n"):
                # prevent_default 阻止父类 TextArea._on_key 执行
                event.prevent_default()
                try:
                    self.app.action_send_message()
                except Exception:
                    pass
                return
            # 斜杠命令补全（opencode prompt.autocomplete.complete = tab）
            if event.key == "tab" and self.text.strip().startswith("/") and "\n" not in self.text:
                event.prevent_default()
                try:
                    self.app.action_complete_slash()
                except Exception:
                    pass
                return
            # 空输入上/下 = 历史翻找（opencode history_previous/next）
            if event.key in ("up", "down") and not self.text.strip():
                event.prevent_default()
                try:
                    self.app.action_history_step(event.key == "up")
                except Exception:
                    pass
                return
            # 其他键正常处理


    # ═══════════════════════════════════════════════════
    #  Vim 风格模态输入框（NORMAL / INSERT）
    # ═══════════════════════════════════════════════════

    class VimSendTextArea(SendTextArea):
        """
        带 Vim 模态编辑的输入框。

        模式：
          INSERT  —— 默认，正常打字；Esc 进入 NORMAL
          NORMAL  —— h/j/k/l 移动，i/a/o 进入插入，dd 删行，x 删字，
                    w/b 跳词，0/$ 行首行尾，gg/G 文首文尾，u 撤销 …

        坐标：VimInputState 用字符偏移 offset，这里负责与 TextArea 的
        (row, col) 光标互相转换。所有 vim 逻辑都在 vim_keys.py（纯函数，
        可单测）；本类只做「按键映射 + 把结果写回 TextArea」。
        """
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.vim_enabled = True
            self.vim = VimInputState(mode="INSERT")

        # ── offset <-> (row, col) ──
        def _cur_off(self) -> int:
            r, c = self.cursor_location
            text = self.text
            lines = text.split("\n")
            return sum(len(l) + 1 for l in lines[:r]) + c

        def _set_off(self, off: int):
            text = self.text
            off = max(0, min(off, len(text)))
            r = text.count("\n", 0, off)
            line_start = text.rfind("\n", 0, off)
            c = off - (line_start + 1)
            self.cursor_location = (r, c)

        # ── key 名字 -> vim token ──
        @staticmethod
        def _vim_token(key: str):
            m = {
                "escape": "escape", "h": "h", "l": "l", "j": "j", "k": "k",
                "w": "w", "b": "b", "e": "e", "0": "0", "$": "$", "^": "^",
                "g": "g", "G": "G", "d": "d", "x": "x", "u": "u",
                "i": "i", "a": "a", "o": "o", "O": "O", "I": "I", "A": "A",
                "left": "left", "right": "right", "up": "up", "down": "down",
                "shift+i": "I", "shift+a": "A", "shift+o": "O",
                "shift+g": "G", "shift+6": "^", "shift+4": "$",
            }
            return m.get(key)

        def _notify_mode(self):
            app = self.app
            if hasattr(app, "_update_vim_mode_display"):
                try:
                    app._update_vim_mode_display()
                except Exception:
                    pass

        def _apply(self, res):
            try:
                if res.text != self.text:
                    self.text = res.text
                self._set_off(res.offset)
                self.vim.mode = res.mode
                self.vim.pending = res.pending
                if res.action == "undo":
                    try:
                        self.undo()
                    except Exception:
                        pass
                self._notify_mode()
            except Exception:
                # 任何意外都不应让输入框崩；退回默认行为
                pass

        async def _on_key(self, event):
            # 回车：INSERT（或 vim 关闭）发送；NORMAL 下移一行
            if event.key in ("enter", "\r", "\n"):
                if self.vim_enabled and self.vim.mode == "NORMAL":
                    event.prevent_default()
                    res = self.vim.feed(self.text, self._cur_off(), "j")
                    self._apply(res)
                else:
                    event.prevent_default()
                    try:
                        self.app.action_send_message()
                    except Exception:
                        pass
                return

            # shift+enter：INSERT/非 vim 只插一个换行（吞掉 App 级 newline 绑定防双换行）；
            # vim NORMAL 模式继续往下当 'o'（下方换行开新行）
            if event.key == "shift+enter" and not (self.vim_enabled and self.vim.mode == "NORMAL"):
                event.prevent_default()
                event.stop()
                try:
                    self.insert("\n")
                except Exception:
                    pass
                return

            if not self.vim_enabled:
                return  # 退化为普通 TextArea

            if self.vim.mode == "INSERT":
                if event.key == "escape":
                    event.prevent_default()
                    res = self.vim.feed(self.text, self._cur_off(), "escape")
                    self._apply(res)
                # 其余键交给 TextArea 默认处理（打字）
                return

            # ── NORMAL 模式 ──
            if event.key == "shift+enter":
                token = "o"
            else:
                token = self._vim_token(event.key)
            if token is None:
                # ctrl+/shift+ 组合键放回去，让 App 级绑定处理（聚焦切换等）
                if event.key.startswith("ctrl+") or event.key.startswith("shift+"):
                    return
                # 普通单键未映射：吞掉，避免 TextArea 在 NORMAL 下误编辑
                event.prevent_default()
                return
            event.prevent_default()
            res = self.vim.feed(self.text, self._cur_off(), token)
            self._apply(res)

    # ═══════════════════════════════════════════════════
    #  TUI 主应用
    # ═══════════════════════════════════════════════════

    class XiaoliTUI(App):
        """小狸 TUI（opencode 高仿版）：左 session 侧栏 + role 标记消息流 + 底部 composer"""
        CSS = _TUI_CSS
        TITLE = " 小狸 Pro-CLI"
        SUB_TITLE = "智能编程助手"

        BINDINGS = [
            Binding("ctrl+c", "quit", "退出", show=True),
            Binding("ctrl+l", "clear", "清屏", show=True),
            Binding("ctrl+n", "new_chat", "新对话", show=True),
            Binding("ctrl+enter", "send_message", "发送", show=False),
            Binding("shift+enter", "newline", "换行", show=False),
            Binding("f1", "toggle_sidebar", "侧栏", show=True),
            Binding("ctrl+p", "command_palette", "面板", show=True),
            Binding("ctrl+o", "toggle_plan", "PLAN", show=True),
            Binding("f2", "cycle_model", "换模型", show=True),
            Binding("f3", "history_search", "历史", show=True),
            Binding("f4", "toggle_tool_fold", "折叠", show=True),
            Binding("1", "tab_engine", "引擎", show=False),
            Binding("2", "tab_files", "文件", show=False),
            Binding("3", "tab_sessions", "会话", show=False),
            Binding("4", "tab_status", "状态", show=False),
            Binding("escape", "cancel", "取消", show=False),
            # ── Vim 风格导航（输入框未聚焦时生效）──
            Binding("j", "chat_down", "↓聊天", show=False),
            Binding("k", "chat_up", "↑聊天", show=False),
            Binding("i", "focus_insert", "插入", show=False),
            Binding("ctrl+f", "chat_page_down", "翻页↓", show=True),
            Binding("ctrl+b", "chat_page_up", "翻页↑", show=True),
            Binding("ctrl+d", "chat_half_down", "半页↓", show=True),
            Binding("ctrl+u", "chat_half_up", "半页↑", show=True),
            Binding("ctrl+space", "toggle_focus", "聚焦切换", show=True),
        ]

        sidebar_visible = var(True)
        is_generating = var(False)
        plan_mode = var(False)
        _sidebar_tab: str = "sessions"  # opencode 默认显示会话列表

        def __init__(self, cli):
            super().__init__()
            self.cli = cli
            self.bridge = _TUIBridge(cli)
            self._thinking_widget = None
            self._typing_widget = None
            self._input_history = []   # 历史输入（f3/上翻）
            self._hist_idx = None
            self._tool_folded = True   # 工具调用折叠开关（f4）
            self._cancel_event = None  # Esc 取消事件（轮间生效）

        def compose(self) -> ComposeResult:
            # ── 顶栏 (opencode: 左品牌 | 中工作区 | 右模型/状态) ──
            yield Static("", id="tui-header")
            with Horizontal(id="app-container"):
                # ── 左侧栏：会话/文件/引擎/状态 ──
                with Vertical(id="sidebar"):
                    with Horizontal(id="sidebar-tabs"):
                        yield Static(" 会话 ", classes="sidebar-tab sidebar-tab-active", id="tab-sessions")
                        yield Static(" 文件 ", classes="sidebar-tab", id="tab-files")
                        yield Static(" 引擎 ", classes="sidebar-tab", id="tab-engine")
                        yield Static(" 状态 ", classes="sidebar-tab", id="tab-status")
                    with VerticalScroll(id="sidebar-content"):
                        yield Vertical(id="panel-sessions", classes="panel-section")
                        yield Vertical(id="panel-files", classes="panel-section")
                        yield Vertical(id="panel-engine", classes="panel-section")
                        yield Vertical(id="panel-status", classes="panel-section")
                # ── 中间：消息流 + composer ──
                with Vertical(id="main"):
                    yield VerticalScroll(id="chat-scroll")
                    with Vertical(id="input-area"):
                        with Container(id="input-wrapper"):
                            yield VimSendTextArea(
                                placeholder="输入消息... (回车发送, Shift+回车换行, Esc 进 Vim 普通模式)",
                                id="user-input",
                                soft_wrap=True,
                                tab_behavior="indent",
                            )
                        yield Static(
                            "  回车发送 | Shift+回车换行 | Ctrl+L 清屏 | F1 侧栏 | Ctrl+P 面板",
                            id="input-hint"
                        )
            yield Static(" 就绪 | Ctrl+C 退出", id="status-bar")

        def on_mount(self):
            # 持久输出桥：cli 任意线程的输出统一进 TUI（替代 stdout，防花屏）
            self.cli.tui_output_callback = self._tui_push
            self._update_header()
            self._switch_sidebar_tab("sessions")
            self._render_welcome_compact()
            self._init_vim_mode()
            self.query_one("#user-input").focus()

            def _show_hint():
                try:
                    self.query_one("#input-hint").add_class("visible")
                except Exception:
                    pass
            self.set_timer(1.5, _show_hint)

        def _init_vim_mode(self):
            try:
                ta = self.query_one("#user-input")
            except Exception:
                return
            cfg = getattr(self.cli, "config", None)
            enabled = True
            if isinstance(cfg, dict) and "vim_mode" in cfg:
                enabled = bool(cfg["vim_mode"])
            ta.vim_enabled = enabled
            self._update_vim_mode_display()

        # ── 欢迎界面 ──

        def _render_welcome_compact(self):
            """opencode 风格: 精简一行欢迎"""
            scroll = self.query_one("#chat-scroll")
            engine = self.bridge.current_engine()
            welcome = Static(
                f"  ◆ 小狸 Pro-CLI v8.0  │  {engine}  │  "
                f"{len(self.bridge.tools())} 工具  │  /help 查看命令",
                classes="welcome-compact"
            )
            scroll.mount(welcome)

        def _render_welcome_animated(self):
            """逐行动画显示欢迎界面"""
            scroll = self.query_one("#chat-scroll")

            welcome_lines = [
                "",
                "  ╔══════════════════════════════════════════════╗",
                "  ║                                              ║",
                "  ║    小狸 Pro-CLI v8.0.4                        ║",
                "  ║    智能编程助手 · opencode 风格               ║",
                "  ║                                              ║",
                "  ╚══════════════════════════════════════════════╝",
                "",
                "   代码编辑 · 代码搜索 · Git 集成 · 多引擎",
                "   输入 /help 查看命令 | /model 切换引擎",
                f"   当前引擎: {self.bridge.current_engine()} | 工具: {len(self.bridge.tools())} 个",
                "   支持多行输入 — Shift+回车换行",
                "",
            ]

            for i, line in enumerate(welcome_lines):
                if "╔" in line or "║" in line or "╚" in line:
                    cls = "msg-welcome-line"
                elif line.strip().startswith("小狸"):
                    cls = "msg-welcome-line"
                elif line.strip().startswith("智能"):
                    cls = "msg-welcome-line"
                elif "代码编辑" in line or "输入 /help" in line or "当前引擎" in line:
                    cls = "msg-system-line"
                elif "多行输入" in line:
                    cls = "msg-system-line"
                else:
                    cls = "msg-dim"

                widget = Static(line, classes=cls)
                scroll.mount(widget)
                delay = max(0.01, i * 0.1)
                self.set_timer(delay, lambda w=widget: w.add_class("visible"))

            self.set_timer(max(0.01, len(welcome_lines) * 0.1 + 0.1),
                          lambda: scroll.scroll_end(animate=True, duration=0.3))

        def _render_welcome(self):
            """静态欢迎界面（用于清屏后快速恢复）"""
            scroll = self.query_one("#chat-scroll")
            lines = [
                ("", "msg-dim"),
                ("  ◆ 小狸 Pro-CLI v8.0.4", "msg-welcome"),
                ("", "msg-dim"),
                ("   代码编辑 · 代码搜索 · Git 集成 · 多引擎", "msg-system"),
                ("   输入 /help 查看命令 | /model 切换引擎", "msg-system"),
                (f"   当前引擎: {self.bridge.current_engine()} | 工具: {len(self.bridge.tools())} 个", "msg-system"),
                ("   支持多行输入 — Shift+回车换行", "msg-system"),
                ("", "msg-dim"),
            ]
            for text, cls in lines:
                scroll.mount(Static(text, classes=cls))

        # ── 侧栏更新 ──

        def _update_sidebar(self):
            """按当前标签页更新侧栏内容"""
            self._update_file_tree()
            self._update_session_list()

            # ── 引擎面板 ──
            engine_panel = self.query_one("#panel-engine")
            engine_panel.remove_children()
            current = self.bridge.current_engine()
            for name in self.bridge.engines():
                if name == current:
                    engine_panel.mount(Static(f"  ▸ {name}", classes="engine-item-active"))
                else:
                    engine_panel.mount(Static(f"    {name}", classes="engine-item"))
            engine_panel.mount(Static("  工具", classes="panel-title"))
            for tool in self.bridge.tools()[:12]:
                name = tool.get('name', '?')
                engine_panel.mount(Static(f"  • {name}", classes="tool-item"))

            # ── 状态面板 ──
            status_panel = self.query_one("#panel-status")
            status_panel.remove_children()
            status_panel.mount(Static(f"  对话: {len(self.bridge.history())} 条", classes="tool-item"))
            status_panel.mount(Static(f"  工具: {len(self.bridge.tools())} 个", classes="tool-item"))
            status_panel.mount(Static(f"  引擎: {len(self.bridge.engines())} 个", classes="tool-item"))
            if self.bridge.plan_mode():
                status_panel.mount(Static("  模式: 📋 PLAN", classes="plan-badge"))
            else:
                status_panel.mount(Static("  模式: 普通", classes="tool-item"))

            self._sync_tab_highlight()

        # ── 文件树 ──

        @staticmethod
        def _build_file_tree(root, max_depth=2, max_items=40):
            """生成 (name, is_dir) 列表，用于侧栏文件树展示。"""
            items = []
            try:
                entries = sorted(os.listdir(root))
            except OSError:
                return items
            dirs = [e for e in entries if os.path.isdir(os.path.join(root, e))]
            files = [e for e in entries if os.path.isfile(os.path.join(root, e))]
            skip = {'.git', '__pycache__', '.tui_snapshots', '.pytest_cache',
                    'node_modules', '.workbuddy', 'chat_history', 'memory',
                    '.idea', '.vscode', '.venv', 'venv'}
            shown = 0
            for name in dirs + files:
                if name in skip or name.startswith('.'):
                    continue
                if shown >= max_items:
                    items.append(("…", False))
                    break
                is_dir = os.path.isdir(os.path.join(root, name))
                items.append((name, is_dir))
                shown += 1
            return items

        def _update_file_tree(self):
            container = self.query_one("#panel-files")
            container.remove_children()
            root = self.bridge.cwd()
            container.mount(Static(f"  📂 {os.path.basename(root)}", classes="file-tree-dir"))
            for name, is_dir in self._build_file_tree(root):
                icon = "📁" if is_dir else "📄"
                container.mount(Static(f"  {icon} {name}", classes="file-tree-item"))

        # ── 会话列表 ──

        @staticmethod
        def _format_rel_time(ts: str) -> str:
            if not ts:
                return ""
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                diff = (datetime.now() - dt).total_seconds()
                if diff < 60:
                    return "刚刚"
                if diff < 3600:
                    return f"{int(diff // 60)}分钟前"
                if diff < 86400:
                    return f"{int(diff // 3600)}小时前"
                return f"{int(diff // 86400)}天前"
            except Exception:
                return ""

        def _update_session_list(self):
            container = self.query_one("#panel-sessions")
            container.remove_children()
            sessions = self.bridge.sessions()[:8]
            if not sessions:
                container.mount(Static("  (无历史会话)", classes="session-item"))
                return
            for i, s in enumerate(sessions, 1):
                title = (s.title or s.id)[:22]
                t = self._format_rel_time(s.updated_at)
                container.mount(Static(f"  {i}. {title}  {t}", classes="session-item"))

        # ── 标签页切换 ──

        def _sync_tab_highlight(self):
            """同步标签高亮状态"""
            tab_map = {"sessions": "tab-sessions", "files": "tab-files",
                       "engine": "tab-engine", "status": "tab-status"}
            for tid in tab_map.values():
                try:
                    w = self.query_one(f"#{tid}")
                    if tid == tab_map.get(self._sidebar_tab, ""):
                        w.add_class("sidebar-tab-active")
                    else:
                        w.remove_class("sidebar-tab-active")
                except Exception:
                    pass

        def _switch_sidebar_tab(self, tab: str):
            """切换侧栏标签页"""
            self._sidebar_tab = tab
            panel_map = {
                "sessions": "panel-sessions", "files": "panel-files",
                "engine": "panel-engine", "status": "panel-status",
            }
            for pt, pid in panel_map.items():
                try:
                    p = self.query_one(f"#{pid}")
                    if pt == tab:
                        p.remove_class("hidden")
                    else:
                        p.add_class("hidden")
                except Exception:
                    pass
            self._sync_tab_highlight()
            self._update_sidebar()

        def action_tab_engine(self):
            if self._guard_chat():
                return
            self._switch_sidebar_tab("engine")

        def action_tab_files(self):
            if self._guard_chat():
                return
            self._switch_sidebar_tab("files")

        def action_tab_sessions(self):
            if self._guard_chat():
                return
            self._switch_sidebar_tab("sessions")

        def action_tab_status(self):
            if self._guard_chat():
                return
            self._switch_sidebar_tab("status")

        def _update_header(self):
            """更新顶栏：品牌 | 工作区 | 模型 [PLAN]"""
            hdr = self.query_one("#tui-header", expect_type=Static)
            engine = self.bridge.current_engine()
            plan_tag = " [PLAN]" if self.bridge.plan_mode() else ""
            workspace = os.path.basename(self.bridge.cwd())
            hdr.update(
                f" ◆ 小狸 v8.0 │ {workspace} │ {engine}{plan_tag}"
            )

        def _update_status(self, text: str):
            bar = self.query_one("#status-bar")
            engine = self.bridge.current_engine()
            prefix = "📋 PLAN | " if self.plan_mode else ""
            bar.update(f" {prefix}{text} | {engine} | {len(self.bridge.history())} 条对话{self._token_str()}")

        def _token_str(self):
            """token 用量进度（token 感知压缩联动，引擎支持时显示）"""
            e = getattr(self.cli, 'current_engine', None)
            if not e:
                return ""
            used = getattr(e, 'last_prompt_tokens', None)
            win = None
            if hasattr(e, 'context_window'):
                try:
                    win = e.context_window()
                except Exception:
                    win = None
            if used and win:
                ratio = min(1.0, used / win)
                filled = int(ratio * 10)
                bar_s = "▓" * filled + "░" * (10 - filled)
                return f" | {used}/{win} {bar_s}"
            if used:
                return f" | {used} tok"
            return ""

        # ── 消息追加（opencode 式 role 标记：❯ 用户 / ● 小狸 / ⚙ 工具）──

        def _append(self, widget):
            scroll = self.query_one("#chat-scroll")
            scroll.mount(widget)
            scroll.scroll_end(animate=True, duration=0.2)

        def _add(self, text, cls="msg-dim"):
            widget = MessageBubble(text, classes=cls)
            self._append(widget)

        def _user_msg(self, text):
            self._add(f"  ❯ {text}", "msg-user")

        def _ai_msg(self, text):
            if "```" in text:
                self._render_with_code(text)
            else:
                self._add(f"  ● {text}", "msg-ai")

        def _render_with_code(self, text):
            parts = re.split(r'```(\w*)\n(.*?)```', text, flags=re.DOTALL)
            i = 0
            while i < len(parts):
                if i % 3 == 0:
                    if parts[i].strip():
                        for line in parts[i].strip().split('\n'):
                            self._add(f"  ● {line}", "msg-ai")
                elif i % 3 == 2:
                    code = parts[i]
                    lang = parts[i-1] if i > 1 else ""
                    try:
                        syntax = Syntax(code, lang or "python", theme="monokai",
                                        line_numbers=True, word_wrap=True)
                        panel = Panel(syntax, border_style=f"dim {_Theme.BORDER}",
                                     box=ROUNDED, padding=(0, 1))
                        widget = MessageBubble(str(panel), classes="code-block")
                        self._append(widget)
                    except Exception:
                        for line in code.split('\n'):
                            self._add(f"    {line}", "msg-dim")
                i += 1

        def _tool_ok(self, name, args):
            if self._tool_folded:
                self._add(f"  ⚙ {name}  ✓", "msg-tool-ok")
            else:
                self._add(f"  ⚙ {name}: {args[:60]}  ✓", "msg-tool-ok")

        def _tool_err(self, name, args):
            if self._tool_folded:
                self._add(f"  ⚙ {name}  ✗", "msg-tool-err")
            else:
                self._add(f"  ⚙ {name}: {args[:60]}  ✗", "msg-tool-err")

        def _show_thinking(self):
            """显示动画思考指示器"""
            self._remove_thinking()
            spinner = ThinkingSpinner(classes="thinking-indicator")
            scroll = self.query_one("#chat-scroll")
            scroll.mount(spinner)
            scroll.scroll_end(animate=True, duration=0.2)
            self._thinking_widget = spinner

        def _remove_thinking(self):
            """移除思考指示器"""
            if self._thinking_widget:
                try:
                    self._thinking_widget.stop()
                    self._thinking_widget.remove()
                except Exception:
                    pass
                self._thinking_widget = None

        def _show_typing_indicator(self):
            """显示打字指示器"""
            self._remove_typing_indicator()
            indicator = TypingIndicator(classes="thinking-indicator")
            scroll = self.query_one("#chat-scroll")
            scroll.mount(indicator)
            scroll.scroll_end(animate=True, duration=0.2)
            self._typing_widget = indicator

        def _remove_typing_indicator(self):
            """移除打字指示器"""
            if self._typing_widget:
                try:
                    self._typing_widget.stop()
                    self._typing_widget.remove()
                except Exception:
                    pass
                self._typing_widget = None

        def _thinking(self):
            """兼容旧接口"""
            self._show_thinking()

        def _system(self, text):
            self._add(f"  ℹ  {text}", "msg-system")

        def _error(self, text):
            self._add(f"    {text}", "msg-error")

        # ── 多行输入处理 ──

        def action_newline(self):
            """Shift+Enter 在输入框插入换行"""
            text_area = self.query_one("#user-input")
            if text_area.has_focus:
                text_area.insert("\n")

        def action_send_message(self):
            """回车发送消息"""
            if self.is_generating:
                self._system("生成中…（Esc 取消当前任务后再发）")
                return
            text_area = self.query_one("#user-input")
            text = text_area.text.strip()
            if not text:
                return

            # 清空输入框 + 记录历史（f3 回溯 / 上下键翻找）
            text_area.clear()
            if not self._input_history or self._input_history[-1] != text:
                self._input_history.append(text)
                if len(self._input_history) > 200:
                    self._input_history = self._input_history[-200:]
            self._hist_idx = None

            if text.startswith('/'):
                self._handle_command(text)
                return

            self._user_msg(text)
            self._show_thinking()
            self.is_generating = True
            self._update_status(" 思考中...")
            self.run_worker(self._generate(text), exclusive=True)

        # ── 输入框高度自适应 ──

        @on(TextArea.Changed, "#user-input")
        def on_textarea_changed(self, event):
            """输入框内容变化：调高度 + 斜杠命令补全提示"""
            text_area = event.text_area
            line_count = text_area.text.count('\n') + 1
            wrapper = self.query_one("#input-wrapper")
            new_height = min(max(line_count + 1, 4), 12)
            wrapper.styles.height = new_height
            self._update_slash_suggest(text_area.text)

        # ── 斜杠命令补全（opencode prompt.autocomplete 式）──

        def _slash_matches(self, text: str):
            """输入以 / 开头时返回匹配命令名列表（模糊，最多 8 个）"""
            q = text.strip().lstrip('/')
            if not text.startswith('/') or ' ' in text.strip():
                return []
            out = []
            for name in self._command_table():
                s = _fuzzy_score(q, name)
                if s > 0:
                    out.append((s, name))
            out.sort(key=lambda x: -x[0])
            return [n for _, n in out[:8]]

        def _update_slash_suggest(self, text: str):
            """把补全候选渲染到输入提示行"""
            try:
                hint = self.query_one("#input-hint")
            except Exception:
                return
            matches = self._slash_matches(text)
            if matches:
                hint.update("  Tab 补全 › " + "  ".join(f"/{m}" for m in matches))
                hint.add_class("visible")
            else:
                self._update_vim_mode_display()

        def action_complete_slash(self):
            """Tab：补全斜杠命令（唯一候选直接补全，多候选补公共前缀）"""
            ta = self._user_input()
            text = ta.text
            matches = self._slash_matches(text)
            if not matches:
                return
            if len(matches) == 1:
                ta.text = f"/{matches[0]} "
            else:
                prefix = os.path.commonprefix(matches)
                if prefix and len(prefix) > len(text.strip().lstrip('/')):
                    ta.text = f"/{prefix}"

        # ── 命令面板 / 模型切换 / 历史 / 工具折叠（opencode 体验三件套）──

        _cmd_docs = {
            'help': '帮助信息', 'quit': '退出', 'q': '退出', 'exit': '退出',
            'cli': '切到命令行模式', 'clear': '清屏', 'cls': '清屏',
            'model': '切换 AI 引擎', 'engine': '切换 AI 引擎', 'about': '关于',
            'status': '系统状态', 'tools': '列出工具', 'engines': '列出引擎',
            'tui': '已在 TUI', 'manual': 'manual 引擎', 'plan': 'PLAN 规划模式',
            'build': '批准 PLAN 执行', 'sessions': '历史会话', 'session': '会话操作',
            'resume': '恢复会话', 'snapshot': '导出截图', 'screenshot': '导出截图',
            'vim': 'Vim 键位开关', 'palette': '打开命令面板',
        }

        def _palette_items(self):
            """汇总面板条目：命令 + 工具 + 引擎 + 会话"""
            items = []
            for name, fn in self._command_table().items():
                doc = self._cmd_docs.get(name, "")
                items.append((f"/{name}", doc or "命令", "cmd", name))
            for t in self.bridge.tools():
                items.append((t.get('name', '?'), (t.get('description', '') or '')[:42], "tool", t.get('name', '')))
            cur = self.bridge.current_engine()
            for name in self.bridge.engines():
                mark = "（当前）" if name == cur else ""
                items.append((name, f"切换引擎{mark}", "engine", name))
            for s in self.bridge.sessions()[:10]:
                title = (s.title or s.id)[:36]
                items.append((title, f"恢复会话 {s.id} · {self._format_rel_time(s.updated_at)}", "session", s.id))
            return items

        def action_command_palette(self):
            """ctrl+p：模糊命令面板（命令/工具/引擎/会话）"""
            def _on_pick(pick):
                if not pick:
                    return
                label, desc, kind, payload = pick
                if kind == "cmd":
                    self._handle_command(f"/{payload}")
                elif kind == "engine":
                    self._switch_model(payload)
                elif kind == "session":
                    self._tui_resume(str(payload))
                elif kind == "tool":
                    self._system(f"  工具 {payload}: 在对话中直接说出需求，AI 会自动调用")
            self.push_screen(CommandPalette(self._palette_items()), _on_pick)

        def action_cycle_model(self):
            """f2：循环切换引擎（opencode model_cycle_recent）"""
            engines = self.bridge.engines()
            if not engines:
                self._error("无可用引擎")
                return
            cur = self.bridge.current_engine()
            try:
                idx = engines.index(cur)
            except ValueError:
                idx = -1
            nxt = engines[(idx + 1) % len(engines)]
            self._switch_model(nxt)

        def action_history_search(self):
            """f3：翻出最近一条历史输入到输入框（连按回溯更早）"""
            self.action_history_step(previous=True)

        def action_history_step(self, previous=True):
            """历史翻找：previous=True 往更早翻，False 往回（opencode up/down）"""
            if not self._input_history:
                self._system("暂无输入历史")
                return
            if self._hist_idx is None:
                if previous:
                    self._hist_idx = len(self._input_history) - 1
                else:
                    return
            else:
                delta = -1 if previous else 1
                self._hist_idx += delta
                if self._hist_idx >= len(self._input_history):
                    self._hist_idx = None
                    self._user_input().text = ""
                    return
                self._hist_idx = max(0, self._hist_idx)
            ta = self._user_input()
            ta.text = self._input_history[self._hist_idx]
            ta.focus()
            self._update_vim_mode_display()

        def action_toggle_tool_fold(self):
            """f4：工具调用折叠/展开"""
            self._tool_folded = not self._tool_folded
            self._system("工具调用显示: " + ("折叠" if self._tool_folded else "展开"))
            self._update_sidebar()

        def _command_table(self):
            """命令名 -> handler(args)（供面板与 _handle_command 共用；统一收一个可选 args）"""
            return {
                'help': lambda a="": self._show_help(),
                'quit': lambda a="": self.exit(),
                'q': lambda a="": self.exit(),
                'exit': lambda a="": self.exit(),
                'cli': lambda a="": self._switch_cli(),
                'clear': lambda a="": self.action_clear(),
                'cls': lambda a="": self.action_clear(),
                'model': lambda a="": self._switch_model(a),
                'engine': lambda a="": self._switch_model(a),
                'about': lambda a="": self._system(f" 小狸 Pro-CLI v{VERSION} - 智能编程助手"),
                'status': lambda a="": self._show_status(),
                'tools': lambda a="": self._show_tools(),
                'engines': lambda a="": self._show_engines(),
                'tui': lambda a="": self._system("已在 TUI 模式中"),
                'manual': lambda a="": self._handle_manual(a),
                'plan': lambda a="": self._tui_plan(a),
                'build': lambda a="": self._tui_build(),
                'sessions': lambda a="": self._tui_sessions(),
                'session': lambda a="": self._tui_session(a),
                'resume': lambda a="": self._tui_resume(a),
                'snapshot': lambda a="": self._save_screenshot(),
                'screenshot': lambda a="": self._save_screenshot(),
                'vim': lambda a="": self._toggle_vim(),
                'palette': lambda a="": self.action_command_palette(),
            }

        # ── 命令处理 ──

        def _handle_command(self, cmd):
            parts = cmd[1:].split(maxsplit=1)
            name = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""

            handler = self._command_table().get(name)
            if handler:
                handler(args)
                return
            if name in self.cli.liugin_commands:
                try:
                    result = self.cli.liugin_commands[name](args)
                    if result:
                        self._system(result[:500])
                except Exception as e:
                    self._error(f"插件命令失败: {e}")
                return
            # 未知命令转发给 cli 完整路由（/agent /providers /chat 等）
            self._forward_to_cli(cmd)

        def _show_help(self):
            help_text = """   命令:
  /help          帮助信息      /palette  命令面板
  /quit          退出          /cli      切命令行
  /model <引擎>  切换 AI 引擎  /engines  列出引擎
  /tools         列出工具      /status   系统状态
  /clear         清屏          /vim      开关 Vim 键位
  /sessions      历史会话      /resume   恢复会话
  /plan /build   PLAN 规划/批准

  ⌨  快捷键 (opencode 对标):
  Ctrl+P     命令面板(模糊搜)  F2       循环换模型
  F3/↑↓     历史输入翻找      F4       工具调用折叠
  Ctrl+O     PLAN 开关         Ctrl+N   新对话
  Ctrl+L     清屏              F1       侧栏
  回车发送   Shift+回车换行    Esc      取消生成
  Ctrl+F/B   翻页下/上         Ctrl+D/U 半页下/上
  Ctrl+Space 焦点切换          i        聚焦并输入
  输入 / 开头 Tab 补全命令

  VIM 输入(默认开): 输入框内 Esc 进普通模式
    h j k l  移动    w/b  跳词    0/$  行首/行尾
    i a o    插入/追加/换行      I A O  行首/行尾/上方
    dd 删行   x 删字   u 撤销     gg/G 文首/文尾
    普通模式下 回车 = 下移一行"""
            self._system(help_text)

        def _handle_manual(self, args):
            """处理 /manual 命令"""
            if 'manual' not in self.cli.engines:
                self._error("manual 引擎未加载")
                return
            if not args:
                if self.bridge.switch_engine('manual'):
                    self._system("已切换到 manual 引擎")
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
            self.cli._switch_to_cli = True
            self.exit()

        def _switch_model(self, name):
            name = name.strip()
            if not name:
                self._show_engines()
                return
            if self.bridge.switch_engine(name):
                self._system(f"已切换到: {name}")
                self._update_sidebar()
                self._update_header()
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
            status_lines = [
                f"  系统状态:",
                f"  引擎: {self.bridge.current_engine()}",
                f"  引擎数: {len(self.bridge.engines())}",
                f"  工具数: {len(self.bridge.tools())}",
                f"  对话数: {len(self.bridge.history())}",
            ]
            self._system('\n'.join(status_lines))

        # ── Plan 模式 / 会话 委派 ──

        def _tui_plan(self, args):
            args = (args or "").strip()
            if args in ('off', 'exit', '退出', 'cancel'):
                self._set_plan_mode(False)
                self._system("已退出 PLAN 模式（计划未执行）")
                return
            self._set_plan_mode(True)
            if args:
                self._system(f"📋 已进入 PLAN 模式，正在只读调研: {args}")
                self._user_msg(f"/plan {args}")
                self._show_thinking()
                self.is_generating = True
                self._update_status("思考中 (PLAN)...")
                self.run_worker(self._generate(args), exclusive=True)
            else:
                self._system("📋 已进入 PLAN 模式。描述任务，AI 将只做只读调研并给出实施计划；/build 批准执行，/plan off 取消。")

        def _tui_build(self):
            if not self.bridge.plan_mode() and not self.bridge.current_plan().strip():
                self._system("当前不在 PLAN 模式，且无已生成的计划")
                return
            self._system("✅ 已批准 PLAN，开始执行…")
            self.is_generating = True
            self._show_thinking()
            self._update_status("执行 PLAN…")
            self.run_worker(self._run_build(), exclusive=True)

        async def _run_build(self):
            """真执行：委托 cli.handle_build_command（计划驱动 process_conversation 走工具链）"""
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self.cli.handle_build_command)
            except Exception as e:
                self.call_after_refresh(self._error, str(e))
            finally:
                self.call_after_refresh(self._remove_thinking)
                self.is_generating = False
                self.call_after_refresh(self._sync_plan)
                self.call_after_refresh(self._update_sidebar)
                self.call_after_refresh(self._update_header)
                self.call_after_refresh(lambda: self._update_status("就绪"))

        def _tui_sessions(self):
            sessions = self.bridge.sessions()
            if not sessions:
                self._system("  无历史会话")
                return
            lines = ["  历史会话:"]
            for i, s in enumerate(sessions[:10], 1):
                title = (s.title or s.id)[:30]
                t = self._format_rel_time(s.updated_at)
                lines.append(f"  {i}. {title}  ({t})")
            self._system('\n'.join(lines))

        def _tui_session(self, args):
            args = (args or "").strip()
            if not args:
                self._tui_sessions()
                return
            if args == 'new':
                self.action_new_chat()
                return
            self._forward_to_cli(f"/resume {args}")

        def _tui_resume(self, args):
            self._forward_to_cli(f"/resume {args}")

        def _forward_to_cli(self, cmd: str):
            """把未知/委派命令交给 cli 完整路由（_handle_cli_command 真命令路由，
            不再走 process_conversation 把命令喂给 AI）；worker 线程执行，不阻塞 UI。"""
            self.is_generating = True
            self._update_status(f"执行 {cmd.split()[0]} …")
            self.run_worker(self._run_cli_command(cmd), exclusive=True)

        async def _run_cli_command(self, cmd: str):
            try:
                loop = asyncio.get_running_loop()

                def _dispatch():
                    fn = getattr(self.cli, '_handle_cli_command', None)
                    if fn is not None:
                        return bool(fn(cmd))
                    self.cli.process_conversation(cmd)
                    return True

                handled = await loop.run_in_executor(None, _dispatch)
                if not handled:
                    # cli 也没认出 → 与 CLI 行为一致，当作普通对话
                    await loop.run_in_executor(None, self.cli.process_conversation, cmd)
            except Exception as e:
                self.call_after_refresh(self._error, str(e))
            finally:
                self.is_generating = False
                self.call_after_refresh(self._sync_plan)
                self.call_after_refresh(self._update_sidebar)
                self.call_after_refresh(lambda: self._update_status("就绪"))

        def _set_plan_mode(self, on: bool):
            self.plan_mode = on
            try:
                self.cli.plan_mode = on
                if not on:
                    self.cli.current_plan = ""
            except Exception:
                pass
            self._update_sidebar()
            self._update_header()
            self._update_status("📋 PLAN" if on else "就绪")

        def _sync_plan(self):
            """从 cli 同步 plan 状态到 TUI 反应变量。"""
            remote = self.bridge.plan_mode()
            if remote != self.plan_mode:
                self.plan_mode = remote
                self._update_sidebar()
                self._update_header()

        # ── AI 生成 ──

        async def _generate(self, user_input):
            import threading
            try:
                self.call_after_refresh(self._remove_thinking)
                self.call_after_refresh(self._show_typing_indicator)

                # 输出走持久桥 _tui_push；挂取消事件供 Esc 真取消（轮间生效）
                ev = threading.Event()
                self._cancel_event = ev
                self.cli._tui_cancel = ev

                try:
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(
                        None, self.cli.process_conversation, user_input
                    )
                finally:
                    # PLAN 模式下把最后一条 assistant 回复同步为当前计划（否则 /build 无计划可执行）
                    try:
                        self.cli._sync_current_plan()
                    except Exception:
                        pass
                    self.cli._tui_cancel = None
                    self._cancel_event = None

            except Exception as e:
                self.call_after_refresh(self._remove_typing_indicator)
                self.call_after_refresh(self._error, str(e))
            finally:
                self.call_after_refresh(self._remove_thinking)
                self.call_after_refresh(self._remove_typing_indicator)
                self.is_generating = False
                self.call_after_refresh(self._sync_plan)
                self.call_after_refresh(lambda: self._update_status("就绪"))
                self.call_after_refresh(self._update_sidebar)
                self.call_after_refresh(self._update_header)

        _ansi_pat = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')

        def _tui_push(self, msg):
            """线程安全输出桥：cli 任意线程（含孤儿生成线程）的输出 → TUI 渲染。
            持久挂载于 cli.tui_output_callback，任何 print/_output 都不会落到 stdout 花屏。"""
            text = self._ansi_pat.sub('', str(msg))

            def _apply():
                self._remove_typing_indicator()
                self._write_raw(text)

            try:
                self.call_from_thread(_apply)
            except RuntimeError:
                # 已在 UI 线程
                try:
                    self.call_after_refresh(_apply)
                except Exception:
                    pass

        def _write_raw(self, msg):
            if '✅' in msg or 'OK 工具' in msg:
                self._add(f"  {msg}" if not self._tool_folded else f"  ⚙ ✓", "msg-tool-ok")
            elif '❌' in msg or 'X 工具' in msg or '错误' in msg:
                self._add(f"  {msg}" if not self._tool_folded else f"  ⚙ ✗", "msg-tool-err")
            elif '🤖' in msg:
                self._add(f"  ● {msg.replace('🤖', '', 1).strip()}", "msg-ai")
            elif '工具' in msg and ('调用' in msg or '执行' in msg):
                if self._tool_folded:
                    return  # 折叠模式下吞掉工具流水行，只留结果标记
                self._add(f"  {msg}", "msg-tool-ok")
            else:
                self._add(f"  {msg}", "msg-dim")

        # ── 动作 ──

        def action_clear(self):
            scroll = self.query_one("#chat-scroll")
            scroll.remove_children()
            self._render_welcome()

        def action_new_chat(self):
            self.cli.shared_conversation_history.clear()
            self.action_clear()
            self._system("已开始新对话")

        def action_toggle_sidebar(self):
            sidebar = self.query_one("#sidebar")
            if sidebar.has_class("hidden"):
                sidebar.remove_class("hidden")
                self.sidebar_visible = True
            else:
                sidebar.add_class("hidden")
                self.sidebar_visible = False

        def action_toggle_plan(self):
            self._set_plan_mode(not self.plan_mode)
            self._system("📋 PLAN 模式: " + ("开" if self.plan_mode else "关"))

        def action_cancel(self):
            if self.is_generating:
                if self._cancel_event is not None:
                    self._cancel_event.set()
                self._remove_thinking()
                self._remove_typing_indicator()
                self._system("已取消（当前轮结束后停止，输出不入流）")
                self.is_generating = False

        # ── Vim 风格：聊天区滚动 / 聚焦切换 ──
        def _user_input(self):
            return self.query_one("#user-input")

        def _chat_scroll(self):
            return self.query_one("#chat-scroll")

        def action_toggle_focus(self):
            """Ctrl+Space：在输入框与聊天区之间切换焦点。"""
            ta = self._user_input()
            if ta.has_focus:
                self.screen.set_focus(None)
            else:
                ta.focus()
                if getattr(ta, "vim_enabled", False):
                    ta.vim.mode = "INSERT"
                self._update_vim_mode_display()

        def action_focus_insert(self):
            """i：输入框未聚焦时聚焦并进入 INSERT（模仿 vim 按 i 开始输入）。"""
            ta = self._user_input()
            if ta.has_focus:
                return
            ta.focus()
            if getattr(ta, "vim_enabled", False):
                ta.vim.mode = "INSERT"
            self._update_vim_mode_display()

        def _guard_chat(self):
            """聊天导航仅在输入框未聚焦时生效，避免与输入冲突。"""
            return self._user_input().has_focus

        def action_chat_down(self):
            if self._guard_chat():
                return
            self._chat_scroll().scroll_down(3)

        def action_chat_up(self):
            if self._guard_chat():
                return
            self._chat_scroll().scroll_up(3)

        def action_chat_page_down(self):
            if self._guard_chat():
                return
            self._chat_scroll().scroll_page_down()

        def action_chat_page_up(self):
            if self._guard_chat():
                return
            self._chat_scroll().scroll_page_up()

        def action_chat_half_down(self):
            if self._guard_chat():
                return
            self._chat_scroll().scroll_relative(y=20)

        def action_chat_half_up(self):
            if self._guard_chat():
                return
            self._chat_scroll().scroll_relative(y=-20)

        def _update_vim_mode_display(self):
            """在输入框下方提示栏显示当前 Vim 模式（opencode 式 -- INSERT -- 标签）。"""
            try:
                hint = self.query_one("#input-hint")
                ta = self._user_input()
            except Exception:
                return
            if not getattr(ta, "vim_enabled", False):
                hint.update("  回车发送 | Shift+回车换行 | Ctrl+L 清屏 | F1 侧栏 | Ctrl+P 面板 | Ctrl+O PLAN")
                return
            mode = getattr(getattr(ta, "vim", None), "mode", "INSERT")
            tag = "-- INSERT --" if mode == "INSERT" else "-- NORMAL --"
            hint.update(f"  {tag}  │  Esc 切模式  │  i插入 a追加 o换行  hjkl移动  dd删行 x删字  u撤销")

        def _toggle_vim(self):
            ta = self._user_input()
            ta.vim_enabled = not getattr(ta, "vim_enabled", True)
            if ta.vim_enabled:
                self._system("Vim 键位: 开 (Esc 在 NORMAL/INSERT 间切换)")
            else:
                self._system("Vim 键位: 关 (普通输入)")
            self._update_vim_mode_display()

        def _save_screenshot(self):
            """导出当前 TUI 屏幕截图（SVG）——AI 可据此自验实时渲染（/snapshot）"""
            import os
            out_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tui_snapshots"
            )
            os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, "live.svg")
            try:
                svg = self.export_screenshot()
                with open(path, "w", encoding="utf-8") as f:
                    f.write(svg)
                self._system(f"截图已保存: {path}")
            except Exception as e:
                self._error(f"截图失败: {e}")

else:
    # Textual 不可用时的占位类
    class XiaoliTUI:
        """Textual 未安装时的占位类"""
        def __init__(self, *args, **kwargs):
            pass
        def run(self, *args, **kwargs):
            print("TUI 模式不可用：Textual 库未安装")
            print("请运行: pip install textual rich")
