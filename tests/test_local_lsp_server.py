"""自研本地 LSP 服务器测试：单元（分帧/协议/引擎）+ 真实 subprocess 集成"""
import io
import json
import os
import queue
import re
import subprocess
import sys
import threading


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from xcli_core.local_lsp_server import (
    LocalLspServer,
    path_to_uri,
    read_message,
    uri_to_path,
    write_message,
)

SRC = "import math\ndef add(a, b):\n    return a + b\n\nresult = add(1, 2)\nprint(result)\n"
URI = "file:///C:/Users/Administrator/Desktop/xiaoli-cli/_test_tmp.py"


# ── 分帧传输层 ──
class TestFraming:
    def test_roundtrip(self):
        buf = io.BytesIO()
        write_message(buf, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        buf.seek(0)
        msg = read_message(buf)
        assert msg == {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}

    def test_cjk_bytes(self):
        # 中文消息体: Content-Length 按字节计
        obj = {"result": "未定义变量 — 中文诊断"}
        buf = io.BytesIO()
        write_message(buf, obj)
        buf.seek(0)
        assert read_message(buf) == obj

    def test_empty_stream(self):
        assert read_message(io.BytesIO(b"")) is None


# ── 路径工具 ──
class TestPath:
    def test_uri_to_path_windows(self):
        p = uri_to_path("file:///C:/Users/a/b.py")
        assert os.path.abspath(p) == os.path.abspath("C:/Users/a/b.py")

    def test_path_to_uri(self):
        assert path_to_uri(r"C:\Users\a\b.py").startswith("file:///C:/Users/a/b.py")


# ── 协议层（进程内直接调 handle） ──
class TestProtocol:
    def make_server(self):
        srv = LocalLspServer()
        srv.handle({"jsonrpc": "2.0", "method": "initialize", "id": 1,
                    "params": {"rootUri": "file:///" + PROJECT_ROOT.replace("\\", "/")}})
        return srv

    def test_initialize_capabilities(self):
        srv = LocalLspServer()
        outs = srv.handle({"jsonrpc": "2.0", "method": "initialize", "id": 1, "params": {}})
        assert outs[0]["id"] == 1
        caps = outs[0]["result"]["capabilities"]
        assert caps["definitionProvider"] is True
        assert "completionProvider" in caps
        assert caps["textDocumentSync"]["change"] == 1

    def test_unknown_method_error(self):
        srv = LocalLspServer()
        outs = srv.handle({"jsonrpc": "2.0", "method": "textDocument/xxx", "id": 9, "params": {}})
        assert outs[0]["error"]["code"] == -32601

    def test_shutdown_and_unknown_notification_no_reply(self):
        srv = LocalLspServer()
        assert srv.handle({"jsonrpc": "2.0", "method": "initialized", "params": {}}) == []
        assert srv.handle({"jsonrpc": "2.0", "method": "shutdown", "id": 2,
                           "params": {}})[0]["result"] is None

    def test_did_open_pushes_diagnostics(self):
        srv = self.make_server()
        outs = srv.handle({"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {
            "textDocument": {"uri": URI, "languageId": "python", "version": 1, "text": SRC}}})
        push = [o for o in outs if o.get("method") == "textDocument/publishDiagnostics"]
        assert push, "didOpen 应推送诊断"
        diags = push[0]["params"]["diagnostics"]
        assert diags, "应检测到问题 (import math 未使用)"
        first = diags[0]
        assert first["source"] == "py_detect"
        assert "range" in first and "severity" in first and "message" in first

    def test_diagnostics_clean_file_no_push(self):
        srv = self.make_server()
        clean = "def add(a, b):\n    return a + b\nprint(add(1, 2))\n"
        outs = srv.handle({"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {
            "textDocument": {"uri": URI, "languageId": "python", "version": 1, "text": clean}}})
        assert not [o for o in outs if o.get("method") == "textDocument/publishDiagnostics"]


# ── jedi 语义（进程内，无需真实文件） ──
class TestSemantic:
    def open(self):
        srv = LocalLspServer()
        srv.handle({"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {
            "textDocument": {"uri": URI, "languageId": "python", "version": 1, "text": SRC}}})
        return srv

    def req(self, srv, method, line, character):
        outs = srv.handle({"jsonrpc": "2.0", "method": method, "id": 1, "params": {
            "textDocument": {"uri": URI}, "position": {"line": line, "character": character}}})
        return outs[0]["result"]

    def test_completion(self):
        srv = self.open()
        res = self.req(srv, "textDocument/completion", 6, 10)  # result.
        items = res.get("items", []) if isinstance(res, dict) else res
        labels = [i["label"] for i in items]
        assert "result" in labels, f"应在 result 后补全: {labels}"

    def test_definition(self):
        srv = self.open()
        res = self.req(srv, "textDocument/definition", 5, 10)  # add 调用处
        assert res, "应找到 add 定义"
        loc = res[0]
        assert loc["uri"].startswith("file:///")
        assert loc["range"]["start"]["line"] == 2  # 定义在第 3 行 (0-based)

    def test_references(self):
        srv = self.open()
        res = self.req(srv, "textDocument/references", 5, 10)  # add
        assert len(res) >= 2, "应至少含定义处+调用处"

    def test_hover(self):
        srv = self.open()
        res = self.req(srv, "textDocument/hover", 5, 10)  # add
        assert res is not None
        contents = res.get("contents", {})
        value = contents.get("value", "") if isinstance(contents, dict) else str(contents)
        assert value, "hover 应有内容"

    def test_hover_builtin(self):
        srv = self.open()
        # math 已 import; 悬停 print 是内置, 不崩溃即可
        res = self.req(srv, "textDocument/hover", 6, 1)
        assert res is None or isinstance(res, dict)


# ── 真实 subprocess 集成（完整握手） ──
class TestSubprocessIntegration:
    def test_full_handshake(self):
        proc = subprocess.Popen(
            [sys.executable, "-m", "xcli_core.local_lsp_server"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, cwd=PROJECT_ROOT, bufsize=0)
        try:
            q = queue.Queue()

            def _reader():
                try:
                    while True:
                        header = b""
                        while b"\r\n\r\n" not in header:
                            chunk = proc.stdout.read(1)
                            if not chunk:
                                return
                            header += chunk
                        m = re.search(rb"Content-Length:\s*(\d+)", header)
                        body = proc.stdout.read(int(m.group(1))) if m else b""
                        if body:
                            q.put(json.loads(body.decode("utf-8")))
                except Exception:
                    pass

            threading.Thread(target=_reader, daemon=True).start()

            def send(obj):
                data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
                proc.stdin.write(f"Content-Length: {len(data)}\r\n\r\n".encode() + data)
                proc.stdin.flush()

            def recv(timeout=25):
                return q.get(timeout=timeout)

            root_uri = "file:///" + PROJECT_ROOT.replace("\\", "/")
            send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                  "params": {"processId": os.getpid(), "rootUri": root_uri,
                             "capabilities": {"textDocument": {}}}})
            r = recv()
            assert "capabilities" in r.get("result", {}), r

            send({"jsonrpc": "2.0", "method": "initialized", "params": {}})
            send({"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {
                "textDocument": {"uri": URI, "languageId": "python", "version": 1,
                                 "text": SRC}}})
            diag = recv()
            assert diag.get("method") == "textDocument/publishDiagnostics", diag
            assert diag["params"]["diagnostics"], "应推送诊断"

            send({"jsonrpc": "2.0", "id": 2, "method": "textDocument/completion", "params": {
                "textDocument": {"uri": URI}, "position": {"line": 6, "character": 10}}})
            c = recv()["result"]
            items = c.get("items", []) if isinstance(c, dict) else c
            assert any(i["label"] == "result" for i in items)

            send({"jsonrpc": "2.0", "id": 3, "method": "textDocument/definition", "params": {
                "textDocument": {"uri": URI}, "position": {"line": 5, "character": 10}}})
            d = recv()["result"]
            assert d and d[0]["range"]["start"]["line"] == 2

            send({"jsonrpc": "2.0", "id": 4, "method": "textDocument/hover", "params": {
                "textDocument": {"uri": URI}, "position": {"line": 5, "character": 10}}})
            h = recv()["result"]
            assert h is not None

            send({"jsonrpc": "2.0", "id": 5, "method": "shutdown", "params": {}})
            assert recv()["result"] is None
            send({"jsonrpc": "2.0", "method": "exit", "params": {}})
            proc.stdin.close()
            proc.wait(timeout=5)
        finally:
            if proc.poll() is None:
                proc.kill()
