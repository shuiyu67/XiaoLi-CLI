"""
项目分析插件 - 代码质量分析、依赖分析、架构建议
"""
import os
import ast
import re
import json
from typing import Dict, List, Tuple


class Plugin:
    """项目分析工具 - 深度分析代码质量、依赖关系、架构问题"""

    def __init__(self):
        self.usage = """项目分析工具

操作类型:
  complexity [目录]          - 圈复杂度分析
  imports [文件]             - 依赖关系图
  duplicates [目录]          - 重复代码检测
  todo [目录]                - TODO/FIXME 汇总
  security [目录]            - 安全风险扫描
  metrics [目录]             - 代码质量指标
  suggest [目录]             - 改进建议
"""
        self.cli = None

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "project_analyzer",
            "description": "项目分析工具 - 代码质量、依赖关系、安全扫描、改进建议",
            "keywords": ["分析", "质量", "复杂度", "重复", "安全", "建议", "analyze"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "project_analyzer",
            "description": "项目深度分析工具",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["complexity", "imports", "duplicates", "todo", "security", "metrics", "suggest"],
                        "description": "分析类型"
                    },
                    "target": {
                        "type": "string",
                        "description": "目标目录或文件"
                    }
                },
                "required": ["operation"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        target = arguments.get("target", ".")
        return f"{op} {target}"

    def handle(self, args: str) -> str:
        parts = args.strip().split(maxsplit=1)
        if not parts:
            return self.usage

        op = parts[0].lower()
        target = parts[1] if len(parts) > 1 else "."

        handlers = {
            "complexity": self._complexity,
            "imports": self._imports,
            "duplicates": self._duplicates,
            "todo": self._todo,
            "security": self._security,
            "metrics": self._metrics,
            "suggest": self._suggest,
        }

        handler = handlers.get(op)
        if not handler:
            return f"错误: 不支持的操作 '{op}'"

        try:
            return handler(target)
        except Exception as e:
            return f"分析错误: {e}"

    def _walk_py(self, target: str) -> List[str]:
        """遍历 Python 文件"""
        files = []
        skip = {'.git', '__pycache__', '.venv', 'venv', 'node_modules'}
        for root, dirs, fnames in os.walk(target):
            dirs[:] = [d for d in dirs if d not in skip]
            for f in fnames:
                if f.endswith('.py'):
                    files.append(os.path.join(root, f))
        return files

    def _complexity(self, target: str) -> str:
        """圈复杂度分析"""
        files = self._walk_py(target)
        results = []

        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    source = f.read()
                tree = ast.parse(source)
            except:
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
                        rel = os.path.relpath(filepath, target)
                        results.append({
                            'file': rel,
                            'func': node.name,
                            'line': node.lineno,
                            'complexity': complexity
                        })

        if not results:
            return "✅ 所有函数复杂度正常 (≤5)"

        results.sort(key=lambda x: x['complexity'], reverse=True)
        lines = [f"⚠️ 高复杂度函数 ({len(results)} 个):\n"]
        for r in results[:20]:
            level = "🔴" if r['complexity'] > 10 else "🟡"
            lines.append(f"  {level} {r['file']}:{r['line']} {r['func']}() 复杂度={r['complexity']}")

        return '\n'.join(lines)

    def _imports(self, target: str) -> str:
        """依赖关系分析"""
        if os.path.isfile(target):
            files = [target]
        else:
            files = self._walk_py(target)

        all_imports = {}
        internal_deps = {}

        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
            except:
                continue

            rel = os.path.relpath(filepath, target if os.path.isdir(target) else os.path.dirname(target))
            imports = []

            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            all_imports[rel] = imports

        # 统计
        stdlib = {'os', 'sys', 'json', 're', 'time', 'datetime', 'logging',
                  'threading', 'subprocess', 'pathlib', 'typing', 'collections',
                  'functools', 'itertools', 'abc', 'dataclasses', 'enum',
                  'importlib', 'ast', 'io', 'traceback', 'uuid', 'shutil'}

        third_party = set()
        for imports in all_imports.values():
            for imp in imports:
                root = imp.split('.')[0]
                if root not in stdlib and root not in {os.path.splitext(os.path.basename(f))[0] for f in files}:
                    third_party.add(root)

        lines = [f"📦 依赖分析 ({len(files)} 个文件):\n"]
        lines.append(f"  第三方依赖: {len(third_party)} 个")
        for dep in sorted(third_party):
            lines.append(f"    • {dep}")

        return '\n'.join(lines)

    def _duplicates(self, target: str) -> str:
        """重复代码检测（简单版：检测相同函数名）"""
        files = self._walk_py(target)
        func_defs = {}

        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
            except:
                continue

            rel = os.path.relpath(filepath, target)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    key = node.name
                    if key not in func_defs:
                        func_defs[key] = []
                    func_defs[key].append(f"{rel}:{node.lineno}")

        # 找重复
        duplicates = {k: v for k, v in func_defs.items() if len(v) > 1}

        if not duplicates:
            return "✅ 没有发现重复函数名"

        lines = [f"⚠️ 重复函数名 ({len(duplicates)} 个):\n"]
        for name, locations in sorted(duplicates.items(), key=lambda x: -len(x[1])):
            lines.append(f"  {name} ({len(locations)} 处):")
            for loc in locations[:5]:
                lines.append(f"    • {loc}")

        return '\n'.join(lines)

    def _todo(self, target: str) -> str:
        """TODO/FIXME 汇总"""
        files = self._walk_py(target)
        pattern = re.compile(r'#\s*(TODO|FIXME|HACK|XXX|BUG|NOTE)\b[:\s]*(.*)', re.IGNORECASE)
        results = []

        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f, 1):
                        match = pattern.search(line)
                        if match:
                            rel = os.path.relpath(filepath, target)
                            tag = match.group(1).upper()
                            desc = match.group(2).strip()
                            results.append((rel, i, tag, desc))
            except:
                continue

        if not results:
            return "✅ 没有 TODO/FIXME"

        lines = [f"📝 TODO/FIXME ({len(results)} 个):\n"]
        for file, line, tag, desc in results[:30]:
            icon = {'TODO': '📌', 'FIXME': '🔧', 'HACK': '⚡', 'XXX': '⚠️', 'BUG': '🐛'}.get(tag, '📝')
            lines.append(f"  {icon} {file}:{line} [{tag}] {desc}")

        return '\n'.join(lines)

    def _security(self, target: str) -> str:
        """安全风险扫描"""
        files = self._walk_py(target)
        risks = []

        patterns = [
            (r'\beval\s*\(', '使用 eval() - 代码注入风险', 'HIGH'),
            (r'\bexec\s*\(', '使用 exec() - 代码注入风险', 'HIGH'),
            (r'\b__import__\s*\(', '动态导入 - 潜在风险', 'MEDIUM'),
            (r'subprocess\.call\s*\(\s*shell\s*=\s*True', 'shell=True - 命令注入风险', 'HIGH'),
            (r'pickle\.loads?\s*\(', 'pickle 反序列化 - 代码执行风险', 'HIGH'),
            (r'password\s*=\s*["\']', '硬编码密码', 'HIGH'),
            (r'api_key\s*=\s*["\']', '硬编码 API Key', 'HIGH'),
            (r'secret\s*=\s*["\']', '硬编码 Secret', 'HIGH'),
        ]

        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f, 1):
                        for pattern, desc, level in patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                rel = os.path.relpath(filepath, target)
                                risks.append((rel, i, level, desc, line.strip()))
            except:
                continue

        if not risks:
            return "✅ 没有发现安全风险"

        lines = [f"🔒 安全风险 ({len(risks)} 个):\n"]
        for file, line, level, desc, code in risks[:20]:
            icon = '🔴' if level == 'HIGH' else '🟡'
            lines.append(f"  {icon} {file}:{line} [{level}] {desc}")
            lines.append(f"      {code[:60]}")

        return '\n'.join(lines)

    def _metrics(self, target: str) -> str:
        """代码质量指标"""
        files = self._walk_py(target)

        total_lines = 0
        total_code = 0
        total_comment = 0
        total_blank = 0
        total_funcs = 0
        total_classes = 0
        max_file_lines = 0
        long_files = []

        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except:
                continue

            file_lines = len(lines)
            total_lines += file_lines
            if file_lines > max_file_lines:
                max_file_lines = file_lines
            if file_lines > 300:
                rel = os.path.relpath(filepath, target)
                long_files.append((rel, file_lines))

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    total_blank += 1
                elif stripped.startswith('#'):
                    total_comment += 1
                else:
                    total_code += 1

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        total_funcs += 1
                    elif isinstance(node, ast.ClassDef):
                        total_classes += 1
            except:
                pass

        comment_rate = (total_comment / max(total_code, 1)) * 100
        avg_lines = total_lines / max(len(files), 1)

        lines = [
            f"📊 代码质量指标 ({target}):\n",
            f"  文件数:     {len(files)}",
            f"  总行数:     {total_lines}",
            f"  代码行:     {total_code}",
            f"  注释行:     {total_comment} ({comment_rate:.1f}%)",
            f"  空行:       {total_blank}",
            f"  函数数:     {total_funcs}",
            f"  类数:       {total_classes}",
            f"  平均文件行: {avg_lines:.0f}",
            f"  最大文件行: {max_file_lines}",
        ]

        if long_files:
            lines.append(f"\n  ⚠️ 超过 300 行的文件 ({len(long_files)} 个):")
            for f, l in sorted(long_files, key=lambda x: -x[1])[:5]:
                lines.append(f"    • {f}: {l} 行")

        return '\n'.join(lines)

    def _suggest(self, target: str) -> str:
        """改进建议"""
        suggestions = []

        # 检查项目结构
        files = os.listdir(target) if os.path.isdir(target) else []
        py_files = self._walk_py(target)

        if not any(f == 'README.md' for f in files):
            suggestions.append("📝 添加 README.md 项目说明")

        if not any(f == 'pyproject.toml' for f in files):
            suggestions.append("📦 使用 pyproject.toml 替代 setup.py")

        if not any(f == '.gitignore' for f in files):
            suggestions.append("🚫 添加 .gitignore 文件")

        if not any(f == 'requirements.txt' or f == 'pyproject.toml' for f in files):
            suggestions.append("📋 添加依赖声明文件")

        # 检查测试
        test_files = [f for f in py_files if 'test' in os.path.basename(f).lower()]
        if not test_files and len(py_files) > 5:
            suggestions.append("🧪 添加单元测试")

        # 检查类型提示
        files_without_typehints = 0
        for filepath in py_files[:20]:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    source = f.read()
                if '-> ' not in source and ': str' not in source and ': int' not in source:
                    files_without_typehints += 1
            except:
                pass

        if files_without_typehints > len(py_files) * 0.5:
            suggestions.append("🏷️ 添加类型提示 (typing)")

        # 检查日志
        uses_print = 0
        uses_logging = 0
        for filepath in py_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    source = f.read()
                if 'print(' in source:
                    uses_print += 1
                if 'logging' in source:
                    uses_logging += 1
            except:
                pass

        if uses_print > uses_logging and uses_print > 3:
            suggestions.append("📊 考虑使用 logging 替代 print")

        # 检查文档
        has_docstrings = 0
        for filepath in py_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    if '"""' in f.read():
                        has_docstrings += 1
            except:
                pass

        if has_docstrings < len(py_files) * 0.3:
            suggestions.append("📚 添加函数/类文档字符串 (docstrings)")

        if not suggestions:
            return "✅ 项目结构良好，暂无改进建议"

        lines = [f"💡 改进建议 ({len(suggestions)} 条):\n"]
        for s in suggestions:
            lines.append(f"  {s}")

        return '\n'.join(lines)
