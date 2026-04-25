"""
代码搜索与理解插件 - 代码库级别的智能搜索
对标 Claude Code 的代码理解能力
"""
import os
import re
import ast
from typing import List, Dict, Optional, Tuple


class Plugin:
    """代码搜索与理解工具 - 跨文件搜索、依赖分析、代码结构理解"""

    def __init__(self):
        self.usage = """代码搜索与理解工具

操作类型:
  find <目录> <关键词> [文件模式]    - 搜索代码中的关键词
  regex <目录> <正则表达式> [文件模式] - 正则表达式搜索
  symbols <目录> [文件模式]           - 提取所有符号（类、函数、变量）
  imports <文件路径>                   - 分析文件的导入依赖
  callers <目录> <函数名>             - 查找调用指定函数的位置
  todo <目录> [文件模式]              - 搜索 TODO/FIXME/HACK 注释
  structure <目录>                    - 显示项目目录结构
  context <文件路径> [行号] [范围]    - 获取某行的上下文
  stats <目录>                        - 代码统计（行数、文件数等）
"""
        self.cli = None

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "code_search",
            "description": "代码搜索与理解工具 - 跨文件搜索、符号提取、依赖分析、项目结构查看",
            "keywords": ["搜索", "查找", "grep", "search", "find", "代码", "符号", "结构"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "code_search",
            "description": "代码搜索与理解工具",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string"},
                    "directory": {"type": "string"},
                    "pattern": {"type": "string"},
                    "file_pattern": {"type": "string"},
                    "file_path": {"type": "string"},
                    "line_number": {"type": "integer"},
                    "range": {"type": "integer"}
                },
                "required": ["operation"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        directory = arguments.get("directory", "")
        pattern = arguments.get("pattern", "")
        return f"{op} {directory} {pattern}".strip()

    def handle(self, args: str) -> str:
        try:
            parts = args.strip().split(maxsplit=2)
            if not parts:
                return "错误：请提供操作类型"

            operation = parts[0].lower()
            arg1 = parts[1] if len(parts) > 1 else ""
            arg2 = parts[2] if len(parts) > 2 else ""

            handlers = {
                "find": self._op_find,
                "regex": self._op_regex,
                "symbols": self._op_symbols,
                "imports": self._op_imports,
                "callers": self._op_callers,
                "todo": self._op_todo,
                "structure": self._op_structure,
                "context": self._op_context,
                "stats": self._op_stats,
            }

            handler = handlers.get(operation)
            if not handler:
                return f"错误：不支持的操作 '{operation}'"

            return handler(arg1, arg2)

        except Exception as e:
            return f"代码搜索错误: {str(e)}"

    def _normalize_path(self, path: str) -> str:
        path = path.strip().strip('"').strip("'")
        path = os.path.expanduser(path)
        return os.path.normpath(path)

    def _walk_files(self, directory: str, file_pattern: str = "*.py",
                    max_files: int = 200) -> List[str]:
        """遍历目录中的文件"""
        if file_pattern.startswith("*."):
            ext = file_pattern[1:]
            file_filter = lambda f: f.endswith(ext)
        elif file_pattern == "*":
            file_filter = lambda f: True
        else:
            file_filter = lambda f: file_pattern in f

        files = []
        skip_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv',
                     'env', '.env', '.tox', '.mypy_cache', '.pytest_cache'}

        for root, dirs, filenames in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in skip_dirs]
            for f in filenames:
                if file_filter(f):
                    files.append(os.path.join(root, f))
                    if len(files) >= max_files:
                        return files
        return files

    def _op_find(self, directory: str, rest: str) -> str:
        """关键词搜索"""
        if not directory:
            return "错误：请提供搜索目录"

        search_dir = self._normalize_path(directory)
        parts = rest.split(maxsplit=1)
        keyword = parts[0] if parts else ""
        file_pattern = parts[1] if len(parts) > 1 else "*.py"

        if not keyword:
            return "错误：请提供搜索关键词"

        if not os.path.isdir(search_dir):
            return f"错误：目录不存在: {search_dir}"

        files = self._walk_files(search_dir, file_pattern)
        results = []
        max_results = 80

        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        if keyword.lower() in line.lower():
                            rel_path = os.path.relpath(filepath, search_dir)
                            results.append(f"  {rel_path}:{line_num}: {line.rstrip()}")
                            if len(results) >= max_results:
                                break
            except (UnicodeDecodeError, PermissionError):
                continue
            if len(results) >= max_results:
                break

        if not results:
            return f"未找到 '{keyword}' 的匹配"

        return f"🔍 搜索 '{keyword}' ({len(results)}{'+' if len(results) >= max_results else ''} 匹配):\n" + '\n'.join(results)

    def _op_regex(self, directory: str, rest: str) -> str:
        """正则表达式搜索"""
        if not directory:
            return "错误：请提供搜索目录"

        search_dir = self._normalize_path(directory)
        parts = rest.split(maxsplit=1)
        pattern = parts[0] if parts else ""
        file_pattern = parts[1] if len(parts) > 1 else "*.py"

        if not pattern:
            return "错误：请提供正则表达式"

        try:
            regex = re.compile(pattern)
        except re.error as e:
            return f"错误：无效的正则表达式: {e}"

        files = self._walk_files(search_dir, file_pattern)
        results = []
        max_results = 50

        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            rel_path = os.path.relpath(filepath, search_dir)
                            results.append(f"  {rel_path}:{line_num}: {line.rstrip()}")
                            if len(results) >= max_results:
                                break
            except (UnicodeDecodeError, PermissionError):
                continue
            if len(results) >= max_results:
                break

        if not results:
            return f"未找到匹配 '{pattern}' 的结果"

        return f"🔍 正则搜索 ({len(results)}{'+' if len(results) >= max_results else ''} 匹配):\n" + '\n'.join(results)

    def _op_symbols(self, directory: str, rest: str) -> str:
        """提取目录中所有 Python 符号"""
        if not directory:
            return "错误：请提供目录路径"

        search_dir = self._normalize_path(directory)
        file_pattern = rest.strip() or "*.py"

        files = self._walk_files(search_dir, file_pattern)
        all_symbols = []

        for filepath in files:
            if not filepath.endswith('.py'):
                continue
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    source = f.read()
                tree = ast.parse(source)
                rel_path = os.path.relpath(filepath, search_dir)

                symbols = []
                for node in ast.iter_child_nodes(tree):
                    if isinstance(node, ast.ClassDef):
                        methods = [n.name for n in ast.iter_child_nodes(node)
                                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                        symbols.append(f"  class {node.name} (行 {node.lineno})")
                        for m in methods[:10]:  # 限制每个类最多显示10个方法
                            symbols.append(f"    └─ {m}()")
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        symbols.append(f"  def {node.name}() (行 {node.lineno})")

                if symbols:
                    all_symbols.append(f"\n📄 {rel_path}:")
                    all_symbols.extend(symbols)

            except (SyntaxError, UnicodeDecodeError):
                continue

        if not all_symbols:
            return "未找到 Python 符号"

        return f"📋 代码符号:\n" + '\n'.join(all_symbols)

    def _op_imports(self, file_path: str, rest: str) -> str:
        """分析文件的导入依赖"""
        if not file_path:
            return "错误：请提供文件路径"

        path = self._normalize_path(file_path)

        if not os.path.exists(path):
            return f"错误：文件不存在: {path}"

        with open(path, 'r', encoding='utf-8') as f:
            source = f.read()

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return f"错误：语法错误 - {e}"

        imports = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(f"  import {alias.name} (行 {node.lineno})")
            elif isinstance(node, ast.ImportFrom):
                names = [a.name for a in node.names]
                imports.append(f"  from {node.module} import {', '.join(names)} (行 {node.lineno})")

        if not imports:
            return f"📄 {file_path}: 没有导入语句"

        return f"📦 {file_path} 导入依赖:\n" + '\n'.join(imports)

    def _op_callers(self, directory: str, rest: str) -> str:
        """查找调用指定函数的位置"""
        if not directory:
            return "错误：请提供搜索目录"

        search_dir = self._normalize_path(directory)
        parts = rest.split(maxsplit=1)
        func_name = parts[0] if parts else ""
        file_pattern = parts[1] if len(parts) > 1 else "*.py"

        if not func_name:
            return "错误：请提供函数名"

        # 搜索函数调用模式
        patterns = [
            re.compile(rf'\b{re.escape(func_name)}\s*\('),
            re.compile(rf'\.{re.escape(func_name)}\s*\('),
        ]

        files = self._walk_files(search_dir, file_pattern)
        results = []

        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        for pat in patterns:
                            if pat.search(line):
                                rel_path = os.path.relpath(filepath, search_dir)
                                results.append(f"  {rel_path}:{line_num}: {line.rstrip()}")
                                break
            except (UnicodeDecodeError, PermissionError):
                continue

        if not results:
            return f"未找到调用 '{func_name}' 的位置"

        return f"🔎 '{func_name}' 的调用位置 ({len(results)}):\n" + '\n'.join(results)

    def _op_todo(self, directory: str, rest: str) -> str:
        """搜索 TODO/FIXME/HACK 注释"""
        if not directory:
            return "错误：请提供目录路径"

        search_dir = self._normalize_path(directory)
        file_pattern = rest.strip() or "*.py"

        pattern = re.compile(r'#\s*(TODO|FIXME|HACK|XXX|BUG|NOTE)\b[:\s]*(.*)', re.IGNORECASE)
        files = self._walk_files(search_dir, file_pattern)
        results = []

        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        match = pattern.search(line)
                        if match:
                            rel_path = os.path.relpath(filepath, search_dir)
                            tag = match.group(1).upper()
                            desc = match.group(2).strip()
                            results.append(f"  {rel_path}:{line_num} [{tag}] {desc}")
            except (UnicodeDecodeError, PermissionError):
                continue

        if not results:
            return "没有找到 TODO/FIXME 注释"

        return f"📝 TODO/FIXME ({len(results)}):\n" + '\n'.join(results)

    def _op_structure(self, directory: str, rest: str) -> str:
        """显示项目目录结构"""
        if not directory:
            return "错误：请提供目录路径"

        search_dir = self._normalize_path(directory)
        if not os.path.isdir(search_dir):
            return f"错误：目录不存在: {search_dir}"

        max_depth = int(rest) if rest.strip().isdigit() else 3
        lines = [f"📁 {os.path.basename(search_dir)}/"]
        skip_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv',
                     'env', '.tox', '.mypy_cache'}

        def _tree(path, prefix="", depth=0):
            if depth >= max_depth:
                return
            try:
                entries = sorted(os.listdir(path))
            except PermissionError:
                return

            dirs = [e for e in entries if os.path.isdir(os.path.join(path, e))
                    and e not in skip_dirs and not e.startswith('.')]
            files = [e for e in entries if os.path.isfile(os.path.join(path, e))]

            # 限制每个目录显示的文件数
            if len(files) > 20:
                files = files[:20] + [f"... ({len(files)-20} more)"]

            for i, d in enumerate(dirs):
                is_last_dir = (i == len(dirs) - 1) and not files
                connector = "└── " if is_last_dir else "├── "
                lines.append(f"{prefix}{connector}{d}/")
                extension = "    " if is_last_dir else "│   "
                _tree(os.path.join(path, d), prefix + extension, depth + 1)

            for i, f in enumerate(files):
                is_last = i == len(files) - 1
                connector = "└── " if is_last else "├── "
                # 文件大小
                fpath = os.path.join(path, f)
                if os.path.isfile(fpath):
                    size = os.path.getsize(fpath)
                    if size > 1024 * 1024:
                        size_str = f" ({size // (1024*1024)}MB)"
                    elif size > 1024:
                        size_str = f" ({size // 1024}KB)"
                    else:
                        size_str = f" ({size}B)"
                else:
                    size_str = ""
                lines.append(f"{prefix}{connector}{f}{size_str}")

        _tree(search_dir)
        return '\n'.join(lines)

    def _op_context(self, file_path: str, rest: str) -> str:
        """获取某行的上下文"""
        if not file_path:
            return "错误：请提供文件路径"

        path = self._normalize_path(file_path)

        if not os.path.exists(path):
            return f"错误：文件不存在: {path}"

        parts = rest.split()
        line_num = int(parts[0]) if parts else 1
        context_range = int(parts[1]) if len(parts) > 1 else 5

        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total = len(lines)
        start = max(1, line_num - context_range)
        end = min(total, line_num + context_range)

        result = [f"📄 {path} 第 {start}-{end} 行 (目标: 第 {line_num} 行):"]
        result.append("─" * 60)

        for i in range(start - 1, end):
            marker = ">>>" if i + 1 == line_num else "   "
            result.append(f"{marker} {i+1:4d} | {lines[i].rstrip()}")

        return '\n'.join(result)

    def _op_stats(self, directory: str, rest: str) -> str:
        """代码统计"""
        if not directory:
            return "错误：请提供目录路径"

        search_dir = self._normalize_path(directory)
        files = self._walk_files(search_dir, "*.py")

        total_lines = 0
        total_blank = 0
        total_comment = 0
        total_code = 0
        file_count = len(files)

        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        total_lines += 1
                        stripped = line.strip()
                        if not stripped:
                            total_blank += 1
                        elif stripped.startswith('#'):
                            total_comment += 1
                        else:
                            total_code += 1
            except (UnicodeDecodeError, PermissionError):
                continue

        return f"""📊 代码统计 ({search_dir}):
  文件数: {file_count}
  总行数: {total_lines}
  代码行: {total_code}
  注释行: {total_comment}
  空行:   {total_blank}
  注释率: {total_comment/max(total_code,1)*100:.1f}%"""
