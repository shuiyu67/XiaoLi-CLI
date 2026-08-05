"""
小狸 LSP 客户端
==============
连接外部语言服务器（Language Server Protocol），把真实的诊断 / 悬停 /
定义跳转 / 引用 / 补全喂给模型——这是对标 opencode 的 P2 收尾能力。

- transport = stdio，使用 LSP 标准的 **Content-Length 分帧** JSON-RPC
  （与 MCP 的逐行 JSON 不同！LSP 消息头是 `Content-Length: N\\r\\n\\r\\n` + N 字节 JSON）。
- 同步 + 线程安全：与 mcp_client.py 一致，契合小狸「同步主循环 + ThreadPoolExecutor」。
- 按文件扩展名路由到对应的语言服务器（python→pylsp、rust→rust-analyzer …），
  配置驱动，不绑定具体 server；未安装/启动失败不影响主程序与其他 LSP。
- 单个 server 失败不阻断其他，也不阻断主程序启动。

后续可在此文件扩展 workspace 级多文件夹、incremental 文本同步等。
"""

import os
import re
import json
import time
import threading
import subprocess
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class LspClientError(RuntimeError):
    """LSP 客户端错误"""


# 扩展名 → LSP languageId
_EXT_TO_LANG = {
    ".py": "python", ".pyi": "python",
    ".rs": "rust",
    ".ts": "typescript", ".tsx": "typescript",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".go": "go",
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp",
    ".java": "java",
    ".lua": "lua",
    ".sh": "shellscript", ".bash": "shellscript",
    ".json": "json", ".jsonc": "json",
    ".html": "html", ".htm": "html",
    ".css": "css", ".scss": "scss", ".less": "less",
    ".md": "markdown", ".markdown": "markdown",
    ".vue": "vue",
    ".rb": "ruby",
    ".php": "php",
    ".sql": "sql",
    ".yaml": "yaml", ".yml": "yaml",
    ".xml": "xml",
    ".toml": "toml",
}


def ext_to_language(path: str) -> Optional[str]:
    """从文件路径推断 LSP languageId"""
    ext = os.path.splitext(path)[1].lower()
    return _EXT_TO_LANG.get(ext)


def path_to_uri(path: str) -> str:
    """绝对路径 → file:// URI（Windows 下 file:///C:/...）"""
    abspath = os.path.abspath(path)
    # 统一为正斜杠
    norm = abspath.replace("\\", "/")
    if not norm.startswith("/"):
        norm = "/" + norm
    return "file://" + norm


def _parse_position(pos: Any) -> Tuple[int, int]:
    """兼容 {line,character} / [line,char] / (line,char) → (line, character)（0-based）"""
    if isinstance(pos, dict):
        return int(pos.get("line", 0)), int(pos.get("character", 0))
    if isinstance(pos, (list, tuple)) and len(pos) >= 2:
        return int(pos[0]), int(pos[1])
    return 0, 0


class LspClient:
    """单个语言服务器的 stdio 客户端（同步、线程安全、Content-Length 分帧）"""

    def __init__(self, name: str, command: str, args: Optional[List[str]] = None,
                 env: Optional[Dict[str, str]] = None, cwd: Optional[str] = None,
                 root_uri: Optional[str] = None, timeout: float = 30.0,
                 language_id: str = ""):
        self.name = name
        self.command = command
        self.args = list(args or [])
        self.env = env or {}
        self.cwd = cwd
        self.root_uri = root_uri
        self.timeout = timeout
        self.language_id = language_id

        self.proc = None
        self._lock = threading.RLock()
        self._next_id = 1
        self._pending: Dict[int, Dict[str, Any]] = {}
        self._reader_thread = None
        self._started = False
        self._opened: set = set()
        self._diagnostics: Dict[str, List[Dict]] = {}  # uri -> diagnostics
        self.capabilities: Dict[str, Any] = {}
        self._diag_lock = threading.Lock()

    # ── 生命周期 ──
    def start(self) -> None:
        if self._started:
            return
        full_env = dict(os.environ)
        full_env.update(self.env)
        cmd = [self.command] + self.args
        try:
            # 二进制模式：避免 CJK 字符数与 Content-Length 字节数不一致
            self.proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=self.cwd,
                env=full_env,
                bufsize=0,
            )
        except Exception as e:
            raise LspClientError(f"启动 LSP server '{self.name}' 失败: {e}")

        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()
        self._started = True

    def _reader_loop(self):
        """后台读线程：按 Content-Length 分帧解析 JSON-RPC，响应按 id 投递；
        通知（publishDiagnostics 等）走回调。"""
        try:
            while True:
                msg = self._read_message()
                if msg is None:
                    break
                self._dispatch(msg)
        except Exception:
            pass
        finally:
            with self._lock:
                pendings = list(self._pending.values())
                self._pending.clear()
            for pend in pendings:
                pend["error"] = {"code": -1, "message": "LSP server 连接断开"}
                pend["event"].set()

    def _read_message(self) -> Optional[Dict[str, Any]]:
        """从 stdout 读取一条 Content-Length 分帧消息，返回解析后的 dict 或 None(EOF)"""
        # 读头部，直到遇到空行（\r\n\r\n）
        header = b""
        while b"\r\n\r\n" not in header:
            chunk = self.proc.stdout.read(1)
            if not chunk:
                return None
            header += chunk
            if len(header) > 65536:  # 防御：头部异常大
                return None
        # 解析 Content-Length
        m = re.search(rb"Content-Length:\s*(\d+)", header)
        if not m:
            return None
        length = int(m.group(1))
        body = b""
        while len(body) < length:
            chunk = self.proc.stdout.read(length - len(body))
            if not chunk:
                return None
            body += chunk
        try:
            return json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _dispatch(self, msg: Dict[str, Any]) -> None:
        msg_id = msg.get("id")
        method = msg.get("method")
        if msg_id is not None and "method" not in msg:
            # 响应
            with self._lock:
                pend = self._pending.pop(msg_id, None)
            if pend is not None:
                if "error" in msg:
                    pend["error"] = msg["error"]
                else:
                    pend["value"] = msg.get("result")
                pend["event"].set()
            return
        # 通知（无 id 或 method 在通知里）
        if method == "textDocument/publishDiagnostics":
            params = msg.get("params", {})
            uri = params.get("uri", "")
            diags = params.get("diagnostics", [])
            with self._diag_lock:
                self._diagnostics[uri] = diags
        # 其余通知（window/logMessage 等）忽略

    def _send(self, method: str, params: Any = None,
              is_notification: bool = False) -> Optional[Any]:
        if not self._started or self.proc is None:
            raise LspClientError(f"LSP client '{self.name}' 未启动")
        with self._lock:
            pend = None
            req_id = None
            if not is_notification:
                req_id = self._next_id
                self._next_id += 1
                pend = {"event": threading.Event(), "value": None, "error": None}
                self._pending[req_id] = pend
            req = {"jsonrpc": "2.0", "method": method}
            if not is_notification:
                req["id"] = req_id
            if params is not None:
                req["params"] = params
        try:
            data = json.dumps(req, ensure_ascii=False).encode("utf-8")
            header = f"Content-Length: {len(data)}\r\n\r\n".encode("ascii")
            self.proc.stdin.write(header + data)
            self.proc.stdin.flush()
        except (BrokenPipeError, ValueError, OSError) as e:
            raise LspClientError(f"向 LSP server '{self.name}' 写入失败: {e}")
        if is_notification:
            return None
        if not pend["event"].wait(self.timeout):
            with self._lock:
                self._pending.pop(req_id, None)
            raise LspClientError(f"LSP server '{self.name}' 响应超时: {method}")
        if pend["error"]:
            err = pend["error"]
            raise LspClientError(
                f"LSP server '{self.name}' 错误 [{err.get('code')}]: {err.get('message')}")
        return pend["value"]

    # ── LSP 协议方法 ──
    def initialize(self, root_uri: Optional[str] = None) -> Dict[str, Any]:
        if root_uri:
            self.root_uri = root_uri
        result = self._send("initialize", {
            "processId": os.getpid(),
            "rootUri": self.root_uri,
            "capabilities": {
                "textDocument": {
                    "synchronization": {"dynamicRegistration": True,
                                          "didSave": True},
                    "publishDiagnostics": {"relatedInformation": True},
                    "hover": {"contentFormat": ["markdown", "plaintext"]},
                    "definition": {"linkSupport": True},
                    "references": {},
                    "completion": {"completionItem": {"snippetSupport": True}},
                },
                "workspace": {"workspaceFolders": True,
                               "configuration": True},
            },
            "clientInfo": {"name": "xiaoli-cli", "version": "8.0"},
        })
        if isinstance(result, dict):
            self.capabilities = result.get("capabilities", {}) or {}
        # 通知服务器初始化完成
        self._send("initialized", {}, is_notification=True)
        return result or {}

    def _ensure_open(self, uri: str, text: str) -> None:
        if uri in self._opened:
            # 已打开则同步最新内容（full 同步）。didChange 是通知，无需等待响应。
            self._send("textDocument/didChange", {
                "textDocument": {"uri": uri},
                "contentChanges": [{"text": text}],
            }, is_notification=True)
            return
        lang = self.language_id or "plaintext"
        # didOpen 是通知，无需等待响应
        self._send("textDocument/didOpen", {
            "textDocument": {
                "uri": uri,
                "languageId": lang,
                "version": 1,
                "text": text,
            }
        }, is_notification=True)
        self._opened.add(uri)

    def _read_file(self, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception as e:
            return f"# 无法读取文件 {file_path}: {e}"

    def diagnostics(self, file_path: str, wait: float = 2.0) -> List[Dict]:
        """返回某文件的诊断（先 didOpen 触发分析，等待并收集 publishDiagnostics）"""
        uri = path_to_uri(file_path)
        text = self._read_file(file_path)
        self._ensure_open(uri, text)
        # 等待服务器推送诊断（最多 wait 秒）
        deadline = time.time() + wait
        while time.time() < deadline:
            with self._diag_lock:
                if uri in self._diagnostics:
                    return list(self._diagnostics[uri])
            time.sleep(0.1)
        with self._diag_lock:
            return list(self._diagnostics.get(uri, []))

    def hover(self, file_path: str, line: int, character: int) -> Any:
        uri = path_to_uri(file_path)
        text = self._read_file(file_path)
        self._ensure_open(uri, text)
        return self._send("textDocument/hover", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
        })

    def definition(self, file_path: str, line: int, character: int) -> Any:
        uri = path_to_uri(file_path)
        text = self._read_file(file_path)
        self._ensure_open(uri, text)
        return self._send("textDocument/definition", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
        })

    def references(self, file_path: str, line: int, character: int) -> Any:
        uri = path_to_uri(file_path)
        text = self._read_file(file_path)
        self._ensure_open(uri, text)
        return self._send("textDocument/references", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
            "context": {"includeDeclaration": True},
        })

    def completion(self, file_path: str, line: int, character: int) -> Any:
        uri = path_to_uri(file_path)
        text = self._read_file(file_path)
        self._ensure_open(uri, text)
        return self._send("textDocument/completion", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
        })

    def has_diagnostics(self, file_path: str) -> bool:
        uri = path_to_uri(file_path)
        with self._diag_lock:
            return bool(self._diagnostics.get(uri))

    def shutdown(self) -> None:
        if self.proc is None:
            return
        try:
            self._send("shutdown", {})
        except Exception:
            pass
        try:
            self._send("exit", {}, is_notification=True)
        except Exception:
            pass
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=3)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass
        self._started = False


class LspManager:
    """管理多个语言服务器，按文件扩展名路由诊断/智能感知请求"""

    def __init__(self):
        self.clients: Dict[str, LspClient] = {}      # language_id -> client
        self._ext_index: Dict[str, str] = {}         # ext -> language_id
        self._lock = threading.RLock()
        self._cleaned = False
        self._workspace_diag: Dict[str, List[Dict]] = {}  # file -> diagnostics（缓存）

    def connect_all(self, servers: Dict[str, Dict[str, Any]],
                    cwd: Optional[str] = None,
                    root_uri: Optional[str] = None) -> None:
        """连接所有已声明且未禁用的语言服务器。

        servers: {language_id 或扩展名: {"command", "args", "env", "cwd", "disabled", "languageId"}}
        键若是扩展名（以 '.' 开头）则直接登记该扩展名；否则视为 languageId，
        并把其常见扩展名都映射到它。
        """
        for key, spec in servers.items():
            if not isinstance(spec, dict):
                continue
            if spec.get("disabled"):
                logger.info(f"LSP server '{key}' 已禁用，跳过")
                continue
            command = spec.get("command")
            if not command:
                logger.warning(f"LSP server '{key}' 缺少 command，跳过")
                continue
            args = spec.get("args") or []
            env = spec.get("env") or {}
            server_cwd = spec.get("cwd") or cwd
            explicit_lang = spec.get("languageId") or ""
            if key.startswith("."):
                lang_id = explicit_lang or (ext_to_language(key) or key[1:])
                self._ext_index[key.lower()] = lang_id
            else:
                lang_id = key
                for ext, lid in _EXT_TO_LANG.items():
                    if lid == lang_id:
                        self._ext_index[ext] = lang_id
            if lang_id in self.clients:
                continue  # 同一语言只起一个 server
            client = LspClient(lang_id, command, args, env, server_cwd,
                               root_uri=root_uri, language_id=lang_id)
            try:
                client.start()
                client.initialize()
                with self._lock:
                    self.clients[lang_id] = client
                logger.info(f"已连接 LSP server '{lang_id}' ({command})")
            except Exception as e:
                try:
                    client.shutdown()
                except Exception:
                    pass
                logger.error(f"连接 LSP server '{lang_id}' 失败: {e}")

    def _resolve_client(self, file_path: str) -> Optional[LspClient]:
        ext = os.path.splitext(file_path)[1].lower()
        with self._lock:
            lang_id = self._ext_index.get(ext)
            if lang_id:
                return self.clients.get(lang_id)
        # 退化：按 languageId 推断
        lid = ext_to_language(file_path)
        if lid:
            with self._lock:
                return self.clients.get(lid)
        return None

    def _format_diagnostics(self, file_path: str, diags: List[Dict]) -> str:
        if not diags:
            return f"✅ {file_path}：无诊断（未发现问题）"
        lines = [f"🔍 {file_path}：{len(diags)} 条诊断"]
        for d in diags:
            rng = d.get("range", {}).get("start", {})
            ln = rng.get("line", "?")
            ch = rng.get("character", "?")
            sev = d.get("severity", 1)
            sev_map = {1: "错误", 2: "警告", 3: "信息", 4: "提示"}
            label = sev_map.get(sev, "问题")
            msg = d.get("message", "")
            src = d.get("source", "")
            src_tag = f" [{src}]" if src else ""
            lines.append(f"  {label}{src_tag} L{ln + 1}:{ch + 1} — {msg}")
        return "\n".join(lines)

    def diagnostics(self, file_path: str, wait: float = 2.0) -> str:
        client = self._resolve_client(file_path)
        if client is None:
            return (f"⚠️ 没有为 {file_path} 配置 LSP server"
                    f"（在 config.json 的 lspServers 中添加对应语言）")
        diags = client.diagnostics(file_path, wait)
        text = self._format_diagnostics(file_path, diags)
        # 缓存，供系统提示自动注入
        with self._lock:
            self._workspace_diag[file_path] = diags
        return text

    def hover(self, file_path: str, line: int, character: int) -> str:
        client = self._resolve_client(file_path)
        if client is None:
            return f"⚠️ 没有为 {file_path} 配置 LSP server"
        try:
            res = client.hover(file_path, line, character)
        except Exception as e:
            return f"❌ hover 失败: {e}"
        return self._format_hover(res)

    def definition(self, file_path: str, line: int, character: int) -> str:
        client = self._resolve_client(file_path)
        if client is None:
            return f"⚠️ 没有为 {file_path} 配置 LSP server"
        try:
            res = client.definition(file_path, line, character)
        except Exception as e:
            return f"❌ definition 失败: {e}"
        return self._format_locations(res, "定义")

    def references(self, file_path: str, line: int, character: int) -> str:
        client = self._resolve_client(file_path)
        if client is None:
            return f"⚠️ 没有为 {file_path} 配置 LSP server"
        try:
            res = client.references(file_path, line, character)
        except Exception as e:
            return f"❌ references 失败: {e}"
        return self._format_locations(res, "引用")

    def completion(self, file_path: str, line: int, character: int) -> str:
        client = self._resolve_client(file_path)
        if client is None:
            return f"⚠️ 没有为 {file_path} 配置 LSP server"
        try:
            res = client.completion(file_path, line, character)
        except Exception as e:
            return f"❌ completion 失败: {e}"
        return self._format_completion(res)

    @staticmethod
    def _format_hover(res: Any) -> str:
        if not res:
            return "（无 hover 信息）"
        contents = res.get("contents") if isinstance(res, dict) else None
        if isinstance(contents, str):
            return contents
        if isinstance(contents, dict):
            return contents.get("value", "") or json.dumps(contents, ensure_ascii=False)
        if isinstance(contents, list):
            parts = []
            for c in contents:
                if isinstance(c, str):
                    parts.append(c)
                elif isinstance(c, dict):
                    parts.append(c.get("value", ""))
            return "\n".join(p for p in parts if p)
        return json.dumps(res, ensure_ascii=False)

    @staticmethod
    def _format_locations(res: Any, label: str) -> str:
        if not res:
            return f"（无{label}）"
        items = res if isinstance(res, list) else [res]
        out = [f"{label}位置（{len(items)}）："]
        for it in items:
            loc = it.get("location", it) if isinstance(it, dict) else {}
            uri = loc.get("uri", "")
            rng = loc.get("range", {}).get("start", {})
            ln = rng.get("line", "?")
            ch = rng.get("character", "?")
            fp = uri.replace("file://", "") if uri.startswith("file://") else uri
            out.append(f"  {fp} L{ln + 1}:{ch + 1}")
        return "\n".join(out)

    @staticmethod
    def _format_completion(res: Any) -> str:
        if not res:
            return "（无补全项）"
        if isinstance(res, dict):
            items = res.get("items", [])
        elif isinstance(res, list):
            items = res
        else:
            items = []
        if not items:
            return "（无补全项）"
        out = [f"补全项（{len(items)}）："]
        for it in items[:30]:
            label = it.get("label", "")
            kind = it.get("kind", "")
            detail = it.get("detail", "")
            txt = f"  {label}"
            if detail:
                txt += f" — {detail}"
            elif kind:
                txt += f" (kind={kind})"
            out.append(txt)
        return "\n".join(out)

    def get_context(self) -> str:
        """返回所有已分析文件的诊断汇总，用于注入系统提示"""
        with self._lock:
            entries = list(self._workspace_diag.items())
        if not entries:
            return ""
        blocks = []
        for fp, diags in entries:
            if diags:
                blocks.append(self._format_diagnostics(fp, diags))
        return "\n\n".join(blocks)

    def get_servers(self) -> List[str]:
        with self._lock:
            return list(self.clients.keys())

    def cleanup(self) -> None:
        with self._lock:
            if self._cleaned:
                return
            self._cleaned = True
            clients = list(self.clients.values())
            self.clients.clear()
            self._ext_index.clear()
            self._workspace_diag.clear()
        for client in clients:
            try:
                client.shutdown()
            except Exception:
                pass
