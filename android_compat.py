"""
Android API → Python 跨平台兼容层
====================================
将 Android 特有的 Java/Kotlin API 全面翻译为 Python 实现，
使 Operit 脚本可无需修改地在 Windows/macOS/Linux 上运行。

覆盖的 Android API 领域:
  - android.content (Intent, Context, ContentResolver, ContentValues)
  - android.net (Uri)
  - android.os (Environment, Build, PowerManager, VibrationEffect)
  - android.app (ActivityManager, NotificationManager, AlarmManager)
  - android.graphics (Bitmap, Canvas, Color, Paint, Rect)
  - android.graphics.pdf (PdfRenderer)
  - android.provider (Settings, MediaStore, ContactsContract, CalendarContract)
  - android.view (View, ViewGroup, accessibility/UIAutomation)
  - android.bluetooth (BluetoothAdapter, BLE)
  - android.location (LocationManager, Geocoder)
  - android.telephony (TelephonyManager)
  - android.hardware (Camera, SensorManager)
  - android.media (MediaPlayer, AudioRecord, TtsEngine)
  - android.widget (Toast)
  - android.print (PrintManager)
  - android.accounts (AccountManager)
  - android.hardware.display (DisplayManager)
  - java.io (File, FileInputStream/OutputStream, BufferedReader)
  - android.hardware.biometrics (BiometricPrompt)
"""

import os
import sys
import re
import io
import json
import time
import math
import random
import base64
import hashlib
import struct
import shutil
import tempfile
import subprocess
import platform
import webbrowser
import urllib.parse
import urllib.request
import socket
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from collections import OrderedDict

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

try:
    import screeninfo
    HAS_SCREENINFO = True
except ImportError:
    HAS_SCREENINFO = False

# ============================================================
#  GLOBAL STATE - 模拟 Android Application 上下文
# ============================================================

_sdcard_root = os.path.join(os.path.expanduser("~"), "Android-compat", "sdcard")
_app_data_dir = os.path.join(os.path.expanduser("~"), "Android-compat", "app-data")
_download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
_package_name = "com.ai.assistance.operit"
_app_version = "1.0.0"

def _ensure_sdcard():
    """确保模拟的 sdcard 目录结构存在"""
    for d in [_sdcard_root, os.path.join(_sdcard_root, "Download"),
              os.path.join(_sdcard_root, "DCIM"), os.path.join(_sdcard_root, "DCIM", "Screenshots"),
              os.path.join(_sdcard_root, "Android", "data"),
              os.path.join(_sdcard_root, "Android", "data", _package_name, "files"),
              os.path.join(_sdcard_root, "Android", "data", _package_name, "files", "packages"),
              os.path.join(_sdcard_root, "Android", "data", _package_name, "js_temp"),
              _app_data_dir]:
        os.makedirs(d, exist_ok=True)

_ensure_sdcard()


# ============================================================
#  android.net.Uri
# ============================================================

class Uri:
    """模拟 android.net.Uri"""

    @staticmethod
    def parse(uri_string: str) -> "Uri":
        return Uri(uri_string)

    @staticmethod
    def fromFile(path: str) -> "Uri":
        return Uri(f"file://{path}")

    @staticmethod
    def withAppendedPath(base: "Uri", segment: str) -> "Uri":
        return Uri(f"{base._uri}/{segment}")

    def __init__(self, uri_string: str):
        self._uri = uri_string
        self._parsed = urllib.parse.urlparse(uri_string)

    def getScheme(self) -> str:
        """content, file, http, https"""
        return self._parsed.scheme or ""

    def getPath(self) -> str:
        p = self._parsed.path
        if p.startswith("/sdcard"):
            return _sdcard_root + p
        return p

    def getLastPathSegment(self) -> str:
        return os.path.basename(self._parsed.path) or ""

    def toString(self) -> str:
        return self._uri

    def __str__(self):
        return self._uri


# ============================================================
#  android.content.ContentValues
# ============================================================

class ContentValues:
    """模拟 android.content.ContentValues"""

    def __init__(self):
        self._values: Dict[str, Any] = {}

    def put(self, key: str, value: Any) -> None:
        self._values[key] = value

    def get(self, key: str) -> Any:
        return self._values.get(key)

    def getAsString(self, key: str) -> Optional[str]:
        v = self._values.get(key)
        return str(v) if v is not None else None

    def getAsLong(self, key: str) -> Optional[int]:
        v = self._values.get(key)
        return int(v) if v is not None else None

    def remove(self, key: str) -> None:
        self._values.pop(key, None)

    def containsKey(self, key: str) -> bool:
        return key in self._values

    def valueSet(self) -> Dict[str, Any]:
        return dict(self._values)

    def size(self) -> int:
        return len(self._values)

    def clear(self) -> None:
        self._values.clear()


# ============================================================
#  android.content.ContentResolver
# ============================================================

class ContentResolver:
    """模拟 android.content.ContentResolver"""

    def __init__(self, context: "Context" = None):
        self._context = context

    def query(self, uri: Uri, projection: List[str] = None,
              selection: str = None, selectionArgs: List[str] = None,
              sortOrder: str = None) -> "Cursor":
        """模拟 ContentResolver.query - 有限实现"""
        cursor = Cursor()
        scheme = uri.getScheme()

        # file:// URI → 读文件
        if scheme == "file":
            path = uri.getPath()
            if os.path.isfile(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        cursor._data = [{"_data": path, "_size": os.path.getsize(path)}]
                except Exception:
                    pass

        # content:// URI → 模拟
        path = uri._parsed.path
        if "calendar" in path:
            cursor._data = [{
                "_id": "1", "title": "Calendar Event",
                "dtstart": str(int(time.time()) * 1000),
                "dtend": str(int(time.time() + 3600) * 1000)
            }]
        elif "contacts" in path:
            cursor._data = [{"_id": "1", "display_name": "Test Contact", "has_phone_number": "1"}]
        elif "media" in path or "images" in path or "downloads" in path:
            cursor._data = self._scan_media()
        elif "settings" in path:
            cursor._data = [{"name": "default", "value": ""}]

        return cursor

    def _scan_media(self) -> List[Dict]:
        """扫描本地文件系统中的媒体文件"""
        results = []
        media_dirs = [
            os.path.expanduser("~/Pictures"),
            os.path.expanduser("~/Downloads"),
            os.path.join(_sdcard_root, "DCIM"),
            os.path.join(_sdcard_root, "Download"),
        ]
        for d in media_dirs:
            if not os.path.isdir(d):
                continue
            for root, dirs, files in os.walk(d):
                for f in files[:50]:  # limit
                    ext = os.path.splitext(f)[1].lower()
                    if ext in (".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mp3"):
                        results.append({
                            "_data": os.path.join(root, f),
                            "_size": os.path.getsize(os.path.join(root, f)),
                            "title": os.path.splitext(f)[0],
                            "mime_type": f"image/{ext[1:]}" if ext in (".jpg", ".jpeg", ".png") else "video/mp4"
                        })
        return results

    def insert(self, uri: Uri, values: ContentValues) -> Uri:
        """模拟插入"""
        return Uri(f"content://media/external/images/media/{int(time.time())}")

    def update(self, uri: Uri, values: ContentValues, where: str = None,
               selectionArgs: List[str] = None) -> int:
        """模拟更新"""
        return 1

    def delete(self, uri: Uri, where: str = None, selectionArgs: List[str] = None) -> int:
        return 0

    def openInputStream(self, uri: Uri) -> io.BytesIO:
        path = uri.getPath()
        if os.path.isfile(path):
            with open(path, "rb") as f:
                return io.BytesIO(f.read())
        return io.BytesIO()

    def openOutputStream(self, uri: Uri) -> io.BytesIO:
        return io.BytesIO()

    def getType(self, uri: Uri) -> str:
        path = uri.getPath()
        ext = os.path.splitext(path)[1].lower()
        if ext == ".jpg" or ext == ".jpeg": return "image/jpeg"
        if ext == ".png": return "image/png"
        if ext == ".mp4": return "video/mp4"
        if ext == ".mp3": return "audio/mpeg"
        return "application/octet-stream"


class Cursor:
    """模拟 android.database.Cursor"""

    def __init__(self):
        self._data: List[Dict] = []
        self._pos = -1

    def moveToFirst(self) -> bool:
        if self._data:
            self._pos = 0
            return True
        return False

    def moveToNext(self) -> bool:
        if self._pos + 1 < len(self._data):
            self._pos += 1
            return True
        return False

    def moveToPosition(self, pos: int) -> bool:
        if 0 <= pos < len(self._data):
            self._pos = pos
            return True
        return False

    def getCount(self) -> int:
        return len(self._data)

    def getColumnIndex(self, columnName: str) -> int:
        if self._pos >= 0 and self._pos < len(self._data):
            keys = list(self._data[self._pos].keys())
            return keys.index(columnName) if columnName in keys else -1
        return -1

    def getString(self, columnIndex: int) -> Optional[str]:
        if self._pos >= 0 and self._pos < len(self._data):
            keys = list(self._data[self._pos].keys())
            if 0 <= columnIndex < len(keys):
                return str(self._data[self._pos].get(keys[columnIndex], ""))
        return None

    def getInt(self, columnIndex: int) -> int:
        val = self.getString(columnIndex)
        return int(val) if val else 0

    def getLong(self, columnIndex: int) -> int:
        return self.getInt(columnIndex)

    def close(self) -> None:
        self._data = []

    def isClosed(self) -> bool:
        return len(self._data) == 0

    def getPosition(self) -> int:
        return self._pos

    def __iter__(self):
        for item in self._data:
            yield item


# ============================================================
#  android.content.Intent
# ============================================================

class IntentAction:
    """常用 Intent Action 常量"""
    ACTION_MAIN = "android.intent.action.MAIN"
    ACTION_VIEW = "android.intent.action.VIEW"
    ACTION_SEND = "android.intent.action.SEND"
    ACTION_SENDTO = "android.intent.action.SENDTO"
    ACTION_DIAL = "android.intent.action.DIAL"
    ACTION_CALL = "android.intent.action.CALL"
    ACTION_CALL_EMERGENCY = "android.intent.action.CALL_EMERGENCY"
    ACTION_INSERT = "android.intent.action.INSERT"
    ACTION_EDIT = "android.intent.action.EDIT"
    ACTION_DELETE = "android.intent.action.DELETE"
    ACTION_WEB_SEARCH = "android.intent.action.WEB_SEARCH"
    ACTION_SET_ALARM = "android.intent.action.SET_ALARM"
    ACTION_IMAGE_CAPTURE = "android.media.action.IMAGE_CAPTURE"
    ACTION_VIDEO_CAPTURE = "android.media.action.VIDEO_CAPTURE"
    ACTION_BATTERY_LOW = "android.intent.action.BATTERY_LOW"
    ACTION_BOOT_COMPLETED = "android.intent.action.BOOT_COMPLETED"
    ACTION_PICK = "android.intent.action.PICK"
    ACTION_GET_CONTENT = "android.intent.action.GET_CONTENT"
    ACTION_OPEN_DOCUMENT = "android.intent.action.OPEN_DOCUMENT"
    ACTION_CREATE_DOCUMENT = "android.intent.action.CREATE_DOCUMENT"
    ACTION_PACKAGE_ADDED = "android.intent.action.PACKAGE_ADDED"
    ACTION_POWER_CONNECTED = "android.intent.action.POWER_CONNECTED"
    ACTION_POWER_DISCONNECTED = "android.intent.action.POWER_DISCONNECTED"
    ACTION_SCREEN_ON = "android.intent.action.SCREEN_ON"
    ACTION_SCREEN_OFF = "android.intent.action.SCREEN_OFF"
    ACTION_TIME_TICK = "android.intent.action.TIME_TICK"
    ACTION_USER_PRESENT = "android.intent.action.USER_PRESENT"


class Intent:
    """模拟 android.content.Intent - 桌面端映射到 webbrowser+subprocess"""

    CATEGORY_DEFAULT = "android.intent.category.DEFAULT"
    FLAG_ACTIVITY_NEW_TASK = 0x10000000
    FLAG_ACTIVITY_CLEAR_TOP = 0x04000000
    FLAG_GRANT_READ_URI_PERMISSION = 0x00000001

    def __init__(self, action_or_params=None, uri_or_params=None):
        self._action = ""
        self._data: Optional[Uri] = None
        self._type = ""
        self._flags = 0
        self._categories: List[str] = []
        self._extras: Dict[str, Any] = {}
        self._component: Optional[tuple] = None
        self._package: Optional[str] = None

        if isinstance(action_or_params, str):
            self._action = action_or_params
        elif isinstance(action_or_params, dict):
            self._from_dict(action_or_params)

        if isinstance(uri_or_params, str):
            self._data = Uri.parse(uri_or_params)
        elif isinstance(uri_or_params, Uri):
            self._data = uri_or_params

    def _from_dict(self, params: dict):
        self._action = params.get("action", params.get("intentAction", ""))
        d = params.get("data", params.get("uri", params.get("uriString", "")))
        if d:
            self._data = Uri.parse(d) if isinstance(d, str) else d
        self._type = params.get("type", "")
        self._extras = params.get("extras", {})

    def setAction(self, action: str) -> "Intent":
        self._action = action
        return self

    def setData(self, data: str) -> "Intent":
        self._data = Uri.parse(data)
        return self

    def setType(self, type_: str) -> "Intent":
        self._type = type_
        return self

    def setDataAndType(self, data: str, type_: str) -> "Intent":
        self._data = Uri.parse(data)
        self._type = type_
        return self

    def putExtra(self, name: str, value: Any) -> "Intent":
        self._extras[name] = value
        return self

    def getStringExtra(self, name: str) -> Optional[str]:
        v = self._extras.get(name)
        return str(v) if v is not None else None

    def getIntExtra(self, name: str, default: int = 0) -> int:
        return int(self._extras.get(name, default))

    def getBooleanExtra(self, name: str, default: bool = False) -> bool:
        return bool(self._extras.get(name, default))

    def getLongExtra(self, name: str, default: int = 0) -> int:
        return int(self._extras.get(name, default))

    def getStringArrayListExtra(self, name: str) -> List[str]:
        val = self._extras.get(name, [])
        return [str(v) for v in val] if isinstance(val, list) else []

    def addCategory(self, category: str) -> "Intent":
        if category not in self._categories:
            self._categories.append(category)
        return self

    def setFlags(self, flags: int) -> "Intent":
        self._flags = flags
        return self

    def addFlags(self, flags: int) -> "Intent":
        self._flags |= flags
        return self

    def setComponent(self, package: str, cls: str) -> "Intent":
        self._component = (package, cls)
        self._package = package
        return self

    def setPackage(self, package: str) -> "Intent":
        self._package = package
        return self

    def getAction(self) -> str:
        return self._action

    def getData(self) -> Optional[Uri]:
        return self._data

    def getScheme(self) -> str:
        return self._data.getScheme() if self._data else ""

    def resolveActivity(self, pm: "PackageManager") -> str:
        """解析 Activity 名称"""
        action_map = {
            IntentAction.ACTION_VIEW: "com.android.browser/.BrowserActivity",
            IntentAction.ACTION_DIAL: "com.android.dialer/.DialtactsActivity",
            IntentAction.ACTION_SEND: "com.android.mms/.ui.ConversationList",
            IntentAction.ACTION_IMAGE_CAPTURE: "com.android.camera/.CameraActivity",
        }
        return action_map.get(self._action, "unknown")

    def to_dict(self) -> dict:
        return {
            "action": self._action,
            "data": str(self._data) if self._data else None,
            "type": self._type,
            "extras": self._extras,
            "package": self._package,
            "categories": self._categories,
            "flags": self._flags,
        }


# ============================================================
#  android.content.Context
# ============================================================

class Context:
    """模拟 android.content.Context"""

    MODE_PRIVATE = 0
    MODE_APPEND = 32768

    def __init__(self, package_name: str = None):
        self._package_name = package_name or _package_name
        self._package_manager = PackageManager()
        self._content_resolver = ContentResolver(self)
        self._files_dir = os.path.join(_app_data_dir, "files")
        self._cache_dir = os.path.join(_app_data_dir, "cache")
        self._preferences: Dict[str, Any] = {}
        self._resources = Resources()
        os.makedirs(self._files_dir, exist_ok=True)
        os.makedirs(self._cache_dir, exist_ok=True)

    def getPackageName(self) -> str:
        return self._package_name

    def getPackageManager(self) -> "PackageManager":
        return self._package_manager

    def getContentResolver(self) -> ContentResolver:
        return self._content_resolver

    def getFilesDir(self) -> str:
        return self._files_dir

    def getCacheDir(self) -> str:
        return self._cache_dir

    def getDir(self, name: str, mode: int = 0) -> str:
        d = os.path.join(_app_data_dir, name)
        os.makedirs(d, exist_ok=True)
        return d

    def getExternalFilesDir(self, type_: str = None) -> str:
        path = os.path.join(_sdcard_root, "Android", "data", self._package_name, "files")
        if type_:
            path = os.path.join(path, type_)
        os.makedirs(path, exist_ok=True)
        return path

    def getExternalCacheDir(self) -> str:
        path = os.path.join(_sdcard_root, "Android", "data", self._package_name, "cache")
        os.makedirs(path, exist_ok=True)
        return path

    def getExternalStorageDirectory(self) -> str:
        return _sdcard_root

    def getResources(self) -> "Resources":
        return self._resources

    def getSystemService(self, name: str) -> Any:
        """返回模拟的系统服务"""
        services = {
            "activity": ActivityManager(),
            "power": PowerManager(),
            "notification": NotificationManager(),
            "alarm": AlarmManager(),
            "location": LocationManager(),
            "sensor": SensorManager(),
            "audio": AudioManager(),
            "connectivity": ConnectivityManager(),
            "display": DisplayManager(),
            "window": WindowManager(),
            "input": InputManager(),
            "layout_inflater": LayoutInflater(),
            "storage": StorageManager(),
            "clipboard": ClipboardManager(),
            "download": DownloadManager(),
            "telephony": TelephonyManager(),
        }
        return services.get(name)

    def startActivity(self, intent: Intent) -> bool:
        """启动 Activity - 映射到桌面操作"""
        action = intent.getAction()

        # ACTION_VIEW: 打开 URL
        if action == IntentAction.ACTION_VIEW:
            data = intent.getData()
            if data:
                url = data.toString()
                if url.startswith("http"):
                    webbrowser.open(url)
                    return True
                return True

        # ACTION_DIAL: 拨号
        elif action == IntentAction.ACTION_DIAL:
            data = intent.getData()
            if data:
                console.log(f"[AndroidCompat] 模拟拨号: {data.toString()}")
            return True

        # ACTION_SEND: 分享
        elif action == IntentAction.ACTION_SEND:
            text = intent.getStringExtra("android.intent.extra.TEXT")
            if text:
                console.log(f"[AndroidCompat] 模拟分享文本: {text[:100]}")
            return True

        # ACTION_SET_ALARM: 设置闹钟
        elif action == IntentAction.ACTION_SET_ALARM:
            alarm_data = intent.to_dict()
            console.log(f"[AndroidCompat] 模拟设置闹钟: {alarm_data['extras']}")
            return True

        # ACTION_IMAGE_CAPTURE: 拍照
        elif action == IntentAction.ACTION_IMAGE_CAPTURE:
            console.log("[AndroidCompat] 模拟拍照")
            return True

        # ACTION_INSERT: 插入日历事件
        elif action == IntentAction.ACTION_INSERT:
            console.log(f"[AndroidCompat] 模拟插入日历事件")
            return True

        console.log(f"[AndroidCompat] 未映射的 Intent: {intent.getAction()}")
        return False

    def sendBroadcast(self, intent: Intent) -> None:
        """广播 - 桌面端模拟"""
        console.log(f"[AndroidCompat] 模拟广播: {intent.getAction()}")
        self._broadcast_receivers = getattr(self, "_broadcast_receivers", {})
        action = intent.getAction()
        if action in self._broadcast_receivers:
            for receiver in self._broadcast_receivers[action]:
                receiver.onReceive(self, intent)

    def registerReceiver(self, receiver: "BroadcastReceiver", filter_: "IntentFilter") -> Intent:
        self._broadcast_receivers = getattr(self, "_broadcast_receivers", {})
        action = filter_._action
        if action not in self._broadcast_receivers:
            self._broadcast_receivers[action] = []
        self._broadcast_receivers[action].append(receiver)
        return None

    def unregisterReceiver(self, receiver: "BroadcastReceiver") -> None:
        self._broadcast_receivers = getattr(self, "_broadcast_receivers", {})
        for action, receivers in list(self._broadcast_receivers.items()):
            self._broadcast_receivers[action] = [r for r in receivers if r != receiver]

    def getSharedPreferences(self, name: str, mode: int = 0) -> "SharedPreferences":
        return SharedPreferences(self, name)

    def checkSelfPermission(self, permission: str) -> int:
        """模拟权限检查 - 默认有所有权限"""
        return 0  # PERMISSION_GRANTED

    def getPackageCodePath(self) -> str:
        return __file__

    def getApplicationInfo(self) -> "ApplicationInfo":
        return ApplicationInfo()


class ApplicationInfo:
    """模拟 android.content.pm.ApplicationInfo"""
    def __init__(self):
        self.sourceDir = __file__
        self.dataDir = _app_data_dir
        self.nativeLibraryDir = os.path.join(os.path.dirname(sys.executable), "lib")


class Resources:
    """模拟 android.content.res.Resources"""
    def getString(self, id_or_name) -> str:
        return f"resource_string_{id_or_name}"
    def getDrawable(self, id_or_name) -> Any:
        return None
    def getColor(self, id_or_name) -> int:
        return 0xFF000000
    def getDimension(self, id_or_name) -> float:
        return 0.0
    def getIdentifier(self, name: str, defType: str, defPackage: str) -> int:
        return hash(name) % 0x7FFFFFFF


class SharedPreferences:
    """模拟 android.content.SharedPreferences"""
    def __init__(self, context: Context, name: str):
        self._path = os.path.join(_app_data_dir, f"prefs_{name}.json")
        self._data = {}
        if os.path.isfile(self._path):
            try:
                with open(self._path, "r") as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}

    def getString(self, key: str, default: str = "") -> str:
        return str(self._data.get(key, default))

    def getInt(self, key: str, default: int = 0) -> int:
        return int(self._data.get(key, default))

    def getBoolean(self, key: str, default: bool = False) -> bool:
        return bool(self._data.get(key, default))

    def getFloat(self, key: str, default: float = 0.0) -> float:
        return float(self._data.get(key, default))

    def getLong(self, key: str, default: int = 0) -> int:
        return int(self._data.get(key, default))

    def contains(self, key: str) -> bool:
        return key in self._data

    def edit(self) -> "SharedPreferencesEditor":
        return SharedPreferencesEditor(self)

    def getAll(self) -> Dict:
        return dict(self._data)


class SharedPreferencesEditor:
    """SharedPreferences.Editor"""
    def __init__(self, prefs: SharedPreferences):
        self._prefs = prefs
        self._changes = {}

    def putString(self, key: str, value: str) -> "SharedPreferencesEditor":
        self._changes[key] = value
        return self

    def putInt(self, key: str, value: int) -> "SharedPreferencesEditor":
        self._changes[key] = value
        return self

    def putBoolean(self, key: str, value: bool) -> "SharedPreferencesEditor":
        self._changes[key] = value
        return self

    def putLong(self, key: str, value: int) -> "SharedPreferencesEditor":
        self._changes[key] = value
        return self

    def remove(self, key: str) -> "SharedPreferencesEditor":
        self._changes[key] = None
        return self

    def clear(self) -> "SharedPreferencesEditor":
        self._changes = {}
        self._prefs._data = {}
        return self

    def apply(self) -> None:
        self.commit()

    def commit(self) -> bool:
        for k, v in self._changes.items():
            if v is None:
                self._prefs._data.pop(k, None)
            else:
                self._prefs._data[k] = v
        try:
            os.makedirs(os.path.dirname(self._prefs._path), exist_ok=True)
            with open(self._prefs._path, "w", encoding="utf-8") as f:
                json.dump(self._prefs._data, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False


# ============================================================
#  android.content.BroadcastReceiver + IntentFilter
# ============================================================

class BroadcastReceiver:
    """模拟 android.content.BroadcastReceiver"""
    def onReceive(self, context: Context, intent: Intent) -> None:
        pass


class IntentFilter:
    """模拟 android.content.IntentFilter"""
    def __init__(self, action: str = None):
        self._action = action
        self._actions: List[str] = []
        if action:
            self._actions.append(action)

    def addAction(self, action: str) -> None:
        if action not in self._actions:
            self._actions.append(action)


# ============================================================
#  android.os (Build, Environment, PowerManager, Vibration)
# ============================================================

class Build:
    """模拟 android.os.Build"""

    class VERSION:
        SDK_INT = 33  # Android 13
        RELEASE = "13"
        CODENAME = "Tiramisu"
        INCREMENTAL = "2026.06"
        SDK_NAME = "Tiramisu"

    BOARD = "generic"
    BRAND = "OperitCompat"
    DEVICE = "pc"
    DISPLAY = "OP1.230607.001"
    FINGERPRINT = "generic/OperitCompat/pc:13/TP1A.220624.014/12345678:user/release-keys"
    HARDWARE = "x86_64"
    HOST = "localhost"
    ID = "TP1A.220624.014"
    MANUFACTURER = "OperitCompat"
    MODEL = platform.node()
    PRODUCT = "operit_compat_pc"
    SERIAL = "0123456789ABCDEF"
    SUPPORTED_ABIS = [platform.machine()]
    TAGS = "release-keys"
    TIME = int(time.time())
    TYPE = "user"
    USER = os.environ.get("USER", "user")

    @staticmethod
    def getRadioVersion() -> str:
        return "unknown"

    @staticmethod
    def getSerial() -> str:
        return Build.SERIAL


class Environment:
    """模拟 android.os.Environment"""

    MEDIA_MOUNTED = "mounted"
    MEDIA_UNMOUNTED = "unmounted"

    @staticmethod
    def getExternalStorageDirectory() -> str:
        return _sdcard_root

    @staticmethod
    def getExternalStoragePublicDirectory(type_: str) -> str:
        mapping = {
            "DCIM": "DCIM",
            "Download": "Download",
            "Documents": "Documents",
            "Music": "Music",
            "Movies": "Movies",
            "Pictures": "Pictures",
            "Alarms": "Alarms",
            "Notifications": "Notifications",
            "Ringtones": "Ringtones",
        }
        subdir = mapping.get(type_, type_)
        path = os.path.join(_sdcard_root, subdir)
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def getDataDirectory() -> str:
        return _app_data_dir

    @staticmethod
    def getDownloadCacheDirectory() -> str:
        return os.path.join(_app_data_dir, "cache", "downloads")

    @staticmethod
    def getExternalStorageState() -> str:
        return Environment.MEDIA_MOUNTED


class PowerManager:
    """模拟 android.os.PowerManager"""
    PARTIAL_WAKE_LOCK = 1
    SCREEN_BRIGHT_WAKE_LOCK = 10
    FULL_WAKE_LOCK = 26
    ACQUIRE_CAUSES_WAKEUP = 0x10000000
    ON_AFTER_RELEASE = 0x20000000

    def newWakeLock(self, levelAndFlags: int, tag: str) -> "WakeLock":
        return WakeLock()

    def isScreenOn(self) -> bool:
        return True

    def isInteractive(self) -> bool:
        return True

    def isPowerSaveMode(self) -> bool:
        return False

    def isDeviceIdleMode(self) -> bool:
        return False

    def reboot(self, reason: str = None) -> None:
        console.log(f"[AndroidCompat] 模拟重启: {reason}")

    def goToSleep(self, timeMs: int) -> None:
        pass


class WakeLock:
    """模拟 android.os.PowerManager.WakeLock"""
    def acquire(self, timeoutMs: int = None) -> None:
        pass
    def release(self, flags: int = 0) -> None:
        pass
    def isHeld(self) -> bool:
        return False
    def setReferenceCounted(self, value: bool) -> None:
        pass


class VibrationEffect:
    """模拟 android.os.VibrationEffect"""
    DEFAULT_AMPLITUDE = -1

    @staticmethod
    def createOneShot(milliseconds: int, amplitude: int = DEFAULT_AMPLITUDE) -> "VibrationEffect":
        return VibrationEffect()

    @staticmethod
    def createWaveform(timings: List[int], amplitudes: List[int], repeat: int) -> "VibrationEffect":
        return VibrationEffect()


class Vibrator:
    """模拟 android.os.Vibrator"""
    def vibrate(self, effect_or_ms) -> None:
        pass
    def hasVibrator(self) -> bool:
        return False
    def cancel(self) -> None:
        pass


# ============================================================
#  android.app services
# ============================================================

class ActivityManager:
    """模拟 android.app.ActivityManager"""
    def getRunningAppProcesses(self) -> List:
        if HAS_PSUTIL:
            return [{"processName": p.name(), "pid": p.pid,
                     "importance": 100} for p in psutil.process_iter()[:10]]
        return [{"processName": "python", "pid": os.getpid(), "importance": 100}]

    def getMemoryInfo(self) -> "MemoryInfo":
        return ActivityManager.MemoryInfo()

    def killBackgroundProcesses(self, packageName: str) -> None:
        console.log(f"[AndroidCompat] 模拟结束进程: {packageName}")

    class MemoryInfo:
        def __init__(self):
            self.availMem = 8 * 1024 * 1024 * 1024  # 8GB
            self.totalMem = 16 * 1024 * 1024 * 1024  # 16GB
            self.threshold = 256 * 1024 * 1024       # 256MB
            self.lowMemory = False

    def getAppTasks(self) -> List:
        return []


class PackageManager:
    """模拟 android.content.pm.PackageManager"""

    def getInstalledPackages(self, flags: int = 0) -> List["PackageInfo"]:
        """返回已安装的应用列表"""
        packages = []
        system_packages = [
            "com.android.settings", "com.android.systemui",
            "com.android.launcher3", "com.google.android.gms",
            "com.google.android.gsf", "com.android.documentsui",
            "com.android.providers.downloads", "com.android.vending",
        ]
        for pkg in system_packages:
            packages.append(PackageInfo(pkg, "13", True))
        packages.append(PackageInfo(_package_name, "1.0.0", False))
        return packages

    def getPackageInfo(self, packageName: str, flags: int = 0) -> Optional["PackageInfo"]:
        for pkg in self.getInstalledPackages():
            if pkg.packageName == packageName:
                return pkg
        return PackageInfo(packageName, "0.0.0", False)

    def getApplicationLabel(self, info: "ApplicationInfo") -> str:
        return info.packageName if hasattr(info, 'packageName') else _package_name

    def queryIntentActivities(self, intent: Intent, flags: int = 0) -> List:
        return [ResolveInfo()]

    def resolveActivity(self, intent: Intent, flags: int = 0) -> Optional["ResolveInfo"]:
        return ResolveInfo()

    def checkPermission(self, permission: str, pid: int, uid: int) -> int:
        return 0  # PERMISSION_GRANTED

    def getPackagesForUid(self, uid: int) -> List[str]:
        return [_package_name]

    @staticmethod
    def getPermission(permission: str) -> str:
        return f"android.permission.{permission}"


class PackageInfo:
    def __init__(self, pkg_name: str, version: str = "1.0", is_system: bool = False):
        self.packageName = pkg_name
        self.versionName = version
        self.versionCode = int(version.replace(".", ""))
        self.applicationInfo = ApplicationInfo()
        self.applicationInfo.packageName = pkg_name
        self.firstInstallTime = int(time.time())
        self.lastUpdateTime = int(time.time())
        self.sharedUserId = None
        self.requestedPermissions = []
        self.gids = []


class ResolveInfo:
    def __init__(self):
        self.activityInfo = ActivityInfo()
        self.resolvePackageName = "com.android.browser"
        self.priority = 0

    def loadLabel(self, pm: PackageManager) -> str:
        return self.resolvePackageName


class ActivityInfo:
    def __init__(self):
        self.packageName = _package_name
        self.name = "MainActivity"
        self.processName = _package_name
        self.taskAffinity = _package_name
        self.launchMode = 0
        self.flags = 0
        self.screenOrientation = 1
        self.configChanges = 0
        self.exported = True
        self.theme = 0


class NotificationManager:
    """模拟 android.app.NotificationManager"""
    IMPORTANCE_HIGH = 4
    IMPORTANCE_DEFAULT = 3
    IMPORTANCE_LOW = 2
    IMPORTANCE_MIN = 1
    IMPORTANCE_NONE = 0

    def notify(self, id_or_tag, notification_or_id=None) -> None:
        console.log(f"[AndroidCompat] 模拟通知: id={id_or_tag}")

    def cancel(self, id_or_tag, notification_id=None) -> None:
        pass

    def cancelAll(self) -> None:
        pass

    def createNotificationChannel(self, channel) -> None:
        pass

    def getNotificationChannel(self, channelId: str) -> Optional["NotificationChannel"]:
        return NotificationChannel(channelId, "Default", self.IMPORTANCE_DEFAULT)


class NotificationChannel:
    def __init__(self, id_: str, name: str, importance: int):
        self.id = id_
        self.name = name
        self.importance = importance
        self.description = ""
        self.enableVibration = True
        self.enableLights = True


class AlarmManager:
    """模拟 android.app.AlarmManager"""
    RTC = 0
    RTC_WAKEUP = 1
    ELAPSED_REALTIME = 2
    ELAPSED_REALTIME_WAKEUP = 3
    INTERVAL_FIFTEEN_MINUTES = 900000
    INTERVAL_HALF_HOUR = 1800000
    INTERVAL_HOUR = 3600000
    INTERVAL_DAY = 86400000

    def set(self, type_: int, triggerAtMillis: int, operation: Any) -> None:
        console.log(f"[AndroidCompat] 模拟闹钟: type={type_}, trigger={triggerAtMillis}")

    def setRepeating(self, type_: int, triggerAtMillis: int, intervalMillis: int, operation: Any) -> None:
        console.log(f"[AndroidCompat] 模拟重复闹钟: trigger={triggerAtMillis}, interval={intervalMillis}")

    def setExact(self, type_: int, triggerAtMillis: int, operation: Any) -> None:
        self.set(type_, triggerAtMillis, operation)

    def cancel(self, operation: Any) -> None:
        pass

    def setAlarmClock(self, info: "AlarmClockInfo", operation: Any) -> None:
        pass


# ============================================================
#  android.graphics
# ============================================================

class Color:
    """模拟 android.graphics.Color"""
    BLACK = 0xFF000000
    WHITE = 0xFFFFFFFF
    RED = 0xFFFF0000
    GREEN = 0xFF00FF00
    BLUE = 0xFF0000FF
    YELLOW = 0xFFFFFF00
    CYAN = 0xFF00FFFF
    MAGENTA = 0xFFFF00FF
    GRAY = 0xFF808080
    TRANSPARENT = 0x00000000

    @staticmethod
    def argb(alpha: int, red: int, green: int, blue: int) -> int:
        return (alpha << 24) | (red << 16) | (green << 8) | blue

    @staticmethod
    def alpha(color: int) -> int:
        return (color >> 24) & 0xFF

    @staticmethod
    def red(color: int) -> int:
        return (color >> 16) & 0xFF

    @staticmethod
    def green(color: int) -> int:
        return (color >> 8) & 0xFF

    @staticmethod
    def blue(color: int) -> int:
        return color & 0xFF

    @staticmethod
    def parseColor(colorString: str) -> int:
        colorString = colorString.strip()
        if colorString.startswith("#"):
            hex_str = colorString[1:]
            if len(hex_str) == 6:
                return 0xFF000000 | int(hex_str, 16)
            elif len(hex_str) == 8:
                return int(hex_str, 16)
        return Color.BLACK

    @staticmethod
    def rgb(red: int, green: int, blue: int) -> int:
        return 0xFF000000 | (red << 16) | (green << 8) | blue

    @staticmethod
    def toArgb(color: int) -> int:
        return color

    @staticmethod
    def toColor(c):
        return c


class Rect:
    """模拟 android.graphics.Rect"""
    def __init__(self, left: int = 0, top: int = 0, right: int = 0, bottom: int = 0):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    def width(self) -> int:
        return self.right - self.left

    def height(self) -> int:
        return self.bottom - self.top

    def centerX(self) -> int:
        return (self.left + self.right) // 2

    def centerY(self) -> int:
        return (self.top + self.bottom) // 2

    def contains(self, x: int, y: int) -> bool:
        return self.left <= x <= self.right and self.top <= y <= self.bottom

    def isEmpty(self) -> bool:
        return self.width() <= 0 or self.height() <= 0

    def inset(self, dx: int, dy: int) -> None:
        self.left += dx
        self.right -= dx
        self.top += dy
        self.bottom -= dy

    def offset(self, dx: int, dy: int) -> None:
        self.left += dx
        self.right += dx
        self.top += dy
        self.bottom += dy

    def toShortString(self) -> str:
        return f"[{self.left},{self.top}][{self.right},{self.bottom}]"

    def __repr__(self):
        return self.toShortString()


class Paint:
    """模拟 android.graphics.Paint"""
    ANTI_ALIAS_FLAG = 0x01
    FILL = 0
    STROKE = 1
    FILL_AND_STROKE = 2

    def __init__(self, flags: int = 0):
        self._flags = flags
        self._color = Color.BLACK
        self._strokeWidth = 0.0
        self._textSize = 16.0
        self._style = self.FILL
        self._alpha = 255
        self._typeface = None

    def setColor(self, color: int) -> None:
        self._color = color

    def getColor(self) -> int:
        return self._color

    def setStrokeWidth(self, width: float) -> None:
        self._strokeWidth = width

    def setTextSize(self, size: float) -> None:
        self._textSize = size

    def setStyle(self, style: int) -> None:
        self._style = style

    def setAlpha(self, alpha: int) -> None:
        self._alpha = alpha

    def setTypeface(self, typeface) -> None:
        self._typeface = typeface

    def measureText(self, text: str) -> float:
        return len(text) * self._textSize * 0.6


class Bitmap:
    """模拟 android.graphics.Bitmap - 基于 PIL"""

    class Config:
        ARGB_8888 = "ARGB_8888"
        RGB_565 = "RGB_565"
        ALPHA_8 = "ALPHA_8"

    @staticmethod
    def createBitmap(width: int, height: int, config: str = Config.ARGB_8888) -> "Bitmap":
        return Bitmap(width, height, config)

    @staticmethod
    def createScaledBitmap(src: "Bitmap", dstWidth: int, dstHeight: int, filter: bool) -> "Bitmap":
        if HAS_PIL:
            pil_img = src._pil.resize((dstWidth, dstHeight), Image.LANCZOS if filter else Image.NEAREST)
            result = Bitmap(dstWidth, dstHeight, src._config)
            result._pil = pil_img
            return result
        return Bitmap(dstWidth, dstHeight, src._config)

    @staticmethod
    def decodeFile(path: str) -> Optional["Bitmap"]:
        if HAS_PIL:
            try:
                pil_img = Image.open(path)
                bmp = Bitmap(pil_img.width, pil_img.height)
                bmp._pil = pil_img
                return bmp
            except Exception:
                return None
        return None

    @staticmethod
    def decodeByteArray(data: bytes, offset: int, length: int) -> Optional["Bitmap"]:
        if HAS_PIL:
            try:
                pil_img = Image.open(io.BytesIO(data[offset:offset + length]))
                bmp = Bitmap(pil_img.width, pil_img.height)
                bmp._pil = pil_img
                return bmp
            except Exception:
                return None
        return None

    def __init__(self, width: int, height: int, config: str = Config.ARGB_8888):
        self._width = width
        self._height = height
        self._config = config
        if HAS_PIL:
            self._pil = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        else:
            self._pil = None
        self._recycled = False

    def getWidth(self) -> int:
        return self._width

    def getHeight(self) -> int:
        return self._height

    def getConfig(self) -> str:
        return self._config

    def getPixel(self, x: int, y: int) -> int:
        if HAS_PIL and self._pil:
            try:
                r, g, b, a = self._pil.getpixel((x, y))
                return Color.argb(a, r, g, b)
            except Exception:
                pass
        return 0

    def setPixel(self, x: int, y: int, color: int) -> None:
        if HAS_PIL and self._pil:
            a = Color.alpha(color)
            r = Color.red(color)
            g = Color.green(color)
            b = Color.blue(color)
            self._pil.putpixel((x, y), (r, g, b, a))

    def eraseColor(self, color: int) -> None:
        if HAS_PIL and self._pil:
            r, g, b, a = Color.red(color), Color.green(color), Color.blue(color), Color.alpha(color)
            self._pil = Image.new("RGBA", (self._width, self._height), (r, g, b, a))

    def compress(self, format_: "Bitmap.CompressFormat", quality: int, stream: io.BytesIO) -> bool:
        if HAS_PIL and self._pil:
            pil_fmt = "JPEG" if format_ == Bitmap.CompressFormat.JPEG else "PNG"
            if self._pil.mode == "RGBA":
                self._pil = self._pil.convert("RGB") if pil_fmt == "JPEG" else self._pil
            self._pil.save(stream, format=pil_fmt, quality=quality)
            return True
        return False

    def copy(self, config: str, isMutable: bool) -> "Bitmap":
        result = Bitmap(self._width, self._height, config)
        if HAS_PIL and self._pil:
            result._pil = self._pil.copy()
        return result

    def recycle(self) -> None:
        self._recycled = True
        self._pil = None

    def isRecycled(self) -> bool:
        return self._recycled

    class CompressFormat:
        JPEG = "JPEG"
        PNG = "PNG"
        WEBP = "WEBP"


class Canvas:
    """模拟 android.graphics.Canvas - 基于 PIL"""

    def __init__(self, bitmap: Bitmap = None):
        self._bitmap = bitmap
        self._draw = ImageDraw.Draw(bitmap._pil) if HAS_PIL and bitmap and bitmap._pil else None

    def drawColor(self, color: int) -> None:
        if self._bitmap:
            self._bitmap.eraseColor(color)

    def drawPoint(self, x: float, y: float, paint: Paint) -> None:
        if self._draw:
            c = Color.toArgb(paint._color)
            self._draw.point([(x, y)], fill=(Color.red(c), Color.green(c), Color.blue(c), Color.alpha(c)))

    def drawLine(self, startX: float, startY: float, stopX: float, stopY: float, paint: Paint) -> None:
        if self._draw:
            c = Color.toArgb(paint._color)
            self._draw.line([(startX, startY), (stopX, stopY)],
                           fill=(Color.red(c), Color.green(c), Color.blue(c), Color.alpha(c)),
                           width=max(1, int(paint._strokeWidth)))

    def drawRect(self, rect: Rect, paint: Paint) -> None:
        if self._draw:
            c = Color.toArgb(paint._color)
            self._draw.rectangle([rect.left, rect.top, rect.right, rect.bottom],
                                fill=(Color.red(c), Color.green(c), Color.blue(c), Color.alpha(c)))

    def drawCircle(self, cx: float, cy: float, radius: float, paint: Paint) -> None:
        if self._draw:
            c = Color.toArgb(paint._color)
            self._draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                              fill=(Color.red(c), Color.green(c), Color.blue(c), Color.alpha(c)))

    def drawText(self, text: str, x: float, y: float, paint: Paint) -> None:
        if self._draw:
            c = Color.toArgb(paint._color)
            self._draw.text((x, y), text, fill=(Color.red(c), Color.green(c), Color.blue(c), Color.alpha(c)))

    def drawBitmap(self, bitmap: Bitmap, left: float, top: float, paint: Paint = None) -> None:
        if HAS_PIL and self._bitmap and self._bitmap._pil and bitmap._pil:
            self._bitmap._pil.paste(bitmap._pil, (int(left), int(top)))

    def getWidth(self) -> int:
        return self._bitmap._width if self._bitmap else 0

    def getHeight(self) -> int:
        return self._bitmap._height if self._bitmap else 0

    def save(self) -> int:
        return 1

    def restore(self) -> None:
        pass


class Typeface:
    """模拟 android.graphics.Typeface"""
    DEFAULT = "DEFAULT"
    BOLD = "BOLD"
    ITALIC = "ITALIC"
    BOLD_ITALIC = "BOLD_ITALIC"
    MONOSPACE = "MONOSPACE"
    SANS_SERIF = "SANS_SERIF"
    SERIF = "SERIF"

    @staticmethod
    def defaultFromStyle(style: int) -> "Typeface":
        return Typeface()

    @staticmethod
    def create(name: str, style: int) -> "Typeface":
        return Typeface()


class BitmapFactory:
    """模拟 android.graphics.BitmapFactory"""

    @staticmethod
    def decodeFile(path: str, opts: dict = None) -> Optional[Bitmap]:
        return Bitmap.decodeFile(path)

    @staticmethod
    def decodeByteArray(data: bytes, offset: int, length: int, opts: dict = None) -> Optional[Bitmap]:
        return Bitmap.decodeByteArray(data, offset, length)

    @staticmethod
    def decodeResource(res: Resources, id_: int) -> Optional[Bitmap]:
        return Bitmap.createBitmap(100, 100)

    class Options:
        def __init__(self):
            self.inSampleSize = 1
            self.inPreferredConfig = Bitmap.Config.ARGB_8888
            self.inJustDecodeBounds = False
            self.outWidth = 0
            self.outHeight = 0
            self.inMutable = False


class Matrix:
    """模拟 android.graphics.Matrix"""
    def __init__(self):
        self._values = [1, 0, 0, 0, 1, 0, 0, 0, 1]

    def setScale(self, sx: float, sy: float) -> None:
        self._values[0] = sx
        self._values[4] = sy

    def setTranslate(self, dx: float, dy: float) -> None:
        self._values[2] = dx
        self._values[5] = dy

    def setRotate(self, degrees: float) -> None:
        rad = math.radians(degrees)
        self._values[0] = math.cos(rad)
        self._values[1] = -math.sin(rad)
        self._values[3] = math.sin(rad)
        self._values[4] = math.cos(rad)

    def postScale(self, sx: float, sy: float) -> None:
        self._values[0] *= sx
        self._values[4] *= sy

    def postTranslate(self, dx: float, dy: float) -> None:
        self._values[2] += dx
        self._values[5] += dy

    def mapRect(self, rect: Rect) -> Rect:
        return rect


# ============================================================
#  android.graphics.pdf.PdfRenderer
# ============================================================

class PdfRenderer:
    """模拟 android.graphics.pdf.PdfRenderer - 基于 PyMuPDF"""

    def __init__(self, input: Any, renderMode: int = 0):
        self._pageCount = 0
        self._currentPage = None
        self._closed = False
        try:
            import fitz
            self._doc = fitz.open(input)
            self._pageCount = len(self._doc)
        except ImportError:
            console.log("[PdfRenderer] PyMuPDF 未安装，使用 pdf2image 降级")
            self._pageCount = 0
            try:
                from pdf2image import convert_from_path
                self._images = convert_from_path(input if isinstance(input, str) else "temp.pdf")
                self._pageCount = len(self._images)
            except ImportError:
                console.log("[PdfRenderer] pdf2image 也未安装，使用空回退")
                self._images = []

    def getPageCount(self) -> int:
        return self._pageCount

    def openPage(self, index: int) -> "PdfRenderer.Page":
        self._currentPage = PdfRenderer.Page(index)
        try:
            if hasattr(self, '_doc'):
                fitz_page = self._doc[index]
                pix = fitz_page.get_pixmap()
                pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                bmp = Bitmap(pix.width, pix.height)
                bmp._pil = pil_img
                self._currentPage._render = bmp
                self._currentPage._width = pix.width
                self._currentPage._height = pix.height
            elif hasattr(self, '_images') and index < len(self._images):
                pil_img = self._images[index]
                bmp = Bitmap(pil_img.width, pil_img.height)
                bmp._pil = pil_img
                self._currentPage._render = bmp
                self._currentPage._width = pil_img.width
                self._currentPage._height = pil_img.height
        except Exception as e:
            console.log(f"[PdfRenderer] 渲染第 {index} 页出错: {e}")
        return self._currentPage

    def close(self) -> None:
        self._closed = True
        if hasattr(self, '_doc'):
            self._doc.close()

    class Page:
        RENDER_MODE_FOR_DISPLAY = 1
        RENDER_MODE_FOR_PRINT = 2

        def __init__(self, index: int):
            self._index = index
            self._render = None
            self._width = 0
            self._height = 0

        def getWidth(self) -> int:
            return self._width

        def getHeight(self) -> int:
            return self._height

        def render(self, bitmap: Bitmap, left: int, top: int, right: int, bottom: int,
                   paintFlags: int, renderMode: int = RENDER_MODE_FOR_DISPLAY) -> None:
            if self._render and self._render._pil and bitmap._pil:
                bitmap._pil.paste(self._render._pil.resize((right - left, bottom - top)))

        def close(self) -> None:
            pass


# ============================================================
#  android.view / accessibility 体系 (UINode)
# ============================================================

class View:
    """模拟 android.view.View"""
    def __init__(self, context: Context = None):
        self._context = context
        self._x = 0
        self._y = 0
        self._width = 0
        self._height = 0
        self._visible = True
        self._enabled = True
        self._clickable = False
        self._text = ""
        self._contentDescription = ""
        self._children: List[View] = []
        self._parent: Optional[View] = None
        self._backgroundColor = Color.TRANSPARENT
        self._alpha = 1.0
        self._rotation = 0.0
        self._scaleX = 1.0
        self._scaleY = 1.0
        self._tag = None
        self._id = -1
        self._onClickListener = None
        self._elevation = 0.0

    def getX(self) -> float: return float(self._x)
    def getY(self) -> float: return float(self._y)
    def getWidth(self) -> int: return self._width
    def getHeight(self) -> int: return self._height
    def getVisibility(self) -> int: return 0 if self._visible else 8
    def isEnabled(self) -> bool: return self._enabled
    def isClickable(self) -> bool: return self._clickable
    def isShown(self) -> bool: return self._visible

    def setVisibility(self, visibility: int) -> None:
        self._visible = (visibility != 8)
    def setEnabled(self, enabled: bool) -> None: self._enabled = enabled
    def setClickable(self, clickable: bool) -> None: self._clickable = clickable
    def setBackgroundColor(self, color: int) -> None: self._backgroundColor = color
    def setAlpha(self, alpha: float) -> None: self._alpha = alpha
    def setRotation(self, rotation: float) -> None: self._rotation = rotation
    def setScaleX(self, sx: float) -> None: self._scaleX = sx
    def setScaleY(self, sy: float) -> None: self._scaleY = sy
    def setTag(self, tag: Any) -> None: self._tag = tag
    def setId(self, id_: int) -> None: self._id = id_

    def getText(self) -> str: return self._text
    def setText(self, text: str) -> None: self._text = text
    def getContentDescription(self) -> str: return self._contentDescription
    def setContentDescription(self, desc: str) -> None: self._contentDescription = desc

    def getParent(self) -> Optional["View"]: return self._parent
    def getChildCount(self) -> int: return len(self._children)
    def getChildAt(self, index: int) -> Optional["View"]:
        return self._children[index] if 0 <= index < len(self._children) else None
    def addView(self, child: "View") -> None:
        self._children.append(child)
        child._parent = self
    def removeView(self, child: "View") -> None:
        if child in self._children:
            self._children.remove(child)
            child._parent = None
    def removeAllViews(self) -> None:
        for child in self._children:
            child._parent = None
        self._children.clear()

    def findViewById(self, id_: int) -> Optional["View"]:
        if self._id == id_: return self
        for child in self._children:
            result = child.findViewById(id_)
            if result: return result
        return None

    def getGlobalVisibleRect(self, rect: Rect) -> bool:
        r = Rect(self._x, self._y, self._x + self._width, self._y + self._height)
        rect.left, rect.top, rect.right, rect.bottom = r.left, r.top, r.right, r.bottom
        return self._visible

    def performClick(self) -> bool:
        if self._onClickListener:
            self._onClickListener.onClick(self)
            return True
        if HAS_PYAUTOGUI:
            pyautogui.click(self._x + self._width // 2, self._y + self._height // 2)
            return True
        return False

    def setOnClickListener(self, listener) -> None:
        self._onClickListener = listener

    def post(self, action: Callable) -> bool:
        action()
        return True

    def postDelayed(self, action: Callable, delayMs: int) -> bool:
        import threading
        timer = threading.Timer(delayMs / 1000, action)
        timer.start()
        return True

    def invalidate(self) -> None: pass


class TextView(View):
    """模拟 android.widget.TextView"""
    def __init__(self, context: Context = None):
        super().__init__(context)
        self._text = ""
        self._textSize = 16.0
        self._textColor = Color.BLACK
        self._gravity = 0
        self._lines = 1
        self._typeface = None
        self._inputType = 0
        self._hint = ""
        self._maxLines = 1
        self._ellipsize = None

    def setTextSize(self, size: float) -> None: self._textSize = size
    def setTextColor(self, color: int) -> None: self._textColor = color
    def setGravity(self, gravity: int) -> None: self._gravity = gravity
    def setLines(self, lines: int) -> None: self._lines = lines
    def setHint(self, hint: str) -> None: self._hint = hint
    def setInputType(self, type_: int) -> None: self._inputType = type_
    def setMaxLines(self, maxLines: int) -> None: self._maxLines = maxLines
    def setEllipsize(self, where: str) -> None: self._ellipsize = where
    def getText(self) -> str: return self._text
    def setText(self, text: str) -> None: self._text = text
    def getTextSize(self) -> float: return self._textSize
    def getCurrentTextColor(self) -> int: return self._textColor
    def getHint(self) -> str: return self._hint


class EditText(TextView):
    """模拟 android.widget.EditText"""
    def __init__(self, context: Context = None):
        super().__init__(context)
        self._selectionStart = 0
        self._selectionEnd = 0

    def getSelectionStart(self) -> int: return self._selectionStart
    def getSelectionEnd(self) -> int: return self._selectionEnd
    def setSelection(self, start: int, stop: int = None) -> None:
        self._selectionStart = start
        self._selectionEnd = stop if stop is not None else start

    def selectAll(self) -> None:
        self._selectionStart = 0
        self._selectionEnd = len(self._text)

    def append(self, text: str) -> None:
        self._text += text


class Button(TextView):
    """模拟 android.widget.Button"""
    def __init__(self, context: Context = None):
        super().__init__(context)
        self._clickable = True


class ImageView(View):
    """模拟 android.widget.ImageView"""
    ScaleType = type("ScaleType", (), {"FIT_XY": "FIT_XY", "CENTER_CROP": "CENTER_CROP",
                                        "CENTER_INSIDE": "CENTER_INSIDE", "MATRIX": "MATRIX"})

    def __init__(self, context: Context = None):
        super().__init__(context)
        self._imageBitmap = None
        self._scaleType = ImageView.ScaleType.FIT_CENTER

    def setImageBitmap(self, bmp: Bitmap) -> None: self._imageBitmap = bmp
    def setImageResource(self, resId: int) -> None: pass
    def setScaleType(self, scaleType: str) -> None: self._scaleType = scaleType
    def getDrawable(self) -> Any: return self._imageBitmap


class ScrollView(View):
    """模拟 android.widget.ScrollView"""
    def __init__(self, context: Context = None):
        super().__init__(context)
        self._scrollX = 0
        self._scrollY = 0

    def scrollTo(self, x: int, y: int) -> None:
        self._scrollX = x
        self._scrollY = y

    def scrollBy(self, dx: int, dy: int) -> None:
        self._scrollX += dx
        self._scrollY += dy

    def fullScroll(self, direction: int) -> bool: return True

    def getScrollX(self) -> int: return self._scrollX
    def getScrollY(self) -> int: return self._scrollY


class RecyclerView(View):
    """模拟 androidx.recyclerview.widget.RecyclerView"""
    def smoothScrollToPosition(self, position: int) -> None: pass


class ViewGroup(View):
    """模拟 android.view.ViewGroup"""
    def __init__(self, context: Context = None):
        super().__init__(context)

    def addView(self, child: View) -> None:
        self._children.append(child)
        child._parent = self

    def removeView(self, child: View) -> None:
        self._children.remove(child)
        child._parent = None

    def removeAllViews(self) -> None:
        self._children.clear()

    def getChildCount(self) -> int:
        return len(self._children)

    def getChildAt(self, index: int) -> Optional[View]:
        return self._children[index] if 0 <= index < len(self._children) else None

    def findViewById(self, id_: int) -> Optional[View]:
        return super().findViewById(id_)

    def indexOfChild(self, child: View) -> int:
        return self._children.index(child) if child in self._children else -1


class LinearLayout(ViewGroup):
    """模拟 android.widget.LinearLayout"""
    HORIZONTAL = 0
    VERTICAL = 1

    def __init__(self, context: Context = None):
        super().__init__(context)
        self._orientation = self.VERTICAL
        self._gravity = 0

    def setOrientation(self, orientation: int) -> None:
        self._orientation = orientation

    def getOrientation(self) -> int:
        return self._orientation

    def setGravity(self, gravity: int) -> None:
        self._gravity = gravity


class FrameLayout(ViewGroup):
    """模拟 android.widget.FrameLayout"""
    def __init__(self, context: Context = None):
        super().__init__(context)


class RelativeLayout(ViewGroup):
    """模拟 android.widget.RelativeLayout"""
    def __init__(self, context: Context = None):
        super().__init__(context)


# ============================================================
#  UINode - Android UI 自动化核心
# ============================================================

class UINode:
    """模拟 Android 无障碍 UI 节点树 - 基于 pyautogui / Playwright"""

    def __init__(self):
        self._nodes: List[dict] = []
        self._focused_node = None

    @staticmethod
    async def getCurrentPage() -> "AccessibilityPage":
        """获取当前页面无障碍树"""
        return AccessibilityPage()


class AccessibilityNodeInfo:
    """模拟 android.view.accessibility.AccessibilityNodeInfo"""
    def __init__(self):
        self._node_id = hash(str(time.time() + random.random()))
        self.packageName = _package_name
        self.className = "android.view.View"
        self.text = ""
        self.contentDescription = ""
        self.viewId = ""
        self.resourceName = ""
        self.boundsInScreen = Rect(0, 0, 1920, 1080)
        self.visibleToUser = True
        self.enabled = True
        self.clickable = False
        self.longClickable = False
        self.focusable = False
        self.focused = False
        self.scrollable = False
        self.checkable = False
        self.checked = False
        self.selected = False
        self.password = False
        self._children: List["AccessibilityNodeInfo"] = []
        self._parent = None
        self.childCount = 0
        self.row = -1
        self.column = -1
        self.rowCount = -1
        self.columnCount = -1
        self.inputType = 0
        self.hintText = ""
        self.errorText = ""
        self.depth = 0

    def getChild(self, index: int) -> Optional["AccessibilityNodeInfo"]:
        return self._children[index] if 0 <= index < len(self._children) else None

    def getChildCount(self) -> int:
        return len(self._children)

    def getParent(self) -> Optional["AccessibilityNodeInfo"]:
        return self._parent

    def addChild(self, child: "AccessibilityNodeInfo") -> None:
        self._children.append(child)
        child._parent = self
        self.childCount = len(self._children)
        child.depth = self.depth + 1

    def findByText(self, text: str) -> Optional["AccessibilityNodeInfo"]:
        if text in (self.text or "") or text in (self.contentDescription or ""):
            return self
        for child in self._children:
            result = child.findByText(text)
            if result:
                return result
        return None

    def findById(self, id_: str) -> Optional["AccessibilityNodeInfo"]:
        if self.viewId == id_ or self.resourceName == id_:
            return self
        for child in self._children:
            result = child.findById(id_)
            if result:
                return result
        return None

    def findAccessibilityFocus(self) -> Optional["AccessibilityNodeInfo"]:
        if self.focused:
            return self
        for child in self._children:
            result = child.findAccessibilityFocus()
            if result:
                return result
        return None

    def performAction(self, action: int) -> bool:
        if action == 16:  # CLICK
            if HAS_PYAUTOGUI:
                x = self.boundsInScreen.centerX()
                y = self.boundsInScreen.centerY()
                pyautogui.click(x, y)
                return True
        elif action == 1:  # FOCUS
            self.focused = True
            return True
        elif action == 64:  # ACCESSIBILITY_FOCUS
            self.focused = True
            return True
        elif action == 4096:  # SCROLL_FORWARD
            if HAS_PYAUTOGUI:
                pyautogui.scroll(-5)
            return True
        elif action == 8192:  # SCROLL_BACKWARD
            if HAS_PYAUTOGUI:
                pyautogui.scroll(5)
            return True
        elif action == 128:  # CLEAR_ACCESSIBILITY_FOCUS
            self.focused = False
            return True
        return False

    def recycle(self) -> None:
        pass


class AccessibilityPage:
    """模拟当前页面的无障碍信息"""

    CLICK = 16
    LONG_CLICK = 32
    FOCUS = 1
    SCROLL_FORWARD = 4096
    SCROLL_BACKWARD = 8192
    ACCESSIBILITY_FOCUS = 64
    CLEAR_ACCESSIBILITY_FOCUS = 128

    def __init__(self):
        self._root = AccessibilityNodeInfo()
        self._build_fake_tree()

    def _build_fake_tree(self):
        """构建模拟的 UI 树"""
        self._root.className = "android.widget.FrameLayout"
        self._root.packageName = _package_name
        self._root.resourceName = f"{_package_name}:id/content"
        self._root.boundsInScreen = Rect(0, 0, 1920, 1080)
        self._root.depth = 0

        # 状态栏
        status_bar = AccessibilityNodeInfo()
        status_bar.className = "android.widget.LinearLayout"
        status_bar.resourceName = f"{_package_name}:id/statusBar"
        status_bar.boundsInScreen = Rect(0, 0, 1920, 80)
        self._root.addChild(status_bar)

        # 主内容区域
        content = AccessibilityNodeInfo()
        content.className = "android.widget.ScrollView"
        content.resourceName = f"{_package_name}:id/contentArea"
        content.boundsInScreen = Rect(0, 80, 1920, 1000)
        content.contentDescription = "主内容区域"
        self._root.addChild(content)

        # 底部导航
        nav = AccessibilityNodeInfo()
        nav.className = "android.widget.LinearLayout"
        nav.resourceName = f"{_package_name}:id/navigation"
        nav.boundsInScreen = Rect(0, 1000, 1920, 1080)
        self._root.addChild(nav)

        btn_home = AccessibilityNodeInfo()
        btn_home.className = "android.widget.Button"
        btn_home.text = "首页"
        btn_home.clickable = True
        btn_home.boundsInScreen = Rect(0, 1000, 640, 1080)
        nav.addChild(btn_home)

        btn_search = AccessibilityNodeInfo()
        btn_search.className = "android.widget.Button"
        btn_search.text = "搜索"
        btn_search.clickable = True
        btn_search.boundsInScreen = Rect(640, 1000, 1280, 1080)
        nav.addChild(btn_search)

        btn_profile = AccessibilityNodeInfo()
        btn_profile.className = "android.widget.Button"
        btn_profile.text = "我的"
        btn_profile.clickable = True
        btn_profile.boundsInScreen = Rect(1280, 1000, 1920, 1080)
        nav.addChild(btn_profile)

    def getRoot(self) -> AccessibilityNodeInfo:
        return self._root

    def findByText(self, text: str) -> Optional[AccessibilityNodeInfo]:
        return self._root.findByText(text)

    def findById(self, id_: str) -> Optional[AccessibilityNodeInfo]:
        return self._root.findById(id_)

    def refresh(self) -> bool:
        self._build_fake_tree()
        return True

    def getSystemWindows(self) -> List:
        return [self._root]

    def getWindows(self) -> List:
        return [self._root]


# ============================================================
#  android.hardware services
# ============================================================

class SensorManager:
    """模拟 android.hardware.SensorManager"""
    TYPE_ACCELEROMETER = 1
    TYPE_GYROSCOPE = 4
    TYPE_LIGHT = 5
    TYPE_PRESSURE = 6
    TYPE_PROXIMITY = 8
    TYPE_MAGNETIC_FIELD = 2

    def getDefaultSensor(self, type_: int):
        return Sensor(type_)

    def getSensorList(self, type_: int) -> List:
        if type_ == -1:
            return [Sensor(t) for t in range(1, 13)]
        return [Sensor(type_)] if type_ >= 1 else []

    def registerListener(self, listener, sensor, rate: int = 3) -> bool:
        return True

    def unregisterListener(self, listener, sensor=None) -> None:
        pass


class Sensor:
    def __init__(self, type_: int):
        self.type = type_
        self.name = {
            1: "Accelerometer", 4: "Gyroscope", 5: "Light",
            6: "Pressure", 8: "Proximity", 2: "Magnetic Field"
        }.get(type_, f"Sensor_{type_}")
        self.vendor = "OperitCompat"
        self.version = 1
        self.resolution = 0.01
        self.maximumRange = 100.0
        self.minDelay = 10000
        self.power = 0.1


class SensorEvent:
    def __init__(self, sensor: Sensor, values: List[float]):
        self.sensor = sensor
        self.values = values
        self.timestamp = int(time.time() * 1000000)
        self.accuracy = 3


class CameraManager:
    """模拟 android.hardware.camera2.CameraManager"""
    def getCameraIdList(self) -> List[str]:
        return ["0"]

    def getCameraCharacteristics(self, cameraId: str) -> "CameraCharacteristics":
        return CameraCharacteristics()

    def openCamera(self, cameraId: str, stateCallback, handler) -> None:
        pass


class CameraCharacteristics:
    def get(self, key: Any) -> Any:
        return None


# ============================================================
#  android.location
# ============================================================

class LocationManager:
    """模拟 android.location.LocationManager"""
    GPS_PROVIDER = "gps"
    NETWORK_PROVIDER = "network"
    PASSIVE_PROVIDER = "passive"

    def getLastKnownLocation(self, provider: str) -> Optional["Location"]:
        return self._get_fake_location()

    def getCurrentLocation(self, provider: str, result: Any = None, executor: Any = None) -> Optional["Location"]:
        return self._get_fake_location()

    def requestLocationUpdates(self, provider: str, minTimeMs: int,
                                minDistanceM: float, listener: Any) -> None:
        pass

    def removeUpdates(self, listener: Any) -> None:
        pass

    def isProviderEnabled(self, provider: str) -> bool:
        return True

    def getAllProviders(self) -> List[str]:
        return [self.GPS_PROVIDER, self.NETWORK_PROVIDER, self.PASSIVE_PROVIDER]

    def _get_fake_location(self) -> "Location":
        loc = Location("gps")
        loc._latitude = 39.9042 + random.random() * 0.01
        loc._longitude = 116.4074 + random.random() * 0.01
        loc._altitude = 43.0
        loc._accuracy = 10.0
        loc._time = int(time.time())
        loc._speed = 0.0
        loc._bearing = 0.0
        return loc


class Location:
    def __init__(self, provider: str = "gps"):
        self._provider = provider
        self._latitude = 0.0
        self._longitude = 0.0
        self._altitude = 0.0
        self._accuracy = 0.0
        self._time = 0
        self._speed = 0.0
        self._bearing = 0.0

    def getLatitude(self) -> float: return self._latitude
    def getLongitude(self) -> float: return self._longitude
    def getAltitude(self) -> float: return self._altitude
    def getAccuracy(self) -> float: return self._accuracy
    def getTime(self) -> int: return self._time
    def getSpeed(self) -> float: return self._speed
    def getBearing(self) -> float: return self._bearing
    def getProvider(self) -> str: return self._provider
    def distanceTo(self, dest: "Location") -> float:
        """Haversine 公式计算距离"""
        lat1, lon1 = math.radians(self._latitude), math.radians(self._longitude)
        lat2, lon2 = math.radians(dest._latitude), math.radians(dest._longitude)
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return 2 * 6371000 * math.asin(math.sqrt(a))


class Geocoder:
    """模拟 android.location.Geocoder"""
    @staticmethod
    def getFromLocation(latitude: float, longitude: float, maxResults: int) -> List["Address"]:
        return [Address(latitude, longitude)]

    @staticmethod
    def getFromLocationName(locationName: str, maxResults: int) -> List["Address"]:
        return [Address(39.9042, 116.4074)]


class Address:
    def __init__(self, lat: float, lng: float):
        self.featureName = ""
        self.thoroughfare = ""
        self.locality = "Beijing"
        self.adminArea = "Beijing"
        self.countryName = "China"
        self.countryCode = "CN"
        self.postalCode = "100000"
        self.subAdminArea = ""
        self.subLocality = ""
        self.latitude = lat
        self.longitude = lng

    def getMaxAddressLineIndex(self) -> int:
        return 1

    def getAddressLine(self, index: int) -> str:
        return f"{self.locality}, {self.adminArea}, {self.countryName}"

    def getLocality(self) -> str: return self.locality
    def getAdminArea(self) -> str: return self.adminArea
    def getCountryName(self) -> str: return self.countryName


# ============================================================
#  android.media
# ============================================================

class MediaPlayer:
    """模拟 android.media.MediaPlayer"""
    def __init__(self):
        self._source = None
        self._volume = 1.0
        self._looping = False

    def setDataSource(self, path_or_uri) -> None: self._source = path_or_uri
    def setVolume(self, left: float, right: float) -> None: self._volume = (left + right) / 2
    def setLooping(self, looping: bool) -> None: self._looping = looping
    def prepare(self) -> None: pass
    def prepareAsync(self) -> None: pass
    def start(self) -> None:
        console.log(f"[MediaPlayer] 模拟播放: {self._source}")
    def stop(self) -> None: pass
    def pause(self) -> None: pass
    def release(self) -> None: pass
    def isPlaying(self) -> bool: return False
    def getDuration(self) -> int: return 0
    def getCurrentPosition(self) -> int: return 0
    def seekTo(self, msec: int) -> None: pass
    def reset(self) -> None: pass

    @staticmethod
    def create(context: Context, uri: Any) -> "MediaPlayer":
        return MediaPlayer()


class AudioRecord:
    """模拟 android.media.AudioRecord"""
    def __init__(self, audioSource, sampleRate, channelConfig, audioFormat, bufferSize):
        pass
    def startRecording(self) -> None: pass
    def stop(self) -> None: pass
    def read(self, audioData, offsetInBytes, sizeInBytes) -> int:
        return sizeInBytes
    def release(self) -> None: pass
    def getRecordingState(self) -> int: return 3  # RECORDSTATE_RECORDING
    def getState(self) -> int: return 1  # STATE_INITIALIZED


class AudioManager:
    """模拟 android.media.AudioManager"""
    RINGER_MODE_NORMAL = 2
    RINGER_MODE_SILENT = 0
    RINGER_MODE_VIBRATE = 1
    STREAM_MUSIC = 3
    STREAM_RING = 2
    STREAM_ALARM = 4
    STREAM_NOTIFICATION = 5

    def getStreamVolume(self, streamType: int) -> int:
        return 7
    def setStreamVolume(self, streamType: int, volume: int, flags: int) -> None: pass
    def getRingerMode(self) -> int: return self.RINGER_MODE_NORMAL
    def setRingerMode(self, mode: int) -> None: pass
    def adjustVolume(self, direction: int, flags: int) -> None: pass
    def isMusicActive(self) -> bool: return False


# ============================================================
#  android.telephony
# ============================================================

class TelephonyManager:
    """模拟 android.telephony.TelephonyManager"""
    def getDeviceId(self) -> str: return "000000000000000"
    def getImei(self) -> str: return "000000000000000"
    def getSimSerialNumber(self) -> str: return "000000000000000"
    def getNetworkOperatorName(self) -> str: return "Network"
    def getNetworkCountryIso(self) -> str: return "CN"
    def getPhoneType(self) -> int: return 0  # PHONE_TYPE_NONE
    def getDataState(self) -> int: return 2  # DATA_CONNECTED
    def getCallState(self) -> int: return 0  # CALL_STATE_IDLE
    def getSimState(self) -> int: return 5  # SIM_STATE_READY
    def hasIccCard(self) -> bool: return False
    def isNetworkRoaming(self) -> bool: return False
    def getNetworkType(self) -> int: return 13  # NETWORK_TYPE_LTE
    def getSignalStrength(self) -> int: return 4
    def listen(self, listener, events: int) -> None: pass


# ============================================================
#  android.provider 合约
# ============================================================

class Settings:
    """模拟 android.provider.Settings"""

    class System:
        @staticmethod
        def getString(cr: ContentResolver, name: str) -> str:
            return ""
        @staticmethod
        def putString(cr: ContentResolver, name: str, value: str) -> bool:
            return True
        @staticmethod
        def getInt(cr: ContentResolver, name: str, default: int = 0) -> int:
            return default

    class Secure:
        ANDROID_ID = "android_id"
        @staticmethod
        def getString(cr: ContentResolver, name: str) -> str:
            return hashlib.md5(b"operit_compat").hexdigest()[:16]

    class Global:
        @staticmethod
        def getString(cr: ContentResolver, name: str) -> str:
            return ""
        @staticmethod
        def putString(cr: ContentResolver, name: str, value: str) -> bool:
            return True


class MediaStore:
    """模拟 android.provider.MediaStore"""

    class Images:
        class Media:
            EXTERNAL_CONTENT_URI = Uri.parse("content://media/external/images/media")
            INTERNAL_CONTENT_URI = Uri.parse("content://media/internal/images/media")
            DATA = "_data"
            DISPLAY_NAME = "_display_name"
            SIZE = "_size"
            MIME_TYPE = "mime_type"
            TITLE = "title"
            DATE_ADDED = "date_added"
            DATE_MODIFIED = "date_modified"
            WIDTH = "width"
            HEIGHT = "height"
            ORIENTATION = "orientation"
            BUCKET_DISPLAY_NAME = "bucket_display_name"
            BUCKET_ID = "bucket_id"

    class Video:
        class Media:
            EXTERNAL_CONTENT_URI = Uri.parse("content://media/external/video/media")
            DATA = "_data"
            DISPLAY_NAME = "_display_name"
            SIZE = "_size"
            TITLE = "title"
            DURATION = "duration"
            DATE_ADDED = "date_added"

    class Audio:
        class Media:
            EXTERNAL_CONTENT_URI = Uri.parse("content://media/external/audio/media")
            DATA = "_data"
            TITLE = "title"
            ARTIST = "artist"
            ALBUM = "album"
            DURATION = "duration"

    class Files:
        class Media:
            EXTERNAL_CONTENT_URI = Uri.parse("content://media/external/files/media")


class CalendarContract:
    """模拟 android.provider.CalendarContract"""

    class Events:
        CONTENT_URI = Uri.parse("content://com.android.calendar/events")
        TITLE = "title"
        DESCRIPTION = "description"
        DTSTART = "dtstart"
        DTEND = "dtend"
        ALL_DAY = "allDay"
        EVENT_TIMEZONE = "eventTimezone"
        CALENDAR_ID = "calendar_id"
        RRULE = "rrule"
        DURATION = "duration"


class ContactsContract:
    """模拟 android.provider.ContactsContract"""

    class Contacts:
        CONTENT_URI = Uri.parse("content://com.android.contacts/contacts")
        DISPLAY_NAME = "display_name"
        HAS_PHONE_NUMBER = "has_phone_number"
        _ID = "_id"

    class CommonDataKinds:
        class Phone:
            CONTENT_URI = Uri.parse("content://com.android.contacts/data/phones")
            NUMBER = "data1"
            TYPE = "data2"
            LABEL = "data3"
            TYPE_HOME = 1
            TYPE_MOBILE = 2
            TYPE_WORK = 3

        class Email:
            CONTENT_URI = Uri.parse("content://com.android.contacts/data/emails")
            ADDRESS = "data1"
            TYPE = "data2"
            TYPE_HOME = 1
            TYPE_WORK = 2


# ============================================================
#  android.os.BatteryManager
# ============================================================

class BatteryManager:
    """模拟 android.os.BatteryManager"""
    BATTERY_PROPERTY_CAPACITY = 0
    BATTERY_PROPERTY_STATUS = 1
    STATUS_CHARGING = 2
    STATUS_DISCHARGING = 3
    STATUS_FULL = 5
    STATUS_NOT_CHARGING = 4

    def getIntProperty(self, id_: int) -> int:
        if id_ == self.BATTERY_PROPERTY_CAPACITY:
            return 85
        return self.STATUS_DISCHARGING

    def getLongProperty(self, id_: int) -> int:
        return 0


# ============================================================
#  android.net services
# ============================================================

class ConnectivityManager:
    """模拟 android.net.ConnectivityManager"""
    TYPE_WIFI = 1
    TYPE_MOBILE = 0
    TYPE_ETHERNET = 9
    TYPE_BLUETOOTH = 7

    def getActiveNetworkInfo(self) -> Optional["NetworkInfo"]:
        return NetworkInfo()

    def getAllNetworkInfo(self) -> List["NetworkInfo"]:
        return [NetworkInfo()]

    def isActiveNetworkMetered(self) -> bool:
        return False

    def getNetworkCapabilities(self, network) -> Optional["NetworkCapabilities"]:
        return NetworkCapabilities()


class NetworkInfo:
    def __init__(self):
        self._type = ConnectivityManager.TYPE_ETHERNET
        self._subtype = 0
        self._isConnected = True
        self._isAvailable = True
        self._typeName = "ETHERNET"
        self._subtypeName = ""
        self._state = "CONNECTED"
        self._reason = ""

    def getType(self) -> int: return self._type
    def getSubtype(self) -> int: return self._subtype
    def isConnected(self) -> bool: return self._isConnected
    def isConnectedOrConnecting(self) -> bool: return True
    def isAvailable(self) -> bool: return self._isAvailable
    def getTypeName(self) -> str: return self._typeName
    def getState(self) -> str: return self._state
    def getExtraInfo(self) -> str: return ""


class NetworkCapabilities:
    def hasCapability(self, cap: int) -> bool:
        return True
    def hasTransport(self, transport: int) -> bool:
        return True


class WifiManager:
    """模拟 android.net.wifi.WifiManager"""
    def getConnectionInfo(self) -> "WifiInfo":
        return WifiInfo()

    def startScan(self) -> bool:
        return True

    def getScanResults(self) -> List:
        return []

    def isWifiEnabled(self) -> bool:
        return True

    def setWifiEnabled(self, enabled: bool) -> bool:
        return True

    def isWifiEnabled(self) -> bool:
        return True


class WifiInfo:
    def __init__(self):
        self._ssid = "OperitCompat_Network"
        self._bssid = "00:00:00:00:00:00"
        self._rssi = -50
        self._linkSpeed = 300
        self._ipAddress = int.from_bytes(socket.inet_aton("192.168.1.100"), "big")
        self._networkId = 1

    def getSSID(self) -> str: return self._ssid
    def getBSSID(self) -> str: return self._bssid
    def getRssi(self) -> int: return self._rssi
    def getLinkSpeed(self) -> int: return self._linkSpeed
    def getIpAddress(self) -> int: return self._ipAddress
    def getNetworkId(self) -> int: return self._networkId
    def getSupplicantState(self) -> str: return "COMPLETED"

    def getMacAddress(self) -> str:
        import uuid
        return ":".join(f"{(uuid.getnode() >> (8 * i)) & 0xFF:02X}" for i in range(6))


# ============================================================
#  android.os.storage
# ============================================================

class StorageManager:
    """模拟 android.os.storage.StorageManager"""
    def getStorageVolumes(self) -> List:
        volumes = []
        vol = StorageVolume("Internal shared storage", _sdcard_root, True, False)
        volumes.append(vol)
        return volumes

    def getPrimaryStorageVolume(self) -> "StorageVolume":
        return StorageVolume("Internal shared storage", _sdcard_root, True, False)

    def getVolumeList(self) -> List:
        return self.getStorageVolumes()


class StorageVolume:
    def __init__(self, desc: str, path: str, primary: bool, removable: bool):
        self._description = desc
        self._path = path
        self._primary = primary
        self._removable = removable
        self._state = "mounted"
        self._uuid = hashlib.md5(path.encode()).hexdigest()
        self._maxFileSize = 4 * 1024 * 1024 * 1024 * 1024  # 4TB

    def getDescription(self, context: Context = None) -> str: return self._description
    def getPath(self) -> str: return self._path
    def isPrimary(self) -> bool: return self._primary
    def isRemovable(self) -> bool: return self._removable
    def getState(self) -> str: return self._state
    def getUuid(self) -> str: return self._uuid
    def getMaxFileSize(self) -> int: return self._maxFileSize
    def getUserLabel(self) -> str: return os.path.basename(self._path)


# ============================================================
#  android.view services
# ============================================================

class WindowManager:
    """模拟 android.view.WindowManager"""
    def getDefaultDisplay(self) -> "Display":
        return self._get_display()

    def _get_display(self) -> "Display":
        w, h = 1920, 1080
        if HAS_SCREENINFO:
            try:
                monitor = screeninfo.get_monitors()[0]
                w, h = monitor.width, monitor.height
            except Exception:
                pass
        return Display(w, h)

    def getCurrentWindowMetrics(self) -> "WindowMetrics":
        display = self._get_display()
        return WindowMetrics(Rect(0, 0, display._width, display._height))


class Display:
    def __init__(self, w: int = 1920, h: int = 1080):
        self._width = w
        self._height = h
        self._refreshRate = 60.0
        self._density = 2.0
        self._densityDpi = 320
        self._rotation = 0

    def getWidth(self) -> int: return self._width
    def getHeight(self) -> int: return self._height
    def getRefreshRate(self) -> float: return self._refreshRate
    def getRotation(self) -> int: return self._rotation
    def getRealSize(self, size: "Point") -> None:
        size.x, size.y = self._width, self._height
    def getSize(self, size: "Point") -> None:
        size.x, size.y = self._width, self._height

    class Metrics:
        def __init__(self):
            self.widthPixels = 1080
            self.heightPixels = 1920
            self.density = 2.0
            self.densityDpi = 320
            self.scaledDensity = 2.0
            self.xdpi = 320.0
            self.ydpi = 320.0

    def getMetrics(self, metrics: Metrics) -> None:
        metrics.widthPixels = self._width
        metrics.heightPixels = self._height
        metrics.density = self._density
        metrics.densityDpi = self._densityDpi


class WindowMetrics:
    def __init__(self, bounds: Rect):
        self._bounds = bounds

    def getBounds(self) -> Rect:
        return self._bounds


class Point:
    def __init__(self, x: int = 0, y: int = 0):
        self.x = x
        self.y = y

    def set(self, x: int, y: int) -> None:
        self.x = x
        self.y = y


class DisplayManager:
    def getDisplay(self, displayId: int) -> Optional[Display]:
        return Display()

    def getDisplays(self) -> List[Display]:
        return [Display()]

    def getDisplayByName(self, name: str) -> Optional[Display]:
        return Display()


class InputManager:
    """模拟 android.hardware.input.InputManager"""
    def injectInputEvent(self, event: Any, mode: int) -> bool:
        return True


class LayoutInflater:
    def inflate(self, resource, root: View) -> View:
        return View()


class ClipboardManager:
    """模拟 android.content.ClipboardManager"""

    def __init__(self):
        self._text = ""

    def setText(self, text: str) -> None:
        self._text = text
        import pyperclip as _pc
        _pc.copy(text)

    def getText(self) -> str:
        try:
            import pyperclip as _pc
            return _pc.paste()
        except Exception:
            return self._text

    def hasText(self) -> bool:
        return bool(self.getText())


class DownloadManager:
    """模拟 android.app.DownloadManager"""
    def enqueue(self, request: "DownloadManager.Request") -> int:
        return int(time.time())

    def query(self, query: "DownloadManager.Query") -> Cursor:
        return Cursor()

    class Request:
        def __init__(self, uri: Uri):
            self._uri = uri
            self._title = ""
            self._description = ""
            self._destination = ""
            self._allowedOverMetered = False
            self._allowedOverRoaming = False

        def setTitle(self, title: str) -> None: self._title = title
        def setDescription(self, desc: str) -> None: self._description = desc
        def setDestinationInExternalFilesDir(self, context: Context, dirType: str, subPath: str) -> None:
            self._destination = os.path.join(context.getExternalFilesDir(dirType), subPath)
        def setAllowedOverMetered(self, allow: bool) -> None: self._allowedOverMetered = allow
        def setAllowedOverRoaming(self, allow: bool) -> None: self._allowedOverRoaming = allow

    class Query:
        def setFilterById(self, *ids: int) -> None: pass


class Toast:
    """模拟 android.widget.Toast"""
    LENGTH_SHORT = 0
    LENGTH_LONG = 1

    @staticmethod
    def makeText(context: Context, text: str, duration: int) -> "Toast":
        return Toast(text)

    def __init__(self, text: str):
        self._text = text

    def show(self) -> None:
        console.log(f"[Toast] {self._text}")


# ============================================================
#  android.print
# ============================================================

class PrintManager:
    def print(self, jobName: str, documentAdapter: Any, attributes: Any = None) -> bool:
        return True


# ============================================================
#  android.accounts
# ============================================================

class AccountManager:
    """模拟 android.accounts.AccountManager"""
    def getAccounts(self) -> List:
        return [Account("user@operit.com", "com.google")]

    def getAccountsByType(self, type_: str) -> List:
        return [Account("user@operit.com", type_)]

    def addAccount(self, accountType: str, authTokenType: str, requiredFeatures: List,
                   addAccountAuthTokenType: str, options: Dict, activity: Any,
                   callback: Callable, handler: Any) -> "AccountManagerFuture":
        return AccountManagerFuture()


class Account:
    def __init__(self, name: str, type_: str):
        self.name = name
        self.type = type_

    def toString(self) -> str:
        return f"Account{{name={self.name}, type={self.type}}}"


class AccountManagerFuture:
    def getResult(self) -> Any:
        return None


# ============================================================
#  android.hardware.biometrics
# ============================================================

class BiometricPrompt:
    """模拟 android.hardware.biometrics.BiometricPrompt"""
    BIOMETRIC_STRONG = 15
    BIOMETRIC_WEAK = 255

    def authenticate(self, crypto: Any = None, cancel: Any = None) -> None:
        console.log("[BiometricPrompt] 模拟生物识别认证")
        if self._callback:
            self._callback.onAuthenticationSucceeded(
                BiometricPrompt.AuthenticationResult()
            )

    def setCallback(self, callback: "AuthenticationCallback") -> None:
        self._callback = callback

    class AuthenticationResult:
        def getAuthenticationType(self) -> int:
            return BiometricPrompt.BIOMETRIC_STRONG

    class AuthenticationCallback:
        def onAuthenticationError(self, errorCode: int, errString: str) -> None: pass
        def onAuthenticationSucceeded(self, result: "AuthenticationResult") -> None: pass
        def onAuthenticationFailed(self) -> None: pass


# ============================================================
#  DisplayMetrics 辅助类
# ============================================================

class DisplayMetrics:
    """辅助类"""
    def __init__(self):
        self.widthPixels = 1080
        self.heightPixels = 1920
        self.density = 2.0
        self.densityDpi = 320
        self.scaledDensity = 2.0
        self.xdpi = 320.0
        self.ydpi = 320.0


# ============================================================
#  java.io 兼容
# ============================================================

class File:
    """跨平台文件操作"""
    separator = os.sep

    def __init__(self, *args):
        self._path = ""
        if len(args) == 1:
            self._path = self._normalize(args[0])
        elif len(args) >= 2:
            self._path = self._normalize(os.path.join(args[0], *args[1:]))

    @staticmethod
    def _normalize(p: str) -> str:
        if p.startswith("/sdcard"):
            return os.path.join(_sdcard_root, p[7:].lstrip("/"))
        return p

    def getAbsolutePath(self) -> str:
        return os.path.abspath(self._path)

    def getName(self) -> str:
        return os.path.basename(self._path)

    def getParent(self) -> str:
        return os.path.dirname(self._path)

    def exists(self) -> bool:
        return os.path.exists(self._path)

    def isFile(self) -> bool:
        return os.path.isfile(self._path)

    def isDirectory(self) -> bool:
        return os.path.isdir(self._path)

    def length(self) -> int:
        return os.path.getsize(self._path) if os.path.isfile(self._path) else 0

    def list(self) -> List[str]:
        return os.listdir(self._path) if os.path.isdir(self._path) else []

    def listFiles(self) -> List["File"]:
        return [File(p) for p in (os.listdir(self._path) if os.path.isdir(self._path) else [])]

    def mkdir(self) -> bool:
        try:
            os.mkdir(self._path)
            return True
        except Exception:
            return False

    def mkdirs(self) -> bool:
        try:
            os.makedirs(self._path, exist_ok=True)
            return True
        except Exception:
            return False

    def delete(self) -> bool:
        try:
            if os.path.isfile(self._path):
                os.remove(self._path)
            elif os.path.isdir(self._path):
                os.rmdir(self._path)
            return True
        except Exception:
            return False

    def renameTo(self, dest: "File") -> bool:
        try:
            os.rename(self._path, dest._path)
            return True
        except Exception:
            return False

    def lastModified(self) -> int:
        return int(os.path.getmtime(self._path) * 1000) if os.path.exists(self._path) else 0

    def canRead(self) -> bool:
        return os.access(self._path, os.R_OK)

    def canWrite(self) -> bool:
        return os.access(self._path, os.W_OK)

    def canExecute(self) -> bool:
        return os.access(self._path, os.X_OK)

    def getFreeSpace(self) -> int:
        stat = os.statvfs(self._path) if hasattr(os, "statvfs") else None
        if stat:
            return stat.f_bavail * stat.f_frsize
        return 1024 * 1024 * 1024 * 50  # 50GB

    def getTotalSpace(self) -> int:
        return 1024 * 1024 * 1024 * 256  # 256GB

    def toPath(self) -> str:
        return self._path

    def toURI(self) -> str:
        return Uri.fromFile(self._path).toString()

    def __str__(self):
        return self._path

    @staticmethod
    def createTempFile(prefix: str, suffix: str) -> "File":
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
        os.close(fd)
        return File(path)


class FileInputStream:
    def __init__(self, file_or_path):
        if isinstance(file_or_path, File):
            self._path = file_or_path._path
        else:
            self._path = str(file_or_path)
        self._file = open(self._path, "rb")

    def read(self, length: int = -1) -> bytes:
        return self._file.read(length) if length >= 0 else self._file.read()

    def available(self) -> int:
        import stat
        return os.stat(self._path).st_size - self._file.tell()

    def close(self) -> None:
        self._file.close()


class FileOutputStream:
    def __init__(self, file_or_path, append: bool = False):
        if isinstance(file_or_path, File):
            self._path = file_or_path._path
        else:
            self._path = str(file_or_path)
        self._file = open(self._path, "ab" if append else "wb")

    def write(self, data) -> None:
        if isinstance(data, bytes):
            self._file.write(data)
        elif isinstance(data, str):
            self._file.write(data.encode("utf-8"))
        else:
            self._file.write(bytes([data]))

    def flush(self) -> None:
        self._file.flush()

    def close(self) -> None:
        self._file.close()


class BufferedReader:
    def __init__(self, reader, buffer_size: int = 8192):
        self._reader = reader
        self._buffer = ""

    def readLine(self) -> Optional[str]:
        lines = self._reader.read().split("\n")
        if lines:
            return lines[0]
        return None

    def read(self) -> str:
        return self._reader.read()

    def close(self) -> None:
        self._reader.close()


class InputStreamReader:
    def __init__(self, stream, charset: str = "UTF-8"):
        self._stream = stream
        self._charset = charset

    def read(self, length: int = -1) -> str:
        data = self._stream.read(length)
        return data.decode(self._charset) if isinstance(data, bytes) else data

    def close(self) -> None:
        self._stream.close()


class OutputStreamWriter:
    def __init__(self, stream, charset: str = "UTF-8"):
        self._stream = stream
        self._charset = charset

    def write(self, text: str) -> None:
        self._stream.write(text.encode(self._charset))

    def flush(self) -> None:
        self._stream.flush()

    def close(self) -> None:
        self._stream.close()


class BufferedWriter:
    def __init__(self, writer, buffer_size: int = 8192):
        self._writer = writer
        self._buffer = ""

    def write(self, text: str) -> None:
        self._writer.write(text)

    def newLine(self) -> None:
        self._writer.write("\n")

    def flush(self) -> None:
        self._writer.flush()

    def close(self) -> None:
        self._writer.close()


# ============================================================
#  通用辅助工具
# ============================================================

class Log:
    """android.util.Log"""
    ASSERT = 7
    DEBUG = 3
    ERROR = 6
    INFO = 4
    VERBOSE = 2
    WARN = 5

    @staticmethod
    def d(tag: str, msg: str) -> int:
        print(f"DEBUG/{tag}: {msg}")
        return 0

    @staticmethod
    def e(tag: str, msg: str) -> int:
        print(f"ERROR/{tag}: {msg}", file=sys.stderr)
        return 0

    @staticmethod
    def i(tag: str, msg: str) -> int:
        print(f"INFO/{tag}: {msg}")
        return 0

    @staticmethod
    def w(tag: str, msg: str) -> int:
        print(f"WARN/{tag}: {msg}")
        return 0

    @staticmethod
    def v(tag: str, msg: str) -> int:
        print(f"VERBOSE/{tag}: {msg}")
        return 0

    @staticmethod
    def wtf(tag: str, msg: str) -> int:
        print(f"WTF/{tag}: {msg}", file=sys.stderr)
        return 0


class Bundle:
    """android.os.Bundle"""
    def __init__(self):
        self._data: Dict[str, Any] = {}

    def getString(self, key: str, default: str = None) -> Optional[str]:
        return str(self._data.get(key, default)) if default or key in self._data else self._data.get(key)

    def getInt(self, key: str, default: int = 0) -> int:
        return int(self._data.get(key, default))

    def getBoolean(self, key: str, default: bool = False) -> bool:
        return bool(self._data.get(key, default))

    def putString(self, key: str, value: str) -> None:
        self._data[key] = value

    def putInt(self, key: str, value: int) -> None:
        self._data[key] = value

    def putBoolean(self, key: str, value: bool) -> None:
        self._data[key] = value

    def containsKey(self, key: str) -> bool:
        return key in self._data

    def isEmpty(self) -> bool:
        return len(self._data) == 0

    def size(self) -> int:
        return len(self._data)

    def keySet(self) -> set:
        return set(self._data.keys())


class Handler:
    """android.os.Handler"""
    def __init__(self, callback: Callable = None):
        self._callback = callback

    def post(self, action: Callable) -> bool:
        action()
        return True

    def postDelayed(self, action: Callable, delayMs: int) -> bool:
        import threading
        timer = threading.Timer(delayMs / 1000, action)
        timer.start()
        return True

    def removeCallbacks(self, action: Callable = None) -> None:
        pass

    def obtainMessage(self, what: int = 0, arg1: int = 0, arg2: int = 0, obj: Any = None) -> "Message":
        return Message(what, arg1, arg2, obj)


class Message:
    def __init__(self, what: int = 0, arg1: int = 0, arg2: int = 0, obj: Any = None):
        self.what = what
        self.arg1 = arg1
        self.arg2 = arg2
        self.obj = obj

    def sendToTarget(self) -> None:
        pass


class Looper:
    """android.os.Looper"""
    @staticmethod
    def getMainLooper() -> "Looper":
        return Looper()

    @staticmethod
    def myLooper() -> Optional["Looper"]:
        return Looper()

    @staticmethod
    def prepare() -> None:
        pass

    @staticmethod
    def loop() -> None:
        pass

    def quit(self) -> None:
        pass


class ParcelFileDescriptor:
    """android.os.ParcelFileDescriptor"""
    MODE_READ_ONLY = 0x10000000
    MODE_WRITE_ONLY = 0x20000000
    MODE_READ_WRITE = 0x30000000

    @staticmethod
    def open(file: File, mode: int) -> "ParcelFileDescriptor":
        return ParcelFileDescriptor(file)

    def __init__(self, file: File = None):
        self._file = file

    def getFileDescriptor(self) -> Any:
        return None

    def close(self) -> None:
        pass

    @staticmethod
    def parseUri(uri: Uri, mode: int) -> "ParcelFileDescriptor":
        return ParcelFileDescriptor()


# ============================================================
#  AndroidUtil - 常用工具函数桥接
# ============================================================

class AndroidUtil:
    """将 Android 路径映射到桌面路径的工具类"""

    @staticmethod
    def resolve_path(path: str) -> str:
        """解析 Android 路径到桌面路径"""
        if path.startswith("/sdcard"):
            return os.path.join(_sdcard_root, path[7:].lstrip("/"))
        if path.startswith("content://"):
            uri = Uri.parse(path)
            return uri.getPath()
        if path.startswith("file://"):
            return urllib.parse.unquote(path[7:])
        return path

    @staticmethod
    def to_android_path(desktop_path: str) -> str:
        """将桌面路径映射回 Android 路径"""
        if desktop_path.startswith(_sdcard_root):
            return desktop_path.replace(_sdcard_root, "/sdcard")
        return desktop_path

    @staticmethod
    def get_app_draw_dir(name: str) -> str:
        """获取应用绘图输出目录（桌面版）"""
        path = os.path.join(_sdcard_root, "Download", "Operit", "plugins", "draw", name, "draws")
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def save_image_to_draw_dir(script_name: str, data: bytes, ext: str = "png") -> str:
        """保存图片到绘图目录"""
        dir_path = AndroidUtil.get_app_draw_dir(script_name)
        filename = f"{int(time.time() * 1000)}_{random.randint(1000,9999)}.{ext}"
        filepath = os.path.join(dir_path, filename)
        with open(filepath, "wb") as f:
            f.write(data)
        return filepath


# ═══════════════════════════════════════════════════════════════
#  GLOBAL INSTANCE - 单例上下文
# ═══════════════════════════════════════════════════════════════

# 全局应用上下文
application_context = Context(_package_name)

# 全局 Java.type 桥接（只在 jpype 可用时有效）
_jpype_available = False
try:
    import jpype
    import jpype.imports
    _jpype_available = True
except ImportError:
    pass


def java_type(class_name: str) -> Any:
    """
    模拟 Java.type() 调用。
    如果安装了 jpype，则尝试真实加载 Java 类；
    否则返回 AndroidUnsupportedStub。
    """
    if _jpype_available and jpype.isJVMStarted():
        try:
            return jpype.JClass(class_name)
        except Exception:
            pass
    return AndroidUnsupportedStub


class AndroidUnsupportedStub:
    """
    通用 Android 不支持存根。
    替换所有无法在桌面端实现的 Java 类。
    任何方法调用都返回自身，支持链式调用。
    """
    def __init__(self, *args, **kwargs):
        self._name = self.__class__.__name__

    def __getattr__(self, name: str) -> "AndroidUnsupportedStub":
        if name.startswith("_"):
            raise AttributeError(name)
        return AndroidUnsupportedStub()

    def __call__(self, *args, **kwargs) -> "AndroidUnsupportedStub":
        return self

    def __repr__(self) -> str:
        return f"<AndroidUnsupportedStub: {self._name}>"

    def __str__(self) -> str:
        return f"[Android-only]"

    # 模拟常见返回类型
    def toString(self) -> str:
        return f"[Android-only: {self._name}]"

    def intValue(self) -> int:
        return 0

    def longValue(self) -> int:
        return 0

    def booleanValue(self) -> bool:
        return False

    def doubleValue(self) -> float:
        return 0.0

    def get(self, *args) -> "AndroidUnsupportedStub":
        return self

    def length(self) -> int:
        return 0

    def size(self) -> int:
        return 0

    def isEmpty(self) -> bool:
        return True

    def close(self) -> None:
        pass

    def release(self) -> None:
        pass

    def recycle(self) -> None:
        pass


# 全局别名 - 让脚本中的 `Java.type("xxx")` 可以直接调用
Java = type("Java", (), {"type": staticmethod(java_type)})


# ═══════════════════════════════════════════════════════════════
#  导出给 operit_runtime.py 的重要对象
# ═══════════════════════════════════════════════════════════════

def get_android_compat_globals() -> dict:
    """返回要注入到脚本命名空间的 Android 兼容对象"""
    return {
        # android 核心包
        "Context": Context,
        "Intent": Intent,
        "IntentAction": IntentAction,
        "BroadcastReceiver": BroadcastReceiver,
        "IntentFilter": IntentFilter,
        "ContentValues": ContentValues,
        "ContentResolver": ContentResolver,
        "Cursor": Cursor,
        "Uri": Uri,
        "Uri_parse": Uri.parse,
        "Uri_fromFile": Uri.fromFile,

        # android.os
        "Build": Build,
        "Environment": Environment,
        "BatteryManager": BatteryManager,
        "PowerManager": PowerManager,
        "WakeLock": WakeLock,
        "VibrationEffect": VibrationEffect,
        "Vibrator": Vibrator,
        "Bundle": Bundle,
        "Handler": Handler,
        "Message": Message,
        "Looper": Looper,
        "ParcelFileDescriptor": ParcelFileDescriptor,

        # android.graphics
        "Bitmap": Bitmap,
        "BitmapFactory": BitmapFactory,
        "Bitmap_Config": Bitmap.Config,
        "Canvas": Canvas,
        "Color": Color,
        "Paint": Paint,
        "Rect": Rect,
        "Matrix": Matrix,
        "Typeface": Typeface,

        # android.graphics.pdf
        "PdfRenderer": PdfRenderer,

        # android.app
        "ActivityManager": ActivityManager,
        "NotificationManager": NotificationManager,
        "NotificationChannel": NotificationChannel,
        "AlarmManager": AlarmManager,
        "DownloadManager": DownloadManager,

        # android.view
        "View": View,
        "TextView": TextView,
        "EditText": EditText,
        "Button": Button,
        "ImageView": ImageView,
        "ScrollView": ScrollView,
        "RecyclerView": RecyclerView,
        "ViewGroup": ViewGroup,
        "LinearLayout": LinearLayout,
        "FrameLayout": FrameLayout,
        "RelativeLayout": RelativeLayout,
        "WindowManager": WindowManager,
        "Display": Display,
        "DisplayMetrics": DisplayMetrics,
        "Point": Point,
        "InputManager": InputManager,
        "LayoutInflater": LayoutInflater,
        "ClipboardManager": ClipboardManager,
        "WindowMetrics": WindowMetrics,

        # android.content.pm
        "PackageManager": PackageManager,
        "PackageInfo": PackageInfo,
        "ResolveInfo": ResolveInfo,
        "ActivityInfo": ActivityInfo,
        "ApplicationInfo": ApplicationInfo,
        "SharedPreferences": SharedPreferences,

        # android.provider
        "Settings": Settings,
        "MediaStore": MediaStore,
        "CalendarContract": CalendarContract,
        "ContactsContract": ContactsContract,

        # android.location
        "LocationManager": LocationManager,
        "Location": Location,
        "Geocoder": Geocoder,

        # android.media
        "MediaPlayer": MediaPlayer,
        "AudioRecord": AudioRecord,
        "AudioManager": AudioManager,

        # android.hardware
        "SensorManager": SensorManager,
        "Sensor": Sensor,
        "SensorEvent": SensorEvent,
        "CameraManager": CameraManager,
        "BiometricPrompt": BiometricPrompt,

        # android.net
        "ConnectivityManager": ConnectivityManager,
        "NetworkInfo": NetworkInfo,
        "NetworkCapabilities": NetworkCapabilities,
        "WifiManager": WifiManager,
        "WifiInfo": WifiInfo,

        # android.os.storage
        "StorageManager": StorageManager,
        "StorageVolume": StorageVolume,

        # android.telephony
        "TelephonyManager": TelephonyManager,

        # android.widget
        "Toast": Toast,

        # android.print
        "PrintManager": PrintManager,

        # android.accounts
        "AccountManager": AccountManager,
        "Account": Account,

        # android.util
        "Log": Log,

        # java.io
        "File": File,
        "FileInputStream": FileInputStream,
        "FileOutputStream": FileOutputStream,
        "BufferedReader": BufferedReader,
        "BufferedWriter": BufferedWriter,
        "InputStreamReader": InputStreamReader,
        "OutputStreamWriter": OutputStreamWriter,

        # 辅助工具
        "AndroidUtil": AndroidUtil,
        "AndroidUnsupportedStub": AndroidUnsupportedStub,

        # Java 桥接
        "Java": Java,

        # UINode 自动化
        "UINode": UINode,
        "AccessibilityNodeInfo": AccessibilityNodeInfo,
        "AccessibilityPage": AccessibilityPage,

        # 运行时对象
        "androidContext": application_context,

        # Android 路径常量
        "SANDBOX_EXTERNAL_PACKAGES_DIR": os.path.join(_sdcard_root, "Android", "data",
                                                        _package_name, "files", "packages"),
        "SDCARD_ROOT": _sdcard_root,
        "EXTERNAL_STORAGE": _sdcard_root,
    }