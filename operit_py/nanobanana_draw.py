# METADATA
# {
#   "name": "nanobanana_draw",
#   "display_name": {"zh": "Nanobanana 绘图", "en": "Nanobanana Draw"},
#   "description": {"zh": "使用 Nano Banana API (基于Grsai的api服务/https://grsai.com/) 根据提示词画图，支持文生图和图生图（可传入参考图片URL或本地图片路径；本地图片会先上传到图床以获得公网URL），将图片保存到本地 /sdcard/Download/Operit/plugins/draw/nanobanana_draw/draws/ 目录，并返回 Markdown 图片提示。", "en": "Generate images using the Nano Banana API (via Grsai service / https://grsai.com/). Supports text-to-image and image-to-image (you can provide reference image URLs or local image paths; local images will be uploaded first to get public URLs). Saves images to /sdcard/Download/Operit/plugins/draw/nanobanana_draw/draws/ and returns a Markdown image reference."},
#   "env": ["NANOBANANA_API_KEY", "NANOBANANA_API_BASE_URL", "BEEIMG_API_KEY"],
#   "category": "Draw",
#   "tools": [
#     {"name": "draw_image", "description": {"zh": "根据提示词调用 Nano Banana API 生成图片（支持文生图和图生图），保存到本地并返回 Markdown 图片提示。", "en": "Generate an image via the Nano Banana API using a prompt (supports text-to-image and image-to-image), save locally, and return a Markdown image reference."}, "parameters": [
#       {"name": "prompt", "description": {"zh": "绘图提示词（英文或中文皆可）", "en": "Image prompt (Chinese or English)"}, "type": "string", "required": True},
#       {"name": "model", "description": {"zh": "Nano Banana 模型名称（优先级最高）。可填 nano-banana-pro（约1800积分）或 nano-banana（约400积分）", "en": "Nano Banana model name (highest priority). e.g. nano-banana-pro (~1800 credits) or nano-banana (~400 credits)."}, "type": "string", "required": False},
#       {"name": "model_variant", "description": {"zh": "模型档位（二选一，可选）：pro（约1800积分）或 nano（约400积分）。未传时默认 pro", "en": "Model tier (optional): pro (~1800 credits) or nano (~400 credits). Defaults to pro."}, "type": "string", "required": False},
#       {"name": "aspect_ratio", "description": {"zh": "输出图像比例，如 '1:1', '16:9', 'auto' 等，可选", "en": "Output aspect ratio, e.g. '1:1', '16:9', 'auto' (optional)"}, "type": "string", "required": False},
#       {"name": "image_size", "description": {"zh": "输出图像大小，仅 nano-banana-pro 支持，如 '1K', '2K', '4K'，可选", "en": "Output image size (only supported by nano-banana-pro), e.g. '1K', '2K', '4K' (optional)"}, "type": "string", "required": False},
#       {"name": "image_urls", "description": {"zh": "参考图URL数组（图生图），支持格式：字符串数组['https://...'] 或 JSON字符串'[\"https://...\"]' 或逗号分隔'url1,url2'，可选", "en": "Reference image URL list for img2img. Accepts: string array ['https://...'], or JSON string '[\"https://...\"]', or comma-separated 'url1,url2' (optional)."}, "type": "array", "required": False},
#       {"name": "image_paths", "description": {"zh": "参考图本地路径数组（图生图，会先上传图床再进行生成），支持格式：字符串数组['/sdcard/...'] 或 JSON字符串 或 逗号分隔，可选", "en": "Reference local image path list for img2img (will be uploaded first). Accepts: string array ['/sdcard/...'], or JSON string, or comma-separated list (optional)."}, "type": "array", "required": False},
#       {"name": "file_name", "description": {"zh": "自定义保存到本地的文件名（不含路径和扩展名）", "en": "Custom output file name (without path or extension)"}, "type": "string", "required": False},
#       {"name": "poll_interval_ms", "description": {"zh": "轮询间隔（毫秒），默认 5000", "en": "Polling interval (milliseconds), default 5000"}, "type": "number", "required": False},
#       {"name": "max_wait_time_ms", "description": {"zh": "最长等待时间（毫秒）。默认 10 分钟", "en": "Max wait time (milliseconds). Default 10 minutes."}, "type": "number", "required": False}
#     ]}
#   ]
# }

import json
import re
import time
import math
from urllib.parse import quote, unquote

Error = Exception

HTTP_TIMEOUT_MS = 600000
client = (
    OkHttp.newBuilder()
    .connectTimeout(HTTP_TIMEOUT_MS)
    .readTimeout(HTTP_TIMEOUT_MS)
    .writeTimeout(HTTP_TIMEOUT_MS)
    .build()
)

BEEIMG_UPLOAD_ENDPOINT = "https://beeimg.com/api/upload/file/json/"

# API配置
DEFAULT_API_BASE_URL = "https://grsai.dakka.com.cn"
DRAW_API_PATH = "v1/draw/nano-banana"
RESULT_API_PATH = "v1/draw/result"
MODEL_PRO = "nano-banana-pro"
MODEL_NANO = "nano-banana"
DEFAULT_MODEL = MODEL_PRO
# Android 实际路径为 /sdcard/Download，对应系统中文名"下载" (Android-only)
DRAW_ROOT_DIR = getPluginConfigDir("draw")
STORAGE_DIR = f"{DRAW_ROOT_DIR}/nanobanana_draw"
DRAWS_DIR = f"{STORAGE_DIR}/draws"

# 轮询配置
POLL_INTERVAL = 5000  # 每5秒查询一次
MAX_WAIT_TIME = 600000  # 最多等待10分钟


def isRecord(value):
    return isinstance(value, dict)


def getErrorMessage(error):
    if isinstance(error, Exception):
        return str(error)
    return str(error)


def getErrorStack(error):
    if isinstance(error, Exception):
        import traceback
        return "".join(traceback.format_exception(type(error), error, error.__traceback__))
    return None


def resolveModel(model=None, modelVariant=None):
    if model and model.strip():
        return model.strip()

    if not modelVariant or not modelVariant.strip():
        return DEFAULT_MODEL

    normalizedVariant = modelVariant.strip().lower()
    if normalizedVariant == "pro":
        return MODEL_PRO
    if normalizedVariant == "nano":
        return MODEL_NANO

    raise Error("参数 model_variant 仅支持 'pro' 或 'nano'。")


def normalizePositiveInt(value, fallback):
    if value is None:
        return fallback
    n = value if isinstance(value, (int, float)) else int(str(value), 10)
    if not math.isfinite(n) or n <= 0:
        return fallback
    return int(n)


def getApiKey():
    apiKey = getEnv("NANOBANANA_API_KEY")
    if not apiKey:
        raise Error("NANOBANANA_API_KEY 未配置，请在环境变量中设置 Nano Banana 的 API Key。")
    return apiKey


def getBeeimgApiKey():
    return getEnv("BEEIMG_API_KEY") or ""


def joinUrl(baseUrl, path):
    normalizedBase = baseUrl if baseUrl.endswith("/") else f"{baseUrl}/"
    normalizedPath = path[1:] if path.startswith("/") else path
    return f"{normalizedBase}{normalizedPath}"


def getApiBaseUrl():
    fromEnv = str(getEnv("NANOBANANA_API_BASE_URL") or "").strip()
    if fromEnv:
        return fromEnv
    return DEFAULT_API_BASE_URL


def getDrawEndpoint(baseUrl):
    trimmed = baseUrl.strip()
    if not trimmed:
        return joinUrl(DEFAULT_API_BASE_URL, DRAW_API_PATH)
    if "/v1/draw/nano-banana" in trimmed:
        return trimmed
    if trimmed.endswith("/v1"):
        return joinUrl(trimmed, "draw/nano-banana")
    if trimmed.endswith("/v1/"):
        return joinUrl(trimmed, "draw/nano-banana")
    return joinUrl(trimmed, DRAW_API_PATH)


def getResultEndpoint(baseUrl):
    trimmed = baseUrl.strip()
    if not trimmed:
        return joinUrl(DEFAULT_API_BASE_URL, RESULT_API_PATH)
    if "/v1/draw/result" in trimmed:
        return trimmed
    if "/v1/draw/nano-banana" in trimmed:
        return trimmed.replace("/v1/draw/nano-banana", "/v1/draw/result")
    if trimmed.endswith("/v1"):
        return joinUrl(trimmed, "draw/result")
    if trimmed.endswith("/v1/"):
        return joinUrl(trimmed, "draw/result")
    return joinUrl(trimmed, RESULT_API_PATH)


def guessMimeTypeFromPath(filePath):
    lower = filePath.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".gif"):
        return "image/gif"
    return "application/octet-stream"


def safeJsonParseLoose(text):
    trimmed = str(text or "").strip()
    if not trimmed:
        return None
    try:
        return json.loads(trimmed)
    except Exception as e:
        start = trimmed.find("{")
        end = trimmed.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(trimmed[start:end + 1])
        raise e


def isApiSuccessResponse(parsed):
    code = parsed.get("code")
    return code is None or code == 0 or code == "0"


def extractTaskPayload(parsed):
    if not isRecord(parsed):
        return None
    if isRecord(parsed.get("data")):
        return parsed.get("data")
    return parsed


def extractMessage(parsed, fallback):
    payload = extractTaskPayload(parsed)
    candidates = [
        parsed.get("msg"),
        parsed.get("message"),
        payload.get("failure_reason") if payload else None,
        payload.get("error") if payload else None,
        payload.get("msg") if payload else None,
        payload.get("message") if payload else None,
    ]

    for candidate in candidates:
        if (isinstance(candidate, str) or isinstance(candidate, (int, float))) and str(candidate).strip():
            return str(candidate).strip()

    return fallback


def normalizeStatus(status):
    return status.strip().lower() if isinstance(status, str) else ""


def normalizeProgress(progress):
    normalized = progress if isinstance(progress, (int, float)) else float(str(progress))
    return normalized if math.isfinite(normalized) else 0


def isSuccessStatus(status):
    return status in ("succeeded", "success", "completed", "done")


def isFailureStatus(status):
    return status in ("failed", "error", "canceled", "cancelled")


def extractImageUrlFromPayload(payload):
    directCandidates = [
        payload.get("url"),
        payload.get("image_url"),
        payload.get("imageUrl"),
        payload.get("file_url"),
        payload.get("fileUrl"),
        payload.get("result_url"),
    ]

    for candidate in directCandidates:
        if (isinstance(candidate, str) or isinstance(candidate, (int, float))) and str(candidate).strip():
            return str(candidate).strip()

    results = payload.get("results")
    if not isinstance(results, list) or len(results) == 0:
        return ""

    first = results[0]
    if isRecord(first):
        nestedCandidates = [
            first.get("url"),
            first.get("image_url"),
            first.get("imageUrl"),
            first.get("file_url"),
            first.get("fileUrl"),
            first.get("result_url"),
        ]
        for candidate in nestedCandidates:
            if (isinstance(candidate, str) or isinstance(candidate, (int, float))) and str(candidate).strip():
                return str(candidate).strip()
    elif (isinstance(first, str) or isinstance(first, (int, float))) and str(first).strip():
        return str(first).strip()

    return ""


async def uploadImageToBeeimg(filePath):
    exists = await Tools.Files.exists(filePath)
    if not exists.exists:
        raise Error(f"参考图文件不存在: {filePath}")

    apiKey = getBeeimgApiKey()
    if not apiKey:
        raise Error("使用 image_paths 需要配置 BEEIMG_API_KEY（用于把本地图片上传到图床以获得公网URL）。")

    resp = await Tools.Net.uploadFile({
        "url": BEEIMG_UPLOAD_ENDPOINT,
        "method": "POST",
        "form_data": {"apikey": apiKey},
        "files": [
            {
                "field_name": "file",
                "file_path": filePath,
                "content_type": guessMimeTypeFromPath(filePath),
            }
        ],
    })

    if resp.statusCode < 200 or resp.statusCode >= 300:
        raise Error(f"BeeIMG 上传失败: HTTP {resp.statusCode} - {resp.content}")

    parsed = None
    try:
        parsed = safeJsonParseLoose(resp.content)
    except Exception as e:
        raise Error(f"BeeIMG 上传响应解析失败: {getErrorMessage(e)}")

    files = parsed.get("files") if isRecord(parsed) and isRecord(parsed.get("files")) else None
    ok = bool(files) and (files.get("status") == "Success" or files.get("code") == "200" or files.get("code") == 200)
    url = files.get("url") if files else None
    if not ok or (not isinstance(url, str) and not isinstance(url, (int, float))) or not str(url).strip():
        raise Error(f"BeeIMG 上传失败: {resp.content}")
    return str(url)


def sanitizeFileName(name):
    safe = re.sub(r'[\\/:*?"<>|]', "_", name).strip()
    if not safe:
        return f"nano_draw_{int(time.time() * 1000)}"
    return safe[:80]


def buildFileName(prompt, customName=None):
    if customName and customName.strip():
        return sanitizeFileName(customName)
    shortPrompt = f"{prompt[:40]}..." if len(prompt) > 40 else prompt
    base = sanitizeFileName(shortPrompt or "image")
    timestamp = int(time.time() * 1000)
    return f"{base}_{timestamp}"


async def ensureDirectories():
    dirs = [DRAW_ROOT_DIR, STORAGE_DIR, DRAWS_DIR]
    for dir_ in dirs:
        try:
            result = await Tools.Files.mkdir(dir_)
            if not result.successful:
                console.warn(f"创建目录失败(可能已存在): {dir_} -> {result.details}")
        except Exception as e:
            console.warn(f"创建目录异常: {dir_} -> {getErrorMessage(e)}")


async def callNanobananaApi(params):
    apiKey = getApiKey()
    endpoint = getDrawEndpoint(getApiBaseUrl())

    # 构建请求体 - 使用异步模式（webHook: "-1"）
    body = {
        "model": params.get("model"),
        "prompt": params.get("prompt"),
        "webHook": "-1",  # 关键：立即返回任务ID
        "shutProgress": False,
    }

    # 添加可选参数
    if params.get("aspect_ratio") and params.get("aspect_ratio").strip():
        body["aspectRatio"] = params.get("aspect_ratio").strip()

    if params.get("image_size") and params.get("image_size").strip():
        body["imageSize"] = params.get("image_size").strip()

    # 图生图：添加参考图URL数组
    if params.get("image_urls") and isinstance(params.get("image_urls"), list) and len(params.get("image_urls")) > 0:
        body["urls"] = [url for url in params.get("image_urls") if url and url.strip()]

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {apiKey}",
    }

    request = (
        client.newRequest()
        .url(endpoint)
        .method("POST")
        .headers(headers)
        .body(json.dumps(body), "json")
    )

    console.log("步骤1/2: 提交绘图任务...")
    response = await request.build().execute()

    if not response.isSuccessful():
        raise Error(f"Nano Banana API 调用失败: {response.statusCode} - {response.content}")

    parsed = None
    try:
        parsed = json.loads(response.content)
    except Exception as e:
        raise Error(f"解析 Nano Banana 响应失败: {getErrorMessage(e)}")

    if not isRecord(parsed):
        raise Error("API响应不是合法对象，请检查参数是否正确。响应: " + response.content)
    if not isApiSuccessResponse(parsed):
        raise Error(f"Nano Banana API 返回错误: {extractMessage(parsed, response.content)}")

    payload = extractTaskPayload(parsed)
    if not payload or not isinstance(payload.get("id"), str):
        raise Error("API响应中未找到任务ID，请检查参数是否正确。响应: " + json.dumps(parsed))

    taskId = payload.get("id")
    console.log(f"任务提交成功! ID: {taskId}")
    pollIntervalMs = params.get("poll_interval_ms") if params.get("poll_interval_ms") is not None else POLL_INTERVAL
    maxWaitTimeMs = params.get("max_wait_time_ms") if params.get("max_wait_time_ms") is not None else MAX_WAIT_TIME
    console.log(f"步骤2/2: 等待任务完成（轮询中，每{pollIntervalMs / 1000}秒查询一次，最长等待{math.ceil(maxWaitTimeMs / 60000)}分钟）...")

    return taskId


async def pollForResult(taskId, options=None):
    options = options or {}
    apiKey = getApiKey()
    endpoint = getResultEndpoint(getApiBaseUrl())
    pollIntervalMs = normalizePositiveInt(options.get("poll_interval_ms"), POLL_INTERVAL)
    maxWaitTimeMs = normalizePositiveInt(options.get("max_wait_time_ms"), MAX_WAIT_TIME)
    startTime = time.time() * 1000
    attempt = 0

    async def doSleep(ms):
        await Tools.System.sleep(ms)

    while time.time() * 1000 - startTime < maxWaitTimeMs:
        attempt += 1
        console.log(f"第{attempt}次查询任务状态...")

        try:
            request = (
                client.newRequest()
                .url(endpoint)
                .method("POST")
                .headers({
                    "accept": "application/json",
                    "content-type": "application/json",
                    "Authorization": f"Bearer {apiKey}",
                })
                .body(json.dumps({"id": taskId}), "json")
            )

            response = await request.build().execute()

            if not response.isSuccessful():
                console.warn(f"⚠️ 查询请求未成功 (HTTP {response.statusCode}): {response.content}，将重试...")
                await doSleep(pollIntervalMs)
                continue

            parsed = None
            try:
                parsed = json.loads(response.content)
            except Exception:
                console.warn("⚠️ 解析结果响应失败，将重试")
                await doSleep(pollIntervalMs)
                continue

            if not isRecord(parsed):
                console.warn(f"查询响应异常: {json.dumps(parsed)}")
                await doSleep(pollIntervalMs)
                continue

            if parsed.get("code") == -22 or parsed.get("code") == "-22":
                console.log("任务排队/处理中... (等待服务器生成)")
                await doSleep(pollIntervalMs)
                continue

            if not isApiSuccessResponse(parsed):
                console.warn(f"⚠️ API 返回异常状态，将重试: {json.dumps(parsed)}")
                await doSleep(pollIntervalMs)
                continue

            data = extractTaskPayload(parsed)
            if not data:
                console.warn(f"查询响应异常 (无有效数据): {json.dumps(parsed)}")
                await doSleep(pollIntervalMs)
                continue

            progress = normalizeProgress(data.get("progress"))
            status = normalizeStatus(data.get("status"))
            imageUrl = extractImageUrlFromPayload(data)

            console.log(f"当前进度: {progress}% | 状态: {status or 'unknown'}")

            if isSuccessStatus(status) or (progress >= 100 and len(imageUrl) > 0):
                console.log("✅ 任务完成!")
                if len(imageUrl) == 0:
                    raise Error("任务完成但响应中未找到图片URL: " + json.dumps(data))
                return imageUrl
            if isFailureStatus(status):
                raise Error(f"任务执行失败: {json.dumps(data)}")
            if (status == "running" or status == "processing") and progress > 0:
                console.log(f"生成中... 进度: {progress}%")
        except Exception as error:
            console.log(f"⚠️ 第{attempt}次查询发生不可预知的异常: {getErrorMessage(error)}，程序将自动进行下一次尝试...")

        await doSleep(pollIntervalMs)

    raise Error(f"任务超时: 等待超过{math.ceil(maxWaitTimeMs / 60000)}分钟仍未完成")


def guessExtensionFromUrl(url):
    match = re.search(r"\.(png|jpg|jpeg|webp|gif)(?:\?|#|$)", url, re.IGNORECASE)
    if match and match.group(1):
        return match.group(1).lower()
    return "png"


def parseImageUrls(image_urls):
    # 如果已经是数组，直接过滤空值返回
    if isinstance(image_urls, list):
        return [url for url in image_urls if url and str(url).strip()]

    # 如果是字符串，尝试解析
    if isinstance(image_urls, str):
        # 方法一：尝试JSON解析
        try:
            parsed = json.loads(image_urls)
            if isinstance(parsed, list):
                return [url for url in parsed if isinstance(url, str) and url.strip()]
        except Exception:
            pass

        # 方法二：按逗号分割（支持 "url1,url2" 格式）
        splitUrls = [url.strip() for url in image_urls.split(",")]
        splitUrls = [url for url in splitUrls if url]
        if splitUrls:
            return splitUrls

    return []


def parseImagePaths(image_paths):
    if isinstance(image_paths, list):
        return [str(p).strip() for p in image_paths if p and str(p).strip()]
    if isinstance(image_paths, str):
        try:
            parsed = json.loads(image_paths)
            if isinstance(parsed, list):
                return [str(p).strip() for p in parsed if p and str(p).strip()]
        except Exception:
            pass

        splitPaths = [p.strip() for p in image_paths.split(",")]
        splitPaths = [p for p in splitPaths if p]
        if splitPaths:
            return splitPaths
    return []


async def draw_image(params):
    if not params or not params.get("prompt") or not str(params.get("prompt")).strip():
        raise Error("参数 prompt 不能为空。")

    prompt = str(params.get("prompt")).strip()
    resolvedModel = resolveModel(params.get("model"), params.get("model_variant"))

    if params.get("image_size") and params.get("image_size").strip() and resolvedModel != MODEL_PRO:
        raise Error("参数 image_size 仅支持 pro 模型（model_variant='pro' 或 model='nano-banana-pro'）。")

    pollIntervalMs = normalizePositiveInt(params.get("poll_interval_ms"), POLL_INTERVAL)
    normalizedImageSize = params.get("image_size").strip().upper() if params.get("image_size") else ""
    defaultMaxWaitTimeMs = 600000 if normalizedImageSize == "4K" else MAX_WAIT_TIME
    maxWaitTimeMs = normalizePositiveInt(params.get("max_wait_time_ms"), defaultMaxWaitTimeMs)

    imageUrlsArray = []
    if params.get("image_urls"):
        imageUrlsArray = parseImageUrls(params.get("image_urls"))
        if len(imageUrlsArray) == 0:
            raise Error("参数 image_urls 必须是有效的URL数组。")

    imagePathsArray = []
    if params.get("image_paths"):
        imagePathsArray = parseImagePaths(params.get("image_paths"))
        if len(imagePathsArray) == 0:
            raise Error("参数 image_paths 必须是有效的本地路径数组。")

    if len(imagePathsArray) > 0:
        console.log(f"检测到 {len(imagePathsArray)} 张本地参考图，开始上传以获得公网URL...")
        for p in imagePathsArray:
            url = await uploadImageToBeeimg(p)
            imageUrlsArray.append(url)
        console.log("本地参考图上传完成。")

    await ensureDirectories()

    # 步骤1: 提交任务并获取任务ID
    taskId = await callNanobananaApi({
        "prompt": prompt,
        "model": resolvedModel,
        "aspect_ratio": params.get("aspect_ratio"),
        "image_size": params.get("image_size"),
        "image_urls": imageUrlsArray,
        "poll_interval_ms": pollIntervalMs,
        "max_wait_time_ms": maxWaitTimeMs,
    })

    # 步骤2: 轮询等待任务完成
    imageUrl = await pollForResult(taskId, {"poll_interval_ms": pollIntervalMs, "max_wait_time_ms": maxWaitTimeMs})

    ext = guessExtensionFromUrl(imageUrl)
    baseName = buildFileName(prompt, params.get("file_name"))
    filePath = f"{DRAWS_DIR}/{baseName}.{ext}"

    downloadResult = await Tools.Files.download(imageUrl, filePath)
    if not downloadResult.successful:
        raise Error(f"下载图片失败: {downloadResult.details}")

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
        "model": resolvedModel,
        "aspect_ratio": params.get("aspect_ratio"),
        "image_size": params.get("image_size"),
        "image_urls": params.get("image_urls"),
        "image_paths": params.get("image_paths"),
        "hint": "\n".join(hintLines),
    }


async def draw_image_wrapper(params):
    try:
        result = await draw_image(params)
        complete({
            "success": True,
            "message": f"图片生成成功，已保存到 {DRAWS_DIR}，并返回 Markdown 图片提示。",
            "data": result,
        })
    except Exception as error:
        console.error("draw_image 执行失败:", error)
        complete({
            "success": False,
            "message": f"图片生成失败: {getErrorMessage(error)}",
            "error_stack": getErrorStack(error),
        })


exports.draw_image = draw_image_wrapper
