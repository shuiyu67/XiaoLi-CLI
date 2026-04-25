"""
代码工具插件 - 统一的代码编辑与搜索能力
合并原 code_editor + code_search，消除重复
"""
import os
import re
import ast
import difflib
from typing import Optional, Tuple, List


class Plugin:
    """代码编辑与搜索 - 精准编辑 + 代码理解"""

    def __init__(self):
        self.usage = """代码编辑与搜索工具

编辑操作:
  edit <文件> <old> <<<>>> <new>   - 精准替换代码片段
  multi <文件> <JSON数组>           - 批量修改
  insert <文件> <行号> <内容>       - 在指定行插入
  delete_lines <文件> <起始行> <结束行> - 删除指定行
  create <文件路径> [内容]          - 创建新文件
  write <文件路径> <内容>           - 写入/覆盖文件
  append <文件路径> <内容>          - 追加内容到文件

查看操作:
  read_range <文件> <起始行> [结束行] - 读取指定行范围
  diff <文件1> <文件2>              - 比较两个文件差异
  diff_text <old> <<<>>> <new>      - 比较两段文本差异
  ast_info <文件>                   - Python AST 摘要 (类/函数/导入)

搜索操作:
  find <目录> <关键词> [文件模式]    - 关键词搜索
  regex <目录> <正则表达式> [文件模式] - 正则搜索
  symbols <目录> [文件模式]          - 提取所有符号 (类/函数)
  imports <文件>                    - 分析导入依赖
  callers <目录> <函数名>           - 查找函数调用位置
  todo <目录> [文件模式]            - 搜索 TODO/FIXME
  structure <目录> [深度]           - 项目目录结构
  context <文件> [行号] [范围]      - 获取某行上下文
  stats <目录>                      - 代码统计
"""
        self.cli = None

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "code_editor",
            "description": "代码编辑与搜索 - 精准替换、批量编辑、代码搜索、符号提取、依赖分析、diff对比",
            "keywords": ["编辑", "修改", "代码", "文件", "edit", "replace", "search", "diff",
                         "find", "grep", "符号", "structure", "imports", "todo", "callers"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "code_editor",
            "description": "代码编辑与搜索工具",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "description": "操作类型"},
                    "path": {"type": "string", "description": "文件路径"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                    "content": {"type": "string"},
                    "line_number": {"type": "integer"},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                    "pattern": {"type": "string"},
                    "file_pattern": {"type": "string"},
                    "directory": {"type": "string"},
                    "operations": {"type": "array"}
                },
                "required": ["operation"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        path = arguments.get("path", "")
        return f"{op} {path}"

    # ── 路由 ──

    def handle(self, args: str) -> str:
        try:
            # 先提取操作名
            first_space = args.strip().find(' ')
            if first_space == -1:
                operation = args.strip().lower()
                arg1, arg2 = "", ""
            else:
                operation = args.strip()[:first_space].lower()
                rest = args.strip()[first_space + 1:]

                # diff_text 特殊处理：用 <<<>>> 分割
                if operation == "diff_text" and " <<<>>> " in rest:
                    arg1, arg2 = rest.split(" <<<>>> ", 1)
                else:
                    parts = rest.split(maxsplit=1)
                    arg1 = parts[0] if parts else ""
                    arg2 = parts[1] if len(parts) > 1 else ""

            if not operation:
                return "错误：请提供操作类型"

            handlers = {
                # 编辑
                "edit": self._op_edit,
                "multi": self._op_multi_edit,
                "insert": self._op_insert,
                "delete_lines": self._op_delete_lines,
                "create": self._op_create,
                "write": self._op_write,
                "append": self._op_append,
                # 查看
                "read_range": self._op_read_range,
                "diff": self._op_diff,
                "diff_text": self._op_diff_text,
                "ast_info": self._op_ast_info,
                # 搜索
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
            return f"代码工具错误: {str(e)}"

    # ── 工具方法 ──

    def _norm(self, path: str) -> str:
        path = path.strip().strip('"').strip("'")
        return os.path.normpath(os.path.expanduser(path))

    def _walk_files(self, directory: str, pattern: str = "*.py",
                    max_files: int = 200) -> List[str]:
        if pattern.startswith("*."):
            ext = pattern[1:]
            filt = lambda f: f.endswith(ext)
        elif pattern == "*":
            filt = lambda f: True
        else:
            filt = lambda f: pattern in f

        files = []
        skip = {'.git', 'node_modules', '__pycache__', '.venv', 'venv',
                'env', '.tox', '.mypy_cache', '.pytest_cache'}
        for root, dirs, fnames in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in skip]
            for f in fnames:
                if filt(f):
                    files.append(os.path.join(root, f))
                    if len(files) >= max_files:
                        return files
        return files

    def _make_diff(self, old: str, new: str, label: str = "修改") -> str:
        diff = difflib.unified_diff(
            old.splitlines(keepends=True), new.splitlines(keepends=True),
            fromfile="原始", tofile="修改后", lineterm='')
        text = '\n'.join(diff)
        return f"📝 变更预览:\n{text}" if text else "内容无变化"

    # ══════════════════════════════════════
    #  编辑操作
    # ══════════════════════════════════════

    def _op_edit(self, path: str, rest: str) -> str:
        if not path:
            return "错误：请提供文件路径"
        fp = self._norm(path)
        if not os.path.exists(fp):
            return f"错误：文件不存在: {fp}"

        sep = " <<<>>> "
        if sep not in rest:
            return "错误：格式: edit <文件> <old_text> <<<>>> <new_text>"

        old_text, new_text = rest.split(sep, 1)
        old_text = old_text.strip()
        new_text = new_text.strip()
        if not old_text:
            return "错误：old_text 不能为空"

        with open(fp, 'r', encoding='utf-8') as f:
            content = f.read()

        if old_text not in content:
            # 模糊匹配提示
            lines = content.split('\n')
            old_lines = old_text.split('\n')
            best_ratio, best_pos = 0, None
            for i in range(len(lines) - len(old_lines) + 1):
                candidate = lines[i:i+len(old_lines)]
                ratio = difflib.SequenceMatcher(
                    None, ''.join(candidate), ''.join(old_lines)).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_pos = i + 1
            if best_ratio > 0.6:
                return f"错误：未找到精确匹配。最接近位置在第 {best_pos} 行 (相似度 {best_ratio:.0%})，请检查缩进。"
            return "错误：未找到要替换的内容，请确保文本完全匹配（包括缩进）。"

        count = content.count(old_text)
        if count > 1:
            return f"警告：找到 {count} 处匹配，请提供更多上下文以确保唯一。"

        new_content = content.replace(old_text, new_text, 1)
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return f"✅ 已编辑: {fp}\n\n{self._make_diff(old_text, new_text)}"

    def _op_multi_edit(self, path: str, rest: str) -> str:
        import json
        if not path:
            return "错误：请提供文件路径"
        fp = self._norm(path)
        if not os.path.exists(fp):
            return f"错误：文件不存在: {fp}"

        try:
            ops = json.loads(rest)
        except json.JSONDecodeError:
            return "错误：JSON 格式: [{\"old\": \"...\", \"new\": \"...\"}]"
        if not isinstance(ops, list):
            return "错误：operations 必须是数组"

        with open(fp, 'r', encoding='utf-8') as f:
            content = f.read()

        results = []
        for i, op in enumerate(ops):
            old = op.get("old", "").strip()
            new = op.get("new", "").strip()
            if not old:
                results.append(f"  ✗ 操作 {i+1}: old 为空")
            elif old not in content:
                results.append(f"  ✗ 操作 {i+1}: 未找到匹配")
            else:
                content = content.replace(old, new, 1)
                results.append(f"  ✓ 操作 {i+1}: 已替换")

        with open(fp, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"✅ 批量编辑: {fp}\n" + "\n".join(results)

    def _op_insert(self, path: str, rest: str) -> str:
        if not path:
            return "错误：请提供文件路径"
        fp = self._norm(path)
        if not os.path.exists(fp):
            return f"错误：文件不存在: {fp}"

        parts = rest.split(maxsplit=1)
        if len(parts) < 2:
            return "错误：格式: insert <文件> <行号> <内容>"
        try:
            line_num = int(parts[0])
        except ValueError:
            return "错误：行号必须是整数"

        with open(fp, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if line_num < 1 or line_num > len(lines) + 1:
            return f"错误：行号超出范围 (1-{len(lines)+1})"

        insert_lines = [l + '\n' for l in parts[1].strip().split('\n')]
        lines[line_num-1:line_num-1] = insert_lines

        with open(fp, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return f"✅ 已在第 {line_num} 行插入 {len(insert_lines)} 行"

    def _op_delete_lines(self, path: str, rest: str) -> str:
        if not path:
            return "错误：请提供文件路径"
        fp = self._norm(path)
        if not os.path.exists(fp):
            return f"错误：文件不存在: {fp}"

        parts = rest.split()
        if len(parts) < 2:
            return "错误：格式: delete_lines <文件> <起始行> <结束行>"
        try:
            start, end = int(parts[0]), int(parts[1])
        except ValueError:
            return "错误：行号必须是整数"

        with open(fp, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if start < 1 or end > len(lines) or start > end:
            return f"错误：行号范围无效 (1-{len(lines)})"

        deleted = lines[start-1:end]
        lines[start-1:end] = []

        with open(fp, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return f"✅ 已删除第 {start}-{end} 行 ({len(deleted)} 行)"

    def _op_create(self, path: str, rest: str) -> str:
        if not path:
            return "错误：请提供文件路径"
        fp = self._norm(path)
        if os.path.exists(fp):
            return f"错误：文件已存在: {fp}"
        dir_path = os.path.dirname(fp)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(rest or "")
        return f"✅ 已创建: {fp} ({len(rest or '')} 字符)"

    def _op_write(self, path: str, rest: str) -> str:
        if not path:
            return "错误：请提供文件路径"
        fp = self._norm(path)
        dir_path = os.path.dirname(fp)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(rest)
        return f"✅ 已写入: {fp} ({len(rest)} 字符)"

    def _op_append(self, path: str, rest: str) -> str:
        if not path:
            return "错误：请提供文件路径"
        fp = self._norm(path)
        if not os.path.exists(fp):
            return f"错误：文件不存在: {fp}"
        with open(fp, 'a', encoding='utf-8') as f:
            f.write(rest)
        return f"✅ 已追加: {fp} ({len(rest)} 字符)"

    # ══════════════════════════════════════
    #  查看操作
    # ══════════════════════════════════════

    def _op_read_range(self, path: str, rest: str) -> str:
        if not path:
            return "错误：请提供文件路径"
        fp = self._norm(path)
        if not os.path.exists(fp):
            return f"错误：文件不存在: {fp}"

        parts = rest.split()
        start = int(parts[0]) if parts else 1
        end = int(parts[1]) if len(parts) > 1 else None

        with open(fp, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total = len(lines)
        end = end or total
        start = max(1, min(start, total))
        end = max(start, min(end, total))

        selected = lines[start-1:end]
        numbered = [f"{start+i:4d} | {line.rstrip()}" for i, line in enumerate(selected)]
        return f"📄 {fp} (第 {start}-{end} 行，共 {total} 行)\n{'─'*60}\n" + '\n'.join(numbered)

    def _op_diff(self, path: str, rest: str) -> str:
        if not path:
            return "错误：请提供第一个文件路径"
        f1 = self._norm(path)
        f2 = self._norm(rest.split()[0] if rest.strip() else "")
        if not os.path.exists(f1):
            return f"错误：文件不存在: {f1}"
        if not os.path.exists(f2):
            return f"错误：文件不存在: {f2}"

        with open(f1, 'r', encoding='utf-8') as f:
            l1 = f.readlines()
        with open(f2, 'r', encoding='utf-8') as f:
            l2 = f.readlines()

        diff = '\n'.join(difflib.unified_diff(l1, l2, fromfile=f1, tofile=f2, lineterm=''))
        return diff or "两个文件完全相同"

    def _op_diff_text(self, old: str, new: str) -> str:
        if not old and not new:
            return "错误：格式: diff_text <old> <<<>>> <new>"
        return self._make_diff(old.strip(), new.strip())

    def _op_ast_info(self, path: str, rest: str) -> str:
        if not path:
            return "错误：请提供文件路径"
        fp = self._norm(path)
        if not os.path.exists(fp):
            return f"错误：文件不存在: {fp}"

        with open(fp, 'r', encoding='utf-8') as f:
            source = f.read()
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return f"错误：语法错误 - {e}"

        info = [f"📄 {fp} AST 摘要:"]
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n.name for n in ast.iter_child_nodes(node)
                          if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                info.append(f"  class {node.name} (行 {node.lineno})")
                for m in methods:
                    info.append(f"    └─ {m}()")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                info.append(f"  def {node.name}() (行 {node.lineno})")
            elif isinstance(node, ast.Import):
                info.append(f"  import {', '.join(a.name for a in node.names)}")
            elif isinstance(node, ast.ImportFrom):
                info.append(f"  from {node.module} import {', '.join(a.name for a in node.names)}")

        return '\n'.join(info) if len(info) > 1 else f"📄 {fp}: 文件为空"

    # ══════════════════════════════════════
    #  搜索操作
    # ══════════════════════════════════════

    def _op_find(self, directory: str, rest: str) -> str:
        if not directory:
            return "错误：请提供搜索目录"
        search_dir = self._norm(directory)
        parts = rest.split(maxsplit=1)
        keyword = parts[0] if parts else ""
        file_pattern = parts[1] if len(parts) > 1 else "*.py"
        if not keyword:
            return "错误：请提供搜索关键词"
        if not os.path.isdir(search_dir):
            return f"错误：目录不存在: {search_dir}"

        files = self._walk_files(search_dir, file_pattern)
        results = []
        for fp in files:
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        if keyword.lower() in line.lower():
                            rel = os.path.relpath(fp, search_dir)
                            results.append(f"  {rel}:{line_num}: {line.rstrip()}")
                            if len(results) >= 80:
                                break
            except (UnicodeDecodeError, PermissionError):
                continue
            if len(results) >= 80:
                break

        if not results:
            return f"未找到 '{keyword}' 的匹配"
        return f"🔍 搜索 '{keyword}' ({len(results)}{'+' if len(results) >= 80 else ''} 匹配):\n" + '\n'.join(results)

    def _op_regex(self, directory: str, rest: str) -> str:
        if not directory:
            return "错误：请提供搜索目录"
        search_dir = self._norm(directory)
        parts = rest.split(maxsplit=1)
        pattern = parts[0] if parts else ""
        file_pattern = parts[1] if len(parts) > 1 else "*.py"
        if not pattern:
            return "错误：请提供正则表达式"
        try:
            regex = re.compile(pattern)
        except re.error as e:
            return f"错误：无效的正则: {e}"

        files = self._walk_files(search_dir, file_pattern)
        results = []
        for fp in files:
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            rel = os.path.relpath(fp, search_dir)
                            results.append(f"  {rel}:{line_num}: {line.rstrip()}")
                            if len(results) >= 50:
                                break
            except (UnicodeDecodeError, PermissionError):
                continue
            if len(results) >= 50:
                break

        if not results:
            return f"未找到匹配 '{pattern}'"
        return f"🔍 正则搜索 ({len(results)}{'+' if len(results) >= 50 else ''} 匹配):\n" + '\n'.join(results)

    def _op_symbols(self, directory: str, rest: str) -> str:
        if not directory:
            return "错误：请提供目录路径"
        search_dir = self._norm(directory)
        file_pattern = rest.strip() or "*.py"
        files = self._walk_files(search_dir, file_pattern)
        all_symbols = []

        for fp in files:
            if not fp.endswith('.py'):
                continue
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                rel = os.path.relpath(fp, search_dir)
                symbols = []
                for node in ast.iter_child_nodes(tree):
                    if isinstance(node, ast.ClassDef):
                        methods = [n.name for n in ast.iter_child_nodes(node)
                                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                        symbols.append(f"  class {node.name} (行 {node.lineno})")
                        for m in methods[:10]:
                            symbols.append(f"    └─ {m}()")
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        symbols.append(f"  def {node.name}() (行 {node.lineno})")
                if symbols:
                    all_symbols.append(f"\n📄 {rel}:")
                    all_symbols.extend(symbols)
            except (SyntaxError, UnicodeDecodeError):
                continue

        return "📋 代码符号:\n" + '\n'.join(all_symbols) if all_symbols else "未找到 Python 符号"

    def _op_imports(self, file_path: str, rest: str) -> str:
        if not file_path:
            return "错误：请提供文件路径"
        path = self._norm(file_path)
        if not os.path.exists(path):
            return f"错误：文件不存在: {path}"

        with open(path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())

        imports = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                imports.append(f"  import {', '.join(a.name for a in node.names)} (行 {node.lineno})")
            elif isinstance(node, ast.ImportFrom):
                names = ', '.join(a.name for a in node.names)
                imports.append(f"  from {node.module} import {names} (行 {node.lineno})")

        return f"📦 {file_path} 导入:\n" + '\n'.join(imports) if imports else f"📄 {file_path}: 没有导入"

    def _op_callers(self, directory: str, rest: str) -> str:
        if not directory:
            return "错误：请提供搜索目录"
        search_dir = self._norm(directory)
        parts = rest.split(maxsplit=1)
        func_name = parts[0] if parts else ""
        file_pattern = parts[1] if len(parts) > 1 else "*.py"
        if not func_name:
            return "错误：请提供函数名"

        patterns = [
            re.compile(rf'\b{re.escape(func_name)}\s*\('),
            re.compile(rf'\.{re.escape(func_name)}\s*\('),
        ]
        files = self._walk_files(search_dir, file_pattern)
        results = []
        for fp in files:
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        if any(p.search(line) for p in patterns):
                            rel = os.path.relpath(fp, search_dir)
                            results.append(f"  {rel}:{line_num}: {line.rstrip()}")
            except (UnicodeDecodeError, PermissionError):
                continue

        return f"🔎 '{func_name}' 的调用 ({len(results)}):\n" + '\n'.join(results) if results else f"未找到调用 '{func_name}'"

    def _op_todo(self, directory: str, rest: str) -> str:
        if not directory:
            return "错误：请提供目录路径"
        search_dir = self._norm(directory)
        file_pattern = rest.strip() or "*.py"
        pattern = re.compile(r'#\s*(TODO|FIXME|HACK|XXX|BUG|NOTE)\b[:\s]*(.*)', re.IGNORECASE)
        files = self._walk_files(search_dir, file_pattern)
        results = []
        for fp in files:
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        m = pattern.search(line)
                        if m:
                            rel = os.path.relpath(fp, search_dir)
                            results.append(f"  {rel}:{line_num} [{m.group(1).upper()}] {m.group(2).strip()}")
            except (UnicodeDecodeError, PermissionError):
                continue

        return f"📝 TODO/FIXME ({len(results)}):\n" + '\n'.join(results) if results else "没有 TODO/FIXME"

    def _op_structure(self, directory: str, rest: str) -> str:
        if not directory:
            return "错误：请提供目录路径"
        search_dir = self._norm(directory)
        if not os.path.isdir(search_dir):
            return f"错误：目录不存在: {search_dir}"

        max_depth = int(rest) if rest.strip().isdigit() else 3
        lines = [f"📁 {os.path.basename(search_dir)}/"]
        skip = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'env', '.tox'}

        def _tree(path, prefix="", depth=0):
            if depth >= max_depth:
                return
            try:
                entries = sorted(os.listdir(path))
            except PermissionError:
                return
            dirs = [e for e in entries if os.path.isdir(os.path.join(path, e))
                    and e not in skip and not e.startswith('.')]
            files = [e for e in entries if os.path.isfile(os.path.join(path, e))]
            if len(files) > 20:
                files = files[:20] + [f"... ({len(files)-20} more)"]

            for i, d in enumerate(dirs):
                is_last = (i == len(dirs) - 1) and not files
                lines.append(f"{prefix}{'└── ' if is_last else '├── '}{d}/")
                _tree(os.path.join(path, d), prefix + ("    " if is_last else "│   "), depth + 1)

            for i, f in enumerate(files):
                is_last = i == len(files) - 1
                size = os.path.getsize(os.path.join(path, f))
                size_str = f" ({size//1024}KB)" if size > 1024 else f" ({size}B)"
                lines.append(f"{prefix}{'└── ' if is_last else '├── '}{f}{size_str}")

        _tree(search_dir)
        return '\n'.join(lines)

    def _op_context(self, file_path: str, rest: str) -> str:
        if not file_path:
            return "错误：请提供文件路径"
        path = self._norm(file_path)
        if not os.path.exists(path):
            return f"错误：文件不存在: {path}"

        parts = rest.split()
        line_num = int(parts[0]) if parts else 1
        ctx = int(parts[1]) if len(parts) > 1 else 5

        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total = len(lines)
        start = max(1, line_num - ctx)
        end = min(total, line_num + ctx)

        result = [f"📄 {path} 第 {start}-{end} 行 (目标: 第 {line_num} 行):", "─" * 60]
        for i in range(start - 1, end):
            marker = ">>>" if i + 1 == line_num else "   "
            result.append(f"{marker} {i+1:4d} | {lines[i].rstrip()}")

        return '\n'.join(result)

    def _op_stats(self, directory: str, rest: str) -> str:
        if not directory:
            return "错误：请提供目录路径"
        search_dir = self._norm(directory)
        files = self._walk_files(search_dir, "*.py")

        total = blank = comment = code = 0
        for fp in files:
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    for line in f:
                        total += 1
                        s = line.strip()
                        if not s:
                            blank += 1
                        elif s.startswith('#'):
                            comment += 1
                        else:
                            code += 1
            except (UnicodeDecodeError, PermissionError):
                continue

        return (f"📊 代码统计 ({search_dir}):\n"
                f"  文件: {len(files)}\n"
                f"  总行: {total}\n"
                f"  代码: {code}\n"
                f"  注释: {comment}\n"
                f"  空行: {blank}\n"
                f"  注释率: {comment/max(code,1)*100:.1f}%")
