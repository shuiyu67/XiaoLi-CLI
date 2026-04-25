"""安全代码沙箱"""
import io
import ast
import re
import time
import threading
import traceback
from contextlib import redirect_stdout, redirect_stderr
from colorama import Fore, Style
import logging

logger = logging.getLogger(__name__)

DANGEROUS_MODULES = frozenset({
    'os', 'sys', 'subprocess', 'shutil', 'socket', 'pickle',
    'marshal', 'ctypes', 'multiprocessing', 'threading',
    'signal', 'resource', 'posix', 'nt', 'builtins',
    'importlib', 'code', 'codeop',
})

DANGEROUS_NAMES = frozenset({
    'exec', 'eval', 'compile', 'execfile', 'open',
    'globals', 'locals', 'vars', 'getattr', 'setattr',
    'delattr', '__import__', '__builtins__', '__subclasses__',
})

DANGEROUS_PATTERNS = [
    r'__', r'\beval\b', r'\bexec\b', r'\bcompile\b',
    r'\bglobals\b', r'\blocals\b', r'\bgetattr\b',
    r'\bsetattr\b', r'\b__import__\b',
]


class Sandbox:
    """安全代码执行沙箱"""

    def __init__(self, timeout=30, whitelist=None):
        self.enabled = True
        self.timeout = timeout
        self.whitelist = whitelist or [
            'json', 'math', 'datetime', 'random', 'collections',
            'itertools', 'functools', 'operator', 'typing', 're'
        ]
        self.history = []

    def is_safe(self, code: str) -> bool:
        """快速安全检查"""
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                return False

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return False

        class Checker(ast.NodeVisitor):
            def __init__(self):
                self.ok = True

            def _check(self, name):
                if name in DANGEROUS_NAMES or name in DANGEROUS_MODULES:
                    self.ok = False

            def visit_Import(self, node):
                for alias in node.names:
                    if alias.name.split('.')[0] in DANGEROUS_MODULES:
                        self.ok = False
                self.generic_visit(node)

            def visit_ImportFrom(self, node):
                if node.module and node.module.split('.')[0] in DANGEROUS_MODULES:
                    self.ok = False
                self.generic_visit(node)

            def visit_Call(self, node):
                if isinstance(node.func, ast.Name):
                    self._check(node.func.id)
                self.generic_visit(node)

            def visit_Name(self, node):
                self._check(node.id)
                self.generic_visit(node)

        checker = Checker()
        checker.visit(tree)
        return checker.ok

    def run(self, code: str, variables: dict = None) -> dict:
        """执行代码"""
        if not self.enabled:
            return {'success': False, 'result': '沙箱已禁用', 'stdout': '', 'stderr': '', 'time': 0}

        if not self.is_safe(code):
            return {'success': False, 'result': '代码包含危险操作', 'stdout': '', 'stderr': '', 'time': 0}

        exec_vars = dict(variables or {})
        exec_vars.update({
            'print': print, 'len': len, 'str': str, 'int': int,
            'float': float, 'list': list, 'dict': dict, 'tuple': tuple,
            'set': set, 'range': range, 'enumerate': enumerate,
            'zip': zip, 'sorted': sorted, 'sum': sum, 'max': max,
            'min': min, 'abs': abs, 'round': round, 'type': type,
            'isinstance': isinstance,
        })

        for mod in self.whitelist:
            try:
                exec_vars[mod] = __import__(mod)
            except ImportError:
                pass

        stdout = io.StringIO()
        stderr = io.StringIO()
        start = time.time()
        result = {'success': True, 'error': None, 'tb': None}

        def _exec():
            try:
                exec(code, exec_vars)
            except Exception as e:
                result['success'] = False
                result['error'] = str(e)
                result['tb'] = traceback.format_exc()

        thread = threading.Thread(target=_exec, daemon=True)
        thread.start()
        thread.join(timeout=self.timeout)
        elapsed = time.time() - start

        if thread.is_alive():
            return {'success': False, 'result': f'超时 ({self.timeout}s)',
                    'stdout': stdout.getvalue(), 'stderr': stderr.getvalue(), 'time': self.timeout}

        if result['success']:
            val = exec_vars.get('result', None)
            return {'success': True,
                    'result': str(val) if val is not None else '执行成功（无返回值）',
                    'stdout': stdout.getvalue(), 'stderr': stderr.getvalue(), 'time': elapsed}
        else:
            return {'success': False,
                    'result': f"错误: {result['error']}",
                    'stdout': stdout.getvalue(),
                    'stderr': stderr.getvalue() + '\n' + (result['tb'] or ''),
                    'time': elapsed}
