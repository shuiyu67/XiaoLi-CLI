# ── 安全代码沙箱 v2（子进程隔离） ──

import ast as _ast
import re
import textwrap as _textwrap
import tempfile as _tempfile

try:
    import resource as _resource_mod
    _HAS_RESOURCE = hasattr(_resource_mod, 'setrlimit')
except ImportError:
    _resource_mod = None
    _HAS_RESOURCE = False

_BLOCKED_MODULES = frozenset({
    'os', 'sys', 'subprocess', 'shutil', 'socket', 'pickle',
    'marshal', 'ctypes', 'multiprocessing', 'threading',
    'signal', 'resource', 'posix', 'nt', 'builtins',
    'importlib', 'code', 'codeop', 'bdb', 'pdb',
    'compileall', 'py_compile', 'zipimport', 'pkgutil',
    'http', 'urllib', 'ftplib', 'smtplib', 'xmlrpc',
    'asyncio', 'concurrent', '_thread',
})
_BLOCKED_NAMES = frozenset({
    'exec', 'eval', 'compile', 'execfile', 'open',
    'globals', 'locals', 'vars', 'getattr', 'setattr',
    'delattr', '__import__', '__builtins__', '__subclasses__',
    '__loader__', '__spec__', '__file__', '__name__',
    'breakpoint', 'exit', 'quit', 'help',
})
_BLOCKED_AST_PATTERNS = [
    r'__', r'\beval\b', r'\bexec\b', r'\bcompile\b',
    r'\bglobals\b', r'\blocals\b', r'\bgetattr\b',
    r'\bsetattr\b', r'\b__import__\b', r'\bbreakpoint\b',
]
_SAFE_WHITELIST = [
    'json', 'math', 'datetime', 'random', 'collections',
    'itertools', 'functools', 'operator', 'typing', 're',
    'string', 'textwrap', 'copy', 'decimal', 'fractions',
    'statistics', 'bisect', 'heapq', 'array', 'struct',
    'hashlib', 'hmac', 'secrets', 'base64', 'binascii',
    'uuid', 'pathlib', 'enum', 'dataclasses', 'contextlib',
]


class _SandboxASTChecker(_ast.NodeVisitor):
    """AST 级安全分析"""
    def __init__(self):
        self.violations = []

    def _check(self, name, node):
        if name in _BLOCKED_NAMES:
            self.violations.append(f"blocked name: {name} (line {getattr(node,'lineno',0)})")
        if name.split('.')[0] in _BLOCKED_MODULES:
            self.violations.append(f"blocked module: {name} (line {getattr(node,'lineno',0)})")

    def visit_Import(self, node):
        for alias in node.names:
            self._check(alias.name, node)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self._check(node.module, node)
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, _ast.Name):
            self._check(node.func.id, node)
        elif isinstance(node.func, _ast.Attribute):
            if isinstance(node.func.value, _ast.Name):
                if node.func.value.id in _BLOCKED_NAMES:
                    self.violations.append(f"blocked call: {node.func.value.id}.{node.func.attr} (line {getattr(node,'lineno',0)})")
        self.generic_visit(node)

    def visit_Name(self, node):
        self._check(node.id, node)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if node.attr.startswith('__') and node.attr.endswith('__'):
            _SAFE_DUNDERS = ('__init__','__str__','__repr__','__len__','__contains__',
                             '__iter__','__eq__','__ne__','__lt__','__gt__','__le__',
                             '__ge__','__hash__','__bool__','__add__','__sub__',
                             '__mul__','__truediv__','__floordiv__','__mod__','__pow__',
                             '__enter__','__exit__')
            if node.attr not in _SAFE_DUNDERS:
                self.violations.append(f"blocked dunder: {node.attr} (line {getattr(node,'lineno',0)})")
        self.generic_visit(node)

    def visit_Delete(self, node):
        self.violations.append(f"blocked del (line {getattr(node,'lineno',0)})")
        self.generic_visit(node)

    def visit_Global(self, node):
        self.violations.append(f"blocked global (line {getattr(node,'lineno',0)})")
        self.generic_visit(node)

    def visit_Nonlocal(self, node):
        self.violations.append(f"blocked nonlocal (line {getattr(node,'lineno',0)})")
        self.generic_visit(node)

    def check(self, code):
        self.violations = []
        for p in _BLOCKED_AST_PATTERNS:
            if re.search(p, code, re.IGNORECASE):
                self.violations.append(f"regex match: {p}")
        try:
            tree = _ast.parse(code)
        except SyntaxError as e:
            return False, [f"syntax error: {e}"]
        self.visit(tree)
        return len(self.violations) == 0, self.violations


def _make_sandbox_worker(code, variables_json, whitelist_json, work_dir):
    """生成子进程隔离脚本"""
    return _textwrap.dedent(f'''\
import sys, os, json, io, traceback
from contextlib import redirect_stdout, redirect_stderr
os.chdir({work_dir!r})

class _FakeSocket:
    def __getattr__(self, name):
        raise OSError("network access blocked by sandbox")
class _FakeSocketModule:
    AF_INET = 0; SOCK_STREAM = 0
    def __getattr__(self, name):
        raise OSError("network access blocked by sandbox")
    def socket(self, *a, **kw):
        raise OSError("network access blocked by sandbox")
import types
_fake = _FakeSocketModule()
sys.modules['socket'] = _fake
sys.modules['_socket'] = _fake

WHITELIST = json.loads({whitelist_json!r})
safe_modules = {{}}
for m in WHITELIST:
    try: safe_modules[m] = __import__(m)
    except ImportError: pass

safe_builtins = {{
    'print': print, 'len': len, 'str': str, 'int': int,
    'float': float, 'list': list, 'dict': dict, 'tuple': tuple,
    'set': set, 'frozenset': frozenset, 'range': range,
    'enumerate': enumerate, 'zip': zip, 'sorted': sorted,
    'reversed': reversed, 'sum': sum, 'max': max, 'min': min,
    'abs': abs, 'round': round, 'pow': pow, 'divmod': divmod,
    'type': type, 'isinstance': isinstance, 'issubclass': issubclass,
    'hasattr': hasattr, 'callable': callable, 'id': id,
    'chr': chr, 'ord': ord, 'hex': hex, 'oct': oct, 'bin': bin,
    'bool': bool, 'bytes': bytes, 'bytearray': bytearray,
    'map': map, 'filter': filter, 'any': any, 'all': all,
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


_sandbox_work_dir = _tempfile.mkdtemp(prefix='xiaoli_sandbox_')
_sandbox_checker = _SandboxASTChecker()
