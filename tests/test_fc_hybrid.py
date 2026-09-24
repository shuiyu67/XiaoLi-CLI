"""
FC 混合模式（AI 自选）集成测试

验证「让 AI 自己选纯 JSON 或 FC」的接线：
1. 支持 FC 的引擎会收到下发的 tools schema（tool_choice=auto，模型自选）
2. 引擎返回 _fc JSON 时，code_editor 被按名分发执行（走 _handle_fc_response 路径）
3. 不支持 FC 的引擎（无 _fc_supported）则不收 tools，纯 JSON 照常工作
"""
import os
import sys
import json
import tempfile


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class FakeFcEngine:
    """模拟一个支持 FC 的引擎：首轮返回 _fc 调用 code_editor，次轮收尾。"""
    def __init__(self):
        self.calls = 0
        self.tools_seen = []

    @property
    def name(self):
        return "fakefc"

    def _fc_supported(self):
        return True

    def generate_response(self, user_input, tool_results=None, system_prompt=None, tools=None):
        self.calls += 1
        self.tools_seen.append(tools)
        if self.calls == 1:
            return json.dumps({
                "_fc": True,
                "tool_calls": [{
                    "id": "c1",
                    "name": "code_editor",
                    "tool": "code_editor",
                    "args": "create %s print(1)" % self._fp,
                }],
            }, ensure_ascii=False)
        return "已完成。"


class FakeNoFcEngine:
    """模拟一个不支持 FC 的引擎（无 _fc_supported）：应降级为纯 JSON。"""
    def __init__(self):
        self.calls = 0
        self.tools_seen = []

    @property
    def name(self):
        return "fakenofc"

    def generate_response(self, user_input, tool_results=None, system_prompt=None, tools=None):
        self.calls += 1
        self.tools_seen.append(tools)
        assert tools is None, f"不支持 FC 的引擎不应收到 tools，实际 {tools!r}"
        if self.calls == 1:
            return ('好的，我来创建文件。\n'
                    '{"action": "use_tool", "tool": "code_editor", '
                    '"args": "create %s print(1)"}' % self._fp)
        return "已完成。"


def _run(engine):
    from xcli_core.cli_core import AICLI
    from xcli_core.safety import get_safety, MODE_UNRESTRICTED

    cli = AICLI()
    cli.current_engine = engine
    cli.tui_output_callback = lambda *a, **k: None  # 同步 TUI 分支，免动画线程
    get_safety().set_mode(MODE_UNRESTRICTED)

    d = tempfile.mkdtemp(prefix="pj_")
    fp = os.path.join(d, "demo.py")
    engine._fp = fp
    cli.process_conversation("帮我创建一个 python 文件")
    return engine, fp


def test_fc_engine_receives_tools_and_dispatches():
    engine, fp = _run(FakeFcEngine())
    # 首轮应向支持 FC 的引擎下发 tools schema
    assert engine.tools_seen[0] is not None, "FC 引擎应收到 tools schema"
    assert isinstance(engine.tools_seen[0], list) and len(engine.tools_seen[0]) > 0
    assert any(
        t.get("function", {}).get("name") == "code_editor" for t in engine.tools_seen[0]
    ), "code_editor 应在下发的 FC 工具集中"
    # _fc 调用应被按名分发执行并真实创建文件
    assert os.path.exists(fp), "FC 路径应执行 code_editor 并创建文件"
    assert "print(1)" in open(fp, encoding="utf-8").read()
    assert engine.calls >= 2


def test_no_fc_engine_stays_pure_json():
    engine, fp = _run(FakeNoFcEngine())
    # 不支持 FC 的引擎不应收到 tools，纯 JSON 照常分发
    assert all(t is None for t in engine.tools_seen), "不支持 FC 的引擎不应收到 tools"
    assert os.path.exists(fp), "纯 JSON 路径仍应创建文件"


def test_build_fc_tools_returns_none_for_unsupported_engine():
    from xcli_core.cli_core import AICLI
    cli = AICLI()
    cli.current_engine = FakeNoFcEngine()
    assert cli._build_fc_tools("帮我创建文件") is None


def test_build_fc_tools_returns_list_for_supported_engine():
    from xcli_core.cli_core import AICLI
    cli = AICLI()
    cli.current_engine = FakeFcEngine()
    tools = cli._build_fc_tools("帮我创建 python 文件")
    assert isinstance(tools, list) and len(tools) > 0
    assert any(t.get("function", {}).get("name") == "code_editor" for t in tools)
