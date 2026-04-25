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