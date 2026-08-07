"""会话（Session）持久化与恢复 —— SQLite 存储后端。

把 openai/ollama/manual 等引擎的对话历史（self.shared_conversation_history）
按「会话」维度持久化到单一 SQLite 数据库 chat_history/conversations.db，
取代原先每个会话一个 JSON 文件的方式。两张逻辑表：
  - sessions  : 自动持久化的会话，供 /resume 使用
  - snapshots : 用户命名的 /chat save 快照

兼容旧版 chat_history/<id>.json：首次打开历史目录时，自动把遗留的 *.json
（含旧 /chat save 的 conversation 格式）迁入库，并移到 _migrated_json/ 备份，
避免重复计数。
"""
import os
import re
import time
import json
import uuid
import sqlite3
import shutil


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

    def __init__(self, sid, title, created_at, updated_at, engine, model, messages,
                 is_snapshot: bool = False):
        self.id = sid
        self.title = title
        self.created_at = created_at
        self.updated_at = updated_at
        self.engine = engine
        self.model = model
        self.messages = messages or []
        self.is_snapshot = is_snapshot  # /chat save 快照在 /resume 里归并

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
    """基于 SQLite 的会话读写与索引管理。"""

    def __init__(self, history_dir: str):
        self.history_dir = history_dir
        if history_dir and not os.path.exists(history_dir):
            try:
                os.makedirs(history_dir)
            except OSError:
                pass
        self.db_path = os.path.join(self.history_dir, "conversations.db") if history_dir else ":memory:"
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        try:
            self._conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.Error:
            pass
        self._init_schema()
        self._migrate_legacy()

    # ── 表结构 ──
    def _init_schema(self):
        c = self._conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS sessions(
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT,
                updated_at TEXT,
                engine TEXT,
                model TEXT,
                messages TEXT
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS snapshots(
                name TEXT PRIMARY KEY,
                saved_at TEXT,
                messages TEXT
            )"""
        )
        self._conn.commit()

    # ── 遗留 JSON 迁移（仅一次）──
    def _migrate_legacy(self):
        if not self.history_dir:
            return
        marker = os.path.join(self.history_dir, ".migrated")
        if os.path.exists(marker):
            return
        try:
            legacy = []
            for fn in os.listdir(self.history_dir):
                if not fn.endswith(".json"):
                    continue
                if fn == "conversations.db":
                    continue
                path = os.path.join(self.history_dir, fn)
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                except (OSError, json.JSONDecodeError, ValueError):
                    continue
                if not isinstance(data, dict):
                    continue
                legacy.append((fn, data))

            if legacy:
                backup = os.path.join(self.history_dir, "_migrated_json")
                os.makedirs(backup, exist_ok=True)
                for fn, data in legacy:
                    src = os.path.join(self.history_dir, fn)
                    sid = data.get("id")
                    if sid and "messages" in data:
                        s = Session.from_dict(data, fallback_id=sid)
                        self._upsert_session_row(s)
                    elif "conversation" in data:
                        name = fn[:-5]
                        self.save_snapshot(
                            name, data["conversation"], saved_at=data.get("timestamp")
                        )
                    else:
                        continue
                    # 迁完后移走，避免被 list_sessions 的遗留扫描重复计数
                    try:
                        shutil.move(src, os.path.join(backup, fn))
                    except OSError:
                        pass
                self._conn.commit()
            try:
                with open(marker, "w", encoding="utf-8") as f:
                    f.write("migrated")
            except OSError:
                pass
        except Exception:
            # 迁移失败绝不阻断启动
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

    # ── 落库辅助 ──
    def _upsert_session_row(self, s: Session):
        self._conn.execute(
            """INSERT OR REPLACE INTO sessions
               (id, title, created_at, updated_at, engine, model, messages)
               VALUES (?,?,?,?,?,?,?)""",
            (s.id, s.title, s.created_at, s.updated_at, s.engine, s.model,
             json.dumps(s.messages, ensure_ascii=False, default=str)),
        )
        self._conn.commit()

    # ── 保存 ──
    def save(self, session: Session, messages, engine: str = "", model: str = "",
             updated_at: str = None) -> bool:
        """把当前对话内容写回到会话表。updated_at 可覆盖（测试/迁移用）。"""
        if session is None:
            return False
        session.messages = list(messages or [])
        if not session.engine and engine:
            session.engine = engine
        if not session.model and model:
            session.model = model
        if session.title in ("(新会话)", "(未命名会话)", ""):
            session.title = _title_from_messages(session.messages)
        now = updated_at or time.strftime("%Y-%m-%d %H:%M:%S")
        session.updated_at = now
        if not session.created_at:
            session.created_at = now
        try:
            self._upsert_session_row(session)
            return True
        except sqlite3.Error:
            return False

    # ── 列出 ──
    def list_sessions(self) -> list:
        """返回按更新时间倒序的 Session 列表（sessions ∪ snapshots ∪ 遗留 JSON）。"""
        sessions = []
        try:
            rows = self._conn.execute(
                "SELECT id, title, created_at, updated_at, engine, model, messages "
                "FROM sessions ORDER BY updated_at DESC"
            ).fetchall()
            for r in rows:
                msgs = self._safe_messages(r["messages"])
                sessions.append(Session(
                    sid=r["id"], title=r["title"], created_at=r["created_at"],
                    updated_at=r["updated_at"], engine=r["engine"], model=r["model"],
                    messages=msgs,
                ))
        except sqlite3.Error:
            pass

        # 合并 /chat save 快照（向后兼容：旧版里它们也出现在 /resume 列表）
        for snap in self._iter_snapshots():
            sessions.append(snap)

        # 合并目录里残留的遗留 JSON（迁移遗漏或非本工具写入）
        for legacy in self._iter_legacy_json():
            # 去重：已入库的同名不重复
            if any(s.id == legacy.id for s in sessions):
                continue
            sessions.append(legacy)

        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    # ── 按 id 或序号解析 ──
    def resolve(self, token: str, sessions: list = None) -> Session:
        """token 可以是会话 id（含文件名去后缀）或列表序号(从1)。"""
        if sessions is None:
            sessions = self.list_sessions()
        token = (token or "").strip()
        if token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(sessions):
                return sessions[idx]
        for s in sessions:
            if s.id == token or s.id.startswith(token):
                return s
        if token.endswith(".json"):
            token = token[:-5]
        for s in sessions:
            if s.id == token:
                return s
        return None

    def load(self, token: str) -> Session:
        """读取指定会话的完整内容（含 messages）。"""
        return self.resolve(token)

    # ── 快照（/chat save）──
    def save_snapshot(self, name: str, messages, saved_at: str = None) -> bool:
        try:
            self._conn.execute(
                "INSERT OR REPLACE INTO snapshots (name, saved_at, messages) VALUES (?,?,?)",
                (name, saved_at or time.strftime("%Y-%m-%d %H:%M:%S"),
                 json.dumps(list(messages or []), ensure_ascii=False, default=str)),
            )
            self._conn.commit()
            return True
        except sqlite3.Error:
            return False

    def list_snapshots(self) -> list:
        """返回 [(name, saved_at), ...] 倒序。"""
        try:
            rows = self._conn.execute(
                "SELECT name, saved_at FROM snapshots ORDER BY saved_at DESC"
            ).fetchall()
            return [(r["name"], r["saved_at"]) for r in rows]
        except sqlite3.Error:
            return []

    def load_snapshot(self, name: str):
        """返回快照的消息列表，或 None。"""
        try:
            row = self._conn.execute(
                "SELECT messages FROM snapshots WHERE name=?", (name,)
            ).fetchone()
            if row is None:
                return None
            return self._safe_messages(row["messages"])
        except sqlite3.Error:
            return None

    # ── 内部辅助 ──
    @staticmethod
    def _safe_messages(text):
        try:
            data = json.loads(text or "[]")
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, ValueError, TypeError):
            return []

    def _iter_snapshots(self):
        try:
            rows = self._conn.execute(
                "SELECT name, saved_at, messages FROM snapshots"
            ).fetchall()
        except sqlite3.Error:
            return
        for r in rows:
            msgs = self._safe_messages(r["messages"])
            yield Session(
                sid=r["name"], title=_title_from_messages(msgs),
                created_at=r["saved_at"], updated_at=r["saved_at"],
                engine="", model="", messages=msgs, is_snapshot=True,
            )

    def _iter_legacy_json(self):
        if not self.history_dir:
            return
        skip = {"conversations.db", ".migrated"}
        for fn in os.listdir(self.history_dir):
            if not fn.endswith(".json"):
                continue
            if fn in skip:
                continue
            path = os.path.join(self.history_dir, fn)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except (OSError, json.JSONDecodeError, ValueError):
                continue
            if not isinstance(data, dict):
                continue
            sid = data.get("id")
            if sid and "messages" in data:
                yield Session.from_dict(data, fallback_id=sid)
            elif "conversation" in data:
                msgs = data["conversation"]
                yield Session(
                    sid=fn[:-5], title=_title_from_messages(msgs),
                    created_at=data.get("timestamp", ""), updated_at=data.get("timestamp", ""),
                    engine="", model="", messages=msgs, is_snapshot=True,
                )
