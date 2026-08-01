"""TUI 界面模块 - Textual TUI 实现 (动画增强版 + 多行输入)"""

from .constants import TEXTUAL_AVAILABLE, VERSION

if TEXTUAL_AVAILABLE:
    import re
    import asyncio
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical, VerticalScroll, Container
    from textual.widgets import Header, Static, Rule, TextArea
    from textual.reactive import var
    from textual.binding import Binding
    from textual import on
    from rich.syntax import Syntax
    from rich.panel import Panel
    from rich.box import ROUNDED

    # ── TUI 主题色 ──
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
        # 动画额外色
        GLOW = "#1f6feb"
        THINKING = "#8b949e"
        WELCOME_ACCENT = "#58a6ff"

    _TUI_CSS = f"""
    Screen {{
        background: {_Theme.BG};
        /* 全局过渡 */
        transition: background 300ms in_out_cubic;
    }}

    #app-container {{
        height: 100%;
        width: 100%;
    }}

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

    /* ── 输入区域 ── */
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
        /* 聚焦时边框颜色过渡 */
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

    /* TextArea 内部样式覆盖 */
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
        /* 渐入效果 */
        opacity: 0;
        transition: opacity 500ms in_out_cubic;
    }}

    #input-hint.visible {{
        opacity: 1;
    }}

    /* ── 侧栏 ── */
    #sidebar {{
        width: 32;
        min-width: 32;
        height: 1fr;
        background: {_Theme.BG_LIGHT};
        border-left: wide {_Theme.BORDER};
        display: block;
        /* 侧栏滑入/滑出动画 */
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

    .tool-item-name {{
        color: {_Theme.TEXT};
        text-style: bold;
    }}

    /* ── 状态栏 ── */
    #status-bar {{
        height: 1;
        width: 100%;
        dock: bottom;
        background: {_Theme.BG_LIGHT};
        color: {_Theme.TEXT_MUTED};
        padding: 0 1;
        /* 状态变化过渡 */
        transition: color 300ms in_out_cubic;
    }}

    /* ── 消息样式 ── */
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
        /* 每行依次淡入 */
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

    /* 动画思考指示器 */
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

    /* ── Tab 样式 ── */
    Tab {{
        background: {_Theme.BG};
    }}

    Tab.-active {{
        background: {_Theme.BG_LIGHT};
    }}

    TabbedContent > Tabs {{
        background: {_Theme.BG};
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
        """带入场动画的消息气泡"""
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
            # 其他键正常处理

    # ═══════════════════════════════════════════════════
    #  TUI 主应用
    # ═══════════════════════════════════════════════════

    class XiaoliTUI(App):
        """小狸 TUI v3 - 动画增强版 + 多行输入"""
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
            Binding("escape", "cancel", "取消", show=False),
        ]

        sidebar_visible = var(True)
        is_generating = var(False)

        def __init__(self, cli):
            super().__init__()
            self.cli = cli
            self.bridge = _TUIBridge(cli)
            self._thinking_widget = None
            self._typing_widget = None

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Horizontal(id="app-container"):
                with Vertical(id="main"):
                    yield VerticalScroll(id="chat-scroll")
                    with Vertical(id="input-area"):
                        with Container(id="input-wrapper"):
                            yield SendTextArea(
                                placeholder="输入消息... (回车发送, Shift+回车换行)",
                                id="user-input",
                                soft_wrap=True,
                                tab_behavior="indent",
                            )
                        yield Static(
                            "  回车发送 | Shift+回车换行 | Ctrl+L 清屏 | F1 侧栏",
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
            yield Static(" 就绪 | Ctrl+C 退出", id="status-bar")

        def on_mount(self):
            self._render_welcome_animated()
            self._update_sidebar()
            self.query_one("#user-input").focus()
            # 延迟显示输入提示（淡入效果）
            self.set_timer(1.5, lambda: self.query_one("#input-hint").add_class("visible"))

        # ── 动画欢迎界面 ──

        def _render_welcome_animated(self):
            """逐行动画显示欢迎界面"""
            scroll = self.query_one("#chat-scroll")

            welcome_lines = [
                "",
                "  ╔══════════════════════════════════════════════╗",
                "  ║                                              ║",
                "  ║    小狸 Pro-CLI v8.0.0                        ║",
                "  ║    智能编程助手 · 动画增强版                  ║",
                "  ║                                              ║",
                "  ╚══════════════════════════════════════════════╝",
                "",
                "   代码编辑 · 代码搜索 · Git 集成 · 多引擎",
                "   输入 /help 查看命令 | /model 切换引擎",
                f"   当前引擎: {self.bridge.current_engine()} | 工具: {len(self.bridge.tools())} 个",
                "   支持多行输入 — Shift+回车换行",
                "",
            ]

            # 逐行渲染，带延迟
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
                # 延迟显示每一行（避免 delay=0 导致 Textual 除零错误）
                delay = max(0.01, i * 0.1)
                self.set_timer(delay, lambda w=widget: w.add_class("visible"))

            # 最后滚动到底部
            self.set_timer(max(0.01, len(welcome_lines) * 0.1 + 0.1),
                          lambda: scroll.scroll_end(animate=True, duration=0.3))

        def _render_welcome(self):
            """静态欢迎界面（用于清屏后快速恢复）"""
            scroll = self.query_one("#chat-scroll")
            lines = [
                ("", "msg-dim"),
                ("  ╔══════════════════════════════════════════════╗", "msg-welcome"),
                ("  ║                                              ║", "msg-welcome"),
                ("  ║    小狸 Pro-CLI v8.0.0                        ║", "msg-welcome"),
                ("  ║    智能编程助手 · 动画增强版                  ║", "msg-welcome"),
                ("  ║                                              ║", "msg-welcome"),
                ("  ╚══════════════════════════════════════════════╝", "msg-welcome"),
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
            engine_container = self.query_one("#engine-list")
            engine_container.remove_children()
            current = self.bridge.current_engine()
            for name in self.bridge.engines():
                if name == current:
                    engine_container.mount(Static(f"  ▸ {name}", classes="engine-item-active"))
                else:
                    engine_container.mount(Static(f"    {name}", classes="engine-item"))

            tool_container = self.query_one("#tool-list")
            tool_container.remove_children()
            for tool in self.bridge.tools():
                name = tool.get('name', '?')
                tool_container.mount(Static(f"  • {name}", classes="tool-item"))

            status_container = self.query_one("#status-info")
            status_container.remove_children()
            status_container.mount(Static(f"  对话: {len(self.bridge.history())} 条", classes="tool-item"))
            status_container.mount(Static(f"  工具: {len(self.bridge.tools())} 个", classes="tool-item"))
            status_container.mount(Static(f"  引擎: {len(self.bridge.engines())} 个", classes="tool-item"))

            # 工具数
            if hasattr(self.cli, 'liugin_manager'):
                status_container.mount(Static(f"  工具: {len(self.cli.liugin_manager.tools)} 个", classes="tool-item"))

        def _update_status(self, text: str):
            bar = self.query_one("#status-bar")
            engine = self.bridge.current_engine()
            bar.update(f" {text} | {engine} | {len(self.bridge.history())} 条对话{self._token_str()}")

        def _token_str(self):
            """token 用量进度（v8.0 token 感知压缩联动，引擎支持时显示）"""
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

        # ── 消息追加 ──

        def _append(self, widget):
            scroll = self.query_one("#chat-scroll")
            scroll.mount(widget)
            scroll.scroll_end(animate=True, duration=0.2)

        def _add(self, text, cls="msg-dim"):
            widget = MessageBubble(text, classes=cls)
            self._append(widget)

        def _user_msg(self, text):
            self._add(f"   {text}", "msg-user")

        def _ai_msg(self, text):
            if "```" in text:
                self._render_with_code(text)
            else:
                self._add(f"   {text}", "msg-ai")

        def _render_with_code(self, text):
            parts = re.split(r'```(\w*)\n(.*?)```', text, flags=re.DOTALL)
            i = 0
            while i < len(parts):
                if i % 3 == 0:
                    if parts[i].strip():
                        for line in parts[i].strip().split('\n'):
                            self._add(f"   {line}", "msg-ai")
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
            self._add(f"   {name}: {args[:60]}", "msg-tool-ok")

        def _tool_err(self, name, args):
            self._add(f"   {name}: {args[:60]}", "msg-tool-err")

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
                text_area.action_edit_insert_newline()

        def action_send_message(self):
            """回车发送消息"""
            text_area = self.query_one("#user-input")
            text = text_area.text.strip()
            if not text:
                return

            # 清空输入框
            text_area.clear()

            if text.startswith('/'):
                self._handle_command(text)
                return

            self._user_msg(text)
            self._show_thinking()
            self.is_generating = True
            self._update_status(" 思考中...")
            self.run_worker(self._generate(text), exclusive=True)

        # ── 兼容旧 Input 提交（保留以防万一） ──

        @on(TextArea.Changed, "#user-input")
        def on_textarea_changed(self, event):
            """输入框内容变化时调整高度"""
            text_area = event.text_area
            line_count = text_area.text.count('\n') + 1
            # 动态调整输入区域高度
            wrapper = self.query_one("#input-wrapper")
            new_height = min(max(line_count + 1, 4), 12)
            wrapper.styles.height = new_height

        # ── 命令处理 ──

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
                'about': lambda: self._system(f" 小狸 Pro-CLI v{VERSION} - 智能编程助手"),
                'status': lambda: self._show_status(),
                'tools': lambda: self._show_tools(),
                'engines': lambda: self._show_engines(),
                'tui': lambda: self._system("已在 TUI 模式中"),
                'manual': lambda: self._handle_manual(args),
                'snapshot': lambda: self._save_screenshot(),
                'screenshot': lambda: self._save_screenshot(),
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

        def _show_help(self):
            help_text = """   命令:
  /help          帮助信息
  /quit          退出
  /cli           切换命令行模式
  /model <引擎>  切换 AI 引擎
  /engines       列出引擎
  /tools         列出工具
  /status        系统状态
  /clear         清屏

  ⌨  快捷键:
  Ctrl+C     退出        Ctrl+L     清屏
  Ctrl+N     新对话      回车       发送消息
  Shift+回车 换行        F1         侧栏
  Escape     取消生成    Tab        缩进"""
            self._system(help_text)

        def _handle_manual(self, args):
            """处理 /manual 命令"""
            if 'manual' not in self.cli.engines:
                self._error("manual 引擎未加载")
                return
            if not args:
                # 切换到 manual 引擎
                if self.bridge.switch_engine('manual'):
                    self._system("已切换到 manual 引擎")
                    self._update_sidebar()
                else:
                    self._error("切换失败")
            else:
                # 执行 manual 引擎子命令
                result = self.cli.engines['manual'].handle_command(args)
                if result:
                    self._system(result)

        def _switch_cli(self):
            self._system("切换到命令行模式...")
            self.cli.tui_output_callback = None
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
            status_lines = [
                f"  系统状态:",
                f"  引擎: {self.bridge.current_engine()}",
                f"  引擎数: {len(self.bridge.engines())}",
                f"  工具数: {len(self.bridge.tools())}",
                f"  对话数: {len(self.bridge.history())}",
            ]

            self._system('\n'.join(status_lines))

        # ── AI 生成 ──

        async def _generate(self, user_input):
            try:
                self.call_after_refresh(self._remove_thinking)
                self.call_after_refresh(self._show_typing_indicator)

                def tui_output(msg):
                    self.call_after_refresh(self._remove_typing_indicator)
                    self.call_after_refresh(self._write_raw, msg)

                original = self.cli.tui_output_callback
                self.cli.tui_output_callback = tui_output

                try:
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(
                        None, self.cli.process_conversation, user_input
                    )
                finally:
                    self.cli.tui_output_callback = original

            except Exception as e:
                self.call_after_refresh(self._remove_typing_indicator)
                self.call_after_refresh(self._error, str(e))
            finally:
                self.call_after_refresh(self._remove_thinking)
                self.call_after_refresh(self._remove_typing_indicator)
                self.is_generating = False
                self.call_after_refresh(lambda: self._update_status("就绪"))
                self.call_after_refresh(self._update_sidebar)

        def _write_raw(self, msg):
            if '✅' in msg or 'OK 工具' in msg:
                self._add(f"  {msg}", "msg-tool-ok")
            elif '❌' in msg or 'X 工具' in msg or '错误' in msg:
                self._add(f"  {msg}", "msg-tool-err")
            elif '🤖' in msg:
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
            self.cli.shared_conversation_history.clear()
            self.action_clear()
            self._system("已开始新对话")

        def action_toggle_sidebar(self):
            sidebar = self.query_one("#sidebar")
            # 通过 CSS 类控制侧栏显隐
            if sidebar.has_class("hidden"):
                sidebar.remove_class("hidden")
                self.sidebar_visible = True
            else:
                sidebar.add_class("hidden")
                self.sidebar_visible = False

        def action_cancel(self):
            if self.is_generating:
                self._remove_thinking()
                self._remove_typing_indicator()
                self._system("已取消")
                self.is_generating = False

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
