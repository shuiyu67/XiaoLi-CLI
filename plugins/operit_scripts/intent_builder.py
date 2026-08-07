# METADATA
# {
#     "name": "intent_builder",
#     "display_name": {
#         "zh": "Intent 意图构建器",
#         "en": "Intent Builder"
#     },
#     "description": {
#         "zh": "用 android.content.Intent 构建意图：ACTION_VIEW 打开 URL、ACTION_SEND 分享文本，解析 Uri，并用 Log 输出。",
#         "en": "Build intents with android.content.Intent: ACTION_VIEW for URLs, ACTION_SEND for sharing text, parse Uri, log via Log."
#     },
#     "category": "System",
#     "tools": [
#         {
#             "name": "build_view_intent",
#             "description": {
#                 "zh": "构建 ACTION_VIEW 意图（打开 URL）",
#                 "en": "Build ACTION_VIEW intent (open URL)"
#             },
#             "parameters": [
#                 { "name": "url", "description": { "zh": "要打开的网址", "en": "URL to open" }, "type": "string", "required": true }
#             ]
#         },
#         {
#             "name": "build_share_intent",
#             "description": {
#                 "zh": "构建 ACTION_SEND 分享意图",
#                 "en": "Build ACTION_SEND share intent"
#             },
#             "parameters": [
#                 { "name": "text", "description": { "zh": "分享的文本", "en": "Text to share" }, "type": "string", "required": true }
#             ]
#         }
#     ]
# }

TAG = "IntentBuilder"


async def build_view_intent(params):
    url = (params or {}).get("url", "")
    if not url:
        raise Exception("url 不能为空")
    intent = Intent(Intent.ACTION_VIEW)
    intent.setData(Uri.parse(url))
    Log.i(TAG, f"ACTION_VIEW -> {url}")
    result = {
        "action": intent.getAction(),
        "data": intent.getData(),
        "flags": intent.getFlags(),
        "resolved": intent.toString(),
    }
    complete({"success": True, "message": "意图构建成功（桌面环境不实际拉起）", "data": result})
    return result


async def build_share_intent(params):
    text = (params or {}).get("text", "")
    if not text:
        raise Exception("text 不能为空")
    intent = Intent(Intent.ACTION_SEND)
    intent.setType("text/plain")
    intent.putExtra(Intent.EXTRA_TEXT, text)
    Log.i(TAG, f"ACTION_SEND: {text[:40]}")
    result = {
        "action": intent.getAction(),
        "type": intent.getType(),
        "extras": intent.getExtras(),
        "resolved": intent.toString(),
    }
    complete({"success": True, "message": "分享意图构建成功", "data": result})
    return result


exports.build_view_intent = build_view_intent
exports.build_share_intent = build_share_intent
