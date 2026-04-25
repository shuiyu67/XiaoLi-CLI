"""
工程化自动化插件 - 代码质量检查、格式化、测试运行
"""
import os
import subprocess
import json
import re
from typing import Tuple


class Plugin:
    """工程化工具 - lint、format、test、build 自动化"""

    def __init__(self):
        self.usage = """工程化自动化工具

操作类型:
  lint [目录] [文件模式]       - 代码质量检查 (ruff/flake8/pylint)
  format [目录] [文件模式]     - 代码格式化 (black/ruff)
  test [目录] [参数]           - 运行测试 (pytest)
  build [命令]                 - 构建项目
  deps                         - 检查依赖 (pip list --outdated)
  deps-check                   - 安全漏洞检查
  pre-commit                   - 运行 pre-commit 检查
  info                         - 项目信息摘要
  init [类型]                  - 初始化项目结构 (python/web/cli)
"""
        self.cli = None

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "auto_engineer",
            "description": "工程化自动化 - lint/format/test/build/deps 一键执行",
            "keywords": ["lint", "format", "test", "build", "代码质量", "格式化", "测试", "构建"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "auto_engineer",
            "description": "工程化自动化工具",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["lint", "format", "test", "build", "deps", "deps-check", "pre-commit", "info", "init"],
                        "description": "操作类型"
                    },
                    "target": {
                        "type": "string",
                        "description": "目标目录或命令"
                    },
                    "options": {
                        "type": "string",
                        "description": "额外选项"
                    }
                },
                "required": ["operation"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        target = arguments.get("target", "")
        options = arguments.get("options", "")
        return f"{op} {target} {options}".strip()

    def handle(self, args: str) -> str:
        parts = args.strip().split(maxsplit=2)
        if not parts:
            return self.usage

        op = parts[0].lower()
        target = parts[1] if len(parts) > 1 else "."
        options = parts[2] if len(parts) > 2 else ""

        handlers = {
            "lint": self._lint,
            "format": self._format,
            "test": self._test,
            "build": self._build,
            "deps": self._deps,
            "deps-check": self._deps_check,
            "pre-commit": self._pre_commit,
            "info": self._info,
            "init": self._init_project,
        }

        handler = handlers.get(op)
        if not handler:
            return f"错误: 不支持的操作 '{op}'"

        try:
            return handler(target, options)
        except Exception as e:
            return f"执行错误: {e}"

    def _run(self, cmd: str, cwd: str = None, timeout: int = 60) -> Tuple[bool, str]:
        """执行命令"""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=cwd or os.getcwd(), timeout=timeout
            )
            output = result.stdout
            if result.stderr:
                output += "\n" + result.stderr
            return result.returncode == 0, output.strip()
        except subprocess.TimeoutExpired:
            return False, f"命令超时 ({timeout}s)"
        except Exception as e:
            return False, str(e)

    def _find_tool(self, *tools) -> str:
        """查找可用的工具"""
        for tool in tools:
            # 检查 pip 包
            mod_name = tool.replace("-", "_")
            ok, _ = self._run(f"python3 -c 'import {mod_name}'", timeout=5)
            if ok:
                return tool
            # 检查命令行
            ok, _ = self._run(f"which {tool}", timeout=5)
            if ok:
                return tool
        return None

    def _lint(self, target: str, options: str) -> str:
        """代码质量检查"""
        # 尝试 ruff > flake8 > pylint
        tool = self._find_tool("ruff", "flake8")
        if not tool:
            return "❌ 未安装 lint 工具。安装: pip install ruff"

        if tool == "ruff":
            cmd = f"ruff check {target} {options}"
        else:
            cmd = f"flake8 {target} {options}"

        ok, output = self._run(cmd, timeout=120)
        if not output:
            return f"✅ lint 检查通过 ({tool})"

        # 统计问题数
        lines = output.split('\n')
        error_count = len([l for l in lines if l.strip() and not l.startswith(' ')])
        status = "❌" if not ok else "⚠️"

        return f"{status} lint ({tool}): {error_count} 个问题\n\n{output[:2000]}"

    def _format(self, target: str, options: str) -> str:
        """代码格式化"""
        tool = self._find_tool("ruff", "black")
        if not tool:
            return "❌ 未安装格式化工具。安装: pip install ruff"

        if tool == "ruff":
            cmd = f"ruff format {target} {options}"
        else:
            cmd = f"black {target} {options}"

        ok, output = self._run(cmd, timeout=120)
        return f"{'✅' if ok else '❌'} 格式化 ({tool})\n{output[:1000]}"

    def _test(self, target: str, options: str) -> str:
        """运行测试"""
        # 检查 pytest
        tool = self._find_tool("pytest")
        if not tool:
            # 回退到 unittest
            ok, output = self._run(f"python3 -m pytest {target} {options} -v", timeout=120)
        else:
            ok, output = self._run(f"pytest {target} {options} -v", timeout=120)

        if not ok and "no tests ran" in output.lower():
            return f"⚠️ 未找到测试文件\n{output[:1000]}"

        # 提取摘要
        for line in output.split('\n'):
            if 'passed' in line or 'failed' in line or 'error' in line:
                return f"{'✅' if ok else '❌'} 测试结果\n{line}\n\n{output[:2000]}"

        return f"{'✅' if ok else '❌'} 测试\n{output[:2000]}"

    def _build(self, target: str, options: str) -> str:
        """构建项目"""
        if not target or target == ".":
            # 自动检测构建系统
            if os.path.exists("Makefile"):
                cmd = "make"
            elif os.path.exists("setup.py"):
                cmd = "python3 setup.py build"
            elif os.path.exists("pyproject.toml"):
                cmd = "python3 -m build"
            elif os.path.exists("package.json"):
                cmd = "npm run build"
            else:
                return "❌ 未找到构建配置 (Makefile/setup.py/pyproject.toml/package.json)"
        else:
            cmd = target

        ok, output = self._run(cmd, timeout=300)
        return f"{'✅' if ok else '❌'} 构建: {cmd}\n{output[:2000]}"

    def _deps(self, target: str, options: str) -> str:
        """检查依赖"""
        ok, output = self._run("pip list --outdated --format=json", timeout=30)
        if not ok:
            return f"❌ 检查依赖失败\n{output}"

        try:
            outdated = json.loads(output)
            if not outdated:
                return "✅ 所有依赖都是最新版本"

            lines = [f"📦 {len(outdated)} 个依赖可更新:\n"]
            for pkg in outdated[:20]:
                name = pkg.get('name', '?')
                current = pkg.get('version', '?')
                latest = pkg.get('latest_version', '?')
                lines.append(f"  {name:30} {current:12} → {latest}")

            if len(outdated) > 20:
                lines.append(f"\n  ... 还有 {len(outdated) - 20} 个")

            return '\n'.join(lines)
        except json.JSONDecodeError:
            return f"📦 依赖状态:\n{output[:2000]}"

    def _deps_check(self, target: str, options: str) -> str:
        """安全漏洞检查"""
        tool = self._find_tool("pip-audit", "safety")
        if not tool:
            return "❌ 未安装安全检查工具。安装: pip install pip-audit"

        if tool == "pip-audit":
            cmd = "pip-audit"
        else:
            cmd = "safety check"

        ok, output = self._run(cmd, timeout=60)
        return f"{'✅' if ok else '⚠️'} 安全检查 ({tool})\n{output[:2000]}"

    def _pre_commit(self, target: str, options: str) -> str:
        """运行 pre-commit"""
        ok, output = self._run("pre-commit run --all-files", timeout=120)
        return f"{'✅' if ok else '❌'} pre-commit\n{output[:2000]}"

    def _info(self, target: str, options: str) -> str:
        """项目信息摘要"""
        info = []

        # 检测项目类型
        files = os.listdir(target or ".")
        project_type = "未知"
        if "pyproject.toml" in files:
            project_type = "Python (pyproject.toml)"
        elif "setup.py" in files:
            project_type = "Python (setup.py)"
        elif "package.json" in files:
            project_type = "Node.js"
        elif "Cargo.toml" in files:
            project_type = "Rust"
        elif "go.mod" in files:
            project_type = "Go"

        info.append(f"📁 项目类型: {project_type}")

        # Python 版本
        ok, ver = self._run("python3 --version", timeout=5)
        if ok:
            info.append(f"🐍 Python: {ver}")

        # 依赖数
        ok, req = self._run("pip list --format=json", timeout=10)
        if ok:
            try:
                deps = json.loads(req)
                info.append(f"📦 依赖: {len(deps)} 个")
            except:
                pass

        # Git 状态
        ok, git = self._run("git log --oneline -1", timeout=5)
        if ok:
            info.append(f"🔀 最新提交: {git}")

        ok, branch = self._run("git branch --show-current", timeout=5)
        if ok:
            info.append(f"🌿 分支: {branch}")

        # 代码统计
        ok, stats = self._run("find . -name '*.py' -not -path './.git/*' | wc -l", timeout=10)
        if ok:
            info.append(f"📄 Python 文件: {stats.strip()} 个")

        # 测试文件
        ok, tests = self._run("find . -name 'test_*.py' -o -name '*_test.py' | wc -l", timeout=10)
        if ok:
            info.append(f"🧪 测试文件: {tests.strip()} 个")

        return '\n'.join(info)

    def _init_project(self, target: str, options: str) -> str:
        """初始化项目结构"""
        project_type = target if target != "." else "python"

        if project_type == "python":
            dirs = ["src", "tests", "docs"]
            files = {
                "pyproject.toml": '[project]\nname = "my-project"\nversion = "0.1.0"\n',
                "README.md": "# My Project\n",
                ".gitignore": "__pycache__/\n*.pyc\n.venv/\n",
                "tests/__init__.py": "",
                "src/__init__.py": "",
            }
        elif project_type == "web":
            dirs = ["src", "public", "tests"]
            files = {
                "package.json": '{\n  "name": "my-project",\n  "version": "1.0.0"\n}\n',
                "README.md": "# My Project\n",
                ".gitignore": "node_modules/\ndist/\n",
            }
        else:
            return f"❌ 不支持的项目类型: {project_type}。支持: python, web"

        created = []
        for d in dirs:
            if not os.path.exists(d):
                os.makedirs(d)
                created.append(f"📁 {d}/")

        for f, content in files.items():
            if not os.path.exists(f):
                os.makedirs(os.path.dirname(f) or ".", exist_ok=True)
                with open(f, 'w') as fp:
                    fp.write(content)
                created.append(f"📄 {f}")

        return f"✅ 已初始化 {project_type} 项目\n" + '\n'.join(created)
