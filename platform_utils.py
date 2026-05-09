"""
跨平台工具模块
提供跨平台的兼容性支持
"""
import os
import sys

def get_platform():
    """获取当前平台类型"""
    if os.name == 'nt':
        return 'windows'
    elif sys.platform == 'darwin':
        return 'macos'
    else:
        return 'linux'

def get_hidden_input(prompt="请输入密码: "):
    """跨平台的隐藏输入"""
    platform = get_platform()
    
    if platform == 'windows':
        try:
            import msvcrt
            print(f"{prompt} ", end='', flush=True)
            password = ""
            
            while True:
                char = msvcrt.getch()
                if char in [b'\r', b'\n']:
                    print()
                    break
                elif char == b'\x08':
                    if len(password) > 0:
                        password = password[:-1]
                        print('\b \b', end='', flush=True)
                else:
                    password += char.decode('utf-8')
                    print('*', end='', flush=True)
            
            return password
        except ImportError:
            import getpass
            return getpass.getpass(prompt)
    else:
        import getpass
        return getpass.getpass(prompt)

def check_key_input():
    """检查是否有键盘输入（跨平台）"""
    platform = get_platform()
    
    if platform == 'windows':
        try:
            import msvcrt
            return msvcrt.kbhit() > 0
        except ImportError:
            return False
    else:
        # Linux/Mac 的实现较为复杂，暂时返回 False
        return False

def get_key():
    """获取按键（跨平台）"""
    platform = get_platform()
    
    if platform == 'windows':
        try:
            import msvcrt
            if msvcrt.kbhit():
                return msvcrt.getch()
            return None
        except ImportError:
            return None
    else:
        # Linux/Mac 的实现
        import select
        import tty
        import termios
        
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
        return None

def supports_esc_detection():
    """检查是否支持 ESC 键检测"""
    platform = get_platform()
    return platform == 'windows'  # 目前只有 Windows 完全支持 ESC 检测

def get_user_directory():
    """获取用户目录（跨平台）"""
    platform = get_platform()
    
    if platform == 'windows':
        return os.path.expanduser("~")
    elif platform == 'macos':
        return os.path.expanduser("~")
    else:  # Linux
        return os.path.expanduser("~")

def get_desktop_directory():
    """获取桌面目录（跨平台）"""
    platform = get_platform()
    
    if platform == 'windows':
        return os.path.join(os.path.expanduser("~"), "Desktop")
    elif platform == 'macos':
        return os.path.join(os.path.expanduser("~"), "Desktop")
    else:  # Linux
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        if os.path.exists(desktop):
            return desktop
        else:
            return os.path.expanduser("~")

def get_config_directory():
    """获取应用配置目录（跨平台）"""
    platform = get_platform()
    
    if platform == 'windows':
        return os.path.join(os.path.getenv('APPDATA', ''), 'Xiaoli Pro-CLI 3')
    elif platform == 'macos':
        return os.path.join(os.path.expanduser("~"), 'Library', 'Application Support', 'Xiaoli Pro-CLI 3')
    else:  # Linux
        return os.path.join(os.path.expanduser('~'), '.config', 'xiaoli-pro-cli-3')

def is_process_running(pid):
    """检查指定 PID 的进程是否在运行"""
    platform = get_platform()
    
    try:
        if platform == 'windows':
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        else:
            os.kill(pid, 0)
            return True
    except (OSError, ProcessLookupError):
        return False


def get_process_priority():
    """获取当前进程优先级"""
    platform = get_platform()
    
    try:
        if platform == 'windows':
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetCurrentProcess()
            return kernel32.GetPriorityClass(handle)
        else:
            import resource
            return resource.getpriority(resource.PRIO_PROCESS, 0)
    except Exception:
        return None


def set_process_priority(level="above_normal"):
    """
    设置进程优先级
    
    Args:
        level: "below_normal" | "normal" | "above_normal" | "high"
    
    Returns:
        是否设置成功
    """
    platform = get_platform()
    
    try:
        if platform == 'windows':
            import ctypes
            kernel32 = ctypes.windll.kernel32
            priority_map = {
                "below_normal": 0x00004000,
                "normal": 0x00000020,
                "above_normal": 0x00008000,
                "high": 0x00000080,
            }
            priority = priority_map.get(level, 0x00008000)
            handle = kernel32.GetCurrentProcess()
            return bool(kernel32.SetPriorityClass(handle, priority))
        else:
            nice_map = {
                "below_normal": 10,
                "normal": 0,
                "above_normal": -10,
                "high": -15,
            }
            nice_val = nice_map.get(level, -10)
            os.nice(nice_val)
            return True
    except Exception:
        return False
