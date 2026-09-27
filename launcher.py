#!/usr/bin/env python3
"""
Lix CLI 启动器（TUI 向导版 · 新手化）
──────────────────────────────────────────
快路径：环境齐备 → 零打扰直接进主程序（TUI）
首次/加 --setup：进入 TUI 向导（textual），可视进度 + 卡片配置 + 密钥掩码输入；
textual 不可用时自动降级为纯文本向导（引导安装依赖的引导器自己不能依赖 TUI）。

新手化约定：
  · 全部有默认值，一路回车即可跑起来
  · 每步一句人话解释，不甩术语
  · 依赖安装全自动（import 名 → pip 包名映射），绝不覆写 requirements.txt
  · 参数原样透传给主程序（launcher.bat --cli 等照常生效）
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

# <input> 特殊语法：配置模型时可用它交互式询问用户并获取输入
try:
    from xcli_core.config import resolve_input_value
except Exception:
    def resolve_input_value(value, field_name="", default_prompt=None):
        return value

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


# import 名 → pip 包名映射（import 名≠pip 名的全部列在这）；requirements.txt 只读，绝不覆写
PIP_MAP = {
    'PIL': 'Pillow',
    'cv2': 'opencv-python',
    'ascii_magic': 'ascii-magic',
    'websocket': 'websocket-client',
    'yaml': 'pyyaml',
    'skimage': 'scikit-image',
    'bs4': 'beautifulsoup4',
    'google': 'protobuf',
}
# 标准库/系统自带，跳过安装
STDLIB_SKIP = {'tkinter', 'msvcrt', 'winsound', 'ctypes', 'readline', 'getpass', 'tty', 'termios'}


# ══════════════════════════════════════════════════════════════════
#  启动器主类
# ══════════════════════════════════════════════════════════════════

class Launcher:
    """Lix CLI 智能启动器"""

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
        self.plugins_dir    = self.project_dir / 'plugins'
        self.config_file    = self.project_dir / 'config.json'

        self.python_exe     = None
        self.pip_exe        = None
        self.is_system      = False
        self.errors         = []
        self.enabled_plugins = []

        self.third_party = {
            'colorama', 'openai', 'requests', 'ollama', 'pygame',
            'PIL', 'cv2', 'numpy', 'ascii_magic', 'matplotlib', 'pandas',
            'jedi', 'websockets', 'websocket', 'textual', 'rich',
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

        choice = prompt('选择下载源（不知道选啥直接回车 = 清华镜像）', '2')
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

        info('安装 pip...')
        self._install_pip()

        self.python_exe = str(self.embedded_exe)
        self.pip_exe = str(self.embedded_pip) if self.embedded_pip.exists() else None
        return True

    def _install_pip(self):
        exe = str(self.embedded_exe)
        r = subprocess.run([exe, '-m', 'ensurepip', '--upgrade'],
                           capture_output=True, text=True, encoding='utf-8')
        if r.returncode == 0:
            ok('pip 安装成功 (ensurepip)')
            return True

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
    #  依赖扫描与安装（requirements.txt 只读，绝不覆写）
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

        needed = {
            m for m in all_imports
            if m.split('.')[0] in self.third_party and m not in STDLIB_SKIP
        }
        if needed:
            info(f'需要的第三方库: {", ".join(sorted(needed))}')
        else:
            ok('所有依赖已就绪')
        # 注意：不再覆写 requirements.txt（那份是人工维护的清单，此前每次启动被本函数冲掉）
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
        info('（自动映射 pip 包名：PIL→Pillow、cv2→opencv-python 等）')
        pip = [self.python_exe, '-m', 'pip']
        mirrors = [
            '',
            '-i https://pypi.tuna.tsinghua.edu.cn/simple/',
            '-i https://mirrors.aliyun.com/pypi/simple/',
        ]

        success = 0
        for pkg in missing:
            pip_name = PIP_MAP.get(pkg, pkg)  # import 名 → pip 名
            installed = False
            for mirror in mirrors:
                cmd = pip + ['install', pip_name] + (mirror.split() if mirror else [])
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
                    if r.returncode == 0:
                        ok(f'{pip_name} 安装成功')
                        installed = True
                        success += 1
                        break
                except Exception:
                    pass
            if not installed:
                error(f'{pip_name} 安装失败（不影响启动，功能会缺）')

        return success == len(missing)

    # ══════════════════════════════════════════════════
    #  模型扫描与配置（统一 OpenAI 兼容格式，引擎架构已删除）
    # ══════════════════════════════════════════════════

    def _model_registry(self):
        sys.path.insert(0, str(self.project_dir))
        from xcli_core import model_registry
        return model_registry

    def scan_models(self):
        section('扫描已配置模型', '')
        try:
            mr = self._model_registry()
            models, current = mr.list_models()
        except Exception:
            models, current = [], None
        if not models:
            warn('尚未配置模型（稍后可添加，全部 OpenAI 兼容格式）')
            return {}
        out = {}
        for m in models:
            name = m.get('name', '?')
            out[name] = bool(m.get('api_key'))
            label = '云端' if out[name] else '本地'
            print(f"  {c(name, S.CYAN)} ({label})  {m.get('model', '')}")
        ok(f'共 {len(out)} 个已配置模型' + (f'，当前: {current}' if current else ''))
        return out

    def ensure_config(self, models=None):
        """确保 config.json 基础结构就绪 + 旧引擎配置迁移为模型条目（新手化：全默认）"""
        config = {}
        if self.config_file.exists():
            try:
                config = json.loads(self.config_file.read_text('utf-8'))
            except Exception:
                pass

        config.setdefault('api', {})
        config.setdefault('system', {})
        config['system'].setdefault('max_history', 50)

        self.config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), 'utf-8')
        try:
            self._model_registry().migrate_legacy()
        except Exception:
            pass
        return config

    def configure_models(self, models=None):
        """交互式添加模型（5+3 必填；全默认可跳过，之后 /model add 随时加）"""
        section('添加模型（OpenAI 兼容格式；可跳过）', '')
        if not prompt_yn('现在添加一个模型?', 'n'):
            return
        try:
            name = prompt('名称(用于切换, 如 gpt4o)', '').strip()
            if not name:
                print('  已跳过（名称为空）')
                return
            base_url = prompt('Base URL(如 https://api.deepseek.com/v1)', '').strip()
            api_key = self.secret_input('API 密钥（本地服务可留空）')
            model = prompt('模型名(如 deepseek-chat / gemma4:31b)', '').strip()
            if not model:
                print('  已跳过（模型名为空）')
                return
            max_in = prompt('最大输入 token', '32768').strip() or '32768'
            max_out = prompt('最大输出 token', '4096').strip() or '4096'
            image_input = prompt_yn('支持图片输入?', 'n')
            video_input = prompt_yn('支持视频输入?', 'n')
            audio_input = prompt_yn('支持音频输入?', 'n')
        except (EOFError, KeyboardInterrupt):
            print('  已取消')
            return
        try:
            mr = self._model_registry()
            mr.add_model({
                'name': name, 'base_url': base_url, 'api_key': api_key, 'model': model,
                'max_input': int(max_in), 'max_output': int(max_out),
                'image_input': image_input, 'video_input': video_input,
                'audio_input': audio_input,
            })
            mr.set_current(name)
            ok(f'已添加模型: {name}')
        except Exception as e:
            error(f'保存失败: {e}')

    # ══════════════════════════════════════════════════
    #  插件管理（新手化：默认全启用，不打扰）
    # ══════════════════════════════════════════════════

    def discover_plugins(self):
        if not self.plugins_dir.exists():
            return []
        return sorted([
            f.stem for f in self.plugins_dir.glob('*.py')
            if not f.stem.startswith('__')
        ])

    def ensure_plugins_config(self):
        """默认启用全部插件；只在配置文件缺失时生成，绝不覆盖已有选择"""
        plugins = self.discover_plugins()
        cfg_path = self.project_dir / 'plugins_config.py'
        if cfg_path.exists():
            self.enabled_plugins = plugins
            return plugins

        lines = ['# Lix插件配置 - 由启动器自动生成（默认全启用）\n']
        for p in plugins:
            lines.append(f'ENABLE_{p.upper()} = True\n')
        cfg_path.write_text(''.join(lines), 'utf-8')
        self.enabled_plugins = plugins
        return plugins

    def configure_plugins(self):
        """高级选择（仅 --setup 时询问；默认全启用）"""
        section('插件配置', '')
        plugins = self.discover_plugins()

        if not plugins:
            info('没有发现插件')
            return []

        ok(f'发现 {len(plugins)} 个插件:')
        for i, p in enumerate(plugins, 1):
            print(f"    {c(i, S.CYAN)}. {p}")

        print()
        choice = prompt("选择插件 (编号逗号分隔 / all / none，回车=all)", 'all')

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

        cfg_path = self.project_dir / 'plugins_config.py'
        lines = ['# Lix插件配置 - 由启动器自动生成\n']
        for p in selected:
            lines.append(f'ENABLE_{p.upper()} = True\n')
        cfg_path.write_text(''.join(lines), 'utf-8')

        return selected

    # ══════════════════════════════════════════════════
    #  快路径判定 / 启动主程序
    # ══════════════════════════════════════════════════

    def quick_check(self):
        """不打扰快路径判定：Python 在 + 核心依赖在 + 配置文件在 → 直接进主程序"""
        candidates = [sys.executable] if sys.executable else []
        candidates += ['python3', 'python']
        for cmd in candidates:
            if not cmd:
                continue
            try:
                r = subprocess.run([cmd, '--version'], capture_output=True, text=True, encoding='utf-8')
                if r.returncode == 0 and 'Python' in r.stdout:
                    self.python_exe = cmd
                    self.is_system = True
                    break
            except FileNotFoundError:
                continue
        else:
            if self.embedded_exe.exists():
                self.python_exe = str(self.embedded_exe)
            else:
                return False

        try:
            r = subprocess.run([self.python_exe, '-c', 'import colorama'],
                               capture_output=True, text=True)
            if r.returncode != 0:
                return False
        except Exception:
            return False

        return self.config_file.exists()

    def launch(self):
        section('启动主程序', '')

        env = os.environ.copy()
        if self.enabled_plugins is not None:
            env['XIAOLI_ENABLED_PLUGINS'] = ','.join(self.enabled_plugins)

        # argv 原样透传（--cli / --logo / --no-tui 等照常生效）
        args = [self.python_exe, str(self.main_program)] + sys.argv[1:]
        try:
            subprocess.run(args, env=env)
        except Exception as e:
            error(f'启动失败: {e}')

    # ══════════════════════════════════════════════════
    #  主流程
    # ══════════════════════════════════════════════════

    def run(self):
        # 快路径：环境齐备且非 --setup → 零打扰直达主程序
        if '--setup' not in sys.argv and self.quick_check():
            self.enabled_plugins = self.discover_plugins()
            self.launch()
            return

        # 向导：优先 TUI（与主程序同观感），textual 不可用降级纯文本
        try:
            import textual  # noqa: F401
            self._run_tui_wizard()
            return
        except ImportError:
            pass

        self._run_text_wizard()

    def _run_text_wizard(self):
        """纯文本向导（textual 不可用时的引导路径）"""
        self.clear()
        print()
        print(c('  ┌────────────────────────────────────────────────┐', S.CYAN))
        print(c('  │       小 狸  Pro-CLI  智 能 启 动 器          │', S.CYAN))
        print(c('  └────────────────────────────────────────────────┘', S.CYAN))
        print(f"\n  {c('第一次用？一路回车就行，全部有默认值。', S.DIM)}")

        if not self.detect_python():
            self._show_report(False)
            return

        models = self.scan_models()
        self.ensure_config(models)

        packages = self.scan_imports()
        deps_ok = self.install_deps(packages)

        self.enabled_plugins = self.ensure_plugins_config()

        self.configure_models(models)

        self._show_report(deps_ok)

        if deps_ok or prompt_yn('依赖不完整，仍然尝试启动?', 'y'):
            self.launch()

    def _run_tui_wizard(self):
        """TUI 向导（textual）：可视进度 + 密钥掩码配置 + 完成页"""
        try:
            run_wizard_app(self)
        except Exception as e:
            warn(f'TUI 向导启动失败（{e}），降级纯文本向导')
            self._run_text_wizard()

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
#  TUI 向导（opencode 同观感：黑底 + 像素 logo + 盒式面板 + 橙 Tip）
# ══════════════════════════════════════════════════════════════════

def run_wizard_app(launcher):
    from textual.app import App, ComposeResult
    from textual.containers import Vertical, VerticalScroll
    from textual.widgets import Static, Input

    BG, PANEL, BORDER = "#121212", "#1c1c1c", "#272727"
    TEXT, DIM, ORANGE = "#d4d4d4", "#6b6b6b", "#d98d5f"

    # 5×7 像素字模（与主 TUI 同款 xiaoli logo）
    LOGO_FONT = {
        'x': [".....", ".....", "X...X", ".X.X.", "..X..", ".X.X.", "X...X"],
        'i': [".X...", ".....", ".X...", ".X...", ".X...", ".X...", ".X..."],
        'a': [".....", ".....", ".XXX.", "....X", ".XXXX", "X...X", ".XXXX"],
        'o': [".....", ".....", ".XXX.", "X...X", "X...X", "X...X", ".XXX."],
        'l': ["..X..", "..X..", "..X..", "..X..", "..X..", "..X..", ".XXX."],
    }

    def logo_rows():
        rows = []
        for r in range(7):
            line = ""
            for j, ch in enumerate("xiaoli"):
                if j:
                    line += " "
                line += "".join("█" if cell == "X" else " " for cell in LOGO_FONT[ch][r])
            rows.append((line, "#6e6e6e" if r < 4 else "#f0f0f0"))
        return rows

    class WizardApp(App):
        TITLE = " Lix CLI 安装向导"
        CSS = f"""
        Screen {{ background: {BG}; }}
        #box {{ border: tall {BORDER}; background: {PANEL}; padding: 1 2; margin: 1 3; height: auto; max-height: 28; }}
        .logo {{ text-style: bold; text-align: center; padding: 0; }}
        .tag  {{ color: {DIM}; text-align: center; padding: 1 0 1 0; }}
        #log {{ color: {TEXT}; height: auto; max-height: 16; overflow-y: auto; }}
        .ln-ok   {{ color: #6cbf6c; }}
        .ln-warn {{ color: #d9a75f; }}
        .ln-err  {{ color: #d9665f; }}
        .ln-info {{ color: {TEXT}; }}
        .ln-dim  {{ color: {DIM}; }}
        #keyline {{ color: {DIM}; text-align: center; padding: 1 0; }}
        #tip {{ color: {DIM}; text-align: center; padding: 1 0 0 0; }}
        Input {{ background: {BG}; border: tall {BORDER}; margin: 0 1; }}
        .field-label {{ color: {DIM}; padding: 1 1 0 1; }}
        """
        BINDINGS = [
            ("enter", "primary", "继续"),
            ("s", "setup", "配置API"),
            ("q", "quit", "退出"),
        ]

        def __init__(self, launcher):
            super().__init__()
            self.launcher = launcher
            self.stage = "progress"   # progress -> config -> done
            self.models = {}
            self.deps_ok = False
            self._fields = {}
            self._caps = {}

        def compose(self) -> ComposeResult:
            with Vertical():
                for text, col in logo_rows():
                    yield Static(text, classes="logo", markup=False, styles={"color": col})
                yield Static("Lix CLI · 首次启动向导（一路回车即可）", classes="tag")
                with Vertical(id="box"):
                    yield VerticalScroll(id="log")
                yield Static(
                    "[bold]回车[/] 继续/启动   [bold]s[/] 配置 API（可跳过）   [bold]q[/] 退出",
                    id="keyline")
                yield Static("[bold]● Tip[/]  不懂的选项全部回车用默认，之后随时可用 --setup 重新配置", id="tip")

        def on_mount(self):
            self.run_worker(self._do_checks(), exclusive=True)

        def _log(self, text, cls="ln-info"):
            try:
                self.query_one("#log").mount(Static(text, classes=cls, markup=False))
            except Exception:
                pass

        async def _do_checks(self):
            import asyncio
            loop = asyncio.get_running_loop()
            L = self.launcher

            def step_detect():
                for cmd in ('python3', 'python'):
                    try:
                        r = subprocess.run([cmd, '--version'], capture_output=True,
                                           text=True, encoding='utf-8')
                        if r.returncode == 0 and 'Python' in r.stdout:
                            L.python_exe = cmd
                            L.is_system = True
                            return r.stdout.strip()
                    except FileNotFoundError:
                        continue
                return None

            ver = await loop.run_in_executor(None, step_detect)
            if ver:
                self._log(f"  ✓ Python 环境: {ver}", "ln-ok")
            else:
                self._log("  ! 未检测到 Python —— 请先安装 Python 3.10+ 再重新打开", "ln-err")

            self.models = await loop.run_in_executor(None, L.scan_models_silent)
            names = ", ".join(self.models.keys()) or "无（按 s 添加）"
            self._log(f"  ✓ 已配置模型: {names}", "ln-ok")

            await loop.run_in_executor(None, L.ensure_config, self.models)
            self._log("  ✓ 配置文件就绪（全默认，可跳过配置）", "ln-ok")

            pkgs = await loop.run_in_executor(None, L.scan_imports_silent)
            missing = [p for p in sorted(pkgs) if not L._pkg_installed(p)]
            if missing:
                self._log(f"  … 安装依赖: {', '.join(missing)}", "ln-dim")
                for p in missing:
                    okk = await loop.run_in_executor(None, L._install_one, p)
                    self._log(f"    {'✓' if okk else '✗'} {PIP_MAP.get(p, p)}",
                              "ln-ok" if okk else "ln-warn")
                self.deps_ok = all(L._pkg_installed(p) for p in missing)
            else:
                self._log("  ✓ 依赖齐备", "ln-ok")
                self.deps_ok = True

            plugins = await loop.run_in_executor(None, L.ensure_plugins_config)
            self._log(f"  ✓ 插件: {len(plugins)} 个默认启用", "ln-ok")

            self._log("", "ln-dim")
            self._log("  准备就绪！回车直接开始用；按 s 添加模型（OpenAI 兼容格式）。", "ln-info")
            self.stage = "done"

        def action_primary(self):
            if self.stage == "progress":
                return
            if self.stage == "config":
                self._save_config()
                self.stage = "done"
                self.query_one("#log").remove_children()
                self._log("  ✓ 配置已保存", "ln-ok")
                self._log("  回车开始使用Lix", "ln-info")
                return
            # done → 启动主程序
            self.exit()
            try:
                from xcli_core.notify_sound import play
                play("special")   # 向导完成彩蛋音
            except Exception:
                pass
            self.launcher.enabled_plugins = self.launcher.discover_plugins()
            self.launcher.launch()

        def action_setup(self):
            if self.stage != "done":
                return
            self.stage = "config"
            self._show_config_form()

        def _show_config_form(self):
            log = self.query_one("#log")
            log.remove_children()
            self._fields = {}
            self._caps = {}
            log.mount(Static("  添加模型（OpenAI 兼容格式；本地 Ollama 填 http://localhost:11434/v1，密钥可留空）",
                             classes="ln-info", markup=False))
            specs = [
                ("name", "名称（用于切换，如 gpt4o）", False),
                ("base_url", "Base URL（如 https://api.deepseek.com/v1）", False),
                ("api_key", "API 密钥（本地服务可留空）", True),
                ("model", "模型名（如 deepseek-chat / gemma4:31b）", False),
                ("max_input", "最大输入 token（如 32768）", False),
                ("max_output", "最大输出 token（如 4096）", False),
            ]
            for key, ph, secret in specs:
                log.mount(Static(f"  {ph}", classes="field-label", markup=False))
                inp = Input(placeholder=ph, password=secret, id=f"f-{key}")
                log.mount(inp)
                self._fields[key] = inp
            log.mount(Static("  多模态能力（输入 y=支持，回车=不支持）",
                             classes="field-label", markup=False))
            for key, ph in (("image_input", "支持图片输入? (y/N)"),
                            ("video_input", "支持视频输入? (y/N)"),
                            ("audio_input", "支持音频输入? (y/N)")):
                inp = Input(placeholder=ph, id=f"f-{key}")
                log.mount(inp)
                self._caps[key] = inp

        def _save_config(self):
            try:
                name = self._fields["name"].value.strip()
                model = self._fields["model"].value.strip()
                if not name or not model:
                    self._log("  ! 名称和模型名不能为空", "ln-err")
                    return
                def _yes(w):
                    return w.value.strip().lower() in ("y", "yes")
                entry = {
                    "name": name,
                    "base_url": self._fields["base_url"].value.strip(),
                    "api_key": self._fields["api_key"].value.strip(),
                    "model": model,
                    "max_input": int(self._fields["max_input"].value.strip() or 0),
                    "max_output": int(self._fields["max_output"].value.strip() or 0),
                    "image_input": _yes(self._caps["image_input"]),
                    "video_input": _yes(self._caps["video_input"]),
                    "audio_input": _yes(self._caps["audio_input"]),
                }
                mr = self.launcher._model_registry()
                mr.add_model(entry)
                mr.set_current(name)
                self.models[name] = bool(entry["api_key"])
                self._log(f"  ✓ 已保存模型: {name}", "ln-ok")
            except Exception as e:
                self._log(f"  ! 保存失败: {e}", "ln-err")

    WizardApp(launcher).run()


# ── Launcher 的静默辅助（TUI 向导用；不打印，结果走 UI 日志）──

def _scan_models_silent(self):
    """已配置模型清单（静默版，TUI 向导用）"""
    try:
        mr = self._model_registry()
        models, _ = mr.list_models()
        return {m.get('name', '?'): bool(m.get('api_key')) for m in models}
    except Exception:
        return {}

def _scan_imports_silent(self):
    exclude = {'__pycache__', '.git', 'venv', '.venv', 'env', '.env', 'build', 'dist'}
    all_imports = set()
    for f in self.project_dir.rglob('*.py'):
        if any(exc in str(f) for exc in exclude):
            continue
        try:
            for m in re.finditer(r'^\s*(?:import|from)\s+([a-zA-Z_]\w*)',
                                 f.read_text('utf-8'), re.MULTILINE):
                all_imports.add(m.group(1))
        except Exception:
            pass
    return {m for m in all_imports
            if m.split('.')[0] in self.third_party and m not in STDLIB_SKIP}

def _pkg_installed(self, pkg):
    try:
        r = subprocess.run([self.python_exe or 'python', '-c', f'import {pkg}'],
                           capture_output=True, text=True)
        return r.returncode == 0
    except Exception:
        return False

def _install_one(self, pkg):
    pip_name = PIP_MAP.get(pkg, pkg)
    for mirror in ['', '-i https://pypi.tuna.tsinghua.edu.cn/simple/',
                   '-i https://mirrors.aliyun.com/pypi/simple/']:
        cmd = [(self.python_exe or 'python'), '-m', 'pip', 'install', pip_name] \
            + (mirror.split() if mirror else [])
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if r.returncode == 0:
                return True
        except Exception:
            pass
    return False

Launcher.scan_models_silent = _scan_models_silent
Launcher.scan_imports_silent = _scan_imports_silent
Launcher._pkg_installed = _pkg_installed
Launcher._install_one = _install_one


def main():
    try:
        Launcher().run()
    except KeyboardInterrupt:
        print(f"\n\n  {c('再见!', S.CYAN)}")
    except Exception as e:
        print(f"\n  {c(f'意外错误: {e}', S.RED)}")


if __name__ == '__main__':
    main()
