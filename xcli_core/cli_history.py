import os
import time
import json
from colorama import Fore, Style


class HistoryMixin:
    """聊天记录管理相关方法"""

    def save_chat_history(self, name):
        """保存当前聊天记录到文件"""
        try:
            chat_data = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "conversation": self.shared_conversation_history.copy()
            }
            file_path = os.path.join(self.chat_history_dir, f"{name}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(chat_data, f, ensure_ascii=False, indent=2, default=str)
            print(f"{Fore.GREEN}聊天记录已保存为: {name}{Style.RESET_ALL}")
            return True
        except Exception as e:
            print(f"{Fore.RED}保存聊天记录失败: {e}{Style.RESET_ALL}")
            return False

    def list_chat_history(self):
        """列出所有已保存的聊天记录"""
        try:
            chat_files = [f for f in os.listdir(self.chat_history_dir) if f.endswith('.json')]
            if not chat_files:
                print(f"{Fore.YELLOW}没有已保存的聊天记录{Style.RESET_ALL}")
                return
            print(f"{Fore.GREEN}已保存的聊天记录:{Style.RESET_ALL}")
            for i, file in enumerate(chat_files, 1):
                file_path = os.path.join(self.chat_history_dir, file)
                mod_time = os.path.getmtime(file_path)
                mod_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mod_time))
                chat_name = file[:-5]
                print(f"{Fore.GREEN}{i}. {chat_name} (保存时间: {mod_time_str}){Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}列出聊天记录失败: {e}{Style.RESET_ALL}")

    def load_chat_history(self, name):
        """加载指定的聊天记录"""
        try:
            file_path = os.path.join(self.chat_history_dir, f"{name}.json")
            if not os.path.exists(file_path):
                print(f"{Fore.RED}聊天记录 '{name}' 不存在{Style.RESET_ALL}")
                return False
            with open(file_path, 'r', encoding='utf-8') as f:
                chat_data = json.load(f)
            self.shared_conversation_history = chat_data.get("conversation", [])
            self._set_shared_conversation_history()
            print(f"{Fore.GREEN}已加载聊天记录: {name}{Style.RESET_ALL}")
            if self.shared_conversation_history:
                print(f"{Fore.CYAN}加载了 {len(self.shared_conversation_history)} 条对话记录{Style.RESET_ALL}")
            return True
        except Exception as e:
            print(f"{Fore.RED}加载聊天记录失败: {e}{Style.RESET_ALL}")
            return False
