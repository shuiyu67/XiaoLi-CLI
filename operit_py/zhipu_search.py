# METADATA
# {
#   "name": "zhipu_search",
#   "display_name": {
#     "zh": "智谱搜索",
#     "en": "Zhipu Search"
#   },
#   "description": {
#     "zh": "智谱 AI 独立网络搜索 API，返回结构化搜索结果。",
#     "en": "Zhipu AI standalone web search API with structured results."
#   },
#   "author": "浮生一梦",
#   "env": [
#     {
#       "name": "ZHIPU_SEARCH_API_KEY",
#       "description": {
#         "zh": "智谱搜索专用 API Key（与生图 Key 独立）",
#         "en": "Zhipu Search API Key (independent from draw Key)"
#       },
#       "required": false
#     }
#   ],
#   "category": "Search",
#   "tools": [
#     {
#       "name": "search",
#       "description": {
#         "zh": "使用智谱 Web Search API 进行搜索",
#         "en": "Search using Zhipu Web Search API"
#       },
#       "parameters": [
#         { "name": "query", "description": { "zh": "搜索关键词", "en": "Search query" }, "type": "string", "required": true },
#         { "name": "api_key", "description": { "zh": "智谱 API Key（可选，不传则读取环境变量）", "en": "Zhipu API Key" }, "type": "string", "required": false },
#         { "name": "engine", "description": { "zh": "搜索引擎：search_std/search_pro/search_pro_sogou/search_pro_quark", "en": "Search engine" }, "type": "string", "required": false },
#         { "name": "count", "description": { "zh": "返回结果数 (1-50)，默认 10", "en": "Result count (1-50)" }, "type": "number", "required": false },
#         { "name": "recency", "description": { "zh": "时间范围：oneDay/oneWeek/oneMonth/oneYear/noLimit", "en": "Time range" }, "type": "string", "required": false },
#         { "name": "content_size", "description": { "zh": "内容长度：medium/high", "en": "Content size" }, "type": "string", "required": false }
#       ]
#     },
#     {
#       "name": "test",
#       "description": {
#         "zh": "测试 API 连接",
#         "en": "Test API connection"
#       },
#       "parameters": []
#     }
#   ]
# }

import json
import time
import traceback

API_URL = "https://open.bigmodel.cn/api/paas/v4/web_search"
TIMEOUT = 60000
client = OkHttp.newBuilder()
client = client.connectTimeout(TIMEOUT)
client = client.readTimeout(TIMEOUT)
client = client.writeTimeout(TIMEOUT)
client = client.build()


def getApiKey(providedKey=None):
    if providedKey:
        return providedKey
    key = getEnv("ZHIPU_SEARCH_API_KEY")
    if key:
        return key
    key = getEnv("DEFAULT_API_KEY")
    return key or ""


async def httpPost(body, apiKey=None):
    key = getApiKey(apiKey)
    if not key:
        raise Exception("未设置 API Key，请配置 ZHIPU_SEARCH_API_KEY 环境变量或在调用时传入 api_key 参数")

    request = client.newRequest()
    request = request.url(API_URL)
    request = request.method("POST")
    request = request.header("Authorization", "Bearer " + key)
    request = request.header("Content-Type", "application/json")
    request = request.body(json.dumps(body), "json")

    response = await request.build().execute()
    content = response.content

    if not response.isSuccessful():
        raise Exception("HTTP " + str(response.statusCode) + ": " + content)

    return json.loads(content)


async def search(params):
    body = {
        "search_query": params["query"],
        "search_engine": params.get("engine") or "search_std",
        "search_intent": True,
        "count": params.get("count") or 10,
        "content_size": params.get("content_size") or "medium"
    }

    if params.get("recency"):
        body["search_recency_filter"] = params["recency"]

    result = await httpPost(body, params.get("api_key"))

    results = []
    if result.get("search_result") and isinstance(result["search_result"], list):
        results = [
            {
                "title": item.get("title"),
                "content": item.get("content"),
                "link": item.get("link"),
                "media": item.get("media"),
                "icon": item.get("icon"),
                "publish_date": item.get("publish_date"),
                "refer": item.get("refer")
            }
            for item in result["search_result"]
        ]

    intent = None
    if result.get("search_intent") and len(result["search_intent"]) > 0:
        intent = result["search_intent"][0] or None

    return {
        "success": True,
        "query": params["query"],
        "id": result.get("id"),
        "intent": intent,
        "results": results,
        "count": len(results)
    }


async def test():
    body = {
        "search_query": "hi",
        "search_engine": "search_std",
        "search_intent": False,
        "count": 1
    }

    start = time.time() * 1000
    result = await httpPost(body, None)
    latency = time.time() * 1000 - start

    return {
        "success": True,
        "latency": latency,
        "id": result.get("id")
    }


async def searchWrapper(params):
    try:
        result = await search(params)
        complete({
            "success": True,
            "message": "搜索完成，找到 " + str(result["count"]) + " 条结果",
            "data": result
        })
    except Exception as error:
        msg = str(getattr(error, "message", error))
        complete({
            "success": False,
            "message": "搜索失败：" + msg,
            "error_stack": traceback.format_exc()
        })


async def testWrapper():
    try:
        result = await test()
        complete({
            "success": True,
            "message": "连接成功，延迟 " + str(result["latency"]) + "ms",
            "data": result
        })
    except Exception as error:
        msg = str(getattr(error, "message", error))
        complete({
            "success": False,
            "message": "测试失败：" + msg,
            "error_stack": traceback.format_exc()
        })


exports.search = searchWrapper
exports.test = testWrapper
