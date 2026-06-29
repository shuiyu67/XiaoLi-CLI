"""
编译验证插件 - 批量语法/编译检查
对项目内 Python 文件做 ast.parse + py_compile 双重验证，
支持按目录、单文件或全项目扫描，并发执行加速。
"""
import os
import sys
import ast
import time
import shutil
import py_compile
import concurrent.futures
from pathlib import Path
from typing import List, Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from xcli_core.tool_result import ToolResult, ErrorCode

try:
    from colorama import Fore, Style, init as _colorama_init
    _colorama_init(autoreset=False)
    _HAS_COLOR = True
except Exception:
    _HAS_COLOR = False

    class _Stub:
        def __getattr__(self, _): return ""
    Fore = Style = _Stub()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SKIP_DIRS = {
    "__pycache__", ".git", ".venv", "venv", "env", ".env",
    "node_modules", ".idea", ".vscode", "dist", "build",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "site-packages",
}

SKIP_FILES = {
    "setup.py",
}


class Liugin:
    """编译验证 - 批量语法检查 / 编译验证 / 清理 __pycache__"""

    def __init__(self):
        self.usage = """编译验证工具

操作:
  all                          - 验证项目内全部 Python 文件
  core                         - 仅验证 xcli_core/ 目录
  engines                      - 仅验证 ai_engines/ 目录
  plugins                      - 仅验证 plugins/ 目录
  dir <目录>                   - 验证指定目录
  check <文件>                 - 验证单个文件 (可多次指定)
  clean [目录]                 - 清理 __pycache__ (默认项目根)
  stats                        - 统计各目录 Python 文件数量

选项:
  -v / --verbose               - 显示每个文件的结果
  -j / --jobs <N>              - 并发线程数 (默认 8)
  -q / --quiet                 - 仅在结束时打印汇总

输出:
  ✅ 绿色 = 通过
  ❌ 红色 = 失败
  汇总: 总数/通过/失败 + 失败文件详情

示例:
  check all -v
  check core
  check plugins/compile_check.py
  check dir ai_engines -j 16
  check clean
"""
        self.cli = None

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "compile_check",
            "description": "编译验证工具 — 批量语法/编译检查(ast.parse + py_compile)，支持目录、单文件、全项目扫描，并发加速，清理 __pycache__",
            "keywords": ["编译", "验证", "语法", "检查", "compile", "syntax",
                         "check", "lint", "py_compile", "ast", "批量",
                         "validate", "verify", "clean", "pycache"],
            "usage": self.usage,
        }

    def get_mcp_definition(self):
        return {
            "name": "compile_check",
            "description": "编译验证工具",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["all", "core", "engines", "plugins",
                                 "dir", "check", "clean", "stats"],
                        "description": "操作类型"
                    },
                    "path": {"type": "string",
                             "description": "目录或文件路径"},
                    "paths": {"type": "array",
                              "items": {"type": "string"},
                              "description": "多文件路径列表"},
                    "verbose": {"type": "boolean", "default": False},
                    "jobs": {"type": "integer", "default": 8},
                    "quiet": {"type": "boolean", "default": False},
                },
                "required": ["operation"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        path = arguments.get("path", "")
        return f"{op} {path}".strip()

    def handle(self, args: str):
        try:
            parts = self._parse_args(args)
            if not parts:
                return self._print_usage()

            operation = parts[0].lower()
            opts = self._extract_options(parts[1:])

            if operation in ("help", "-h", "--help"):
                return self._print_usage()

            routes = {
                "all": self._op_all,
                "core": self._op_core,
                "engines": self._op_engines,
                "plugins": self._op_plugins,
                "dir": self._op_dir,
                "check": self._op_check,
                "clean": self._op_clean,
                "stats": self._op_stats,
            }
            handler = routes.get(operation)
            if not handler:
                return ToolResult.fail(
                    f"不支持的操作 '{operation}'",
                    ErrorCode.UNSUPPORTED_OP,
                    tool_name="compile_check",
                )
            return handler(opts)

        except Exception as e:
            return ToolResult.fail(
                f"编译验证错误: {e}",
                ErrorCode.EXEC_FAILED,
                tool_name="compile_check",
            )

    def _print_usage(self):
        self._emit(self.usage)
        return ToolResult.ok("usage_printed", tool_name="compile_check")

    def _out(self, msg: str):
        """统一输出，适配 TUI/CLI"""
        if self.cli is not None and hasattr(self.cli, "_output"):
            self.cli._output(msg)
        else:
            print(msg)

    def _emit(self, msg: str, end: str = "\n"):
        """统一输出，自动适配 TUI/CLI

        - TUI 模式: 一行一行输出到 _output，忽略 end（TUI 有自己的状态指示器）
        - CLI 模式: 尊重 end，支持 end="" 的进度条刷新
        - TUI 模式下 end != "\\n" 的进度条输出直接跳过（避免污染对话区）
        """
        if self.cli is not None and hasattr(self.cli, "_output"):
            if end != "\n":
                return  # TUI 模式跳过进度条类输出
            self.cli._output(msg)
        else:
            print(msg, end=end)

    def _ok(self, msg: str) -> str:
        return f"{Fore.GREEN}{msg}{Style.RESET_ALL}"

    def _err(self, msg: str) -> str:
        return f"{Fore.RED}{msg}{Style.RESET_ALL}"

    def _warn(self, msg: str) -> str:
        return f"{Fore.YELLOW}{msg}{Style.RESET_ALL}"

    def _dim(self, msg: str) -> str:
        return f"{Fore.CYAN}{msg}{Style.RESET_ALL}"

    def _banner(self, title: str) -> str:
        bar = "═" * max(20, len(title) + 4)
        return f"{Fore.CYAN}{bar}\n  {title}\n{bar}{Style.RESET_ALL}"

    def _parse_args(self, args: str) -> List[str]:
        parts, current, in_quotes, qc = [], "", False, None
        for ch in args:
            if ch in ('"', "'") and not in_quotes:
                in_quotes, qc = True, ch
            elif ch == qc and in_quotes:
                in_quotes, qc = False, None
            elif ch == " " and not in_quotes:
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += ch
        if current:
            parts.append(current)
        return parts

    def _extract_options(self, args: List[str]) -> dict:
        opts = {
            "positional": [],
            "verbose": False,
            "quiet": False,
            "jobs": 8,
        }
        i = 0
        while i < len(args):
            a = args[i]
            if a in ("-v", "--verbose"):
                opts["verbose"] = True
            elif a in ("-q", "--quiet"):
                opts["quiet"] = True
            elif a in ("-j", "--jobs") and i + 1 < len(args):
                try:
                    opts["jobs"] = max(1, int(args[i + 1]))
                except ValueError:
                    pass
                i += 1
            elif not a.startswith("-"):
                opts["positional"].append(a)
            i += 1
        return opts

    def _collect_py_files(self, root: str) -> List[str]:
        root = os.path.abspath(root)
        if not os.path.isdir(root):
            return []
        result: List[str] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                if fn in SKIP_FILES:
                    continue
                result.append(os.path.join(dirpath, fn))
        result.sort()
        return result

    def _verify_one(self, filepath: str) -> Tuple[str, bool, str]:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                src = f.read()
        except UnicodeDecodeError:
            try:
                with open(filepath, "r", encoding="gbk") as f:
                    src = f.read()
            except Exception as e:
                return filepath, False, f"读取失败: {e}"
        except Exception as e:
            return filepath, False, f"读取失败: {e}"

        try:
            ast.parse(src, filename=filepath)
        except SyntaxError as e:
            line = getattr(e, "lineno", "?")
            col = getattr(e, "offset", "?")
            msg = getattr(e, "msg", str(e))
            return filepath, False, f"SyntaxError 第{line}行第{col}列: {msg}"

        try:
            py_compile.compile(filepath, doraise=True, quiet=2)
        except py_compile.PyCompileError as e:
            return filepath, False, f"PyCompileError: {e.msg if hasattr(e, 'msg') else e}"
        except Exception as e:
            return filepath, False, f"编译失败: {e}"

        return filepath, True, ""

    def _run_batch(
        self,
        files: List[str],
        title: str,
        verbose: bool = False,
        quiet: bool = False,
        jobs: int = 8,
    ) -> Tuple[int, int, List[Tuple[str, str]]]:
        total = len(files)
        if total == 0:
            self._emit(self._warn(f"{title}: 没有可验证的 Python 文件"))
            return 0, 0, []

        if not quiet:
            self._emit(self._banner(f"{title}  ({total} 个文件, {jobs} 线程)"))
            self._emit("")

        passed = 0
        failed: List[Tuple[str, str]] = []
        start = time.time()

        results: List[Tuple[str, bool, str]] = []
        if jobs == 1:
            for f in files:
                results.append(self._verify_one(f))
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as ex:
                futures = {ex.submit(self._verify_one, f): f for f in files}
                done = 0
                for fut in concurrent.futures.as_completed(futures):
                    results.append(fut.result())
                    done += 1
                    if not quiet and not verbose and total > 0:
                        pct = done * 100 // total
                        rel = os.path.relpath(futures[fut], PROJECT_ROOT)
                        self._emit(f"\r  进度: [{done}/{total}] {pct:3d}%  {rel[:40]:<40}", end="")
                if not quiet and not verbose:
                    self._emit("")

        results.sort(key=lambda x: x[0])

        if verbose and not quiet:
            self._emit("")

        for filepath, ok, err in results:
            rel = os.path.relpath(filepath, PROJECT_ROOT)
            if ok:
                passed += 1
                if verbose and not quiet:
                    self._emit(f"  {self._ok('✓')} {rel}")
            else:
                failed.append((rel, err))
                if not quiet:
                    self._emit(f"  {self._err('✗')} {rel}")
                    self._emit(f"      {self._err(err)}")

        elapsed = time.time() - start

        self._emit("")
        self._emit("─" * 60)
        if failed:
            self._emit(f"  {self._err('✗ 失败:')} {len(failed)}/{total}")
            self._emit(f"  {self._ok('✓ 通过:')} {passed}/{total}")
            self._emit(f"  {self._dim(f'耗时: {elapsed:.2f}s')}")
            self._emit("")
            self._emit(self._err("失败列表:"))
            for rel, err in failed:
                self._emit(f"  • {self._err(rel)}")
                first_line = err.split("\n")[0][:120]
                self._emit(f"      {first_line}")
        else:
            self._emit(f"  {self._ok(f'✓ 全部通过:')} {passed}/{total} 个文件")
            self._emit(f"  {self._dim(f'耗时: {elapsed:.2f}s')}")
        self._emit("─" * 60)

        return passed, len(failed), failed

    def _op_all(self, opts: dict):
        files = self._collect_py_files(PROJECT_ROOT)
        passed, failed, _ = self._run_batch(
            files,
            "全项目编译验证",
            verbose=opts["verbose"],
            quiet=opts["quiet"],
            jobs=opts["jobs"],
        )
        if failed == 0:
            return ToolResult.ok(
                f"全部通过 ({passed}/{passed})",
                tool_name="compile_check",
            )
        return ToolResult.fail(
            f"有 {failed} 个文件编译失败",
            ErrorCode.EXEC_FAILED,
            tool_name="compile_check",
        )

    def _op_core(self, opts: dict):
        return self._scan_subdir("xcli_core", "xcli_core 编译验证", opts)

    def _op_engines(self, opts: dict):
        return self._scan_subdir("ai_engines", "ai_engines 编译验证", opts)

    def _op_plugins(self, opts: dict):
        return self._scan_subdir("plugins", "plugins 编译验证", opts)

    def _scan_subdir(self, sub: str, title: str, opts: dict):
        target = os.path.join(PROJECT_ROOT, sub)
        if not os.path.isdir(target):
            return ToolResult.not_found(f"目录: {sub}", tool_name="compile_check")
        files = self._collect_py_files(target)
        passed, failed, _ = self._run_batch(
            files, title,
            verbose=opts["verbose"],
            quiet=opts["quiet"],
            jobs=opts["jobs"],
        )
        if failed == 0:
            return ToolResult.ok(
                f"{sub} 全部通过 ({passed})",
                tool_name="compile_check",
            )
        return ToolResult.fail(
            f"{sub} 有 {failed} 个文件编译失败",
            ErrorCode.EXEC_FAILED,
            tool_name="compile_check",
        )

    def _op_dir(self, opts: dict):
        if not opts["positional"]:
            return ToolResult.missing("目录路径", tool_name="compile_check")
        target = os.path.abspath(opts["positional"][0])
        if not os.path.isdir(target):
            return ToolResult.not_found(f"目录: {target}", tool_name="compile_check")
        files = self._collect_py_files(target)
        passed, failed, _ = self._run_batch(
            files,
            f"目录验证: {os.path.relpath(target, PROJECT_ROOT)}",
            verbose=opts["verbose"],
            quiet=opts["quiet"],
            jobs=opts["jobs"],
        )
        if failed == 0:
            return ToolResult.ok(
                f"目录全部通过 ({passed})",
                tool_name="compile_check",
            )
        return ToolResult.fail(
            f"目录有 {failed} 个文件编译失败",
            ErrorCode.EXEC_FAILED,
            tool_name="compile_check",
        )

    def _op_check(self, opts: dict):
        if not opts["positional"]:
            return ToolResult.missing("文件路径", tool_name="compile_check")

        targets = []
        for p in opts["positional"]:
            fp = os.path.abspath(p)
            if not os.path.isfile(fp):
                return ToolResult.not_found(
                    f"文件: {p}", tool_name="compile_check",
                )
            targets.append(fp)

        if len(targets) == 1:
            self._emit(self._banner(
                f"单文件验证: {os.path.relpath(targets[0], PROJECT_ROOT)}"
            ))
            filepath, ok, err = self._verify_one(targets[0])
            rel = os.path.relpath(filepath, PROJECT_ROOT)
            self._emit("")
            if ok:
                self._emit(f"  {self._ok('✓ 通过')} {rel}")
                self._emit("─" * 60)
                return ToolResult.ok(f"通过: {rel}", tool_name="compile_check")
            else:
                self._emit(f"  {self._err('✗ 失败')} {rel}")
                self._emit(f"      {self._err(err)}")
                self._emit("─" * 60)
                return ToolResult.fail(
                    f"编译失败: {rel}",
                    ErrorCode.EXEC_FAILED,
                    tool_name="compile_check",
                )

        passed, failed, _ = self._run_batch(
            targets,
            f"批量验证 ({len(targets)} 个文件)",
            verbose=opts["verbose"],
            quiet=opts["quiet"],
            jobs=opts["jobs"],
        )
        if failed == 0:
            return ToolResult.ok(
                f"全部通过 ({passed})",
                tool_name="compile_check",
            )
        return ToolResult.fail(
            f"有 {failed} 个文件编译失败",
            ErrorCode.EXEC_FAILED,
            tool_name="compile_check",
        )

    def _op_clean(self, opts: dict):
        target = PROJECT_ROOT
        if opts["positional"]:
            target = os.path.abspath(opts["positional"][0])
        if not os.path.isdir(target):
            return ToolResult.not_found(
                f"目录: {target}", tool_name="compile_check",
            )

        self._emit(self._banner(f"清理 __pycache__: {os.path.relpath(target, PROJECT_ROOT)}"))
        removed = 0
        for dirpath, dirnames, _ in os.walk(target):
            for d in list(dirnames):
                if d == "__pycache__":
                    full = os.path.join(dirpath, d)
                    try:
                        shutil.rmtree(full)
                        removed += 1
                        rel = os.path.relpath(full, PROJECT_ROOT)
                        if not opts["quiet"]:
                            self._emit(f"  {self._ok('✓ 已删除')} {rel}")
                    except Exception as e:
                        rel = os.path.relpath(full, PROJECT_ROOT)
                        self._emit(f"  {self._err('✗ 失败')} {rel}: {e}")
        self._emit("")
        self._emit("─" * 60)
        if removed:
            self._emit(f"  {self._ok(f'✓ 已清理')} {removed} 个 __pycache__")
        else:
            self._emit(f"  {self._dim('没有可清理的 __pycache__')}")
        self._emit("─" * 60)

        return ToolResult.ok(
            f"清理完成 ({removed} 个目录)",
            tool_name="compile_check",
        )

    def _op_stats(self, opts: dict):
        self._emit(self._banner("项目 Python 文件统计"))

        subdirs = [
            ("xcli_core", "xcli_core"),
            ("ai_engines", "ai_engines"),
            ("plugins", "plugins"),
        ]

        total = 0
        rows: List[Tuple[str, int]] = []
        for sub, label in subdirs:
            target = os.path.join(PROJECT_ROOT, sub)
            if os.path.isdir(target):
                count = len(self._collect_py_files(target))
                rows.append((label, count))
                total += count

        other = len(self._collect_py_files(PROJECT_ROOT)) - total
        rows.append(("其他(根目录等)", other))
        total += other

        self._emit("")
        self._emit(f"  {'目录':<20} {'文件数':>8}")
        self._emit("  " + "─" * 30)
        for label, count in rows:
            bar = "█" * min(count, 40) if count else ""
            color = Fore.GREEN if count else Fore.CYAN
            self._emit(f"  {label:<20} {count:>8}  {color}{bar}{Style.RESET_ALL}")
        self._emit("  " + "─" * 30)
        self._emit(f"  {'合计':<20} {total:>8}")
        self._emit("")
        self._emit("─" * 60)

        return ToolResult.ok(
            f"统计完成 (共 {total} 个文件)",
            tool_name="compile_check",
        )