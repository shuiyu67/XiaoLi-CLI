"""max_input_tokens 统一 API + token 感知压缩 回归测试

验证:
1. 统一模型连接器（ModelConnection，引擎架构已删）暴露 max_input_tokens
   且返回正整数（API 契约）。
2. 系统依据 max_input_tokens 的 70% 自动判定压缩（should_compress）。
"""
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _connections():
    """按 5+3 契约构造若干模型连接（含显式限额与旧条目兜底两种）"""
    from xcli_core.model_conn import ModelConnection
    return {
        "explicit": ModelConnection("explicit", {
            "name": "explicit", "base_url": "https://api.openai.com/v1",
            "api_key": "sk", "model": "gpt-4o",
            "max_input": 128000, "max_output": 4096,
        }),
        "legacy": ModelConnection("legacy", {
            "name": "legacy", "base_url": "https://api.deepseek.com/v1",
            "api_key": "sk", "model": "deepseek-chat",
        }),
        "local": ModelConnection("local", {
            "name": "local", "base_url": "http://localhost:11434/v1",
            "api_key": "", "model": "gemma4:31b",
            "max_input": 32768, "max_output": 4096,
        }),
    }


def test_model_connection_exposes_max_input_tokens():
    """统一连接器必须返回 max_input_tokens（API 契约）"""
    for name, conn in _connections().items():
        assert hasattr(conn, "max_input_tokens"), f"{name} 缺少 max_input_tokens 属性"


def test_max_input_tokens_positive():
    """max_input_tokens 应为正整数（显式限额优先，旧条目兜底查表）"""
    for name, conn in _connections().items():
        val = conn.max_input_tokens
        assert isinstance(val, int) and val > 0, f"{name} 的 max_input_tokens 非法: {val!r}"
    # 显式限额必须优先
    assert _connections()["explicit"].max_input_tokens == 128000
    assert _connections()["local"].max_input_tokens == 32768


def _mgr():
    from xcli_core.memory import MemoryManager
    return MemoryManager(project_dir=PROJECT_ROOT)


def _conv(n):
    return [{"role": "user", "content": f"msg {i}"} for i in range(n)]


def test_should_compress_token_aware_triggers_at_70pct():
    mgr = _mgr()
    # 7000 / 10000 = 0.7 >= 0.7 → 触发
    assert mgr.should_compress(_conv(5), prompt_tokens=7000, max_input_tokens=10000, ratio=0.7) is True


def test_should_compress_token_aware_below_threshold():
    mgr = _mgr()
    # 6000 / 10000 = 0.6 < 0.7 → 不触发（消息数也未超阈值）
    assert mgr.should_compress(_conv(5), prompt_tokens=6000, max_input_tokens=10000, ratio=0.7) is False


def test_should_compress_message_count_fallback():
    mgr = _mgr()
    # 无 token 信息，仅消息数 > 50 → 兜底触发
    assert mgr.should_compress(_conv(60)) is True
    assert mgr.should_compress(_conv(10)) is False
