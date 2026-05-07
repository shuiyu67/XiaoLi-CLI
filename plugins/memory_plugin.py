"""
记忆系统插件 — 包装 xcli_core/memory.py 中的 MemoryManager
使 AI 可以通过工具接口读写日记、搜索记忆、管理聊天记录
"""
import os
import sys

# 添加项目根目录到 path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from xcli_core.memory import MemoryManager


class Liugin:
    """持久化记忆系统 — AI 可写日记、搜索记忆、管理聊天记录"""

    def __init__(self):
        self.cli = None
        self.memory = None
        self.usage = """持久化记忆系统工具

操作:
  diary <内容>                    - 写当日日记
  diary_ai <内容>                 - AI 写观察日记（标记为 AI 观察）
  remember <内容>                 - 记录到长期记忆 (MEMORY.md)
  search <关键词>                 - 全局搜索（日记+记忆+聊天记录）
  context                         - 查看当前注入的记忆上下文
  diary_list                      - 列出所有日记文件
  diary_read <日期>               - 读取指定日期的日记（如 2026-04-27）
  chat_list                       - 列出最近的聊天记录
  chat_search <关键词>            - 在聊天记录中搜索
  memory_read                     - 读取 MEMORY.md 长期记忆
  memory_write <内容>             - 写入 MEMORY.md（追加）

JSON 格式示例:
  {"action": "use_tool", "tool": "memory_plugin", "args": "diary 今天完成了API对接"}
  {"action": "use_tool", "tool": "memory_plugin", "args": "search 定时任务"}
  {"action": "use_tool", "tool": "memory_plugin", "args": "remember 用户偏好深色主题"}
"""

    def set_cli(self, cli):
        self.cli = cli
        # 初始化 MemoryManager
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.memory = MemoryManager(project_dir)
        # 挂载到 cli 实例上，让 cli_core.py 能访问
        cli.memory_manager = self.memory

    def get_tool_info(self):
        return {
            "name": "memory_plugin",
            "description": "持久化记忆系统 — AI 可写日记、记录长期记忆、搜索历史对话和日记。支持自动压缩上下文。",
            "keywords": ["记忆", "memory", "日记", "diary", "搜索", "search", "历史", "history",
                         "remember", "聊天记录", "chat", "上下文", "context", "压缩", "compress"],
            "usage": self.usage
        }

    def handle(self, args: str) -> str:
        if not self.memory:
            return "错误：记忆系统未初始化"

        if not args or not args.strip():
            return self._help()

        parts = args.strip().split(None, 1)
        action = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""

        handlers = {
            "diary": self._diary,
            "diary_ai": self._diary_ai,
            "remember": self._remember,
            "search": self._search,
            "context": self._context,
            "diary_list": self._diary_list,
            "diary_read": self._diary_read,
            "chat_list": self._chat_list,
            "chat_search": self._chat_search,
            "memory_read": self._memory_read,
            "memory_write": self._memory_write,
            "help": lambda _: self._help(),
        }

        handler = handlers.get(action)
        if not handler:
            return f"未知操作: {action}\n" + self._help()

        return handler(rest)

    def _diary(self, content: str) -> str:
        if not content:
            return "错误：请提供日记内容\n用法: diary <内容>"
        self.memory.write_diary(content)
        return f" 日记已写入 {self.memory._today_file()}"

    def _diary_ai(self, content: str) -> str:
        if not content:
            return "错误：请提供 AI 观察内容\n用法: diary_ai <内容>"
        self.memory.write_ai_diary(content)
        return f" AI 观察日记已写入"

    def _remember(self, content: str) -> str:
        if not content:
            return "错误：请提供要记住的内容\n用法: remember <内容>"
        self.memory.append_memory("备忘", f"- {content}")
        return f" 已记录到 MEMORY.md 长期记忆"

    def _search(self, keyword: str) -> str:
        if not keyword:
            return "错误：请提供搜索关键词\n用法: search <关键词>"
        results = self.memory.search_memory(keyword)
        if not results:
            return f" 未找到与 '{keyword}' 相关的记忆"
        lines = [f" 搜索 '{keyword}' 的结果 ({len(results)} 条):"]
        for r in results:
            source = r.get("source", "")
            snippet = r.get("snippet", "")
            role = r.get("role", "")
            line_num = r.get("line", "")
            prefix = f"[{role}] " if role else ""
            line_info = f" (L{line_num})" if line_num else ""
            lines.append(f"   {source}{line_info}: {prefix}{snippet}")
        return "\n".join(lines)

    def _context(self, _: str) -> str:
        ctx = self.memory.build_memory_context()
        return ctx if ctx else " 当前没有记忆上下文"

    def _diary_list(self, _: str) -> str:
        files = self.memory.list_diary_files()
        if not files:
            return " 还没有日记文件"
        return " 日记文件:\n" + "\n".join(f"   {f}" for f in files[:20])

    def _diary_read(self, date_str: str) -> str:
        if not date_str:
            return "错误：请提供日期\n用法: diary_read <日期，如 2026-04-27>"
        content = self.memory.load_diary(date_str)
        return content if content else f" 没有找到 {date_str} 的日记"

    def _chat_list(self, _: str) -> str:
        chats = self.memory.list_chats()
        if not chats:
            return " 没有保存的聊天记录"
        lines = [" 最近的聊天记录:"]
        for c in chats:
            lines.append(f"   {c['name']} ({c['time']}, {c['size_kb']}KB)")
        return "\n".join(lines)

    def _chat_search(self, keyword: str) -> str:
        if not keyword:
            return "错误：请提供关键词\n用法: chat_search <关键词>"
        results = self.memory.search_chats(keyword)
        if not results:
            return f" 未在聊天记录中找到 '{keyword}'"
        lines = [f" 聊天记录搜索 '{keyword}':"]
        for r in results:
            lines.append(f"   {r['file']} [{r['role']}]: {r['snippet']}")
        return "\n".join(lines)

    def _memory_read(self, _: str) -> str:
        content = self.memory.load_memory()
        return content if content else " MEMORY.md 为空"

    def _memory_write(self, content: str) -> str:
        if not content:
            return "错误：请提供内容\n用法: memory_write <内容>"
        self.memory.append_memory("备忘", f"- {content}")
        return f" 已写入 MEMORY.md"

    def _help(self) -> str:
        return """ 记忆系统用法:
  diary <内容>          - 写当日日记
  diary_ai <内容>       - AI 写观察日记
  remember <内容>       - 记到长期记忆 (MEMORY.md)
  search <关键词>       - 全局搜索记忆
  context               - 查看记忆上下文
  diary_list            - 列出日记
  diary_read <日期>     - 读取日记
  chat_list             - 列出聊天记录
  chat_search <关键词>  - 搜索聊天记录
  memory_read           - 读取 MEMORY.md
  memory_write <内容>   - 写入 MEMORY.md"""
