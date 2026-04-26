"""
跨平台系统通知模块
当 AI 完成任务时，发送系统通知提醒用户
支持 Windows / macOS / Linux
"""
import os
import sys
import subprocess
import threading
from typing import Optional


class NotificationManager:
    """跨平台系统通知管理器"""

    def __init__(self):
        self.enabled = True
        self._platform = self._detect_platform()
        self._last_title = ""
        self._last_message = ""
        self._cooldown_seconds = 2  # 防止重复通知的冷却时间
        self._last_notify_time = 0

    @staticmethod
    def _detect_platform() -> str:
        """检测当前平台"""
        if os.name == 'nt':
            return 'windows'
        elif sys.platform == 'darwin':
            return 'macos'
        else:
            return 'linux'

    def set_enabled(self, enabled: bool):
        """启用/禁用通知"""
        self.enabled = enabled

    def notify(self, title: str, message: str, force: bool = False):
        """
        发送系统通知

        Args:
            title: 通知标题
            message: 通知内容
            force: 是否忽略冷却时间强制发送
        """
        if not self.enabled:
            return

        # 防止重复通知
        import time
        now = time.time()
        if (not force and
            title == self._last_title and
            message == self._last_message and
            now - self._last_notify_time < self._cooldown_seconds):
            return

        self._last_title = title
        self._last_message = message
        self._last_notify_time = now

        # 在后台线程发送，不阻塞主流程
        thread = threading.Thread(
            target=self._send_notification,
            args=(title, message),
            daemon=True
        )
        thread.start()

    def notify_task_complete(self, task_summary: str = ""):
        """通知任务完成的快捷方法"""
        title = "小狸 Pro-CLI"
        if task_summary:
            # 截断过长的摘要
            if len(task_summary) > 80:
                task_summary = task_summary[:77] + "..."
            message = f"任务已完成: {task_summary}"
        else:
            message = "任务已完成 ✓"

        self.notify(title, message)

    def notify_tool_complete(self, tool_name: str, result_summary: str = ""):
        """通知工具执行完成"""
        title = "小狸 Pro-CLI"
        if result_summary:
            if len(result_summary) > 60:
                result_summary = result_summary[:57] + "..."
            message = f"{tool_name}: {result_summary}"
        else:
            message = f"{tool_name} 执行完成 ✓"

        self.notify(title, message)

    # ── 平台实现 ──

    def _send_notification(self, title: str, message: str):
        """根据平台发送通知"""
        try:
            if self._platform == 'windows':
                self._notify_windows(title, message)
            elif self._platform == 'macos':
                self._notify_macos(title, message)
            else:
                self._notify_linux(title, message)
        except Exception:
            # 通知失败不应影响正常流程
            pass

    def _notify_windows(self, title: str, message: str):
        """Windows 通知 — 优先使用 win10toast，降级到 PowerShell"""
        # 方法1: win10toast (pip install win10toast)
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=3, threaded=True)
            return
        except ImportError:
            pass

        # 方法2: PowerShell BurntToast 模块
        try:
            ps_script = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $textNodes = $template.GetElementsByTagName("text")
            $textNodes.Item(0).AppendChild($template.CreateTextNode("{title}")) > $null
            $textNodes.Item(1).AppendChild($template.CreateTextNode("{message}")) > $null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{title}").Show($toast)
            '''
            subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True, timeout=5
            )
            return
        except Exception:
            pass

        # 方法3: PowerShell 简单弹窗 (最后降级)
        try:
            escaped_msg = message.replace("'", "''")
            escaped_title = title.replace("'", "''")
            ps_cmd = (
                f"Add-Type -AssemblyName System.Windows.Forms; "
                f"[System.Windows.Forms.MessageBox]::Show('{escaped_msg}', '{escaped_title}')"
            )
            subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True, timeout=5
            )
        except Exception:
            pass

    def _notify_macos(self, title: str, message: str):
        """macOS 通知 — 使用 osascript"""
        escaped_title = title.replace('"', '\\"')
        escaped_message = message.replace('"', '\\"')
        script = f'display notification "{escaped_message}" with title "{escaped_title}"'
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, timeout=5
        )

    def _notify_linux(self, title: str, message: str):
        """Linux 通知 — 优先 notify-send，降级到 D-Bus"""
        # 方法1: notify-send (libnotify)
        try:
            subprocess.run(
                ["notify-send", title, message, "-i", "dialog-information", "-t", "3000"],
                capture_output=True, timeout=5
            )
            return
        except FileNotFoundError:
            pass

        # 方法2: D-Bus 直接调用
        try:
            dbus_script = f'''
import dbus
bus = dbus.SessionBus()
notify_obj = bus.get_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
notify_iface = dbus.Interface(notify_obj, 'org.freedesktop.Notifications')
notify_iface.Notify('xiaoli-cli', 0, 'dialog-information', '{title}', '{message}', [], {{}}, 3000)
'''
            subprocess.run(
                [sys.executable, "-c", dbus_script],
                capture_output=True, timeout=5
            )
        except Exception:
            pass


# ── 全局单例 ──
_notification_manager = None


def get_notification_manager() -> NotificationManager:
    """获取全局通知管理器单例"""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


def notify_task_complete(task_summary: str = ""):
    """快捷函数：通知任务完成"""
    get_notification_manager().notify_task_complete(task_summary)


def notify_tool_complete(tool_name: str, result_summary: str = ""):
    """快捷函数：通知工具执行完成"""
    get_notification_manager().notify_tool_complete(tool_name, result_summary)
