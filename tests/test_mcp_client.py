"""
MCP 客户端测试
==============
用 inline 的 fake MCP server（写入临时文件，subprocess 启动）验证：

1. McpClient 全链路：start → initialize → list_tools → call_tool → stop（进程回收）
2. McpClientManager 多 server 并发连接、聚合、调用、cleanup 幂等
3. 超时：沉默 server 不响应 → call_tool 应在 timeout 内抛错
4. UnifiedToolManager 桥接：外部 MCP 工具按 {server}__{tool} 注册、schema 保真、可被 execute 调用、shutdown 清理子进程
5. fc_tools.mcp_to_openai_tools 优先走 get_mcp_tools 保真分支（不把 schema 压成 args）

全程不依赖真实 AI 引擎、网络或外部 npx。
"""

import os
import sys

import pytest

# 确保项目根在 sys.path（unified_tool_manager / mcp_client / config 均在根目录）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from mcp_client import McpClient, McpClientManager  # noqa: E402
import unified_tool_manager as utm  # noqa: E402
from xcli_core.fc_tools import mcp_to_openai_tools  # noqa: E402

# fake MCP server：实现 initialize / tools/list / tools/call / ping，
# 以及一个 echo 工具（inputSchema 保真）。与 mcp_server.py 协议对称。
FAKE_SERVER_SRC = r'''
import sys, json

def send(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        method = req.get("method", "")
        mid = req.get("id")
        if method == "notifications/initialized":
            continue
        if method == "initialize":
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fake", "version": "1.0"},
            }})
        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": mid, "result": {"tools": [{
                "name": "echo",
                "description": "回声工具",
                "inputSchema": {
                    "type": "object",
                    "properties": {"text": {"type": "string", "description": "要回声的文本"}},
                    "required": ["text"],
                },
            }]}})
        elif method == "tools/call":
            params = req.get("params", {})
            name = params.get("name")
            args = params.get("arguments", {})
            if name == "echo":
                send({"jsonrpc": "2.0", "id": mid, "result": {
                    "content": [{"type": "text", "text": "echo: " + str(args.get("text", ""))}],
                }})
            else:
                send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "unknown tool"}})
        elif method == "ping":
            send({"jsonrpc": "2.0", "id": mid, "result": {}})
        else:
            send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found"}})

if __name__ == "__main__":
    main()
'''


@pytest.fixture
def fake_server_path(tmp_path):
    p = tmp_path / "fake_mcp_server.py"
    p.write_text(FAKE_SERVER_SRC)
    return str(p)


def test_mcp_client_lifecycle(fake_server_path):
    client = McpClient("fake", sys.executable, [fake_server_path])
    try:
        client.start()
        info = client.initialize()
        assert info.get("protocolVersion") == "2024-11-05"
        tools = client.list_tools()
        assert any(t.get("name") == "echo" for t in tools)
        out = client.call_tool("echo", {"text": "hi"})
        assert "hi" in out
    finally:
        client.stop()
    # 进程应已被回收
    assert client.proc.poll() is not None


def test_manager_multi_server(fake_server_path):
    mgr = McpClientManager()
    mgr.connect_all({
        "a": {"command": sys.executable, "args": [fake_server_path]},
        "b": {"command": sys.executable, "args": [fake_server_path]},
    })
    assert set(mgr.get_servers()) == {"a", "b"}
    assert len(mgr.get_all_tools()) == 2
    out = mgr.call_tool("a", "echo", {"text": "x"})
    assert "x" in out
    mgr.cleanup()
    mgr.cleanup()  # 幂等


def test_client_timeout(tmp_path):
    silent = tmp_path / "silent.py"
    silent.write_text("import time\nwhile True:\n    time.sleep(1)\n")
    client = McpClient("silent", sys.executable, [str(silent)], timeout=2)
    try:
        client.start()
        with pytest.raises(Exception):
            client.list_tools()  # 沉默 server 不响应 → 超时
    finally:
        client.stop()


def test_unified_manager_bridges_external_mcp(tmp_path, monkeypatch):
    fake = tmp_path / "fake_mcp_server.py"
    fake.write_text(FAKE_SERVER_SRC)
    cfg = {"mcpServers": {"fake": {"command": sys.executable, "args": [str(fake)]}}}

    import xcli_core.config as xcfg
    monkeypatch.setattr(xcfg, "load_config", lambda: cfg)
    try:
        import config as root_cfg
        monkeypatch.setattr(root_cfg, "load_config", lambda: cfg)
    except ImportError:
        pass

    mgr = utm.UnifiedToolManager()
    # 用不存在的插件/技能目录，避免加载真实插件
    mgr.initialize(
        plugins_dir=str(tmp_path / "noplugins"),
        skills_dir=str(tmp_path / "noskills"),
    )
    try:
        tool = mgr.get_tool("fake__echo")
        assert tool is not None, "外部 MCP 工具应已桥接为 fake__echo"
        assert tool["protocol"] == "mcp"

        names = [t["name"] for t in mgr.get_mcp_tools()]
        assert "fake__echo" in names

        echo_def = next(t for t in mgr.get_mcp_tools() if t["name"] == "fake__echo")
        assert "text" in echo_def["inputSchema"]["properties"]

        res = mgr.execute("fake__echo", '{"text": "hello"}')
        assert res.success
        assert "hello" in (res.data or "")
    finally:
        mgr.shutdown()


def test_fc_tools_uses_get_mcp_tools():
    class FakeMgr:
        def get_mcp_tools(self):
            return [{
                "name": "my_tool",
                "description": "d",
                "inputSchema": {
                    "type": "object",
                    "properties": {"q": {"type": "string"}},
                    "required": ["q"],
                },
            }]

    tools = mcp_to_openai_tools(FakeMgr())
    my = next(t for t in tools if t["function"]["name"] == "my_tool")
    # schema 保真：不被压成 {"args": string}
    assert "q" in my["function"]["parameters"]["properties"]
    assert "args" not in my["function"]["parameters"]["properties"]
    # 内置工具（memory / scheduler）仍被追加
    names = [t["function"]["name"] for t in tools]
    assert "memory" in names and "scheduler" in names
