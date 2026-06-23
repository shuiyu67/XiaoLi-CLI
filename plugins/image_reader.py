"""
图片读取插件 — 从图片中提取文字，发送给 AI
=============================================
功能：读取图片 → OCR 提取文字 → 返回给 AI
支持：Tesseract OCR / Windows PowerShell OCR / 纯 Python 元数据
"""
import os
import sys
import json
import base64
import hashlib
import subprocess
import platform
import tempfile
from pathlib import Path

_IS_WIN = platform.system() == "Windows"


class Liugin:
    """图片读取 — 从图片中提取文字"""

    def __init__(self):
        self.cli = None

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "image_reader",
            "description": "图片读取工具 — 从图片中提取文字（OCR），获取图片信息，"
                           "将图片内容转为文本发送给 AI",
            "keywords": [
                "图片", "image", "OCR", "文字识别", "读图", "截图",
                "提取文字", "图片转文字", "识别", "tesseract",
            ],
            "usage": (
                "image_reader <操作> <路径>\n\n"
                "操作:\n"
                "  ocr <图片路径>         - 从图片中提取文字\n"
                "  info <图片路径>        - 获取图片信息（尺寸/格式/大小）\n"
                "  read <图片路径>        - 综合读取（信息 + OCR）\n"
                "  ascii <图片路径> [宽]  - 转 ASCII 字符画（终端显示）\n"
                "  base64 <图片路径>      - 转 Base64 编码\n"
                "  hash <图片路径>        - 计算图片哈希值\n\n"
                "示例:\n"
                "  image_reader ocr screenshot.png     - 识别截图中的文字\n"
                "  image_reader read photo.jpg          - 综合读取图片\n"
                "  image_reader ascii logo.png 40       - 转40列宽ASCII画\n"
            ),
        }

    def get_mcp_definition(self):
        return {
            "name": "image_reader",
            "description": "图片读取工具 — 从图片中提取文字（OCR）",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["ocr", "info", "read", "ascii", "base64", "hash"],
                        "description": "操作类型",
                    },
                    "path": {"type": "string", "description": "图片文件路径"},
                    "width": {"type": "integer", "description": "ASCII 画宽度"},
                },
                "required": ["action", "path"],
            },
        }

    def convert_mcp_args(self, arguments):
        action = arguments.get("action", "")
        path = arguments.get("path", "")
        width = arguments.get("width", "")
        parts = [action, path]
        if width:
            parts.append(str(width))
        return " ".join(parts)

    def handle(self, args: str) -> str:
        parts = args.strip().split(maxsplit=2)
        if not parts:
            return "请提供操作和图片路径"
        action = parts[0].lower()
        path = parts[1] if len(parts) > 1 else ""
        extra = parts[2] if len(parts) > 2 else ""

        if not path:
            return "请提供图片路径"

        # 展开 ~ 和环境变量
        path = os.path.expanduser(os.path.expandvars(path))
        if not os.path.isfile(path):
            return f"文件不存在: {path}"

        handlers = {
            "ocr": self._ocr,
            "info": self._info,
            "read": self._read,
            "ascii": self._ascii,
            "base64": self._b64,
            "hash": self._hash,
        }
        h = handlers.get(action)
        if not h:
            return f"不支持的操作 '{action}'"
        try:
            return h(path, extra)
        except Exception as e:
            return f"错误: {e}"

    # ── 图片信息 ──

    def _info(self, path: str, _: str) -> str:
        size = os.path.getsize(path)
        ext = os.path.splitext(path)[1].lower()
        lines = [
            f"图片: {os.path.basename(path)}",
            f"格式: {ext}",
            f"大小: {self._human_size(size)}",
        ]
        # 尝试用 PIL 获取尺寸
        try:
            from PIL import Image
            with Image.open(path) as img:
                lines.append(f"尺寸: {img.width} x {img.height}")
                lines.append(f"模式: {img.mode}")
                if hasattr(img, 'info'):
                    dpi = img.info.get('dpi')
                    if dpi:
                        lines.append(f"DPI: {dpi}")
        except ImportError:
            pass
        except Exception as e:
            lines.append(f"读取详情失败: {e}")
        return "\n".join(lines)

    # ── OCR 文字识别 ──

    def _ocr(self, path: str, _: str) -> str:
        # 方案1: Tesseract
        result = self._ocr_tesseract(path)
        if result:
            return result

        # 方案2: Windows PowerShell OCR
        if _IS_WIN:
            result = self._ocr_windows(path)
            if result:
                return result

        # 方案3: 用 PIL 读取图片元数据，至少告诉用户图片是什么
        return (
            "未找到 OCR 引擎。请安装以下任一工具:\n"
            "  - Tesseract: https://github.com/tesseract-ocr/tesseract\n"
            "  - Ubuntu: sudo apt install tesseract-ocr tesseract-ocr-chi-sim\n"
            "  - macOS: brew install tesseract\n"
            "  - Windows: 下载 UB-Mannheim installer\n\n"
            f"图片信息:\n{self._info(path, '')}"
        )

    def _ocr_tesseract(self, path: str) -> str:
        """用 Tesseract OCR 提取文字"""
        # 检查 tesseract 是否可用
        try:
            subprocess.run(["tesseract", "--version"],
                           capture_output=True, timeout=5)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ""

        # 执行 OCR
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # 检测语言：中文+英文
            cmd = ["tesseract", path, tmp_path[:-4], "-l", "chi_sim+eng"]
            subprocess.run(cmd, capture_output=True, timeout=30)

            if os.path.exists(tmp_path):
                with open(tmp_path, "r", encoding="utf-8") as f:
                    text = f.read().strip()
                if text:
                    return f"OCR 识别结果:\n{text}"
                return "OCR 未识别到文字"
        except subprocess.TimeoutExpired:
            return "OCR 超时"
        except Exception as e:
            return f"OCR 失败: {e}"
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return ""

    def _ocr_windows(self, path: str) -> str:
        """用 Windows 内置 OCR (PowerShell + Windows.Media.Ocr)"""
        try:
            ps_script = f'''
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$bitmap = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
$ocrEngine = [Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType=WindowsRuntime]
$ocr = $ocrEngine.TryCreateFromUserProfileLanguages()
$file = Get-Item "{path}"
$stream = [System.IO.File]::OpenRead($file.FullName)
$decoder = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream).GetAwaiter().GetResult()
$bitmap = $decoder.GetSoftwareBitmapAsync().GetAwaiter().GetResult()
$result = $ocr.RecognizeAsync($bitmap).GetAwaiter().GetResult()
$result.Text
'''
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return f"OCR 识别结果:\n{result.stdout.strip()}"
        except Exception:
            pass
        return ""

    # ── 综合读取 ──

    def _read(self, path: str, _: str) -> str:
        """信息 + OCR"""
        info = self._info(path, "")
        ocr = self._ocr(path, "")
        return f"{info}\n\n{ocr}"

    # ── ASCII 字符画 ──

    def _ascii(self, path: str, extra: str) -> str:
        """将图片转为 ASCII 字符画"""
        width = int(extra) if extra.strip().isdigit() else 60

        try:
            from PIL import Image
        except ImportError:
            return "需要 Pillow 库: pip install Pillow"

        chars = " .:-=+*#%@"

        with Image.open(path) as img:
            # 转灰度
            img = img.convert("L")
            # 缩放
            ratio = img.height / img.width
            new_height = int(width * ratio * 0.5)  # 字符高宽比约 2:1
            img = img.resize((width, new_height))

            lines = []
            for y in range(new_height):
                row = ""
                for x in range(width):
                    pixel = img.getpixel((x, y))
                    idx = pixel * (len(chars) - 1) // 255
                    row += chars[idx]
                lines.append(row)

        return "\n".join(lines)

    # ── Base64 编码 ──

    def _b64(self, path: str, _: str) -> str:
        with open(path, "rb") as f:
            data = f.read()
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "gif": "image/gif", "webp": "image/webp", "bmp": "image/bmp"
                }.get(ext, "image/png")
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:{mime};base64,{b64[:100]}... ({len(b64)} 字符)"

    # ── 哈希 ──

    def _hash(self, path: str, _: str) -> str:
        with open(path, "rb") as f:
            data = f.read()
        md5 = hashlib.md5(data).hexdigest()
        sha = hashlib.sha256(data).hexdigest()
        return f"MD5:    {md5}\nSHA256: {sha}"

    # ── 工具 ──

    @staticmethod
    def _human_size(size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
