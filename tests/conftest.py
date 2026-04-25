"""共享测试 fixtures"""
import os
import sys
import json
import tempfile
import shutil
import pytest

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture
def tmp_dir():
    """创建临时目录，测试后清理"""
    d = tempfile.mkdtemp(prefix='xiaoli_test_')
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_python_code():
    """安全的示例 Python 代码"""
    return '''
import json
import math

result = math.sqrt(144)
data = {"value": result, "squared": result ** 2}
print(json.dumps(data))
'''


@pytest.fixture
def dangerous_codes():
    """各种危险代码样本"""
    return {
        'os_import': 'import os\nos.system("rm -rf /")',
        'subprocess': 'import subprocess\nsubprocess.run(["ls"])',
        'exec_call': 'exec("import os")',
        'eval_call': 'eval("__import__(\'os\')")',
        'dunder': 'x = (1).__class__.__bases__[0].__subclasses__()',
        'open_file': 'f = open("/etc/passwd")',
        'getattr_bypass': 'getattr(__builtins__, "exec")',
        'socket': 'import socket\ns = socket.socket()',
        'shutil': 'import shutil\nshutil.rmtree("/")',
        'compile': 'compile("import os", "<string>", "exec")',
        'globals': 'globals()["__builtins__"]',
        'breakpoint': 'breakpoint()',
        'del_stmt': 'del some_var',
        'global_stmt': 'global x',
    }


@pytest.fixture
def safe_codes():
    """各种安全代码样本"""
    return {
        'math': 'import math\nresult = math.pi',
        'json': 'import json\nresult = json.dumps({"a": 1})',
        're': 'import re\nresult = re.findall(r"\\d+", "abc123")',
        'datetime': 'from datetime import datetime\nresult = datetime.now().year',
        'collections': 'from collections import Counter\nresult = Counter("aabbc")',
        'list_comp': 'result = [x**2 for x in range(10)]',
        'function': 'def add(a, b): return a + b\nresult = add(3, 4)',
        'string_ops': 'result = "hello world".upper().split()',
        'sorting': 'result = sorted([3,1,2], reverse=True)',
        'fizzbuzz': 'result = ["fizz"*(i%3==0)+"buzz"*(i%5==0) or str(i) for i in range(1,16)]',
    }


@pytest.fixture
def config_file(tmp_dir):
    """创建临时配置文件"""
    config = {
        "system": {
            "default_engine": "ollama",
            "max_history": 100,
            "code_execution_timeout": 10,
        },
        "api": {
            "engines": {
                "ollama": {"base_url": "http://localhost:11434"},
                "mimo": {"api_key": "test-key", "base_url": "http://test.com"},
            }
        },
        "plugins": {},
    }
    path = os.path.join(tmp_dir, "config.json")
    with open(path, 'w') as f:
        json.dump(config, f)
    return path


@pytest.fixture
def history_dir(tmp_dir):
    """创建临时历史目录"""
    d = os.path.join(tmp_dir, "chat_history")
    os.makedirs(d)
    return d


@pytest.fixture
def plugins_dir(tmp_dir):
    """创建带示例插件的目录"""
    d = os.path.join(tmp_dir, "plugins")
    os.makedirs(d)

    # __init__.py
    with open(os.path.join(d, "__init__.py"), 'w') as f:
        f.write("")

    # 简单插件
    with open(os.path.join(d, "test_plugin.py"), 'w') as f:
        f.write('''
class Plugin:
    def __init__(self):
        self.cli = None

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "test_tool",
            "description": "A test tool",
            "keywords": ["test"],
        }

    def get_mcp_definition(self):
        return {
            "name": "test_tool",
            "description": "A test tool",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string"},
                },
                "required": ["operation"]
            }
        }

    def convert_mcp_args(self, arguments):
        return arguments.get("operation", "")

    def handle(self, args):
        return f"test result: {args}"
''')

    return d


@pytest.fixture
def skills_dir(tmp_dir):
    """创建带示例 skill 的目录"""
    d = os.path.join(tmp_dir, "skills")
    os.makedirs(d)

    with open(os.path.join(d, "__init__.py"), 'w') as f:
        f.write("")

    with open(os.path.join(d, "test_skill.py"), 'w') as f:
        f.write('''
class Skill:
    def __init__(self):
        self.cli = None

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "test_skill",
            "description": "A test skill",
            "keywords": ["test", "skill"],
        }

    def handle(self, args):
        return f"skill result: {args}"
''')

    return d
