import subprocess
import sys
import os
import re
import json
import tempfile
import urllib.request
import zipfile
from pathlib import Path
import io
from datetime import datetime
import platform

# 设置控制台编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class KawaiiPythonLauncher:
    """可爱版Python启动器～"""
    
    def clear_screen(self):
        """清屏函数"""
        os.system('cls' if platform.system() == 'Windows' else 'clear')
    
    def get_hidden_input(self):
        """获取隐藏输入的API密钥（Windows和跨平台兼容）"""
        import sys
        try:
            import msvcrt  # Windows only
            # Windows implementation
            print("💡 输入API密钥 (输入后按回车确认，字符将被隐藏): ", end='', flush=True)
            password = ""
            
            while True:
                char = msvcrt.getch()  # 获取单个字符（不显示）
                if char in [b'\r', b'\n']:  # Enter键
                    print()  # 换行
                    break
                elif char == b'\x08':  # Backspace键
                    if len(password) > 0:
                        password = password[:-1]
                        print('\b \b', end='', flush=True)  # 删除一个星号
                else:
                    password += char.decode('utf-8')
                    print('*', end='', flush=True)  # 显示星号
            
            return password
        except ImportError:
            # Fallback for non-Windows systems
            import getpass
            return getpass.getpass("💡 请输入API密钥 (输入时将隐藏): ")
    
    def __init__(self):
        # 获取项目目录
        if getattr(sys, 'frozen', False):
            self.project_dir = Path(os.path.dirname(sys.executable))
        else:
            self.project_dir = Path(__file__).parent
        
        # 嵌入式Python目录
        self.embedded_python_dir = self.project_dir / "embedded_python"
        self.embedded_python_exe = self.embedded_python_dir / "python.exe"
        self.embedded_pip_exe = self.embedded_python_dir / "Scripts" / "pip.exe"
        
        # 主程序文件
        self.main_program = self.project_dir / "ai_cli.py"
        self.ai_engines_dir = self.project_dir / "ai_engines"
        self.plugins_dir = self.project_dir / "plugins"
        
        # 下载源配置
        self.download_sources = {
            "1": {
                "name": "Python官方源 🌟",
                "url": "https://www.python.org/ftp/python/3.12.0/python-3.12.0-embed-amd64.zip",
                "description": "官方源，最稳定可靠啦～"
            },
            "2": {
                "name": "清华镜像源 🚀",
                "url": "https://mirrors.tuna.tsinghua.edu.cn/python/3.12.0/python-3.12.0-embed-amd64.zip",
                "description": "国内小伙伴推荐，飞一般的速度！"
            },
            "3": {
                "name": "中科大镜像源 📚", 
                "url": "https://mirrors.ustc.edu.cn/python/3.12.0/python-3.12.0-embed-amd64.zip",
                "description": "学霸源，稳定又快速～"
            },
            "4": {
                "name": "阿里云镜像源 ☁️",
                "url": "https://mirrors.aliyun.com/python/3.12.0/python-3.12.0-embed-amd64.zip",
                "description": "云上小可爱，下载超顺畅"
            }
        }
        
        # 状态变量
        self.use_system_python = False
        self.use_embedded_python = False
        self.current_python_exe = None
        self.current_pip_exe = None
        
        # 错误收集
        self.errors = []
        
        # 已知的第三方库
        self.known_third_party_packages = {
            # 基础库
            'colorama', 'openai', 'requests', 'ollama', 'pygame',
            # 图像处理
            'PIL', 'Pillow', 'cv2', 'opencv-python', 'numpy',
            # 终端显示
            'ascii_magic',
            # 其他可能的库
            'tkinter', 'matplotlib', 'pandas', 'scipy', 'scikit-learn'
        }
        
        # 插件管理
        self.enabled_plugins = []
    
    def discover_plugins(self):
        """发现可用的插件"""
        plugins = []
        if self.plugins_dir.exists():
            for py_file in self.plugins_dir.glob("*.py"):
                # 跳过__init__.py等特殊文件
                if not py_file.name.startswith('__'):
                    plugin_name = py_file.stem
                    plugins.append(plugin_name)
        return sorted(plugins)
    
    def show_plugin_selection(self):
        """显示插件选择菜单"""
        available_plugins = self.discover_plugins()
        
        if not available_plugins:
            print("🎈 没有发现任何插件呢～")
            return []
        
        print("\n" + "🎀" * 25)
        print("✨ 插件选择菜单 ✨")
        print("🎀" * 25)
        print(f"🎯 发现了 {len(available_plugins)} 个插件:")
        
        for i, plugin in enumerate(available_plugins, 1):
            print(f"  {i}. {plugin}")
        
        print("\n💫 请选择要启用的插件:")
        print("   🎯 输入 'all' 启用所有插件")
        print("   🎯 输入插件编号（多个用逗号分隔，如: 1,3,5")
        print("   🎯 输入 'none' 不启用任何插件")
        print("-" * 40)
        
        return available_plugins
    
    def get_plugin_selection(self, available_plugins):
        """获取用户的插件选择"""
        if not available_plugins:
            return []
        
        while True:
            try:
                choice = input("🎯 你的选择: ").strip().lower()
                
                if choice == 'all':
                    print("🎊 启用所有插件！")
                    return available_plugins
                
                elif choice == 'none' or choice == '0':
                    print("🐾 不启用任何插件")
                    return []
                
                elif choice:
                    # 处理数字选择
                    selected_indices = []
                    for part in choice.split(','):
                        part = part.strip()
                        if part.isdigit():
                            idx = int(part)
                            if 1 <= idx <= len(available_plugins):
                                selected_indices.append(idx - 1)
                    
                    if selected_indices:
                        selected_plugins = [available_plugins[i] for i in selected_indices]
                        print(f"🎯 已选择插件: {', '.join(selected_plugins)}")
                        return selected_plugins
                    else:
                        print("🤔 唔...没有识别到有效的选择呢，请重新输入～")
                
                else:
                    print("💫 请输入你的选择哦～")
                    
            except KeyboardInterrupt:
                print("\n🐾 你按了Ctrl+C，小狸明白啦～使用默认设置")
                return []
            except Exception as e:
                print(f"💫 选择时出了点小问题: {e}")
                return []
    
    def ask_plugin_enable(self):
        """询问用户是否启用插件"""
        available_plugins = self.discover_plugins()
        
        if not available_plugins:
            print("🎈 没有发现任何插件呢，直接启动主程序～")
            return []
        
        print(f"\n🎁 小狸发现了 {len(available_plugins)} 个插件！")
        
        while True:
            try:
                enable_all = input("🎯 是否启用所有插件？(y/N): ").strip().lower()
                
                if enable_all == 'y':
                    print("🎊 启用所有插件！")
                    return available_plugins
                elif enable_all == 'n' or enable_all == '':
                    # 显示选择菜单
                    plugins = self.show_plugin_selection()
                    return self.get_plugin_selection(plugins)
                else:
                    print("🤔 请输入 y 或 n 哦～")
                    
            except KeyboardInterrupt:
                print("\n🐾 你按了Ctrl+C，小狸明白啦～使用默认设置")
                return []
            except Exception as e:
                print(f"💫 选择时出了点小问题: {e}")
                return []
    
    def create_plugin_config(self, enabled_plugins):
        """创建插件配置文件"""
        config_content = "# 小狸插件配置 - 由启动器自动生成\n"
        
        if not enabled_plugins:
            # 用户选择不启用任何插件
            config_content += "# 不启用任何插件\n"
            config_content += "# 启用的插件: 无\n\n"
        else:
            config_content += f"# 启用的插件: {', '.join(enabled_plugins)}\n\n"
            for plugin in enabled_plugins:
                config_content += f"ENABLE_{plugin.upper()} = True\n"
        
        config_file = self.project_dir / "plugins_config.py"
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(config_content)
            print(f"📝 插件配置已保存到: {config_file}")
            return config_file
        except Exception as e:
            print(f"💫 保存插件配置时出错了: {e}")
            return None
    
    def show_download_source_menu(self):
        """显示可爱的下载源选择菜单"""
        print("\n" + "✨" * 30)
        print("🎀 请选择Python下载源 🎀")
        print("✨" * 30)
        
        print("小狸为你准备了多个下载源，选一个最适合你的吧～")
        print()
        
        for key, source in self.download_sources.items():
            print(f"🍭 {key}. {source['name']}")
            print(f"   💬 {source['description']}")
            print(f"   🔗 {source['url']}")
            print()
        
        print("🌠 5. 手动输入下载地址（高级模式）")
        print("🐾 0. 取消下载（人家会伤心的 😢）")
        print("-" * 60)
    
    def get_user_download_choice(self):
        """获取用户下载源选择（可爱版）"""
        while True:
            try:
                choice = input("🎯 请选择下载源 (1-5, 0取消): ").strip()
                
                if choice == "0":
                    print("😿 呜...你取消了下载，小狸好难过...")
                    return None
                
                elif choice == "5":
                    print("🧚‍♀️ 进入高级模式～请输入完整的下载地址：")
                    custom_url = input("🔗 下载地址: ").strip()
                    if custom_url and custom_url.startswith(('http://', 'https://')):
                        print("✅ 自定义地址设置成功！")
                        return custom_url
                    else:
                        print("❌ 哎呀，这个地址不太对呢，请重新输入～")
                        continue
                
                elif choice in self.download_sources:
                    source = self.download_sources[choice]
                    print(f"🎉 太棒了！选择了: {source['name']}")
                    return source['url']
                
                else:
                    print("🤔 唔...这个选择小狸看不懂呢，请输入 1-5 的数字哦～")
                    
            except KeyboardInterrupt:
                print("\n🐾 你按了Ctrl+C，小狸明白啦～")
                return None
            except Exception as e:
                print(f"💫 选择时出了点小问题: {e}")
                return None
    
    def test_download_source(self, url):
        """测试下载源是否可用（可爱版）"""
        print(f"🔍 正在测试下载源: {url}")
        try:
            # 创建测试请求
            req = urllib.request.Request(url, method='HEAD')
            response = urllib.request.urlopen(req, timeout=10)
            
            if response.status == 200:
                file_size = response.headers.get('Content-Length')
                if file_size:
                    size_mb = int(file_size) / (1024 * 1024)
                    print(f"🎊 太棒了！源可用，文件大小: {size_mb:.1f} MB")
                else:
                    print("🎊 耶～源可用！")
                return True
            else:
                print(f"💔 哎呀，源不可用，状态码: {response.status}")
                return False
                
        except Exception as e:
            print(f"🌧️  源测试失败: {e}")
            return False
    
    def log_error(self, action, error):
        """记录错误信息（可爱版）"""
        error_msg = f"行为: {action}\n错误: {error}\n{'-'*50}"
        self.errors.append(error_msg)
        print(f"💔 {action}时出错了: {error}")
    
    def save_errors_to_file(self):
        """保存错误信息到文件（可爱版）"""
        if self.errors:
            bug_file = self.project_dir / "bug.txt"
            try:
                with open(bug_file, 'w', encoding='utf-8') as f:
                    f.write("🐛 小狸 Pro-CLI 启动错误报告 🐛\n")
                    f.write("🌈" * 20 + "\n")
                    f.write("\n".join(self.errors))
                print(f"📝 已经把错误信息悄悄保存在: {bug_file}")
                return True
            except Exception as e:
                print(f"😅 保存错误文件时也出错了: {e}")
        return False
    
    def check_system_python(self):
        """检测系统Python环境（可爱版）"""
        print("🔍 正在寻找系统里的Python...")
        try:
            # 尝试python命令
            result = subprocess.run(
                ["python", "--version"],
                capture_output=True, text=True, check=False, encoding='utf-8'
            )
            if result.returncode == 0 and "Python" in result.stdout:
                print(f"🎯 找到系统Python啦: {result.stdout.strip()}")
                self.use_system_python = True
                self.current_python_exe = "python"
                return True
        except Exception as e:
            self.log_error("寻找系统Python", str(e))
        
        try:
            # 尝试python3命令
            result = subprocess.run(
                ["python3", "--version"],
                capture_output=True, text=True, check=False, encoding='utf-8'
            )
            if result.returncode == 0 and "Python" in result.stdout:
                print(f"🎯 找到系统Python3啦: {result.stdout.strip()}")
                self.use_system_python = True
                self.current_python_exe = "python3"
                return True
        except Exception as e:
            self.log_error("寻找系统Python3", str(e))
        
        print("😢 没有找到系统Python呢...")
        return False
    
    def check_embedded_python(self):
        """检测嵌入式Python（可爱版）"""
        print("🔍 看看有没有自带的Python...")
        if self.embedded_python_exe.exists():
            try:
                result = subprocess.run(
                    [str(self.embedded_python_exe), "--version"],
                    capture_output=True, text=True, check=False, encoding='utf-8'
                )
                if result.returncode == 0:
                    print(f"🎁 找到嵌入式Python啦: {result.stdout.strip()}")
                    self.use_embedded_python = True
                    self.current_python_exe = str(self.embedded_python_exe)
                    self.current_pip_exe = str(self.embedded_pip_exe)
                    return True
            except Exception as e:
                self.log_error("检查嵌入式Python", str(e))
        
        print("📦 没有找到现成的嵌入式Python呢...")
        return False
    
    def download_file(self, url, local_filename):
        """下载文件（可爱版）"""
        print(f"🌐 正在下载: {os.path.basename(local_filename)}...")
        try:
            def progress_hook(count, block_size, total_size):
                if total_size > 0:
                    percent = min(100, int(count * block_size * 100 / total_size))
                    # 可爱的进度条
                    bars = "🟩" * (percent // 5) + "⬜" * (20 - percent // 5)
                    print(f"\r📥 下载中... {bars} {percent}%", end='', flush=True)
            
            urllib.request.urlretrieve(url, local_filename, progress_hook)
            print("\n🎊 下载完成！太棒了！")
            return True
        except Exception as e:
            print(f"\n💔 下载失败了: {e}")
            return False
    
    def install_embedded_python(self):
        """安装嵌入式Python（可爱版）"""
        print("🛠️  准备安装Python环境...")
        
        # 显示下载源菜单
        self.show_download_source_menu()
        
        # 获取用户选择
        python_url = self.get_user_download_choice()
        if not python_url:
            return False
        
        # 测试下载源
        print("\n🧪 测试下载源...")
        if not self.test_download_source(python_url):
            print("💔 下载源不可用，可能是网络问题呢～")
            retry = input("🔄 要再试一次吗？(y/N): ").strip().lower()
            if retry == 'y':
                print("🦄 小狸陪你再来一次！")
                return self.install_embedded_python()
            else:
                return False
        
        # 创建目录
        self.embedded_python_dir.mkdir(exist_ok=True)
        
        # 下载嵌入式Python
        zip_path = self.project_dir / "python_embedded.zip"
        
        print(f"\n🚀 开始下载Python...")
        if not self.download_file(python_url, zip_path):
            self.log_error("下载嵌入式Python", "网络连接失败")
            
            # 提供重试选项
            retry = input("🔄 下载失败，要再试一次吗？(y/N): ").strip().lower()
            if retry == 'y':
                print("💪 不放弃！我们再试一次！")
                return self.install_embedded_python()
            else:
                return False
        
        # 解压
        try:
            print("📦 解压Python中...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.embedded_python_dir)
            print("🎀 解压完成！")
        except Exception as e:
            self.log_error("解压Python", str(e))
            return False
        finally:
            if zip_path.exists():
                zip_path.unlink()
        
        # 配置Python环境
        try:
            pth_file = self.embedded_python_dir / "python._pth"
            if pth_file.exists():
                content = pth_file.read_text(encoding='utf-8')
                # 确保import site被启用并添加当前目录
                content = content.replace('#import site', 'import site')
                if 'import site' not in content:
                    content += '\nimport site'
                # 添加当前目录到路径
                content += f'\n.\n{str(self.embedded_python_dir / "Lib")}\n{str(self.embedded_python_dir / "DLLs")}'
                pth_file.write_text(content, encoding='utf-8')
                print("⚙️  Python环境配置完成！")
        except Exception as e:
            self.log_error("配置Python环境", str(e))
        
        # 验证Python是否能正常运行
        try:
            result = subprocess.run(
                [str(self.embedded_python_exe), "--version"],
                capture_output=True, text=True, check=False, encoding='utf-8'
            )
            if result.returncode == 0:
                print(f"✅ Python版本: {result.stdout.strip()}")
            else:
                print(f"⚠️ Python验证失败: {result.stderr.strip() if result.stderr else '未知错误'}")
        except Exception as e:
            print(f"⚠️ Python验证异常: {str(e)}")
        
        # 安装pip
        print("\n🔧 安装pip工具...")
        if not self.install_pip_for_embedded():
            print("⚠️  pip安装失败，但Python环境已安装，部分功能可能受限")
            # 即使pip安装失败也继续，因为Python本身可能仍然可用
        else:
            # 验证pip安装
            try:
                pip_result = subprocess.run(
                    [str(self.embedded_python_exe), "-m", "pip", "--version"],
                    capture_output=True, text=True, check=False, encoding='utf-8'
                )
                if pip_result.returncode == 0:
                    print(f"✅ pip版本: {pip_result.stdout.strip()}")
                else:
                    print(f"⚠️ pip验证失败: {pip_result.stderr.strip() if pip_result.stderr else '未知错误'}")
            except Exception as e:
                print(f"⚠️ pip验证异常: {str(e)}")
        
        # 验证安装
        return self.check_embedded_python()
    
    def install_pip_for_embedded(self):
        """为嵌入式Python安装pip（可爱版）"""
        try:
            # 首先尝试使用ensurepip（Python内置的pip安装工具）
            print("🔍 尝试使用内置ensurepip安装pip...")
            result = subprocess.run(
                [str(self.embedded_python_exe), "-m", "ensurepip", "--upgrade"],
                capture_output=True, text=True, check=False, encoding='utf-8'
            )
            
            if result.returncode == 0:
                print("🎯 pip通过ensurepip安装成功！现在可以安装各种库啦～")
                
                # 验证pip安装
                pip_result = subprocess.run(
                    [str(self.embedded_python_exe), "-m", "pip", "--version"],
                    capture_output=True, text=True, check=False, encoding='utf-8'
                )
                
                if pip_result.returncode == 0:
                    print(f"✅ pip验证成功: {pip_result.stdout.strip()}")
                    # 更新pip路径
                    pip_exe_path = self.embedded_python_dir / "Scripts" / "pip.exe"
                    if pip_exe_path.exists():
                        self.current_pip_exe = str(pip_exe_path)
                    return True
                else:
                    print("⚠️ pip安装完成但验证失败")
                    return False
            else:
                print("⚠️ ensurepip安装失败，尝试使用get-pip.py...")
            
            # 如果ensurepip失败，尝试下载get-pip.py
            get_pip_urls = [
                "https://bootstrap.pypa.io/get-pip.py",  # 官方源
                "https://gitee.com/mirrors/get-pip/raw/main/public/get-pip.py",  # 国内镜像
            ]
            
            get_pip_path = self.embedded_python_dir / "get-pip.py"
            downloaded = False
            
            # 尝试多个源下载get-pip.py
            for url in get_pip_urls:
                print(f"📥 正在从 {url} 下载 get-pip.py...")
                if self.download_file(url, get_pip_path):
                    downloaded = True
                    break
                else:
                    print(f"❌ 从 {url} 下载失败，尝试下一个源...")
            
            if not downloaded:
                print("💔 所有pip下载源都不可用")
                return False
            
            # 运行get-pip.py
            result = subprocess.run(
                [str(self.embedded_python_exe), str(get_pip_path)],
                capture_output=True, text=True, check=False, encoding='utf-8'
            )
            
            # 清理
            if get_pip_path.exists():
                get_pip_path.unlink()
            
            if result.returncode == 0:
                print("🎯 pip安装成功！现在可以安装各种库啦～")
                
                # 验证pip安装
                pip_result = subprocess.run(
                    [str(self.embedded_python_exe), "-m", "pip", "--version"],
                    capture_output=True, text=True, check=False, encoding='utf-8'
                )
                
                if pip_result.returncode == 0:
                    print(f"✅ pip验证成功: {pip_result.stdout.strip()}")
                    # 更新pip路径
                    pip_exe_path = self.embedded_python_dir / "Scripts" / "pip.exe"
                    if pip_exe_path.exists():
                        self.current_pip_exe = str(pip_exe_path)
                    return True
                else:
                    print("⚠️ pip安装完成但验证失败")
                    return False
            else:
                error_msg = result.stderr[-200:] if result.stderr else '未知错误'
                print(f"❌ pip安装失败: {error_msg}")
                self.log_error("安装pip", error_msg)
                return False
        except Exception as e:
            print(f"💥 pip安装过程中出现异常: {str(e)}")
            self.log_error("安装pip", str(e))
            return False
    
    def scan_imports_in_file(self, file_path):
        """扫描Python文件中的import语句"""
        imports = set()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # import module
            import_pattern = r'^\s*import\s+([a-zA-Z_][a-zA-Z0-9_.]*)'
            matches = re.findall(import_pattern, content, re.MULTILINE)
            imports.update(matches)
            
            # from module import ...
            from_pattern = r'^\s*from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import'
            matches = re.findall(from_pattern, content, re.MULTILINE)
            imports.update(matches)
            
        except Exception as e:
            self.log_error(f"扫描文件 {file_path}", str(e))
        
        return imports
    
    def get_required_packages(self):
        """获取所有需要的包（可爱版）- 扫描整个项目目录"""
        print("🔍 正在扫描需要的依赖库...")
        all_imports = set()
        
        # 扫描整个项目目录中的所有 Python 文件（递归）
        print(f"📂 扫描目录: {self.project_dir}")
        
        # 使用 glob 递归查找所有 .py 文件
        py_files = list(self.project_dir.rglob("*.py"))
        
        # 排除一些不需要扫描的文件/目录
        exclude_patterns = [
            "__pycache__",
            ".git",
            "venv",
            ".venv",
            "env",
            ".env",
            "build",
            "dist",
            "*.egg-info",
        ]
        
        scanned_files = []
        skipped_files = []
        
        for py_file in py_files:
            # 检查是否在排除目录中
            should_skip = False
            for pattern in exclude_patterns:
                if pattern in str(py_file):
                    should_skip = True
                    break
            
            if should_skip:
                skipped_files.append(py_file)
                continue
            
            # 扫描文件
            file_imports = self.scan_imports_in_file(py_file)
            if file_imports:
                all_imports.update(file_imports)
                scanned_files.append(py_file)
        
        print(f"📄 扫描了 {len(scanned_files)} 个 Python 文件")
        if skipped_files:
            print(f"⏭️  跳过了 {len(skipped_files)} 个文件（在排除目录中）")
        
        # 显示扫描到的所有导入
        if all_imports:
            print(f"📦 发现的导入模块: {len(all_imports)} 个")
            # 显示前10个导入
            import_list = sorted(list(all_imports))
            if import_list:
                sample = import_list[:10]
                print(f"   示例: {', '.join(sample)}")
                if len(import_list) > 10:
                    print(f"   ... 还有 {len(import_list) - 10} 个")
        
        # 筛选第三方库
        required = set()
        unknown_imports = set()
        
        for imp in all_imports:
            module_name = imp.split('.')[0]
            if module_name in self.known_third_party_packages:
                required.add(module_name)
            else:
                # 收集未知的导入，可能需要添加到已知列表中
                unknown_imports.add(module_name)
        
        # 显示未知的导入（可能是新添加的第三方库）
        if unknown_imports:
            print(f"❓ 发现 {len(unknown_imports)} 个未分类的导入:")
            unknown_list = sorted(list(unknown_imports))[:15]
            for imp in unknown_list:
                print(f"   - {imp}")
            if len(unknown_imports) > 15:
                print(f"   ... 还有 {len(unknown_imports) - 15} 个")
            print(f"💡 提示: 这些可能是 Python 标准库或未识别的第三方库")
        
        print(f"📋 需要安装的第三方库: {', '.join(required)}")
        
        # 保存到 requirements.txt
        if required:
            requirements_file = self.project_dir / "requirements.txt"
            try:
                with open(requirements_file, 'w', encoding='utf-8') as f:
                    f.write("# 小狸 Pro-CLI 依赖库\n")
                    f.write(f"# 自动生成于: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"# 扫描了 {len(scanned_files)} 个 Python 文件\n\n")
                    for package in sorted(required):
                        f.write(f"{package}\n")
                print(f"✅ 依赖列表已保存到: {requirements_file}")
            except Exception as e:
                print(f"💫 保存 requirements.txt 失败: {e}")
        
        return required

    def scan_and_save_engines(self):
        """扫描引擎并保存配置到 config.json"""
        print("🔍 正在扫描 AI 引擎...")
        engines_config = {}
        
        if self.ai_engines_dir.exists():
            engine_files = list(self.ai_engines_dir.glob("*_engine.py"))
            if engine_files:
                print(f"🎯 发现了 {len(engine_files)} 个引擎文件:")
                for engine_file in engine_files:
                    engine_name = engine_file.stem.replace("_engine", "")
                    engines_config[engine_name] = {
                        "api_key": "",
                        "base_url": "",
                        "model": ""
                    }
                    print(f"  - {engine_name}")
            else:
                print("🎈 没有发现任何引擎文件")
        else:
            print("🎈 ai_engines 目录不存在")
        
        # 读取或创建配置文件
        config_file = self.project_dir / "config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception as e:
                print(f"💫 读取配置文件失败: {e}")
                config = {
                    "api": {"engines": {}},
                    "system": {
                        "web_server_port": 8080,
                        "max_file_size": 52428800,
                        "max_history": 10,
                        "max_video_duration": 10000,
                        "video_frame_delay": 0.04,
                        "love_file_path": "love.txt"
                    },
                    "plugins": {"enabled": []}
                }
        else:
            config = {
                "api": {"engines": {}},
                "system": {
                    "web_server_port": 8080,
                    "max_file_size": 52428800,
                    "max_history": 10,
                    "max_video_duration": 10000,
                    "video_frame_delay": 0.04,
                    "love_file_path": "love.txt"
                },
                "plugins": {"enabled": []}
            }
        
        # 合并引擎配置，保留已设置的值
        if "api" not in config:
            config["api"] = {}
        if "engines" not in config["api"]:
            config["api"]["engines"] = {}
        
        for engine_name, engine_config in engines_config.items():
            if engine_name in config["api"]["engines"]:
                # 保留已设置的值
                existing_config = config["api"]["engines"][engine_name]
                engines_config[engine_name]["api_key"] = existing_config.get("api_key", "")
                engines_config[engine_name]["base_url"] = existing_config.get("base_url", "")
                engines_config[engine_name]["model"] = existing_config.get("model", "")
        
        config["api"]["engines"] = engines_config
        
        # 保存配置
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            print(f"✅ 引擎配置已保存到: {config_file}")
            return True
        except Exception as e:
            print(f"💫 保存配置文件失败: {e}")
            return False
    
    def check_package_installed(self, package_name):
        """检查包是否已安装（可爱版）"""
        try:
            result = subprocess.run(
                [self.current_python_exe, "-c", f"import {package_name}"],
                capture_output=True, text=True, check=False, encoding='utf-8'
            )
            return result.returncode == 0
        except Exception as e:
            self.log_error(f"检查包 {package_name}", str(e))
            return False
    
    def install_package(self, package_name):
        """安装单个包（可爱版）"""
        print(f"📦 正在安装 {package_name}...")
        
        # 确定pip命令
        if self.use_system_python:
            pip_cmd = [self.current_python_exe, "-m", "pip"]
        else:
            # 优先使用已知的pip路径，否则使用python -m pip
            pip_cmd = [self.current_pip_exe] if self.current_pip_exe and os.path.exists(self.current_pip_exe) else [self.current_python_exe, "-m", "pip"]
        
        # 检查pip是否可用
        pip_check = subprocess.run(
            pip_cmd + ["--version"],
            capture_output=True, text=True, check=False, encoding='utf-8'
        )
        
        if pip_check.returncode != 0:
            print("⚠️  pip不可用，尝试修复pip...")
            # 尝试修复pip
            fix_result = subprocess.run(
                [self.current_python_exe, "-m", "ensurepip", "--upgrade"],
                capture_output=True, text=True, check=False, encoding='utf-8'
            )
            if fix_result.returncode == 0:
                print("✅ pip修复成功！")
                # 更新pip路径
                pip_exe_path = self.embedded_python_dir / "Scripts" / "pip.exe"
                if pip_exe_path.exists():
                    self.current_pip_exe = str(pip_exe_path)
                pip_cmd = [self.current_pip_exe] if self.current_pip_exe and os.path.exists(self.current_pip_exe) else [self.current_python_exe, "-m", "pip"]
            else:
                print("❌ pip修复失败，使用备用方案")
                # 仍然使用python -m pip
                pip_cmd = [self.current_python_exe, "-m", "pip"]
        
        # 尝试安装，如果失败则使用国内镜像源重试
        install_commands = [
            pip_cmd + ["install", package_name],
            pip_cmd + ["install", package_name, "-i", "https://pypi.tuna.tsinghua.edu.cn/simple/"],
            pip_cmd + ["install", package_name, "-i", "https://mirrors.aliyun.com/pypi/simple/"],
        ]
        
        for i, cmd in enumerate(install_commands):
            try:
                print(f"🔍 尝试安装方式 {i+1}/3...")
                result = subprocess.run(
                    cmd,
                    capture_output=True, text=True, check=False, encoding='utf-8'
                )
                
                if result.returncode == 0:
                    print(f"🎉 {package_name} 安装成功！")
                    return True
                else:
                    error_msg = result.stderr[-200:] if result.stderr else '未知错误'
                    print(f"⚠️  方式 {i+1} 安装失败: {error_msg}")
                    if i == len(install_commands) - 1:  # 最后一次尝试
                        self.log_error(f"安装包 {package_name}", error_msg)
                        return False
            except Exception as e:
                print(f"⚠️  方式 {i+1} 安装异常: {str(e)}")
                if i == len(install_commands) - 1:  # 最后一次尝试
                    self.log_error(f"安装包 {package_name}", str(e))
                    return False
    
    def check_and_install_packages(self, required_packages):
        """检查并安装需要的包（可爱版）"""
        if not required_packages:
            print("🌈 所有依赖库都已经准备好啦！")
            return True
        
        # 检查缺失的包
        missing_packages = []
        for package in required_packages:
            if self.check_package_installed(package):
                print(f"✅ {package} 已经安装好啦～")
            else:
                print(f"❌ {package} 还没有安装呢")
                missing_packages.append(package)
        
        if not missing_packages:
            print("🎊 太棒了！所有依赖库都准备就绪！")
            return True
        
        # 安装缺失的包
        print(f"🔧 需要安装 {len(missing_packages)} 个库: {', '.join(missing_packages)}")
        success_count = 0
        
        for package in missing_packages:
            if self.install_package(package):
                success_count += 1
            print()  # 空行分隔
        
        return success_count == len(missing_packages)
    
    def run_main_program(self):
        """运行主程序（可爱版）"""
        self.clear_screen()
        print("🚀 启动主程序...")
        
        # 设置环境变量，传递启用的插件信息
        env = os.environ.copy()
        if self.enabled_plugins is not None:
            # 即使是空列表也要传递，表示不启用任何插件
            env["XIAOLI_ENABLED_PLUGINS"] = ",".join(self.enabled_plugins)
            if self.enabled_plugins:
                print(f"🎯 启用的插件: {', '.join(self.enabled_plugins)}")
            else:
                print("🎯 不启用任何插件")
        
        try:
            result = subprocess.run(
                [self.current_python_exe, str(self.main_program)],
                env=env
            )
            return result.returncode == 0
        except Exception as e:
            self.log_error("启动主程序", str(e))
            return False
    
    def run(self):
        """运行启动器（可爱版）"""
        print("🎀" * 25)
        print("✨ 欢迎使用小狸 Pro-CLI 智能启动器 ✨")
        print("🐾 让小狸帮你准备好一切吧～")
        print("🎀" * 25)
        
        # 步骤1: 检测Python环境
        print("\n[步骤1] 🔍 检测Python环境")
        if self.check_system_python():
            print("👉 使用系统Python")
        else:
            print("👉 系统Python不可用，看看有没有自带的...")
            if self.check_embedded_python():
                print("👉 使用嵌入式Python")
            else:
                print("👉 需要安装Python环境...")
                if self.install_embedded_python():
                    print("👉 使用新安装的嵌入式Python")
                else:
                    print("💔 无法设置Python环境")
                    self.show_final_result()
                    return
        
        # 步骤2: 检测并安装依赖
        print("\n[步骤2] 📚 检测依赖库")
        required_packages = self.get_required_packages()
        all_packages_installed = self.check_and_install_packages(required_packages)
        
        # 步骤3: 插件选择
        print("\n[步骤3] 🎁 插件配置")
        self.enabled_plugins = self.ask_plugin_enable()
        
        # 创建插件配置文件
        if self.enabled_plugins:
            self.create_plugin_config(self.enabled_plugins)
        
        # 步骤4: 显示最终结果
        self.show_final_result(all_packages_installed)
        
        # 步骤5: 运行主程序
        if all_packages_installed or (not all_packages_installed and len(self.errors) < len(required_packages)):
            print("\n[步骤4] 🎮 运行主程序")
            self.run_main_program()
        else:
            print("\n由于严重错误，跳过运行主程序")
    
    def show_final_result(self, all_packages_installed=True):
        """显示最终检测结果（超可爱版）"""
        print("\n" + "⭐" * 30)
        print("🎯 检测结果报告")
        print("⭐" * 30)
        
        error_count = len(self.errors)
        
        if error_count == 0 and all_packages_installed:
            print("🎊 太棒了！所有配置都成功啦！")
            print(f"✅ Python环境: 已准备就绪")
            print(f"✅ 依赖库: 全部安装完成")
            print(f"✅ 插件: {len(self.enabled_plugins) if self.enabled_plugins else 0} 个已启用")
        else:
            print("💫 部分配置信息:")
            print(f"✅ Python环境: {'已准备就绪' if (self.use_system_python or self.use_embedded_python) else '未准备就绪'}")
            print(f"✅ 依赖库: {'全部安装' if all_packages_installed else '部分缺失'}")
            print(f"⚠️  错误数量: {error_count}")
        
        print("⭐" * 30)

    def get_available_ai_engines(self):
        """自动检测可用的AI引擎"""
        engines_dir = self.project_dir / "ai_engines"
        available_engines = {}
        
        if engines_dir.exists():
            import re
            for py_file in engines_dir.glob("*_engine.py"):
                # 提取引擎名称（从文件名中移除_engine.py后缀）
                engine_name = py_file.stem.replace('_engine', '')
                # 使用更准确的引擎名称映射
                display_name = engine_name.replace('_', ' ').replace('-', ' ').title()
                available_engines[engine_name] = f"{display_name}"
        
        return available_engines
    
    def ensure_api_config_has_all_engines(self):
        """确保config.json包含所有检测到的AI引擎的默认配置"""
        config_file = self.project_dir / "config.json"
        
        # 加载config.json现有配置
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                config = {"api": {"engines": {}}}
        else:
            config = {"api": {"engines": {}}}
        
        if "api" not in config:
            config["api"] = {}
        if "engines" not in config["api"]:
            config["api"]["engines"] = {}
        
        # 检测AI引擎
        ai_engines_dir = self.project_dir / "ai_engines"
        if not ai_engines_dir.exists():
            return
        
        config_updated = False
        
        for py_file in ai_engines_dir.glob("*_engine.py"):
            engine_name = py_file.stem.replace("_engine", "")
            
            if engine_name not in config["api"]["engines"]:
                # 为新引擎添加默认配置，根据引擎类型设置不同的默认值
                default_config = {
                    "base_url": "https://api.example.com/v1/chat/completions",
                    "model": engine_name,
                    "api_key": ""  # 为需要API密钥的引擎也设置空api_key，但用户需要手动配置
                }
                
                # 通过动态导入引擎模块来确定是否需要API密钥和默认配置
                engine_requires_api = True  # 默认需要API密钥
                
                # 尝试动态加载引擎以获取其配置需求
                import importlib.util
                import os
                
                engines_dir = os.path.join(self.project_dir, "ai_engines")
                engine_file = os.path.join(engines_dir, f"{engine_name}_engine.py")
                
                if os.path.exists(engine_file):
                    try:
                        spec = importlib.util.spec_from_file_location(f"{engine_name}_engine", engine_file)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        # 查找引擎类并检查其属性
                        possible_class_names = [
                            f"{engine_name.replace('-', '_').replace(' ', '').title()}AI",
                            f"{engine_name.replace('-', '_').replace('http', '').replace(' ', '').title()}AI",
                            f"{engine_name.replace('_', '').replace('-', '').title()}AI"
                        ]
                        
                        engine_class = None
                        for class_name in possible_class_names:
                            if hasattr(module, class_name):
                                engine_class = getattr(module, class_name)
                                break
                        
                        if engine_class:
                            # 检查是否需要API密钥
                            if hasattr(engine_class, 'requires_api_key'):
                                engine_requires_api = engine_class.requires_api_key
                            elif 'requires_api_key' in engine_class.__dict__:
                                engine_requires_api = engine_class.__dict__['requires_api_key']
                            
                            # 检查默认配置
                            if hasattr(engine_class, 'default_base_url'):
                                default_config["base_url"] = engine_class.default_base_url
                            if hasattr(engine_class, 'default_model'):
                                default_config["model"] = engine_class.default_model

                    except Exception:
                        pass  # 如果导入失败，使用默认值
                
                # 根据引擎是否需要API密钥设置默认API密钥
                default_config["api_key"] = "" if not engine_requires_api else ""
                
                # 为常见本地引擎设置默认URL和模型
                if 'ollama' in engine_name.lower():
                    default_config.setdefault("base_url", "http://localhost:11434/v1")
                    default_config.setdefault("model", "llama2")
                elif 'lm_studio' in engine_name.lower():
                    default_config.setdefault("base_url", "http://localhost:1234/v1")
                    default_config.setdefault("model", "local-model")
                elif 'openrouter' in engine_name.lower():
                    default_config.setdefault("base_url", "https://openrouter.ai/api/v1/chat/completions")
                    default_config.setdefault("model", "openai/gpt-3.5-turbo")
                elif 'http' in engine_name.lower():
                    default_config.setdefault("base_url", "https://api.example.com/v1/chat/completions")
                    default_config.setdefault("model", engine_name)
                
                config["api"]["engines"][engine_name] = default_config
                print(f"📝 为引擎 {engine_name} 添加了默认API配置到config.json")
                config_updated = True
        
        # 保存更新后的config.json
        if config_updated:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            print("✅ config.json 已更新")
    

        
    def _check_engine_requires_api_key(self, engine_name):
        """
        检测引擎是否需要API密钥
        通过动态导入引擎模块并检查其requires_api_key属性
        """
        import importlib.util
        import os
        
        # 构建引擎文件路径
        engines_dir = os.path.join(os.path.dirname(self.project_dir), "ai_engines")
        if not os.path.exists(engines_dir):
            engines_dir = self.project_dir / "ai_engines"
        
        engine_file = os.path.join(engines_dir, f"{engine_name}_engine.py")
        
        if not os.path.exists(engine_file):
            # 如果没找到对应文件，使用启发式判断
            # 含有特定关键词的引擎通常不需要API密钥
            if any(keyword in engine_name.lower() for keyword in ["ollama", "lm_studio", "local", "custom"]):
                return False
            else:
                # 默认情况下，假设需要API密钥
                return True
        
        try:
            # 动态导入引擎模块
            spec = importlib.util.spec_from_file_location(f"{engine_name}_engine", engine_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 查找引擎类
            possible_class_names = [
                f"{engine_name.replace('-', '_').replace(' ', '').title()}AI",
                f"{engine_name.replace('-', '_').replace('http', '').replace(' ', '').title()}AI",
                f"{engine_name.replace('_', '').replace('-', '').title()}AI"
            ]
            
            engine_class = None
            for class_name in possible_class_names:
                if hasattr(module, class_name):
                    engine_class = getattr(module, class_name)
                    break
            
            if engine_class:
                # 检查类是否有requires_api_key属性
                if hasattr(engine_class, 'requires_api_key'):
                    return engine_class.requires_api_key
                elif hasattr(engine_class, '__annotations__') or hasattr(engine_class, '__dict__'):
                    # 检查类属性
                    if 'requires_api_key' in engine_class.__dict__:
                        return engine_class.__dict__['requires_api_key']
            
            # 如果没找到明确声明，使用启发式判断
            if any(keyword in engine_name.lower() for keyword in ["ollama", "lm_studio", "local", "custom"]):
                return False
            else:
                # 默认需要API密钥
                return True
        except Exception:
            # 如果导入失败，使用启发式判断
            if any(keyword in engine_name.lower() for keyword in ["ollama", "lm_studio", "local", "custom"]):
                return False
            else:
                return True

    def configure_api_keys(self):
        """配置API密钥功能 - 自动检测可用的AI引擎"""
        self.clear_screen()
        print("\n" + "🌟" * 20)
        print("🎯 API密钥配置向导")
        print("🌟" * 20)
        print("请输入您要使用的AI服务的API密钥")
        print("注意：API密钥是敏感信息，请确保在安全的环境中配置\n")
        
        # 自动检测可用的AI引擎
        available_engines = self.get_available_ai_engines()
        
        if not available_engines:
            print("⚠️  未检测到任何AI引擎文件")
            print("   请确保AI引擎文件遵循命名规范: {engine_name}_engine.py")
            return
        
        print(f"🔍 检测到 {len(available_engines)} 个AI引擎:")
        for engine_key, engine_name in available_engines.items():
            print(f"  - {engine_key}: {engine_name}")
        
        # 尝试导入配置管理器
        config_file = "config.json"
        config = {}

        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                print("⚠️  配置文件不存在或格式错误，将创建新的配置")
                config = {}

        if "api" not in config:
            config["api"] = {}
        if "engines" not in config["api"]:
            config["api"]["engines"] = {}
        
        for engine_key, engine_display_name in available_engines.items():
            print(f"\n--- {engine_display_name} ({engine_key}) ---")
            
            # 动态检测引擎是否需要API密钥
            requires_api_key = self._check_engine_requires_api_key(engine_key)
            
            current_config = config["api"]["engines"].get(engine_key, {})
            current_key = current_config.get("api_key", "")
            current_url = current_config.get("base_url", "")
            current_model = current_config.get("model", "")
            
            # 显示当前配置
            if current_url or current_model or current_key:
                print(f"  当前配置:")
                if current_key:
                    print(f"    API密钥: {'*' * min(len(current_key), 8)}{current_key[-4:] if len(current_key) > 4 else current_key}")
                if current_url:
                    print(f"    基础URL: {current_url}")
                if current_model:
                    print(f"    模型名称: {current_model}")
            
            # 根据引擎是否需要API密钥进行不同的配置流程
            if not requires_api_key:
                print(f"💡 {engine_display_name} 为本地引擎或无需API密钥的引擎")
                
                # 询问是否配置URL和模型
                config_url = input(f"是否要配置{engine_display_name}的基础URL? [Y/n]: ").lower()
                if config_url != 'n':
                    # 根据引擎类型提供合适的默认URL
                    if 'ollama' in engine_key.lower():
                        default_url = "http://localhost:11434/v1"
                    elif 'lm_studio' in engine_key.lower():
                        default_url = "http://localhost:1234/v1"
                    else:
                        default_url = "http://localhost:11434/v1"
                    
                    base_url = input(f"请输入{engine_display_name}的基础URL (默认: {default_url}): ").strip()
                    if not base_url:
                        base_url = default_url
                    if "api" not in config:
                        config["api"] = {}
                    if "engines" not in config["api"]:
                        config["api"]["engines"] = {}
                    if engine_key not in config["api"]["engines"]:
                        config["api"]["engines"][engine_key] = {}
                    config["api"]["engines"][engine_key]["base_url"] = base_url
                    print(f"✅ {engine_display_name} 基础URL已配置")
                
                config_model = input(f"是否要配置{engine_display_name}的模型名称? [Y/n]: ").lower()
                if config_model != 'n':
                    # 根据引擎类型提供合适的默认模型
                    if 'ollama' in engine_key.lower():
                        default_model = "llama2"
                    elif 'lm_studio' in engine_key.lower():
                        default_model = "local-model"
                    else:
                        default_model = "default-model"
                    
                    model_name = input(f"请输入{engine_display_name}的模型名称 (默认: {default_model}): ").strip()
                    if not model_name:
                        model_name = default_model
                    if "api" not in config:
                        config["api"] = {}
                    if "engines" not in config["api"]:
                        config["api"]["engines"] = {}
                    if engine_key not in config["api"]["engines"]:
                        config["api"]["engines"][engine_key] = {}
                    config["api"]["engines"][engine_key]["model"] = model_name
                    print(f"✅ {engine_display_name} 模型名称已配置")
            else:
                # 需要API密钥的引擎
                if current_key:
                    print(f"当前API密钥: {'*' * min(len(current_key), 8)}{current_key[-4:] if len(current_key) > 4 else current_key}")
                
                # 询问是否配置API密钥
                action = input(f"是否要配置{engine_display_name}的API密钥? [Y/n]: ").lower()
                if action != 'n':
                    print(f"请输入{engine_display_name}的API密钥 (输入后按回车确认，字符将被隐藏): ", end='', flush=True)
                    # 使用隐藏输入函数，避免直接使用getpass
                    api_key = self.get_hidden_input()
                    if "api" not in config:
                        config["api"] = {}
                    if "engines" not in config["api"]:
                        config["api"]["engines"] = {}
                    if engine_key not in config["api"]["engines"]:
                        config["api"]["engines"][engine_key] = {}
                    config["api"]["engines"][engine_key]["api_key"] = api_key
                    print(f"✅ {engine_display_name} API密钥已配置")
                
                # 询问是否配置URL（云端引擎也可能需要自定义URL）
                config_url = input(f"是否要配置{engine_display_name}的基础URL? [Y/n]: ").lower()
                if config_url != 'n':
                    # 根据引擎类型提供合适的默认URL
                    if 'mimo' in engine_key.lower():
                        default_url = "https://api.xiaomimimo.com/v1/chat/completions"
                    elif 'qwen' in engine_key.lower():
                        default_url = "https://apis.iflow.cn/v1/chat/completions"
                    elif 'spark' in engine_key.lower():
                        default_url = "https://spark-api-open.xf-yun.com/v1/chat/completions"
                    elif 'glm' in engine_key.lower():
                        default_url = "https://www.dmxapi.cn/v1"
                    elif 'maas' in engine_key.lower():
                        default_url = "http://maas-api.cn-huabei-1.xf-yun.com/v1"
                    else:
                        # 默认API基础URL
                        default_url = "https://api.example.com/v1/chat/completions"
                    
                    base_url = input(f"请输入{engine_display_name}的基础URL (默认: {default_url}): ").strip()
                    if not base_url:
                        base_url = default_url
                    if "api" not in config:
                        config["api"] = {}
                    if "engines" not in config["api"]:
                        config["api"]["engines"] = {}
                    if engine_key not in config["api"]["engines"]:
                        config["api"]["engines"][engine_key] = {}
                    config["api"]["engines"][engine_key]["base_url"] = base_url
                    print(f"✅ {engine_display_name} 基础URL已配置")
                
                # 询问是否配置模型名称
                config_model = input(f"是否要配置{engine_display_name}的模型名称? [Y/n]: ").lower()
                if config_model != 'n':
                    # 根据引擎类型提供合适的默认模型
                    if 'mimo' in engine_key.lower():
                        default_model = "mimo-v2-flash"
                    elif 'qwen' in engine_key.lower():
                        default_model = "qwen3-coder-plus"
                    elif 'spark' in engine_key.lower():
                        default_model = "lite"
                    elif 'glm' in engine_key.lower():
                        default_model = "GLM-4.5-Flash"
                    elif 'maas' in engine_key.lower():
                        default_model = "xopdeepseekv32"
                    else:
                        default_model = engine_key  # 使用引擎名称作为默认模型名
                    
                    model_name = input(f"请输入{engine_display_name}的模型名称 (默认: {default_model}): ").strip()
                    if not model_name:
                        model_name = default_model
                    if "api" not in config:
                        config["api"] = {}
                    if "engines" not in config["api"]:
                        config["api"]["engines"] = {}
                    if engine_key not in config["api"]["engines"]:
                        config["api"]["engines"][engine_key] = {}
                    config["api"]["engines"][engine_key]["model"] = model_name
                    print(f"✅ {engine_display_name} 模型名称已配置")
                
                if action == 'n' and config_url == 'n' and config_model == 'n':
                    print(f"跳过{engine_display_name}的配置")
        
        # 保存配置到两个文件
        try:
            # 保存到 config.json（用于主程序读取）
            with open("config.json", 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            print("✅ 配置已保存到 config.json 文件")
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
    
    def configure_system_settings(self):
        """配置系统设置"""
        self.clear_screen()
        print("\n" + "⚙️ " * 15)
        print("🎯 系统设置配置")
        print("⚙️ " * 15)
        
        config_file = "config.json"
        config = {}
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                config = {}
        
        if "system" not in config:
            config["system"] = {}
        
        print("\n当前系统设置:")
        system_defaults = {
            "web_server_port": 8080,
            "max_file_size": 52428800,
            "max_history": 10,
            "max_video_duration": 10000,
            "video_frame_delay": 0.04,
            "love_file_path": "love.txt"
        }
        
        for key, default_value in system_defaults.items():
            current_value = config["system"].get(key, default_value)
            print(f"  {key}: {current_value}")
        
        change = input("\n是否要修改系统设置? [y/N]: ").lower()
        if change == 'y':
            for key, default_value in system_defaults.items():
                current_value = config["system"].get(key, default_value)
                new_value_str = input(f"请输入 {key} 的新值 (默认: {current_value}): ").strip()
                
                if new_value_str == "":
                    new_value = current_value
                else:
                    # 尝试转换为适当的数据类型
                    if isinstance(default_value, int):
                        try:
                            new_value = int(new_value_str)
                        except ValueError:
                            print(f"⚠️  输入无效，使用默认值 {default_value}")
                            new_value = default_value
                    elif isinstance(default_value, float):
                        try:
                            new_value = float(new_value_str)
                        except ValueError:
                            print(f"⚠️  输入无效，使用默认值 {default_value}")
                            new_value = default_value
                    else:
                        new_value = new_value_str
                
                config["system"][key] = new_value
            
            # 保存配置
            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                print("\n✅ 系统设置已保存")
            except Exception as e:
                print(f"\n❌ 保存设置失败: {e}")
    
    def show_current_config(self):
        """显示当前配置"""
        self.clear_screen()
        print("\n" + "📋" * 15)
        print("🎯 当前配置状态")
        print("📋" * 15)
        
        config_file = "config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                print("\n--- API配置 ---")
                if "api" in config and "engines" in config["api"]:
                    for engine_name, engine_config in config["api"]["engines"].items():
                        # 检查引擎是否需要API密钥
                        requires_api_key = True
                        engine_file = self.ai_engines_dir / f"{engine_name}_engine.py"
                        if engine_file.exists():
                            try:
                                with open(engine_file, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    if 'requires_api_key = False' in content:
                                        requires_api_key = False
                            except:
                                pass
                        
                        if not requires_api_key:
                            # 不需要API密钥的引擎（如Ollama）
                            print(f"  {engine_name}: 本地引擎，无需API密钥")
                        else:
                            api_key = engine_config.get("api_key", "")
                            if api_key:
                                masked_key = f"{'*' * max(0, len(api_key) - 4)}{api_key[-4:] if len(api_key) > 4 else api_key}"
                                print(f"  {engine_name}: API密钥已配置 ({masked_key})")
                            else:
                                print(f"  {engine_name}: 未配置API密钥")
                
                print("\n--- 系统配置 ---")
                if "system" in config:
                    for key, value in config["system"].items():
                        print(f"  {key}: {value}")
                
                print("\n--- 插件配置 ---")
                if "plugins" in config:
                    enabled_plugins = config["plugins"].get("enabled", [])
                    if enabled_plugins:
                        print(f"  启用的插件: {', '.join(enabled_plugins)}")
                    else:
                        print("  启用的插件: 无")
                else:
                    print("  启用的插件: 未配置")
            except (json.JSONDecodeError, FileNotFoundError):
                print("❌ 无法读取配置文件")
        else:
            print("📝 配置文件不存在")
        
        # 询问用户是否继续
        print("\n" + "-" * 40)
        print("请选择下一步操作:")
        print("   1. 🚀 启动主程序")
        print("   2. 🎛️  进入配置向导")
        print("   3. 🌈 退出")
        
        next_choice = input("\n请选择 (1-3): ").strip()
        
        if next_choice == "1":
            print("\n🚀 启动主程序...")
            self._run_main_process()
        elif next_choice == "2":
            print("\n🎛️  进入配置向导...")
            self.run_config_wizard()
        else:
            print("\n🌈 退出程序")
            return
    
    def run_config_wizard(self):
        """运行配置向导"""
        import json  # 在方法内导入，避免与其他导入冲突
        
        while True:
            self.clear_screen()
            print("\n" + "🎊" * 25)
            print("🎯 小狸 Pro-CLI 配置向导")
            print("🎊" * 25)
            print("请选择要进行的操作:")
            print("   1. 🎯 配置API密钥")
            print("   2. ⚙️  配置系统设置")
            print("   3. 🧩 配置插件")
            print("   4. 📋 查看当前配置")
            print("   5. 🏃‍♂️  返回并启动主程序")
            print("-" * 30)
            
            choice = input("请输入选项 (1-5): ").strip()
            
            if choice == "1":
                self.configure_api_keys()
            elif choice == "2":
                self.configure_system_settings()
            elif choice == "3":
                self.configure_plugins_interactive()
            elif choice == "4":
                self.show_current_config()
            elif choice == "5":
                print("🚀 返回启动主程序...")
                break
            else:
                print("🤔 无效选项，请重新选择")

    def configure_plugins_interactive(self):
        """交互式插件配置"""
        self.clear_screen()
        print("\n" + "🧩" * 20)
        print("🎯 插件配置")
        print("🧩" * 20)
        
        # 发现可用插件
        available_plugins = self.discover_plugins()
        
        if not available_plugins:
            print("🎁 没有发现任何插件")
            input("\n按回车键返回...")
            return
        
        print(f"\n🎯 发现了 {len(available_plugins)} 个插件:")
        for i, plugin in enumerate(available_plugins, 1):
            print(f"  {i}. {plugin}")
        
        print("\n💫 请选择要启用的插件:")
        print("   🎯 输入 'all' 启用所有插件")
        print("   🎯 输入插件编号（多个用逗号分隔，如: 1,3,5）")
        print("   🎯 输入 'none' 不启用任何插件")
        print("   🎯 输入 'back' 返回上级菜单")
        print("-" * 40)
        
        while True:
            try:
                choice = input("🎯 你的选择: ").strip().lower()
                
                if choice == 'back':
                    return
                elif choice == 'all':
                    selected_plugins = available_plugins
                    print("🎊 启用所有插件！")
                elif choice == 'none' or choice == '0':
                    selected_plugins = []
                    print("🐾 不启用任何插件")
                elif choice:
                    # 处理数字选择
                    selected_indices = []
                    for part in choice.split(','):
                        part = part.strip()
                        if part.isdigit():
                            idx = int(part)
                            if 1 <= idx <= len(available_plugins):
                                selected_indices.append(idx - 1)
                    
                    if selected_indices:
                        selected_plugins = [available_plugins[i] for i in selected_indices]
                        print(f"🎯 已选择插件: {', '.join(selected_plugins)}")
                    else:
                        print("🤔 唔...没有识别到有效的选择呢，请重新输入～")
                        continue
                else:
                    print("💫 请输入你的选择哦～")
                    continue
                
                # 创建插件配置
                self.create_plugin_config(selected_plugins)
                print(f"\n✅ 已成功配置 {len(selected_plugins)} 个插件")
                input("\n按回车键返回...")
                return
                    
            except KeyboardInterrupt:
                print("\n🐾 你按了Ctrl+C，返回上级菜单")
                return
            except Exception as e:
                print(f"💫 配置插件时出了点小问题: {e}")
                return
    
    def run(self):
        """运行启动器（可爱版）- 修改版本，添加配置选项"""
        self.clear_screen()
        print("🎀" * 25)
        print("✨ 欢迎使用小狸 Pro-CLI 智能启动器 ✨")
        print("🐾 让小狸帮你准备好一切吧～")
        print("🎀" * 25)
        
        # 自动检测并确保API配置包含所有引擎
        print("🔍 检测可用的AI引擎...")
        self.ensure_api_config_has_all_engines()
        
        # 询问用户想要进行的操作
        print("\n🎯 请选择操作模式:")
        print("   1. 🚀 直接启动（检测并安装环境后启动主程序）")
        print("   2. 🎛️  配置向导（先配置API密钥等设置）")
        print("   3. 📋 查看当前配置状态")
        print("-" * 40)
        
        mode_choice = input("请选择模式 (1-3): ").strip()
        
        if mode_choice == "2":
            # 进入配置向导
            self.run_config_wizard()
            # 配置完成后询问是否启动主程序
            start_main = input("\n是否现在启动主程序? [Y/n]: ").lower()
            if start_main != 'n':
                self._run_main_process()  # 用私有方法执行实际启动过程
            return
        elif mode_choice == "3":
            # 查看配置并返回
            self.show_current_config()
            return
        elif mode_choice != "1":
            print("⚠️  无效选择，默认执行直接启动...")
        
        # 原有的直接启动流程
        self._run_main_process()
    
    def _run_main_process(self):
        """私有方法：执行主启动流程"""
        # 步骤1: 检测Python环境
        print("\n[步骤1] 🔍 检测Python环境")
        if self.check_system_python():
            print("👉 使用系统Python")
        else:
            print("👉 系统Python不可用，看看有没有自带的...")
            if self.check_embedded_python():
                print("👉 使用嵌入式Python")
            else:
                print("👉 需要安装Python环境...")
                if self.install_embedded_python():
                    print("👉 使用新安装的嵌入式Python")
                else:
                    print("💔 无法设置Python环境")
                    self.show_final_result()
                    return
        
        # 步骤2: 扫描并保存引擎配置
        print("\n[步骤2] 🤖 扫描AI引擎")
        self.scan_and_save_engines()
        
        # 步骤3: 检测并安装依赖
        print("\n[步骤3] 📚 检测依赖库")
        required_packages = self.get_required_packages()
        all_packages_installed = self.check_and_install_packages(required_packages)
        
        # 步骤4: 插件选择
        print("\n[步骤4] 🎁 插件配置")
        self.enabled_plugins = self.ask_plugin_enable()
        
        # 创建插件配置文件
        if self.enabled_plugins:
            self.create_plugin_config(self.enabled_plugins)
        
        # 步骤5: 显示最终结果
        self.show_final_result(all_packages_installed)
        
        # 步骤6: 运行主程序
        if all_packages_installed or (not all_packages_installed and len(self.errors) < len(required_packages)):
            print("\n[步骤5] 🎮 运行主程序")
            self.run_main_program()
        else:
            print("\n由于严重错误，跳过运行主程序")
        
        print("⭐" * 30)

    def show_final_result(self, all_packages_installed=True):
        """显示最终检测结果（超可爱版）"""
        print("\n" + "⭐" * 30)
        print("🎯 检测结果报告")
        print("⭐" * 30)
        
        error_count = len(self.errors)
        
        if error_count == 0 and all_packages_installed:
            print("🎊 太棒了！所有配置都成功啦！")
            print(f"✅ Python环境: 已准备就绪")
            print(f"✅ 依赖库: 全部安装完成")
            print(f"✅ 插件: {len(self.enabled_plugins) if self.enabled_plugins else 0} 个已启用")
        elif error_count > 0 and error_count < len(self.known_third_party_packages):
            print("🤔 咦？好像有一些小问题...")
            print("💫 不过没关系，我们还是可以继续的！")
            print(f"✅ Python环境: {'已准备就绪' if (self.use_system_python or self.use_embedded_python) else '未准备就绪'}")
            print(f"⚠️  错误数量: {error_count}")
            if self.enabled_plugins:
                print(f"✅ 插件: 启用了 {len(self.enabled_plugins)} 个")
            print("📝 下面是遇到的问题:")
            for error in self.errors:
                print(f"   🐛 {error}")
            
            if self.save_errors_to_file():
                print("💾 小狸已经把错误信息记在小本本上啦～")
        else:
            print("😭 呜呜...遇到了好多问题...")
            print("💔 可能无法正常运行了")
            print(f"✅ Python环境: {'已准备就绪' if (self.use_system_python or self.use_embedded_python) else '未准备就绪'}")
            print(f"⚠️  错误数量: {error_count}")
            print("🔍 详细问题如下:")
            for error in self.errors:
                print(f"   ❌ {error}")
            
            if self.save_errors_to_file():
                print("📁 错误信息已经保存在 bug.txt 文件里")
        
        print("⭐" * 30)


def main():
    """主函数（可爱版）"""
    try:
        launcher = KawaiiPythonLauncher()
        launcher.run()
    except KeyboardInterrupt:
        print("\n\n🐾 你按了Ctrl+C，小狸明白啦～再见！")
    except Exception as e:
        print(f"\n\n💫 程序运行出了点小问题: {e}")
        # 保存未捕获的异常
        launcher = KawaiiPythonLauncher()
        launcher.log_error("程序运行", str(e))
        launcher.save_errors_to_file()
    finally:
        print("\n🌈 小狸感谢你的使用，下次再见啦～")


if __name__ == "__main__":
    main()
