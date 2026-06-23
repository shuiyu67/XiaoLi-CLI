# METADATA
# {
#   "name": "zhipu_draw",
#   "display_name": {
#     "zh": "智谱生图",
#     "en": "Zhipu Draw"
#   },
#   "description": {
#     "zh": "使用智谱AI图像生成API根据提示词画图，将图片保存到本地 /sdcard/Download/Operit/plugins/draw/zhipu_draw/draws/ 目录，并返回 Markdown 图片提示。",
#     "en": "Generate images via Zhipu AI image generation API from a prompt, save to /sdcard/Download/Operit/plugins/draw/zhipu_draw/draws/, and return a Markdown image reference."
#   },
#   "env": [
#     {
#       "name": "ZHIPU_API_KEY",
#       "description": {
#         "zh": "智谱API Key（必填）",
#         "en": "Zhipu API key (required)"
#       },
#       "required": true
#     },
#     {
#       "name": "ZHIPU_IMAGE_MODEL",
#       "description": {
#         "zh": "默认绘图模型（可选；当 draw_image 未传 model 时使用）",
#         "en": "Default image model (optional; used when draw_image doesn't pass model)"
#       },
#       "required": false
#     }
#   ],
#   "category": "Draw",
#   "tools": [
#     {
#       "name": "draw_image",
#       "description": {
#         "zh": "根据提示词调用智谱AI图像生成接口生成图片，保存到本地并返回 Markdown 图片提示。",
#         "en": "Generate an image via Zhipu AI image generation API using a prompt, save it locally, and return a Markdown image reference."
#       },
#       "parameters": [
#         { "name": "prompt", "description": { "zh": "绘图提示词（中文或英文）", "en": "Prompt for image generation (Chinese or English)" }, "type": "string", "required": true },
#         { "name": "size", "description": { "zh": "图片尺寸，例如 '1024x1024' 或 '1280x1280'（可选，默认1024x1024）", "en": "Image size, e.g. '1024x1024' or '1280x1280' (optional, default 1024x1024)" }, "type": "string", "required": false },
#         { "name": "file_name", "description": { "zh": "自定义保存到本地的文件名（不含路径和扩展名）", "en": "Custom output file name (without path or extension)" }, "type": "string", "required": false },
#         { "name": "model", "description": { "zh": "模型名称（可选；不传则使用环境变量 ZHIPU_IMAGE_MODEL，否则默认glm-image）", "en": "Model name (optional; falls back to env ZHIPU_IMAGE_MODEL)" }, "type": "string", "required": false }
#       ]
#     }
#   ]
# }

import json
import re
import time
import traceback

HTTP_TIMEOUT_MS = 600000
client = OkHttp.newBuilder()
client = client.connectTimeout(HTTP_TIMEOUT_MS)
client = client.readTimeout(HTTP_TIMEOUT_MS)
client = client.writeTimeout(HTTP_TIMEOUT_MS)
client = client.build()

API_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/images/generations"
DRAW_ROOT_DIR = getPluginConfigDir("draw")
STORAGE_DIR = f"{DRAW_ROOT_DIR}/zhipu_draw"
DRAWS_DIR = f"{STORAGE_DIR}/draws"


def getErrorMessage(error):
    if isinstance(error, Exception):
        return str(error)
    return str(error)


def getErrorStack(error):
    if isinstance(error, Exception):
        return traceback.format_exc()
    return None


def getApiKey():
    apiKey = getEnv("ZHIPU_API_KEY")
    if not apiKey:
        raise Exception("ZHIPU_API_KEY 未配置，请在环境变量中设置智谱的 API Key。")
    return apiKey


def sanitizeFileName(name):
    safe = re.sub(r'[\\/:*?"<>|]', '_', name).strip()
    if not safe:
        return f"zhipu_draw_{int(time.time() * 1000)}"
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
            console.warn(f"创建目录异常: {dir_} -> {getErrorMessage(e)}")


async def callZhipuImageAPI(params):
    apiKey = getApiKey()
    modelFromParam = (params.get("model") or "").strip()
    modelFromEnv = (getEnv("ZHIPU_IMAGE_MODEL") or "").strip()
    effectiveModel = modelFromParam or modelFromEnv or "glm-image"

    body = {
        "model": effectiveModel,
        "prompt": params["prompt"],
        "size": params.get("size") or "1024x1024"
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {apiKey}"
    }

    request = client.newRequest()
    request = request.url(API_BASE_URL)
    request = request.method("POST")
    request = request.headers(headers)
    request = request.body(json.dumps(body), "json")

    response = await request.build().execute()

    if not response.isSuccessful():
        raise Exception(f"智谱图片 API 调用失败: {response.statusCode} - {response.content}")

    try:
        parsed = json.loads(response.content)
    except Exception as e:
        raise Exception(f"解析智谱响应失败: {getErrorMessage(e)}")

    data = parsed.get("data") if isinstance(parsed, dict) else None
    first = data[0] if (data and len(data) > 0) else None
    if not first or not first.get("url"):
        raise Exception("智谱响应中未找到有效的图片数据，请检查API返回格式")

    result = {
        "url": str(first["url"]),
        "model": str(first["model"]) if first.get("model") else None
    }

    if not result["model"]:
        result["model"] = effectiveModel

    return result


async def draw_image(params):
    if not params or not params.get("prompt") or len(params.get("prompt", "").strip()) == 0:
        raise Exception("参数 prompt 不能为空。")

    prompt = params["prompt"].strip()
    size = params.get("size") or "1024x1024"
    model = params.get("model")

    await ensureDirectories()

    apiResult = await callZhipuImageAPI({"prompt": prompt, "size": size, "model": model})

    if not apiResult["url"] or not apiResult["url"].strip():
        raise Exception("API响应中未包含图片URL")

    baseName = buildFileName(prompt, params.get("file_name"))
    filePath = f"{DRAWS_DIR}/{baseName}.png"

    downloadResult = await Tools.Files.download(apiResult["url"], filePath)
    if not downloadResult.get("successful"):
        raise Exception(f"下载图片失败: {downloadResult.get('details')}")

    fileUri = f"file://{filePath}"
    markdown = f"![AI生成的图片]({fileUri})"

    hintLines = []
    hintLines.append(f"图片已生成并保存在本地 {DRAWS_DIR}。")
    hintLines.append(f"本地路径: {filePath}")
    hintLines.append(f"提示词: {prompt}")
    hintLines.append(f"模型: {apiResult.get('model') or 'glm-image'}")
    hintLines.append("")
    hintLines.append("在后续回答中，请直接输出下面这一行 Markdown 来展示这张图片：")
    hintLines.append("")
    hintLines.append(markdown)

    return {
        "file_path": filePath,
        "file_uri": fileUri,
        "markdown": markdown,
        "prompt": prompt,
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
