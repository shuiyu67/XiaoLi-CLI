"""
Function Calling 工具格式转换
将 MCP 插件定义转为 OpenAI FC 格式，收集所有可用工具
"""
import json
from typing import List, Dict, Optional


def mcp_to_openai_tools(plugin_manager) -> List[Dict]:
    """
    从插件管理器收集所有工具定义，转为 OpenAI function calling 格式

    Returns:
        [{"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}, ...]
    """
    tools = []

    # 从插件管理器获取工具
    if not plugin_manager:
        return tools

    # 统一工具管理器
    if hasattr(plugin_manager, 'plugins'):
        for plugin in plugin_manager.plugins:
            fc_def = _extract_fc_def(plugin)
            if fc_def:
                tools.append(fc_def)
    # 普通插件管理器
    elif hasattr(plugin_manager, 'tools'):
        for tool_info in plugin_manager.tools:
            fc_def = _tool_info_to_fc(tool_info)
            if fc_def:
                tools.append(fc_def)

    # 追加内置工具（memory 等）
    builtin_tools = _get_builtin_tools()
    tools.extend(builtin_tools)

    return tools


def _extract_fc_def(plugin) -> Optional[Dict]:
    """从插件实例提取 FC 定义"""
    if not hasattr(plugin, 'get_mcp_definition'):
        return None

    try:
        mcp_def = plugin.get_mcp_definition()
        return mcp_to_fc(mcp_def)
    except Exception:
        return None


def _tool_info_to_fc(tool_info: dict) -> Optional[Dict]:
    """从 tool_info 字典转为 FC 定义"""
    name = tool_info.get('name', '')
    desc = tool_info.get('description', '')
    if not name:
        return None

    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": {
                    "args": {
                        "type": "string",
                        "description": f"操作参数。格式参见 {name} 工具说明"
                    }
                },
                "required": ["args"]
            }
        }
    }


def mcp_to_fc(mcp_def: dict) -> Optional[Dict]:
    """
    MCP 定义 → OpenAI FC 定义

    MCP 格式: {"name": ..., "description": ..., "inputSchema": {...}}
    OpenAI FC: {"type": "function", "function": {"name": ..., "description": ..., "parameters": {...}}}
    """
    name = mcp_def.get('name', '')
    desc = mcp_def.get('description', '')
    schema = mcp_def.get('inputSchema', mcp_def.get('parameters', {}))

    if not name:
        return None

    # 如果 schema 为空，生成默认的 args 参数
    if not schema or not schema.get('properties'):
        schema = {
            "type": "object",
            "properties": {
                "args": {
                    "type": "string",
                    "description": f"操作参数字符串，格式参见 {name} 工具说明"
                }
            },
            "required": ["args"]
        }

    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": schema
        }
    }


def fc_result_to_message(tool_call_id: str, tool_name: str, result: str) -> Dict:
    """
    工具执行结果 → OpenAI 消息格式

    Returns:
        {"role": "tool", "tool_call_id": ..., "content": ...}
    """
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "name": tool_name,
        "content": result[:10000] if result else ""  # 截断过长结果
    }


def parse_fc_response(response_data: dict) -> Optional[List[Dict]]:
    """
    解析 OpenAI FC 响应，提取 tool_calls

    Returns:
        [{"id": "call_xxx", "name": "tool_name", "arguments": {...}}, ...]
        或 None（如果不是 FC 响应）
    """
    choices = response_data.get("choices", [])
    if not choices:
        return None

    message = choices[0].get("message", {})
    tool_calls_raw = message.get("tool_calls")

    if not tool_calls_raw:
        return None

    tool_calls = []
    for tc in tool_calls_raw:
        func = tc.get("function", {})
        name = func.get("name", "")
        args_str = func.get("arguments", "{}")

        # 解析 arguments JSON
        try:
            if isinstance(args_str, str):
                args = json.loads(args_str)
            else:
                args = args_str
        except json.JSONDecodeError:
            args = {"raw": args_str}

        # 统一为小狸内部格式: {"action": "use_tool", "tool": name, "args": "..." }
        # 如果 args 里有 args 字段，直接用；否则把整个 args 序列化
        if "args" in args and isinstance(args["args"], str):
            final_args = args["args"]
        elif "args" in args:
            final_args = json.dumps(args["args"], ensure_ascii=False)
        else:
            # 把所有参数拼成字符串
            parts = []
            for k, v in args.items():
                if isinstance(v, str):
                    parts.append(f"{v}")
                else:
                    parts.append(json.dumps(v, ensure_ascii=False))
            final_args = " ".join(parts) if parts else ""

        tool_calls.append({
            "id": tc.get("id", f"call_{name}"),
            "name": name,
            "arguments": args,
            # 小狸内部格式
            "action": "use_tool",
            "tool": name,
            "args": final_args,
        })

    return tool_calls


def _get_builtin_tools() -> List[Dict]:
    """内置工具定义（不依赖插件系统）"""
    return [
        {
            "type": "function",
            "function": {
                "name": "memory",
                "description": "持久化记忆系统。写日记、记录长期记忆、搜索历史记忆和聊天记录。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["write", "diary", "remember", "search", "context",
                                    "diary_list", "diary_read", "chat_list", "chat_search"],
                            "description": "操作类型"
                        },
                        "content": {
                            "type": "string",
                            "description": "内容或关键词"
                        }
                    },
                    "required": ["action"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "scheduler",
                "description": "定时任务工具，设定定时提醒。支持相对时间(30m/2h)、今日时间(14:30)、绝对时间、重复任务(r:前缀)。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["add", "list", "delete", "clear"],
                            "description": "操作类型"
                        },
                        "time": {
                            "type": "string",
                            "description": "时间: 30m / 14:30 / 2026-04-28 10:00 / r:30m"
                        },
                        "message": {
                            "type": "string",
                            "description": "任务描述"
                        },
                        "task_id": {
                            "type": "integer",
                            "description": "任务ID (用于 delete)"
                        }
                    },
                    "required": ["action"]
                }
            }
        }
    ]
