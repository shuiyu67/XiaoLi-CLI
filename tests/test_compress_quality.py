"""上下文压缩质量测试：覆盖保真度、可配置 keep_recent、避免二次失真。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xcli_core.memory import MemoryManager


class FakeEngine:
    """捕获发给引擎的摘要 prompt，并返回确定结构化摘要。"""
    def __init__(self):
        self.last_prompt = None
        self.calls = 0

    def generate_response(self, user_input, system_prompt=None, tools=None):
        self.last_prompt = user_input
        self.calls += 1
        return "[用户]: 需求A\n[助手]: 调用 code_editor 创建 main.py\n[助手]: 调用 git_tools 提交"


class _Msg(dict):
    def __init__(self, role, content):
        super().__init__(role=role, content=content)


def _make_convo(n):
    msgs = []
    for i in range(n):
        msgs.append(_Msg("user" if i % 2 == 0 else "assistant",
                         f"消息{i} 内容占位 " + "x" * 5))
    return msgs


def test_prepare_keeps_tool_json_full():
    """工具调用 JSON 不应被 200 字截断，应完整保留。"""
    mm = MemoryManager(project_dir="C:/tmp/xiaoli_test_mm")
    tool_json = ('{"action": "use_tool", "tool": "code_editor", '
                 '"args": "edit C:/repo/main.py old_block <<<>>> new_block"}')
    msg = _Msg("assistant", "我先调用工具：\n" + tool_json)
    out = mm._prepare_for_summary(msg)
    assert tool_json in out, "工具调用 JSON 必须完整保留"
    assert "[助手] [工具调用]" in out or "[assistant] [工具调用]" in out


def test_prepare_keeps_code_fence_when_long():
    """超长内容但含代码块时，应保留代码块而非简单前 1500 字截断。"""
    mm = MemoryManager(project_dir="C:/tmp/xiaoli_test_mm")
    long_prose = "p" * 3000
    code = "```python\ndef add(a, b):\n    return a + b\n```"
    msg = _Msg("assistant", long_prose + "\n" + code)
    out = mm._prepare_for_summary(msg)
    assert "def add" in out, "长内容中的代码块应被保留"
    assert "保留代码块" in out


def test_compress_uses_current_engine_and_keeps_recent():
    """压缩调用当前引擎，并保留最近 keep_recent 条。"""
    mm = MemoryManager(project_dir="C:/tmp/xiaoli_test_mm")
    eng = FakeEngine()
    conv = _make_convo(30)  # 30 条 > keep_recent(12)
    result = mm.compress_context(conv, engine=eng)
    # 返回 = 1 条摘要 system + 最近 12 条
    assert len(result) == 1 + mm.keep_recent
    assert result[0]["role"] == "system"
    assert "[上下文压缩]" in result[0]["content"]
    # 最近的消息在末尾
    assert result[-1] is conv[-1]
    assert eng.calls == 1


def test_no_double_compaction_on_growth():
    """历史摘要标记不会被二次摘要；真正新增的消息才会产生新摘要。"""
    mm = MemoryManager(project_dir="C:/tmp/xiaoli_test_mm")
    eng = FakeEngine()
    conv = _make_convo(30)
    r1 = mm.compress_context(conv, engine=eng)
    assert len(mm.compressed_blobs) == 1

    # 幂等：对返回的同一历史再次压缩，不应二次摘要旧摘要、不调引擎
    eng2 = FakeEngine()
    r2 = mm.compress_context(r1, engine=eng2)
    assert r2 is r1, "对已压缩历史再压缩应为幂等 no-op"
    assert len(mm.compressed_blobs) == 1, "不应二次摘要旧摘要"
    assert eng2.calls == 0

    # 真正增长的新消息应被压缩为第二条摘要，且旧摘要标记保留
    grown2 = list(r1) + [_Msg("user", f"后续{i}") for i in range(15)]
    eng3 = FakeEngine()
    r3 = mm.compress_context(grown2, engine=eng3)
    assert len(mm.compressed_blobs) == 2, "新增的真实消息应被压缩为第二条摘要"
    # 合并摘要里应同时含第一次与第二次的标记
    assert "[上下文压缩]" in r3[0]["content"]


def test_keep_recent_configurable():
    """keep_recent 可通过参数覆盖。"""
    mm = MemoryManager(project_dir="C:/tmp/xiaoli_test_mm")
    eng = FakeEngine()
    conv = _make_convo(20)
    result = mm.compress_context(conv, engine=eng, keep_recent=5)
    assert len(result) == 1 + 5
