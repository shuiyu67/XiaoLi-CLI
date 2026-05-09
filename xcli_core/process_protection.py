"""
跨平台进程保护模块
提供单实例保护、进程优先级提升、看门狗监控、优雅关闭等功能

支持 Windows / macOS / Linux
Windows 特有: PPL (Protected Process Light) 风格保护、错误模式抑制
"""
import os
import sys
import time
import signal
import atexit
import threading
import subprocess
from typing import Optional, Callable


# ── 平台检测 ──
PLATFORM = (
    'windows' if os.name == 'nt'
    else 'macos' if sys.platform == 'darwin'
    else 'linux'
)


class ProcessProtection:
    """跨平台进程保护器"""

    def __init__(self, app_name: str = "xiaoli-cli"):
        self.app_name = app_name
        self._lock_file_path: Optional[str] = None
        self._lock_fd = None
        self._watchdog_thread: Optional[threading.Thread] = None
        self._watchdog_running = threading.Event()
        self._shutdown_hooks: list[Callable] = []
        self._is_protected = False
        self._original_priority = None
        self._restart_on_crash = False
        self._restart_script: Optional[str] = None

    # ══════════════════════════════════════════════════
    #  单实例保护
    # ══════════════════════════════════════════════════

    def acquire_single_instance(self) -> bool:
        """
        获取单实例锁，防止重复启动
        返回 True 表示成功（当前是唯一实例），False 表示已有实例在运行
        """
        if PLATFORM == 'windows':
            return self._acquire_windows_mutex()
        else:
            return self._acquire_posix_lock()

    def release_single_instance(self):
        """释放单实例锁"""
        if PLATFORM == 'windows':
            self._release_windows_mutex()
        else:
            self._release_posix_lock()

    def _acquire_windows_mutex(self) -> bool:
        """Windows: 使用命名 Mutex 实现单实例"""
        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.windll.kernel32
            mutex_name = f"Global\\{self.app_name}_single_instance"

            # 创建命名 Mutex
            handle = kernel32.CreateMutexW(None, True, mutex_name)
            last_error = kernel32.GetLastError()

            ERROR_ALREADY_EXISTS = 183
            if last_error == ERROR_ALREADY_EXISTS:
                kernel32.CloseHandle(handle)
                return False

            self._win_mutex_handle = handle
            atexit.register(self.release_single_instance)
            return True

        except Exception:
            # 降级到文件锁
            return self._acquire_posix_lock()

    def _release_windows_mutex(self):
        """Windows: 释放 Mutex"""
        try:
            if hasattr(self, '_win_mutex_handle') and self._win_mutex_handle:
                import ctypes
                ctypes.windll.kernel32.CloseHandle(self._win_mutex_handle)
                self._win_mutex_handle = None
        except Exception:
            pass

    def _acquire_posix_lock(self) -> bool:
        """POSIX (macOS/Linux): 使用文件锁实现单实例"""
        import tempfile

        lock_dir = tempfile.gettempdir()
        self._lock_file_path = os.path.join(lock_dir, f"{self.app_name}.lock")

        try:
            # 尝试创建并锁定文件
            if sys.platform == 'darwin':
                # macOS: 使用 fcntl 文件锁
                import fcntl
                self._lock_fd = open(self._lock_file_path, 'w')
                try:
                    fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except (IOError, OSError):
                    # 文件已被锁定 — 已有实例在运行
                    # 检查锁文件中的 PID 是否仍在运行
                    try:
                        old_pid = self._lock_fd.read().strip()
                        if old_pid and self._is_process_running(int(old_pid)):
                            self._lock_fd.close()
                            self._lock_fd = None
                            return False
                        else:
                            # 旧进程已死，清理残留锁
                            self._lock_fd.seek(0)
                            self._lock_fd.truncate()
                    except (ValueError, OSError):
                        pass

                self._lock_fd.seek(0)
                self._lock_fd.truncate()
                self._lock_fd.write(str(os.getpid()))
                self._lock_fd.flush()
                atexit.register(self.release_single_instance)
                return True
            else:
                # Linux: 使用 fcntl 文件锁
                import fcntl
                self._lock_fd = open(self._lock_file_path, 'w')
                try:
                    fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except (IOError, OSError):
                    # 检查旧进程是否仍在运行
                    try:
                        old_pid = self._lock_fd.read().strip()
                        if old_pid and self._is_process_running(int(old_pid)):
                            self._lock_fd.close()
                            self._lock_fd = None
                            return False
                        else:
                            self._lock_fd.seek(0)
                            self._lock_fd.truncate()
                    except (ValueError, OSError):
                        pass

                self._lock_fd.seek(0)
                self._lock_fd.truncate()
                self._lock_fd.write(str(os.getpid()))
                self._lock_fd.flush()
                atexit.register(self.release_single_instance)
                return True

        except Exception:
            # 锁获取失败，但不阻止程序运行
            return True

    def _release_posix_lock(self):
        """POSIX: 释放文件锁"""
        try:
            if self._lock_fd:
                if sys.platform == 'darwin':
                    import fcntl
                    fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_UN)
                else:
                    import fcntl
                    fcntl.flock(self._lock_fd.fileno(), fcntl.LOCK_UN)
                self._lock_fd.close()
                self._lock_fd = None
            if self._lock_file_path and os.path.exists(self._lock_file_path):
                try:
                    os.unlink(self._lock_file_path)
                except OSError:
                    pass
        except Exception:
            pass

    @staticmethod
    def _is_process_running(pid: int) -> bool:
        """检查指定 PID 的进程是否在运行"""
        try:
            if PLATFORM == 'windows':
                import ctypes
                kernel32 = ctypes.windll.kernel32
                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                if handle:
                    kernel32.CloseHandle(handle)
                    return True
                return False
            else:
                os.kill(pid, 0)
                return True
        except (OSError, ProcessLookupError):
            return False

    # ══════════════════════════════════════════════════
    #  进程优先级提升
    # ══════════════════════════════════════════════════

    def elevate_priority(self, level: str = "high") -> bool:
        """
        提升进程优先级

        Args:
            level: "above_normal" | "high" | "realtime"(仅Windows)

        Returns:
            是否成功提升
        """
        try:
            if PLATFORM == 'windows':
                return self._elevate_windows(level)
            elif PLATFORM == 'macos':
                return self._elevate_macos(level)
            else:
                return self._elevate_linux(level)
        except Exception:
            return False

    def _elevate_windows(self, level: str) -> bool:
        """Windows: 使用 SetPriorityClass 提升优先级"""
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32

            # 优先级映射
            priority_map = {
                "above_normal": 0x00008000,   # ABOVE_NORMAL_PRIORITY_CLASS
                "high": 0x00000080,            # HIGH_PRIORITY_CLASS
                "realtime": 0x00000100,         # REALTIME_PRIORITY_CLASS
            }

            priority = priority_map.get(level, 0x00000080)

            # 获取当前进程句柄
            handle = kernel32.GetCurrentProcess()

            # 记录原始优先级
            self._original_priority = kernel32.GetPriorityClass(handle)

            # 设置新优先级
            result = kernel32.SetPriorityClass(handle, priority)
            if result:
                self._is_protected = True
                return True
            return False

        except Exception:
            return False

    def _elevate_macos(self, level: str) -> bool:
        """macOS: 使用 renice 提升优先级"""
        try:
            nice_map = {
                "above_normal": -10,
                "high": -15,
                "realtime": -20,
            }
            nice_val = nice_map.get(level, -10)
            os.nice(nice_val)
            self._is_protected = True
            return True
        except Exception:
            return False

    def _elevate_linux(self, level: str) -> bool:
        """Linux: 使用 renice 提升优先级"""
        try:
            nice_map = {
                "above_normal": -10,
                "high": -15,
                "realtime": -20,
            }
            nice_val = nice_map.get(level, -10)

            # os.nice() 是相对值，需要先获取当前 nice 值
            try:
                import resource
                current = resource.getpriority(resource.PRIO_PROCESS, 0)
                target = nice_val
                delta = target - current
                if delta != 0:
                    os.nice(delta)
            except (ImportError, OSError):
                # fallback: 直接使用 subprocess
                subprocess.run(
                    ["renice", str(nice_val), "-p", str(os.getpid())],
                    capture_output=True, timeout=5
                )

            self._is_protected = True
            return True
        except Exception:
            return False

    def restore_priority(self):
        """恢复原始进程优先级"""
        if not self._is_protected:
            return

        try:
            if PLATFORM == 'windows' and self._original_priority:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.GetCurrentProcess()
                kernel32.SetPriorityClass(handle, self._original_priority)
            elif PLATFORM in ('macos', 'linux'):
                # 恢复到默认 nice 值 (0)
                try:
                    import resource
                    current = resource.getpriority(resource.PRIO_PROCESS, 0)
                    os.nice(-current)
                except (ImportError, OSError):
                    subprocess.run(
                        ["renice", "0", "-p", str(os.getpid())],
                        capture_output=True, timeout=5
                    )
            self._is_protected = False
        except Exception:
            pass

    # ══════════════════════════════════════════════════
    #  Windows PPL 风格保护
    # ══════════════════════════════════════════════════

    def enable_ppl_protection(self) -> bool:
        """
        Windows: 启用 PPL (Protected Process Light) 风格保护
        - 抑制错误弹窗
        - 设置进程缓解策略
        - 禁用 DEP 异常弹窗

        macOS/Linux: 启用等效保护
        - 设置信号处理
        - 忽略 SIGHUP
        """
        if PLATFORM == 'windows':
            return self._enable_windows_ppl()
        else:
            return self._enable_posix_protection()

    def _enable_windows_ppl(self) -> bool:
        """Windows: PPL 风格保护"""
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32

            # 1. 抑制系统错误弹窗 (SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX)
            SEM_FAILCRITICALERRORS = 0x0001
            SEM_NOGPFAULTERRORBOX = 0x0002
            SEM_NOOPENFILEERRORBOX = 0x8000
            old_mode = kernel32.SetErrorMode(
                SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX
            )
            self._original_error_mode = old_mode

            # 2. 设置进程为后台优先级模式（减少对用户交互的影响）
            # PROCESS_MODE_BACKGROUND_BEGIN = 0x00100000
            # kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), 0x00100000)

            # 3. 注册异常处理（防止未处理异常导致崩溃弹窗）
            try:
                import faulthandler
                faulthandler.enable()
            except Exception:
                pass

            self._is_protected = True
            return True

        except Exception:
            return False

    def _enable_posix_protection(self) -> bool:
        """macOS/Linux: 等效保护"""
        try:
            # 1. 忽略 SIGHUP（终端关闭时不停止进程）
            signal.signal(signal.SIGHUP, signal.SIG_IGN)

            # 2. 注册优雅关闭信号
            def _graceful_shutdown(signum, frame):
                self._execute_shutdown_hooks()
                sys.exit(0)

            signal.signal(signal.SIGTERM, _graceful_shutdown)

            # 3. macOS 特有：忽略 SIGPIPE
            if PLATFORM == 'macos':
                signal.signal(signal.SIGPIPE, signal.SIG_IGN)

            # 4. 启用 faulthandler（崩溃时输出堆栈）
            try:
                import faulthandler
                faulthandler.enable()
            except Exception:
                pass

            self._is_protected = True
            return True

        except Exception:
            return False

    # ══════════════════════════════════════════════════
    #  看门狗监控
    # ══════════════════════════════════════════════════

    def start_watchdog(self, check_interval: float = 5.0,
                       restart_on_crash: bool = False,
                       restart_script: Optional[str] = None):
        """
        启动看门狗线程，监控父进程状态
        当父进程退出时，自动清理并退出

        Args:
            check_interval: 检查间隔（秒）
            restart_on_crash: 崩溃时是否自动重启
            restart_script: 重启脚本路径
        """
        self._restart_on_crash = restart_on_crash
        self._restart_script = restart_script

        if self._watchdog_thread and self._watchdog_thread.is_alive():
            return

        self._watchdog_running.set()
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop,
            args=(check_interval,),
            daemon=True,
            name="process-watchdog"
        )
        self._watchdog_thread.start()

    def stop_watchdog(self):
        """停止看门狗"""
        self._watchdog_running.clear()
        if self._watchdog_thread:
            self._watchdog_thread.join(timeout=3)
            self._watchdog_thread = None

    def _watchdog_loop(self, check_interval: float):
        """看门狗主循环"""
        parent_pid = os.getppid()

        while self._watchdog_running.is_set():
            try:
                # 检查父进程是否仍在运行
                if not self._is_process_running(parent_pid):
                    # 父进程已退出，执行清理
                    self._execute_shutdown_hooks()
                    if self._restart_on_crash and self._restart_script:
                        self._do_restart()
                    else:
                        os._exit(0)
                    break

                time.sleep(check_interval)

            except Exception:
                time.sleep(check_interval)

    def _do_restart(self):
        """执行重启"""
        try:
            if self._restart_script and os.path.exists(self._restart_script):
                if PLATFORM == 'windows':
                    subprocess.Popen(
                        ["python", self._restart_script],
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )
                else:
                    subprocess.Popen(
                        ["python3", self._restart_script],
                        start_new_session=True
                    )
        except Exception:
            pass
        finally:
            os._exit(0)

    # ══════════════════════════════════════════════════
    #  关闭钩子
    # ══════════════════════════════════════════════════

    def register_shutdown_hook(self, hook: Callable):
        """注册关闭钩子，在进程退出时执行"""
        if hook not in self._shutdown_hooks:
            self._shutdown_hooks.append(hook)

    def _execute_shutdown_hooks(self):
        """执行所有关闭钩子"""
        for hook in reversed(self._shutdown_hooks):
            try:
                hook()
            except Exception:
                pass

    # ══════════════════════════════════════════════════
    #  一键启用全部保护
    # ══════════════════════════════════════════════════

    def enable_all(self, priority_level: str = "above_normal",
                   watchdog: bool = True,
                   restart_on_crash: bool = False,
                   restart_script: Optional[str] = None) -> dict:
        """
        一键启用所有进程保护

        Args:
            priority_level: 优先级 ("above_normal" | "high")
            watchdog: 是否启用看门狗
            restart_on_crash: 崩溃时是否自动重启
            restart_script: 重启脚本路径

        Returns:
            各项保护的启用状态字典
        """
        results = {
            "single_instance": False,
            "priority": False,
            "ppl_protection": False,
            "watchdog": False,
            "platform": PLATFORM,
        }

        # 1. 单实例保护
        results["single_instance"] = self.acquire_single_instance()

        # 2. 进程优先级提升
        results["priority"] = self.elevate_priority(priority_level)

        # 3. PPL 风格保护
        results["ppl_protection"] = self.enable_ppl_protection()

        # 4. 看门狗
        if watchdog:
            self.start_watchdog(
                restart_on_crash=restart_on_crash,
                restart_script=restart_script
            )
            results["watchdog"] = True

        # 注册清理
        atexit.register(self.disable_all)

        return results

    def disable_all(self):
        """禁用所有保护并清理"""
        self.stop_watchdog()
        self.restore_priority()
        self.release_single_instance()
        self._execute_shutdown_hooks()
        self._is_protected = False

    def get_status(self) -> dict:
        """获取当前保护状态"""
        return {
            "platform": PLATFORM,
            "is_protected": self._is_protected,
            "single_instance_held": (
                self._lock_fd is not None or
                hasattr(self, '_win_mutex_handle') and self._win_mutex_handle is not None
            ),
            "watchdog_running": (
                self._watchdog_thread is not None and
                self._watchdog_thread.is_alive()
            ),
            "shutdown_hooks_count": len(self._shutdown_hooks),
        }


# ── 全局单例 ──
_protection: Optional[ProcessProtection] = None


def get_protection() -> ProcessProtection:
    """获取全局进程保护器单例"""
    global _protection
    if _protection is None:
        _protection = ProcessProtection()
    return _protection


def enable_process_protection(priority_level: str = "above_normal",
                               watchdog: bool = True,
                               restart_on_crash: bool = False) -> dict:
    """
    快捷函数：启用进程保护

    Returns:
        各项保护状态字典
    """
    return get_protection().enable_all(
        priority_level=priority_level,
        watchdog=watchdog,
        restart_on_crash=restart_on_crash,
    )


def disable_process_protection():
    """快捷函数：禁用进程保护"""
    get_protection().disable_all()


def get_protection_status() -> dict:
    """快捷函数：获取保护状态"""
    return get_protection().get_status()


# ── CLI 入口（可独立运行测试） ──
if __name__ == "__main__":
    import json

    print(f"平台: {PLATFORM}")
    print(f"PID: {os.getpid()}")
    print()

    prot = ProcessProtection("xiaoli-cli-test")

    # 测试单实例
    is_first = prot.acquire_single_instance()
    print(f"单实例锁: {'获取成功 (首个实例)' if is_first else '获取失败 (已有实例)'}")

    if is_first:
        # 测试优先级提升
        prio_ok = prot.elevate_priority("above_normal")
        print(f"优先级提升: {'成功' if prio_ok else '失败'}")

        # 测试 PPL 保护
        ppl_ok = prot.enable_ppl_protection()
        print(f"PPL 保护: {'启用' if ppl_ok else '失败'}")

        # 测试看门狗
        prot.start_watchdog(check_interval=2.0)
        print(f"看门狗: 已启动")

        # 显示状态
        status = prot.get_status()
        print(f"\n状态: {json.dumps(status, indent=2, ensure_ascii=False)}")

        print("\n按 Ctrl+C 退出...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n正在清理...")
            prot.disable_all()
            print("完成")
