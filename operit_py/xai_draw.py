# METADATA
# {
#   "name": "xai_draw",
#   "display_name": {"zh": "xAI 图片与视频", "en": "xAI Images and Video"},
#   "description": {"zh": "使用 xAI 官方接口生成图片和视频，并保存到本地。", "en": "Generate images and videos with the official xAI APIs and save them locally."},
#   "env": [
#     {"name": "XAI_API_KEY", "description": {"zh": "xAI API Key（必填）", "en": "xAI API key (required)"}, "required": True},
#     {"name": "XAI_IMAGE_MODEL", "description": {"zh": "默认图片模型（可选；未传 model 时使用，默认 grok-2-image-1212）", "en": "Default image model (optional; used when model is omitted, default grok-2-image-1212)"}, "required": False},
#     {"name": "XAI_VIDEO_MODEL", "description": {"zh": "默认视频模型（可选；未传 model 时使用，默认 grok-imagine-video）", "en": "Default video model (optional; used when model is omitted, default grok-imagine-video)"}, "required": False}
#   ],
#   "category": "Draw",
#   "tools": [
#     {"name": "draw_image", "description": {"zh": "根据提示词调用 xAI 图像生成 API 生成图片，保存到本地并返回 Markdown 图片提示。", "en": "Generate an image via the xAI image generation API using a prompt, save it locally, and return a Markdown image reference."}, "parameters": [
#       {"name": "prompt", "description": {"zh": "绘图提示词（英文或中文皆可）", "en": "Prompt for image generation (Chinese or English)"}, "type": "string", "required": True},
#       {"name": "model", "description": {"zh": "xAI 图像模型名称；不传则优先取 XAI_IMAGE_MODEL，再用默认值 grok-2-image-1212", "en": "xAI image model name; falls back to XAI_IMAGE_MODEL, then grok-2-image-1212"}, "type": "string", "required": False},
#       {"name": "size", "description": {"zh": "图片尺寸，例如 1024x1024（可选）", "en": "Image size, e.g. 1024x1024 (optional)"}, "type": "string", "required": False},
#       {"name": "file_name", "description": {"zh": "自定义保存到本地的文件名（不含路径和扩展名）", "en": "Custom output file name (without path or extension)"}, "type": "string", "required": False}
#     ]},
#     {"name": "draw_video", "description": {"zh": "根据提示词调用 xAI 官方视频生成 API 生成视频，支持文生视频、图生视频和视频编辑，轮询完成后下载到本地并返回本地视频链接提示。", "en": "Generate a video with the official xAI video API. Supports text-to-video, image-to-video, and video editing. Polls until completion, downloads locally, and returns local video link hints."}, "parameters": [
#       {"name": "prompt", "description": {"zh": "视频提示词", "en": "Video prompt"}, "type": "string", "required": True},
#       {"name": "model", "description": {"zh": "视频模型；不传则优先取 XAI_VIDEO_MODEL，再用默认值 grok-imagine-video", "en": "Video model; falls back to XAI_VIDEO_MODEL, then grok-imagine-video"}, "type": "string", "required": False},
#       {"name": "aspect_ratio", "description": {"zh": "输出比例，可选 1:1、16:9、9:16、4:3、3:4、3:2、2:3；默认 16:9；视频编辑模式不支持", "en": "Output aspect ratio. Supported: 1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3. Defaults to 16:9; not supported for video editing."}, "type": "string", "required": False},
#       {"name": "resolution", "description": {"zh": "输出分辨率，仅支持 480p 或 720p；默认 480p；视频编辑模式不支持", "en": "Output resolution, only 480p or 720p. Defaults to 480p; not supported for video editing."}, "type": "string", "required": False},
#       {"name": "duration", "description": {"zh": "输出时长，支持 1-15 秒；默认 5；视频编辑模式不支持", "en": "Output duration from 1 to 15 seconds. Defaults to 5; not supported for video editing."}, "type": "number", "required": False},
#       {"name": "image_url", "description": {"zh": "图生视频输入图 URL（可选）", "en": "Input image URL for image-to-video (optional)"}, "type": "string", "required": False},
#       {"name": "image_path", "description": {"zh": "图生视频输入图本地路径（可选，会转成 data URL）", "en": "Local input image path for image-to-video (optional; converted to a data URL)"}, "type": "string", "required": False},
#       {"name": "video_url", "description": {"zh": "视频编辑输入视频 URL（可选）", "en": "Input video URL for video editing (optional)"}, "type": "string", "required": False},
#       {"name": "file_name", "description": {"zh": "自定义保存到本地的文件名（不含路径和扩展名）", "en": "Custom output file name (without path or extension)"}, "type": "string", "required": False},
#       {"name": "poll_interval_ms", "description": {"zh": "轮询间隔毫秒数，默认 5000", "en": "Polling interval in milliseconds, default 5000"}, "type": "number", "required": False},
#       {"name": "max_wait_time_ms", "description": {"zh": "最大等待毫秒数，默认 600000", "en": "Maximum wait time in milliseconds, default 600000"}, "type": "number", "required": False}
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

DEFAULT_IMAGE_MODEL = "grok-2-image-1212"
DEFAULT_VIDEO_MODEL = "grok-imagine-video"
DEFAULT_POLL_INTERVAL_MS = 5000
DEFAULT_MAX_WAIT_TIME_MS = 600000
DEFAULT_VIDEO_ASPECT_RATIO = "16:9"
DEFAULT_VIDEO_RESOLUTION = "480p"
DEFAULT_VIDEO_DURATION = 5
VIDEO_ASPECT_RATIOS = ["1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3"]
VIDEO_RESOLUTIONS = ["480p", "720p"]
MIN_VIDEO_DURATION = 1
MAX_VIDEO_DURATION = 15

API_BASE_URL = "https://api.x.ai/v1"
IMAGE_API_ENDPOINT = f"{API_BASE_URL}/images/generations"
VIDEO_GENERATION_ENDPOINT = f"{API_BASE_URL}/videos/generations"

DRAW_ROOT_DIR = getPluginConfigDir("draw")
STORAGE_DIR = f"{DRAW_ROOT_DIR}/xai_draw"
DRAWS_DIR = f"{STORAGE_DIR}/draws"
VIDEOS_DIR = f"{STORAGE_DIR}/videos"


def getErrorMessage(error):
    if isinstance(error, Exception):
        return str(error)
    return str(error)


def getErrorStack(error):
    if isinstance(error, Exception):
        import traceback
        return "".join(traceback.format_exception(type(error), error, error.__traceback__))
    return None


def isRecord(value):
    return isinstance(value, dict)


def getApiKey():
    apiKey = getEnv("XAI_API_KEY")
    if not apiKey:
        raise Error("XAI_API_KEY 未配置，请在环境变量中设置 xAI 的 API Key。")
    return apiKey


def getDefaultImageModel():
    fromEnv = str(getEnv("XAI_IMAGE_MODEL") or "").strip()
    return fromEnv or DEFAULT_IMAGE_MODEL


def getDefaultVideoModel():
    fromEnv = str(getEnv("XAI_VIDEO_MODEL") or "").strip()
    return fromEnv or DEFAULT_VIDEO_MODEL


def sanitizeFileName(name, fallbackPrefix):
    safe = re.sub(r'[\\/:*?"<>|]', "_", str(name or "")).strip()
    if not safe:
        return f"{fallbackPrefix}_{int(time.time() * 1000)}"
    return safe[:80]


def buildFileName(prompt, customName, fallbackPrefix):
    if customName and customName.strip():
        return sanitizeFileName(customName, fallbackPrefix)
    shortPrompt = f"{prompt[:40]}..." if len(prompt) > 40 else prompt
    base = sanitizeFileName(shortPrompt or fallbackPrefix, fallbackPrefix)
    return f"{base}_{int(time.time() * 1000)}"


def guessExtensionFromUrl(url, fallback):
    match = re.search(r"\.(png|jpg|jpeg|webp|gif|mp4|mov|webm|mkv)(?:\?|#|$)", str(url or ""), re.IGNORECASE)
    if match and match.group(1):
        return match.group(1).lower()
    return fallback


def guessMimeTypeFromPath(path):
    normalized = str(path or "").strip().lower()
    if normalized.endswith(".png"):
        return "image/png"
    if normalized.endswith(".webp"):
        return "image/webp"
    if normalized.endswith(".gif"):
        return "image/gif"
    if normalized.endswith(".jpg") or normalized.endswith(".jpeg"):
        return "image/jpeg"
    return "application/octet-stream"


def isProbablyUrl(value):
    return bool(re.match(r"^https?://", str(value or "").strip(), re.IGNORECASE))


def normalizePositiveInteger(value, fallback):
    if value is None or value == "":
        return fallback
    parsed = value if isinstance(value, (int, float)) else int(str(value), 10)
    if not math.isfinite(parsed) or parsed <= 0:
        return fallback
    return int(parsed)


def normalizeVideoAspectRatio(value):
    raw = str(value or "").strip()
    if not raw:
        return DEFAULT_VIDEO_ASPECT_RATIO
    if raw not in VIDEO_ASPECT_RATIOS:
        raise Error(f"aspect_ratio 仅支持 {' 或 '.join(VIDEO_ASPECT_RATIOS)}。")
    return raw


def normalizeVideoResolution(value):
    raw = str(value or "").strip().lower()
    if not raw:
        return DEFAULT_VIDEO_RESOLUTION
    if raw not in VIDEO_RESOLUTIONS:
        raise Error(f"resolution 仅支持 {' 或 '.join(VIDEO_RESOLUTIONS)}。")
    return raw


def normalizeVideoDuration(value):
    if value is None or value == "":
        return DEFAULT_VIDEO_DURATION
    parsed = value if isinstance(value, (int, float)) else int(str(value), 10)
    if not math.isfinite(parsed):
        raise Error("duration 必须是数字。")
    normalized = int(parsed)
    if normalized < MIN_VIDEO_DURATION or normalized > MAX_VIDEO_DURATION:
        raise Error(f"duration 仅支持 {MIN_VIDEO_DURATION}-{MAX_VIDEO_DURATION} 秒。")
    return normalized


async def ensureDirectories():
    dirs = [DRAW_ROOT_DIR, STORAGE_DIR, DRAWS_DIR, VIDEOS_DIR]
    for dir_ in dirs:
        try:
            result = await Tools.Files.mkdir(dir_)
            if not result.successful:
                console.warn(f"创建目录失败(可能已存在): {dir_} -> {result.details}")
        except Exception as error:
            console.warn(f"创建目录异常: {dir_} -> {getErrorMessage(error)}")


async def parseJsonResponse(response, label):
    try:
        parsed = json.loads(response.content)
        if not isRecord(parsed):
            raise Error("响应不是对象")
        return parsed
    except Exception as error:
        raise Error(f"解析 {label} 响应失败: {getErrorMessage(error)}")


def extractApiErrorMessage(payload):
    directError = payload.get("error")
    if isinstance(directError, str) and directError.strip():
        return directError.strip()
    if isRecord(directError):
        if isinstance(directError.get("message"), str) and directError["message"].strip():
            return directError["message"].strip()
        if isinstance(directError.get("code"), str) and directError["code"].strip():
            return directError["code"].strip()
    return ""


async def readLocalImageAsDataUrl(filePath):
    trimmedPath = str(filePath or "").strip()
    if not trimmedPath:
        raise Error("image_path 不能为空。")

    existsResult = await Tools.Files.exists(trimmedPath)
    if not existsResult.exists:
        raise Error(f"本地图片不存在: {trimmedPath}")

    binaryResult = await Tools.Files.readBinary(trimmedPath)
    base64Content = (
        str(binaryResult.contentBase64).strip()
        if binaryResult and getattr(binaryResult, "contentBase64", None)
        else ""
    )
    if not base64Content:
        raise Error(f"读取本地图片失败: {trimmedPath}")

    return f"data:{guessMimeTypeFromPath(trimmedPath)};base64,{base64Content}"


async def resolveVideoInputs(imageUrl, imagePath, videoUrl):
    trimmedImageUrl = str(imageUrl or "").strip()
    trimmedImagePath = str(imagePath or "").strip()
    trimmedVideoUrl = str(videoUrl or "").strip()

    imageInputCount = (1 if trimmedImageUrl else 0) + (1 if trimmedImagePath else 0)
    if imageInputCount > 1:
        raise Error("image_url 和 image_path 只能二选一，请不要同时传。")
    if trimmedVideoUrl and imageInputCount > 0:
        raise Error("视频生成一次只能使用一种输入源：纯文本、图片或视频。请不要同时传 image_* 和 video_url。")

    if trimmedImageUrl:
        if not isProbablyUrl(trimmedImageUrl):
            raise Error("image_url 必须是 http 或 https 链接。")
        return {"image": trimmedImageUrl, "input_type": "image_url"}

    if trimmedImagePath:
        return {"image": await readLocalImageAsDataUrl(trimmedImagePath), "input_type": "image_path"}

    if trimmedVideoUrl:
        if not isProbablyUrl(trimmedVideoUrl):
            raise Error("video_url 必须是 http 或 https 链接。")
        return {"video_url": trimmedVideoUrl, "input_type": "video_url"}

    return {"input_type": "text"}


async def callXaiImageApi(params):
    apiKey = getApiKey()
    modelFromParam = str(params.get("model") or "").strip()
    effectiveModel = modelFromParam or getDefaultImageModel()

    body = {
        "model": effectiveModel,
        "prompt": params.get("prompt"),
    }

    size = str(params.get("size") or "").strip()
    if size:
        body["size"] = size

    request = (
        client.newRequest()
        .url(IMAGE_API_ENDPOINT)
        .method("POST")
        .headers({
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"Bearer {apiKey}",
        })
        .body(json.dumps(body), "json")
    )

    response = await request.build().execute()
    if not response.isSuccessful():
        raise Error(f"xAI 图片 API 调用失败: {response.statusCode} - {response.content}")

    parsed = await parseJsonResponse(response, "xAI 图片生成")
    data = parsed.get("data") if isinstance(parsed.get("data"), list) else []
    first = data[0] if len(data) > 0 and isRecord(data[0]) else None
    imageUrl = str(first.get("url")).strip() if first and isinstance(first.get("url"), str) else ""

    if not imageUrl:
        raise Error("xAI 响应中未找到图片 URL，请检查模型和参数是否正确。")

    return {"image_url": imageUrl, "effective_model": effectiveModel}


async def createVideoTask(params):
    apiKey = getApiKey()
    modelFromParam = str(params.get("model") or "").strip()
    effectiveModel = modelFromParam or getDefaultVideoModel()

    body = {
        "model": effectiveModel,
        "prompt": str(params.get("prompt") or "").strip(),
    }

    isVideoEdit = bool(params.get("video_url"))
    if not isVideoEdit:
        body["aspect_ratio"] = normalizeVideoAspectRatio(params.get("aspect_ratio"))
        body["resolution"] = normalizeVideoResolution(params.get("resolution"))
        body["duration"] = normalizeVideoDuration(params.get("duration"))

    if params.get("image"):
        body["image"] = {"url": params.get("image")}
    if params.get("video_url"):
        body["video_url"] = params.get("video_url")

    request = (
        client.newRequest()
        .url(VIDEO_GENERATION_ENDPOINT)
        .method("POST")
        .headers({
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"Bearer {apiKey}",
        })
        .body(json.dumps(body), "json")
    )

    response = await request.build().execute()
    if not response.isSuccessful():
        raise Error(f"xAI 视频创建任务失败: {response.statusCode} - {response.content}")

    parsed = await parseJsonResponse(response, "xAI 视频创建")
    requestId = str(parsed.get("request_id")).strip() if isinstance(parsed.get("request_id"), str) else ""
    status = str(parsed.get("status")).strip() if isinstance(parsed.get("status"), str) else ""

    if not requestId:
        raise Error(f"xAI 视频创建响应中未找到 request_id: {response.content}")

    return {
        "request_id": requestId,
        "status": status,
        "effective_model": effectiveModel,
        "aspect_ratio": body.get("aspect_ratio") if isinstance(body.get("aspect_ratio"), str) else None,
        "resolution": body.get("resolution") if isinstance(body.get("resolution"), str) else None,
        "duration": body.get("duration") if isinstance(body.get("duration"), (int, float)) else None,
    }


async def queryVideoTaskStatus(requestId):
    apiKey = getApiKey()
    endpoint = f"{API_BASE_URL}/videos/{quote(requestId)}"
    request = (
        client.newRequest()
        .url(endpoint)
        .method("GET")
        .headers({
            "accept": "application/json",
            "Authorization": f"Bearer {apiKey}",
        })
    )

    response = await request.build().execute()
    if not response.isSuccessful():
        raise Error(f"xAI 视频查询失败: {response.statusCode} - {response.content}")

    parsed = await parseJsonResponse(response, "xAI 视频查询")
    status = str(parsed.get("status")).strip() if isinstance(parsed.get("status"), str) else ""
    video = parsed.get("video") if isRecord(parsed.get("video")) else None
    videoUrl = str(video.get("url")).strip() if video and isinstance(video.get("url"), str) else ""
    contentType = str(video.get("content_type")).strip() if video and isinstance(video.get("content_type"), str) else ""
    expiresAt = str(video.get("expires_at")).strip() if video and isinstance(video.get("expires_at"), str) else ""
    duration = video.get("duration") if video and isinstance(video.get("duration"), (int, float)) else None
    respectModeration = str(video.get("respect_moderation")).strip() if video and isinstance(video.get("respect_moderation"), str) else ""
    errorMessage = extractApiErrorMessage(parsed)

    return {
        "status": status,
        "video_url": videoUrl,
        "content_type": contentType,
        "expires_at": expiresAt,
        "duration": duration,
        "respect_moderation": respectModeration,
        "error_message": errorMessage,
    }


def normalizeVideoTaskStatus(status):
    normalized = str(status or "").strip().lower()
    if normalized == "done":
        return "completed"
    if normalized == "expired":
        return "failed"
    return "processing"


async def draw_image(params):
    if not params or not params.get("prompt") or not str(params.get("prompt")).strip():
        raise Error("参数 prompt 不能为空。")

    prompt = str(params.get("prompt")).strip()
    await ensureDirectories()

    apiResult = await callXaiImageApi({
        "prompt": prompt,
        "model": params.get("model"),
        "size": params.get("size"),
    })

    ext = guessExtensionFromUrl(apiResult["image_url"], "png")
    baseName = buildFileName(prompt, params.get("file_name"), "xai_draw")
    filePath = f"{DRAWS_DIR}/{baseName}.{ext}"
    downloadResult = await Tools.Files.download(apiResult["image_url"], filePath)
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
        "prompt": prompt,
        "model": apiResult["effective_model"],
        "remote_image_url": apiResult["image_url"],
        "file_path": filePath,
        "file_uri": fileUri,
        "markdown": markdown,
        "hint": "\n".join(hintLines),
    }


async def draw_video(params):
    prompt = str(params.get("prompt") if params else "").strip()
    if not prompt:
        raise Error("prompt 不能为空。")

    await ensureDirectories()

    resolvedInputs = await resolveVideoInputs(params.get("image_url"), params.get("image_path"), params.get("video_url"))
    mergedParams = dict(params)
    mergedParams["prompt"] = prompt
    mergedParams["image"] = resolvedInputs.get("image")
    mergedParams["video_url"] = resolvedInputs.get("video_url")
    createdTask = await createVideoTask(mergedParams)

    pollIntervalMs = normalizePositiveInteger(params.get("poll_interval_ms"), DEFAULT_POLL_INTERVAL_MS)
    maxWaitTimeMs = normalizePositiveInteger(params.get("max_wait_time_ms"), DEFAULT_MAX_WAIT_TIME_MS)
    deadline = time.time() * 1000 + maxWaitTimeMs

    latestStatus = createdTask["status"]
    latestErrorMessage = ""
    remoteVideoUrl = ""
    remoteContentType = ""
    expiresAt = ""
    remoteDuration = createdTask["duration"]
    remoteRespectModeration = ""

    while time.time() * 1000 <= deadline:
        statusResult = await queryVideoTaskStatus(createdTask["request_id"])
        latestStatus = statusResult["status"]
        latestErrorMessage = statusResult["error_message"]
        remoteContentType = statusResult["content_type"]
        expiresAt = statusResult["expires_at"]
        remoteDuration = statusResult["duration"]
        remoteRespectModeration = statusResult["respect_moderation"]

        normalizedStatus = normalizeVideoTaskStatus(statusResult["status"])
        if normalizedStatus == "completed":
            remoteVideoUrl = statusResult["video_url"]
            if not remoteVideoUrl:
                raise Error("视频任务已完成，但响应中未找到 video.url。")
            break

        if normalizedStatus == "failed":
            raise Error(f"视频生成失败或过期: {latestErrorMessage or latestStatus or '接口未返回失败原因'}")

        await Tools.System.sleep(pollIntervalMs)

    if not remoteVideoUrl:
        raise Error(
            f"视频生成超时，最后状态为 {latestStatus or '未知'}{('，原因：' + latestErrorMessage) if latestErrorMessage else ''}"
        )

    extension = guessExtensionFromUrl(remoteVideoUrl, "mp4")
    baseName = buildFileName(prompt, params.get("file_name"), "xai_video")
    filePath = f"{VIDEOS_DIR}/{baseName}.{extension}"
    downloadResult = await Tools.Files.download(remoteVideoUrl, filePath)
    if not downloadResult.successful:
        raise Error(f"下载视频失败: {downloadResult.details}")

    fileUri = f"file://{filePath}"
    markdownLink = f"[点击查看生成的视频]({fileUri})"
    htmlVideo = f'<video controls src="{fileUri}"></video>'

    hintLines = []
    hintLines.append(f"视频已生成并保存在本地 {VIDEOS_DIR}。")
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
        "status": latestStatus,
        "input_type": resolvedInputs["input_type"],
        "aspect_ratio": createdTask["aspect_ratio"],
        "resolution": createdTask["resolution"],
        "duration": remoteDuration,
        "remote_video_url": remoteVideoUrl,
        "remote_content_type": remoteContentType,
        "remote_expires_at": expiresAt,
        "remote_respect_moderation": remoteRespectModeration,
        "file_path": filePath,
        "file_uri": fileUri,
        "markdown_link": markdownLink,
        "html_video": htmlVideo,
        "hint": "\n".join(hintLines),
    }


async def draw_image_wrapper(params):
    try:
        result = await draw_image(params)
        complete({
            "success": True,
            "message": "xAI 图片生成成功，已下载到本地。",
            "data": result,
        })
    except Exception as error:
        console.error("draw_image 执行失败:", error)
        complete({
            "success": False,
            "message": f"xAI 图片生成失败: {getErrorMessage(error)}",
            "error_stack": getErrorStack(error),
        })


async def draw_video_wrapper(params):
    try:
        result = await draw_video(params if params else {})
        complete({
            "success": True,
            "message": "xAI 视频生成成功，已下载到本地。",
            "data": result,
        })
    except Exception as error:
        console.error("draw_video 执行失败:", error)
        complete({
            "success": False,
            "message": f"xAI 视频生成失败: {getErrorMessage(error)}",
            "error_stack": getErrorStack(error),
        })


exports.draw_image = draw_image_wrapper
exports.draw_video = draw_video_wrapper
