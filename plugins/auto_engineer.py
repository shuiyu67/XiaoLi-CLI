"""
工程化工具插件 - 代码质量 + 项目分析
合并原 auto_engineer + project_analyzer，消除重复
"""
import os
import ast
import re
import json
import subprocess
from typing import Tuple, List


class Plugin:
    """工程化工具 - lint/format/test/build + 代码分析"""

    def __init__(self):
        self.usage = """工程化与分析工具

质量检查:
  lint [目录] [文件模式]       - 代码质量检查 (ruff/flake8)
  format [目录] [文件模式]     - 代码格式化 (ruff/black)
  test [目录] [参数]           - 运行测试 (pytest)
  build [命令]                 - 构建项目
  deps                         - 检查过时依赖
  deps-check                   - 安全漏洞检查
  pre-commit                   - 运行 pre-commit 检查

项目分析:
  complexity [目录]            - 圈复杂度分析
  duplicates [目录]            - 重复代码检测
  security [目录]              - 安全风险扫描
  metrics [目录]               - 代码质量指标
  suggest [目录]               - 改进建议
  info                         - 项目信息摘要
  init [类型]                  - 初始化项目 (python/web)
"""
        self.cli = None

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "auto_engineer",
            "description": "工程化工具 - lint/format/test/build + 代码复杂度/安全/质量分析",
            "keywords": ["lint", "format", "test", "build", "代码质量", "格式化", "测试",
                         "复杂度", "安全", "分析", "依赖", "项目"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "auto_engineer",
            "description": "工程化与分析工具",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string"},
                    "target": {"type": "string"},
                    "options": {"type": "string"}
                },
                "required": ["operation"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        target = arguments.get("target", "")
        return f"{op} {target}".strip()

    # ── 工具方法 ──

    def _run(self, cmd: str, cwd: str = None, timeout: int = 60) -> Tuple[bool, str]:
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=cwd or os.getcwd(), timeout=timeout
            )
            output = result.stdout + (("\n" + result.stderr) if result.stderr else "")
            return result.returncode == 0, output.strip()
        except subprocess.TimeoutExpired:
            return False, f"命令超时 ({timeout}s)"
        except Exception as e:
            return False, str(e)

    def _find_tool(self, *tools) -> str:
        for tool in tools:
            mod = tool.replace("-", "_")
            ok, _ = self._run(f"python3 -c 'import {mod}'", timeout=5)
            if ok:
                return tool
            ok, _ = self._run(f"which {tool}", timeout=5)
            if ok:
                return tool
        return None

    def _walk_py(self, target: str) -> List[str]:
        files = []
        skip = {'.git', '__pycache__', '.venv', 'venv', 'node_modules'}
        for root, dirs, fnames in os.walk(target):
            dirs[:] = [d for d in dirs if d not in skip]
            for f in fnames:
                if f.endswith('.py'):
                    files.append(os.path.join(root, f))
        return files

    # ── 路由 ──

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
            "complexity": self._complexity,
            "duplicates": self._duplicates,
            "security": self._security,
            "metrics": self._metrics,
            "suggest": self._suggest,
            "info": self._info,
            "init": self._init_project,
        }

        handler = handlers.get(op)
        if not handler:
            return f"错误：不支持的操作 '{op}'"
        try:
            return handler(target, options)
        except Exception as e:
            return f"执行错误: {e}"

    # ══════════════════════════════════════
    #  质量检查
    # ══════════════════════════════════════

    def _lint(self, target: str, options: str) -> str:
        tool = self._find_tool("ruff", "flake8")
        if not tool:
            return "❌ 未安装 lint 工具。安装: pip install ruff"
        cmd = f"ruff check {target} {options}" if tool == "ruff" else f"flake8 {target} {options}"
        ok, output = self._run(cmd, timeout=120)
        if not output:
            return f"✅ lint 检查通过 ({tool})"
        lines = output.split('\n')
        count = len([l for l in lines if l.strip() and not l.startswith(' ')])
        return f"{'❌' if not ok else '⚠️'} lint ({tool}): {count} 个问题\n\n{output[:2000]}"

    def _format(self, target: str, options: str) -> str:
        tool = self._find_tool("ruff", "black")
        if not tool:
            return "❌ 未安装格式化工具。安装: pip install ruff"
        cmd = f"ruff format {target} {options}" if tool == "ruff" else f"black {target} {options}"
        ok, output = self._run(cmd, timeout=120)
        return f"{'✅' if ok else '❌'} 格式化 ({tool})\n{output[:1000]}"

    def _test(self, target: str, options: str) -> str:
        ok, output = self._run(f"pytest {target} {options} -v", timeout=120)
        if not ok and "no tests ran" in output.lower():
            return f"⚠️ 未找到测试文件\n{output[:1000]}"
        for line in output.split('\n'):
            if 'passed' in line or 'failed' in line:
                return f"{'✅' if ok else '❌'} 测试\n{line}\n\n{output[:2000]}"
        return f"{'✅' if ok else '❌'} 测试\n{output[:2000]}"

    def _build(self, target: str, options: str) -> str:
        if not target or target == ".":
            if os.path.exists("Makefile"):
                cmd = "make"
            elif os.path.exists("pyproject.toml"):
                cmd = "python3 -m build"
            elif os.path.exists("package.json"):
                cmd = "npm run build"
            else:
                return "❌ 未找到构建配置"
        else:
            cmd = target
        ok, output = self._run(cmd, timeout=300)
        return f"{'✅' if ok else '❌'} 构建: {cmd}\n{output[:2000]}"

    def _deps(self, target: str, options: str) -> str:
        ok, output = self._run("pip list --outdated --format=json", timeout=30)
        if not ok:
            return f"❌ 检查失败\n{output}"
        try:
            outdated = json.loads(output)
            if not outdated:
                return "✅ 所有依赖都是最新版本"
            lines = [f"📦 {len(outdated)} 个依赖可更新:\n"]
            for pkg in outdated[:20]:
                lines.append(f"  {pkg['name']:30} {pkg['version']:12} → {pkg['latest_version']}")
            return '\n'.join(lines)
        except json.JSONDecodeError:
            return f"📦 依赖状态:\n{output[:2000]}"

    def _deps_check(self, target: str, options: str) -> str:
        tool = self._find_tool("pip-audit", "safety")
        if not tool:
            return "❌ 未安装安全检查工具。安装: pip install pip-audit"
        cmd = "pip-audit" if tool == "pip-audit" else "safety check"
        ok, output = self._run(cmd, timeout=60)
        return f"{'✅' if ok else '⚠️'} 安全检查 ({tool})\n{output[:2000]}"

    def _pre_commit(self, target: str, options: str) -> str:
        ok, output = self._run("pre-commit run --all-files", timeout=120)
        return f"{'✅' if ok else '❌'} pre-commit\n{output[:2000]}"

    # ══════════════════════════════════════
    #  项目分析
    # ══════════════════════════════════════

    def _complexity(self, target: str, options: str) -> str:
        files = self._walk_py(target)
        results = []
        for fp in files:
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
            except Exception:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    complexity = 1
                    for child in ast.walk(node):
                        if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                            complexity += 1
                        elif isinstance(child, ast.BoolOp):
                            complexity += len(child.values) - 1
                    if complexity > 5:
                        rel = os.path.relpath(fp, target)
                        results.append((rel, node.lineno, node.name, complexity))

        if not results:
            return "✅ 所有函数复杂度正常 (≤5)"

        results.sort(key=lambda x: x[3], reverse=True)
        lines = [f"⚠️ 高复杂度函数 ({len(results)} 个):\n"]
        for file, line, func, c in results[:20]:
            icon = "🔴" if c > 10 else "🟡"
            lines.append(f"  {icon} {file}:{line} {func}() 复杂度={c}")
        return '\n'.join(lines)

    def _duplicates(self, target: str, options: str) -> str:
        files = self._walk_py(target)
        func_defs = {}
        for fp in files:
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
            except Exception:
                continue
            rel = os.path.relpath(fp, target)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_defs.setdefault(node.name, []).append(f"{rel}:{node.lineno}")

        dupes = {k: v for k, v in func_defs.items() if len(v) > 1}
        if not dupes:
            return "✅ 没有重复函数名"
        lines = [f"⚠️ 重复函数名 ({len(dupes)} 个):\n"]
        for name, locs in sorted(dupes.items(), key=lambda x: -len(x[1])):
            lines.append(f"  {name} ({len(locs)} 处):")
            for loc in locs[:5]:
                lines.append(f"    • {loc}")
        return '\n'.join(lines)

    def _security(self, target: str, options: str) -> str:
        files = self._walk_py(target)
        patterns = [
            (r'\beval\s*\(', 'eval() - 代码注入', 'HIGH'),
            (r'\bexec\s*\(', 'exec() - 代码注入', 'HIGH'),
            (r'subprocess\.call\s*\(\s*shell\s*=\s*True', 'shell=True - 命令注入', 'HIGH'),
            (r'pickle\.loads?\s*\(', 'pickle 反序列化', 'HIGH'),
            (r'password\s*=\s*["\']', '硬编码密码', 'HIGH'),
            (r'api_key\s*=\s*["\']', '硬编码 API Key', 'HIGH'),
        ]
        risks = []
        for fp in files:
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f, 1):
                        for pat, desc, level in patterns:
                            if re.search(pat, line, re.IGNORECASE):
                                rel = os.path.relpath(fp, target)
                                risks.append((rel, i, level, desc, line.strip()))
            except Exception:
                continue

        if not risks:
            return "✅ 没有发现安全风险"
        lines = [f"🔒 安全风险 ({len(risks)} 个):\n"]
        for file, line, level, desc, code in risks[:20]:
            lines.append(f"  {'🔴' if level == 'HIGH' else '🟡'} {file}:{line} [{level}] {desc}")
            lines.append(f"      {code[:60]}")
        return '\n'.join(lines)

    def _metrics(self, target: str, options: str) -> str:
        files = self._walk_py(target)
        total = blank = comment = code = funcs = classes = max_lines = 0
        long_files = []

        for fp in files:
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except Exception:
                continue
            fl = len(lines)
            total += fl
            max_lines = max(max_lines, fl)
            if fl > 300:
                long_files.append((os.path.relpath(fp, target), fl))
            for line in lines:
                s = line.strip()
                if not s:
                    blank += 1
                elif s.startswith('#'):
                    comment += 1
                else:
                    code += 1
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        funcs += 1
                    elif isinstance(node, ast.ClassDef):
                        classes += 1
            except Exception:
                pass

        rate = comment / max(code, 1) * 100
        lines = [
            f"📊 代码指标 ({target}):\n",
            f"  文件: {len(files)}  |  总行: {total}  |  代码: {code}",
            f"  注释: {comment} ({rate:.1f}%)  |  空行: {blank}",
            f"  函数: {funcs}  |  类: {classes}  |  最大文件: {max_lines} 行",
        ]
        if long_files:
            lines.append(f"\n  ⚠️ 超过 300 行的文件 ({len(long_files)}):")
            for f, l in sorted(long_files, key=lambda x: -x[1])[:5]:
                lines.append(f"    • {f}: {l} 行")
        return '\n'.join(lines)

    def _suggest(self, target: str, options: str) -> str:
        files = os.listdir(target) if os.path.isdir(target) else []
        py_files = self._walk_py(target)
        suggestions = []

        if 'README.md' not in files:
            suggestions.append("📝 添加 README.md")
        if 'pyproject.toml' not in files:
            suggestions.append("📦 使用 pyproject.toml")
        if '.gitignore' not in files:
            suggestions.append("🚫 添加 .gitignore")

        test_files = [f for f in py_files if 'test' in os.path.basename(f).lower()]
        if not test_files and len(py_files) > 5:
            suggestions.append("🧪 添加单元测试")

        uses_print = sum(1 for f in py_files if 'print(' in open(f, errors='ignore').read())
        uses_log = sum(1 for f in py_files if 'logging' in open(f, errors='ignore').read())
        if uses_print > uses_log and uses_print > 3:
            suggestions.append("📊 考虑用 logging 替代 print")

        return "💡 改进建议:\n" + '\n'.join(f"  {s}" for s in suggestions) if suggestions else "✅ 项目结构良好"

    # ══════════════════════════════════════
    #  项目信息与初始化
    # ══════════════════════════════════════

    def _info(self, target: str, options: str) -> str:
        info = []
        files = os.listdir(target or ".")

        if "pyproject.toml" in files:
            info.append("📁 项目类型: Python (pyproject.toml)")
        elif "setup.py" in files:
            info.append("📁 项目类型: Python (setup.py)")
        elif "package.json" in files:
            info.append("📁 项目类型: Node.js")
        else:
            info.append("📁 项目类型: 未知")

        ok, ver = self._run("python3 --version", timeout=5)
        if ok:
            info.append(f"🐍 Python: {ver}")

        ok, req = self._run("pip list --format=json", timeout=10)
        if ok:
            try:
                info.append(f"📦 依赖: {len(json.loads(req))} 个")
            except Exception:
                pass

        ok, git = self._run("git log --oneline -1", timeout=5)
        if ok:
            info.append(f"🔀 最新提交: {git}")

        ok, branch = self._run("git branch --show-current", timeout=5)
        if ok:
            info.append(f"🌿 分支: {branch}")

        py_count = len([f for f in self._walk_py(target or ".")])
        info.append(f"📄 Python 文件: {py_count}")

        return '\n'.join(info)

    def _init_project(self, target: str, options: str) -> str:
        ptype = target if target != "." else "python"
        if ptype == "python":
            dirs = ["src", "tests", "docs"]
            files = {
                "pyproject.toml": '[project]\nname = "my-project"\nversion = "0.1.0"\n',
                "README.md": "# My Project\n",
                ".gitignore": "__pycache__/\n*.pyc\n.venv/\n",
            }
        elif ptype == "web":
            dirs = ["src", "public", "tests"]
            files = {
                "package.json": '{\n  "name": "my-project",\n  "version": "1.0.0"\n}\n',
                ".gitignore": "node_modules/\ndist/\n",
            }
        else:
            return f"❌ 不支持: {ptype}。支持: python, web"

        created = []
        for d in dirs:
            os.makedirs(d, exist_ok=True)
            created.append(f"📁 {d}/")
        for f, content in files.items():
            if not os.path.exists(f):
                os.makedirs(os.path.dirname(f) or ".", exist_ok=True)
                with open(f, 'w') as fp:
                    fp.write(content)
                created.append(f"📄 {f}")

        return f"✅ 已初始化 {ptype} 项目\n" + '\n'.join(created)
