"""
Git 集成插件 - 版本控制能力
对标 Claude Code 的 Git 工作流支持
"""
import os
import subprocess
from typing import Optional, Tuple


class Plugin:
    """Git 集成工具 - 提供完整的 Git 操作支持"""

    def __init__(self):
        self.usage = """Git 集成工具

操作类型:
  status                     - 查看仓库状态
  diff [文件路径]            - 查看未暂存的变更
  diff --cached              - 查看已暂存的变更
  log [数量]                 - 查看提交历史
  log --oneline [数量]       - 查看简洁提交历史
  add <文件路径>             - 暂存文件
  add .                      - 暂存所有变更
  commit <提交信息>          - 提交变更
  branch                     - 查看分支列表
  branch <名称>              - 创建新分支
  checkout <分支名>          - 切换分支
  checkout -b <分支名>       - 创建并切换分支
  stash                      - 暂存当前变更
  stash pop                  - 恢复暂存的变更
  show <commit>              - 查看指定提交
  blame <文件路径>           - 查看文件逐行修改记录
  remote                     - 查看远程仓库
  init                       - 初始化仓库
  clone <URL> [目录]         - 克隆仓库
"""
        self.cli = None

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "git_tools",
            "description": "Git 版本控制工具 - 查看状态、提交、分支管理、查看历史等",
            "keywords": ["git", "版本控制", "提交", "分支", "commit", "branch", "status"],
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
                    "args": {"type": "string", "description": "操作参数"},
                    "cwd": {"type": "string", "description": "工作目录"}
                },
                "required": ["operation"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        args = arguments.get("args", "")
        return f"{op} {args}".strip()

    def _run_git(self, args: list, cwd: Optional[str] = None) -> Tuple[bool, str]:
        """执行 git 命令"""
        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=30
            )
            output = result.stdout
            if result.stderr:
                output += result.stderr
            return result.returncode == 0, output.strip()
        except FileNotFoundError:
            return False, "错误：git 未安装。请先安装 Git。"
        except subprocess.TimeoutExpired:
            return False, "错误：Git 命令执行超时"
        except Exception as e:
            return False, f"错误：{str(e)}"

    def handle(self, args: str) -> str:
        try:
            parts = args.strip().split(maxsplit=1)
            if not parts:
                return self._git_status("")

            operation = parts[0].lower()
            rest = parts[1] if len(parts) > 1 else ""

            # 获取工作目录
            cwd = None
            if self.cli and hasattr(self.cli, 'current_dir'):
                cwd = self.cli.current_dir

            handlers = {
                "status": self._git_status,
                "diff": self._git_diff,
                "log": self._git_log,
                "add": self._git_add,
                "commit": self._git_commit,
                "branch": self._git_branch,
                "checkout": self._git_checkout,
                "stash": self._git_stash,
                "show": self._git_show,
                "blame": self._git_blame,
                "remote": self._git_remote,
                "init": self._git_init,
                "clone": self._git_clone,
            }

            handler = handlers.get(operation)
            if not handler:
                # 尝试直接执行 git 命令
                return self._git_raw(args, cwd)

            return handler(rest, cwd)

        except Exception as e:
            return f"Git 工具错误: {str(e)}"

    def _git_status(self, args: str, cwd=None) -> str:
        ok, output = self._run_git(["status", "--porcelain"], cwd)
        if not ok:
            return f"Git 错误: {output}"

        if not output:
            return "✅ 工作区干净，没有未提交的变更"

        # 解析状态
        lines = output.split('\n')
        staged = []
        unstaged = []
        untracked = []

        for line in lines:
            if len(line) < 4:
                continue
            status = line[:2]
            filename = line[3:]

            if status[0] in ('M', 'A', 'D', 'R', 'C'):
                staged.append(f"  ✅ {status[0]} {filename}")
            if status[1] in ('M', 'D'):
                unstaged.append(f"  ⚠️  {status[1]} {filename}")
            if status == '??':
                untracked.append(f"  🆕 {filename}")

        result = ["📊 Git 状态:"]
        if staged:
            result.append(f"\n已暂存 ({len(staged)}):")
            result.extend(staged)
        if unstaged:
            result.append(f"\n未暂存 ({len(unstaged)}):")
            result.extend(unstaged)
        if untracked:
            result.append(f"\n未跟踪 ({len(untracked)}):")
            result.extend(untracked)

        # 获取分支信息
        ok2, branch = self._run_git(["branch", "--show-current"], cwd)
        if ok2 and branch:
            result.insert(1, f"🌿 分支: {branch}")

        return '\n'.join(result)

    def _git_diff(self, args: str, cwd=None) -> str:
        if args.strip() == "--cached":
            ok, output = self._run_git(["diff", "--cached"], cwd)
        elif args.strip():
            ok, output = self._run_git(["diff", args.strip()], cwd)
        else:
            ok, output = self._run_git(["diff"], cwd)

        if not ok:
            return f"Git 错误: {output}"
        if not output:
            return "没有变更"

        # 限制输出长度
        if len(output) > 5000:
            output = output[:5000] + f"\n... (输出截断，共 {len(output)} 字符)"

        return f"📝 变更:\n{output}"

    def _git_log(self, args: str, cwd=None) -> str:
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
        if not output:
            return "暂无提交历史"

        return f"📜 提交历史:\n{output}"

    def _git_add(self, args: str, cwd=None) -> str:
        target = args.strip()
        if not target:
            return "错误：请提供文件路径（使用 . 暂存所有）"

        ok, output = self._run_git(["add", target], cwd)
        if not ok:
            return f"Git add 失败: {output}"

        return f"✅ 已暂存: {target}"

    def _git_commit(self, args: str, cwd=None) -> str:
        message = args.strip()
        if not message:
            return "错误：请提供提交信息"

        ok, output = self._run_git(["commit", "-m", message], cwd)
        if not ok:
            return f"Git commit 失败: {output}"

        return f"✅ 提交成功:\n{output}"

    def _git_branch(self, args: str, cwd=None) -> str:
        if not args.strip():
            ok, output = self._run_git(["branch", "-a"], cwd)
            if not ok:
                return f"Git 错误: {output}"
            return f"🌿 分支列表:\n{output}"
        else:
            ok, output = self._run_git(["branch", args.strip()], cwd)
            if not ok:
                return f"创建分支失败: {output}"
            return f"✅ 已创建分支: {args.strip()}"

    def _git_checkout(self, args: str, cwd=None) -> str:
        if args.startswith("-b "):
            branch = args[3:].strip()
            ok, output = self._run_git(["checkout", "-b", branch], cwd)
        else:
            branch = args.strip()
            ok, output = self._run_git(["checkout", branch], cwd)

        if not ok:
            return f"切换分支失败: {output}"
        return f"✅ 已切换到分支: {branch}"

    def _git_stash(self, args: str, cwd=None) -> str:
        if args.strip() == "pop":
            ok, output = self._run_git(["stash", "pop"], cwd)
        else:
            ok, output = self._run_git(["stash"], cwd)

        if not ok:
            return f"Git stash 失败: {output}"
        return f"✅ {output}"

    def _git_show(self, args: str, cwd=None) -> str:
        commit = args.strip() or "HEAD"
        ok, output = self._run_git(["show", "--stat", commit], cwd)
        if not ok:
            return f"Git show 失败: {output}"

        if len(output) > 3000:
            output = output[:3000] + "\n... (输出截断)"
        return output

    def _git_blame(self, args: str, cwd=None) -> str:
        path = args.strip()
        if not path:
            return "错误：请提供文件路径"

        ok, output = self._run_git(["blame", "--line-porcelain", path], cwd)
        if not ok:
            return f"Git blame 失败: {output}"

        # 简化输出
        lines = output.split('\n')
        simplified = []
        for line in lines:
            if line.startswith('author '):
                author = line[7:]
            elif line.startswith('\t'):
                simplified.append(f"  {author}: {line[1:]}")

        if len(simplified) > 100:
            simplified = simplified[:100]
            simplified.append(f"  ... (共 {len(simplified)} 行)")

        return f"📝 {path} 修改记录:\n" + '\n'.join(simplified)

    def _git_remote(self, args: str, cwd=None) -> str:
        ok, output = self._run_git(["remote", "-v"], cwd)
        if not ok:
            return f"Git 错误: {output}"
        if not output:
            return "没有配置远程仓库"
        return f"🌐 远程仓库:\n{output}"

    def _git_init(self, args: str, cwd=None) -> str:
        path = args.strip() or "."
        ok, output = self._run_git(["init", path], cwd)
        if not ok:
            return f"Git init 失败: {output}"
        return f"✅ {output}"

    def _git_clone(self, args: str, cwd=None) -> str:
        parts = args.split()
        if not parts:
            return "错误：请提供仓库 URL"

        url = parts[0]
        target = parts[1] if len(parts) > 1 else ""

        cmd = ["clone", url]
        if target:
            cmd.append(target)

        ok, output = self._run_git(cmd, cwd)
        if not ok:
            return f"Git clone 失败: {output}"
        return f"✅ 克隆成功:\n{output}"

    def _git_raw(self, args: str, cwd=None) -> str:
        """直接执行 git 命令"""
        parts = args.split()
        ok, output = self._run_git(parts, cwd)
        if not ok:
            return f"Git 错误: {output}"
        return output
