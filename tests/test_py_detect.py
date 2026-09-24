"""py_detect 本地智能检测插件测试"""
import importlib.util
import os

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


# ── 算法智能解释 (零 AI 模型, 纯算法动态生成) ──
class TestSmartExplain:
    def fix_of(self, issues, code):
        for d in issues:
            if d["code"] == code:
                return d.get("fix", "")
        return ""

    def test_spell_suggestion(self, pd):
        # 拼写纠错: 未定义变量 totl → 建议 total
        src = "total = 0\ndef f():\n    return totl\n"
        issues = pd.analyze(src, "t.py")
        fix = self.fix_of(issues, "E002")
        assert "total" in fix, fix
        assert "totl" in fix, fix

    def test_mutable_default_dynamic_fix(self, pd):
        src = "def f(items=[]):\n    pass\n"
        fix = self.fix_of(pd.analyze(src, "t.py"), "W004")
        assert "def f(items=None)" in fix, fix

    def test_eq_none_dynamic_fix(self, pd):
        src = "if x == None:\n    pass\n"
        fix = self.fix_of(pd.analyze(src, "t.py"), "W005")
        assert "x is None" in fix, fix

    def test_ne_none_dynamic_fix(self, pd):
        src = "if x != None:\n    pass\n"
        fix = self.fix_of(pd.analyze(src, "t.py"), "W005")
        assert "x is not None" in fix, fix

    def test_mutate_iter_dynamic_fix(self, pd):
        src = "for x in items:\n    items.remove(x)\n"
        fix = self.fix_of(pd.analyze(src, "t.py"), "W006")
        assert "items[:]" in fix, fix

    def test_dup_def_dynamic_line(self, pd):
        src = "def f():\n    pass\ndef f():\n    pass\n"
        fix = self.fix_of(pd.analyze(src, "t.py"), "E003")
        assert "第 1 行" in fix, fix

    def test_dead_code_dynamic_line(self, pd):
        src = "def f():\n    return 1\n    x = 2\n"
        fix = self.fix_of(pd.analyze(src, "t.py"), "W009")
        assert "第 2 行 return" in fix, fix

    def test_method_self_dynamic(self, pd):
        src = "class A:\n    def f():\n        pass\n"
        fix = self.fix_of(pd.analyze(src, "t.py"), "W007")
        assert "self" in fix, fix

    def test_type_compare_dynamic(self, pd):
        src = "if type(x) == int:\n    pass\n"
        fix = self.fix_of(pd.analyze(src, "t.py"), "I001")
        assert "isinstance(x, int)" in fix, fix


# ── L2 jedi 语义验证后端 (可选, 无 jedi 自动降级) ──
class TestJediBackend:
    def test_import_star_false_positive_removed(self, pd):
        pytest.importorskip("jedi")
        # 规则引擎: import * 不收集 sin → 误报 E002; jedi: 能解析 math.sin → 消除
        src = "from math import *\ndef f():\n    return sin(3.14)\n"
        codes = {d["code"] for d in pd.analyze(src, "C:/tmp/x.py")}
        assert "E002" not in codes
        assert "W010" in codes  # import * 警告保留

    def test_real_undefined_kept_with_jedi(self, pd):
        pytest.importorskip("jedi")
        src = "def f():\n    return totally_missing_xyz\n"
        assert "E002" in {d["code"] for d in pd.analyze(src, "C:/tmp/x.py")}

    def test_fallback_without_jedi(self, pd, monkeypatch):
        import sys
        monkeypatch.setitem(sys.modules, "jedi", None)  # import jedi 将失败
        src = "from math import *\ndef f():\n    return sin(3.14)\n"
        codes = {d["code"] for d in pd.analyze(src, "C:/tmp/x.py")}
        assert "E002" in codes  # 无 jedi → 保留规则引擎判定 (行为不变)
        assert "W010" in codes

    def test_cross_file_symbol_no_error(self, pd, tmp_path):
        pytest.importorskip("jedi")
        helper = tmp_path / "helper.py"
        helper.write_text("def helper_func():\n    return 1\n", encoding="utf-8")
        main = tmp_path / "main.py"
        src = "from helper import helper_func\ndef f():\n    return helper_func()\n"
        issues = pd.analyze(src, str(main))
        assert "E002" not in {d["code"] for d in issues}


# ── L3 数据流: 部分路径未定义就用 (E004) ──
class TestDataFlow:
    def test_if_partial_path(self, pd):
        src = "def f(flag):\n    if flag:\n        result = 1\n    return result\n"
        assert 4 in code_lines(pd.analyze(src, "t.py"), "E004")

    def test_if_else_both_defined_ok(self, pd):
        src = "def f(flag):\n    if flag:\n        r = 1\n    else:\n        r = 2\n    return r\n"
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_for_zero_iteration(self, pd):
        src = "def f(items):\n    for x in items:\n        total = x\n    return total\n"
        assert 4 in code_lines(pd.analyze(src, "t.py"), "E004")

    def test_for_loop_var_defined_inside(self, pd):
        src = "def f(items):\n    total = 0\n    for x in items:\n        total += x\n    return total\n"
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_sequential_ok(self, pd):
        src = "def f():\n    result = 1\n    return result\n"
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_param_ok(self, pd):
        src = "def f(x):\n    return x\n"
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_global_in_function_ok(self, pd):
        src = "g = 1\ndef f():\n    return g\n"
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_augassign_before_def(self, pd):
        src = "def f():\n    x = x + 1\n    return x\n"
        assert 2 in code_lines(pd.analyze(src, "t.py"), "E004")

    def test_elif_missing_branch(self, pd):
        src = "def f(a):\n    if a > 0:\n        v = 1\n    elif a < 0:\n        v = 2\n    return v\n"
        assert 6 in code_lines(pd.analyze(src, "t.py"), "E004")

    def test_del_then_use(self, pd):
        src = "def f():\n    x = 1\n    del x\n    return x\n"
        assert 4 in code_lines(pd.analyze(src, "t.py"), "E004")

    def test_class_method_path(self, pd):
        src = "class A:\n    def m(self, flag):\n        if flag:\n            r = 1\n        return r\n"
        assert 5 in code_lines(pd.analyze(src, "t.py"), "E004")

    def test_e004_dynamic_fix(self, pd):
        src = "def f(flag):\n    if flag:\n        result = 1\n    return result\n"
        issues = pd.analyze(src, "t.py")
        fix = ""
        for d in issues:
            if d["code"] == "E004":
                fix = d.get("fix", "")
        assert "result = None" in fix, fix

    def test_no_duplicate_diagnostics(self, pd):
        """L1+L3 合并不得产生重复诊断 (回归: 曾因 extend 两次全部重复)"""
        src = ("import os\n"
               "from math import *\n"
               "def f(flag):\n"
               "    if flag:\n"
               "        r = build()\n"
               "    return r\n")
        issues = pd.analyze(src, "t.py")
        keys = [(d["code"], d["line"], d["col"]) for d in issues]
        assert len(keys) == len(set(keys)), f"存在重复诊断: {keys}"

    # ── L3 误报回归 (真实项目扫描发现, 曾 422 条误报) ──
    def test_with_as_var_ok(self, pd):
        src = "def f():\n    with open('x') as fh:\n        return fh.read()\n"
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_comprehension_var_ok(self, pd):
        src = "def f(items):\n    return [x * 2 for x in items]\n"
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_nested_comprehension_ok(self, pd):
        src = ("def f(rows):\n"
               "    names = ', '.join(t.get('name', '') for t in rows)\n"
               "    return names\n")
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_lambda_param_ok(self, pd):
        src = "def f(issues):\n    return sorted(issues, key=lambda d: d['x'])\n"
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_except_handler_var_ok(self, pd):
        src = ("def f():\n"
               "    try:\n"
               "        risky()\n"
               "    except ValueError as e:\n"
               "        return str(e)\n")
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_return_in_else_terminates(self, pd):
        """else 分支 return 终止 → elif 分支流出时变量确定 (send_image 场景)"""
        src = ("def f(args):\n"
               "    if isinstance(args, str):\n"
               "        p = 1\n"
               "    elif isinstance(args, dict):\n"
               "        p = 2\n"
               "    else:\n"
               "        return None\n"
               "    return p\n")
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_return_in_else_both_terminate(self, pd):
        src = ("def f(x):\n"
               "    if x:\n"
               "        return 1\n"
               "    else:\n"
               "        return 2\n")
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    # ── 真实项目扫描发现的回归 (元组解包 / for-else) ──
    def test_tuple_unpack_no_undefined(self, pd):
        """a, b = ... 解包赋值不得误报 E002 (xiaoli_chat.py RoPE 场景)"""
        src = ("def f(x):\n"
               "    r, i = x.float().unbind(-1)\n"
               "    return r * i\n")
        assert "E002" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_for_else_fallback(self, pd):
        """for-else: else 在无 break 时必执行(含 0 次) → 变量确定 (renpy gamedir 场景)"""
        src = ("def f(cands):\n"
               "    for g in cands:\n"
               "        if g:\n"
               "            break\n"
               "    else:\n"
               "        g = 'default'\n"
               "    return g\n")
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_for_else_break_keeps_checking(self, pd):
        """循环体内赋值 + 无 orelse → 仍报 (0 次循环风险保留)"""
        src = "def f(items):\n    for x in items:\n        total = x\n    return total\n"
        assert 4 in code_lines(pd.analyze(src, "t.py"), "E004")

    def test_try_else_return_handler_ok(self, pd):
        """except 赋值 + else return 终止 → 仅异常路径流出, 变量确定 (jinja2 asyncsupport)"""
        src = ("def g():\n"
               "    try:\n"
               "        work()\n"
               "    except ValueError:\n"
               "        exc = sys.exc_info()\n"
               "    else:\n"
               "        return\n"
               "    return handle(exc)\n")
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_try_handler_real_undefined_kept(self, pd):
        """无 else: handler 变量在正常路径不确定 → 保留 E004 (jinja2 debug 真问题)"""
        src = ("def d(code, gl, lo):\n"
               "    try:\n"
               "        exec(code, gl, lo)\n"
               "    except ValueError:\n"
               "        exc = sys.exc_info()\n"
               "        tb = exc[2].tb_next\n"
               "    return exc[:2] + (tb,)\n")
        assert "E004" in {d["code"] for d in pd.analyze(src, "t.py")}

    # ── 标准库压测发现的回归 (walrus / match-case) ──
    def test_walrus_in_condition_ok(self, pd):
        """(x := ...) 在 if 条件里 → x 在 if 体内确定 (ast.py end_lineno 场景)"""
        src = ("def f(node):\n"
               "    if 'end' in node._attributes and (end := getattr(node, 'end', 0)) is not None:\n"
               "        node.end = end + 1\n"
               "    return node\n")
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_match_case_bind_ok(self, pd):
        """match/case 模式绑定变量在其 body 内确定 (dataclasses iterable 场景)"""
        src = ("def f(v):\n"
               "    match v:\n"
               "        case iterable if not hasattr(iterable, '__next__'):\n"
               "            return iterable\n"
               "        case _:\n"
               "            return None\n")
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_match_after_use_ok(self, pd):
        src = ("def h(v):\n"
               "    match v:\n"
               "        case [a, b]:\n"
               "            return a + b\n"
               "        case _:\n"
               "            return 0\n")
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_continue_branch_terminates(self, pd):
        """elif 分支 continue → 不流出, 后续 fdata 确定 (requests/models.py 场景)"""
        src = ("def f(fp):\n"
               "    if isinstance(fp, str):\n"
               "        d = fp\n"
               "    elif hasattr(fp, 'read'):\n"
               "        d = fp.read()\n"
               "    elif fp is None:\n"
               "        continue\n"
               "    else:\n"
               "        d = fp\n"
               "    return d\n")
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_break_branch_terminates(self, pd):
        src = ("def f(items):\n"
               "    for x in items:\n"
               "        if x > 10:\n"
               "            break\n"
               "        else:\n"
               "            y = x\n"
               "    return y\n")
        assert "E004" in {d["code"] for d in pd.analyze(src, "t.py")}  # break 路径 y 未定义

    # ── 第三方库压测回归 (async with/for, 星号解包, while True, 嵌套推导式) ──
    def test_async_with_bind_ok(self, pd):
        src = ("async def f():\n"
               "    async with get() as resp:\n"
               "        return resp.status\n")
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_async_for_bind_ok(self, pd):
        src = ("async def f():\n"
               "    async for msg in ws:\n"
               "        return msg.data\n")
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_starred_unpack_ok(self, pd):
        """a, *rest = ... 星号解包不得误报 (aiohttp multipart parts 场景)"""
        src = ("def f(h):\n"
               "    a, *parts = h.split(';')\n"
               "    while parts:\n"
               "        parts.pop(0)\n"
               "    return a\n")
        assert "E002" not in {d["code"] for d in pd.analyze(src, "t.py")}
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_while_true_body_defines(self, pd):
        """while True: 循环体必执行至少一次 → 其赋值确定 (aiohttp client_reqrep message)"""
        src = ("def f():\n"
               "    while True:\n"
               "        m = read()\n"
               "        if m:\n"
               "            break\n"
               "    return m\n")
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_nested_comp_outer_target_in_inner_iter(self, pd):
        """嵌套推导式: 内层 iter 可用外层 target (aiohttp cookiejar cookie 场景)"""
        src = ("def f(items):\n"
               "    return [m for (d, p), c in items for name, m in c.items()]\n")
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_comp_if_walrus_elt_uses(self, pd):
        """推导式 if 里的 walrus 先于 elt 求值 (aiohttp cookiejar key 场景)"""
        src = ("def f(items):\n"
               "    expirations = {}\n"
               "    return [key for (d, p), c in items for name, m in c.items()\n"
               "            if (key := (d, p, name)) in expirations]\n")
        assert "E002" not in {d["code"] for d in pd.analyze(src, "t.py")}
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    # ── 顶级库压测回归 (posonlyargs / 常量迭代源) ──
    def test_posonly_args_collected(self, pd):
        """def f(a, /, b): a 是位置专用参数, 不得误报 (pydantic Self | str 场景)"""
        src = ("def inner(class_, /):\n"
               "    return class_.__name__\n")
        assert "E002" not in {d["code"] for d in pd.analyze(src, "t.py")}
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_function_local_import_ok(self, pd):
        """函数内 import 不得误报 E002 (标准库 aifc math / argparse copy 场景)"""
        src = ("def f(x):\n"
               "    import math\n"
               "    return math.frexp(x)\n")
        assert "E002" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_function_local_import_from_ok(self, pd):
        src = ("def f():\n"
               "    from math import sqrt\n"
               "    return sqrt(4)\n")
        assert "E002" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_const_iter_always_runs(self, pd):
        """for f in ('a','b','c'): 常量非空 → 循环变量确定 (pydantic v1 host 场景)"""
        src = ("def f(parts):\n"
               "    for k in ('a', 'b', 'c'):\n"
               "        host = parts[k]\n"
               "        if host:\n"
               "            break\n"
               "    return host\n")
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}

    def test_range_const_iter(self, pd):
        src = "def f():\n    for i in range(3):\n        x = i\n    return x\n"
        assert "E004" not in {d["code"] for d in pd.analyze(src, "t.py")}


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
