"""
Operit Runtime for Python — 跨平台兼容层
==========================================
将 Operit AI 的 TypeScript 工具脚本 API 全面映射到 Python，
使翻译后的 Python 脚本可在 Windows / macOS / Linux 上运行。

核心映射:
  complete(result)        → 返回结果字典
  exports                 → 模块级工具注册
  OkHttp                  → requests/httpx 封装
  Tools.System.*          → OS 系统操作
  Tools.Files.*           → 文件系统操作
  Tools.Net.*             → 网络请求 + 浏览器自动化
  Tools.UI.*              → 桌面 UI 自动化 (pyautogui 降级)
  Tools.Memory.*          → 记忆库 (SQLite)
  Tools.FFmpeg.*          → FFmpeg 子进程
  Tools.Workflow.*        → 工作流引擎
  Tools.Chat.*            → 对话管理
  Tools.SoftwareSettings.* → 配置管理
  Tools.Tasker.*          → 任务调度
"""

import os
import sys
import json
import time
import shutil
import base64
import hashlib
import platform
import subprocess
import tempfile
import asyncio
import re
import glob
import zipfile
import sqlite3
import traceback
import inspect
import importlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union, Callable

# 导入 Android 兼容层
_ANDROID_COMPAT_AVAILABLE = False
try:
    import android_compat
    _ANDROID_COMPAT_AVAILABLE = True
except ImportError:
    android_compat = None

# ── 第三方依赖（可选导入） ──
try:
    import requests
except ImportError:
    requests = None

try:
    import httpx
except ImportError:
    httpx = None

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    from playwright.sync_api import sync_playwright
    from playwright.async_api import async_playwright
except ImportError:
    sync_playwright = None
    async_playwright = None


# ═══════════════════════════════════════════════════════════════
#  全局状态
# ═══════════════════════════════════════════════════════════════

# 临时目录（对应 Operit 的 OPERIT_CLEAN_ON_EXIT_DIR）
OPERIT_CLEAN_ON_EXIT_DIR = tempfile.mkdtemp(prefix="operit_")

# 结果回调
_result_holder: Dict[str, Any] = {"result": None, "called": False}


def complete(result: Any) -> None:
    """Operit 的结果回调函数。Python 版直接存储结果。"""
    _result_holder["result"] = result
    _result_holder["called"] = True


def _reset_result() -> None:
    _result_holder["result"] = None
    _result_holder["called"] = False


def _get_result() -> Any:
    return _result_holder["result"]


# ═══════════════════════════════════════════════════════════════
#  Console 兼容
# ═══════════════════════════════════════════════════════════════

class _Console:
    def log(self, *args, **kwargs):
        print(*args, **kwargs)

    def error(self, *args, **kwargs):
        print(*args, file=sys.stderr, **kwargs)

    def warn(self, *args, **kwargs):
        print(*args, file=sys.stderr, **kwargs)

    def info(self, *args, **kwargs):
        print(*args, **kwargs)


console = _Console()


# ═══════════════════════════════════════════════════════════════
#  OkHttp 兼容层
# ═══════════════════════════════════════════════════════════════

class OkHttpResponse:
    """模拟 Operit OkHttp 的 Response 对象"""

    def __init__(self, status_code: int, content: str, headers: dict = None):
        self.statusCode = status_code
        self.content = content
        self._headers = headers or {}

    def isSuccessful(self) -> bool:
        return 200 <= self.statusCode < 300

    def headers(self) -> dict:
        return self._headers

    def header(self, name: str) -> str:
        return self._headers.get(name, "")


class OkHttpRequest:
    """模拟 Operit OkHttp 的 Request 构建器"""

    def __init__(self, client):
        self._client = client
        self._url = ""
        self._method = "GET"
        self._body_data = None
        self._body_type = None
        self._headers = {}

    def url(self, url: str) -> "OkHttpRequest":
        self._url = url
        return self

    def method(self, method: str) -> "OkHttpRequest":
        self._method = method.upper()
        return self

    def body(self, data: Any, encoding: str = "json") -> "OkHttpRequest":
        self._body_data = data
        self._body_type = encoding
        return self

    def headers(self, headers: dict) -> "OkHttpRequest":
        self._headers = headers
        return self

    def build(self) -> "OkHttpRequest":
        return self

    def execute(self) -> OkHttpResponse:
        """同步执行请求"""
        if requests is None and httpx is None:
            raise RuntimeError("需要安装 requests 或 httpx: pip install requests")

        lib = requests or httpx
        kwargs = {"headers": self._headers}

        if self._body_data is not None:
            if self._body_type == "json":
                kwargs["json"] = self._body_data
            elif self._body_type == "form":
                kwargs["data"] = self._body_data
            else:
                kwargs["data"] = self._body_data

        if self._method == "GET":
            resp = lib.get(self._url, **kwargs)
        elif self._method == "POST":
            resp = lib.post(self._url, **kwargs)
        elif self._method == "PUT":
            resp = lib.put(self._url, **kwargs)
        elif self._method == "DELETE":
            resp = lib.delete(self._url, **kwargs)
        elif self._method == "PATCH":
            resp = lib.patch(self._url, **kwargs)
        else:
            resp = lib.request(self._method, self._url, **kwargs)

        return OkHttpResponse(
            status_code=resp.status_code,
            content=resp.text,
            headers=dict(resp.headers)
        )


class OkHttpClient:
    """模拟 Operit OkHttp 的 Client 对象"""

    def __init__(self, base_url: str = ""):
        self._base_url = base_url

    def newRequest(self) -> OkHttpRequest:
        return OkHttpRequest(self)

    def newRequest(self) -> OkHttpRequest:
        return OkHttpRequest(self)


class OkHttpBuilder:
    """模拟 Operit OkHttp.newBuilder() 链式构建器"""

    def __init__(self):
        self._base_url = ""

    def baseUrl(self, url: str) -> "OkHttpBuilder":
        self._base_url = url
        return self

    def build(self) -> OkHttpClient:
        return OkHttpClient(self._base_url)


class _OkHttp:
    """OkHttp 全局对象"""

    @staticmethod
    def newBuilder() -> OkHttpBuilder:
        return OkHttpBuilder()

    @staticmethod
    def newClient() -> OkHttpClient:
        return OkHttpClient()


OkHttp = _OkHttp()


# ═══════════════════════════════════════════════════════════════
#  Tools.System
# ═══════════════════════════════════════════════════════════════

class _TerminalSession:
    """终端会话管理"""

    def __init__(self, name: str):
        self.name = name
        self.id = name
        self._process = None
        self._output = ""
        self._env = os.environ.copy()

    def exec(self, command: str, timeout: int = 30) -> dict:
        """执行命令并返回结果"""
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout, env=self._env
            )
            self._output = result.stdout + result.stderr
            return {
                "returnCode": result.returncode,
                "output": self._output
            }
        except subprocess.TimeoutExpired:
            return {"returnCode": -1, "output": "Command timed out"}
        except Exception as e:
            return {"returnCode": -1, "output": str(e)}

    def hiddenExec(self, command: str, options: dict = None) -> dict:
        """静默执行命令"""
        timeout = (options or {}).get("timeout", 30)
        return self.exec(command, timeout)

    def screen(self) -> str:
        """获取终端屏幕内容"""
        return self._output

    def input(self, params: dict) -> str:
        """向终端输入"""
        text = params.get("text", "")
        key = params.get("key", "")
        if text:
            self._output += text
        return self._output


class _Terminal:
    """Tools.System.terminal"""

    def __init__(self):
        self._sessions: Dict[str, _TerminalSession] = {}

    def create(self, name: str) -> str:
        session = _TerminalSession(name)
        self._sessions[name] = session
        return name

    def exec(self, session_id: str, command: str, timeout: int = 30) -> dict:
        session = self._sessions.get(session_id)
        if not session:
            return {"returnCode": -1, "output": f"Session {session_id} not found"}
        return session.exec(command, timeout)

    def hiddenExec(self, command: str, options: dict = None) -> dict:
        session = _TerminalSession("hidden")
        return session.hiddenExec(command, options)

    def screen(self, session_id: str) -> str:
        session = self._sessions.get(session_id)
        if not session:
            return ""
        return session.screen()

    def input(self, session_id: str, params: dict) -> str:
        session = self._sessions.get(session_id)
        if not session:
            return ""
        return session.input(params)


class _Bluetooth:
    """Tools.System.bluetooth — 桌面端降级实现"""

    def requestPermission(self): return {"success": False, "message": "Bluetooth not supported on desktop"}
    def getState(self): return {"success": False, "message": "Bluetooth not supported on desktop"}
    def requestEnable(self): return {"success": False, "message": "Bluetooth not supported on desktop"}
    def listBondedDevices(self): return {"success": False, "message": "Bluetooth not supported on desktop"}
    def scan(self, params): return {"success": False, "message": "Bluetooth not supported on desktop"}
    def connect(self, params): return {"success": False, "message": "Bluetooth not supported on desktop"}
    def listen(self, params): return {"success": False, "message": "Bluetooth not supported on desktop"}
    def accept(self, session_id, timeout): return {"success": False, "message": "Bluetooth not supported on desktop"}
    def send(self, session_id, params): return {"success": False, "message": "Bluetooth not supported on desktop"}
    def read(self, session_id, params): return {"success": False, "message": "Bluetooth not supported on desktop"}
    def sendAndRead(self, session_id, params): return {"success": False, "message": "Bluetooth not supported on desktop"}
    def close(self, session_id): return {"success": False, "message": "Bluetooth not supported on desktop"}

    @property
    def ble(self):
        return _BluetoothBLE()


class _BluetoothBLE:
    """Tools.System.bluetooth.ble — 桌面端降级实现"""
    def connect(self, params): return {"success": False, "message": "BLE not supported on desktop"}
    def discoverServices(self, session_id, timeout): return {"success": False, "message": "BLE not supported on desktop"}
    def readCharacteristic(self, session_id, params): return {"success": False, "message": "BLE not supported on desktop"}
    def writeCharacteristic(self, session_id, params): return {"success": False, "message": "BLE not supported on desktop"}
    def writeAndReadCharacteristic(self, session_id, params): return {"success": False, "message": "BLE not supported on desktop"}
    def subscribe(self, session_id, params): return {"success": False, "message": "BLE not supported on desktop"}
    def readNotifications(self, session_id, limit): return {"success": False, "message": "BLE not supported on desktop"}


class _ToolsSystem:
    """Tools.System — 跨平台系统操作"""

    def __init__(self):
        self.terminal = _Terminal()
        self.bluetooth = _Bluetooth()

    async def getDeviceInfo(self) -> dict:
        return {
            "model": platform.node(),
            "os": f"{platform.system()} {platform.release()}",
            "version": platform.version(),
            "manufacturer": platform.machine(),
            "platform": sys.platform,
            "python": sys.version
        }

    async def sleep(self, ms: float) -> None:
        await asyncio.sleep(ms / 1000.0)

    async def shell(self, command: str) -> str:
        """执行 shell 命令并返回输出"""
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=60
            )
            return result.stdout + result.stderr
        except Exception as e:
            return str(e)

    async def exec(self, command: str) -> str:
        return await self.shell(command)

    async def getSetting(self, name: str, namespace: str = "system") -> str:
        """桌面端降级：返回空字符串"""
        return ""

    async def setSetting(self, name: str, value: str, namespace: str = "system") -> dict:
        return {"success": False, "message": "System settings not supported on desktop"}

    async def installApp(self, path: str) -> dict:
        return {"success": False, "message": "App installation not supported on desktop"}

    async def uninstallApp(self, package_name: str) -> dict:
        return {"success": False, "message": "App uninstallation not supported on desktop"}

    async def listApps(self, include_system: bool = False) -> list:
        return []

    async def startApp(self, package_name: str, activity: str = None) -> dict:
        return {"success": False, "message": "App launch not supported on desktop"}

    async def stopApp(self, package_name: str) -> dict:
        return {"success": False, "message": "App stop not supported on desktop"}

    async def sendBroadcast(self, params: dict) -> dict:
        return {"success": False, "message": "Broadcast not supported on desktop"}

    async def intent(self, params: dict) -> dict:
        return {"success": False, "message": "Intent not supported on desktop"}

    async def getNotifications(self, limit: int = 10, include_ongoing: bool = False) -> list:
        return []

    async def getAppUsageTime(self, params: dict) -> list:
        return []

    async def getLocation(self, high_accuracy: bool = False, timeout: int = 10) -> dict:
        return {"success": False, "message": "Location not supported on desktop"}

    async def usePackage(self, package_name: str) -> dict:
        return {"success": False, "message": "Package system not supported on desktop"}


# ═══════════════════════════════════════════════════════════════
#  Tools.Files
# ═══════════════════════════════════════════════════════════════

class _ToolsFiles:
    """Tools.Files — 跨平台文件操作"""

    async def read(self, path_or_params) -> dict:
        """读取文件内容"""
        if isinstance(path_or_params, dict):
            path = path_or_params.get("path", "")
        else:
            path = path_or_params
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def write(self, path: str, content: str, append: bool = False) -> dict:
        """写入文件"""
        try:
            mode = "a" if append else "w"
            with open(path, mode, encoding="utf-8") as f:
                f.write(content)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def readBinary(self, path: str, environment: str = None) -> dict:
        """读取二进制文件，返回 base64"""
        try:
            with open(path, "rb") as f:
                data = f.read()
            return {"success": True, "content": base64.b64encode(data).decode("utf-8")}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def writeBinary(self, path: str, base64_data: str, environment: str = None) -> dict:
        """写入二进制文件（从 base64）"""
        try:
            data = base64.b64decode(base64_data)
            with open(path, "wb") as f:
                f.write(data)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def exists(self, path: str, environment: str = None) -> dict:
        """检查文件/目录是否存在"""
        return {"exists": os.path.exists(path), "success": True}

    async def mkdir(self, path: str, recursive: bool = False, environment: str = None) -> dict:
        """创建目录"""
        try:
            if recursive:
                os.makedirs(path, exist_ok=True)
            else:
                os.mkdir(path)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def deleteFile(self, path: str, recursive: bool = False, environment: str = None) -> dict:
        """删除文件或目录"""
        try:
            if os.path.isdir(path):
                if recursive:
                    shutil.rmtree(path)
                else:
                    os.rmdir(path)
            else:
                os.remove(path)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def list(self, path: str, environment: str = None) -> dict:
        """列出目录内容"""
        try:
            entries = []
            for entry in os.listdir(path):
                full_path = os.path.join(path, entry)
                entries.append({
                    "name": entry,
                    "path": full_path,
                    "isDirectory": os.path.isdir(full_path),
                    "size": os.path.getsize(full_path) if os.path.isfile(full_path) else 0
                })
            return {"success": True, "entries": entries}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def find(self, directory: str, pattern: str) -> list:
        """查找匹配模式的文件"""
        if directory == "~":
            directory = os.path.expanduser("~")
        search_pattern = os.path.join(directory, "**", pattern)
        return glob.glob(search_pattern, recursive=True)

    async def move(self, source: str, destination: str, environment: str = None) -> dict:
        """移动文件/目录"""
        try:
            shutil.move(source, destination)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def copy(self, source: str, destination: str, recursive: bool = False,
                   source_env: str = None, dest_env: str = None) -> dict:
        """复制文件/目录"""
        try:
            if os.path.isdir(source):
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def info(self, path: str, environment: str = None) -> dict:
        """获取文件信息"""
        try:
            stat = os.stat(path)
            return {
                "success": True,
                "exists": True,
                "size": stat.st_size,
                "isDirectory": os.path.isdir(path),
                "isFile": os.path.isfile(path),
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
                "path": path,
                "name": os.path.basename(path)
            }
        except Exception as e:
            return {"success": False, "message": str(e), "exists": False}

    async def download(self, url: str, file_path: str) -> dict:
        """下载文件"""
        try:
            lib = requests or (httpx if httpx else None)
            if lib is None:
                raise RuntimeError("需要 requests 或 httpx")
            resp = lib.get(url, stream=True)
            resp.raise_for_status()
            os.makedirs(os.path.dirname(file_path), exist_ok=True) if os.path.dirname(file_path) else None
            with open(file_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return {"success": True, "path": file_path}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def zip(self, source: str, destination: str, environment: str = None, include_root: bool = False) -> dict:
        """压缩文件/目录"""
        try:
            with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as zf:
                if os.path.isdir(source):
                    for root, dirs, files in os.walk(source):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, source)
                            zf.write(file_path, arcname)
                else:
                    zf.write(source, os.path.basename(source))
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def unzip(self, source: str, destination: str, environment: str = None) -> dict:
        """解压文件"""
        try:
            with zipfile.ZipFile(source, "r") as zf:
                zf.extractall(destination)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def open(self, path: str, environment: str = None) -> dict:
        """用系统默认程序打开文件"""
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def share(self, path: str, title: str = "", environment: str = None) -> dict:
        """分享文件（桌面端降级为打开）"""
        return await self.open(path, environment)


# ═══════════════════════════════════════════════════════════════
#  Tools.Net
# ═══════════════════════════════════════════════════════════════

class _ToolsNet:
    """Tools.Net — 网络请求 + 浏览器自动化"""

    async def visit(self, url_or_params) -> str:
        """访问网页并返回内容"""
        if isinstance(url_or_params, dict):
            url = url_or_params.get("url", "")
        else:
            url = url_or_params
        try:
            lib = requests or (httpx if httpx else None)
            if lib is None:
                raise RuntimeError("需要 requests 或 httpx")
            resp = lib.get(url, timeout=30, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            return resp.text
        except Exception as e:
            return str(e)

    async def fetch(self, url: str, options: dict = None) -> dict:
        """HTTP 请求"""
        options = options or {}
        method = options.get("method", "GET")
        headers = options.get("headers", {})
        body = options.get("body")
        try:
            lib = requests or (httpx if httpx else None)
            if lib is None:
                raise RuntimeError("需要 requests 或 httpx")
            kwargs = {"headers": headers, "timeout": 30}
            if body:
                kwargs["data"] = body if isinstance(body, str) else json.dumps(body)
            resp = lib.request(method, url, **kwargs)
            return {
                "ok": resp.ok if hasattr(resp, 'ok') else resp.is_success,
                "status": resp.status_code,
                "text": resp.text,
                "headers": dict(resp.headers)
            }
        except Exception as e:
            return {"ok": False, "status": 0, "text": str(e)}

    async def uploadFile(self, params: dict) -> dict:
        """上传文件"""
        url = params.get("url", "")
        file_path = params.get("file", params.get("path", ""))
        field_name = params.get("field", "file")
        extra_data = params.get("data", {})
        headers = params.get("headers", {})
        try:
            lib = requests or (httpx if httpx else None)
            if lib is None:
                raise RuntimeError("需要 requests 或 httpx")
            with open(file_path, "rb") as f:
                resp = lib.post(url, files={field_name: f}, data=extra_data, headers=headers, timeout=60)
            return {"success": True, "statusCode": resp.status_code, "content": resp.text}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ── 浏览器自动化（Playwright 对齐）──

    def _check_playwright(self):
        if async_playwright is None:
            raise RuntimeError("需要安装 Playwright: pip install playwright && playwright install")

    async def browserNavigate(self, params: dict) -> str:
        self._check_playwright()
        # 实际实现需要维护一个浏览器实例池
        # 这里提供接口，具体由 browser_auto 插件或 Playwright MCP 处理
        return f"[browser] Navigate to {params.get('url', '')}"

    async def browserClick(self, params: dict) -> str:
        return f"[browser] Click {params}"

    async def browserClose(self) -> str:
        return "[browser] Closed"

    async def browserCloseAll(self) -> str:
        return "[browser] All closed"

    async def browserSnapshot(self, params: dict = None) -> str:
        return "[browser] Snapshot"

    async def browserType(self, params: dict) -> str:
        return f"[browser] Type {params}"

    async def browserPressKey(self, params: dict) -> str:
        return f"[browser] Press {params.get('key', '')}"

    async def browserFillForm(self, params: dict) -> str:
        return f"[browser] Fill form"

    async def browserHover(self, params: dict) -> str:
        return f"[browser] Hover"

    async def browserDrag(self, params: dict) -> str:
        return f"[browser] Drag"

    async def browserEvaluate(self, params: dict) -> str:
        return f"[browser] Evaluate"

    async def browserConsoleMessages(self, params: dict = None) -> str:
        return "[browser] Console messages"

    async def browserNetworkRequests(self, params: dict = None) -> str:
        return "[browser] Network requests"

    async def browserResize(self, params: dict) -> str:
        return f"[browser] Resize {params.get('width', 0)}x{params.get('height', 0)}"

    async def browserSelectOption(self, params: dict) -> str:
        return f"[browser] Select option"

    async def browserHandleDialog(self, params: dict) -> str:
        return f"[browser] Handle dialog"

    async def browserFileUpload(self, params: dict) -> str:
        return f"[browser] File upload"

    async def browserWaitFor(self, params: dict) -> str:
        return "[browser] Wait complete"

    async def browserRunCode(self, params: dict) -> str:
        return f"[browser] Run code"

    async def browserNavigateBack(self) -> str:
        return "[browser] Navigate back"

    async def browserTabs(self, params: dict) -> str:
        return f"[browser] Tabs {params.get('action', '')}"


# ═══════════════════════════════════════════════════════════════
#  Tools.UI — 桌面 UI 自动化（pyautogui 降级）
# ═══════════════════════════════════════════════════════════════

class _ToolsUI:
    """Tools.UI — 桌面端 UI 自动化"""

    async def tap(self, x: int, y: int) -> dict:
        if pyautogui:
            pyautogui.click(x, y)
            return {"success": True}
        return {"success": False, "message": "pyautogui not installed"}

    async def longPress(self, x: int, y: int) -> dict:
        if pyautogui:
            pyautogui.rightClick(x, y)
            return {"success": True}
        return {"success": False, "message": "pyautogui not installed"}

    async def clickElement(self, params: dict) -> dict:
        return {"success": False, "message": "clickElement not supported on desktop"}

    async def setText(self, text: str) -> dict:
        if pyautogui:
            pyautogui.typewrite(text)
            return {"success": True}
        return {"success": False, "message": "pyautogui not installed"}

    async def pressKey(self, key_code: str) -> dict:
        if pyautogui:
            key_map = {
                "KEYCODE_BACK": "escape",
                "KEYCODE_ENTER": "enter",
                "KEYCODE_HOME": "win",
                "KEYCODE_TAB": "tab",
                "KEYCODE_ESCAPE": "escape",
            }
            pyautogui.press(key_map.get(key_code, key_code.lower()))
            return {"success": True}
        return {"success": False, "message": "pyautogui not installed"}

    async def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int) -> dict:
        if pyautogui:
            pyautogui.moveTo(start_x, start_y)
            pyautogui.dragTo(end_x, end_y, duration=0.5)
            return {"success": True}
        return {"success": False, "message": "pyautogui not installed"}

    async def getPageInfo(self) -> dict:
        return {"success": False, "message": "getPageInfo not supported on desktop", "activity": ""}

    async def runSubAgent(self, intent: str, max_steps: int = 10,
                          agent_id: str = None, target_app: str = None) -> dict:
        return {"success": False, "message": "UI SubAgent not supported on desktop"}


# ═══════════════════════════════════════════════════════════════
#  Tools.Memory — SQLite 记忆库
# ═══════════════════════════════════════════════════════════════

class _ToolsMemory:
    """Tools.Memory — SQLite 持久化记忆"""

    def __init__(self):
        self._db_path = os.path.join(tempfile.gettempdir(), "operit_memory.db")
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT UNIQUE,
                content TEXT,
                category TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_title TEXT,
                target_title TEXT,
                relation TEXT
            )
        """)
        conn.commit()
        conn.close()

    async def create(self, params: dict) -> dict:
        try:
            conn = sqlite3.connect(self._db_path)
            now = datetime.now().isoformat()
            conn.execute(
                "INSERT OR REPLACE INTO memories (title, content, category, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (params.get("title", ""), params.get("content", ""),
                 params.get("category", ""), now, now)
            )
            conn.commit()
            conn.close()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def update(self, old_title: str, updates: dict) -> dict:
        try:
            conn = sqlite3.connect(self._db_path)
            now = datetime.now().isoformat()
            for key, value in updates.items():
                if key in ("content", "category", "title"):
                    conn.execute(f"UPDATE memories SET {key}=?, updated_at=? WHERE title=?", (value, now, old_title))
            conn.commit()
            conn.close()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def deleteMemory(self, params: dict) -> dict:
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute("DELETE FROM memories WHERE title=?", (params.get("title", ""),))
            conn.commit()
            conn.close()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def move(self, params: dict) -> dict:
        return await self.update(params.get("from", ""), {"title": params.get("to", "")})

    async def link(self, params: dict) -> dict:
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute(
                "INSERT INTO links (source_title, target_title, relation) VALUES (?, ?, ?)",
                (params.get("source", ""), params.get("target", ""), params.get("relation", ""))
            )
            conn.commit()
            conn.close()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def queryLinks(self, params: dict) -> list:
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.execute(
                "SELECT * FROM links WHERE source_title=? OR target_title=?",
                (params.get("source", ""), params.get("target", ""))
            )
            results = [{"id": r[0], "source": r[1], "target": r[2], "relation": r[3]} for r in cursor.fetchall()]
            conn.close()
            return results
        except Exception:
            return []

    async def updateLink(self, params: dict) -> dict:
        return {"success": True}

    async def deleteLink(self, params: dict) -> dict:
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute("DELETE FROM links WHERE id=?", (params.get("id", 0),))
            conn.commit()
            conn.close()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}


# ═══════════════════════════════════════════════════════════════
#  Tools.FFmpeg
# ═══════════════════════════════════════════════════════════════

class _ToolsFFmpeg:
    """Tools.FFmpeg — FFmpeg 子进程封装"""

    async def execute(self, command: str) -> dict:
        try:
            result = subprocess.run(
                f"ffmpeg {command}", shell=True, capture_output=True, text=True, timeout=300
            )
            return {"returnCode": result.returncode, "output": result.stdout + result.stderr}
        except Exception as e:
            return {"returnCode": -1, "output": str(e)}

    async def info(self) -> dict:
        try:
            result = subprocess.run(
                "ffmpeg -version", shell=True, capture_output=True, text=True, timeout=10
            )
            return {"returnCode": result.returncode, "output": result.stdout + result.stderr}
        except Exception as e:
            return {"returnCode": -1, "output": str(e)}

    async def convert(self, input_path: str, output_path: str, opts: dict = None) -> dict:
        opts = opts or {}
        cmd_parts = ["ffmpeg", "-y"]
        if opts.get("video_codec"):
            cmd_parts.extend(["-c:v", opts["video_codec"]])
        if opts.get("audio_codec"):
            cmd_parts.extend(["-c:a", opts["audio_codec"]])
        if opts.get("resolution"):
            cmd_parts.extend(["-s", opts["resolution"]])
        if opts.get("bitrate"):
            cmd_parts.extend(["-b", opts["bitrate"]])
        cmd_parts.extend(["-i", input_path, output_path])
        try:
            result = subprocess.run(" ".join(cmd_parts), shell=True, capture_output=True, text=True, timeout=300)
            return {"returnCode": result.returncode, "output": result.stdout + result.stderr}
        except Exception as e:
            return {"returnCode": -1, "output": str(e)}


# ═══════════════════════════════════════════════════════════════
#  Tools.Workflow
# ═══════════════════════════════════════════════════════════════

class _ToolsWorkflow:
    """Tools.Workflow — 工作流引擎"""

    def __init__(self):
        self._workflows: Dict[str, dict] = {}
        self._next_id = 1

    async def getAll(self) -> list:
        return list(self._workflows.values())

    async def create(self, name: str, description: str = "", nodes=None, edges=None, enabled: bool = False) -> dict:
        wf_id = str(self._next_id)
        self._next_id += 1
        wf = {
            "id": wf_id, "name": name, "description": description,
            "nodes": nodes or [], "edges": edges or [],
            "enabled": enabled, "created_at": datetime.now().isoformat()
        }
        self._workflows[wf_id] = wf
        return wf

    async def get(self, workflow_id: str) -> dict:
        return self._workflows.get(workflow_id, {"success": False, "message": "Not found"})

    async def update(self, workflow_id: str, updates: dict) -> dict:
        if workflow_id in self._workflows:
            self._workflows[workflow_id].update(updates)
            return self._workflows[workflow_id]
        return {"success": False, "message": "Not found"}

    async def patch(self, workflow_id: str, patch: dict) -> dict:
        return await self.update(workflow_id, patch)

    async def enable(self, workflow_id: str) -> dict:
        return await self.update(workflow_id, {"enabled": True})

    async def disable(self, workflow_id: str) -> dict:
        return await self.update(workflow_id, {"enabled": False})

    async def delete(self, workflow_id: str) -> dict:
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            return {"success": True}
        return {"success": False, "message": "Not found"}

    async def trigger(self, workflow_id: str) -> dict:
        wf = self._workflows.get(workflow_id)
        if wf:
            return {"success": True, "message": f"Workflow '{wf['name']}' triggered"}
        return {"success": False, "message": "Not found"}


# ═══════════════════════════════════════════════════════════════
#  Tools.Chat
# ═══════════════════════════════════════════════════════════════

class _ToolsChat:
    """Tools.Chat — 对话管理（桌面端降级）"""

    async def listChats(self, params: dict = None) -> list:
        return []

    async def findChat(self, params: dict) -> dict:
        return {"success": False, "message": "Chat not found"}

    async def getMessages(self, chat_id: str, opts: dict = None) -> list:
        return []

    async def updateTitle(self, chat_id: str, new_title: str) -> dict:
        return {"success": False, "message": "Not supported on desktop"}

    async def deleteChat(self, chat_id: str) -> dict:
        return {"success": False, "message": "Not supported on desktop"}

    async def agentStatus(self, chat_id: str) -> dict:
        return {"success": False, "message": "Not supported on desktop"}

    async def listCharacterCards(self) -> list:
        return []

    async def startService(self) -> dict:
        return {"success": False, "message": "Not supported on desktop"}

    async def createNew(self, *args) -> dict:
        return {"success": False, "message": "Not supported on desktop"}

    async def sendMessage(self, *args) -> dict:
        return {"success": False, "message": "Not supported on desktop"}


# ═══════════════════════════════════════════════════════════════
#  Tools.SoftwareSettings
# ═══════════════════════════════════════════════════════════════

class _ToolsSoftwareSettings:
    """Tools.SoftwareSettings — 配置管理（桌面端降级）"""

    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._env_vars: Dict[str, str] = {}
        self._model_configs: Dict[str, dict] = {}
        self._sandbox_packages: Dict[str, bool] = {}

    async def listSandboxPackages(self) -> list:
        return [{"packageName": k, "enabled": v} for k, v in self._sandbox_packages.items()]

    async def setSandboxPackageEnabled(self, package_name: str, enabled: bool) -> dict:
        self._sandbox_packages[package_name] = enabled
        return {"success": True}

    async def getFunctionModelConfig(self, function_type: str) -> dict:
        return self._model_configs.get(function_type, {"success": False, "message": "Not configured"})

    async def setFunctionModelConfig(self, *args) -> dict:
        return {"success": True}

    async def listModelConfigs(self) -> list:
        return list(self._model_configs.values())

    async def createModelConfig(self, options: dict) -> dict:
        config_id = str(len(self._model_configs) + 1)
        self._model_configs[config_id] = {"id": config_id, **options}
        return {"success": True, "id": config_id}

    async def updateModelConfig(self, config_id: str, updates: dict) -> dict:
        if config_id in self._model_configs:
            self._model_configs[config_id].update(updates)
            return {"success": True}
        return {"success": False, "message": "Not found"}

    async def deleteModelConfig(self, config_id: str) -> dict:
        self._model_configs.pop(config_id, None)
        return {"success": True}

    async def listFunctionModelConfigs(self) -> list:
        return []

    async def testModelConfigConnection(self, config_id: str, model_index: int = None) -> dict:
        return {"success": False, "message": "Not supported on desktop"}

    async def readEnvironmentVariable(self, key: str) -> str:
        return self._env_vars.get(key, os.environ.get(key, ""))

    async def writeEnvironmentVariable(self, key: str, value: str) -> dict:
        self._env_vars[key] = value
        return {"success": True}

    async def restartMcpWithLogs(self, timeout_ms: int = 30000) -> dict:
        return {"success": False, "message": "Not supported on desktop"}

    async def getSpeechServicesConfig(self) -> dict:
        return {}

    async def setSpeechServicesConfig(self, updates: dict) -> dict:
        return {"success": True}

    async def testTtsPlayback(self, text: str, options: dict = None) -> dict:
        return {"success": False, "message": "TTS not supported on desktop"}

    async def executeSandboxScriptDirect(self, params: dict) -> dict:
        return {"success": False, "message": "Sandbox not supported on desktop"}


# ═══════════════════════════════════════════════════════════════
#  Tools.Tasker
# ═══════════════════════════════════════════════════════════════

class _ToolsTasker:
    """Tools.Tasker — Tasker 集成（桌面端降级）"""

    async def triggerEvent(self, params: dict) -> dict:
        return {"success": False, "message": "Tasker not supported on desktop"}


# ═══════════════════════════════════════════════════════════════
#  组装 Tools 全局对象
# ═══════════════════════════════════════════════════════════════

class _Tools:
    """Tools 全局对象 — 包含所有子模块"""

    def __init__(self):
        self.System = _ToolsSystem()
        self.Files = _ToolsFiles()
        self.Net = _ToolsNet()
        self.UI = _ToolsUI()
        self.Memory = _ToolsMemory()
        self.FFmpeg = _ToolsFFmpeg()
        self.Workflow = _ToolsWorkflow()
        self.Chat = _ToolsChat()
        self.SoftwareSettings = _ToolsSoftwareSettings()
        self.Tasker = _ToolsTasker()


Tools = _Tools()


# ═══════════════════════════════════════════════════════════════
#  Exports 容器
# ═══════════════════════════════════════════════════════════════

class Exports:
    """模拟 CommonJS exports 对象"""

    def __init__(self):
        self._items: Dict[str, Any] = {}

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._items[name] = value

    def __getattr__(self, name):
        if name.startswith("_"):
            return super().__getattribute__(name)
        return self._items.get(name)

    def get(self, name: str, default=None):
        return self._items.get(name, default)

    def items(self) -> Dict[str, Any]:
        return self._items

    def keys(self):
        return self._items.keys()


# ═══════════════════════════════════════════════════════════════
#  脚本加载器
# ═══════════════════════════════════════════════════════════════

class OperitScriptLoader:
    """加载和执行 Python 版 Operit 脚本"""

    def __init__(self, scripts_dir: str = None):
        self.scripts_dir = scripts_dir or os.path.join(
            os.path.dirname(__file__), "operit_py"
        )
        self._loaded_tools: Dict[str, dict] = {}

    def load_script(self, script_path: str) -> dict:
        """加载单个脚本，返回其 METADATA 和导出的工具"""
        # 构建脚本的全局环境
        exports = Exports()
        script_globals = {
            # Operit 全局 API
            "complete": complete,
            "exports": exports,
            "console": console,
            "OkHttp": OkHttp,
            "Tools": Tools,
            "OPERIT_CLEAN_ON_EXIT_DIR": OPERIT_CLEAN_ON_EXIT_DIR,
            # Python 标准库
            "os": os, "sys": sys, "json": json, "re": re, "time": time,
            "datetime": datetime, "base64": base64, "hashlib": hashlib,
            "subprocess": subprocess, "asyncio": asyncio,
            "requests": requests, "httpx": httpx,
        }

        # 注入 Android 兼容层（如果可用）
        if _ANDROID_COMPAT_AVAILABLE and android_compat:
            android_globals = android_compat.get_android_compat_globals()
            script_globals.update(android_globals)
            # 特别注入 context 和 service 实例
            script_globals["androidContext"] = android_compat.application_context
        else:
            # 没有 android_compat 时提供空桩
            script_globals["Java"] = type("Java", (), {"type": staticmethod(
                lambda cls: type("Stub", (), {
                    "__getattr__": lambda s, n: s,
                    "__call__": lambda s, *a, **kw: s,
                    "toString": lambda s: "[Android-only]",
                })())
            })

        try:
            with open(script_path, "r", encoding="utf-8") as f:
                code = f.read()
            exec(compile(code, script_path, "exec"), script_globals)
        except Exception as e:
            return {"success": False, "message": f"加载失败: {e}", "traceback": traceback.format_exc()}

        # 提取 METADATA
        metadata = self._extract_metadata(script_path, code)

        # 提取导出的工具
        tools = {}
        for name, func in exports.items().items():
            if callable(func):
                tools[name] = {
                    "name": name,
                    "func": func,
                    "metadata": metadata
                }

        return {
            "success": True,
            "metadata": metadata,
            "tools": tools
        }

    def _extract_metadata(self, script_path: str, code: str) -> dict:
        """从脚本注释中提取 METADATA"""
        # 匹配 Python 版 METADATA 注释
        # 格式: # METADATA { ... } 或 '''METADATA { ... }'''
        patterns = [
            r'#\s*METADATA\s*(\{.*?\})\s*#',  # 单行注释
            r'#\s*METADATA\s*\n(.*?)(?=\n#(?!\s)|\n\ndef |\Z)',  # 多行注释
            r"'''\s*METADATA\s*(\{.*?\})\s*'''",  # 三引号
            r'"""\s*METADATA\s*(\{.*?\})\s*"""',  # 双引号三引号
        ]
        for pattern in patterns:
            match = re.search(pattern, code, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue

        # 从文件名推断
        return {
            "name": Path(script_path).stem,
            "display_name": {"zh": Path(script_path).stem, "en": Path(script_path).stem},
            "description": "",
            "category": "Utility",
            "tools": []
        }

    def scan_directory(self, directory: str = None) -> dict:
        """扫描目录，加载所有 .py 脚本"""
        directory = directory or self.scripts_dir
        if not os.path.isdir(directory):
            return {"success": False, "message": f"目录不存在: {directory}"}

        all_tools = {}
        script_count = 0

        for py_file in sorted(glob.glob(os.path.join(directory, "*.py"))):
            if py_file.endswith("__init__.py"):
                continue
            result = self.load_script(py_file)
            if result.get("success"):
                script_count += 1
                for tool_name, tool_info in result["tools"].items():
                    all_tools[tool_name] = tool_info
                    meta = result.get("metadata", {})
                    all_tools[tool_name]["script"] = Path(py_file).stem
                    all_tools[tool_name]["metadata"] = meta

        self._loaded_tools = all_tools
        return {
            "success": True,
            "scripts": script_count,
            "tools": len(all_tools),
            "tool_list": list(all_tools.keys())
        }

    def call_tool(self, tool_name: str, params: dict = None) -> Any:
        """调用已加载的工具"""
        params = params or {}
        tool = self._loaded_tools.get(tool_name)
        if not tool:
            return {"success": False, "message": f"工具 '{tool_name}' 未找到"}

        func = tool["func"]
        _reset_result()

        try:
            # 检查函数签名，决定是否传参
            sig = inspect.signature(func)
            param_count = len([p for p in sig.parameters.values()
                             if p.kind in (p.POSITIONAL_OR_KEYWORD, p.POSITIONAL_ONLY)])

            # 检查是否是协程函数
            if asyncio.iscoroutinefunction(func):
                if param_count > 0:
                    result = asyncio.run(func(params))
                else:
                    result = asyncio.run(func())
            else:
                if param_count > 0:
                    result = func(params)
                else:
                    result = func()

            # 如果调用了 complete()，返回其结果
            if _result_holder["called"]:
                return _get_result()
            # 否则返回函数返回值
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"执行错误: {e}",
                "traceback": traceback.format_exc()
            }

    def list_tools(self) -> list:
        """列出所有已加载的工具"""
        return [
            {
                "name": name,
                "script": info.get("script", ""),
                "category": info.get("metadata", {}).get("category", ""),
                "description": info.get("metadata", {}).get("description", "")
            }
            for name, info in self._loaded_tools.items()
        ]


# ═══════════════════════════════════════════════════════════════
#  便捷函数
# ═══════════════════════════════════════════════════════════════

def create_exports() -> Exports:
    """创建一个新的 exports 对象"""
    return Exports()


def wrap_tool(core_func: Callable, success_msg: str = "操作成功", fail_msg: str = "操作失败") -> Callable:
    """
    Operit Wrapper 模式的 Python 实现
    自动处理 try/except 和 complete() 调用
    """
    async def wrapper(params: dict) -> None:
        try:
            result = await core_func(params) if asyncio.iscoroutinefunction(core_func) else core_func(params)
            complete({"success": True, "message": success_msg, "data": result})
        except Exception as e:
            complete({"success": False, "message": f"{fail_msg}: {e}", "error_stack": traceback.format_exc()})

    return wrapper


# ═══════════════════════════════════════════════════════════════
#  测试入口
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    loader = OperitScriptLoader()
    print(f"Operit Runtime 初始化完成")
    print(f"  临时目录: {OPERIT_CLEAN_ON_EXIT_DIR}")
    print(f"  脚本目录: {loader.scripts_dir}")
    print(f"  平台: {platform.system()} {platform.release()}")
    print(f"  Python: {sys.version.split()[0]}")

    # Android 兼容层状态
    try:
        import android_compat as _ac
        ag = _ac.get_android_compat_globals()
        print(f"  Android兼容层: 已加载 ({len(ag)} 个 API)")
        print(f"      ├─ Android核心API: Intent, Context, Uri, ContentResolver, 等")
        print(f"      ├─ Android系统服务: ActivityManager, PackageManager, 等")
        print(f"      ├─ Android图形API: Bitmap, Canvas, Color, Paint, PdfRenderer")
        print(f"      ├─ Android视图体系: View, TextView, UINode, AccessibilityNodeInfo")
        print(f"      ├─ Android媒体/定位/通信: MediaPlayer, LocationManager, TelephonyManager")
        print(f"      ├─ Java桥接: Java.type() - 直接调用Java类 (需jpype)")
        print(f"      ├─ java.io兼容: File, FileInputStream, FileOutputStream")
        print(f"      └─ 路径映射: /sdcard → {_ac._sdcard_root}")
    except Exception as _e:
        print(f"  Android兼容层: 未安装 (android_compat.py 不可用, {_e})")

    # 如果脚本目录存在，扫描加载
    if os.path.isdir(loader.scripts_dir):
        result = loader.scan_directory()
        print(f"  已加载: {result.get('scripts', 0)} 个脚本, {result.get('tools', 0)} 个工具")
    else:
        print(f"  脚本目录不存在，请放入 .py 脚本")
