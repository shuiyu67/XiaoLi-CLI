"""
Vim 风格输入编辑状态机（纯逻辑，不依赖 textual）
================================================
把“模态编辑”的核心（NORMAL / INSERT 双模式 + 各种 motion / operator）抽成
纯函数 + 一个小状态类，便于在不依赖 textual 的环境里做单元测试。

widget 侧（tui.py 的 VimSendTextArea）只负责：
- 把 textual 的 key 名字映射成这里的 token（见 tui.py 的 _vim_token）
- 调用 VimInputState.feed(text, offset, token) 拿到 EditResult
- 把 EditResult 应用回 TextArea（设 text / 设光标 / 触发 undo 等）

坐标约定：文本用单一字符串表示，光标用「字符偏移 offset」表示（从 0 开始）。
widget 负责 offset <-> (row, col) 的转换。
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class EditResult:
    """一次 vim 动作的执行结果。"""
    text: str                       # 应用后的文本
    offset: int                     # 应用后的光标偏移
    mode: str                       # 结束时的模式: "INSERT" / "NORMAL"
    pending: Optional[str]          # 多键序列的待定前缀: "d" / "g" / None
    handled: bool = True            # False 表示“交给输入框默认处理”（仅 INSERT 非 Esc 键）
    action: Optional[str] = None    # 额外指令: "undo"
    message: str = ""               # 状态栏提示语


# ── 文本/坐标辅助 ──────────────────────────────────────────────────────────

def _line_start_off(text: str, off: int) -> int:
    """当前行行首偏移。"""
    s = text.rfind("\n", 0, off)
    return s + 1


def _line_end_off(text: str, off: int) -> int:
    """当前行行尾（不含换行符）偏移。"""
    e = text.find("\n", off)
    return e if e != -1 else len(text)


def _first_nonblank_off(text: str, off: int) -> int:
    """当前行第一个非空白字符偏移，若整行空白则回到行首。"""
    s = _line_start_off(text, off)
    e = _line_end_off(text, off)
    i = s
    while i < e and text[i].isspace():
        i += 1
    return i


def _word_forward_off(text: str, off: int) -> int:
    """跳到下一个 word 的词首（vim 的 w）：越过当前词 + 词间空白。"""
    n = len(text)
    i = off
    # 越过错当前空白
    while i < n and text[i].isspace():
        i += 1
    # 越过当前 word
    if i < n and (text[i].isalnum() or text[i] == "_"):
        while i < n and (text[i].isalnum() or text[i] == "_"):
            i += 1
    else:
        while i < n and not text[i].isspace() and not (text[i].isalnum() or text[i] == "_"):
            i += 1
    # 越过词间空白，落到下一词首
    while i < n and text[i].isspace():
        i += 1
    return i


def _word_back_off(text: str, off: int) -> int:
    """跳到上一个 word 的词首（vim 的 b）。"""
    i = off
    # 越过光标前空白
    while i > 0 and text[i - 1].isspace():
        i -= 1
    # 越过当前 word
    if i > 0 and (text[i - 1].isalnum() or text[i - 1] == "_"):
        while i > 0 and (text[i - 1].isalnum() or text[i - 1] == "_"):
            i -= 1
    else:
        while i > 0 and not text[i - 1].isspace() and not (text[i - 1].isalnum() or text[i - 1] == "_"):
            i -= 1
    # 越过词间空白，落到上一词首
    while i > 0 and text[i - 1].isspace():
        i -= 1
    return i


def _offset_to_rc(text: str, off: int):
    off = max(0, min(off, len(text)))
    row = text.count("\n", 0, off)
    line_start = text.rfind("\n", 0, off)
    col = off - (line_start + 1)
    return row, col


def _rc_to_offset(text: str, row: int, col: int) -> int:
    lines = text.split("\n")
    row = max(0, min(row, len(lines) - 1))
    line = lines[row]
    col = max(0, min(col, len(line)))
    off = 0
    for l in lines[:row]:
        off += len(l) + 1
    return off + col


# ── 状态机 ────────────────────────────────────────────────────────────────

class VimInputState:
    """
    Vim 输入状态机。

    mode:   "INSERT" 或 "NORMAL"
    pending: 多键序列待定前缀（"d" / "g"），单键动作时为 None

    用法：
        st = VimInputState(mode="INSERT")   # 输入框默认进入 INSERT
        res = st.feed(text, offset, token)
        # 把 res 应用回输入框
    """

    def __init__(self, mode: str = "INSERT"):
        self.mode = mode
        self.pending: Optional[str] = None

    # 进入 INSERT 时返回的结果构造器
    @staticmethod
    def _insert(text, offset, msg) -> EditResult:
        return EditResult(text, offset, "INSERT", None, message=msg)

    def feed(self, text: str, offset: int, token: str) -> EditResult:
        """
        token 是已经映射好的 vim 键名，例如:
        "h","l","j","k","w","b","e","0","$","^","g","G","d","x","u",
        "i","a","o","O","I","A","escape","left","right","up","down"
        """
        if self.mode == "INSERT":
            if token == "escape":
                # 回到 NORMAL，光标左移一格（vim 习惯：Esc 后光标退到本字上）
                new_off = offset
                if offset > 0 and text[offset - 1] != "\n":
                    new_off = offset - 1
                self.mode = "NORMAL"
                self.pending = None
                return EditResult(text, new_off, "NORMAL", None, message="-- NORMAL --")
            # 其余键交给 TextArea 默认处理（打字）
            return EditResult(text, offset, "INSERT", None, handled=False)

        # ── NORMAL 模式 ──
        # 多键序列待定前缀
        if self.pending == "d":
            self.pending = None
            if token == "d":
                return self._delete_line(text, offset, "dd")
            if token == "w":
                return self._delete_word(text, offset, "dw")
            if token == "$":
                return self._delete_to_eol(text, offset, "d$")
            # 非法组合：清掉 pending 后把当前键当单键重新处理
            # （落到下面的单键逻辑）

        if self.pending == "g":
            self.pending = None
            if token == "g":
                return EditResult(text, 0, "NORMAL", None, message="gg")
            # 其余：当作普通单键处理

        # ── 单键 ──
        if token in ("i",):
            self.mode = "INSERT"
            return self._insert(text, offset, "-- INSERT --")
        if token == "I":
            self.mode = "INSERT"
            return self._insert(text, _first_nonblank_off(text, offset), "-- INSERT (行首) --")
        if token == "a":
            self.mode = "INSERT"
            return self._insert(text, min(offset + 1, len(text)), "-- INSERT (追加) --")
        if token == "A":
            self.mode = "INSERT"
            return self._insert(text, _line_end_off(text, offset), "-- INSERT (行尾) --")
        if token == "o":
            self.mode = "INSERT"
            e = _line_end_off(text, offset)
            new_text = text[:e] + "\n" + text[e:]
            return self._insert(new_text, e + 1, "-- INSERT (新行) --")
        if token == "O":
            self.mode = "INSERT"
            s = _line_start_off(text, offset)
            new_text = text[:s] + "\n" + text[s:]
            return self._insert(new_text, s, "-- INSERT (上方新行) --")

        if token in ("h", "left"):
            new_off = max(_line_start_off(text, offset), offset - 1)
            return EditResult(text, new_off, "NORMAL", None)
        if token in ("l", "right"):
            le = _line_end_off(text, offset)
            new_off = min(le, offset + 1) if offset < len(text) else offset
            return EditResult(text, new_off, "NORMAL", None)
        if token in ("j", "down"):
            r, c = _offset_to_rc(text, offset)
            return EditResult(text, _rc_to_offset(text, r + 1, c), "NORMAL", None)
        if token in ("k", "up"):
            r, c = _offset_to_rc(text, offset)
            return EditResult(text, _rc_to_offset(text, r - 1, c), "NORMAL", None)
        if token == "w":
            return EditResult(text, _word_forward_off(text, offset), "NORMAL", None)
        if token == "b":
            return EditResult(text, _word_back_off(text, offset), "NORMAL", None)
        if token == "e":
            i = _word_forward_off(text, offset)
            new_off = max(offset, i - 1) if i > offset else offset
            return EditResult(text, new_off, "NORMAL", None)
        if token == "0":
            return EditResult(text, _line_start_off(text, offset), "NORMAL", None)
        if token == "^":
            return EditResult(text, _first_nonblank_off(text, offset), "NORMAL", None)
        if token == "$":
            return EditResult(text, _line_end_off(text, offset), "NORMAL", None)
        if token == "G":
            r, c = _offset_to_rc(text, offset)
            last_row = text.count("\n")
            return EditResult(text, _rc_to_offset(text, last_row, c), "NORMAL", None)
        if token == "g":
            self.pending = "g"
            return EditResult(text, offset, "NORMAL", "g", message="g")
        if token == "d":
            self.pending = "d"
            return EditResult(text, offset, "NORMAL", "d", message="d")
        if token == "x":
            if offset < len(text):
                new_text = text[:offset] + text[offset + 1:]
                return EditResult(new_text, offset, "NORMAL", None, message="x")
            return EditResult(text, offset, "NORMAL", None)
        if token == "u":
            return EditResult(text, offset, "NORMAL", None, action="undo", message="u")
        if token == "escape":
            return EditResult(text, offset, "NORMAL", None, message="-- NORMAL --")

        # 未知键：忽略（保持 NORMAL）
        return EditResult(text, offset, "NORMAL", None)

    # ── operator 实现 ──
    def _delete_line(self, text, offset, msg) -> EditResult:
        s = _line_start_off(text, offset)
        e = _line_end_off(text, offset)
        if e < len(text):
            e2 = e + 1          # 连同行尾换行一起删
        else:
            e2 = e
            if s > 0:
                s = s - 1       # 最后一行：删掉上一行的换行
        new_text = text[:s] + text[e2:]
        new_off = min(s, len(new_text))
        return EditResult(new_text, new_off, "NORMAL", None, message=msg)

    def _delete_word(self, text, offset, msg) -> EditResult:
        s = offset
        e = _word_forward_off(text, offset)
        new_text = text[:s] + text[e:]
        new_off = min(s, len(new_text))
        return EditResult(new_text, new_off, "NORMAL", None, message=msg)

    def _delete_to_eol(self, text, offset, msg) -> EditResult:
        s = offset
        e = _line_end_off(text, offset)
        new_text = text[:s] + text[e:]
        new_off = min(s, len(new_text))
        return EditResult(new_text, new_off, "NORMAL", None, message=msg)
