from colorama import Fore, Style


class HistoryMixin:
    """聊天记录管理 — 统一委托给 MemoryManager"""

    def save_chat_history(self, name):
        """保存当前聊天记录"""
        if not hasattr(self, 'memory_manager') or not self.memory_manager:
            print(f"{Fore.RED}记忆系统未初始化{Style.RESET_ALL}")
            return False
        self.memory_manager.auto_save_chat(
            self.shared_conversation_history,
            label=name
        )
        print(f"{Fore.GREEN}聊天记录已保存: {name}{Style.RESET_ALL}")
        return True

    def list_chat_history(self):
        """列出所有聊天记录"""
        if not hasattr(self, 'memory_manager') or not self.memory_manager:
            print(f"{Fore.RED}记忆系统未初始化{Style.RESET_ALL}")
            return
        chats = self.memory_manager.list_chats(limit=30)
        if not chats:
            print(f"{Fore.YELLOW}没有已保存的聊天记录{Style.RESET_ALL}")
            return
        print(f"{Fore.GREEN}已保存的聊天记录:{Style.RESET_ALL}")
        for i, c in enumerate(chats, 1):
            print(f"{Fore.GREEN}{i}. {c['name']} ({c['time']}, {c['size_kb']}KB){Style.RESET_ALL}")

    def load_chat_history(self, name):
        """加载聊天记录（支持序号或文件名）"""
        if not hasattr(self, 'memory_manager') or not self.memory_manager:
            print(f"{Fore.RED}记忆系统未初始化{Style.RESET_ALL}")
            return False

        # 支持序号加载
        if name.isdigit():
            chats = self.memory_manager.list_chats(limit=50)
            idx = int(name) - 1
            if 0 <= idx < len(chats):
                name = chats[idx]['name'].replace('.json', '')
            else:
                print(f"{Fore.RED}序号 {name} 超出范围{Style.RESET_ALL}")
                return False

        conversation = self.memory_manager.load_chat(name)
        if conversation is None:
            # 尝试加 .json 后缀
            if not name.endswith('.json'):
                conversation = self.memory_manager.load_chat(name + '.json')
        if conversation is None:
            print(f"{Fore.RED}聊天记录 '{name}' 不存在{Style.RESET_ALL}")
            return False

        self.shared_conversation_history = conversation
        self._set_shared_conversation_history()
        print(f"{Fore.GREEN}已加载聊天记录: {name}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}加载了 {len(conversation)} 条对话记录{Style.RESET_ALL}")
        return True
