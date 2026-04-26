import os
import sys
import json
import re
import time
import shutil
import threading
import random
from colorama import Fore, Style

from .constants import TEXTUAL_AVAILABLE, LOVE_FILE_PATH, DEFAULT_MAX_HISTORY
from .config import get_system_config, logger
from .cli_base import BaseAICLI
from .safety import get_safety, MODE_UNRESTRICTED, MODE_NORMAL, MODE_MANUAL
from .cli_clawli import ClawliMixin
from .cli_tools import ToolMixin
from .cli_code_exec import CodeExecMixin
from .cli_display import DisplayMixin
from .cli_history import HistoryMixin
from .notification import notify_task_complete, get_notification_manager


class AICLI(BaseAICLI, ClawliMixin, ToolMixin, CodeExecMixin, DisplayMixin, HistoryMixin):
    """AI CLI主程序 - 组合所有 Mixin"""

    # ── 深度思考处理 ──

    def process_thinking_response(self, response):
        """处理深度思考AI返回的内容, 分离思考和回复内容"""
        try:
            response_data = json.loads(response)
            if isinstance(response_data, dict) and response_data.get('action') == 'use_tool':
                return response
            if isinstance(response_data, dict):
                if 'answer' in response_data:
                    extracted_content = response_data['answer']
                elif 'response' in response_data:
                    extracted_content = response_data['response']
                elif 'content' in response_data:
                    extracted_content = response_data['content']
                elif 'text' in response_data:
                    extracted_content = response_data['text']
                else:
                    return json.dumps(response_data, ensure_ascii=False, indent=2)
                return self._process_content_with_thinking(extracted_content)
        except json.JSONDecodeError:
            return self._process_content_with_thinking(response)

    def _process_content_with_thinking(self, content):
        """处理包含思考标记的内容"""
        thinking_start_marker = getattr(self.current_engine, 'thinking_start_marker', None) if self.current_engine else None
        thinking_end_marker = getattr(self.current_engine, 'thinking_end_marker', None) if self.current_engine else None

        if '<think/>' in content:
            parts = content.split('<think/>')
            if len(parts) >= 2:
                thinking_content = parts[0].strip()
                reply_content = parts[1].strip()
                if thinking_content:
                    print(f"{Fore.LIGHTBLACK_EX}{Style.DIM}[思考: {thinking_content}]{Style.RESET_ALL}")
                return reply_content if reply_content else ""

        if thinking_start_marker and thinking_end_marker and thinking_start_marker in content and thinking_end_marker in content:
            parts = content.split(thinking_start_marker)
            if len(parts) > 1:
                remaining = parts[1]
                if thinking_end_marker in remaining:
                    thinking_part, reply_part = remaining.split(thinking_end_marker, 1)
                    thinking_content = thinking_part.strip()
                    reply_content = reply_part.strip()
                    if thinking_content:
                        print(f"{Fore.LIGHTBLACK_EX}{Style.DIM}[思考: {thinking_content}]{Style.RESET_ALL}")
                    return reply_content if reply_content else ""

        return content

    # ── 系统提示构建 ──

    def _build_system_prompt(self, liugin_prompts=None):
        """构建系统提示词 - 增强版，支持编程任务"""
        base_prompt = """你叫小狸，是一个强大的智能编程助手。你具备以下核心能力：

1. **精准代码编辑** - 使用 code_editor 工具进行搜索替换、多文件批量编辑
2. **代码搜索与理解** - 使用 code_search 工具跨文件搜索、提取符号、分析依赖
3. **Git 版本控制** - 使用 git_tools 工具管理代码版本
4. **Shell 命令执行** - 使用 cmd_executor 执行系统命令
5. **文件管理** - 使用 file_manager 管理文件和目录
6. **浏览器自动化** - 使用 browser_auto 工具操控浏览器
7. **子 Agent 协作** - 使用 sub_agent 创建子 Agent 并行处理任务
8. **工程化自动化** - 使用 auto_engineer 进行 lint/test/build
9. **网络工具** - 使用 network_tools 进行 HTTP 请求和网络诊断
10. **AI 联网搜索** - 使用 ai_search 搜索实时信息

你在说话时可以适当加上'nyan'来表现可爱性格，但不要过度使用。"""

        has_tool_search = any(t.get('name') == 'tool_search' for t in self.liugin_manager.tools)

        tool_search_rule = ""
        if has_tool_search:
            tool_search_rule = """【⚠️ 强制工具查询规则 — 必须遵守】
在调用任何工具之前，你必须先使用 tool_search 查询该工具的详细用法、参数格式和示例。
这是硬性要求，没有例外。即使你认为自己知道工具的用法，也必须先查询确认。

【⚠️ 工具调用格式 — 必须使用 JSON】
所有工具都必须通过 JSON 指令调用，格式如下：
{{"action": "use_tool", "tool": "工具名", "args": "操作 参数"}}

禁止直接写 "工具名 操作 参数"，必须包在 JSON 里。
例如：
  ✅ 正确: {{"action": "use_tool", "tool": "code_editor", "args": "find . keyword *.py"}}
  ❌ 错误: code_editor find . keyword *.py
  ❌ 错误: code_editor("find . keyword *.py")

执行流程：
第一步：用 tool_search 查询工具用法
{{"action": "use_tool", "tool": "tool_search", "args": "你要用的工具名"}}
第二步：阅读 tool_search 返回的详细说明（包括参数格式、操作列表、示例）
第三步：根据返回的说明，用 JSON 格式正确调用工具

为什么要这样做：
- 工具的参数格式可能已更新，你的记忆可能过时
- 先查询可以避免参数格式错误导致的调用失败
- 确保你使用的是最优的操作和参数组合
- 减少因格式不对而反复重试的浪费

示例流程（修改代码）：
用户: "帮我修复 src/app.py 第 10 行的 bug"
你的思考过程:
1. 需要先查看代码 → 先查 code_editor 怎么读取文件
2. {{"action": "use_tool", "tool": "tool_search", "args": "code_editor"}} → 发现 read_range 操作
3. {{"action": "use_tool", "tool": "code_editor", "args": "read_range src/app.py 5 15"}} → 拿到代码
4. 需要修改代码 → 已经在第一步查过 code_editor，知道 edit 格式
5. {{"action": "use_tool", "tool": "code_editor", "args": "edit src/app.py
旧代码
<<<>>>
新代码"}}

示例流程（Git 操作）：
用户: "帮我提交代码"
你的思考过程:
1. 需要 git 操作 → 先查 git_tools 怎么用
2. {{"action": "use_tool", "tool": "tool_search", "args": "git_tools"}} → 发现 smart-commit 操作
3. {{"action": "use_tool", "tool": "git_tools", "args": "smart-commit"}} → 自动提交"""

        if liugin_prompts:
            prompt = f"""{base_prompt}

{liugin_prompts}

{tool_search_rule}

【工具调用格式】
在回复中包含 JSON 指令来执行操作：

1. 纯 JSON: {{"action": "use_tool", "tool": "code_editor", "args": "edit file.py old <<<>>> new"}}
2. 文本+JSON: 好的，我来修改。{{"action": "use_tool", "tool": "code_editor", "args": "edit file.py old <<<>>> new"}}

【编程工作流 — 每一步都必须先查询工具】
1. 理解需求 → 先 tool_search "code_editor"，再用 structure 查看项目结构
2. 定位代码 → 已查询过，直接用 find 或 regex 搜索
3. 查看上下文 → 用 read_range 查看相关代码
4. 精准修改 → 用 edit 替换代码（old <<<>>> new 分隔）
5. 验证变更 → 先 tool_search "git_tools"，再用 diff 查看变更
6. 提交代码 → 已查询过，用 commit 提交

【code_editor 编辑格式】
edit 操作使用 <<<>>> 分隔旧代码和新代码：
{{"action": "use_tool", "tool": "code_editor", "args": "edit path/to/file.py
def old_function():
    pass
<<<>>>
def new_function():
    return True"}}

【批量编辑】
multi 操作支持一次修改多处：
{{"action": "use_tool", "tool": "code_editor", "args": "multi path/to/file.py [{{\\"old\\": \\"old1\\", \\"new\\": \\"new1\\"}}, {{\\"old\\": \\"old2\\", \\"new\\": \\"new2\\"}}]"}}

【搜索代码】
- 关键词搜索: {{"action": "use_tool", "tool": "code_search", "args": "find . keyword *.py"}}
- 正则搜索: {{"action": "use_tool", "tool": "code_search", "args": "regex . def\\\\s+\\\\w+ *.py"}}
- 查看结构: {{"action": "use_tool", "tool": "code_search", "args": "structure ."}}
- 查找调用: {{"action": "use_tool", "tool": "code_search", "args": "callers . function_name"}}

【Git 操作】
- 查看状态: {{"action": "use_tool", "tool": "git_tools", "args": "status"}}
- 查看变更: {{"action": "use_tool", "tool": "git_tools", "args": "diff"}}
- 提交代码: {{"action": "use_tool", "tool": "git_tools", "args": "commit 描述信息"}}
- 查看历史: {{"action": "use_tool", "tool": "git_tools", "args": "log --oneline 10"}}

【重要提醒】
- 调用任何不熟悉的工具前，必须先 tool_search 查询
- code_editor.edit 的 old_text 必须与文件中的内容完全匹配（包括缩进）
- 如果 edit 失败，先用 read_range 查看实际内容再重试
- args 必须是字符串
- 可以一次返回多个 JSON 指令
- 使用 continue 补充回答: {{"action": "continue", "content": "补充内容"}}"""
        else:
            prompt = f"""{base_prompt}

{tool_search_rule}

【工具调用格式】
{{"action": "use_tool", "tool": "工具名", "args": "参数"}}

【⚠️ 核心规则：调用任何工具前必须先查询】
1. 先调用 tool_search 查询工具用法
2. 阅读返回的参数说明和示例
3. 再根据说明正确调用工具

【核心工具】
- tool_search: 查询任何工具的用法（必须先调用这个）
- code_editor: edit/search/diff/insert/create/write/read_range
- code_search: find/regex/symbols/imports/structure/stats
- git_tools: status/diff/log/add/commit/branch
- cmd_executor: 执行 shell 命令
- file_manager: 文件管理

【code_editor.edit 格式】
{{"action": "use_tool", "tool": "code_editor", "args": "edit 文件路径
旧代码内容
<<<>>>
新代码内容"}}

【continue 格式】
{{"action": "continue", "content": "要补充的内容"}}"""

        # ── 注入持久化记忆上下文 ──
        if hasattr(self, 'memory_manager') and self.memory_manager:
            try:
                memory_ctx = self.memory_manager.build_memory_context()
                if memory_ctx:
                    prompt += memory_ctx
            except Exception:
                pass

        return prompt

    # ── JSON 解析 ──

    def _clean_json_response(self, response):
        """清理AI响应中的Markdown代码块标记"""
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        return response.strip()

    def get_liugin_usage_prompts(self):
        """获取可用工具提示词"""
        if not self.liugin_manager.tools:
            return "当前没有可用的工具."

        prompts = []
        prompts.append("可用的工具列表：\n")

        plugins = []
        skills = []
        for tool in self.liugin_manager.tools:
            protocol = tool.get('protocol', 'liugin')
            if protocol == 'skill':
                skills.append(tool)
            else:
                plugins.append(tool)

        if plugins:
            prompts.append("## 内置工具（使用 tool_search 查询详细用法）：")
            for tool in plugins:
                tool_name = tool.get('name', '')
                tool_desc = tool.get('description', '')
                prompts.append(f"- {tool_name}: {tool_desc}")

        if skills:
            prompts.append("\n## 扩展技能（已加载详细指令）：")
            for tool in skills:
                tool_name = tool.get('name', '')
                tool_desc = tool.get('description', '')
                prompts.append(f"\n### {tool_name}")
                prompts.append(f"描述: {tool_desc}")
                instance = tool.get('instance')
                if instance:
                    instructions = getattr(instance, 'instructions', '')
                    if instructions:
                        if len(instructions) > 2000:
                            instructions = instructions[:2000] + "\n...(内容已截断)"
                        prompts.append(f"\n{instructions}")

        if self.is_clawli_mode:
            prompts.append("\n## Clawli 远程模式专属工具：")
            prompts.append("""
### send_image - 发送图片到手机端
当用户请求发送图片到手机时，使用此工具：

```json
{
    "action": "use_tool",
    "tool": "send_image",
    "args": {
        "image_path": "图片文件的绝对路径",
        "caption": "图片说明文字（可选）"
    }
}
```

支持的图片格式：JPG、PNG、GIF、BMP、WEBP
""")

        return "\n".join(prompts)

    def _parse_mixed_response(self, response):
        """
        解析混合响应，处理同时包含文本和JSON指令的内容
        返回格式: (text_content, json_data)
        """
        response = response.strip()

        # 方法0: 处理 <tool_call>... 格式
        if response.startswith("<tool_call>"):
            json_str = response[11:]
            json_str = "{" + json_str
            try:
                parsed = json.loads(json_str)
                if isinstance(parsed, dict):
                    return "", parsed
            except json.JSONDecodeError:
                pass

        # 方法1: 直接解析为纯JSON
        try:
            parsed = json.loads(response)
            if isinstance(parsed, (list, dict)):
                return "", parsed
        except json.JSONDecodeError:
            pass

        # 方法2: 修复JSON中的控制字符问题
        try:
            def fix_json_string(match):
                content = match.group(1)
                content = content.replace('\\', '\\\\')
                content = content.replace('\n', '\\n')
                content = content.replace('\r', '\\r')
                content = content.replace('\t', '\\t')
                content = content.replace('"', '\\"')
                return f'"{content}"'
            fixed_response = re.sub(r'"([^"]*(?:\n[^"]*)*)"', fix_json_string, response, flags=re.DOTALL)
            parsed = json.loads(fixed_response)
            if isinstance(parsed, (list, dict)):
                return "", parsed
        except:
            pass

        # 方法3: 查找代码块中的JSON
        json_pattern = r"```(?:json)?\s*({.*?})\s*```"
        matches = re.findall(json_pattern, response, re.DOTALL)
        if matches:
            try:
                json_data = json.loads(matches[-1])
                if isinstance(json_data, (dict, list)):
                    text_content = re.sub(json_pattern, "", response, flags=re.DOTALL).strip()
                    text_content = re.sub(r"\n\s*\n", "\n\n", text_content).strip()
                    return text_content, json_data
            except json.JSONDecodeError:
                pass

        # 方法4: 查找每行独立的JSON对象
        lines_resp = response.split("\n")
        json_objects = []
        text_lines = []
        for line in lines_resp:
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    parsed = json.loads(line)
                    if isinstance(parsed, dict):
                        json_objects.append(parsed)
                        continue
                except json.JSONDecodeError:
                    pass
            text_lines.append(line)

        if json_objects:
            text_content = "\n".join(text_lines).strip()
            if len(json_objects) == 1:
                return text_content, json_objects[0]
            else:
                return text_content, json_objects

        # 方法5: 查找内联的JSON对象
        json_start_markers = [
            '{"action": "use_tool"', '{"action": "continue"',
            '{"action":"use_tool"', '{"action":"continue"',
            '{ "action": "use_tool"', '{ "action": "continue"',
            '{ "action":"use_tool"', '{ "action":"continue"'
        ]
        for marker in json_start_markers:
            json_start = response.find(marker)
            if json_start != -1:
                brace_count = 0
                in_json = False
                for i in range(json_start, len(response)):
                    char = response[i]
                    if char == '{':
                        if not in_json:
                            in_json = True
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if in_json and brace_count == 0:
                            json_str = response[json_start:i+1]
                            try:
                                json_data = json.loads(json_str)
                                if isinstance(json_data, dict) and json_data.get('action') in ['use_tool', 'continue']:
                                    text_content = response[:json_start].strip()
                                    return text_content, json_data
                            except json.JSONDecodeError:
                                pass
                            break

        # 方法6: 通用JSON对象查找
        potential_jsons = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
        for json_str in potential_jsons:
            try:
                json_data = json.loads(json_str)
                if isinstance(json_data, dict) and json_data.get('action') in ['use_tool', 'continue']:
                    json_start = response.find(json_str)
                    text_content = response[:json_start].strip()
                    return text_content, json_data
            except json.JSONDecodeError:
                continue

        # 方法7: 批量JSON
        try:
            cleaned = response.strip()
            for action in ['use_tool', 'continue']:
                last_brace_pos = cleaned.rfind(f'{{"action": "{action}"')
                if last_brace_pos == -1:
                    last_brace_pos = cleaned.rfind(f'{{"action":"{action}"')
                if last_brace_pos != -1:
                    json_part = cleaned[last_brace_pos:]
                    if json_part.startswith('['):
                        parsed = json.loads(json_part)
                        if isinstance(parsed, list):
                            text_content = cleaned[:last_brace_pos].strip()
                            return text_content, parsed
                    else:
                        parsed = json.loads(json_part)
                        if isinstance(parsed, dict):
                            text_content = cleaned[:last_brace_pos].strip()
                            return text_content, parsed
        except:
            pass

        return response, None

    # ── 对话处理 ──

    def process_conversation(self, user_input):
        """处理完整的对话循环, 支持工具调用循环和AI继续操作循环"""
        self.shared_conversation_history.append({
            "role": "user",
            "content": user_input
        })
        liugin_prompts = self.get_liugin_usage_prompts()
        loop_count = 0
        current_input = user_input
        max_loops = 20

        while loop_count < max_loops:
            response = self._generate_response_with_animation(current_input, liugin_prompts=liugin_prompts)
            processed_response = self.process_thinking_response(response)
            processed_response = self._process_code_blocks(processed_response)

            try:
                text_content, json_data = self._parse_mixed_response(processed_response)

                if json_data:
                    if text_content:
                        text_content = self._process_code_blocks(text_content)
                        self.shared_conversation_history.append({
                            "role": "assistant",
                            "content": text_content
                        })
                        self._display_response(text_content)

                    if isinstance(json_data, dict):
                        response_data = json_data

                        if response_data.get('action') == 'use_tool':
                            canceled = self._execute_single_tool(response_data)
                            if canceled:
                                break
                            break

                        if (response_data.get('continue') is True or
                              response_data.get('need_continue') is True or
                              response_data.get('think_more') is True):
                            continue_message = response_data.get('message', '')
                            if continue_message:
                                processed_response = continue_message
                                self.shared_conversation_history.append({
                                    "role": "assistant",
                                    "content": processed_response
                                })
                                self._display_response(processed_response, is_continue=True)
                            loop_count += 1
                        elif response_data.get('message'):
                            message = response_data.get('message')
                            if text_content:
                                text_content = self._process_code_blocks(text_content)
                                self.shared_conversation_history.append({
                                    "role": "assistant",
                                    "content": text_content
                                })
                                self._display_response(text_content)
                            self.shared_conversation_history.append({
                                "role": "assistant",
                                "content": message
                            })
                            self._display_response(message)
                            break
                        else:
                            if text_content:
                                text_content = self._process_code_blocks(text_content)
                                self.shared_conversation_history.append({
                                    "role": "assistant",
                                    "content": text_content
                                })
                                self._display_response(text_content)
                            else:
                                self.shared_conversation_history.append({
                                    "role": "assistant",
                                    "content": processed_response
                                })
                            self._display_response(processed_response)
                            break

                    elif isinstance(json_data, list):
                        tool_calls = [item for item in json_data if isinstance(item, dict) and item.get('action') == 'use_tool']
                        if tool_calls:
                            self._execute_concurrent_tools(tool_calls)
                            break
                        continue_items = [item for item in json_data if isinstance(item, dict) and
                                         (item.get('continue') is True or
                                          item.get('need_continue') is True or
                                          item.get('think_more') is True)]
                        if continue_items:
                            continue_message = continue_items[0].get('message', '')
                            if continue_message:
                                processed_response = continue_message
                                self.shared_conversation_history.append({
                                    "role": "assistant",
                                    "content": processed_response
                                })
                                self._display_response(processed_response, is_continue=True)
                            loop_count += 1
                        else:
                            if text_content:
                                self.shared_conversation_history.append({
                                    "role": "assistant",
                                    "content": text_content
                                })
                            self._display_response(text_content or processed_response)
                            break
                else:
                    display_content = text_content if text_content else processed_response
                    self.shared_conversation_history.append({
                        "role": "assistant",
                        "content": display_content
                    })
                    self._display_response(display_content)
                    break
            except json.JSONDecodeError:
                text_content, json_data = self._parse_mixed_response(processed_response)
                if json_data:
                    if text_content:
                        text_content = self._process_code_blocks(text_content)
                        self.shared_conversation_history.append({
                            "role": "assistant",
                            "content": text_content
                        })
                        self._display_response(text_content)

                    if isinstance(json_data, dict):
                        response_data = json_data
                        if response_data.get('action') == 'continue':
                            continue_content = response_data.get('content', '')
                            if continue_content:
                                self.shared_conversation_history.append({
                                    "role": "assistant",
                                    "content": continue_content
                                })
                                self._display_response(continue_content)
                            continue

                        if response_data.get('action') == 'use_tool':
                            canceled = self._execute_single_tool(response_data)
                            if canceled:
                                break
                            break

                        if (response_data.get('continue') is True or
                              response_data.get('need_continue') is True or
                              response_data.get('think_more') is True):
                            continue_message = response_data.get('message', '')
                            if continue_message:
                                processed_response = continue_message
                                self.shared_conversation_history.append({
                                    "role": "assistant",
                                    "content": processed_response
                                })
                                self._display_response(processed_response, is_continue=True)
                            loop_count += 1
                        else:
                            message = response_data.get('message', '')
                            if message:
                                self.shared_conversation_history.append({
                                    "role": "assistant",
                                    "content": message
                                })
                                self._display_response(message)
                                loop_count += 1
                            else:
                                if text_content:
                                    self.shared_conversation_history.append({
                                        "role": "assistant",
                                        "content": text_content
                                    })
                                self._display_response(text_content or processed_response)
                                break

                    elif isinstance(json_data, list):
                        tool_calls = [item for item in json_data if isinstance(item, dict) and item.get('action') == 'use_tool']
                        if tool_calls:
                            self._execute_concurrent_tools(tool_calls)
                            break
                        continue_items = [item for item in json_data if isinstance(item, dict) and
                                         (item.get('continue') is True or
                                          item.get('need_continue') is True or
                                          item.get('think_more') is True)]
                        if continue_items:
                            continue_message = continue_items[0].get('message', '')
                            if continue_message:
                                processed_response = continue_message
                                self.shared_conversation_history.append({
                                    "role": "assistant",
                                    "content": processed_response
                                })
                                self._display_response(processed_response, is_continue=True)
                            loop_count += 1
                        else:
                            if text_content:
                                self.shared_conversation_history.append({
                                    "role": "assistant",
                                    "content": text_content
                                })
                            self._display_response(text_content or processed_response)
                            break
                else:
                    display_content = text_content if text_content else processed_response
                    self.shared_conversation_history.append({
                        "role": "assistant",
                        "content": display_content
                    })
                    self._display_response(display_content)
                break
        else:
            self._output(f"AI 已达到最大循环次数 ({max_loops})，已停止自动处理")
            self.shared_conversation_history.append({
                "role": "assistant",
                "content": f"已达到最大处理次数 ({max_loops})，已自动停止。如需继续处理，请重新输入。"
            })

        # ── 任务完成通知 ──
        task_summary = self._extract_task_summary(user_input)
        notify_task_complete(task_summary)

        # ── 自动保存聊天记录 ──
        if hasattr(self, 'memory_manager') and self.memory_manager:
            try:
                self.memory_manager.auto_save_chat(
                    self.shared_conversation_history,
                    label=user_input[:30]
                )
            except Exception:
                pass

            # ── 自动压缩上下文 ──
            try:
                if self.memory_manager.should_compress(self.shared_conversation_history):
                    self.shared_conversation_history = self.memory_manager.compress_context(
                        self.shared_conversation_history,
                        engine=self.current_engine
                    )
                    self._set_shared_conversation_history()
                    print(f"{Fore.DIM}[上下文已压缩，保留最近 10 条]{Style.RESET_ALL}")
            except Exception:
                pass

    def _extract_task_summary(self, user_input: str) -> str:
        """提取任务摘要用于通知显示"""
        # 取用户输入的前 80 字符作为摘要
        summary = user_input.strip().replace('\n', ' ')
        if len(summary) > 80:
            summary = summary[:77] + "..."
        return summary

    def _generate_response_with_animation(self, current_input, liugin_prompts=None):
        """生成AI响应并显示等待动画 — 支持 ESC 跨平台取消"""
        # TUI 模式：不做动画
        if self.tui_output_callback:
            system_prompt = self._build_system_prompt(liugin_prompts)
            if not self.current_engine:
                return "错误: 当前没有可用的AI引擎，请检查ai_engines目录中的引擎插件"
            response = self.current_engine.generate_response(current_input, system_prompt=system_prompt)
            if response and self.shared_conversation_history is not None:
                self.shared_conversation_history.append({
                    "role": "assistant",
                    "content": response
                })
            return response

        # CLI 模式：带动画和跨平台 ESC 取消
        animation_running = threading.Event()
        animation_running.set()
        esc_pressed = threading.Event()
        response_ready = threading.Event()
        response_result = [None]  # 用列表存储，方便线程内修改

        love_sentences = []
        love_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), LOVE_FILE_PATH)
        if os.path.exists(love_file_path):
            try:
                with open(love_file_path, 'r', encoding='utf-8') as f:
                    love_sentences = [line.strip() for line in f.readlines() if line.strip()]
            except Exception:
                pass
        if not love_sentences:
            love_sentences = ["AI正在思考中...", "请稍等片刻...", "正在处理您的请求..."]

        # ── 跨平台 ESC 检测 ──
        def check_for_esc():
            """跨平台 ESC 键检测"""
            import platform
            if platform.system() == 'Windows':
                try:
                    import msvcrt
                    while animation_running.is_set():
                        if msvcrt.kbhit():
                            key = msvcrt.getch()
                            if ord(key) == 27:  # ESC
                                esc_pressed.set()
                                break
                        time.sleep(0.05)
                except ImportError:
                    pass
            else:
                # Linux / macOS — 用 select 做非阻塞读取
                import select
                import sys
                try:
                    # 保存原始终端设置
                    import tty, termios
                    fd = sys.stdin.fileno()
                    old_settings = termios.tcgetattr(fd)
                    try:
                        tty.setcbreak(fd)  # cbreak 模式：无需回车即可读取
                        while animation_running.is_set():
                            if select.select([sys.stdin], [], [], 0.05)[0]:
                                ch = sys.stdin.read(1)
                                if ord(ch) == 27:  # ESC
                                    esc_pressed.set()
                                    break
                    finally:
                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                except Exception:
                    # 降级：无法检测 ESC，只能等 AI 完成
                    pass

        # ── 动画线程 ──
        def show_animation():
            last_change_time = time.time()
            current_sentence = random.choice(love_sentences)
            while animation_running.is_set():
                current_time = time.time()
                if current_time - last_change_time >= 5:
                    current_sentence = random.choice(love_sentences)
                    last_change_time = current_time
                animation_chars = "|/-\\"
                char_idx = int((current_time * 10) % len(animation_chars))
                display_sentence = current_sentence[:47] + "..." if len(current_sentence) > 50 else current_sentence
                print(f"\r{Fore.MAGENTA}{display_sentence} {animation_chars[char_idx]}{Style.RESET_ALL}", end="", flush=True)
                time.sleep(0.1)

        # ── AI 响应线程 ──
        def generate_in_thread():
            try:
                system_prompt = self._build_system_prompt(liugin_prompts)
                if not self.current_engine:
                    response_result[0] = "错误: 当前没有可用的AI引擎，请检查ai_engines目录中的引擎插件"
                else:
                    response_result[0] = self.current_engine.generate_response(
                        current_input, system_prompt=system_prompt
                    )
            except Exception as e:
                response_result[0] = f"AI 响应生成失败: {e}"
            finally:
                response_ready.set()

        # 启动三个线程
        threads = []
        for target in (show_animation, check_for_esc, generate_in_thread):
            t = threading.Thread(target=target, daemon=True)
            t.start()
            threads.append(t)

        try:
            # 主线程等待：ESC 或 响应完成
            while not response_ready.is_set() and not esc_pressed.is_set():
                time.sleep(0.1)

            # ESC 被按下 → 取消
            if esc_pressed.is_set():
                # 清除动画行
                print("\r" + " " * 80 + "\r", end="", flush=True)
                print(f"\n{Fore.YELLOW}⚡ AI 请求已取消 (ESC){Style.RESET_ALL}")
                return "[AI请求已取消]"

            # 响应正常返回
            response = response_result[0]
            if response:
                # 清除动画行后再输出
                print("\r" + " " * 80 + "\r", end="", flush=True)
                self._typeprint(response, Fore.CYAN)

            if response and self.shared_conversation_history is not None:
                self.shared_conversation_history.append({
                    "role": "assistant",
                    "content": response
                })

            return response

        finally:
            animation_running.clear()
            for t in threads:
                t.join(timeout=1)

    # ── CLI 主循环 ──

    def run_tui(self):
        """运行 TUI 模式"""
        if not TEXTUAL_AVAILABLE:
            print(f"{Fore.RED}TUI 模式不可用：Textual 库未安装{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}请运行: pip install textual rich{Style.RESET_ALL}")
            return
        from .tui import XiaoliTUI
        app = XiaoliTUI(self)
        app.run()

    def run(self):
        """运行 CLI"""
        import uuid
        self.user_id = str(uuid.getnode())
        print(f"{Fore.GREEN}小狸 Pro-CLI 已启动!{Style.RESET_ALL}")
        print(f"{Fore.GREEN}用户ID: {self.user_id}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/help' 查看帮助信息{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/quit' 退出程序{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/tui' 切换到 TUI 模式{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/engine list' 查看可用AI引擎{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/engine switch <引擎名>' 切换AI引擎{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/safe' 切换安全模式 (普通→人工→无限制){Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/notify' 切换任务完成通知 (开/关){Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/scheduler' 或 '/remind' 管理定时任务{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/memory' 管理记忆系统 (日记/搜索/聊天记录){Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/file.read <文件名> [行数]' 直接读取文件内容{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '@文件路径' 自动读取文件内容并发送给AI{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '@图片路径' 自动分析图片并发送描述给AI{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/image engines' 查看图像识别引擎{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/chat save <名称>' 保存当前聊天记录{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/chat list' 查看所有已保存的聊天记录{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/chat open <名称>' 加载聊天记录{Style.RESET_ALL}")
        print(f"{Fore.GREEN}输入 '/remote' 查看远程连接帮助{Style.RESET_ALL}")
        current_engine_name = getattr(self.current_engine, 'name', '未设置') if self.current_engine else '未设置'
        print(f"{Fore.GREEN}当前使用的AI引擎: {current_engine_name}{Style.RESET_ALL}")
        loaded_engines = list(self.engines.keys())
        if len(loaded_engines) > 1:
            print(f"{Fore.GREEN}已加载的AI引擎: {', '.join(loaded_engines)}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'-' * 50}{Style.RESET_ALL}")
        self._run_cli_loop()

    def _run_cli_loop(self):
        """运行 CLI 主循环"""
        while True:
            try:
                user_input = input(f"\n{Fore.WHITE}> {Style.RESET_ALL}").strip()

                if user_input == '/quit':
                    print(f"{Fore.GREEN}再见!{Style.RESET_ALL}")
                    break

                if user_input == '/help':
                    self.show_help()
                    continue

                if user_input.startswith('/help '):
                    liugin_name = user_input[6:].strip()
                    self.show_liugin_help(liugin_name)
                    continue

                if user_input.startswith('/engine '):
                    engine_command = user_input[8:].strip()
                    parts = engine_command.split(' ', 1)
                    cmd = parts[0]
                    args = parts[1] if len(parts) > 1 else ''
                    if cmd in self.engine_commands:
                        self.engine_commands[cmd](args)
                    else:
                        available_commands = ', '.join(self.engine_commands.keys())
                        print(f"{Fore.RED}未知的引擎命令.可用命令: {available_commands}{Style.RESET_ALL}")
                    continue

                if user_input.startswith('/engine.'):
                    engine_command = user_input[8:].strip()
                    if not self.handle_engine_command(engine_command):
                        print(f"{Fore.RED}当前引擎不支持该命令或命令执行失败{Style.RESET_ALL}")
                    continue

                if user_input.startswith('/file.read '):
                    args = user_input[11:].strip()
                    parts = args.split(' ', 2)
                    if len(parts) < 1:
                        print(f"{Fore.RED}请提供文件名.用法: /file.read <文件名> [行数]{Style.RESET_ALL}")
                        continue
                    filename = parts[0]
                    max_lines = None
                    if len(parts) >= 2:
                        try:
                            max_lines = int(parts[1])
                            if max_lines <= 0:
                                print(f"{Fore.RED}行数必须是正整数{Style.RESET_ALL}")
                                continue
                        except ValueError:
                            print(f"{Fore.RED}行数必须是正整数{Style.RESET_ALL}")
                            continue
                    result = self._read_file_direct(filename, max_lines)
                    print(f"{Fore.GREEN}{result}{Style.RESET_ALL}")
                    continue

                if user_input.startswith('/chat '):
                    chat_command = user_input[6:].strip()
                    if chat_command.startswith('save '):
                        name = chat_command[5:].strip()
                        if name:
                            self.save_chat_history(name)
                        else:
                            print(f"{Fore.RED}请提供聊天记录名称.用法: /chat save <名称>{Style.RESET_ALL}")
                        continue
                    elif chat_command == 'list':
                        self.list_chat_history()
                        continue
                    elif chat_command.startswith('open '):
                        name = chat_command[5:].strip()
                        if name:
                            self.load_chat_history(name)
                        else:
                            print(f"{Fore.RED}请提供聊天记录名称.用法: /chat open <名称>{Style.RESET_ALL}")
                        continue
                    else:
                        print(f"{Fore.RED}未知的聊天命令.可用命令: save, list, open{Style.RESET_ALL}")
                        continue

                if user_input.startswith('/remote'):
                    remote_command = user_input[7:].strip()
                    self._handle_remote_command(remote_command)
                    continue

                if user_input == '/about':
                    self._read_about_file()
                    continue

                if user_input == '/tui':
                    print(f"{Fore.CYAN}正在切换到 TUI 模式...{Style.RESET_ALL}")
                    self.run_tui()
                    print(f"{Fore.CYAN}已从 TUI 模式返回 CLI 模式{Style.RESET_ALL}")
                    continue

                if user_input.startswith('/safe'):
                    parts = user_input.split()
                    safety = get_safety()
                    if len(parts) > 1:
                        mode_arg = parts[1].lower()
                        if mode_arg in ('off', 'unrestricted', '无限制'):
                            safety.set_mode(MODE_UNRESTRICTED)
                        elif mode_arg in ('on', 'normal', '普通'):
                            safety.set_mode(MODE_NORMAL)
                        elif mode_arg in ('manual', '人工', 'all'):
                            safety.set_mode(MODE_MANUAL)
                        else:
                            print(f"{Fore.RED}用法: /safe [off|on|manual]{Style.RESET_ALL}")
                            continue
                    else:
                        # 无参数：循环切换
                        safety.cycle_mode()
                    mode_name = safety.get_mode_name()
                    icons = {"无限制": "", "普通": "", "人工确认": ""}
                    icon = icons.get(mode_name, "")
                    print(f"{icon} 安全模式: {mode_name}")
                    continue

                if user_input.startswith('/notify'):
                    parts = user_input.split()
                    nm = get_notification_manager()
                    if len(parts) > 1:
                        arg = parts[1].lower()
                        if arg in ('on', '开启', '启用'):
                            nm.set_enabled(True)
                            print(f"{Fore.GREEN}🔔 系统通知已开启{Style.RESET_ALL}")
                        elif arg in ('off', '关闭', '禁用'):
                            nm.set_enabled(False)
                            print(f"{Fore.YELLOW}🔕 系统通知已关闭{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.RED}用法: /notify [on|off]{Style.RESET_ALL}")
                    else:
                        # 无参数：切换状态
                        nm.set_enabled(not nm.enabled)
                        if nm.enabled:
                            print(f"{Fore.GREEN}🔔 系统通知已开启{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.YELLOW}🔕 系统通知已关闭{Style.RESET_ALL}")
                    continue

                if user_input.startswith('/'):
                    command_parts = user_input[1:].split(' ', 1)
                    command = command_parts[0]
                    args = command_parts[1] if len(command_parts) > 1 else ""
                    if command in self.liugin_commands:
                        try:
                            result = self.liugin_commands[command](args)
                            if result:
                                result = self._limit_output_lines(result, max_lines=5)
                                print(f"{Fore.GREEN}{result}{Style.RESET_ALL}")
                        except Exception as e:
                            print(f"{Fore.RED}插件命令执行失败: {e}{Style.RESET_ALL}")
                        continue

                if user_input.startswith('/thinking '):
                    thinking_input = user_input[10:].strip()
                    processed_response = self.process_thinking_response(thinking_input)
                    processed_response = self._process_code_blocks(processed_response)
                    user_id_display = f"[用户ID: {self.user_id}]"
                    response_lines = processed_response.split('\n')
                    for i, line in enumerate(response_lines):
                        if i == 0:
                            line = " " + line
                        if i == len(response_lines) - 1:
                            print(f"{line} {user_id_display}")
                        else:
                            print(f"{line}")
                    continue

                if '@' in user_input:
                    processed_input = self._process_file_paths(user_input)
                    if processed_input != user_input:
                        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
                        user_input = processed_input
                        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")

                self.process_conversation(user_input)
            except KeyboardInterrupt:
                user_id_display = f"[用户ID: {self.user_id}]"
                print(f"\n{Fore.GREEN}再见! {user_id_display}{Style.RESET_ALL}")
                break
            except Exception as e:
                user_id_display = f"[用户ID: {self.user_id}]"
                print(f"{Fore.RED}发生错误: {e} {user_id_display}{Style.RESET_ALL}")


# ============================================================================
# Main Entry Point
# ============================================================================
def main():
    """主入口函数"""
    import time
    import sys

    art_lines = [
        "█████████████████████████████████████████████████████████████████████████████████████████████████████",
        "█████████████████████████████████████████████████████████████████████████████████████████████████████",
        "█████████████████████████████████████████████████████████████████████████████████████████████████████",
        "█████████████████████████████████████████████████████████████████████████████████████████████████████",
        "█████████████████████████████████████████████████████████████████████████████████████████████████████",
        "███████████▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓██████████████████",
        "██████████                                                                          ▓████████████████",
        "██████████                                                                           ▒███████████████",
        "██████████                                                                            ░██████████████",
        "██████████                                                                             ░█████████████",
        "██████████                                                                               ████████████",
        "██████████                                                                                ███████████",
        "██████████                                      ▒████████████████████████████████████████████████████",
        "██████████                                    ░██████████████████████████████████████████████████████",
        "██████████                                   ████████████████████████████████████████████████████████",
        "██████████                                 ▓█████████████████████████████████████████████████████████",
        "██████████                               ▒███████████████████████████████████████████████████████████",
        "██████████                              ███████████▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓██████████",
        "██████████                            ███████████▓▒▓▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒██████████",
        "██████████                          ▓██████████▓▒▒▓▒▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▒▒▒▓██████████",
        "██████████                        ░███████████▒▒▓▒▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▒██████████",
        "██████████                       ███████████▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▒▓▒▒▒▒▓▒▒▒▓▒▒▒▒▓▒▒▒▓▒▒▒▒▓▓▒██████████",
        "██████████                     ███████████▓▒▓▒▒▓▒▒▒▒▓▒▒▓▒▒▒▓▒▓▒▒▓▒▒▒▓▒▓▒▒▓▒▒▒▓▒▓▒▒▓▒▒▒▓▒▓▒▓██████████",
        "██████████                   ▓██████████▓▒▒▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▒▒▒▓▒▒▒▓██████████",
        "██████████                 ░██████████▓▒▒▓▒▓▒▒▓▒▒▒▒▓▒▒▓▒▓▒▓▒▒▒▓▒▒▓▒▓▒▒▒▓▒▒▓▒▓▒▒▒▓▒▒▓▒▓▒▒▒▓▓██████████",
        "██████████                ███████████▒▓▒▓▒▒▒▓▒▒▓▒▓▒▒▓▒▒▒▒▒▒▓▒▓▒▒▓▒▒▒▓▒▓▒▒▓▒▒▒▓▒▓▒▒▒▒▒▒▓▒▓▒▓██████████",
        "██████████              ███████████▒▒▒▒▒▒▓▒▓▒▒▓▒▒▒▓▒▒▓▒▓▒▓▒▒▒▒▓▒▒▒▓▒▒▒▒▒▓▒▒▓▒▒▒▒▒▓▒▓▒▓▒▒▒▓▓██████████",
        "██████████            ░██████████▒▓▒▓▒▓▒▓▒▒▒▓▒▒▒▓▒▒▓▒▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▓▒▓▒▒▒▒▓▒▓▒▓▒▒▓▒▒▒▓▒▒▒██████████",
        "██████████            █████████▓▒▒▒▓▒▒▓▒▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▓▒▒██████████",
        "██████████            █████████▒▒▓▒▒▓▒▒▓▒▓▒▒▓▒▒▒▓▒▒▓▒▒▓▒▒▒▒▒▒▓▒▓▒▒▓▒▒▒▓▒▒▓▒▒▓▒▒▓▒▒▒▒▒▓██████████",
        "██████████            ▓████████▒▓▒▓▒▒▓▒▒▒▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▒▒▒▒▓▒▒▓▒▒▓▒▓▒▒▒▓▒▒▓▒▒▓▓▒▒▒██████████",
        "██████████            █████████▒▒▒▒▓▒▒▒▓▒▓▒▒▓▒▒▓▒▒▓▒▒▓▒▒▒▒▒▒▓▒▒▒▓▒▒▒▓▒▒▓▒▒▒▒▓▒▓▒▒▓▒▒▒▒▒▓▒██████████",
        "██████████            █████████▒▓▒▓▒▒▓▒▒▓▒▒▒▒▓▒▒▒▓▒▒▓▒▒▓▒▒▓▒▒▒▒▓▒▒▓▒▒▓▒▓▒▒▒▓▒▓▒▒▓▒▒▒▒▒▓▒▒▒██████████",
        "██████████            ▓████████▒▒▓▒▒▒▓▒▒▓▒▒▒▒▓▒▒▓▒▒▓▒▓▒▒▒▒▒▒▒▓▒▒▓▒▒▓▒▓▒▒▒▒▓▒▓▒▒▓▒▒▒▓▒▒██████████",
        "██████████            █████████▒▓▒▒▒▒▓▒▒▒▒▓▒▓▒▒▓▒▒▒▓▒▒▒▒▒▒▒▒▓▒▒▒▓▒▒▒▓▒▒▓▒▒▒▒▓▒▓▒▒▒▒▒▒▒██████████",
        "██████████            █████████▒▒▓▒▓▒▒▓▒▓▒▒▒▒▓▒▒▒▓▒▒▓▒▒▓▒▒▓▒▒▒▒▓▒▒▓▒▒▓▒▒▒▒▓▒▒▒▒▓▒▒▒▒▒▓▒██████████",
        "██████████            ▓████████▒▓▒▒▒▓▒▒▒▒▒▒▓▒▓▒▒▓▒▒▒▓▒▒▒▒▒▒▒▓▒▒▒▓▒▒▒▓▒▒▓▒▒▒▒▒▓▒▓▒▒▒▒▒▓██████████",
        "██████████            █████████▒▒▓▒▓▒▒▓▒▓▒▒▒▒▓▒▒▒▓▒▒▓▒▒▒▒▒▒▒▒▓▒▒▒▓▒▒▒▓▒▒▓▒▒▒▒▒▓▒▒▒▒▒▒██████████",
        "██████████            █████████▒▓▒▒▒▓▒▒▒▒▒▒▓▒▓▒▒▓▒▒▒▓▒▒▒▒▒▒▒▓▒▒▒▓▒▒▒▓▒▒▓▒▒▒▒▒▓▒▒▒▒▒▒██████████",
        "██████████            ▓████████▒▒▓▒▒▒▓▒▒▓▒▒▒▒▓▒▒▓▒▒▓▒▓▒▒▒▒▒▒▒▓▒▒▓▒▒▓▒▓▒▒▒▒▓▒▓▒▒▓▒▒▒▓▒▒▒██████████",
        "██████████            █████████▒▓▒▒▒▒▓▒▒▒▒▒▒▓▒▓▒▒▓▒▒▒▓▒▒▒▒▒▒▒▓▒▒▒▓▒▒▒▓▒▒▓▒▒▒▒▒▓▒▒▒▒▒▒██████████",
        "██████████            █████████▒▒▓▒▓▒▒▓▒▓▒▒▒▒▓▒▒▒▓▒▒▓▒▒▒▒▒▒▒▒▓▒▒▒▓▒▒▒▓▒▒▓▒▒▒▒▒▓▒▒▒▒▒▒██████████",
        "██████████            ▓████████▒▓▒▒▒▓▒▒▒▒▒▒▓▒▓▒▒▓▒▒▒▓▒▒▒▒▒▒▒▓▒▒▒▓▒▒▒▓▒▒▓▒▒▒▒▒▓▒▒▒▒▒▒██████████",
        "██████████            █████████▒▒▓▒▒▒▓▒▒▓▒▒▒▒▓▒▒▒▓▒▒▒▓▒▓▒▒▒▒▒▓▒▒▒▓▒▒▒▓▒▒▓▒▒▒▒▒▓▒▒▒▒▒▒██████████",
        "██████████            █████████▒▓▒▒▒▒▒▒▓▒▒▒▓▒▒▓▒▒▒▒▒▒▒▒▓▒▒▓▒▒▒▒▓▒▒▒▓▒▒▒▓▒▒▓▒▒▒▒▒▓▒▒▒▒▒▒██████████",
        "██████████            ▓████████▒▒▓▒▒▒▒▒▓▒▒▓▒▒▒▒▓▒▒▒▒▒▒▓▒▒▒▒▓▒▒▒▓▒▒▒▓▒▒▒▓▒▒▓▒▒▒▒▒▓▒▒▒▒▒▒██████████",
        "███████████           █████████▒▓▒▒▒▒▒▒▓▒▒▒▒▓▒▒▓▒▒▒▒▒▒▒▒▓▒▒▓▒▒▒▒▓▒▒▒▓▒▒▒▓▒▒▓▒▒▒▒▒▓▒▒▒▒▒▒██████████",
        "█████████████▓        █████████▒▒▓▒▒▓▒▒▓▒▒▒▒▓▒▒▒▓▒▒▓▒▒▒▒▓▒▒▓▒▒▒▒▓▒▒▒▓▒▒▒▓▒▒▓▒▒▒▒▒▓▒▒▒▒▒▒██████████",
        "█████████████████     ▓████████▒▓▒▒▒▒▒▒▓▒▒▒▓▒▒▓▒▒▒▒▒▒▒▒▒▓▒▒▓▒▒▒▒▓▒▒▒▓▒▒▒▓▒▒▓▒▒▒▒▒▓▒▒▒▒▒▒██████████",
        "███████████████████▒  █████████▒▒▓▒▒▒▓▒▒▓▒▒▒▒▓▒▒▒▓▒▒▒▒▒▒▒▒▓▒▒▓▒▒▒▓▒▒▒▓▒▒▒▓▒▒▓▒▒▒▒▒▓▒▒▒▒▒▒██████████",
        "█████████████████████████████████████████████████████████████████████████████████████████████████████",
        "█████████████████████████████████████████████████████████████████████████████████████████████████████",
        "█████████████████████████████████████████████████████████████████████████████████████████████████████",
        "█████████████████████████████████████████████████████████████████████████████████████████████████████",
        "█████████████████████████████████████████████████████████████████████████████████████████████████████",
        "█████████████████████████████████████████████████████████████████████████████████████████████████████",
    ]

    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

    for line in art_lines:
        try:
            print(line, flush=True)
        except UnicodeEncodeError:
            print(line.encode('gbk', errors='ignore').decode('gbk'), flush=True)
        time.sleep(0.05)

    cli = AICLI()
    cli.run()
