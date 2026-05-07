"""
JSON 工具箱插件 - JSON 格式化、校验、查询、转换
提供 JSON 美化、压缩、验证、路径查询、类型转换等功能
"""

import json
import os
import re
from typing import List


class Liugin:
    """JSON 工具箱 - 格式化/校验/查询/转换"""

    def __init__(self):
        self.usage = """JSON 工具箱

操作:
  format <文件或JSON>             - 美化 JSON（自动缩进）
  minify <文件或JSON>             - 压缩 JSON（去除空白）
  validate <文件或JSON>           - 校验 JSON 是否合法
  query <文件或JSON> <路径>       - 按路径查询值（如 users[0].name）
  keys <文件或JSON>               - 列出所有键（扁平化）
  diff <文件1> <文件2>            - 比较两个 JSON 的差异
  to_csv <文件或JSON>             - 将 JSON 数组转为 CSV
  merge <文件1> <文件2>           - 合并两个 JSON 对象
  sample <文件或JSON> [-n 数量]   - 从数组中随机采样
  schema <文件或JSON>             - 推断 JSON Schema

示例:
  json_toolkit format data.json
  json_toolkit validate '{"name": "test"}'
  json_toolkit query config.json "database.host"
  json_toolkit keys data.json
  json_toolkit diff a.json b.json
"""
        self.cli = None

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "json_toolkit",
            "description": "JSON 工具箱 - 格式化、压缩、校验、路径查询、键提取、差异比较、转换",
            "keywords": ["json", "格式化", "校验", "查询", "格式", "转换", "美化", "压缩", "validate", "format"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "json_toolkit",
            "description": "JSON 工具箱，支持格式化、压缩、校验、路径查询、键提取、差异比较",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["format", "minify", "validate", "query", "keys",
                                 "diff", "to_csv", "merge", "sample", "schema"],
                        "description": "操作类型"
                    },
                    "input": {"type": "string", "description": "JSON 字符串或文件路径"},
                    "path": {"type": "string", "description": "查询路径（query 操作用）"},
                    "input2": {"type": "string", "description": "第二个 JSON 输入（diff/merge 用）"},
                    "count": {"type": "integer", "description": "采样数量（sample 操作用）"}
                },
                "required": ["operation", "input"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        inp = arguments.get("input", "")
        path = arguments.get("path", "")
        parts = [op, inp]
        if path:
            parts.append(path)
        return " ".join(parts)

    def handle(self, args: str) -> str:
        try:
            parts = self._parse_args(args)
            if not parts:
                return "错误：请提供操作类型"

            operation = parts[0].lower()
            handlers = {
                "format": self._op_format,
                "minify": self._op_minify,
                "validate": self._op_validate,
                "query": self._op_query,
                "keys": self._op_keys,
                "diff": self._op_diff,
                "to_csv": self._op_to_csv,
                "merge": self._op_merge,
                "sample": self._op_sample,
                "schema": self._op_schema,
            }

            handler = handlers.get(operation)
            if not handler:
                return f"错误：不支持的操作 '{operation}'\n支持: {', '.join(handlers.keys())}"
            return handler(parts[1:])

        except Exception as e:
            return f"JSON 工具错误: {str(e)}"

    def _parse_args(self, args: str) -> List[str]:
        parts, current, in_quotes, qc = [], "", False, None
        for ch in args:
            if ch in ('"', "'") and not in_quotes:
                in_quotes, qc = True, ch
            elif ch == qc and in_quotes:
                in_quotes, qc = False, None
            elif ch == ' ' and not in_quotes:
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += ch
        if current:
            parts.append(current)
        return parts

    def _load_json(self, text: str):
        """加载 JSON（支持文件路径或 JSON 字符串）"""
        if os.path.isfile(text):
            with open(text, 'r', encoding='utf-8') as f:
                return json.load(f), f"文件: {text}"
        try:
            return json.loads(text), "JSON 字符串"
        except json.JSONDecodeError as e:
            raise ValueError(f"无效的 JSON: {e}")

    def _op_format(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供 JSON 文件或字符串"
        data, source = self._load_json(args[0])
        formatted = json.dumps(data, indent=2, ensure_ascii=False)
        return f"✅ 格式化结果 ({source}):\n{formatted}"

    def _op_minify(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供 JSON 文件或字符串"
        data, source = self._load_json(args[0])
        minified = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        original_len = len(json.dumps(data, indent=2, ensure_ascii=False))
        saved = original_len - len(minified)
        return f"✅ 压缩结果 ({source}):\n{minified}\n\n📊 大小: {len(minified)} 字符 (节省 {saved} 字符, {saved/original_len*100:.1f}%)"

    def _op_validate(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供 JSON 文件或字符串"
        text = args[0]
        try:
            if os.path.isfile(text):
                with open(text, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                source = f"文件: {text}"
            else:
                data = json.loads(text)
                source = "JSON 字符串"

            depth = self._get_depth(data)
            keys_count = self._count_keys(data)

            result = f"✅ JSON 合法 ({source})\n"
            result += f"   类型: {type(data).__name__}\n"
            result += f"   嵌套深度: {depth}\n"
            result += f"   键总数: {keys_count}"
            return result
        except json.JSONDecodeError as e:
            return f"❌ JSON 无效:\n   行 {e.lineno}, 列 {e.colno}: {e.msg}"
        except Exception as e:
            return f"❌ 验证失败: {e}"

    def _op_query(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：格式: query <JSON或文件> <路径>\n示例: query data.json users[0].name"
        data, _ = self._load_json(args[0])
        path = args[1]

        result = data
        parts = re.findall(r'\w+|\[\d+\]', path)
        current_path = ""

        for part in parts:
            if part.startswith('['):
                idx = int(part[1:-1])
                current_path += part
                if isinstance(result, list) and 0 <= idx < len(result):
                    result = result[idx]
                else:
                    return f"❌ 路径 '{current_path}' 无效: 索引越界或非数组"
            else:
                current_path += f".{part}" if current_path else part
                if isinstance(result, dict) and part in result:
                    result = result[part]
                else:
                    return f"❌ 路径 '{current_path}' 无效: 键不存在"

        output = json.dumps(result, indent=2, ensure_ascii=False) if isinstance(result, (dict, list)) else str(result)
        return f"🔍 查询结果 ({path}):\n{output}"

    def _op_keys(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供 JSON 文件或字符串"
        data, _ = self._load_json(args[0])

        keys = []
        self._flatten_keys(data, "", keys)

        result = f"🔑 键列表 (共 {len(keys)} 个):\n"
        for k in keys:
            result += f"   {k}\n"
        return result.rstrip()

    def _flatten_keys(self, obj, prefix, keys):
        if isinstance(obj, dict):
            for k, v in obj.items():
                full_key = f"{prefix}.{k}" if prefix else k
                keys.append(full_key)
                self._flatten_keys(v, full_key, keys)
        elif isinstance(obj, list) and obj:
            self._flatten_keys(obj[0], f"{prefix}[0]", keys)

    def _op_diff(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：请提供两个 JSON 文件或字符串"
        data1, src1 = self._load_json(args[0])
        data2, src2 = self._load_json(args[1])

        diffs = []
        self._compare(data1, data2, "", diffs)

        if not diffs:
            return "✅ 两个 JSON 完全相同"

        result = f"🔀 差异比较 ({len(diffs)} 处不同):\n"
        for d in diffs[:50]:
            result += f"   {d}\n"
        if len(diffs) > 50:
            result += f"   ... 还有 {len(diffs) - 50} 处差异"
        return result.rstrip()

    def _compare(self, a, b, path, diffs):
        if type(a) != type(b):
            diffs.append(f"  类型不同 @ {path or '根'}: {type(a).__name__} vs {type(b).__name__}")
            return
        if isinstance(a, dict):
            all_keys = set(a.keys()) | set(b.keys())
            for k in sorted(all_keys):
                p = f"{path}.{k}" if path else k
                if k not in a:
                    diffs.append(f"➕ 新增 @ {p}: {b[k]}")
                elif k not in b:
                    diffs.append(f"➖ 删除 @ {p}: {a[k]}")
                else:
                    self._compare(a[k], b[k], p, diffs)
        elif isinstance(a, list):
            if len(a) != len(b):
                diffs.append(f"  数组长度不同 @ {path}: {len(a)} vs {len(b)}")
            for i in range(min(len(a), len(b))):
                self._compare(a[i], b[i], f"{path}[{i}]", diffs)
        else:
            if a != b:
                diffs.append(f"  值不同 @ {path}: {a!r} → {b!r}")

    def _op_to_csv(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供 JSON 文件或字符串"
        data, _ = self._load_json(args[0])

        if not isinstance(data, list) or not data:
            return "错误：需要非空 JSON 数组"
        if not isinstance(data[0], dict):
            return "错误：数组元素必须是对象"

        headers = list(data[0].keys())
        lines = [",".join(headers)]
        for item in data:
            row = []
            for h in headers:
                val = str(item.get(h, ""))
                if "," in val or '"' in val or "\n" in val:
                    val = '"' + val.replace('"', '""') + '"'
                row.append(val)
            lines.append(",".join(row))

        csv_content = "\n".join(lines)
        return f"📊 CSV 转换结果 ({len(data)} 行):\n{csv_content}"

    def _op_merge(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：请提供两个 JSON 文件或字符串"
        data1, _ = self._load_json(args[0])
        data2, _ = self._load_json(args[1])

        if not isinstance(data1, dict) or not isinstance(data2, dict):
            return "错误：合并仅支持 JSON 对象"

        merged = self._deep_merge(data1, data2)
        return f"✅ 合并结果:\n{json.dumps(merged, indent=2, ensure_ascii=False)}"

    def _deep_merge(self, a, b):
        result = a.copy()
        for k, v in b.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self._deep_merge(result[k], v)
            else:
                result[k] = v
        return result

    def _op_sample(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供 JSON 文件或字符串"
        data, _ = self._load_json(args[0])
        count = 3
        for i, a in enumerate(args):
            if a == "-n" and i + 1 < len(args):
                count = int(args[i + 1])

        if not isinstance(data, list):
            return "错误：需要 JSON 数组"

        import random
        sampled = random.sample(data, min(count, len(data)))
        return f"🎲 随机采样 ({len(sampled)}/{len(data)}):\n{json.dumps(sampled, indent=2, ensure_ascii=False)}"

    def _op_schema(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供 JSON 文件或字符串"
        data, _ = self._load_json(args[0])
        schema = self._infer_schema(data)
        return f"📋 推断 Schema:\n{json.dumps(schema, indent=2, ensure_ascii=False)}"

    def _infer_schema(self, obj, depth=0):
        if depth > 10:
            return {"type": "any"}
        if isinstance(obj, dict):
            props = {}
            for k, v in obj.items():
                props[k] = self._infer_schema(v, depth + 1)
            return {"type": "object", "properties": props}
        elif isinstance(obj, list):
            if obj:
                return {"type": "array", "items": self._infer_schema(obj[0], depth + 1)}
            return {"type": "array", "items": {}}
        elif isinstance(obj, bool):
            return {"type": "boolean"}
        elif isinstance(obj, int):
            return {"type": "integer"}
        elif isinstance(obj, float):
            return {"type": "number"}
        else:
            return {"type": "string"}

    def _get_depth(self, obj, depth=0):
        if depth > 50:
            return depth
        if isinstance(obj, dict):
            return max((self._get_depth(v, depth + 1) for v in obj.values()), default=depth)
        elif isinstance(obj, list):
            return max((self._get_depth(v, depth + 1) for v in obj), default=depth)
        return depth

    def _count_keys(self, obj):
        if isinstance(obj, dict):
            return len(obj) + sum(self._count_keys(v) for v in obj.values())
        elif isinstance(obj, list):
            return sum(self._count_keys(v) for v in obj)
        return 0


def test_plugin():
    plugin = Liugin()
    print("JSON 工具箱测试:")
    print(plugin.handle('validate \'{"name": "test", "age": 25}\''))
    print(plugin.handle('format \'{"name":"test","items":[1,2,3]}\''))
    print(plugin.handle('keys \'{"database": {"host": "localhost", "port": 3306}}\''))
    print(plugin.handle('query \'{"users": [{"name": "Alice"}]}\' users[0].name'))


if __name__ == "__main__":
    test_plugin()
