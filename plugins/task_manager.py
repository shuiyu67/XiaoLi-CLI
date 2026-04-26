"""
任务管理插件 - 提供任务追踪和进度管理功能
"""

import json
import os
from datetime import datetime
from colorama import Fore, Style


class Liugin:
    """任务管理插件 - 类似 iFlow CLI 的 todo 功能"""

    def __init__(self):
        self.usage = """任务管理工具使用方法：

JSON格式示例：
{"action": "use_tool", "tool": "task_manager", "args": "add 创建登录页面"} - 添加新任务
{"action": "use_tool", "tool": "task_manager", "args": "list"} - 列出所有任务
{"action": "use_tool", "tool": "task_manager", "args": "complete 1"} - 完成任务ID为1的任务
{"action": "use_tool", "tool": "task_manager", "args": "in_progress 2"} - 将任务ID为2标记为进行中
{"action": "use_tool", "tool": "task_manager", "args": "delete 3"} - 删除任务ID为3的任务
{"action": "use_tool", "tool": "task_manager", "args": "clear"} - 清除所有已完成的任务

功能说明：
- add <任务描述> - 添加新任务（自动分配ID）
- list - 列出所有任务及其状态
- complete <任务ID> - 标记任务为已完成
- in_progress <任务ID> - 标记任务为进行中
- delete <任务ID> - 删除指定任务
- clear - 清除所有已完成的任务

状态说明：
- pending: 待处理
- in_progress: 进行中
- completed: 已完成
- failed: 失败"""
        self.cli = None
        self.tasks_file = "tasks.json"
        self.tasks = []
        self._load_tasks()

    def set_cli(self, cli):
        """设置CLI实例引用"""
        self.cli = cli
        # 注册插件命令
        self.cli.register_liugin_command('task', self.command_handler)
        self.cli.register_liugin_command('todo', self.command_handler)

    def command_handler(self, args):
        """处理 /task 或 /todo 命令"""
        return self.handle(args)

    def get_tool_info(self):
        return {
            "name": "task_manager",
            "description": "任务管理工具，提供任务追踪和进度管理功能，支持添加、完成、删除任务",
            "keywords": ["任务", "task", "todo", "管理", "进度", "追踪", "list", "complete"],
            "usage": self.usage
        }

    def _load_tasks(self):
        """从文件加载任务"""
        try:
            if os.path.exists(self.tasks_file):
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    self.tasks = json.load(f)
        except Exception as e:
            self.tasks = []

    def _save_tasks(self):
        """保存任务到文件"""
        try:
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"保存任务失败: {e}"
        return None

    def get_mcp_definition(self):
        return {
            "name": "task_manager",
            "description": "任务管理工具，支持添加、完成、删除任务",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["add", "done", "delete", "list", "clear"],
                        "description": "操作类型"
                    },
                    "task": {
                        "type": "string",
                        "description": "任务内容（add/done/delete 时使用）"
                    }
                },
                "required": ["operation"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        task = arguments.get("task", "")
        return f"{op} {task}".strip()

    def handle(self, args):
        """处理任务管理请求"""
        try:
            parts = args.strip().split()
            if not parts:
                return self._list_tasks()

            operation = parts[0].lower()

            if operation == "add":
                # 添加任务
                if len(parts) < 2:
                    return "错误：请提供任务描述。格式: add <任务描述>"
                task_desc = " ".join(parts[1:])
                return self._add_task(task_desc)

            elif operation == "list":
                # 列出任务
                return self._list_tasks()

            elif operation == "complete":
                # 完成任务
                if len(parts) < 2:
                    return "错误：请提供任务ID。格式: complete <任务ID>"
                task_id = parts[1]
                return self._update_task_status(task_id, "completed")

            elif operation == "in_progress":
                # 标记为进行中
                if len(parts) < 2:
                    return "错误：请提供任务ID。格式: in_progress <任务ID>"
                task_id = parts[1]
                return self._update_task_status(task_id, "in_progress")

            elif operation == "delete":
                # 删除任务
                if len(parts) < 2:
                    return "错误：请提供任务ID。格式: delete <任务ID>"
                task_id = parts[1]
                return self._delete_task(task_id)

            elif operation == "clear":
                # 清除已完成任务
                return self._clear_completed()

            else:
                return f"错误：不支持的操作 '{operation}'。支持的操作有: add, list, complete, in_progress, delete, clear"

        except Exception as e:
            return f"任务管理操作错误: {str(e)}"

    def _add_task(self, description):
        """添加新任务"""
        # 使用最大ID+1的方式分配ID，避免删除后ID重复
        existing_ids = [int(t.get("id", 0)) for t in self.tasks if t.get("id", "").isdigit()]
        task_id = str(max(existing_ids, default=0) + 1)
        new_task = {
            "id": task_id,
            "task": description,
            "status": "pending",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "priority": "medium"
        }
        self.tasks.append(new_task)
        error = self._save_tasks()
        if error:
            return error
        return f" 已添加任务 #{task_id}: {description}"

    def _list_tasks(self):
        """列出所有任务"""
        if not self.tasks:
            return " 当前没有任务"

        result = f"\n 任务列表 (共 {len(self.tasks)} 个任务)\n"
        result += "=" * 50 + "\n"

        pending_count = 0
        in_progress_count = 0
        completed_count = 0

        for task in self.tasks:
            status = task.get('status', 'pending')
            task_id = task.get('id', '?')
            description = task.get('task', '')
            created_at = task.get('created_at', '')

            # 统计
            if status == 'pending':
                pending_count += 1
                status_icon = ""
                status_color = Fore.YELLOW
            elif status == 'in_progress':
                in_progress_count += 1
                status_icon = ""
                status_color = Fore.CYAN
            elif status == 'completed':
                completed_count += 1
                status_icon = ""
                status_color = Fore.GREEN
            else:
                status_icon = ""
                status_color = Fore.RED

            result += f"{status_icon} [{task_id}] {status_color}{status}{Style.RESET_ALL} - {description}\n"
            result += f"    创建时间: {created_at}\n\n"

        result += "=" * 50 + "\n"
        result += f" 统计: {Fore.YELLOW}待处理 {pending_count}{Style.RESET_ALL} | {Fore.CYAN}进行中 {in_progress_count}{Style.RESET_ALL} | {Fore.GREEN}已完成 {completed_count}{Style.RESET_ALL}\n"

        return result

    def _update_task_status(self, task_id, new_status):
        """更新任务状态"""
        for task in self.tasks:
            if task.get('id') == task_id:
                old_status = task.get('status')
                task['status'] = new_status
                if new_status == 'completed':
                    task['completed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                error = self._save_tasks()
                if error:
                    return error
                return f" 任务 #{task_id} 状态已更新: {old_status} → {new_status}"

        return f" 未找到任务ID: {task_id}"

    def _delete_task(self, task_id):
        """删除任务"""
        for i, task in enumerate(self.tasks):
            if task.get('id') == task_id:
                deleted_task = self.tasks.pop(i)
                error = self._save_tasks()
                if error:
                    return error
                return f" 已删除任务 #{task_id}: {deleted_task.get('task', '')}"

        return f" 未找到任务ID: {task_id}"

    def _clear_completed(self):
        """清除所有已完成的任务"""
        completed_count = len([t for t in self.tasks if t.get('status') == 'completed'])
        if completed_count == 0:
            return " 没有已完成的任务需要清除"

        self.tasks = [t for t in self.tasks if t.get('status') != 'completed']
        error = self._save_tasks()
        if error:
            return error
        return f" 已清除 {completed_count} 个已完成的任务"


# 测试函数
def test_plugin():
    """测试插件功能"""
    plugin = Plugin()
    print("任务管理插件测试:")

    print("\n1. 添加任务:")
    print(plugin.handle("add 创建登录页面"))
    print(plugin.handle("add 实现用户认证"))
    print(plugin.handle("add 添加数据库连接"))

    print("\n2. 列出任务:")
    print(plugin.handle("list"))

    print("\n3. 标记任务为进行中:")
    print(plugin.handle("in_progress 1"))

    print("\n4. 完成任务:")
    print(plugin.handle("complete 1"))

    print("\n5. 再次列出任务:")
    print(plugin.handle("list"))

    print("\n6. 清除已完成任务:")
    print(plugin.handle("clear"))

    print("\n7. 最终任务列表:")
    print(plugin.handle("list"))


if __name__ == "__main__":
    test_plugin()