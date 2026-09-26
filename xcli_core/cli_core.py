import sys
import json
import re
import time
import threading
from typing import Optional
from colorama import Fore, Style

from .constants import TEXTUAL_AVAILABLE, VERSION
from .config import get_system_config, set_system_config, logger
from .cli_base import BaseAICLI
from .safety import get_safety, MODE_UNRESTRICTED, MODE_NORMAL, MODE_MANUAL
from .cli_clawli import ClawliMixin
from .cli_tools import ToolMixin
from .cli_code_exec import CodeExecMixin
from .cli_display import DisplayMixin, emit
from .cli_history import HistoryMixin
from .plugin_market import PluginMarketMixin
from .notification import notify_task_complete, get_notification_manager
from .process_protection import get_protection_status

# ── Plan 模式 system prompt 追加段（只读规划约束）──
PLAN_MODE_SYSTEM_APPEND = """

【PLAN 模式 — 只读规划】
你当前处于 PLAN 模式。此模式下你只能进行调查、阅读、分析，不得执行任何修改。
- 你可以使用只读工具调研代码库：code_search（搜索/结构/符号/统计）、file_manager 的 list/read/info/search、code_editor 的 read_range/find/diff、git_tools 的 status/log/diff/show/blame、tool_search（查询工具用法）、ai_search（联网搜索）。
- 你**不能**执行写操作（编辑/创建/删除文件、运行 shell 命令、git commit/push/checkout、委派会修改的子代理等）——这些会被系统拦截并返回提示。
- 调研完成后，输出一份清晰的、带编号步骤的「实施计划」，让用户审批。计划应包含：每步要做什么、涉及哪些文件/函数、预期结果、潜在风险。
- 计划以如下标记开头：## 实施计划
- 完成计划后停止，等待用户输入 /build 批准执行，或继续追问以完善计划。不要自行开始修改。"""


class AICLI(BaseAICLI, ClawliMixin, ToolMixin, CodeExecMixin, DisplayMixin, HistoryMixin, PluginMarketMixin):
    """AI CLI主程序 - 组合所有 Mixin"""

    # ── 深度思考处理 ──

    def process_thinking_response(self, response):
        """处理深度思考AI返回的内容, 分离思考和回复内容"""
        try:
            response_data = self._loads_json(response)
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

1. **精准代码编辑** - 使用 code_editor 工具进行搜索替换、多文件批量编辑（修改后自动检查语法）
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
3. {{"action": "use_tool", "tool": "git_tools", "args": "smart-commit"}} → 自动提交        """

        # 参数格式统一示例：无论用哪种工具，args 都是同一个字符串外壳，给 AI 一个速查锚点
        unified_arg_example = """【参数格式统一示例】
所有工具共用同一套 JSON 外壳，`args` 永远是【字符串】（不是 JSON 对象）：
{"action":"use_tool","tool":"<工具名>","args":"<操作> <参数>"}

高频工具的 args 写法（照抄即可）：
- code_editor : "edit 文件 旧<<<>>>新"  |  "read_range 文件 起 止"  |  "create 文件 内容"
- code_search : "find . 关键词 *.py"  |  "structure ."
- git_tools   : "status"  |  "commit 说明文字"
- cmd_executor: "dir"  |  "python main.py"
说明：多行内容（如 edit 的代码片段）直接换行写在 args 里，无需转义；一次可返回多个 JSON 指令。
调用方式可选：纯 JSON（默认）或 function calling（引擎支持时），两种都会被正确处理。"""

        if liugin_prompts:
            prompt = f"""{base_prompt}

{liugin_prompts}

{tool_search_rule}

{unified_arg_example}

【工具调用格式】
在回复中包含 JSON 指令来执行操作：

1. 纯 JSON: {{"action": "use_tool", "tool": "code_editor", "args": "edit file.py old <<<>>> new"}}
2. 文本+JSON: 好的，我来修改。{{"action": "use_tool", "tool": "code_editor", "args": "edit file.py old <<<>>> new"}}

【编程工作流 — 每一步都必须先查询工具】
1. 理解需求 → 先 tool_search "code_editor"，再用 structure 查看项目结构
2. 定位代码 → 已查询过，直接用 find 或 regex 搜索
3. 查看上下文 → 用 read_range 查看相关代码
4. 精准修改 → 用 edit 替换代码（old <<<>>> new 分隔）
5. 语法自动检查 → 编辑操作后自动执行，通过显示 ✓，失败显示详细错误
6. 验证变更 → 先 tool_search "git_tools"，再用 diff 查看变更
7. 提交代码 → 已查询过，用 commit 提交

【语法检查 — 自动 + 主动】
- 编辑操作(edit/multi/insert/delete_lines/create/write/append)完成后自动检查语法
- 通过: 显示 "  语法检查通过 ✓"
- 失败: 显示具体错误（行号、列号、错误描述）
- 主动检查: syntax_check <文件路径> 或 check <文件路径>
- 支持语言: Python, JavaScript, TypeScript, JSON, YAML, TOML, HTML, XML, CSS, Shell, SQL
- 如果语法检查失败，根据错误信息修复代码后再次编辑

【Diff 弹窗 — 自动弹出修改对比】
- 编辑操作完成后自动显示修改前后的完整内容和行号对比
- 新增行用绿色标记，删除行用红色标记
- 支持两种模式: 弹窗模式（新终端窗口）/ 主终端内显示（SSH 兼容）
- 开关: diff_popup on / diff_popup off / diff_popup popup / diff_popup inline
- 默认开启，无需手动调用

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

{unified_arg_example}

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

        # ── Plan 模式：追加只读规划约束 ──
        if getattr(self, 'plan_mode', False):
            prompt += PLAN_MODE_SYSTEM_APPEND

        # ── LSP 诊断自动注入：让模型持续看到真实语言诊断 ──
        liugin_manager = getattr(self, 'liugin_manager', None)
        if liugin_manager and hasattr(liugin_manager, 'get_lsp_context'):
            try:
                lsp_ctx = liugin_manager.get_lsp_context()
                if lsp_ctx:
                    prompt += "\n\n# 当前代码诊断（来自 LSP 语言服务器）\n" + lsp_ctx
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
            # 工具名清单（纯 JSON 模式：不发送 FC schema，模型按 action JSON 调用）。
            # 只列名字 + 由 tool_search 提供用法，避免重复曝光、省 token。
            names = ", ".join(t.get('name', '') for t in plugins)
            prompts.append(
                "## 内置工具（纯 JSON 模式：不发送 function calling 的 tools schema，"
                "模型按下方 JSON 格式直接调用，调用前请先用 tool_search 查询其详细用法与示例）\n"
                f"工具名: {names}\n"
                '调用格式: {"action": "use_tool", "tool": "工具名", "args": "参数"}'
            )

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

    def _loads_json(self, s):
        """json.loads，带多级容错修复（模型输出的 JSON 常常不规整）。

        尝试顺序：
          1) 标准解析
          2) 未成对的反斜杠转义（Windows 路径 C:\\Users 常见）
          3) 字符串内的未转义换行/制表符（多行 args 常见）
          4) 去掉对象/数组里多余的尾随逗号（模型高频错误）
        """
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
        # 2) 反斜杠修复
        try:
            fixed = re.sub(r'(?<!\\)\\(?!\\\\)', r'\\\\', s)
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass
        # 3) 字符串内未转义换行/制表符修复
        try:
            repaired = re.sub(
                r'"([^"]*(?:\n[^"]*)*)"',
                lambda m: '"' + (m.group(1)
                                 .replace('\\', '\\\\')
                                 .replace('\n', '\\n')
                                 .replace('\r', '\\r')
                                 .replace('\t', '\\t')
                                 .replace('"', '\\"')) + '"',
                s, flags=re.DOTALL)
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass
        # 4) 尾随逗号修复
        try:
            trimmed = re.sub(r',\s*([}\]])', r'\1', s)
            return json.loads(trimmed)
        except json.JSONDecodeError:
            raise

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
                parsed = self._loads_json(json_str)
                if isinstance(parsed, dict):
                    return "", parsed
            except json.JSONDecodeError:
                pass

        # 方法1: 直接解析为纯JSON
        try:
            parsed = self._loads_json(response)
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
            parsed = self._loads_json(fixed_response)
            if isinstance(parsed, (list, dict)):
                return "", parsed
        except Exception:
            pass

        # 方法3: 查找代码块中的JSON
        json_pattern = r"```(?:json)?\s*({.*?})\s*```"
        matches = re.findall(json_pattern, response, re.DOTALL)
        if matches:
            try:
                json_data = self._loads_json(matches[-1])
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
                    parsed = self._loads_json(line)
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

        # 方法5: 稳健抽取最后一个「控制指令」JSON（兼容长文本后格式不规整的情况）。
        # 结构化 FC 已是主路径；这里是纯 JSON 兜底：不再依赖脆弱的 marker 匹配，
        # 而是扫描所有平衡括号的 JSON 对象，取最后一个含控制键的，最大限度避免
        # 「长篇文本 + 格式错乱的工具调用」被解析失败、白白浪费 token。
        text_before, json_data = self._extract_last_action_json(response)
        if json_data is not None:
            return text_before, json_data

        return response, None

    def _extract_last_action_json(self, response):
        """在可能夹杂长篇正文的响应里，稳健抽取最后一个控制指令 JSON。

        控制指令指含以下任一字段的 JSON 对象：
          action / continue / need_continue / think_more / message
        返回 (text_before, json_data)；找不到返回 (response, None)。
        """
        # 整段就是 JSON 数组（多个工具调用）时直接返回，保留并发执行能力
        stripped = response.strip()
        if stripped.startswith('['):
            try:
                arr = self._loads_json(stripped)
                if isinstance(arr, list) and arr:
                    return "", arr
            except json.JSONDecodeError:
                pass

        CONTROL_KEYS = {"action", "continue", "need_continue", "think_more", "message"}
        candidates = []  # (start_index, parsed_dict)
        n = len(response)
        i = 0
        while i < n:
            if response[i] == '{':
                # 从 i 起做括号/字符串感知的平衡解析，取出一个完整 JSON 对象
                depth = 0
                in_str = False
                esc = False
                end = -1
                for j in range(i, n):
                    c = response[j]
                    if in_str:
                        if esc:
                            esc = False
                        elif c == '\\':
                            esc = True
                        elif c == '"':
                            in_str = False
                        continue
                    if c == '"':
                        in_str = True
                    elif c == '{':
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0:
                            end = j
                            break
                if end != -1:
                    frag = response[i:end + 1]
                    try:
                        obj = self._loads_json(frag)
                    except json.JSONDecodeError:
                        obj = None
                    if isinstance(obj, dict) and (set(obj.keys()) & CONTROL_KEYS):
                        candidates.append((i, obj))
                    i = end + 1
                    continue
            i += 1

        if candidates:
            start, obj = candidates[-1]
            return response[:start].strip(), obj

        # 退路：整段若为 JSON 数组（如 [{"action":"use_tool"}, ...]）
        try:
            stripped = response.strip()
            if stripped.startswith('['):
                arr = self._loads_json(stripped)
                if isinstance(arr, list) and arr:
                    return "", arr
        except json.JSONDecodeError:
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
            # TUI Esc 真取消：轮间检查取消事件（CLI 下 _tui_cancel 不存在，行为不变）
            if getattr(self, '_tui_cancel', None) is not None and self._tui_cancel.is_set():
                self._output("⚡ 已取消")
                break
            response = self._generate_response_with_animation(current_input, liugin_prompts=liugin_prompts)
            if getattr(self, '_tui_cancel', None) is not None and self._tui_cancel.is_set():
                self._output("⚡ 已取消（本轮输出已丢弃）")
                break
            processed_response = self.process_thinking_response(response)
            processed_response = self._process_code_blocks(processed_response)

            # ── Function Calling 响应检测 ──
            fc_handled = self._handle_fc_response(processed_response, user_input)
            if fc_handled:
                # FC 工具已执行，用结果继续循环
                current_input = fc_handled
                loop_count += 1
                continue

            try:
                text_content, json_data = self._parse_mixed_response(processed_response)
                signal = self._dispatch_round(text_content, json_data, processed_response, fallback=False)
            except json.JSONDecodeError:
                text_content, json_data = self._parse_mixed_response(processed_response)
                signal = self._dispatch_round(text_content, json_data, processed_response, fallback=True)

            # 信号：'pass'=不计数继续（action:continue）；'loop'=计数继续（think_more 等）；
            #       'loop_break'=计数后结束（降级支特有）；'break'=结束
            if signal == 'pass':
                continue
            if signal == 'loop':
                loop_count += 1
                continue
            if signal == 'loop_break':
                loop_count += 1
                break
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

            # ── 自动压缩上下文（token 感知优先，消息数兜底）──
            try:
                if hasattr(self, 'memory_manager') and self.memory_manager:
                    engine = self.current_engine
                    prompt_tokens = getattr(engine, 'last_prompt_tokens', None) if engine else None
                    # 统一 API：所有引擎必须返回 max_input_tokens（最大输入 token 数）
                    ctx = None
                    if engine:
                        try:
                            ctx = engine.max_input_tokens
                        except Exception:
                            ctx = None
                    ratio = get_system_config('compress_ratio', 0.7)
                    self.memory_manager.set_compress_ratio(ratio)
                    if self.memory_manager.should_compress(
                        self.shared_conversation_history, prompt_tokens, ctx, ratio
                    ):
                        before = len(self.shared_conversation_history)
                        self.shared_conversation_history = self.memory_manager.compress_context(
                            self.shared_conversation_history,
                            engine=engine
                        )
                        token_info = f"，token {prompt_tokens}/{ctx}" if (prompt_tokens and ctx) else ""
                        self._output(
                            f"{Fore.CYAN}🗜 上下文已自动压缩 (原 {before} 条 → {len(self.shared_conversation_history)} 条{token_info}，阈值 {ratio}){Style.RESET_ALL}"
                        )
            except Exception as e:
                logger.warning(f"自动压缩上下文失败: {e}")

    # ── 对话轮次分派（自 process_conversation 拆出，行为与原实现逐行等价）──

    def _record(self, content, is_continue=False):
        """记入助手消息并显示"""
        self.shared_conversation_history.append({
            "role": "assistant",
            "content": content
        })
        self._display_response(content, is_continue=is_continue)

    def _record_only(self, content):
        """只记入助手消息（原文部分分支不立即显示）"""
        self.shared_conversation_history.append({
            "role": "assistant",
            "content": content
        })

    def _dispatch_round(self, text_content, json_data, processed_response, fallback):
        """单轮响应分派，返回 'break' | 'loop' | 'loop_break' | 'pass'"""
        if not json_data:
            display_content = text_content if text_content else processed_response
            self._record(display_content)
            return 'break'
        if text_content:
            text_content = self._process_code_blocks(text_content)
            self._record(text_content)
        if isinstance(json_data, dict):
            if fallback:
                return self._dispatch_dict_fallback(json_data, text_content, processed_response)
            return self._dispatch_dict_primary(json_data, text_content, processed_response)
        if isinstance(json_data, list):
            signal = self._dispatch_list(json_data, text_content, processed_response)
            # 降级支原文 loop_count += 1 后仍落全局 break
            return 'loop_break' if (fallback and signal == 'loop') else signal
        # 非 dict/list 的怪类型：正常支原文走完 if 链后落回 while 不计数继续；
        # 降级支落 handler 末尾全局 break
        return 'break' if fallback else 'pass'

    def _dispatch_dict_primary(self, response_data, text_content, processed_response):
        """dict 分派（正常支）"""
        if response_data.get('action') == 'use_tool':
            self._execute_single_tool(response_data)
            return 'break'
        if (response_data.get('continue') is True or
                response_data.get('need_continue') is True or
                response_data.get('think_more') is True):
            continue_message = response_data.get('message', '')
            if continue_message:
                self._record(continue_message, is_continue=True)
            return 'loop'
        if response_data.get('message'):
            message = response_data.get('message')
            if text_content:
                self._record(self._process_code_blocks(text_content))
            self._record(message)
            return 'break'
        if text_content:
            self._record(self._process_code_blocks(text_content))
        else:
            self._record_only(processed_response)
        self._display_response(processed_response)
        return 'break'

    def _dispatch_dict_fallback(self, response_data, text_content, processed_response):
        """dict 分派（JSONDecodeError 降级支：仅 action:continue 真正继续）"""
        if response_data.get('action') == 'continue':
            continue_content = response_data.get('content', '')
            if continue_content:
                self._record(continue_content)
            return 'pass'
        if response_data.get('action') == 'use_tool':
            self._execute_single_tool(response_data)
            return 'break'
        if (response_data.get('continue') is True or
                response_data.get('need_continue') is True or
                response_data.get('think_more') is True):
            continue_message = response_data.get('message', '')
            if continue_message:
                self._record(continue_message, is_continue=True)
            return 'loop_break'
        message = response_data.get('message', '')
        if message:
            self._record(message)
            return 'loop_break'
        if text_content:
            self._record_only(text_content)
        self._display_response(text_content or processed_response)
        return 'break'

    def _dispatch_list(self, json_data, text_content, processed_response):
        """list 分派（正常/降级两支原文行为一致）"""
        tool_calls = [item for item in json_data if isinstance(item, dict) and item.get('action') == 'use_tool']
        if tool_calls:
            self._execute_concurrent_tools(tool_calls)
            return 'break'
        continue_items = [item for item in json_data if isinstance(item, dict) and
                          (item.get('continue') is True or
                           item.get('need_continue') is True or
                           item.get('think_more') is True)]
        if continue_items:
            continue_message = continue_items[0].get('message', '')
            if continue_message:
                self._record(continue_message, is_continue=True)
            return 'loop'
        if text_content:
            self._record_only(text_content)
        self._display_response(text_content or processed_response)
        return 'break'


    def _extract_task_summary(self, user_input: str) -> str:
        """提取任务摘要用于通知显示"""
        # 取用户输入的前 80 字符作为摘要
        summary = user_input.strip().replace('\n', ' ')
        if len(summary) > 80:
            summary = summary[:77] + "..."
        return summary

    def _handle_fc_response(self, response: str, original_input: str) -> Optional[str]:
        """
        处理 Function Calling 响应
        如果响应是 FC 格式，执行工具并返回结果（供下一轮循环使用）
        如果不是 FC 响应，返回 None
        """
        if not response or '_fc' not in response:
            return None

        try:
            data = self._loads_json(response)
            if not data.get("_fc"):
                return None

            tool_calls = data.get("tool_calls", [])
            if not tool_calls:
                return None

            # 记录 assistant 的 FC 消息到历史
            fc_history_entry = {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": tc.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": tc.get("name", ""),
                        "arguments": json.dumps(tc.get("arguments", {}), ensure_ascii=False)
                    }
                } for tc in tool_calls]
            }
            self.shared_conversation_history.append(fc_history_entry)

            # 执行每个工具调用
            results = []
            for tc in tool_calls:
                tool_name = tc.get("tool", tc.get("name", ""))
                tool_args = tc.get("args", "")
                call_id = tc.get("id", "")

                self._output(f"[green]  FC 调用: {tool_name}({tool_args[:60]})[/]")

                # 通过插件管理器执行
                result = self._execute_tool_by_name(tool_name, tool_args)

                # 记录工具结果到历史（官方 OpenAI tool 消息不含 name 字段）
                tool_result_msg = {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result if result else "执行完成"
                }
                self.shared_conversation_history.append(tool_result_msg)

                results.append(f"[{tool_name}]: {result if result else '完成'}")

            # 返回工具结果，供下一轮 AI 处理
            return "工具执行结果:\n" + "\n".join(results)

        except (ValueError, KeyError, TypeError):
            return None

    def _execute_tool_by_name(self, tool_name: str, tool_args: str) -> str:
        """根据名称执行工具（FC 调用路径）

        注意：插件 handler 可能返回 ToolResult / dict / str，
        这里统一归一成 str，保证调用方能安全做切片与拼接。
        """
        from .tool_result import normalize_tool_text

        # 安全检查
        safety = get_safety()
        allowed, msg = safety.check(tool_name, tool_args)
        if not allowed:
            return f"操作被拒绝: {msg}"

        # 查找工具
        tool = self.liugin_manager.get_tool_by_name(tool_name)
        if tool and 'handler' in tool:
            try:
                return normalize_tool_text(tool['handler'](tool_args), default="执行完成")
            except Exception as e:
                return f"工具执行失败: {e}"

        # memory 内置工具
        if tool_name == 'memory' and hasattr(self, 'memory_manager'):
            return normalize_tool_text(self.memory_manager.handle_tool(tool_args), default="执行完成")

        # scheduler 内置工具
        if tool_name == 'scheduler':
            for t in self.liugin_manager.tools:
                if t.get('name') == 'scheduler' and 'handler' in t:
                    try:
                        return normalize_tool_text(t['handler'](tool_args), default="执行完成")
                    except Exception as e:
                        return f"工具执行失败: {e}"

        return f"未找到工具: {tool_name}"

    def _build_fc_tools(self, current_input):
        """构建本轮下发给引擎的 FC 工具子集，让引擎自行决定用 FC 结构化调用还是回退纯 JSON。

        引擎不支持 FC（探测缓存未通过）时返回 None —— 引擎自动降级为纯 JSON 模式。
        仅对带 `_fc_supported()` 的引擎下发 tools（Manual 等不支持的引擎不传 tools，
        避免关键字参数错误）。
        """
        engine = self.current_engine
        if not engine or not hasattr(engine, '_fc_supported'):
            return None
        try:
            if not engine._fc_supported():
                return None
        except Exception:
            return None
        # 工具结果续轮也下发 FC 工具：让模型在续轮里继续用结构化 function calling
        # 调用工具，避免把工具调用写成散文 JSON（长文本后格式错乱会浪费 token）。
        # 仅对带 _fc_supported() 的引擎下发 tools（Manual 等不支持的引擎不传 tools）。
        try:
            from .fc_tools import mcp_to_openai_tools, prune_tools
            all_tools = mcp_to_openai_tools(self.liugin_manager)
            if not all_tools:
                return None
            return prune_tools(all_tools, current_input)
        except Exception:
            return None

    def _call_engine_with_tools(self, current_input, system_prompt, fc_tools):
        """调用当前引擎；fc_tools 非空时下发 FC 工具定义（tool_choice=auto，模型自选）。"""
        if fc_tools:
            return self.current_engine.generate_response(
                current_input, system_prompt=system_prompt, tools=fc_tools)
        return self.current_engine.generate_response(
            current_input, system_prompt=system_prompt)

    def _generate_response_with_animation(self, current_input, liugin_prompts=None):
        """生成AI响应并显示等待动画 — 支持 ESC 跨平台取消"""
        # TUI 模式：不做动画
        if self.tui_output_callback:
            system_prompt = self._build_system_prompt(liugin_prompts)
            if not self.current_engine:
                return "错误: 当前没有可用的模型，请用 /model add 添加模型（OpenAI 兼容格式）"
            # 混合模式：下发 FC 工具定义，tool_choice=auto —— 模型可自行选择
            # 用 FC 结构化调用，或回退到纯 JSON action（两种都会被正确处理）。
            fc_tools = self._build_fc_tools(current_input)
            response = self._call_engine_with_tools(current_input, system_prompt, fc_tools)
            return response

        # CLI 模式：去掉流式显示与逐帧加载动画，改为「一次性等待 + 完整输出」。
        # 仍用线程跑生成以支持 ESC 取消，但不再喷任何中间动画/情话帧。
        esc_pressed = threading.Event()
        response_ready = threading.Event()
        response_result = [None]  # 用列表存储，方便线程内修改

        # 是否真实交互终端：非 TTY（管道 / 日志镜像 / 聊天前端捕获 stdout）时
        # 不打印任何等待提示，避免污染捕获流。
        is_tty = sys.stdout.isatty()
        if is_tty:
            # 仅一行静态提示，非动画
            print(f"{Fore.MAGENTA}💭 思考中… (按 ESC 取消){Style.RESET_ALL}", end="", flush=True)

        # ── 跨平台 ESC 检测 ──
        def check_for_esc():
            """跨平台 ESC 键检测"""
            import platform
            while not response_ready.is_set() and not esc_pressed.is_set():
                if platform.system() == 'Windows':
                    try:
                        import msvcrt
                        if msvcrt.kbhit():
                            key = msvcrt.getch()
                            if ord(key) == 27:  # ESC
                                esc_pressed.set()
                                break
                        time.sleep(0.05)
                    except ImportError:
                        break
                else:
                    # Linux / macOS — 用 select 做非阻塞读取
                    import select
                    try:
                        import sys as _sys
                        import tty, termios
                        fd = _sys.stdin.fileno()
                        old_settings = termios.tcgetattr(fd)
                        try:
                            tty.setcbreak(fd)  # cbreak 模式：无需回车即可读取
                            if select.select([_sys.stdin], [], [], 0.05)[0]:
                                ch = _sys.stdin.read(1)
                                if ord(ch) == 27:  # ESC
                                    esc_pressed.set()
                                    break
                        finally:
                            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                    except Exception:
                        # 降级：无法检测 ESC，只能等 AI 完成
                        break

        # ── AI 响应线程 ──
        def generate_in_thread():
            try:
                system_prompt = self._build_system_prompt(liugin_prompts)
                if not self.current_engine:
                    response_result[0] = "错误: 当前没有可用的模型，请用 /model add 添加模型（OpenAI 兼容格式）"
                else:
                    # 混合模式：下发 FC 工具（tool_choice=auto），模型自选 FC 或纯 JSON
                    fc_tools = self._build_fc_tools(current_input)
                    response_result[0] = self._call_engine_with_tools(current_input, system_prompt, fc_tools)
            except Exception as e:
                response_result[0] = f"AI 响应生成失败: {e}"
            finally:
                response_ready.set()

        # 启动线程（生成 + ESC 检测）
        threads = []
        for target in (check_for_esc, generate_in_thread):
            t = threading.Thread(target=target, daemon=True)
            t.start()
            threads.append(t)

        try:
            # 主线程等待：ESC 或 响应完成
            while not response_ready.is_set() and not esc_pressed.is_set():
                time.sleep(0.1)

            # ESC 被按下 → 取消
            if esc_pressed.is_set():
                if is_tty:
                    print("\r" + " " * 80 + "\r", end="", flush=True)
                print(f"\n{Fore.YELLOW}⚡ AI 请求已取消 (ESC){Style.RESET_ALL}")
                return "[AI请求已取消]"

            # 响应正常返回：清除等待行，不做逐字流式打印。
            # 完整结果由 process_conversation 统一经 _display_response 透出（含展示层截断）。
            response = response_result[0]
            if is_tty:
                print("\r" + " " * 80 + "\r", end="", flush=True)

            if response and self.shared_conversation_history is not None:
                self.shared_conversation_history.append({
                    "role": "assistant",
                    "content": response
                })

            return response

        finally:
            for t in threads:
                t.join(timeout=1)

    # ── Plan 模式（只读规划 → 审批 → 执行）──

    def _sync_current_plan(self):
        """Plan 模式下，把对话历史中最后一条 assistant 内容记为当前计划。"""
        if not getattr(self, 'plan_mode', False):
            return
        for msg in reversed(self.shared_conversation_history):
            if isinstance(msg, dict) and msg.get("role") == "assistant" and msg.get("content"):
                self.current_plan = msg["content"]
                break

    def handle_plan_command(self, args):
        """处理 /plan 命令。进入 PLAN 模式（只读规划）。

        /plan            进入模式，等待描述任务
        /plan <任务>     进入模式并立即只读调研、生成实施计划
        /plan off|exit   退出模式（计划不执行）
        """
        args = (args or "").strip()
        if args in ('off', 'exit', '退出', 'cancel'):
            self.plan_mode = False
            emit(self, f"{Fore.YELLOW}已退出 PLAN 模式（计划未执行）{Style.RESET_ALL}")
            return

        self.plan_mode = True
        try:
            from .notify_sound import play
            play("notify")   # 待你确认/批准 → 气泡音
        except Exception:
            pass
        if args:
            emit(self, f"{Fore.CYAN}已进入 PLAN 模式，正在只读调研并生成实施计划...{Style.RESET_ALL}")
            self.process_conversation(args)
            self._autosave_session()
            self._sync_current_plan()
        else:
            emit(self, f"{Fore.CYAN}已进入 PLAN 模式。{Style.RESET_ALL}")
            emit(self, f"  描述你的任务，AI 将只做只读调研并给出实施计划；"
                  f"完成后用 {Fore.WHITE}/build{Style.RESET_ALL} 批准执行，或 "
                  f"{Fore.WHITE}/plan off{Style.RESET_ALL} 取消。{Style.RESET_ALL}")

    def handle_agent_command(self, arg: str):
        """@<agent名> <任务> 委派给指定 agent 独立执行。"""
        mgr = getattr(self, 'agent_manager', None)
        if mgr is None:
            emit(self, f"{Fore.RED}Agents 管理器未初始化{Style.RESET_ALL}")
            return
        if not arg:
            names = mgr.names()
            if names:
                emit(self, f"{Fore.CYAN}可用 Agents: {', '.join(names)}{Style.RESET_ALL}")
            else:
                emit(self, f"{Fore.YELLOW}暂无 agent 定义（在 agents/ 目录放置 *.md）{Style.RESET_ALL}")
            return
        parts = arg.split(maxsplit=1)
        name = parts[0]
        task = parts[1] if len(parts) > 1 else ""
        agent = mgr.get(name)
        if not agent:
            emit(self, f"{Fore.RED}未找到 agent: {name}{Style.RESET_ALL}")
            return
        emit(self, f"{Fore.CYAN}委派给 agent「{agent.name}」: {task}{Style.RESET_ALL}")
        try:
            result = mgr.dispatch(name, task, self._agent_runner)
        except Exception as e:
            emit(self, f"{Fore.RED}agent 执行失败: {e}{Style.RESET_ALL}")
            return
        emit(self, f"{Fore.GREEN}{result}{Style.RESET_ALL}")

    def _agent_runner(self, system_prompt, task, tools, model):
        """agent 执行器：用当前引擎跑一轮独立上下文（不污染主会话）。"""
        engine = getattr(self, 'current_engine', None) or getattr(self, 'engine', None)
        if engine is None:
            return "错误：当前无可用的 AI 引擎"
        prompt = task
        if system_prompt:
            prompt = f"{system_prompt}\n\n---\n用户任务：\n{task}"
        return engine.generate_response(prompt, system_prompt=system_prompt)

    def handle_build_command(self):
        """处理 /build 命令。从 PLAN 模式进入执行（用已批准计划驱动）。"""
        plan = getattr(self, 'current_plan', '') or ""
        if not getattr(self, 'plan_mode', False) and not plan.strip():
            emit(self, f"{Fore.YELLOW}当前不在 PLAN 模式，且无已生成的计划{Style.RESET_ALL}")
            return

        self.plan_mode = False
        if not plan.strip():
            emit(self, f"{Fore.YELLOW}尚未生成实施计划，先 /plan 描述任务让 AI 调研{Style.RESET_ALL}")
            return

        emit(self, f"{Fore.GREEN}已批准计划，开始执行...{Style.RESET_ALL}")
        try:
            from .notify_sound import play
            play("special")   # 特殊节点：开工
        except Exception:
            pass
        instruction = ("【已批准的实施计划，请现在严格按照以下步骤执行，利用可用工具完成每一步；"
                       "遇到与计划不符的情况先说明再继续】\n\n" + plan)
        self.process_conversation(instruction)
        self._autosave_session()

    # ── CLI 主循环 ──

    def run_tui(self):
        """运行 TUI 模式（默认入口，opencode 式；textual 不可用时回退 rich 面板）"""
        # 非交互静默初始化 diff 模式（TUI 启动不弹问题；用 /diff 可改）
        self._ask_diff_popup_mode(interactive=False)
        if TEXTUAL_AVAILABLE:
            from .tui import XiaoliTUI
            app = XiaoliTUI(self)
            app.run()
            return
        # 回退 rich 面板 TUI（textual 不可用时）
        try:
            from .rich_tui import RichTUI
            from xcli_core.constants import VERSION as _V
            tui = RichTUI(self)
            tui.version = _V
            tui.set_status(
                engine=getattr(self.current_engine, 'name', '') if self.current_engine else '',
                model=getattr(self.current_engine, 'model', '') if self.current_engine else '',
                mode='TUI',
            )
            self.tui_output_callback = tui.push
            tui.run()
            self.tui_output_callback = None
        except ImportError:
            print(f"{Fore.RED}TUI 不可用: 请安装 textual (pip install textual){Style.RESET_ALL}")

    def run(self):
        """运行 CLI"""
        import uuid
        self.user_id = str(uuid.getnode())
        current_engine_name = getattr(self.current_engine, 'name', '未设置') if self.current_engine else '未设置'
        model_name = getattr(self.current_engine, 'model', '') if self.current_engine else ''
        engine_desc = f"{current_engine_name} ({model_name})" if model_name else current_engine_name

        print(f"{Fore.GREEN}小狸 Pro-CLI v{VERSION} 已启动!{Style.RESET_ALL} "
              f"{Fore.WHITE}引擎: {engine_desc}{Style.RESET_ALL}")

        # 一行速览，完整命令清单收进 /help
        print(f"{Fore.CYAN}/help 全部命令 · /quit 退出 · /tui 图形界面 · "
              f"/model 换模型 · /resume 恢复会话 · /plan 规划模式 · @文件路径 读文件给 AI{Style.RESET_ALL}")

        # 历史会话提示（opencode 式 /resume）
        try:
            sessions = self.session_manager.list_sessions()
            if sessions:
                latest = sessions[0]
                print(f"{Fore.YELLOW}有 {len(sessions)} 个历史会话，/resume 可恢复"
                      f"（最近: {latest.id} · {latest.title}）{Style.RESET_ALL}")
        except Exception:
            pass

        extras = []
        loaded_engines = list(self.engines.keys())
        if len(loaded_engines) > 1:
            extras.append(f"可切换引擎: {', '.join(loaded_engines)}")
        # 进程保护：只在有未生效项时才提示，全绿就闭嘴
        if getattr(self, 'protection_results', None):
            r = self.protection_results
            failed = [n for k, n in (('single_instance', '单实例'), ('priority', '优先级'),
                                     ('ppl_protection', 'PPL保护'), ('watchdog', '看门狗'))
                      if not r.get(k)]
            if failed:
                extras.append(f"进程保护未生效: {', '.join(failed)}")
        if extras:
            print(f"{Fore.BLACK}{Style.BRIGHT}{' · '.join(extras)}{Style.RESET_ALL}")

        print(f"{Fore.BLACK}{Style.BRIGHT}用户ID: {self.user_id}{Style.RESET_ALL}")

        # 恢复 diff 显示模式（首次运行才询问）
        self._ask_diff_popup_mode()

        self._run_cli_loop()

    def _get_code_editor_plugin(self):
        """拿到 code_editor 插件实例（找不到返回 None）"""
        for tool in self.liugin_manager.tools:
            if tool.get('name') == 'code_editor':
                return getattr(tool.get('handler'), '__self__', None)
        return None

    def _ask_diff_popup_mode(self, interactive=True):
        """设置 diff 显示模式：已保存过就静默沿用；首次运行时 CLI 交互询问，
        TUI（interactive=False）静默用默认内联模式，不阻塞启动。"""
        plugin_instance = self._get_code_editor_plugin()
        if plugin_instance is None:
            return

        saved = get_system_config('diff_popup_mode', None)
        if saved is not None:
            plugin_instance.diff_popup_mode = bool(saved)
            return

        if not interactive:
            plugin_instance.diff_popup_mode = False
            return

        print(f"\n{Fore.CYAN}  Diff 显示模式（AI 修改文件后的对比方式）:{Style.RESET_ALL}")
        print(f"    {Fore.WHITE}1{Style.RESET_ALL} - 弹窗模式（新终端窗口显示）")
        print(f"    {Fore.WHITE}2{Style.RESET_ALL} - 主终端内显示（SSH 兼容，推荐）")

        try:
            choice = input(f"\n{Fore.WHITE}  请选择 [1/2]（默认 2，之后可用 /diff 改）: {Style.RESET_ALL}").strip()
        except (EOFError, KeyboardInterrupt):
            choice = '2'

        self._set_diff_popup_mode(choice == '1', plugin_instance)
        print()

    def _set_diff_popup_mode(self, popup, plugin_instance=None):
        """写入并持久化 diff 显示模式"""
        if plugin_instance is None:
            plugin_instance = self._get_code_editor_plugin()
        if plugin_instance is not None:
            plugin_instance.diff_popup_mode = bool(popup)
        set_system_config('diff_popup_mode', bool(popup))
        label = '弹窗模式' if popup else '主终端内显示'
        print(f"{Fore.GREEN}  ✓ Diff 显示模式: {label}{Style.RESET_ALL}")

    def _handle_cli_command(self, user_input) -> bool:
        """CLI 内置命令分发（自 _run_cli_loop 拆出，行为等价）。

        返回 True = 命令已处理（继续下一轮输入）；False = 非命令（落入对话）。
        """
        # @agent 委派（opencode 式 Agents 体系化）
        if user_input.startswith('@'):
            self.handle_agent_command(user_input[1:].strip())
            return True

        if user_input == '/help':
            self.show_help()
            return True

        if user_input.startswith('/help '):
            liugin_name = user_input[6:].strip()
            self.show_liugin_help(liugin_name)
            return True

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
            return True

        if user_input.startswith('/engine.'):
            engine_command = user_input[8:].strip()
            if not self.handle_engine_command(engine_command):
                print(f"{Fore.RED}当前引擎不支持该命令或命令执行失败{Style.RESET_ALL}")
            return True

        # /model 命令族 — OpenAI 引擎多模型在线增删切换
        if user_input == '/model' or user_input.startswith('/model '):
            self.handle_model_command(user_input[7:].strip())
            return True

        # /providers — opencode 式原生多 Provider 注册与状态一览
        if user_input == '/providers' or user_input.startswith('/providers '):
            self.handle_providers_command(user_input[11:].strip())
            return True

        # /plan 进入 PLAN 模式（只读规划 → 审批 → 执行）
        if user_input == '/plan' or user_input.startswith('/plan '):
            sub = user_input[6:].strip() if user_input.startswith('/plan ') else ''
            self.handle_plan_command(sub)
            return True
        if user_input == '/build':
            self.handle_build_command()
            return True

        # /resume 会话恢复（opencode 式自动持久化 + 一键恢复）
        if user_input in ('/resume', '/sessions') or \
           user_input.startswith('/resume ') or user_input.startswith('/sessions ') or \
           user_input.startswith('/session '):
            if user_input.startswith('/resume'):
                self.handle_resume_command(user_input[7:].strip())
            elif user_input.startswith('/sessions'):
                self.handle_resume_command(user_input[9:].strip())
            else:  # /session <子命令>
                sub = user_input[8:].strip()
                self.handle_resume_command(sub if sub != 'new' else 'new')
            return True

        # /manual 已随引擎架构删除（一切模型皆 OpenAI 格式），留提示桩引导
        if user_input == '/manual' or user_input.startswith('/manual '):
            emit(self, f"{Fore.YELLOW}/manual 已移除：引擎架构已删，一切模型皆 OpenAI 兼容格式。"
                       f"用 /model add 添加模型、/model 切换{Style.RESET_ALL}")
            return True

        if user_input.startswith('/file.read '):
            args = user_input[11:].strip()
            parts = args.split(' ', 2)
            if len(parts) < 1:
                print(f"{Fore.RED}请提供文件名.用法: /file.read <文件名> [行数]{Style.RESET_ALL}")
                return True
            filename = parts[0]
            max_lines = None
            if len(parts) >= 2:
                try:
                    max_lines = int(parts[1])
                    if max_lines <= 0:
                        print(f"{Fore.RED}行数必须是正整数{Style.RESET_ALL}")
                        return True
                except ValueError:
                    print(f"{Fore.RED}行数必须是正整数{Style.RESET_ALL}")
                    return True
            result = self._read_file_direct(filename, max_lines)
            print(f"{Fore.GREEN}{result}{Style.RESET_ALL}")
            return True

        if user_input.startswith('/chat '):
            chat_command = user_input[6:].strip()
            if chat_command.startswith('save '):
                name = chat_command[5:].strip()
                if name:
                    self.save_chat_history(name)
                else:
                    print(f"{Fore.RED}请提供聊天记录名称.用法: /chat save <名称>{Style.RESET_ALL}")
                return True
            elif chat_command == 'list':
                self.list_chat_history()
                return True
            elif chat_command.startswith('open '):
                name = chat_command[5:].strip()
                if name:
                    self.load_chat_history(name)
                else:
                    print(f"{Fore.RED}请提供聊天记录名称.用法: /chat open <名称>{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.RED}未知的聊天命令.可用命令: save, list, open{Style.RESET_ALL}")
                return True

        if user_input.startswith('/plugin'):
            plugin_args = user_input[7:].strip()
            result = self.handle_plugin_command(plugin_args)
            if result:
                print(result)
            return True

        if user_input.startswith('/protect'):
            parts = user_input.split()
            if len(parts) > 1 and parts[1] == 'test':
                # 重新测试所有保护
                from .process_protection import enable_process_protection
                results = enable_process_protection()
                print(f"\n{Fore.CYAN}  进程保护测试结果:{Style.RESET_ALL}")
                for key, val in results.items():
                    icon = '' if val else ''
                    print(f"    {icon} {key}: {val}")
            else:
                status = get_protection_status()
                print(f"\n{Fore.CYAN}  进程保护状态:{Style.RESET_ALL}")
                print(f"    平台: {status.get('platform', '未知')}")
                icon = '' if status.get('is_protected') else ''
                print(f"    {icon} 保护已启用: {status.get('is_protected', False)}")
                icon = '' if status.get('single_instance_held') else ''
                print(f"    {icon} 单实例锁: {status.get('single_instance_held', False)}")
                icon = '' if status.get('watchdog_running') else ''
                print(f"    {icon} 看门狗: {status.get('watchdog_running', False)}")
                print(f"      关闭钩子: {status.get('shutdown_hooks_count', 0)} 个")
            return True

        if user_input.startswith('/remote'):
            remote_command = user_input[7:].strip()
            self._handle_remote_command(remote_command)
            return True

        if user_input == '/about':
            self._read_about_file()
            return True

        if user_input == '/tui':
            print(f"{Fore.CYAN}正在切换到 TUI 模式...{Style.RESET_ALL}")
            self.run_tui()
            print(f"{Fore.CYAN}已从 TUI 模式返回 CLI 模式{Style.RESET_ALL}")
            return True

        if user_input == '/compress':
            if hasattr(self, 'memory_manager') and self.memory_manager:
                engine = self.current_engine
                before = len(self.shared_conversation_history)
                self.shared_conversation_history = self.memory_manager.compress_context(
                    self.shared_conversation_history, engine=engine)
                self._set_shared_conversation_history()
                print(f"{Fore.CYAN}已手动压缩上下文: {before} → {len(self.shared_conversation_history)} 条{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}记忆系统未加载，无法压缩{Style.RESET_ALL}")
            return True

        if user_input.startswith('/memory mode '):
            mode = user_input[len('/memory mode '):].strip().lower()
            if mode in ('companion', 'work'):
                try:
                    set_system_config('memory_mode', mode)
                except Exception:
                    pass
                print(f"{Fore.GREEN}记忆模式已设为: {mode}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}用法: /memory mode <companion|work>{Style.RESET_ALL}")
            return True

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
                    return True
            else:
                # 无参数：循环切换
                safety.cycle_mode()
            mode_name = safety.get_mode_name()
            icons = {"无限制": "", "普通": "", "人工确认": ""}
            icon = icons.get(mode_name, "")
            print(f"{icon} 安全模式: {mode_name}")
            return True

        if user_input.startswith('/diff'):
            parts = user_input.split()
            if self._get_code_editor_plugin() is None:
                print(f"{Fore.YELLOW}code_editor 插件未加载，无法设置 diff 模式{Style.RESET_ALL}")
                return True
            if len(parts) > 1:
                arg = parts[1].lower()
                if arg in ('popup', '弹窗', '1'):
                    self._set_diff_popup_mode(True)
                elif arg in ('inline', '内联', '主终端', '2'):
                    self._set_diff_popup_mode(False)
                else:
                    print(f"{Fore.RED}用法: /diff [popup|inline]{Style.RESET_ALL}")
            else:
                cur = bool(get_system_config('diff_popup_mode', False))
                self._set_diff_popup_mode(not cur)
            return True

        if user_input.startswith('/fc'):
            from .fc_tools import get_fc_cache, reset_fc_cache
            parts = user_input.split()
            if len(parts) > 1 and parts[1].lower() in ('reset', 'clear', '清除'):
                n = reset_fc_cache()
                print(f"{Fore.GREEN}已清除 {n} 条 FC 探测记录，下次请求会重新试探{Style.RESET_ALL}")
            else:
                cache = get_fc_cache()
                if not cache:
                    print(f"{Fore.GREEN}FC 探测缓存为空：所有模型都按支持 function calling 处理{Style.RESET_ALL}")
                else:
                    print(f"{Fore.CYAN}已探测到不支持 function calling 的模型:{Style.RESET_ALL}")
                    for key, ok in cache.items():
                        if ok is False:
                            print(f"  {Fore.YELLOW}✗{Style.RESET_ALL} {key}")
                    print(f"{Fore.WHITE}这些请求会自动跳过 tools 字段；/fc reset 可清除重测{Style.RESET_ALL}")
            return True

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
            return True

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
                return True

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
            return True

        return False

    def _run_cli_loop(self):
        """运行 CLI 主循环"""
        while True:
            try:
                user_input = input(f"\n{Fore.WHITE}> {Style.RESET_ALL}").strip()

                if user_input == '/quit':
                    print(f"{Fore.GREEN}再见!{Style.RESET_ALL}")
                    break

                # 内置命令分发（/help /engine /model /providers /plan /resume …）
                if self._handle_cli_command(user_input):
                    continue

                if '@' in user_input:
                    processed_input = self._process_file_paths(user_input)
                    if processed_input != user_input:
                        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
                        user_input = processed_input
                        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")

                self.process_conversation(user_input)
                # 自动持久化当前会话（opencode 式 /resume 落盘）
                self._autosave_session()
                # Plan 模式下：把本轮最后一条 assistant 内容记为当前计划
                self._sync_current_plan()
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

    def _safe_print(line):
        try:
            print(line, flush=True)
        except UnicodeEncodeError:
            print(line.encode('gbk', errors='ignore').decode('gbk'), flush=True)

    # 完整开机动画（57 行 + 逐行 0.05s）默认不放，用 --logo 显式召唤
    if '--logo' in sys.argv or '--banner' in sys.argv:
        for line in art_lines:
            _safe_print(line)
            time.sleep(0.05)
    else:
        _safe_print(f"\n{Fore.CYAN}  ▄▀▄  小狸 Pro-CLI v{VERSION}{Style.RESET_ALL}")
        _safe_print(f"{Fore.CYAN}  ▀▄▀  {Style.RESET_ALL}"
                    f"{Fore.WHITE}AI 智能编程助手{Style.RESET_ALL}"
                    f"  {Fore.BLACK}{Style.BRIGHT}(--logo 看完整开机动画){Style.RESET_ALL}")

    cli = AICLI()
    # opencode 式默认 TUI；--cli / --no-tui 回退命令行模式
    if '--cli' in sys.argv or '--no-tui' in sys.argv:
        cli.run()
    else:
        cli.run_tui()
        # TUI 里 /cli 请求切换命令行时，接管进入 CLI 主循环
        if getattr(cli, '_switch_to_cli', False):
            cli.run()
