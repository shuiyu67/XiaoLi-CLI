# -*- coding: utf-8 -*-
"""视觉审查第一步：headless 采集 TUI 四屏截图（home/session/palette/leader）"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeCli:
    engines = {"openai": object(), "ollama": object()}
    liugin_manager = type("T", (), {"tools": [{"name": "code_editor", "description": "x"},
                                              {"name": "py_detect", "description": "x"}]})()
    shared_conversation_history = []
    plan_mode = False
    current_plan = ""
    config = {}
    current_engine = None
    liugin_commands = {}
    tui_output_callback = None
    session_manager = None

    def get_current_engine_name(self):
        return "openai"

    def switch_engine(self, n):
        pass

    def _handle_cli_command(self, cmd):
        return True

    def _sync_current_plan(self):
        pass


from xcli_core.tui import XiaoliTUI  # noqa: E402


def shot(app, name):
    svg = app.export_screenshot()
    with open(name, "w", encoding="utf-8") as f:
        f.write(svg)
    # 文字真值走 compositor strips（=终端真实字符）。
    # 不用 rich Console 序列化：那条路会丢部分 CJK 与空白（审查假象之源）。
    sr = app.screen._compositor.render_update(
        full=True, screen_stack=app._background_screens, simplify=False)
    lines = []
    for strip in sr.strips:
        row = []
        for seg in strip:
            t = getattr(seg, "text", None)
            if t:
                row.append(t)
        lines.append("".join(row).rstrip())
    txt = "\n".join(lines)
    with open(name.replace(".svg", ".txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    print(f"{name} + .txt(strips)  ({len(svg)}/{len(txt)} bytes)", flush=True)


async def main():
    app = XiaoliTUI(FakeCli())
    async with app.run_test(size=(120, 38)) as pilot:
        await pilot.pause(0.6)
        shot(app, "tui_v_home.svg")

        app._user_msg("帮我看看这段代码怎么改")
        app._ai_msg("## 修复方案\n\n1. 修正 `foo()` 的空指针\n\n```python\ndef foo(x):\n    return x or 0\n```\n\n**完成。**")
        app._tool_ok("code_editor", "edit foo.py --line 12")
        app._update_status("就绪")
        await pilot.pause(0.6)
        shot(app, "tui_v_session.svg")

        await pilot.press("ctrl+p")
        await pilot.pause(0.4)
        shot(app, "tui_v_palette.svg")
        await pilot.press("escape")
        await pilot.pause(0.3)

        await pilot.press("ctrl+x")
        await pilot.pause(0.4)
        shot(app, "tui_v_leader.svg")
        await pilot.press("escape")

    print("4 屏采集完成", flush=True)


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(main(), timeout=90))
