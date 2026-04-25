"""对话历史管理测试"""
import os
import sys
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xiaoli.conversation.history import History


class TestHistory:
    """History 类测试"""

    def test_add_message(self, history_dir):
        h = History(history_dir)
        h.add("user", "hello")
        h.add("assistant", "hi there")
        assert len(h.messages) == 2
        assert h.messages[0] == {"role": "user", "content": "hello"}
        assert h.messages[1] == {"role": "assistant", "content": "hi there"}

    def test_get_messages(self, history_dir):
        h = History(history_dir)
        h.add("user", "q1")
        h.add("assistant", "a1")
        msgs = h.get()
        assert len(msgs) == 2
        assert msgs[0]['role'] == 'user'

    def test_clear(self, history_dir):
        h = History(history_dir)
        h.add("user", "hello")
        h.add("assistant", "hi")
        h.clear()
        assert len(h.messages) == 0

    def test_max_items(self, history_dir):
        h = History(history_dir, max_items=3)
        for i in range(5):
            h.add("user", f"msg {i}")
        assert len(h.messages) == 3
        assert h.messages[0]['content'] == 'msg 2'

    def test_save_and_load(self, history_dir):
        h = History(history_dir)
        h.add("user", "hello")
        h.add("assistant", "hi")
        assert h.save("test_chat")

        h2 = History(history_dir)
        assert h2.load("test_chat")
        assert len(h2.messages) == 2
        assert h2.messages[0]['content'] == 'hello'

    def test_load_nonexistent(self, history_dir, capsys):
        h = History(history_dir)
        result = h.load("nonexistent_chat")
        assert not result

    def test_list_saved(self, history_dir, capsys):
        h = History(history_dir)
        h.add("user", "test")
        h.save("chat1")
        h.save("chat2")

        h2 = History(history_dir)
        h2.list_saved()  # should not raise
        captured = capsys.readouterr()
        assert 'chat1' in captured.out or 'chat2' in captured.out

    def test_list_saved_empty(self, history_dir, capsys):
        h = History(history_dir)
        h.list_saved()
        captured = capsys.readouterr()
        assert 'no' in captured.out.lower() or '没有' in captured.out

    def test_set_all(self, history_dir):
        h = History(history_dir)
        msgs = [
            {"role": "user", "content": "q"},
            {"role": "assistant", "content": "a"},
        ]
        h.set_all(msgs)
        assert len(h.messages) == 2
        assert h.messages == msgs

    def test_save_creates_directory(self, tmp_dir):
        nested_dir = os.path.join(tmp_dir, "deep", "nested", "history")
        h = History(nested_dir)
        h.add("user", "test")
        h.save("test")
        assert os.path.exists(os.path.join(nested_dir, "test.json"))

    def test_save_file_format(self, history_dir):
        h = History(history_dir)
        h.add("user", "hello")
        h.save("format_test")

        path = os.path.join(history_dir, "format_test.json")
        with open(path, 'r') as f:
            data = json.load(f)
        assert 'timestamp' in data
        assert 'conversation' in data
        assert len(data['conversation']) == 1

    def test_load_corrupted_file(self, history_dir):
        path = os.path.join(history_dir, "corrupt.json")
        with open(path, 'w') as f:
            f.write("{bad json")

        h = History(history_dir)
        result = h.load("corrupt")
        assert not result
