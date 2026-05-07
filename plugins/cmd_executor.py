"""
命令执行器插件 - 跨平台 Shell 命令执行
"""
import os
import re
import subprocess
import platform


class Liugin:
    """Shell 命令执行器 - 跨平台命令行工具"""

    def __init__(self):
        self.usage = """Shell 命令执行器

操作:
  run <命令> [--timeout 秒]   - 执行 Shell 命令 (默认超时 30s)

示例:
  run ls -la                  - 列出当前目录
  run python3 --version       - 查看 Python 版本
  run git status              - 查看 Git 状态
  run make build --timeout 60 - 执行构建 (60秒超时)

注意:
  - 跨平台兼容 (Linux/macOS/Windows)
  - 输出限制 5000 字符
  - 某些危险命令会被拦截
"""
        self.cli = None

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "cmd_executor",
            "description": "Shell 命令执行器 - 跨平台执行系统命令，支持超时控制",
            "keywords": ["命令", "执行", "shell", "cmd", "终端", "命令行", "subprocess"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "cmd_executor",
            "description": "Shell 命令执行器",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "要执行的命令"},
                    "timeout": {"type": "integer", "description": "超时秒数", "default": 30}
                },
                "required": ["command"]
            }
        }

    def convert_mcp_args(self, arguments):
        cmd = arguments.get("command", "")
        timeout = arguments.get("timeout", "")
        result = f"run {cmd}"
        if timeout:
            result += f" --timeout {timeout}"
        return result

    # 危险命令黑名单
    BLOCKED = {
        'rm -rf /', 'rm -rf ~', 'mkfs', 'dd if=', 'wipefs', 'shred',
        ':(){ :|:& };:', 'chmod -R 777 /', 'mv / ', 'wget http',
    }

    def handle(self, args: str) -> str:
        try:
            parts = args.strip().split(maxsplit=1)
            if not parts:
                return "错误：请提供操作。可用: run <命令>"

            operation = parts[0].lower()
            if operation != "run":
                return f"错误：不支持的操作 '{operation}'。可用: run"

            if len(parts) < 2:
                return "错误：请提供要执行的命令"

            rest = parts[1]

            # 解析 --timeout
            timeout = 30
            timeout_match = re.search(r'--timeout\s+(\d+)', rest)
            if timeout_match:
                timeout = int(timeout_match.group(1))
                rest = re.sub(r'--timeout\s+\d+', '', rest).strip()

            if not rest:
                return "错误：请提供要执行的命令"

            # 安全检查
            for blocked in self.BLOCKED:
                if blocked in rest:
                    return f" 安全拦截: 检测到危险命令模式 '{blocked}'"

            return self._execute(rest, timeout)

        except Exception as e:
            return f"命令执行错误: {str(e)}"

    def _execute(self, command: str, timeout: int) -> str:
        try:
            # Windows 下用 shell=True，Unix 下直接执行
            use_shell = platform.system() == 'Windows'

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8',
                errors='replace'
            )

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            rc = result.returncode

            output = ""
            if stdout:
                output += stdout + "\n"
            if stderr:
                output += f"[stderr]\n{stderr}\n"
            if rc != 0:
                output += f"[exit code: {rc}]\n"

            if not output:
                output = f"命令执行完成，无输出 (超时: {timeout}s)"

            if len(output) > 5000:
                output = output[:5000] + f"\n... (截断，超时: {timeout}s)"

            return output.strip()

        except subprocess.TimeoutExpired:
            return f" 命令超时 ({timeout}s): {command}"
        except Exception as e:
            return f"执行失败: {str(e)}"
