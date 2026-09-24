"""TUI 全按钮严格自查：每个快捷键/命令连按 2 次，记录调用次数/异常/后置状态。

判定"按一次就废"：第一次有调用、第二次无调用或抛异常或后置状态卡死
（is_generating 卡 True / leader_pending 卡 True / screen_stack 不回落）。
"""
import asyncio
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeCli:
    engines = {'openai': object(), 'ollama': object(), 'manual': object()}
    liugin_manager = type('T', (), {'tools': [
        {'name': 'code_editor', 'description': 'x'},
        {'name': 'py_detect', 'description': 'x'}]})()
    shared_conversation_history = []
    plan_mode = False
    current_plan = ''
    config = {}
    current_engine = None
    liugin_commands = {}
    tui_output_callback = None
    session_manager = None
    _switch_to_cli = False

    def get_current_engine_name(self):
        return 'openai'

    def switch_engine(self, n):
        pass

    def _handle_cli_command(self, cmd):
        return True

    def _sync_current_plan(self):
        pass

    def handle_build_command(self):
        pass

    def process_conversation(self, s):
        pass


calls = {}
errs = []


def wrap_actions(app):
    for name in dir(app):
        if name.startswith('action_') and callable(getattr(app, name)):
            orig = getattr(app, name)

            def mk(n, f):
                def g(*a, **k):
                    calls[n] = calls.get(n, 0) + 1
                    try:
                        return f(*a, **k)
                    except Exception as e:
                        errs.append((n, repr(e)))
                        traceback.print_exc()
                return g
            setattr(app, name, mk(name, orig))
    # exit 打桩：审计中 /quit 等不得真杀 App（否则后续按键全挂死）
    def fake_exit(*a, **k):
        calls['action_exit(桩)'] = calls.get('action_exit(桩)', 0) + 1
    app.exit = fake_exit


async def main():
    from xcli_core.tui import XiaoliTUI
    app = XiaoliTUI(FakeCli())
    wrap_actions(app)
    problems = []

    def snap_state():
        return {
            'stack': len(app.screen_stack),
            'gen': bool(app.is_generating),
            'leader': bool(app._leader_pending),
        }

    async def press2(*keys, label=''):
        """按同一组键两次，比较两次的调用增量与状态回落"""
        print(f"[按键] {label or keys}", flush=True)
        # 导航键语义 = 输入框未聚焦时生效；聚焦时打字是正确行为，逐轮先失焦
        nav_keys = {'j', 'k', 'i', '1', '2', '3', '4', 'ctrl+d', 'ctrl+u'}
        first_hit = 0
        first_delta = {}
        for rnd in (1, 2):
            if set(keys) & nav_keys:
                try:
                    app.screen.set_focus(None)
                    await pilot.pause(0.1)
                except Exception:
                    pass
            before = dict(calls)
            s0 = snap_state()
            await pilot.press(*keys)
            await pilot.pause(0.25)
            s1 = snap_state()
            delta = {k: v - before.get(k, 0) for k, v in calls.items() if v - before.get(k, 0)}
            hit = sum(delta.values())
            if rnd == 1:
                first_hit = hit
                first_delta = delta
            else:
                if hit == 0 and first_hit > 0:
                    problems.append(f"[一次就废] {label or keys}: 第1次触发 {first_delta}，第2次 0")
                elif hit == 0 and first_hit == 0:
                    problems.append(f"[完全没反应] {label or keys}: 两次都 0 调用")
            # 状态卡死检查
            if s1['gen'] and not s0['gen'] and 'send_message' not in label:
                # 生成态由 send/命令触发；其他动作不该卡生成态
                if not any(k in first_delta for k in ('action_send_message',)):
                    problems.append(f"[状态卡死] {label or keys}: is_generating 卡 True")
            if s1['leader']:
                problems.append(f"[状态卡死] {label or keys}: leader_pending 卡 True")
        # 模态回落检查
        s = snap_state()
        if s['stack'] > 1:
            problems.append(f"[界面卡住] {label or keys}: screen_stack={s['stack']}（模态没关掉）")
            # 强制清场救回后续测试
            try:
                while len(app.screen_stack) > 1:
                    app.screen.dismiss(None)
            except Exception:
                pass

    async with app.run_test(size=(120, 38)) as pilot:
        await pilot.pause(0.4)

        # ── 功能键（全部 ×2）──
        await press2('f1', label='F1 侧栏')
        await press2('f2', label='F2 换模型')
        await press2('f4', label='F4 工具折叠')
        await press2('ctrl+o', label='Ctrl+O PLAN')
        await press2('ctrl+o', label='Ctrl+O PLAN 回关')
        await press2('ctrl+n', label='Ctrl+N 新对话')
        await press2('ctrl+l', label='Ctrl+L 清屏')
        await press2('ctrl+p', 'escape', label='Ctrl+P 面板开关')
        await press2('ctrl+x', 'escape', label='Ctrl+X leader 取消')
        await press2('ctrl+x', 'n', label='Ctrl+X N 新会话')
        await press2('ctrl+x', 'x', label='Ctrl+X X 导出')
        await press2('ctrl+x', 'l', label='Ctrl+X L 会话')
        await press2('ctrl+x', '?', label='Ctrl+X ? 帮助')
        await press2('ctrl+space', label='Ctrl+Space 焦点切换')
        await press2('ctrl+f', label='Ctrl+F 翻页')
        await press2('ctrl+b', label='Ctrl+B 翻页')
        await press2('ctrl+d', label='Ctrl+D 半页')
        await press2('ctrl+u', label='Ctrl+U 半页')
        await press2('j', label='j 滚动')
        await press2('k', label='k 滚动')
        await press2('i', label='i 聚焦')
        await press2('1', label='1 侧栏页')
        await press2('2', label='2 侧栏页')
        await press2('3', label='3 侧栏页')
        await press2('4', label='4 侧栏页')
        await press2('f3', label='F3 历史')

        # ── 命令 ×2（走 _handle_command 全表）──
        ta = app.query_one('#user-input')
        for cmd in ['/help', '/clear', '/status', '/tools', '/engines', '/about',
                    '/vim', '/sound', '/palette', '/plan', '/plan off',
                    '/build', '/sessions', '/manual', '/snapshot']:
            calls_before = dict(calls)
            for _ in range(2):
                try:
                    app._handle_command(cmd)
                except Exception as e:
                    errs.append((cmd, repr(e)))
                await pilot.pause(0.15)
            delta = sum(v - calls_before.get(k, 0) for k, v in calls.items()) + 1  # +1: _handle_command 自身不计
            s = snap_state()
            if s['stack'] > 1:
                problems.append(f"[界面卡住] 命令 {cmd}: screen_stack={s['stack']}")
                try:
                    while len(app.screen_stack) > 1:
                        app.screen.dismiss(None)
                except Exception:
                    pass
            if s['leader']:
                problems.append(f"[状态卡死] 命令 {cmd}: leader_pending 卡 True")

        # ── 面板专项：↑↓ 滚动跟随 + 二次打开（覆盖层 API）──
        from xcli_core.tui import CommandPalette
        for rnd in (1, 2):
            await pilot.press('ctrl+p')
            await pilot.pause(0.3)
            pal = app.query_one(CommandPalette)
            if not pal.is_open():
                problems.append(f"[面板] 第{rnd}次: ctrl+p 未打开覆盖层")
                break
            # 连按 25 次 down（越过 20 条窗口）
            for _ in range(25):
                await pilot.press('down')
            await pilot.pause(0.3)
            if pal._cursor < 20:
                problems.append(f"[面板] 第{rnd}次: down×25 后 cursor={pal._cursor}（没走动/越界回绕异常）")
            sel = [w for w in pal._pool if 'pal-sel' in w.classes]
            if not sel:
                problems.append(f"[面板] 第{rnd}次: 无选中高亮")
            await pilot.press('enter')
            await pilot.pause(0.3)
            if pal.is_open():
                problems.append(f"[面板] 第{rnd}次: 回车执行后覆盖层未关闭")
                pal.close(None)

        print("\n===== 调用统计 =====", flush=True)
        for k in sorted(calls):
            print(f"  {k}: {calls[k]}", flush=True)
        print("\n===== handler 异常 =====", flush=True)
        for n, e in errs:
            print(f"  {n}: {e}", flush=True)
        print("\n===== 问题清单 =====", flush=True)
        if not problems and not errs:
            print("  全部通过", flush=True)
        for p in problems:
            print("  " + p, flush=True)
        print(f"\n结论: {len(problems)} 个问题, {len(errs)} 个异常", flush=True)


asyncio.run(asyncio.wait_for(main(), timeout=240))
