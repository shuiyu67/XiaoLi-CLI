# METADATA
# {
#   "name": "minimax_draw",
#   "display_name": {
#     "zh": "MiniMax 绘图",
#     "en": "MiniMax Draw"
#   },
#   "description": {
#     "zh": "使用 MiniMax 官方图像生成接口 (/v1/image_generation) 生成图片，支持文生图和带参考图的生图；结果保存到本地 /sdcard/Download/Operit/plugins/draw/minimax_draw/draws/ 目录，并返回 Markdown 图片提示。",
#     "en": "Generate images with the official MiniMax image generation API (/v1/image_generation). Supports text-to-image and reference-image generation. Saves results to /sdcard/Download/Operit/plugins/draw/minimax_draw/draws/ and returns Markdown image hints."
#   },
#   "category": "Draw",
#   "env": [
#     { "name": "MINIMAX_API_KEY", "description": { "zh": "MiniMax API Key（必填）", "en": "MiniMax API key (required)" }, "required": true },
#     { "name": "MINIMAX_API_BASE_URL", "description": { "zh": "MiniMax API Base URL（可选；默认 https://api.minimaxi.com，国际站可改为 https://api.minimax.io）", "en": "MiniMax API base URL (optional; defaults to https://api.minimaxi.com, international users can use https://api.minimax.io)" }, "required": false },
#     { "name": "MINIMAX_IMAGE_MODEL", "description": { "zh": "默认图片模型（可选；未传 model 时使用，默认 image-01）", "en": "Default image model (optional; used when model is omitted, default image-01)" }, "required": false },
#     { "name": "BEEIMG_API_KEY", "description": { "zh": "BeeIMG API Key（可选；仅当 image_paths 传本地参考图路径时需要，用于先上传到公网图床）", "en": "BeeIMG API key (optional; only needed when image_paths is used so local reference images can be uploaded first)" }, "required": false }
#   ],
#   "tools": [
#     {
#       "name": "draw_image",
#       "description": { "zh": "根据提示词调用 MiniMax 官方绘图接口生成图片，支持文生图和参考图生图，保存到本地并返回 Markdown 图片提示。", "en": "Generate images with the official MiniMax image API using a prompt. Supports text-to-image and reference-image generation, saves locally, and returns Markdown image hints." },
#       "parameters": [
#         { "name": "prompt", "description": { "zh": "绘图提示词（中文或英文）", "en": "Image prompt (Chinese or English)" }, "type": "string", "required": true },
#         { "name": "model", "description": { "zh": "模型名称（可选；不传则使用环境变量 MINIMAX_IMAGE_MODEL，否则默认 image-01）", "en": "Model name (optional; falls back to MINIMAX_IMAGE_MODEL, then image-01)" }, "type": "string", "required": false },
#         { "name": "aspect_ratio", "description": { "zh": "输出比例，可选 1:1、16:9、4:3、3:2、2:3、3:4、9:16、21:9；21:9 仅 image-01 支持", "en": "Aspect ratio. Supported: 1:1, 16:9, 4:3, 3:2, 2:3, 3:4, 9:16, 21:9. 21:9 is only supported by image-01." }, "type": "string", "required": false },
#         { "name": "width", "description": { "zh": "输出宽度（可选；仅 image-01 支持；需与 height 一起传，范围 512-2048 且为 8 的倍数）", "en": "Output width (optional; image-01 only; must be provided together with height, range 512-2048 and multiple of 8)" }, "type": "number", "required": false },
#         { "name": "height", "description": { "zh": "输出高度（可选；仅 image-01 支持；需与 width 一起传，范围 512-2048 且为 8 的倍数）", "en": "Output height (optional; image-01 only; must be provided together with width, range 512-2048 and multiple of 8)" }, "type": "number", "required": false },
#         { "name": "n", "description": { "zh": "生成图片数量，范围 1-9，默认 1", "en": "Number of images to generate, range 1-9, default 1" }, "type": "number", "required": false },
#         { "name": "response_format", "description": { "zh": "返回格式，可选 url 或 base64；默认 base64（更适合直接保存到本地）", "en": "Response format: url or base64. Defaults to base64 for direct local saving." }, "type": "string", "required": false },
#         { "name": "prompt_optimizer", "description": { "zh": "是否启用提示词优化（可选）", "en": "Enable prompt optimizer (optional)" }, "type": "boolean", "required": false },
#         { "name": "aigc_watermark", "description": { "zh": "是否添加 AIGC 水印（可选）", "en": "Add AIGC watermark (optional)" }, "type": "boolean", "required": false },
#         { "name": "seed", "description": { "zh": "随机种子（可选）", "en": "Seed (optional)" }, "type": "number", "required": false },
#         { "name": "image_urls", "description": { "zh": "参考图公网 URL 数组（可选；图生图用）。支持字符串数组、JSON 字符串或逗号分隔字符串", "en": "Reference image public URL list (optional; for reference-image generation). Accepts string array, JSON string, or comma-separated string." }, "type": "array", "required": false },
#         { "name": "image_paths", "description": { "zh": "参考图本地路径数组（可选；会先上传到图床再提交给 MiniMax）。支持字符串数组、JSON 字符串或逗号分隔字符串", "en": "Reference local image path list (optional; local images are uploaded first before calling MiniMax). Accepts string array, JSON string, or comma-separated string." }, "type": "array", "required": false },
#         { "name": "file_name", "description": { "zh": "自定义本地文件名（不含扩展名）", "en": "Custom local output file name without extension" }, "type": "string", "required": false },
#         { "name": "api_base_url", "description": { "zh": "自定义 MiniMax API Base URL（可选）", "en": "Custom MiniMax API base URL (optional)" }, "type": "string", "required": false }
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

DEFAULT_API_BASE_URL = "https://api.minimaxi.com"
DEFAULT_MODEL = "image-01"
DEFAULT_RESPONSE_FORMAT = "base64"
DEFAULT_IMAGE_COUNT = 1
DEFAULT_BASE64_EXTENSION = "jpeg"
SUPPORTED_ASPECT_RATIOS = ["1:1", "16:9", "4:3", "3:2", "2:3", "3:4", "9:16", "21:9"]
BEEIMG_UPLOAD_ENDPOINT = "https://beeimg.com/api/upload/file/json/"

DRAW_ROOT_DIR = getPluginConfigDir("draw")
STORAGE_DIR = f"{DRAW_ROOT_DIR}/minimax_draw"
DRAWS_DIR = f"{STORAGE_DIR}/draws"


def _is_finite(n):
    return isinstance(n, (int, float)) and not isinstance(n, bool) and math.isfinite(n)


def _is_integer(n):
    return _is_finite(n) and n == int(n)


def isRecord(value):
    return isinstance(value, dict)


def getErrorMessage(error):
    if isinstance(error, Exception):
        return str(error)
    return str(error)


def getApiKey():
    apiKey = str(getEnv("MINIMAX_API_KEY") or "").strip()
    if not apiKey:
        raise Exception("MINIMAX_API_KEY 未配置，请先在环境变量中设置 MiniMax API Key。")
    return apiKey


def joinUrl(baseUrl, path):
    baseStr = str(baseUrl or "")
    normalizedBase = baseStr if baseStr.endswith("/") else f"{baseStr}/"
    pathStr = str(path or "")
    normalizedPath = pathStr[1:] if pathStr.startswith("/") else pathStr
    return f"{normalizedBase}{normalizedPath}"


def getApiBaseUrl(customBaseUrl=None):
    fromParam = str(customBaseUrl or "").strip()
    if fromParam:
        return fromParam

    fromEnv = str(getEnv("MINIMAX_API_BASE_URL") or "").strip()
    if fromEnv:
        return fromEnv

    return DEFAULT_API_BASE_URL


def getImageEndpoint(baseUrl):
    trimmed = str(baseUrl or "").strip()
    if not trimmed:
        return joinUrl(DEFAULT_API_BASE_URL, "v1/image_generation")
    if "/v1/image_generation" in trimmed:
        return trimmed
    if trimmed.endswith("/v1"):
        return joinUrl(trimmed, "image_generation")
    if trimmed.endswith("/v1/"):
        return joinUrl(trimmed, "image_generation")
    return joinUrl(trimmed, "v1/image_generation")


def resolveModel(model):
    fromParam = str(model or "").strip()
    if fromParam:
        return fromParam

    fromEnv = str(getEnv("MINIMAX_IMAGE_MODEL") or "").strip()
    if fromEnv:
        return fromEnv

    return DEFAULT_MODEL


def sanitizeFileName(name, fallbackPrefix):
    safe = re.sub(r'[\\/:*?"<>|]', "_", str(name or "")).strip()
    if not safe:
        return f"{fallbackPrefix}_{int(time.time() * 1000)}"
    return safe[:80]


def buildFileBaseName(prompt, customName, fallbackPrefix):
    fromCustom = str(customName or "").strip()
    if fromCustom:
        return sanitizeFileName(fromCustom, fallbackPrefix)
    rawPrompt = str(prompt or "").strip()
    shortPrompt = f"{rawPrompt[:40]}..." if len(rawPrompt) > 40 else rawPrompt
    return f"{sanitizeFileName(shortPrompt or fallbackPrefix, fallbackPrefix)}_{int(time.time() * 1000)}"


async def ensureDirectories():
    dirs = [DRAW_ROOT_DIR, STORAGE_DIR, DRAWS_DIR]
    for dir_ in dirs:
        try:
            result = await Tools.Files.mkdir(dir_)
            if not result.get("successful"):
                console.warn(f"创建目录失败(可能已存在): {dir_} -> {result.get('details')}")
        except Exception as error:
            console.warn(f"创建目录异常: {dir_} -> {getErrorMessage(error)}")


def parsePositiveInteger(value, fieldName, options=None):
    hasDefault = options is not None and "defaultValue" in options
    defaultValue = options["defaultValue"] if hasDefault else None

    if value is None or value == "":
        return defaultValue

    numberValue = value if isinstance(value, (int, float)) and not isinstance(value, bool) else float(str(value))
    if not _is_finite(numberValue) or numberValue <= 0 or not _is_integer(numberValue):
        raise Exception(f"{fieldName} 必须是正整数。")
    numberValue = int(numberValue)

    if options and options.get("min") is not None and numberValue < options["min"]:
        raise Exception(f"{fieldName} 不能小于 {options['min']}。")

    if options and options.get("max") is not None and numberValue > options["max"]:
        raise Exception(f"{fieldName} 不能大于 {options['max']}。")

    return numberValue


def parseInteger(value, fieldName):
    if value is None or value == "":
        return None

    numberValue = value if isinstance(value, (int, float)) and not isinstance(value, bool) else float(str(value))
    if not _is_finite(numberValue) or not _is_integer(numberValue):
        raise Exception(f"{fieldName} 必须是整数。")

    return int(numberValue)


def parseBoolean(value, fieldName):
    if value is None or value == "":
        return None

    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized in ("true", "1", "yes"):
        return True
    if normalized in ("false", "0", "no"):
        return False

    raise Exception(f"{fieldName} 必须是布尔值。")


def normalizeResponseFormat(value):
    normalized = str(value or DEFAULT_RESPONSE_FORMAT).strip().lower()
    if normalized != "url" and normalized != "base64":
        raise Exception("response_format 仅支持 url 或 base64。")
    return normalized


def normalizeAspectRatio(model, value):
    normalized = str(value or "").strip()
    if not normalized:
        return None

    if normalized not in SUPPORTED_ASPECT_RATIOS:
        raise Exception(f"aspect_ratio 仅支持 {'、'.join(SUPPORTED_ASPECT_RATIOS)}。")

    if normalized == "21:9" and str(model or "").strip() != "image-01":
        raise Exception("aspect_ratio=21:9 仅支持 model=image-01。")

    return normalized


def normalizeDimensions(model, widthValue, heightValue, aspectRatio):
    if aspectRatio:
        return {"width": None, "height": None}

    width = parsePositiveInteger(widthValue, "width")
    height = parsePositiveInteger(heightValue, "height")

    if width is None and height is None:
        return {"width": None, "height": None}

    if width is None or height is None:
        raise Exception("width 和 height 需要同时传入。")

    if str(model or "").strip() != "image-01":
        raise Exception("width 和 height 仅支持 model=image-01。")

    if width < 512 or width > 2048 or width % 8 != 0:
        raise Exception("width 需要在 512-2048 之间，且必须为 8 的倍数。")

    if height < 512 or height > 2048 or height % 8 != 0:
        raise Exception("height 需要在 512-2048 之间，且必须为 8 的倍数。")

    return {"width": width, "height": height}


def parseStringList(value, fieldName):
    if value is None or value == "":
        return []

    if isinstance(value, list):
        return [str(item or "").strip() for item in value if str(item or "").strip()]

    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return []

        try:
            parsed = json.loads(trimmed)
            if isinstance(parsed, list):
                return [str(item or "").strip() for item in parsed if str(item or "").strip()]
        except Exception:
            # ignore and try comma-separated parsing
            pass

        return [item.strip() for item in trimmed.split(",") if item.strip()]

    raise Exception(f"{fieldName} 必须是字符串数组、JSON 字符串或逗号分隔字符串。")


def isProbablyUrl(value):
    return bool(re.match(r"^https?://", str(value or "").strip(), re.IGNORECASE))


def getBeeimgApiKey():
    return str(getEnv("BEEIMG_API_KEY") or "").strip()


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
    return "application/octet-stream"


async def uploadImageToBeeimg(filePath):
    exists = await Tools.Files.exists(filePath)
    if not exists.get("exists"):
        raise Exception(f"参考图文件不存在: {filePath}")

    apiKey = getBeeimgApiKey()
    if not apiKey:
        raise Exception("使用 image_paths 需要配置 BEEIMG_API_KEY，用于先把本地参考图上传到公网图床。")

    response = await Tools.Net.uploadFile({
        "url": BEEIMG_UPLOAD_ENDPOINT,
        "method": "POST",
        "form_data": {
            "apikey": apiKey
        },
        "files": [
            {
                "field_name": "file",
                "file_path": filePath,
                "content_type": guessMimeTypeFromPath(filePath)
            }
        ]
    })

    if response.statusCode < 200 or response.statusCode >= 300:
        raise Exception(f"BeeIMG 上传失败: HTTP {response.statusCode} - {response.content}")

    try:
        parsed = json.loads(response.content)
    except Exception as error:
        raise Exception(f"解析 BeeIMG 响应失败: {getErrorMessage(error)}")

    files = parsed.get("files") if (isRecord(parsed) and isRecord(parsed.get("files"))) else None
    fileUrl = str(files.get("url")).strip() if (files and files.get("url")) else ""
    code = str(files.get("code")) if (files and files.get("code") is not None) else ""
    status = str(files.get("status")) if (files and files.get("status")) else ""

    if not fileUrl or (code != "200" and code != "" and status != "Success"):
        raise Exception(f"BeeIMG 上传失败: {response.content}")

    return fileUrl


async def resolveSubjectReference(imageUrls, imagePaths):
    resolvedUrls = parseStringList(imageUrls, "image_urls")
    resolvedPaths = parseStringList(imagePaths, "image_paths")

    for url in resolvedUrls:
        if not isProbablyUrl(url):
            raise Exception(f"image_urls 中包含无效链接: {url}")

    for filePath in resolvedPaths:
        uploadedUrl = await uploadImageToBeeimg(filePath)
        resolvedUrls.append(uploadedUrl)

    if len(resolvedUrls) == 0:
        return None

    return [{"type": "character", "image_file": url} for url in resolvedUrls]


def normalizeBase64(base64):
    raw = str(base64 or "").strip()
    if not raw:
        return raw

    prefixIndex = raw.find("base64,")
    if raw.startswith("data:") and prefixIndex >= 0:
        return raw[prefixIndex + len("base64,"):].strip()

    return raw


def guessExtensionFromUrl(url, fallbackExtension):
    match = re.search(r"\.([a-z0-9]{2,5})(?:[?#].*)?$", str(url or ""), re.IGNORECASE)
    if match and match.group(1):
        return match.group(1).lower()
    return fallbackExtension


def parseMiniMaxError(parsed, fallbackMessage):
    baseResp = parsed.get("base_resp") if (isRecord(parsed) and isRecord(parsed.get("base_resp"))) else None
    if not baseResp:
        return

    statusCode = float(baseResp.get("status_code")) if baseResp.get("status_code") is not None else 0
    if _is_finite(statusCode) and statusCode != 0:
        statusMsg = str(baseResp.get("status_msg")) if baseResp.get("status_msg") else fallbackMessage
        raise Exception(f"MiniMax 图片接口返回错误: {statusMsg} (status_code={int(statusCode) if _is_integer(statusCode) else statusCode})")


async def callMiniMaxImageApi(params):
    apiBaseUrl = getApiBaseUrl(params.get("api_base_url"))
    endpoint = getImageEndpoint(apiBaseUrl)
    effectiveModel = resolveModel(params.get("model"))
    responseFormat = normalizeResponseFormat(params.get("response_format"))
    aspectRatio = normalizeAspectRatio(effectiveModel, params.get("aspect_ratio"))
    dimensions = normalizeDimensions(effectiveModel, params.get("width"), params.get("height"), aspectRatio)
    imageCount = parsePositiveInteger(params.get("n"), "n", {"defaultValue": DEFAULT_IMAGE_COUNT, "min": 1, "max": 9})
    promptOptimizer = parseBoolean(params.get("prompt_optimizer"), "prompt_optimizer")
    aigcWatermark = parseBoolean(params.get("aigc_watermark"), "aigc_watermark")
    seed = parseInteger(params.get("seed"), "seed")
    subjectReference = await resolveSubjectReference(params.get("image_urls"), params.get("image_paths"))

    body = {
        "model": effectiveModel,
        "prompt": str(params.get("prompt") or "").strip(),
        "response_format": responseFormat,
        "n": imageCount
    }

    if aspectRatio:
        body["aspect_ratio"] = aspectRatio

    if dimensions.get("width") is not None and dimensions.get("height") is not None:
        body["width"] = dimensions["width"]
        body["height"] = dimensions["height"]

    if promptOptimizer is not None:
        body["prompt_optimizer"] = promptOptimizer

    if aigcWatermark is not None:
        body["aigc_watermark"] = aigcWatermark

    if seed is not None:
        body["seed"] = seed

    if subjectReference:
        body["subject_reference"] = subjectReference

    request = client.newRequest().url(endpoint).method("POST").headers({
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {getApiKey()}"
    }).body(json.dumps(body), "json")

    response = await request.build().execute()
    if not response.isSuccessful():
        raise Exception(f"MiniMax 图片 API 调用失败: {response.statusCode} - {response.content}")

    try:
        parsed = json.loads(response.content)
    except Exception as error:
        raise Exception(f"解析 MiniMax 响应失败: {getErrorMessage(error)}")

    parseMiniMaxError(parsed, "MiniMax 接口返回错误")

    data = parsed.get("data") if (isRecord(parsed) and isRecord(parsed.get("data"))) else None
    if not data:
        raise Exception("MiniMax 响应中未找到 data 对象。")

    metadata = data.get("metadata") if isRecord(data.get("metadata")) else None
    successCount = float(metadata.get("success_count")) if (metadata and metadata.get("success_count") is not None) else None
    failedCount = float(metadata.get("failed_count")) if (metadata and metadata.get("failed_count") is not None) else None
    requestId = str(parsed.get("id")) if (isRecord(parsed) and parsed.get("id")) else ""

    if responseFormat == "base64":
        imageBase64 = [str(item or "").strip() for item in data.get("image_base64")] if isinstance(data.get("image_base64"), list) else []
        imageBase64 = [item for item in imageBase64 if len(item) > 0]

        if len(imageBase64) == 0:
            raise Exception("MiniMax 响应中未找到 data.image_base64。")

        return {
            "request_id": requestId,
            "effective_model": effectiveModel,
            "response_format": responseFormat,
            "image_base64": imageBase64,
            "image_urls": [],
            "success_count": int(successCount) if _is_finite(successCount) else len(imageBase64),
            "failed_count": int(failedCount) if _is_finite(failedCount) else 0,
            "reference_count": len(subjectReference) if subjectReference else 0
        }

    imageUrls = [str(item or "").strip() for item in data.get("image_urls")] if isinstance(data.get("image_urls"), list) else []
    imageUrls = [item for item in imageUrls if len(item) > 0]

    if len(imageUrls) == 0:
        raise Exception("MiniMax 响应中未找到 data.image_urls。")

    return {
        "request_id": requestId,
        "effective_model": effectiveModel,
        "response_format": responseFormat,
        "image_base64": [],
        "image_urls": imageUrls,
        "success_count": int(successCount) if _is_finite(successCount) else len(imageUrls),
        "failed_count": int(failedCount) if _is_finite(failedCount) else 0,
        "reference_count": len(subjectReference) if subjectReference else 0
    }


async def draw_image(params):
    prompt = str(params.get("prompt") if params and params.get("prompt") else "").strip()
    if not prompt:
        raise Exception("参数 prompt 不能为空。")

    await ensureDirectories()

    apiResult = await callMiniMaxImageApi({
        "prompt": prompt,
        "model": params.get("model"),
        "aspect_ratio": params.get("aspect_ratio"),
        "width": params.get("width"),
        "height": params.get("height"),
        "n": params.get("n"),
        "response_format": params.get("response_format"),
        "prompt_optimizer": params.get("prompt_optimizer"),
        "aigc_watermark": params.get("aigc_watermark"),
        "seed": params.get("seed"),
        "image_urls": params.get("image_urls"),
        "image_paths": params.get("image_paths"),
        "api_base_url": params.get("api_base_url")
    })

    baseName = buildFileBaseName(prompt, params.get("file_name"), "minimax_draw")
    files = []

    if apiResult["response_format"] == "base64":
        for index in range(len(apiResult["image_base64"])):
            suffix = f"_{index + 1}" if len(apiResult["image_base64"]) > 1 else ""
            filePath = f"{DRAWS_DIR}/{baseName}{suffix}.{DEFAULT_BASE64_EXTENSION}"
            writeResult = await Tools.Files.writeBinary(filePath, normalizeBase64(apiResult["image_base64"][index]))
            if not writeResult.get("successful"):
                raise Exception(f"保存图片失败: {writeResult.get('details')}")
            fileUri = f"file://{filePath}"
            files.append({
                "file_path": filePath,
                "file_uri": fileUri,
                "markdown": f"![MiniMax 生成的图片{f' {index + 1}' if len(apiResult['image_base64']) > 1 else ''}]({fileUri})",
                "remote_image_url": None
            })
    else:
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
                "markdown": f"![MiniMax 生成的图片{f' {index + 1}' if len(apiResult['image_urls']) > 1 else ''}]({fileUri})",
                "remote_image_url": imageUrl
            })

    hintLines = []
    hintLines.append(f"图片已生成并保存在本地 {DRAWS_DIR}。")
    hintLines.append(f"共生成 {len(files)} 张。")
    if apiResult["reference_count"] > 0:
        hintLines.append(f"本次使用了 {apiResult['reference_count']} 张参考图。")
    hintLines.append("")
    hintLines.append("后续回答如果需要展示图片，请直接输出下面这些 Markdown：")
    hintLines.append("")
    for fileItem in files:
        hintLines.append(fileItem["markdown"])

    return {
        "prompt": prompt,
        "model": apiResult["effective_model"],
        "request_id": apiResult["request_id"] or None,
        "response_format": apiResult["response_format"],
        "success_count": apiResult["success_count"],
        "failed_count": apiResult["failed_count"],
        "reference_count": apiResult["reference_count"],
        "file_path": files[0]["file_path"],
        "file_uri": files[0]["file_uri"],
        "markdown": files[0]["markdown"],
        "files": files,
        "hint": "\n".join(hintLines)
    }


async def draw_image_wrapper(params=None):
    if params is None:
        params = {}
    try:
        result = await draw_image(params)
        complete({
            "success": True,
            "message": "MiniMax 图片生成成功，已保存到本地。",
            "data": result
        })
    except Exception as error:
        console.error("draw_image 执行失败:", error)
        complete({
            "success": False,
            "message": f"MiniMax 图片生成失败: {getErrorMessage(error)}",
            "error_stack": traceback.format_exc()
        })


exports.draw_image = draw_image_wrapper
