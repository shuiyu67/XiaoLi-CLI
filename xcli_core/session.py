"""会话（Session）持久化与恢复。

把 openai/ollama/manual 等引擎的对话历史（self.shared_conversation_history）
按「会话」维度持久化到 chat_history/<id>.json，支持：
  - 自动落盘（每轮对话后调用 SessionManager.save）
  - 列出历史会话（/resume、/sessions）
  - 一键恢复（把 messages 重新载入 shared_conversation_history）

存储格式（新）：
  {
    "id": "20260805-171045-a1b2c3",
    "title": "用户首条消息前若干个字",
    "created_at": "2026-08-05 17:10:45",
    "updated_at": "2026-08-05 17:15:22",
    "engine": "openai",
    "model": "xophunyuan7bmt",
    "messages": [ ... ]
  }

兼容旧 /chat save 写入的文件（无 id 字段、用 "conversation" 键）：
  读取时回退——id 取文件名，messages 取 conversation 键。
"""
import os
import re
import time
import json
import uuid


def _make_session_id() -> str:
    """生成形如 20260805-171045-a1b2c3 的会话 ID。"""
    ts = time.strftime("%Y%m%d-%H%M%S")
    suffix = uuid.uuid4().hex[:6]
    return f"{ts}-{suffix}"


def _title_from_messages(messages, limit: int = 40) -> str:
    """从首条 user 消息生成会话标题。"""
    for m in messages or []:
        if isinstance(m, dict) and m.get("role") == "user":
            content = m.get("content", "")
            if isinstance(content, list):  # 多模态 content 可能是列表
                parts = [c.get("text", "") for c in content if isinstance(c, dict)]
                content = " ".join(parts)
            content = (content or "").strip().replace("\n", " ")
            return content[:limit] if content else "(空消息)"
    return "(未命名会话)"


class Session:
    """单个会话的轻量容器。"""

    def __init__(self, sid, title, created_at, updated_at, engine, model, messages):
        self.id = sid
        self.title = title
        self.created_at = created_at
        self.updated_at = updated_at
        self.engine = engine
        self.model = model
        self.messages = messages or []

    @property
    def msg_count(self) -> int:
        return len(self.messages)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "engine": self.engine,
            "model": self.model,
            "messages": self.messages,
        }

    @classmethod
    def from_dict(cls, data: dict, fallback_id: str = ""):
        # 兼容旧 /chat save 格式：无 id、用 "conversation" 键
        sid = data.get("id") or fallback_id
        messages = data.get("messages")
        if messages is None and "conversation" in data:
            messages = data["conversation"]
        return cls(
            sid=sid,
            title=data.get("title") or _title_from_messages(messages),
            created_at=data.get("created_at") or data.get("timestamp") or "",
            updated_at=data.get("updated_at") or data.get("timestamp") or "",
            engine=data.get("engine") or "",
            model=data.get("model") or "",
            messages=messages or [],
        )


class SessionManager:
    """会话的读写与索引管理。"""

    def __init__(self, history_dir: str):
        self.history_dir = history_dir
        if history_dir and not os.path.exists(history_dir):
            try:
                os.makedirs(history_dir)
            except OSError:
                pass

    # ── 新建 ──
    def new_session(self, engine: str = "", model: str = ""):
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        return Session(
            sid=_make_session_id(),
            title="(新会话)",
            created_at=now,
            updated_at=now,
            engine=engine or "",
            model=model or "",
            messages=[],
        )

    # ── 保存 ──
    def save(self, session: Session, messages, engine: str = "", model: str = ""):
        """把当前对话内容写回到 session 对应的文件。"""
        if session is None:
            return False
        session.messages = list(messages or [])
        if not session.engine and engine:
            session.engine = engine
        if not session.model and model:
            session.model = model
        # 首条用户消息生成标题（仅当仍是占位标题时）
        if session.title in ("(新会话)", "(未命名会话)", ""):
            session.title = _title_from_messages(session.messages)
        session.updated_at = time.strftime("%Y-%m-%d %H:%M:%S")
        if not session.created_at:
            session.created_at = session.updated_at
        file_path = os.path.join(self.history_dir, f"{session.id}.json")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, ensure_ascii=False, indent=2, default=str)
            return True
        except OSError:
            return False

    # ── 列出 ──
    def list_sessions(self) -> list:
        """返回按更新时间倒序的 Session 列表。"""
        sessions = []
        try:
            files = [f for f in os.listdir(self.history_dir) if f.endswith(".json")]
        except OSError:
            return sessions
        for f in files:
            path = os.path.join(self.history_dir, f)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                sid = data.get("id") or f[:-5]
                s = Session.from_dict(data, fallback_id=sid)
                # 跳过明显空会话（无消息且非手动命名）
                sessions.append(s)
            except (OSError, json.JSONDecodeError, ValueError):
                continue
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    # ── 按 id 或序号解析 ──
    def resolve(self, token: str, sessions: list = None) -> Session:
        """token 可以是会话 id（含文件名去后缀）或列表序号(从1)。"""
        if sessions is None:
            sessions = self.list_sessions()
        token = (token or "").strip()
        # 序号
        if token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(sessions):
                return sessions[idx]
        # id（精确或前缀）
        for s in sessions:
            if s.id == token or s.id.startswith(token):
                return s
        # 文件名（去掉 .json）
        if token.endswith(".json"):
            token = token[:-5]
        for s in sessions:
            if s.id == token:
                return s
        return None

    def load(self, token: str) -> Session:
        """读取指定会话的完整内容（含 messages）。"""
        sessions = self.list_sessions()
        s = self.resolve(token, sessions)
        if s is None:
            return None
        # 重新从文件读取以确保 messages 完整
        path = os.path.join(self.history_dir, f"{s.id}.json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return Session.from_dict(data, fallback_id=s.id)
        except (OSError, json.JSONDecodeError, ValueError):
            return s
