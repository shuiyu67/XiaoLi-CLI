"""
定时任务插件 - AI 可设定定时任务，到时自动激活提醒
支持一次性和重复性定时任务
"""
import json
import os
import time
import threading
from datetime import datetime, timedelta
from colorama import Fore, Style


class Liugin:
    """定时任务插件"""

    def __init__(self):
        self.usage = """定时任务工具使用方法：

JSON格式示例：
{"action": "use_tool", "tool": "scheduler", "args": "add 30m 提醒我检查代码"} - 30分钟后提醒
{"action": "use_tool", "tool": "scheduler", "args": "add 2h 提交代码"} - 2小时后提醒
{"action": "use_tool", "tool": "scheduler", "args": "add 14:30 开会"} - 今天14:30提醒
{"action": "use_tool", "tool": "scheduler", "args": "add 2026-04-28 10:00 发布v5.2"} - 指定日期时间提醒
{"action": "use_tool", "tool": "scheduler", "args": "list"} - 列出所有定时任务
{"action": "use_tool", "tool": "scheduler", "args": "delete 1"} - 删除任务ID为1的任务
{"action": "use_tool", "tool": "scheduler", "args": "clear"} - 清除所有已完成/已取消的任务

时间格式说明：
- 相对时间: 30s / 30m / 2h / 1d（秒/分/时/天）
- 今日时间: HH:MM（如 14:30）
- 绝对时间: YYYY-MM-DD HH:MM（如 2026-04-28 10:00）
- 重复任务: 每个时间前加 r: 前缀，如 r:30m / r:2h / r:14:30
  重复任务会自动重新调度，不会自动删除

功能说明：
- add <时间> <描述> - 添加定时任务
- list - 列出所有定时任务
- delete <任务ID> - 删除指定任务
- clear - 清除已完成/已取消的任务

当定时任务到期时，AI 会自动被激活并收到提醒。"""

        self.cli = None
        self.tasks_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "scheduler_tasks.json"
        )
        self.tasks = []
        self._lock = threading.Lock()
        self._monitor_thread = None
        self._monitor_running = False
        self._load_tasks()

    def set_cli(self, cli):
        """设置CLI实例引用"""
        self.cli = cli
        self.cli.register_liugin_command('scheduler', self.command_handler)
        self.cli.register_liugin_command('remind', self.command_handler)
        # 启动后台监控线程
        self._start_monitor()

    def command_handler(self, args):
        """处理 /scheduler 或 /remind 命令"""
        return self.handle(args)

    def get_tool_info(self):
        return {
            "name": "scheduler",
            "description": "定时任务工具，AI 可设定定时提醒。支持相对时间(30m/2h)、今日时间(14:30)、绝对时间(2026-04-28 10:00)、重复任务(r:30m)",
            "keywords": ["定时", "提醒", "scheduler", "remind", "闹钟", "alarm", "schedule", "计划"],
            "usage": self.usage
        }

    # ── 数据持久化 ──

    def _load_tasks(self):
        """从文件加载任务"""
        try:
            if os.path.exists(self.tasks_file):
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    self.tasks = json.load(f)
        except Exception:
            self.tasks = []

    def _save_tasks(self):
        """保存任务到文件"""
        try:
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ── 时间解析 ──

    def _parse_time(self, time_str: str) -> tuple:
        """
        解析时间字符串
        返回: (datetime, is_repeat, repeat_seconds)
        """
        time_str = time_str.strip()
        now = datetime.now()
        is_repeat = False
        repeat_seconds = 0

        # 检查是否是重复任务
        if time_str.startswith('r:'):
            is_repeat = True
            time_str = time_str[2:].strip()

        # 相对时间: 30s / 30m / 2h / 1d
        if time_str[-1:].lower() in ('s', 'm', 'h', 'd') and time_str[:-1].strip().isdigit():
            num = int(time_str[:-1].strip())
            unit = time_str[-1].lower()
            multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
            seconds = num * multipliers[unit]
            if is_repeat:
                repeat_seconds = seconds
            return now + timedelta(seconds=seconds), is_repeat, repeat_seconds

        # 绝对时间: YYYY-MM-DD HH:MM
        try:
            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
            if is_repeat:
                # 重复任务的绝对时间当作每日重复
                repeat_seconds = 86400  # 24h
            return dt, is_repeat, repeat_seconds
        except ValueError:
            pass

        # 今日时间: HH:MM
        try:
            dt = datetime.strptime(time_str, "%H:%M")
            target = now.replace(hour=dt.hour, minute=dt.minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            if is_repeat:
                repeat_seconds = 86400
            return target, is_repeat, repeat_seconds
        except ValueError:
            pass

        return None, False, 0

    # ── 核心操作 ──

    def _add_task(self, time_str: str, message: str) -> str:
        """添加定时任务"""
        target_time, is_repeat, repeat_seconds = self._parse_time(time_str)
        if target_time is None:
            return f"无法解析时间: {time_str}。支持格式: 30m / 2h / 14:30 / 2026-04-28 10:00 / r:30m"

        with self._lock:
            task_id = max([t.get('id', 0) for t in self.tasks], default=0) + 1
            task = {
                "id": task_id,
                "message": message,
                "trigger_at": target_time.strftime("%Y-%m-%d %H:%M:%S"),
                "repeat": is_repeat,
                "repeat_seconds": repeat_seconds,
                "status": "pending",  # pending / fired / canceled
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self.tasks.append(task)
            self._save_tasks()

        time_display = target_time.strftime("%Y-%m-%d %H:%M:%S")
        repeat_info = f" (每{self._format_seconds(repeat_seconds)}重复)" if is_repeat else ""
        return f"定时任务 #{task_id} 已创建{repeat_info}\n⏰ {time_display} → {message}"

    def _list_tasks(self) -> str:
        """列出所有定时任务"""
        with self._lock:
            if not self.tasks:
                return "暂无定时任务"

            lines = []
            now = datetime.now()
            for t in self.tasks:
                tid = t['id']
                status = t['status']
                msg = t['message']
                trigger = t['trigger_at']
                repeat = t.get('repeat', False)

                # 状态图标
                if status == 'pending':
                    remaining = self._calc_remaining(trigger, now)
                    icon = "⏰"
                    suffix = f" ({remaining})" if remaining else ""
                    repeat_tag = f" [每{self._format_seconds(t.get('repeat_seconds', 0))}重复]" if repeat else ""
                    lines.append(f"  {icon} #{tid}{suffix}{repeat_tag}: {msg}")
                elif status == 'fired':
                    lines.append(f"  ✅ #{tid} (已触发): {msg}")
                elif status == 'canceled':
                    lines.append(f"  ❌ #{tid} (已取消): {msg}")

            return "\n".join(lines) if lines else "暂无定时任务"

    def _delete_task(self, task_id_str: str) -> str:
        """删除指定任务"""
        try:
            task_id = int(task_id_str)
        except ValueError:
            return f"无效的任务ID: {task_id_str}"

        with self._lock:
            for t in self.tasks:
                if t['id'] == task_id:
                    t['status'] = 'canceled'
                    self._save_tasks()
                    return f"定时任务 #{task_id} 已取消: {t['message']}"
            return f"未找到任务 #{task_id}"

    def _clear_tasks(self) -> str:
        """清除已完成/已取消的任务"""
        with self._lock:
            before = len(self.tasks)
            self.tasks = [t for t in self.tasks if t['status'] == 'pending']
            removed = before - len(self.tasks)
            self._save_tasks()
            return f"已清除 {removed} 个已结束的任务" if removed else "没有需要清除的任务"

    # ── 后台监控 ──

    def _start_monitor(self):
        """启动后台监控线程"""
        if self._monitor_running:
            return
        self._monitor_running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _stop_monitor(self):
        """停止后台监控"""
        self._monitor_running = False

    def _monitor_loop(self):
        """后台监控循环 — 每秒检查到期任务"""
        while self._monitor_running:
            try:
                self._check_due_tasks()
            except Exception:
                pass
            time.sleep(1)

    def _check_due_tasks(self):
        """检查并触发到期任务"""
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        with self._lock:
            for task in self.tasks:
                if task['status'] != 'pending':
                    continue

                trigger_at = task['trigger_at']
                if now_str >= trigger_at:
                    # 触发任务
                    self._fire_task(task, now)

        # 保存可能的变更
        self._save_tasks()

    def _fire_task(self, task: dict, now: datetime):
        """触发一个到期任务"""
        task_id = task['id']
        message = task['message']
        is_repeat = task.get('repeat', False)
        repeat_seconds = task.get('repeat_seconds', 0)

        # 标记为已触发
        task['status'] = 'fired'
        task['fired_at'] = now.strftime("%Y-%m-%d %H:%M:%S")

        # 重复任务：重新调度
        if is_repeat and repeat_seconds > 0:
            next_time = now + timedelta(seconds=repeat_seconds)
            # 创建新的重复任务
            new_task = {
                "id": max([t.get('id', 0) for t in self.tasks], default=0) + 1,
                "message": message,
                "trigger_at": next_time.strftime("%Y-%m-%d %H:%M:%S"),
                "repeat": True,
                "repeat_seconds": repeat_seconds,
                "status": "pending",
                "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                "parent_id": task_id,
            }
            self.tasks.append(new_task)

        # 发送系统通知
        try:
            from xcli_core.notification import notify_task_complete
            notify_task_complete(f"定时提醒: {message}")
        except Exception:
            pass

        # 打印醒目提醒
        print()
        print(f"{Fore.YELLOW}{'═' * 50}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}  ⏰ 定时任务提醒 #{task_id}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'─' * 50}{Style.RESET_ALL}")
        print(f"  {Fore.CYAN}任务:{Style.RESET_ALL} {message}")
        print(f"  {Fore.CYAN}时间:{Style.RESET_ALL} {now.strftime('%H:%M:%S')}")
        if is_repeat:
            next_str = (now + timedelta(seconds=repeat_seconds)).strftime("%Y-%m-%d %H:%M:%S")
            print(f"  {Fore.CYAN}下次:{Style.RESET_ALL} {next_str}")
        print(f"{Fore.YELLOW}{'═' * 50}{Style.RESET_ALL}")

        # 自动激活 AI — 将提醒注入对话
        self._activate_ai(task_id, message)

    def _activate_ai(self, task_id: int, message: str):
        """激活 AI 处理定时任务提醒"""
        if not self.cli:
            return

        reminder = (
            f"[系统定时提醒] 定时任务 #{task_id} 已到期。\n"
            f"任务内容: {message}\n"
            f"请根据任务内容进行相应的操作或提醒用户。"
        )

        # TUI 模式：使用回调
        if hasattr(self.cli, 'tui_output_callback') and self.cli.tui_output_callback:
            try:
                # TUI 模式下通过线程调用，避免阻塞
                def _tui_activate():
                    try:
                        self.cli.process_conversation(reminder)
                    except Exception:
                        pass
                threading.Thread(target=_tui_activate, daemon=True).start()
            except Exception:
                pass
        else:
            # CLI 模式：在新线程中调用，避免阻塞监控
            def _cli_activate():
                try:
                    # 先给用户一个视觉提示
                    print(f"\n{Fore.GREEN}  AI 正在处理定时提醒...{Style.RESET_ALL}")
                    print(f"{Fore.WHITE}> {Style.RESET_ALL}", end='', flush=True)
                    self.cli.process_conversation(reminder)
                    # 重新显示输入提示
                    print(f"\n{Fore.WHITE}> {Style.RESET_ALL}", end='', flush=True)
                except Exception:
                    pass
            threading.Thread(target=_cli_activate, daemon=True).start()

    # ── 辅助函数 ──

    @staticmethod
    def _format_seconds(seconds: int) -> str:
        """格式化秒数为可读文本"""
        if seconds <= 0:
            return ""
        if seconds < 60:
            return f"{seconds}秒"
        if seconds < 3600:
            return f"{seconds // 60}分钟"
        if seconds < 86400:
            h = seconds // 3600
            m = (seconds % 3600) // 60
            return f"{h}小时{m}分钟" if m else f"{h}小时"
        d = seconds // 86400
        return f"{d}天"

    @staticmethod
    def _calc_remaining(trigger_str: str, now: datetime) -> str:
        """计算剩余时间"""
        try:
            trigger = datetime.strptime(trigger_str, "%Y-%m-%d %H:%M:%S")
            diff = trigger - now
            if diff.total_seconds() <= 0:
                return "即将触发"
            secs = int(diff.total_seconds())
            if secs < 60:
                return f"剩余 {secs}秒"
            if secs < 3600:
                return f"剩余 {secs // 60}分钟"
            if secs < 86400:
                h = secs // 3600
                m = (secs % 3600) // 60
                return f"剩余 {h}小时{m}分钟" if m else f"剩余 {h}小时"
            d = secs // 86400
            return f"剩余 {d}天"
        except Exception:
            return ""

    # ── 插件入口 ──

    def handle(self, args: str) -> str:
        """处理工具调用"""
        if not args or not args.strip():
            return self.usage

        parts = args.strip().split(None, 1)
        action = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""

        if action == 'add':
            if not rest:
                return "用法: add <时间> <描述>\n示例: add 30m 检查代码 / add 14:30 开会 / add r:2h 站会"
            # 分离时间和描述
            time_parts = rest.split(None, 1)
            if len(time_parts) < 2:
                return "请同时提供时间和描述。示例: add 30m 检查代码"
            return self._add_task(time_parts[0], time_parts[1])

        elif action == 'list':
            return self._list_tasks()

        elif action in ('delete', 'cancel', 'rm'):
            if not rest:
                return "用法: delete <任务ID>"
            return self._delete_task(rest)

        elif action == 'clear':
            return self._clear_tasks()

        else:
            return f"未知操作: {action}\n可用操作: add / list / delete / clear"

    def get_mcp_definition(self):
        """返回 MCP 工具定义"""
        return {
            "name": "scheduler",
            "description": "定时任务工具，设定定时提醒。到期时 AI 会自动激活并收到提醒。",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["add", "list", "delete", "clear"],
                        "description": "操作类型"
                    },
                    "time": {
                        "type": "string",
                        "description": "时间: 30m(相对) / 14:30(今日) / 2026-04-28 10:00(绝对) / r:30m(重复)"
                    },
                    "message": {
                        "type": "string",
                        "description": "任务描述/提醒内容"
                    },
                    "task_id": {
                        "type": "integer",
                        "description": "任务ID (用于 delete)"
                    }
                },
                "required": ["action"]
            }
        }
