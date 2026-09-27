"""
Function Calling 工具格式转换
将 MCP 插件定义转为 OpenAI FC 格式，收集所有可用工具
"""
import os
import json
import threading
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

    # 优先使用统一工具管理器的 MCP 定义（含外部 MCP client 桥接的工具，schema 保真）
    if hasattr(plugin_manager, 'get_mcp_tools'):
        try:
            for mcp_def in plugin_manager.get_mcp_tools():
                fc_def = mcp_to_fc(mcp_def)
                if fc_def:
                    tools.append(fc_def)
        except Exception:
            pass
    # 统一工具管理器（兜底，旧实现未暴露 get_mcp_tools 时）
    elif hasattr(plugin_manager, 'plugins'):
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

    # ── 去重：同名工具只保留首个 ──
    # 来源：get_mcp_tools() 的缓存里已含 memory/scheduler/lsp 等，
    # 下方 _get_builtin_tools() 又追加了一遍，导致同名重复（约 17% 的 FC token 是垃圾）。
    # 按 function.name 去重，消除双重曝光，对真实工具无影响。
    seen = set()
    deduped = []
    for t in tools:
        fname = (t.get("function") or {}).get("name", "")
        if fname in seen:
            continue
        seen.add(fname)
        deduped.append(t)
    return deduped


# ══════════════════════════════════════════════════════════════════
#  动态工具裁剪（方案 B：按场景分层）
#
#  把 40+ 的 FC 工具全量发给模型，每轮要重发数千 token schema，且
#  模型要在大列表里选对工具，决策面大、易选错、成本高。
#  这里按「当前用户输入」的信号，只下发本轮相关的工具子集：
#    - ALWAYS_KEEP：始终保留（含强制 tool_search 规则依赖、记忆、定时）
#    - 外部桥接工具（含 "mcp__"）默认保留（用户显式配置，误杀代价高）
#    - 命中关键词信号才追加对应工具（代码/文件/git/shell/浏览器/搜索/子agent/工程化）
#  纯聊天时模型只背 ~10 个核心工具而非 40+，FC token 可降约 70%+。
# ══════════════════════════════════════════════════════════════════

# 始终保留的工具（与系统提示里的强制规则/记忆机制强绑定）
ALWAYS_KEEP = {
    "tool_search",   # 系统提示的「强制工具查询规则」依赖它
    "memory",        # 持久化记忆
    "scheduler",     # 定时任务
}

# 信号：关键词集合 → 追加「以此前缀开头」的工具
_SIGNAL_RULES = [
    # 代码 / 文件操作：Python 等源码信号命中时，连 pylsp 的 lsp__* 一起给
    (
        {"写", "创建", "新建", "修改", "编辑", "代码", "脚本", "函数", "bug", "修复",
         "调试", "重构", "文件", "报错", "语法", "实现", "module", "def ", "import ",
         "class ", "print(", ".py", ".js", ".ts", ".java", ".go", ".cpp", ".c", ".rs"},
        ["code_editor", "code_search", "file_manager", "lsp__", "syntax_check", "check"],
    ),
    # 版本控制
    (
        {"git", "提交", "commit", "分支", "branch", "版本", "diff", "stash", "merge", "rebase"},
        ["git_tools"],
    ),
    # Shell 命令
    (
        {"命令", "shell", "终端", "执行", "运行", "cmd", "bash", "powershell", "terminal"},
        ["cmd_executor"],
    ),
    # 浏览器
    (
        {"浏览器", "网页", "点击", "browser", "打开网页", "截图", "scroll", "页面"},
        ["browser_auto"],
    ),
    # 联网 / 搜索 / HTTP
    (
        {"搜索", "联网", "http", "请求", "url", "curl", "api", "查一下", "上网", "fetch"},
        ["network_tools", "ai_search"],
    ),
    # 子 Agent 并行
    (
        {"子agent", "并行", "subagent", "sub_agent", "多智能体"},
        ["sub_agent"],
    ),
    # 工程化自动化
    (
        {"测试", "test", "lint", "build", "自动化", "工程化", "ci", "部署", "deploy"},
        ["auto_engineer"],
    ),
]


def prune_tools(fc_tools: List[Dict], user_input: str) -> List[Dict]:
    """
    按当前用户输入动态裁剪 FC 工具子集。

    返回保留下来的工具列表。无输入或空列表时原样返回（不裁剪）。
    规则见模块顶部 _SIGNAL_RULES / ALWAYS_KEEP 注释。
    """
    if not fc_tools:
        return fc_tools

    text = (user_input or "").lower()

    keep_prefixes = set()
    for keywords, prefixes in _SIGNAL_RULES:
        if any(kw in text for kw in keywords):
            keep_prefixes.update(prefixes)

    out = []
    for t in fc_tools:
        name = (t.get("function") or {}).get("name", "")
        # 1) 常驻工具
        if name in ALWAYS_KEEP:
            out.append(t)
            continue
        # 2) 外部桥接工具（用户显式配置）默认保留，避免误杀
        if "mcp__" in name:
            out.append(t)
            continue
        # 3) 命中当前轮信号 → 追加（前缀匹配，如 lsp__diagnostics 命中 "lsp__"）
        if any(name.startswith(p) for p in keep_prefixes):
            out.append(t)
            continue
        # 4) 其余（未命中信号的低频工具）本轮裁剪掉

    return out


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
        注意: 官方 OpenAI 的 tool 消息不含 name 字段（严格服务端如讯飞会拒），故不写入。
    """
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
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

        # 统一为Lix内部格式: {"action": "use_tool", "tool": name, "args": "..." }
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
            # Lix内部格式
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


# ══════════════════════════════════════════════════════════════════
#  FC 能力探测缓存
#
#  部分渠道/模型（如讯飞星火经 one-api 转发的 xophunyuan* 系列）
#  不支持 function calling，请求体里只要带上非空 tools 字段就会直接
#  返回 500 RequestParamsError:Invalid Params。
#  引擎捕获到这种错误后会去掉 tools 降级重试；本缓存把"该模型不支持 FC"
#  这件事记下来，后续请求直接跳过 tools，避免每次冷启动都白撞一次 500。
# ══════════════════════════════════════════════════════════════════

_FC_CACHE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".fc_support.json"
)
_fc_cache = None
_fc_lock = threading.Lock()


def _fc_key(base_url, model) -> str:
    """缓存键：base_url + model（同一渠道下不同模型能力可能不同）"""
    return f"{(base_url or '').rstrip('/')}::{model or ''}"


def _load_fc_cache() -> dict:
    global _fc_cache
    if _fc_cache is not None:
        return _fc_cache
    try:
        with open(_FC_CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        _fc_cache = data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
        _fc_cache = {}
    return _fc_cache


def _save_fc_cache(cache: dict):
    try:
        with open(_FC_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def supports_fc(base_url, model) -> bool:
    """该 (base_url, model) 是否支持 FC。未探测过时默认 True（乐观，先试一次）"""
    return _load_fc_cache().get(_fc_key(base_url, model)) is not False


def mark_fc_unsupported(base_url, model) -> bool:
    """标记该 (base_url, model) 不支持 FC 并持久化。首次标记返回 True"""
    with _fc_lock:
        cache = _load_fc_cache()
        key = _fc_key(base_url, model)
        if cache.get(key) is False:
            return False
        cache[key] = False
        _save_fc_cache(cache)
        return True


def reset_fc_cache(base_url=None, model=None) -> int:
    """清除 FC 探测缓存。不传参数则全清，返回清除的条目数"""
    with _fc_lock:
        cache = _load_fc_cache()
        if base_url is None and model is None:
            count = len(cache)
            cache.clear()
        else:
            count = 1 if cache.pop(_fc_key(base_url, model), None) is not None else 0
        _save_fc_cache(cache)
        return count


def get_fc_cache() -> dict:
    """返回 FC 探测缓存副本（供 /fc 命令展示）"""
    return dict(_load_fc_cache())
