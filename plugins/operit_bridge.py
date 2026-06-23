"""
Operit Bridge — xiaoli-cli 原生 Liugin 插件
===========================================
让 xiaoli-cli 兼容 Operit AI 的第三方工具格式。

自动扫描 plugins/operit/ 子目录下所有 .js/.ts 脚本，
解析 METADATA 块，注册为 xiaoli-cli 可调用的工具。
"""
import os
import re
import json
import glob
import importlib.util
from typing import Dict, List, Optional


# ═══════════════════════════════════════════════════════════════
#  Operit METADATA 解析器
# ═══════════════════════════════════════════════════════════════

def _hjson_to_json(raw: str) -> str:
    """
    将 Operit 的 HJSON 风格元数据转为标准 JSON。
    逐行解析，处理: 无引号键名、单引号/三引号字符串、嵌套双引号、// 注释、尾逗号。
    """
    SQ = chr(39)  # '
    DQ = chr(34)  # "
    result = []
    i = 0
    n = len(raw)

    def skip_ws():
        nonlocal i
        while i < n and raw[i] in ' \t\r\n':
            i += 1

    def parse_string_val(quote):
        """解析引号字符串，正确处理转义"""
        nonlocal i
        i += 1  # skip opening quote
        chars = []
        while i < n:
            ch = raw[i]
            if ch == '\\':
                chars.append(ch)
                i += 1
                if i < n:
                    chars.append(raw[i])
                    i += 1
            elif ch == quote:
                i += 1  # skip closing quote
                return ''.join(chars)
            else:
                chars.append(ch)
                i += 1
        return ''.join(chars)  # unclosed

    def parse_triple_string():
        """解析 '''...''' 三引号字符串"""
        nonlocal i
        i += 3  # skip '''
        chars = []
        while i < n - 2:
            if raw[i:i+3] == SQ * 3:
                i += 3
                return ''.join(chars)
            chars.append(raw[i])
            i += 1
        return ''.join(chars)

    def parse_unquoted_val():
        """解析无引号值，到行尾或逗号/}等"""
        nonlocal i
        chars = []
        depth = 0
        while i < n:
            ch = raw[i]
            if ch == '{' or ch == '[':
                depth += 1
                chars.append(ch)
                i += 1
            elif ch == '}' or ch == ']':
                if depth <= 0:
                    break
                depth -= 1
                chars.append(ch)
                i += 1
            elif ch == ',' and depth == 0:
                break
            elif ch == '\n' and depth == 0:
                break
            else:
                chars.append(ch)
                i += 1
        return ''.join(chars).strip()

    def escape_for_json(s):
        """转义字符串为 JSON 安全格式"""
        return json.dumps(s)

    # ── 主解析循环 ──
    skip_ws()
    if i >= n or raw[i] != '{':
        return raw  # 不是对象
    result.append('{')
    i += 1

    expect_comma = False
    while i < n:
        skip_ws()
        if i >= n:
            break
        ch = raw[i]

        # 对象结束
        if ch == '}':
            result.append('}')
            i += 1
            break
        # 数组结束
        if ch == ']':
            result.append(']')
            i += 1
            break
        # 逗号
        if ch == ',':
            result.append(',')
            i += 1
            expect_comma = False
            continue

        # 注释
        if ch == '/' and i + 1 < n and raw[i+1] == '/':
            while i < n and raw[i] != '\n':
                i += 1
            continue

        # 如果需要逗号但遇到新键/值，自动补逗号
        if expect_comma and (ch == '"' or ch == SQ or ch.isalpha() or ch == '_' or ch == '{' or ch == '['):
            result.append(',')
            expect_comma = False

        # 解析 key
        key = None
        if ch == '"':
            key = parse_string_val('"')
        elif ch == SQ:
            if i + 2 < n and raw[i+1] == SQ and raw[i+2] == SQ:
                key = parse_triple_string()
            else:
                key = parse_string_val(SQ)
        elif ch.isalpha() or ch == '_':
            # 无引号键名
            start = i
            while i < n and (raw[i].isalnum() or raw[i] == '_'):
                i += 1
            key = raw[start:i]

        if key is None:
            i += 1
            continue

        skip_ws()
        if i >= n or raw[i] != ':':
            continue
        i += 1  # skip ':'
        skip_ws()

        # 输出 key
        result.append(escape_for_json(key))
        result.append(':')

        # 解析 value
        if i >= n:
            break
        vch = raw[i]

        if vch == '"':
            # 双引号字符串
            val = parse_string_val('"')
            result.append(escape_for_json(val))
        elif vch == SQ:
            if i + 2 < n and raw[i+1] == SQ and raw[i+2] == SQ:
                val = parse_triple_string()
            else:
                val = parse_string_val(SQ)
            result.append(escape_for_json(val))
        elif vch == '{' or vch == '[':
            # 嵌套对象/数组 — 递归处理
            if vch == '{':
                depth = 1
                j = i + 1
                while j < n and depth > 0:
                    if raw[j] == '{': depth += 1
                    elif raw[j] == '}': depth -= 1
                    j += 1
                inner = raw[i:j]
                result.append(_hjson_to_json(inner))
                i = j
            else:
                # 数组 — 找匹配的 ]，对内部每个元素递归
                depth = 1
                j = i + 1
                while j < n and depth > 0:
                    if raw[j] == '[': depth += 1
                    elif raw[j] == ']': depth -= 1
                    j += 1
                arr_inner = raw[i+1:j-1].strip()
                result.append('[')
                # 按顶层逗号分割数组元素
                elems = []
                elem_start = 0
                d = 0
                for k, c in enumerate(arr_inner):
                    if c in '{[': d += 1
                    elif c in '}]': d -= 1
                    elif c == ',' and d == 0:
                        elems.append(arr_inner[elem_start:k])
                        elem_start = k + 1
                elems.append(arr_inner[elem_start:])
                for ei, elem in enumerate(elems):
                    elem = elem.strip()
                    if not elem:
                        continue
                    if ei > 0:
                        result.append(',')
                    if elem.startswith('{'):
                        result.append(_hjson_to_json(elem))
                    elif elem.startswith('['):
                        # 嵌套数组
                        result.append(_hjson_to_json('{"_":' + elem + '}')[6:-1])
                    else:
                        # 普通值
                        if elem.startswith('"') or elem.startswith(SQ):
                            q = elem[0]
                            if len(elem) >= 3 and elem[1] == q and elem[2] == q:
                                val = elem[3:-3]
                            else:
                                val = elem[1:-1]
                            result.append(json.dumps(val))
                        elif elem in ('true', 'false', 'null'):
                            result.append(elem)
                        else:
                            try:
                                float(elem)
                                result.append(elem)
                            except ValueError:
                                result.append(json.dumps(elem))
                result.append(']')
                i = j
        elif vch in ('t', 'f', 'n') and raw[i:i+4] in ('true', 'null'):
            result.append(raw[i:i+4])
            i += 4
        elif vch == 'f' and raw[i:i+5] == 'false':
            result.append('false')
            i += 5
        elif vch.isdigit() or vch == '-':
            start = i
            while i < n and (raw[i].isdigit() or raw[i] in '.-eE+'):
                i += 1
            result.append(raw[start:i])
        else:
            # 无引号字符串值
            val = parse_unquoted_val()
            if val:
                result.append(escape_for_json(val))

        expect_comma = True

    return ''.join(result)


def parse_operit_metadata(file_path: str) -> Optional[Dict]:
    """
    从 JS/TS 文件中提取 /* METADATA ... */ 块并解析为 dict。
    支持 Operit 完整 schema: name, display_name, description, author, category, env, tools, states
    同时兼容标准 JSON 和 HJSON 风格（无引号键名、单引号、三引号、注释）。
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (FileNotFoundError, UnicodeDecodeError):
        return None

    # 匹配 /* METADATA ... */ 块
    pattern = r'/\*\s*METADATA\s*\n?(.*?)\*/'
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return None

    raw = match.group(1).strip()

    # 先尝试标准 JSON
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 尝试 HJSON 转换
    try:
        cleaned = _hjson_to_json(raw)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # 最后兜底: 移除注释和尾逗号再试
        fallback = re.sub(r'//.*$', '', raw, flags=re.MULTILINE)
        fallback = re.sub(r',\s*([}\]])', r'\1', fallback)
        try:
            return json.loads(fallback)
        except json.JSONDecodeError:
            return None


def _localized(field, lang="zh") -> str:
    """解析 Operit 多语言字段: 字符串 或 {zh, en, default} 对象"""
    if isinstance(field, str):
        return field
    if isinstance(field, dict):
        for key in [lang, lang.split("-")[0], "default"]:
            if key in field:
                return field[key]
        return next(iter(field.values()), "")
    return str(field) if field else ""


# ═══════════════════════════════════════════════════════════════
#  格式转换: Operit ↔ MCP
# ═══════════════════════════════════════════════════════════════

_TYPE_MAP = {
    "string": "string", "number": "number", "integer": "integer",
    "boolean": "boolean", "object": "object", "array": "array",
}


def operit_tool_to_mcp(tool_def: Dict, script_name: str) -> Dict:
    """Operit tool 定义 → MCP inputSchema 格式"""
    properties, required = {}, []
    for p in tool_def.get("parameters", []):
        pname = p.get("name", "")
        properties[pname] = {
            "type": _TYPE_MAP.get(p.get("type", "string"), "string"),
            "description": p.get("description", ""),
        }
        if p.get("required", False):
            required.append(pname)

    full_name = f"{script_name}__{tool_def.get('name', 'unknown')}"
    return {
        "name": full_name,
        "description": _localized(tool_def.get("description", "")),
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


def meta_to_tools(meta: Dict) -> List[Dict]:
    """一个 Operit METADATA → xiaoli-cli 工具列表"""
    script_name = meta.get("name", "unknown")
    category = meta.get("category", "")
    tools = []
    for td in meta.get("tools", []):
        mcp = operit_tool_to_mcp(td, script_name)
        tools.append({
            "name": mcp["name"],
            "description": mcp["description"],
            "keywords": _build_keywords(meta, td),
            "usage": _build_usage(mcp),
            "mcp_definition": mcp,
            "source": "operit",
            "script_name": script_name,
            "original_tool_name": td.get("name", ""),
        })
    return tools


def _build_keywords(meta: Dict, tool_def: Dict) -> List[str]:
    kw = ["operit"]
    for s in [meta.get("name", ""), tool_def.get("name", ""), meta.get("category", "")]:
        if s and s not in kw:
            kw.append(s)
    for text in [_localized(meta.get("description", "")), _localized(tool_def.get("description", ""))]:
        for w in re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]{3,}', text):
            if w not in kw:
                kw.append(w)
    return kw


def _build_usage(mcp: Dict) -> str:
    props = mcp.get("inputSchema", {}).get("properties", {})
    req = mcp.get("inputSchema", {}).get("required", [])
    lines = [f"Operit 工具: {mcp['name']}", mcp.get("description", ""), ""]
    if props:
        lines.append("参数:")
        for pn, pd in props.items():
            r = " (必填)" if pn in req else ""
            lines.append(f"  {pn}: {pd.get('description', pd.get('type', ''))}{r}")
    lines.append(f'\n调用: {{"action":"use_tool","tool":"{mcp["name"]}","args":"..."}}')
    return "\n".join(lines)


def xiaoli_to_operit_js(plugin_instance) -> str:
    """将 xiaoli-cli 插件导出为 Operit METADATA JS 文件内容"""
    info = plugin_instance.get_tool_info()
    mcp = plugin_instance.get_mcp_definition()
    name = info.get("name", "Unknown")
    desc = info.get("description", "")
    schema = mcp.get("inputSchema", {})
    props = schema.get("properties", {})
    required = schema.get("required", [])

    parameters = []
    for pn, pd in props.items():
        parameters.append({
            "name": pn,
            "description": pd.get("description", ""),
            "type": pd.get("type", "string"),
            "required": pn in required,
        })

    metadata = {
        "name": name,
        "display_name": {"zh": desc[:50], "en": name},
        "description": {"zh": desc, "en": desc},
        "author": ["xiaoli-cli"],
        "category": "Utility",
        "tools": [{
            "name": "execute",
            "description": {"zh": f"执行 {name}", "en": f"Execute {name}"},
            "parameters": parameters or [
                {"name": "args", "description": "操作参数", "type": "string", "required": True}
            ],
        }],
    }

    meta_json = json.dumps(metadata, indent=4, ensure_ascii=False)
    lines = [
        "/*", "METADATA", meta_json, "*/", "",
        f"// Auto-generated from xiaoli-cli plugin: {name}",
        f"// Compatible with Operit AI tool system", "",
        f"const {name}Bridge = (function () {{",
        "    async function wrap(func, params) {",
        "        try { return await func(params); }",
        '        catch (e) { return { success: false, message: "执行失败: " + e.message }; }',
        "    }",
        "    async function execute(params) {",
        f"        // 由 xiaoli-cli {name} 插件提供",
        '        const args = params.args || JSON.stringify(params);',
        f'        const cmd = "cd /path/to/xiaoli-cli && python3 -c \\"'
        f"import sys; sys.path.insert(0, '.'); "
        f"from plugins.{name} import Liugin; p = Liugin(); "
        f"""print(p.handle('\\" + args + \\"'))\\\\"";""",
        "        try { return { success: true, data: await Tools.System.execute(cmd) }; }",
        "        catch (e) { return { success: false, message: e.message }; }",
        "    }",
        "    return { execute: function(p) { return wrap(execute, p); } };",
        "})();",
        f"exports.execute = {name}Bridge.execute;",
    ]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
#  Liugin 插件主体
# ═══════════════════════════════════════════════════════════════

class Liugin:
    """
    Operit Bridge — 让 xiaoli-cli 兼容 Operit AI 第三方工具格式。

    自动扫描 plugins/operit/ 子目录，解析所有 Operit METADATA 脚本，
    注册为 xiaoli-cli 可调用的工具。支持双向格式转换和导出。
    """

    def __init__(self):
        self.cli = None
        # 已加载的 Operit 工具: name -> tool_info
        self._operit_tools: Dict[str, Dict] = {}
        # 脚本源文件映射
        self._script_files: Dict[str, str] = {}

    def set_cli(self, cli):
        self.cli = cli
        # 挂载后自动扫描 operit 子目录
        self._auto_scan()

    # ── 自动扫描 plugins/operit/ ──

    def _get_operit_dir(self) -> str:
        """获取 plugins/operit/ 绝对路径"""
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(plugin_dir, "operit")

    def _auto_scan(self):
        """启动时自动扫描 operit 子目录"""
        operit_dir = self._get_operit_dir()
        if not os.path.isdir(operit_dir):
            return
        count = 0
        for ext in ("*.js", "*.ts"):
            for fpath in glob.glob(os.path.join(operit_dir, "**", ext), recursive=True):
                meta = parse_operit_metadata(fpath)
                if meta:
                    for t in meta_to_tools(meta):
                        t["_source_file"] = fpath
                        self._operit_tools[t["name"]] = t
                    self._script_files[meta.get("name", "")] = fpath
                    count += 1
        if count:
            print(f"[operit_bridge] 自动加载了 {count} 个 Operit 脚本, "
                  f"{len(self._operit_tools)} 个工具")

    # ── Liugin 协议接口 ──

    def get_tool_info(self):
        return {
            "name": "operit_bridge",
            "description": "Operit 双向工具桥接 — 自动加载 plugins/operit/ 下的 Operit 脚本, "
                           "支持解析/扫描/导出/格式转换",
            "keywords": [
                "operit", "bridge", "桥接", "兼容", "格式转换", "METADATA",
                "插件互通", "第三方工具", "脚本", "导入", "导出",
            ],
            "usage": (
                "operit_bridge <操作> [参数]\n"
                "操作:\n"
                "  scan [目录]       - 扫描 Operit 脚本目录 (默认 plugins/operit/)\n"
                "  list              - 列出已加载的 Operit 工具\n"
                "  parse <文件>      - 解析单个 Operit METADATA 文件\n"
                "  info <工具名>     - 查看工具详情\n"
                "  export <插件名>   - 将 xiaoli-cli 插件导出为 Operit 格式\n"
                "  export_all [目录] - 导出所有插件\n"
                "  convert_mcp <JSON>    - MCP → Operit\n"
                "  convert_operit <JSON> - Operit → MCP"
            ),
        }

    def get_mcp_definition(self):
        return {
            "name": "operit_bridge",
            "description": "Operit 双向工具桥接，自动加载 plugins/operit/ 目录下的 Operit 格式脚本",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["scan", "list", "parse", "info",
                                 "export", "export_all", "convert_mcp", "convert_operit"],
                        "description": "操作类型",
                    },
                    "target": {
                        "type": "string",
                        "description": "目标路径/插件名/JSON",
                    },
                },
                "required": ["operation"],
            },
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        target = arguments.get("target", "")
        return f"{op} {target}".strip()

    def handle(self, args: str) -> str:
        parts = args.strip().split(maxsplit=1)
        if not parts:
            return self._help()
        op = parts[0].lower()
        target = parts[1].strip() if len(parts) > 1 else ""
        handler = {
            "scan": self._h_scan, "list": self._h_list,
            "parse": self._h_parse, "info": self._h_info,
            "export": self._h_export, "export_all": self._h_export_all,
            "convert_mcp": self._h_convert_mcp, "convert_operit": self._h_convert_operit,
        }.get(op)
        if not handler:
            return f"错误: 不支持的操作 '{op}'\n{self._help()}"
        try:
            return handler(target)
        except Exception as e:
            return f"Operit Bridge 错误: {e}"

    def _help(self):
        return (
            "Operit Bridge — 可用操作:\n"
            "  scan [目录]       - 扫描 Operit 脚本\n"
            "  list              - 列出已加载工具\n"
            "  parse <文件>      - 解析单个 METADATA 文件\n"
            "  info <工具名>     - 查看工具详情\n"
            "  export <插件名>   - 导出 xiaoli 插件为 Operit 格式\n"
            "  export_all [目录] - 批量导出\n"
            "  convert_mcp <JSON>    - MCP → Operit\n"
            "  convert_operit <JSON> - Operit → MCP"
        )

    # ═══════════════════════════════════════════════════════════
    #  操作实现
    # ═══════════════════════════════════════════════════════════

    def _h_scan(self, target: str) -> str:
        """扫描 Operit 脚本目录"""
        operit_dir = target or self._get_operit_dir()
        if not os.path.isdir(operit_dir):
            return f"错误: 目录不存在 — {operit_dir}\n请将 Operit 脚本放入 plugins/operit/ 目录"

        found, tool_count = 0, 0
        for ext in ("*.js", "*.ts"):
            for fpath in glob.glob(os.path.join(operit_dir, "**", ext), recursive=True):
                meta = parse_operit_metadata(fpath)
                if meta:
                    tools = meta_to_tools(meta)
                    for t in tools:
                        t["_source_file"] = fpath
                        self._operit_tools[t["name"]] = t
                    self._script_files[meta.get("name", "")] = fpath
                    found += 1
                    tool_count += len(tools)

        lines = [f"✓ 扫描完成: {operit_dir}", f"  {found} 个脚本, {tool_count} 个工具", ""]
        for name, fpath in self._script_files.items():
            lines.append(f"  📦 {name} — {os.path.basename(fpath)}")
        return "\n".join(lines)

    def _h_list(self, _: str) -> str:
        """列出已加载的 Operit 工具"""
        if not self._operit_tools:
            return ("暂无已加载的 Operit 工具。\n"
                    "请将 .js/.ts 脚本放入 plugins/operit/ 目录，或使用 scan <目录> 手动加载。")
        lines = [f"已加载 {len(self._operit_tools)} 个 Operit 工具:", ""]
        for name, t in self._operit_tools.items():
            src = os.path.basename(t.get("_source_file", "?"))
            lines.append(f"  🔧 {name}  [{src}]")
            desc = t.get("description", "")
            if desc:
                lines.append(f"     {desc[:80]}")
        return "\n".join(lines)

    def _h_parse(self, target: str) -> str:
        """解析单个 Operit METADATA 文件"""
        if not target:
            return "错误: 请提供文件路径"
        if not os.path.isfile(target):
            return f"错误: 文件不存在 — {target}"
        meta = parse_operit_metadata(target)
        if not meta:
            return f"错误: 未找到有效 METADATA 块 — {target}"

        tools = meta_to_tools(meta)
        for t in tools:
            t["_source_file"] = target
            self._operit_tools[t["name"]] = t

        lines = [
            f"✓ 解析成功: {target}",
            f"  脚本: {meta.get('name', 'N/A')}",
            f"  描述: {_localized(meta.get('description', ''))}",
            f"  分类: {meta.get('category', 'N/A')}",
        ]
        author = meta.get("author", [])
        if author:
            lines.append(f"  作者: {', '.join(author) if isinstance(author, list) else author}")
        lines.append(f"  工具数: {len(tools)}")
        lines.append("")
        for t in tools:
            mcp = t["mcp_definition"]
            props = mcp["inputSchema"]["properties"]
            req = mcp["inputSchema"]["required"]
            lines.append(f"  🔧 {t['name']}")
            lines.append(f"     {t['description']}")
            if props:
                ps = []
                for pn, pd in props.items():
                    r = "*" if pn in req else ""
                    ps.append(f"{pn}({pd.get('type', '?')}){r}")
                lines.append(f"     参数: {', '.join(ps)}")
        return "\n".join(lines)

    def _h_info(self, target: str) -> str:
        """查看工具详情"""
        if not target:
            return "错误: 请提供工具名"
        t = self._operit_tools.get(target)
        if not t:
            return f"错误: 未找到工具 '{target}'\n可用: {', '.join(self._operit_tools.keys()) or '无'}"
        lines = [
            f"工具: {t['name']}",
            f"描述: {t.get('description', '')}",
            f"来源: {t.get('_source_file', 'unknown')}",
            f"脚本: {t.get('script_name', 'N/A')}",
            f"原始名: {t.get('original_tool_name', 'N/A')}",
            f"关键词: {', '.join(t.get('keywords', []))}",
            "", "MCP 定义:",
            json.dumps(t.get("mcp_definition", {}), indent=2, ensure_ascii=False),
        ]
        return "\n".join(lines)

    def _h_export(self, target: str) -> str:
        """将 xiaoli-cli 插件导出为 Operit 格式"""
        if not target:
            return "错误: 请提供插件名"
        instance = self._load_xiaoli_plugin(target)
        if isinstance(instance, str):
            return instance  # error msg

        js = xiaoli_to_operit_js(instance)
        out_dir = os.path.join(self._get_operit_dir(), "exported")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{target}.js")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(js)
        return f"✓ 导出成功!\n  输出: {out_path}\n  可直接放入 Operit AI 使用"

    def _h_export_all(self, target: str) -> str:
        """批量导出所有 xiaoli 插件"""
        plugins_dir = os.path.dirname(os.path.abspath(__file__))
        out_dir = target or os.path.join(self._get_operit_dir(), "exported")
        os.makedirs(out_dir, exist_ok=True)
        exported, errors = [], []
        for fname in sorted(os.listdir(plugins_dir)):
            if not fname.endswith(".py") or fname == "__init__.py":
                continue
            name = fname[:-3]
            try:
                spec = importlib.util.spec_from_file_location(name, os.path.join(plugins_dir, fname))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                cls = getattr(mod, 'Liugin', None) or getattr(mod, 'Plugin', None)
                if cls:
                    inst = cls()
                    with open(os.path.join(out_dir, f"{name}.js"), "w", encoding="utf-8") as f:
                        f.write(xiaoli_to_operit_js(inst))
                    exported.append(name)
            except Exception as e:
                errors.append(f"{name}: {e}")
        lines = [f"✓ 批量导出完成", f"  目录: {out_dir}", f"  成功: {len(exported)}"]
        if errors:
            lines.append(f"  失败: {len(errors)}")
            for err in errors[:5]:
                lines.append(f"    ⚠ {err}")
        return "\n".join(lines)

    def _h_convert_mcp(self, target: str) -> str:
        """MCP → Operit METADATA"""
        if not target:
            return "错误: 请提供 MCP JSON"
        mcp = json.loads(target)
        name = mcp.get("name", "unknown")
        desc = mcp.get("description", "")
        props = mcp.get("inputSchema", {}).get("properties", {})
        required = mcp.get("inputSchema", {}).get("required", [])
        params = []
        for pn, pd in props.items():
            params.append({"name": pn, "description": pd.get("description", ""),
                           "type": pd.get("type", "string"), "required": pn in required})
        operit = {
            "name": name,
            "display_name": {"zh": desc[:50] or name, "en": name},
            "description": {"zh": desc, "en": desc},
            "author": ["xiaoli-cli"],
            "category": "Utility",
            "tools": [{"name": "execute", "description": {"zh": f"执行 {name}", "en": f"Execute {name}"},
                       "parameters": params}],
        }
        return json.dumps(operit, indent=2, ensure_ascii=False)

    def _h_convert_operit(self, target: str) -> str:
        """Operit → MCP"""
        if not target:
            return "错误: 请提供 Operit METADATA JSON"
        meta = json.loads(target)
        results = [operit_tool_to_mcp(t, meta.get("name", "unknown")) for t in meta.get("tools", [])]
        return json.dumps(results, indent=2, ensure_ascii=False)

    # ── 辅助 ──

    def _load_xiaoli_plugin(self, name: str):
        """加载一个 xiaoli-cli 插件实例，返回实例或错误字符串"""
        plugins_dir = os.path.dirname(os.path.abspath(__file__))
        fpath = os.path.join(plugins_dir, f"{name}.py")
        if not os.path.isfile(fpath):
            # 按 name 搜索
            for fname in os.listdir(plugins_dir):
                if fname.endswith(".py") and fname != "__init__.py":
                    try:
                        spec = importlib.util.spec_from_file_location(fname[:-3],
                                os.path.join(plugins_dir, fname))
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        cls = getattr(mod, 'Liugin', None) or getattr(mod, 'Plugin', None)
                        if cls:
                            inst = cls()
                            if inst.get_tool_info().get("name", "").lower() == name.lower():
                                return inst
                    except Exception:
                        continue
            return f"错误: 未找到插件 '{name}'"
        try:
            spec = importlib.util.spec_from_file_location(name, fpath)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            cls = getattr(mod, 'Liugin', None) or getattr(mod, 'Plugin', None)
            if not cls:
                return f"错误: 插件文件中未找到 Liugin/Plugin 类"
            return cls()
        except Exception as e:
            return f"错误: 加载失败 — {e}"

    # ── 给 plugin_manager 用的工具注册接口 ──

    def get_operit_tools_for_registration(self) -> List[Dict]:
        """
        返回所有已加载的 Operit 工具，格式兼容 plugin_manager.tools 列表。
        可被 cli_base 在初始化时调用，将 Operit 工具注入工具列表。
        """
        result = []
        for name, t in self._operit_tools.items():
            result.append({
                "name": name,
                "description": t.get("description", ""),
                "keywords": t.get("keywords", []),
                "usage": t.get("usage", ""),
                "handler": self._make_handler(name),
                "source": "operit",
            })
        return result

    def _make_handler(self, tool_name: str):
        """为 Operit 工具创建 handler 闭包"""
        tool_info = self._operit_tools.get(tool_name)
        if not tool_info:
            return lambda args: f"错误: 工具 {tool_name} 未加载"

        def handler(args: str) -> str:
            # 解析参数: 支持 JSON 和 "key=value" 两种格式
            params = {}
            args = args.strip()
            if args.startswith("{"):
                try:
                    params = json.loads(args)
                except json.JSONDecodeError:
                    params = {"args": args}
            else:
                # "city=北京 days=3" 格式
                for part in re.split(r'[;\s]+', args):
                    if '=' in part:
                        k, v = part.split('=', 1)
                        params[k.strip()] = v.strip()
                    elif part:
                        # 单个值填入第一个参数
                        schema_props = tool_info["mcp_definition"]["inputSchema"]["properties"]
                        for pname in schema_props:
                            if pname not in params:
                                params[pname] = part
                                break

            # 如果有 _source_file，尝试用 Node.js 执行
            source_file = tool_info.get("_source_file", "")
            original_name = tool_info.get("original_tool_name", "execute")

            if source_file and os.path.isfile(source_file):
                return self._exec_operit_script(source_file, original_name, params)

            # 否则返回参数解析结果（供 AI 理解）
            return json.dumps({
                "status": "parsed",
                "tool": tool_name,
                "original_tool": original_name,
                "source": source_file,
                "params": params,
                "note": "如需执行，请确保设备上有 Node.js 运行时",
            }, ensure_ascii=False)

        return handler

    def _exec_operit_script(self, source_file: str, func_name: str, params: Dict) -> str:
        """通过 Node.js 执行 Operit 脚本中的指定函数"""
        import subprocess
        import tempfile

        # 生成一个临时执行器脚本
        runner_code = f"""
const path = require('path');
const mod = require({json.dumps(source_file)});
const func = mod[{json.dumps(func_name)}];
if (!func) {{
    console.log(JSON.stringify({{error: "函数 '{func_name}' 不存在"}}));
    process.exit(1);
}}
const params = {json.dumps(params)};
func(params).then(result => {{
    console.log(JSON.stringify(result, null, 2));
}}).catch(err => {{
    console.log(JSON.stringify({{error: err.message}}));
    process.exit(1);
}});
"""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False,
                                              encoding='utf-8') as f:
                f.write(runner_code)
                runner_path = f.name

            result = subprocess.run(
                ["node", runner_path],
                capture_output=True, text=True, timeout=30,
            )
            os.unlink(runner_path)

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"执行失败: {result.stderr.strip() or result.stdout.strip()}"
        except FileNotFoundError:
            return ("错误: 未找到 Node.js 运行时。\n"
                    "请安装 Node.js 以执行 Operit 脚本，或将脚本移植为 Python 版本。")
        except subprocess.TimeoutExpired:
            return "错误: 脚本执行超时 (30s)"
        except Exception as e:
            return f"执行错误: {e}"
