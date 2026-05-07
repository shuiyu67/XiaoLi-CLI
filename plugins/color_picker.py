"""
颜色工具插件 - 颜色格式转换、调色板、对比度检查
支持 HEX/RGB/HSL/HSV/CMYK 格式互转，WCAG 对比度检查
"""

import re
import colorsys
from typing import List, Tuple


class Liugin:
    """颜色工具 - 格式转换、调色板、对比度检查"""

    def __init__(self):
        self.usage = """颜色工具

操作:
  convert <颜色>                  - 自动检测并转换为所有格式
  hex <RGB或HSL>                  - 转换为 HEX
  rgb <HEX或HSL>                  - 转换为 RGB
  hsl <HEX或RGB>                  - 转换为 HSL
  hsv <HEX或RGB>                  - 转换为 HSV
  cmyk <HEX或RGB>                 - 转换为 CMYK
  contrast <颜色1> <颜色2>        - WCAG 对比度检查
  palette <颜色> [-n 数量]        - 生成调色板（明暗变体）
  complementary <颜色>            - 互补色
  analogous <颜色>                - 类似色
  triadic <颜色>                  - 三色组
  random [-n 数量]                - 随机颜色
  mix <颜色1> <颜色2> [-w 权重]  - 混合两种颜色
  blind <颜色> <类型>             - 色盲模拟
  named                           - 列出 CSS 命名颜色

颜色格式:
  HEX: #FF6600, #F60, FF6600
  RGB: rgb(255,102,0) 或 255,102,0
  HSL: hsl(24,100%,50%)
  HSV: hsv(24,100%,100%)
  CMYK: cmyk(0,60,100,0)

示例:
  color_picker convert "#3498db"
  color_picker rgb "hsl(207,62%,54%)"
  color_picker contrast "#FFFFFF" "#000000"
  color_picker palette "#e74c3c" -n 9
  color_picker complementary "#3498db"
"""
        self.cli = None

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "color_picker",
            "description": "颜色工具 - HEX/RGB/HSL/HSV/CMYK 转换、对比度检查、调色板生成",
            "keywords": ["颜色", "color", "HEX", "RGB", "HSL", "调色板", "对比度", "色盲", "转换"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "color_picker",
            "description": "颜色工具，支持格式转换、对比度检查、调色板生成",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["convert", "hex", "rgb", "hsl", "hsv", "cmyk",
                                 "contrast", "palette", "complementary", "analogous",
                                 "triadic", "random", "mix", "blind"],
                        "description": "操作类型"
                    },
                    "color": {"type": "string", "description": "颜色值"},
                    "color2": {"type": "string", "description": "第二个颜色值"},
                    "count": {"type": "integer", "description": "数量"},
                    "weight": {"type": "number", "description": "混合权重 (0-1)"},
                    "blind_type": {"type": "string", "description": "色盲类型"}
                },
                "required": ["operation"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        color = arguments.get("color", "")
        return f"{op} {color}".strip()

    def handle(self, args: str) -> str:
        try:
            parts = self._parse_args(args)
            if not parts:
                return self._op_random(["1"])

            operation = parts[0].lower()
            handlers = {
                "convert": self._op_convert,
                "hex": self._op_hex,
                "rgb": self._op_rgb,
                "hsl": self._op_hsl,
                "hsv": self._op_hsv,
                "cmyk": self._op_cmyk,
                "contrast": self._op_contrast,
                "palette": self._op_palette,
                "complementary": self._op_complementary,
                "analogous": self._op_analogous,
                "triadic": self._op_triadic,
                "random": self._op_random,
                "mix": self._op_mix,
                "blind": self._op_blind,
            }

            handler = handlers.get(operation)
            if not handler:
                return f"错误：不支持的操作 '{operation}'"
            return handler(parts[1:])

        except Exception as e:
            return f"颜色工具错误: {str(e)}"

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

    def _parse_color(self, color_str: str) -> Tuple[int, int, int]:
        """解析颜色字符串为 RGB (0-255)"""
        s = color_str.strip().lower()

        # HEX
        hex_match = re.match(r'^#?([0-9a-f]{3,8})$', s)
        if hex_match:
            h = hex_match.group(1)
            if len(h) == 3:
                h = h[0]*2 + h[1]*2 + h[2]*2
            elif len(h) == 8:
                h = h[:6]  # ignore alpha
            if len(h) == 6:
                return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

        # RGB
        rgb_match = re.match(r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', s)
        if rgb_match:
            return (int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3)))

        # plain r,g,b
        plain_match = re.match(r'^(\d+)\s*,\s*(\d+)\s*,\s*(\d+)$', s)
        if plain_match:
            return (int(plain_match.group(1)), int(plain_match.group(2)), int(plain_match.group(3)))

        # HSL
        hsl_match = re.match(r'hsl\s*\(\s*(\d+)\s*,\s*(\d+)%,\s*(\d+)%\s*\)', s)
        if hsl_match:
            h = int(hsl_match.group(1)) / 360
            sl = int(hsl_match.group(2)) / 100
            l = int(hsl_match.group(3)) / 100
            r, g, b = colorsys.hls_to_rgb(h, l, sl)
            return (int(r * 255), int(g * 255), int(b * 255))

        # HSV/HSB
        hsv_match = re.match(r'hsv\s*\(\s*(\d+)\s*,\s*(\d+)%,\s*(\d+)%\s*\)', s)
        if hsv_match:
            h = int(hsv_match.group(1)) / 360
            sv = int(hsv_match.group(2)) / 100
            v = int(hsv_match.group(3)) / 100
            r, g, b = colorsys.hsv_to_rgb(h, sv, v)
            return (int(r * 255), int(g * 255), int(b * 255))

        # CMYK
        cmyk_match = re.match(r'cmyk\s*\(\s*(\d+)%?\s*,\s*(\d+)%?\s*,\s*(\d+)%?\s*,\s*(\d+)%?\s*\)', s)
        if cmyk_match:
            c = int(cmyk_match.group(1)) / 100
            m = int(cmyk_match.group(2)) / 100
            y = int(cmyk_match.group(3)) / 100
            k = int(cmyk_match.group(4)) / 100
            r = int(255 * (1 - c) * (1 - k))
            g = int(255 * (1 - m) * (1 - k))
            b = int(255 * (1 - y) * (1 - k))
            return (r, g, b)

        raise ValueError(f"无法解析颜色: {color_str}")

    def _rgb_to_hex(self, r: int, g: int, b: int) -> str:
        return f"#{r:02X}{g:02X}{b:02X}"

    def _rgb_to_hsl(self, r: int, g: int, b: int) -> Tuple[int, int, int]:
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        return (int(h * 360), int(s * 100), int(l * 100))

    def _rgb_to_hsv(self, r: int, g: int, b: int) -> Tuple[int, int, int]:
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        return (int(h * 360), int(s * 100), int(v * 100))

    def _rgb_to_cmyk(self, r: int, g: int, b: int) -> Tuple[int, int, int, int]:
        if r == g == b == 0:
            return (0, 0, 0, 100)
        c = 1 - r / 255
        m = 1 - g / 255
        y = 1 - b / 255
        k = min(c, m, y)
        c = int((c - k) / (1 - k) * 100)
        m = int((m - k) / (1 - k) * 100)
        y = int((y - k) / (1 - k) * 100)
        k = int(k * 100)
        return (c, m, y, k)

    def _luminance(self, r: int, g: int, b: int) -> float:
        """计算相对亮度 (WCAG 2.0)"""
        def linearize(c):
            c = c / 255
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)

    def _format_color_block(self, r: int, g: int, b: int) -> str:
        """生成颜色预览块"""
        return f"  ■  RGB({r}, {g}, {b})"

    def _op_convert(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供颜色值"
        r, g, b = self._parse_color(args[0])
        h, s, l = self._rgb_to_hsl(r, g, b)
        hh, sv, vv = self._rgb_to_hsv(r, g, b)
        c, m, y, k = self._rgb_to_cmyk(r, g, b)

        result = f"  颜色转换: {args[0]}\n"
        result += self._format_color_block(r, g, b) + "\n"
        result += "─" * 35 + "\n"
        result += f"   HEX:  {self._rgb_to_hex(r, g, b)}\n"
        result += f"   RGB:  rgb({r}, {g}, {b})\n"
        result += f"   HSL:  hsl({h}, {s}%, {l}%)\n"
        result += f"   HSV:  hsv({hh}, {sv}%, {vv}%)\n"
        result += f"   CMYK: cmyk({c}%, {m}%, {y}%, {k}%)\n"
        return result.rstrip()

    def _op_hex(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供颜色值"
        r, g, b = self._parse_color(args[0])
        return f"  HEX: {self._rgb_to_hex(r, g, b)}"

    def _op_rgb(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供颜色值"
        r, g, b = self._parse_color(args[0])
        return f"  RGB: rgb({r}, {g}, {b})"

    def _op_hsl(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供颜色值"
        r, g, b = self._parse_color(args[0])
        h, s, l = self._rgb_to_hsl(r, g, b)
        return f"  HSL: hsl({h}, {s}%, {l}%)"

    def _op_hsv(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供颜色值"
        r, g, b = self._parse_color(args[0])
        h, s, v = self._rgb_to_hsv(r, g, b)
        return f"  HSV: hsv({h}, {s}%, {v}%)"

    def _op_cmyk(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供颜色值"
        r, g, b = self._parse_color(args[0])
        c, m, y, k = self._rgb_to_cmyk(r, g, b)
        return f"  CMYK: cmyk({c}%, {m}%, {y}%, {k}%)"

    def _op_contrast(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：请提供两种颜色"
        r1, g1, b1 = self._parse_color(args[0])
        r2, g2, b2 = self._parse_color(args[1])

        l1 = self._luminance(r1, g1, b1)
        l2 = self._luminance(r2, g2, b2)
        lighter = max(l1, l2)
        darker = min(l1, l2)
        ratio = (lighter + 0.05) / (darker + 0.05)

        aa_large = ratio >= 3
        aa_normal = ratio >= 4.5
        aaa_large = ratio >= 4.5
        aaa_normal = ratio >= 7

        result = f"  WCAG 对比度检查\n"
        result += "─" * 40 + "\n"
        result += f"   颜色1: {self._rgb_to_hex(r1, g1, b1)} {self._format_color_block(r1, g1, b1)}\n"
        result += f"   颜色2: {self._rgb_to_hex(r2, g2, b2)} {self._format_color_block(r2, g2, b1)}\n"
        result += f"   对比度: {ratio:.2f}:1\n"
        result += "─" * 40 + "\n"
        result += f"   {'  ' if aa_normal else '❌'} AA 正文 (≥4.5:1)\n"
        result += f"   {'  ' if aa_large else '❌'} AA 大字 (≥3:1)\n"
        result += f"   {'  ' if aaa_normal else '❌'} AAA 正文 (≥7:1)\n"
        result += f"   {'  ' if aaa_large else '❌'} AAA 大字 (≥4.5:1)\n"
        return result.rstrip()

    def _op_palette(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供基础颜色"
        r, g, b = self._parse_color(args[0])
        opts = self._parse_opts(args[1:])
        count = int(opts.get("n", 9))
        count = max(3, min(count, 15))

        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)

        result = f"  调色板 (基于 {args[0]}):\n"
        result += "─" * 50 + "\n"

        steps = count
        for i in range(steps):
            # 从暗到亮
            new_l = 0.1 + (0.8 * i / (steps - 1))
            nr, ng, nb = colorsys.hls_to_rgb(h, new_l, s)
            nr, ng, nb = int(nr * 255), int(ng * 255), int(nb * 255)
            hex_val = self._rgb_to_hex(nr, ng, nb)
            bar = "█" * int(new_l * 20)
            result += f"   {hex_val}  {bar}  L:{int(new_l*100)}%\n"

        return result.rstrip()

    def _op_complementary(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供颜色"
        r, g, b = self._parse_color(args[0])
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        # 互补色: 色相旋转180°
        comp_h = (h + 0.5) % 1.0
        cr, cg, cb = colorsys.hls_to_rgb(comp_h, l, s)
        cr, cg, cb = int(cr * 255), int(cg * 255), int(cb * 255)

        result = f"  互补色:\n"
        result += f"   原色: {self._rgb_to_hex(r, g, b)}\n"
        result += f"   互补: {self._rgb_to_hex(cr, cg, cb)}\n"
        return result

    def _op_analogous(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供颜色"
        r, g, b = self._parse_color(args[0])
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)

        result = f"  类似色:\n"
        for offset in [-30, -15, 0, 15, 30]:
            ah = (h + offset / 360) % 1.0
            ar, ag, ab = colorsys.hls_to_rgb(ah, l, s)
            ar, ag, ab = int(ar * 255), int(ag * 255), int(ab * 255)
            marker = " ◀" if offset == 0 else ""
            result += f"   {self._rgb_to_hex(ar, ag, ab)} ({offset:+d}°){marker}\n"
        return result.rstrip()

    def _op_triadic(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供颜色"
        r, g, b = self._parse_color(args[0])
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)

        result = f"  三色组:\n"
        for i, offset in enumerate([0, 120, 240]):
            th = (h + offset / 360) % 1.0
            tr, tg, tb = colorsys.hls_to_rgb(th, l, s)
            tr, tg, tb = int(tr * 255), int(tg * 255), int(tb * 255)
            result += f"   {i+1}. {self._rgb_to_hex(tr, tg, tb)} ({offset}°)\n"
        return result.rstrip()

    def _op_random(self, args: List[str]) -> str:
        opts = self._parse_opts(args)
        count = int(opts.get("n", 5))
        count = min(count, 20)

        result = f"  随机颜色 ({count} 个):\n"
        for _ in range(count):
            r, g, b = __import__('random').randint(0, 255), __import__('random').randint(0, 255), __import__('random').randint(0, 255)
            result += f"   {self._rgb_to_hex(r, g, b)}  rgb({r}, {g}, {b})\n"
        return result.rstrip()

    def _op_mix(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：请提供两种颜色"
        r1, g1, b1 = self._parse_color(args[0])
        r2, g2, b2 = self._parse_color(args[1])
        opts = self._parse_opts(args[2:])
        w = float(opts.get("w", 0.5))
        w = max(0, min(1, w))

        mr = int(r1 * (1 - w) + r2 * w)
        mg = int(g1 * (1 - w) + g2 * w)
        mb = int(b1 * (1 - w) + b2 * w)

        result = f"  颜色混合 (权重 {w}):\n"
        result += f"   颜色1: {self._rgb_to_hex(r1, g1, b1)}\n"
        result += f"   颜色2: {self._rgb_to_hex(r2, g2, b2)}\n"
        result += f"   混合:  {self._rgb_to_hex(mr, mg, mb)}\n"
        return result

    def _op_blind(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：请提供颜色和色盲类型\n类型: protanopia, deuteranopia, tritanopia"
        r, g, b = self._parse_color(args[0])
        blind_type = args[1].lower()

        # 简化的色盲模拟矩阵
        matrices = {
            "protanopia":    [[0.567, 0.433, 0.0], [0.558, 0.442, 0.0], [0.0, 0.242, 0.758]],
            "deuteranopia":  [[0.625, 0.375, 0.0], [0.7, 0.3, 0.0], [0.0, 0.3, 0.7]],
            "tritanopia":    [[0.95, 0.05, 0.0], [0.0, 0.433, 0.567], [0.0, 0.475, 0.525]],
        }

        matrix = matrices.get(blind_type)
        if not matrix:
            return f"错误：未知类型 '{blind_type}'\n支持: protanopia, deuteranopia, tritanopia"

        nr = int(matrix[0][0] * r + matrix[0][1] * g + matrix[0][2] * b)
        ng = int(matrix[1][0] * r + matrix[1][1] * g + matrix[1][2] * b)
        nb = int(matrix[2][0] * r + matrix[2][1] * g + matrix[2][2] * b)
        nr, ng, nb = max(0, min(255, nr)), max(0, min(255, ng)), max(0, min(255, nb))

        result = f"  色盲模拟 ({blind_type}):\n"
        result += f"   原色: {self._rgb_to_hex(r, g, b)}\n"
        result += f"   模拟: {self._rgb_to_hex(nr, ng, nb)}\n"
        return result


def test_plugin():
    plugin = Liugin()
    print("颜色工具测试:")
    print(plugin.handle('convert "#3498db"'))
    print(plugin.handle('contrast "#FFFFFF" "#000000"'))
    print(plugin.handle('palette "#e74c3c" -n 7'))
    print(plugin.handle('complementary "#3498db"'))


if __name__ == "__main__":
    test_plugin()
