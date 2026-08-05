import sys
import time
import threading
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import Fore, Style

from .constants import UNIFIED_TOOL_MANAGER_AVAILABLE
from .safety import get_safety
from .tool_result import normalize_tool_dict, normalize_tool_text


class ToolMixin:
    """工具调用相关方法"""

    def _extract_tool_calls(self, json_data) -> list:
        """从 JSON 数据中提取工具调用列表（支持多种格式）"""
        tool_calls = []

        if isinstance(json_data, dict):
            # 格式1: 小狸自有格式
            if json_data.get('action') == 'use_tool':
                tool_calls.append(json_data)
            # 格式2: 简化格式
            elif 'tool' in json_data and 'args' in json_data:
                tool_calls.append(json_data)
            # 格式3: OpenAI function_call 格式
            elif 'function_call' in json_data:
                fc = json_data['function_call']
                if isinstance(fc, dict):
                    args = fc.get('arguments', '')
                    if isinstance(args, str) and args.startswith('{'):
                        try:
                            args = json.loads(args)
                        except:
                            pass
                    tool_calls.append({
                        'tool': fc.get('name', ''),
                        'args': args if isinstance(args, str) else '',
                        'arguments': args if isinstance(args, dict) else None
                    })
            # 格式4: MCP/Anthropic 格式
            elif 'name' in json_data and 'arguments' in json_data:
                args = json_data.get('arguments', '')
                if isinstance(args, str) and args.startswith('{'):
                    try:
                        args = json.loads(args)
                    except:
                        pass
                tool_calls.append({
                    'tool': json_data.get('name', ''),
                    'args': args if isinstance(args, str) else '',
                    'arguments': args if isinstance(args, dict) else None
                })
            # 格式5: OpenAI tool_calls 格式
            elif json_data.get('type') == 'function' and 'function' in json_data:
                func = json_data['function']
                args = func.get('arguments', '')
                if isinstance(args, str) and args.startswith('{'):
                    try:
                        args = json.loads(args)
                    except:
                        pass
                tool_calls.append({
                    'tool': func.get('name', ''),
                    'args': args if isinstance(args, str) else '',
                    'arguments': args if isinstance(args, dict) else None
                })
        elif isinstance(json_data, list):
            for item in json_data:
                if isinstance(item, dict):
                    if item.get('action') == 'use_tool':
                        tool_calls.append(item)
                    elif 'tool' in item and 'args' in item:
                        tool_calls.append(item)
                    elif 'name' in item and 'arguments' in item:
                        args = item.get('arguments', '')
                        if isinstance(args, str) and args.startswith('{'):
                            try:
                                args = json.loads(args)
                            except:
                                pass
                        tool_calls.append({
                            'tool': item.get('name', ''),
                            'args': args if isinstance(args, str) else '',
                            'arguments': args if isinstance(args, dict) else None
                        })

        return tool_calls if tool_calls else None

    def process_tool_call(self, tool_call_data):
        """处理工具调用(支持 Liugin 和 MCP 两种格式)"""
        try:
            tool_name = tool_call_data.get('tool')
            args = tool_call_data.get('args', '')
            arguments = tool_call_data.get('arguments')

            # ── 安全检查 ──
            safety = get_safety()
            allowed, msg = safety.check(tool_name, str(args))
            if not allowed:
                return {"result": f" 已取消: {msg}"}

            if UNIFIED_TOOL_MANAGER_AVAILABLE and hasattr(self.liugin_manager, 'execute'):
                if arguments and isinstance(arguments, dict):
                    result = self.liugin_manager.execute(tool_name, args, **arguments)
                else:
                    result = self.liugin_manager.execute(tool_name, args)
                # execute() 返回 ToolResult，必须归一成 dict——
                # 否则上层 result.get('result') 会报
                # "'ToolResult' object has no attribute 'get'"
                return normalize_tool_dict(result)

            # 回退：直接调用 handler（旧逻辑，handler 可能返回 ToolResult/str）
            for tool in self.liugin_manager.tools:
                if tool['name'] == tool_name:
                    try:
                        return normalize_tool_dict(tool['handler'](args))
                    except Exception as e:
                        return {"result": f"工具执行错误: {e}", "success": False}

            return {"result": f"未找到工具: {tool_name}"}

        except Exception as e:
            return {"result": f"处理工具调用时出错: {e}"}

    def process_tool_calls_concurrent(self, tool_calls_list):
        """并发批量执行工具调用，按顺序返回结果"""
        if not tool_calls_list:
            return []

        cancel_event = threading.Event()
        history_lock = threading.Lock()

        def execute_single_tool(tool_data, index):
            if cancel_event.is_set():
                return {"index": index, "result": "工具执行已取消"}
            try:
                result = self.process_tool_call(tool_data)
                tool_result = normalize_tool_text(result)
                with history_lock:
                    self.shared_conversation_history.append({
                        "role": "assistant",
                        "content": f"工具{index+1}执行结果:\n{tool_result}"
                    })
                return {"index": index, "result": tool_result}
            except Exception as e:
                error_msg = f"工具执行错误: {e}"
                with history_lock:
                    self.shared_conversation_history.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                return {"index": index, "result": error_msg}

        def supports_esc_detection():
            return sys.platform == 'win32'

        def check_key_input():
            try:
                import msvcrt
                return msvcrt.kbhit()
            except:
                return False

        def get_key():
            try:
                import msvcrt
                return msvcrt.getch()
            except:
                return None

        def detect_esc_key():
            if supports_esc_detection():
                while not cancel_event.is_set() and not all(f.done() for f in futures):
                    if check_key_input():
                        key = get_key()
                        if key == b'\x1b':
                            cancel_event.set()
                            break
                    time.sleep(0.1)

        with ThreadPoolExecutor(max_workers=min(len(tool_calls_list), 10)) as executor:
            futures = {executor.submit(execute_single_tool, tool_data, i): i
                      for i, tool_data in enumerate(tool_calls_list)}

            esc_thread = threading.Thread(target=detect_esc_key, daemon=True)
            esc_thread.start()

            results = []
            for future in as_completed(futures):
                if cancel_event.is_set():
                    for f in futures:
                        if not f.done():
                            f.cancel()
                    break
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    index = futures[future]
                    results.append({"index": index, "result": f"工具执行错误: {e}"})

            results.sort(key=lambda x: x['index'])
            return [r['result'] for r in results]

    def _execute_single_tool(self, tool_data):
        """执行单个工具（零等待，执行前非阻塞检测 ESC 取消）"""
        tool_name = tool_data.get('tool', '未知工具')
        tool_args = tool_data.get('args', '')
        if len(tool_args) > 30:
            tool_args_display = tool_args[:27] + "..."
        else:
            tool_args_display = tool_args

        # 非 TUI 模式：执行前零等待检查 ESC（不再做倒计时延迟，立即执行）
        showed_hint = False
        if not self.tui_output_callback:
            try:
                import msvcrt
                canceled = False
                # 排空键盘缓冲区：若在此之前按过 ESC 则取消（非阻塞，无等待）
                while msvcrt.kbhit():
                    if msvcrt.getch() == b'\x1b':
                        canceled = True
                if canceled:
                    print(f"{Fore.YELLOW}工具执行已取消（用户按ESC键）{Style.RESET_ALL}")
                    cancel_message = f"工具 {tool_name} 执行已被用户取消（按ESC键）。工具参数: {tool_args}"
                    self.shared_conversation_history.append({
                        "role": "assistant",
                        "content": cancel_message
                    })
                    return True
            except ImportError:
                pass

            try:
                sys.stdout.write(f"\r   正在执行: {tool_name} {tool_args_display}")
                sys.stdout.flush()
                showed_hint = True
            except Exception:
                pass

        tool_results = self.process_tool_call(tool_data)
        full_result = normalize_tool_text(tool_results)

        if showed_hint:
            try:
                sys.stdout.write("\r" + " " * 60 + "\r")
                sys.stdout.flush()
            except Exception:
                pass
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._display_tool_result(tool_name, tool_args, full_result, current_time)
        current_input = f"工具调用结果 (时间: {current_time}):\n{full_result}"
        self.shared_conversation_history.append({
            "role": "assistant",
            "content": f"工具调用结果 (时间: {current_time}):\n{full_result}"
        })
        self.process_conversation(current_input)

    def _execute_concurrent_tools(self, tool_calls_list):
        """并发批量执行工具调用"""
        if not tool_calls_list:
            return

        self._output(f"   正在批量执行 {len(tool_calls_list)} 个工具")

        results = self.process_tool_calls_concurrent(tool_calls_list)

        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for i, (tool_data, result) in enumerate(zip(tool_calls_list, results)):
            tool_name = tool_data.get('tool', '未知工具')
            tool_args = tool_data.get('args', '')
            self._display_tool_result(tool_name, tool_args, result, current_time)

        all_results = "\n".join([f"工具{i+1}结果:\n{result}" for i, result in enumerate(results)])
        current_input = f"批量工具调用结果 (时间: {current_time}):\n{all_results}"

        self.shared_conversation_history.append({
            "role": "assistant",
            "content": f"批量工具调用结果 (时间: {current_time}):\n{all_results}"
        })

        self.process_conversation(current_input)
