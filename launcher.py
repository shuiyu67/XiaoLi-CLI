#!/usr/bin/env python3
"""
小狸 Pro-CLI 启动器
自动检测环境、安装依赖、配置引擎，然后启动主程序
"""

import subprocess
import sys
import os
import re
import json
import urllib.request
import zipfile
import io
from pathlib import Path
from datetime import datetime
import platform

# ── 编码设置 ──
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ── 样式常量 ──
class S:
    """终端样式"""
    RESET  = '\033[0m'
    BOLD   = '\033[1m'
    DIM    = '\033[2m'
    CYAN   = '\033[36m'
    GREEN  = '\033[32m'
    YELLOW = '\033[33m'
    RED    = '\033[31m'
    MAGENTA= '\033[35m'
    BLUE   = '\033[34m'
    WHITE  = '\033[97m'

def c(text, color):
    return f"{color}{text}{S.RESET}"

def banner(text, color=S.CYAN):
    lines = text.split('\n')
    width = max(len(line) for line in lines)
    border = '─' * (width + 4)
    top = '┌' + border + '┐'
    bot = '└' + border + '┘'
    print(c(top, color))
    for line in lines:
        padded = line.center(width)
        print(c('│  ' + padded + '  │', color))
    print(c(bot, color))

def section(title, icon='●'):
    print(f"\n{c(f' {icon} ', S.CYAN)} {c(title, S.BOLD)}")
    print(c('  ' + '─' * 44, S.DIM))

def info(msg):
    print(f"  {c('→', S.GREEN)} {msg}")

def warn(msg):
    print(f"  {c('!', S.YELLOW)} {msg}")

def error(msg):
    print(f"  {c('', S.RED)} {msg}")

def ok(msg):
    print(f"  {c('', S.GREEN)} {msg}")

def prompt(msg, default=''):
    suffix = f" [{default}]" if default else ''
    try:
        val = input(f"  {c('?', S.BLUE)} {msg}{suffix}: ").strip()
        return val if val else default
    except (KeyboardInterrupt, EOFError):
        print()
        return default

def prompt_yn(msg, default='y'):
    suffix = '[Y/n]' if default == 'y' else '[y/N]'
    val = prompt(f"{msg} {suffix}", default)
    return val.lower() in ('y', 'yes')


# ══════════════════════════════════════════════════════════════════
#  启动器主类
# ══════════════════════════════════════════════════════════════════

class Launcher:
    """小狸 Pro-CLI 智能启动器"""

    DOWNLOAD_SOURCES = {
        '1': ('Python 官方源',   'https://www.python.org/ftp/python/3.12.0/python-3.12.0-embed-amd64.zip'),
        '2': ('清华镜像 (推荐)', 'https://mirrors.tuna.tsinghua.edu.cn/python/3.12.0/python-3.12.0-embed-amd64.zip'),
        '3': ('中科大镜像',      'https://mirrors.ustc.edu.cn/python/3.12.0/python-3.12.0-embed-amd64.zip'),
        '4': ('阿里云镜像',      'https://mirrors.aliyun.com/python/3.12.0/python-3.12.0-embed-amd64.zip'),
    }

    def __init__(self):
        if getattr(sys, 'frozen', False):
            self.project_dir = Path(os.path.dirname(sys.executable))
        else:
            self.project_dir = Path(__file__).parent

        self.embedded_dir   = self.project_dir / 'embedded_python'
        self.embedded_exe   = self.embedded_dir / 'python.exe'
        self.embedded_pip   = self.embedded_dir / 'Scripts' / 'pip.exe'
        self.main_program   = self.project_dir / 'ai_cli.py'
        self.engines_dir    = self.project_dir / 'ai_engines'
        self.plugins_dir    = self.project_dir / 'plugins'
        self.config_file    = self.project_dir / 'config.json'

        self.python_exe     = None
        self.pip_exe        = None
        self.is_system      = False
        self.errors         = []
        self.enabled_plugins = []

        self.third_party = {
            'colorama', 'openai', 'requests', 'ollama', 'pygame',
            'PIL', 'Pillow', 'cv2', 'opencv-python', 'numpy',
            'ascii_magic', 'tkinter', 'matplotlib', 'pandas',
        }

    # ── 清屏 ──
    def clear(self):
        os.system('cls' if platform.system() == 'Windows' else 'clear')

    # ── 安全输入 API 密钥 ──
    def secret_input(self, prompt_text='API 密钥'):
        try:
            import msvcrt
            print(f"  {c('?', S.BLUE)} {prompt_text} (输入时隐藏，回车确认): ", end='', flush=True)
            buf = ''
            while True:
                ch = msvcrt.getch()
                if ch in (b'\r', b'\n'):
                    print()
                    return buf
                elif ch == b'\x08':
                    if buf:
                        buf = buf[:-1]
                        print('\b \b', end='', flush=True)
                else:
                    buf += ch.decode('utf-8')
                    print('*', end='', flush=True)
        except ImportError:
            import getpass
            return getpass.getpass(f"  {c('?', S.BLUE)} {prompt_text}: ")

    # ══════════════════════════════════════════════════
    #  Python 环境检测
    # ══════════════════════════════════════════════════

    def detect_python(self):
        section('检测 Python 环境', '')

        # 系统 Python
        for cmd in ('python3', 'python'):
            try:
                r = subprocess.run([cmd, '--version'], capture_output=True, text=True, encoding='utf-8')
                if r.returncode == 0 and 'Python' in r.stdout:
                    ver = r.stdout.strip()
                    ok(f'找到系统 Python: {ver}')
                    self.python_exe = cmd
                    self.is_system = True
                    return True
            except FileNotFoundError:
                pass

        warn('未找到系统 Python')

        # 嵌入式 Python
        if self.embedded_exe.exists():
            try:
                r = subprocess.run([str(self.embedded_exe), '--version'],
                                   capture_output=True, text=True, encoding='utf-8')
                if r.returncode == 0:
                    ok(f'找到嵌入式 Python: {r.stdout.strip()}')
                    self.python_exe = str(self.embedded_exe)
                    self.pip_exe = str(self.embedded_pip)
                    return True
            except Exception:
                pass

        warn('嵌入式 Python 也不在')
        info('需要下载安装...')

        if self.install_embedded_python():
            ok('Python 环境安装完成')
            return True

        error('无法获取 Python 环境')
        return False

    # ── 下载安装嵌入式 Python ──

    def install_embedded_python(self):
        section('安装嵌入式 Python', '')

        print()
        for key, (name, url) in self.DOWNLOAD_SOURCES.items():
            print(f"    {c(key, S.CYAN)}. {name}")
            print(f"      {c(url, S.DIM)}")
        print(f"    {c('5', S.CYAN)}. 自定义 URL")
        print(f"    {c('0', S.CYAN)}. 取消")
        print()

        choice = prompt('选择下载源', '2')
        if choice == '0':
            return False
        elif choice == '5':
            url = prompt('输入下载 URL')
            if not url.startswith(('http://', 'https://')):
                error('无效的 URL')
                return False
        elif choice in self.DOWNLOAD_SOURCES:
            url = self.DOWNLOAD_SOURCES[choice][1]
        else:
            error('无效的选择')
            return False

        # 测试连通性
        info(f'测试下载源...')
        try:
            req = urllib.request.Request(url, method='HEAD')
            resp = urllib.request.urlopen(req, timeout=10)
            if resp.status != 200:
                error(f'源不可用 (HTTP {resp.status})')
                return False
            size = resp.headers.get('Content-Length')
            if size:
                ok(f'源可用, 文件大小 {int(size)/1024/1024:.1f} MB')
        except Exception as e:
            error(f'连接失败: {e}')
            return False

        # 下载
        self.embedded_dir.mkdir(exist_ok=True)
        zip_path = self.project_dir / 'python_embedded.zip'

        try:
            info('正在下载...')

            def hook(count, block, total):
                if total > 0:
                    pct = min(100, int(count * block * 100 / total))
                    filled = pct // 5
                    bar = '█' * filled + '░' * (20 - filled)
                    print(f"\r    {c('↓', S.CYAN)} [{bar}] {pct}%", end='', flush=True)

            urllib.request.urlretrieve(url, str(zip_path), hook)
            print()
            ok('下载完成')
        except Exception as e:
            print()
            error(f'下载失败: {e}')
            return False

        # 解压
        try:
            info('解压中...')
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(self.embedded_dir)
            ok('解压完成')
        except Exception as e:
            error(f'解压失败: {e}')
            return False
        finally:
            zip_path.unlink(missing_ok=True)

        # 配置 ._pth
        try:
            pth = self.embedded_dir / 'python._pth'
            if pth.exists():
                content = pth.read_text('utf-8')
                content = content.replace('#import site', 'import site')
                if 'import site' not in content:
                    content += '\nimport site'
                content += f'\n.\n{self.embedded_dir / "Lib"}\n{self.embedded_dir / "DLLs"}'
                pth.write_text(content, 'utf-8')
        except Exception:
            pass

        # 安装 pip
        info('安装 pip...')
        self._install_pip()

        # 验证
        self.python_exe = str(self.embedded_exe)
        self.pip_exe = str(self.embedded_pip) if self.embedded_pip.exists() else None
        return True

    def _install_pip(self):
        exe = str(self.embedded_exe)
        # 方式1: ensurepip
        r = subprocess.run([exe, '-m', 'ensurepip', '--upgrade'],
                           capture_output=True, text=True, encoding='utf-8')
        if r.returncode == 0:
            ok('pip 安装成功 (ensurepip)')
            return True

        # 方式2: get-pip.py
        info('尝试 get-pip.py...')
        urls = [
            'https://bootstrap.pypa.io/get-pip.py',
            'https://gitee.com/mirrors/get-pip/raw/main/public/get-pip.py',
        ]
        get_pip = self.embedded_dir / 'get-pip.py'
        for url in urls:
            try:
                urllib.request.urlretrieve(url, str(get_pip))
                r = subprocess.run([exe, str(get_pip)], capture_output=True, text=True, encoding='utf-8')
                get_pip.unlink(missing_ok=True)
                if r.returncode == 0:
                    ok('pip 安装成功 (get-pip.py)')
                    return True
            except Exception:
                continue

        warn('pip 安装失败，部分功能可能受限')
        return False

    # ══════════════════════════════════════════════════
    #  依赖扫描与安装
    # ══════════════════════════════════════════════════

    def scan_imports(self):
        section('扫描项目依赖', '')

        exclude = {'__pycache__', '.git', 'venv', '.venv', 'env', '.env', 'build', 'dist'}
        py_files = [
            f for f in self.project_dir.rglob('*.py')
            if not any(exc in str(f) for exc in exclude)
        ]

        all_imports = set()
        for f in py_files:
            try:
                content = f.read_text('utf-8')
                for m in re.finditer(r'^\s*(?:import|from)\s+([a-zA-Z_]\w*)', content, re.MULTILINE):
                    all_imports.add(m.group(1))
            except Exception:
                pass

        ok(f'扫描了 {len(py_files)} 个 Python 文件')
        ok(f'发现 {len(all_imports)} 个模块引用')

        needed = {m for m in all_imports if m.split('.')[0] in self.third_party}
        if needed:
            info(f'需要安装: {", ".join(sorted(needed))}')
        else:
            ok('所有依赖已就绪')

        # 写 requirements.txt
        req_file = self.project_dir / 'requirements.txt'
        try:
            with open(req_file, 'w', encoding='utf-8') as f:
                f.write(f'# 小狸 Pro-CLI 依赖\n# 生成于 {datetime.now():%Y-%m-%d %H:%M}\n\n')
                for pkg in sorted(needed):
                    f.write(f'{pkg}\n')
        except Exception:
            pass

        return needed

    def install_deps(self, packages):
        if not packages:
            return True

        section('安装依赖', '')
        missing = []
        for pkg in sorted(packages):
            try:
                r = subprocess.run([self.python_exe, '-c', f'import {pkg}'],
                                   capture_output=True, text=True)
                if r.returncode == 0:
                    ok(f'{pkg}  ')
                else:
                    warn(f'{pkg}  缺失')
                    missing.append(pkg)
            except Exception:
                missing.append(pkg)

        if not missing:
            ok('全部依赖已就绪')
            return True

        info(f'需要安装 {len(missing)} 个包: {", ".join(missing)}')
        pip = [self.python_exe, '-m', 'pip']
        mirrors = [
            '',
            '-i https://pypi.tuna.tsinghua.edu.cn/simple/',
            '-i https://mirrors.aliyun.com/pypi/simple/',
        ]

        success = 0
        for pkg in missing:
            installed = False
            for i, mirror in enumerate(mirrors):
                cmd = pip + ['install', pkg] + (mirror.split() if mirror else [])
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
                    if r.returncode == 0:
                        ok(f'{pkg} 安装成功')
                        installed = True
                        success += 1
                        break
                except Exception:
                    pass
            if not installed:
                error(f'{pkg} 安装失败')

        return success == len(missing)

    # ══════════════════════════════════════════════════
    #  引擎扫描与配置
    # ══════════════════════════════════════════════════

    def scan_engines(self):
        section('扫描 AI 引擎', '')

        if not self.engines_dir.exists():
            warn('ai_engines 目录不存在')
            return {}

        engines = {}
        for f in self.engines_dir.glob('*_engine.py'):
            name = f.stem.replace('_engine', '')
            # 检查 requires_api_key
            needs_key = True
            try:
                content = f.read_text('utf-8')
                if 'requires_api_key = False' in content:
                    needs_key = False
            except Exception:
                pass
            engines[name] = needs_key
            icon = '' if not needs_key else ''
            label = '本地' if not needs_key else '云端'
            print(f"  {icon} {c(name, S.CYAN)} ({label})")

        if not engines:
            warn('未发现引擎文件')
        else:
            ok(f'共发现 {len(engines)} 个引擎')

        return engines

    def ensure_config(self, engines):
        """确保 config.json 包含所有引擎的配置"""
        config = {}
        if self.config_file.exists():
            try:
                config = json.loads(self.config_file.read_text('utf-8'))
            except Exception:
                pass

        config.setdefault('api', {}).setdefault('engines', {})
        config.setdefault('system', {})
        config['system'].setdefault('default_engine', 'ollama')
        config['system'].setdefault('max_history', 50)

        for name, needs_key in engines.items():
            if name not in config['api']['engines']:
                entry = {'api_key': '', 'base_url': '', 'model': ''}
                if name == 'ollama':
                    entry['base_url'] = 'http://localhost:11434'
                    entry['model'] = 'gemma4:31b'
                elif name == 'openai':
                    entry['base_url'] = 'https://api.deepseek.com/v1'
                    entry['model'] = 'deepseek-chat'
                config['api']['engines'][name] = entry

        self.config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), 'utf-8')
        return config

    def configure_engines(self, engines):
        """交互式配置引擎"""
        section('配置 API', '')

        config = {}
        if self.config_file.exists():
            try:
                config = json.loads(self.config_file.read_text('utf-8'))
            except Exception:
                pass

        for name, needs_key in engines.items():
            cfg = config.get('api', {}).get('engines', {}).get(name, {})
            print()
            print(f"  {c('───', S.DIM)} {c(name, S.BOLD)} {c('───', S.DIM)}")

            if needs_key:
                current_key = cfg.get('api_key', '')
                if current_key:
                    masked = '*' * max(0, len(current_key) - 4) + current_key[-4:]
                    info(f'当前密钥: {masked}')
                if prompt_yn(f'配置 {name} 的 API 密钥?', 'n'):
                    key = self.secret_input(f'{name} API 密钥')
                    cfg['api_key'] = key

            # URL
            current_url = cfg.get('base_url', '')
            if current_url:
                info(f'当前 URL: {current_url}')
            if prompt_yn(f'配置 {name} 的 Base URL?', 'n'):
                url = prompt('Base URL', current_url)
                cfg['base_url'] = url

            # Model
            current_model = cfg.get('model', '')
            if current_model:
                info(f'当前模型: {current_model}')
            if prompt_yn(f'配置 {name} 的模型?', 'n'):
                model = prompt('模型名称', current_model)
                cfg['model'] = model

            config.setdefault('api', {}).setdefault('engines', {})[name] = cfg

        self.config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), 'utf-8')
        ok('配置已保存')

    # ══════════════════════════════════════════════════
    #  插件管理
    # ══════════════════════════════════════════════════

    def discover_plugins(self):
        if not self.plugins_dir.exists():
            return []
        return sorted([
            f.stem for f in self.plugins_dir.glob('*.py')
            if not f.stem.startswith('__')
        ])

    def configure_plugins(self):
        section('插件配置', '')
        plugins = self.discover_plugins()

        if not plugins:
            info('没有发现插件')
            return []

        ok(f'发现 {len(plugins)} 个插件:')
        for i, p in enumerate(plugins, 1):
            print(f"    {c(i, S.CYAN)}. {p}")

        print()
        choice = prompt("选择插件 (编号逗号分隔 / all / none)", 'all')

        if choice.lower() == 'all':
            selected = plugins
        elif choice.lower() in ('none', '0'):
            selected = []
        else:
            indices = []
            for part in choice.split(','):
                part = part.strip()
                if part.isdigit() and 1 <= int(part) <= len(plugins):
                    indices.append(int(part) - 1)
            selected = [plugins[i] for i in indices]

        if selected:
            info(f'启用: {", ".join(selected)}')
        else:
            info('不启用任何插件')

        # 写配置
        cfg_path = self.project_dir / 'plugins_config.py'
        lines = ['# 小狸插件配置 - 由启动器自动生成\n']
        for p in selected:
            lines.append(f'ENABLE_{p.upper()} = True\n')
        cfg_path.write_text(''.join(lines), 'utf-8')

        return selected

    # ══════════════════════════════════════════════════
    #  启动主程序
    # ══════════════════════════════════════════════════

    def launch(self):
        section('启动主程序', '')

        env = os.environ.copy()
        if self.enabled_plugins is not None:
            env['XIAOLI_ENABLED_PLUGINS'] = ','.join(self.enabled_plugins)

        try:
            subprocess.run([self.python_exe, str(self.main_program)], env=env)
        except Exception as e:
            error(f'启动失败: {e}')

    # ══════════════════════════════════════════════════
    #  主流程
    # ══════════════════════════════════════════════════

    def run(self):
        self.clear()

        print()
        print(c('  ┌────────────────────────────────────────────────┐', S.CYAN))
        print(c('  │                                                │', S.CYAN))
        print(c('  │       小 狸  Pro-CLI  智 能 启 动 器          │', S.CYAN))
        print(c('  │                                                │', S.CYAN))
        print(c('  └────────────────────────────────────────────────┘', S.CYAN))
        print()

        # 1. Python 环境
        if not self.detect_python():
            self._show_report(False)
            return

        # 2. 扫描引擎
        engines = self.scan_engines()
        self.ensure_config(engines)

        # 3. 依赖
        packages = self.scan_imports()
        deps_ok = self.install_deps(packages)

        # 4. 插件
        self.enabled_plugins = self.configure_plugins()

        # 5. 配置向导
        if engines and prompt_yn('现在配置 API / 引擎?', 'n'):
            self.configure_engines(engines)

        # 6. 报告
        self._show_report(deps_ok)

        # 7. 启动
        if deps_ok or prompt_yn('依赖不完整，仍然尝试启动?', 'y'):
            self.launch()

    def _show_report(self, deps_ok):
        section('环境报告', '')
        py_ok = self.python_exe is not None
        print(f"  {'' if py_ok else ''} Python 环境: {'就绪' if py_ok else '未就绪'}")
        print(f"  {'' if deps_ok else ''} 依赖安装: {'完成' if deps_ok else '部分缺失'}")
        print(f"  {'' if self.enabled_plugins is not None else '?'} 插件: {len(self.enabled_plugins) if self.enabled_plugins else 0} 个已启用")

        if self.errors:
            print(f"\n  {c('错误日志:', S.RED)}")
            for e in self.errors:
                print(f"    • {e}")
            try:
                bug = self.project_dir / 'bug.txt'
                bug.write_text('\n'.join(self.errors), 'utf-8')
                info(f'错误已保存到 {bug}')
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════════

def main():
    try:
        Launcher().run()
    except KeyboardInterrupt:
        print(f"\n\n  {c('再见!', S.CYAN)}")
    except Exception as e:
        print(f"\n  {c(f'意外错误: {e}', S.RED)}")


if __name__ == '__main__':
    main()
