# METADATA
# {
#   "name": "qwen_draw",
#   "display_name": {
#       "zh": "Qwen 绘图",
#       "en": "Qwen Draw"
#   },
#   "description": {
#     "zh": "使用阿里云百炼/DashScope 文生图接口（通义万相/通义千问图像）根据提示词画图（异步任务轮询），将图片保存到本地 /sdcard/Download/Operit/plugins/draw/qwen_draw/draws/ 目录，并返回 Markdown 图片提示。",
#     "en": "Generate images via Alibaba Cloud Model Studio (DashScope) text-to-image API (async task polling), save to /sdcard/Download/Operit/plugins/draw/qwen_draw/draws/, and return a Markdown image reference."
#   },
#   "env": [
#     { "name": "DASHSCOPE_API_KEY", "description": { "zh": "DashScope API Key（必填）", "en": "DashScope API key (required)" }, "required": true },
#     { "name": "DASHSCOPE_API_BASE_URL", "description": { "zh": "DashScope API Base URL（可选，不填则默认 https://dashscope.aliyuncs.com；国际站可用 https://dashscope-intl.aliyuncs.com）", "en": "DashScope API base URL (optional; defaults to https://dashscope.aliyuncs.com; intl: https://dashscope-intl.aliyuncs.com)" }, "required": false },
#     { "name": "QWEN_IMAGE_MODEL", "description": { "zh": "默认文生图模型（可选；当 draw_image 未传 model 时使用，例如 qwen-image-plus 或 wan2.2-t2i-flash）", "en": "Default image model (optional; used when draw_image doesn't pass model), e.g. qwen-image-plus or wan2.2-t2i-flash" }, "required": false }
#   ],
#   "category": "Draw",
#   "tools": [
#     {
#       "name": "draw_image",
#       "description": { "zh": "根据提示词调用 DashScope 文生图接口生成图片，保存到本地并返回 Markdown 图片提示。", "en": "Generate an image via DashScope text-to-image API using a prompt, save it locally, and return a Markdown image reference." },
#       "parameters": [
#         { "name": "prompt", "description": { "zh": "绘图提示词（英文或中文皆可）", "en": "Prompt for image generation (Chinese or English)" }, "type": "string", "required": true },
#         { "name": "model", "description": { "zh": "模型名称（可选；不传则使用环境变量 QWEN_IMAGE_MODEL，再不行使用默认值）", "en": "Model name (optional; falls back to env QWEN_IMAGE_MODEL, then default)" }, "type": "string", "required": false },
#         { "name": "size", "description": { "zh": "输出图像分辨率，如 '1664*928' 或 '1024x1024'（可选）", "en": "Output image resolution, e.g. '1664*928' or '1024x1024' (optional)" }, "type": "string", "required": false },
#         { "name": "n", "description": { "zh": "生成图片数量（可选，默认 1）", "en": "Number of images (optional; default 1)" }, "type": "number", "required": false },
#         { "name": "negative_prompt", "description": { "zh": "负面提示词（可选）", "en": "Negative prompt (optional)" }, "type": "string", "required": false },
#         { "name": "prompt_extend", "description": { "zh": "是否开启 prompt 智能改写（可选，默认 true）", "en": "Enable prompt extension (optional; default true)" }, "type": "boolean", "required": false },
#         { "name": "watermark", "description": { "zh": "是否加水印（可选，默认 false）", "en": "Enable watermark (optional; default false)" }, "type": "boolean", "required": false },
#         { "name": "file_name", "description": { "zh": "自定义保存到本地的文件名（不含路径和扩展名）", "en": "Custom output file name (without path or extension)" }, "type": "string", "required": false },
#         { "name": "api_base_url", "description": { "zh": "DashScope API Base URL（不传则取环境变量 DASHSCOPE_API_BASE_URL 或默认 https://dashscope.aliyuncs.com ）", "en": "DashScope API base URL (optional; falls back to env DASHSCOPE_API_BASE_URL or https://dashscope.aliyuncs.com)" }, "type": "string", "required": false },
#         { "name": "poll_interval_ms", "description": { "zh": "轮询间隔（毫秒），默认 2000", "en": "Polling interval (milliseconds), default 2000" }, "type": "number", "required": false },
#         { "name": "max_wait_time_ms", "description": { "zh": "最长等待时间（毫秒），默认 10 分钟", "en": "Max wait time (milliseconds), default 10 minutes" }, "type": "number", "required": false }
#       ]
#     }
#   ]
# }

import json
import math
import re
import time

HTTP_TIMEOUT_MS = 600000
client = OkHttp.newBuilder().connectTimeout(HTTP_TIMEOUT_MS).readTimeout(HTTP_TIMEOUT_MS).writeTimeout(HTTP_TIMEOUT_MS).build()

DEFAULT_API_BASE_URL = "https://dashscope.aliyuncs.com"
DEFAULT_MODEL = "qwen-image-plus"

DRAW_ROOT_DIR = getPluginConfigDir("draw")
STORAGE_DIR = f"{DRAW_ROOT_DIR}/qwen_draw"
DRAWS_DIR = f"{STORAGE_DIR}/draws"

POLL_INTERVAL_MS = 2000
MAX_WAIT_TIME_MS = 600000


def _is_finite(n):
    return isinstance(n, (int, float)) and not isinstance(n, bool) and math.isfinite(n)


def isRecord(value):
    return isinstance(value, dict)


def getErrorMessage(error):
    if isinstance(error, Exception):
        return str(error)
    return str(error)


def getErrorStack(error):
    if isinstance(error, Exception):
        import traceback
        return traceback.format_exc()
    return None


def normalizePositiveInt(value, fallback):
    if value is None:
        return fallback
    n = value if isinstance(value, (int, float)) else int(str(value), 10)
    if not _is_finite(n) or n <= 0:
        return fallback
    return int(n)


def joinUrl(baseUrl, path):
    normalizedBase = baseUrl if baseUrl.endswith("/") else f"{baseUrl}/"
    normalizedPath = path[1:] if path.startswith("/") else path
    return f"{normalizedBase}{normalizedPath}"


def getApiKey():
    apiKey = getEnv("DASHSCOPE_API_KEY")
    if not apiKey:
        raise Exception("DASHSCOPE_API_KEY 未配置，请在环境变量中设置 DashScope 的 API Key。")
    return apiKey


def getApiBaseUrl(customBaseUrl=None):
    fromParam = str(customBaseUrl or "").strip()
    if fromParam:
        return fromParam

    fromEnv = str(getEnv("DASHSCOPE_API_BASE_URL") or "").strip()
    if fromEnv:
        return fromEnv

    return DEFAULT_API_BASE_URL


def getTextToImageEndpoint(baseUrl):
    trimmed = baseUrl.strip()
    if not trimmed:
        return joinUrl(DEFAULT_API_BASE_URL, "api/v1/services/aigc/text2image/image-synthesis")

    if "/api/v1/services/aigc/text2image/image-synthesis" in trimmed:
        return trimmed

    if trimmed.endswith("/api/v1"):
        return joinUrl(trimmed, "services/aigc/text2image/image-synthesis")
    if trimmed.endswith("/api/v1/"):
        return joinUrl(trimmed, "services/aigc/text2image/image-synthesis")

    return joinUrl(trimmed, "api/v1/services/aigc/text2image/image-synthesis")


def getTaskEndpoint(baseUrl, taskId):
    trimmed = baseUrl.strip()
    safeBase = trimmed or DEFAULT_API_BASE_URL
    if "/api/v1/tasks/" in safeBase:
        idx = safeBase.index("/api/v1/tasks/")
        return safeBase[:idx] + f"/api/v1/tasks/{taskId}"
    if safeBase.endswith("/api/v1"):
        return joinUrl(safeBase, f"tasks/{taskId}")
    if safeBase.endswith("/api/v1/"):
        return joinUrl(safeBase, f"tasks/{taskId}")
    return joinUrl(safeBase, f"api/v1/tasks/{taskId}")


def sanitizeFileName(name):
    safe = re.sub(r'[\\/:*?"<>|]', "_", str(name)).strip()
    if not safe:
        return f"qwen_draw_{int(time.time() * 1000)}"
    return safe[:80]


def buildFileName(prompt, customName=None):
    if customName and str(customName).strip():
        return sanitizeFileName(customName)
    shortPrompt = f"{prompt[:40]}..." if len(prompt) > 40 else prompt
    base = sanitizeFileName(shortPrompt or "image")
    timestamp = int(time.time() * 1000)
    return f"{base}_{timestamp}"


def normalizeSize(size=None):
    raw = str(size or "").strip()
    if not raw:
        return None

    cleaned = raw.replace("×", "*").replace("x", "*").replace("X", "*")
    cleaned = re.sub(r"\s+", "", cleaned)
    if not re.match(r"^\d+\*\d+$", cleaned):
        return None
    return cleaned


def guessExtensionFromUrl(url):
    match = re.search(r"\.(png|jpg|jpeg|webp|gif)(?:\?|#|$)", url, re.IGNORECASE)
    if match and match.group(1):
        return match.group(1).lower()
    return "png"


async def ensureDirectories():
    dirs = [DRAW_ROOT_DIR, STORAGE_DIR, DRAWS_DIR]
    for dir_ in dirs:
        try:
            result = await Tools.Files.mkdir(dir_)
            if not result.get("successful"):
                console.warn(f"创建目录失败(可能已存在): {dir_} -> {result.get('details')}")
        except Exception as e:
            console.warn(f"创建目录异常: {dir_} -> {getErrorMessage(e)}")


async def createTask(params):
    apiKey = getApiKey()
    apiBaseUrl = getApiBaseUrl(params.get("api_base_url"))
    endpoint = getTextToImageEndpoint(apiBaseUrl)

    modelFromParam = str(params.get("model") or "").strip()
    modelFromEnv = str(getEnv("QWEN_IMAGE_MODEL") or "").strip()
    effectiveModel = modelFromParam or modelFromEnv or DEFAULT_MODEL

    body = {
        "model": effectiveModel,
        "input": {
            "prompt": params["prompt"]
        },
        "parameters": {
            "n": int(params["n"]) if isinstance(params.get("n"), (int, float)) and _is_finite(params["n"]) and params["n"] > 0 else 1,
            "prompt_extend": True if params.get("prompt_extend") is None else bool(params.get("prompt_extend")),
            "watermark": False if params.get("watermark") is None else bool(params.get("watermark"))
        }
    }

    normalizedSize = normalizeSize(params.get("size"))
    if normalizedSize:
        body["parameters"]["size"] = normalizedSize

    negativePrompt = str(params.get("negative_prompt") or "").strip()
    if negativePrompt:
        body["parameters"]["negative_prompt"] = negativePrompt

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {apiKey}",
        "X-DashScope-Async": "enable"
    }

    request = client.newRequest().url(endpoint).method("POST").headers(headers).body(json.dumps(body), "json")

    response = await request.build().execute()

    if not response.isSuccessful():
        raise Exception(f"DashScope 文生图创建任务失败: {response.statusCode} - {response.content}")

    try:
        parsed = json.loads(response.content)
    except Exception as e:
        raise Exception(f"解析 DashScope 创建任务响应失败: {getErrorMessage(e)}")

    output = parsed.get("output") if isRecord(parsed) and isRecord(parsed.get("output")) else None
    taskId = output.get("task_id") if (output and isinstance(output.get("task_id"), str)) else ""
    if not taskId:
        raise Exception(f"DashScope 创建任务响应中未找到 output.task_id: {response.content}")

    return {"task_id": taskId, "effective_model": effectiveModel}


async def pollTask(params):
    apiKey = getApiKey()
    apiBaseUrl = getApiBaseUrl(params.get("api_base_url"))

    pollIntervalMs = normalizePositiveInt(params.get("poll_interval_ms"), POLL_INTERVAL_MS)
    maxWaitTimeMs = normalizePositiveInt(params.get("max_wait_time_ms"), MAX_WAIT_TIME_MS)

    startTime = int(time.time() * 1000)
    attempts = 0

    while int(time.time() * 1000) - startTime < maxWaitTimeMs:
        attempts += 1

        endpoint = getTaskEndpoint(apiBaseUrl, params["task_id"])
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {apiKey}"
        }

        request = client.newRequest().url(endpoint).method("GET").headers(headers)

        response = await request.build().execute()

        if not response.isSuccessful():
            raise Exception(f"DashScope 查询任务失败: {response.statusCode} - {response.content}")

        try:
            parsed = json.loads(response.content)
        except Exception as e:
            raise Exception(f"解析 DashScope 查询任务响应失败: {getErrorMessage(e)}")

        output = parsed.get("output") if isRecord(parsed) and isRecord(parsed.get("output")) else None
        taskStatus = str(output.get("task_status")) if (output and isinstance(output.get("task_status"), str)) else ""

        if taskStatus == "SUCCEEDED":
            results = output.get("results") if output else None
            first = results[0] if (isinstance(results, list) and len(results) > 0) else None
            url = first.get("url") if isRecord(first) else None
            if not ((isinstance(url, str) or isinstance(url, (int, float))) and str(url).strip()):
                raise Exception(f"任务已完成但未找到图片 URL: {response.content}")
            return {"image_url": str(url), "task_status": taskStatus}

        if taskStatus == "FAILED":
            raise Exception(f"任务失败: {response.content}")

        if attempts % 5 == 0:
            console.log(f"任务状态: {taskStatus or 'UNKNOWN'}，继续等待...")

        await Tools.System.sleep(pollIntervalMs)

    raise Exception(f"任务超时: 等待超过{math.ceil(maxWaitTimeMs / 60000)}分钟仍未完成")


async def draw_image(params):
    if not params or not params.get("prompt") or not str(params["prompt"]).strip():
        raise Exception("参数 prompt 不能为空。")

    prompt = str(params["prompt"]).strip()

    await ensureDirectories()

    createResult = await createTask({
        "prompt": prompt,
        "model": params.get("model"),
        "size": params.get("size"),
        "n": params.get("n"),
        "negative_prompt": params.get("negative_prompt"),
        "prompt_extend": params.get("prompt_extend"),
        "watermark": params.get("watermark"),
        "api_base_url": params.get("api_base_url")
    })

    pollResult = await pollTask({
        "task_id": createResult["task_id"],
        "api_base_url": params.get("api_base_url"),
        "poll_interval_ms": params.get("poll_interval_ms"),
        "max_wait_time_ms": params.get("max_wait_time_ms")
    })

    ext = guessExtensionFromUrl(pollResult["image_url"])
    baseName = buildFileName(prompt, params.get("file_name"))
    filePath = f"{DRAWS_DIR}/{baseName}.{ext}"

    downloadResult = await Tools.Files.download(pollResult["image_url"], filePath)
    if not downloadResult.get("successful"):
        raise Exception(f"下载图片失败: {downloadResult.get('details')}")

    fileUri = f"file://{filePath}"
    markdown = f"![AI生成的图片]({fileUri})"

    hintLines = []
    hintLines.append(f"图片已生成并保存在本地 {DRAWS_DIR}。")
    hintLines.append(f"本地路径: {filePath}")
    hintLines.append("")
    hintLines.append("在后续回答中，请直接输出下面这一行 Markdown 来展示这张图片：")
    hintLines.append("")
    hintLines.append(markdown)

    return {
        "file_path": filePath,
        "file_uri": fileUri,
        "markdown": markdown,
        "prompt": prompt,
        "model": createResult["effective_model"],
        "task_id": createResult["task_id"],
        "task_status": pollResult["task_status"],
        "image_url": pollResult["image_url"],
        "hint": "\n".join(hintLines)
    }


async def draw_image_wrapper(params):
    try:
        result = await draw_image(params)
        complete({
            "success": True,
            "message": f"图片生成成功，已保存到 {DRAWS_DIR}，并返回 Markdown 图片提示。",
            "data": result
        })
    except Exception as error:
        console.error("draw_image 执行失败:", error)
        complete({
            "success": False,
            "message": f"图片生成失败: {getErrorMessage(error)}",
            "error_stack": getErrorStack(error)
        })


exports.draw_image = draw_image_wrapper
