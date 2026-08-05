"""Plan 模式（只读规划 → 审批 → 执行）回归测试。

全程不实例化 AICLI（避免加载真实引擎/插件/进程保护/网络），
通过伪造 cli 对象与轻量 SimpleNamespace 验证核心逻辑。
"""
import types

import pytest

from xcli_core.safety import (
    get_safety,
    plan_is_write_operation,
    PLAN_WRITE_RULES,
)


# ── 纯函数：写操作判定 ──

def test_write_rules_known_and_unknown():
    # 整类拦截
    assert plan_is_write_operation("cmd_executor", "ls -la") is True
    assert plan_is_write_operation("browser_auto", "navigate https://x") is True
    assert plan_is_write_operation("network_tools", "ping 1.1.1.1") is True
    assert plan_is_write_operation("scheduler", "add 1h do") is True
    # 整类放行
    assert plan_is_write_operation("tool_search", "code_editor") is False
    assert plan_is_write_operation("ai_search", "python 教程") is False
    assert plan_is_write_operation("code_search", "find . kw") is False
    # 未知工具：保守拦截
    assert plan_is_write_operation("mystery_tool", "anything") is True


def test_code_editor_readonly_allowed_write_blocked():
    assert plan_is_write_operation("code_editor", "read_range a.py 1 10") is False
    assert plan_is_write_operation("code_editor", "find . kw") is False
    assert plan_is_write_operation("code_editor", "diff a.py") is False
    assert plan_is_write_operation("code_editor", "edit a.py old <<<>>> new") is True
    assert plan_is_write_operation("code_editor", "write a.py content") is True
    assert plan_is_write_operation("code_editor", "append a.py line") is True
    assert plan_is_write_operation("code_editor", "multi a.py [...]") is True
    assert plan_is_write_operation("code_editor", "insert a.py 3 line") is True
    assert plan_is_write_operation("code_editor", "delete_lines a.py 1 2") is True


def test_git_readonly_allowed_write_blocked():
    assert plan_is_write_operation("git_tools", "status") is False
    assert plan_is_write_operation("git_tools", "log --oneline 10") is False
    assert plan_is_write_operation("git_tools", "diff") is False
    assert plan_is_write_operation("git_tools", "show HEAD") is False
    assert plan_is_write_operation("git_tools", "branch") is False  # 仅列出
    assert plan_is_write_operation("git_tools", "commit 修复") is True
    assert plan_is_write_operation("git_tools", "smart-commit") is True  # 后缀命中
    assert plan_is_write_operation("git_tools", "push") is True
    assert plan_is_write_operation("git_tools", "checkout main") is True
    assert plan_is_write_operation("git_tools", "branch -d old") is True
    assert plan_is_write_operation("git_tools", "reset --hard") is True
    assert plan_is_write_operation("git_tools", "fetch origin") is True


def test_file_manager_sub_agent_auto_engineer():
    assert plan_is_write_operation("file_manager", "list .") is False
    assert plan_is_write_operation("file_manager", "read a.txt") is False
    assert plan_is_write_operation("file_manager", "search kw") is False
    assert plan_is_write_operation("file_manager", "write a.txt x") is True
    assert plan_is_write_operation("file_manager", "delete a.txt") is True

    assert plan_is_write_operation("sub_agent", "list") is False
    assert plan_is_write_operation("sub_agent", "status") is False
    assert plan_is_write_operation("sub_agent", "result 12") is False
    assert plan_is_write_operation("sub_agent", "run 任务") is True
    assert plan_is_write_operation("sub_agent", "dispatch 任务") is True

    assert plan_is_write_operation("auto_engineer", "lint") is False  # 只读
    assert plan_is_write_operation("auto_engineer", "metrics") is False
    assert plan_is_write_operation("auto_engineer", "test") is True
    assert plan_is_write_operation("auto_engineer", "build") is True


# ── safety.check 在 plan 模式下的拦截 ──

@pytest.fixture
def safety_with_fake_cli():
    safety = get_safety()
    saved_cli = safety.cli
    saved_mode = safety.mode
    fake_cli = types.SimpleNamespace(plan_mode=True)
    safety.set_cli(fake_cli)
    yield safety
    safety.set_cli(saved_cli)
    safety.set_mode(saved_mode)


def test_plan_mode_blocks_write_at_safety_layer(safety_with_fake_cli):
    s = safety_with_fake_cli
    allowed, msg = s.check("code_editor", "edit a.py x <<<>>> y")
    assert allowed is False
    assert "PLAN" in msg

    allowed, _ = s.check("git_tools", "commit 修复")
    assert allowed is False

    allowed, _ = s.check("cmd_executor", "rm -rf /")
    assert allowed is False


def test_plan_mode_allows_readonly_at_safety_layer(safety_with_fake_cli):
    s = safety_with_fake_cli
    allowed, _ = s.check("code_editor", "read_range a.py 1 10")
    assert allowed is True
    allowed, _ = s.check("tool_search", "code_editor")
    assert allowed is True
    allowed, _ = s.check("git_tools", "status")
    assert allowed is True


def test_normal_mode_does_not_plan_block():
    """非 plan 模式：safety.check 不被 plan 逻辑拦截（用无限制模式避免触发 AI 分析）。"""
    safety = get_safety()
    saved_cli = safety.cli
    saved_mode = safety.mode
    fake_cli = types.SimpleNamespace(plan_mode=False)
    safety.set_cli(fake_cli)
    safety.set_mode(0)  # MODE_UNRESTRICTED：直接放行，不消耗 AI
    try:
        allowed, _ = safety.check("code_editor", "write a.py x")
        assert allowed is True
        allowed, _ = safety.check("cmd_executor", "rm -rf /")
        assert allowed is True
    finally:
        safety.set_cli(saved_cli)
        safety.set_mode(saved_mode)


# ── system prompt 注入 ──

def test_build_system_prompt_injects_plan():
    from xcli_core.cli_core import AICLI, PLAN_MODE_SYSTEM_APPEND
    fake = types.SimpleNamespace(
        plan_mode=True,
        liugin_manager=types.SimpleNamespace(tools=[]),
        memory_manager=None,
    )
    prompt = AICLI._build_system_prompt(fake)
    assert "PLAN" in prompt
    assert "实施计划" in prompt
    assert PLAN_MODE_SYSTEM_APPEND in prompt


def test_build_system_prompt_no_plan_when_off():
    from xcli_core.cli_core import AICLI
    fake = types.SimpleNamespace(
        plan_mode=False,
        liugin_manager=types.SimpleNamespace(tools=[]),
        memory_manager=None,
    )
    prompt = AICLI._build_system_prompt(fake)
    assert "实施计划" not in prompt


# ── 命令 handler 状态转换 ──

def _fake_for_plan():
    calls = {"process": [], "autosave": 0, "sync": 0}
    fake = types.SimpleNamespace(
        plan_mode=False,
        current_plan="",
        process_conversation=lambda x: calls["process"].append(x),
        _autosave_session=lambda: calls.__setitem__("autosave", calls["autosave"] + 1),
        _sync_current_plan=lambda: calls.__setitem__("sync", calls["sync"] + 1),
    )
    return fake, calls


def test_handle_plan_command_enters_mode_with_task():
    from xcli_core.cli_core import AICLI
    fake, calls = _fake_for_plan()
    AICLI.handle_plan_command(fake, "重构缓存模块")
    assert fake.plan_mode is True
    assert calls["process"] == ["重构缓存模块"]
    assert calls["autosave"] == 1
    assert calls["sync"] == 1


def test_handle_plan_command_enters_mode_without_task():
    from xcli_core.cli_core import AICLI
    fake, calls = _fake_for_plan()
    AICLI.handle_plan_command(fake, "")
    assert fake.plan_mode is True
    assert calls["process"] == []  # 无任务不主动调研


def test_handle_plan_command_off_exits():
    from xcli_core.cli_core import AICLI
    fake, calls = _fake_for_plan()
    fake.plan_mode = True
    AICLI.handle_plan_command(fake, "off")
    assert fake.plan_mode is False
    assert calls["process"] == []


def test_handle_build_command_executes_plan():
    from xcli_core.cli_core import AICLI
    fake, calls = _fake_for_plan()
    fake.plan_mode = True
    fake.current_plan = "## 实施计划\n1. 改 a.py\n2. 改 b.py"
    AICLI.handle_build_command(fake)
    assert fake.plan_mode is False
    assert len(calls["process"]) == 1
    assert "已批准的实施计划" in calls["process"][0]
    assert "## 实施计划" in calls["process"][0]


def test_handle_build_command_no_plan_warns():
    from xcli_core.cli_core import AICLI
    fake, calls = _fake_for_plan()
    fake.plan_mode = False
    fake.current_plan = ""
    AICLI.handle_build_command(fake)
    assert calls["process"] == []  # 无计划不执行


def test_sync_current_plan_captures_last_assistant():
    from xcli_core.cli_core import AICLI
    fake = types.SimpleNamespace(
        plan_mode=True,
        current_plan="",
        shared_conversation_history=[
            {"role": "user", "content": "任务"},
            {"role": "assistant", "content": "调研中..."},
            {"role": "tool", "content": "结果"},
            {"role": "assistant", "content": "## 实施计划\n1. do x"},
        ],
    )
    AICLI._sync_current_plan(fake)
    assert "实施计划" in fake.current_plan


def test_sync_current_plan_noop_when_not_plan():
    from xcli_core.cli_core import AICLI
    fake = types.SimpleNamespace(
        plan_mode=False,
        current_plan="unchanged",
        shared_conversation_history=[{"role": "assistant", "content": "x"}],
    )
    AICLI._sync_current_plan(fake)
    assert fake.current_plan == "unchanged"
