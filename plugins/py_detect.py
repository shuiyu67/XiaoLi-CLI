"""
本地 Python 智能检测插件 (py_detect)
===================================
纯本地、零第三方依赖、零 AI 模型的代码检测引擎——为 xiaoli-cli「纯本地」而生。

设计目标:
  1. 只依赖标准库 (ast / tokenize / difflib)，低配电脑（连 1B 模型都跑不动）
     也秒级运行，永不联网、永不卡死。
  2. 三层检测算法:
     ① 语法层   — tokenize + ast.parse 精确定位语法错误 (行列 + 原因)
     ② 语义层   — 作用域感知: 未定义变量 / 重复定义 / 未使用导入
     ③ 反模式层 — 可变默认参数 / 裸 except / ==None / 迭代中修改列表 /
                   覆盖内置名 / import * / 除零 / 方法缺 self / 死代码
  3. 算法智能解释 (不靠 AI 模型): 每条诊断按代码上下文动态生成——
     拼写纠错建议 (difflib 相似名)、带函数名/参数名的修复示例、
     改后代码片段。纯算法推理，任何设备跑得动。
  4. L2 语义验证后端 (可选): 检测到 jedi 时自动启用, 用语义推断二次确认
     E002 未定义变量——消除「from x import * / 跨文件符号」等误报;
     无 jedi 时自动降级为纯标准库模式, 行为完全不变。
  5. 结果纯文本结构化 (code:line:col 前缀), 方便回喂给 AI 与用户。

操作:
  check <文件> [行号]          - 检测整个文件 / 只检测某一行
  check <文件> <起>-<止>       - 只检测某一段范围
  rules [规则码]               - 列出全部规则 / 查看单条规则
  version                      - 版本信息
"""

import ast
import difflib
import os
import tokenize
from typing import Dict, List, Optional, Tuple

__version__ = "1.2.0"

# ── 内置名集合 (判定「覆盖内置」与「未定义」用) ──
if isinstance(__builtins__, dict):
    _BUILTINS = set(__builtins__)
else:
    _BUILTINS = set(dir(__builtins__))

# ── 规则元数据: code -> (severity, 标题, 修复建议) ──
RULES: Dict[str, Tuple[str, str, str]] = {
    "E001": ("错误", "语法错误", "修复: 检查该行附近——常见原因: 缺冒号、括号不匹配、引号未闭合、缩进错误。"),
    "E002": ("错误", "使用了未定义的变量", "修复: 先给变量赋值或导入它；若是闭包/动态注入(globals()/exec)可忽略。"),
    "E003": ("错误", "函数/类重复定义", "修复: 删掉其中一个定义，或改名避免覆盖。"),
    "W001": ("警告", "导入后未使用", "修复: 删除该 import，或补上使用处。"),
    "W002": ("警告", "裸 except", "修复: 写成 except Exception: 或指定具体异常类型，避免吞掉所有错误。"),
    "W003": ("警告", "捕获范围过宽 (except Exception)", "修复: 尽量捕获具体异常 (如 ValueError/KeyError)，避免隐藏 bug。"),
    "W004": ("警告", "可变默认参数", "修复: 改成 def f(x=None): x = x if x is not None else []，避免跨调用共享同一对象。"),
    "W005": ("警告", "用 == 比较 None/True/False", "修复: 应使用 is / is not，如 if x is None。"),
    "W006": ("警告", "迭代过程中修改了列表", "修复: 先复制: for x in lst[:]: 或用列表推导生成新列表。"),
    "W007": ("警告", "方法缺少 self/cls 参数", "修复: 方法首参数应为 self(实例方法)或 cls(@classmethod)；若是独立函数请移出类。"),
    "W008": ("警告", "赋值覆盖了内置名", "修复: 换一个名字(如 data/items/input_text)，避免后续行为诡异。"),
    "W009": ("警告", "return/raise 之后有不可达代码", "修复: 删除无效语句，或把 return 放到函数最后。"),
    "W010": ("警告", "使用了 import *", "修复: 显式导入用到的名字，避免污染命名空间。"),
    "W011": ("警告", "除零风险 (字面量 0 作除数)", "修复: 除之前判断除数是否为 0，或改用安全除法。"),
    "I001": ("提示", "建议用 isinstance 替代 type 比较", "修复: 用 isinstance(x, int) 更健壮 (支持继承)。"),
}


def _smart_explain(code: str, ctx: dict) -> Tuple[str, str]:
    """算法智能解释：按代码上下文动态生成「针对性标题 + 修复建议」。

    纯算法 (模板渲染 + 名字注入 + 相似度), 不调用任何 AI 模型。
    ctx 常见键: name / func / arg / lst / op / typ / suggestion / first_line / prev / prev_line
    """
    sev, title, base_fix = RULES[code]

    if code == "E002":
        name = ctx.get("name", "")
        sugg = ctx.get("suggestion", "")
        if name:
            title = f"使用了未定义的变量 {name}"
            if sugg:
                fix = (f"修复: 变量 {name} 未定义——你是不是想写「{sugg}」？"
                       f"先给它赋值/导入；若是闭包或动态注入(globals()/exec)可忽略。")
            else:
                fix = (f"修复: 变量 {name} 未定义。先给它赋值或导入；"
                       f"若是闭包或动态注入(globals()/exec)可忽略。")
            return title, fix

    elif code == "W004":
        func = ctx.get("func", "")
        arg = ctx.get("arg", "")
        if func and arg:
            fix = (f"修复: 改写成 def {func}({arg}=None):  {arg} = {arg} if {arg} is not None else 默认值"
                   f"——避免所有调用共享同一个可变对象。")
            return title, fix

    elif code == "W005":
        obj = ctx.get("name", "x")
        op = ctx.get("op", "is")
        fix = f"修复: 应写成 if {obj} {op} None: ——用身份比较，语义更准确。"
        return title, fix

    elif code == "W006":
        lst = ctx.get("lst", "lst")
        fix = f"修复: 先复制再迭代: for x in {lst}[:]: ——或在循环外用新列表收集，避免跳过/漏项。"
        return title, fix

    elif code == "W007":
        func = ctx.get("func", "")
        if func:
            fix = (f"修复: 方法 {func} 首参数应为 self(实例方法)或 cls(@classmethod)；"
                   f"若是独立函数请移出类。")
            return title, fix

    elif code == "E003":
        name = ctx.get("name", "")
        first = ctx.get("first_line")
        if name and first:
            fix = f"修复: {name} 已在第 {first} 行定义过——删掉其中一个，或改名避免覆盖。"
            return title, fix

    elif code == "W008":
        name = ctx.get("name", "")
        if name:
            fix = (f"修复: 别用内置名 {name} 当变量，换个名字(如 {name}_val / data / items)，"
                   f"避免覆盖内置行为导致诡异 bug。")
            return title, fix

    elif code == "I001":
        obj = ctx.get("name", "x")
        typ = ctx.get("typ", "int")
        fix = f"修复: 用 isinstance({obj}, {typ}) 更健壮 (支持子类，且是 Python 官方推荐写法)。"
        return title, fix

    elif code == "W009":
        prev = ctx.get("prev", "return")
        prev_line = ctx.get("prev_line")
        if prev_line:
            fix = f"修复: 第 {prev_line} 行 {prev} 之后的代码永远不会执行——删除它，或把逻辑放到 {prev} 之前。"
            return title, fix

    return title, base_fix


class _ModuleCollector(ast.NodeVisitor):
    """收集模块级定义 (name -> node)，供作用域分析与重复定义/未使用导入检测"""

    def __init__(self):
        self.module_scope: Dict[str, Optional[ast.AST]] = {}
        self.def_nodes: Dict[str, List[ast.AST]] = {}   # def/class 定义节点 (重复定义检测)
        self.imports: Dict[str, int] = {}               # 导入的名字 -> 行号
        self.used_names: set = set()                    # 被 load 使用的名字
        self.import_star_lines: List[int] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = (alias.asname or alias.name).split(".")[0]
            self.module_scope[name] = node
            self.imports[name] = node.lineno
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if any(alias.name == "*" for alias in node.names):
            self.import_star_lines.append(node.lineno)
            return
        for alias in node.names:
            name = alias.asname or alias.name
            self.module_scope[name] = node
            self.imports[name] = node.lineno
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.module_scope[node.name] = node
        self.def_nodes.setdefault(node.name, []).append(node)
        self._collect_uses(node)  # 函数体内的使用也计入 (判定未使用导入)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef):
        self.module_scope[node.name] = node
        self.def_nodes.setdefault(node.name, []).append(node)
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._collect_uses(child)  # 方法体内的使用也计入

    def visit_Assign(self, node: ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name):
                self.module_scope.setdefault(t.id, None)
        self._collect_uses(node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if isinstance(node.target, ast.Name):
            self.module_scope.setdefault(node.target.id, None)
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        self.module_scope.setdefault(self._first_name(node.target), None)
        self._collect_uses(node)

    def visit_With(self, node: ast.With):
        for item in node.items:
            if item.optional_vars:
                self.module_scope.setdefault(self._first_name(item.optional_vars), None)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        if node.name:
            self.module_scope.setdefault(node.name, None)
        self.generic_visit(node)

    def _first_name(self, target) -> Optional[str]:
        if isinstance(target, ast.Name):
            return target.id
        if isinstance(target, (ast.Tuple, ast.List)) and target.elts:
            return self._first_name(target.elts[0])
        return None

    def _collect_uses(self, node: ast.AST):
        for n in ast.walk(node):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                self.used_names.add(n.id)
            elif isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
                self.used_names.add(n.value.id)


class _ScopeAnalyzer(ast.NodeVisitor):
    """作用域感知检测器: 未定义变量 / 方法缺 self / 反模式扫描等"""

    def __init__(self, source: str, module_scope: Dict[str, Optional[ast.AST]]):
        self.source = source
        self.lines = source.splitlines()
        self.module_scope = module_scope
        self.scope_stack: List[Dict[str, str]] = []     # 函数/类作用域栈
        self.additional_defs: set = set()               # 顶层推导式/walrus/循环变量等
        self.defined_names: set = set(module_scope)     # 全部已定义名 (拼写纠错用)
        self.issues: List[Dict] = []

    # ── 工具 ──
    def _add(self, code: str, lineno: int, col: int, extra: str = "", **ctx):
        title, fix = _smart_explain(code, ctx)
        self.issues.append({
            "code": code,
            "severity": RULES[code][0],
            "title": title,
            "line": lineno, "col": col + 1,
            "text": self._line_text(lineno), "fix": fix, "extra": extra,
        })

    def _declare(self, name: str):
        """无条件登记一个已定义名字 (顶层也生效, 避免误报)"""
        self.additional_defs.add(name)
        self.defined_names.add(name)

    def _suggest(self, name: str) -> str:
        """拼写纠错: 在已定义名字里找最接近的 (difflib, 纯算法)"""
        try:
            matches = difflib.get_close_matches(name, self.defined_names, n=1, cutoff=0.6)
            return matches[0] if matches else ""
        except Exception:
            return ""

    def _line_text(self, lineno: int) -> str:
        if 0 < lineno <= len(self.lines):
            return self.lines[lineno - 1].strip()[:120]
        return ""

    def _in_scope(self, name: str) -> bool:
        for scope in reversed(self.scope_stack):
            if name in scope:
                return True
        return name in self.module_scope or name in self.additional_defs

    def _collect_target(self, target: ast.AST, scope: Dict[str, str]):
        if isinstance(target, ast.Name):
            scope[target.id] = "变量"
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._collect_target(elt, scope)

    def _target_names(self, target: ast.AST) -> set:
        names = set()
        if isinstance(target, ast.Name):
            names.add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                names |= self._target_names(elt)
        return names

    # ── 函数/类/作用域 ──
    def visit_FunctionDef(self, node: ast.FunctionDef):
        if self.scope_stack:
            self.scope_stack[-1][node.name] = "函数"   # 局部函数名可见
        parent = self.scope_stack[-1] if self.scope_stack else None
        if parent is not None and "<class>" in parent:
            decos = {getattr(d, "id", "") for d in node.decorator_list}
            is_static = "staticmethod" in decos or "classmethod" in decos
            args0 = node.args.args[0].arg if node.args.args else None
            if not is_static and args0 not in ("self", "cls"):
                self._add("W007", node.lineno, node.col_offset,
                          extra=f"方法 {node.name} 缺 self/cls", func=node.name)
        scope: Dict[str, str] = {}
        for arg in node.args.args + node.args.kwonlyargs:
            scope[arg.arg] = "参数"
        if node.args.vararg:
            scope[node.args.vararg.arg] = "参数"
        if node.args.kwarg:
            scope[node.args.kwarg.arg] = "参数"
        # 可变默认参数 (经典坑: 默认值跨调用共享) —— 动态注入函数名/参数名
        n_defaults = len(node.args.defaults)
        if n_defaults:
            for arg, d in zip(node.args.args[-n_defaults:], node.args.defaults):
                if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                    self._add("W004", node.lineno, node.col_offset,
                              extra=f"可变默认参数: {node.name}.{arg.arg}",
                              func=node.name, arg=arg.arg)
        for d in node.args.kw_defaults:
            if d is not None and isinstance(d, (ast.List, ast.Dict, ast.Set)):
                self._add("W004", node.lineno, node.col_offset,
                          extra=f"可变默认参数: {node.name}",
                          func=node.name, arg="kw")
        self.scope_stack.append(scope)
        self.generic_visit(node)
        self.scope_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef):
        scope: Dict[str, str] = {"<class>": "类"}
        self.scope_stack.append(scope)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_Lambda(self, node: ast.Lambda):
        for a in node.args.args:
            self._declare(a.arg)
        self.generic_visit(node)

    def _visit_comprehension(self, node):
        for gen in node.generators:
            for n in ast.walk(gen.target):
                if isinstance(n, ast.Name):
                    self._declare(n.id)
        self.generic_visit(node)

    def visit_ListComp(self, node): self._visit_comprehension(node)
    def visit_SetComp(self, node): self._visit_comprehension(node)
    def visit_GeneratorExp(self, node): self._visit_comprehension(node)
    def visit_DictComp(self, node): self._visit_comprehension(node)

    def visit_NamedExpr(self, node: ast.NamedExpr):
        if isinstance(node.target, ast.Name):
            self._declare(node.target.id)
        self.generic_visit(node)

    # ── 赋值/循环/上下文 ──
    def visit_Assign(self, node: ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name):
                if self.scope_stack:
                    self.scope_stack[-1][t.id] = "变量"
                if t.id in _BUILTINS:
                    self._add("W008", node.lineno, node.col_offset,
                              extra=f"覆盖内置名: {t.id}", name=t.id)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if isinstance(node.target, ast.Name):
            if self.scope_stack:
                self.scope_stack[-1][node.target.id] = "变量"
            if node.target.id in _BUILTINS:
                self._add("W008", node.lineno, node.col_offset,
                          extra=f"覆盖内置名: {node.target.id}", name=node.target.id)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign):
        if isinstance(node.target, ast.Name) and self.scope_stack:
            self.scope_stack[-1][node.target.id] = "变量"
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        if self.scope_stack:
            self._collect_target(node.target, self.scope_stack[-1])
        for n in ast.walk(node.target):
            if isinstance(n, ast.Name):
                self._declare(n.id)  # 顶层 for 变量也登记, 避免误报
        # 迭代中修改列表检测: 检查被迭代对象 (iter) 在循环体里被增删改
        iter_names = self._target_names(node.iter)
        for stmt in node.body:
            for sub in ast.walk(stmt):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                    if sub.func.attr in ("append", "remove", "pop", "clear", "insert", "extend", "sort", "reverse"):
                        if isinstance(sub.func.value, ast.Name) and sub.func.value.id in iter_names:
                            self._add("W006", sub.lineno, sub.col_offset,
                                      extra=f"迭代中修改列表: {sub.func.value.id}",
                                      lst=sub.func.value.id)
        self.generic_visit(node)

    def visit_With(self, node: ast.With):
        if self.scope_stack:
            for item in node.items:
                if item.optional_vars:
                    self._collect_target(item.optional_vars, self.scope_stack[-1])
        for item in node.items:
            if item.optional_vars:
                for n in ast.walk(item.optional_vars):
                    if isinstance(n, ast.Name):
                        self._declare(n.id)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        if node.name:
            if self.scope_stack:
                self.scope_stack[-1][node.name] = "异常变量"
            self._declare(node.name)
        if node.type is None:
            self._add("W002", node.lineno, 0)
        elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
            self._add("W003", node.lineno, 0)
        self.generic_visit(node)

    # ── 表达式检测 ──
    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Load):
            if node.id not in _BUILTINS and not self._in_scope(node.id):
                self._add("E002", node.lineno, node.col_offset,
                          extra=f"未定义变量: {node.id}",
                          name=node.id, suggestion=self._suggest(node.id))
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare):
        if len(node.ops) == 1 and isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
            sides = [node.left, *node.comparators]
            is_eq = isinstance(node.ops[0], ast.Eq)
            op_word = "is" if is_eq else "is not"
            for side in sides:
                if isinstance(side, ast.Constant) and isinstance(side.value, (type(None), bool)):
                    others = [s for s in sides if s is not side]
                    obj = others[0].id if others and isinstance(others[0], ast.Name) else "x"
                    self._add("W005", node.lineno, node.col_offset,
                              extra=f"用 == 比较 {side.value!r}",
                              name=obj, op=op_word)
                if isinstance(side, ast.Call) and isinstance(side.func, ast.Name) and side.func.id == "type":
                    others = [s for s in sides if s is not side]
                    obj = (side.args[0].id
                           if side.args and isinstance(side.args[0], ast.Name) else "x")
                    typ = others[0].id if others and isinstance(others[0], ast.Name) else "int"
                    self._add("I001", node.lineno, node.col_offset,
                              extra="type() 比较", name=obj, typ=typ)
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            if isinstance(node.right, ast.Constant) and node.right.value in (0, 0.0):
                self._add("W011", node.lineno, node.col_offset, "字面量 0 作除数")
        self.generic_visit(node)

    # ── 死代码 (函数体 return/raise 后) ──
    def _check_dead_code(self, tree: ast.AST):
        for fn in ast.walk(tree):
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for i, stmt in enumerate(fn.body[:-1]):
                    if isinstance(stmt, (ast.Return, ast.Raise)):
                        nxt = fn.body[i + 1]
                        prev = "return" if isinstance(stmt, ast.Return) else "raise"
                        self._add("W009", nxt.lineno, nxt.col_offset,
                                  extra=f"{prev} 后不可达",
                                  prev=prev, prev_line=stmt.lineno)
                        break


def _check_syntax(source: str) -> Tuple[List[Dict], Optional[ast.Module]]:
    issues: List[Dict] = []
    tree = None
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        issues.append({
            "code": "E001", "severity": "错误", "title": "语法错误",
            "line": e.lineno or 1, "col": (e.offset or 1),
            "text": (e.text or "").strip()[:120],
            "fix": RULES["E001"][2], "extra": f"ast: {e.msg}",
        })
    if not issues:
        try:
            for _tok in tokenize.generate_tokens(iter(source.splitlines(True)).__next__):
                pass
        except tokenize.TokenError as e:
            issues.append({
                "code": "E001", "severity": "错误", "title": "语法错误",
                "line": e.args[1][0] + 1, "col": e.args[1][1] + 1,
                "text": "", "fix": RULES["E001"][2],
                "extra": f"tokenize: 未闭合括号/引号 {e.args[0]}",
            })
    return issues, tree


def _jedi_validate(source: str, path: str, issues: List[Dict]) -> List[Dict]:
    """L2 语义验证后端 (可选增强): 用 jedi 对规则引擎的 E002 做二次确认。

    - 有 jedi: 消除「跨文件符号 / from x import * 动态名 / 类型别名」等误报
      (规则引擎只认本文件, jedi 能解析项目级/第三方库符号)
    - 无 jedi: 原样返回 (纯标准库模式, 低配设备行为完全不变)
    """
    try:
        import jedi
    except Exception:
        return issues
    try:
        if path and path not in ("<string>", "<buffer>"):
            script = jedi.Script(code=source, path=path)
        else:
            script = jedi.Script(code=source)
    except Exception:
        return issues
    out = []
    for d in issues:
        if d["code"] == "E002":
            extra = d.get("extra", "")
            name = extra.split(":", 1)[-1].strip() if ":" in extra else ""
            # jedi 的行列与 ast 一致均为 1-based (与 LSP 的 0-based 不同!)
            line1 = int(d.get("line", 1))
            col1 = int(d.get("col", 1))
            try:
                inferred = script.infer(line1, col1)
            except Exception:
                inferred = []
            if inferred:
                continue  # jedi 能解析出符号 → 动态/跨文件定义, 消除规则引擎误报
        out.append(d)
    return out


def analyze(source: str, filename: str = "<string>") -> List[Dict]:
    """三层检测主入口 + L2 jedi 语义验证: 返回诊断列表"""
    issues, tree = _check_syntax(source)
    if tree is None:
        return issues

    collector = _ModuleCollector()
    collector.visit(tree)

    analyzer = _ScopeAnalyzer(source, collector.module_scope)
    analyzer.visit(tree)
    analyzer._check_dead_code(tree)

    for name, lineno in collector.imports.items():
        if name not in collector.used_names:
            analyzer._add("W001", lineno, 0, f"导入未使用: {name}")
    for lineno in collector.import_star_lines:
        analyzer._add("W010", lineno, 0, "import *")

    for name, nodes in collector.def_nodes.items():
        if len(nodes) > 1:
            for node in nodes[1:]:
                analyzer._add("E003", node.lineno, node.col_offset,
                              extra=f"重复定义: {name}",
                              name=name, first_line=nodes[0].lineno)

    issues.extend(analyzer.issues)
    issues = _jedi_validate(source, filename, issues)   # L2: 语义二次确认 (可选)
    return issues


def format_report(path: str, issues: List[Dict], scope: Optional[Tuple[int, int]] = None) -> str:
    if not issues:
        return f"[OK] {path}: 未发现可疑问题。"

    order = {"错误": 0, "警告": 1, "提示": 2}
    issues = sorted(issues, key=lambda d: (order.get(d["severity"], 9), d["line"], d["col"]))
    if scope:
        lo, hi = scope
        issues = [d for d in issues if lo <= d["line"] <= hi]
    if not issues:
        return f"[OK] {path}: 该范围未发现可疑问题。"

    n_e = sum(1 for d in issues if d["severity"] == "错误")
    n_w = sum(1 for d in issues if d["severity"] == "警告")
    n_i = sum(1 for d in issues if d["severity"] == "提示")
    head = f"[DETECT] {path} — {len(issues)} 个问题 (错误 {n_e} · 警告 {n_w} · 提示 {n_i})\n"

    body = []
    for d in issues:
        loc = f"{d['line']}:{d['col']}"
        line = f"[{d['code']}] {d['severity']} @{loc} {d['title']}"
        if d.get("extra"):
            line += f" ({d['extra']})"
        body.append(line)
        if d.get("text"):
            body.append(f"   代码: {d['text']}")
        if d.get("fix"):
            body.append(f"   {d['fix']}")
    return head + "\n".join(body)


class Liugin:
    """本地 Python 智能检测 — 纯本地、零依赖、低配友好"""

    def __init__(self):
        self.cli = None
        self.usage = """本地 Python 智能检测 (py_detect)

纯本地、零第三方依赖的代码检测引擎 (仅标准库 ast/tokenize)。
三层算法: 语法错误精确定位 → 作用域语义检测 → 常见反模式扫描，
每条诊断自带中文解释与修复建议 (规则模板, 零 AI)。

操作:
  check <文件> [行号]       - 检测整个文件 / 只检测某一行
  check <文件> <起>-<止>    - 只检测某段范围 (如 10-30)
  rules [规则码]            - 列出全部规则 / 查看单条规则 (如 rules E002)
  version                   - 版本信息

示例:
  py_detect check main.py
  py_detect check main.py 12
  py_detect check main.py 10-30
  py_detect rules W004
"""

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "py_detect",
            "description": "本地 Python 智能检测 - 语法错误精确定位 + 未定义变量/未使用导入/可变默认参数/裸except等反模式扫描，纯本地零依赖，每条诊断带中文修复建议",
            "keywords": ["检测", "检查", "lint", "静态分析", "语法", "错误", "诊断", "代码质量", "审查"],
            "usage": self.usage,
        }

    def get_mcp_definition(self):
        return {
            "name": "py_detect",
            "description": "本地 Python 代码智能检测引擎: 语法错误、未定义变量、未使用导入、可变默认参数、裸 except、==None、迭代中修改列表、覆盖内置名、import*、除零、方法缺 self、死代码等",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["check", "rules", "version"],
                        "description": "操作: check 检测文件 / rules 列出规则 / version 版本",
                    },
                    "file": {"type": "string", "description": "要检测的 Python 文件路径"},
                    "scope": {"type": "string", "description": "检测范围, 如 '12' 或 '10-30' (可选)"},
                    "code": {"type": "string", "description": "查看单条规则 (rules 操作用, 可选)"},
                },
                "required": ["operation"],
            },
        }

    def handle(self, args: str) -> str:
        args = (args or "").strip()
        if not args:
            return self.usage

        parts = args.split()
        op = parts[0].lower()

        if op == "version":
            return f"py_detect v{__version__} - 纯本地智能检测 (零第三方依赖, 规则 {len(RULES)} 条)"

        if op == "rules":
            code = parts[1].upper() if len(parts) > 1 else ""
            return self._rules(code)

        if op == "check":
            return self._check(parts[1:])

        return f"未知操作: {op}\n\n{self.usage}"

    def _rules(self, code: str) -> str:
        if code:
            if code not in RULES:
                return f"没有规则 {code}。可用: {', '.join(sorted(RULES))}"
            sev, title, fix = RULES[code]
            return f"[{code}] {sev} {title}\n  {fix}"
        lines = [f"py_detect 规则表 (共 {len(RULES)} 条):", ""]
        for c in sorted(RULES):
            sev, title, _ = RULES[c]
            lines.append(f"  [{c}] {sev} - {title}")
        lines.append("")
        lines.append("查看单条: py_detect rules <规则码>")
        return "\n".join(lines)

    def _check(self, args: List[str]) -> str:
        if not args:
            return "用法: py_detect check <文件> [行号] 或 [起-止]"

        path = args[0]
        if not os.path.exists(path):
            return f"[X] 文件不存在: {path}"
        if os.path.isdir(path):
            return f"[X] {path} 是目录，请指定 .py 文件"

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
        except OSError as e:
            return f"[X] 读取失败: {e}"

        scope = None
        if len(args) > 1:
            scope = self._parse_scope(args[1])
            if scope is None:
                return "[X] 范围格式错误: 用 行号 (如 12) 或 起-止 (如 10-30)"

        try:
            issues = analyze(source, path)
        except Exception as e:
            return f"[!] 检测器内部错误: {e!r} (请反馈)"

        return format_report(path, issues, scope)

    def _parse_scope(self, raw: str) -> Optional[Tuple[int, int]]:
        raw = raw.strip()
        if raw.isdigit():
            n = int(raw)
            return (n, n)
        if "-" in raw:
            a, b = raw.split("-", 1)
            if a.isdigit() and b.isdigit():
                lo, hi = int(a), int(b)
                return (min(lo, hi), max(lo, hi))
        return None
