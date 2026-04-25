"""统一显示输出 - CLI/TUI 双模式"""
import sys
import time
import random
import threading
from colorama import Fore, Style


class Display:
    """统一输出管理器"""

    def __init__(self, user_id="", tui_callback=None):
        self.user_id = user_id
        self.tui = tui_callback

    def out(self, msg):
        """输出"""
        if self.tui:
            self.tui(msg)
        else:
            print(msg)

    def ai(self, content, is_continue=False):
        """显示 AI 响应"""
        uid = f"[用户ID: {self.user_id}]"
        lines = content.split('\n')
        for i, line in enumerate(lines):
            prefix = f"{Fore.YELLOW}✦{Style.RESET_ALL} " if is_continue else "✦ "
            if i == 0:
                line = prefix + line
            if i == len(lines) - 1:
                print(f"{line} {uid}")
            else:
                print(line)
        print()

    def tool_ok(self, name, args, result):
        """工具执行成功"""
        self.out("")
        uid = f"[用户ID: {self.user_id}]"
        self.out(f"{Fore.GREEN}     OK 工具: {name}{Style.RESET_ALL}")
        self.out(f"{Fore.GREEN}     参数: {args} {uid}{Style.RESET_ALL}")
        for line in self._trunc(result).split('\n'):
            self.out(f"{Fore.GREEN}          {line}{Style.RESET_ALL}")

    def tool_err(self, name, args, result):
        """工具执行失败"""
        self.out("")
        uid = f"[用户ID: {self.user_id}]"
        self.out(f"{Fore.RED}     X 工具: {name}{Style.RESET_ALL}")
        self.out(f"{Fore.RED}     参数: {args} {uid}{Style.RESET_ALL}")
        for line in self._trunc(result).split('\n'):
            self.out(f"{Fore.RED}          {line}{Style.RESET_ALL}")

    def err(self, msg):
        self.out(f"{Fore.RED}{msg}{Style.RESET_ALL}")

    def ok(self, msg):
        self.out(f"{Fore.GREEN}{msg}{Style.RESET_ALL}")

    def info(self, msg):
        self.out(f"{Fore.CYAN}{msg}{Style.RESET_ALL}")

    def warn(self, msg):
        self.out(f"{Fore.YELLOW}{msg}{Style.RESET_ALL}")

    def typeprint(self, text, color=None, delay=0.01):
        """打字机效果"""
        for ch in text:
            print(f"{color}{ch}{Style.RESET_ALL}" if color else ch, end="", flush=True)
            time.sleep(delay)
        print()

    def thinking(self, sentences, stop_event):
        """等待动画"""
        if not sentences:
            sentences = ["AI正在思考中...", "请稍等片刻..."]
        last_change = time.time()
        cur = random.choice(sentences)
        chars = "|/-\\"
        idx = 0
        while not stop_event.is_set():
            now = time.time()
            if now - last_change >= 5:
                cur = random.choice(sentences)
                last_change = now
            disp = cur[:47] + "..." if len(cur) > 50 else cur
            print(f"\r{Fore.MAGENTA}{disp} {chars[idx % 4]}{Style.RESET_ALL}", end="", flush=True)
            idx += 1
            time.sleep(0.1)
        print("\r" + " " * 60 + "\r", end="", flush=True)

    def banner(self, engine_name, engines, user_id):
        """启动横幅"""
        self.ok(f"小狸 Pro-CLI v3.6 已启动!")
        self.ok(f"用户ID: {user_id}")
        print(f"{Fore.GREEN}TUI 模式 | '/help' 帮助 | '/cli' 命令行 | '/quit' 退出{Style.RESET_ALL}")
        print(f"{Fore.GREEN}当前引擎: {engine_name}{Style.RESET_ALL}")
        if len(engines) > 1:
            print(f"{Fore.GREEN}已加载: {', '.join(engines)}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'-' * 50}{Style.RESET_ALL}")

    @staticmethod
    def _trunc(text, max_lines=2):
        if not text:
            return "无结果"
        lines = text.split('\n')
        if len(lines) <= max_lines:
            return text
        return '\n'.join(lines[:max_lines]) + f"\n... (已截断，共{len(lines)}行)"
