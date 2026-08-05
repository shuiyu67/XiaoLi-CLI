"""启动输出瘦身 + FC 能力探测缓存 回归测试

覆盖两件事：
1. 无 FC 能力的模型（如讯飞 xophunyuan7bmt）被 500 打回后会被记住，
   之后不再每次白撞一发 500 试探。
2. 启动输出从 117 行折叠到 10 行，详细日志改由 --verbose 召唤。
"""
import contextlib
import io
import json
import os
import sys
import types

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

BASE_URL = "https://maas-api.cn-huabei-1.xf-yun.com/v2"
MODEL = "xophunyuan7bmt"

TOOL = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "读文件",
        "parameters": {"type": "object", "properties": {}},
    },
}

OK_BODY = {"choices": [{"message": {"content": "好"}}], "usage": {"prompt_tokens": 12}}
ERR_500 = {"error": {"message": "xunfei response error: sid: xxx msg: RequestParamsError:Invalid Params"}}


@pytest.fixture
def fc(tmp_path):
    """把 FC 缓存文件隔离到临时目录，避免污染真实运行时缓存"""
    from xcli_core import fc_tools

    old_file, old_mem = fc_tools._FC_CACHE_FILE, fc_tools._fc_cache
    fc_tools._FC_CACHE_FILE = str(tmp_path / ".fc_support.json")
    fc_tools._fc_cache = None
    try:
        yield fc_tools
    finally:
        fc_tools._FC_CACHE_FILE, fc_tools._fc_cache = old_file, old_mem


class FakeResp:
    def __init__(self, code, payload):
        self.status_code = code
        self._payload = payload
        self.text = json.dumps(payload, ensure_ascii=False)

    def json(self):
        return self._payload


def make_engine(model=MODEL):
    """不走 __init__（会读配置/连网），直接摆一个可用实例"""
    import ai_engines.openai_engine as oe

    eng = oe.OpenaiAI.__new__(oe.OpenaiAI)
    eng.name = "openai"
    eng.cli = None
    eng.api_key = "k"
    eng.base_url = BASE_URL
    eng.model = model
    eng.max_history = 10
    eng.conversation_history = []
    eng.shared_conversation_history = None
    eng.last_prompt_tokens = None
    eng.thinking_start_marker = "<think>"
    eng.thinking_end_marker = "</think>"
    return eng


@pytest.fixture
def http(monkeypatch):
    """替换 openai_engine 里的 requests，记录每次请求体"""
    import ai_engines.openai_engine as oe

    calls = []

    def install(responder):
        def fake_post(url=None, json=None, headers=None, timeout=None, **kw):
            calls.append(dict(json))
            return responder(json)

        monkeypatch.setattr(
            oe, "requests",
            types.SimpleNamespace(post=fake_post, exceptions=oe.requests.exceptions),
        )
        return calls

    install.calls = calls
    return install


# ══════════════════════════════════════
#  1. FC 能力探测缓存
# ══════════════════════════════════════

class TestFCCache:
    def test_default_assume_supported(self, fc):
        assert fc.supports_fc(BASE_URL, MODEL) is True

    def test_mark_and_remember(self, fc):
        assert fc.mark_fc_unsupported(BASE_URL, MODEL) is True
        assert fc.supports_fc(BASE_URL, MODEL) is False

    def test_repeat_mark_not_reported(self, fc):
        fc.mark_fc_unsupported(BASE_URL, MODEL)
        # 第二次返回 False，调用方据此不重复刷屏提示
        assert fc.mark_fc_unsupported(BASE_URL, MODEL) is False

    def test_persist_across_restart(self, fc):
        fc.mark_fc_unsupported(BASE_URL, MODEL)
        assert os.path.exists(fc._FC_CACHE_FILE)
        fc._fc_cache = None  # 模拟进程重启
        assert fc.supports_fc(BASE_URL, MODEL) is False

    def test_other_model_unaffected(self, fc):
        fc.mark_fc_unsupported(BASE_URL, MODEL)
        assert fc.supports_fc(BASE_URL, "spark-4.0-ultra") is True

    def test_trailing_slash_normalized(self, fc):
        fc.mark_fc_unsupported(BASE_URL, MODEL)
        assert fc.supports_fc(BASE_URL + "/", MODEL) is False

    def test_get_cache_returns_copy(self, fc):
        fc.mark_fc_unsupported(BASE_URL, MODEL)
        snap = fc.get_fc_cache()
        assert isinstance(snap, dict) and snap is not fc._fc_cache

    def test_reset(self, fc):
        fc.mark_fc_unsupported(BASE_URL, MODEL)
        assert fc.reset_fc_cache() == 1
        assert fc.supports_fc(BASE_URL, MODEL) is True

    def test_reset_single_entry(self, fc):
        fc.mark_fc_unsupported(BASE_URL, MODEL)
        fc.mark_fc_unsupported(BASE_URL, "other")
        assert fc.reset_fc_cache(BASE_URL, MODEL) == 1
        assert fc.supports_fc(BASE_URL, MODEL) is True
        assert fc.supports_fc(BASE_URL, "other") is False

    def test_corrupted_file_does_not_crash(self, fc):
        with open(fc._FC_CACHE_FILE, "w", encoding="utf-8") as f:
            f.write("{ not json")
        fc._fc_cache = None
        assert fc.supports_fc(BASE_URL, MODEL) is True


# ══════════════════════════════════════
#  2. openai 引擎接线（假 HTTP，不动真实接口）
# ══════════════════════════════════════

class TestOpenAIDegrade:
    def test_first_call_degrades_and_caches(self, fc, http):
        calls = http(lambda body: FakeResp(500, ERR_500) if "tools" in body else FakeResp(200, OK_BODY))

        reply = make_engine().generate_response("说'好'", tools=[TOOL])

        assert len(calls) == 2, f"应为 带tools→500 + 降级重试，实际 {len(calls)} 次"
        assert "tools" in calls[0]
        assert "tools" not in calls[1] and "tool_choice" not in calls[1]
        assert reply == "好"
        assert fc.supports_fc(BASE_URL, MODEL) is False, "降级成功后应记住该模型不支持 FC"

    def test_second_call_skips_probe(self, fc, http):
        fc.mark_fc_unsupported(BASE_URL, MODEL)
        calls = http(lambda body: FakeResp(500, ERR_500) if "tools" in body else FakeResp(200, OK_BODY))

        reply = make_engine().generate_response("再说一次", tools=[TOOL])

        assert len(calls) == 1, f"已知不支持 FC 时不该再撞 500，实际 {len(calls)} 次"
        assert "tools" not in calls[0]
        assert reply == "好"

    def test_unmarked_model_still_sends_tools(self, fc, http):
        calls = http(lambda body: FakeResp(200, OK_BODY))

        make_engine(model="gpt-4o").generate_response("hi", tools=[TOOL])

        assert len(calls) == 1 and "tools" in calls[0]

    def test_tools_payload_is_pure_official_format(self, fc, http):
        calls = http(lambda body: FakeResp(200, OK_BODY))

        make_engine(model="gpt-4o").generate_response("hi", tools=[TOOL])

        tool = calls[0]["tools"][0]
        assert tool.get("type") == "function"
        assert set(tool.keys()) == {"type", "function"}
        assert calls[0].get("tool_choice") == "auto"

    def test_failed_degrade_does_not_cache(self, fc, http):
        http(lambda body: FakeResp(500, ERR_500))

        reply = make_engine().generate_response("hi", tools=[TOOL])

        assert fc.supports_fc(BASE_URL, MODEL) is True, "降级也失败说明不是 FC 的锅，不能误判"
        assert "API 调用失败" in str(reply)


# ══════════════════════════════════════
#  3. 启动输出瘦身
# ══════════════════════════════════════

def _read(*parts):
    with open(os.path.join(PROJECT_ROOT, *parts), encoding="utf-8") as f:
        return f.read()


class TestStartupSlim:
    def test_no_21_line_help_dump(self):
        src = _read("xcli_core", "cli_core.py")
        run_body = src.split("    def run(self):", 1)[1].split("    def _get_code_editor_plugin", 1)[0]
        assert run_body.count("输入 '/") == 0, "启动不该再逐条打印命令说明"
        assert "/help 全部命令" in run_body

    def test_logo_is_opt_in(self):
        src = _read("xcli_core", "cli_core.py")
        assert "'--logo' in sys.argv" in src
        assert "--banner" in src

    def test_quick_commands_moved_into_help(self):
        from xcli_core import cli_display

        names = [n for n in dir(cli_display) if n.endswith("Mixin")]
        assert names, "cli_display 里应有 Mixin 类"
        cls = getattr(cli_display, names[0])
        assert hasattr(cls, "show_quick_commands")

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cls.show_quick_commands(cls.__new__(cls))
        out = buf.getvalue()

        assert "/fc" in out and "/diff" in out, "速查表要覆盖新命令"
        assert 18 <= len(out.strip().splitlines()) <= 34

    def test_diff_mode_remembered(self):
        src = _read("xcli_core", "cli_core.py")
        assert "set_system_config('diff_popup_mode'" in src
        assert "if saved is not None:" in src, "存过就不该再问第二次"

    def test_new_commands_registered(self):
        src = _read("xcli_core", "cli_core.py")
        assert "user_input.startswith('/diff')" in src
        assert "user_input.startswith('/fc')" in src


# ══════════════════════════════════════
#  4. 启动噪音折叠到 --verbose
# ══════════════════════════════════════

class TestVerboseGate:
    def test_loading_chatter_is_gated(self):
        base_src = _read("xcli_core", "cli_base.py")
        utm_src = _read("unified_tool_manager.py")
        assert 'vprint(f"{Fore.GREEN}已注册插件命令' in base_src
        assert 'vprint(f"{Fore.GREEN}已加载AI引擎' in base_src
        assert 'vprint(f"{Fore.GREEN}已加载 Skill' in utm_src
        assert "已加载 {len(self._tools)} 个工具" in utm_src, "工具加载应汇总成一行"

    @pytest.mark.parametrize("argv,env,expected", [
        (["ai_cli.py"], None, False),
        (["ai_cli.py", "--verbose"], None, True),
        (["ai_cli.py", "-v"], None, True),
        (["ai_cli.py"], "1", True),
        (["ai_cli.py"], "0", False),
    ])
    def test_is_verbose(self, monkeypatch, argv, env, expected):
        from xcli_core import verbose as vb

        monkeypatch.setattr(sys, "argv", argv)
        if env is None:
            monkeypatch.delenv("XCLI_VERBOSE", raising=False)
        else:
            monkeypatch.setenv("XCLI_VERBOSE", env)
        assert vb.is_verbose() is expected

    def test_vprint_silent_by_default(self, monkeypatch, capsys):
        from xcli_core import verbose as vb

        monkeypatch.setattr(sys, "argv", ["ai_cli.py"])
        monkeypatch.delenv("XCLI_VERBOSE", raising=False)
        vb.vprint("should not appear")
        assert capsys.readouterr().out == ""

        monkeypatch.setattr(sys, "argv", ["ai_cli.py", "-v"])
        vb.vprint("should appear")
        assert "should appear" in capsys.readouterr().out
