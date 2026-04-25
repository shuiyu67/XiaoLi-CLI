"""对话历史管理"""
import os
import json
import time
import logging
from typing import Optional
from colorama import Fore, Style

logger = logging.getLogger(__name__)


class History:
    """对话历史管理器"""

    def __init__(self, history_dir: str, max_items: int = 999999):
        self.dir = history_dir
        self.max = max_items
        self.messages = []

        os.makedirs(self.dir, exist_ok=True)

    def add(self, role: str, content: str):
        """添加消息"""
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > self.max:
            self.messages = self.messages[-self.max:]

    def get(self) -> list:
        """获取全部历史"""
        return self.messages

    def clear(self):
        """清空历史"""
        self.messages = []

    def set_all(self, messages: list):
        """设置全部历史"""
        self.messages = messages

    def save(self, name: str) -> bool:
        """保存到文件"""
        try:
            data = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "conversation": self.messages.copy()
            }
            path = os.path.join(self.dir, f"{name}.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            print(f"{Fore.GREEN}聊天记录已保存: {name}{Style.RESET_ALL}")
            return True
        except Exception as e:
            print(f"{Fore.RED}保存失败: {e}{Style.RESET_ALL}")
            return False

    def load(self, name: str) -> bool:
        """从文件加载"""
        try:
            path = os.path.join(self.dir, f"{name}.json")
            if not os.path.exists(path):
                print(f"{Fore.RED}记录 '{name}' 不存在{Style.RESET_ALL}")
                return False
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.messages = data.get("conversation", [])
            print(f"{Fore.GREEN}已加载: {name} ({len(self.messages)} 条){Style.RESET_ALL}")
            return True
        except Exception as e:
            print(f"{Fore.RED}加载失败: {e}{Style.RESET_ALL}")
            return False

    def list_saved(self):
        """列出所有已保存的记录"""
        try:
            files = [f for f in os.listdir(self.dir) if f.endswith('.json')]
            if not files:
                print(f"{Fore.YELLOW}没有已保存的记录{Style.RESET_ALL}")
                return
            print(f"{Fore.GREEN}已保存的记录:{Style.RESET_ALL}")
            for i, f in enumerate(files, 1):
                path = os.path.join(self.dir, f)
                mtime = time.strftime("%Y-%m-%d %H:%M:%S",
                                      time.localtime(os.path.getmtime(path)))
                print(f"{Fore.GREEN}{i}. {f[:-5]} ({mtime}){Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}列出记录失败: {e}{Style.RESET_ALL}")
