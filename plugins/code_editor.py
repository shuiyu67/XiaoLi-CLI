"""
代码工具 - 统一的代码编辑与搜索能力
合并原 code_editor + code_search，消除重复
"""
import os
import re
import ast
import difflib
import py_compile
import json
import subprocess
import sys
import tempfile
import platform
import threading
from typing import Optional, Tuple, List


class Liugin:
    """代码编辑与搜索 - 精准编辑 + 代码理解"""

    def __init__(self):
        self.usage = """代码编辑与搜索工具

编辑操作 (修改后自动检查语法):
  edit <文件> <old> <<<>>> <new>   - 精准替换代码片段
  multi <文件> <JSON数组>           - 批量修改
  insert <文件> <行号> <内容>       - 在指定行插入
  delete_lines <文件> <起始行> <结束行> - 删除指定行
  create <文件路径> [内容]          - 创建新文件
  write <文件路径> <内容>           - 写入/覆盖文件
  append <文件路径> <内容>          - 追加内容到文件

语法检查:
  syntax_check <文件路径>           - 主动检查文件语法 (别名: check)
  支持: Python/JS/TS/JSON/YAML/TOML/HTML/XML/CSS/Shell/SQL
  编辑操作后自动执行，无需手动调用

Diff 弹窗:
  diff_popup [on|off|popup|inline]  - 开关/切换 diff 显示模式 (别名: popup)
  popup/弹窗    → 弹窗模式（新终端窗口）
  inline/ssh    → 主终端内显示（SSH 兼容）
  on/开         → 开启  |  off/关 → 关闭  |  无参数 → 切换

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
        self.diff_popup_enabled = True  # diff 弹窗开关
        self.diff_popup_mode = None     # None=启动时询问, True=弹窗, False=主终端内显示

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "code_editor",
            "description": "代码编辑与搜索 — 精准替换、批量编辑、代码搜索、符号提取、依赖分析、diff对比、自动语法检查",
            "keywords": ["编辑", "修改", "代码", "文件", "edit", "replace", "search", "diff",
                         "find", "grep", "符号", "structure", "imports", "todo", "callers",
                         "语法", "syntax", "check", "lint", "检查"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "code_editor",
            "description": "代码编辑与搜索工具（含自动语法检查）",
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
                # 语法检查
                "syntax_check": self._op_syntax_check,
                "check": self._op_syntax_check,  # 简写别名
                # Diff 弹窗
                "diff_popup": self._op_diff_popup,
                "popup": self._op_diff_popup,  # 简写别名
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
        return f" 变更预览:\n{text}" if text else "内容无变化"

    # ══════════════════════════════════════
    #  语法检查系统
    # ══════════════════════════════════════

    # 支持语法检查的语言映射
    _CODE_EXTENSIONS = {
        '.py':   'python',
        '.pyw':  'python',
        '.pyi':  'python',
        '.js':   'javascript',
        '.mjs':  'javascript',
        '.cjs':  'javascript',
        '.jsx':  'javascript',
        '.ts':   'typescript',
        '.tsx':  'typescript',
        '.mts':  'typescript',
        '.json': 'json',
        '.jsonl': 'json',
        '.jsonc': 'json',
        '.yaml': 'yaml',
        '.yml':  'yaml',
        '.toml': 'toml',
        '.html': 'html',
        '.htm':  'html',
        '.xml':  'xml',
        '.css':  'css',
        '.sh':   'shell',
        '.bash': 'shell',
        '.zsh':  'shell',
        '.sql':  'sql',
        '.md':   None,    # 不检查
        '.txt':  None,
        '.csv':  None,
        '.log':  None,
        '.gitignore': None,
        '.env':  None,
    }

    def _get_lang(self, filepath: str) -> Optional[str]:
        """根据文件扩展名获取语言类型，None 表示跳过检查"""
        _, ext = os.path.splitext(filepath.lower())
        return self._CODE_EXTENSIONS.get(ext)

    def _is_code_file(self, filepath: str) -> bool:
        """判断是否是需要语法检查的代码文件"""
        lang = self._get_lang(filepath)
        return lang is not None

    def _check_syntax(self, filepath: str) -> str:
        """
        检查文件语法，返回结果字符串。
        - 通过: 返回空字符串 ""
        - 失败: 返回详细的错误信息
        - 跳过: 返回 None
        """
        lang = self._get_lang(filepath)
        if lang is None:
            return None  # 非代码文件，跳过

        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
        except (UnicodeDecodeError, PermissionError):
            return None

        if not source.strip():
            return None  # 空文件跳过

        if lang == 'python':
            return self._check_python_syntax(filepath, source)
        elif lang == 'javascript':
            return self._check_js_syntax(filepath, source)
        elif lang == 'typescript':
            return self._check_ts_syntax(filepath, source)
        elif lang == 'json':
            return self._check_json_syntax(filepath, source)
        elif lang == 'yaml':
            return self._check_yaml_syntax(filepath, source)
        elif lang == 'toml':
            return self._check_toml_syntax(filepath, source)
        elif lang == 'html':
            return self._check_html_syntax(filepath, source)
        elif lang == 'xml':
            return self._check_xml_syntax(filepath, source)
        elif lang == 'css':
            return self._check_css_syntax(filepath, source)
        elif lang == 'shell':
            return self._check_shell_syntax(filepath, source)
        elif lang == 'sql':
            return self._check_sql_syntax(filepath, source)
        return None

    def _check_python_syntax(self, filepath: str, source: str) -> str:
        """Python 语法检查：ast.parse + py_compile 双重验证"""
        errors = []

        # 方法1: ast.parse（更精确的错误定位）
        try:
            tree = ast.parse(source, filename=filepath)
        except SyntaxError as e:
            lineno = e.lineno or 0
            offset = e.offset or 0
            text = (e.text or '').rstrip()
            msg = e.msg or 'syntax error'
            pointer = ' ' * (offset - 1) + '^' if offset > 0 else ''
            errors.append(
                f"  第 {lineno} 行, 列 {offset}: {msg}\n"
                f"    {text}\n"
                f"    {pointer}"
            )

        # 方法2: py_compile（捕获 ast.parse 可能遗漏的问题）
        if not errors:
            try:
                py_compile.compile(filepath, doraise=True)
            except py_compile.PyCompileError as e:
                errors.append(f"  编译错误: {e}")

        if errors:
            return f" Python 语法检查失败 ({filepath}):\n" + "\n".join(errors)
        return ""

    def _check_js_syntax(self, filepath: str, source: str) -> str:
        """JavaScript 语法检查：使用 Node.js --check"""
        try:
            result = subprocess.run(
                [sys.executable, '-c', f'''
import json, sys
# 基础 JS 语法检查：括号匹配
source = {json.dumps(source)}
errors = []
stack = []
pairs = {{'(': ')', '[': ']', '{{': '}}'}}
close_to_open = {{v: k for k, v in pairs.items()}}
line = 1
col = 0
in_string = None
in_comment = False
in_block_comment = False
prev = ''
for i, ch in enumerate(source):
    col += 1
    if ch == '\\n':
        line += 1
        col = 0
        in_comment = False
        continue
    if in_block_comment:
        if prev == '*' and ch == '/':
            in_block_comment = False
        prev = ch
        continue
    if in_comment:
        prev = ch
        continue
    if prev == '/' and ch == '/':
        in_comment = True
        prev = ch
        continue
    if prev == '/' and ch == '*':
        in_block_comment = True
        prev = ch
        continue
    if ch in ('"', "'", '`'):
        if in_string == ch:
            in_string = None
        elif not in_string:
            in_string = ch
        prev = ch
        continue
    if in_string:
        prev = ch
        continue
    if ch in pairs:
        stack.append((ch, line, col))
    elif ch in close_to_open:
        if stack and stack[-1][0] == close_to_open[ch]:
            stack.pop()
        else:
            errors.append(f"  第 {{line}} 行, 列 {{col}}: 不匹配的闭合括号 '{{ch}}'")
    prev = ch
for open_ch, line, col in stack:
    errors.append(f"  第 {{line}} 行, 列 {{col}}: 未闭合的括号 '{{open_ch}}'")
if errors:
    print("ERROR:" + "\\n".join(errors))
else:
    print("OK")
'''],
                capture_output=True, text=True, timeout=5
            )
            output = result.stdout.strip()
            if output.startswith("ERROR:"):
                return f" JavaScript 语法检查失败 ({filepath}):\n" + output[6:]
        except Exception:
            pass
        return ""

    def _check_ts_syntax(self, filepath: str, source: str) -> str:
        """TypeScript 语法检查：尝试 tsc --noEmit，回退到 JS 检查"""
        try:
            result = subprocess.run(
                ['npx', 'tsc', '--noEmit', '--pretty', 'false', filepath],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0 and result.stderr.strip():
                errors = []
                for line in result.stderr.strip().split('\n')[:10]:
                    if 'error TS' in line:
                        errors.append(f"  {line.strip()}")
                if errors:
                    return f" TypeScript 语法检查失败 ({filepath}):\n" + "\n".join(errors)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        # 回退到 JS 括号检查
        return self._check_js_syntax(filepath, source)

    def _check_json_syntax(self, filepath: str, source: str) -> str:
        """JSON 语法检查"""
        try:
            json.loads(source)
        except json.JSONDecodeError as e:
            lineno = e.lineno or 0
            colno = e.colno or 0
            return (
                f" JSON 语法检查失败 ({filepath}):\n"
                f"  第 {lineno} 行, 列 {colno}: {e.msg}\n"
                f"    文档位置: 字符 {e.pos}"
            )
        return ""

    def _check_yaml_syntax(self, filepath: str, source: str) -> str:
        """YAML 语法检查"""
        try:
            import yaml
            list(yaml.safe_load_all(source))
        except ImportError:
            # 无 PyYAML，用基础检查
            if source.strip().startswith('{') or source.strip().startswith('['):
                return self._check_json_syntax(filepath, source)
        except yaml.YAMLError as e:
            mark = getattr(e, 'problem_mark', None)
            if mark:
                return (
                    f" YAML 语法检查失败 ({filepath}):\n"
                    f"  第 {mark.line + 1} 行, 列 {mark.column + 1}: {getattr(e, 'problem', str(e))}"
                )
            return f" YAML 语法检查失败 ({filepath}):\n  {e}"
        return ""

    def _check_toml_syntax(self, filepath: str, source: str) -> str:
        """TOML 语法检查"""
        try:
            import tomllib
            tomllib.loads(source)
        except ImportError:
            pass  # Python < 3.11 无 tomllib
        except Exception as e:
            return f" TOML 语法检查失败 ({filepath}):\n  {e}"
        return ""

    def _check_html_syntax(self, filepath: str, source: str) -> str:
        """HTML 基础检查：标签匹配"""
        errors = []
        import re as _re
        # 匹配开闭标签
        tag_pattern = _re.compile(r'<(/?)(\w+)[^>]*>')
        void_tags = {'br', 'hr', 'img', 'input', 'meta', 'link', 'area',
                     'base', 'col', 'embed', 'source', 'track', 'wbr'}
        stack = []
        for m in tag_pattern.finditer(source):
            is_close = m.group(1) == '/'
            tag_name = m.group(2).lower()
            if tag_name in void_tags:
                continue
            pos = m.start()
            line_num = source[:pos].count('\n') + 1
            if is_close:
                if stack and stack[-1][0] == tag_name:
                    stack.pop()
                elif stack:
                    errors.append(
                        f"  第 {line_num} 行: </{tag_name}> 与 <{stack[-1][0]}> 不匹配"
                    )
            else:
                stack.append((tag_name, line_num))
        for tag_name, line_num in stack:
            errors.append(f"  第 {line_num} 行: <{tag_name}> 未闭合")
        if errors and len(errors) <= 10:
            return f" HTML 标签检查 ({filepath}):\n" + "\n".join(errors)
        return ""

    def _check_xml_syntax(self, filepath: str, source: str) -> str:
        """XML 语法检查：使用 xml.etree"""
        import xml.etree.ElementTree as ET
        try:
            ET.fromstring(source)
        except ET.ParseError as e:
            return f" XML 语法检查失败 ({filepath}):\n  {e}"
        return ""

    def _check_css_syntax(self, filepath: str, source: str) -> str:
        """CSS 基础检查：花括号匹配"""
        errors = []
        depth = 0
        in_string = False
        string_char = None
        line_num = 1
        for i, ch in enumerate(source):
            if ch == '\n':
                line_num += 1
                continue
            if in_string:
                if ch == string_char and (i == 0 or source[i-1] != '\\'):
                    in_string = False
                continue
            if ch in ('"', "'"):
                in_string = True
                string_char = ch
                continue
            if ch == '{':
                depth += 1
            elif ch == '}':
                if depth > 0:
                    depth -= 1
                else:
                    errors.append(f"  第 {line_num} 行: 多余的闭合花括号 '}}'")
        if depth > 0:
            errors.append(f"  文件末尾: {depth} 个未闭合的花括号 '{{' ")
        if errors:
            return f" CSS 括号检查 ({filepath}):\n" + "\n".join(errors)
        return ""

    def _check_shell_syntax(self, filepath: str, source: str) -> str:
        """Shell 脚本语法检查：使用 bash -n"""
        try:
            result = subprocess.run(
                ['bash', '-n', filepath],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                stderr = result.stderr.strip()
                lines = stderr.split('\n')[:5]
                return f" Shell 语法检查失败 ({filepath}):\n" + "\n".join(f"  {l}" for l in lines)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return ""

    def _check_sql_syntax(self, filepath: str, source: str) -> str:
        """SQL 基础检查：关键字匹配"""
        # 简单检查未闭合的引号和括号
        errors = []
        single_q = double_q = 0
        paren_depth = 0
        line_num = 1
        for ch in source:
            if ch == '\n':
                line_num += 1
                continue
            if ch == "'":
                single_q += 1
            elif ch == '"':
                double_q += 1
            elif ch == '(':
                paren_depth += 1
            elif ch == ')':
                paren_depth -= 1
        if single_q % 2 != 0:
            errors.append("  存在未闭合的单引号")
        if double_q % 2 != 0:
            errors.append("  存在未闭合的双引号")
        if paren_depth > 0:
            errors.append(f"  存在 {paren_depth} 个未闭合的括号")
        if errors:
            return f" SQL 检查 ({filepath}):\n" + "\n".join(errors)
        return ""

    def _auto_syntax_check(self, filepath: str) -> str:
        """
        编辑操作后自动语法检查。
        返回格式化的结果字符串，供拼接到操作结果末尾。
        - 通过: 返回简短成功提示
        - 失败: 返回详细错误信息
        - 跳过: 返回空字符串
        """
        result = self._check_syntax(filepath)
        if result is None:
            return ""  # 非代码文件，不检查
        if result == "":
            return f"\n  语法检查通过 ✓"
        else:
            return f"\n{result}"

    def _auto_lsp_check(self, filepath: str) -> str:
        """写/改文件后自动让已连接的语言服务器(pylsp 等)重新诊断该文件。

        诊断结果会被缓存进 LSP 管理器的 _workspace_diag，由 get_lsp_context()
        在下一轮静默注入模型上下文；同时仅在确有问题时给一行可见提示。
        无对应 server / 文件干净时静默跳过，绝不影响主流程。
        """
        manager = None
        try:
            cli = self.cli
            utm = getattr(cli, 'liugin_manager', None)
            if utm is not None:
                manager = getattr(utm, '_lsp_manager', None)
        except Exception:
            manager = None
        if manager is None:
            return ""
        try:
            diag_text = manager.diagnostics(filepath, wait=1.5)
        except Exception:
            return ""
        if not diag_text or "没有为" in diag_text:
            return ""  # 该扩展名未配置 LSP server，跳过
        if "无诊断" in diag_text:
            return ""  # 干净，无需呈现（缓存也为空）
        first = diag_text.splitlines()[0] if diag_text else ""
        return f"\n  LSP 诊断: {first}"

    # ══════════════════════════════════════
    #  Diff 弹窗系统
    # ══════════════════════════════════════

    def _read_file_safe(self, filepath: str) -> str:
        """安全读取文件，失败返回空字符串"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ""

    def _spawn_diff_popup(self, filepath: str, before: str, after: str):
        """
        显示修改前后的对比。
        根据 diff_popup_mode 决定弹窗还是主终端内显示。
        """
        if not self.diff_popup_enabled:
            return
        if before == after:
            return  # 内容无变化，不弹窗

        # 启动时未选择模式，默认为主终端内显示（SSH 兼容）
        popup = self.diff_popup_mode if self.diff_popup_mode is not None else False

        if popup:
            thread = threading.Thread(
                target=self._do_spawn_diff_popup,
                args=(filepath, before, after),
                daemon=True
            )
            thread.start()
        else:
            self._show_inline_diff(filepath, before, after)

    def _do_spawn_diff_popup(self, filepath: str, before: str, after: str):
        """实际执行弹窗创建（在子线程中运行）"""
        basename = os.path.basename(filepath)

        # 生成带行号的 before/after
        before_numbered = self._number_lines(before)
        after_numbered = self._number_lines(after)

        # 生成 diff
        diff_lines = list(difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"修改前: {basename}",
            tofile=f"修改后: {basename}",
            lineterm=''
        ))

        # 统计变更
        added = sum(1 for l in diff_lines if l.startswith('+') and not l.startswith('+++'))
        removed = sum(1 for l in diff_lines if l.startswith('-') and not l.startswith('---'))

        before_count = len(before.splitlines())
        after_count = len(after.splitlines())

        # 构建弹窗显示内容
        display = self._build_diff_display(
            basename, filepath,
            before_numbered, after_numbered,
            diff_lines, added, removed,
            before_count, after_count
        )

        # 写入临时脚本并弹出
        self._launch_popup_window(display, basename)

    def _number_lines(self, content: str) -> str:
        """给内容加上行号"""
        lines = content.splitlines()
        width = len(str(len(lines)))
        return '\n'.join(f"{i+1:>{width}} | {line}" for i, line in enumerate(lines))

    def _build_diff_display(self, basename, filepath,
                             before_numbered, after_numbered,
                             diff_lines, added, removed,
                             before_count, after_count):
        """构建完整的 diff 显示文本（带 ANSI 颜色）"""
        sep = '═' * 70
        thin_sep = '─' * 70

        # ANSI 颜色
        R = '\033[31m'   # 红字
        G = '\033[32m'   # 绿字
        C = '\033[36m'   # 青
        B = '\033[1m'    # 粗体
        D = '\033[2m'    # 暗
        W = '\033[37m'   # 白
        N = '\033[0m'    # 重置
        RBG = '\033[41m\033[97m'  # 红底白字
        GBG = '\033[42m\033[97m'  # 绿底白字

        # 构建带颜色的 diff
        diff_colored_lines = []
        for line in diff_lines:
            if line.startswith('@@'):
                diff_colored_lines.append(f"{C}{line}{N}")
            elif line.startswith('+++') or line.startswith('---'):
                diff_colored_lines.append(f"{B}{line}{N}")
            elif line.startswith('+'):
                diff_colored_lines.append(f"{GBG} {line} {N}")
            elif line.startswith('-'):
                diff_colored_lines.append(f"{RBG} {line} {N}")
            else:
                diff_colored_lines.append(line)
        diff_colored = '\n'.join(diff_colored_lines) if diff_colored_lines else '  (无差异)'

        display = f"""
{W}{sep}{N}
{B}  文件变更对比: {basename}{N}
{D}  路径: {filepath}{N}
{W}{sep}{N}

  统计: {before_count} 行 → {after_count} 行  |  {G}+{added} 新增{N}  {R}-{removed} 删除{N}

{W}{thin_sep}{N}
  修改前 ({before_count} 行):
{W}{thin_sep}{N}
{before_numbered}

{W}{thin_sep}{N}
  修改后 ({after_count} 行):
{W}{thin_sep}{N}
{after_numbered}

{W}{thin_sep}{N}
  差异 (Diff):
{W}{thin_sep}{N}
{diff_colored}

{W}{sep}{N}
  按任意键关闭此窗口...
{W}{sep}{N}
"""
        return display

    def _launch_popup_window(self, display_text: str, title: str):
        """根据平台弹出新终端窗口"""
        # 写入临时显示脚本
        try:
            script_fd, script_path = tempfile.mkstemp(suffix='.py', prefix='xiaoli_diff_')
            with os.fdopen(script_fd, 'w', encoding='utf-8') as f:
                # 写入显示内容到脚本
                escaped = display_text.replace('\\', '\\\\').replace("'", "\\'")
                f.write(f"#!/usr/bin/env python3\n")
                f.write(f"# -*- coding: utf-8 -*-\n")
                f.write(f"import sys\n")
                f.write(f"text = '''{escaped}'''\n")
                f.write(f"try:\n")
                f.write(f"    sys.stdout.reconfigure(encoding='utf-8')\n")
                f.write(f"except Exception:\n")
                f.write(f"    pass\n")
                f.write(f"print(text)\n")
                f.write(f"try:\n")
                f.write(f"    input()\n")
                f.write(f"except (EOFError, KeyboardInterrupt):\n")
                f.write(f"    pass\n")

            system = platform.system()

            if system == 'Windows':
                # Windows: 新开 cmd 窗口
                subprocess.Popen(
                    ['cmd', '/c', 'start', 'cmd', '/k', sys.executable, script_path],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    shell=False
                )
            elif system == 'Darwin':
                # macOS: 用 osascript 打开 Terminal.app
                apple_script = (
                    f'tell application "Terminal"\n'
                    f'    activate\n'
                    f'    do script "{sys.executable} {script_path}"\n'
                    f'end tell'
                )
                subprocess.Popen(['osascript', '-e', apple_script])
            else:
                # Linux: 尝试多个终端模拟器
                terminals = [
                    ['gnome-terminal', '--', sys.executable, script_path],
                    ['xterm', '-e', sys.executable, script_path],
                    ['konsole', '-e', sys.executable, script_path],
                    ['xfce4-terminal', '-e', f'{sys.executable} {script_path}'],
                    ['lxterminal', '-e', sys.executable, script_path],
                    ['mate-terminal', '-e', sys.executable, script_path],
                ]
                launched = False
                for cmd in terminals:
                    try:
                        subprocess.Popen(cmd, start_new_session=True)
                        launched = True
                        break
                    except FileNotFoundError:
                        continue
                if not launched:
                    # 兜底: 用 xdg-open 不太行，直接打印到当前终端
                    print(f"\n[Diff 弹窗] 无可用终端模拟器，直接输出:\n")
                    print(display_text)
                    try:
                        os.unlink(script_path)
                    except Exception:
                        pass

        except Exception as e:
            print(f"[Diff 弹窗] 创建失败: {e}")

    def _show_inline_diff(self, filepath: str, before: str, after: str):
        """在主终端内显示 diff（SSH 兼容模式），带颜色"""
        basename = os.path.basename(filepath)
        is_tui = self.cli and getattr(self.cli, 'tui_output_callback', None)

        # 生成 diff
        diff_lines = list(difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"修改前: {basename}",
            tofile=f"修改后: {basename}",
            lineterm=''
        ))

        # 统计
        added = sum(1 for l in diff_lines if l.startswith('+') and not l.startswith('+++'))
        removed = sum(1 for l in diff_lines if l.startswith('-') and not l.startswith('---'))
        before_count = len(before.splitlines())
        after_count = len(after.splitlines())

        sep = '═' * 60
        thin = '─' * 60

        if is_tui:
            # TUI 模式：使用 Rich 标记
            output = self.cli._output
            output(f"[dim]{sep}[/]")
            output(f"[bold cyan]  文件变更: {basename}[/]  [dim]{filepath}[/]")
            output(f"[dim]{sep}[/]")
            output(f"[bold]  统计: {before_count} 行 → {after_count} 行  |  "
                   f"[green]+{added} 新增[/]  [red]-{removed} 删除[/]")
            output(f"[dim]{thin}[/]")

            for line in diff_lines:
                if line.startswith('@@'):
                    output(f"[cyan]{line}[/]")
                elif line.startswith('+++') or line.startswith('---'):
                    output(f"[bold]{line}[/]")
                elif line.startswith('+'):
                    output(f"[white on green] {line} [/]")
                elif line.startswith('-'):
                    output(f"[white on red] {line} [/]")
                else:
                    output(line)

            output(f"[dim]{sep}[/]")
        else:
            # CLI 模式：使用 ANSI 颜色
            from colorama import Fore, Style
            _out = print

            _out(f"{Fore.WHITE}{sep}{Style.RESET_ALL}")
            _out(f"{Fore.CYAN}  文件变更: {basename}{Style.RESET_ALL}  {filepath}")
            _out(f"{Fore.WHITE}{sep}{Style.RESET_ALL}")
            _out(f"  统计: {before_count} 行 → {after_count} 行  |  "
                 f"{Fore.GREEN}+{added} 新增{Style.RESET_ALL}  "
                 f"{Fore.RED}-{removed} 删除{Style.RESET_ALL}")
            _out(f"{Fore.WHITE}{thin}{Style.RESET_ALL}")

            for line in diff_lines:
                if line.startswith('@@'):
                    _out(f"{Fore.CYAN}{line}{Style.RESET_ALL}")
                elif line.startswith('+++') or line.startswith('---'):
                    _out(f"{Style.BRIGHT}{line}{Style.RESET_ALL}")
                elif line.startswith('+'):
                    _out(f"\033[42m\033[97m {line} {Style.RESET_ALL}")
                elif line.startswith('-'):
                    _out(f"\033[41m\033[97m {line} {Style.RESET_ALL}")
                else:
                    _out(line)

            _out(f"{Fore.WHITE}{sep}{Style.RESET_ALL}")

    def _op_diff_popup(self, path: str, rest: str) -> str:
        """切换 diff 弹窗开关 / 设置显示模式"""
        arg = (path + ' ' + rest).strip().lower()
        if arg in ('on', '开', '开启', 'enable', '1', 'true'):
            self.diff_popup_enabled = True
            return "  Diff 弹窗已开启"
        elif arg in ('off', '关', '关闭', 'disable', '0', 'false'):
            self.diff_popup_enabled = False
            return "  Diff 弹窗已关闭"
        elif arg in ('popup', '弹窗', '弹窗模式'):
            self.diff_popup_enabled = True
            self.diff_popup_mode = True
            return "  Diff 模式: 弹窗（新终端窗口）"
        elif arg in ('inline', '内联', 'ssh', '终端', '主终端'):
            self.diff_popup_enabled = True
            self.diff_popup_mode = False
            return "  Diff 模式: 主终端内显示（SSH 兼容）"
        else:
            # 无参数：切换状态
            self.diff_popup_enabled = not self.diff_popup_enabled
            state = "开启" if self.diff_popup_enabled else "关闭"
            return f"  Diff 弹窗: {state}"

    def _op_syntax_check(self, path: str, rest: str) -> str:
        """主动语法检查操作"""
        if not path:
            return "错误：请提供文件路径。用法: syntax_check <文件路径>"
        fp = self._norm(path)
        if not os.path.exists(fp):
            return f"错误：文件不存在: {fp}"

        lang = self._get_lang(fp)
        if lang is None:
            return f"⏭ 跳过: {fp} (不支持的文件类型，无需语法检查)"

        result = self._check_syntax(fp)
        if result is None:
            return f"⏭ 跳过: {fp} (无法读取文件)"
        if result == "":
            return f"  语法检查通过 ✓ ({fp})\n  语言: {lang}"
        else:
            return result

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

        before_content = content  # 保存修改前内容
        new_content = content.replace(old_text, new_text, 1)
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(new_content)

        self._spawn_diff_popup(fp, before_content, new_content)
        result = f" 已编辑: {fp}\n\n{self._make_diff(old_text, new_text)}"
        result += self._auto_syntax_check(fp) + self._auto_lsp_check(fp)
        return result

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

        before_content = content  # 保存修改前内容
        results = []
        for i, op in enumerate(ops):
            old = op.get("old", "").strip()
            new = op.get("new", "").strip()
            if not old:
                results.append(f"   操作 {i+1}: old 为空")
            elif old not in content:
                results.append(f"   操作 {i+1}: 未找到匹配")
            else:
                content = content.replace(old, new, 1)
                results.append(f"   操作 {i+1}: 已替换")

        with open(fp, 'w', encoding='utf-8') as f:
            f.write(content)
        self._spawn_diff_popup(fp, before_content, content)
        result = f" 批量编辑: {fp}\n" + "\n".join(results)
        result += self._auto_syntax_check(fp) + self._auto_lsp_check(fp)
        return result

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

        before_content = ''.join(lines)  # 保存修改前内容
        insert_lines = [l + '\n' for l in parts[1].strip().split('\n')]
        lines[line_num-1:line_num-1] = insert_lines

        with open(fp, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        after_content = ''.join(lines)
        self._spawn_diff_popup(fp, before_content, after_content)
        result = f" 已在第 {line_num} 行插入 {len(insert_lines)} 行"
        result += self._auto_syntax_check(fp) + self._auto_lsp_check(fp)
        return result

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

        before_content = ''.join(lines)  # 保存修改前内容
        deleted = lines[start-1:end]
        lines[start-1:end] = []

        with open(fp, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        after_content = ''.join(lines)
        self._spawn_diff_popup(fp, before_content, after_content)
        result = f" 已删除第 {start}-{end} 行 ({len(deleted)} 行)"
        result += self._auto_syntax_check(fp) + self._auto_lsp_check(fp)
        return result

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
        self._spawn_diff_popup(fp, "", rest or "")
        result = f" 已创建: {fp} ({len(rest or '')} 字符)"
        result += self._auto_syntax_check(fp) + self._auto_lsp_check(fp)
        return result

    def _op_write(self, path: str, rest: str) -> str:
        if not path:
            return "错误：请提供文件路径"
        fp = self._norm(path)
        dir_path = os.path.dirname(fp)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        before_content = self._read_file_safe(fp)  # 保存修改前内容
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(rest)
        self._spawn_diff_popup(fp, before_content, rest)
        result = f" 已写入: {fp} ({len(rest)} 字符)"
        result += self._auto_syntax_check(fp) + self._auto_lsp_check(fp)
        return result

    def _op_append(self, path: str, rest: str) -> str:
        if not path:
            return "错误：请提供文件路径"
        fp = self._norm(path)
        if not os.path.exists(fp):
            return f"错误：文件不存在: {fp}"
        before_content = self._read_file_safe(fp)  # 保存修改前内容
        with open(fp, 'a', encoding='utf-8') as f:
            f.write(rest)
        after_content = self._read_file_safe(fp)
        self._spawn_diff_popup(fp, before_content, after_content)
        result = f" 已追加: {fp} ({len(rest)} 字符)"
        result += self._auto_syntax_check(fp) + self._auto_lsp_check(fp)
        return result

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
        return f" {fp} (第 {start}-{end} 行，共 {total} 行)\n{'─'*60}\n" + '\n'.join(numbered)

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

        info = [f" {fp} AST 摘要:"]
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

        return '\n'.join(info) if len(info) > 1 else f" {fp}: 文件为空"

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
        return f" 搜索 '{keyword}' ({len(results)}{'+' if len(results) >= 80 else ''} 匹配):\n" + '\n'.join(results)

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
        return f" 正则搜索 ({len(results)}{'+' if len(results) >= 50 else ''} 匹配):\n" + '\n'.join(results)

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
                    all_symbols.append(f"\n {rel}:")
                    all_symbols.extend(symbols)
            except (SyntaxError, UnicodeDecodeError):
                continue

        return " 代码符号:\n" + '\n'.join(all_symbols) if all_symbols else "未找到 Python 符号"

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

        return f" {file_path} 导入:\n" + '\n'.join(imports) if imports else f" {file_path}: 没有导入"

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

        return f" '{func_name}' 的调用 ({len(results)}):\n" + '\n'.join(results) if results else f"未找到调用 '{func_name}'"

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

        return f" TODO/FIXME ({len(results)}):\n" + '\n'.join(results) if results else "没有 TODO/FIXME"

    def _op_structure(self, directory: str, rest: str) -> str:
        if not directory:
            return "错误：请提供目录路径"
        search_dir = self._norm(directory)
        if not os.path.isdir(search_dir):
            return f"错误：目录不存在: {search_dir}"

        max_depth = int(rest) if rest.strip().isdigit() else 3
        lines = [f" {os.path.basename(search_dir)}/"]
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

        result = [f" {path} 第 {start}-{end} 行 (目标: 第 {line_num} 行):", "─" * 60]
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

        return (f" 代码统计 ({search_dir}):\n"
                f"  文件: {len(files)}\n"
                f"  总行: {total}\n"
                f"  代码: {code}\n"
                f"  注释: {comment}\n"
                f"  空行: {blank}\n"
                f"  注释率: {comment/max(code,1)*100:.1f}%")
