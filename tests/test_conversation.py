"""对话响应解析器测试"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xiaoli.conversation import parse_response, process_thinking, process_code_blocks, extract_tool_calls


# ═══════════════════════════════════════════════
# 1. parse_response 测试
# ═══════════════════════════════════════════════

class TestParseResponse:
    """响应解析测试"""

    def test_pure_text(self):
        text, data = parse_response("hello world")
        assert text == "hello world"
        assert data is None

    def test_empty_response(self):
        text, data = parse_response("")
        assert text == ""
        assert data is None

    def test_pure_json_dict(self):
        resp = '{"action": "use_tool", "tool": "code_editor", "args": "read foo.py"}'
        text, data = parse_response(resp)
        assert text == ""
        assert isinstance(data, dict)
        assert data['action'] == 'use_tool'
        assert data['tool'] == 'code_editor'

    def test_pure_json_list(self):
        resp = '[{"action": "use_tool", "tool": "t1", "args": "a1"}]'
        text, data = parse_response(resp)
        assert text == ""
        assert isinstance(data, list)

    def test_json_in_code_block(self):
        resp = 'Here is the command:\n```json\n{"action": "use_tool", "tool": "git_tools", "args": "status"}\n```'
        text, data = parse_response(resp)
        assert 'command' in text.lower() or 'Here' in text
        assert isinstance(data, dict)
        assert data['tool'] == 'git_tools'

    def test_text_before_json(self):
        resp = 'I will edit the file.\n{"action": "use_tool", "tool": "code_editor", "args": "edit foo.py"}'
        text, data = parse_response(resp)
        assert 'edit' in text.lower()
        assert isinstance(data, dict)
        assert data['action'] == 'use_tool'

    def test_continue_action(self):
        resp = '{"action": "continue", "content": "more info"}'
        text, data = parse_response(resp)
        assert text == ""
        assert isinstance(data, dict)
        assert data['action'] == 'continue'

    def test_inline_json_use_tool(self):
        resp = 'Let me check. {"action":"use_tool","tool":"code_search","args":"find . test"}'
        text, data = parse_response(resp)
        assert isinstance(data, dict)
        assert data['tool'] == 'code_search'

    def test_inline_json_continue(self):
        resp = 'Some text. {"action":"continue","content":"extra"}'
        text, data = parse_response(resp)
        assert isinstance(data, dict)
        assert data['action'] == 'continue'

    def test_multiple_json_per_line(self):
        resp = '{"action":"use_tool","tool":"t1","args":"a1"}\n{"action":"use_tool","tool":"t2","args":"a2"}'
        text, data = parse_response(resp)
        # Should pick up at least one
        assert data is not None

    def test_invalid_json_ignored(self):
        resp = 'This is not json {broken'
        text, data = parse_response(resp)
        assert text == resp
        assert data is None

    def test_tool_call_tag_format(self):
        resp = '<tool_call>{"action":"use_tool","tool":"test","args":"arg"}'
        text, data = parse_response(resp)
        assert isinstance(data, dict)
        assert data['tool'] == 'test'

    def test_message_field(self):
        resp = '{"message": "done processing"}'
        text, data = parse_response(resp)
        assert isinstance(data, dict)
        assert data['message'] == 'done processing'


# ═══════════════════════════════════════════════
# 2. process_thinking 测试
# ═══════════════════════════════════════════════

class TestProcessThinking:
    """思考标记处理测试"""

    def test_think_tag(self):
        resp = '<think/>This is the reply'
        result = process_thinking(resp)
        assert result == 'This is the reply'

    def test_think_tag_with_thinking(self):
        resp = 'I am thinking deeply<think/>Here is my answer'
        result = process_thinking(resp)
        assert 'answer' in result

    def test_no_think_tag(self):
        resp = 'Just a normal response'
        result = process_thinking(resp)
        assert result == resp

    def test_empty_after_think(self):
        resp = '<think/>'
        result = process_thinking(resp)
        assert result == '' or result is not None

    def test_custom_markers(self):
        class FakeEngine:
            thinking_start_marker = '<thinking>'
            thinking_end_marker = '</thinking>'

        resp = '<thinking>deep thought</thinking>The answer is 42'
        result = process_thinking(resp, FakeEngine())
        assert '42' in result


# ═══════════════════════════════════════════════
# 3. process_code_blocks 测试
# ═══════════════════════════════════════════════

class TestProcessCodeBlocks:
    """代码块处理测试"""

    def test_triple_quote_block(self):
        text = 'before\n"""\ncode here\n"""\nafter'
        result = process_code_blocks(text)
        assert 'before' in result
        assert 'after' in result

    def test_no_code_blocks(self):
        text = 'plain text no blocks'
        result = process_code_blocks(text)
        assert result == text


# ═══════════════════════════════════════════════
# 4. extract_tool_calls 测试
# ═══════════════════════════════════════════════

class TestExtractToolCalls:
    """工具调用提取测试"""

    def test_single_use_tool(self):
        data = {"action": "use_tool", "tool": "code_editor", "args": "edit foo.py"}
        calls = extract_tool_calls(data)
        assert len(calls) == 1
        assert calls[0]['tool'] == 'code_editor'

    def test_list_of_use_tool(self):
        data = [
            {"action": "use_tool", "tool": "t1", "args": "a1"},
            {"action": "use_tool", "tool": "t2", "args": "a2"},
        ]
        calls = extract_tool_calls(data)
        assert len(calls) == 2

    def test_simplified_format(self):
        data = {"tool": "git_tools", "args": "status"}
        calls = extract_tool_calls(data)
        assert len(calls) == 1
        assert calls[0]['tool'] == 'git_tools'

    def test_openai_function_call(self):
        data = {"function_call": {"name": "code_editor", "arguments": '{"operation": "read"}'}}
        calls = extract_tool_calls(data)
        assert len(calls) == 1
        assert calls[0]['tool'] == 'code_editor'

    def test_mcp_format(self):
        data = {"name": "code_search", "arguments": {"operation": "find", "directory": "."}}
        calls = extract_tool_calls(data)
        assert len(calls) == 1
        assert calls[0]['tool'] == 'code_search'

    def test_empty_data(self):
        assert extract_tool_calls([]) == []
        assert extract_tool_calls({}) == []
        assert extract_tool_calls(None) == []
        assert extract_tool_calls("string") == []

    def test_non_tool_dict(self):
        data = {"message": "just text", "continue": True}
        calls = extract_tool_calls(data)
        # continue action should not be extracted as tool call
        assert len(calls) == 0

    def test_mixed_list(self):
        data = [
            {"action": "use_tool", "tool": "t1", "args": "a1"},
            {"action": "continue", "content": "more"},
        ]
        calls = extract_tool_calls(data)
        assert len(calls) == 1
        assert calls[0]['tool'] == 't1'

    def test_function_call_string_args(self):
        data = {"function_call": {"name": "test", "arguments": '{"key": "val"}'}}
        calls = extract_tool_calls(data)
        assert len(calls) == 1
        assert calls[0]['arguments'] == {"key": "val"}

    def test_function_call_dict_args(self):
        data = {"function_call": {"name": "test", "arguments": {"key": "val"}}}
        calls = extract_tool_calls(data)
        assert len(calls) == 1
        assert calls[0]['arguments'] == {"key": "val"}
