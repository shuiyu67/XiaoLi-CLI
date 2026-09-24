"""
纯 JSON 工具调用模式 测试

取代 FC：引擎不再收到 tools schema，模型按系统提示里的
{"action":"use_tool","tool":名,"args":参数} 文本输出，由 _parse_mixed_response
解析、按名分发。重点验证：
1. _loads_json / _parse_mixed_response 对 Windows 反斜杠路径健壮
2. 引擎在 tools=None 时返回纯文本（不产 _fc / tool_calls）
3. 端到端：真实 AICLI + FakeEngine，use_tool 被按名分发执行，且无 FC schema 下发
"""
import os
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ════════════════════════════════════════════════
#  1. 解析器：Windows 反斜杠路径容错
# ════════════════════════════════════════════════

@pytest.fixture
def cli():
    from xcli_core.cli_core import AICLI
    return AICLI()


class TestParseRobustness:
    def test_loads_json_tolerates_backslash_path(self, cli):
        # 模型常把 Windows 路径写成单反斜杠 → 非法 JSON 转义
        raw = r'{"action": "use_tool", "tool": "code_editor", "args": "create C:\Users\me\demo.py print(1)"}'
        data = cli._loads_json(raw)
        assert data["action"] == "use_tool"
        assert data["tool"] == "code_editor"
        # 修复后应是合法的单反斜杠路径
        assert data["args"] == r"create C:\Users\me\demo.py print(1)"

    def test_parse_mixed_extracts_use_tool_with_backslash(self, cli):
        resp = (
            '好的，我来创建文件。\n'
            r'{"action": "use_tool", "tool": "code_editor", "args": "create C:\Users\me\demo.py print(1)"}'
        )
        text, data = cli._parse_mixed_response(resp)
        assert isinstance(data, dict)
        assert data["action"] == "use_tool"
        assert data["tool"] == "code_editor"
        assert r"C:\Users\me\demo.py" in data["args"]

    def test_parse_mixed_plain_text_no_action(self, cli):
        text, data = cli._parse_mixed_response("今天天气不错")
        assert data is None
        assert "今天天气不错" in text


# ════════════════════════════════════════════════
#  2. 引擎：tools=None 返回纯文本，不产 tool_calls
# ════════════════════════════════════════════════

class TestEngineToolsNone:
    def test_openai_engine_no_tools_sent(self, monkeypatch):
        import types
        import ai_engines.openai_engine as oe

        calls = []

        def fake_post(url=None, json=None, headers=None, timeout=None, **kw):
            calls.append(dict(json))
            return types.SimpleNamespace(
                status_code=200,
                json=lambda: {"choices": [{"message": {"content": "好"}}],
                               "usage": {"prompt_tokens": 5}},
                text="{}",
            )

        monkeypatch.setattr(oe, "requests",
                             types.SimpleNamespace(post=fake_post, exceptions=oe.requests.exceptions))

        eng = oe.OpenaiAI.__new__(oe.OpenaiAI)
        eng.name = "openai"
        eng.api_key = "k"
        eng.base_url = "https://example.com/v1"
        eng.model = "gpt-4o"
        eng.max_history = 10
        eng.conversation_history = []
        eng.shared_conversation_history = None
        eng.last_prompt_tokens = None
        eng.thinking_start_marker = "<think>"
        eng.thinking_end_marker = "</think>"

        reply = eng.generate_response("hi", tools=None)
        assert reply == "好"
        assert "tools" not in calls[0], "tools=None 时不应下发 FC schema"
        assert "tool_choice" not in calls[0]


# ════════════════════════════════════════════════
#  3. 端到端：真实 AICLI + FakeEngine，use_tool 按名分发
# ════════════════════════════════════════════════

class FakeEngine:
    def __init__(self):
        self.calls = 0
        self.tools_seen = []

    @property
    def name(self):
        return "fake"

    def generate_response(self, user_input, tool_results=None, system_prompt=None, tools=None):
        self.calls += 1
        self.tools_seen.append(tools)
        assert tools is None, f"纯 JSON 模式不应下发 FC tools，实际 {tools!r}"
        if self.calls == 1:
            return ('好的，我来创建文件。\n'
                    '{"action": "use_tool", "tool": "code_editor", '
                    '"args": "create %s print(1)"}' % self._fp)
        return "已完成。"


class TestEndToEndDispatch:
    def test_use_tool_dispatched_without_fc(self):
        from xcli_core.cli_core import AICLI
        from xcli_core.safety import get_safety, MODE_UNRESTRICTED

        cli = AICLI()
        engine = FakeEngine()
        cli.current_engine = engine
        cli.tui_output_callback = lambda *a, **k: None   # 同步 TUI 分支，免动画线程
        get_safety().set_mode(MODE_UNRESTRICTED)          # 跳过交互确认，验证分发本身

        d = tempfile.mkdtemp(prefix="pj_")
        FakeEngine._fp = os.path.join(d, "demo.py")       # 原始反斜杠路径
        fp = FakeEngine._fp

        cli.process_conversation("帮我创建一个 python 文件")

        assert all(t is None for t in engine.tools_seen), "引擎不应收到任何 FC tools"
        assert engine.calls >= 2, "至少应有：首轮JSON + 工具结果续轮"
        assert os.path.exists(fp), "code_editor 应被按名分发执行并创建文件"
        assert "print(1)" in open(fp, encoding="utf-8").read()
