"""
回归测试：ollama 必须惰性导入。

原因：ollama SDK 在 import 时会触发平台探测（platform.machine() → WMI），
在部分沙箱/未安装 ollama 的环境会卡死或拖慢启动。
修复后：
- ai_engines/ollama_engine 模块顶层不得 import ollama；
- OllamaAI.__init__ 不得急切点服务（is_service_running 改为惰性 property），
  只有真正选用 ollama 引擎时才 import ollama。

本测试只 import 模块、不构造 AICLI（避免触发 LSP 连接等环境依赖），
因此可在任意沙箱稳定运行，专门守住「ollama 惰性导入」这一改动。
"""
import sys
import types
import builtins

PROJECT_ROOT = sys.path[0] if sys.path else ""
# 兜底：确保能找到仓库根
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def test_ollama_engine_module_import_is_lazy():
    """import ai_engines.ollama_engine 不应触发 import ollama。"""
    imported = []
    real_import = builtins.__import__

    def traced(name, *a, **k):
        if name == "ollama" or name.startswith("ollama."):
            imported.append(name)
        return real_import(name, *a, **k)

    builtins.__import__ = traced
    try:
        import ai_engines.ollama_engine as oe
        # 旧顶层 ollama_client 应已移除
        assert not hasattr(oe, "ollama_client"), \
            "旧的顶层 ollama_client 应已移除，改为惰性 _ollama() getter"
        # 应有惰性 getter
        assert hasattr(oe, "_ollama"), "应有惰性 _ollama() getter"
        # 模块被 import 后不应已有 ollama 真身
        assert oe._ollama_import_tried is False, \
            "模块加载完成时尚不应尝试 import ollama（惰性）"
    finally:
        builtins.__import__ = real_import

    assert imported == [], \
        f"import ai_engines.ollama_engine 不应触发 import ollama，实际 {imported}"


def test_ollama_sdk_only_imported_on_use():
    """调用 _ollama() 才真正 import ollama；未调用前仍是惰性。"""
    # 用一个假 ollama 顶替，避免真实 SDK / WMI；只验证「调用时才触发」
    fake = types.ModuleType("ollama")
    fake.list = lambda *a, **k: []
    fake.chat = lambda *a, **k: {}
    fake.pull = lambda *a, **k: []
    sys.modules["ollama"] = fake

    import ai_engines.ollama_engine as oe
    assert oe._ollama_import_tried is False
    client = oe._ollama()          # 首次调用
    assert oe._ollama_import_tried is True
    assert client is fake          # 取回的是我们注入的 ollama
    # 第二次调用应命中缓存，不重复 import
    again = oe._ollama()
    assert again is fake
