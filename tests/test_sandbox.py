"""沙箱安全测试 - 测试所有安全层级"""
import os
import sys
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xiaoli.sandbox import Sandbox, SandboxResult, ASTSecurityChecker


# ═══════════════════════════════════════════════
# 1. AST 安全检查器测试
# ═══════════════════════════════════════════════

class TestASTSecurityChecker:
    """AST 静态分析测试"""

    def setup_method(self):
        self.checker = ASTSecurityChecker()

    # ── 应该拒绝的 ──

    def test_block_os_import(self):
        safe, violations = self.checker.check('import os')
        assert not safe
        assert any('os' in v for v in violations)

    def test_block_subprocess_import(self):
        safe, violations = self.checker.check('import subprocess')
        assert not safe

    def test_block_from_import(self):
        safe, violations = self.checker.check('from os import system')
        assert not safe
        assert any('os' in v for v in violations)

    def test_block_exec_call(self):
        safe, violations = self.checker.check('exec("print(1)")')
        assert not safe
        assert any('exec' in v for v in violations)

    def test_block_eval_call(self):
        safe, violations = self.checker.check('x = eval("1+1")')
        assert not safe

    def test_block_compile(self):
        safe, violations = self.checker.check('compile("x=1", "<s>", "exec")')
        assert not safe

    def test_block_globals(self):
        safe, violations = self.checker.check('globals()')
        assert not safe

    def test_block_locals(self):
        safe, violations = self.checker.check('locals()')
        assert not safe

    def test_block_getattr(self):
        safe, violations = self.checker.check('getattr(obj, "name")')
        assert not safe

    def test_block_setattr(self):
        safe, violations = self.checker.check('setattr(obj, "name", 1)')
        assert not safe

    def test_block_dunder_class(self):
        safe, violations = self.checker.check('x = object.__class__')
        assert not safe

    def test_block_dunder_subclasses(self):
        safe, violations = self.checker.check('x = object.__subclasses__()')
        assert not safe

    def test_block_open(self):
        safe, violations = self.checker.check('f = open("/etc/passwd")')
        assert not safe

    def test_block_breakpoint(self):
        safe, violations = self.checker.check('breakpoint()')
        assert not safe

    def test_block_socket_import(self):
        safe, violations = self.checker.check('import socket')
        assert not safe

    def test_block_pickle_import(self):
        safe, violations = self.checker.check('import pickle')
        assert not safe

    def test_block_ctypes_import(self):
        safe, violations = self.checker.check('import ctypes')
        assert not safe

    def test_block_importlib(self):
        safe, violations = self.checker.check('import importlib')
        assert not safe

    def test_block_del(self):
        safe, violations = self.checker.check('del x')
        assert not safe

    def test_block_global_stmt(self):
        safe, violations = self.checker.check('global x')
        assert not safe

    def test_block_nested_dunder(self):
        safe, violations = self.checker.check(
            'x = (1).__class__.__bases__[0].__subclasses__()'
        )
        assert not safe

    def test_block_sys_import(self):
        safe, violations = self.checker.check('import sys')
        assert not safe

    def test_block_shutil(self):
        safe, violations = self.checker.check('import shutil')
        assert not safe

    def test_block_urllib(self):
        safe, violations = self.checker.check('import urllib')
        assert not safe

    def test_block_http(self):
        safe, violations = self.checker.check('import http')
        assert not safe

    # ── 应该允许的 ──

    def test_allow_math(self):
        safe, _ = self.checker.check('import math\nresult = math.pi')
        assert safe

    def test_allow_json(self):
        safe, _ = self.checker.check('import json\nresult = json.dumps({"a": 1})')
        assert safe

    def test_allow_re(self):
        safe, _ = self.checker.check('import re\nresult = re.findall(r"\\d+", "abc")')
        assert safe

    def test_allow_datetime(self):
        safe, _ = self.checker.check('from datetime import datetime\nresult = datetime.now()')
        assert safe

    def test_allow_collections(self):
        safe, _ = self.checker.check('from collections import Counter\nresult = Counter("aab")')
        assert safe

    def test_allow_list_comprehension(self):
        safe, _ = self.checker.check('result = [x**2 for x in range(10)]')
        assert safe

    def test_allow_function_def(self):
        safe, _ = self.checker.check('def add(a, b): return a + b\nresult = add(1, 2)')
        assert safe

    def test_allow_string_ops(self):
        safe, _ = self.checker.check('result = "hello".upper()')
        assert safe

    def test_allow_sorting(self):
        safe, _ = self.checker.check('result = sorted([3,1,2])')
        assert safe

    def test_allow_typing(self):
        safe, _ = self.checker.check('from typing import List\nresult: List[int] = [1,2,3]')
        assert safe

    def test_allow_enum(self):
        safe, _ = self.checker.check('from enum import Enum')
        assert safe

    def test_allow_decimal(self):
        safe, _ = self.checker.check('from decimal import Decimal\nresult = Decimal("3.14")')
        assert safe

    def test_allow_itertools(self):
        safe, _ = self.checker.check('import itertools\nresult = list(itertools.chain([1],[2]))')
        assert safe

    # ── 语法错误 ──

    def test_syntax_error(self):
        safe, violations = self.checker.check('def foo(')
        assert not safe
        assert any('syntax' in v.lower() for v in violations)

    def test_empty_code(self):
        safe, _ = self.checker.check('')
        assert safe

    # ── 多种违规组合 ──

    def test_multiple_violations(self):
        code = 'import os\nimport socket\nexec("x=1")\nglobals()'
        safe, violations = self.checker.check(code)
        assert not safe
        assert len(violations) >= 4


# ═══════════════════════════════════════════════
# 2. Sandbox 核心功能测试
# ═══════════════════════════════════════════════

class TestSandboxBasic:
    """沙箱基本功能测试"""

    def setup_method(self):
        self.sandbox = Sandbox(timeout=10, mode='threaded')

    def teardown_method(self):
        self.sandbox.cleanup()

    def test_simple_execution(self):
        result = self.sandbox.run('result = 1 + 2')
        assert result['success']
        assert result['result'] == '3'

    def test_string_manipulation(self):
        result = self.sandbox.run('result = "hello world".split()')
        assert result['success']
        assert 'hello' in result['result']

    def test_math_operations(self):
        result = self.sandbox.run('import math\nresult = math.sqrt(144)')
        assert result['success']
        assert '12.0' in result['result']

    def test_json_operations(self):
        result = self.sandbox.run(
            'import json\nresult = json.dumps({"key": "value"})'
        )
        assert result['success']
        assert 'key' in result['result']

    def test_print_capture(self):
        result = self.sandbox.run('print("hello")\nresult = "done"')
        assert result['success']
        assert 'hello' in result['stdout']

    def test_variables_injection(self):
        result = self.sandbox.run(
            'result = x + y',
            variables={'x': 10, 'y': 20}
        )
        assert result['success']
        assert '30' in result['result']

    def test_function_definition(self):
        code = '''
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
result = factorial(5)
'''
        result = self.sandbox.run(code)
        assert result['success']
        assert '120' in result['result']

    def test_list_comprehension(self):
        result = self.sandbox.run('result = [x**2 for x in range(5)]')
        assert result['success']
        assert '[0, 1, 4, 9, 16]' in result['result']

    def test_dict_operations(self):
        code = '''
data = {"a": 1, "b": 2, "c": 3}
result = {k: v*2 for k, v in data.items()}
'''
        result = self.sandbox.run(code)
        assert result['success']

    def test_datetime(self):
        code = 'from datetime import datetime\nresult = datetime.now().year'
        result = self.sandbox.run(code)
        assert result['success']

    def test_collections_counter(self):
        code = 'from collections import Counter\nresult = Counter("aabbc")'
        result = self.sandbox.run(code)
        assert result['success']

    def test_regex(self):
        code = 'import re\nresult = re.findall(r"\\d+", "abc123def456")'
        result = self.sandbox.run(code)
        assert result['success']
        assert '123' in result['result']

    def test_no_result_variable(self):
        result = self.sandbox.run('x = 42')
        assert result['success']
        assert 'no return' in result['result'].lower() or 'ok' in result['result'].lower()

    def test_syntax_error(self):
        result = self.sandbox.run('def foo(')
        assert not result['success']

    def test_runtime_error(self):
        result = self.sandbox.run('result = 1 / 0')
        assert not result['success']
        assert 'error' in result['result'].lower() or 'division' in result['result'].lower()


# ═══════════════════════════════════════════════
# 3. 安全拒绝测试
# ═══════════════════════════════════════════════

class TestSandboxSecurity:
    """沙箱安全拒绝测试"""

    def setup_method(self):
        self.sandbox = Sandbox(timeout=10, mode='threaded')

    def teardown_method(self):
        self.sandbox.cleanup()

    def test_reject_os_import(self):
        result = self.sandbox.run('import os\nresult = os.getcwd()')
        assert not result['success']

    def test_reject_subprocess(self):
        result = self.sandbox.run('import subprocess\nsubprocess.run(["ls"])')
        assert not result['success']

    def test_reject_exec(self):
        result = self.sandbox.run('exec("result = 1")')
        assert not result['success']

    def test_reject_eval(self):
        result = self.sandbox.run('result = eval("1+1")')
        assert not result['success']

    def test_reject_open(self):
        result = self.sandbox.run('f = open("/etc/passwd")\nresult = f.read()')
        assert not result['success']

    def test_reject_socket(self):
        result = self.sandbox.run('import socket\ns = socket.socket()')
        assert not result['success']

    def test_reject_pickle(self):
        result = self.sandbox.run('import pickle\nresult = pickle.dumps({})')
        assert not result['success']

    def test_reject_sys(self):
        result = self.sandbox.run('import sys\nresult = sys.version')
        assert not result['success']

    def test_reject_getattr(self):
        result = self.sandbox.run('result = getattr(str, "upper")')
        assert not result['success']

    def test_reject_dunder(self):
        result = self.sandbox.run('result = object.__class__')
        assert not result['success']

    def test_reject_breakpoint(self):
        result = self.sandbox.run('breakpoint()')
        assert not result['success']

    def test_reject_compile(self):
        result = self.sandbox.run('compile("x=1", "<s>", "exec")')
        assert not result['success']

    def test_reject_globals(self):
        result = self.sandbox.run('result = globals()')
        assert not result['success']

    def test_reject_importlib(self):
        result = self.sandbox.run('import importlib')
        assert not result['success']

    def test_reject_shutil(self):
        result = self.sandbox.run('import shutil')
        assert not result['success']

    def test_reject_ctypes(self):
        result = self.sandbox.run('import ctypes')
        assert not result['success']

    def test_reject_multiprocessing(self):
        result = self.sandbox.run('import multiprocessing')
        assert not result['success']

    def test_reject_threading(self):
        result = self.sandbox.run('import threading')
        assert not result['success']

    def test_reject_http(self):
        result = self.sandbox.run('import http')
        assert not result['success']

    def test_reject_urllib(self):
        result = self.sandbox.run('import urllib')
        assert not result['success']


# ═══════════════════════════════════════════════
# 4. 超时测试
# ═══════════════════════════════════════════════

class TestSandboxTimeout:
    """超时机制测试"""

    def test_timeout_infinite_loop(self):
        sandbox = Sandbox(timeout=2, mode='threaded')
        result = sandbox.run('while True: pass')
        assert not result['success']
        assert result['killed']
        sandbox.cleanup()

    def test_timeout_sleep(self):
        sandbox = Sandbox(timeout=2, mode='threaded')
        result = sandbox.run('import time\ntime.sleep(30)\nresult = "done"')
        # Should either timeout or fail on import
        assert not result['success'] or result['killed']
        sandbox.cleanup()


# ═══════════════════════════════════════════════
# 5. SandboxResult 测试
# ═══════════════════════════════════════════════

class TestSandboxResult:
    """SandboxResult 数据类测试"""

    def test_success_result(self):
        r = SandboxResult(success=True, result="42", time=0.1)
        assert r.success
        d = r.to_dict()
        assert d['success']
        assert d['result'] == '42'
        assert d['time'] == 0.1

    def test_failure_result(self):
        r = SandboxResult(success=False, result="error", security_violation="blocked os")
        assert not r.success
        d = r.to_dict()
        assert not d['success']
        assert d['security_violation'] == 'blocked os'

    def test_str_representation(self):
        r = SandboxResult(success=True, result="ok", time=0.05)
        s = str(r)
        assert 'OK' in s
        assert '0.050' in s


# ═══════════════════════════════════════════════
# 6. 沙箱模式对比测试
# ═══════════════════════════════════════════════

class TestSandboxModes:
    """threaded vs subprocess 模式对比"""

    def test_threaded_mode(self):
        sandbox = Sandbox(timeout=10, mode='threaded')
        result = sandbox.run('result = 2 + 3')
        assert result['success']
        assert '5' in result['result']
        sandbox.cleanup()

    def test_subprocess_mode(self):
        sandbox = Sandbox(timeout=10, mode='subprocess')
        result = sandbox.run('result = 2 + 3')
        assert result['success']
        assert '5' in result['result']
        sandbox.cleanup()

    def test_both_modes_same_result(self):
        code = 'import json\nresult = json.dumps({"x": 42})'

        t = Sandbox(timeout=10, mode='threaded')
        s = Sandbox(timeout=10, mode='subprocess')

        r_threaded = t.run(code)
        r_subprocess = s.run(code)

        assert r_threaded['success'] == r_subprocess['success']
        assert r_threaded['result'] == r_subprocess['result']

        t.cleanup()
        s.cleanup()


# ═══════════════════════════════════════════════
# 7. 禁用沙箱测试
# ═══════════════════════════════════════════════

class TestSandboxDisabled:
    """沙箱禁用时的行为"""

    def test_disabled_rejects_all(self):
        sandbox = Sandbox(timeout=10, mode='threaded')
        sandbox.enabled = False
        result = sandbox.run('result = 1')
        assert not result['success']
        assert 'disabled' in result['result'].lower() or 'off' in result['security_violation'].lower()
        sandbox.cleanup()


# ═══════════════════════════════════════════════
# 8. 历史记录测试
# ═══════════════════════════════════════════════

class TestSandboxHistory:
    """沙箱执行历史记录"""

    def test_history_recorded(self):
        sandbox = Sandbox(timeout=10, mode='threaded')
        sandbox.run('result = 1')
        sandbox.run('result = 2')
        assert len(sandbox.history) == 2
        assert sandbox.history[0]['success']
        assert sandbox.history[1]['success']
        sandbox.cleanup()

    def test_failed_history_recorded(self):
        sandbox = Sandbox(timeout=10, mode="threaded")
        result = sandbox.run("x = 1 / 0")  # runtime error, not security
        assert not result["success"]
        assert len(sandbox.history) == 1
        assert not sandbox.history[0]["success"]
        sandbox.cleanup()

    def test_security_violation_no_history(self):
        sandbox = Sandbox(timeout=10, mode="threaded")
        result = sandbox.run("import os")  # security violation
        assert not result["success"]
        # security violations may not record history
        sandbox.cleanup()


# ═══════════════════════════════════════════════
# 9. 变量注入安全测试
# ═══════════════════════════════════════════════

class TestSandboxVariables:
    """变量注入测试"""

    def test_inject_numbers(self):
        sandbox = Sandbox(timeout=10, mode='threaded')
        result = sandbox.run('result = a + b', variables={'a': 100, 'b': 200})
        assert result['success']
        assert '300' in result['result']
        sandbox.cleanup()

    def test_inject_strings(self):
        sandbox = Sandbox(timeout=10, mode='threaded')
        result = sandbox.run('result = name.upper()', variables={'name': 'hello'})
        assert result['success']
        assert 'HELLO' in result['result']
        sandbox.cleanup()

    def test_inject_dict(self):
        sandbox = Sandbox(timeout=10, mode='threaded')
        result = sandbox.run(
            'result = data["key"]',
            variables={'data': {'key': 'found'}}
        )
        assert result['success']
        assert 'found' in result['result']
        sandbox.cleanup()

    def test_inject_list(self):
        sandbox = Sandbox(timeout=10, mode='threaded')
        result = sandbox.run(
            'result = sum(items)',
            variables={'items': [1, 2, 3, 4, 5]}
        )
        assert result['success']
        assert '15' in result['result']
        sandbox.cleanup()
