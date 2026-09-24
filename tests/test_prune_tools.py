"""
测试：FC 工具去重 + 按场景动态裁剪（方案 A+B）。

不依赖真实插件/引擎加载，用构造的 fake 数据验证：
- mcp_to_openai_tools 按 name 去重（消除 cache + builtin 叠加重复）
- prune_tools 分层裁剪：纯聊天极简、代码信号追加 lsp__*、外部 mcp 默认保留
"""

from xcli_core.fc_tools import mcp_to_openai_tools, prune_tools


def _fc(name, desc="d"):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    }


def _mcp(name, desc="d"):
    """MCP 格式（get_mcp_tools 返回的就是这种）"""
    return {
        "name": name,
        "description": desc,
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    }


class _FakePM:
    """最小 plugin_manager：get_mcp_tools 返回预置列表。"""

    def __init__(self, tools):
        self._tools = tools

    def get_mcp_tools(self):
        return self._tools


# ───────────── 去重 ─────────────

def test_mcp_to_openai_tools_dedup():
    # 模拟真实场景：cache 里已有 memory/scheduler，_get_builtin_tools 又追加一遍
    pm = _FakePM([
        _mcp("a"), _mcp("a"),                     # 同名重复
        _mcp("b"),
        _mcp("memory"), _mcp("scheduler"),        # cache 已有
    ])
    out = mcp_to_openai_tools(pm)
    names = [t["function"]["name"] for t in out]
    assert names.count("a") == 1, "同名工具应去重为 1"
    assert names.count("memory") == 1, "builtin 与 cache 重复应去重"
    assert names.count("scheduler") == 1
    assert "b" in names
    # builtin 追加的 memory/scheduler 不应再产生第二份
    assert names.count("memory") == 1


# ───────────── 分层裁剪 ─────────────

_CORE = ["tool_search", "memory", "scheduler", "code_editor", "code_search",
         "file_manager", "lsp__diagnostics", "lsp__hover", "lsp__definition",
         "lsp__references", "lsp__completion", "browser_auto", "network_tools",
         "ai_search", "git_tools", "cmd_executor", "sub_agent", "auto_engineer"]


def _full_set():
    return [_fc(n) for n in _CORE]


def test_prune_pure_chat_keeps_only_always():
    out = prune_tools(_full_set(), "你好啊，今天天气真不错")
    names = {t["function"]["name"] for t in out}
    assert names == {"tool_search", "memory", "scheduler"}, \
        f"纯聊天应只留常驻工具，实际: {names}"


def test_prune_code_signal_adds_lsp():
    out = prune_tools(_full_set(), "帮我写一个 python 脚本读取文件")
    names = {t["function"]["name"] for t in out}
    assert "code_editor" in names
    assert "file_manager" in names
    assert "lsp__diagnostics" in names, "写代码应追加 pylsp 的 lsp__* 工具"
    assert "lsp__completion" in names
    assert "tool_search" in names


def test_prune_git_signal():
    out = prune_tools(_full_set(), "提交代码并查看 git 状态")
    names = {t["function"]["name"] for t in out}
    assert "git_tools" in names
    assert "tool_search" in names


def test_prune_external_mcp_kept_even_in_chat():
    tools = [_fc("my_mcp__search"), _fc("code_editor"), _fc("tool_search")]
    out = prune_tools(tools, "你好")
    names = {t["function"]["name"] for t in out}
    assert "my_mcp__search" in names, "外部桥接工具(mcp__)应默认保留"
    assert "code_editor" not in names, "未命中信号的低频工具应被裁剪"
    assert "tool_search" in names


def test_prune_empty_input_no_crash():
    out = prune_tools(_full_set(), "")
    names = {t["function"]["name"] for t in out}
    assert names == {"tool_search", "memory", "scheduler"}


def test_prune_none_tools_returns_none():
    assert prune_tools(None, "任意输入") is None
    assert prune_tools([], "任意输入") == []
