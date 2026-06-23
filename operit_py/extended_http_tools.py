# METADATA
# {
#     "name": "extended_http_tools",
#
#     "display_name": {
#         "zh": "增强 HTTP 工具",
#         "en": "Extended HTTP Tools"
#     },
#     "description": {
#         "zh": "允许文件上传，以及 GET/POST 等网络直接访问操作。",
#         "en": "Allows file uploads and direct network access operations such as GET/POST."
#     },
#     "enabledByDefault": true,
#     "category": "Network",
#     "tools": [
#         {
#             "name": "http_request",
#             "description": { "zh": "发送 HTTP 请求。", "en": "Send an HTTP request." },
#             "parameters": [
#                 { "name": "url", "description": { "zh": "请求 URL", "en": "Request URL" }, "type": "string", "required": true },
#                 { "name": "method", "description": { "zh": "请求方法：GET/POST/PUT/DELETE", "en": "Method: GET/POST/PUT/DELETE" }, "type": "string", "required": true },
#                 { "name": "headers", "description": { "zh": "可选：headers（JSON 对象字符串）", "en": "Optional: headers (JSON object string)" }, "type": "string", "required": false },
#                 { "name": "body", "description": { "zh": "可选：请求体（字符串）", "en": "Optional: body (string)" }, "type": "string", "required": false },
#                 { "name": "body_type", "description": { "zh": "可选：json/form/text/xml", "en": "Optional: json/form/text/xml" }, "type": "string", "required": false },
#                 { "name": "ignore_ssl", "description": { "zh": "可选：是否忽略 HTTPS 证书校验（true/false）", "en": "Optional: ignore HTTPS certificate verification (true/false)" }, "type": "boolean", "required": false }
#             ]
#         },
#         {
#             "name": "multipart_request",
#             "description": { "zh": "上传文件（multipart）。", "en": "Upload files (multipart)." },
#             "parameters": [
#                 { "name": "url", "description": { "zh": "请求 URL", "en": "Request URL" }, "type": "string", "required": true },
#                 { "name": "method", "description": { "zh": "请求方法：POST/PUT", "en": "Method: POST/PUT" }, "type": "string", "required": true },
#                 { "name": "headers", "description": { "zh": "可选：headers（JSON 对象字符串）", "en": "Optional: headers (JSON object string)" }, "type": "string", "required": false },
#                 { "name": "form_data", "description": { "zh": "可选：form_data（字符串）", "en": "Optional: form_data (string)" }, "type": "string", "required": false },
#                 { "name": "files", "description": { "zh": "可选：files（JSON 数组字符串）", "en": "Optional: files (JSON array string)" }, "type": "string", "required": false },
#                 { "name": "ignore_ssl", "description": { "zh": "可选：是否忽略 HTTPS 证书校验（true/false）", "en": "Optional: ignore HTTPS certificate verification (true/false)" }, "type": "boolean", "required": false }
#             ]
#         },
#         {
#             "name": "manage_cookies",
#             "description": { "zh": "管理 Cookies。", "en": "Manage cookies." },
#             "parameters": [
#                 { "name": "action", "description": { "zh": "操作：get/set/clear", "en": "Action: get/set/clear" }, "type": "string", "required": true },
#                 { "name": "domain", "description": { "zh": "可选：域名", "en": "Optional: domain" }, "type": "string", "required": false },
#                 { "name": "cookies", "description": { "zh": "可选：cookies（字符串）", "en": "Optional: cookies (string)" }, "type": "string", "required": false }
#             ]
#         }
#     ]
# }

import re
import random
import datetime

MAX_INLINE_HTTP_RESPONSE_CHARS = 12000


async def http_request(params):
    toolParams = {
        "url": params["url"],
        "method": params["method"],
    }
    if params.get("headers") is not None:
        toolParams["headers"] = params["headers"]
    if params.get("body") is not None:
        toolParams["body"] = params["body"]
    if params.get("body_type") is not None:
        toolParams["body_type"] = params["body_type"]
    if params.get("ignore_ssl") is not None:
        toolParams["ignore_ssl"] = params["ignore_ssl"]

    result = await toolCall({"name": "http_request", "params": toolParams})
    statusCode = result.get("statusCode")
    success = statusCode is not None and statusCode >= 200 and statusCode < 400

    contentStr = result.get("content") if isinstance(result.get("content"), str) else ""
    if len(contentStr) > MAX_INLINE_HTTP_RESPONSE_CHARS:
        await Tools.Files.mkdir(OPERIT_CLEAN_ON_EXIT_DIR, True)

        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        timestamp = re.sub(r'[:.]', '-', timestamp)
        rand = int(random.random() * 1000000)

        ext = "txt"
        ct = result.get("contentType", "").lower() if isinstance(result.get("contentType"), str) else ""
        if "json" in ct:
            ext = "json"
        elif "html" in ct:
            ext = "html"
        elif "xml" in ct:
            ext = "xml"

        filePath = f"{OPERIT_CLEAN_ON_EXIT_DIR}/http_response_{timestamp}_{rand}.{ext}"
        await Tools.Files.write(filePath, contentStr, False)

        resultMeta = {
            "url": result.get("url"),
            "statusCode": result.get("statusCode"),
            "statusMessage": result.get("statusMessage"),
            "headers": result.get("headers"),
            "contentType": result.get("contentType"),
            "size": result.get("size"),
            "content": "(saved_to_file)",
        }

        return {
            "success": success,
            "message": f"HTTP 请求完成；响应内容过大，已保存到文件：{filePath}。请使用 read_file_part 读取指定行范围，或用 grep_code 在该文件中检索关键字。",
            "data": {
                "result": resultMeta,
                "content_saved_to": filePath,
                "operit_clean_on_exit_dir": OPERIT_CLEAN_ON_EXIT_DIR,
            },
        }

    return {"success": success, "message": "HTTP 请求完成", "data": result}


async def multipart_request(params):
    toolParams = {
        "url": params["url"],
        "method": params["method"],
    }
    if params.get("headers") is not None:
        toolParams["headers"] = params["headers"]
    if params.get("form_data") is not None:
        toolParams["form_data"] = params["form_data"]
    if params.get("files") is not None:
        toolParams["files"] = params["files"]
    if params.get("ignore_ssl") is not None:
        toolParams["ignore_ssl"] = params["ignore_ssl"]

    result = await toolCall({"name": "multipart_request", "params": toolParams})
    statusCode = result.get("statusCode")
    success = statusCode is not None and statusCode >= 200 and statusCode < 400
    return {"success": success, "message": "文件上传完成", "data": result}


async def manage_cookies(params):
    toolParams = {
        "action": params["action"],
    }
    if params.get("domain") is not None:
        toolParams["domain"] = params["domain"]
    if params.get("cookies") is not None:
        toolParams["cookies"] = params["cookies"]

    result = await toolCall({"name": "manage_cookies", "params": toolParams})
    statusCode = result.get("statusCode")
    success = statusCode is not None and statusCode >= 200 and statusCode < 400
    return {"success": success, "message": "Cookies 操作完成", "data": result}


async def wrapToolExecution(func, params):
    try:
        result = await func(params)
        complete(result)
    except Exception as error:
        console.error(f"Tool {func.__name__} failed unexpectedly", error)
        msg = getattr(error, "message", str(error))
        complete({
            "success": False,
            "message": f"工具执行时发生意外错误: {msg}",
        })


async def main():
    results = []

    # 这些工具可能对外发请求 / 写 cookies，默认不做自动化演示。
    results.append({"tool": "http_request", "result": {"success": None, "message": "未测试（会对外发起网络请求）"}})
    results.append({"tool": "multipart_request", "result": {"success": None, "message": "未测试（会上传文件/对外发起网络请求）"}})
    results.append({"tool": "manage_cookies", "result": {"success": None, "message": "未测试（会读写 cookies）"}})

    complete({
        "success": True,
        "message": "拓展 HTTP 工具包加载完成（未执行网络请求测试）",
        "data": {"results": results}
    })


async def http_request_wrapper(params):
    await wrapToolExecution(http_request, params)


async def multipart_request_wrapper(params):
    await wrapToolExecution(multipart_request, params)


async def manage_cookies_wrapper(params):
    await wrapToolExecution(manage_cookies, params)


exports.http_request = http_request_wrapper
exports.multipart_request = multipart_request_wrapper
exports.manage_cookies = manage_cookies_wrapper
exports.main = main
