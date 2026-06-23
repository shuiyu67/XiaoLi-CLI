# METADATA
# {
#     "name": "hex_editor",
#     "display_name": {
#         "zh": "十六进制编辑器",
#         "en": "Hex Editor"
#     },
#     "description": {
#         "zh": "一个面向二进制文件的轻量十六进制查看与修改工具包，支持查看指定偏移的 hex 窗口、按偏移写入字节序列，以及搜索指定 hex 模式。",
#         "en": "A lightweight binary hex inspection and patching toolkit. It can read hex windows at offsets, write byte sequences at offsets, and search for hex patterns."
#     },
#     "enabledByDefault": false,
#     "category": "File",
#     "tools": [
#         {
#             "name": "read_hex_window",
#             "description": {
#                 "zh": "读取二进制文件在指定偏移附近的十六进制窗口，并附带 ASCII 预览，便于快速定位和人工核对。",
#                 "en": "Read a hex window from a binary file at a specific offset, including an ASCII preview for quick inspection."
#             },
#             "parameters": [
#                 { "name": "file_path", "description": { "zh": "目标文件路径。", "en": "Target file path." }, "type": "string", "required": true },
#                 { "name": "offset", "description": { "zh": "起始偏移，可写十进制或 0x 开头的十六进制。", "en": "Start offset in decimal or 0x-prefixed hexadecimal." }, "type": "string", "required": true },
#                 { "name": "length", "description": { "zh": "读取字节数，默认 128，最大 4096。", "en": "Number of bytes to read. Default 128, max 4096." }, "type": "number", "required": false },
#                 { "name": "environment", "description": { "zh": "文件环境：android 或 linux，默认 android。", "en": "File environment: android or linux. Defaults to android." }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "write_hex_bytes",
#             "description": {
#                 "zh": "把给定的 hex 字节序列直接写入文件指定偏移。该工具会原地修改文件，不会自动生成回退文件。",
#                 "en": "Write a hex byte sequence directly into a file at the specified offset. This patches the file in place and does not create rollback files."
#             },
#             "parameters": [
#                 { "name": "file_path", "description": { "zh": "目标文件路径。", "en": "Target file path." }, "type": "string", "required": true },
#                 { "name": "offset", "description": { "zh": "写入起始偏移，可写十进制或 0x 开头的十六进制。", "en": "Write offset in decimal or 0x-prefixed hexadecimal." }, "type": "string", "required": true },
#                 { "name": "hex_bytes", "description": { "zh": "要写入的 hex 字节序列，例如 'DE AD BE EF' 或 'deadbeef'。", "en": "Hex bytes to write, for example 'DE AD BE EF' or 'deadbeef'." }, "type": "string", "required": true },
#                 { "name": "environment", "description": { "zh": "文件环境：android 或 linux，默认 android。", "en": "File environment: android or linux. Defaults to android." }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "find_hex_pattern",
#             "description": {
#                 "zh": "在二进制文件中搜索指定的 hex 模式，返回命中偏移以及每个命中点附近的十六进制窗口。",
#                 "en": "Search a binary file for a hex pattern and return matched offsets with nearby hex windows."
#             },
#             "parameters": [
#                 { "name": "file_path", "description": { "zh": "目标文件路径。", "en": "Target file path." }, "type": "string", "required": true },
#                 { "name": "hex_bytes", "description": { "zh": "要搜索的 hex 模式，例如 '50 4B 03 04'。", "en": "Hex pattern to search for, for example '50 4B 03 04'." }, "type": "string", "required": true },
#                 { "name": "max_results", "description": { "zh": "最多返回多少个命中，默认 20，最大 100。", "en": "Maximum number of matches to return. Default 20, max 100." }, "type": "number", "required": false },
#                 { "name": "environment", "description": { "zh": "文件环境：android 或 linux，默认 android。", "en": "File environment: android or linux. Defaults to android." }, "type": "string", "required": false }
#             ]
#         }
#     ]
# }

import base64
import math
import re
import traceback

DEFAULT_WINDOW_LENGTH = 128
MAX_WINDOW_LENGTH = 4096
DEFAULT_MAX_RESULTS = 20
MAX_RESULTS_LIMIT = 100
CONTEXT_BEFORE = 16
CONTEXT_TOTAL = 64
BYTES_PER_LINE = 16


def _is_finite(n):
    return isinstance(n, (int, float)) and not isinstance(n, bool) and math.isfinite(n)


def normalizeEnvironment(environment=None):
    value = str(environment or "android").strip().lower()
    if value != "android" and value != "linux":
        raise Exception("environment 只能是 android 或 linux。")
    return value


def normalizeBase64Input(value):
    cleaned = re.sub(r"\s+", "", str(value or ""))
    cleaned = cleaned.replace("-", "+").replace("_", "/")
    if not cleaned:
        return ""
    remainder = len(cleaned) % 4
    if remainder == 1:
        raise Exception("Invalid base64 string")
    if remainder == 0:
        return cleaned
    return cleaned + "=" * (4 - remainder)


def decodeBase64ToBytes(value):
    normalized = normalizeBase64Input(value)
    if not normalized:
        return []
    decoded = base64.b64decode(normalized)
    return list(decoded)


def encodeBytesToBase64(byte_list):
    raw = bytes((b & 0xFF) for b in byte_list)
    return base64.b64encode(raw).decode("ascii")


def parseOffset(value):
    trimmed = str(value or "").strip().lower()
    if not trimmed:
        raise Exception("offset 不能为空。")

    if re.match(r"^0x[0-9a-f]+$", trimmed):
        parsed = int(trimmed[2:], 16)
    elif re.match(r"^\d+$", trimmed):
        parsed = int(trimmed, 10)
    else:
        raise Exception("offset 必须是十进制数字或 0x 开头的十六进制。")

    if not _is_finite(parsed) or parsed < 0:
        raise Exception("offset 必须是大于等于 0 的整数。")
    return parsed


def clampPositiveInteger(value, defaultValue, maxValue, fieldName):
    actual = defaultValue if value is None else int(value)
    if not _is_finite(actual) or actual <= 0:
        raise Exception(f"{fieldName} 必须是大于 0 的整数。")
    return min(actual, maxValue)


def normalizeHexBytesInput(value):
    trimmed = str(value or "").strip()
    if not trimmed:
        raise Exception("hex_bytes 不能为空。")
    withoutPrefix = re.sub(r"^0x", "", trimmed, flags=re.IGNORECASE)
    normalized = re.sub(r"[^0-9a-fA-F]", "", withoutPrefix).lower()
    if not normalized:
        raise Exception("hex_bytes 中没有可用的十六进制字符。")
    if len(normalized) % 2 != 0:
        raise Exception("hex_bytes 必须包含偶数个十六进制字符。")
    return normalized


def parseHexBytes(value):
    normalized = normalizeHexBytesInput(value)
    bytes_list = []
    for i in range(0, len(normalized), 2):
        bytes_list.append(int(normalized[i:i + 2], 16))
    return bytes_list


def toHex(value, width):
    hex_str = format(max(0, int(value or 0)), "x").upper()
    while len(hex_str) < width:
        hex_str = "0" + hex_str
    return hex_str


def bytesToHexString(bytes_list):
    return " ".join(toHex(b, 2) for b in bytes_list)


def bytesToAscii(bytes_list):
    return "".join(chr(b) if 32 <= b <= 126 else "." for b in bytes_list)


def buildHexDump(bytes_list, startOffset):
    if len(bytes_list) == 0:
        return ""

    lines = []
    offsetWidth = max(8, len(format(startOffset + len(bytes_list), "x")))

    for index in range(0, len(bytes_list), BYTES_PER_LINE):
        slice_ = bytes_list[index:index + BYTES_PER_LINE]
        hexCells = [toHex(b, 2) for b in slice_]
        while len(hexCells) < BYTES_PER_LINE:
            hexCells.append("  ")
        left = " ".join(hexCells[:8])
        right = " ".join(hexCells[8:])
        ascii_str = bytesToAscii(slice_).ljust(BYTES_PER_LINE, " ")
        lines.append(f"{toHex(startOffset + index, offsetWidth)}  {left}  {right}  |{ascii_str}|")

    return "\n".join(lines)


async def ensureFileExists(path, environment):
    exists = await Tools.Files.exists(path, environment)
    if not exists.get("exists"):
        raise Exception(f"文件不存在: {path}")
    if exists.get("isDirectory"):
        raise Exception(f"目标路径是目录，不是文件: {path}")


async def readFileBytes(path, environment):
    await ensureFileExists(path, environment)
    result = await Tools.Files.readBinary(path, environment)
    base64_str = str(result.get("contentBase64") or "")
    return {
        "base64": base64_str,
        "bytes": decodeBase64ToBytes(base64_str),
        "size": int(result.get("size") or 0)
    }


async def writeFileBytes(path, bytes_list, environment):
    return await Tools.Files.writeBinary(path, encodeBytesToBase64(bytes_list), environment)


def collectWindow(bytes_list, offset, length):
    if offset > len(bytes_list):
        raise Exception(f"offset 超出文件范围。文件大小为 {len(bytes_list)} 字节。")
    end = min(len(bytes_list), offset + length)
    window = bytes_list[offset:end]
    return {
        "window": window,
        "actualLength": len(window)
    }


async def read_hex_window(params):
    environment = normalizeEnvironment(params.get("environment"))
    offset = parseOffset(params.get("offset"))
    length = clampPositiveInteger(params.get("length"), DEFAULT_WINDOW_LENGTH, MAX_WINDOW_LENGTH, "length")
    file = await readFileBytes(params["file_path"], environment)
    collected = collectWindow(file["bytes"], offset, length)
    window = collected["window"]
    actualLength = collected["actualLength"]

    return {
        "file_path": params["file_path"],
        "environment": environment,
        "file_size": file["size"],
        "offset_decimal": offset,
        "offset_hex": f"0x{toHex(offset, 8)}",
        "requested_length": length,
        "actual_length": actualLength,
        "end_offset_exclusive_decimal": offset + actualLength,
        "end_offset_exclusive_hex": f"0x{toHex(offset + actualLength, 8)}",
        "hex": bytesToHexString(window),
        "ascii_preview": bytesToAscii(window),
        "hex_dump": buildHexDump(window, offset)
    }


async def write_hex_bytes(params):
    environment = normalizeEnvironment(params.get("environment"))
    offset = parseOffset(params.get("offset"))
    patchBytes = parseHexBytes(params.get("hex_bytes"))
    file = await readFileBytes(params["file_path"], environment)

    if offset + len(patchBytes) > len(file["bytes"]):
        raise Exception(f"写入范围超出文件大小。文件大小 {len(file['bytes'])} 字节，尝试写入到 {offset + len(patchBytes)}。")

    beforeBytes = file["bytes"][offset:offset + len(patchBytes)]
    for i in range(len(patchBytes)):
        file["bytes"][offset + i] = patchBytes[i]

    writeResult = await writeFileBytes(params["file_path"], file["bytes"], environment)
    afterBytes = file["bytes"][offset:offset + len(patchBytes)]

    return {
        "file_path": params["file_path"],
        "environment": environment,
        "offset_decimal": offset,
        "offset_hex": f"0x{toHex(offset, 8)}",
        "bytes_written": len(patchBytes),
        "before_hex": bytesToHexString(beforeBytes),
        "after_hex": bytesToHexString(afterBytes),
        "write_result": writeResult
    }


async def find_hex_pattern(params):
    environment = normalizeEnvironment(params.get("environment"))
    patternBytes = parseHexBytes(params.get("hex_bytes"))
    maxResults = clampPositiveInteger(params.get("max_results"), DEFAULT_MAX_RESULTS, MAX_RESULTS_LIMIT, "max_results")
    file = await readFileBytes(params["file_path"], environment)
    matches = []

    if len(patternBytes) > len(file["bytes"]):
        return {
            "file_path": params["file_path"],
            "environment": environment,
            "file_size": file["size"],
            "pattern_hex": bytesToHexString(patternBytes),
            "match_count": 0,
            "matches": matches
        }

    for offset in range(0, len(file["bytes"]) - len(patternBytes) + 1):
        matched = True
        for index in range(len(patternBytes)):
            if file["bytes"][offset + index] != patternBytes[index]:
                matched = False
                break
        if not matched:
            continue

        contextStart = max(0, offset - CONTEXT_BEFORE)
        contextEnd = min(len(file["bytes"]), contextStart + CONTEXT_TOTAL)
        contextBytes = file["bytes"][contextStart:contextEnd]

        matches.append({
            "offset_decimal": offset,
            "offset_hex": f"0x{toHex(offset, 8)}",
            "matched_hex": bytesToHexString(patternBytes),
            "context_hex_dump": buildHexDump(contextBytes, contextStart)
        })

        if len(matches) >= maxResults:
            break

    return {
        "file_path": params["file_path"],
        "environment": environment,
        "file_size": file["size"],
        "pattern_hex": bytesToHexString(patternBytes),
        "match_count": len(matches),
        "matches": matches
    }


async def wrap(fn, params, successMessage, failureMessage):
    try:
        data = await fn(params)
        complete({
            "success": True,
            "message": successMessage,
            "data": data
        })
    except Exception as error:
        console.error(f"[hex_editor] {fn.__name__} failed:", error)
        complete({
            "success": False,
            "message": f"{failureMessage}: {str(error)}",
            "error_stack": traceback.format_exc()
        })


async def _exported_read_hex_window(params):
    await wrap(read_hex_window, params, "Hex 窗口读取成功。", "Hex 窗口读取失败")


async def _exported_write_hex_bytes(params):
    await wrap(write_hex_bytes, params, "Hex 字节写入成功。", "Hex 字节写入失败")


async def _exported_find_hex_pattern(params):
    await wrap(find_hex_pattern, params, "Hex 模式搜索成功。", "Hex 模式搜索失败")


exports.read_hex_window = _exported_read_hex_window
exports.write_hex_bytes = _exported_write_hex_bytes
exports.find_hex_pattern = _exported_find_hex_pattern
