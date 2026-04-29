"""
代码片段管理器插件 - 保存、搜索、复用常用代码片段
支持分类、标签、搜索、导出，JSON 持久化存储
"""

import json
import os
import time
import hashlib
from datetime import datetime
from typing import List, Optional


class Plugin:
    """代码片段管理器 - 保存和复用代码片段"""

    def __init__(self):
        self.usage = """代码片段管理器

操作:
  add <名称> -l <语言> -c "代码" [-t 标签1,标签2] [-d 描述]
                                  - 添加代码片段
  list [-l 语言] [-t 标签]       - 列出片段（可按语言/标签过滤）
  get <名称或ID>                 - 获取片段详情
  search <关键词>                 - 搜索片段（名称/描述/代码/标签）
  delete <名称或ID>              - 删除片段
  edit <名称或ID> -c "新代码"    - 更新片段代码
  export [文件]                  - 导出所有片段
  import <文件>                  - 导入片段
  tags                           - 列出所有标签
  stats                          - 统计信息
  copy <名称或ID>                - 复制到剪贴板（如可用）
  recent [-n 数量]               - 最近添加的片段

示例:
  snippet_manager add quick_sort -l python -c "def qsort(arr): ..." -t 排序,算法
  snippet_manager list -l python
  snippet_manager search 排序
  snippet_manager get quick_sort
"""
        self.cli = None
        self.snippets_file = "snippets.json"
        self.snippets = []
        self._load_snippets()

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "snippet_manager",
            "description": "代码片段管理器 - 保存、搜索、复用常用代码片段，支持分类和标签",
            "keywords": ["代码", "片段", "snippet", "模板", "复用", "保存", "搜索", "代码片段"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "snippet_manager",
            "description": "代码片段管理器，支持添加、搜索、获取、删除代码片段",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["add", "list", "get", "search", "delete",
                                 "edit", "export", "import", "tags", "stats", "recent"],
                        "description": "操作类型"
                    },
                    "name": {"type": "string", "description": "片段名称或ID"},
                    "language": {"type": "string", "description": "编程语言"},
                    "code": {"type": "string", "description": "代码内容"},
                    "tags": {"type": "string", "description": "标签（逗号分隔）"},
                    "description": {"type": "string", "description": "描述"},
                    "keyword": {"type": "string", "description": "搜索关键词"},
                    "file": {"type": "string", "description": "文件路径"},
                    "count": {"type": "integer", "description": "数量"}
                },
                "required": ["operation"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        name = arguments.get("name", "")
        return f"{op} {name}".strip()

    def _load_snippets(self):
        try:
            if os.path.exists(self.snippets_file):
                with open(self.snippets_file, 'r', encoding='utf-8') as f:
                    self.snippets = json.load(f)
        except Exception:
            self.snippets = []

    def _save_snippets(self):
        try:
            with open(self.snippets_file, 'w', encoding='utf-8') as f:
                json.dump(self.snippets, f, ensure_ascii=False, indent=2)
            return None
        except Exception as e:
            return f"保存失败: {e}"

    def _gen_id(self, name: str) -> str:
        return hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:8]

    def handle(self, args: str) -> str:
        try:
            parts = self._parse_args(args)
            if not parts:
                return self._op_list([])

            operation = parts[0].lower()
            handlers = {
                "add": self._op_add,
                "list": self._op_list,
                "get": self._op_get,
                "search": self._op_search,
                "delete": self._op_delete,
                "edit": self._op_edit,
                "export": self._op_export,
                "import": self._op_import,
                "tags": self._op_tags,
                "stats": self._op_stats,
                "recent": self._op_recent,
                "copy": self._op_copy,
            }

            handler = handlers.get(operation)
            if not handler:
                return f"错误：不支持的操作 '{operation}'"
            return handler(parts[1:])

        except Exception as e:
            return f"片段管理错误: {str(e)}"

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

    def _op_add(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供片段名称"
        name = args[0]
        language, code, tags, desc = "", "", [], ""

        i = 1
        while i < len(args):
            if args[i] == "-l" and i + 1 < len(args):
                language = args[i + 1]; i += 1
            elif args[i] == "-c" and i + 1 < len(args):
                code = args[i + 1]; i += 1
            elif args[i] == "-t" and i + 1 < len(args):
                tags = [t.strip() for t in args[i + 1].split(",") if t.strip()]; i += 1
            elif args[i] == "-d" and i + 1 < len(args):
                desc = args[i + 1]; i += 1
            i += 1

        if not code:
            return "错误：请用 -c 提供代码内容"

        # 检查重名
        for s in self.snippets:
            if s["name"] == name:
                return f"错误：片段 '{name}' 已存在，用 edit 更新"

        snippet = {
            "id": self._gen_id(name),
            "name": name,
            "language": language,
            "code": code,
            "tags": tags,
            "description": desc,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "usage_count": 0
        }
        self.snippets.append(snippet)
        err = self._save_snippets()
        if err:
            return err
        return f"✅ 已添加片段 '{name}' (ID: {snippet['id']}, 语言: {language or '未指定'})"

    def _op_list(self, args: List[str]) -> str:
        lang_filter, tag_filter = None, None
        i = 0
        while i < len(args):
            if args[i] == "-l" and i + 1 < len(args):
                lang_filter = args[i + 1].lower(); i += 1
            elif args[i] == "-t" and i + 1 < len(args):
                tag_filter = args[i + 1].lower(); i += 1
            i += 1

        filtered = self.snippets
        if lang_filter:
            filtered = [s for s in filtered if s.get("language", "").lower() == lang_filter]
        if tag_filter:
            filtered = [s for s in filtered if any(tag_filter in t.lower() for t in s.get("tags", []))]

        if not filtered:
            return "📭 没有找到代码片段"

        result = f"\n📝 代码片段列表 (共 {len(filtered)} 个)\n"
        result += "─" * 55 + "\n"
        for s in filtered:
            lang = s.get("language", "未知")
            tags = ", ".join(s.get("tags", [])) if s.get("tags") else ""
            code_preview = s.get("code", "")[:60].replace("\n", "↵")
            result += f"  [{s['id']}] {s['name']} ({lang})\n"
            if tags:
                result += f"    ️  {tags}\n"
            result += f"    {code_preview}...\n"
            result += f"    ⏱ {s.get('created_at', '未知')}\n\n"

        result += "─" * 55
        return result

    def _op_get(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供片段名称或ID"
        key = args[0]
        snippet = self._find_snippet(key)
        if not snippet:
            return f"❌ 未找到片段: {key}"

        snippet["usage_count"] = snippet.get("usage_count", 0) + 1
        self._save_snippets()

        result = f"\n  片段: {snippet['name']}\n"
        result += "─" * 50 + "\n"
        result += f"  ID: {snippet['id']}\n"
        result += f"  语言: {snippet.get('language', '未指定')}\n"
        if snippet.get("tags"):
            result += f" ️  标签: {', '.join(snippet['tags'])}\n"
        if snippet.get("description"):
            result += f"  描述: {snippet['description']}\n"
        result += f"  创建: {snippet.get('created_at', '未知')}\n"
        result += f"  使用: {snippet.get('usage_count', 0)} 次\n"
        result += "─" * 50 + "\n"
        result += f" 代码:\n{snippet['code']}\n"
        result += "─" * 50
        return result

    def _op_search(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供搜索关键词"
        keyword = " ".join(args).lower()

        results = []
        for s in self.snippets:
            searchable = f"{s['name']} {s.get('description', '')} {s.get('code', '')} {' '.join(s.get('tags', []))} {s.get('language', '')}".lower()
            if keyword in searchable:
                results.append(s)

        if not results:
            return f" 未找到匹配 '{keyword}' 的片段"

        output = f"  搜索结果 ({len(results)} 个):\n"
        output += "─" * 50 + "\n"
        for s in results:
            lang = s.get("language", "")
            output += f"  [{s['id']}] {s['name']} ({lang}) - {s.get('description', '')[:40]}\n"
        return output.rstrip()

    def _op_delete(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供片段名称或ID"
        key = args[0]
        for i, s in enumerate(self.snippets):
            if s["name"] == key or s["id"] == key:
                removed = self.snippets.pop(i)
                self._save_snippets()
                return f" ️  已删除片段: {removed['name']}"
        return f"❌ 未找到片段: {key}"

    def _op_edit(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供片段名称或ID"
        key = args[0]
        snippet = self._find_snippet(key)
        if not snippet:
            return f"❌ 未找到片段: {key}"

        new_code = None
        new_desc = None
        i = 1
        while i < len(args):
            if args[i] == "-c" and i + 1 < len(args):
                new_code = args[i + 1]; i += 1
            elif args[i] == "-d" and i + 1 < len(args):
                new_desc = args[i + 1]; i += 1
            i += 1

        if new_code:
            snippet["code"] = new_code
        if new_desc:
            snippet["description"] = new_desc
        snippet["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self._save_snippets()
        return f"✅ 已更新片段: {snippet['name']}"

    def _op_export(self, args: List[str]) -> str:
        output_file = args[0] if args else "snippets_export.json"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.snippets, f, ensure_ascii=False, indent=2)
            return f"✅ 已导出 {len(self.snippets)} 个片段到: {output_file}"
        except Exception as e:
            return f"❌ 导出失败: {e}"

    def _op_import(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供导入文件路径"
        file_path = args[0]
        if not os.path.isfile(file_path):
            return f"❌ 文件不存在: {file_path}"
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported = json.load(f)
            if not isinstance(imported, list):
                return "❌ 文件格式错误：需要 JSON 数组"

            existing_names = {s["name"] for s in self.snippets}
            added = 0
            for s in imported:
                if isinstance(s, dict) and s.get("name") and s["name"] not in existing_names:
                    s["id"] = self._gen_id(s["name"])
                    self.snippets.append(s)
                    existing_names.add(s["name"])
                    added += 1

            self._save_snippets()
            return f"✅ 已导入 {added} 个片段 (跳过 {len(imported) - added} 个重复)"
        except Exception as e:
            return f"❌ 导入失败: {e}"

    def _op_tags(self, args: List[str]) -> str:
        tag_count = {}
        for s in self.snippets:
            for t in s.get("tags", []):
                tag_count[t] = tag_count.get(t, 0) + 1

        if not tag_count:
            return " ️  暂无标签"

        result = " ️  标签列表:\n"
        for tag, count in sorted(tag_count.items(), key=lambda x: -x[1]):
            result += f"   {tag} ({count})\n"
        return result.rstrip()

    def _op_stats(self, args: List[str]) -> str:
        total = len(self.snippets)
        if not total:
            return "📊 暂无片段"

        lang_count = {}
        total_usage = 0
        for s in self.snippets:
            lang = s.get("language", "未知")
            lang_count[lang] = lang_count.get(lang, 0) + 1
            total_usage += s.get("usage_count", 0)

        result = f"📊 片段统计\n"
        result += "─" * 30 + "\n"
        result += f"   总数: {total}\n"
        result += f"   总使用: {total_usage} 次\n"
        result += f"   语言分布:\n"
        for lang, count in sorted(lang_count.items(), key=lambda x: -x[1]):
            result += f"     {lang}: {count}\n"
        return result.rstrip()

    def _op_recent(self, args: List[str]) -> str:
        count = 5
        for i, a in enumerate(args):
            if a == "-n" and i + 1 < len(args):
                count = int(args[i + 1])

        recent = sorted(self.snippets, key=lambda s: s.get("created_at", ""), reverse=True)[:count]
        if not recent:
            return "📭 暂无片段"

        result = f"⏰ 最近 {len(recent)} 个片段:\n"
        for s in recent:
            result += f"  [{s['id']}] {s['name']} - {s.get('created_at', '')}\n"
        return result.rstrip()

    def _op_copy(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供片段名称或ID"
        snippet = self._find_snippet(args[0])
        if not snippet:
            return f"❌ 未找到片段: {args[0]}"

        snippet["usage_count"] = snippet.get("usage_count", 0) + 1
        self._save_snippets()
        return f" 代码内容 ({snippet['name']}):\n{snippet['code']}"

    def _find_snippet(self, key: str) -> Optional[dict]:
        for s in self.snippets:
            if s["name"] == key or s["id"] == key:
                return s
        return None


def test_plugin():
    plugin = Plugin()
    print("代码片段管理器测试:")
    print(plugin.handle('add hello -l python -c "print(\'Hello, World!\')" -t 示例,入门 -d 最简单的Python程序'))
    print(plugin.handle('add fib -l python -c "def fib(n): return n if n < 2 else fib(n-1)+fib(n-2)" -t 算法,递归'))
    print(plugin.handle('list'))
    print(plugin.handle('search python'))


if __name__ == "__main__":
    test_plugin()
