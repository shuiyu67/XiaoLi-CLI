"""
自研本地 LSP 服务器 (local_lsp_server)
======================================
纯本地、零外部服务依赖的 Python 语言服务器——替代 pylsp。

架构:
  - 语义引擎: jedi (纯 Python, 已在环境) — 补全/跳转/引用/悬停/签名
  - 诊断引擎: plugins/py_detect (ast 规则引擎, 中文诊断)
  - 协议: LSP over stdio (Content-Length 分帧), 与 xiaoli 的 lsp_client.py 完全兼容

特性:
  - 零网络请求, 不依赖任何外部安装 (无需 pip install pylsp)
  - 服务器不响应时客户端可超时跳过, 不会无限卡死
  - 诊断推送自动携带 py_detect 的中文解释 + 修复建议

用法:
  python -m xcli_core.local_lsp_server
  或配置进 config.json 的 lspServers: {"command": "python", "args": ["-m", "xcli_core.local_lsp_server"]}

支持的 LSP 方法:
  initialize / initialized / shutdown / exit
  textDocument/didOpen|didChange|didClose (通知)
  textDocument/completion|definition|references|hover (请求)
  textDocument/publishDiagnostics (主动推送, 来自 py_detect)
"""

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

__version__ = "1.0.0"

# ══════════════════════════════════════════════
#  Content-Length 分帧 (LSP stdio 传输层)
# ══════════════════════════════════════════════


def read_message(stream) -> Optional[Dict[str, Any]]:
    """从流中读取一条 Content-Length 分帧消息"""
    header = b""
    while b"\r\n\r\n" not in header:
        chunk = stream.read(1)
        if not chunk:
            return None
        header += chunk
        if len(header) > 65536:
            return None
    m = re.search(rb"Content-Length:\s*(\d+)", header)
    if not m:
        return None
    length = int(m.group(1))
    body = b""
    while len(body) < length:
        chunk = stream.read(length - len(body))
        if not chunk:
            return None
        body += chunk
    try:
        return json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def write_message(stream, obj: Dict[str, Any]) -> None:
    """向流中写入一条 Content-Length 分帧消息"""
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    stream.write(f"Content-Length: {len(data)}\r\n\r\n".encode("ascii"))
    stream.write(data)
    stream.flush()


# ══════════════════════════════════════════════
#  路径工具 (file:// URI <-> 文件系统路径)
# ══════════════════════════════════════════════


def uri_to_path(uri: str) -> str:
    """file:///C:/a/b.py -> C:/a/b.py"""
    if uri.startswith("file://"):
        path = uri[7:]
        if len(path) >= 3 and path[0] == "/" and path[2] == ":":
            path = path[1:]  # /C:/... -> C:/...
        return path.replace("/", os.sep) if os.sep == "\\" else path
    return uri


def path_to_uri(path: str) -> str:
    abspath = os.path.abspath(path)
    norm = abspath.replace("\\", "/")
    if not norm.startswith("/"):
        norm = "/" + norm
    return "file://" + norm


# ══════════════════════════════════════════════
#  自研本地 LSP 服务器
# ══════════════════════════════════════════════


class LocalLspServer:
    """本地 Python 语言服务器: jedi 语义 + py_detect 诊断。

    handle(msg) 返回要写出的消息列表（响应/推送），便于单元测试与进程模式复用。
    """

    def __init__(self):
        self.documents: Dict[str, str] = {}      # uri -> 最新文本
        self.root_path: Optional[str] = None
        self._project = None
        self._jedi = None
        self._py_detect = None
        self._shutdown = False

    # ── 引擎惰性加载 (首次用时才 import, 失败不崩) ──
    def _get_jedi(self):
        if self._jedi is None:
            try:
                import jedi
                self._jedi = jedi
            except Exception:
                self._jedi = False
        return self._jedi or None

    def _get_project(self):
        if self._project is None and self._get_jedi() is not None:
            try:
                root = self.root_path
                if root and os.path.isdir(root):
                    self._project = self._jedi.Project(root)
                else:
                    self._project = False
            except Exception:
                self._project = False
        return self._project if self._project else None

    def _load_py_detect(self):
        """从 plugins/py_detect.py 加载诊断引擎 (与 code_editor 同源, 零复制)"""
        if self._py_detect is not None:
            return self._py_detect if self._py_detect is not False else None
        try:
            import importlib.util
            here = os.path.dirname(os.path.abspath(__file__))
            plugin_path = os.path.join(here, "..", "plugins", "py_detect.py")
            if not os.path.exists(plugin_path):
                self._py_detect = False
                return None
            spec = importlib.util.spec_from_file_location("py_detect_server", plugin_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self._py_detect = mod
            return mod
        except Exception:
            self._py_detect = False
            return None

    def _script(self, uri: str, text: Optional[str] = None):
        jedi = self._get_jedi()
        if jedi is None:
            return None
        path = uri_to_path(uri)
        code = text if text is not None else self.documents.get(uri, "")
        return jedi.Script(code=code, path=path, project=self._get_project())

    # ── 消息分发: 返回要写出的消息列表 ──
    def handle(self, msg: Dict[str, Any]) -> List[Dict[str, Any]]:
        method = msg.get("method")
        msg_id = msg.get("id")
        params = msg.get("params") or {}

        # 客户端不应向服务器发响应; 防御性忽略
        if method is None and msg_id is not None:
            return []

        if method == "initialize":
            root_uri = params.get("rootUri") or ""
            if root_uri:
                self.root_path = uri_to_path(root_uri)
            return [self._reply(msg_id, {"capabilities": self._capabilities()})]

        if method == "initialized":
            return []

        if method == "shutdown":
            self._shutdown = True
            return [self._reply(msg_id, None)]

        if method == "exit":
            self._shutdown = True
            return []  # 进程层据此退出

        if method == "textDocument/didOpen":
            td = params.get("textDocument", {})
            uri = td.get("uri", "")
            self.documents[uri] = td.get("text", "")
            return self._diag_push(uri)

        if method == "textDocument/didChange":
            uri = (params.get("textDocument", {}) or {}).get("uri", "")
            changes = params.get("contentChanges") or []
            if changes:
                self.documents[uri] = changes[-1].get("text", "")
            return self._diag_push(uri)

        if method == "textDocument/didClose":
            uri = (params.get("textDocument", {}) or {}).get("uri", "")
            self.documents.pop(uri, None)
            return []

        if method == "textDocument/completion":
            return [self._reply(msg_id, self._completion(params))]

        if method == "textDocument/definition":
            return [self._reply(msg_id, self._definition(params))]

        if method == "textDocument/references":
            return [self._reply(msg_id, self._references(params))]

        if method == "textDocument/hover":
            return [self._reply(msg_id, self._hover(params))]

        if msg_id is not None:
            return [self._reply(msg_id, None,
                                error={"code": -32601, "message": f"未知方法: {method}"})]
        return []

    def _reply(self, msg_id, result, error=None) -> Dict[str, Any]:
        msg = {"jsonrpc": "2.0", "id": msg_id}
        if error is not None:
            msg["error"] = error
        else:
            msg["result"] = result
        return msg

    def _capabilities(self) -> Dict[str, Any]:
        return {
            "textDocumentSync": {"openClose": True, "change": 1},  # 1 = full
            "completionProvider": {"triggerCharacters": [".", "(", ","]},
            "definitionProvider": True,
            "referencesProvider": True,
            "hoverProvider": True,
        }

    # ── py_detect 诊断 → publishDiagnostics 推送 ──
    def _diag_push(self, uri: str) -> List[Dict[str, Any]]:
        pd = self._load_py_detect()
        text = self.documents.get(uri, "")
        diags = []
        if pd is not None:
            try:
                issues = pd.analyze(text, uri_to_path(uri) or "<buffer>")
                sev_map = {"错误": 1, "警告": 2, "提示": 4, "信息": 3}
                for d in issues:
                    line0 = max(int(d.get("line", 1)) - 1, 0)
                    col0 = max(int(d.get("col", 1)) - 1, 0)
                    sev = sev_map.get(d.get("severity", "警告"), 2)
                    message = "[{}] {}{}".format(
                        d.get("code", "?"),
                        d.get("title", ""),
                        (" — " + d.get("fix", "")) if d.get("fix") else "",
                    )
                    diags.append({
                        "range": {
                            "start": {"line": line0, "character": col0},
                            "end": {"line": line0, "character": col0},
                        },
                        "severity": sev,
                        "source": "py_detect",
                        "message": message,
                    })
            except Exception:
                diags = []
        if not diags:
            return []
        return [{
            "jsonrpc": "2.0",
            "method": "textDocument/publishDiagnostics",
            "params": {"uri": uri, "diagnostics": diags},
        }]

    # ── jedi 语义能力 ──
    def _position(self, params: Dict[str, Any]):
        pos = params.get("position") or {}
        return int(pos.get("line", 0) or 0), int(pos.get("character", 0) or 0)

    def _uri(self, params: Dict[str, Any]) -> str:
        return (params.get("textDocument") or {}).get("uri", "")

    def _completion(self, params: Dict[str, Any]) -> Dict[str, Any]:
        uri = self._uri(params)
        line, character = self._position(params)
        script = self._script(uri)
        if script is None:
            return {"items": []}
        try:
            completions = script.complete(line, character)
        except Exception:
            return {"items": []}
        items = []
        seen = set()
        for c in completions:
            name = getattr(c, "name", "") or ""
            if not name or name in seen:
                continue
            seen.add(name)
            ctype = getattr(c, "type", "") or ""
            detail = (getattr(c, "description", "") or "")[:120]
            items.append({
                "label": name,
                "kind": ctype,
                "detail": detail,
                "sortText": f"0{ctype}_{name}",
            })
        return {"items": items[:60]}

    def _locations(self, defs) -> List[Dict[str, Any]]:
        out = []
        for d in defs:
            module_path = getattr(d, "module_path", None)
            if module_path is None:
                continue  # 内置/无源码定义跳过
            line = getattr(d, "line", 0) or 0
            col = getattr(d, "column", 0) or 0
            out.append({
                "uri": path_to_uri(str(module_path)),
                "range": {
                    "start": {"line": line, "character": col},
                    "end": {"line": line, "character": col},
                },
            })
        return out

    def _definition(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        uri = self._uri(params)
        line, character = self._position(params)
        script = self._script(uri)
        if script is None:
            return []
        try:
            defs = script.goto(line, character)  # jedi 0.20 API
            return self._locations(defs)
        except Exception:
            return []

    def _references(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        uri = self._uri(params)
        line, character = self._position(params)
        script = self._script(uri)
        if script is None:
            return []
        try:
            refs = script.get_references(line, character)  # jedi 0.20 API
            return self._locations(refs)
        except Exception:
            return []

    def _hover(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        uri = self._uri(params)
        line, character = self._position(params)
        script = self._script(uri)
        if script is None:
            return None
        parts = []
        # 类型推断 (jedi 0.20: infer 替代 goto_definitions)
        try:
            inferred = script.infer(line, character)
            seen_types = set()
            for d in inferred[:5]:
                dname = getattr(d, "name", "")
                dtype = getattr(d, "type", "")
                key = (dname, dtype)
                if key in seen_types:
                    continue
                seen_types.add(key)
                if dtype:
                    parts.append(f"类型: {dname}: {dtype}")
        except Exception:
            pass
        # 签名
        try:
            for s in script.get_signatures(line, character)[:3]:
                stxt = getattr(s, "to_string", lambda: "")()
                if stxt:
                    parts.append(f"签名: {stxt}")
        except Exception:
            pass
        # 文档
        try:
            for h in script.help(line, character)[:3]:
                doc = getattr(h, "docstring", None)
                if doc:
                    d = doc() or ""
                    if d:
                        parts.append(d.strip()[:400])
        except Exception:
            pass
        if not parts:
            return None
        return {"contents": {"kind": "plaintext", "value": "\n\n".join(parts[:6])}}


# ══════════════════════════════════════════════
#  进程入口
# ══════════════════════════════════════════════


def main() -> None:
    server = LocalLspServer()
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    while True:
        try:
            msg = read_message(stdin)
        except Exception:
            break
        if msg is None:
            break
        try:
            outputs = server.handle(msg)
        except Exception:
            outputs = []
        for out in outputs:
            try:
                write_message(stdout, out)
            except (BrokenPipeError, OSError):
                return
        if server._shutdown and msg.get("method") == "exit":
            break


if __name__ == "__main__":
    main()
