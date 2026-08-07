import os
import time
import json
from colorama import Fore, Style
from .session import SessionManager


class HistoryMixin:
    """聊天记录管理相关方法（含 opencode 式会话持久化 /resume）"""

    def save_chat_history(self, name):
        """保存当前聊天记录（SQLite 快照）"""
        try:
            if not hasattr(self, 'session_manager'):
                self.init_session_manager()
            ok = self.session_manager.save_snapshot(
                name, self.shared_conversation_history.copy())
            if ok:
                print(f"{Fore.GREEN}聊天记录已保存为: {name}{Style.RESET_ALL}")
                return True
            print(f"{Fore.RED}保存聊天记录失败{Style.RESET_ALL}")
            return False
        except Exception as e:
            print(f"{Fore.RED}保存聊天记录失败: {e}{Style.RESET_ALL}")
            return False

    def list_chat_history(self):
        """列出所有已保存的聊天记录"""
        try:
            if not hasattr(self, 'session_manager'):
                self.init_session_manager()
            snaps = self.session_manager.list_snapshots()
            if not snaps:
                print(f"{Fore.YELLOW}没有已保存的聊天记录{Style.RESET_ALL}")
                return
            print(f"{Fore.GREEN}已保存的聊天记录:{Style.RESET_ALL}")
            for i, (chat_name, saved_at) in enumerate(snaps, 1):
                print(f"{Fore.GREEN}{i}. {chat_name} (保存时间: {saved_at}){Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}列出聊天记录失败: {e}{Style.RESET_ALL}")

    def load_chat_history(self, name):
        """加载指定的聊天记录（SQLite 快照）"""
        try:
            if not hasattr(self, 'session_manager'):
                self.init_session_manager()
            msgs = self.session_manager.load_snapshot(name)
            if msgs is None:
                print(f"{Fore.RED}聊天记录 '{name}' 不存在{Style.RESET_ALL}")
                return False
            self.shared_conversation_history = list(msgs)
            self._set_shared_conversation_history()
            print(f"{Fore.GREEN}已加载聊天记录: {name}{Style.RESET_ALL}")
            if self.shared_conversation_history:
                print(f"{Fore.CYAN}加载了 {len(self.shared_conversation_history)} 条对话记录{Style.RESET_ALL}")
            return True
        except Exception as e:
            print(f"{Fore.RED}加载聊天记录失败: {e}{Style.RESET_ALL}")
            return False

    # ── opencode 式会话（自动持久化 + /resume） ──

    def init_session_manager(self):
        """初始化会话管理器与当前会话状态。在 chat_history_dir 就绪后调用。"""
        self.session_manager = SessionManager(self.chat_history_dir)
        self.current_session = None  # 首轮对话时惰性创建

    def _autosave_session(self):
        """每轮对话后调用：把当前会话落盘（首轮自动建会话）。"""
        if not getattr(self, 'shared_conversation_history', None):
            return
        if not hasattr(self, 'session_manager'):
            return
        engine = getattr(self.current_engine, 'name', None) if self.current_engine else None
        model = getattr(self, 'current_model', None)
        try:
            if self.current_session is None:
                self.current_session = self.session_manager.new_session(engine=engine, model=model)
            self.session_manager.save(
                self.current_session, self.shared_conversation_history,
                engine=engine, model=model,
            )
        except Exception:
            pass  # 自动保存失败不应中断对话

    def handle_resume_command(self, args):
        """/resume 命令：列出或恢复历史会话。"""
        args = (args or "").strip()
        if not hasattr(self, 'session_manager'):
            self.init_session_manager()
        if args == 'new':
            self.current_session = None
            print(f"{Fore.GREEN}已开始新会话（下一轮对话自动创建）{Style.RESET_ALL}")
            return
        sessions = self.session_manager.list_sessions()
        if not sessions:
            print(f"{Fore.YELLOW}没有可恢复的会话{Style.RESET_ALL}")
            return
        if not args:
            print(f"{Fore.GREEN}已保存的会话 (按时间倒序):{Style.RESET_ALL}")
            for i, s in enumerate(sessions, 1):
                line = f"{Fore.GREEN}{i}. {s.id}{Style.RESET_ALL}  {s.title}"
                meta = f"   {s.updated_at}  {s.engine or '-'}/{s.model or '-'}  {s.msg_count} 条"
                print(line + f"{Fore.CYAN}{meta}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}用法: /resume <序号或ID> 恢复 · /resume new 开新会话{Style.RESET_ALL}")
            return
        s = self.session_manager.load(args)
        if s is None:
            print(f"{Fore.RED}未找到会话: {args}{Style.RESET_ALL}")
            return
        self.shared_conversation_history = list(s.messages)
        self.current_session = s
        self._set_shared_conversation_history()
        print(f"{Fore.GREEN}已恢复会话: {s.id}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}标题: {s.title} · {s.msg_count} 条记录 · 引擎 {s.engine or '-'}/{s.model or '-'}{Style.RESET_ALL}")
        cur = getattr(self.current_engine, 'name', None) if self.current_engine else None
        if s.engine and cur and cur != s.engine:
            print(f"{Fore.YELLOW}提示: 当前引擎为 {cur}，可用 /engine switch {s.engine} 切回该会话的引擎{Style.RESET_ALL}")
