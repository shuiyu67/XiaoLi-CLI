import subprocess
import os
import sys
import time
from colorama import Fore, Style


class Liugin:
    """CMD命令执行插件 - 仅限Windows环境"""
    
    def __init__(self):
        self.usage = """CMD命令执行工具使用方法：
cmd_executor <操作> <参数>
例如:
- cmd_executor run dir - 执行dir命令查看当前目录内容
- cmd_executor run "ipconfig /all" - 执行ipconfig命令查看网络配置
- cmd_executor run "tasklist | findstr python" - 查找Python相关进程

详细说明:
- run操作: cmd_executor run <命令> - 执行指定的CMD命令

使用工具的JSON格式示例:
{"action": "use_tool", "tool": "cmd_executor", "args": "run dir"} - 执行dir命令
{"action": "use_tool", "tool": "cmd_executor", "args": "run ipconfig /all"} - 执行ipconfig命令

重要说明:
- 此工具仅在Windows环境下可用
- 为安全起见，某些系统命令可能被限制执行
- 命令执行结果会返回给AI进行分析"""
        self.cli = None  # CLI实例引用
        
    def set_cli(self, cli):
        """设置CLI实例引用"""
        self.cli = cli
        # 注册插件命令
        self.cli.register_liugin_command('cmd', self.command_handler)
    
    def command_handler(self, args):
        """处理 /cmd 命令"""
        # 解析参数
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 1:
            return "请提供操作类型: run <命令>"
        
        operation = parts[0].lower()
        remaining_args = parts[1] if len(parts) > 1 else ""
        
        # 调用实际的CMD执行功能
        return self.handle(f"{operation} {remaining_args}")
    
    def get_tool_info(self):
            return {
                "name": "cmd_executor",
                "description": "CMD命令执行工具，用于执行Windows命令行指令",
                "keywords": ["命令", "执行", "CMD", "cmd", "executor", "Windows", "指令", "操作"],
                "usage": """cmd_executor 工具使用说明：
    JSON格式示例：
    {"action": "use_tool", "tool": "cmd_executor", "args": "run dir"} - 执行dir命令
    {"action": "use_tool", "tool": "cmd_executor", "args": "run ipconfig /all"} - 执行ipconfig命令
    {"action": "use_tool", "tool": "cmd_executor", "args": "run tasklist"} - 列出所有进程
    注意：仅限Windows环境使用"""
            }    
    def handle(self, args):
        """处理CMD命令执行请求"""
        try:
            # 解析参数
            parts = args.strip().split(maxsplit=1)
            if len(parts) < 1:
                return "错误：参数不足。请提供操作类型。\n可用操作: run"
            
            operation = parts[0].lower()
            
            if operation == "run":
                # 检查是否为Windows系统
                if os.name != 'nt':
                    return "错误：CMD命令执行工具仅支持Windows系统。"
                
                if len(parts) < 2:
                    return "错误：请提供要执行的命令。格式: run <命令>"
                
                command = parts[1]
                return self._execute_command(command)
            
            else:
                return f"错误：不支持的操作 '{operation}'。支持的操作有: run。"
        
        except Exception as e:
            return f"CMD命令执行错误: {str(e)}"
    
    def _execute_command(self, command):
        """执行CMD命令"""
        try:
            # 解析命令和可能的超时参数
            # 允许格式如 "command --timeout 10" 或 "command -t 10"
            timeout = 30  # 默认超时时间
            import re
            
            # 检查是否在命令中指定超时
            timeout_pattern = r'(?:--timeout|-t)\s+(\d+)'
            timeout_match = re.search(timeout_pattern, command, re.IGNORECASE)
            
            if timeout_match:
                timeout = int(timeout_match.group(1))
                # 移除超时参数，只保留实际命令
                command = re.sub(timeout_pattern, '', command).strip()
            
            # 检查是否有CLI实例可用，请求用户确认
            if self.cli is not None:
                # 检查是否是 Clawli 远程模式
                if not getattr(self.cli, 'is_clawli_mode', False):
                    # 非远程模式，请求用户确认
                    try:
                        from ai_cli import ask_user_confirmation
                        # 生成唯一的请求ID
                        import uuid
                        request_id = str(uuid.uuid4())
                        
                        # 存储请求信息
                        self.cli.user_input_queue[request_id] = {
                            'type': 'cmd_confirm',
                            'command': command,
                            'timeout': timeout,
                            'status': 'pending'
                        }
                        
                        # 发送确认请求给用户
                        confirmed = ask_user_confirmation(
                            f"即将执行CMD命令: {command}\n超时时间: {timeout}秒\n是否确认执行?",
                            request_id
                        )
                        
                        if not confirmed:
                            return f"命令执行已取消: {command}"
                    except Exception as e:
                        # 如果无法请求确认，直接执行
                        pass
            
            # 执行命令
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,  # 使用自定义超时时间
                encoding='utf-8',  # 指定编码
                errors='replace'   # 处理编码错误
            )
            
            # 获取输出
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            return_code = result.returncode
            
            output = ""
            if stdout:
                output += f"命令输出:\n{stdout}\n"
            if stderr:
                output += f"错误信息:\n{stderr}\n"
            if return_code != 0:
                output += f"命令退出码: {return_code}\n"

            if not output:
                output = f"命令执行完成，无输出。(超时设置: {timeout}秒)"

            # 限制输出长度为5000字符
            if len(output) > 5000:
                output = output[:5000] + f"\n... (输出已截断，超时设置: {timeout}秒)"

            return output            
        except subprocess.TimeoutExpired:
            return f"错误：命令执行超时（超过{timeout}秒），已取消执行。"
        except ValueError:
            return f"错误：超时值无效，已使用默认30秒超时。命令: {command}"
        except Exception as e:
            return f"命令执行失败: {str(e)}"


# 测试函数
def test_plugin():
    """测试插件功能"""
    plugin = Plugin()
    print("CMD执行器插件测试:")
    print("工具信息:", plugin.get_tool_info())
    print("使用说明:", plugin.usage)


if __name__ == "__main__":
    test_plugin()