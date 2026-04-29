"""
正则表达式测试器插件 - 测试、调试、管理正则表达式
支持匹配测试、提取、替换、常用模式库
"""

import re
import json
import os
from typing import List


class Plugin:
    """正则表达式测试器 - 测试、调试、管理正则"""

    def __init__(self):
        self.usage = """正则表达式测试器

操作:
  test <正则> <文本> [-f flags]   - 测试正则是否匹配
  match <正则> <文本> [-f flags]  - 提取所有匹配项
  replace <正则> <文本> <替换>    - 测试替换
  groups <正则> <文本>            - 显示分组信息
  explain <正则>                  - 解释正则含义
  flags <正则> <文本>             - 测试不同标志组合
  pattern [名称]                  - 列出/查看常用模式
  save <名称> <正则> [-d 描述]   - 保存自定义模式
  delete_pattern <名称>          - 删除自定义模式
  bench <正则> <文本> [-n 次数]  - 性能测试

标志 (flags):
  i - 忽略大小写  m - 多行模式  s - 点匹配换行
  x - 详细模式    a - ASCII模式

示例:
  regex_tester test "\\d+" "abc123def456"
  regex_tester match "[a-z]+@[a-z]+\\.[a-z]+" "test@example.com foo@bar.org"
  regex_tester groups "(\\w+)@(\\w+)\\.(\\w+)" "user@domain.com"
  regex_tester explain "[a-z]+@\\w+\\.\\w+"
  regex_tester pattern email
"""
        self.cli = None
        self.patterns_file = "regex_patterns.json"
        self.custom_patterns = self._load_patterns()

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "regex_tester",
            "description": "正则表达式测试器 - 测试匹配、提取、替换、解释、常用模式库",
            "keywords": ["正则", "regex", "匹配", "表达式", "测试", "替换", "提取", "模式"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "regex_tester",
            "description": "正则表达式测试器，支持匹配测试、提取、替换、解释、性能测试",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["test", "match", "replace", "groups", "explain",
                                 "flags", "pattern", "save", "bench"],
                        "description": "操作类型"
                    },
                    "pattern": {"type": "string", "description": "正则表达式"},
                    "text": {"type": "string", "description": "测试文本"},
                    "replacement": {"type": "string", "description": "替换文本"},
                    "flags": {"type": "string", "description": "标志 (i/m/s/x)"},
                    "name": {"type": "string", "description": "模式名称"},
                    "description": {"type": "string", "description": "模式描述"},
                    "count": {"type": "integer", "description": "测试次数"}
                },
                "required": ["operation"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        pattern = arguments.get("pattern", "")
        text = arguments.get("text", "")
        return f"{op} {pattern} {text}".strip()

    def _load_patterns(self):
        try:
            if os.path.exists(self.patterns_file):
                with open(self.patterns_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return self._default_patterns()

    def _save_patterns(self):
        try:
            with open(self.patterns_file, 'w', encoding='utf-8') as f:
                json.dump(self.custom_patterns, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _default_patterns(self):
        return {
            "email": {"pattern": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "desc": "邮箱地址"},
            "phone_cn": {"pattern": r"1[3-9]\d{9}", "desc": "中国手机号"},
            "url": {"pattern": r"https?://[^\s<>\"']+|www\.[^\s<>\"']+", "desc": "URL链接"},
            "ipv4": {"pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "desc": "IPv4地址"},
            "date": {"pattern": r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", "desc": "日期格式"},
            "time": {"pattern": r"\d{2}:\d{2}(:\d{2})?", "desc": "时间格式"},
            "chinese": {"pattern": r"[\u4e00-\u9fff]+", "desc": "中文字符"},
            "id_card": {"pattern": r"\d{17}[\dXx]", "desc": "身份证号"},
            "html_tag": {"pattern": r"<[^>]+>", "desc": "HTML标签"},
            "ip_port": {"pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}:\d{1,5}\b", "desc": "IP:端口"},
            "mac_addr": {"pattern": r"([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}", "desc": "MAC地址"},
            "hex_color": {"pattern": r"#[0-9A-Fa-f]{3,8}", "desc": "十六进制颜色"},
            "number": {"pattern": r"-?\d+\.?\d*", "desc": "数字（整数/浮点）"},
            "word": {"pattern": r"\b\w+\b", "desc": "单词"},
        }

    def handle(self, args: str) -> str:
        try:
            parts = self._parse_args(args)
            if not parts:
                return "错误：请提供操作类型"

            operation = parts[0].lower()
            handlers = {
                "test": self._op_test,
                "match": self._op_match,
                "replace": self._op_replace,
                "groups": self._op_groups,
                "explain": self._op_explain,
                "flags": self._op_flags,
                "pattern": self._op_pattern,
                "save": self._op_save,
                "delete_pattern": self._op_delete_pattern,
                "bench": self._op_bench,
            }

            handler = handlers.get(operation)
            if not handler:
                return f"错误：不支持的操作 '{operation}'"
            return handler(parts[1:])

        except Exception as e:
            return f"正则测试错误: {str(e)}"

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

    def _parse_flags(self, flags_str: str) -> int:
        flags = 0
        for c in flags_str.lower():
            if c == 'i': flags |= re.IGNORECASE
            elif c == 'm': flags |= re.MULTILINE
            elif c == 's': flags |= re.DOTALL
            elif c == 'x': flags |= re.VERBOSE
        return flags

    def _op_test(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：格式: test <正则> <文本> [-f 标志]"
        pattern_str, text = args[0], args[1]
        flags = 0
        for i, a in enumerate(args):
            if a == "-f" and i + 1 < len(args):
                flags = self._parse_flags(args[i + 1])

        try:
            pattern = re.compile(pattern_str, flags)
            match = pattern.search(text)
            if match:
                return (f"✅ 匹配成功!\n"
                        f"   正则: {pattern_str}\n"
                        f"   位置: {match.start()}-{match.end()}\n"
                        f"   匹配: '{match.group()}'\n"
                        f"   全文: {pattern.findall(text)}")
            else:
                return f"❌ 无匹配\n   正则: {pattern_str}\n   文本: {text[:100]}"
        except re.error as e:
            return f"❌ 正则语法错误: {e}"

    def _op_match(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：格式: match <正则> <文本>"
        pattern_str, text = args[0], args[1]
        flags = 0
        for i, a in enumerate(args):
            if a == "-f" and i + 1 < len(args):
                flags = self._parse_flags(args[i + 1])

        try:
            pattern = re.compile(pattern_str, flags)
            matches = pattern.finditer(text)

            results = []
            for m in matches:
                results.append(f"   [{m.start():3d}-{m.end():3d}] '{m.group()}'")

            if results:
                return f"  找到 {len(results)} 个匹配:\n" + "\n".join(results)
            else:
                return "❌ 未找到匹配"
        except re.error as e:
            return f"❌ 正则语法错误: {e}"

    def _op_replace(self, args: List[str]) -> str:
        if len(args) < 3:
            return "错误：格式: replace <正则> <文本> <替换>"
        pattern_str, text, replacement = args[0], args[1], args[2]

        try:
            result = re.sub(pattern_str, replacement, text)
            count = len(re.findall(pattern_str, text))
            return (f"  替换结果 ({count} 处):\n"
                    f"   原文: {text}\n"
                    f"   结果: {result}")
        except re.error as e:
            return f"❌ 正则语法错误: {e}"

    def _op_groups(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：格式: groups <正则> <文本>"
        pattern_str, text = args[0], args[1]

        try:
            pattern = re.compile(pattern_str)
            match = pattern.search(text)
            if not match:
                return "❌ 无匹配"

            result = f"  分组信息:\n"
            result += f"   完整匹配: '{match.group()}' (span: {match.span()})\n"
            for i, group in enumerate(match.groups(), 1):
                result += f"   分组 {i}: '{group}' (span: {match.span(i) if group else 'N/A'})\n"
            if match.groupdict():
                result += f"   命名分组:\n"
                for name, value in match.groupdict().items():
                    result += f"     {name}: '{value}'\n"
            return result.rstrip()
        except re.error as e:
            return f"❌ 正则语法错误: {e}"

    def _op_explain(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供正则表达式"
        pattern_str = args[0]

        explanations = []
        i = 0
        while i < len(pattern_str):
            ch = pattern_str[i]

            if ch == '\\':
                if i + 1 < len(pattern_str):
                    next_ch = pattern_str[i + 1]
                    escape_map = {
                        'd': '数字 [0-9]', 'D': '非数字', 'w': '字母/数字/下划线',
                        'W': '非字母数字下划线', 's': '空白字符', 'S': '非空白字符',
                        'b': '单词边界', 'B': '非单词边界', 'n': '换行', 't': '制表符',
                    }
                    if next_ch in escape_map:
                        explanations.append(('\\' + next_ch, escape_map[next_ch]))
                    else:
                        explanations.append(('\\' + next_ch, f'转义字符 {next_ch}'))
                    i += 2
                    continue

            if ch == '.':
                explanations.append(('.', '任意字符（除换行）'))
            elif ch == '^':
                explanations.append(('^', '行/字符串开头'))
            elif ch == '$':
                explanations.append(('$', '行/字符串结尾'))
            elif ch == '*':
                explanations.append(('*', '0次或多次'))
            elif ch == '+':
                explanations.append(('+', '1次或多次'))
            elif ch == '?':
                explanations.append(('?', '0次或1次'))
            elif ch == '{':
                end = pattern_str.find('}', i)
                if end != -1:
                    quantifier = pattern_str[i:end + 1]
                    explanations.append((quantifier, f'量词: {quantifier}'))
                    i = end + 1
                    continue
            elif ch == '[':
                end = pattern_str.find(']', i)
                if end != -1:
                    char_class = pattern_str[i:end + 1]
                    explanations.append((char_class, f'字符类: {char_class}'))
                    i = end + 1
                    continue
            elif ch == '(':
                if i + 1 < len(pattern_str) and pattern_str[i + 1] == '?':
                    if i + 2 < len(pattern_str):
                        special = pattern_str[i + 2]
                        if special == ':':
                            explanations.append(('(?:', '非捕获组'))
                        elif special == '=':
                            explanations.append(('(?=', '正向前瞻'))
                        elif special == '!':
                            explanations.append(('(?!', '负向前瞻'))
                        i += 3
                        continue
                explanations.append(('(', '捕获组开始'))
            elif ch == ')':
                explanations.append((')', '组结束'))
            elif ch == '|':
                explanations.append(('|', '或 (交替)'))

            i += 1

        result = f"  正则解释: {pattern_str}\n"
        result += "─" * 45 + "\n"
        for token, meaning in explanations:
            result += f"   {token:12s} → {meaning}\n"
        return result.rstrip()

    def _op_flags(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：格式: flags <正则> <文本>"
        pattern_str, text = args[0], args[1]

        flag_combos = [
            ("", 0, "默认"),
            ("i", re.IGNORECASE, "忽略大小写"),
            ("m", re.MULTILINE, "多行模式"),
            ("s", re.DOTALL, "点匹配换行"),
            ("im", re.IGNORECASE | re.MULTILINE, "忽略大小写+多行"),
        ]

        result = f" ️  标志测试: {pattern_str}\n"
        result += "─" * 45 + "\n"
        for flag_str, flag_val, desc in flag_combos:
            try:
                matches = re.findall(pattern_str, text, flag_val)
                count = len(matches) if isinstance(matches, list) else 1
                result += f"   [{flag_str or '-':3s}] {desc:12s} → {count} 个匹配: {matches[:3]}\n"
            except re.error as e:
                result += f"   [{flag_str or '-':3s}] {desc:12s} → 错误: {e}\n"
        return result.rstrip()

    def _op_pattern(self, args: List[str]) -> str:
        if args:
            name = args[0]
            if name in self.custom_patterns:
                p = self.custom_patterns[name]
                return f"  模式 '{name}':\n   正则: {p['pattern']}\n   描述: {p.get('desc', '')}"
            return f"❌ 未找到模式: {name}"

        result = "  常用正则模式:\n"
        result += "─" * 50 + "\n"
        for name, p in self.custom_patterns.items():
            result += f"   {name:15s} {p['pattern'][:35]:35s} {p.get('desc', '')}\n"
        return result.rstrip()

    def _op_save(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：格式: save <名称> <正则> [-d 描述]"
        name, pattern_str = args[0], args[1]
        desc = ""
        for i, a in enumerate(args):
            if a == "-d" and i + 1 < len(args):
                desc = args[i + 1]

        # 验证正则
        try:
            re.compile(pattern_str)
        except re.error as e:
            return f"❌ 正则语法错误: {e}"

        self.custom_patterns[name] = {"pattern": pattern_str, "desc": desc}
        self._save_patterns()
        return f"✅ 已保存模式 '{name}': {pattern_str}"

    def _op_delete_pattern(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供模式名称"
        name = args[0]
        if name in self.custom_patterns:
            del self.custom_patterns[name]
            self._save_patterns()
            return f" ️  已删除模式: {name}"
        return f"❌ 未找到模式: {name}"

    def _op_bench(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：格式: bench <正则> <文本> [-n 次数]"
        pattern_str, text = args[0], args[1]
        count = 10000
        for i, a in enumerate(args):
            if a == "-n" and i + 1 < len(args):
                count = int(args[i + 1])

        try:
            import time
            pattern = re.compile(pattern_str)

            start = time.perf_counter()
            for _ in range(count):
                pattern.findall(text)
            elapsed = time.perf_counter() - start

            per_op = elapsed / count * 1_000_000  # 微秒
            return (f"⏱ 性能测试:\n"
                    f"   正则: {pattern_str}\n"
                    f"   次数: {count}\n"
                    f"   总耗时: {elapsed:.3f}s\n"
                    f"   每次: {per_op:.2f}μs\n"
                    f"   吞吐: {count / elapsed:.0f} ops/s")
        except re.error as e:
            return f"❌ 正则语法错误: {e}"


def test_plugin():
    plugin = Plugin()
    print("正则表达式测试器测试:")
    print(plugin.handle('test "\\d+" "abc123def456"'))
    print(plugin.handle('match "[a-z]+" "hello world foo bar"'))
    print(plugin.handle('groups "(\\w+)@(\\w+)\\.(\\w+)" "user@domain.com"'))
    print(plugin.handle('explain "\\d{4}-\\d{2}-\\d{2}"'))


if __name__ == "__main__":
    test_plugin()
