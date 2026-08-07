"""
小狸 MCP 客户端
===============
连接外部 MCP (Model Context Protocol) server，将其工具桥接进小狸的统一工具体系。

- transport = stdio（subprocess + 逐行 JSON-RPC 2.0），与项目根 mcp_server.py（暴露侧）对称。
- 同步 + 线程安全：契合小狸「同步主循环 + ThreadPoolExecutor」模型，不引入官方 mcp SDK
  （其 asyncio 风格与现有同步调用链不搭）。
- 单个 server 失败不阻断其他 server，也不阻断主程序启动。

后续可在此文件扩展 SSE / HTTP transport（McpClient 子类即可）。
"""

import os
import json
import time
import threading
import subprocess
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "2024-11-05"


class McpClientError(RuntimeError):
    """MCP 客户端错误"""


class McpClient:
    """单个 MCP server 的 stdio 客户端（同步、线程安全）"""

    def __init__(self, name: str, command: str, args: Optional[List[str]] = None,
                 env: Optional[Dict[str, str]] = None, cwd: Optional[str] = None,
                 timeout: float = 30.0):
        self.name = name
        self.command = command
        self.args = list(args or [])
        self.env = env or {}
        self.cwd = cwd
        self.timeout = timeout

        self.proc = None
        self._lock = threading.RLock()
        self._next_id = 1
        self._pending: Dict[int, Dict[str, Any]] = {}
        self._reader_thread = None
        self._started = False

    # ── 生命周期 ──
    def start(self) -> None:
        """启动子进程并开启 reader 线程"""
        if self._started:
            return
        full_env = dict(os.environ)
        full_env.update(self.env)
        cmd = [self.command] + self.args
        try:
            self.proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=self.cwd,
                env=full_env,
                text=True,
                encoding="utf-8",
                bufsize=1,
            )
        except Exception as e:
            raise McpClientError(f"启动 MCP server '{self.name}' 失败: {e}")

        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()
        self._started = True

    def _reader_loop(self):
        """后台读线程：逐行解析 JSON-RPC 响应，按 id 投递到 _pending 表"""
        try:
            for raw in self.proc.stdout:
                line = raw.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    # 容错：跳过 server 可能混入 stdout 的非 JSON 噪声
                    continue
                msg_id = msg.get("id")
                if msg_id is None:
                    # 通知（如进度），忽略
                    continue
                with self._lock:
                    pend = self._pending.pop(msg_id, None)
                if pend is not None:
                    if "error" in msg:
                        pend["error"] = msg["error"]
                    else:
                        pend["value"] = msg.get("result")
                    pend["event"].set()
        except Exception:
            pass
        finally:
            # 连接断开：唤醒所有等待中的请求，避免永久阻塞
            with self._lock:
                pendings = list(self._pending.values())
                self._pending.clear()
            for pend in pendings:
                pend["error"] = {"code": -1, "message": "MCP server 连接断开"}
                pend["event"].set()

    def _send(self, method: str, params: Any = None,
              is_notification: bool = False) -> Optional[Any]:
        """发送一个 JSON-RPC 请求；非通知则等待响应（带超时）"""
        if not self._started or self.proc is None:
            raise McpClientError(f"MCP client '{self.name}' 未启动")

        with self._lock:
            if is_notification:
                req = {"jsonrpc": "2.0", "method": method, "params": params or {}}
                pend = None
                req_id = None
            else:
                req_id = self._next_id
                self._next_id += 1
                pend = {"event": threading.Event(), "value": None, "error": None}
                self._pending[req_id] = pend
                req = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or {}}

        try:
            self.proc.stdin.write(json.dumps(req, ensure_ascii=False) + "\n")
            self.proc.stdin.flush()
        except (BrokenPipeError, ValueError, OSError) as e:
            raise McpClientError(f"向 MCP server '{self.name}' 写入失败: {e}")

        if is_notification:
            return None

        if not pend["event"].wait(self.timeout):
            with self._lock:
                self._pending.pop(req_id, None)
            raise McpClientError(f"MCP server '{self.name}' 响应超时: {method}")
        if pend["error"]:
            err = pend["error"]
            raise McpClientError(
                f"MCP server '{self.name}' 错误 [{err.get('code')}]: {err.get('message')}")
        return pend["value"]

    # ── MCP 协议方法 ──
    def initialize(self) -> Dict[str, Any]:
        """握手：协商协议版本并通知初始化完成"""
        result = self._send("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "xiaoli-cli", "version": "8.0.3"},
        })
        # 通知 server 初始化完成（无响应，无需等待）
        self._send("notifications/initialized", {}, is_notification=True)
        return result or {}

    def list_tools(self) -> List[Dict[str, Any]]:
        """列出 server 提供的工具定义"""
        result = self._send("tools/list", {})
        if isinstance(result, dict):
            return result.get("tools", [])
        return []

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """调用一个工具，返回文本结果"""
        result = self._send("tools/call", {"name": tool_name, "arguments": arguments or {}})
        return self._extract_content(result)

    @staticmethod
    def _extract_content(result: Any) -> str:
        """从 tools/call 的 result 提取文本结果"""
        if result is None:
            return ""
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            content = result.get("content")
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text" or "text" in item:
                            parts.append(str(item.get("text", "")))
                return "\n".join(p for p in parts if p)
            if isinstance(result.get("content"), str):
                return result["content"]
            # 部分 server 直接把结果放 result 顶层
            if "isError" in result and result.get("isError"):
                return f"[工具错误] {json.dumps(result, ensure_ascii=False)}"
            return json.dumps(result, ensure_ascii=False)
        return str(result)

    def ping(self) -> bool:
        try:
            self._send("ping", {})
            return True
        except Exception:
            return False

    def stop(self) -> None:
        """优雅关闭子进程，失败则强杀"""
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


class McpClientManager:
    """管理多个外部 MCP server 客户端（按配置并发连接、聚合工具）"""

    def __init__(self):
        self.clients: Dict[str, McpClient] = {}
        self._tool_index: List[Tuple[str, Dict[str, Any]]] = []  # (server_name, tool_def)
        self._lock = threading.RLock()
        self._cleaned = False

    def connect_all(self, servers: Dict[str, Dict[str, Any]],
                    cwd: Optional[str] = None) -> None:
        """连接所有已声明且未禁用的 server。单个失败不阻断其他。

        servers: {name: {"command", "args", "env", "cwd", "disabled"}}
        """
        for name, spec in servers.items():
            if not isinstance(spec, dict):
                continue
            if spec.get("disabled"):
                logger.info(f"MCP server '{name}' 已禁用，跳过")
                continue
            command = spec.get("command")
            if not command:
                logger.warning(f"MCP server '{name}' 缺少 command，跳过")
                continue
            args = spec.get("args") or []
            env = spec.get("env") or {}
            server_cwd = spec.get("cwd") or cwd
            client = McpClient(name, command, args, env, server_cwd)
            try:
                client.start()
                client.initialize()
                tools = client.list_tools()
                with self._lock:
                    self.clients[name] = client
                    for tool in tools:
                        self._tool_index.append((name, tool))
                logger.info(f"已连接 MCP server '{name}': {len(tools)} 个工具")
            except Exception as e:
                try:
                    client.stop()
                except Exception:
                    pass
                logger.error(f"连接 MCP server '{name}' 失败: {e}")
                # 不向上抛，继续下一个 server

    def get_all_tools(self) -> List[Tuple[str, Dict[str, Any]]]:
        """返回 [(server_name, tool_def), ...]"""
        with self._lock:
            return list(self._tool_index)

    def get_servers(self) -> List[str]:
        with self._lock:
            return list(self.clients.keys())

    def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> str:
        with self._lock:
            client = self.clients.get(server_name)
        if client is None:
            raise McpClientError(f"未连接的 MCP server: {server_name}")
        return client.call_tool(tool_name, arguments)

    def cleanup(self) -> None:
        """幂等：终止所有子进程。每个桥接工具的 shutdown 都会调一次，故必须可重入。"""
        with self._lock:
            if self._cleaned:
                return
            self._cleaned = True
            clients = list(self.clients.values())
            self.clients.clear()
            self._tool_index.clear()
        for client in clients:
            try:
                client.stop()
            except Exception:
                pass
