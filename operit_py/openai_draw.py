# METADATA
# {
#   "name": "openai_draw",
#
#   "display_name": {
#       "zh": "OpenAI 绘图",
#       "en": "OpenAI Draw"
#   },
#   "description": {
#     "zh": "使用 OpenAI 格式的图像生成 API (/v1/images/generations) 根据提示词画图，将图片保存到本地 /sdcard/Download/Operit/plugins/draw/openai_draw/draws/ 目录，并返回 Markdown 图片提示。",
#     "en": "Generate images via an OpenAI-compatible image generation API (/v1/images/generations) from a prompt, save to /sdcard/Download/Operit/plugins/draw/openai_draw/draws/, and return a Markdown image reference."
#   },
#   "category": "Draw",
#   "env": [
#     {
#       "name": "OPENAI_API_KEY",
#       "description": {
#         "zh": "OpenAI API Key（必填）",
#         "en": "OpenAI API key (required)"
#       },
#       "required": true
#     },
#     {
#       "name": "OPENAI_API_BASE_URL",
#       "description": {
#         "zh": "OpenAI API Base URL（可选，不填则默认 https://api.openai.com ）",
#         "en": "OpenAI API base URL (optional; defaults to https://api.openai.com)"
#       },
#       "required": false
#     },
#     {
#       "name": "OPENAI_IMAGE_MODEL",
#       "description": {
#         "zh": "默认绘图模型（可选；当 draw_image 未传 model 时使用）",
#         "en": "Default image model (optional; used when draw_image doesn't pass model)"
#       },
#       "required": false
#     }
#   ],
#   "tools": [
#     {
#       "name": "draw_image",
#       "description": {
#         "zh": "根据提示词调用 OpenAI 格式图像生成接口生成图片，保存到本地并返回 Markdown 图片提示。",
#         "en": "Generate an image via an OpenAI-compatible image generation endpoint using a prompt, save it locally, and return a Markdown image reference."
#       },
#       "parameters": [
#         { "name": "prompt", "description": { "zh": "绘图提示词（英文或中文皆可）", "en": "Prompt for image generation (Chinese or English)" }, "type": "string", "required": true },
#         { "name": "model", "description": { "zh": "模型名称（可选；不传则使用环境变量 OPENAI_IMAGE_MODEL，再不行使用默认值）", "en": "Model name (optional; falls back to env OPENAI_IMAGE_MODEL, then default)" }, "type": "string", "required": false },
#         { "name": "size", "description": { "zh": "图片尺寸，例如 '1024x1024'，可选", "en": "Image size, e.g. '1024x1024' (optional)" }, "type": "string", "required": false },
#         { "name": "file_name", "description": { "zh": "自定义保存到本地的文件名（不含路径和扩展名）", "en": "Custom output file name (without path or extension)" }, "type": "string", "required": false },
#         { "name": "api_base_url", "description": { "zh": "OpenAI API Base URL（不传则取环境变量 OPENAI_API_BASE_URL 或默认 https://api.openai.com ）", "en": "OpenAI API base URL (optional; falls back to env OPENAI_API_BASE_URL or https://api.openai.com)" }, "type": "string", "required": false }
#       ]
#     }
#   ]
# }

import json
import re
import time
import random
import traceback

HTTP_TIMEOUT_MS = 600000
client = OkHttp.newBuilder()
client = client.connectTimeout(HTTP_TIMEOUT_MS)
client = client.readTimeout(HTTP_TIMEOUT_MS)
client = client.writeTimeout(HTTP_TIMEOUT_MS)
client = client.build()
DEFAULT_API_BASE_URL = "https://api.openai.com"
DEFAULT_MODEL = "gpt-image-1"

DRAW_ROOT_DIR = getPluginConfigDir("draw")
STORAGE_DIR = f"{DRAW_ROOT_DIR}/openai_draw"
DRAWS_DIR = f"{STORAGE_DIR}/draws"


def getApiKey():
    apiKey = getEnv("OPENAI_API_KEY")
    if not apiKey:
        raise Exception("OPENAI_API_KEY 未配置，请在环境变量中设置 OpenAI 的 API Key。")
    return apiKey


def joinUrl(baseUrl, path):
    normalizedBase = baseUrl if baseUrl.endswith("/") else baseUrl + "/"
    normalizedPath = path[1:] if path.startswith("/") else path
    return normalizedBase + normalizedPath


def getApiBaseUrl(customBaseUrl=None):
    fromParam = (customBaseUrl or "").strip()
    if fromParam:
        return fromParam

    fromEnv = (getEnv("OPENAI_API_BASE_URL") or "").strip()
    if fromEnv:
        return fromEnv

    return DEFAULT_API_BASE_URL


def getImageEndpoint(baseUrl):
    trimmed = baseUrl.strip()
    if not trimmed:
        return joinUrl(DEFAULT_API_BASE_URL, "v1/images/generations")

    if "/v1/images/generations" in trimmed:
        return trimmed

    # If user passes .../v1, we should append images/generations
    if trimmed.endswith("/v1") or trimmed.endswith("/v1/"):
        return joinUrl(trimmed, "images/generations")

    # Otherwise append v1/images/generations
    return joinUrl(trimmed, "v1/images/generations")


def sanitizeFileName(name):
    safe = re.sub(r'[\\/:*?"<>|]', '_', name).strip()
    if not safe:
        return f"openai_draw_{int(time.time() * 1000)}"
    return safe[:80]


def buildFileName(prompt, customName=None):
    if customName and len(customName.strip()) > 0:
        return sanitizeFileName(customName)
    shortPrompt = (prompt[:40] + "...") if len(prompt) > 40 else prompt
    base = sanitizeFileName(shortPrompt or "image")
    timestamp = int(time.time() * 1000)
    return f"{base}_{timestamp}"


async def ensureDirectories():
    dirs = [DRAW_ROOT_DIR, STORAGE_DIR, DRAWS_DIR]
    for dir_ in dirs:
        try:
            result = await Tools.Files.mkdir(dir_)
            if not result.get("successful"):
                console.warn(f"创建目录失败(可能已存在): {dir_} -> {result.get('details')}")
        except Exception as e:
            console.warn(f"创建目录异常: {dir_} -> {getattr(e, 'message', e)}")


def normalizeBase64(base64):
    raw = str(base64 or "").strip()
    if not raw:
        return raw

    # Some providers may return: data:image/png;base64,xxxx
    prefixIndex = raw.find("base64,")
    if raw.startswith("data:") and prefixIndex >= 0:
        return raw[prefixIndex + len("base64,"):].strip()

    return raw


async def callOpenAIImageApi(params):
    apiKey = getApiKey()
    apiBaseUrl = getApiBaseUrl(params.get("api_base_url"))
    endpoint = getImageEndpoint(apiBaseUrl)

    modelFromParam = (params.get("model") or "").strip()
    modelFromEnv = (getEnv("OPENAI_IMAGE_MODEL") or "").strip()
    effectiveModel = modelFromParam or modelFromEnv or DEFAULT_MODEL

    body = {
        "model": effectiveModel,
        "prompt": params["prompt"],
        "response_format": "b64_json"
    }

    if params.get("size") and len(params["size"].strip()) > 0:
        body["size"] = params["size"].strip()

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {apiKey}"
    }

    request = client.newRequest()
    request = request.url(endpoint)
    request = request.method("POST")
    request = request.headers(headers)
    request = request.body(json.dumps(body), "json")

    response = await request.build().execute()

    if not response.isSuccessful():
        raise Exception(f"OpenAI 图片 API 调用失败: {response.statusCode} - {response.content}")

    try:
        parsed = json.loads(response.content)
    except Exception as e:
        msg = str(getattr(e, "message", e))
        raise Exception(f"解析 OpenAI 响应失败: {msg}")

    data = parsed.get("data") if isinstance(parsed, dict) else None
    item = data[0] if (data and len(data) > 0) else None
    if not item:
        raise Exception("OpenAI 响应中未找到 data[0]，请检查接口返回格式。")

    if item.get("b64_json") and len(str(item["b64_json"]).strip()) > 0:
        return {
            "b64_json": str(item["b64_json"]),
            "revised_prompt": str(item["revised_prompt"]) if item.get("revised_prompt") else None,
            "effective_model": effectiveModel
        }

    if item.get("url") and len(str(item["url"]).strip()) > 0:
        # Some OpenAI-compatible APIs may return url only. We download it, then read as base64.
        tmpName = f"openai_tmp_{int(time.time() * 1000)}"
        tmpPath = f"{DRAWS_DIR}/{tmpName}.png"
        downloadResult = await Tools.Files.download(str(item["url"]), tmpPath)
        if not downloadResult.get("successful"):
            raise Exception(f"下载图片失败: {downloadResult.get('details')}")

        readBinary = await Tools.Files.readBinary(tmpPath)
        contentBase64 = readBinary.get("contentBase64") if isinstance(readBinary, dict) else None
        if not contentBase64 or len(str(contentBase64).strip()) == 0:
            raise Exception("读取下载图片失败: contentBase64 为空")

        try:
            await Tools.Files.deleteFile(tmpPath)
        except Exception:
            # ignore
            pass

        return {
            "b64_json": str(contentBase64),
            "revised_prompt": str(item["revised_prompt"]) if item.get("revised_prompt") else None,
            "effective_model": effectiveModel
        }

    raise Exception("OpenAI 响应中未找到 b64_json 或 url，请检查模型/参数以及接口兼容性。")


async def draw_image(params):
    if not params or not params.get("prompt") or len(params.get("prompt", "").strip()) == 0:
        raise Exception("参数 prompt 不能为空。")

    prompt = params["prompt"].strip()

    await ensureDirectories()

    apiResult = await callOpenAIImageApi({
        "prompt": prompt,
        "model": params.get("model"),
        "size": params.get("size"),
        "api_base_url": params.get("api_base_url")
    })

    baseName = buildFileName(prompt, params.get("file_name"))
    filePath = f"{DRAWS_DIR}/{baseName}.png"

    writeResult = await Tools.Files.writeBinary(filePath, normalizeBase64(apiResult["b64_json"]))
    if not writeResult.get("successful"):
        raise Exception(f"保存图片失败: {writeResult.get('details')}")

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
        "revised_prompt": apiResult.get("revised_prompt") or None,
        "model": apiResult["effective_model"],
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
        msg = str(getattr(error, "message", error))
        stack = traceback.format_exc() if isinstance(error, Exception) else None
        complete({
            "success": False,
            "message": f"图片生成失败: {msg}",
            "error_stack": stack
        })


exports.draw_image = draw_image_wrapper
