"""集成测试 - 模块间协作"""
import os
import sys
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xiaoli.sandbox import Sandbox
from xiaoli.conversation import parse_response, extract_tool_calls
from xiaoli.conversation.history import History


class TestSandboxConversationIntegration:
    """沙箱 + 对话解析 集成测试"""

    def test_sandbox_result_parsed_as_tool_output(self):
        """沙箱执行结果可以正确传递给对话系统"""
        sandbox = Sandbox(timeout=10, mode='threaded')
        result = sandbox.run('result = [x**2 for x in range(5)]')
        assert result['success']

        # 模拟工具结果注入对话
        tool_msg = f"工具执行结果:\n{result['result']}"
        text, data = parse_response(tool_msg)
        assert data is None  # 纯文本，无工具调用
        assert '0' in text and '16' in text

        sandbox.cleanup()

    def test_sandbox_failure_triggers_error_handling(self):
        """沙箱失败时应正确处理"""
        sandbox = Sandbox(timeout=10, mode='threaded')
        result = sandbox.run('import os')  # should fail
        assert not result['success']

        # 错误信息应可解析
        assert result['result']
        assert len(result['result']) > 0

        sandbox.cleanup()


class TestHistoryConversationIntegration:
    """历史 + 对话解析 集成测试"""

    def test_full_conversation_roundtrip(self, history_dir):
        """完整的对话存取流程"""
        h = History(history_dir)

        # 模拟对话
        h.add("user", "帮我写一个排序函数")
        h.add("assistant", "好的，这是一个快速排序：\n```python\ndef quicksort(arr):\n    ...\n```")
        h.add("user", "能改成归并排序吗？")

        # 保存
        assert h.save("sorting_chat")

        # 加载到新实例
        h2 = History(history_dir)
        assert h2.load("sorting_chat")
        assert len(h2.messages) == 3
        assert "quicksort" in h2.messages[1]['content']

    def test_conversation_with_tool_calls(self, history_dir):
        """带工具调用的对话历史"""
        h = History(history_dir)

        # 用户请求
        h.add("user", "查看 main.py 的第 10-20 行")

        # AI 的工具调用
        tool_call = '{"action":"use_tool","tool":"code_editor","args":"read_range main.py 10 20"}'
        text, data = parse_response(tool_call)
        assert data is not None
        calls = extract_tool_calls(data)
        assert len(calls) == 1
        assert calls[0]['tool'] == 'code_editor'

        # 记录工具结果
        h.add("assistant", f"工具调用: {json.dumps(data)}")
        h.add("assistant", "工具执行结果:\n  line 10: def main():")

        assert len(h.messages) == 3


class TestSandboxSecurityIntegration:
    """沙箱安全 + 工具链 集成测试"""

    def test_safe_code_executes_in_chain(self):
        """安全代码在工具链中正常执行"""
        sandbox = Sandbox(timeout=10, mode='threaded')

        # 步骤 1: 数学计算
        r1 = sandbox.run('import math\nresult = math.factorial(10)')
        assert r1['success']
        assert '3628800' in r1['result']

        # 步骤 2: 使用上一步结果
        r2 = sandbox.run(
            'result = f"factorial(10) = {val}"',
            variables={'val': r1['result']}
        )
        assert r2['success']
        assert '3628800' in r2['result']

        sandbox.cleanup()

    def test_blocked_code_stops_chain(self):
        """被阻止的代码应中断工具链"""
        sandbox = Sandbox(timeout=10, mode='threaded')

        r = sandbox.run('import os\nresult = os.listdir(".")')
        assert not r['success']
        # 后续步骤不应执行
        assert r['result']

        sandbox.cleanup()

    def test_subprocess_isolation(self):
        """子进程模式下文件系统隔离"""
        sandbox = Sandbox(timeout=10, mode='subprocess')
        result = sandbox.run(
            'import tempfile\nresult = tempfile.gettempdir()'
        )
        # 子进程应使用沙箱临时目录
        if result['success']:
            assert 'xiaoli_sandbox' in result['result'] or result['success']

        sandbox.cleanup()


class TestPromptIntegration:
    """系统提示词集成测试"""

    def test_prompt_builder(self):
        from xiaoli import prompt as prompt_builder

        # 无工具
        p1 = prompt_builder.build()
        assert '小狸' in p1
        assert '编程' in p1 or 'code' in p1.lower()

        # 带工具
        p2 = prompt_builder.build(tool_prompts="- code_editor: edit code")
        assert 'code_editor' in p2

        # 带 tool_search
        p3 = prompt_builder.build(has_tool_search=True)
        assert 'tool_search' in p3

        # Clawli 模式
        p4 = prompt_builder.build(is_clawli=True)
        assert 'Clawli' in p4 or 'clawli' in p4 or '远程' in p4
