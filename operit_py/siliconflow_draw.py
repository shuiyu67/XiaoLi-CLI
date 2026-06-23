# METADATA
# {
#   "name": "siliconflow_draw",
#   "display_name": {
#     "zh": "硅基流动绘图",
#     "en": "SiliconFlow Draw"
#   },
#   "description": {
#     "zh": "使用 SiliconFlow 官方图像与视频接口生成图片和视频。图片走 /v1/images/generations，视频走 /v1/video/submit + /v1/video/status；生成结果会立即下载到本地，避免官方临时链接过期。",
#     "en": "Generate images and videos with SiliconFlow official image and video APIs. Images use /v1/images/generations; videos use /v1/video/submit + /v1/video/status. Generated assets are downloaded locally immediately before temporary URLs expire."
#   },
#   "category": "Draw",
#   "env": [
#     { "name": "SILICONFLOW_API_KEY", "description": { "zh": "SiliconFlow API Key（必填）", "en": "SiliconFlow API key (required)" }, "required": true },
#     { "name": "SILICONFLOW_API_BASE_URL", "description": { "zh": "SiliconFlow API Base URL（可选，不填默认 https://api.siliconflow.cn ）", "en": "SiliconFlow API base URL (optional; defaults to https://api.siliconflow.cn)" }, "required": false },
#     { "name": "SILICONFLOW_IMAGE_MODEL", "description": { "zh": "默认生图模型（可选；例如 Kwai-Kolors/Kolors、Qwen/Qwen-Image）", "en": "Default image model (optional), e.g. Kwai-Kolors/Kolors or Qwen/Qwen-Image" }, "required": false },
#     { "name": "SILICONFLOW_VIDEO_MODEL", "description": { "zh": "默认生视频模型（可选；例如 Wan-AI/Wan2.2-T2V-A14B 或 Wan-AI/Wan2.2-I2V-A14B）", "en": "Default video model (optional), e.g. Wan-AI/Wan2.2-T2V-A14B or Wan-AI/Wan2.2-I2V-A14B" }, "required": false }
#   ],
#   "tools": [
#     {
#       "name": "draw_image",
#       "description": { "zh": "调用 SiliconFlow 官方图片生成接口生图，下载到本地并返回 Markdown 图片提示。", "en": "Generate images with SiliconFlow official image API, download locally, and return Markdown image hints." },
#       "parameters": [
#         { "name": "prompt", "description": { "zh": "生图提示词", "en": "Image prompt" }, "type": "string", "required": true },
#         { "name": "model", "description": { "zh": "模型名；不传则优先取 SILICONFLOW_IMAGE_MODEL，再取默认值 Kwai-Kolors/Kolors", "en": "Model name; falls back to SILICONFLOW_IMAGE_MODEL, then Kwai-Kolors/Kolors" }, "type": "string", "required": false },
#         { "name": "image_size", "description": { "zh": "图片尺寸，例如 1024x1024；未传时默认 1024x1024", "en": "Image size, e.g. 1024x1024; defaults to 1024x1024" }, "type": "string", "required": false },
#         { "name": "negative_prompt", "description": { "zh": "负面提示词（可选）", "en": "Negative prompt (optional)" }, "type": "string", "required": false },
#         { "name": "batch_size", "description": { "zh": "一次生成多少张图（可选）", "en": "Number of images to generate (optional)" }, "type": "number", "required": false },
#         { "name": "num_inference_steps", "description": { "zh": "推理步数（可选）", "en": "Inference steps (optional)" }, "type": "number", "required": false },
#         { "name": "guidance_scale", "description": { "zh": "提示词引导强度（可选）", "en": "Guidance scale (optional)" }, "type": "number", "required": false },
#         { "name": "seed", "description": { "zh": "随机种子（可选）", "en": "Seed (optional)" }, "type": "number", "required": false },
#         { "name": "file_name", "description": { "zh": "本地保存文件名（不含扩展名）", "en": "Local output filename without extension" }, "type": "string", "required": false },
#         { "name": "api_base_url", "description": { "zh": "自定义 API Base URL（可选）", "en": "Custom API base URL (optional)" }, "type": "string", "required": false }
#       ]
#     },
#     {
#       "name": "draw_video",
#       "description": { "zh": "调用 SiliconFlow 官方视频生成接口生视频，轮询状态，下载到本地并返回本地视频链接提示。", "en": "Generate videos with SiliconFlow official video API, poll status, download locally, and return local video link hints." },
#       "parameters": [
#         { "name": "prompt", "description": { "zh": "生视频提示词", "en": "Video prompt" }, "type": "string", "required": true },
#         { "name": "model", "description": { "zh": "模型名；不传则优先取 SILICONFLOW_VIDEO_MODEL，若传了 image_url/image_path 默认走 Wan-AI/Wan2.2-I2V-A14B，否则默认 Wan-AI/Wan2.2-T2V-A14B", "en": "Model name; falls back to SILICONFLOW_VIDEO_MODEL. If image_url/image_path is provided, defaults to Wan-AI/Wan2.2-I2V-A14B; otherwise Wan-AI/Wan2.2-T2V-A14B" }, "type": "string", "required": false },
#         { "name": "image_size", "description": { "zh": "视频尺寸，可选 1280x720、720x1280、960x960；默认 1280x720", "en": "Video size: 1280x720, 720x1280, or 960x960; defaults to 1280x720" }, "type": "string", "required": false },
#         { "name": "negative_prompt", "description": { "zh": "负面提示词（可选）", "en": "Negative prompt (optional)" }, "type": "string", "required": false },
#         { "name": "image_url", "description": { "zh": "图生视频输入图 URL（可选）", "en": "Input image URL for image-to-video (optional)" }, "type": "string", "required": false },
#         { "name": "image_path", "description": { "zh": "图生视频输入图本地路径（可选，会转成 data URL 上传）", "en": "Local input image path for image-to-video (optional; converted to data URL)" }, "type": "string", "required": false },
#         { "name": "seed", "description": { "zh": "随机种子（可选）", "en": "Seed (optional)" }, "type": "number", "required": false },
#         { "name": "file_name", "description": { "zh": "本地保存文件名（不含扩展名）", "en": "Local output filename without extension" }, "type": "string", "required": false },
#         { "name": "api_base_url", "description": { "zh": "自定义 API Base URL（可选）", "en": "Custom API base URL (optional)" }, "type": "string", "required": false },
#         { "name": "poll_interval_ms", "description": { "zh": "轮询间隔毫秒数，默认 5000", "en": "Polling interval in ms, default 5000" }, "type": "number", "required": false },
#         { "name": "max_wait_time_ms", "description": { "zh": "最大等待毫秒数，默认 600000", "en": "Maximum wait time in ms, default 600000" }, "type": "number", "required": false }
#       ]
#     }
#   ]
# }

import json
import math
import re
import time
import traceback

HTTP_TIMEOUT_MS = 600000
client = OkHttp.newBuilder().connectTimeout(HTTP_TIMEOUT_MS).readTimeout(HTTP_TIMEOUT_MS).writeTimeout(HTTP_TIMEOUT_MS).build()

DEFAULT_API_BASE_URL = "https://api.siliconflow.cn"
DEFAULT_IMAGE_MODEL = "Kwai-Kolors/Kolors"
DEFAULT_IMAGE_SIZE = "1024x1024"
DEFAULT_VIDEO_TEXT_MODEL = "Wan-AI/Wan2.2-T2V-A14B"
DEFAULT_VIDEO_IMAGE_MODEL = "Wan-AI/Wan2.2-I2V-A14B"
DEFAULT_VIDEO_SIZE = "1280x720"
DEFAULT_POLL_INTERVAL_MS = 5000
DEFAULT_MAX_WAIT_TIME_MS = 600000
VIDEO_SIZE_OPTIONS = ["1280x720", "720x1280", "960x960"]

DRAW_ROOT_DIR = getPluginConfigDir("draw")
STORAGE_DIR = f"{DRAW_ROOT_DIR}/siliconflow_draw"
DRAWS_DIR = f"{STORAGE_DIR}/draws"
VIDEOS_DIR = f"{STORAGE_DIR}/videos"


def _is_finite(n):
    return isinstance(n, (int, float)) and not isinstance(n, bool) and math.isfinite(n)


def getApiKey():
    apiKey = getEnv("SILICONFLOW_API_KEY")
    if not apiKey:
        raise Exception("SILICONFLOW_API_KEY 未配置，请先在环境变量中设置硅基流动 API Key。")
    return apiKey


def getApiBaseUrl(customBaseUrl=None):
    fromParam = str(customBaseUrl or "").strip()
    if fromParam:
        return fromParam

    fromEnv = str(getEnv("SILICONFLOW_API_BASE_URL") or "").strip()
    if fromEnv:
        return fromEnv

    return DEFAULT_API_BASE_URL


def joinUrl(baseUrl, path):
    normalizedBase = baseUrl if baseUrl.endswith("/") else f"{baseUrl}/"
    normalizedPath = path[1:] if path.startswith("/") else path
    return f"{normalizedBase}{normalizedPath}"


def getImageEndpoint(baseUrl):
    trimmed = str(baseUrl or "").strip()
    if not trimmed:
        return joinUrl(DEFAULT_API_BASE_URL, "v1/images/generations")
    if "/v1/images/generations" in trimmed:
        return trimmed
    if trimmed.endswith("/v1"):
        return joinUrl(trimmed, "images/generations")
    if trimmed.endswith("/v1/"):
        return joinUrl(trimmed, "images/generations")
    return joinUrl(trimmed, "v1/images/generations")


def getVideoSubmitEndpoint(baseUrl):
    trimmed = str(baseUrl or "").strip()
    if not trimmed:
        return joinUrl(DEFAULT_API_BASE_URL, "v1/video/submit")
    if "/v1/video/submit" in trimmed:
        return trimmed
    if trimmed.endswith("/v1"):
        return joinUrl(trimmed, "video/submit")
    if trimmed.endswith("/v1/"):
        return joinUrl(trimmed, "video/submit")
    return joinUrl(trimmed, "v1/video/submit")


def getVideoStatusEndpoint(baseUrl):
    trimmed = str(baseUrl or "").strip()
    if not trimmed:
        return joinUrl(DEFAULT_API_BASE_URL, "v1/video/status")
    if "/v1/video/status" in trimmed:
        return trimmed
    if trimmed.endswith("/v1"):
        return joinUrl(trimmed, "video/status")
    if trimmed.endswith("/v1/"):
        return joinUrl(trimmed, "video/status")
    return joinUrl(trimmed, "v1/video/status")


def sanitizeFileName(name, prefix):
    safe = re.sub(r'[\\/:*?"<>|]', "_", str(name or "")).strip()
    if not safe:
        return f"{prefix}_{int(time.time() * 1000)}"
    return safe[:80]


def buildFileBaseName(prompt, customName, prefix):
    if customName and len(str(customName).strip()) > 0:
        return sanitizeFileName(customName, prefix)
    rawPrompt = str(prompt or "").strip()
    shortPrompt = f"{rawPrompt[:40]}..." if len(rawPrompt) > 40 else rawPrompt
    return f"{sanitizeFileName(shortPrompt or prefix, prefix)}_{int(time.time() * 1000)}"


def getErrorMessage(error):
    if isinstance(error, Exception):
        return str(error)
    return str(error)


def guessMimeTypeFromPath(filePath):
    lower = str(filePath or "").lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".gif"):
        return "image/gif"
    return "image/png"


def guessExtensionFromUrl(url, fallbackExtension):
    match = re.search(r"\.([a-z0-9]{2,5})(?:[?#].*)?$", str(url or ""), re.IGNORECASE)
    if match and match.group(1):
        return match.group(1).lower()
    return fallbackExtension


def parsePositiveInteger(value, fieldName):
    if value is None or value == "":
        return None
    try:
        numberValue = float(value)
    except (TypeError, ValueError):
        raise Exception(f"{fieldName} 必须是正整数。")
    if not _is_finite(numberValue) or numberValue <= 0:
        raise Exception(f"{fieldName} 必须是正整数。")
    return int(numberValue)


def parseFiniteNumber(value, fieldName):
    if value is None or value == "":
        return None
    try:
        numberValue = float(value)
    except (TypeError, ValueError):
        raise Exception(f"{fieldName} 必须是有效数字。")
    if not _is_finite(numberValue):
        raise Exception(f"{fieldName} 必须是有效数字。")
    return numberValue


def parseSeed(value):
    if value is None or value == "":
        return None
    try:
        numberValue = float(value)
    except (TypeError, ValueError):
        raise Exception("seed 必须是有效数字。")
    if not _is_finite(numberValue):
        raise Exception("seed 必须是有效数字。")
    return int(numberValue)


def normalizeImageSize(imageSize, model):
    trimmedModel = str(model or "").strip().lower()
    rawSize = str(imageSize or "").strip()
    isQwenEditModel = trimmedModel.startswith("qwen/qwen-image-edit")
    if isQwenEditModel:
        if rawSize:
            raise Exception("当前模型为 Qwen 图像编辑模型，官方文档标注不支持 image_size 参数，请去掉 image_size。")
        return None
    if not rawSize:
        return DEFAULT_IMAGE_SIZE
    if not re.match(r"^\d+x\d+$", rawSize, re.IGNORECASE):
        raise Exception("image_size 格式必须是 widthxheight，例如 1024x1024。")
    return rawSize.lower()


def normalizeVideoSize(imageSize):
    rawSize = str(imageSize or "").strip()
    if not rawSize:
        return DEFAULT_VIDEO_SIZE
    if rawSize not in VIDEO_SIZE_OPTIONS:
        raise Exception(f"image_size 仅支持 {'、'.join(VIDEO_SIZE_OPTIONS)}。")
    return rawSize


def isProbablyUrl(value):
    return bool(re.match(r"^https?://", str(value or "").strip(), re.IGNORECASE))


async def ensureDirectories():
    dirs = [DRAW_ROOT_DIR, STORAGE_DIR, DRAWS_DIR, VIDEOS_DIR]
    for dir_ in dirs:
        try:
            result = await Tools.Files.mkdir(dir_)
            if not result.get("successful"):
                console.warn(f"创建目录失败(可能已存在): {dir_} -> {result.get('details')}")
        except Exception as error:
            console.warn(f"创建目录异常: {dir_} -> {getErrorMessage(error)}")


async def readLocalImageAsDataUrl(filePath):
    trimmedPath = str(filePath or "").strip()
    if not trimmedPath:
        raise Exception("image_path 不能为空。")
    existsResult = await Tools.Files.exists(trimmedPath)
    if not existsResult.get("exists"):
        raise Exception(f"本地图片不存在: {trimmedPath}")
    binaryResult = await Tools.Files.readBinary(trimmedPath)
    base64Content = str(binaryResult.get("contentBase64") if binaryResult and binaryResult.get("contentBase64") else "").strip() if binaryResult else ""
    if not base64Content:
        raise Exception(f"读取本地图片失败: {trimmedPath}")
    return f"data:{guessMimeTypeFromPath(trimmedPath)};base64,{base64Content}"


async def resolveVideoImageInput(imageUrl, imagePath):
    trimmedUrl = str(imageUrl or "").strip()
    trimmedPath = str(imagePath or "").strip()
    if trimmedUrl and trimmedPath:
        raise Exception("image_url 和 image_path 只能二选一，请不要同时传。")
    if trimmedUrl:
        if not isProbablyUrl(trimmedUrl):
            raise Exception("image_url 必须是 http 或 https 链接。")
        return trimmedUrl
    if trimmedPath:
        return await readLocalImageAsDataUrl(trimmedPath)
    return None


async def executeJsonRequest(url, body):
    apiKey = getApiKey()
    request = client.newRequest().url(url).method("POST").headers({
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {apiKey}"
    }).body(json.dumps(body), "json")

    response = await request.build().execute()
    if not response.isSuccessful():
        raise Exception(f"HTTP {response.statusCode}: {response.content}")
    try:
        return json.loads(response.content)
    except Exception as error:
        raise Exception(f"解析响应 JSON 失败: {getErrorMessage(error)}")


async def callImageApi(params):
    apiBaseUrl = getApiBaseUrl(params.get("api_base_url"))
    endpoint = getImageEndpoint(apiBaseUrl)

    modelFromParam = str(params.get("model") or "").strip()
    modelFromEnv = str(getEnv("SILICONFLOW_IMAGE_MODEL") or "").strip()
    effectiveModel = modelFromParam or modelFromEnv or DEFAULT_IMAGE_MODEL

    body = {
        "model": effectiveModel,
        "prompt": str(params.get("prompt") or "").strip()
    }

    imageSize = normalizeImageSize(params.get("image_size"), effectiveModel)
    if imageSize:
        body["image_size"] = imageSize

    negativePrompt = str(params.get("negative_prompt") or "").strip()
    if negativePrompt:
        body["negative_prompt"] = negativePrompt

    batchSize = parsePositiveInteger(params.get("batch_size"), "batch_size")
    if batchSize is not None:
        body["batch_size"] = batchSize

    numInferenceSteps = parsePositiveInteger(params.get("num_inference_steps"), "num_inference_steps")
    if numInferenceSteps is not None:
        body["num_inference_steps"] = numInferenceSteps

    guidanceScale = parseFiniteNumber(params.get("guidance_scale"), "guidance_scale")
    if guidanceScale is not None:
        body["guidance_scale"] = guidanceScale

    seed = parseSeed(params.get("seed"))
    if seed is not None:
        body["seed"] = seed

    parsed = await executeJsonRequest(endpoint, body)
    images = parsed.get("images") if (isinstance(parsed, dict) and isinstance(parsed.get("images"), list)) else []
    imageUrls = [str(item.get("url")).strip() for item in images if item and item.get("url")]
    imageUrls = [u for u in imageUrls if len(u) > 0]

    if len(imageUrls) == 0:
        raise Exception("图片接口返回中未找到 images[].url，请检查模型与参数是否匹配。")

    return {
        "effective_model": effectiveModel,
        "image_urls": imageUrls,
        "seed": parsed.get("seed") if (isinstance(parsed, dict) and parsed.get("seed") is not None) else (seed if seed is not None else None)
    }


async def createVideoTask(params, imageInput=None):
    apiBaseUrl = getApiBaseUrl(params.get("api_base_url"))
    endpoint = getVideoSubmitEndpoint(apiBaseUrl)

    modelFromParam = str(params.get("model") or "").strip()
    modelFromEnv = str(getEnv("SILICONFLOW_VIDEO_MODEL") or "").strip()
    defaultVideoModel = DEFAULT_VIDEO_IMAGE_MODEL if imageInput else DEFAULT_VIDEO_TEXT_MODEL
    effectiveModel = modelFromParam or modelFromEnv or defaultVideoModel

    if effectiveModel == DEFAULT_VIDEO_IMAGE_MODEL and not imageInput:
        raise Exception(f"当前模型 {DEFAULT_VIDEO_IMAGE_MODEL} 为图生视频模型，必须传 image_url 或 image_path。")

    body = {
        "model": effectiveModel,
        "prompt": str(params.get("prompt") or "").strip(),
        "image_size": normalizeVideoSize(params.get("image_size"))
    }

    negativePrompt = str(params.get("negative_prompt") or "").strip()
    if negativePrompt:
        body["negative_prompt"] = negativePrompt

    if imageInput:
        body["image"] = imageInput

    seed = parseSeed(params.get("seed"))
    if seed is not None:
        body["seed"] = seed

    parsed = await executeJsonRequest(endpoint, body)
    requestId = str(parsed.get("requestId")).strip() if (isinstance(parsed, dict) and parsed.get("requestId")) else ""
    if not requestId:
        raise Exception("视频接口返回中未找到 requestId。")

    return {
        "api_base_url": apiBaseUrl,
        "effective_model": effectiveModel,
        "request_id": requestId,
        "seed": seed if seed is not None else None
    }


async def queryVideoStatus(apiBaseUrl, requestId):
    endpoint = getVideoStatusEndpoint(apiBaseUrl)
    parsed = await executeJsonRequest(endpoint, {"requestId": requestId})
    status = str(parsed.get("status")).strip() if (isinstance(parsed, dict) and parsed.get("status")) else ""
    reason = str(parsed.get("reason")).strip() if (isinstance(parsed, dict) and parsed.get("reason")) else ""
    results = parsed.get("results") if isinstance(parsed, dict) else None
    videos = results.get("videos") if (isinstance(results, dict) and isinstance(results.get("videos"), list)) else []
    videoUrl = str(videos[0].get("url")).strip() if (len(videos) > 0 and videos[0] and videos[0].get("url")) else ""
    seed = results.get("seed") if (isinstance(results, dict) and results.get("seed") is not None) else None
    return {
        "status": status,
        "reason": reason,
        "video_url": videoUrl,
        "seed": seed
    }


def normalizeVideoStatus(status):
    return str(status or "").strip().lower()


async def draw_image(params):
    prompt = str(params.get("prompt") if params and params.get("prompt") else "").strip()
    if not prompt:
        raise Exception("prompt 不能为空。")

    await ensureDirectories()

    apiResult = await callImageApi(params)
    baseName = buildFileBaseName(prompt, params.get("file_name"), "siliconflow_image")
    files = []

    for index in range(len(apiResult["image_urls"])):
        imageUrl = apiResult["image_urls"][index]
        extension = guessExtensionFromUrl(imageUrl, "png")
        suffix = f"_{index + 1}" if len(apiResult["image_urls"]) > 1 else ""
        filePath = f"{DRAWS_DIR}/{baseName}{suffix}.{extension}"
        downloadResult = await Tools.Files.download(imageUrl, filePath)
        if not downloadResult.get("successful"):
            raise Exception(f"下载图片失败: {downloadResult.get('details')}")
        fileUri = f"file://{filePath}"
        files.append({
            "file_path": filePath,
            "file_uri": fileUri,
            "markdown": f"![AI生成的图片{f' {index + 1}' if len(apiResult['image_urls']) > 1 else ''}]({fileUri})"
        })

    hintLines = []
    hintLines.append(f"图片已生成并下载到 {DRAWS_DIR}。")
    hintLines.append(f"共生成 {len(files)} 张。")
    hintLines.append("")
    hintLines.append("后续回答如果需要展示图片，请直接输出下面这些 Markdown：")
    hintLines.append("")
    for fileItem in files:
        hintLines.append(fileItem["markdown"])

    return {
        "prompt": prompt,
        "model": apiResult["effective_model"],
        "seed": apiResult["seed"],
        "file_path": files[0]["file_path"],
        "file_uri": files[0]["file_uri"],
        "markdown": files[0]["markdown"],
        "files": files,
        "hint": "\n".join(hintLines)
    }


async def draw_video(params):
    prompt = str(params.get("prompt") if params and params.get("prompt") else "").strip()
    if not prompt:
        raise Exception("prompt 不能为空。")

    await ensureDirectories()

    imageInput = await resolveVideoImageInput(params.get("image_url"), params.get("image_path"))
    createdTask = await createVideoTask(params, imageInput)
    pollIntervalMs = parsePositiveInteger(params.get("poll_interval_ms"), "poll_interval_ms") or DEFAULT_POLL_INTERVAL_MS
    maxWaitTimeMs = parsePositiveInteger(params.get("max_wait_time_ms"), "max_wait_time_ms") or DEFAULT_MAX_WAIT_TIME_MS
    deadline = int(time.time() * 1000) + maxWaitTimeMs

    latestStatus = ""
    latestReason = ""
    remoteVideoUrl = ""
    resultSeed = createdTask["seed"]

    while int(time.time() * 1000) <= deadline:
        statusResult = await queryVideoStatus(createdTask["api_base_url"], createdTask["request_id"])
        latestStatus = statusResult["status"]
        latestReason = statusResult["reason"]
        resultSeed = statusResult["seed"] if (statusResult["seed"] is not None) else resultSeed

        normalizedStatus = normalizeVideoStatus(statusResult["status"])
        if normalizedStatus == "succeed":
            remoteVideoUrl = statusResult["video_url"]
            if not remoteVideoUrl:
                raise Exception("视频任务已成功，但返回中未找到 results.videos[0].url。")
            break

        if normalizedStatus == "failed":
            raise Exception(f"视频生成失败: {latestReason or '接口未返回失败原因'}")

        await Tools.System.sleep(pollIntervalMs)

    if not remoteVideoUrl:
        raise Exception(f"视频生成超时，最后状态为 {latestStatus or '未知'}{f'，原因：{latestReason}' if latestReason else ''}")

    baseName = buildFileBaseName(prompt, params.get("file_name"), "siliconflow_video")
    extension = guessExtensionFromUrl(remoteVideoUrl, "mp4")
    filePath = f"{VIDEOS_DIR}/{baseName}.{extension}"
    downloadResult = await Tools.Files.download(remoteVideoUrl, filePath)
    if not downloadResult.get("successful"):
        raise Exception(f"下载视频失败: {downloadResult.get('details')}")

    fileUri = f"file://{filePath}"
    markdownLink = f"[点击查看生成的视频]({fileUri})"
    htmlVideo = f'<video controls src="{fileUri}"></video>'
    hintLines = []
    hintLines.append(f"视频已生成并下载到 {VIDEOS_DIR}。")
    hintLines.append(f"本地路径: {filePath}")
    hintLines.append("")
    hintLines.append("后续回答如果要给出视频，请优先返回这个本地链接：")
    hintLines.append(markdownLink)
    hintLines.append("")
    hintLines.append("如果当前渲染环境支持 HTML 视频标签，也可以使用：")
    hintLines.append(htmlVideo)

    return {
        "prompt": prompt,
        "model": createdTask["effective_model"],
        "request_id": createdTask["request_id"],
        "seed": resultSeed,
        "file_path": filePath,
        "file_uri": fileUri,
        "remote_video_url": remoteVideoUrl,
        "markdown_link": markdownLink,
        "html_video": htmlVideo,
        "hint": "\n".join(hintLines)
    }


async def draw_image_wrapper(params=None):
    if params is None:
        params = {}
    try:
        result = await draw_image(params)
        complete({
            "success": True,
            "message": "SiliconFlow 图片生成成功，已下载到本地。",
            "data": result
        })
    except Exception as error:
        console.error("draw_image 执行失败:", error)
        complete({
            "success": False,
            "message": f"SiliconFlow 图片生成失败: {getErrorMessage(error)}",
            "error_stack": traceback.format_exc()
        })


async def draw_video_wrapper(params=None):
    if params is None:
        params = {}
    try:
        result = await draw_video(params)
        complete({
            "success": True,
            "message": "SiliconFlow 视频生成成功，已下载到本地。",
            "data": result
        })
    except Exception as error:
        console.error("draw_video 执行失败:", error)
        complete({
            "success": False,
            "message": f"SiliconFlow 视频生成失败: {getErrorMessage(error)}",
            "error_stack": traceback.format_exc()
        })


exports.draw_image = draw_image_wrapper
exports.draw_video = draw_video_wrapper
