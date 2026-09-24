import os
import sys
import shutil
import time
import subprocess
import platform
import re
from colorama import Fore, Style

from .constants import MAX_FILE_SIZE, VIDEO_FRAME_DELAY
from .config import logger


def emit(obj, message):
    """统一输出助手：真 AICLI 走 _output（TUI 回调/CLI print 双模式）；
    测试桩（SimpleNamespace 等无 _output）回退 print，行为等价。"""
    fn = getattr(obj, "_output", None)
    if callable(fn):
        fn(message)
    else:
        print(message)


class DisplayMixin:
    """显示、输出、图片、帮助相关方法"""

    def _process_code_blocks(self, text):
        """处理包含""" """语法的文本，将代码块部分显示为红色"""
        pattern = r'(\"\"\".*?\"\"\")'

        def replace_match(match):
            full_match = match.group(1)
            inner_content = full_match[3:-3]
            return f'{Fore.RED}{inner_content}{Style.RESET_ALL}'
        result = re.sub(pattern, replace_match, text, flags=re.DOTALL)
        return result

    def _limit_output_lines(self, text, max_lines=2):
        """限制输出行数为指定的最大行数"""
        lines = text.split('\n')
        if len(lines) <= max_lines:
            return text
        return '\n'.join(lines[:max_lines]) + f"\n... (已截断，共{len(lines)}行)"

    def _output(self, message):
        """统一输出方法，支持 TUI 和 CLI 模式"""
        if self.tui_output_callback:
            self.tui_output_callback(message)
        else:
            print(message)

    def _truncate_for_display(self, content, max_chars=4000, max_lines=160):
        """仅用于「展示层」的截断：过长时折叠，不影响底层存储的对话数据。"""
        if not content:
            return content
        lines = content.split('\n')
        if len(lines) > max_lines or len(content) > max_chars:
            kept = "\n".join(lines[:max_lines])
            kept = kept[:max_chars]
            hidden = len(content) - len(kept)
            note = f"\n\n… (展示已折叠，完整内容共 {len(content)} 字符 / {len(lines)} 行，已完整保存到会话)"
            return kept + note
        return content

    def _display_response(self, content, is_continue=False):
        """统一显示 AI 响应，支持 TUI 和 CLI 模式（仅展示层截断，不改存储）"""
        user_id_display = f"[用户ID: {self.user_id}]"
        # 仅展示截断：存储用的 shared_conversation_history 仍是完整内容
        content = self._truncate_for_display(content)
        response_lines = content.split('\n')
        if self.tui_output_callback:
            for i, line in enumerate(response_lines):
                if i == 0:
                    prefix = "[yellow]>[/] " if is_continue else "[cyan]>[/] "
                    line = prefix + line
                if i == len(response_lines) - 1:
                    self._output(f"{line} {user_id_display}")
                else:
                    self._output(line)
            self._output("")
        else:
            for i, line in enumerate(response_lines):
                if i == 0:
                    prefix = f"{Fore.YELLOW}{Style.RESET_ALL} " if is_continue else " "
                    line = prefix + line
                if i == len(response_lines) - 1:
                    print(f"{line} {user_id_display}")
                else:
                    print(f"{line}")
            print()

    def _display_tool_result(self, tool_name, tool_args, full_result, current_time):
        """显示工具执行结果"""
        if full_result is None:
            full_result = "无结果"

        self._output("")
        user_id_display = f"[用户ID: {self.user_id}]"
        is_error = full_result.startswith("错误:") or full_result.startswith("错误：") or full_result.startswith("工具执行错误")

        if self.tui_output_callback:
            if is_error:
                self._output(f"[red]  X 工具: {tool_name}[/]")
                self._output(f"[red]  参数: {tool_args} {user_id_display}[/]")
            else:
                self._output(f"[green]  OK 工具: {tool_name}[/]")
                self._output(f"[green]  参数: {tool_args} {user_id_display}[/]")
        else:
            if is_error:
                self._output(f"{Fore.RED}     X 工具: {tool_name}{Style.RESET_ALL}")
                self._output(f"{Fore.RED}     参数: {tool_args} {user_id_display}{Style.RESET_ALL}")
            else:
                self._output(f"{Fore.GREEN}     OK 工具: {tool_name}{Style.RESET_ALL}")
                self._output(f"{Fore.GREEN}     参数: {tool_args} {user_id_display}{Style.RESET_ALL}")

        display_result = self._limit_output_lines(full_result, max_lines=2)
        color_tag = "red" if is_error else "green"
        for line in display_result.split('\n'):
            if self.tui_output_callback:
                self._output(f"[{color_tag}]       {line}[/]")
            else:
                color = Fore.RED if is_error else Fore.GREEN
                self._output(f"{color}          {line}{Style.RESET_ALL}")

    def _typeprint(self, text, color=None, delay=0.01):
        """输出文本（已取消逐字打字机效果，改为一次性完整输出）。

        保留方法签名以兼容潜在调用方；不再逐字符 sleep，避免「流式显示」。
        """
        if color:
            print(f"{color}{text}{Style.RESET_ALL}")
        else:
            print(text)

    # ── 图片显示 ──

    def display_image_in_terminal(self, image_path, width=None):
        """在终端中显示图片"""
        try:
            if not os.path.exists(image_path):
                print(f"{Fore.RED}错误: 图片文件不存在: {image_path}{Style.RESET_ALL}")
                return False

            valid_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']
            if not os.path.splitext(image_path)[1].lower() in valid_extensions:
                print(f"{Fore.RED}错误: 不支持的图片格式。支持的格式: {', '.join(valid_extensions)}{Style.RESET_ALL}")
                return False

            try:
                from PIL import Image
                with Image.open(image_path) as img:
                    img_size = img.size
                    img_format = img.format
                    file_size = os.path.getsize(image_path)
                    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}图片预览: {os.path.basename(image_path)}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
                    print(f"{Fore.GREEN}  格式: {img_format}{Style.RESET_ALL}")
                    print(f"{Fore.GREEN}  尺寸: {img_size[0]} x {img_size[1]} 像素{Style.RESET_ALL}")
                    print(f"{Fore.GREEN}  大小: {file_size / 1024:.2f} KB{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
            except ImportError:
                print(f"\n{Fore.CYAN}图片预览: {os.path.basename(image_path)}{Style.RESET_ALL}")

            # 方法1: 使用色块显示
            try:
                from PIL import Image

                terminal_size = shutil.get_terminal_size()
                terminal_width = terminal_size.columns
                terminal_height = terminal_size.lines - 5

                if width is None:
                    width = min(250, terminal_width)

                with Image.open(image_path) as img:
                    img_width, img_height = img.size
                    pixel_width = width * 2
                    pixel_height = (terminal_height - 2) * 2
                    scale = min(pixel_width / img_width, pixel_height / img_height)
                    scale = min(scale * 1.1, 1.0)
                    new_width = max(int(img_width * scale), 80)
                    new_height = max(int(img_height * scale), 40)
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    pixels = img.load()

                    print(f"{Fore.YELLOW}正在生成色块图片 ({new_width}x{new_height} 像素)...{Style.RESET_ALL}")

                    block_chars = {
                        (False, False, False, False): ' ',
                        (True,  False, False, False): '▘',
                        (False, True,  False, False): '▝',
                        (True,  True,  False, False): '▀',
                        (False, False, True,  False): '▖',
                        (True,  False, True,  False): '▌',
                        (False, True,  True,  False): '▞',
                        (True,  True,  True,  False): '▛',
                        (False, False, False, True):  '▗',
                        (True,  False, False, True):  '▚',
                        (False, True,  False, True):  '▐',
                        (True,  True,  False, True):  '▜',
                        (False, False, True,  True):  '▄',
                        (True,  False, True,  True):  '▙',
                        (False, True,  True,  True):  '▟',
                        (True,  True,  True,  True):  '█',
                    }

                    for y in range(0, new_height, 2):
                        line = []
                        for x in range(0, new_width, 2):
                            r1, g1, b1 = pixels[x, y] if y < new_height and x < new_width else (0, 0, 0)
                            r2, g2, b2 = pixels[x + 1, y] if y < new_height and x + 1 < new_width else (0, 0, 0)
                            r3, g3, b3 = pixels[x, y + 1] if y + 1 < new_height and x < new_width else (0, 0, 0)
                            r4, g4, b4 = pixels[x + 1, y + 1] if y + 1 < new_height and x + 1 < new_width else (0, 0, 0)

                            has_tl = y < new_height and x < new_width
                            has_tr = y < new_height and x + 1 < new_width
                            has_bl = y + 1 < new_height and x < new_width
                            has_br = y + 1 < new_height and x + 1 < new_width

                            all_pixels = [(r1, g1, b1), (r2, g2, b2), (r3, g3, b3), (r4, g4, b4)]
                            avg_r = sum(p[0] for p in all_pixels) // 4
                            avg_g = sum(p[1] for p in all_pixels) // 4
                            avg_b = sum(p[2] for p in all_pixels) // 4

                            char = block_chars.get((has_tl, has_tr, has_bl, has_br), ' ')
                            fg_color = f"\033[38;2;{avg_r};{avg_g};{avg_b}m"
                            reset = "\033[0m"
                            line.append(f"{fg_color}{char}{reset}")

                        print(''.join(line))

                    print(f"{Fore.GREEN} 已使用色块显示 ({new_width}x{new_height} 像素){Style.RESET_ALL}\n")
                    return True

            except ImportError:
                print(f"{Fore.YELLOW}未安装 ascii-magic 库，尝试使用系统默认图片查看器...{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.YELLOW}ASCII 艺术显示失败: {e}，尝试使用系统默认图片查看器...{Style.RESET_ALL}")

            # 方法2: 使用系统默认图片查看器
            system = platform.system()
            if system == 'Windows':
                os.startfile(image_path)
            elif system == 'Darwin':
                subprocess.run(['open', image_path])
            else:
                subprocess.run(['xdg-open', image_path])
            print(f"{Fore.GREEN} 已在系统默认图片查看器中打开{Style.RESET_ALL}\n")
            return True

        except Exception as e:
            print(f"{Fore.RED}显示图片失败: {str(e)}{Style.RESET_ALL}")
            return False

    # ── 文件读取 ──

    def _read_file_direct(self, filename, max_lines=None):
        """直接读取文件内容, 支持指定行数"""
        try:
            if not os.path.exists(filename):
                return f"错误：文件 '{filename}' 不存在。"
            if not os.path.isfile(filename):
                return f"错误：'{filename}' 不是一个文件。"
            with open(filename, 'r', encoding='utf-8') as f:
                if max_lines is not None:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            break
                        lines.append(line.rstrip('\n'))
                    content = '\n'.join(lines)
                    info = f"(文件共{len(lines)}行)" if len(lines) < max_lines else f"(已读取前{max_lines}行)"
                    return f"文件 '{filename}' 的内容 {info}:\n{content}"
                else:
                    content = f.read()
                    MAX_CONTENT_LENGTH = 10000
                    if len(content) > MAX_CONTENT_LENGTH:
                        content = content[:10000] + f"\n... (内容已截断, 共{len(content)}字符)"
                    return f"文件 '{filename}' 的内容:\n{content}"
        except UnicodeDecodeError:
            file_size = os.path.getsize(filename)
            return f"文件 '{filename}' 是二进制文件, 大小: {file_size} 字节。无法直接读取文本内容。"
        except PermissionError as e:
            logger.error(f"权限错误，无法读取文件 '{filename}': {e}")
            return f"权限错误：无法读取文件 '{filename}'，可能需要管理员权限或文件被占用。"
        except OSError as e:
            logger.error(f"操作系统错误，无法读取文件 '{filename}': {e}")
            return f"操作系统错误：无法读取文件 '{filename}'，原因: {str(e)}"
        except Exception as e:
            logger.error(f"读取文件 '{filename}' 失败: {e}")
            return f"读取文件 '{filename}' 失败: {str(e)}"

    def _process_file_paths(self, user_input):
        """处理用户输入中的 @文件路径 语法"""
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg'}
        pattern = r'@"([^"]+)"|@([^\s]+)'
        matches = list(re.finditer(pattern, user_input))

        if not matches:
            return user_input

        result_parts = []
        last_pos = 0

        for match in matches:
            if match.start() > last_pos:
                result_parts.append(user_input[last_pos:match.start()])

            file_path = match.group(1) or match.group(2)
            if not file_path:
                continue

            file_path = os.path.normpath(file_path)

            try:
                if os.path.exists(file_path):
                    if os.path.isdir(file_path):
                        print(f"{Fore.CYAN}检测到目录: {file_path}{Style.RESET_ALL}")
                        try:
                            entries = os.listdir(file_path)
                            files = [e for e in entries if os.path.isfile(os.path.join(file_path, e))]
                            if not files:
                                result_parts.append(f"[目录: {file_path} 为空]")
                            else:
                                file_list_text = f"\n[目录: {file_path} - 共 {len(files)} 个文件]\n"
                                file_list_text += "=" * 50 + "\n"
                                for i, filename in enumerate(sorted(files), 1):
                                    full_path = os.path.join(file_path, filename)
                                    file_size = os.path.getsize(full_path)
                                    file_list_text += f"{i}. {filename} ({file_size} 字节)\n"
                                file_list_text += "=" * 50 + "\n"
                                result_parts.append(file_list_text)
                        except PermissionError:
                            result_parts.append(f"[错误: 无权限访问目录 {file_path}]")
                        except Exception as e:
                            result_parts.append(f"[错误: 无法读取目录 {file_path} - {str(e)}]")
                    else:
                        file_ext = os.path.splitext(file_path)[1].lower()
                        is_image = file_ext in image_extensions

                        if is_image:
                            print(f"{Fore.CYAN}检测到图片文件: {file_path}{Style.RESET_ALL}")
                            try:
                                self.display_image_in_terminal(file_path)
                            except Exception as e:
                                print(f"{Fore.YELLOW}图片预览失败: {e}{Style.RESET_ALL}")

                            image_plugin = None
                            for tool in self.liugin_manager.tools:
                                tool_name = tool.get('name', '').lower()
                                tool_desc = tool.get('description', '').lower()
                                if 'image' in tool_name or 'analyze' in tool_name or '图片' in tool_desc:
                                    image_plugin = tool
                                    break

                            if image_plugin:
                                try:
                                    print(f"{Fore.YELLOW}正在分析图片...{Style.RESET_ALL}")
                                    image_result = image_plugin['handler'](f"analyze {file_path}")
                                    if image_result:
                                        result_parts.append(f" {image_result}")
                                    else:
                                        result_parts.append(f" [图片: {file_path}]")
                                except Exception as e:
                                    result_parts.append(f"[错误: 图片分析失败 - {str(e)}]")
                            else:
                                result_parts.append(f"[错误: 图像分析插件未加载]")
                        else:
                            file_size = os.path.getsize(file_path)
                            if file_size > MAX_FILE_SIZE:
                                result_parts.append(f"[错误: 文件 {file_path} 超过大小限制 ({MAX_FILE_SIZE} 字节)]")
                            else:
                                try:
                                    with open(file_path, 'r', encoding='utf-8') as f:
                                        file_content = f.read()
                                    result_parts.append(f"\n[文件: {file_path}]\n{file_content}\n")
                                except UnicodeDecodeError:
                                    try:
                                        with open(file_path, 'r', encoding='gbk') as f:
                                            file_content = f.read()
                                        result_parts.append(f"\n[文件: {file_path}]\n{file_content}\n")
                                    except Exception as e:
                                        result_parts.append(f"[错误: 无法读取文件 {file_path} - {str(e)}]")
                                except Exception as e:
                                    result_parts.append(f"[错误: 无法读取文件 {file_path} - {str(e)}]")
                else:
                    result_parts.append(f"[错误: 文件 {file_path} 不存在]")

                last_pos = match.end()
            except Exception as e:
                result_parts.append(f"[错误: 处理文件路径时出错 - {str(e)}]")
                last_pos = match.end()

        if last_pos < len(user_input):
            result_parts.append(user_input[last_pos:])

        return ''.join(result_parts)

    # ── 帮助系统 ──

    def show_quick_commands(self):
        """常用命令速查表（启动时不再刷屏，改由 /help 展示）"""
        rows = [
            ('/help [插件名]', '显示帮助信息'),
            ('/quit', '退出程序'),
            ('/tui', '切换到 TUI 图形模式'),
            ('/engine list', '查看可用 AI 引擎'),
            ('/engine switch <名>', '切换 AI 引擎'),
            ('/model', '列出已配置的 OpenAI 模型'),
            ('/model <名称>', '切换当前 OpenAI 模型'),
            ('/model add', '交互式新增 OpenAI 模型'),
            ('/model rm <名称>', '删除已配置的模型'),
            ('/fc [reset]', '查看/清除 FC 能力探测缓存'),
            ('/safe', '切换安全模式 (普通→人工→无限制)'),
            ('/diff', '切换 diff 显示模式 (弹窗/主终端)'),
            ('/notify', '切换任务完成通知 (开/关)'),
            ('/scheduler 或 /remind', '管理定时任务'),
            ('/memory', '管理记忆系统 (日记/搜索/聊天记录)'),
            ('/file.read <文件> [行数]', '直接读取文件内容'),
            ('@文件路径', '自动读取文件内容并发送给 AI'),
            ('@图片路径', '自动分析图片并发送描述给 AI'),
            ('/image engines', '查看图像识别引擎'),
            ('/chat save|list|open', '保存/查看/加载聊天记录'),
            ('/resume', '列出历史会话 (自动持久化)'),
            ('/resume <序号或ID>', '恢复指定会话继续对话'),
            ('/resume new', '开始一个全新的会话'),
            ('/plan [任务]', '进入 PLAN 模式：只读调研并生成实施计划'),
            ('/build', '批准并Plan模式生成的计划，开始执行'),
            ('/remote', '查看远程连接帮助'),
            ('/plugin', '管理插件市场 (安装/卸载/搜索)'),
            ('/protect', '查看进程保护状态'),
        ]
        width = max(len(cmd) for cmd, _ in rows)
        print(f"{Fore.GREEN}常用命令:{Style.RESET_ALL}")
        for cmd, desc in rows:
            print(f"  {Fore.WHITE}{cmd.ljust(width)}{Style.RESET_ALL}  {desc}")
        print()
        print(f"{Fore.GREEN}启动参数:{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}{'--verbose / -v'.ljust(width)}{Style.RESET_ALL}  打印引擎/插件/技能的逐条加载明细")
        print(f"  {Fore.WHITE}{'--logo'.ljust(width)}{Style.RESET_ALL}  播放完整开机动画")
        print()

    def show_help(self):
        """显示帮助信息"""
        self.show_quick_commands()
        help_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "HELP.md")
        if os.path.exists(help_file_path):
            try:
                with open(help_file_path, 'r', encoding='utf-8') as f:
                    help_content = f.read()
                print(help_content)
            except Exception as e:
                print(f"读取帮助文件失败: {e}")
                self._show_basic_help()
        else:
            self._show_basic_help()

    def show_liugin_help(self, liugin_name):
        """显示特定插件的帮助信息"""
        if liugin_name in self.engines:
            engine = self.engines[liugin_name]
            print(f"{Fore.GREEN}AI引擎 '{liugin_name}' 的帮助信息:{Style.RESET_ALL}")
            engine_name = getattr(engine, 'name', liugin_name)
            print(f"{Fore.GREEN}引擎名称: {engine_name}{Style.RESET_ALL}")
            if hasattr(engine, 'get_help_info'):
                help_info = engine.get_help_info()
                if isinstance(help_info, str):
                    print(f"{Fore.GREEN}帮助信息:{Style.RESET_ALL}")
                    print(help_info)
                elif isinstance(help_info, dict):
                    for key, value in help_info.items():
                        print(f"{Fore.GREEN}{key}: {value}{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}可用命令:{Style.RESET_ALL}")
                print(f"  /engine.{liugin_name} <命令> - 执行{liugin_name}引擎的特定命令")
            return

        for tool in self.liugin_manager.tools:
            if tool.get('name') == liugin_name:
                print(f"{Fore.GREEN}插件 '{liugin_name}' 的帮助信息:{Style.RESET_ALL}")
                description = tool.get('description', '无描述')
                print(f"{Fore.GREEN}描述: {description}{Style.RESET_ALL}")
                if 'usage' in tool:
                    print(f"{Fore.GREEN}用法:{Style.RESET_ALL}")
                    print(f"  {tool['usage']}")
                if 'keywords' in tool:
                    keywords = tool['keywords']
                    if isinstance(keywords, list):
                        print(f"{Fore.GREEN}关键词: {', '.join(keywords)}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.GREEN}关键词: {keywords}{Style.RESET_ALL}")
                return

        print(f"{Fore.RED}未找到插件或引擎 '{liugin_name}'{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}可用AI引擎:{Style.RESET_ALL}")
        for engine_name in self.engines.keys():
            print(f"{Fore.YELLOW}  - {engine_name}{Style.RESET_ALL}")
        if self.liugin_manager.tools:
            print(f"{Fore.YELLOW}可用插件:{Style.RESET_ALL}")
            for tool in self.liugin_manager.tools:
                tool_name = tool.get('name', '未知插件')
                tool_description = tool.get('description', '无描述')
                print(f"{Fore.YELLOW}  - {tool_name}: {tool_description}{Style.RESET_ALL}")

    def _show_basic_help(self):
        """显示基本帮助信息"""
        help_text = """
小狸 Pro-CLI 帮助信息
==================
基本命令:
  /help              - 显示此帮助信息
  /help <插件名>      - 显示特定插件的帮助信息
  /quit              - 退出程序
  /tui               - 切换到 TUI 模式
  /model <引擎名>     - 切换AI引擎 (当前支持: """
        available_engines = list(self.engines.keys())
        help_text += ", ".join(available_engines) + ")"
        help_text += r"""
文件操作命令:
  /file.read <文件名> [行数] - 直接读取文件内容
  @文件路径                 - 发送时自动读取文件内容并拼接
图像分析命令:
  /image analyze <图片路径>  - 详细分析图片
  /image ocr <图片路径>     - OCR文字识别
  /image quick <图片路径>   - 快速描述
引擎管理命令:
""" + self._get_engine_commands_help() + """
  /engine.<命令>     - 执行引擎特定命令
聊天记录命令:
  /chat save <名称>   - 保存当前聊天记录
  /chat list         - 查看所有已保存的聊天记录
  /chat open <名称>   - 加载聊天记录
插件工具:
"""
        if self.liugin_manager.tools:
            for tool in self.liugin_manager.tools:
                tool_name = tool.get('name', '未知工具')
                tool_description = tool.get('description', '无描述')
                help_text += f"  {tool_name}: {tool_description}\n"
                if 'usage' in tool:
                    help_text += f"    用法: {tool['usage']}\n"
        else:
            help_text += "  当前没有可用的工具插件\n"
        print(help_text)

    def _read_about_file(self):
        """读取并返回about.txt文件的内容，逐字显示"""
        try:
            project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            about_file_path = os.path.join(project_dir, "about.txt")
            if not os.path.exists(about_file_path):
                return "错误：about.txt 文件不存在。"
            with open(about_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            for char in content:
                sys.stdout.write(char)
                sys.stdout.flush()
                if char in ['，', '。', '！', '？', ',', '.', '!', '?', '\n', '\r']:
                    time.sleep(0.1)
                else:
                    time.sleep(VIDEO_FRAME_DELAY)
            print()
            return ""
        except UnicodeDecodeError:
            return "错误：about.txt 文件编码格式不支持。"
        except Exception as e:
            return f"读取 about.txt 文件时发生错误: {str(e)}"

    # ── 视频播放 ──

    def start_video_player(self):
        """启动视频播放窗口"""
        import threading
        video_thread = threading.Thread(target=self._show_video_window, daemon=True)
        video_thread.start()

    def _show_video_window(self):
        """显示视频播放窗口"""
        try:
            import tkinter as tk
            import cv2
            import numpy as np

            root = tk.Tk()
            root.overrideredirect(True)
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            video_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Video_1765688252672.mp4")
            if not os.path.exists(video_path):
                error_width, error_height = 400, 100
                x = (screen_width // 2) - (error_width // 2)
                y = (screen_height // 2) - (error_height // 2)
                root.geometry(f"{error_width}x{error_height}+{x}+{y}")
                canvas = tk.Canvas(root, width=error_width, height=error_height)
                canvas.pack(fill=tk.BOTH, expand=True)
                canvas.create_text(error_width//2, error_height//2, text=f"视频文件不存在:\n{video_path}", fill="red", font=("Arial", 12))
                root.mainloop()
                return

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                error_width, error_height = 400, 100
                x = (screen_width // 2) - (error_width // 2)
                y = (screen_height // 2) - (error_height // 2)
                root.geometry(f"{error_width}x{error_height}+{x}+{y}")
                canvas = tk.Canvas(root, width=error_width, height=error_height)
                canvas.pack(fill=tk.BOTH, expand=True)
                canvas.create_text(error_width//2, error_height//2, text="无法打开视频文件", fill="red", font=("Arial", 12))
                root.mainloop()
                return

            video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            max_width = int(screen_width * 0.4)
            max_height = int(screen_height * 0.4)
            scale = min(max_width / video_width, max_height / video_height)
            window_width = int(video_width * scale)
            window_height = int(video_height * scale)
            x = (screen_width // 2) - (window_width // 2)
            y = (screen_height // 2) - (window_height // 2)
            root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            root.wm_attributes("-transparentcolor", "black")
            canvas = tk.Canvas(root, width=window_width, height=window_height, highlightthickness=0, bg='black')
            canvas.pack(fill=tk.BOTH, expand=True)

            def update_frame():
                nonlocal cap
                try:
                    ret, frame = cap.read()
                    if ret:
                        frame = cv2.resize(frame, (window_width, window_height), interpolation=cv2.INTER_CUBIC)
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        lower_black = np.array([0, 0, 0])
                        upper_black = np.array([30, 30, 30])
                        mask = cv2.inRange(frame_rgb, lower_black, upper_black)
                        frame_rgb[mask > 0] = [0, 0, 0]
                        img = tk.PhotoImage(data=cv2.imencode('.ppm', frame_rgb)[1].tobytes())
                        canvas.delete("all")
                        canvas.create_image(0, 0, anchor=tk.NW, image=img)
                        canvas.image = img
                        delay = int(1000 / fps) if fps > 0 else 33
                        root.after(delay, update_frame)
                    else:
                        cap.release()
                        self._fade_out(root)
                except tk.TclError:
                    cap.release()
                    try:
                        root.destroy()
                    except Exception:
                        pass
                except Exception as e:
                    print(f"更新视频帧时出错: {e}")
                    cap.release()
                    try:
                        root.destroy()
                    except Exception:
                        pass

            update_frame()
            root.mainloop()
        except Exception as e:
            print(f"播放视频时出错: {e}")
            try:
                if 'cap' in locals() and cap.isOpened():
                    cap.release()
            except Exception:
                pass
            try:
                if 'root' in locals():
                    root.after(100, root.destroy)
            except Exception:
                pass

    def _fade_out(self, root, duration=1000):
        """实现窗口渐隐效果"""
        try:
            alpha = float(root.wm_attributes("-alpha"))
        except Exception:
            alpha = 1.0
        alpha -= 0.1
        if alpha <= 0:
            try:
                root.destroy()
            except Exception:
                pass
        else:
            root.wm_attributes("-alpha", alpha)
            root.after(50, self._fade_out, root, duration)
