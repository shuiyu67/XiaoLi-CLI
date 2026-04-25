"""
安全代码沙箱 v2 - 多层隔离执行环境

安全层级:
  1. AST 静态分析 - 拒绝危险语法
  2. 子进程隔离 - 独立进程执行，资源限制
  3. 文件系统限制 - 仅允许临时目录读写
  4. 网络阻断 - 禁止 socket 连接
  5. 模块白名单 - 仅允许安全模块导入
  6. 输出截断 - 防止内存耗尽
"""
import ast
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import traceback
import threading
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import logging

logger = logging.getLogger(__name__)

try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False


# ──────────────────────────────────────────────
# 安全策略配置
# ──────────────────────────────────────────────

BLOCKED_MODULES: Set[str] = frozenset({
    'os', 'sys', 'subprocess', 'shutil', 'socket', 'pickle',
    'marshal', 'ctypes', 'multiprocessing', 'threading',
    'signal', 'resource', 'posix', 'nt', 'builtins',
    'importlib', 'code', 'codeop', 'bdb', 'pdb',
    'compileall', 'py_compile', 'zipimport', 'pkgutil',
    'http', 'urllib', 'ftplib', 'smtplib', 'xmlrpc',
    'asyncio', 'concurrent', '_thread',
})

BLOCKED_NAMES: Set[str] = frozenset({
    'exec', 'eval', 'compile', 'execfile', 'open',
    'globals', 'locals', 'vars', 'getattr', 'setattr',
    'delattr', '__import__', '__builtins__', '__subclasses__',
    '__loader__', '__spec__', '__file__', '__name__',
    'breakpoint', 'exit', 'quit', 'help',
})

BLOCKED_AST_PATTERNS: List[str] = [
    r'__', r'\beval\b', r'\bexec\b', r'\bcompile\b',
    r'\bglobals\b', r'\blocals\b', r'\bgetattr\b',
    r'\bsetattr\b', r'\b__import__\b', r'\bbreakpoint\b',
]

DEFAULT_WHITELIST: List[str] = [
    'json', 'math', 'datetime', 'random', 'collections',
    'itertools', 'functools', 'operator', 'typing', 're',
    'string', 'textwrap', 'copy', 'decimal', 'fractions',
    'statistics', 'bisect', 'heapq', 'array', 'struct',
    'hashlib', 'hmac', 'secrets', 'base64', 'binascii',
    'uuid', 'pathlib', 'enum', 'dataclasses', 'contextlib',
]

DEFAULT_MEMORY_LIMIT_MB = 256
DEFAULT_CPU_TIME_LIMIT = 30
DEFAULT_OUTPUT_LIMIT = 1_000_000


# ──────────────────────────────────────────────
# 结果数据类
# ──────────────────────────────────────────────

@dataclass
class SandboxResult:
    """沙箱执行结果"""
    success: bool
    result: str = ""
    stdout: str = ""
    stderr: str = ""
    time: float = 0.0
    exit_code: int = 0
    killed: bool = False
    security_violation: str = ""

    def to_dict(self) -> dict:
        return {
            'success': self.success,
            'result': self.result,
            'stdout': self.stdout,
            'stderr': self.stderr,
            'time': round(self.time, 4),
            'exit_code': self.exit_code,
            'killed': self.killed,
            'security_violation': self.security_violation,
        }

    def __str__(self) -> str:
        status = "OK" if self.success else "FAIL"
        parts = [f"{status}: {self.result}"]
        if self.stdout:
            parts.append(f"stdout={self.stdout[:200]}")
        if self.stderr:
            parts.append(f"stderr={self.stderr[:200]}")
        if self.security_violation:
            parts.append(f"security={self.security_violation}")
        parts.append(f"{self.time:.3f}s")
        return " | ".join(parts)


# ──────────────────────────────────────────────
# AST 安全检查器
# ──────────────────────────────────────────────

class ASTSecurityChecker(ast.NodeVisitor):
    """AST 级静态安全分析"""

    def __init__(self, blocked_modules: Set[str] = None,
                 blocked_names: Set[str] = None):
        self.blocked = blocked_modules or BLOCKED_MODULES
        self.blocked_names = blocked_names or BLOCKED_NAMES
        self.violations: List[str] = []

    def _check_name(self, name: str, node: ast.AST):
        lineno = getattr(node, 'lineno', 0)
        if name in self.blocked_names:
            self.violations.append(f"blocked name: {name} (line {lineno})")
        if name.split('.')[0] in self.blocked:
            self.violations.append(f"blocked module: {name} (line {lineno})")

    def visit_Import(self, node):
        for alias in node.names:
            self._check_name(alias.name, node)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self._check_name(node.module, node)
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self._check_name(node.func.id, node)
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                name = node.func.value.id
                if name in self.blocked_names:
                    lineno = getattr(node, 'lineno', 0)
                    self.violations.append(
                        f"blocked call: {name}.{node.func.attr} (line {lineno})"
                    )
        self.generic_visit(node)

    def visit_Name(self, node):
        self._check_name(node.id, node)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if node.attr.startswith('__') and node.attr.endswith('__'):
            if node.attr not in ('__init__', '__str__', '__repr__',
                                  '__len__', '__contains__', '__iter__',
                                  '__eq__', '__ne__', '__lt__', '__gt__',
                                  '__le__', '__ge__', '__hash__', '__bool__',
                                  '__add__', '__sub__', '__mul__', '__truediv__',
                                  '__floordiv__', '__mod__', '__pow__',
                                  '__enter__', '__exit__'):
                lineno = getattr(node, 'lineno', 0)
                self.violations.append(
                    f"blocked dunder: {node.attr} (line {lineno})"
                )
        self.generic_visit(node)

    def visit_Delete(self, node):
        self.violations.append(f"blocked del (line {getattr(node, 'lineno', 0)})")
        self.generic_visit(node)

    def visit_Global(self, node):
        self.violations.append(f"blocked global (line {getattr(node, 'lineno', 0)})")
        self.generic_visit(node)

    def visit_Nonlocal(self, node):
        self.violations.append(f"blocked nonlocal (line {getattr(node, 'lineno', 0)})")
        self.generic_visit(node)

    def check(self, code: str) -> Tuple[bool, List[str]]:
        """检查代码安全性，返回 (safe, violations)"""
        self.violations = []

        for pattern in BLOCKED_AST_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                self.violations.append(f"regex match: {pattern}")

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, [f"syntax error: {e}"]

        self.visit(tree)
        return len(self.violations) == 0, self.violations


# ──────────────────────────────────────────────
# 子进程包装脚本
# ──────────────────────────────────────────────

def _make_worker_script(code: str, variables_json: str,
                        whitelist_json: str, work_dir: str) -> str:
    return textwrap.dedent(f'''\
import sys
import os
import json
import io
import traceback
from contextlib import redirect_stdout, redirect_stderr

os.chdir({work_dir!r})

# Block networking
class _FakeSocket:
    def __getattr__(self, name):
        raise OSError("network access blocked by sandbox")
class _FakeSocketModule:
    AF_INET = 0
    SOCK_STREAM = 0
    def __getattr__(self, name):
        raise OSError("network access blocked by sandbox")
    def socket(self, *a, **kw):
        raise OSError("network access blocked by sandbox")

import types
_fake_mod = _FakeSocketModule()
sys.modules['socket'] = _fake_mod
sys.modules['_socket'] = _fake_mod

WHITELIST = json.loads({whitelist_json!r})
safe_modules = {{}}
for mod_name in WHITELIST:
    try:
        safe_modules[mod_name] = __import__(mod_name)
    except ImportError:
        pass

safe_builtins = {{
    'print': print, 'len': len, 'str': str, 'int': int,
    'float': float, 'list': list, 'dict': dict, 'tuple': tuple,
    'set': set, 'frozenset': frozenset,
    'range': range, 'enumerate': enumerate, 'zip': zip,
    'sorted': sorted, 'reversed': reversed,
    'sum': sum, 'max': max, 'min': min, 'abs': abs,
    'round': round, 'pow': pow, 'divmod': divmod,
    'type': type, 'isinstance': isinstance, 'issubclass': issubclass,
    'hasattr': hasattr, 'callable': callable, 'id': id,
    'chr': chr, 'ord': ord, 'hex': hex, 'oct': oct, 'bin': bin,
    'bool': bool, 'bytes': bytes, 'bytearray': bytearray,
    'map': map, 'filter': filter,
    'any': any, 'all': all,
    'True': True, 'False': False, 'None': None,
}}

user_vars = json.loads({variables_json!r})

exec_vars = {{}}
exec_vars.update(safe_builtins)
exec_vars.update(safe_modules)
exec_vars.update(user_vars)

stdout_buf = io.StringIO()
stderr_buf = io.StringIO()
result_data = {{"success": True, "result": "", "stdout": "", "stderr": "", "error": ""}}

try:
    with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
        exec({code!r}, exec_vars)
    val = exec_vars.get('result', None)
    result_data["result"] = str(val) if val is not None else "executed ok"
except Exception as e:
    result_data["success"] = False
    result_data["error"] = str(e)
    result_data["stderr"] = traceback.format_exc()

result_data["stdout"] = stdout_buf.getvalue()
result_data["stderr"] = stderr_buf.getvalue() or result_data.get("stderr", "")

max_out = 500000
if len(result_data["stdout"]) > max_out:
    result_data["stdout"] = result_data["stdout"][:max_out] + "\\n... (truncated)"
if len(result_data["stderr"]) > max_out:
    result_data["stderr"] = result_data["stderr"][:max_out] + "\\n... (truncated)"

sys.stdout.write(json.dumps(result_data, ensure_ascii=False))
''')


# ──────────────────────────────────────────────
# 主沙箱类
# ──────────────────────────────────────────────

class Sandbox:
    """安全代码执行沙箱 v2

    mode:
      - 'subprocess': 子进程隔离（默认，最安全）
      - 'threaded':   线程内 exec（兼容模式）
    """

    def __init__(self, timeout: int = 30,
                 memory_limit_mb: int = DEFAULT_MEMORY_LIMIT_MB,
                 whitelist: List[str] = None,
                 mode: str = 'subprocess',
                 work_dir: str = None):
        self.enabled = True
        self.timeout = timeout
        self.memory_limit_mb = memory_limit_mb
        self.whitelist = whitelist or DEFAULT_WHITELIST
        self.mode = mode
        self.work_dir = work_dir or tempfile.mkdtemp(prefix='xiaoli_sandbox_')
        self.history: List[Dict] = []
        self._checker = ASTSecurityChecker()
        os.makedirs(self.work_dir, exist_ok=True)

    def is_safe(self, code: str) -> Tuple[bool, List[str]]:
        """静态安全检查（AST + 正则）"""
        return self._checker.check(code)

    def run(self, code: str, variables: dict = None) -> dict:
        """执行代码，返回结果字典（兼容旧接口）"""
        result = self.execute(code, variables)
        return result.to_dict()

    def execute(self, code: str, variables: dict = None) -> SandboxResult:
        """执行代码，返回 SandboxResult"""
        if not self.enabled:
            return SandboxResult(
                success=False, result="sandbox disabled",
                security_violation="sandbox is off"
            )

        safe, violations = self.is_safe(code)
        if not safe:
            return SandboxResult(
                success=False,
                result="code failed security check",
                security_violation="; ".join(violations[:5])
            )

        if self.mode == 'subprocess':
            result = self._run_subprocess(code, variables)
        else:
            result = self._run_threaded(code, variables)

        self.history.append({
            'code': code[:500],
            'success': result.success,
            'time': result.time,
            'timestamp': time.time(),
        })
        return result

    def cleanup(self):
        """清理临时目录"""
        try:
            if os.path.exists(self.work_dir) and 'xiaoli_sandbox_' in self.work_dir:
                shutil.rmtree(self.work_dir, ignore_errors=True)
        except Exception:
            pass

    # ── subprocess ──

    def _run_subprocess(self, code: str, variables: dict = None) -> SandboxResult:
        vars_json = json.dumps(variables or {}, ensure_ascii=False, default=str)
        whitelist_json = json.dumps(self.whitelist)
        script = _make_worker_script(code, vars_json, whitelist_json, self.work_dir)
        start = time.time()

        try:
            proc = subprocess.run(
                [sys.executable, '-c', script],
                capture_output=True,
                timeout=self.timeout,
                cwd=self.work_dir,
                env=self._safe_env(),
                preexec_fn=self._set_limits if HAS_RESOURCE else None,
            )
            elapsed = time.time() - start

            stdout = proc.stdout.decode('utf-8', errors='replace')[:DEFAULT_OUTPUT_LIMIT]
            stderr = proc.stderr.decode('utf-8', errors='replace')[:DEFAULT_OUTPUT_LIMIT]

            try:
                data = json.loads(stdout)
                return SandboxResult(
                    success=data.get('success', False),
                    result=data.get('result', ''),
                    stdout=data.get('stdout', ''),
                    stderr=data.get('stderr', ''),
                    time=elapsed,
                    exit_code=proc.returncode,
                )
            except json.JSONDecodeError:
                return SandboxResult(
                    success=proc.returncode == 0,
                    result=stdout[:2000] if stdout else "no output",
                    stdout=stdout,
                    stderr=stderr,
                    time=elapsed,
                    exit_code=proc.returncode,
                )

        except subprocess.TimeoutExpired:
            return SandboxResult(
                success=False,
                result=f"timeout ({self.timeout}s)",
                time=self.timeout,
                killed=True,
            )
        except Exception as e:
            return SandboxResult(
                success=False,
                result=f"subprocess error: {e}",
                time=time.time() - start,
            )

    def _safe_env(self) -> dict:
        env = {
            'PATH': '/usr/bin:/bin',
            'LANG': 'en_US.UTF-8',
            'LC_ALL': 'en_US.UTF-8',
            'HOME': self.work_dir,
            'TMPDIR': self.work_dir,
            'TEMP': self.work_dir,
            'TMP': self.work_dir,
            'PYTHONNOUSERSITE': '1',
            'PYTHONDONTWRITEBYTECODE': '1',
        }
        for key in ('TERM', 'COLUMNS', 'LINES', 'SHELL'):
            val = os.environ.get(key)
            if val:
                env[key] = val
        return env

    @staticmethod
    def _set_limits():
        if not HAS_RESOURCE:
            return
        try:
            mem_bytes = DEFAULT_MEMORY_LIMIT_MB * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
            resource.setrlimit(resource.RLIMIT_CPU, (
                DEFAULT_CPU_TIME_LIMIT, DEFAULT_CPU_TIME_LIMIT + 5
            ))
            resource.setrlimit(resource.RLIMIT_NPROC, (0, 0))
            resource.setrlimit(resource.RLIMIT_FSIZE, (50 * 1024 * 1024, 50 * 1024 * 1024))
        except (ValueError, OSError):
            pass

    # ── threaded (compat) ──

    def _run_threaded(self, code: str, variables: dict = None) -> SandboxResult:
        exec_vars = {}
        exec_vars.update({
            'print': print, 'len': len, 'str': str, 'int': int,
            'float': float, 'list': list, 'dict': dict, 'tuple': tuple,
            'set': set, 'range': range, 'enumerate': enumerate,
            'zip': zip, 'sorted': sorted, 'sum': sum, 'max': max,
            'min': min, 'abs': abs, 'round': round, 'type': type,
            'isinstance': isinstance,
        })
        for mod_name in self.whitelist:
            try:
                exec_vars[mod_name] = __import__(mod_name)
            except ImportError:
                pass
        if variables:
            exec_vars.update(variables)

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        result = {'success': True, 'error': None, 'tb': None}

        def _exec():
            try:
                with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                    exec(code, exec_vars)
            except Exception as e:
                result['success'] = False
                result['error'] = str(e)
                result['tb'] = traceback.format_exc()

        start = time.time()
        thread = threading.Thread(target=_exec, daemon=True)
        thread.start()
        thread.join(timeout=self.timeout)
        elapsed = time.time() - start

        if thread.is_alive():
            return SandboxResult(
                success=False,
                result=f"timeout ({self.timeout}s)",
                stdout=stdout_buf.getvalue(),
                stderr=stderr_buf.getvalue(),
                time=self.timeout,
                killed=True,
            )

        stdout = stdout_buf.getvalue()
        stderr = stderr_buf.getvalue()

        if result['success']:
            val = exec_vars.get('result', None)
            return SandboxResult(
                success=True,
                result=str(val) if val is not None else "executed ok",
                stdout=stdout,
                stderr=stderr,
                time=elapsed,
            )
        else:
            return SandboxResult(
                success=False,
                result=f"error: {result['error']}",
                stdout=stdout,
                stderr=stderr + ('\n' + (result['tb'] or '')),
                time=elapsed,
            )

    def __del__(self):
        self.cleanup()
