"""
UUID / ID 生成器插件 - 生成各种格式的唯一标识符
支持 UUID v1/v4/v5、NanoID、短ID、雪花ID、自定义格式
"""

import uuid
import hashlib
import time
import random
import string
import json
import os
import struct
from datetime import datetime
from typing import List


class Liugin:
    """UUID / ID 生成器 - 多格式唯一标识符生成"""

    def __init__(self):
        self.usage = """UUID / ID 生成器

操作:
  uuid [-v 版本] [-n 数量]       - 生成 UUID（默认 v4）
                                   v1=时间戳  v4=随机  v5=命名
  nanoid [-s 长度] [-n 数量]     - 生成 NanoID（默认21位）
  short [-s 长度] [-n 数量]      - 生成短ID（默认8位）
  snowflake [-n 数量]            - 生成雪花ID（时间排序）
  custom <模板> [-n 数量]        - 自定义格式生成
                                   模板: {U}=大写字母 {L}=小写 {D}=数字 {X}=十六进制
  ulid [-n 数量]                 - 生成 ULID（时间排序+随机）
  timestamp                      - 当前时间戳（秒/毫秒/微秒）
  from_name <命名空间> <名称>   - 基于名称生成确定性 UUID (v5)
  batch <类型> [-n 数量] [-o 文件] - 批量生成并保存到文件

示例:
  id_generator uuid
  id_generator uuid -v 1 -n 5
  id_generator nanoid -s 16
  id_generator short -s 6 -n 10
  id_generator custom "USER-{D}{D}{D}{D}{U}{U}" -n 5
  id_generator snowflake -n 3
  id_generator batch uuid -n 100 -o ids.txt
"""
        self.cli = None
        self._machine_id = random.randint(0, 1023)
        self._sequence = 0
        self._last_ts = 0

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "id_generator",
            "description": "UUID/ID 生成器 - 支持 UUID、NanoID、短ID、雪花ID、ULID、自定义格式",
            "keywords": ["uuid", "id", "生成", "唯一", "标识", "nanoid", "snowflake", "ulid", "短id"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "id_generator",
            "description": "UUID/ID 生成器，支持多种格式",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["uuid", "nanoid", "short", "snowflake", "custom",
                                 "ulid", "timestamp", "from_name", "batch"],
                        "description": "操作类型"
                    },
                    "version": {"type": "integer", "description": "UUID 版本 (1/4/5)"},
                    "length": {"type": "integer", "description": "ID 长度"},
                    "count": {"type": "integer", "description": "生成数量"},
                    "template": {"type": "string", "description": "自定义模板"},
                    "namespace": {"type": "string", "description": "命名空间"},
                    "name": {"type": "string", "description": "名称"},
                    "output": {"type": "string", "description": "输出文件"}
                },
                "required": ["operation"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        count = arguments.get("count", "")
        parts = [op]
        if count:
            parts.extend(["-n", str(count)])
        return " ".join(parts)

    def handle(self, args: str) -> str:
        try:
            parts = self._parse_args(args)
            if not parts:
                return self._op_uuid([])

            operation = parts[0].lower()
            handlers = {
                "uuid": self._op_uuid,
                "nanoid": self._op_nanoid,
                "short": self._op_short,
                "snowflake": self._op_snowflake,
                "custom": self._op_custom,
                "ulid": self._op_ulid,
                "timestamp": self._op_timestamp,
                "from_name": self._op_from_name,
                "batch": self._op_batch,
            }

            handler = handlers.get(operation)
            if not handler:
                return f"错误：不支持的操作 '{operation}'"
            return handler(parts[1:])

        except Exception as e:
            return f"ID 生成错误: {str(e)}"

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

    def _parse_opts(self, args: List[str]) -> dict:
        opts = {}
        i = 0
        while i < len(args):
            if args[i].startswith("-") and i + 1 < len(args):
                key = args[i].lstrip("-")
                opts[key] = args[i + 1]
                i += 1
            i += 1
        return opts

    def _op_uuid(self, args: List[str]) -> str:
        opts = self._parse_opts(args)
        version = int(opts.get("v", 4))
        count = int(opts.get("n", 1))
        count = min(count, 1000)

        ids = []
        for _ in range(count):
            if version == 1:
                ids.append(str(uuid.uuid1()))
            elif version == 4:
                ids.append(str(uuid.uuid4()))
            elif version == 5:
                ids.append(str(uuid.uuid5(uuid.NAMESPACE_DNS, "example.com")))
            else:
                return f"错误：不支持的 UUID 版本: {version}"

        header = f"  UUID v{version} ({count} 个):\n"
        if count <= 20:
            return header + "\n".join(f"   {u}" for u in ids)
        else:
            return header + "\n".join(f"   {u}" for u in ids[:10]) + f"\n   ... (共 {count} 个)"

    def _op_nanoid(self, args: List[str]) -> str:
        opts = self._parse_opts(args)
        size = int(opts.get("s", 21))
        count = int(opts.get("n", 1))
        count = min(count, 1000)

        alphabet = string.ascii_letters + string.digits + "_-"
        ids = []
        for _ in range(count):
            ids.append(''.join(random.choices(alphabet, k=size)))

        header = f"  NanoID (长度 {size}, {count} 个):\n"
        if count <= 20:
            return header + "\n".join(f"   {i}" for i in ids)
        else:
            return header + "\n".join(f"   {i}" for i in ids[:10]) + f"\n   ... (共 {count} 个)"

    def _op_short(self, args: List[str]) -> str:
        opts = self._parse_opts(args)
        size = int(opts.get("s", 8))
        count = int(opts.get("n", 1))
        count = min(count, 1000)

        chars = string.ascii_letters + string.digits
        ids = []
        for _ in range(count):
            ids.append(''.join(random.choices(chars, k=size)))

        header = f"  短ID (长度 {size}, {count} 个):\n"
        if count <= 20:
            return header + "\n".join(f"   {i}" for i in ids)
        else:
            return header + "\n".join(f"   {i}" for i in ids[:10]) + f"\n   ... (共 {count} 个)"

    def _op_snowflake(self, args: List[str]) -> str:
        opts = self._parse_opts(args)
        count = int(opts.get("n", 1))
        count = min(count, 1000)

        # Twitter Snowflake: 41位时间戳 + 10位机器ID + 12位序列号
        epoch = 1288834974657  # Twitter epoch (2010-11-04)

        ids = []
        for _ in range(count):
            ts = int(time.time() * 1000) - epoch
            if ts == self._last_ts:
                self._sequence = (self._sequence + 1) & 0xFFF
                if self._sequence == 0:
                    while ts <= self._last_ts:
                        ts = int(time.time() * 1000) - epoch
            else:
                self._sequence = 0
            self._last_ts = ts

            snowflake_id = (ts << 22) | (self._machine_id << 12) | self._sequence
            ids.append(str(snowflake_id))

        header = f"❄️  雪花ID ({count} 个):\n"
        if count <= 20:
            return header + "\n".join(f"   {i}" for i in ids)
        else:
            return header + "\n".join(f"   {i}" for i in ids[:10]) + f"\n   ... (共 {count} 个)"

    def _op_custom(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供模板\n示例: custom \"ORDER-{D}{D}{D}{D}-{U}{U}{U}\""
        template = args[0]
        opts = self._parse_opts(args[1:])
        count = int(opts.get("n", 1))
        count = min(count, 1000)

        ids = []
        for _ in range(count):
            result = []
            for ch in template:
                if ch == '{':
                    continue  # handled below
                result.append(ch)
            # Actually use proper template parsing
            ids.append(self._expand_template(template))

        header = f" ️  自定义ID (模板: {template}, {count} 个):\n"
        if count <= 20:
            return header + "\n".join(f"   {i}" for i in ids)
        else:
            return header + "\n".join(f"   {i}" for i in ids[:10]) + f"\n   ... (共 {count} 个)"

    def _expand_template(self, template: str) -> str:
        result = []
        i = 0
        while i < len(template):
            if template[i] == '{' and i + 2 < len(template) and template[i + 2] == '}':
                token = template[i + 1]
                if token == 'U':
                    result.append(random.choice(string.ascii_uppercase))
                elif token == 'L':
                    result.append(random.choice(string.ascii_lowercase))
                elif token == 'D':
                    result.append(random.choice(string.digits))
                elif token == 'X':
                    result.append(random.choice('0123456789ABCDEF'))
                elif token == 'x':
                    result.append(random.choice('0123456789abcdef'))
                elif token == 'A':
                    result.append(random.choice(string.ascii_letters))
                else:
                    result.append(template[i:i + 3])
                i += 3
            else:
                result.append(template[i])
                i += 1
        return ''.join(result)

    def _op_ulid(self, args: List[str]) -> str:
        opts = self._parse_opts(args)
        count = int(opts.get("n", 1))
        count = min(count, 1000)

        # ULID: 48位时间戳 + 80位随机数, Crockford Base32
        alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

        ids = []
        for _ in range(count):
            ts = int(time.time() * 1000)
            # 时间部分 (10 chars)
            t_chars = []
            t = ts
            for _ in range(10):
                t_chars.append(alphabet[t & 0x1F])
                t >>= 5
            t_chars.reverse()
            # 随机部分 (16 chars)
            r_chars = [random.choice(alphabet) for _ in range(16)]
            ids.append(''.join(t_chars) + ''.join(r_chars))

        header = f"  ULID ({count} 个):\n"
        if count <= 20:
            return header + "\n".join(f"   {i}" for i in ids)
        else:
            return header + "\n".join(f"   {i}" for i in ids[:10]) + f"\n   ... (共 {count} 个)"

    def _op_timestamp(self, args: List[str]) -> str:
        now = time.time()
        return (f"⏱  当前时间戳:\n"
                f"   秒:     {int(now)}\n"
                f"   毫秒:   {int(now * 1000)}\n"
                f"   微秒:   {int(now * 1000000)}\n"
                f"   ISO:    {datetime.now().isoformat()}")

    def _op_from_name(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：格式: from_name <命名空间> <名称>\n命名空间: dns, url, oid, x500"
        ns_map = {"dns": uuid.NAMESPACE_DNS, "url": uuid.NAMESPACE_URL,
                  "oid": uuid.NAMESPACE_OID, "x500": uuid.NAMESPACE_X500}
        ns = ns_map.get(args[0].lower(), uuid.NAMESPACE_DNS)
        name = args[1]
        result = uuid.uuid5(ns, name)
        return f"  确定性 UUID v5:\n   命名空间: {args[0]}\n   名称: {name}\n   UUID: {result}"

    def _op_batch(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供类型 (uuid/nanoid/short/snowflake/ulid)"
        id_type = args[0]
        opts = self._parse_opts(args[1:])
        count = int(opts.get("n", 10))
        output = opts.get("o", "")

        # 生成对应类型的ID
        gen_args = [f"-n", str(count)]
        handlers = {
            "uuid": self._op_uuid,
            "nanoid": self._op_nanoid,
            "short": self._op_short,
            "snowflake": self._op_snowflake,
            "ulid": self._op_ulid,
        }
        handler = handlers.get(id_type)
        if not handler:
            return f"错误：不支持的类型 '{id_type}'"

        result = handler(gen_args)

        if output:
            # 提取纯ID保存到文件
            ids = [line.strip().lstrip(' ') for line in result.split('\n')
                   if line.strip() and not any(c in line for c in [' ', '️', '', '❄️', ''])]
            try:
                with open(output, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(ids))
                return f"{result}\n\n  已保存到: {output}"
            except Exception as e:
                return f"{result}\n\n  保存失败: {e}"

        return result


def test_plugin():
    plugin = Liugin()
    print("ID 生成器测试:")
    print(plugin.handle('uuid'))
    print(plugin.handle('uuid -v 1 -n 3'))
    print(plugin.handle('nanoid -s 16'))
    print(plugin.handle('short -s 6 -n 5'))
    print(plugin.handle('snowflake -n 3'))
    print(plugin.handle('ulid'))
    print(plugin.handle('timestamp'))
    print(plugin.handle('custom "ORD-{D}{D}{D}{D}-{U}{U}{U}" -n 5'))


if __name__ == "__main__":
    test_plugin()
