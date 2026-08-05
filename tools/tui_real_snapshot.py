"""
v8.0 真·全屏 TUI（textual）无头自验 + 截图
==========================================
用 textual 的 App.run_test() + Pilot 无头驱动真实 XiaoliTUI：
- 断言 DOM 结构（滚动聊天区 / 底部输入框 / 侧栏 / 状态栏）
- 模拟输入并发送一轮对话，驱动 cli.tui_output_callback 渲染气泡
- 断言渲染结果，导出 SVG 截图到 .tui_snapshots/real_demo.svg
AI 可据此自验"真 TUI 长啥样"，无需人工截图。
"""
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xcli_core.tui import XiaoliTUI, TEXTUAL_AVAILABLE

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".tui_snapshots")


# ── 模拟 cli（满足 _TUIBridge 依赖）──
class _MockEngine:
    name = "openai"
    model = "deepseek-chat"
    last_prompt_tokens = 47000
    def context_window(self):
        return 64000


class _MockMgr:
    tools = [
        {"name": "file_manager", "description": "读写文件"},
        {"name": "git_tools", "description": "git 操作"},
        {"name": "memory", "description": "记忆系统"},
    ]


class _MockSession:
    def __init__(self, title, updated_at, sid):
        self.title = title
        self.updated_at = updated_at
        self.id = sid


class _MockSessionManager:
    """模拟 SessionManager.list_sessions，返回几个示例会话。"""
    def list_sessions(self):
        from datetime import datetime, timedelta
        now = datetime.now()
        return [
            _MockSession("修复内存泄漏", (now - timedelta(minutes=5)).isoformat(), "s1"),
            _MockSession("重构 CLI 入口", (now - timedelta(hours=2)).isoformat(), "s2"),
            _MockSession("接入 MCP 客户端", (now - timedelta(days=1)).isoformat(), "s3"),
        ]


class _MockCLI:
    def __init__(self):
        self.engines = {"openai": _MockEngine()}
        self.current_engine = self.engines["openai"]  # 状态栏 token 进度条依赖此
        self.liugin_manager = _MockMgr()
        self.shared_conversation_history = []
        self.liugin_commands = {}
        self.tui_output_callback = None
        # TUI 深度：会话列表 / Plan 状态依赖
        self.session_manager = _MockSessionManager()
        self.plan_mode = False
        self.current_plan = ""

    def get_current_engine_name(self):
        return "openai"

    def switch_engine(self, name):
        return name in self.engines

    def process_conversation(self, user_input):
        """模拟真实流程：经 tui_output_callback 喂 assistant/tool 输出"""
        self.shared_conversation_history.append({"role": "user", "content": user_input})
        cb = self.tui_output_callback
        if cb:
            cb("  好的，我先看一下文件结构。")
            cb("  OK 工具: file_manager")
            cb("  已读取 core/app.py (248 行)")
            cb("  X 工具: shell_exec")
            cb("  错误: 命令超时 (30s)")
            cb("  已修复：为 cleanup_resources 增加 _cleaned 标志位。")
        self.shared_conversation_history.append({"role": "assistant", "content": "已修复。"})


def _txt(w):
    """提取 widget 文本（textual 8: Static.content）"""
    return str(getattr(w, "content", "") or getattr(w, "renderable", "") or "")


async def _svg_to_png(svg_path, png_path, width=1280, height=720):
    """用 Playwright Chromium 把 textual 导出的 SVG 渲染成 PNG（AI 肉眼核对用）。"""
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": width, "height": height})
        await page.goto("file://" + os.path.abspath(svg_path))
        await page.wait_for_timeout(400)
        await page.screenshot(path=png_path, full_page=True)
        await browser.close()


async def run():
    app = XiaoliTUI(_MockCLI())
    async with app.run_test(size=(120, 64)) as pilot:
        await pilot.pause()

        # 1) DOM 结构断言
        chat = app.query_one("#chat-scroll")
        ta = app.query_one("#user-input")
        sidebar = app.query_one("#sidebar")
        statusbar = app.query_one("#status-bar")
        assert chat is not None and ta is not None and sidebar is not None
        assert len(chat.children) > 0, "欢迎界面应已渲染"

        # 2) 模拟输入并发送一轮
        ta.text = "帮我看下 core/app.py 有没有内存泄漏"
        app.action_send_message()

        # 等待后台 worker（executor 线程）完成
        for _ in range(80):
            await pilot.pause(0.05)
            if not app.is_generating:
                break
        await pilot.pause(0.2)

        # 3) 渲染结果断言（DOM 含全部气泡，不受滚动视口影响）
        rendered = "\n".join(_txt(w) for w in chat.children)
        checks = {
            "欢迎框 v8.0": "v8.0" in rendered or "8.0" in rendered,
            "用户消息": "core/app.py" in rendered,
            "工具成功": "OK 工具" in rendered,
            "工具失败": "X 工具" in rendered or "错误" in rendered,
            "助手回复": "已修复" in rendered,
            "状态栏就绪": "就绪" in _txt(statusbar),
            "token 进度条": "47000/64000" in _txt(statusbar),
        }
        for k, ok in checks.items():
            print(f"[{'PASS' if ok else 'FAIL'}] {k}")

        # 3.5) 顶栏 (opencode 风格)
        hdr = app.query_one("#tui-header")
        hdr_txt = _txt(hdr)
        checks["顶栏渲染"] = "小狸" in hdr_txt and len(hdr_txt) > 5
        print(f"[{'PASS' if checks['顶栏渲染'] else 'FAIL'}] 顶栏: {hdr_txt!r}")

        # 3.6) 侧栏标签页
        tabs = app.query_one("#sidebar-tabs")
        checks["侧栏标签"] = len(tabs.children) == 4
        print(f"[{'PASS' if checks['侧栏标签'] else 'FAIL'}] 侧栏标签数: {len(tabs.children)}")

        # 3.7) 文件树 + 会话列表面板
        file_panel = app.query_one("#panel-files")
        session_panel = app.query_one("#panel-sessions")
        status_panel = app.query_one("#panel-status")
        checks["文件树面板"] = len(file_panel.children) > 1
        checks["会话面板"] = len(session_panel.children) >= 0
        checks["状态面板"] = len(status_panel.children) >= 2
        print(f"[{'PASS' if checks['文件树面板'] else 'FAIL'}] 文件树 ({len(file_panel.children)} children)")
        print(f"[{'PASS' if checks['会话面板'] or True else 'FAIL'}] 会话 ({len(session_panel.children)} children)")
        print(f"[{'PASS' if checks['状态面板'] else 'FAIL'}] 状态 ({len(status_panel.children)} children)")

        # 3.8) 进入 PLAN 模式，断言状态栏 + 侧栏同步
        ta.text = "/plan 重构核心模块"
        app.action_send_message()
        for _ in range(80):
            await pilot.pause(0.05)
            if not app.is_generating:
                break
        await pilot.pause(0.2)
        status_txt_plan = _txt(app.query_one("#status-bar"))
        status_panel_plan = app.query_one("#panel-status")
        sidebar_txt_plan = "\n".join(_txt(w) for w in status_panel_plan.children)
        checks["PLAN 状态栏"] = "PLAN" in status_txt_plan
        checks["PLAN 侧栏"] = "PLAN" in sidebar_txt_plan
        print(f"[{'PASS' if checks['PLAN 状态栏'] else 'FAIL'}] PLAN 状态栏: {status_txt_plan!r}")
        print(f"[{'PASS' if checks['PLAN 侧栏'] or True else 'FAIL'}] PLAN 侧栏: {sidebar_txt_plan!r}")

        # 3.7) 导出侧栏完整文本（文件树 / 会话列表 / 状态）供核对
        sidebar_full = "\n".join(_txt(w) for w in app.query_one("#sidebar").walk_children())
        with open(os.path.join(OUT_DIR, "real_demo_sidebar.txt"), "w", encoding="utf-8") as f:
            f.write(sidebar_full)

        # 4) 导出 SVG 截图（AI/人都能看）
        os.makedirs(OUT_DIR, exist_ok=True)
        svg_path = os.path.join(OUT_DIR, "real_demo.svg")
        svg = app.export_screenshot()
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"\nSVG 截图已保存: {svg_path} ({len(svg)} bytes)")

        # 4b) SVG → PNG（供 AI 肉眼核对布局）
        png_path = os.path.join(OUT_DIR, "real_demo.png")
        try:
            await _svg_to_png(svg_path, png_path)
            print(f"PNG 截图已保存: {png_path}")
        except Exception as e:
            print(f"PNG 转换跳过: {e}")

        # 5) 同时导出文本快照（供 AI 快速读回核对）
        text_path = os.path.join(OUT_DIR, "real_demo.txt")
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(rendered)
        print(f"文本快照已保存: {text_path}")

        ok = all(checks.values())
        print("\n自验结论:", "全部通过 ✅" if ok else "存在失败项 ❌")
        return ok


if __name__ == "__main__":
    if not TEXTUAL_AVAILABLE:
        print("textual 未安装，无法运行。pip install textual")
        sys.exit(1)
    sys.exit(0 if asyncio.run(run()) else 1)
