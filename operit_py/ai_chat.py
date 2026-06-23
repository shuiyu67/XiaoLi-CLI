# METADATA
# {
#   "name": "ai_chat",
#   "display_name": {
#       "zh": "AI 相互对话",
#       "en": "AI-to-AI Chat"
#   },
#   "description": {
#     "zh": "调用AI模型API实现AI之间智能对话互动。",
#     "en": "Call an AI model API to enable interactive conversations between AIs."
#   },
#   "env": ["AI_API_BASE_URL", "AI_API_KEY", "AI_MODEL_NAME"],
#   "category": "Chat",
#   "tools": [{
#     "name": "chat_completion",
#     "description": {
#       "zh": "发送消息给AI模型并获取回复。支持超时保护（默认30秒）。从根源上禁止分点列表输出。",
#       "en": "Send messages to an AI model and get responses. Includes timeout protection (default: 30s). Enforces non-bulleted output from the source."
#     },
#     "parameters": [
#       {"name": "messages", "description": {"zh": "消息数组或字符串", "en": "Message array or a string"}, "type": "any", "required": true},
#       {"name": "system_prompt", "description": {"zh": "系统提示词（会自动追加禁止分点指令）", "en": "System prompt (the system will automatically append non-bulleted instructions)"}, "type": "string", "required": false},
#       {"name": "temperature", "description": {"zh": "温度参数(0.0-2.0)", "en": "Temperature (0.0-2.0)"}, "type": "number", "required": false, "default": 0.7},
#       {"name": "max_tokens", "description": {"zh": "最大生成长度", "en": "Maximum generation length"}, "type": "number", "required": false},
#       {"name": "timeout", "description": {"zh": "超时时间（毫秒）", "en": "Timeout (milliseconds)"}, "type": "number", "required": false, "default": 30000}
#     ]
#   }]
# }

import asyncio
import json
import math
import re


def _is_nan(n):
    try:
        return isinstance(n, float) and math.isnan(n)
    except Exception:
        return False


async def universalHttpRequest(url, method="POST", headers=None, body=None, responseType="json", timeout=30000):
    if headers is None:
        headers = {}

    async def _do_request():
        if OkHttp is None:
            raise Exception("OkHttp 不可用")

        client = OkHttp.newBuilder().connectTimeout(timeout).readTimeout(timeout).writeTimeout(timeout).build()

        requestBuilder = client.newRequest().url(url).method(method.upper())

        if headers and len(headers) > 0:
            requestBuilder.headers(headers)

        upperMethod = method.upper()
        if body is not None and upperMethod not in ("GET", "HEAD"):
            if isinstance(body, str):
                requestBuilder.body(body, "text")
            else:
                requestBuilder.body(body, "json")

        response = await requestBuilder.build().execute()
        resultBody = json.loads(response.content) if responseType == "json" else response.content
        return {
            "status": response.statusCode,
            "statusText": getattr(response, "statusMessage", "") or "",
            "headers": getattr(response, "headers", None),
            "body": resultBody,
        }

    try:
        return await asyncio.wait_for(_do_request(), timeout=timeout / 1000)
    except asyncio.TimeoutError:
        raise Exception(f"请求超时：{timeout}ms")


def cleanText(text):
    if not text or not isinstance(text, str):
        return str(text if text is not None else "")

    cleaned = text

    # 处理转义与实体
    cleaned = re.sub(r'\|["\\]?n', '\n', cleaned)

    escape_map = {"n": "\n", "r": "\r", "t": "\t", '"': '"', "'": "'", "&": "&"}

    def _escape_repl(m):
        c = m.group(1)
        return escape_map.get(c, m.group(0))

    cleaned = re.sub(r'\\\\([\\nrt"\'&])', _escape_repl, cleaned)
    cleaned = re.sub(r'\\u([0-9A-Fa-f]{4})', lambda m: chr(int(m.group(1), 16)), cleaned)

    # 一次性替换HTML实体
    entities = {"quot": '"', "amp": "&", "lt": "<", "gt": ">", "nbsp": " ", "#39": "'", "apos": "'"}

    def _entity_repl(m):
        e = m.group(1)
        return entities.get(e, m.group(0))

    cleaned = re.sub(r"&(\w+|#\d+);", _entity_repl, cleaned)

    # 清理代码块
    cleaned = re.sub(r'```[\w-]*\s*\n([\s\S]*?)```', r'\1', cleaned)
    cleaned = cleaned.replace('```', '')
    cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)

    # 格式化空白与分点
    cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned)
    lines = cleaned.split('\n')
    lines = [re.sub(r'^[\s\uFEFF\xA0\u3000\u200B-\u200D]+', '', l) for l in lines]
    cleaned = '\n'.join(lines)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
    cleaned = re.sub(r'^\s*[-•●]\s+|^\s*\d+\.\s+|^\s*\d+\)\s+|^\s*\([a-zA-Z]\)\s+', '', cleaned, flags=re.MULTILINE)

    return cleaned or text


def getConfig(varName, defaultValue=None):
    try:
        value = getEnv(varName)
        if not value or value == f"YOUR_{varName}":
            if defaultValue is not None:
                return defaultValue
            raise Exception(f"{varName} 未配置")
        return value.strip()
    except Exception:
        if defaultValue is not None:
            return defaultValue
        raise Exception(f"{varName} 未配置")


def getFullConfig():
    try:
        return {
            "apiBaseUrl": getConfig("AI_API_BASE_URL", ""),
            "apiKey": getConfig("AI_API_KEY", ""),
            "modelName": getConfig("AI_MODEL_NAME", ""),
            "timeout": 30000
        }
    except Exception:
        return {"apiBaseUrl": "", "apiKey": "", "modelName": "", "timeout": 30000}


def joinUrl(baseUrl, path):
    normalizedBase = baseUrl if baseUrl.endswith("/") else f"{baseUrl}/"
    normalizedPath = path[1:] if path.startswith("/") else path
    return f"{normalizedBase}{normalizedPath}"


async def tryEndpoints(baseUrl, payload, config, timeout):
    if "chat/completions" in baseUrl:
        return await universalHttpRequest(
            baseUrl,
            "POST",
            {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config['apiKey']}"
            },
            payload,
            "json",
            timeout
        )

    endpoints = ["v1/chat/completions", "chat/completions"]
    lastError = None

    for endpoint in endpoints:
        try:
            url = joinUrl(baseUrl, endpoint)
            response = await universalHttpRequest(
                url,
                "POST",
                {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {config['apiKey']}"
                },
                payload,
                "json",
                timeout
            )
            if response["status"] == 200:
                return response
            lastError = Exception(f"端点 {endpoint} 返回 {response['status']}")
        except Exception as error:
            lastError = error

    raise lastError or Exception("所有端点尝试失败")


async def chat_completion_logic(rawInput, timeout):
    if rawInput is None:
        raise Exception("参数错误: 输入参数不能为空")

    internalParams = {
        "messages": [],
        "system_prompt": None,
        "temperature": 0.7,
        "max_tokens": None,
        "functions": None,
    }

    # 处理输入参数
    if isinstance(rawInput, str):
        internalParams["messages"] = [{"role": "user", "content": rawInput}]
    elif isinstance(rawInput, dict):
        hasMessageField = "message" in rawInput
        hasMessagesField = "messages" in rawInput

        if hasMessagesField:
            messagesValue = rawInput.get("messages")
            if isinstance(messagesValue, list):
                internalParams["messages"] = messagesValue
            elif isinstance(messagesValue, str):
                internalParams["messages"] = [{"role": "user", "content": messagesValue}]
            else:
                raise Exception("'messages' 必须是数组或字符串")
        elif hasMessageField:
            messageValue = rawInput.get("message")
            if not isinstance(messageValue, str):
                raise Exception("'message' 必须是字符串")
            internalParams["messages"] = [{"role": "user", "content": messageValue}]
        else:
            raise Exception("对象必须包含 'message' 或 'messages' 字段")

        internalParams["system_prompt"] = str(rawInput["system_prompt"]) if rawInput.get("system_prompt") else None
        if rawInput.get("temperature") is not None:
            internalParams["temperature"] = float(rawInput["temperature"])
        if _is_nan(internalParams["temperature"]):
            internalParams["temperature"] = 0.7

        if rawInput.get("max_tokens") is not None:
            internalParams["max_tokens"] = float(rawInput["max_tokens"])
        if internalParams["max_tokens"] is not None and _is_nan(internalParams["max_tokens"]):
            internalParams["max_tokens"] = None

        internalParams["functions"] = rawInput.get("functions") if isinstance(rawInput.get("functions"), list) else None
    else:
        raise Exception(f"不支持的参数类型 '{type(rawInput).__name__}'")

    # 验证messages
    if not isinstance(internalParams["messages"], list) or len(internalParams["messages"]) == 0:
        raise Exception("messages必须是有效数组且不为空")

    for idx, msg in enumerate(internalParams["messages"]):
        if not msg or not isinstance(msg, dict) or not msg.get("role") or not isinstance(msg.get("content"), str):
            raise Exception(f"消息 #{idx} 格式无效")

    # 获取配置
    config = getFullConfig()
    if not config["apiBaseUrl"] or not config["apiKey"]:
        raise Exception("AI_API_BASE_URL 和 AI_API_KEY 必须配置")

    # 构建消息数组
    antiListInstruction = "【重要指令】你必须以连续段落的方式回答，严禁使用任何分点、列表、编号或项目符号格式。"
    finalMessages = [
        {
            "role": "system",
            "content": (internalParams["system_prompt"] + "\n\n" + antiListInstruction) if internalParams["system_prompt"] else antiListInstruction
        }
    ] + internalParams["messages"]

    # 构建请求
    payload = {
        "model": str(config["modelName"] or "gpt-3.5-turbo"),
        "messages": finalMessages,
        "temperature": float(internalParams["temperature"])
    }

    if internalParams["max_tokens"] is not None and not _is_nan(internalParams["max_tokens"]):
        payload["max_tokens"] = float(internalParams["max_tokens"])
    if internalParams["functions"]:
        payload["functions"] = internalParams["functions"]

    payload = {k: v for k, v in payload.items() if v is not None}

    # 发送请求
    response = None
    try:
        response = await tryEndpoints(config["apiBaseUrl"], payload, config, timeout)
    except Exception:
        response = await universalHttpRequest(
            config["apiBaseUrl"],
            "POST",
            {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config['apiKey']}"
            },
            payload,
            "json",
            timeout
        )

    if response["status"] != 200:
        errorMsg = f"API请求失败: {response['status']}"
        try:
            errorData = json.loads(response["body"]) if isinstance(response["body"], str) else response["body"]
            err_msg = errorData.get("error", {}).get("message") if isinstance(errorData, dict) else None
            errorMsg += f" - {err_msg or json.dumps(errorData, ensure_ascii=False)}"
        except Exception:
            errorMsg += f" - {response['statusText']}"
        raise Exception(errorMsg)

    result = json.loads(response["body"]) if isinstance(response["body"], str) else response["body"]
    choices = result.get("choices") if isinstance(result, dict) else None
    if not choices or len(choices) == 0:
        raise Exception("API返回格式异常")

    choice = choices[0]
    reply = {
        "message": choice.get("message"),
        "finish_reason": choice.get("finish_reason"),
        "usage": result.get("usage") or None,
        "model": result.get("model") or config["modelName"],
        "id": result.get("id"),
        "created": result.get("created")
    }

    message = choice.get("message") or {}
    if message.get("function_call"):
        reply["is_function_call"] = True
        reply["function_name"] = message["function_call"].get("name")
        reply["function_arguments"] = json.loads(message["function_call"].get("arguments") or "{}")

    return reply


async def chat_completion_impl(params):
    if isinstance(params, dict):
        normalizedParams = params
    else:
        normalizedParams = {"messages": str(params)}

    timeout = normalizedParams.get("timeout") or 30000

    try:
        result = await asyncio.wait_for(chat_completion_logic(normalizedParams, timeout), timeout=timeout / 1000)
    except asyncio.TimeoutError:
        raise Exception(f"操作超时：{timeout}ms")

    rawReply = (result.get("message") or {}).get("content")
    cleanedReply = cleanText(rawReply)

    return {
        "success": True,
        "message": "AI回复获取成功！",
        "data": result,
        "reply": cleanedReply,
        "raw_reply": rawReply,
        "usage": result.get("usage"),
        "anti_list_applied": True
    }


async def wrapToolExecution(func, params=None):
    try:
        result = await func(params or {})
        complete(result)
    except Exception as error:
        console.error(f"Tool {func.__name__} failed unexpectedly", error)
        complete({
            "success": False,
            "message": f"AI对话失败: {str(error.message if hasattr(error, 'message') else error)}",
            "error_stack": getattr(error, "__traceback__", None)
        })


async def chat_completion(params=None):
    return await wrapToolExecution(chat_completion_impl, params)


async def main(params=None):
    if params is None:
        params = {}
    config = getFullConfig()
    if not config["apiBaseUrl"] or not config["apiKey"]:
        return {
            "success": False,
            "message": "AI_API_BASE_URL 和 AI_API_KEY 必须配置",
            "config": config
        }

    return await chat_completion_impl({
        "messages": params.get("message") or "Hello! Please respond in a continuous paragraph without any list or bullet points.",
        "temperature": params.get("temperature") if params.get("temperature") is not None else 0.2,
        "timeout": params.get("timeout") if params.get("timeout") is not None else 15000,
    })


async def _test_connection_impl():
    return await chat_completion_impl({
        "messages": "Hello! Please respond in a continuous paragraph without any list or bullet points.",
        "temperature": 0.1,
        "timeout": 10000
    })


async def _exported_test_connection(params=None):
    if params is None:
        params = {}
    await wrapToolExecution(_test_connection_impl, {})


async def _exported_main(params=None):
    await wrapToolExecution(main, params)


exports.chat_completion = chat_completion
exports.single_message = chat_completion
exports.test_connection = _exported_test_connection
exports.getConfig = getFullConfig
exports.main = _exported_main
