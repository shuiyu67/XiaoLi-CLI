# METADATA
# {
#     "name": "super_admin",
#     "display_name": {
#         "zh": "超级管理员",
#         "en": "Super Admin"
#     },
#     "description": { "zh": "超级管理员工具集，提供终端命令和Shell操作的高级功能。terminal工具运行在Ubuntu环境中（已正确挂载sdcard和storage），shell工具通过Shizuku/Root直接执行Android系统命令。适合需要进行底层系统管理和命令行操作的场景。", "en": "Super admin toolkit providing advanced terminal and shell capabilities. The terminal tool runs in an Ubuntu environment (with sdcard/storage mounted). The shell tool executes Android system commands directly via Shizuku/Root. Useful for low-level system administration and CLI operations." },
#     "enabledByDefault": true,
#     "category": "System",
#     "tools": [
#         {
#             "name": "terminal",
#             "description": { "zh": "在Ubuntu环境中执行命令并收集输出结果。运行环境：完整的Ubuntu系统，已正确挂载sdcard和storage目录，可访问Android存储空间。所有命令将会在相同的会话执行且上下文连贯。强烈建议每次都显式传 timeoutMs，避免命令卡住。禁止使用 `set -e`、`set -o errexit` 等会改变 shell 退出行为的命令，这会导致终端会话直接退出并卡死。若未传，前台默认15秒超时；background=true 时不使用该默认超时。命令超时时不会被自动取消，不需要重新执行命令，请继续通过 terminal_getscreen 跟踪当前屏幕内容。", "en": "Execute commands in an Ubuntu environment and collect output. Environment: full Ubuntu system with sdcard/storage mounted, allowing access to Android storage. Automatically preserves working-directory context. Strongly recommend explicitly passing timeoutMs every time to avoid hangs. Do not use commands such as `set -e` or `set -o errexit` that change shell exit behavior, because they can cause the terminal session to exit and hang. If omitted, foreground mode defaults to 15s timeout; background=true does not use this default timeout. When a command times out, it is not automatically cancelled. Do not rerun the command; continue tracking the current screen via terminal_getscreen." },
#             "parameters": [
#                 { "name": "command", "description": { "zh": "要执行的命令", "en": "Command to execute." }, "type": "string", "required": true },
#                 { "name": "background", "description": { "zh": "是否在后台运行命令,\"true\" 表示后台执行并立即返回,适合启动服务器等长时间运行的任务（AI 不会收到该命令的输出结果），\"false\" 或未提供则前台执行并等待并返回命令结果", "en": "Run command in background. 'true' runs in background and returns immediately (good for long-running tasks like servers; AI will not receive output). 'false' or omitted runs in foreground and returns the command result." }, "type": "string", "required": false },
#                 { "name": "timeoutMs", "description": { "zh": "可选超时（毫秒，最低3000ms）。强烈建议显式传入；未传时前台默认15000ms，background=true时不使用默认超时。", "en": "Optional timeout (ms, minimum 3000ms). Strongly recommended to pass explicitly; if omitted, foreground defaults to 15000ms, and background=true does not use the default timeout." }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "terminal_wait",
#             "description": { "zh": "等待同一终端会话中的上一条命令执行完成。适用于安装/编译等长命令在 timeout 后继续后台执行的场景。与 sleep 不同，本工具会在命令实际完成时提前返回，而不是固定睡眠。", "en": "Wait until the previous command in the same terminal session finishes. Useful when long install/build commands continue running after a timeout. Unlike sleep, this tool can return early as soon as the command actually completes." },
#             "parameters": [
#                 { "name": "sessionId", "description": { "zh": "可选目标会话ID。不传则使用当前对话的默认会话；无 chatId 时为 super_admin_default_session。", "en": "Optional target session ID. If omitted, uses the current chat's default session; without chatId it is super_admin_default_session." }, "type": "string", "required": false },
#                 { "name": "timeoutMs", "description": { "zh": "可选超时（毫秒，最低3000ms）。未传时默认300000ms（5分钟）。", "en": "Optional timeout (ms, minimum 3000ms). Defaults to 300000ms (5 minutes) if omitted." }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "terminal_getscreen",
#             "description": { "zh": "获取当前终端会话可见屏幕内容（仅一屏，不包含历史滚动缓冲）。", "en": "Get the current visible screen content for the active terminal session (single screen only, no scrollback history)." },
#             "parameters": []
#         },
#         {
#             "name": "terminal_input",
#             "description": { "zh": "向当前终端会话写入输入。input 与 control 至少传一个。常见用法：先写 input，再写 control=enter 提交；control=ctrl 且 input=c 可发送 Ctrl+C。", "en": "Write input to the active terminal session. Provide at least one of input or control. Typical usage: send input first, then control=enter to submit; use control=ctrl with input=c for Ctrl+C." },
#             "parameters": [
#                 { "name": "input", "description": { "zh": "写入终端的文本", "en": "Text to write to terminal." }, "type": "string", "required": false },
#                 { "name": "control", "description": { "zh": "控制键，例如 enter / tab / esc / ctrl", "en": "Control key, e.g. enter / tab / esc / ctrl." }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "shell",
#             "description": { "zh": "通过Shizuku/Root权限直接在Android系统中执行Shell命令。运行环境：直接访问Android系统，具有系统级权限，适用于需要操作Android系统底层的场景（如pm、am等系统命令）。", "en": "Execute shell commands directly on Android with Shizuku/Root. Environment: direct Android system access with system-level privileges, suitable for low-level commands such as pm/am." },
#             "parameters": [
#                 { "name": "command", "description": { "zh": "要执行的Shell命令", "en": "Shell command to execute." }, "type": "string", "required": true }
#             ]
#         }
#     ]
# }

import asyncio
import datetime
import math
import random
import re
import time
import traceback

MAX_INLINE_TERMINAL_OUTPUT_CHARS = 12000
DEFAULT_FOREGROUND_TIMEOUT_MS = 15000
DEFAULT_WAIT_TIMEOUT_MS = 300000
MIN_TIMEOUT_MS = 3000
DEFAULT_TERMINAL_SESSION_NAME = "super_admin_default_session"
BACKGROUND_TERMINAL_SESSION_PREFIX = "super_admin_background"


def _is_finite(n):
    return isinstance(n, (int, float)) and not isinstance(n, bool) and math.isfinite(n)


def getCurrentChatSessionSuffix():
    chatId = getChatId()
    if chatId is None:
        return ""
    normalizedChatId = (chatId or "").strip()
    if not normalizedChatId:
        return ""
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", normalizedChatId)


def getDefaultTerminalSessionName():
    chatSuffix = getCurrentChatSessionSuffix()
    return f"{DEFAULT_TERMINAL_SESSION_NAME}_{chatSuffix}" if chatSuffix else DEFAULT_TERMINAL_SESSION_NAME


def getBackgroundTerminalSessionName():
    chatSuffix = getCurrentChatSessionSuffix()
    prefix = f"{BACKGROUND_TERMINAL_SESSION_PREFIX}_{chatSuffix}" if chatSuffix else BACKGROUND_TERMINAL_SESSION_PREFIX
    return f"{prefix}_{int(time.time() * 1000)}"


async def persistTerminalOutputIfTooLong(command, result):
    outputStr = result.get("output") if isinstance(result, dict) else None
    if not isinstance(outputStr, str):
        outputStr = str((result.get("output") if isinstance(result, dict) else "") or "")

    if len(outputStr) <= MAX_INLINE_TERMINAL_OUTPUT_CHARS:
        return None

    await Tools.Files.mkdir(OPERIT_CLEAN_ON_EXIT_DIR, True)

    timestamp = datetime.datetime.utcnow().isoformat().replace(":", "-").replace(".", "-")
    rand = int(random.random() * 1000000)
    filePath = f"{OPERIT_CLEAN_ON_EXIT_DIR}/terminal_output_{timestamp}_{rand}.log"

    await Tools.Files.write(filePath, outputStr, False)

    return {
        "command": command,
        "output": "(saved_to_file)",
        "exitCode": result.get("exitCode") if isinstance(result, dict) else None,
        "sessionId": result.get("sessionId") if isinstance(result, dict) else None,
        "context_preserved": True,
        "output_saved_to": filePath,
        "output_chars": len(outputStr),
        "operit_clean_on_exit_dir": OPERIT_CLEAN_ON_EXIT_DIR,
        "hint": "Output is large and saved to file. Use read_file_part or grep_code to inspect it.",
    }


async def terminal(params):
    try:
        if not params.get("command"):
            raise Exception("命令不能为空")

        command = params["command"]
        background = params.get("background")
        timeoutMs = params.get("timeoutMs")

        console.log(f"执行终端命令: {command}")

        isBackground = background == "true"
        timeout = None
        if not isBackground:
            if timeoutMs is not None:
                parsedTimeout = int(timeoutMs)
                if not _is_finite(parsedTimeout) or parsedTimeout < MIN_TIMEOUT_MS:
                    raise Exception(f"timeoutMs必须是整数且不少于{MIN_TIMEOUT_MS}毫秒")
                timeout = parsedTimeout
            else:
                timeout = DEFAULT_FOREGROUND_TIMEOUT_MS

        if isBackground:
            session = await Tools.System.terminal.create(getBackgroundTerminalSessionName())
            sessionId = session["sessionId"]

            # 调用系统工具执行终端命令（后台运行，不等待）
            async def _bg_exec():
                try:
                    await Tools.System.terminal.exec(sessionId, command)
                except Exception as error:
                    console.error(f"[terminal/background] 错误: {str(error)}")
                    console.error(traceback.format_exc())

            asyncio.ensure_future(_bg_exec())

            return {
                "command": command,
                "background": True,
                "sessionId": sessionId,
                "started": True
            }

        # 创建或获取一个默认会话
        session = await Tools.System.terminal.create(getDefaultTerminalSessionName())
        sessionId = session["sessionId"]

        # 调用系统工具执行终端命令
        result = await Tools.System.terminal.exec(sessionId, command, timeout)
        timedOut = result.get("timedOut") is True

        timeoutScreen = None
        if timedOut:
            screenResult = await Tools.System.terminal.screen(sessionId)
            timeoutScreen = {
                "sessionId": screenResult.get("sessionId") or sessionId,
                "rows": screenResult.get("rows"),
                "cols": screenResult.get("cols"),
                "content": screenResult.get("content")
            }

        persistedResult = await persistTerminalOutputIfTooLong(command, result)
        if persistedResult:
            persistedResult["timeoutMsUsed"] = timeout
            if timeoutScreen:
                persistedResult["timeoutScreen"] = timeoutScreen
            return persistedResult

        return {
            "command": command,
            "output": result.get("output"),
            "exitCode": result.get("exitCode"),
            "sessionId": result.get("sessionId"),
            "timedOut": timedOut,
            "timeoutMsUsed": timeout,
            "timeoutScreen": timeoutScreen,
            "context_preserved": True  # 标记此命令保留了目录上下文
        }
    except Exception as error:
        console.error(f"[terminal] 错误: {str(error)}")
        console.error(traceback.format_exc())

        raise error


async def terminal_wait(params=None):
    if params is None:
        params = {}
    try:
        timeoutMs = params.get("timeoutMs")
        timeout = DEFAULT_WAIT_TIMEOUT_MS
        if timeoutMs is not None:
            parsedTimeout = int(timeoutMs)
            if not _is_finite(parsedTimeout) or parsedTimeout < MIN_TIMEOUT_MS:
                raise Exception(f"timeoutMs必须是整数且不少于{MIN_TIMEOUT_MS}毫秒")
            timeout = parsedTimeout

        if params.get("sessionId"):
            session = {"sessionId": params["sessionId"]}
        else:
            session = await Tools.System.terminal.create(getDefaultTerminalSessionName())
        sessionId = session["sessionId"]

        marker = f"__OPERIT_TERMINAL_WAIT_DONE_{int(time.time() * 1000)}_{int(random.random() * 1000000)}__"
        waitCommand = f"printf '{marker}\\n'"
        startedAt = int(time.time() * 1000)
        result = await Tools.System.terminal.exec(sessionId, waitCommand, timeout)
        elapsedMs = int(time.time() * 1000) - startedAt
        timedOut = (result or {}).get("timedOut") is True

        timeoutScreen = None
        if timedOut:
            screenResult = await Tools.System.terminal.screen(sessionId)
            timeoutScreen = {
                "sessionId": screenResult.get("sessionId") or sessionId,
                "rows": screenResult.get("rows"),
                "cols": screenResult.get("cols"),
                "content": screenResult.get("content")
            }

        outputStr = (result or {}).get("output")
        if not isinstance(outputStr, str):
            outputStr = str((result or {}).get("output") or "")
        markerSeen = marker in outputStr

        return {
            "sessionId": sessionId,
            "timedOut": timedOut,
            "timeoutMsUsed": timeout,
            "elapsedMs": elapsedMs,
            "waitCompleted": (not timedOut) and markerSeen,
            "markerSeen": markerSeen,
            "exitCode": (result or {}).get("exitCode"),
            "timeoutScreen": timeoutScreen,
            "context_preserved": True
        }
    except Exception as error:
        console.error(f"[terminal_wait] 错误: {str(error)}")
        console.error(traceback.format_exc())
        raise error


async def shell(params):
    try:
        if not params.get("command"):
            raise Exception("命令不能为空")
        command = params["command"]

        console.log(f"执行Shell命令: {command}")

        # 通过Shizuku/Root权限执行shell操作
        result = await Tools.System.shell(f"{command}")

        return {
            "command": command,
            "output": result.get("output") if isinstance(result, dict) else result,
            "exitCode": result.get("exitCode") if isinstance(result, dict) else None
        }
    except Exception as error:
        console.error(f"[shell] 错误: {str(error)}")
        console.error(traceback.format_exc())

        raise error


async def terminal_getscreen(params=None):
    if params is None:
        params = {}
    try:
        session = await Tools.System.terminal.create(getDefaultTerminalSessionName())
        sessionId = session["sessionId"]
        result = await Tools.System.terminal.screen(sessionId)
        return {
            "sessionId": result.get("sessionId") or sessionId,
            "rows": result.get("rows"),
            "cols": result.get("cols"),
            "content": result.get("content"),
            "commandRunning": result.get("commandRunning") is True
        }
    except Exception as error:
        console.error(f"[terminal_getscreen] 错误: {str(error)}")
        console.error(traceback.format_exc())
        raise error


async def terminal_input(params=None):
    if params is None:
        params = {}
    try:
        if params.get("input") is None and params.get("control") is None:
            raise Exception("input和control至少需要提供一个")

        session = await Tools.System.terminal.create(getDefaultTerminalSessionName())
        sessionId = session["sessionId"]
        result = await Tools.System.terminal.input(sessionId, {
            "input": params.get("input"),
            "control": params.get("control")
        })

        return {
            "sessionId": sessionId,
            "input": params.get("input"),
            "control": params.get("control"),
            "result": (result.get("value") if isinstance(result, dict) and result.get("value") is not None else str(result if result is not None else ""))
        }
    except Exception as error:
        console.error(f"[terminal_input] 错误: {str(error)}")
        console.error(traceback.format_exc())
        raise error


exports.terminal = terminal
exports.terminal_wait = terminal_wait
exports.terminal_getscreen = terminal_getscreen
exports.terminal_input = terminal_input
exports.shell = shell
