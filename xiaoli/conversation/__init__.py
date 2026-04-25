"""响应解析器 - 从 AI 响应中提取文本和工具调用"""
import re
import json
import logging
from colorama import Fore, Style
from typing import Tuple, Optional, Union

logger = logging.getLogger(__name__)


def parse_response(response: str) -> Tuple[str, Optional[Union[dict, list]]]:
    """
    解析混合响应，分离文本和 JSON 工具调用

    Returns:
        (text_content, json_data)
        json_data 可以是 dict（单个调用）或 list（批量调用），或 None
    """
    response = response.strip()
    if not response:
        return "", None

    # 方法1: <tool_call> 格式修复
    if response.startswith("<tool_call>"):
        try:
            parsed = json.loads("{" + response[11:])
            if isinstance(parsed, dict):
                return "", parsed
        except json.JSONDecodeError:
            pass

    # 方法2: 纯 JSON
    try:
        parsed = json.loads(response)
        if isinstance(parsed, (dict, list)):
            return "", parsed
    except json.JSONDecodeError:
        pass

    # 方法3: 代码块中的 JSON
    pattern = r"```(?:json)?\s*({.*?})\s*```"
    matches = re.findall(pattern, response, re.DOTALL)
    if matches:
        try:
            data = json.loads(matches[-1])
            if isinstance(data, (dict, list)):
                text = re.sub(pattern, "", response, flags=re.DOTALL).strip()
                return re.sub(r"\n\s*\n", "\n\n", text).strip(), data
        except json.JSONDecodeError:
            pass

    # 方法4: 每行独立 JSON
    lines = response.split("\n")
    json_objs = []
    text_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                obj = json.loads(stripped)
                if isinstance(obj, dict):
                    json_objs.append(obj)
                    continue
            except json.JSONDecodeError:
                pass
        text_lines.append(line)

    if json_objs:
        text = "\n".join(text_lines).strip()
        return (text, json_objs[0]) if len(json_objs) == 1 else (text, json_objs)

    # 方法5: 内联 JSON（use_tool / continue）
    for marker in ['{"action": "use_tool"', '{"action": "continue"',
                   '{"action":"use_tool"', '{"action":"continue"']:
        idx = response.find(marker)
        if idx != -1:
            brace = 0
            for i in range(idx, len(response)):
                if response[i] == '{':
                    brace += 1
                elif response[i] == '}':
                    brace -= 1
                    if brace == 0:
                        try:
                            data = json.loads(response[idx:i + 1])
                            if isinstance(data, dict) and data.get('action') in ['use_tool', 'continue']:
                                return response[:idx].strip(), data
                        except json.JSONDecodeError:
                            pass
                        break

    return response, None


def process_thinking(response: str, engine=None) -> str:
    """处理深度思考标记，返回纯回复内容"""
    # <think/> 格式
    if '<think/>' in response:
        parts = response.split('<think/>', 1)
        if len(parts) >= 2:
            thinking = parts[0].strip()
            reply = parts[1].strip()
            if thinking:
                short = thinking[:200] + "..." if len(thinking) > 200 else thinking
                print(f"{Fore.LIGHTBLACK_EX}[思考: {short}]{Style.RESET_ALL}")
            return reply if reply else ""

    # 自定义标记
    if engine:
        start = getattr(engine, 'thinking_start_marker', None)
        end = getattr(engine, 'thinking_end_marker', None)
        if start and end and start in response and end in response:
            parts = response.split(start, 1)
            if len(parts) > 1 and end in parts[1]:
                thinking, reply = parts[1].split(end, 1)
                if thinking.strip():
                    short = thinking.strip()[:200]
                    print(f"{Fore.LIGHTBLACK_EX}[思考: {short}]{Style.RESET_ALL}")
                return reply.strip()

    return response


def process_code_blocks(text: str) -> str:
    """处理三引号代码块，红色显示"""
    def replace(m):
        inner = m.group(1)[3:-3]
        return f'{Fore.RED}{inner}{Style.RESET_ALL}'
    return re.sub(r'(""".*?""")', replace, text, flags=re.DOTALL)


def extract_tool_calls(json_data) -> list:
    """从 JSON 数据中提取工具调用列表（支持多种格式）"""
    calls = []

    if isinstance(json_data, dict):
        json_data = [json_data]

    if not isinstance(json_data, list):
        return calls

    for item in json_data:
        if not isinstance(item, dict):
            continue

        # 小狸格式
        if item.get('action') == 'use_tool':
            calls.append(item)
        # 简化格式
        elif 'tool' in item and 'args' in item:
            calls.append(item)
        # OpenAI function_call
        elif 'function_call' in item:
            fc = item['function_call']
            args = fc.get('arguments', '')
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except:
                    pass
            calls.append({
                'tool': fc.get('name', ''),
                'args': args if isinstance(args, str) else '',
                'arguments': args if isinstance(args, dict) else None
            })
        # MCP 格式
        elif 'name' in item and 'arguments' in item:
            args = item.get('arguments', '')
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except:
                    pass
            calls.append({
                'tool': item.get('name', ''),
                'args': args if isinstance(args, str) else '',
                'arguments': args if isinstance(args, dict) else None
            })

    return calls
