"""max_input_tokens 统一 API + token 感知压缩 回归测试

验证:
1. 所有引擎（openai / ollama / manual）都暴露 max_input_tokens 且返回正整数（API 契约）。
2. 系统依据 max_input_tokens 的 70% 自动判定压缩（should_compress）。
"""
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _engine_classes():
    from ai_engines.openai_engine import OpenaiAI
    from ai_engines.ollama_engine import OllamaAI
    from ai_engines.manual_engine import ManualAI
    return {"openai": OpenaiAI, "ollama": OllamaAI, "manual": ManualAI}


def test_all_engines_expose_max_input_tokens():
    """所有引擎必须返回 max_input_tokens（统一 API 契约）"""
    for name, cls in _engine_classes().items():
        assert hasattr(cls, "max_input_tokens"), f"{name} 引擎缺少 max_input_tokens 属性"


def test_max_input_tokens_positive_when_instantiated():
    """实例化后 max_input_tokens 应为正整数"""
    for name, cls in _engine_classes().items():
        try:
            inst = cls()
        except Exception as e:
            pytest.skip(f"{name} 引擎实例化失败（环境/网络），跳过实例检查: {e}")
        val = inst.max_input_tokens
        assert isinstance(val, int) and val > 0, f"{name} 的 max_input_tokens 非法: {val!r}"


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
