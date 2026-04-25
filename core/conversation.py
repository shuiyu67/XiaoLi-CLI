"""
对话处理模块 - 核心对话循环和工具调用
"""
import json
import re
import time
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import Fore, Style

logger = logging.getLogger(__name__)


class ConversationManager:
    """对话管理器 - 处理用户输入、AI 响应、工具调用循环"""

    def __init__(self, cli):
        self.cli = cli
        self.history = []
        self.max_history = 999999

    def process(self, user_input: str):
        """处理完整的对话循环"""
        self.history.append({"role": "user", "content": user_input})

        tool_prompts = self._get_tool_prompts()
        loop_count = 0
        current_input = user_input
        max_loops = 20

        while loop_count < max_loops:
            response = self._generate_with_animation(current_input, tool_prompts)
            processed = self._process_thinking(response)
            processed = self._process_code_blocks(processed)

            try:
                text_content, json_data = self._parse_response(processed)

                if json_data:
                    if text_content:
                        self._add_and_display(text_content)

                    if isinstance(json_data, dict):
                        result = self._handle_dict(json_data, text_content, processed)
                        if result == "break":
                            break
                        elif result == "continue":
                            loop_count += 1
                            continue
                    elif isinstance(json_data, list):
                        result = self._handle_list(json_data, text_content, processed)
                        if result == "break":
                            break
                        elif result == "continue":
                            loop_count += 1
                            continue
                else:
                    display = text_content if text_content else processed
                    self._add_and_display(display)
                    break

            except json.JSONDecodeError:
                text_content, json_data = self._parse_response(processed)
                if json_data:
                    # Re-process with parsed data
                    pass
                else:
                    self._add_and_display(processed)
                break

        if loop_count >= max_loops:
            self.cli.display.output(f"AI 已达到最大循环次数 ({max_loops})，已停止")

    def _handle_dict(self, data, text_content, processed):
        """处理 dict 类型的 JSON 数据"""
        if data.get('action') == 'use_tool':
            self.cli._execute_single_tool(data)
            return "break"

        if data.get('action') == 'continue':
            content = data.get('content', '')
            if content:
                self._add_and_display(content)
            return "continue"

        if data.get('continue') or data.get('need_continue') or data.get('think_more'):
            msg = data.get('message', '')
            if msg:
                self.history.append({"role": "assistant", "content": msg})
                self.cli.display.response(msg, is_continue=True)
            return "continue"

        msg = data.get('message', '')
        if msg:
            self._add_and_display(msg)
            return "break"

        if text_content:
            self._add_and_display(text_content)
        else:
            self._add_and_display(processed)
        return "break"

    def _handle_list(self, data_list, text_content, processed):
        """处理 list 类型的 JSON 数据"""
        tool_calls = [item for item in data_list
                     if isinstance(item, dict) and item.get('action') == 'use_tool']

        if tool_calls:
            self.cli._execute_concurrent_tools(tool_calls)
            return "break"

        continue_items = [item for item in data_list
                         if isinstance(item, dict) and
                         (item.get('continue') or item.get('need_continue') or item.get('think_more'))]

        if continue_items:
            msg = continue_items[0].get('message', '')
            if msg:
                self.history.append({"role": "assistant", "content": msg})
                self.cli.display.response(msg, is_continue=True)
            return "continue"

        if text_content:
            self._add_and_display(text_content)
        else:
            self._add_and_display(processed)
        return "break"

    def _add_and_display(self, content):
        """添加到历史并显示"""
        self.history.append({"role": "assistant", "content": content})
        self.cli.display.response(content)

    def _generate_with_animation(self, user_input, tool_prompts=None):
        """生成 AI 响应（带动画）"""
        system_prompt = self._build_system_prompt(tool_prompts)

        if not self.cli.engine_manager.current_engine:
            return "错误: 当前没有可用的AI引擎"

        # TUI 模式：直接生成
        if self.cli.display.tui_callback:
            response = self.cli.engine_manager.generate_response(user_input, system_prompt)
            if response:
                self.history.append({"role": "assistant", "content": response})
            return response

        # CLI 模式：带动画
        stop_event = threading.Event()
        esc_event = threading.Event()

        # 加载等待句子
        sentences = self._load_love_sentences()

        anim_thread = threading.Thread(
            target=self.cli.display.thinking_animation,
            args=(sentences, stop_event, esc_event), daemon=True)
        anim_thread.start()

        try:
            response = self.cli.engine_manager.generate_response(user_input, system_prompt)
            if response:
                self.cli.display.typeprint(response, Fore.CYAN)
                self.history.append({"role": "assistant", "content": response})
            return response
        finally:
            stop_event.set()
            anim_thread.join()

    def _build_system_prompt(self, tool_prompts=None):
        """构建系统提示词"""
        base = ("你叫小狸，是一个强大的智能编程助手。你具备精准的代码编辑能力、"
                "完整的 Git 工作流支持、以及跨文件代码搜索和理解能力。"
                "你可以帮助用户编写、修改、调试代码，管理版本控制，理解复杂代码库。")

        tool_section = ""
        if tool_prompts:
            tool_section = f"\n\n{tool_prompts}"

        call_format = """
【工具调用格式】
当需要执行操作时，在回复中包含 JSON 指令：

1. 纯 JSON: {"action": "use_tool", "tool": "工具名", "args": "参数"}
2. 文本+JSON: 好的，我来修改这个文件。{"action": "use_tool", "tool": "code_editor", "args": "edit file.py old_code <<<>>> new_code"}

【核心工具】
- code_editor: 精准代码编辑（edit/search/diff/insert/create/write）
- code_search: 代码搜索与理解（find/regex/symbols/imports/structure）
- git_tools: Git 操作（status/diff/log/add/commit/branch）
- cmd_executor: 执行 shell 命令
- file_manager: 文件管理

【编码工作流】
1. 先用 code_search 了解代码结构
2. 用 code_editor.read_range 查看相关代码
3. 用 code_editor.edit 精准修改
4. 用 git_tools 提交变更

【注意事项】
- code_editor.edit 的格式: old_text <<<>>> new_text（用 <<<>>> 分隔）
- args 必须是字符串
- 可以一次返回多个 JSON 指令顺序执行
- 使用 continue 补充回答: {"action": "continue", "content": "补充内容"}"""

        return base + tool_section + call_format

    def _process_thinking(self, response):
        """处理深度思考标记"""
        # <think/> 格式
        if '<think/>' in response:
            parts = response.split('<think/>', 1)
            if len(parts) >= 2:
                thinking = parts[0].strip()
                reply = parts[1].strip()
                if thinking:
                    print(f"{Fore.LIGHTBLACK_EX}[思考: {thinking[:200]}...]{Style.RESET_ALL}" if len(thinking) > 200 else f"{Fore.LIGHTBLACK_EX}[思考: {thinking}]{Style.RESET_ALL}")
                return reply if reply else ""

        # <thinking>...</thinking> 格式
        engine = self.cli.engine_manager.current_engine
        if engine:
            start = getattr(engine, 'thinking_start_marker', None)
            end = getattr(engine, 'thinking_end_marker', None)
            if start and end and start in response and end in response:
                parts = response.split(start, 1)
                if len(parts) > 1 and end in parts[1]:
                    thinking, reply = parts[1].split(end, 1)
                    if thinking.strip():
                        print(f"{Fore.LIGHTBLACK_EX}[思考: {thinking.strip()[:200]}]{Style.RESET_ALL}")
                    return reply.strip()

        return response

    def _process_code_blocks(self, text):
        """处理代码块标记"""
        pattern = r'(""".*?""")'
        def replace(m):
            inner = m.group(1)[3:-3]
            return f'{Fore.RED}{inner}{Style.RESET_ALL}'
        return re.sub(pattern, replace, text, flags=re.DOTALL)

    def _parse_response(self, response):
        """解析混合响应（文本+JSON）"""
        response = response.strip()

        # 直接 JSON
        try:
            parsed = json.loads(response)
            if isinstance(parsed, (dict, list)):
                return "", parsed
        except json.JSONDecodeError:
            pass

        # 代码块中的 JSON
        pattern = r"```(?:json)?\s*({.*?})\s*```"
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            try:
                data = json.loads(matches[-1])
                if isinstance(data, (dict, list)):
                    text = re.sub(pattern, "", response, flags=re.DOTALL).strip()
                    return text, data
            except json.JSONDecodeError:
                pass

        # 内联 JSON
        markers = ['{"action": "use_tool"', '{"action": "continue"',
                   '{"action":"use_tool"', '{"action":"continue"']
        for marker in markers:
            idx = response.find(marker)
            if idx != -1:
                brace_count = 0
                for i in range(idx, len(response)):
                    if response[i] == '{':
                        brace_count += 1
                    elif response[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            try:
                                data = json.loads(response[idx:i+1])
                                if isinstance(data, dict) and data.get('action') in ['use_tool', 'continue']:
                                    return response[:idx].strip(), data
                            except json.JSONDecodeError:
                                pass
                            break

        return response, None

    def _get_tool_prompts(self):
        """获取工具提示词"""
        if not self.cli.tool_manager or not self.cli.tool_manager.tools:
            return "当前没有可用的工具"

        lines = ["可用工具列表：\n"]
        for tool in self.cli.tool_manager.tools:
            name = tool.get('name', '')
            desc = tool.get('description', '')
            lines.append(f"- {name}: {desc}")

        return '\n'.join(lines)

    def _load_love_sentences(self):
        """加载等待动画句子"""
        import os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "love.txt")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return [l.strip() for l in f.readlines() if l.strip()]
            except:
                pass
        return ["AI正在思考中...", "请稍等片刻...", "正在处理您的请求..."]
