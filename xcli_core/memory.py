"""
持久化记忆系统
- MEMORY.md: 长期记忆（AI 自己维护的精华）
- memory/YYYY-MM-DD.md: 每日日记/日志
- chat_history/: 自动保存的聊天记录
- 支持关键词检索、上下文压缩、AI 写日记
"""
import os
import re
import json
import time
import glob
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple


class MemoryManager:
    """持久化记忆管理器"""

    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.memory_dir = os.path.join(project_dir, "memory")
        self.memory_file = os.path.join(project_dir, "MEMORY.md")
        self.chat_dir = os.path.join(project_dir, "chat_history")
        self.compress_threshold = 50  # 超过 50 条消息触发压缩（兜底）
        self.compress_ratio = 0.7    # token 感知压缩阈值：used/context_window >= 0.7 触发
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保目录存在"""
        os.makedirs(self.memory_dir, exist_ok=True)
        os.makedirs(self.chat_dir, exist_ok=True)

    # ══════════════════════════════════════════════
    #  MEMORY.md — 长期记忆
    # ══════════════════════════════════════════════

    def load_memory(self) -> str:
        """读取 MEMORY.md 内容"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception:
                return ""
        return ""

    def save_memory(self, content: str):
        """保存 MEMORY.md"""
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            f.write(content)

    def append_memory(self, section: str, content: str):
        """向 MEMORY.md 的指定 section 追加内容"""
        existing = self.load_memory()
        marker = f"## {section}"
        if marker in existing:
            # 在该 section 末尾追加
            parts = existing.split(marker, 1)
            after = parts[1]
            # 找到下一个 ## 或文件末尾
            next_section = after.find("\n## ")
            if next_section == -1:
                new_content = parts[0] + marker + after.rstrip() + "\n" + content + "\n"
            else:
                new_content = (parts[0] + marker + after[:next_section].rstrip() +
                              "\n" + content + "\n" + after[next_section:])
            self.save_memory(new_content)
        else:
            # 新增 section
            new_content = existing.rstrip() + f"\n\n{marker}\n{content}\n"
            self.save_memory(new_content)

    # ══════════════════════════════════════════════
    #  每日日记 — memory/YYYY-MM-DD.md
    # ══════════════════════════════════════════════

    def _today_file(self) -> str:
        """今天的日记文件路径"""
        return os.path.join(self.memory_dir, f"{datetime.now().strftime('%Y-%m-%d')}.md")

    def load_today(self) -> str:
        """读取今天的日记"""
        path = self._today_file()
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception:
                return ""
        return ""

    def write_diary(self, content: str, tag: str = ""):
        """写日记条目"""
        path = self._today_file()
        now = datetime.now().strftime("%H:%M")
        tag_str = f" [{tag}]" if tag else ""
        entry = f"\n### {now}{tag_str}\n{content}\n"

        existing = ""
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    existing = f.read()
            except Exception:
                pass

        if not existing:
            date_str = datetime.now().strftime("%Y-%m-%d")
            existing = f"# {date_str} 开发日志\n"

        with open(path, 'a', encoding='utf-8') as f:
            f.write(entry)

    def write_ai_diary(self, content: str):
        """AI 写日记（自动标记为 AI 观察）"""
        self.write_diary(content, tag="AI观察")

    def list_diary_files(self) -> List[str]:
        """列出所有日记文件"""
        files = glob.glob(os.path.join(self.memory_dir, "*.md"))
        files.sort(reverse=True)
        return [os.path.basename(f) for f in files]

    def load_diary(self, date_str: str) -> str:
        """读取指定日期的日记"""
        path = os.path.join(self.memory_dir, f"{date_str}.md")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception:
                return ""
        return ""

    # ══════════════════════════════════════════════
    #  聊天记录 — 自动保存
    # ══════════════════════════════════════════════

    def auto_save_chat(self, conversation: list, label: str = ""):
        """自动保存聊天记录"""
        if not conversation:
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if label:
            safe_label = re.sub(r'[^\w\u4e00-\u9fff-]', '_', label)[:30]
            filename = f"{timestamp}_{safe_label}.json"
        else:
            filename = f"{timestamp}.json"

        path = os.path.join(self.chat_dir, filename)
        chat_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "label": label,
            "message_count": len(conversation),
            "conversation": conversation
        }
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(chat_data, f, ensure_ascii=False, indent=2, default=str)
        except Exception:
            pass

    def list_chats(self, limit: int = 20) -> List[Dict]:
        """列出最近的聊天记录"""
        files = glob.glob(os.path.join(self.chat_dir, "*.json"))
        files.sort(key=os.path.getmtime, reverse=True)
        results = []
        for f in files[:limit]:
            try:
                mtime = os.path.getmtime(f)
                size = os.path.getsize(f)
                name = os.path.basename(f)
                results.append({
                    "name": name,
                    "time": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
                    "size_kb": round(size / 1024, 1),
                })
            except Exception:
                pass
        return results

    def load_chat(self, filename: str) -> Optional[list]:
        """加载指定的聊天记录"""
        path = os.path.join(self.chat_dir, filename)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get("conversation", [])
            except Exception:
                pass
        return None

    def search_chats(self, keyword: str, limit: int = 10) -> List[Dict]:
        """在聊天记录中搜索关键词"""
        keyword_lower = keyword.lower()
        results = []
        files = glob.glob(os.path.join(self.chat_dir, "*.json"))
        for f in files:
            try:
                with open(f, 'r', encoding='utf-8') as fobj:
                    data = json.load(fobj)
                conversation = data.get("conversation", [])
                for msg in conversation:
                    content = msg.get("content", "")
                    if isinstance(content, str) and keyword_lower in content.lower():
                        results.append({
                            "file": os.path.basename(f),
                            "time": data.get("timestamp", ""),
                            "snippet": content[:120],
                            "role": msg.get("role", ""),
                        })
                        break  # 每个文件只匹配一次
                if len(results) >= limit:
                    break
            except Exception:
                pass
        return results

    # ══════════════════════════════════════════════
    #  关键词检索 — 全局记忆搜索
    # ══════════════════════════════════════════════

    def search_memory(self, keyword: str, limit: int = 20) -> List[Dict]:
        """
        在所有记忆文件中搜索关键词
        搜索范围: MEMORY.md + memory/*.md + chat_history/*.json
        """
        keyword_lower = keyword.lower()
        results = []

        # 搜索 MEMORY.md
        if os.path.exists(self.memory_file):
            results.extend(self._search_file(
                self.memory_file, keyword_lower, "MEMORY.md", limit - len(results)
            ))

        # 搜索日记文件
        for md_file in sorted(glob.glob(os.path.join(self.memory_dir, "*.md")), reverse=True):
            if len(results) >= limit:
                break
            name = f"memory/{os.path.basename(md_file)}"
            results.extend(self._search_file(
                md_file, keyword_lower, name, limit - len(results)
            ))

        # 搜索聊天记录
        for json_file in sorted(glob.glob(os.path.join(self.chat_dir, "*.json")), reverse=True):
            if len(results) >= limit:
                break
            name = f"chat/{os.path.basename(json_file)}"
            results.extend(self._search_json_file(
                json_file, keyword_lower, name, limit - len(results)
            ))

        return results[:limit]

    def _search_file(self, path: str, keyword: str, source: str, limit: int) -> List[Dict]:
        """在单个文件中搜索"""
        results = []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            for i, line in enumerate(lines):
                if keyword in line.lower():
                    snippet = line.strip()[:120]
                    results.append({
                        "source": source,
                        "line": i + 1,
                        "snippet": snippet,
                    })
                    if len(results) >= limit:
                        break
        except Exception:
            pass
        return results

    def _search_json_file(self, path: str, keyword: str, source: str, limit: int) -> List[Dict]:
        """在 JSON 聊天记录中搜索"""
        results = []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for msg in data.get("conversation", []):
                content = msg.get("content", "")
                if isinstance(content, str) and keyword in content.lower():
                    results.append({
                        "source": source,
                        "role": msg.get("role", ""),
                        "snippet": content[:120],
                    })
                    if len(results) >= limit:
                        break
        except Exception:
            pass
        return results

    # ══════════════════════════════════════════════
    #  上下文压缩
    # ══════════════════════════════════════════════

    def set_compress_ratio(self, ratio: float):
        """设置 token 感知压缩阈值（0~1）"""
        try:
            self.compress_ratio = float(ratio)
        except (TypeError, ValueError):
            pass

    def should_compress(self, conversation: list, prompt_tokens=None, max_input_tokens=None, ratio=None) -> bool:
        """
        判断是否需要压缩上下文。
        优先级:
          1. token 感知: prompt_tokens/max_input_tokens >= ratio 触发（引擎需返回 max_input_tokens）
          2. 兜底: 消息数超过 compress_threshold
        """
        if ratio is None:
            ratio = self.compress_ratio
        if prompt_tokens and max_input_tokens:
            try:
                if int(max_input_tokens) > 0 and (int(prompt_tokens) / int(max_input_tokens)) >= ratio:
                    return True
            except (TypeError, ValueError):
                pass
        return len(conversation) > self.compress_threshold

    def compress_context(self, conversation: list, engine=None) -> list:
        """
        压缩对话历史
        策略: 保留最近 10 条 + 用 AI 总结前面的内容
        """
        if len(conversation) <= 10:
            return conversation

        keep_recent = 10
        to_compress = conversation[:-keep_recent]
        recent = conversation[-keep_recent:]

        # 尝试用 AI 生成摘要
        summary = self._ai_summarize(to_compress, engine)

        # 构建压缩后的历史
        compressed = [{
            "role": "system",
            "content": f"[上下文压缩] 以下是之前 {len(to_compress)} 条对话的摘要:\n{summary}"
        }]
        compressed.extend(recent)
        return compressed

    def _ai_summarize(self, messages: list, engine=None) -> str:
        """用 AI 生成对话摘要"""
        if not engine:
            return self._simple_summarize(messages)

        # 构建摘要请求
        conversation_text = ""
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if isinstance(content, str):
                conversation_text += f"[{role}]: {content[:200]}\n"

        prompt = (
            "请用简洁的中文总结以下对话的关键信息（工具调用、代码修改、重要决策）。"
            "控制在 200 字以内。\n\n"
            f"{conversation_text}"
        )

        try:
            summary = engine.generate_response(
                prompt,
                system_prompt="你是摘要生成器。只输出摘要，不要多余内容。"
            )
            if summary and len(summary) > 10:
                return summary
        except Exception:
            pass

        return self._simple_summarize(messages)

    def _simple_summarize(self, messages: list) -> str:
        """简单摘要（不依赖 AI）"""
        topics = []
        tool_calls = []
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")
            if role == "user" and isinstance(content, str):
                # 提取用户请求
                if len(content) < 100:
                    topics.append(content)
                else:
                    topics.append(content[:50] + "...")
            if role == "assistant" and isinstance(content, str):
                # 提取工具调用
                if '"action": "use_tool"' in content or '"tool":' in content:
                    try:
                        # 尝试解析工具名
                        for part in content.split('"tool":'):
                            if len(part) > 2:
                                tool_name = part.split('"')[1] if '"' in part else ""
                                if tool_name and tool_name not in tool_calls:
                                    tool_calls.append(tool_name)
                    except Exception:
                        pass

        summary_parts = []
        if topics:
            summary_parts.append(f"讨论了 {len(topics)} 个话题: {'; '.join(topics[:5])}")
        if tool_calls:
            summary_parts.append(f"使用了工具: {', '.join(tool_calls[:8])}")
        summary_parts.append(f"共 {len(messages)} 条对话")

        return "。".join(summary_parts)

    # ══════════════════════════════════════════════
    #  构建记忆上下文（注入系统提示词）
    # ══════════════════════════════════════════════

    def build_memory_context(self) -> str:
        """构建记忆上下文，用于注入系统提示词"""
        parts = []

        # 加载 MEMORY.md
        memory = self.load_memory()
        if memory:
            parts.append(f"【长期记忆 MEMORY.md】\n{memory[:2000]}")

        # 加载今天的日记
        today = self.load_today()
        if today:
            parts.append(f"【今日日志】\n{today[:1000]}")

        if not parts:
            return ""

        return (
            "\n\n---\n"
            "以下是你的持久化记忆，帮助你了解之前的工作和上下文:\n\n"
            + "\n\n".join(parts)
            + "\n---\n"
        )

    # ══════════════════════════════════════════════
    #  工具接口（供 AI 调用）
    # ══════════════════════════════════════════════

    def handle_tool(self, args: str) -> str:
        """处理 memory 工具调用"""
        if not args or not args.strip():
            return self._tool_help()

        parts = args.strip().split(None, 1)
        action = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""

        if action == "write":
            if not rest:
                return "用法: memory write <内容>"
            self.write_diary(rest)
            return f"日记已写入 {datetime.now().strftime('%Y-%m-%d')}"

        elif action == "diary":
            if not rest:
                return "用法: memory diary <AI观察内容>"
            self.write_ai_diary(rest)
            return f"AI 日记已写入"

        elif action == "remember":
            if not rest:
                return "用法: memory remember <要记住的内容>"
            self.append_memory("备忘", f"- {rest}")
            return f"已记录到 MEMORY.md"

        elif action == "search":
            if not rest:
                return "用法: memory search <关键词>"
            results = self.search_memory(rest)
            if not results:
                return f"未找到与 '{rest}' 相关的记忆"
            lines = [f"搜索 '{rest}' 的结果:"]
            for r in results:
                source = r.get("source", "")
                snippet = r.get("snippet", "")
                role = r.get("role", "")
                prefix = f"[{role}] " if role else ""
                lines.append(f"  📄 {source}: {prefix}{snippet}")
            return "\n".join(lines)

        elif action == "context":
            ctx = self.build_memory_context()
            return ctx if ctx else "当前没有记忆上下文"

        elif action == "diary_list":
            files = self.list_diary_files()
            if not files:
                return "还没有日记文件"
            return "日记文件:\n" + "\n".join(f"  📅 {f}" for f in files[:20])

        elif action == "diary_read":
            if not rest:
                return "用法: memory diary_read <日期，如 2026-04-27>"
            content = self.load_diary(rest)
            return content if content else f"没有找到 {rest} 的日记"

        elif action == "chat_list":
            chats = self.list_chats()
            if not chats:
                return "没有保存的聊天记录"
            lines = ["最近的聊天记录:"]
            for c in chats:
                lines.append(f"  💬 {c['name']} ({c['time']}, {c['size_kb']}KB)")
            return "\n".join(lines)

        elif action == "chat_search":
            if not rest:
                return "用法: memory chat_search <关键词>"
            results = self.search_chats(rest)
            if not results:
                return f"未在聊天记录中找到 '{rest}'"
            lines = [f"聊天记录搜索 '{rest}':"]
            for r in results:
                lines.append(f"  💬 {r['file']} [{r['role']}]: {r['snippet']}")
            return "\n".join(lines)

        else:
            return f"未知操作: {action}\n" + self._tool_help()

    def _tool_help(self) -> str:
        return """memory 工具用法:
  memory write <内容>          - 写日记
  memory diary <内容>          - AI 写观察日记
  memory remember <内容>       - 记录到长期记忆 (MEMORY.md)
  memory search <关键词>       - 搜索所有记忆
  memory context               - 查看当前记忆上下文
  memory diary_list            - 列出所有日记
  memory diary_read <日期>     - 读取指定日期日记
  memory chat_list             - 列出聊天记录
  memory chat_search <关键词>  - 在聊天记录中搜索"""


# ══════════════════════════════════════════════
#  记忆插件（注册到插件系统）
# ══════════════════════════════════════════════

class Liugin:
    """记忆系统插件 — AI 可读写记忆、搜索历史"""

    def __init__(self):
        self.cli = None
        self.memory = None
        self.usage = """记忆系统工具使用方法：

JSON格式示例：
{"action": "use_tool", "tool": "memory", "args": "write 今天完成了v5.2的开发"} - 写日记
{"action": "use_tool", "tool": "memory", "args": "diary 用户偏好使用中文交流"} - AI观察日记
{"action": "use_tool", "tool": "memory", "args": "remember 项目使用MIT协议"} - 记到长期记忆
{"action": "use_tool", "tool": "memory", "args": "search 定时任务"} - 搜索所有记忆
{"action": "use_tool", "tool": "memory", "args": "context"} - 查看记忆上下文
{"action": "use_tool", "tool": "memory", "args": "diary_list"} - 列出日记
{"action": "use_tool", "tool": "memory", "args": "diary_read 2026-04-27"} - 读日记
{"action": "use_tool", "tool": "memory", "args": "chat_list"} - 列出聊天记录
{"action": "use_tool", "tool": "memory", "args": "chat_search 关键词"} - 搜聊天记录

功能说明:
- write: 写当日日记
- diary: AI 自己写观察日记
- remember: 写入 MEMORY.md 长期记忆
- search: 全局关键词搜索（日记+记忆+聊天记录）
- context: 查看当前注入的上下文
- diary_list / diary_read: 管理日记
- chat_list / chat_search: 管理聊天记录"""

    def set_cli(self, cli):
        self.cli = cli
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.memory = MemoryManager(project_dir)
        # 挂载到 cli 实例上供其他模块使用
        cli.memory_manager = self.memory
        # 注册命令
        self.cli.register_liugin_command('memory', self.command_handler)

    def command_handler(self, args):
        return self.handle(args)

    def get_tool_info(self):
        return {
            "name": "memory",
            "description": "持久化记忆系统。AI 可写日记、记录长期记忆、搜索历史记忆和聊天记录。支持关键词检索。",
            "keywords": ["记忆", "memory", "日记", "diary", "搜索", "search", "历史", "history", "remember"],
            "usage": self.usage
        }

    def handle(self, args: str) -> str:
        if not self.memory:
            return "记忆系统未初始化"
        return self.memory.handle_tool(args)

    def get_mcp_definition(self):
        return {
            "name": "memory",
            "description": "持久化记忆系统",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["write", "diary", "remember", "search", "context",
                                "diary_list", "diary_read", "chat_list", "chat_search"],
                        "description": "操作类型"
                    },
                    "content": {
                        "type": "string",
                        "description": "内容/关键词"
                    }
                },
                "required": ["action"]
            }
        }
