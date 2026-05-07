"""
书签管理器插件 - 管理开发相关链接和资源
支持分类、标签、搜索、导入导出，JSON 持久化
"""

import json
import os
import hashlib
import time
from datetime import datetime
from typing import List, Optional


class Liugin:
    """书签管理器 - 开发资源和链接管理"""

    def __init__(self):
        self.usage = """书签管理器

操作:
  add <URL> -n <名称> [-c 分类] [-t 标签1,标签2] [-d 描述]
                                  - 添加书签
  list [-c 分类] [-t 标签]       - 列出书签
  open <名称或ID>                - 获取书签 URL
  search <关键词>                 - 搜索书签
  delete <名称或ID>              - 删除书签
  edit <名称或ID> [-n 名称] [-d 描述] [-c 分类] [-t 标签]
                                  - 编辑书签
  categories                     - 列出所有分类
  tags                           - 列出所有标签
  export [文件]                  - 导出书签
  import <文件>                  - 导入书签
  stats                          - 统计信息
  recent [-n 数量]               - 最近添加的书签
  check                          - 检查书签是否可访问
  favicon <URL>                  - 获取网站 favicon URL

示例:
  bookmark_manager add https://github.com -n GitHub -c 开发 -t 代码,托管 -d 代码托管平台
  bookmark_manager list -c 开发
  bookmark_manager search github
  bookmark_manager open GitHub
  bookmark_manager categories
"""
        self.cli = None
        self.bookmarks_file = "bookmarks.json"
        self.bookmarks = []
        self._load_bookmarks()

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "bookmark_manager",
            "description": "书签管理器 - 管理开发相关链接和资源，支持分类、标签、搜索",
            "keywords": ["书签", "链接", "收藏", "bookmark", "网址", "资源", "网站", "URL"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "bookmark_manager",
            "description": "书签管理器，支持添加、搜索、获取、删除书签",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["add", "list", "open", "search", "delete",
                                 "edit", "categories", "tags", "export",
                                 "import", "stats", "recent", "check"],
                        "description": "操作类型"
                    },
                    "url": {"type": "string", "description": "URL"},
                    "name": {"type": "string", "description": "书签名称"},
                    "category": {"type": "string", "description": "分类"},
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

    def _load_bookmarks(self):
        try:
            if os.path.exists(self.bookmarks_file):
                with open(self.bookmarks_file, 'r', encoding='utf-8') as f:
                    self.bookmarks = json.load(f)
        except Exception:
            self.bookmarks = []

    def _save_bookmarks(self):
        try:
            with open(self.bookmarks_file, 'w', encoding='utf-8') as f:
                json.dump(self.bookmarks, f, ensure_ascii=False, indent=2)
            return None
        except Exception as e:
            return f"保存失败: {e}"

    def _gen_id(self, url: str) -> str:
        return hashlib.md5(f"{url}{time.time()}".encode()).hexdigest()[:8]

    def handle(self, args: str) -> str:
        try:
            parts = self._parse_args(args)
            if not parts:
                return self._op_list([])

            operation = parts[0].lower()
            handlers = {
                "add": self._op_add,
                "list": self._op_list,
                "open": self._op_open,
                "search": self._op_search,
                "delete": self._op_delete,
                "edit": self._op_edit,
                "categories": self._op_categories,
                "tags": self._op_tags,
                "export": self._op_export,
                "import": self._op_import,
                "stats": self._op_stats,
                "recent": self._op_recent,
                "check": self._op_check,
                "favicon": self._op_favicon,
            }

            handler = handlers.get(operation)
            if not handler:
                return f"错误：不支持的操作 '{operation}'"
            return handler(parts[1:])

        except Exception as e:
            return f"书签管理错误: {str(e)}"

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
            return "错误：请提供 URL"
        url = args[0]
        name, category, tags, desc = "", "", [], ""

        i = 1
        while i < len(args):
            if args[i] == "-n" and i + 1 < len(args):
                name = args[i + 1]; i += 1
            elif args[i] == "-c" and i + 1 < len(args):
                category = args[i + 1]; i += 1
            elif args[i] == "-t" and i + 1 < len(args):
                tags = [t.strip() for t in args[i + 1].split(",") if t.strip()]; i += 1
            elif args[i] == "-d" and i + 1 < len(args):
                desc = args[i + 1]; i += 1
            i += 1

        if not name:
            # 从 URL 推断名称
            from urllib.parse import urlparse
            parsed = urlparse(url if '://' in url else 'https://' + url)
            name = parsed.netloc.replace('www.', '').split('.')[0].capitalize()
            url = parsed.geturl()

        # 检查重复
        for b in self.bookmarks:
            if b["url"] == url:
                return f"错误：URL 已存在 (书签: {b['name']})"

        bookmark = {
            "id": self._gen_id(url),
            "name": name,
            "url": url,
            "category": category,
            "tags": tags,
            "description": desc,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "access_count": 0
        }
        self.bookmarks.append(bookmark)
        err = self._save_bookmarks()
        if err:
            return err
        return f"✅ 已添加书签 '{name}'\n   URL: {url}\n   分类: {category or '未分类'}"

    def _op_list(self, args: List[str]) -> str:
        cat_filter, tag_filter = None, None
        i = 0
        while i < len(args):
            if args[i] == "-c" and i + 1 < len(args):
                cat_filter = args[i + 1].lower(); i += 1
            elif args[i] == "-t" and i + 1 < len(args):
                tag_filter = args[i + 1].lower(); i += 1
            i += 1

        filtered = self.bookmarks
        if cat_filter:
            filtered = [b for b in filtered if b.get("category", "").lower() == cat_filter]
        if tag_filter:
            filtered = [b for b in filtered if any(tag_filter in t.lower() for t in b.get("tags", []))]

        if not filtered:
            return "📭 没有找到书签"

        # 按分类分组
        grouped = {}
        for b in filtered:
            cat = b.get("category", "未分类")
            grouped.setdefault(cat, []).append(b)

        result = f"\n  书签列表 (共 {len(filtered)} 个)\n"
        result += "═" * 55 + "\n"

        for cat, items in sorted(grouped.items()):
            result += f"\n  {cat} ({len(items)} 个)\n"
            result += "─" * 45 + "\n"
            for b in items:
                tags = ", ".join(b.get("tags", [])) if b.get("tags") else ""
                result += f"  [{b['id']}] {b['name']}\n"
                result += f"     {b['url']}\n"
                if tags:
                    result += f"    ️  {tags}\n"
                if b.get("description"):
                    result += f"    {b['description'][:50]}\n"
                result += "\n"

        return result.rstrip()

    def _op_open(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供书签名称或 ID"
        key = args[0]
        bookmark = self._find_bookmark(key)
        if not bookmark:
            return f"❌ 未找到书签: {key}"

        bookmark["access_count"] = bookmark.get("access_count", 0) + 1
        self._save_bookmarks()

        return (f"  {bookmark['name']}\n"
                f"   URL: {bookmark['url']}\n"
                f"   访问次数: {bookmark.get('access_count', 0)}")

    def _op_search(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供搜索关键词"
        keyword = " ".join(args).lower()

        results = []
        for b in self.bookmarks:
            searchable = f"{b['name']} {b['url']} {b.get('description', '')} {' '.join(b.get('tags', []))} {b.get('category', '')}".lower()
            if keyword in searchable:
                results.append(b)

        if not results:
            return f" 未找到匹配 '{keyword}' 的书签"

        output = f"  搜索结果 ({len(results)} 个):\n"
        output += "─" * 50 + "\n"
        for b in results:
            output += f"  [{b['id']}] {b['name']} - {b['url']}\n"
            if b.get("description"):
                output += f"    {b['description'][:40]}\n"
        return output.rstrip()

    def _op_delete(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供书签名称或 ID"
        key = args[0]
        for i, b in enumerate(self.bookmarks):
            if b["name"].lower() == key.lower() or b["id"] == key:
                removed = self.bookmarks.pop(i)
                self._save_bookmarks()
                return f" ️  已删除书签: {removed['name']} ({removed['url']})"
        return f"❌ 未找到书签: {key}"

    def _op_edit(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供书签名称或 ID"
        key = args[0]
        bookmark = self._find_bookmark(key)
        if not bookmark:
            return f"❌ 未找到书签: {key}"

        i = 1
        while i < len(args):
            if args[i] == "-n" and i + 1 < len(args):
                bookmark["name"] = args[i + 1]; i += 1
            elif args[i] == "-d" and i + 1 < len(args):
                bookmark["description"] = args[i + 1]; i += 1
            elif args[i] == "-c" and i + 1 < len(args):
                bookmark["category"] = args[i + 1]; i += 1
            elif args[i] == "-t" and i + 1 < len(args):
                bookmark["tags"] = [t.strip() for t in args[i + 1].split(",") if t.strip()]; i += 1
            i += 1

        bookmark["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save_bookmarks()
        return f"✅ 已更新书签: {bookmark['name']}"

    def _op_categories(self, args: List[str]) -> str:
        cat_count = {}
        for b in self.bookmarks:
            cat = b.get("category", "未分类")
            cat_count[cat] = cat_count.get(cat, 0) + 1

        if not cat_count:
            return "  暂无分类"

        result = "  分类列表:\n"
        for cat, count in sorted(cat_count.items(), key=lambda x: -x[1]):
            bar = "█" * min(count, 20)
            result += f"   {cat:15s} {bar} ({count})\n"
        return result.rstrip()

    def _op_tags(self, args: List[str]) -> str:
        tag_count = {}
        for b in self.bookmarks:
            for t in b.get("tags", []):
                tag_count[t] = tag_count.get(t, 0) + 1

        if not tag_count:
            return " ️  暂无标签"

        result = " ️  标签列表:\n"
        for tag, count in sorted(tag_count.items(), key=lambda x: -x[1]):
            result += f"   {tag} ({count})\n"
        return result.rstrip()

    def _op_export(self, args: List[str]) -> str:
        output_file = args[0] if args else "bookmarks_export.json"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.bookmarks, f, ensure_ascii=False, indent=2)
            return f"✅ 已导出 {len(self.bookmarks)} 个书签到: {output_file}"
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

            existing_urls = {b["url"] for b in self.bookmarks}
            added = 0
            for b in imported:
                if isinstance(b, dict) and b.get("url") and b["url"] not in existing_urls:
                    b["id"] = self._gen_id(b["url"])
                    self.bookmarks.append(b)
                    existing_urls.add(b["url"])
                    added += 1

            self._save_bookmarks()
            return f"✅ 已导入 {added} 个书签 (跳过 {len(imported) - added} 个重复)"
        except Exception as e:
            return f"❌ 导入失败: {e}"

    def _op_stats(self, args: List[str]) -> str:
        total = len(self.bookmarks)
        if not total:
            return "📊 暂无书签"

        cat_count = {}
        total_access = 0
        for b in self.bookmarks:
            cat = b.get("category", "未分类")
            cat_count[cat] = cat_count.get(cat, 0) + 1
            total_access += b.get("access_count", 0)

        most_accessed = max(self.bookmarks, key=lambda b: b.get("access_count", 0))

        result = f"📊 书签统计\n"
        result += "─" * 35 + "\n"
        result += f"   总数: {total}\n"
        result += f"   总访问: {total_access} 次\n"
        result += f"   分类数: {len(cat_count)}\n"
        result += f"   最常访问: {most_accessed['name']} ({most_accessed.get('access_count', 0)} 次)\n"
        result += f"\n   分类分布:\n"
        for cat, count in sorted(cat_count.items(), key=lambda x: -x[1]):
            result += f"     {cat}: {count}\n"
        return result.rstrip()

    def _op_recent(self, args: List[str]) -> str:
        count = 5
        for i, a in enumerate(args):
            if a == "-n" and i + 1 < len(args):
                count = int(args[i + 1])

        recent = sorted(self.bookmarks, key=lambda b: b.get("created_at", ""), reverse=True)[:count]
        if not recent:
            return "📭 暂无书签"

        result = f"⏰ 最近 {len(recent)} 个书签:\n"
        for b in recent:
            result += f"  [{b['id']}] {b['name']} - {b.get('created_at', '')}\n"
        return result.rstrip()

    def _op_check(self, args: List[str]) -> str:
        import socket
        from urllib.parse import urlparse

        bookmarks = self.bookmarks
        if args:
            # 检查指定书签
            bookmark = self._find_bookmark(args[0])
            if not bookmark:
                return f"❌ 未找到书签: {args[0]}"
            bookmarks = [bookmark]

        result = f" ️  书签可访问性检查 ({len(bookmarks)} 个):\n"
        result += "─" * 50 + "\n"

        for b in bookmarks[:20]:
            url = b["url"]
            try:
                parsed = urlparse(url)
                host = parsed.netloc or parsed.path.split('/')[0]
                socket.create_connection((host, 80), timeout=3)
                result += f"   {b['name']} ({host})\n"
            except (socket.timeout, socket.error, OSError):
                result += f"   {b['name']} ({host}) - 不可达\n"

        if len(bookmarks) > 20:
            result += f"   ... 仅检查前 20 个\n"
        return result.rstrip()

    def _op_favicon(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供 URL"
        url = args[0]
        if '://' not in url:
            url = 'https://' + url

        from urllib.parse import urlparse
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        favicon_url = f"{base}/favicon.ico"

        return (f"  Favicon:\n"
                f"   网站: {base}\n"
                f"   Favicon: {favicon_url}\n"
                f"   Google: https://www.google.com/s2/favicons?domain={parsed.netloc}&sz=64")

    def _find_bookmark(self, key: str) -> Optional[dict]:
        for b in self.bookmarks:
            if b["name"].lower() == key.lower() or b["id"] == key:
                return b
        return None


def test_plugin():
    plugin = Liugin()
    print("书签管理器测试:")
    print(plugin.handle('add https://github.com -n GitHub -c 开发 -t 代码,托管 -d 代码托管平台'))
    print(plugin.handle('add https://stackoverflow.com -n StackOverflow -c 学习 -t 问答,编程'))
    print(plugin.handle('list'))
    print(plugin.handle('search github'))


if __name__ == "__main__":
    test_plugin()
