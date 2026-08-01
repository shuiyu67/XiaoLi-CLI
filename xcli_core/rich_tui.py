"""
v8.0 Rich 面板式 TUI + 可截取快照出口
======================================
- 通过 cli.tui_output_callback = RichTUI.push 接收逐行输出，渲染为 rich 面板
- Console(record=True) 快照出口: export_text / export_svg / export_html
  → AI 开发 TUI 时能把渲染结果读回自验，补上“看不见渲染”的反馈闭环

设计取舍（与 7.0 重构前 textual TUI 的区别）:
- 不用 textual 的异步全屏 App，避免与同步 input() 主循环冲突；
- 采用 rich 顺序面板流（一问一答往下渲染），天然支持 record=True 快照；
- 这正是“让 AI 能看见自己写的 TUI”的关键能力。
"""
import os
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.box import ROUNDED

SNAP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tui_snapshots"
)


class RichTUI:
    """rich 面板式 TUI：聊天面板 + 状态栏 + 快照出口。"""

    def __init__(self, cli):
        self.cli = cli
        # record=True 是关键：渲染过程被记录，可随时导出文本/SVG/HTML 自验
        self.console = Console(record=True, width=100)
        self.version = "8.0.0"
        self.engine = ""
        self.model = ""
        self.mode = "普通"
        self.used_tokens = None
        self.context_window = None
        self.msg_count = 0
        self._log = []

    # ── 状态设置（由 cli 在切换引擎/压缩后刷新）──
    def set_status(self, engine=None, model=None, mode=None,
                   used_tokens=None, context_window=None, msg_count=None):
        if engine is not None:
            self.engine = engine
        if model is not None:
            self.model = model
        if mode is not None:
            self.mode = mode
        if used_tokens is not None:
            self.used_tokens = used_tokens
        if context_window is not None:
            self.context_window = context_window
        if msg_count is not None:
            self.msg_count = msg_count

    def banner(self):
        self.console.print(Panel(
            Text.from_markup(f"[bold cyan]小狸 Pro-CLI[/]  [yellow]v{self.version}[/]  ·  Rich TUI"),
            subtitle="[dim]自然语言对话 · /exit 返回 CLI · /snapshot 导出快照[/]",
            box=ROUNDED, border_style="cyan"))
        self.console.print()

    def _bar(self):
        if self.used_tokens and self.context_window:
            ratio = min(1.0, self.used_tokens / self.context_window)
            filled = int(ratio * 10)
            bar = "▓" * filled + "░" * (10 - filled)
            tok = f"{self.used_tokens}/{self.context_window} {bar}"
        elif self.used_tokens:
            tok = f"{self.used_tokens} tokens"
        else:
            tok = "-"
        return (f"[dim]引擎 {self.engine or '-'} · 模型 {self.model or '-'} · "
                f"模式 {self.mode} · {tok} · 消息 {self.msg_count}[/]")

    # ── 回调入口：DisplayMixin._output 把每行输出投到这里 ──
    def push(self, message):
        m = (message or "").strip("\n")
        if not m:
            return
        self._log.append(m)
        if len(self._log) > 300:
            self._log = self._log[-300:]
        # 原始 message 已由 DisplayMixin 产出合法 rich markup，直接打印；
        # 个别工具结果含裸方括号可能破坏 markup，失败则降级为纯文本。
        try:
            self.console.print(m)
        except Exception:
            self.console.print(m, markup=False)

    # ── 快照出口（AI 自验渲染的关键能力）──
    def snapshot_text(self):
        return self.console.export_text(clear=False)

    def snapshot_svg(self, title="小狸 Pro-CLI v8.0 Rich TUI"):
        return self.console.export_svg(title=title, clear=False)

    def snapshot_html(self, title="小狸 Pro-CLI v8.0 Rich TUI"):
        # rich 新版 export_html 不接受 title 参数，标题作为注释写入
        html = self.console.export_html(clear=False)
        return f"<!-- {title} -->\n{html}"

    def save_snapshot(self, stem):
        os.makedirs(os.path.dirname(stem), exist_ok=True)
        with open(stem + ".txt", "w", encoding="utf-8") as f:
            f.write(self.snapshot_text())
        with open(stem + ".svg", "w", encoding="utf-8") as f:
            f.write(self.snapshot_svg())
        with open(stem + ".html", "w", encoding="utf-8") as f:
            f.write(self.snapshot_html())
        return stem + ".txt", stem + ".svg", stem + ".html"

    # ── 主循环 ──
    def run(self):
        self.banner()
        try:
            import readline  # 可选：输入历史补全
        except Exception:
            pass
        while True:
            try:
                ui = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if ui in ("/exit", "/quit"):
                break
            if ui == "/snapshot":
                paths = self.save_snapshot(os.path.join(SNAP_DIR, "live"))
                print(f"[快照已保存] {paths[2]}")
                continue
            if ui:
                self.cli.process_conversation(ui)
                self.msg_count = len(self.cli.shared_conversation_history)
                self.console.print(Text.from_markup(self._bar()))
