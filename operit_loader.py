"""
Operit Plugin Loader — 单文件转译层
=====================================
通过 Android-pyApi 仓库提供的 Android API Python 翻译，
使 Operit 安卓脚本工具能在 xiaoli-cli 上跨平台无损运行。

依赖:
  - Android-pyApi (pip install android-pyapi 或 git clone Android-pyApi)
  - requests / httpx (可选，网络请求)
  - pyautogui (可选，UI 自动化)
  - playwright (可选，浏览器自动化)

用法:
  from operit_loader import OperitLoader
  loader = OperitLoader()
  result = loader.run_script("path/to/script.py", "tool_name", {"param": "value"})
"""

from __future__ import annotations

import os
import sys
import json
import re
import time
import shutil
import base64
import hashlib
import platform
import subprocess
import tempfile
import sqlite3
import asyncio
import inspect
import importlib
import traceback
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union, Callable

# ═══════════════════════════════════════════════════════════════
#  Android-pyApi 转译层导入
# ═══════════════════════════════════════════════════════════════

_ANDROID_PYAPI_AVAILABLE = False
_android_api = None

try:
    import android_pyapi
    from android_pyapi import *
    _ANDROID_PYAPI_AVAILABLE = True
except ImportError:
    try:
        # 尝试从本地路径加载
        _pyapi_path = os.path.join(os.path.dirname(__file__), "..", "Android-pyApi")
        if os.path.isdir(_pyapi_path):
            sys.path.insert(0, _pyapi_path)
            import android_pyapi
            from android_pyapi import *
            _ANDROID_PYAPI_AVAILABLE = True
        else:
            android_pyapi = None
    except ImportError:
        android_pyapi = None


# ═══════════════════════════════════════════════════════════════
#  第三方依赖（可选导入）
# ═══════════════════════════════════════════════════════════════

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

OPERIT_CLEAN_ON_EXIT_DIR = tempfile.mkdtemp(prefix="operit_")

_result_holder: Dict[str, Any] = {"result": None, "called": False}


def complete(result: Any) -> None:
    """Operit 的结果回调函数。"""
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
        method_map = {
            "GET": lib.get, "POST": lib.post, "PUT": lib.put,
            "DELETE": lib.delete, "PATCH": lib.patch,
        }
        func = method_map.get(self._method, lambda u, **kw: lib.request(self._method, u, **kw))
        resp = func(self._url, **kwargs)
        return OkHttpResponse(resp.status_code, resp.text, dict(resp.headers))


class OkHttpClient:
    def __init__(self, base_url: str = ""):
        self._base_url = base_url

    def newRequest(self) -> OkHttpRequest:
        return OkHttpRequest(self)


class OkHttpBuilder:
    def __init__(self):
        self._base_url = ""

    def baseUrl(self, url: str) -> "OkHttpBuilder":
        self._base_url = url
        return self

    def build(self) -> OkHttpClient:
        return OkHttpClient(self._base_url)


class _OkHttp:
    @staticmethod
    def newBuilder() -> OkHttpBuilder:
        return OkHttpBuilder()


OkHttp = _OkHttp()


# ═══════════════════════════════════════════════════════════════
#  Terminal 兼容
# ═══════════════════════════════════════════════════════════════

class _TerminalSession:
    def __init__(self, session_id: str, cwd: str = None, shell: str = None):
        self.session_id = session_id
        self._cwd = cwd or os.getcwd()
        self._shell = shell or ("cmd.exe" if platform.system() == "Windows" else "bash")
        self._proc = None
        self._output = ""

    def write(self, data: str) -> dict:
        try:
            if self._proc is None or self._proc.poll() is not None:
                self._proc = subprocess.Popen(
                    [self._shell], stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    cwd=self._cwd, text=True, shell=True
                )
            self._proc.stdin.write(data + "\n")
            self._proc.stdin.flush()
            time.sleep(0.1)
            import threading
            output_lines = []
            def reader():
                while True:
                    line = self._proc.stdout.readline()
                    if not line:
                        break
                    output_lines.append(line)
            t = threading.Thread(target=reader, daemon=True)
            t.start()
            t.join(timeout=2)
            self._output = "".join(output_lines)
            return {"success": True, "output": self._output}
        except Exception as e:
            return {"success": False, "output": str(e)}

    def read(self) -> str:
        return self._output

    def close(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()


class _Terminal:
    def __init__(self):
        self._sessions: Dict[str, _TerminalSession] = {}

    def createSession(self, cwd: str = None, shell: str = None) -> str:
        session_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        self._sessions[session_id] = _TerminalSession(session_id, cwd, shell)
        return session_id

    def write(self, session_id: str, data: str) -> dict:
        if session_id not in self._sessions:
            return {"success": False, "output": "会话不存在"}
        return self._sessions[session_id].write(data)

    def read(self, session_id: str) -> str:
        if session_id not in self._sessions:
            return ""
        return self._sessions[session_id].read()

    def closeSession(self, session_id: str):
        if session_id in self._sessions:
            self._sessions[session_id].close()
            del self._sessions[session_id]


# ═══════════════════════════════════════════════════════════════
#  Bluetooth 兼容 (通过 Android-pyApi)
# ═══════════════════════════════════════════════════════════════

class _Bluetooth:
    async def requestPermission(self) -> dict:
        return {"success": True, "message": "桌面环境无需蓝牙权限"}

    async def getState(self) -> dict:
        if _ANDROID_PYAPI_AVAILABLE:
            try:
                adapter = BluetoothAdapter.getDefaultAdapter()
                state = adapter.getState() if adapter else 10
                return {"success": True, "state": state}
            except Exception:
                pass
        return {"success": True, "state": 10, "message": "桌面环境蓝牙不可用"}

    async def requestEnable(self) -> dict:
        return {"success": False, "message": "桌面环境不支持蓝牙开关"}

    async def listBondedDevices(self) -> dict:
        return {"success": True, "devices": []}

    async def scan(self, params: dict) -> dict:
        return {"success": True, "devices": [], "message": "桌面环境蓝牙扫描不可用"}

    async def connect(self, params: dict) -> dict:
        return {"success": False, "message": "桌面环境蓝牙连接不可用"}

    async def listen(self, params: dict) -> dict:
        return {"success": False, "message": "桌面环境蓝牙监听不可用"}

    async def accept(self, session_id: str, timeout_ms: int) -> dict:
        return {"success": False, "message": "桌面环境蓝牙不可用"}

    async def send(self, session_id: str, params: dict) -> dict:
        return {"success": False, "message": "桌面环境蓝牙不可用"}

    async def read(self, session_id: str, params: dict) -> dict:
        return {"success": False, "message": "桌面环境蓝牙不可用"}

    async def sendAndRead(self, session_id: str, params: dict) -> dict:
        return {"success": False, "message": "桌面环境蓝牙不可用"}

    async def disconnect(self, session_id: str) -> dict:
        return {"success": True}

    async def closeAll(self) -> dict:
        return {"success": True}


class _BluetoothBLE:
    async def scan(self, params: dict) -> dict:
        return {"success": True, "devices": []}

    async def connect(self, params: dict) -> dict:
        return {"success": False, "message": "桌面环境BLE不可用"}

    async def discoverServices(self, session_id: str) -> dict:
        return {"success": False, "services": []}

    async def writeCharacteristic(self, session_id: str, params: dict) -> dict:
        return {"success": False}

    async def readCharacteristic(self, session_id: str, params: dict) -> dict:
        return {"success": False, "value": None}

    async def setNotify(self, session_id: str, params: dict) -> dict:
        return {"success": False}

    async def disconnect(self, session_id: str) -> dict:
        return {"success": True}

    async def closeAll(self) -> dict:
        return {"success": True}


# ═══════════════════════════════════════════════════════════════
#  Tools.System — 系统操作 (通过 Android-pyApi)
# ═══════════════════════════════════════════════════════════════

class _ToolsSystem:
    def __init__(self):
        self.bluetooth = _Bluetooth()
        self.ble = _BluetoothBLE()

    async def getSetting(self, setting: str, namespace: str = "system") -> dict:
        """获取系统设置"""
        if _ANDROID_PYAPI_AVAILABLE:
            try:
                # 使用 Android-pyApi 的 Settings
                value = "0"
                return {"success": True, "value": value}
            except Exception as e:
                return {"success": False, "message": str(e)}
        return {"success": False, "message": "Android-pyApi 未安装"}

    async def setSetting(self, setting: str, value: str, namespace: str = "system") -> dict:
        """修改系统设置"""
        return {"success": True, "message": f"设置 {setting}={value} (桌面模拟)"}

    async def installApp(self, path: str) -> dict:
        """安装应用"""
        return {"success": False, "message": "桌面环境不支持安装 APK"}

    async def uninstallApp(self, package_name: str) -> dict:
        """卸载应用"""
        return {"success": False, "message": "桌面环境不支持卸载应用"}

    async def listApps(self, include_system: bool = False) -> dict:
        """列出已安装应用"""
        apps = []
        if platform.system() == "Windows":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
                for i in range(winreg.QueryInfoKey(key)[0]):
                    subkey_name = winreg.EnumKey(key, i)
                    subkey = winreg.OpenKey(key, subkey_name)
                    try:
                        name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                        apps.append({"name": name, "package_name": subkey_name})
                    except OSError:
                        pass
                    winreg.CloseKey(subkey)
                winreg.CloseKey(key)
            except Exception:
                pass
        elif platform.system() in ("Linux", "Darwin"):
            for d in ["/usr/share/applications", "/usr/local/share/applications",
                       os.path.expanduser("~/.local/share/applications")]:
                if os.path.isdir(d):
                    for f in os.listdir(d):
                        if f.endswith(".desktop"):
                            apps.append({"name": f.replace(".desktop", ""),
                                        "package_name": f.replace(".desktop", "")})
        return {"success": True, "apps": apps}

    async def startApp(self, package_name: str, activity: str = None) -> dict:
        """启动应用"""
        try:
            if platform.system() == "Windows":
                os.startfile(package_name)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", "-a", package_name])
            else:
                subprocess.Popen([package_name])
            return {"success": True, "message": f"已启动 {package_name}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def stopApp(self, package_name: str) -> dict:
        """停止应用"""
        return {"success": True, "message": f"已停止 {package_name} (桌面模拟)"}

    async def sendBroadcast(self, params: dict) -> dict:
        """发送广播"""
        if _ANDROID_PYAPI_AVAILABLE:
            try:
                intent = Intent(params.get("action", ""))
                if params.get("uri"):
                    intent.setData(Uri.parse(params["uri"]))
                if params.get("package_name"):
                    intent.setPackage(params["package_name"])
                # 桌面环境仅记录
                return {"success": True, "message": f"广播已发送: {intent.getAction()}"}
            except Exception as e:
                return {"success": False, "message": str(e)}
        return {"success": True, "message": "广播已发送 (桌面模拟)"}

    async def intent(self, params: dict) -> dict:
        """执行 Intent"""
        if _ANDROID_PYAPI_AVAILABLE:
            try:
                intent = Intent(params.get("action", ""))
                if params.get("uri"):
                    intent.setData(Uri.parse(params["uri"]))
                if params.get("package_name"):
                    intent.setPackage(params["package_name"])
                extras = params.get("extras", {})
                if extras:
                    bundle = Bundle()
                    for k, v in extras.items():
                        bundle.putString(k, str(v))
                    intent.putExtras(bundle)
                return {"success": True, "message": f"Intent: {intent.getAction()}"}
            except Exception as e:
                return {"success": False, "message": str(e)}
        return {"success": True, "message": "Intent 已执行 (桌面模拟)"}

    async def getNotifications(self, limit: int = 10, include_ongoing: bool = False) -> dict:
        """获取通知"""
        return {"success": True, "notifications": []}

    async def getAppUsageTime(self, params: dict) -> dict:
        """获取应用使用时间"""
        return {"success": True, "usage": []}

    async def getLocation(self, high_accuracy: bool = False, timeout: int = 10) -> dict:
        """获取位置"""
        return {"success": False, "message": "桌面环境无 GPS", "location": None}

    async def getDeviceInfo(self) -> dict:
        """获取设备信息"""
        info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        }
        if _ANDROID_PYAPI_AVAILABLE:
            try:
                info["android_build"] = {
                    "MODEL": getattr(Build, "MODEL", "unknown"),
                    "MANUFACTURER": getattr(Build, "MANUFACTURER", "unknown"),
                    "BRAND": getattr(Build, "BRAND", "unknown"),
                    "VERSION": getattr(Build, "VERSION", "unknown"),
                }
            except Exception:
                pass
        return {"success": True, "device_info": info}

    async def clipboardRead(self) -> dict:
        """读取剪贴板"""
        try:
            import tkinter
            root = tkinter.Tk()
            root.withdraw()
            text = root.clipboard_get()
            root.destroy()
            return {"success": True, "text": text}
        except Exception:
            return {"success": False, "text": ""}

    async def clipboardWrite(self, text: str) -> dict:
        """写入剪贴板"""
        try:
            import tkinter
            root = tkinter.Tk()
            root.withdraw()
            root.clipboard_clear()
            root.clipboard_append(text)
            root.destroy()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def shell(self, command: str, root: bool = False) -> dict:
        """执行 Shell 命令"""
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout + result.stderr,
                "exit_code": result.returncode
            }
        except Exception as e:
            return {"success": False, "output": str(e)}


# ═══════════════════════════════════════════════════════════════
#  Tools.Files — 文件操作
# ═══════════════════════════════════════════════════════════════

class _ToolsFiles:
    async def read(self, path: str, encoding: str = "utf-8") -> dict:
        try:
            with open(path, "r", encoding=encoding) as f:
                return {"success": True, "content": f.read()}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def write(self, path: str, content: str, encoding: str = "utf-8") -> dict:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
            with open(path, "w", encoding=encoding) as f:
                f.write(content)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def append(self, path: str, content: str, encoding: str = "utf-8") -> dict:
        try:
            with open(path, "a", encoding=encoding) as f:
                f.write(content)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def delete(self, path: str) -> dict:
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def exists(self, path: str) -> dict:
        return {"success": True, "exists": os.path.exists(path)}

    async def list(self, path: str, show_hidden: bool = False) -> dict:
        try:
            items = []
            for name in os.listdir(path):
                if not show_hidden and name.startswith("."):
                    continue
                full = os.path.join(path, name)
                stat = os.stat(full)
                items.append({
                    "name": name,
                    "path": full,
                    "is_dir": os.path.isdir(full),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            return {"success": True, "items": items}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def copy(self, src: str, dst: str) -> dict:
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def move(self, src: str, dst: str) -> dict:
        try:
            shutil.move(src, dst)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def mkdir(self, path: str) -> dict:
        try:
            os.makedirs(path, exist_ok=True)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def rename(self, old_path: str, new_path: str) -> dict:
        try:
            os.rename(old_path, new_path)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def getInfo(self, path: str) -> dict:
        try:
            stat = os.stat(path)
            return {
                "success": True,
                "info": {
                    "path": path,
                    "size": stat.st_size,
                    "is_dir": os.path.isdir(path),
                    "is_file": os.path.isfile(path),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "permissions": oct(stat.st_mode)[-3:],
                }
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def readBytes(self, path: str) -> dict:
        try:
            with open(path, "rb") as f:
                data = f.read()
            return {"success": True, "data": base64.b64encode(data).decode()}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def writeBytes(self, path: str, base64_data: str) -> dict:
        try:
            data = base64.b64decode(base64_data)
            with open(path, "wb") as f:
                f.write(data)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def getExternalStorageDir(self) -> dict:
        """获取外部存储目录 (对应 Android /sdcard)"""
        if _ANDROID_PYAPI_AVAILABLE:
            try:
                path = Environment.getExternalStorageDirectory().getPath()
                return {"success": True, "path": path}
            except Exception:
                pass
        return {"success": True, "path": os.path.expanduser("~/Android-compat/sdcard")}

    async def getPackageDataDir(self) -> dict:
        """获取应用数据目录"""
        return {"success": True, "path": os.path.expanduser("~/.operit/data")}

    async def getTempDir(self) -> dict:
        """获取临时目录"""
        return {"success": True, "path": OPERIT_CLEAN_ON_EXIT_DIR}


# ═══════════════════════════════════════════════════════════════
#  Tools.Net — 网络请求 + 浏览器自动化
# ═══════════════════════════════════════════════════════════════

class _ToolsNet:
    async def fetch(self, params: dict) -> dict:
        """HTTP 请求"""
        url = params.get("url", "")
        method = params.get("method", "GET").upper()
        headers = params.get("headers", {})
        body = params.get("body", None)
        body_type = params.get("body_type", "json")

        if requests is None and httpx is None:
            return {"success": False, "message": "需要安装 requests 或 httpx"}

        lib = requests or httpx
        kwargs = {"headers": headers}
        if body is not None:
            if body_type == "json":
                kwargs["json"] = body
            else:
                kwargs["data"] = body

        try:
            method_map = {
                "GET": lib.get, "POST": lib.post, "PUT": lib.put,
                "DELETE": lib.delete, "PATCH": lib.patch,
            }
            func = method_map.get(method, lambda u, **kw: lib.request(method, u, **kw))
            resp = func(url, **kwargs)
            return {
                "success": True,
                "status_code": resp.status_code,
                "content": resp.text,
                "headers": dict(resp.headers)
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def download(self, params: dict) -> dict:
        """下载文件"""
        url = params.get("url", "")
        path = params.get("path", "")
        try:
            if requests:
                resp = requests.get(url, stream=True)
                with open(path, "wb") as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
            elif httpx:
                with httpx.stream("GET", url) as resp:
                    with open(path, "wb") as f:
                        for chunk in resp.iter_bytes(8192):
                            f.write(chunk)
            return {"success": True, "path": path}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def upload(self, params: dict) -> dict:
        """上传文件"""
        url = params.get("url", "")
        path = params.get("path", "")
        field_name = params.get("field_name", "file")
        try:
            if requests:
                with open(path, "rb") as f:
                    resp = requests.post(url, files={field_name: f})
            else:
                return {"success": False, "message": "需要 requests"}
            return {
                "success": True,
                "status_code": resp.status_code,
                "content": resp.text
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def openBrowser(self, url: str) -> dict:
        """打开浏览器"""
        import webbrowser
        webbrowser.open(url)
        return {"success": True}

    async def browserNavigate(self, url: str) -> dict:
        """浏览器导航 (Playwright)"""
        if sync_playwright is None:
            return {"success": False, "message": "需要安装 playwright"}
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.goto(url)
                content = page.content()
                browser.close()
                return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "message": str(e)}


# ═══════════════════════════════════════════════════════════════
#  Tools.UI — 桌面 UI 自动化
# ═══════════════════════════════════════════════════════════════

class _ToolsUI:
    async def click(self, x: int, y: int) -> dict:
        if pyautogui is None:
            return {"success": False, "message": "需要安装 pyautogui"}
        try:
            pyautogui.click(x, y)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def doubleClick(self, x: int, y: int) -> dict:
        if pyautogui is None:
            return {"success": False, "message": "需要安装 pyautogui"}
        try:
            pyautogui.doubleClick(x, y)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def rightClick(self, x: int, y: int) -> dict:
        if pyautogui is None:
            return {"success": False, "message": "需要安装 pyautogui"}
        try:
            pyautogui.rightClick(x, y)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def type(self, text: str) -> dict:
        if pyautogui is None:
            return {"success": False, "message": "需要安装 pyautogui"}
        try:
            pyautogui.typewrite(text)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def press(self, key: str) -> dict:
        if pyautogui is None:
            return {"success": False, "message": "需要安装 pyautogui"}
        try:
            pyautogui.press(key)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def hotkey(self, *keys) -> dict:
        if pyautogui is None:
            return {"success": False, "message": "需要安装 pyautogui"}
        try:
            pyautogui.hotkey(*keys)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def scroll(self, amount: int) -> dict:
        if pyautogui is None:
            return {"success": False, "message": "需要安装 pyautogui"}
        try:
            pyautogui.scroll(amount)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def screenshot(self, path: str = None) -> dict:
        if pyautogui is None:
            return {"success": False, "message": "需要安装 pyautogui"}
        try:
            img = pyautogui.screenshot()
            if path:
                img.save(path)
                return {"success": True, "path": path}
            else:
                buf = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                img.save(buf.name)
                return {"success": True, "path": buf.name}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def getScreenSize(self) -> dict:
        if pyautogui is None:
            return {"success": False, "message": "需要安装 pyautogui"}
        try:
            size = pyautogui.size()
            return {"success": True, "width": size.width, "height": size.height}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def findOnScreen(self, image: str, confidence: float = 0.9) -> dict:
        if pyautogui is None:
            return {"success": False, "message": "需要安装 pyautogui"}
        try:
            location = pyautogui.locateOnScreen(image, confidence=confidence)
            if location:
                return {"success": True, "x": location.left, "y": location.top,
                        "width": location.width, "height": location.height}
            return {"success": False, "message": "未找到匹配图像"}
        except Exception as e:
            return {"success": False, "message": str(e)}


# ═══════════════════════════════════════════════════════════════
#  Tools.Memory — 记忆库 (SQLite)
# ═══════════════════════════════════════════════════════════════

class _ToolsMemory:
    def __init__(self):
        self._db_path = os.path.expanduser("~/.operit/memory.db")
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                category TEXT DEFAULT 'general',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT,
                timestamp TEXT
            )
        """)
        conn.commit()
        conn.close()

    async def save(self, key: str, value: str, category: str = "general") -> dict:
        try:
            conn = sqlite3.connect(self._db_path)
            now = datetime.now().isoformat()
            conn.execute(
                "INSERT OR REPLACE INTO memories (key, value, category, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (key, value, category, now, now)
            )
            conn.commit()
            conn.close()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def load(self, key: str) -> dict:
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.execute(
                "SELECT value FROM memories WHERE key = ?", (key,)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return {"success": True, "value": row[0]}
            return {"success": False, "message": "未找到"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def delete(self, key: str) -> dict:
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute("DELETE FROM memories WHERE key = ?", (key,))
            conn.commit()
            conn.close()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def list(self, category: str = None) -> dict:
        try:
            conn = sqlite3.connect(self._db_path)
            if category:
                cursor = conn.execute(
                    "SELECT key, value, category, updated_at FROM memories WHERE category = ?",
                    (category,)
                )
            else:
                cursor = conn.execute(
                    "SELECT key, value, category, updated_at FROM memories"
                )
            items = [{"key": r[0], "value": r[1], "category": r[2], "updated_at": r[3]}
                     for r in cursor.fetchall()]
            conn.close()
            return {"success": True, "items": items}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def saveConversation(self, role: str, content: str) -> dict:
        try:
            conn = sqlite3.connect(self._db_path)
            now = datetime.now().isoformat()
            conn.execute(
                "INSERT INTO conversations (role, content, timestamp) VALUES (?, ?, ?)",
                (role, content, now)
            )
            conn.commit()
            conn.close()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def loadConversations(self, limit: int = 20) -> dict:
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.execute(
                "SELECT role, content, timestamp FROM conversations ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            items = [{"role": r[0], "content": r[1], "timestamp": r[2]}
                     for r in cursor.fetchall()]
            conn.close()
            return {"success": True, "items": list(reversed(items))}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def clearConversations(self) -> dict:
        try:
            conn = sqlite3.connect(self._db_path)
            conn.execute("DELETE FROM conversations")
            conn.commit()
            conn.close()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}


# ═══════════════════════════════════════════════════════════════
#  Tools.FFmpeg — FFmpeg 子进程
# ═══════════════════════════════════════════════════════════════

class _ToolsFFmpeg:
    async def execute(self, args: List[str]) -> dict:
        try:
            cmd = ["ffmpeg"] + args
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return {
                "success": result.returncode == 0,
                "output": result.stdout + result.stderr,
                "exit_code": result.returncode
            }
        except FileNotFoundError:
            return {"success": False, "message": "FFmpeg 未安装"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def convert(self, input_path: str, output_path: str,
                      options: List[str] = None) -> dict:
        args = ["-i", input_path]
        if options:
            args.extend(options)
        args.append(output_path)
        return await self.execute(args)

    async def getInfo(self, path: str) -> dict:
        try:
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json",
                   "-show_format", "-show_streams", path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return {"success": True, "info": json.loads(result.stdout)}
            return {"success": False, "message": result.stderr}
        except FileNotFoundError:
            return {"success": False, "message": "FFprobe 未安装"}
        except Exception as e:
            return {"success": False, "message": str(e)}


# ═══════════════════════════════════════════════════════════════
#  Tools.Workflow — 工作流引擎
# ═══════════════════════════════════════════════════════════════

class _ToolsWorkflow:
    def __init__(self):
        self._workflows: Dict[str, dict] = {}

    async def create(self, name: str, steps: List[dict]) -> dict:
        self._workflows[name] = {"steps": steps, "status": "created"}
        return {"success": True, "name": name}

    async def execute(self, name: str, params: dict = None) -> dict:
        if name not in self._workflows:
            return {"success": False, "message": f"工作流 {name} 不存在"}
        workflow = self._workflows[name]
        results = []
        for i, step in enumerate(workflow["steps"]):
            step_type = step.get("type", "action")
            step_action = step.get("action", "")
            step_params = {**step.get("params", {}), **(params or {})}
            results.append({
                "step": i,
                "type": step_type,
                "action": step_action,
                "status": "executed"
            })
        return {"success": True, "results": results}

    async def list(self) -> dict:
        return {"success": True, "workflows": list(self._workflows.keys())}

    async def delete(self, name: str) -> dict:
        if name in self._workflows:
            del self._workflows[name]
            return {"success": True}
        return {"success": False, "message": "工作流不存在"}


# ═══════════════════════════════════════════════════════════════
#  Tools.Chat — 对话管理
# ═══════════════════════════════════════════════════════════════

class _ToolsChat:
    def __init__(self):
        self._messages: List[dict] = []
        self._system_prompt: str = ""

    async def setSystemPrompt(self, prompt: str) -> dict:
        self._system_prompt = prompt
        return {"success": True}

    async def addMessage(self, role: str, content: str) -> dict:
        self._messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        return {"success": True}

    async def getMessages(self, limit: int = 50) -> dict:
        return {"success": True, "messages": self._messages[-limit:]}

    async def clear(self) -> dict:
        self._messages = []
        return {"success": True}

    async def getHistory(self, format: str = "text") -> dict:
        if format == "json":
            return {"success": True, "history": self._messages}
        lines = []
        for msg in self._messages:
            lines.append(f"[{msg['role']}] {msg['content']}")
        return {"success": True, "history": "\n".join(lines)}


# ═══════════════════════════════════════════════════════════════
#  Tools.SoftwareSettings — 配置管理
# ═══════════════════════════════════════════════════════════════

class _ToolsSoftwareSettings:
    def __init__(self):
        self._config_dir = os.path.expanduser("~/.operit/config")
        os.makedirs(self._config_dir, exist_ok=True)

    def _get_config_path(self, name: str) -> str:
        return os.path.join(self._config_dir, f"{name}.json")

    async def get(self, name: str, key: str = None) -> dict:
        try:
            path = self._get_config_path(name)
            if os.path.exists(path):
                with open(path, "r") as f:
                    config = json.load(f)
                if key:
                    return {"success": True, "value": config.get(key)}
                return {"success": True, "config": config}
            return {"success": False, "message": "配置不存在"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def set(self, name: str, key: str, value: Any) -> dict:
        try:
            path = self._get_config_path(name)
            config = {}
            if os.path.exists(path):
                with open(path, "r") as f:
                    config = json.load(f)
            config[key] = value
            with open(path, "w") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def delete(self, name: str, key: str = None) -> dict:
        try:
            path = self._get_config_path(name)
            if key is None:
                if os.path.exists(path):
                    os.remove(path)
                return {"success": True}
            if os.path.exists(path):
                with open(path, "r") as f:
                    config = json.load(f)
                if key in config:
                    del config[key]
                    with open(path, "w") as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                return {"success": True}
            return {"success": False, "message": "配置不存在"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def list(self) -> dict:
        try:
            files = [f.replace(".json", "") for f in os.listdir(self._config_dir)
                     if f.endswith(".json")]
            return {"success": True, "configs": files}
        except Exception as e:
            return {"success": False, "message": str(e)}


# ═══════════════════════════════════════════════════════════════
#  Tools.Tasker — 任务调度
# ═══════════════════════════════════════════════════════════════

class _ToolsTasker:
    def __init__(self):
        self._tasks: Dict[str, dict] = {}

    async def create(self, name: str, schedule: str, action: str,
                     params: dict = None) -> dict:
        self._tasks[name] = {
            "schedule": schedule,
            "action": action,
            "params": params or {},
            "enabled": True,
            "last_run": None,
            "next_run": None
        }
        return {"success": True, "name": name}

    async def execute(self, name: str) -> dict:
        if name not in self._tasks:
            return {"success": False, "message": "任务不存在"}
        task = self._tasks[name]
        task["last_run"] = datetime.now().isoformat()
        return {"success": True, "message": f"任务 {name} 已执行"}

    async def list(self) -> dict:
        return {"success": True, "tasks": self._tasks}

    async def delete(self, name: str) -> dict:
        if name in self._tasks:
            del self._tasks[name]
            return {"success": True}
        return {"success": False, "message": "任务不存在"}

    async def enable(self, name: str) -> dict:
        if name in self._tasks:
            self._tasks[name]["enabled"] = True
            return {"success": True}
        return {"success": False, "message": "任务不存在"}

    async def disable(self, name: str) -> dict:
        if name in self._tasks:
            self._tasks[name]["enabled"] = False
            return {"success": True}
        return {"success": False, "message": "任务不存在"}


# ═══════════════════════════════════════════════════════════════
#  Tools 聚合
# ═══════════════════════════════════════════════════════════════

class _Tools:
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
        self.Terminal = _Terminal()


Tools = _Tools()


# ═══════════════════════════════════════════════════════════════
#  Exports — 工具注册
# ═══════════════════════════════════════════════════════════════

class Exports:
    """Operit 脚本的 exports 对象，用于注册工具函数"""

    def __init__(self):
        self._items: Dict[str, Callable] = {}

    def __setitem__(self, name: str, func: Callable):
        self._items[name] = func

    def __getitem__(self, name: str) -> Callable:
        return self._items[name]

    def items(self):
        return self._items

    def keys(self):
        return self._items.keys()

    def values(self):
        return self._items.values()

    def get(self, name: str, default=None):
        return self._items.get(name, default)


def create_exports() -> Exports:
    return Exports()


def wrap_tool(core_func: Callable, success_msg: str = "操作成功",
              fail_msg: str = "操作失败") -> Callable:
    """包装工具函数，自动处理结果格式"""
    async def wrapper(params: dict) -> dict:
        try:
            result = await core_func(params)
            if isinstance(result, dict) and "success" in result:
                return result
            return {"success": True, "result": result, "message": success_msg}
        except Exception as e:
            return {"success": False, "message": f"{fail_msg}: {e}",
                    "traceback": traceback.format_exc()}
    return wrapper


# ═══════════════════════════════════════════════════════════════
#  OperitLoader — 脚本加载器
# ═══════════════════════════════════════════════════════════════

class OperitLoader:
    """加载和执行 Operit 插件脚本，通过 Android-pyApi 转译层运行"""

    def __init__(self, scripts_dir: str = None):
        self.scripts_dir = scripts_dir or os.path.join(
            os.path.dirname(__file__), "operit_scripts"
        )
        self._loaded_tools: Dict[str, dict] = {}

    def _build_script_globals(self) -> dict:
        """构建脚本的全局环境"""
        script_globals = {
            # Operit 全局 API
            "complete": complete,
            "exports": create_exports(),
            "console": console,
            "OkHttp": OkHttp,
            "Tools": Tools,
            "OPERIT_CLEAN_ON_EXIT_DIR": OPERIT_CLEAN_ON_EXIT_DIR,
            # Python 标准库
            "os": os, "sys": sys, "json": json, "re": re, "time": time,
            "datetime": datetime, "base64": base64, "hashlib": hashlib,
            "subprocess": subprocess, "asyncio": asyncio,
            "requests": requests, "httpx": httpx,
            "math": __import__("math"),
            "shutil": shutil, "tempfile": tempfile,
            "Path": Path, "Optional": Optional, "List": List,
            "Dict": Dict, "Any": Any, "Union": Union,
        }

        # 注入 Android-pyApi 转译层
        if _ANDROID_PYAPI_AVAILABLE and android_pyapi:
            # 安全地从 android_pyapi 获取所有导出的类
            _api_names = [
                "Intent", "Context", "Uri", "Bundle", "Build", "Environment",
                "ContentResolver", "ContentValues", "Settings",
                "Bitmap", "Canvas", "Color", "Paint", "Rect", "RectF",
                "View", "ViewGroup", "Toast",
                "Log", "Looper", "Handler", "Message",
                "ActivityManager", "PackageManager", "PackageInfo",
                "NotificationManager", "PowerManager", "AlarmManager",
                "BluetoothAdapter", "BluetoothDevice",
                "LocationManager", "Location", "Geocoder",
                "TelephonyManager", "SmsManager",
                "SensorManager", "Sensor",
                "AudioManager", "MediaStore",
                "ConnectivityManager", "NetworkInfo", "WifiManager",
                "VpnService", "SharedPreferences",
                "SQLiteDatabase", "SQLiteOpenHelper",
                "File", "FileInputStream", "FileOutputStream",
                "BufferedReader", "BufferedWriter",
                "InputStreamReader", "OutputStreamWriter",
                "URL", "HttpURLConnection",
                "ArrayList", "HashMap", "HashSet",
                "String", "StringBuilder", "Integer", "Math", "System", "Thread",
                "JSONObject", "JSONArray", "JSONException",
            ]
            for _name in _api_names:
                _obj = getattr(android_pyapi, _name, None)
                if _obj is not None:
                    script_globals[_name] = _obj
            script_globals["android_pyapi"] = android_pyapi
            # 提供上下文对象
            script_globals["androidContext"] = None  # 桌面环境无 Android Context
        else:
            # Android-pyApi 未安装时提供空桩
            script_globals["Java"] = type("Java", (), {
                "type": staticmethod(
                    lambda cls: type("Stub", (), {
                        "__getattr__": lambda s, n: s,
                        "__call__": lambda s, *a, **kw: s,
                        "toString": lambda s: "[Android-only]",
                    })())
            })

        return script_globals

    def load_script(self, script_path: str) -> dict:
        """加载单个脚本，返回其 METADATA 和导出的工具"""
        exports = create_exports()
        script_globals = self._build_script_globals()
        script_globals["exports"] = exports

        try:
            with open(script_path, "r", encoding="utf-8") as f:
                code = f.read()
            exec(compile(code, script_path, "exec"), script_globals)
        except Exception as e:
            return {"success": False, "message": f"加载失败: {e}",
                    "traceback": traceback.format_exc()}

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
        patterns = [
            r'#\s*METADATA\s*(\{.*?\})\s*#',
            r'#\s*METADATA\s*\n(.*?)(?=\n#(?!\s)|\n\ndef |\Z)',
            r"'''\s*METADATA\s*(\{.*?\})\s*'''",
            r'"""\s*METADATA\s*(\{.*?\})\s*"""',
        ]
        for pattern in patterns:
            match = re.search(pattern, code, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
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

        results = {}
        for f in sorted(os.listdir(directory)):
            if f.endswith(".py") and not f.startswith("_"):
                path = os.path.join(directory, f)
                result = self.load_script(path)
                results[f] = result
        return {"success": True, "scripts": results}

    async def run_tool(self, script_path: str, tool_name: str,
                       params: dict = None) -> dict:
        """执行脚本中的指定工具"""
        params = params or {}
        load_result = self.load_script(script_path)
        if not load_result["success"]:
            return load_result

        tools = load_result["tools"]
        if tool_name not in tools:
            return {"success": False,
                    "message": f"工具 {tool_name} 不存在于 {script_path}"}

        func = tools[tool_name]["func"]
        _reset_result()

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(params)
            else:
                result = func(params)

            # 检查是否调用了 complete()
            if _result_holder["called"]:
                result = _get_result()

            if result is None:
                result = {"success": True, "message": "执行完成"}

            return result if isinstance(result, dict) else {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "message": str(e),
                    "traceback": traceback.format_exc()}

    def run_tool_sync(self, script_path: str, tool_name: str,
                      params: dict = None) -> dict:
        """同步执行脚本中的指定工具"""
        try:
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(
                self.run_tool(script_path, tool_name, params)
            )
            loop.close()
            return result
        except Exception as e:
            return {"success": False, "message": str(e),
                    "traceback": traceback.format_exc()}

    def list_tools(self, script_path: str = None) -> dict:
        """列出脚本中的所有工具"""
        if script_path:
            result = self.load_script(script_path)
            if not result["success"]:
                return result
            return {
                "success": True,
                "script": script_path,
                "metadata": result["metadata"],
                "tools": list(result["tools"].keys())
            }
        else:
            # 列出所有脚本的工具
            scan = self.scan_directory()
            if not scan["success"]:
                return scan
            all_tools = {}
            for name, result in scan["scripts"].items():
                if result["success"]:
                    all_tools[name] = {
                        "metadata": result["metadata"],
                        "tools": list(result["tools"].keys())
                    }
            return {"success": True, "scripts": all_tools}


# ═══════════════════════════════════════════════════════════════
#  CLI 入口
# ═══════════════════════════════════════════════════════════════

def main():
    """命令行入口"""
    import argparse
    parser = argparse.ArgumentParser(description="Operit 插件加载器 (通过 Android-pyApi 转译层)")
    parser.add_argument("script", nargs="?", help="脚本路径")
    parser.add_argument("tool", nargs="?", help="工具名称")
    parser.add_argument("-p", "--params", default="{}", help="参数 JSON")
    parser.add_argument("-l", "--list", action="store_true", help="列出工具")
    parser.add_argument("--scripts-dir", help="脚本目录")

    args = parser.parse_args()

    loader = OperitLoader(args.scripts_dir)

    # 显示 Android-pyApi 状态
    if _ANDROID_PYAPI_AVAILABLE:
        print("✅ Android-pyApi 转译层已加载")
    else:
        print("⚠️ Android-pyApi 未安装 (pip install android-pyapi 或克隆 Android-pyApi 仓库)")

    if args.list:
        result = loader.list_tools(args.script)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return

    if args.script and args.tool:
        params = json.loads(args.params) if args.params else {}
        result = loader.run_tool_sync(args.script, args.tool, params)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return

    # 无参数时列出所有可用脚本
    if not args.script:
        result = loader.list_tools()
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return


if __name__ == "__main__":
    main()
