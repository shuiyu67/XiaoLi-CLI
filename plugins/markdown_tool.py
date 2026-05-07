"""
Markdown 工具插件 - Markdown 渲染、目录生成、格式转换
支持 TOC 生成、标题提取、表格生成、格式化、统计
"""

import re
import json
import os
from typing import List, Tuple


class Liugin:
    """Markdown 工具 - TOC/渲染/格式转换/统计"""

    def __init__(self):
        self.usage = """Markdown 工具

操作:
  toc <文件或Markdown>           - 生成目录 (Table of Contents)
  headings <文件或Markdown>      - 提取所有标题
  stats <文件或Markdown>         - 统计信息（字数/行数/段落数等）
  table <数据>                   - 从 JSON 数组生成 Markdown 表格
  checklist <文件>               - 提取所有待办事项
  links <文件或Markdown>         - 提取所有链接
  images <文件或Markdown>        - 提取所有图片
  frontmatter <文件>             - 提取 YAML frontmatter
  format <文件或Markdown>        - 格式化（标题层级、列表缩进等）
  wordcount <文件或Markdown>     - 详细字数统计
  outline <文件或Markdown>       - 生成大纲视图
  lint <文件>                    - Markdown 语法检查

示例:
  markdown_tool toc README.md
  markdown_tool stats article.md
  markdown_tool table '[{"name":"Alice","age":25},{"name":"Bob","age":30}]'
  markdown_tool checklist TODO.md
  markdown_tool links README.md
  markdown_tool lint README.md
"""
        self.cli = None

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "markdown_tool",
            "description": "Markdown 工具 - TOC 生成、标题提取、统计、表格生成、语法检查",
            "keywords": ["markdown", "md", "目录", "toc", "标题", "表格", "统计", "链接", "检查"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "markdown_tool",
            "description": "Markdown 工具，支持 TOC、统计、表格生成、链接提取、语法检查",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["toc", "headings", "stats", "table", "checklist",
                                 "links", "images", "frontmatter", "format",
                                 "wordcount", "outline", "lint"],
                        "description": "操作类型"
                    },
                    "input": {"type": "string", "description": "Markdown 文件路径或内容"},
                    "data": {"type": "string", "description": "JSON 数据（table 操作用）"}
                },
                "required": ["operation", "input"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        inp = arguments.get("input", "")
        return f"{op} {inp}".strip()

    def _load_content(self, text: str) -> Tuple[str, str]:
        """加载内容（文件路径或文本）"""
        if os.path.isfile(text):
            with open(text, 'r', encoding='utf-8') as f:
                return f.read(), f"文件: {text}"
        return text, "文本输入"

    def handle(self, args: str) -> str:
        try:
            parts = self._parse_args(args)
            if not parts:
                return "错误：请提供操作类型"

            operation = parts[0].lower()
            handlers = {
                "toc": self._op_toc,
                "headings": self._op_headings,
                "stats": self._op_stats,
                "table": self._op_table,
                "checklist": self._op_checklist,
                "links": self._op_links,
                "images": self._op_images,
                "frontmatter": self._op_frontmatter,
                "format": self._op_format,
                "wordcount": self._op_wordcount,
                "outline": self._op_outline,
                "lint": self._op_lint,
            }

            handler = handlers.get(operation)
            if not handler:
                return f"错误：不支持的操作 '{operation}'"
            return handler(parts[1:])

        except Exception as e:
            return f"Markdown 工具错误: {str(e)}"

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

    def _extract_headings(self, content: str) -> List[Tuple[int, str, str]]:
        """提取标题: [(level, text, slug)]"""
        headings = []
        in_code = False
        for line in content.split('\n'):
            if line.strip().startswith('```'):
                in_code = not in_code
                continue
            if in_code:
                continue
            match = re.match(r'^(#{1,6})\s+(.+)', line)
            if match:
                level = len(match.group(1))
                text = match.group(2).strip()
                # 生成 slug
                slug = re.sub(r'[^\w\s-]', '', text.lower())
                slug = re.sub(r'\s+', '-', slug.strip())
                headings.append((level, text, slug))
        return headings

    def _op_toc(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供 Markdown 文件或内容"
        content, source = self._load_content(args[0])
        headings = self._extract_headings(content)

        if not headings:
            return "📭 未找到标题"

        result = f"  目录 ({source}):\n"
        result += "─" * 40 + "\n"
        for level, text, slug in headings:
            indent = "  " * (level - 1)
            result += f"{indent}- [{text}](#{slug})\n"
        return result.rstrip()

    def _op_headings(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供 Markdown 文件或内容"
        content, source = self._load_content(args[0])
        headings = self._extract_headings(content)

        if not headings:
            return "📭 未找到标题"

        result = f"  标题列表 ({len(headings)} 个):\n"
        for level, text, _ in headings:
            prefix = "#" * level
            result += f"   {prefix:8s} {text}\n"
        return result.rstrip()

    def _op_stats(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供 Markdown 文件或内容"
        content, source = self._load_content(args[0])

        lines = content.split('\n')
        total_lines = len(lines)
        blank_lines = sum(1 for l in lines if not l.strip())
        code_blocks = content.count('```') // 2
        headings = len(self._extract_headings(content))
        links = len(re.findall(r'\[([^\]]+)\]\([^)]+\)', content))
        images = len(re.findall(r'!\[([^\]]*)\]\([^)]+\)', content))
        # 中文字符
        chinese = len(re.findall(r'[\u4e00-\u9fff]', content))
        # 英文单词
        english = len(re.findall(r'[a-zA-Z]+', content))

        # 段落数（连续非空行）
        paragraphs = 0
        in_para = False
        for l in lines:
            if l.strip():
                if not in_para:
                    paragraphs += 1
                    in_para = True
            else:
                in_para = False

        result = f"📊 Markdown 统计 ({source})\n"
        result += "─" * 35 + "\n"
        result += f"   总行数: {total_lines}\n"
        result += f"   空行: {blank_lines}\n"
        result += f"   段落: {paragraphs}\n"
        result += f"   代码块: {code_blocks}\n"
        result += f"   标题: {headings}\n"
        result += f"   链接: {links}\n"
        result += f"   图片: {images}\n"
        result += f"   中文字: {chinese}\n"
        result += f"   英文词: {english}\n"
        result += f"   字符数: {len(content)}\n"
        return result.rstrip()

    def _op_table(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供 JSON 数组"
        data_str = args[0]
        try:
            data = json.loads(data_str)
        except json.JSONDecodeError as e:
            return f"❌ JSON 解析错误: {e}"

        if not isinstance(data, list) or not data:
            return "❌ 需要非空 JSON 数组"
        if not isinstance(data[0], dict):
            return "❌ 数组元素必须是对象"

        headers = list(data[0].keys())
        # 计算列宽
        widths = {h: len(h) for h in headers}
        for row in data:
            for h in headers:
                widths[h] = max(widths[h], len(str(row.get(h, ""))))

        # 生成表格
        header_line = "| " + " | ".join(h.ljust(widths[h]) for h in headers) + " |"
        sep_line = "| " + " | ".join("-" * widths[h] for h in headers) + " |"
        rows = []
        for row in data:
            rows.append("| " + " | ".join(str(row.get(h, "")).ljust(widths[h]) for h in headers) + " |")

        result = f"  Markdown 表格 ({len(data)} 行):\n\n"
        result += header_line + "\n" + sep_line + "\n" + "\n".join(rows)
        return result

    def _op_checklist(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供 Markdown 文件"
        content, source = self._load_content(args[0])

        todos = []
        done = []
        for i, line in enumerate(content.split('\n'), 1):
            match = re.match(r'^(\s*)[-*]\s*\[([ xX])\]\s*(.+)', line)
            if match:
                indent = match.group(1)
                checked = match.group(2).lower() == 'x'
                text = match.group(3).strip()
                if checked:
                    done.append((i, text))
                else:
                    todos.append((i, text))

        result = f"  待办事项 ({source}):\n"
        result += "─" * 45 + "\n"
        result += f"  ☑ 已完成: {len(done)} 个\n"
        result += f"   未完成: {len(todos)} 个\n"
        result += "─" * 45 + "\n"

        if todos:
            result += "\n  未完成:\n"
            for line_no, text in todos[:30]:
                result += f"   L{line_no:4d}  {text}\n"
        if done:
            result += "\n  已完成:\n"
            for line_no, text in done[:20]:
                result += f"   L{line_no:4d}  {text}\n"
        return result.rstrip()

    def _op_links(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供 Markdown 文件或内容"
        content, source = self._load_content(args[0])

        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
        if not links:
            return f"📭 未找到链接 ({source})"

        result = f"  链接列表 ({len(links)} 个, {source}):\n"
        result += "─" * 50 + "\n"
        seen = set()
        for text, url in links:
            if url not in seen:
                seen.add(url)
                result += f"   {text[:30]:30s} → {url}\n"
        return result.rstrip()

    def _op_images(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供 Markdown 文件或内容"
        content, source = self._load_content(args[0])

        images = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', content)
        if not images:
            return f"📭 未找到图片 ({source})"

        result = f" ️  图片列表 ({len(images)} 个, {source}):\n"
        result += "─" * 50 + "\n"
        seen = set()
        for alt, url in images:
            if url not in seen:
                seen.add(url)
                result += f"   {alt[:25]:25s} → {url}\n"
        return result.rstrip()

    def _op_frontmatter(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供 Markdown 文件"
        content, source = self._load_content(args[0])

        match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not match:
            return f"📭 未找到 frontmatter ({source})"

        fm = match.group(1)
        result = f"  Frontmatter ({source}):\n"
        result += "─" * 35 + "\n"
        result += fm
        return result

    def _op_format(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供 Markdown 文件或内容"
        content, source = self._load_content(args[0])
        lines = content.split('\n')
        formatted = []
        prev_blank = False

        for line in lines:
            stripped = line.strip()
            # 确保标题前后有空行
            if re.match(r'^#{1,6}\s', stripped):
                if formatted and not prev_blank:
                    formatted.append('')
                formatted.append(stripped)
                prev_blank = False
                continue
            # 确保列表项格式一致
            if re.match(r'^[-*]\s', stripped):
                formatted.append(re.sub(r'^[-*]\s', '- ', stripped))
                prev_blank = False
                continue
            # 去除多余空行
            if not stripped:
                if not prev_blank:
                    formatted.append('')
                    prev_blank = True
                continue

            prev_blank = False
            formatted.append(line.rstrip())

        # 确保文件末尾有换行
        while formatted and not formatted[-1]:
            formatted.pop()
        formatted.append('')

        return f"✅ 格式化完成 ({source}):\n" + '\n'.join(formatted)

    def _op_wordcount(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供 Markdown 文件或内容"
        content, source = self._load_content(args[0])

        # 移除代码块
        no_code = re.sub(r'```[\s\S]*?```', '', content)
        # 移除行内代码
        no_code = re.sub(r'`[^`]+`', '', no_code)
        # 移除链接标记
        no_code = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', no_code)
        # 移除图片标记
        no_code = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', no_code)
        # 移除标题标记
        no_code = re.sub(r'^#{1,6}\s+', '', no_code, flags=re.MULTILINE)
        # 移除加粗/斜体标记
        no_code = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', no_code)

        chinese = len(re.findall(r'[\u4e00-\u9fff]', no_code))
        english_words = re.findall(r'[a-zA-Z]+', no_code)
        english = len(english_words)
        total_chars = len(no_code.strip())

        # 阅读时间估算（中文 300字/分钟, 英文 200词/分钟）
        read_time_cn = chinese / 300
        read_time_en = english / 200
        read_time = read_time_cn + read_time_en

        result = f"  详细字数统计 ({source}):\n"
        result += "─" * 35 + "\n"
        result += f"   中文字数: {chinese}\n"
        result += f"   英文单词: {english}\n"
        result += f"   总字符数: {total_chars}\n"
        result += f"   预计阅读: {read_time:.1f} 分钟\n"
        return result.rstrip()

    def _op_outline(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供 Markdown 文件或内容"
        content, source = self._load_content(args[0])
        headings = self._extract_headings(content)

        if not headings:
            return "📭 未找到标题"

        result = f"  大纲视图 ({source}):\n"
        result += "═" * 40 + "\n"
        for level, text, _ in headings:
            if level == 1:
                result += f"\n  {text}\n"
                result += "─" * 30 + "\n"
            elif level == 2:
                result += f"   {text}\n"
            elif level == 3:
                result += f"     {text}\n"
            else:
                result += f"       {'·' * (level - 3)} {text}\n"
        return result.rstrip()

    def _op_lint(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供 Markdown 文件"
        file_path = args[0]
        if not os.path.isfile(file_path):
            return f"❌ 文件不存在: {file_path}"

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.split('\n')

        issues = []
        in_code = False
        prev_blank = False
        heading_levels = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # 代码块跟踪
            if stripped.startswith('```'):
                in_code = not in_code
                continue
            if in_code:
                continue

            # 检查标题格式
            heading_match = re.match(r'^(#{1,6})\s+(.+)', line)
            if heading_match:
                level = len(heading_match.group(1))
                text = heading_match.group(2)
                # 检查标题前后空行
                if i > 1 and lines[i - 2].strip() and not lines[i - 2].startswith('#'):
                    issues.append(f"  L{i:4d} 标题前缺少空行")
                # 检查标题层级跳跃
                if heading_levels and level > heading_levels[-1] + 1:
                    issues.append(f"  L{i:4d} 标题层级跳跃 ({heading_levels[-1]} → {level})")
                heading_levels.append(level)
                # 检查标题末尾空格
                if text != text.rstrip():
                    issues.append(f"  L{i:4d} 标题末尾有多余空格")
            else:
                # 检查行尾空格
                if line != line.rstrip() and stripped:
                    trailing = len(line) - len(line.rstrip())
                    if trailing >= 2:  # 2个以上空格是换行符
                        pass  # 这是合法的 Markdown 换行
                    elif trailing > 0:
                        issues.append(f"  L{i:4d} 行尾有多余空格")

                # 检查连续空行
                if not stripped:
                    if prev_blank:
                        issues.append(f"  L{i:4d} 连续空行")
                    prev_blank = True
                else:
                    prev_blank = False

                # 检查列表格式
                list_match = re.match(r'^(\s*)[-*+]\s', line)
                if list_match:
                    indent = len(list_match.group(1))
                    if indent % 2 != 0 and indent > 0:
                        issues.append(f"  L{i:4d} 列表缩进不是2的倍数")

                # 检查链接格式
                if re.search(r'\[[^\]]*\]\(\s*\)', line):
                    issues.append(f"  L{i:4d} 链接URL为空")

                # 检查重复词
                words = stripped.lower().split()
                for j in range(len(words) - 1):
                    if len(words[j]) > 2 and words[j] == words[j + 1]:
                        issues.append(f"  L{i:4d} 重复词: '{words[j]}'")

        result = f" ️  Markdown 语法检查 ({file_path}):\n"
        result += "─" * 45 + "\n"

        if not issues:
            result += "   未发现问题！\n"
        else:
            result += f"   发现 {len(issues)} 个问题:\n\n"
            for issue in issues[:50]:
                result += f"  {issue}\n"
            if len(issues) > 50:
                result += f"\n   ... 还有 {len(issues) - 50} 个问题\n"

        return result.rstrip()


def test_plugin():
    plugin = Liugin()
    print("Markdown 工具测试:")
    print(plugin.handle('headings "# Hello\\n## World\\n### Sub"'))
    print(plugin.handle('stats "# Hello\\n\\nThis is a test."'))
    print(plugin.handle('table \'[{"name":"Alice","age":25},{"name":"Bob","age":30}]\''))


if __name__ == "__main__":
    test_plugin()
