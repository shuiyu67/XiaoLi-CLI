"""
统一工具返回格式 - ToolResult

所有插件和工具管理器使用统一的返回格式，
替代原来混乱的字符串/Dict 返回。
"""

from dataclasses import dataclass, field
from typing import Any


# 错误码常量
class ErrorCode:
    """工具错误码"""
    SUCCESS = 0
    # 参数错误 (1xx)
    MISSING_ARGS = 100
    INVALID_ARGS = 101
    UNSUPPORTED_OP = 102
    # 资源错误 (2xx)
    NOT_FOUND = 200
    FILE_NOT_FOUND = 201
    PERMISSION_DENIED = 202
    # 执行错误 (3xx)
    EXEC_FAILED = 300
    TIMEOUT = 301
    DECODE_ERROR = 302
    # 系统错误 (4xx)
    INTERNAL_ERROR = 400
    NOT_IMPLEMENTED = 401

    _NAMES = {
        0: "成功",
        100: "缺少参数",
        101: "参数无效",
        102: "不支持的操作",
        200: "未找到",
        201: "文件不存在",
        202: "权限不足",
        300: "执行失败",
        301: "超时",
        302: "解码错误",
        400: "内部错误",
        401: "未实现",
    }

    @classmethod
    def name(cls, code: int) -> str:
        return cls._NAMES.get(code, f"未知({code})")


@dataclass
class ToolResult:
    """统一工具返回格式"""

    success: bool
    data: Any = None
    error_code: int = ErrorCode.SUCCESS
    error_message: str = ""

    # 可选元数据
    tool_name: str = ""
    execution_time: float = 0.0
    metadata: dict = field(default_factory=dict)

    def __str__(self) -> str:
        if self.success:
            return str(self.data) if self.data is not None else "执行完成"
        return f"[{ErrorCode.name(self.error_code)}] {self.error_message}"

    # ── 便捷构造方法 ──

    @classmethod
    def ok(cls, data: Any = None, **kwargs) -> "ToolResult":
        """成功"""
        return cls(success=True, data=data, **kwargs)

    @classmethod
    def fail(cls, message: str, code: int = ErrorCode.EXEC_FAILED, **kwargs) -> "ToolResult":
        """失败"""
        return cls(success=False, error_code=code, error_message=message, **kwargs)

    @classmethod
    def missing(cls, what: str = "参数", **kwargs) -> "ToolResult":
        """缺少参数"""
        return cls.fail(f"缺少{what}", ErrorCode.MISSING_ARGS, **kwargs)

    @classmethod
    def not_found(cls, what: str = "资源", **kwargs) -> "ToolResult":
        """未找到"""
        return cls.fail(f"{what}不存在", ErrorCode.NOT_FOUND, **kwargs)

    @classmethod
    def timeout(cls, seconds: int = 0, **kwargs) -> "ToolResult":
        """超时"""
        msg = f"执行超时"
        if seconds:
            msg += f" ({seconds}秒)"
        return cls.fail(msg, ErrorCode.TIMEOUT, **kwargs)

    # ── 格式转换 ──

    def to_dict(self) -> dict:
        """转为普通 dict（兼容旧接口）"""
        if self.success:
            return {"result": self.data if self.data is not None else "执行完成"}
        return {"result": str(self)}

    def to_mcp(self) -> dict:
        """转为 MCP 协议格式"""
        text = str(self)
        return {
            "content": [{"type": "text", "text": text}],
            "isError": not self.success,
        }

    def to_string(self) -> str:
        """转为字符串（兼容旧插件 handle() 返回值）"""
        return str(self)


# ── 归一化辅助（跨层兼容：ToolResult / dict / str / None）──

def normalize_tool_text(result: Any, default: str = "无结果") -> str:
    """把任意工具返回值统一成字符串。

    工具链里三种返回形态都可能出现：
      - ToolResult（新插件 / UnifiedToolManager.execute）
      - {"result": ...}（旧插件 / to_dict）
      - 纯字符串（最老的 handler）
    统一收敛成字符串，避免上层对 ToolResult 调用 .get() 报
    "'ToolResult' object has no attribute 'get'"。
    """
    if result is None:
        return default
    if isinstance(result, ToolResult):
        text = str(result)
    elif isinstance(result, dict):
        text = result.get("result", result.get("content", ""))
        if isinstance(text, (dict, list)):
            import json as _json
            try:
                text = _json.dumps(text, ensure_ascii=False)
            except Exception:
                text = str(text)
        elif not isinstance(text, str):
            text = str(text) if text is not None else ""
    else:
        text = str(result)
    text = text.strip() if isinstance(text, str) else str(text)
    return text if text else default


def normalize_tool_dict(result: Any, default: str = "无结果") -> dict:
    """把任意工具返回值统一成 {"result": str, ...} 结构。

    额外附带 success / error_code / tool_result，方便需要细节的调用方，
    同时保证 .get('result') 一定可用。
    """
    text = normalize_tool_text(result, default)
    if isinstance(result, ToolResult):
        return {
            "result": text,
            "success": result.success,
            "error_code": result.error_code,
            "tool_result": result,
        }
    if isinstance(result, dict):
        out = dict(result)
        out["result"] = text
        out.setdefault("success", True)
        return out
    return {"result": text, "success": True}
