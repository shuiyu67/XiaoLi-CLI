"""声明式权限（allow/ask/deny）回归测试。不触真实引擎/网络。"""
from xcli_core.safety import SafetyLayer, MODE_UNRESTRICTED, MODE_NORMAL


def _new_safety(allow=None, ask=None, deny=None, mode=MODE_NORMAL):
    s = SafetyLayer()
    s.set_permissions(allow=allow, ask=ask, deny=deny)
    s.mode = mode
    return s


# ── 纯函数：规则匹配 ──

def test_match_wildcard():
    s = SafetyLayer()
    assert s._permission_match("*", "anything", "rm -rf /") is True


def test_match_exact_tool():
    s = SafetyLayer()
    assert s._permission_match("git_tools", "git_tools", "status") is True
    assert s._permission_match("git_tools", "cmd_executor", "status") is False


def test_match_tool_star():
    s = SafetyLayer()
    assert s._permission_match("git_tools:*", "git_tools", "push origin") is True


def test_match_tool_op_prefix():
    s = SafetyLayer()
    assert s._permission_match("cmd_executor:rm", "cmd_executor", "rm -rf /tmp") is True
    assert s._permission_match("cmd_executor:rm", "cmd_executor", "ls -la") is False
    # 操作词精确相等也应命中
    assert s._permission_match("git_tools:push", "git_tools", "push") is True


def test_match_empty_rule_ignored():
    s = SafetyLayer()
    assert s._permission_match("", "git_tools", "status") is False


# ── deny 最高优先级 ──

def test_deny_blocks():
    s = _new_safety(deny=["git_tools:reset"], mode=MODE_UNRESTRICTED)
    ok, msg = s.check("git_tools", "reset --hard HEAD")
    assert ok is False
    assert "deny" in msg


def test_deny_blocks_even_unrestricted():
    s = _new_safety(deny=["cmd_executor:rm"], mode=MODE_UNRESTRICTED)
    ok, _ = s.check("cmd_executor", "rm -rf /")
    assert ok is False


def test_deny_overrides_allow():
    # 同一工具同时出现在 deny 与 allow，deny 胜出
    s = _new_safety(deny=["git_tools:reset"], allow=["git_tools:reset"], mode=MODE_NORMAL)
    ok, _ = s.check("git_tools", "reset --hard")
    assert ok is False


# ── ask 强制确认 ──

def test_ask_forces_confirm():
    s = _new_safety(ask=["cmd_executor"], mode=MODE_NORMAL)
    confirmed = []
    s._ask_user_confirm = lambda *a, **k: (confirmed.append(True) or (True, "ok"))
    ok, _ = s.check("cmd_executor", "ls")
    assert ok is True
    assert confirmed == [True]


def test_ask_overrides_allow():
    # 同时 allow 与 ask，ask（确认）胜出，不会自动放行
    s = _new_safety(allow=["cmd_executor"], ask=["cmd_executor"], mode=MODE_NORMAL)
    called = []
    s._ask_user_confirm = lambda *a, **k: (called.append(True) or (True, "ok"))
    s.check("cmd_executor", "ls")
    assert called == [True]


def test_ask_works_in_unrestricted():
    s = _new_safety(ask=["git_tools:push"], mode=MODE_UNRESTRICTED)
    called = []
    s._ask_user_confirm = lambda *a, **k: (called.append(True) or (False, "no"))
    ok, _ = s.check("git_tools", "push origin master")
    assert ok is False
    assert called == [True]


# ── allow 自动放行 ──

def test_allow_auto_passes():
    s = _new_safety(allow=["git_tools:status"], mode=MODE_NORMAL)
    # 不应触发 AI 分析 / 确认
    s._ask_user_confirm = lambda *a, **k: (False, "SHOULD_NOT_BE_CALLED")
    ok, msg = s.check("git_tools", "status")
    assert ok is True
    assert msg == ""


def test_allow_no_match_falls_through():
    s = _new_safety(allow=["git_tools:status"], mode=MODE_UNRESTRICTED)
    ok, _ = s.check("cmd_executor", "ls")
    # 无规则命中 → 走默认（无限制模式直接放行）
    assert ok is True


def test_default_without_rules_unrestricted_passes():
    s = _new_safety(mode=MODE_UNRESTRICTED)
    ok, _ = s.check("file_manager", "read foo.txt")
    assert ok is True
