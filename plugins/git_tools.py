"""
Git 工具插件 - 统一的版本控制能力
合并原 git_tools + git_workflow，消除重复
"""
import os
import re
import subprocess
from typing import Tuple, Optional


class Liugin:
    """Git 版本控制 - 基础操作 + 工作流自动化"""

    def __init__(self):
        self.usage = """Git 版本控制工具

基础操作:
  status                         - 查看仓库状态
  diff [文件路径]                - 查看未暂存变更
  diff --cached                  - 查看已暂存变更
  log [数量]                     - 提交历史 (默认10条)
  log --oneline [数量]           - 简洁提交历史
  add <文件路径>                 - 暂存文件
  add .                          - 暂存所有变更
  commit <提交信息>              - 提交变更
  branch                         - 查看分支列表
  branch <名称>                  - 创建新分支
  checkout <分支名>              - 切换分支
  checkout -b <分支名>           - 创建并切换分支
  stash                          - 暂存当前变更
  stash pop                      - 恢复暂存的变更
  show <commit>                  - 查看指定提交
  blame <文件路径>               - 逐行修改记录
  remote                         - 查看远程仓库
  init                           - 初始化仓库
  clone <URL> [目录]             - 克隆仓库

工作流:
  smart-commit [消息]            - 智能提交 (自动 add + 规范化消息)
  changelog [版本]               - 生成 CHANGELOG
  summary                        - 变更摘要 (未提交改动)
  contributors                   - 贡献者统计
  stale [天数]                   - 查找长期未更新文件
"""
        self.cli = None

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "git_tools",
            "description": "Git 版本控制 - 状态查看、提交、分支管理、diff、历史、blame、工作流自动化",
            "keywords": ["git", "版本控制", "提交", "分支", "commit", "branch", "status", "diff",
                         "changelog", "log", "blame", "stash", "checkout", "merge"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "git_tools",
            "description": "Git 版本控制工具",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "description": "Git 操作"},
                    "args": {"type": "string", "description": "操作参数"}
                },
                "required": ["operation"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        args = arguments.get("args", "")
        return f"{op} {args}".strip()

    # ── 执行 Git 命令 ──

    def _run_git(self, args: list, cwd: Optional[str] = None) -> Tuple[bool, str]:
        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True, text=True,
                cwd=cwd, timeout=30
            )
            output = (result.stdout + result.stderr).strip()
            return result.returncode == 0, output
        except FileNotFoundError:
            return False, "git 未安装，请先安装 Git"
        except subprocess.TimeoutExpired:
            return False, "Git 命令执行超时"
        except Exception as e:
            return False, str(e)

    def _run_shell(self, cmd: str, cwd: Optional[str] = None) -> Tuple[bool, str]:
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=cwd or os.getcwd(), timeout=30
            )
            return result.returncode == 0, (result.stdout + result.stderr).strip()
        except Exception as e:
            return False, str(e)

    def _get_cwd(self):
        if self.cli and hasattr(self.cli, 'current_dir'):
            return self.cli.current_dir
        return None

    # ── 路由 ──

    def handle(self, args: str) -> str:
        try:
            parts = args.strip().split(maxsplit=1)
            if not parts:
                return self._status()

            op = parts[0].lower()
            rest = parts[1] if len(parts) > 1 else ""
            cwd = self._get_cwd()

            handlers = {
                # 基础
                "status": lambda r: self._status(cwd),
                "diff": lambda r: self._diff(r, cwd),
                "log": lambda r: self._log(r, cwd),
                "add": lambda r: self._add(r, cwd),
                "commit": lambda r: self._commit(r, cwd),
                "branch": lambda r: self._branch(r, cwd),
                "checkout": lambda r: self._checkout(r, cwd),
                "stash": lambda r: self._stash(r, cwd),
                "show": lambda r: self._show(r, cwd),
                "blame": lambda r: self._blame(r, cwd),
                "remote": lambda r: self._remote(cwd),
                "init": lambda r: self._init(r, cwd),
                "clone": lambda r: self._clone(r, cwd),
                # 工作流
                "smart-commit": lambda r: self._smart_commit(r, cwd),
                "changelog": lambda r: self._changelog(r, cwd),
                "summary": lambda r: self._summary(cwd),
                "contributors": lambda r: self._contributors(cwd),
                "stale": lambda r: self._stale(r, cwd),
            }

            handler = handlers.get(op)
            if handler:
                return handler(rest)

            # 回退：直接执行 git 命令
            ok, output = self._run_git(args.split(), cwd)
            return output if ok else f"Git 错误: {output}"

        except Exception as e:
            return f"Git 工具错误: {str(e)}"

    # ── 基础操作 ──

    def _status(self, cwd=None) -> str:
        ok, output = self._run_git(["status", "--porcelain"], cwd)
        if not ok:
            return f"Git 错误: {output}"

        if not output:
            # 获取分支
            _, branch = self._run_git(["branch", "--show-current"], cwd)
            return f" 工作区干净 (分支: {branch})"

        lines = output.split('\n')
        staged, unstaged, untracked = [], [], []

        for line in lines:
            if len(line) < 4:
                continue
            s, filename = line[:2], line[3:]
            if s[0] in 'MADRC':
                staged.append(f"   {s[0]} {filename}")
            if s[1] in 'MD':
                unstaged.append(f"  ! {s[1]} {filename}")
            if s == '??':
                untracked.append(f"  ? {filename}")

        _, branch = self._run_git(["branch", "--show-current"], cwd)
        result = [f" Git 状态 (分支: {branch})"]

        if staged:
            result.append(f"\n已暂存 ({len(staged)}):")
            result.extend(staged)
        if unstaged:
            result.append(f"\n未暂存 ({len(unstaged)}):")
            result.extend(unstaged)
        if untracked:
            result.append(f"\n未跟踪 ({len(untracked)}):")
            result.extend(untracked)

        return '\n'.join(result)

    def _diff(self, args: str, cwd=None) -> str:
        args = args.strip()
        if args == "--cached":
            git_args = ["diff", "--cached"]
        elif args:
            git_args = ["diff", args]
        else:
            git_args = ["diff"]

        ok, output = self._run_git(git_args, cwd)
        if not ok:
            return f"Git 错误: {output}"
        if not output:
            return "没有变更"
        if len(output) > 5000:
            output = output[:5000] + f"\n... (截断，共 {len(output)} 字符)"
        return output

    def _log(self, args: str, cwd=None) -> str:
        parts = args.split()
        oneline = "--oneline" in parts
        count = 10
        for p in parts:
            if p.isdigit():
                count = int(p)

        if oneline:
            ok, output = self._run_git(
                ["log", "--oneline", f"-{count}", "--graph", "--decorate"], cwd)
        else:
            ok, output = self._run_git(
                ["log", f"-{count}", "--format=%h %an %ad %s", "--date=short"], cwd)

        if not ok:
            return f"Git 错误: {output}"
        return output or "暂无提交历史"

    def _add(self, args: str, cwd=None) -> str:
        target = args.strip()
        if not target:
            return "错误：请提供文件路径（使用 . 暂存所有）"
        ok, output = self._run_git(["add", target], cwd)
        return f" 已暂存: {target}" if ok else f"Git add 失败: {output}"

    def _commit(self, args: str, cwd=None) -> str:
        message = args.strip()
        if not message:
            return "错误：请提供提交信息"
        ok, output = self._run_git(["commit", "-m", message], cwd)
        return f" 提交成功:\n{output}" if ok else f"Git commit 失败: {output}"

    def _branch(self, args: str, cwd=None) -> str:
        if not args.strip():
            ok, output = self._run_git(["branch", "-a"], cwd)
            return f" 分支列表:\n{output}" if ok else f"Git 错误: {output}"
        else:
            ok, output = self._run_git(["branch", args.strip()], cwd)
            return f" 已创建分支: {args.strip()}" if ok else f"创建分支失败: {output}"

    def _checkout(self, args: str, cwd=None) -> str:
        args = args.strip()
        if args.startswith("-b "):
            branch = args[3:].strip()
            ok, output = self._run_git(["checkout", "-b", branch], cwd)
        else:
            branch = args
            ok, output = self._run_git(["checkout", branch], cwd)
        return f" 已切换到: {branch}" if ok else f"切换失败: {output}"

    def _stash(self, args: str, cwd=None) -> str:
        if args.strip() == "pop":
            ok, output = self._run_git(["stash", "pop"], cwd)
        else:
            ok, output = self._run_git(["stash"], cwd)
        return f" {output}" if ok else f"Git stash 失败: {output}"

    def _show(self, args: str, cwd=None) -> str:
        commit = args.strip() or "HEAD"
        ok, output = self._run_git(["show", "--stat", commit], cwd)
        if not ok:
            return f"Git show 失败: {output}"
        if len(output) > 3000:
            output = output[:3000] + "\n... (截断)"
        return output

    def _blame(self, args: str, cwd=None) -> str:
        path = args.strip()
        if not path:
            return "错误：请提供文件路径"
        ok, output = self._run_git(["blame", "--line-porcelain", path], cwd)
        if not ok:
            return f"Git blame 失败: {output}"

        lines = output.split('\n')
        result = []
        author = ""
        for line in lines:
            if line.startswith('author '):
                author = line[7:]
            elif line.startswith('\t'):
                result.append(f"  {author}: {line[1:]}")

        if len(result) > 100:
            result = result[:100]
            result.append(f"  ... (共 {len(result)} 行)")

        return f" {path} 修改记录:\n" + '\n'.join(result)

    def _remote(self, cwd=None) -> str:
        ok, output = self._run_git(["remote", "-v"], cwd)
        if not ok:
            return f"Git 错误: {output}"
        return output or "没有配置远程仓库"

    def _init(self, args: str, cwd=None) -> str:
        path = args.strip() or "."
        ok, output = self._run_git(["init", path], cwd)
        return f" {output}" if ok else f"Git init 失败: {output}"

    def _clone(self, args: str, cwd=None) -> str:
        parts = args.split()
        if not parts:
            return "错误：请提供仓库 URL"
        cmd = ["clone", parts[0]]
        if len(parts) > 1:
            cmd.append(parts[1])
        ok, output = self._run_git(cmd, cwd)
        return f" 克隆成功:\n{output}" if ok else f"Git clone 失败: {output}"

    # ── 工作流 ──

    def _smart_commit(self, message: str, cwd=None) -> str:
        """智能提交：自动 add + 规范化消息"""
        ok, status = self._run_git(["status", "--porcelain"], cwd)
        if not status:
            return " 工作区干净，没有需要提交的变更"

        self._run_git(["add", "-A"], cwd)

        if not message:
            message = self._auto_commit_message(status)

        # conventional commits 检查
        if not re.match(r'^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?: .+', message):
            if 'test' in message.lower():
                message = f"test: {message}"
            elif 'doc' in message.lower() or 'readme' in message.lower():
                message = f"docs: {message}"
            else:
                message = f"feat: {message}"

        ok, output = self._run_git(["commit", "-m", message], cwd)
        if ok:
            _, hash_out = self._run_git(["log", "--oneline", "-1"], cwd)
            return f" 已提交: {message}\n   {hash_out}"
        return f" 提交失败: {output}"

    def _auto_commit_message(self, status: str) -> str:
        lines = status.strip().split('\n')
        added = len([l for l in lines if l.startswith('A ') or l.startswith('A') and l[1] == ' '])
        modified = len([l for l in lines if l.startswith('M ') or (len(l) > 1 and l[1] == 'M')])
        deleted = len([l for l in lines if l.startswith('D ') or (len(l) > 1 and l[1] == 'D')])

        parts = []
        if added:
            parts.append(f"添加 {added} 个文件")
        if modified:
            parts.append(f"修改 {modified} 个文件")
        if deleted:
            parts.append(f"删除 {deleted} 个文件")
        return ", ".join(parts) if parts else "更新代码"

    def _changelog(self, version: str, cwd=None) -> str:
        ok, output = self._run_shell(
            'git log --oneline --format="%s" | head -50', cwd)
        if not ok:
            return f" {output}"

        commits = output.strip().split('\n')
        categories = {
            'feat': [], 'fix': [], 'docs': [], 'refactor': [],
            'test': [], 'chore': [], 'other': []
        }

        for commit in commits:
            matched = False
            for prefix in categories:
                if commit.startswith(prefix + ':') or commit.startswith(prefix + '('):
                    categories[prefix].append(commit)
                    matched = True
                    break
            if not matched:
                categories['other'].append(commit)

        labels = {
            'feat': ' 新增', 'fix': ' 修复', 'docs': ' 文档',
            'refactor': ' 重构', 'test': ' 测试', 'chore': ' 杂项',
            'other': ' 其他'
        }

        ver = version or "未发布"
        result = [f"## {ver}\n"]
        for prefix, label in labels.items():
            items = categories[prefix]
            if items:
                result.append(f"\n### {label}")
                for item in items[:10]:
                    result.append(f"- {item}")

        return '\n'.join(result)

    def _summary(self, cwd=None) -> str:
        ok, output = self._run_git(["diff", "--stat"], cwd)
        if not output:
            return " 没有未提交的变更"
        _, short = self._run_git(["diff", "--shortstat"], cwd)
        return f" 变更摘要:\n\n{short}\n\n{output[:2000]}"

    def _contributors(self, cwd=None) -> str:
        ok, output = self._run_git(["shortlog", "-sn", "--all", "--no-merges"], cwd)
        if not ok:
            return f" {output}"
        lines = output.strip().split('\n')
        result = [f" 贡献者 ({len(lines)} 人):\n"]
        for line in lines[:20]:
            result.append(f"  {line.strip()}")
        return '\n'.join(result)

    def _stale(self, args: str, cwd=None) -> str:
        days = int(args) if args.strip().isdigit() else 90
        ok, output = self._run_shell(
            f"git log --diff-filter=A --format='%aI %n' --since='{days} days ago' | head -20", cwd)
        return f" 最近 {days} 天新增的文件:\n{output[:2000]}" if ok else f" {output}"
