"""Agents 体系化测试 - AgentManager 加载/解析/委派（不触真实引擎）"""
import os
import tempfile
import textwrap

from xcli_core.agent_manager import AgentManager, AgentDef


def _write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def test_parse_frontmatter():
    text = textwrap.dedent("""\
    ---
    name: coder
    description: 代码实现专家
    tools: code_editor, git_tools, file_manager
    model: gpt-4o
    ---
    你是一个资深程序员。
    任务完成后报告结果。
    """)
    d = AgentManager._parse(text, name="coder")
    assert isinstance(d, AgentDef)
    assert d.name == "coder"
    assert d.description == "代码实现专家"
    assert d.tools == ["code_editor", "git_tools", "file_manager"]
    assert d.model == "gpt-4o"
    assert "资深程序员" in d.system_prompt


def test_parse_no_frontmatter_uses_filename_and_body():
    text = "纯文本 agent 定义，无 frontmatter。"
    d = AgentManager._parse(text, name="plain")
    assert d.name == "plain"
    assert d.system_prompt == text
    assert d.tools == []


def test_load_dir_and_list():
    with tempfile.TemporaryDirectory() as td:
        _write(os.path.join(td, "coder.md"), textwrap.dedent("""\
        ---
        name: coder
        description: 编码
        tools: code_editor
        ---
        写代码。
        """))
        _write(os.path.join(td, "reviewer.md"), textwrap.dedent("""\
        ---
        name: reviewer
        description: 审查
        tools: code_editor, git_tools
        ---
        审代码。
        """))
        _write(os.path.join(td, "skip.txt"), "不是 md")
        mgr = AgentManager()
        n = mgr.load_dir(td)
        assert n == 2
        assert set(mgr.names()) == {"coder", "reviewer"}
        assert mgr.get("coder").description == "编码"
        assert mgr.get("missing") is None


def test_load_dir_missing_dir_is_noop():
    mgr = AgentManager()
    assert mgr.load_dir("") == 0
    assert mgr.load_dir("/no/such/dir/xyz") == 0


def test_dispatch_calls_runner_with_fields():
    mgr = AgentManager()
    mgr._agents["coder"] = AgentDef(
        name="coder", description="编码",
        tools=["code_editor"], model="gpt-4o",
        system_prompt="你是 coder。",
    )
    captured = {}
    def runner(system_prompt, task, tools, model):
        captured["system_prompt"] = system_prompt
        captured["task"] = task
        captured["tools"] = tools
        captured["model"] = model
        return f"done:{task}"
    out = mgr.dispatch("coder", "写 hello.py", runner)
    assert out == "done:写 hello.py"
    assert captured["system_prompt"] == "你是 coder。"
    assert captured["tools"] == ["code_editor"]
    assert captured["model"] == "gpt-4o"


def test_dispatch_missing_raises():
    mgr = AgentManager()
    def runner(*a):
        return "x"
    try:
        mgr.dispatch("nope", "t", runner)
        assert False, "expected KeyError"
    except KeyError:
        pass
