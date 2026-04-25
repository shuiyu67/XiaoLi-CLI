"""
安全代码沙箱 - 在隔离环境中执行用户/插件代码
"""
import io
import ast
import time
import re
import threading
import traceback
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime
from colorama import Fore, Style
import logging

logger = logging.getLogger(__name__)


class CodeSandbox:
    """安全代码执行沙箱"""

    # 危险模块黑名单
    DANGEROUS_MODULES = {
        'os', 'sys', 'subprocess', 'shutil', 'socket', 'pickle',
        'marshal', 'ctypes', 'multiprocessing', 'threading',
        'signal', 'resource', 'posix', 'nt', 'builtins',
        'importlib', 'code', 'codeop', 'commands', 'popen2',
    }

    # 危险函数/属性黑名单
    DANGEROUS_FUNCTIONS = {
        'exec', 'eval', 'compile', 'execfile', 'open',
        'input', 'raw_input', 'globals', 'locals', 'vars',
        'dir', 'getattr', 'setattr', 'delattr', 'hasattr',
        '__import__', '__builtins__', '__class__', '__bases__',
        '__subclasses__', '__mro__', '__dict__', '__getattribute__',
    }

    def __init__(self, timeout=30, whitelist=None):
        self.enabled = True
        self.timeout = timeout
        self.whitelist = whitelist or [
            'json', 'math', 'datetime', 'random', 'collections',
            'itertools', 'functools', 'operator', 'typing', 're'
        ]
        self.history = []
        self.max_history = 100

    def is_safe(self, code: str) -> bool:
        """检查代码是否安全（AST 分析 + 字符串快速检查）"""
        # 快速字符串检查
        dangerous_patterns = [
            r'__', r'\beval\b', r'\bexec\b', r'\bcompile\b',
            r'\bglobals\b', r'\blocals\b', r'\bgetattr\b',
            r'\bsetattr\b', r'\b__import__\b',
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return False

        # AST 分析
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return False

        class SafetyVisitor(ast.NodeVisitor):
            def __init__(self):
                self.is_safe = True

            def _check_name(self, name):
                if name in CodeSandbox.DANGEROUS_FUNCTIONS:
                    self.is_safe = False

            def visit_Import(self, node):
                for alias in node.names:
                    if alias.name.split('.')[0] in CodeSandbox.DANGEROUS_MODULES:
                        self.is_safe = False
                self.generic_visit(node)

            def visit_ImportFrom(self, node):
                if node.module:
                    if node.module.split('.')[0] in CodeSandbox.DANGEROUS_MODULES:
                        self.is_safe = False
                self.generic_visit(node)

            def visit_Call(self, node):
                if isinstance(node.func, ast.Name):
                    self._check_name(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    self._check_name(node.func.attr)
                self.generic_visit(node)

            def visit_Attribute(self, node):
                self._check_name(node.attr)
                self.generic_visit(node)

            def visit_Name(self, node):
                self._check_name(node.id)
                self.generic_visit(node)

        visitor = SafetyVisitor()
        visitor.visit(tree)
        return visitor.is_safe

    def execute(self, code: str, variables: dict = None) -> dict:
        """
        在安全沙箱中执行代码

        Returns:
            {
                'success': bool,
                'result': str,
                'stdout': str,
                'stderr': str,
                'execution_time': float,
            }
        """
        if not self.enabled:
            return {'success': False, 'result': '代码执行功能已禁用',
                    'stdout': '', 'stderr': '', 'execution_time': 0}

        if not self.is_safe(code):
            return {'success': False, 'result': '代码包含潜在危险操作，已阻止执行',
                    'stdout': '', 'stderr': '', 'execution_time': 0}

        # 准备变量
        exec_vars = {}
        if variables:
            exec_vars.update(variables)

        # 添加安全的内置函数
        safe_builtins = {
            'print': print, 'len': len, 'str': str, 'int': int,
            'float': float, 'list': list, 'dict': dict, 'tuple': tuple,
            'set': set, 'range': range, 'enumerate': enumerate,
            'zip': zip, 'sorted': sorted, 'sum': sum, 'max': max,
            'min': min, 'abs': abs, 'round': round, 'bool': bool,
            'type': type, 'isinstance': isinstance,
        }
        exec_vars.update(safe_builtins)

        # 添加白名单模块
        for module_name in self.whitelist:
            try:
                exec_vars[module_name] = __import__(module_name)
            except ImportError:
                pass

        # 捕获输出
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        start_time = time.time()
        result = {'success': True, 'error': None, 'traceback': None}

        def _exec():
            try:
                exec(code, exec_vars)
            except Exception as e:
                result['success'] = False
                result['error'] = str(e)
                result['traceback'] = traceback.format_exc()

        exec_thread = threading.Thread(target=_exec, daemon=True)
        exec_thread.start()
        exec_thread.join(timeout=self.timeout)

        exec_time = time.time() - start_time

        if exec_thread.is_alive():
            return {
                'success': False,
                'result': f'代码执行超时（超过 {self.timeout} 秒）',
                'stdout': stdout_capture.getvalue(),
                'stderr': stderr_capture.getvalue(),
                'execution_time': self.timeout,
            }

        if result['success']:
            exec_result = exec_vars.get('result', None)
            result_str = str(exec_result) if exec_result is not None else '代码执行成功（无返回值）'
            return {
                'success': True,
                'result': result_str,
                'stdout': stdout_capture.getvalue(),
                'stderr': stderr_capture.getvalue(),
                'execution_time': exec_time,
            }
        else:
            return {
                'success': False,
                'result': f"代码执行错误: {result['error']}",
                'stdout': stdout_capture.getvalue(),
                'stderr': stderr_capture.getvalue() + '\n' + (result['traceback'] or ''),
                'execution_time': exec_time,
            }

    def add_to_history(self, record: dict):
        """添加执行记录"""
        self.history.append(record)
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def get_history(self, limit=10):
        """获取执行历史"""
        return self.history[-limit:]

    def clear_history(self):
        """清空执行历史"""
        self.history = []
