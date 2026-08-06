"""py_detect 本地智能检测插件测试"""
import importlib.util
import os
import sys

import pytest

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN_PATH = os.path.join(PROJECT_ROOT, "plugins", "py_detect.py")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def pd():
    mod = load_module("py_detect", PLUGIN_PATH)
    return mod


def codes(issues):
    """提取诊断规则码集合"""
    return {d["code"] for d in issues}


def code_lines(issues, code):
    """按规则码提取行号集合"""
    return {d["line"] for d in issues if d["code"] == code}


# ── 语法层 ──
class TestSyntax:
    def test_syntax_error(self, pd):
        issues = pd.analyze("def f(:\n    pass\n", "bad.py")
        assert "E001" in codes(issues)
        e = [d for d in issues if d["code"] == "E001"][0]
        assert e["line"] >= 1

    def test_unclosed_paren(self, pd):
        issues = pd.analyze("x = (1 + 2\n", "bad.py")
        assert "E001" in codes(issues)


# ── 语义层 ──
class TestSemantic:
    def test_undefined_variable(self, pd):
        src = "def f():\n    return y\n"
        assert 2 in code_lines(pd.analyze(src, "t.py"), "E002")

    def test_no_undefined_for_local_and_global(self, pd):
        src = "x = 1\ndef f(a):\n    b = a + x\n    return b\nprint(f(1))\n"
        assert "E002" not in codes(pd.analyze(src, "t.py"))

    def test_undefined_recursion_ok(self, pd):
        src = "def f(n):\n    if n <= 1:\n        return 1\n    return n * f(n - 1)\n"
        assert "E002" not in codes(pd.analyze(src, "t.py"))

    def test_comprehension_and_walrus_ok(self, pd):
        src = "nums = [1, 2, 3]\nsq = [x * x for x in nums]\nif (n := len(nums)) > 2:\n    print(n)\n"
        assert "E002" not in codes(pd.analyze(src, "t.py"))

    def test_closure_reads_global_ok(self, pd):
        src = "counter = 0\ndef inc():\n    return counter + 1\n"
        assert "E002" not in codes(pd.analyze(src, "t.py"))

    def test_dup_function(self, pd):
        src = "def f():\n    pass\ndef f():\n    pass\n"
        assert 3 in code_lines(pd.analyze(src, "t.py"), "E003")

    def test_unused_import(self, pd):
        src = "import os\nimport json\nprint(json.dumps(1))\n"
        assert 1 in code_lines(pd.analyze(src, "t.py"), "W001")

    def test_import_used_inside_function(self, pd):
        src = "import os\ndef f():\n    return os.path.join('a', 'b')\n"
        assert "W001" not in codes(pd.analyze(src, "t.py"))


# ── 反模式层 ──
class TestAntiPatterns:
    def test_mutable_default(self, pd):
        src = "def f(items=[]):\n    pass\n"
        assert 1 in code_lines(pd.analyze(src, "t.py"), "W004")

    def test_bare_except(self, pd):
        src = "try:\n    x = 1\nexcept:\n    pass\n"
        assert 3 in code_lines(pd.analyze(src, "t.py"), "W002")

    def test_wide_except(self, pd):
        src = "try:\n    x = 1\nexcept Exception:\n    pass\n"
        assert 3 in code_lines(pd.analyze(src, "t.py"), "W003")

    def test_eq_none(self, pd):
        src = "if x == None:\n    pass\n"
        assert 1 in code_lines(pd.analyze(src, "t.py"), "W005")

    def test_mutate_during_iter(self, pd):
        src = "for x in items:\n    items.remove(x)\n"
        assert 2 in code_lines(pd.analyze(src, "t.py"), "W006")

    def test_method_missing_self(self, pd):
        src = "class A:\n    def f():\n        pass\n"
        assert 2 in code_lines(pd.analyze(src, "t.py"), "W007")

    def test_staticmethod_ok(self, pd):
        src = "class A:\n    @staticmethod\n    def f():\n        pass\n"
        assert "W007" not in codes(pd.analyze(src, "t.py"))

    def test_builtin_shadow(self, pd):
        src = "list = [1, 2]\n"
        assert 1 in code_lines(pd.analyze(src, "t.py"), "W008")

    def test_dead_code(self, pd):
        src = "def f():\n    return 1\n    x = 2\n"
        assert 3 in code_lines(pd.analyze(src, "t.py"), "W009")

    def test_import_star(self, pd):
        src = "from math import *\n"
        assert 1 in code_lines(pd.analyze(src, "t.py"), "W010")

    def test_div_zero(self, pd):
        src = "x = 1 / 0\n"
        assert 1 in code_lines(pd.analyze(src, "t.py"), "W011")

    def test_type_compare(self, pd):
        src = "if type(x) == int:\n    pass\n"
        assert 1 in code_lines(pd.analyze(src, "t.py"), "I001")

    def test_clean_code_no_issues(self, pd):
        src = (
            "import os\n"
            "def add(a, b):\n"
            "    return a + b\n"
            "def main():\n"
            "    path = os.path.join('x', 'y')\n"
            "    items = [1, 2, 3]\n"
            "    total = sum(items)\n"
            "    return path, add(total, 1)\n"
            "if __name__ == '__main__':\n"
            "    main()\n"
        )
        assert pd.analyze(src, "clean.py") == []


# ── 插件接口 / handle ──
class TestHandle:
    def test_version(self, pd):
        plugin = pd.Liugin()
        out = plugin.handle("version")
        assert "py_detect" in out and "v1" in out

    def test_rules_list(self, pd):
        plugin = pd.Liugin()
        out = plugin.handle("rules")
        assert "E002" in out and "W004" in out and "I001" in out

    def test_rules_single(self, pd):
        plugin = pd.Liugin()
        out = plugin.handle("rules W004")
        assert "可变默认参数" in out

    def test_rules_unknown(self, pd):
        plugin = pd.Liugin()
        out = plugin.handle("rules ZZZ")
        assert "没有规则" in out

    def test_check_missing_file(self, pd):
        plugin = pd.Liugin()
        out = plugin.handle("check /no/such/file.py")
        assert "文件不存在" in out

    def test_check_dir(self, pd, tmp_path):
        plugin = pd.Liugin()
        out = plugin.handle(f"check {tmp_path}")
        assert "是目录" in out

    def test_check_clean_file(self, pd, tmp_path):
        plugin = pd.Liugin()
        f = tmp_path / "ok.py"
        f.write_text("x = 1\nprint(x)\n", encoding="utf-8")
        out = plugin.handle(f"check {f}")
        assert "未发现可疑问题" in out

    def test_check_with_issues(self, pd, tmp_path):
        plugin = pd.Liugin()
        f = tmp_path / "bad.py"
        f.write_text("def f(items=[]):\n    return items\n", encoding="utf-8")
        out = plugin.handle(f"check {f}")
        assert "[W004]" in out and "可变默认参数" in out

    def test_check_scope_filter(self, pd, tmp_path):
        plugin = pd.Liugin()
        f = tmp_path / "scoped.py"
        f.write_text("y = None\nif y == None:\n    pass\nz = 2\n", encoding="utf-8")
        out = plugin.handle(f"check {f} 2")
        assert "[W005]" in out and "未定义变量" not in out

    def test_check_bad_scope(self, pd, tmp_path):
        plugin = pd.Liugin()
        f = tmp_path / "any.py"
        f.write_text("x = 1\n", encoding="utf-8")
        out = plugin.handle(f"check {f} abc")
        assert "范围格式错误" in out

    def test_tool_info(self, pd):
        plugin = pd.Liugin()
        info = plugin.get_tool_info()
        assert info["name"] == "py_detect"
        assert "智能检测" in info["description"]
        assert "check" in info["usage"]

    def test_mcp_definition(self, pd):
        plugin = pd.Liugin()
        mcp = plugin.get_mcp_definition()
        assert mcp["name"] == "py_detect"
        assert "check" in mcp["inputSchema"]["properties"]["operation"]["enum"]


# ── code_editor 写文件后自动检测集成 ──
class TestAutoDetectIntegration:
    """AI 用 code_editor 改完 .py 文件后，系统自动跑 py_detect"""

    @pytest.fixture
    def editor(self):
        mod = load_module("code_editor", os.path.join(PROJECT_ROOT, "plugins", "code_editor.py"))
        cls = getattr(mod, "Liugin", None) or getattr(mod, "Plugin", None)
        return cls()

    def test_write_dirty_py_auto_detects(self, editor, tmp_path):
        f = tmp_path / "bad.py"
        out = editor.handle(f"write {f} def f(items=[]):\n    return missing_var\n")
        assert "[py_detect]" in out, out
        assert "[W004]" in out and "[E002]" in out, out

    def test_write_clean_py_silent(self, editor, tmp_path):
        f = tmp_path / "ok.py"
        out = editor.handle(f"write {f} x = 1\nprint(x)\n")
        assert "[py_detect]" not in out, out

    def test_edit_py_auto_detects(self, editor, tmp_path):
        f = tmp_path / "edit.py"
        f.write_text("y = 1\nif y == 1:\n    print('a')\n", encoding="utf-8")
        # 编辑引入 == None 反模式
        out = editor.handle(f"edit {f} y == 1 <<<>>> y == None")
        assert "[py_detect]" in out and "[W005]" in out, out

    def test_create_py_auto_detects(self, editor, tmp_path):
        f = tmp_path / "new.py"
        out = editor.handle(f"create {f} import os")
        assert "[py_detect]" in out and "[W001]" in out, out  # import os 未使用

    def test_non_py_no_detect(self, editor, tmp_path):
        f = tmp_path / "data.txt"
        out = editor.handle(f"write {f} hello world")
        assert "[py_detect]" not in out, out
