"""
终端模拟器插件 — 纯标准库，Windows/Linux/macOS 通用
===================================================
持久交互式终端会话，AI 可以像人一样打开终端、敲命令、
看输出、继续交互，支持 Python REPL、SSH、top 等。
"""
import os
import re
import sys
import time
import json
import uuid
import shutil
import signal
import threading
import subprocess
import platform
from collections import deque


# ═══════════════════════════════════════════════════════════════
#  ToolResult 轻量替代（避免依赖 xcli_core）
# ═══════════════════════════════════════════════════════════════

class _R:
    """极简返回值"""
    @staticmethod
    def ok(data): return str(data)
    @staticmethod
    def fail(msg): return f"[错误] {msg}"


# ═══════════════════════════════════════════════════════════════
#  单个终端会话
# ═══════════════════════════════════════════════════════════════

_IS_WIN = platform.system() == "Windows"

class TerminalSession:
    """
    一个持久的交互式终端会话。
    纯标准库实现：subprocess.Popen + threading.Thread，
    不依赖 pty、pty.openpty、select.poll 等 Unix 特有 API。
    """

    _SENTINEL = "<<<XLI_DONE_"

    def __init__(self, session_id: str, shell: str = "", cwd: str = "",
                 env: dict = None, label: str = ""):
        self.id = session_id
        self.label = label or session_id
        self.shell = shell or self._default_shell()
        self.cwd = cwd or os.getcwd()
        self.env = env or {}
        self.created_at = time.time()
        self.last_active = time.time()

        self._output_buf = deque(maxlen=5000)
        self._raw_buf = ""
        self._last_cmd_output = ""   # 最近一次 send_cmd 的结果
        self._lock = threading.Lock()
        self._proc = None
        self._reader = None
        self._start()

    @staticmethod
    def _default_shell():
        if _IS_WIN:
            return os.environ.get("COMSPEC", "cmd.exe")
        for sh in ["/bin/bash", "/bin/sh", "/usr/bin/bash"]:
            if os.path.isfile(sh):
                return sh
        return "/bin/sh"

    def _start(self):
        env = {**os.environ, **self.env}

        if _IS_WIN:
            shell_args = [self.shell, "/K", "chcp 65001 >nul"]
            creationflags = subprocess.CREATE_NO_WINDOW
        else:
            env["TERM"] = "dumb"
            env["NO_COLOR"] = "1"
            env["PROMPT_COMMAND"] = ""
            env["PYTHONUNBUFFERED"] = "1"  # Python REPL 不缓冲
            creationflags = 0

            # 只有 bash 才加 --norc --noprofile
            shell_base = os.path.basename(self.shell)
            if shell_base in ("bash", "bash.exe"):
                env["PS1"] = ""
                shell_args = [self.shell, "--norc", "--noprofile"]
            elif "python" in shell_base:
                # Python 需要 -i 才能管道下交互
                shell_args = [self.shell, "-i"]
            else:
                shell_args = [self.shell]

        try:
            self._proc = subprocess.Popen(
                shell_args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=self.cwd,
                env=env,
                bufsize=0,
                creationflags=creationflags if _IS_WIN else 0,
            )
        except FileNotFoundError:
            raise RuntimeError(f"Shell 不存在: {self.shell}")
        except Exception as e:
            raise RuntimeError(f"启动终端失败: {e}")

        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        time.sleep(0.3)
        self.last_active = time.time()

    def _read_loop(self):
        """后台持续读取子进程 stdout"""
        proc = self._proc
        fd = proc.stdout.fileno()
        while proc.poll() is None:
            try:
                chunk = os.read(fd, 4096)
                if not chunk:
                    break
                text = chunk.decode("utf-8", errors="replace")
                with self._lock:
                    self._raw_buf += text
                    for line in text.split("\n"):
                        self._output_buf.append(line)
            except (OSError, ValueError):
                break

    def send(self, text: str, wait: float = 0.3, timeout: float = 15) -> str:
        """发送文本，返回后续输出"""
        if not self.alive():
            return "[错误] 终端进程已退出"

        self.last_active = time.time()
        with self._lock:
            self._raw_buf = ""

        try:
            self._proc.stdin.write(text.encode("utf-8"))
            self._proc.stdin.flush()
        except (OSError, BrokenPipeError) as e:
            return f"[错误] 发送失败: {e}"

        return self._collect(wait, timeout)

    def send_cmd(self, command: str, timeout: float = 15) -> str:
        """
        发送命令并可靠等待输出结束。
        用临时文件做哨兵，避免 stdout 混入提示符。
        """
        if not self.alive():
            return "[错误] 终端进程已退出"

        self.last_active = time.time()
        with self._lock:
            self._raw_buf = ""

        # 哨兵临时文件
        marker = f"/tmp/.xli_{uuid.uuid4().hex[:8]}" if not _IS_WIN else f"%TEMP%\\.xli_{uuid.uuid4().hex[:8]}"

        # 发送: 命令 + 哨兵文件创建
        payload = f"{command}\n{'touch' if not _IS_WIN else 'type nul >'} {marker}\n"
        try:
            self._proc.stdin.write(payload.encode("utf-8"))
            self._proc.stdin.flush()
        except (OSError, BrokenPipeError) as e:
            return f"[错误] 发送失败: {e}"

        # 等待哨兵文件出现
        real_marker = marker if not _IS_WIN else os.path.expandvars(marker)
        deadline = time.time() + timeout
        while time.time() < deadline:
            if os.path.exists(real_marker):
                break
            time.sleep(0.03)

        # 给 stdout 一点时间把剩余输出冲完
        time.sleep(0.1)

        # 收集输出
        with self._lock:
            out = self._raw_buf
            self._raw_buf = ""

        # 清理哨兵文件
        try:
            os.unlink(real_marker)
        except OSError:
            pass

        # 过滤掉命令回显和哨兵行
        lines = out.split("\n")
        result = []
        for line in lines:
            s = line.strip()
            if s == command.strip():
                continue
            if ".xli_" in s:
                continue
            if s.startswith("touch ") or s.startswith("type nul"):
                continue
            result.append(line)

        out = self._clean("\n".join(result))
        with self._lock:
            self._last_cmd_output = out
        return out

    def _collect(self, wait: float, timeout: float) -> str:
        """收集输出"""
        time.sleep(wait)
        deadline = time.time() + timeout
        buf = ""
        while time.time() < deadline:
            with self._lock:
                new = self._raw_buf
                self._raw_buf = ""
            buf += new
            if new:
                time.sleep(0.05)
            else:
                time.sleep(0.1)
                with self._lock:
                    new = self._raw_buf
                    self._raw_buf = ""
                buf += new
                if not new:
                    break
        return self._clean(buf)

    def _clean(self, text: str) -> str:
        if not text:
            return ""
        # 去 ANSI 转义
        text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
        text = re.sub(r'\x1b\][^\x07]*\x07', '', text)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        text = re.sub(r'\n{4,}', '\n\n\n', text)
        return text.strip()

    def alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def recent(self, lines: int = 50) -> str:
        """返回原始输出缓冲的最近几行"""
        with self._lock:
            buf = list(self._output_buf)[-lines:]
        return self._clean("\n".join(buf))

    def status(self) -> dict:
        with self._lock:
            lines = len(self._last_cmd_output.split('\n')) if self._last_cmd_output else 0
        return {
            "id": self.id,
            "label": self.label,
            "shell": self.shell,
            "cwd": self.cwd,
            "alive": self.alive(),
            "pid": self._proc.pid if self._proc else None,
            "uptime": round(time.time() - self.created_at, 1),
            "idle": round(time.time() - self.last_active, 1),
            "lines": lines,
        }

    def close(self):
        try:
            if self._proc and self._proc.poll() is None:
                try:
                    self._proc.stdin.write(b"exit\n")
                    self._proc.stdin.flush()
                except Exception:
                    pass
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
    """终端模拟器 — 纯标准库，全平台"""

    def __init__(self):
        self.cli = None
        self._sessions: dict = {}
        self._default_id = "main"

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "terminal",
            "description": "交互式终端模拟器 — 持久 Shell 会话，纯标准库实现，"
                           "Windows/Linux/macOS 通用，支持 Python REPL、SSH 等交互式程序",
            "keywords": [
                "终端", "terminal", "shell", "交互", "会话", "REPL",
                "持久", "cmd", "powershell", "bash", "pty", "windows",
            ],
            "usage": (
                "terminal <操作> [参数]\n\n"
                "操作:\n"
                "  open [shell] [label]    - 打开新终端 (默认: 系统 shell)\n"
                "  send <命令> [--timeout N] - 发送命令并获取输出\n"
                "  input <文本>            - 发送纯输入 (不换行)\n"
                "  read [行数]             - 读取最近输出\n"
                "  switch <ID>             - 切换会话\n"
                "  list                    - 列出所有会话\n"
                "  close [ID]              - 关闭会话\n"
                "  status                  - 当前状态\n"
                "  cwd [路径]              - 获取/切换目录\n"
                "  env <KEY> [VALUE]       - 环境变量\n"
                "  keys <按键名>           - 发送特殊按键\n\n"
                "示例:\n"
                "  terminal open                        - 打开默认 shell\n"
                "  terminal open python3 \"Python\"      - 打开 Python REPL\n"
                "  terminal send dir                    - Windows 列目录\n"
                "  terminal send ls -la                 - Linux 列目录\n"
                "  terminal send ssh user@host          - SSH 连接\n"
                "  terminal keys Ctrl+C                 - 中断程序\n"
                "  terminal close                       - 关闭当前会话"
            ),
        }

    def get_mcp_definition(self):
        return {
            "name": "terminal",
            "description": "交互式终端模拟器 — 持久 Shell 会话，支持交互式程序",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["open", "send", "input", "read", "switch",
                                 "list", "close", "status", "cwd", "env", "keys"],
                        "description": "操作类型",
                    },
                    "command": {"type": "string", "description": "命令或文本"},
                    "session_id": {"type": "string", "description": "会话 ID"},
                    "shell": {"type": "string", "description": "Shell 路径"},
                    "label": {"type": "string", "description": "会话标签"},
                    "timeout": {"type": "number", "description": "超时秒数 (默认 15)"},
                    "lines": {"type": "integer", "description": "读取行数"},
                    "value": {"type": "string", "description": "环境变量值"},
                    "keys": {"type": "string", "description": "特殊按键"},
                },
                "required": ["action"],
            },
        }

    def convert_mcp_args(self, arguments):
        action = arguments.get("action", "")
        parts = [action]
        cmd = arguments.get("command", "")
        if cmd:
            parts.append(cmd)
        sid = arguments.get("session_id", "")
        if sid:
            parts.append(f"--sid {sid}")
        shell = arguments.get("shell", "")
        if shell:
            parts.append(f"--shell {shell}")
        label = arguments.get("label", "")
        if label:
            parts.append(f"--label {label}")
        timeout = arguments.get("timeout")
        if timeout is not None:
            parts.append(f"--timeout {timeout}")
        lines = arguments.get("lines")
        if lines is not None:
            parts.append(f"--lines {lines}")
        value = arguments.get("value")
        if value is not None:
            parts.append(value)
        keys = arguments.get("keys")
        if keys:
            parts.append(keys)
        return " ".join(parts)

    _KEY_MAP = {
        "ctrl+c": "\x03", "ctrl+d": "\x04", "ctrl+z": "\x1a",
        "ctrl+l": "\x0c", "ctrl+a": "\x01", "ctrl+e": "\x05",
        "ctrl+k": "\x0b", "ctrl+u": "\x15", "ctrl+w": "\x17",
        "tab": "\t", "enter": "\n",
        "up": "\x1b[A", "down": "\x1b[B",
        "right": "\x1b[C", "left": "\x1b[D",
        "home": "\x1b[H", "end": "\x1b[F",
        "backspace": "\x7f", "esc": "\x1b",
        "pageup": "\x1b[5~", "pagedown": "\x1b[6~",
    }

    def handle(self, args: str) -> str:
        parts = args.strip().split(maxsplit=1)
        if not parts:
            return self._help()
        action = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""
        h = {
            "open": self._h_open, "send": self._h_send,
            "input": self._h_input, "read": self._h_read,
            "switch": self._h_switch, "list": self._h_list,
            "close": self._h_close, "status": self._h_status,
            "cwd": self._h_cwd, "env": self._h_env, "keys": self._h_keys,
        }.get(action)
        if not h:
            return f"错误: 不支持 '{action}'\n{self._help()}"
        try:
            return h(rest)
        except Exception as e:
            return f"终端错误: {e}"

    def _help(self):
        return (
            "终端模拟器:\n"
            "  open [shell] [label]  - 打开新会话\n"
            "  send <命令>           - 执行命令\n"
            "  input <文本>          - 纯输入\n"
            "  read [行数]           - 读输出\n"
            "  switch/list/close     - 会话管理\n"
            "  cwd/env/keys          - 目录/变量/按键"
        )

    def _get(self, sid: str = "") -> TerminalSession:
        sid = sid or self._default_id
        if sid not in self._sessions:
            self._sessions[sid] = TerminalSession(sid)
        return self._sessions[sid]

    def _opts(self, rest: str) -> dict:
        opts = {}
        for m in re.finditer(r'--(\w+)\s+(\S+)', rest):
            opts[m.group(1)] = m.group(2)
        opts["_"] = re.sub(r'--\w+\s+\S+', '', rest).strip()
        return opts

    def _h_open(self, rest: str) -> str:
        o = self._opts(rest)
        shell = o.get("shell", "")
        label = o.get("label", "")
        sid = o.get("sid", "")
        pos = o.get("_", "")
        if pos and not shell:
            ps = pos.split()
            shell = ps[0]
            if len(ps) > 1 and not label:
                label = ps[1]
        if not sid:
            sid = f"s{len(self._sessions) + 1}" if self._sessions else self._default_id
        try:
            s = TerminalSession(sid, shell=shell, label=label)
            self._sessions[sid] = s
            self._default_id = sid  # 自动切换到新会话
            info = s.status()
            return (
                f"✓ 终端已打开\n"
                f"  会话: {sid} ({info['label']})\n"
                f"  Shell: {info['shell']}\n"
                f"  PID: {info['pid']}\n"
                f"  输出:\n{s.recent(10) or '(空)'}"
            )
        except RuntimeError as e:
            return f"✗ 打开失败: {e}"

    def _h_send(self, rest: str) -> str:
        if not rest:
            return "错误: 请提供命令"
        o = self._opts(rest)
        cmd = o.get("_", rest).strip()
        timeout = float(o.get("timeout", "15"))
        if not cmd:
            cmd = re.sub(r'--timeout\s+\S+', '', rest).strip()
        if not cmd:
            return "错误: 请提供命令"
        s = self._get()
        out = s.send_cmd(cmd, timeout=timeout)
        tag = "✓" if s.alive() else "✗"
        return f"{tag} {cmd}\n{out}"

    def _h_input(self, rest: str) -> str:
        if not rest:
            return "错误: 请提供文本"
        s = self._get()
        # 加换行让 REPL 执行
        out = s.send(rest + "\n", wait=0.5)
        with s._lock:
            s._last_cmd_output = out
        return f"← 输入: {rest}\n{out}"

    def _h_read(self, rest: str) -> str:
        """读取输出 — 优先用缓存，否则从原始缓冲读"""
        s = self._get()
        with s._lock:
            cached = s._last_cmd_output
        if cached:
            return cached
        # REPL 场景：从原始缓冲读
        return s.recent(30) or "(无输出)"

    def _h_switch(self, rest: str) -> str:
        sid = rest.strip()
        if not sid:
            return "错误: 请提供会话 ID"
        if sid not in self._sessions:
            return f"错误: 不存在 '{sid}'。可用: {', '.join(self._sessions)}"
        self._default_id = sid
        s = self._sessions[sid]
        return f"✓ 已切换到 {sid} ({s.label})"

    def _h_list(self, _: str) -> str:
        if not self._sessions:
            return "暂无终端。用 terminal open 打开。"
        lines = [f"终端 ({len(self._sessions)} 个):", ""]
        for sid, s in self._sessions.items():
            st = s.status()
            cur = " ← 当前" if sid == self._default_id else ""
            dot = "●" if st["alive"] else "○"
            lines.append(
                f"  {dot} {sid}: {st['label']}  "
                f"[{st['shell']}]  "
                f"空闲{st['idle']}s  "
                f"{st['lines']}行{cur}"
            )
        return "\n".join(lines)

    def _h_close(self, rest: str) -> str:
        sid = rest.strip() or self._default_id
        if sid not in self._sessions:
            return f"错误: 不存在 '{sid}'"
        s = self._sessions.pop(sid)
        s.close()
        if self._default_id == sid:
            self._default_id = next(iter(self._sessions), "main")
        return f"✓ 终端 {sid} ({s.label}) 已关闭"

    def _h_status(self, _: str) -> str:
        s = self._get()
        st = s.status()
        return (
            f"终端状态:\n"
            f"  会话: {st['id']} ({st['label']})\n"
            f"  Shell: {st['shell']}\n"
            f"  PID: {st['pid']}\n"
            f"  目录: {st['cwd']}\n"
            f"  状态: {'运行中' if st['alive'] else '已退出'}\n"
            f"  运行: {st['uptime']}s  空闲: {st['idle']}s\n"
            f"  输出: {st['lines']}行"
        )

    def _h_cwd(self, rest: str) -> str:
        s = self._get()
        target = rest.strip()
        if not target:
            return f"当前目录: {s.send_cmd('cd' if _IS_WIN else 'pwd', timeout=5)}"
        cmd = f"cd /d {target} && cd" if _IS_WIN else f"cd {target} && pwd"
        out = s.send_cmd(cmd, timeout=5)
        if out and not out.startswith("[错误"):
            s.cwd = out.strip().split("\n")[-1].strip()
            return f"✓ 目录: {s.cwd}"
        return f"切换失败: {out}"

    def _h_env(self, rest: str) -> str:
        s = self._get()
        parts = rest.strip().split(maxsplit=1)
        if not parts:
            return s.send_cmd("set" if _IS_WIN else "env | head -30", timeout=5)
        key = parts[0]
        if len(parts) == 1:
            var = f"%{key}%" if _IS_WIN else f"${key}"
            return s.send_cmd(f"echo {var}", timeout=5)
        val = parts[1]
        cmd = f"set {key}={val}" if _IS_WIN else f"export {key}={val}"
        s.send_cmd(cmd, timeout=5)
        return f"✓ {key}={val}"

    def _h_keys(self, rest: str) -> str:
        if not rest:
            return f"可用: {', '.join(self._KEY_MAP)}"
        s = self._get()
        name = rest.strip().lower()
        seq = self._KEY_MAP.get(name)
        if not seq:
            return f"错误: 未知按键 '{name}'\n可用: {', '.join(self._KEY_MAP)}"
        out = s.send(seq, wait=0.3)
        return f"← {name}\n{out}"
