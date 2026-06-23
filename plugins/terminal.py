"""
终端模拟器 v2 — AI 的虚拟键盘和屏幕
=====================================
设计理念：AI 面前有一个终端，它能做的事就是：
  1. 打字（type）
  2. 按键（key）
  3. 看屏幕（read）
就这么简单。
"""
import os
import re
import sys
import time
import uuid
import json
import threading
import subprocess
import platform
from collections import deque

_IS_WIN = platform.system() == "Windows"


class Terminal:
    """一个终端 = 一个子进程 + 一个屏幕缓冲"""

    def __init__(self, sid: str, shell: str = "", cwd: str = ""):
        self.id = sid
        self.shell = shell or self._default_shell()
        self.cwd = cwd or os.getcwd()
        self._proc = None
        self._screen = deque(maxlen=5000)   # 屏幕行
        self._raw = ""                       # 未处理原始输出
        self._lock = threading.Lock()
        self._start()

    @staticmethod
    def _default_shell():
        if _IS_WIN:
            return os.environ.get("COMSPEC", "cmd.exe")
        for s in ["/bin/bash", "/bin/sh"]:
            if os.path.isfile(s):
                return s
        return "/bin/sh"

    def _start(self):
        env = {**os.environ, "TERM": "dumb", "NO_COLOR": "1",
               "PYTHONUNBUFFERED": "1", "PROMPT_COMMAND": ""}
        if not _IS_WIN:
            base = os.path.basename(self.shell)
            if "bash" in base:
                env["PS1"] = ""
                args = [self.shell, "--norc", "--noprofile"]
            elif "python" in base:
                args = [self.shell, "-i"]
            else:
                args = [self.shell]
            flags = 0
        else:
            args = [self.shell, "/K", "chcp 65001 >nul"]
            flags = subprocess.CREATE_NO_WINDOW

        self._proc = subprocess.Popen(
            args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, bufsize=0, cwd=self.cwd,
            env=env, creationflags=flags if _IS_WIN else 0,
        )
        threading.Thread(target=self._reader, daemon=True).start()
        time.sleep(0.3)

    def _reader(self):
        fd = self._proc.stdout.fileno()
        while self._proc.poll() is None:
            try:
                chunk = os.read(fd, 4096)
                if not chunk:
                    break
                text = chunk.decode("utf-8", errors="replace")
                with self._lock:
                    self._raw += text
                    for line in text.split("\n"):
                        self._screen.append(line)
            except (OSError, ValueError):
                break

    def alive(self):
        return self._proc and self._proc.poll() is None

    # ── 核心操作：打字 ──

    def type(self, text: str):
        """像人一样打字，每个字符发到 stdin"""
        if not self.alive():
            return
        try:
            self._proc.stdin.write(text.encode("utf-8"))
            self._proc.stdin.flush()
        except (OSError, BrokenPipeError):
            pass

    # ── 核心操作：按键 ──

    _KEYS = {
        "enter": "\n", "return": "\n",
        "tab": "\t",
        "backspace": "\x7f", "bs": "\x7f",
        "esc": "\x1b", "escape": "\x1b",
        "space": " ",
        "delete": "\x1b[3~", "del": "\x1b[3~",
        "insert": "\x1b[2~",
        "up": "\x1b[A", "down": "\x1b[B",
        "right": "\x1b[C", "left": "\x1b[D",
        "home": "\x1b[H", "end": "\x1b[F",
        "pageup": "\x1b[5~", "pagedown": "\x1b[6~",
        "f1": "\x1bOP", "f2": "\x1bOQ", "f3": "\x1bOR", "f4": "\x1bOS",
        "f5": "\x1b[15~", "f6": "\x1b[17~", "f7": "\x1b[18~", "f8": "\x1b[19~",
        "f9": "\x1b[20~", "f10": "\x1b[21~", "f11": "\x1b[23~", "f12": "\x1b[24~",
    }

    # Ctrl+ 字母映射
    _CTRL = {chr(i): chr(i - 64) for i in range(65, 91)}  # A-Z → \x01-\x1a

    def key(self, name: str):
        """
        按一个键。
        支持: enter, tab, esc, up, down, left, right,
              ctrl+c, ctrl+d, ctrl+z, ctrl+l, ctrl+a, ctrl+e,
              f1-f12, backspace, delete, home, end, space, ...
        """
        if not self.alive():
            return
        name = name.lower().strip()

        # Ctrl+ 组合
        if name.startswith("ctrl+"):
            letter = name[5:]
            seq = self._CTRL.get(letter.upper())
            if seq:
                self._send_raw(seq)
            return

        # 普通按键
        seq = self._KEYS.get(name)
        if seq:
            self._send_raw(seq)
        elif len(name) == 1:
            # 单个字符直接发
            self._send_raw(name)

    def combo(self, *keys):
        """
        组合键，如 combo("ctrl", "shift", "t")
        目前主要支持 ctrl+单字母
        """
        parts = [k.lower() for k in keys]
        if "ctrl" in parts and len(parts) == 2:
            other = [k for k in parts if k != "ctrl"][0]
            self.key(f"ctrl+{other}")
        elif "alt" in parts:
            # Alt+key → ESC + key
            other = [k for k in parts if k != "alt"][0]
            self._send_raw("\x1b" + other)
        elif "shift" in parts:
            other = [k for k in parts if k != "shift"][0]
            self._send_raw(other.upper() if len(other) == 1 else other)

    def _send_raw(self, data: str):
        try:
            self._proc.stdin.write(data.encode("utf-8"))
            self._proc.stdin.flush()
        except (OSError, BrokenPipeError):
            pass

    # ── 核心操作：看屏幕 ──

    def read(self, lines: int = 0) -> str:
        """读取屏幕当前内容"""
        with self._lock:
            if lines > 0:
                buf = list(self._screen)[-lines:]
            else:
                buf = list(self._screen)
        return self._clean("\n".join(buf))

    def read_new(self, timeout: float = 1) -> str:
        """等待并读取新输出"""
        with self._lock:
            self._raw = ""
        time.sleep(timeout)
        with self._lock:
            out = self._raw
            self._raw = ""
        return self._clean(out)

    def wait(self, seconds: float = 1):
        """等待，让终端输出完"""
        time.sleep(seconds)

    def _clean(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
        text = re.sub(r'\x1b\][^\x07]*\x07', '', text)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        text = re.sub(r'\n{4,}', '\n\n\n', text)
        return text.strip()

    def close(self):
        try:
            if self._proc and self._proc.poll() is None:
                self._send_raw("exit\n")
                time.sleep(0.2)
                if self._proc.poll() is None:
                    self._proc.terminate()
                    try:
                        self._proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        self._proc.kill()
        except Exception:
            pass
        self._proc = None


# ═══════════════════════════════════════════════════════════════
#  Liugin 插件
# ═══════════════════════════════════════════════════════════════

class Liugin:
    """终端模拟器 v2 — AI 的虚拟键盘和屏幕"""

    def __init__(self):
        self.cli = None
        self._terminals: dict = {}
        self._current = "main"

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "terminal",
            "description": "终端模拟器 — AI 的虚拟键盘和屏幕。"
                           "启动终端、打字、按键、看屏幕，像人一样操作。",
            "keywords": [
                "终端", "terminal", "shell", "键盘", "按键", "打字",
                "屏幕", "交互", "REPL", "cmd", "bash", "python",
            ],
            "usage": (
                "terminal <操作> [参数]\n\n"
                "  open [shell]         - 打开终端，返回初始画面\n"
                "  type <文字>          - 打字（发送到终端）\n"
                "  key <按键名>         - 按一个键（enter/tab/ctrl+c/方向键...）\n"
                "  read [行数]          - 看屏幕内容\n"
                "  last [行数]          - 看最近N行（默认20，避免上下文爆炸）\n"
                "  wait [秒]            - 等待输出完毕\n"
                "  switch <ID>          - 切换终端\n"
                "  list                 - 列出所有终端\n"
                "  close [ID]           - 关闭终端\n\n"
                "按键: enter tab esc space backspace delete\n"
                "      up down left right home end\n"
                "      ctrl+c ctrl+d ctrl+z ctrl+l ctrl+a ctrl+e\n"
                "      f1-f12\n\n"
                "示例:\n"
                "  terminal open                   - 打开 bash\n"
                "  terminal open python3           - 打开 Python\n"
                "  terminal type ls -la            - 打字\n"
                "  terminal key enter              - 按回车\n"
                "  terminal read                   - 看屏幕\n"
                "  terminal key ctrl+c             - 中断"
            ),
        }

    def get_mcp_definition(self):
        return {
            "name": "terminal",
            "description": "终端模拟器 — AI 的虚拟键盘和屏幕",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["open", "type", "key", "read", "last", "wait",
                                 "switch", "list", "close"],
                    },
                    "text": {"type": "string", "description": "要打的字 / shell路径"},
                    "key": {"type": "string", "description": "按键名"},
                    "last": {"type": "integer", "description": "最近N行"},
                    "seconds": {"type": "number", "description": "等待秒数"},
                    "session": {"type": "string", "description": "终端 ID"},
                },
                "required": ["action"],
            },
        }

    def convert_mcp_args(self, arguments):
        a = arguments.get("action", "")
        parts = [a]
        for k in ["text", "key", "lines", "seconds", "session"]:
            v = arguments.get(k)
            if v is not None:
                parts.append(str(v))
        return " ".join(parts)

    def handle(self, args: str) -> str:
        parts = args.strip().split(maxsplit=1)
        if not parts:
            return self._help()
        action = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""

        # 支持 `read 20` 省写
        if rest.isdigit() and action in ('read', 'last'):
            action, rest = 'last', rest

        h = {
            "open": self._h_open, "type": self._h_type,
            "key": self._h_key, "read": self._h_read,
            "last": self._h_last, "wait": self._h_wait,
            "switch": self._h_switch, "list": self._h_list,
            "close": self._h_close,
        }.get(action)
        if not h:
            return f"不支持 '{action}'\n{self._help()}"
        try:
            return h(rest)
        except Exception as e:
            return f"终端错误: {e}"

    def _help(self):
        return (
            "terminal open [shell]   - 打开终端\n"
            "terminal type <文字>    - 打字\n"
            "terminal key <按键>     - 按键\n"
            "terminal read [行数]    - 看屏幕\n"
            "terminal wait [秒]      - 等待\n"
            "terminal list           - 列出终端\n"
            "terminal close          - 关闭"
        )

    def _get(self, sid: str = "") -> Terminal:
        sid = sid or self._current
        if sid not in self._terminals:
            self._terminals[sid] = Terminal(sid)
        return self._terminals[sid]

    def _h_open(self, rest: str) -> str:
        sid = f"s{len(self._terminals) + 1}" if self._terminals else "main"
        t = Terminal(sid, shell=rest.strip())
        self._terminals[sid] = t
        self._current = sid
        screen = t.read()
        return f"✓ 终端 {sid} 已打开\n{screen}"

    def _h_type(self, rest: str) -> str:
        if not rest:
            return "请提供要打的字"
        t = self._get()
        t.type(rest)
        t.wait(0.3)
        return f"← 打字: {rest}"

    def _h_key(self, rest: str) -> str:
        if not rest:
            return "请提供按键名"
        t = self._get()
        t.key(rest)
        t.wait(0.3)
        return f"← 按键: {rest}"

    def _h_read(self, rest: str) -> str:
        t = self._get()
        return t.read() or "(屏幕为空)"

    def _h_last(self, rest: str) -> str:
        t = self._get()
        n = int(rest) if rest.strip().isdigit() else 20
        return t.read(n) or "(屏幕为空)"

    def _h_wait(self, rest: str) -> str:
        secs = float(rest) if rest.strip() else 1.0
        t = self._get()
        t.wait(secs)
        return t.read()

    def _h_switch(self, rest: str) -> str:
        sid = rest.strip()
        if sid not in self._terminals:
            return f"终端 '{sid}' 不存在"
        self._current = sid
        return f"✓ 切换到 {sid}"

    def _h_list(self, _: str) -> str:
        if not self._terminals:
            return "无终端"
        lines = []
        for sid, t in self._terminals.items():
            cur = " ← 当前" if sid == self._current else ""
            dot = "●" if t.alive() else "○"
            lines.append(f"  {dot} {sid} [{t.shell}]{cur}")
        return "\n".join(lines)

    def _h_close(self, rest: str) -> str:
        sid = rest.strip() or self._current
        if sid not in self._terminals:
            return f"终端 '{sid}' 不存在"
        self._terminals[sid].close()
        del self._terminals[sid]
        if self._current == sid:
            self._current = next(iter(self._terminals), "main")
        return f"✓ 终端 {sid} 已关闭"
