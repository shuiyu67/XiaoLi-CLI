"""Provider 抽象层测试：预设、resolve、消息/工具转换、汇总。不触网、不读真实 config。"""
import os
import sys


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xcli_core.provider_router import (
    PROVIDER_PRESETS, list_providers, resolve_provider,
    convert_messages, convert_tools, provider_summary,
)


def test_presets_exist():
    for name in ["openai", "anthropic", "google", "deepseek", "xunfei", "ollama"]:
        assert name in PROVIDER_PRESETS
    assert "openai" in list_providers()


def test_resolve_default_no_key():
    r = resolve_provider("openai")
    assert r["name"] == "openai"
    assert r["base_url"] == "https://api.openai.com/v1"
    assert r["protocol"] == "openai"
    # 无环境变量无配置 → api_key 空
    assert r["api_key"] == ""


def test_resolve_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
    r = resolve_provider("openai")
    assert r["api_key"] == "sk-test-123"


def test_resolve_from_cfg_overrides_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    r = resolve_provider("openai", {"openai": {"api_key": "sk-cfg", "model": "gpt-4o-mini"}})
    assert r["api_key"] == "sk-cfg"
    assert r["model"] == "gpt-4o-mini"


def test_resolve_anthropic_headers():
    r = resolve_provider("anthropic", {"anthropic": {"api_key": "ak"}})
    assert r["protocol"] == "anthropic"
    assert r["headers"].get("anthropic-version") == "2023-06-01"


def test_resolve_google_query_header():
    r = resolve_provider("google", {"google": {"api_key": "gk"}})
    assert r["headers"].get("x-goog-api-key") == "gk"


def test_resolve_unknown():
    assert resolve_provider("not-a-provider") == {}


# ── 消息转换 ──
OPENAI_MSGS = [
    {"role": "system", "content": "你是助手"},
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "在的", "tool_calls": [{"id": "c1"}]},
    {"role": "tool", "content": "结果", "name": "calc"},
]


def test_convert_openai_keeps():
    out = convert_messages("openai", OPENAI_MSGS)
    assert out[0]["role"] == "system"
    assert out[1]["content"] == "你好"
    assert out[2]["tool_calls"] == [{"id": "c1"}]


def test_convert_anthropic_strips_system_blocks():
    out = convert_messages("anthropic", OPENAI_MSGS)
    roles = [m["role"] for m in out]
    assert "system" not in roles
    assert out[0]["content"][0]["type"] == "text"
    assert out[-1]["role"] == "user"  # tool 角色映射到 user


def test_convert_google_uses_parts():
    out = convert_messages("google", OPENAI_MSGS)
    roles = [m["role"] for m in out]
    assert "system" not in roles
    assert out[0]["parts"][0]["text"] == "你好"
    assert out[-1]["role"] == "user"


def test_convert_multimodal_content_blocks():
    msgs = [{"role": "user", "content": [
        {"type": "text", "text": "看图"},
        {"type": "image", "image_url": {"url": "x"}},
    ]}]
    oai = convert_messages("openai", msgs)
    assert oai[0]["content"] == "看图"  # 多模态 → 文本拼接
    ant = convert_messages("anthropic", msgs)
    assert ant[0]["content"][0]["type"] == "text"
    assert ant[0]["content"][1]["type"] == "image"


# ── 工具转换 ──
TOOLS = [{"type": "function", "function": {
    "name": "search", "description": "搜索", "parameters": {"type": "object", "properties": {}}}}]


def test_convert_tools_openai_passthrough():
    assert convert_tools("openai", TOOLS) == TOOLS


def test_convert_tools_anthropic_schema():
    out = convert_tools("anthropic", TOOLS)
    assert out[0]["name"] == "search"
    assert out[0]["input_schema"] == {"type": "object", "properties": {}}


def test_convert_tools_google_declarations():
    out = convert_tools("google", TOOLS)
    assert "functionDeclarations" in out[0]
    assert out[0]["functionDeclarations"][0]["name"] == "search"


# ── 汇总 ──
def test_provider_summary_unconfigured():
    s = provider_summary("anthropic")
    assert s["name"] == "anthropic"
    assert s["configured"] is False
    assert s["protocol"] == "anthropic"


def test_provider_summary_configured(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_BASE", "ignored")
    s = provider_summary("anthropic", {"anthropic": {"api_key": "x"}})
    assert s["configured"] is True
