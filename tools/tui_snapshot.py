"""
v8.0 TUI 快照生成器（无头）
==========================
直接用 RichTUI.push() 喂一段脚本化对话，导出 .tui_snapshots/demo.{txt,svg,html}。
AI 可把 .txt 读回核验布局；把 .html/.svg 交给用户预览。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.text import Text
from xcli_core.rich_tui import RichTUI, SNAP_DIR


def main():
    tui = RichTUI(cli=None)
    tui.set_status(
        engine="openai", model="deepseek-chat", mode="TUI",
        used_tokens=47000, context_window=64000, msg_count=4,
    )
    tui.banner()

    # 脚本化 transcript（模拟 DisplayMixin 通过 tui_output_callback 投喂的内容）
    transcript = [
        ("[cyan]>[/] 帮我看下 core/app.py 有没有内存泄漏", "user"),
        ("[yellow]思考: 我先搜索一下文件结构与资源释放逻辑...[/]", "think"),
        ("[green]  OK 工具: read_file[/]", "tool_ok"),
        ("[green]   文件路径: core/app.py (248 行)[/]", "tool_ok"),
        ("[red]  X 工具: shell_exec[/]", "tool_err"),
        ("[red]   错误: 命令超时 (30s)[/]", "tool_err"),
        ("[white]根据分析，core/app.py 在 __del__ 中调用 cleanup_resources，"
         "但多线程下可能重复释放...[/]", "assistant"),
        ("[cyan]>[/] 那顺手修一下吧", "user"),
        ("[green]  OK 工具: edit_file[/]", "tool_ok"),
        ("[green]   已更新 cleanup_resources，加锁防止重复释放[/]", "tool_ok"),
        ("[white]已修复：为 cleanup_resources 增加了 _cleaned 标志位，确保只释放一次。[/]", "assistant"),
    ]
    for msg, _kind in transcript:
        tui.push(msg)

    tui.console.print(Text.from_markup(tui._bar()))

    os.makedirs(SNAP_DIR, exist_ok=True)
    stem = os.path.join(SNAP_DIR, "demo")
    txt, svg, html = tui.save_snapshot(stem)
    print("快照已生成:")
    print("  文本:", txt)
    print("  SVG :", svg)
    print("  HTML:", html)
    print("\n===== 文本快照预览 =====\n")
    print(tui.snapshot_text())


if __name__ == "__main__":
    main()
