"""
代码编辑器插件 - 小狸的精准代码编辑能力
对标 Claude Code 的多文件编辑、上下文感知修改
"""
import os
import re
import difflib
from typing import Optional, Tuple, List, Dict


class Plugin:
    """精准代码编辑器 - 支持搜索替换、多文件编辑、diff 预览"""

    def __init__(self):
        self.usage = """代码编辑器 - 精准修改代码文件

操作类型:
  edit <文件路径> <old_text> <new_text>  - 精准替换代码片段
  multi <文件路径> <JSON批量操作>         - 批量修改（JSON数组）
  diff <文件路径1> <文件路径2>            - 比较两个文件差异
  diff_text <old_text> <new_text>         - 比较两段文本差异
  insert <文件路径> <行号> <内容>         - 在指定行插入内容
  delete_lines <文件路径> <起始行> <结束行> - 删除指定行范围
  read_range <文件路径> <起始行> <结束行>  - 读取指定行范围
  search <目录> <正则表达式> [文件模式]   - 在代码中搜索
  ast_info <文件路径>                     - 获取 Python 文件的 AST 摘要
  create <文件路径> <内容>                - 创建新文件
  write <文件路径> <内容>                 - 写入/覆盖文件内容
  append <文件路径> <内容>                - 追加内容到文件
"""
        self.cli = None

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "code_editor",
            "description": "精准代码编辑器 - 支持搜索替换、多文件批量编辑、代码搜索、diff对比。用于修改代码文件的核心工具。",
            "keywords": ["编辑", "修改", "代码", "文件", "edit", "replace", "search", "diff", "code"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "code_editor",
            "description": "精准代码编辑器",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["edit", "multi", "diff", "diff_text", "insert",
                                 "delete_lines", "read_range", "search", "ast_info",
                                 "create", "write", "append"],
                        "description": "操作类型"
                    },
                    "path": {"type": "string", "description": "文件路径"},
                    "old_text": {"type": "string", "description": "要替换的原文"},
                    "new_text": {"type": "string", "description": "替换后的新文本"},
                    "content": {"type": "string", "description": "文件内容"},
                    "line_number": {"type": "integer", "description": "行号"},
                    "start_line": {"type": "integer", "description": "起始行"},
                    "end_line": {"type": "integer", "description": "结束行"},
                    "pattern": {"type": "string", "description": "搜索正则表达式"},
                    "file_pattern": {"type": "string", "description": "文件匹配模式"},
                    "directory": {"type": "string", "description": "搜索目录"},
                    "operations": {"type": "array", "description": "批量操作列表"}
                },
                "required": ["operation"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        path = arguments.get("path", "")
        return f"{op} {path}"

    def handle(self, args: str) -> str:
        try:
            parts = args.strip().split(maxsplit=2)
            if not parts:
                return "错误：请提供操作类型"

            operation = parts[0].lower()

            handlers = {
                "edit": self._op_edit,
                "multi": self._op_multi_edit,
                "diff": self._op_diff,
                "diff_text": self._op_diff_text,
                "insert": self._op_insert,
                "delete_lines": self._op_delete_lines,
                "read_range": self._op_read_range,
                "search": self._op_search,
                "ast_info": self._op_ast_info,
                "create": self._op_create,
                "write": self._op_write,
                "append": self._op_append,
            }

            handler = handlers.get(operation)
            if not handler:
                return f"错误：不支持的操作 '{operation}'"

            return handler(parts[1] if len(parts) > 1 else "",
                          parts[2] if len(parts) > 2 else "")

        except Exception as e:
            return f"代码编辑器错误: {str(e)}"

    def _normalize_path(self, path: str) -> str:
        """规范化路径"""
        path = path.strip().strip('"').strip("'")
        path = os.path.expanduser(path)
        path = os.path.normpath(path)
        return path

    def _op_edit(self, path: str, rest: str) -> str:
        """精准替换代码片段 - 核心编辑能力"""
        if not path:
            return "错误：请提供文件路径"

        file_path = self._normalize_path(path)

        if not os.path.exists(file_path):
            return f"错误：文件不存在: {file_path}"

        # 从 rest 中解析 old_text 和 new_text
        # 格式: old_text <<<SEPARATOR>>> new_text
        separator = " <<<>>> "
        if separator not in rest:
            return "错误：格式应为: edit <文件> <old_text> <<<>>> <new_text>"

        old_text, new_text = rest.split(separator, 1)

        if not old_text.strip():
            return "错误：old_text 不能为空"

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 精准匹配（去除首尾空白但保留内部格式）
        old_text = old_text.strip()
        new_text = new_text.strip()

        if old_text not in content:
            # 尝试模糊匹配
            lines = content.split('\n')
            old_lines = old_text.split('\n')
            match_info = self._fuzzy_match(lines, old_lines)
            if match_info:
                return f"错误：未找到精确匹配。最接近的位置在第 {match_info[0]+1}-{match_info[1]} 行，但内容不完全一致。请检查缩进和空白字符。"
            return f"错误：在文件中未找到要替换的内容。请确保文本完全匹配（包括缩进）。"

        count = content.count(old_text)
        if count > 1:
            return f"警告：找到 {count} 处匹配，请提供更多上下文以确保唯一匹配。"

        new_content = content.replace(old_text, new_text, 1)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        # 生成 diff 预览
        diff = self._make_diff(old_text, new_text, file_path)
        return f"✅ 已编辑: {file_path}\n\n{diff}"

    def _op_multi_edit(self, path: str, rest: str) -> str:
        """批量编辑 - 一次修改多处"""
        import json

        if not path:
            return "错误：请提供文件路径"

        file_path = self._normalize_path(path)

        if not os.path.exists(file_path):
            return f"错误：文件不存在: {file_path}"

        try:
            operations = json.loads(rest)
        except json.JSONDecodeError:
            return "错误：operations 必须是有效的 JSON 数组。格式: [{\"old\": \"...\", \"new\": \"...\"}]"

        if not isinstance(operations, list):
            return "错误：operations 必须是数组"

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        results = []
        for i, op in enumerate(operations):
            old_text = op.get("old", "").strip()
            new_text = op.get("new", "").strip()

            if not old_text:
                results.append(f"  ❌ 操作 {i+1}: old 为空")
                continue

            if old_text not in content:
                results.append(f"  ❌ 操作 {i+1}: 未找到匹配")
                continue

            content = content.replace(old_text, new_text, 1)
            results.append(f"  ✅ 操作 {i+1}: 已替换")

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return f"✅ 批量编辑完成: {file_path}\n" + "\n".join(results)

    def _op_diff(self, path: str, rest: str) -> str:
        """比较两个文件差异"""
        if not path:
            return "错误：请提供第一个文件路径"

        file1 = self._normalize_path(path)
        file2 = self._normalize_path(rest.split()[0] if rest.strip() else "")

        if not os.path.exists(file1):
            return f"错误：文件不存在: {file1}"
        if not os.path.exists(file2):
            return f"错误：文件不存在: {file2}"

        with open(file1, 'r', encoding='utf-8') as f:
            lines1 = f.readlines()
        with open(file2, 'r', encoding='utf-8') as f:
            lines2 = f.readlines()

        diff = difflib.unified_diff(lines1, lines2,
                                     fromfile=file1, tofile=file2, lineterm='')
        diff_text = '\n'.join(diff)

        if not diff_text:
            return "两个文件完全相同"

        return f"文件差异:\n{diff_text}"

    def _op_diff_text(self, path: str, rest: str) -> str:
        """比较两段文本差异"""
        separator = " <<<>>> "
        if separator not in rest:
            return "错误：格式: diff_text <old_text> <<<>>> <new_text>"

        old_text, new_text = rest.split(separator, 1)
        diff = self._make_diff(old_text.strip(), new_text.strip(), "修改")
        return diff

    def _op_insert(self, path: str, rest: str) -> str:
        """在指定行插入内容"""
        if not path:
            return "错误：请提供文件路径"

        file_path = self._normalize_path(path)

        if not os.path.exists(file_path):
            return f"错误：文件不存在: {file_path}"

        parts = rest.split(maxsplit=1)
        if len(parts) < 2:
            return "错误：格式: insert <文件> <行号> <内容>"

        try:
            line_num = int(parts[0])
        except ValueError:
            return "错误：行号必须是整数"

        content_to_insert = parts[1].strip()

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if line_num < 1 or line_num > len(lines) + 1:
            return f"错误：行号超出范围 (1-{len(lines)+1})"

        insert_lines = [l + '\n' for l in content_to_insert.split('\n')]
        lines[line_num-1:line_num-1] = insert_lines

        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return f"✅ 已在第 {line_num} 行插入 {len(insert_lines)} 行内容"

    def _op_delete_lines(self, path: str, rest: str) -> str:
        """删除指定行范围"""
        if not path:
            return "错误：请提供文件路径"

        file_path = self._normalize_path(path)

        if not os.path.exists(file_path):
            return f"错误：文件不存在: {file_path}"

        parts = rest.split()
        if len(parts) < 2:
            return "错误：格式: delete_lines <文件> <起始行> <结束行>"

        try:
            start = int(parts[0])
            end = int(parts[1])
        except ValueError:
            return "错误：行号必须是整数"

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if start < 1 or end > len(lines) or start > end:
            return f"错误：行号范围无效 (1-{len(lines)})"

        deleted = lines[start-1:end]
        lines[start-1:end] = []

        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return f"✅ 已删除第 {start}-{end} 行 ({len(deleted)} 行)"

    def _op_read_range(self, path: str, rest: str) -> str:
        """读取指定行范围"""
        if not path:
            return "错误：请提供文件路径"

        file_path = self._normalize_path(path)

        if not os.path.exists(file_path):
            return f"错误：文件不存在: {file_path}"

        parts = rest.split()
        start = int(parts[0]) if len(parts) > 0 else 1
        end = int(parts[1]) if len(parts) > 1 else None

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total = len(lines)
        if end is None:
            end = total
        start = max(1, min(start, total))
        end = max(start, min(end, total))

        selected = lines[start-1:end]
        numbered = [f"{start+i:4d} | {line.rstrip()}" for i, line in enumerate(selected)]

        return f"📄 {file_path} (第 {start}-{end} 行，共 {total} 行)\n{'─'*60}\n" + '\n'.join(numbered)

    def _op_search(self, path: str, rest: str) -> str:
        """在代码中搜索（类似 grep）"""
        if not path:
            return "错误：请提供搜索目录"

        search_dir = self._normalize_path(path)

        if not os.path.isdir(search_dir):
            return f"错误：目录不存在: {search_dir}"

        parts = rest.split(maxsplit=1)
        if not parts:
            return "错误：请提供搜索正则表达式"

        pattern = parts[0]
        file_pattern = parts[1] if len(parts) > 1 else "*.py"

        try:
            regex = re.compile(pattern)
        except re.error as e:
            return f"错误：无效的正则表达式: {e}"

        # 构建文件匹配模式
        if file_pattern.startswith("*."):
            ext = file_pattern[1:]  # .py
            file_filter = lambda f: f.endswith(ext)
        elif file_pattern == "*":
            file_filter = lambda f: True
        else:
            file_filter = lambda f: file_pattern in f

        results = []
        max_results = 50

        for root, dirs, files in os.walk(search_dir):
            # 跳过隐藏目录和常见不需要搜索的目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in
                      {'node_modules', '__pycache__', '.git', 'venv', '.venv', 'env'}]

            for filename in files:
                if not file_filter(filename):
                    continue

                filepath = os.path.join(root, filename)
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
            if len(results) >= max_results:
                break

        if not results:
            return f"未找到匹配 '{pattern}' 的结果"

        header = f"🔍 搜索结果 ({len(results)}{'+' if len(results) >= max_results else ''} 匹配):\n"
        return header + '\n'.join(results)

    def _op_ast_info(self, path: str, rest: str) -> str:
        """获取 Python 文件的 AST 摘要"""
        import ast

        if not path:
            return "错误：请提供文件路径"

        file_path = self._normalize_path(path)

        if not os.path.exists(file_path):
            return f"错误：文件不存在: {file_path}"

        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return f"错误：语法错误 - {e}"

        info = [f"📄 {file_path} AST 摘要:"]

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
                names = [a.name for a in node.names]
                info.append(f"  import {', '.join(names)}")
            elif isinstance(node, ast.ImportFrom):
                names = [a.name for a in node.names]
                info.append(f"  from {node.module} import {', '.join(names)}")

        if len(info) == 1:
            return f"📄 {file_path}: 文件为空或无顶层定义"

        return '\n'.join(info)

    def _op_create(self, path: str, rest: str) -> str:
        """创建新文件"""
        if not path:
            return "错误：请提供文件路径"

        file_path = self._normalize_path(path)

        if os.path.exists(file_path):
            return f"错误：文件已存在: {file_path}"

        # 确保目录存在
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)

        content = rest if rest else ""

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return f"✅ 已创建文件: {file_path} ({len(content)} 字符)"

    def _op_write(self, path: str, rest: str) -> str:
        """写入/覆盖文件内容"""
        if not path:
            return "错误：请提供文件路径"

        file_path = self._normalize_path(path)

        # 确保目录存在
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(rest)

        return f"✅ 已写入文件: {file_path} ({len(rest)} 字符)"

    def _op_append(self, path: str, rest: str) -> str:
        """追加内容到文件"""
        if not path:
            return "错误：请提供文件路径"

        file_path = self._normalize_path(path)

        if not os.path.exists(file_path):
            return f"错误：文件不存在: {file_path}"

        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(rest)

        return f"✅ 已追加内容到: {file_path} ({len(rest)} 字符)"

    def _make_diff(self, old_text: str, new_text: str, label: str) -> str:
        """生成 diff 预览"""
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)

        diff = difflib.unified_diff(old_lines, new_lines,
                                     fromfile=f"原始", tofile=f"修改后", lineterm='')
        diff_text = '\n'.join(diff)

        if not diff_text:
            return "内容无变化"

        return f"📝 变更预览:\n{diff_text}"

    def _fuzzy_match(self, lines: list, old_lines: list) -> Optional[Tuple[int, int]]:
        """模糊匹配，尝试找到最接近的位置"""
        if not old_lines:
            return None

        best_ratio = 0
        best_pos = None

        for i in range(len(lines) - len(old_lines) + 1):
            candidate = lines[i:i+len(old_lines)]
            ratio = difflib.SequenceMatcher(None,
                ''.join(candidate), ''.join(old_lines)).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_pos = (i, i + len(old_lines) - 1)

        if best_ratio > 0.6:
            return best_pos
        return None
