"""
文件管理器插件 - 文件系统操作
聚焦文件系统操作，代码编辑交给 code_editor
"""
import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List


class Plugin:
    """文件管理器 - 文件和目录的增删改查"""

    def __init__(self):
        self.usage = """文件管理器

操作:
  list <路径> [-p "模式"]       - 列出目录内容
  read <文件> [-n 行数]         - 读取文件内容
  write <文件> -c "内容"        - 写入文件
  append <文件> -c "内容"       - 追加内容
  copy <源> <目标>              - 复制文件/目录
  move <源> <目标>              - 移动/重命名
  delete <路径> [-r]            - 删除文件/目录
  search <目录> [-p 模式] [-c 内容] - 搜索文件
  info <路径>                   - 文件详细信息
  mkdir <路径>                  - 创建目录
"""
        self.cli = None

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "file_manager",
            "description": "文件管理器 - 文件和目录的创建、读写、复制、移动、删除、搜索",
            "keywords": ["文件", "目录", "管理", "file", "复制", "删除", "搜索", "mkdir",
                         "读取", "写入", "移动", "重命名"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "file_manager",
            "description": "文件管理器",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["list", "read", "write", "append", "copy",
                                 "move", "delete", "search", "info", "mkdir"],
                        "description": "操作类型"
                    },
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "destination": {"type": "string"},
                    "pattern": {"type": "string"},
                    "recursive": {"type": "boolean", "default": False}
                },
                "required": ["operation"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        path = arguments.get("path", "")
        return f"{op} {path}".strip()

    def handle(self, args: str) -> str:
        try:
            parts = self._parse_args(args)
            if not parts:
                return "错误：请提供操作类型"

            operation = parts[0].lower()
            handlers = {
                "list": self._op_list,
                "read": self._op_read,
                "write": self._op_write,
                "append": self._op_append,
                "copy": self._op_copy,
                "move": self._op_move,
                "delete": self._op_delete,
                "search": self._op_search,
                "info": self._op_info,
                "mkdir": self._op_mkdir,
            }

            handler = handlers.get(operation)
            if not handler:
                return f"错误：不支持的操作 '{operation}'"
            return handler(parts[1:])

        except Exception as e:
            return f"文件操作错误: {str(e)}"

    def _parse_args(self, args: str) -> List[str]:
        parts, current, in_quotes, qc = [], "", False, None
        for ch in args:
            if ch in ('"', "'") and not in_quotes:
                in_quotes, qc = True, ch
            elif ch == qc and in_quotes:
                in_quotes, qc = False, None
            elif ch == ' ' and not in_quotes:
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += ch
        if current:
            parts.append(current)
        return parts

    def _op_list(self, args: List[str]) -> str:
        path, pattern = ".", None
        i = 0
        while i < len(args):
            if args[i] == "-p" and i + 1 < len(args):
                pattern = args[i + 1]; i += 1
            elif not args[i].startswith("-"):
                path = args[i]
            i += 1

        path = os.path.abspath(path)
        if not os.path.isdir(path):
            return f"错误：不是目录: {path}"

        items = []
        try:
            for item in os.listdir(path):
                full = os.path.join(path, item)
                if pattern and not Path(item).match(pattern):
                    continue
                if os.path.isdir(full):
                    items.append(('dir', item, ''))
                else:
                    size = os.path.getsize(full)
                    size_str = f"{size/1024:.1f}KB" if size > 1024 else f"{size}B"
                    items.append(('file', item, size_str))

            items.sort(key=lambda x: (0 if x[0] == 'dir' else 1, x[1].lower()))
            dirs = sum(1 for x in items if x[0] == 'dir')
            files = len(items) - dirs

            result = [f" {path}", "─" * 50]
            for t, name, size in items[:100]:
                result.append(f"  {'' if t == 'dir' else ''} {name}{'/' if t == 'dir' else f'  ({size})'}")
            if len(items) > 100:
                result.append(f"  ... 还有 {len(items) - 100} 项")
            result.append("─" * 50)
            result.append(f"共 {dirs} 个文件夹, {files} 个文件")
            return '\n'.join(result)
        except Exception as e:
            return f"列出目录失败: {e}"

    def _op_read(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供文件路径"
        file_path = os.path.abspath(args[0])
        max_lines = None
        i = 1
        while i < len(args):
            if args[i] == "-n" and i + 1 < len(args):
                try:
                    max_lines = int(args[i + 1])
                except ValueError:
                    return "错误：行数必须是整数"
                i += 1
            i += 1

        if not os.path.isfile(file_path):
            return f"错误：文件不存在: {file_path}"

        size = os.path.getsize(file_path)
        if size > 10 * 1024 * 1024:
            return f"文件过大 ({size/1024/1024:.1f}MB)，请用 -n 限制行数"

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if max_lines:
                    lines = []
                    total = 0
                    for i, line in enumerate(f):
                        total = i + 1
                        if i < max_lines:
                            lines.append(f"{i+1:4d} | {line.rstrip()}")
                    content = '\n'.join(lines)
                    header = f" {file_path} ({size}B, 前 {min(max_lines, total)}/{total} 行)"
                else:
                    all_lines = f.readlines()
                    content = '\n'.join(f"{i+1:4d} | {l.rstrip()}" for i, l in enumerate(all_lines))
                    header = f" {file_path} ({size}B, {len(all_lines)} 行)"

            return f"{header}\n{'─' * 50}\n{content}"
        except UnicodeDecodeError:
            return "错误：无法解码（可能是二进制文件）"

    def _op_write(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：格式: write <文件> -c <内容>"
        fp = os.path.abspath(args[0])
        content = None
        i = 1
        while i < len(args):
            if args[i] == "-c" and i + 1 < len(args):
                content = args[i + 1]; i += 1
            i += 1
        if content is None:
            return "错误：请用 -c 提供内容"
        os.makedirs(os.path.dirname(fp) or ".", exist_ok=True)
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(content)
        return f" 已写入: {fp} ({len(content)} 字符)"

    def _op_append(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：格式: append <文件> -c <内容>"
        fp = os.path.abspath(args[0])
        content = None
        i = 1
        while i < len(args):
            if args[i] == "-c" and i + 1 < len(args):
                content = args[i + 1]; i += 1
            i += 1
        if content is None:
            return "错误：请用 -c 提供内容"
        if not os.path.isfile(fp):
            return f"错误：文件不存在: {fp}"
        with open(fp, 'a', encoding='utf-8') as f:
            f.write(content)
        return f" 已追加: {fp}"

    def _op_copy(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：请提供源和目标路径"
        src, dst = os.path.abspath(args[0]), os.path.abspath(args[1])
        if not os.path.exists(src):
            return f"错误：源不存在: {src}"
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
        else:
            shutil.copytree(src, dst, dirs_exist_ok=True)
        return f" 已复制:\n  {src}\n  → {dst}"

    def _op_move(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：请提供源和目标路径"
        src, dst = os.path.abspath(args[0]), os.path.abspath(args[1])
        if not os.path.exists(src):
            return f"错误：源不存在: {src}"
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        shutil.move(src, dst)
        return f" 已移动:\n  {src}\n  → {dst}"

    def _op_delete(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供路径"
        path = os.path.abspath(args[0])
        recursive = "-r" in args
        if not os.path.exists(path):
            return f"错误：不存在: {path}"
        if os.path.isfile(path):
            os.remove(path)
            return f" 已删除文件: {path}"
        elif os.path.isdir(path):
            if recursive:
                shutil.rmtree(path)
                return f" 已删除目录: {path}"
            elif not os.listdir(path):
                os.rmdir(path)
                return f" 已删除空目录: {path}"
            else:
                return "错误：目录不为空，用 -r 递归删除"

    def _op_search(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供搜索目录"
        directory = os.path.abspath(args[0])
        pattern, content_search = None, None
        i = 1
        while i < len(args):
            if args[i] == "-p" and i + 1 < len(args):
                pattern = args[i + 1]; i += 1
            elif args[i] == "-c" and i + 1 < len(args):
                content_search = args[i + 1]; i += 1
            i += 1

        if not os.path.isdir(directory):
            return f"错误：目录不存在: {directory}"

        results = []
        for root, dirs, files in os.walk(directory):
            for fn in files:
                if pattern and not Path(fn).match(pattern):
                    continue
                fp = os.path.join(root, fn)
                rel = os.path.relpath(fp, directory)
                if content_search:
                    try:
                        with open(fp, 'r', encoding='utf-8') as f:
                            for i, line in enumerate(f, 1):
                                if content_search in line:
                                    results.append(f"{rel}:{i}: {line.strip()[:80]}")
                                    if len(results) >= 50:
                                        break
                    except (UnicodeDecodeError, IOError):
                        continue
                else:
                    results.append(rel)
                if len(results) >= 50:
                    break
            if len(results) >= 50:
                break

        return f"搜索结果 ({len(results)}):\n" + '\n'.join(results) if results else "未找到匹配"

    def _op_info(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供路径"
        path = os.path.abspath(args[0])
        if not os.path.exists(path):
            return f"错误：不存在: {path}"

        stat = os.stat(path)
        result = [
            f"路径: {path}",
            f"类型: {'目录' if os.path.isdir(path) else '文件'}",
            f"大小: {stat.st_size:,} 字节 ({stat.st_size/1024:.1f} KB)",
            f"修改: {datetime.fromtimestamp(stat.st_mtime):%Y-%m-%d %H:%M:%S}",
            f"访问: {datetime.fromtimestamp(stat.st_atime):%Y-%m-%d %H:%M:%S}",
        ]
        if os.path.isfile(path):
            ext = os.path.splitext(path)[1]
            result.append(f"扩展名: {ext or '无'}")
        return '\n'.join(result)

    def _op_mkdir(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供目录路径"
        path = os.path.abspath(args[0])
        if os.path.exists(path):
            return f"错误：已存在: {path}"
        os.makedirs(path, exist_ok=True)
        return f" 已创建: {path}"
