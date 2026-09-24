# -*- coding: utf-8 -*-
"""跨模块共享的兜底定义（xcli_core 不可用时的降级实现）。

历史上 websocket_server / manual_engine / ollama_engine / openai_engine
四个文件各自内联了一份完全相同的 normalize_tool_text 兜底，
现收敛于此，保证降级语义只有一份定义。
"""

try:
    from xcli_core.tool_result import normalize_tool_text  # noqa: F401
except Exception:
    def normalize_tool_text(result, default="无结果"):
        """兜底归一化：ToolResult / dict / str 统一成字符串"""
        if result is None:
            return default
        if isinstance(result, dict):
            return str(result.get("result", default))
        return str(result)
