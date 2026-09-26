"""
回归测试：统一模型连接器不得急切导入重型 SDK。

原因：ollama SDK 在 import 时会触发平台探测（platform.machine() → WMI），
在部分沙箱/未安装 ollama 的环境会卡死或拖慢启动。
引擎架构删除后，ollama 走其 OpenAI 兼容口（requests 直连），
本测试守住两件事：
- xcli_core/model_conn 顶层只允许 requests/colorama 等轻依赖，不得 import ollama/openai SDK；
- cli 启动链 import model_conn 不应触发任何重型 SDK 导入。

本测试只 import 模块、不构造 AICLI（避免触发 LSP 连接等环境依赖），
因此可在任意沙箱稳定运行。
"""
import builtins
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

HEAVY_SDKS = ("ollama", "openai", "torch", "cv2")


def test_model_conn_import_is_lazy():
    """import xcli_core.model_conn 不应触发任何重型 SDK 导入。"""
    imported = []
    real_import = builtins.__import__

    def traced(name, *a, **k):
        root = name.split(".")[0]
        if root in HEAVY_SDKS:
            imported.append(name)
        return real_import(name, *a, **k)

    sys.modules.pop("xcli_core.model_conn", None)
    builtins.__import__ = traced
    try:
        import xcli_core.model_conn as mc  # noqa: F401
    finally:
        builtins.__import__ = real_import

    assert imported == [], \
        f"import xcli_core.model_conn 不应触发重型 SDK 导入，实际 {imported}"


def test_model_conn_top_level_imports_are_light():
    """model_conn 模块命名空间里不应出现 ollama/openai 符号。"""
    import xcli_core.model_conn as mc
    assert not hasattr(mc, "ollama"), "model_conn 不应持有 ollama SDK"
    assert not hasattr(mc, "OpenAI"), "model_conn 不应持有 openai SDK"
    assert hasattr(mc, "ModelConnection"), "应有统一连接器 ModelConnection"
