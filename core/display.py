"""
显示与输出模块 - 统一 CLI/TUI 输出
"""
import sys
import os
import time
import random
import shutil
import threading
from colorama import Fore, Style
import logging

logger = logging.getLogger(__name__)


class Display:
    """统一显示管理器"""

    def __init__(self, user_id="", tui_callback=None):
        self.user_id = user_id
        self.tui_callback = tui_callback

    def output(self, message):
        """统一输出方法"""
        if self.tui_callback:
            self.tui_callback(message)
        else:
            print(message)

    def response(self, content, is_continue=False):
        """显示 AI 响应"""
        user_id_display = f"[用户ID: {self.user_id}]"
        lines = content.split('\n')

        for i, line in enumerate(lines):
            if i == 0:
                prefix = f"{Fore.YELLOW}✦{Style.RESET_ALL} " if is_continue else "✦ "
                line = prefix + line
            if i == len(lines) - 1:
                print(f"{line} {user_id_display}")
            else:
                print(line)
        print()

    def tool_result(self, tool_name, tool_args, full_result, is_error=False):
        """显示工具执行结果"""
        if full_result is None:
            full_result = "无结果"

        self.output("")
        user_id_display = f"[用户ID: {self.user_id}]"

        if is_error:
            self.output(f"{Fore.RED}     X 工具: {tool_name}{Style.RESET_ALL}")
            self.output(f"{Fore.RED}     参数: {tool_args} {user_id_display}{Style.RESET_ALL}")
        else:
            self.output(f"{Fore.GREEN}     OK 工具: {tool_name}{Style.RESET_ALL}")
            self.output(f"{Fore.GREEN}     参数: {tool_args} {user_id_display}{Style.RESET_ALL}")

        display_result = self._limit_lines(full_result, max_lines=2)
        color = Fore.RED if is_error else Fore.GREEN
        for line in display_result.split('\n'):
            self.output(f"{color}          {line}{Style.RESET_ALL}")

    def error(self, message):
        """显示错误"""
        self.output(f"{Fore.RED}{message}{Style.RESET_ALL}")

    def success(self, message):
        """显示成功"""
        self.output(f"{Fore.GREEN}{message}{Style.RESET_ALL}")

    def info(self, message):
        """显示信息"""
        self.output(f"{Fore.CYAN}{message}{Style.RESET_ALL}")

    def warning(self, message):
        """显示警告"""
        self.output(f"{Fore.YELLOW}{message}{Style.RESET_ALL}")

    def typeprint(self, text, color=None, delay=0.01):
        """打字机效果输出"""
        for char in text:
            if color:
                print(f"{color}{char}{Style.RESET_ALL}", end="", flush=True)
            else:
                print(char, end="", flush=True)
            time.sleep(delay)
        print()

    def thinking_animation(self, sentences, stop_event, esc_event):
        """等待动画"""
        if not sentences:
            sentences = ["AI正在思考中...", "请稍等片刻...", "正在处理您的请求..."]

        last_change = time.time()
        current_sentence = random.choice(sentences)
        chars = "|/-\\"
        idx = 0

        while not stop_event.is_set():
            now = time.time()
            if now - last_change >= 5:
                current_sentence = random.choice(sentences)
                last_change = now

            char = chars[idx % len(chars)]
            display = current_sentence[:47] + "..." if len(current_sentence) > 50 else current_sentence
            print(f"\r{Fore.MAGENTA}{display} {char}{Style.RESET_ALL}", end="", flush=True)
            idx += 1
            time.sleep(0.1)

        print("\r" + " " * 60 + "\r", end="", flush=True)

    def _limit_lines(self, text, max_lines=2):
        """限制输出行数"""
        lines = text.split('\n')
        if len(lines) <= max_lines:
            return text
        return '\n'.join(lines[:max_lines]) + f"\n... (已截断，共{len(lines)}行)"

    def show_banner(self, engine_name, engines, user_id):
        """显示启动横幅"""
        self.success(f"小狸 Pro-CLI 已启动!")
        self.success(f"用户ID: {user_id}")
        print(f"{Fore.GREEN}输入 '/help' 查看帮助信息{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/quit' 退出程序{Style.RESET_ALL}")
        print(f"{Fore.GREEN}当前引擎: {engine_name}{Style.RESET_ALL}")
        if len(engines) > 1:
            print(f"{Fore.GREEN}已加载引擎: {', '.join(engines)}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'-' * 50}{Style.RESET_ALL}")
