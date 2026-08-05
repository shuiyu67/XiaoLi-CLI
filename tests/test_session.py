"""会话持久化与 /resume 的回归测试。

全程使用临时目录，不触碰真实 chat_history/ 与 config.json。
"""
import os
import json
import tempfile
import shutil
import uuid

import pytest

from xcli_core.session import Session, SessionManager, _make_session_id, _title_from_messages


@pytest.fixture
def tmp_history():
    d = tempfile.mkdtemp(prefix="xiaoli_sess_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _write_old_format(history_dir, name, messages):
    """模拟旧 /chat save 写入（无 id 字段、用 conversation 键）。"""
    path = os.path.join(history_dir, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"timestamp": "2026-08-01 10:00:00", "conversation": messages}, f, ensure_ascii=False)
    return path


# ── SessionManager 单元 ──

def test_session_id_format():
    sid = _make_session_id()
    assert len(sid.split("-")) == 3  # YYYYMMDD-HHMMSS-xxxxxx


def test_new_session_basic_fields(tmp_history):
    mgr = SessionManager(tmp_history)
    s = mgr.new_session(engine="openai", model="xophunyuan7bmt")
    assert s.id and s.engine == "openai" and s.model == "xophunyuan7bmt"
    assert s.messages == [] and s.title == "(新会话)"


def test_save_then_load_roundtrip(tmp_history):
    mgr = SessionManager(tmp_history)
    s = mgr.new_session(engine="openai", model="gpt-4o")
    msgs = [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "你也好"}]
    assert mgr.save(s, msgs, engine="openai", model="gpt-4o") is True
    loaded = mgr.load(s.id)
    assert loaded is not None
    assert loaded.msg_count == 2
    assert loaded.messages[0]["content"] == "你好"
    assert loaded.engine == "openai" and loaded.model == "gpt-4o"


def test_title_generated_from_first_user_msg(tmp_history):
    mgr = SessionManager(tmp_history)
    s = mgr.new_session()
    msgs = [{"role": "user", "content": "帮我写一个快排函数"}]
    mgr.save(s, msgs)
    loaded = mgr.load(s.id)
    assert "快排" in loaded.title


def test_list_sessions_sorted_desc(tmp_history):
    mgr = SessionManager(tmp_history)
    # 写入两个会话，并强制 s1 的更新时间更早，制造稳定可排序差
    s1 = mgr.new_session(); mgr.save(s1, [{"role": "user", "content": "旧会话A"}])
    path1 = os.path.join(tmp_history, f"{s1.id}.json")
    with open(path1, "r", encoding="utf-8") as f:
        d = json.load(f)
    d["updated_at"] = "2020-01-01 00:00:00"
    with open(path1, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    s2 = mgr.new_session(); mgr.save(s2, [{"role": "user", "content": "新会话B"}])
    sessions = mgr.list_sessions()
    assert len(sessions) == 2
    # 倒序：更新的在前（updated_at 时间戳更大）
    assert sessions[0].id == s2.id


def test_resolve_by_index_and_prefix(tmp_history):
    mgr = SessionManager(tmp_history)
    s1 = mgr.new_session(); mgr.save(s1, [{"role": "user", "content": "x"}])
    s2 = mgr.new_session(); mgr.save(s2, [{"role": "user", "content": "y"}])
    sessions = mgr.list_sessions()
    by_idx = mgr.resolve("1", sessions)
    by_id = mgr.resolve(s2.id, sessions)
    by_prefix = mgr.resolve(s2.id[:20], sessions)
    assert by_idx is not None and by_idx.id == sessions[0].id
    assert by_id is not None and by_id.id == s2.id
    assert by_prefix is not None and by_prefix.id == s2.id


def test_compat_old_chat_format(tmp_history):
    """兼容旧 /chat save 写入的文件（无 id、conversation 键）。"""
    _write_old_format(tmp_history, "我的旧记录",
                      [{"role": "user", "content": "旧消息"}])
    mgr = SessionManager(tmp_history)
    sessions = mgr.list_sessions()
    assert len(sessions) == 1
    s = sessions[0]
    assert s.id == "我的旧记录"  # 回退用文件名
    assert s.msg_count == 1
    assert s.messages[0]["content"] == "旧消息"


# ── 与 CLI 集成（用 stub 复用 HistoryMixin 的会话方法） ──

from xcli_core.cli_history import HistoryMixin as HistoryMixinStubBase


class _Stub(HistoryMixinStubBase):
    def __init__(self, history_dir):
        self.chat_history_dir = history_dir
        self.shared_conversation_history = []
        self.current_session = None
        self.current_engine = None
        self.current_model = None
        self.session_manager = SessionManager(history_dir)

    def _set_shared_conversation_history(self):
        # 真实 AICLI 会把列表同步给所有引擎，这里做成空操作
        pass


def test_autosave_creates_session_lazily(tmp_history):
    stub = _Stub(tmp_history)
    stub.shared_conversation_history = [{"role": "user", "content": "首条"}]
    stub._autosave_session()
    assert stub.current_session is not None
    sessions = stub.session_manager.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].msg_count == 1


def test_autosave_updates_existing_session(tmp_history):
    stub = _Stub(tmp_history)
    stub.shared_conversation_history = [{"role": "user", "content": "a"}]
    stub._autosave_session()  # 建
    stub.shared_conversation_history.append({"role": "assistant", "content": "b"})
    stub._autosave_session()  # 更新
    sessions = stub.session_manager.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].msg_count == 2


def test_handle_resume_lists_and_restores(tmp_history, capsys):
    stub = _Stub(tmp_history)
    # 先写一个会话
    stub.shared_conversation_history = [{"role": "user", "content": "历史问题"}]
    stub._autosave_session()
    first_id = stub.current_session.id

    # 清空当前上下文，模拟新会话
    stub.shared_conversation_history = []
    stub.current_session = None

    # /resume 列出
    stub.handle_resume_command("")
    out = capsys.readouterr().out
    assert "已保存的会话" in out

    # /resume <id> 恢复
    stub.handle_resume_command(first_id)
    assert stub.shared_conversation_history == [{"role": "user", "content": "历史问题"}]
    assert stub.current_session.id == first_id


def test_handle_resume_new_clears_current(tmp_history):
    stub = _Stub(tmp_history)
    stub.shared_conversation_history = [{"role": "user", "content": "x"}]
    stub._autosave_session()
    assert stub.current_session is not None
    stub.handle_resume_command("new")
    assert stub.current_session is None


def test_handle_resume_unknown_token(tmp_history, capsys):
    stub = _Stub(tmp_history)
    # 先写一个会话，使目录非空，才能走到「未找到」分支而非「没有可恢复」
    stub.shared_conversation_history = [{"role": "user", "content": "历史"}]
    stub._autosave_session()
    stub.handle_resume_command("nonexistent-id")
    out = capsys.readouterr().out
    assert "未找到会话" in out
