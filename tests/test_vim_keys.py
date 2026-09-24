"""VimInputState 纯逻辑单测（不依赖 textual）。

用一个极简 FakeBuffer 持有 (text, offset)，把 EditResult 应用回去，
逐动作断言文本/光标/模式变化。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xcli_core.vim_keys import VimInputState


class FakeBuffer:
    """模拟输入框：持有 text 与 cursor offset。"""
    def __init__(self, text, offset, mode="INSERT"):
        self.st = VimInputState(mode=mode)
        self.text = text
        self.offset = offset

    def press(self, token):
        res = self.st.feed(self.text, self.offset, token)
        self.text = res.text
        self.offset = res.offset
        return res

    def press_seq(self, *tokens):
        return [self.press(t) for t in tokens]


def test_escape_enters_normal_and_steps_left():
    b = FakeBuffer("hello", 5, mode="INSERT")
    r = b.press("escape")
    assert b.st.mode == "NORMAL"
    assert b.offset == 4
    assert r.message == "-- NORMAL --"


def test_normal_h_l_clamp():
    b = FakeBuffer("hello", 0, mode="NORMAL")
    b.press("h")                       # 行首不动
    assert b.offset == 0
    b.press_seq("l", "l", "l", "l", "l")  # 走到末尾
    assert b.offset == 5
    b.press("l")                       # 末尾不动
    assert b.offset == 5


def test_j_k_move_lines():
    b = FakeBuffer("aa\nbb\ncc", 1, mode="NORMAL")  # 第0行 col1
    b.press("j")                       # 第1行 col1
    assert b.offset == 4              # "aa\n"=3 +1
    b.press("k")                       # 回第0行 col1
    assert b.offset == 1


def test_0_and_dollar():
    b = FakeBuffer("hello world", 5, mode="NORMAL")
    b.press("0")
    assert b.offset == 0
    b.press("$")
    assert b.offset == 11


def test_i_enters_insert():
    b = FakeBuffer("abc", 1, mode="NORMAL")
    r = b.press("i")
    assert b.st.mode == "INSERT"
    assert r.action is None


def test_a_insert_after():
    b = FakeBuffer("abc", 1, mode="NORMAL")
    r = b.press("a")
    assert b.st.mode == "INSERT"
    assert b.offset == 2


def test_o_opens_new_line():
    b = FakeBuffer("line1\nline2", 2, mode="NORMAL")  # 第0行
    r = b.press("o")
    assert b.st.mode == "INSERT"
    assert b.text == "line1\n\nline2"
    assert b.offset == 6               # "line1\n"=6


def test_O_opens_above():
    b = FakeBuffer("line1\nline2", 7, mode="NORMAL")  # 第1行 'l' of line2
    r = b.press("O")
    assert b.st.mode == "INSERT"
    assert b.text == "line1\n\nline2"
    assert b.offset == 6               # 新空行起始


def test_dd_deletes_line():
    b = FakeBuffer("aaa\nbbb\nccc", 4, mode="NORMAL")  # 第1行
    b.press_seq("d", "d")
    assert b.text == "aaa\nccc"
    assert b.offset == 4                # 回到第1行行首(aaa\n 之后)


def test_dw_deletes_word():
    b = FakeBuffer("foo bar baz", 0, mode="NORMAL")
    b.press_seq("d", "w")
    assert b.text == "bar baz"
    assert b.offset == 0


def test_d_dollar_deletes_to_eol():
    b = FakeBuffer("abc def", 2, mode="NORMAL")  # 第0行 col2 ('c')
    b.press_seq("d", "$")
    assert b.text == "ab"
    assert b.offset == 2


def test_x_deletes_char():
    b = FakeBuffer("abc", 1, mode="NORMAL")  # 'b'
    b.press("x")
    assert b.text == "ac"
    assert b.offset == 1


def test_w_b_word_motion():
    b = FakeBuffer("foo bar baz", 0, mode="NORMAL")
    b.press("w")
    assert b.offset == 4               # 下一词 "bar" 词首
    b.press("b")
    assert b.offset == 0


def test_gg_and_G():
    b = FakeBuffer("a\nb\nc", 4, mode="NORMAL")
    b.press_seq("g", "g")
    assert b.offset == 0
    b.press("G")
    assert b.offset == 4               # 末行同列


def test_u_sets_undo_action():
    b = FakeBuffer("hello", 2, mode="NORMAL")
    r = b.press("u")
    assert r.action == "undo"


def test_pending_cleared_on_invalid_combo():
    b = FakeBuffer("abc", 1, mode="NORMAL")
    b.press("d")                        # 进入待定
    assert b.st.pending == "d"
    b.press("x")                        # 非法组合 -> 清待定, 当普通键
    assert b.st.pending is None
    assert b.st.mode == "NORMAL"


def test_unmapped_key_ignored_in_normal():
    b = FakeBuffer("abc", 1, mode="NORMAL")
    r = b.press("z")                    # 未映射
    assert r.handled is True
    assert b.text == "abc"
    assert b.offset == 1


def test_insert_typing_delegated():
    b = FakeBuffer("abc", 1, mode="INSERT")
    r = b.press("h")                    # 非 Esc：交给输入框默认处理
    assert r.handled is False
