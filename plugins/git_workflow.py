"""
Git 工作流自动化 - commit 规范、分支管理、PR 生成
"""
import os
import subprocess
import re
from typing import Tuple


class Plugin:
    """Git 工作流自动化 - 规范提交、分支管理、变更摘要"""

    def __init__(self):
        self.usage = """Git 工作流自动化

操作类型:
  commit [消息]              - 智能提交 (自动 add + 规范化消息)
  log [数量]                 - 格式化提交历史
  changelog [版本]           - 生成 CHANGELOG
  summary                    - 变更摘要 (本次未提交的改动)
  blame [文件]               - 逐行追溯
  contributors               - 贡献者统计
  stale [天数]               - 查找长期未更新的文件
  hooks                      - 管理 git hooks
"""
        self.cli = None

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "git_workflow",
            "description": "Git 工作流自动化 - 规范提交、变更摘要、贡献者统计",
            "keywords": ["git", "commit", "changelog", "提交", "变更", "工作流"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "git_workflow",
            "description": "Git 工作流自动化工具",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["commit", "log", "changelog", "summary", "blame", "contributors", "stale", "hooks"],
                        "description": "操作类型"
                    },
                    "args": {
                        "type": "string",
                        "description": "操作参数"
                    }
                },
                "required": ["operation"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        args = arguments.get("args", "")
        return f"{op} {args}".strip()

    def _run(self, cmd: str, cwd: str = None) -> Tuple[bool, str]:
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=cwd or os.getcwd(), timeout=30
            )
            return result.returncode == 0, (result.stdout + result.stderr).strip()
        except Exception as e:
            return False, str(e)

    def handle(self, args: str) -> str:
        parts = args.strip().split(maxsplit=1)
        if not parts:
            return self.usage

        op = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""

        handlers = {
            "commit": self._commit,
            "log": self._log,
            "changelog": self._changelog,
            "summary": self._summary,
            "blame": self._blame,
            "contributors": self._contributors,
            "stale": self._stale,
            "hooks": self._hooks,
        }

        handler = handlers.get(op)
        if not handler:
            return f"错误: 不支持的操作 '{op}'"

        try:
            return handler(rest)
        except Exception as e:
            return f"执行错误: {e}"

    def _commit(self, message: str) -> str:
        """智能提交"""
        # 检查是否有变更
        ok, status = self._run("git status --porcelain")
        if not status:
            return "✅ 工作区干净，没有需要提交的变更"

        # 自动 add
        self._run("git add -A")

        # 规范化提交消息
        if not message:
            # 根据变更自动生成消息
            message = self._auto_commit_message(status)

        # 检查是否符合 conventional commits
        if not re.match(r'^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?: .+', message):
            # 自动添加前缀
            if any('.py' in l for l in status.split('\n')):
                if 'test' in message.lower():
                    message = f"test: {message}"
                elif 'doc' in message.lower() or 'readme' in message.lower():
                    message = f"docs: {message}"
                else:
                    message = f"feat: {message}"

        # 提交
        ok, output = self._run(f'git commit -m "{message}"')
        if ok:
            # 获取 commit hash
            _, hash_out = self._run("git log --oneline -1")
            return f"✅ 已提交: {message}\n   {hash_out}"
        return f"❌ 提交失败: {output}"

    def _auto_commit_message(self, status: str) -> str:
        """根据变更自动生成提交消息"""
        lines = status.strip().split('\n')
        added = [l[3:] for l in lines if l.startswith('A')]
        modified = [l[3:] for l in lines if l.startswith('M')]
        deleted = [l[3:] for l in lines if l.startswith('D')]

        parts = []
        if added:
            parts.append(f"添加 {len(added)} 个文件")
        if modified:
            parts.append(f"修改 {len(modified)} 个文件")
        if deleted:
            parts.append(f"删除 {len(deleted)} 个文件")

        return ", ".join(parts) if parts else "更新代码"

    def _log(self, args: str) -> str:
        """格式化提交历史"""
        count = int(args) if args.strip().isdigit() else 10
        ok, output = self._run(f'git log --oneline -{count} --format="%h %s (%ar, %an)"')
        if not ok:
            return f"❌ {output}"

        lines = output.strip().split('\n')
        result = [f"📜 最近 {len(lines)} 次提交:\n"]
        for line in lines:
            result.append(f"  {line}")

        return '\n'.join(result)

    def _changelog(self, version: str) -> str:
        """生成 CHANGELOG"""
        # 获取所有提交
        ok, output = self._run('git log --oneline --format="%s" | head -50')
        if not ok:
            return f"❌ {output}"

        commits = output.strip().split('\n')

        # 分类
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

        # 生成
        ver = version or "未发布"
        result = [f"## {ver}\n"]

        labels = {
            'feat': '🚀 新增', 'fix': '🐛 修复', 'docs': '📝 文档',
            'refactor': '♻️ 重构', 'test': '🧪 测试', 'chore': '🔧 杂项',
            'other': '📦 其他'
        }

        for prefix, label in labels.items():
            items = categories[prefix]
            if items:
                result.append(f"\n### {label}")
                for item in items[:10]:
                    result.append(f"- {item}")

        return '\n'.join(result)

    def _summary(self, args: str) -> str:
        """变更摘要"""
        ok, output = self._run("git diff --stat")
        if not output:
            return "✅ 没有未提交的变更"

        ok2, short = self._run("git diff --shortstat")
        return f"📊 变更摘要:\n\n{short}\n\n{output[:2000]}"

    def _blame(self, args: str) -> str:
        """逐行追溯"""
        if not args.strip():
            return "错误: 请提供文件路径"

        ok, output = self._run(f"git blame --line-porcelain {args} | grep -E '^(author |	)'")
        if not ok:
            return f"❌ {output}"

        # 简化输出
        lines = output.strip().split('\n')
        result = [f"📝 {args} 修改记录:\n"]
        author = ""
        for line in lines:
            if line.startswith('author '):
                author = line[7:]
            elif line.startswith('\t'):
                result.append(f"  {author:20} {line[1:]}")

        return '\n'.join(result[:50])

    def _contributors(self, args: str) -> str:
        """贡献者统计"""
        ok, output = self._run("git shortlog -sn --all --no-merges")
        if not ok:
            return f"❌ {output}"

        lines = output.strip().split('\n')
        result = [f"👥 贡献者 ({len(lines)} 人):\n"]
        for line in lines[:20]:
            result.append(f"  {line.strip()}")

        return '\n'.join(result)

    def _stale(self, args: str) -> str:
        """查找长期未更新的文件"""
        days = int(args) if args.strip().isdigit() else 90
        ok, output = self._run(f"git log --diff-filter=A --format='%aI %n' --since='{days} days ago' | head -20")
        if not ok:
            return f"❌ {output}"

        return f"📁 最近 {days} 天新增的文件:\n{output[:2000]}"

    def _hooks(self, args: str) -> str:
        """管理 git hooks"""
        hooks_dir = ".git/hooks"
        if not os.path.exists(hooks_dir):
            return "❌ 不是 git 仓库"

        hooks = os.listdir(hooks_dir)
        active = [h for h in hooks if not h.endswith('.sample') and os.path.isfile(os.path.join(hooks_dir, h))]

        result = ["🪝 Git Hooks:\n"]
        for h in hooks:
            path = os.path.join(hooks_dir, h)
            if h.endswith('.sample'):
                result.append(f"  ⭕ {h.replace('.sample', '')} (未激活)")
            elif os.path.isfile(path):
                result.append(f"  ✅ {h} (活跃)")

        if not active:
            result.append("\n  没有活跃的 hooks。可以添加 pre-commit 等钩子。")

        return '\n'.join(result)
