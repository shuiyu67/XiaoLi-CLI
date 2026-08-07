# METADATA
# {
#     "name": "beeimg_image_uploader_v2",
#
#     "display_name": {
#         "zh": "Beeimg 图片上传器 V2",
#         "en": "Beeimg Image Uploader V2"
#     },
#     "description": {
#         "zh": "BeeIMG（https://beeimg.com/）工具将本地图片上传到图床并返回图片url，配合图片生成工具实现图生图（图生图务必开启）。",
#         "en": "Upload a local image to BeeIMG (https://beeimg.com/) and return a public image URL. Useful for image-to-image workflows (make sure img2img is enabled)."
#     },
#     "env": [
#         "BEEIMG_API_KEY"
#     ],
#     "category": "Media",
#     "tools": [
#         {
#             "name": "upload_image",
#             "description": {
#                 "zh": "使用 multipart 上传将本地图片上传到 BeeIMG 图床并返回图片 url。",
#                 "en": "Upload a local image to BeeIMG via multipart upload and return the image URL."
#             },
#             "parameters": [
#                 { "name": "file_path", "description": { "zh": "要上传的图片文件绝对路径 (建议使用 /sdcard/ 开头的完整路径)。", "en": "Absolute path of the image file to upload (recommended: full path starting with /sdcard/)." }, "type": "string", "required": true },
#                 { "name": "album_id", "description": { "zh": "相册ID (可选)。", "en": "Album ID (optional)." }, "type": "string", "required": false },
#                 { "name": "privacy", "description": { "zh": "隐私设置，'public' 或 'private' (可选)。", "en": "Privacy setting: 'public' or 'private' (optional)." }, "type": "string", "required": false }
#             ]
#         }
#     ]
# }

import json
import traceback

API_ENDPOINT = "https://beeimg.com/api/upload/file/json/"


def isRecord(value):
    return isinstance(value, dict)


def getErrorMessage(error):
    if isinstance(error, Exception):
        return str(error)
    return str(error)


def getErrorStack(error):
    if isinstance(error, Exception):
        return traceback.format_exc()
    return None


def getApiKey():
    return getEnv("BEEIMG_API_KEY") or ""


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
    trimmed = (text or "").strip()
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


async def upload_image(params):
    file_path = params.get("file_path") if params else None
    album_id = params.get("album_id") if params else None
    privacy = params.get("privacy") if params else None

    if not file_path or len(str(file_path).strip()) == 0:
        raise Exception("参数 file_path 不能为空。")

    # 1. 检查文件是否存在
    fileExists = await Tools.Files.exists(file_path)
    if not fileExists["exists"]:
        raise Exception(f"文件未找到: {file_path} (请尝试使用 /sdcard/ 开头的绝对路径)")

    # 2. 准备参数
    apiKey = getApiKey()
    if not apiKey:
        raise Exception("BEEIMG_API_KEY 未配置，请在环境变量中设置 BeeIMG 的 API Key。")

    form_data = {
        "apikey": apiKey
    }
    if album_id:
        form_data["albumid"] = str(album_id)
    if privacy:
        form_data["privacy"] = str(privacy)

    # 3. 发起 multipart 上传
    console.log("正在执行上传...")

    resp = await Tools.Net.uploadFile({
        "url": API_ENDPOINT,
        "method": "POST",
        "headers": {
            # 尽量模拟浏览器 UA，降低被风控概率
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36"
        },
        "form_data": form_data,
        "files": [
            {
                "field_name": "file",
                "file_path": file_path,
                "content_type": guessMimeTypeFromPath(file_path)
            }
        ]
    })

    if resp["statusCode"] < 200 or resp["statusCode"] >= 300:
        raise Exception(f"上传请求失败 (HTTP {resp['statusCode']})。可能是网络问题或 IP 被屏蔽。\n响应: {resp['content']}")

    responseText = (resp.get("content") or "").strip()
    if not responseText:
        raise Exception("上传失败：服务器返回了空内容。请检查网络连接或尝试关闭 VPN。")

    try:
        jsonResponse = safeJsonParseLoose(responseText)
    except Exception as e:
        raise Exception(f"API 响应解析失败。服务器返回内容不是 JSON:\n{responseText[:200]}...")

    files = jsonResponse["files"] if isRecord(jsonResponse) and isRecord(jsonResponse.get("files")) else None
    ok = bool(files) and (files.get("status") == "Success" or files.get("code") == "200" or files.get("code") == 200)
    url = files.get("url") if files else None

    if ok and (isinstance(url, str) or isinstance(url, (int, float))) and len(str(url).strip()) > 0:
        return {
            "url": str(url),
            "thumbnail_url": str(files["thumbnail_url"]) if files and files.get("thumbnail_url") else None,
            "page_url": str(files["view_url"]) if files and files.get("view_url") else None,
            "details": f"上传成功! URL: {str(url)}"
        }
    else:
        if files:
            errMsg = files.get("status") or files.get("message") or json.dumps(files, ensure_ascii=False)
        else:
            errMsg = "未知错误"
        raise Exception(f"BeeIMG API 报错: {errMsg}")


async def wrap(func, params):
    try:
        result = await func(params)
        complete({"success": True, "message": "图片上传成功", "data": result})
    except Exception as error:
        console.error(f"Error: {getErrorMessage(error)}")
        complete({"success": False, "message": getErrorMessage(error), "error_stack": getErrorStack(error)})


async def upload_image_wrapper(params):
    await wrap(upload_image, params)


exports.upload_image = upload_image_wrapper
