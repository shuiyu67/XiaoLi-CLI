#!/usr/bin/env python3
"""
手动引擎 - 让人类在另一个终端扮演 AI
消息通过文件传递，另一个终端窗口显示消息并等待人工输入
"""

import os
import sys
import time
import subprocess
import tempfile

# 添加项目根目录到sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

try:
    from xcli_core.tool_result import normalize_tool_text
except Exception:
    def normalize_tool_text(result, default="无结果"):
        """兜底归一化：ToolResult / dict / str 统一成字符串"""
        if result is None:
            return default
        if isinstance(result, dict):
            return str(result.get("result", default))
        return str(result)

# 通信用的临时目录
COMM_DIR = os.path.join(tempfile.gettempdir(), "xiaoli_manual_engine")


class ManualAI:
    """手动引擎 — 让人类在另一个终端扮演 AI"""

    requires_api_key = False

    def __init__(self):
        self.name = "manual"
        self.cli = None
        self.conversation_history = []
        self.max_history = 10
        self._subprocess = None
        # 最近一次请求的 prompt token 数（手动引擎无真实模型，恒为 None）
        self.last_prompt_tokens = None
        self._session_id = str(int(time.time()))
        self._started = False

        # 确保通信目录存在
        os.makedirs(COMM_DIR, exist_ok=True)

    def get_help_info(self):
        return """手动引擎帮助信息
========================

引擎名称: manual
描述: 让人类在另一个终端窗口扮演 AI，消息通过文件传递

工作原理:
  1. 切换到 manual 引擎时，自动打开一个新终端窗口
  2. 用户在 CLI 中输入消息，消息会显示在新终端窗口中
  3. 另一个终端窗口中的人阅读消息，手动输入回复并按回车
  4. 回复传回 CLI，显示为 AI 的响应

使用说明:
  1. /engine switch manual  — 切换到手动引擎，自动打开另一个终端
  2. 在 CLI 中正常对话，消息会转发到另一个终端
  3. 在另一个终端中手动输入回复
  4. /engine.manual status   — 查看连接状态
  5. /engine.manual restart  — 重启另一个终端窗口

注意: 需要图形桌面环境才能自动打开新终端窗口。
      如果是无头服务器，请手动运行通信脚本。
"""

    def _get_paths(self):
        """获取通信文件路径"""
        base = os.path.join(COMM_DIR, self._session_id)
        return {
            "msg_to_human": base + "_to_human.txt",
            "msg_from_human": base + "_from_human.txt",
            "ready": base + "_ready.flag",
            "alive": base + "_alive.flag",
        }

    def _spawn_terminal(self):
        """在新终端窗口中启动人工回复脚本"""
        paths = self._get_paths()

        # 写一个临时脚本
        script_content = self._generate_script(paths)
        script_path = os.path.join(COMM_DIR, f"worker_{self._session_id}.py")
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)

        # 根据平台选择终端
        import platform
        system = platform.system()

        try:
            if system == "Windows":
                self._subprocess = subprocess.Popen(
                    ["cmd", "/c", "start", "cmd", "/k", f"python \"{script_path}\""],
                    shell=True
                )
            elif system == "Darwin":  # macOS
                self._subprocess = subprocess.Popen([
                    "osascript", "-e",
                    f'tell app "Terminal" to do script "python3 \\"{script_path}\\""'
                ])
            else:  # Linux
                # 尝试常见的终端模拟器
                terminals = [
                    ["x-terminal-emulator", "-e", f"python3 {script_path}"],
                    ["gnome-terminal", "--", "python3", script_path],
                    ["konsole", "-e", f"python3 {script_path}"],
                    ["xfce4-terminal", "-e", f"python3 {script_path}"],
                    ["xterm", "-e", f"python3 {script_path}"],
                ]
                launched = False
                for cmd in terminals:
                    try:
                        self._subprocess = subprocess.Popen(cmd)
                        launched = True
                        break
                    except FileNotFoundError:
                        continue
                if not launched:
                    print(f"\033[33m[manual] 无法自动打开终端窗口，请手动运行:\033[0m")
                    print(f"\033[36m  python3 {script_path}\033[0m")
                    return False

            # 等待对方就绪
            ready_path = paths["ready"]
            for _ in range(30):  # 最多等 15 秒
                if os.path.exists(ready_path):
                    self._started = True
                    return True
                time.sleep(0.5)

            # 超时但不报错，可能终端启动慢
            self._started = True
            return True

        except Exception as e:
            print(f"\033[31m[manual] 启动终端失败: {e}\033[0m")
            print(f"\033[33m[manual] 请手动运行: python3 {script_path}\033[0m")
            return False

    def _generate_script(self, paths):
        """生成人工回复脚本的内容"""
        return f'''#!/usr/bin/env python3
"""小狸手动引擎 — 人工回复终端"""
import os
import sys
import time
import signal

MSG_IN   = r"{paths['msg_to_human']}"
MSG_OUT  = r"{paths['msg_from_human']}"
READY    = r"{paths['ready']}"
ALIVE    = r"{paths['alive']}"

# 标记自己已就绪
with open(READY, 'w') as f:
    f.write("ready")

# 定期刷新 alive 标记
def keep_alive():
    try:
        with open(ALIVE, 'w') as f:
            f.write(str(time.time()))
    except:
        pass

keep_alive()

print()
print("\\033[36m╔══════════════════════════════════════════╗\\033[0m")
print("\\033[36m║    小狸手动引擎 — 人工回复终端          ║\\033[0m")
print("\\033[36m║    在这里输入回复，按回车发送           ║\\033[0m")
print("\\033[36m║    输入 quit 退出                       ║\\033[0m")
print("\\033[36m╚══════════════════════════════════════════╝\\033[0m")
print()
sys.stdout.flush()

last_msg_time = 0

while True:
    keep_alive()

    # 检查是否有新消息
    try:
        if os.path.exists(MSG_IN):
            mtime = os.path.getmtime(MSG_IN)
            if mtime > last_msg_time:
                last_msg_time = mtime
                with open(MSG_IN, 'r', encoding='utf-8') as f:
                    msg = f.read()
                if msg:
                    print("\\033[33m[用户消息]\\033[0m")
                    print(msg)
                    print()
                    sys.stdout.flush()
    except:
        pass

    # 检查用户输入（非阻塞）
    try:
        import select
        if select.select([sys.stdin], [], [], 0.3)[0]:
            line = sys.stdin.readline().strip()
            if line:
                if line.lower() == "quit":
                    print("\\033[31m[已退出手动引擎]\\033[0m")
                    break
                # 写回复
                with open(MSG_OUT, 'w', encoding='utf-8') as f:
                    f.write(line)
                print(f"\\033[32m[已发送] {{line}}\\033[0m")
                print()
                sys.stdout.flush()
    except:
        # Windows 没有 select，用阻塞方式
        try:
            import msvcrt
            if msvcrt.kbhit():
                line = input().strip()
                if line:
                    if line.lower() == "quit":
                        print("\\033[31m[已退出手动引擎]\\033[0m")
                        break
                    with open(MSG_OUT, 'w', encoding='utf-8') as f:
                        f.write(line)
                    print(f"\\033[32m[已发送] {{line}}\\033[0m")
                    print()
                    sys.stdout.flush()
        except:
            time.sleep(0.3)
'''

    @property
    def max_input_tokens(self):
        """当前引擎支持的最大输入 token 数（统一 API）。手动引擎无真实模型，给名义上限。"""
        return 128000

    def generate_response(self, user_input, tool_results=None, system_prompt=None):
        """生成响应 — 转发给另一个终端的人工"""
        paths = self._get_paths()

        # 如果还没启动终端，现在启动
        if not self._started:
            if not self._spawn_terminal():
                return "[manual] 手动引擎未就绪，无法打开终端窗口。请手动启动通信脚本。"

        # 清除旧的回复文件
        from_human = paths["msg_from_human"]
        if os.path.exists(from_human):
            os.remove(from_human)

        # 把用户消息写入文件
        msg = user_input
        if tool_results:
            msg = f"[工具结果] {normalize_tool_text(tool_results)}\n\n{user_input}"

        to_human = paths["msg_to_human"]
        with open(to_human, 'w', encoding='utf-8') as f:
            f.write(msg)

        print(f"\033[36m[manual] 消息已发送到人工终端，等待回复...\033[0m")

        # 等待回复
        timeout = 300  # 最多等 5 分钟
        waited = 0
        while waited < timeout:
            if os.path.exists(from_human):
                try:
                    with open(from_human, 'r', encoding='utf-8') as f:
                        response = f.read().strip()
                    if response:
                        # 清理回复文件
                        os.remove(from_human)
                        return response
                except:
                    pass
            time.sleep(0.5)
            waited += 0.5

        return "[manual] 等待人工回复超时（5分钟）"

    def handle_command(self, command):
        """处理 manual 引擎专属命令"""
        if command == "status":
            paths = self._get_paths()
            alive = os.path.exists(paths["alive"])
            return f"会话ID: {self._session_id}\n终端状态: {'已连接' if alive else '未连接'}\n通信目录: {COMM_DIR}"
        elif command == "restart":
            self._started = False
            self._session_id = str(int(time.time()))
            if self._spawn_terminal():
                return "手动引擎终端已重启"
            else:
                return "重启失败，无法打开终端"
        else:
            return f"未知命令: {command}\n可用: status, restart"
