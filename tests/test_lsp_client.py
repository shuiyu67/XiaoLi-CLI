"""
LSP 客户端测试
==============
用 inline 的 fake LSP server（Content-Length 分帧 JSON-RPC）验证：
- LspClient 全链路（initialize / didOpen 触发诊断 / hover / definition / shutdown）
- LspManager 按扩展名路由、多 server
- UnifiedToolManager 桥接：5 个 lsp__* 工具注册、get_mcp_tools 可见、execute 返回诊断
- get_lsp_context 注入
- fc_tools 保真（lsp 工具进入模型视野）
全程不触真实引擎 / 网络。
"""

import sys
import json

import pytest

from lsp_client import LspClient, LspManager, path_to_uri, ext_to_language


# ── Fake LSP server（Content-Length 分帧）──
FAKE_SERVER_SRC = r'''
import sys, json, threading, time

def send(obj):
    data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
    sys.stdout.buffer.write(b"Content-Length: %d\r\n\r\n" % len(data))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()

def read_msg():
    header = b""
    while b"\r\n\r\n" not in header:
        c = sys.stdin.buffer.read(1)
        if not c:
            return None
        header += c
    m = __import__("re").search(rb"Content-Length:\s*(\d+)", header)
    if not m:
        return None
    n = int(m.group(1))
    body = b""
    while len(body) < n:
        c = sys.stdin.buffer.read(n - len(body))
        if not c:
            return None
        body += c
    return json.loads(body.decode("utf-8"))

def main():
    initialized = threading.Event()
    while True:
        msg = read_msg()
        if msg is None:
            break
        mid = msg.get("id")
        method = msg.get("method")
        if method == "initialize":
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "capabilities": {"hoverProvider": True,
                                 "definitionProvider": True,
                                 "referencesProvider": True,
                                 "completionProvider": {}}}})
        elif method == "initialized":
            initialized.set()
        elif method == "textDocument/didOpen":
            params = msg.get("params", {})
            uri = params.get("textDocument", {}).get("uri", "")
            # 立即推送一条诊断
            send({"jsonrpc": "2.0", "method": "textDocument/publishDiagnostics",
                  "params": {"uri": uri, "diagnostics": [
                      {"range": {"start": {"line": 2, "character": 4},
                                 "end": {"line": 2, "character": 7}},
                       "severity": 1, "source": "fake-lsp",
                       "message": "Undefined variable 'foo'"}]}})
        elif method == "textDocument/hover":
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "contents": {"kind": "markdown", "value": "def foo(): ..."}}})
        elif method == "textDocument/definition":
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "uri": "file:///x.py", "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 3}}}})
        elif method == "textDocument/references":
            send({"jsonrpc": "2.0", "id": mid, "result": [
                {"uri": "file:///x.py", "range": {
                    "start": {"line": 1, "character": 0},
                    "end": {"line": 1, "character": 3}}}]})
        elif method == "textDocument/completion":
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "items": [{"label": "bar"}, {"label": "baz"}]}})
        elif method == "shutdown":
            send({"jsonrpc": "2.0", "id": mid, "result": None})
        elif method == "exit":
            break
        else:
            if mid is not None:
                send({"jsonrpc": "2.0", "id": mid, "result": {}})

if __name__ == "__main__":
    main()
'''


@pytest.fixture
def fake_server(tmp_path):
    p = tmp_path / "fake_lsp_server.py"
    p.write_text(FAKE_SERVER_SRC)
    return str(p)


def test_path_to_uri_windows():
    uri = path_to_uri("C:\\Users\\me\\a.py")
    assert uri.startswith("file:///")
    assert uri.endswith("/C:/Users/me/a.py")


def test_ext_to_language():
    assert ext_to_language("x.py") == "python"
    assert ext_to_language("x.rs") == "rust"
    assert ext_to_language("x.unknown") is None


def test_lsp_client_lifecycle(fake_server, tmp_path):
    code_file = tmp_path / "sample.py"
    code_file.write_text("print('hi')\nx = 1\nfoo = 2\n")

    client = LspClient("python", sys.executable, [fake_server],
                       language_id="python", root_uri="file:///tmp")
    try:
        client.start()
        init = client.initialize()
        assert isinstance(init, dict)

        diags = client.diagnostics(str(code_file), wait=3.0)
        assert len(diags) == 1
        assert "Undefined variable" in diags[0]["message"]

        hover = client.hover(str(code_file), 0, 0)
        assert hover and "foo" in json.dumps(hover)

        definition = client.definition(str(code_file), 0, 0)
        assert definition

        references = client.references(str(code_file), 0, 0)
        assert references

        completion = client.completion(str(code_file), 0, 0)
        assert completion
    finally:
        client.shutdown()


def test_lsp_manager_routing(fake_server, tmp_path):
    # 用 .py 扩展名映射到 fake server（languageId=python）
    servers = {"python": {"command": sys.executable, "args": [fake_server],
                          "disabled": False}}
    mgr = LspManager()
    mgr.connect_all(servers, cwd=str(tmp_path), root_uri="file:///tmp")
    assert "python" in mgr.get_servers()

    code_file = tmp_path / "sample.py"
    code_file.write_text("a = 1\nb = 2\nfoo = 3\n")
    out = mgr.diagnostics(str(code_file))
    assert "Undefined variable" in out
    # 诊断被缓存，供上下文注入
    ctx = mgr.get_context()
    assert "Undefined variable" in ctx

    hover_out = mgr.hover(str(code_file), 0, 0)
    assert "foo" in hover_out


def test_lsp_manager_unknown_ext_graceful(fake_server, tmp_path):
    servers = {"python": {"command": sys.executable, "args": [fake_server]}}
    mgr = LspManager()
    mgr.connect_all(servers, cwd=str(tmp_path), root_uri="file:///tmp")
    # .rs 没有配置 server，应优雅提示而非崩溃
    out = mgr.diagnostics(str(tmp_path / "x.rs"))
    assert "没有为" in out or "LSP server" in out


def test_lsp_manager_connect_failure_graceful(tmp_path):
    # 命令不存在 → 不应抛异常，仅记录
    servers = {"python": {"command": "this_command_does_not_exist_xyz"}}
    mgr = LspManager()
    mgr.connect_all(servers, cwd=str(tmp_path), root_uri="file:///tmp")
    assert mgr.get_servers() == []


def test_unified_manager_bridges_lsp(fake_server, tmp_path, monkeypatch):
    code_file = tmp_path / "sample.py"
    code_file.write_text("a = 1\nb = 2\nfoo = 3\n")
    cfg = {
        "mcpServers": {},
        "lspServers": {"python": {"command": sys.executable, "args": [fake_server],
                                  "disabled": False}},
    }

    import xcli_core.config as xcfg
    monkeypatch.setattr(xcfg, "load_config", lambda: cfg)
    try:
        import config as root_cfg
        monkeypatch.setattr(root_cfg, "load_config", lambda: cfg)
    except ImportError:
        pass

    import unified_tool_manager as utm
    mgr = utm.UnifiedToolManager()
    mgr.initialize(
        plugins_dir=str(tmp_path / "noplugins"),
        skills_dir=str(tmp_path / "noskills"),
    )
    try:
        tools = mgr.get_mcp_tools()
        names = [t["name"] for t in tools]
        for expected in ("lsp__diagnostics", "lsp__hover", "lsp__definition",
                         "lsp__references", "lsp__completion"):
            assert expected in names, f"缺少 LSP 工具: {expected}"

        # inputSchema 保真（不压成 args）
        diag_def = next(t for t in tools if t["name"] == "lsp__diagnostics")
        assert "file" in diag_def["inputSchema"]["properties"]

        # execute 返回真实诊断文本
        res = mgr.execute("lsp__diagnostics", json.dumps({"file": str(code_file)}))
        assert res.success
        assert "Undefined variable" in (res.data or "")

        # 上下文注入可用
        ctx = mgr.get_lsp_context()
        assert "Undefined variable" in ctx
    finally:
        mgr.shutdown()


def test_lsp_skip_when_no_servers_configured(tmp_path, monkeypatch):
    # noch keinen LSP-Server -> keine lsp__ Tools
    cfg = {"mcpServers": {}, "lspServers": {}}
    import xcli_core.config as xcfg
    monkeypatch.setattr(xcfg, "load_config", lambda: cfg)
    try:
        import config as root_cfg
        monkeypatch.setattr(root_cfg, "load_config", lambda: cfg)
    except ImportError:
        pass
    import unified_tool_manager as utm
    mgr = utm.UnifiedToolManager()
    mgr.initialize(
        plugins_dir=str(tmp_path / "noplugins"),
        skills_dir=str(tmp_path / "noskills"),
    )
    try:
        names = [t["name"] for t in mgr.get_mcp_tools()]
        assert not any(n.startswith("lsp__") for n in names)
    finally:
        mgr.shutdown()


def test_fc_tools_includes_lsp(tmp_path, monkeypatch, fake_server):
    """验证 lsp__* 工具能经 get_mcp_tools 进入 fc_tools 保真输出"""
    import xcli_core.config as xcfg
    cfg = {"mcpServers": {},
           "lspServers": {"python": {"command": sys.executable, "args": [fake_server]}}}
    monkeypatch.setattr(xcfg, "load_config", lambda: cfg)
    try:
        import config as root_cfg
        monkeypatch.setattr(root_cfg, "load_config", lambda: cfg)
    except ImportError:
        pass

    import unified_tool_manager as utm
    import xcli_core.fc_tools as fc_tools

    mgr = utm.UnifiedToolManager()
    mgr.initialize(
        plugins_dir=str(tmp_path / "noplugins"),
        skills_dir=str(tmp_path / "noskills"),
    )
    try:
        fc = fc_tools.mcp_to_openai_tools(mgr)
        lsp_fc = [t for t in fc if t.get("function", {}).get("name", "").startswith("lsp__")]
        assert len(lsp_fc) == 5, f"应进入 5 个 lsp 工具，实际 {len(lsp_fc)}"
        # 保真：参数应是 file/line/character，而非单个 args
        diag = next(t for t in lsp_fc if t["function"]["name"] == "lsp__diagnostics")
        assert "file" in diag["function"]["parameters"]["properties"]
    finally:
        mgr.shutdown()


# ── code_editor / file_manager 的「写 .py 后自动触发 pylsp 诊断」钩子 ──
def _make_fake_lsp_manager(diag_text):
    """构造一个 fake LSP 管理器，记录被调用，并返回固定诊断文本。"""
    calls = []

    class FakeManager:
        def __init__(self):
            self.clients = {"python": object()}  # 模拟已连接 python server

        def diagnostics(self, filepath, wait=1.5):
            calls.append(filepath)
            return diag_text

    fm = FakeManager()
    fm._calls = calls
    return fm


def _attach(cli, fm):
    class UTM:
        _lsp_manager = fm
    cli.liugin_manager = UTM()


def test_auto_lsp_check_triggers_on_py_write(tmp_path):
    """写/改 .py 后钩子应调用 LSP 诊断，并在有问题时返回概要。"""
    from plugins.code_editor import Liugin as CodeEditor
    ce = CodeEditor()
    fm = _make_fake_lsp_manager("🔍 x.py：2 条诊断\n  错误 L1:1 — undefined name 'foo'")
    cli = type("CLI", (), {})()
    _attach(cli, fm)
    ce.set_cli(cli)

    py_file = tmp_path / "mod.py"
    py_file.write_text("foo = bar\n", encoding="utf-8")
    out = ce._auto_lsp_check(str(py_file))
    assert str(py_file) in fm._calls, "应调用 lsp_manager.diagnostics(该 py 文件)"
    assert "LSP 诊断" in out and "2 条诊断" in out


def test_auto_lsp_check_silent_when_clean(tmp_path):
    """文件干净（无诊断）时钩子应静默返回空串。"""
    from plugins.code_editor import Liugin as CodeEditor
    ce = CodeEditor()
    fm = _make_fake_lsp_manager("✅ mod.py：无诊断（未发现问题）")
    cli = type("CLI", (), {})()
    _attach(cli, fm)
    ce.set_cli(cli)

    py_file = tmp_path / "clean.py"
    py_file.write_text("x = 1\n", encoding="utf-8")
    assert ce._auto_lsp_check(str(py_file)) == ""


def test_auto_lsp_check_silent_without_lsp_manager(tmp_path):
    """未连接 LSP 管理器（或未配置 server）时钩子应静默跳过，绝不报错。"""
    from plugins.code_editor import Liugin as CodeEditor
    ce = CodeEditor()
    cli = type("CLI", (), {})()
    # liugin_manager 没有 _lsp_manager 属性
    cli.liugin_manager = type("UTM", (), {})()
    ce.set_cli(cli)

    py_file = tmp_path / "any.py"
    py_file.write_text("pass\n", encoding="utf-8")
    assert ce._auto_lsp_check(str(py_file)) == ""


def test_auto_lsp_check_no_server_for_ext(tmp_path):
    """扩展名未配置 LSP server 时（如 .txt）应静默返回空串。"""
    from plugins.code_editor import Liugin as CodeEditor
    ce = CodeEditor()
    fm = _make_fake_lsp_manager("⚠️ 没有为 x.txt 配置 LSP server")
    # clients 里只有 python，没有 txt 对应的 server；这里用文本模拟「无 server」返回
    cli = type("CLI", (), {})()
    _attach(cli, fm)
    ce.set_cli(cli)

    txt_file = tmp_path / "note.txt"
    txt_file.write_text("hello\n", encoding="utf-8")
    assert ce._auto_lsp_check(str(txt_file)) == ""
