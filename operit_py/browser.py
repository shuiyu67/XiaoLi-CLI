# METADATA
# {
#     "name": "browser",
#     "display_name": {
#         "zh": "Browser 自动化操作",
#         "en": "Browser Automation"
#     },
#     "description": {
#         "zh": "严格对齐 Playwright MCP 默认 browser 工具面的浏览器自动化工具集。",
#         "en": "Browser automation tools aligned to the default Playwright MCP browser surface."
#     },
#     "enabledByDefault": true,
#     "category": "Automatic",
#     "tools": [
#         {
#             "name": "click",
#             "description": { "zh": "按快照 ref 点击页面元素，包括同源 iframe 内的元素。", "en": "Click an element by snapshot ref, including refs inside same-origin iframes." },
#             "parameters": [
#                 { "name": "ref", "description": { "zh": "快照中的目标元素引用；和 selector 至少提供一个。", "en": "Target element ref from the snapshot; provide ref or selector." }, "type": "string", "required": false },
#                 { "name": "selector", "description": { "zh": "可选，ref 不可用时的元素选择器。", "en": "Optional selector fallback when ref is not available." }, "type": "string", "required": false },
#                 { "name": "element", "description": { "zh": "可选，人类可读元素描述。", "en": "Optional human-readable element description." }, "type": "string", "required": false },
#                 { "name": "doubleClick", "description": { "zh": "可选，是否双击。", "en": "Optional double click." }, "type": "boolean", "required": false },
#                 { "name": "button", "description": { "zh": "可选，left/right/middle。", "en": "Optional mouse button: left/right/middle." }, "type": "string", "required": false },
#                 { "name": "modifiers", "description": { "zh": "可选，修饰键数组。", "en": "Optional modifier keys array." }, "type": "array", "required": false }
#             ]
#         },
#         {
#             "name": "close",
#             "description": { "zh": "关闭当前 tab。", "en": "Close the current tab." },
#             "parameters": []
#         },
#         {
#             "name": "console_messages",
#             "description": { "zh": "读取控制台消息。", "en": "Read console messages." },
#             "parameters": [
#                 { "name": "level", "description": { "zh": "可选，日志级别：error/warning/info/debug，默认 info。", "en": "Optional log level: error/warning/info/debug. Defaults to info." }, "type": "string", "required": false },
#                 { "name": "filename", "description": { "zh": "可选，保存输出的文件名。", "en": "Optional output file name." }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "drag",
#             "description": { "zh": "在两个元素之间拖拽。", "en": "Drag between two elements." },
#             "parameters": [
#                 { "name": "startElement", "description": { "zh": "源元素的人类可读描述。", "en": "Human-readable source element description." }, "type": "string", "required": true },
#                 { "name": "startRef", "description": { "zh": "源元素 ref。", "en": "Source element ref." }, "type": "string", "required": true },
#                 { "name": "endElement", "description": { "zh": "目标元素的人类可读描述。", "en": "Human-readable target element description." }, "type": "string", "required": true },
#                 { "name": "endRef", "description": { "zh": "目标元素 ref。", "en": "Target element ref." }, "type": "string", "required": true }
#             ]
#         },
#         {
#             "name": "evaluate",
#             "description": { "zh": "在页面或元素上执行 JavaScript 函数。", "en": "Evaluate a JavaScript function on the page or an element." },
#             "parameters": [
#                 { "name": "function", "description": { "zh": "要执行的函数源码。", "en": "Function source to execute." }, "type": "string", "required": true },
#                 { "name": "element", "description": { "zh": "可选，人类可读元素描述。", "en": "Optional human-readable element description." }, "type": "string", "required": false },
#                 { "name": "ref", "description": { "zh": "可选，目标元素 ref。", "en": "Optional target element ref." }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "upload",
#             "description": { "zh": "向当前文件选择器上传文件。", "en": "Upload files to the current file chooser." },
#             "parameters": [
#                 { "name": "paths", "description": { "zh": "可选，绝对路径数组；不传则取消 file chooser。", "en": "Optional absolute file paths; omit to cancel the file chooser." }, "type": "array", "required": false }
#             ]
#         },
#         {
#             "name": "fill_form",
#             "description": { "zh": "批量填写表单字段。", "en": "Fill multiple form fields." },
#             "parameters": [
#                 { "name": "fields", "description": { "zh": "字段数组。", "en": "Array of form fields." }, "type": "array", "required": true }
#             ]
#         },
#         {
#             "name": "handle_dialog",
#             "description": { "zh": "处理当前对话框。", "en": "Handle the current dialog." },
#             "parameters": [
#                 { "name": "accept", "description": { "zh": "是否接受对话框。", "en": "Whether to accept the dialog." }, "type": "boolean", "required": true },
#                 { "name": "promptText", "description": { "zh": "可选，prompt 的输入文本。", "en": "Optional prompt text." }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "hover",
#             "description": { "zh": "悬停到页面元素上。", "en": "Hover over an element." },
#             "parameters": [
#                 { "name": "ref", "description": { "zh": "目标元素 ref。", "en": "Target element ref." }, "type": "string", "required": true },
#                 { "name": "element", "description": { "zh": "可选，人类可读元素描述。", "en": "Optional human-readable element description." }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "goto",
#             "description": { "zh": "导航到指定 URL。", "en": "Navigate to a URL." },
#             "parameters": [
#                 { "name": "url", "description": { "zh": "目标 URL。", "en": "Target URL." }, "type": "string", "required": true }
#             ]
#         },
#         {
#             "name": "back",
#             "description": { "zh": "后退到上一页。", "en": "Go back to the previous page." },
#             "parameters": []
#         },
#         {
#             "name": "network_requests",
#             "description": { "zh": "读取当前页面的网络请求。", "en": "Read network requests for the current page." },
#             "parameters": [
#                 { "name": "includeStatic", "description": { "zh": "可选，是否包含静态资源请求，默认 false。", "en": "Optional include static resource requests. Defaults to false." }, "type": "boolean", "required": false },
#                 { "name": "filename", "description": { "zh": "可选，保存输出的文件名。", "en": "Optional output file name." }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "press_key",
#             "description": { "zh": "按下键盘按键。", "en": "Press a keyboard key." },
#             "parameters": [
#                 { "name": "key", "description": { "zh": "按键名。", "en": "Key name." }, "type": "string", "required": true }
#             ]
#         },
#         {
#             "name": "resize",
#             "description": { "zh": "调整浏览器视口大小。", "en": "Resize the browser viewport." },
#             "parameters": [
#                 { "name": "width", "description": { "zh": "宽度。", "en": "Width." }, "type": "number", "required": true },
#                 { "name": "height", "description": { "zh": "高度。", "en": "Height." }, "type": "number", "required": true }
#             ]
#         },
#         {
#             "name": "run_code",
#             "description": { "zh": "运行 Playwright 风格代码片段。", "en": "Run a Playwright-style code snippet." },
#             "parameters": [
#                 { "name": "code", "description": { "zh": "代码片段。", "en": "Code snippet." }, "type": "string", "required": true }
#             ]
#         },
#         {
#             "name": "select_option",
#             "description": { "zh": "在下拉框中选择选项。", "en": "Select options in a dropdown." },
#             "parameters": [
#                 { "name": "ref", "description": { "zh": "目标元素 ref。", "en": "Target element ref." }, "type": "string", "required": true },
#                 { "name": "values", "description": { "zh": "要选择的值数组。", "en": "Values to select." }, "type": "array", "required": true },
#                 { "name": "element", "description": { "zh": "可选，人类可读元素描述。", "en": "Optional human-readable element description." }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "snapshot",
#             "description": { "zh": "获取当前页面结构化快照，包括同源 iframe 内容。", "en": "Get a structured page snapshot, including same-origin iframe content." },
#             "parameters": [
#                 { "name": "filename", "description": { "zh": "可选，保存快照的文件名。", "en": "Optional snapshot output file name." }, "type": "string", "required": false },
#                 { "name": "selector", "description": { "zh": "可选，作为快照根节点的元素选择器。", "en": "Optional root element selector for a partial snapshot." }, "type": "string", "required": false },
#                 { "name": "depth", "description": { "zh": "可选，限制快照树深度。", "en": "Optional snapshot tree depth limit." }, "type": "number", "required": false }
#             ]
#         },
#         {
#             "name": "type",
#             "description": { "zh": "向可编辑元素输入文本。", "en": "Type text into an editable element." },
#             "parameters": [
#                 { "name": "ref", "description": { "zh": "目标元素 ref。", "en": "Target element ref." }, "type": "string", "required": true },
#                 { "name": "text", "description": { "zh": "输入文本。", "en": "Text to type." }, "type": "string", "required": true },
#                 { "name": "element", "description": { "zh": "可选，人类可读元素描述。", "en": "Optional human-readable element description." }, "type": "string", "required": false },
#                 { "name": "submit", "description": { "zh": "可选，输入后是否提交。", "en": "Optional submit after typing." }, "type": "boolean", "required": false },
#                 { "name": "slowly", "description": { "zh": "可选，是否逐字输入。", "en": "Optional type slowly." }, "type": "boolean", "required": false }
#             ]
#         },
#         {
#             "name": "wait_for",
#             "description": { "zh": "等待文本出现、消失或等待指定时间。", "en": "Wait for text to appear, disappear, or for a duration." },
#             "parameters": [
#                 { "name": "time", "description": { "zh": "可选，等待秒数。", "en": "Optional number of seconds to wait." }, "type": "number", "required": false },
#                 { "name": "text", "description": { "zh": "可选，等待出现的文本。", "en": "Optional text to wait for." }, "type": "string", "required": false },
#                 { "name": "textGone", "description": { "zh": "可选，等待消失的文本。", "en": "Optional text to wait to disappear." }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "tabs",
#             "description": { "zh": "列出、创建、切换或关闭 tab。", "en": "List, create, select, or close tabs." },
#             "parameters": [
#                 { "name": "action", "description": { "zh": "操作：list/create/select/close。", "en": "Action: list/create/select/close." }, "type": "string", "required": true },
#                 { "name": "index", "description": { "zh": "可选，0-based tab 索引。", "en": "Optional 0-based tab index." }, "type": "number", "required": false }
#             ]
#         }
#     ]
# }

import datetime
import random
import re

MAX_INLINE_BROWSER_TEXT_CHARS = 24000

TOOL_NAMES = [
    "click",
    "close",
    "close_all",
    "console_messages",
    "drag",
    "evaluate",
    "upload",
    "fill_form",
    "handle_dialog",
    "hover",
    "goto",
    "back",
    "network_requests",
    "press_key",
    "resize",
    "run_code",
    "select_option",
    "snapshot",
    "type",
    "wait_for",
    "tabs"
]


def normalizeOptionalString(value=None):
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized if normalized else None


def buildLargeOutputFilename(prefix, extension):
    timestamp = datetime.datetime.utcnow().isoformat().replace(":", "-").replace(".", "-")
    rand = int(random.random() * 1000000)
    return OPERIT_CLEAN_ON_EXIT_DIR + "/browser_" + prefix + "_" + timestamp + "_" + rand + "." + extension


async def maybePersistLargeBrowserResponse(result, prefix, extension="md"):
    if not isinstance(result, str) or len(result) <= MAX_INLINE_BROWSER_TEXT_CHARS:
        return result
    await Tools.Files.mkdir(OPERIT_CLEAN_ON_EXIT_DIR, True)
    filename = buildLargeOutputFilename(prefix, extension)
    await Tools.Files.write(filename, result, False)
    normalizedPath = filename.replace("\\", "/")
    return "Large browser response saved to:\n- [Browser Output](" + normalizedPath + ")"


async def click(params):
    result = await Tools.Net.browserClick(params)
    return await maybePersistLargeBrowserResponse(result, "click")


async def close(params=None):
    if params is None:
        params = {}
    result = await Tools.Net.browserClose()
    return await maybePersistLargeBrowserResponse(result, "close")


async def close_all(params=None):
    if params is None:
        params = {}
    result = await Tools.Net.browserCloseAll()
    return await maybePersistLargeBrowserResponse(result, "close_all")


async def console_messages(params=None):
    if params is None:
        params = {}
    result = await Tools.Net.browserConsoleMessages(params)
    return await maybePersistLargeBrowserResponse(result, "console_messages")


async def drag(params):
    result = await Tools.Net.browserDrag(params)
    return await maybePersistLargeBrowserResponse(result, "drag")


async def evaluate(params):
    result = await Tools.Net.browserEvaluate(params)
    return await maybePersistLargeBrowserResponse(result, "evaluate")


async def upload(params=None):
    if params is None:
        params = {}
    result = await Tools.Net.browserFileUpload(params)
    return await maybePersistLargeBrowserResponse(result, "upload")


def normalizeFormFields(fields):
    if len(fields) == 0:
        raise Exception("fields must be a non-empty array")
    normalizedFields = []
    for index, field in enumerate(fields):
        normalized = {
            "name": str(field.get("name", "")).strip(),
            "type": str(field.get("type", "")).strip(),
            "value": field.get("value")
        }
        if not normalized["name"]:
            raise Exception("fields[" + str(index) + "].name is required")
        if not normalized["type"]:
            raise Exception("fields[" + str(index) + "].type is required")
        ref = normalizeOptionalString(field.get("ref"))
        selector = normalizeOptionalString(field.get("selector"))
        if not ref and not selector:
            raise Exception("fields[" + str(index) + "] requires ref or selector")
        if ref:
            normalized["ref"] = ref
        if selector:
            normalized["selector"] = selector
        normalizedFields.append(normalized)
    return normalizedFields


async def fill_form(params):
    result = await Tools.Net.browserFillForm({
        "fields": normalizeFormFields(params["fields"])
    })
    return await maybePersistLargeBrowserResponse(result, "fill_form")


async def handle_dialog(params):
    result = await Tools.Net.browserHandleDialog(params)
    return await maybePersistLargeBrowserResponse(result, "handle_dialog")


async def hover(params):
    result = await Tools.Net.browserHover(params)
    return await maybePersistLargeBrowserResponse(result, "hover")


async def goto(params):
    result = await Tools.Net.browserNavigate(params)
    return await maybePersistLargeBrowserResponse(result, "goto")


async def back(params=None):
    if params is None:
        params = {}
    result = await Tools.Net.browserNavigateBack()
    return await maybePersistLargeBrowserResponse(result, "back")


async def network_requests(params=None):
    if params is None:
        params = {}
    result = await Tools.Net.browserNetworkRequests(params)
    return await maybePersistLargeBrowserResponse(result, "network_requests")


async def press_key(params):
    result = await Tools.Net.browserPressKey(params)
    return await maybePersistLargeBrowserResponse(result, "press_key")


async def resize(params):
    result = await Tools.Net.browserResize(params)
    return await maybePersistLargeBrowserResponse(result, "resize")


async def run_code(params):
    result = await Tools.Net.browserRunCode(params)
    return await maybePersistLargeBrowserResponse(result, "run_code")


async def select_option(params):
    result = await Tools.Net.browserSelectOption(params)
    return await maybePersistLargeBrowserResponse(result, "select_option")


async def snapshot(params=None):
    if params is None:
        params = {}
    result = await Tools.Net.browserSnapshot(params)
    return await maybePersistLargeBrowserResponse(result, "snapshot")


async def type(params):
    result = await Tools.Net.browserType(params)
    return await maybePersistLargeBrowserResponse(result, "type")


async def wait_for(params=None):
    if params is None:
        params = {}
    result = await Tools.Net.browserWaitFor(params)
    return await maybePersistLargeBrowserResponse(result, "wait_for")


async def tabs(params):
    result = await Tools.Net.browserTabs(params)
    return await maybePersistLargeBrowserResponse(result, "tabs")


async def browserMain(params=None):
    if params is None:
        params = {}
    return "Browser package ready: " + ", ".join(TOOL_NAMES)


exports.click = click
exports.close = close
exports.close_all = close_all
exports.console_messages = console_messages
exports.drag = drag
exports.evaluate = evaluate
exports.upload = upload
exports.fill_form = fill_form
exports.handle_dialog = handle_dialog
exports.hover = hover
exports.goto = goto
exports.back = back
exports.network_requests = network_requests
exports.press_key = press_key
exports.resize = resize
exports.run_code = run_code
exports.select_option = select_option
exports.snapshot = snapshot
exports.type = type
exports.wait_for = wait_for
exports.tabs = tabs
exports.main = browserMain
