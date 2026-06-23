# METADATA
# {
#     "name": "google_search",
#
#     "display_name": {
#         "zh": "Google 搜索",
#         "en": "Google Search"
#     },
#     "description": {
#         "zh": "提供 Google 普通搜索与 Google Scholar 学术搜索能力，支持设置语言与返回条数。",
#         "en": "Google web search and Google Scholar search, with configurable language and result count."
#     },
#     "enabledByDefault": false,
#     "category": "Search",
#     "tools": [
#         {
#             "name": "search_web",
#             "description": { "zh": "执行 Google 普通搜索，返回网页搜索结果。", "en": "Perform a regular Google search and return web results." },
#             "parameters": [
#                 { "name": "query", "description": { "zh": "搜索关键词", "en": "Search query" }, "type": "string", "required": true },
#                 { "name": "max_results", "description": { "zh": "返回结果数量，默认 10，最大 20", "en": "Number of results to return (default: 10, max: 20)" }, "type": "number", "required": false },
#                 { "name": "language", "description": { "zh": "界面语言参数，默认 en", "en": "Interface language (default: en)" }, "type": "string", "required": false },
#                 { "name": "region", "description": { "zh": "地区参数，例如 us、cn。默认 us", "en": "Region parameter, e.g. us, cn (default: us)" }, "type": "string", "required": false },
#                 { "name": "includeLinks", "description": { "zh": "是否在结果中包含可点击的链接列表，默认为false。", "en": "Whether to include a clickable link list in results (default: false)" }, "type": "boolean", "required": false }
#             ]
#         },
#         {
#             "name": "search_scholar",
#             "description": { "zh": "执行 Google Scholar 学术搜索，返回学术文献结果。", "en": "Perform a Google Scholar search and return academic results." },
#             "parameters": [
#                 { "name": "query", "description": { "zh": "搜索关键词", "en": "Search query" }, "type": "string", "required": true },
#                 { "name": "max_results", "description": { "zh": "返回结果数量，默认 10，最大 20", "en": "Number of results to return (default: 10, max: 20)" }, "type": "number", "required": false },
#                 { "name": "language", "description": { "zh": "界面语言参数，默认 en", "en": "Interface language (default: en)" }, "type": "string", "required": false },
#                 { "name": "includeLinks", "description": { "zh": "是否在结果中包含可点击的链接列表，默认为false。", "en": "Whether to include a clickable link list in results (default: false)" }, "type": "boolean", "required": false }
#             ]
#         },
#         {
#             "name": "search_scholar_mirror",
#             "description": { "zh": "通过镜像站执行 Google Scholar 学术搜索，以绕过人机验证。", "en": "Use a mirror site to perform Google Scholar searches to bypass CAPTCHA checks." },
#             "parameters": [
#                 { "name": "query", "description": { "zh": "搜索关键词", "en": "Search query" }, "type": "string", "required": true },
#                 { "name": "max_results", "description": { "zh": "返回结果数量，默认 10，最大 20", "en": "Number of results to return (default: 10, max: 20)" }, "type": "number", "required": false },
#                 { "name": "language", "description": { "zh": "界面语言参数，默认 en", "en": "Interface language (default: en)" }, "type": "string", "required": false },
#                 { "name": "includeLinks", "description": { "zh": "是否在结果中包含可点击的链接列表，默认为false。", "en": "Whether to include a clickable link list in results (default: false)" }, "type": "boolean", "required": false }
#             ]
#         }
#     ]
# }

import json
import re
from urllib.parse import quote

GOOGLE_SEARCH_URL = "https://www.google.com/search"
GOOGLE_SCHOLAR_URL = "https://scholar.google.com/scholar"
GOOGLE_SCHOLAR_MIRRORS = [
    "https://xs.cntpj.com/scholar",
]
MAX_RESULTS = 20


def buildUrl(base, params):
    queryString = "&".join(f"{quote(k)}={quote(v)}" for k, v in params.items())
    return f"{base}?{queryString}"


def getHostname(rawUrl):
    match = re.match(r'^[a-zA-Z][a-zA-Z\d+\-.]*:\/\/([^/?#]+)', rawUrl.strip())
    if not match or not match.group(1):
        return rawUrl
    authority = match.group(1)
    host = authority.split("@")[-1] or authority if "@" in authority else authority
    return re.sub(r':\d+$', '', host)


async def fetchHtmlViaWebVisit(url):
    result = await Tools.Net.visit(url)
    # The result can be a string if the underlying tool returns a simple string.
    # We'll normalize it to a dict object.
    if isinstance(result, str):
        return {
            "url": url,
            "title": "",
            "content": result,
            "links": [],
        }
    return result


# 解析相关逻辑已移除，直接返回 visit 的纯文本结果

async def performSearch(url, includeLinks=False, sourceName=""):
    try:
        result = await fetchHtmlViaWebVisit(url)
        content = result.get("content", "") if isinstance(result, dict) else ""

        parts = []
        if isinstance(result, dict) and result.get("visitKey"):
            parts.append(f"visit_key: {result['visitKey']}")
        if includeLinks and isinstance(result, dict) and result.get("links") and len(result["links"]) > 0:
            linksLines = [f"[{index + 1}] {link.get('text')}" for index, link in enumerate(result["links"])]
            parts.append("\n".join(linksLines))
        parts.append(content)

        return {
            "success": True,
            "message": f"{sourceName} 搜索成功",
            "data": "\n\n".join(parts)
        }
    except Exception as error:
        msg = str(getattr(error, "message", error))
        return {
            "success": False,
            "message": f"{sourceName} 搜索失败: {msg}"
        }


async def searchWeb(params):
    if not params.get("query") or params.get("query", "").strip() == "":
        raise Exception("请提供有效的 query 参数。")
    maxResults = min(max(params.get("max_results") or 10, 1), MAX_RESULTS)
    language = params.get("language") or "en"
    region = params.get("region") or "us"
    url = buildUrl(GOOGLE_SEARCH_URL, {
        "q": params["query"],
        "hl": language,
        "gl": region,
        "num": str(maxResults),
        "pws": "0",
    })

    return await performSearch(url, params.get("includeLinks"), "Google")


async def searchScholar(params):
    if not params.get("query") or params.get("query", "").strip() == "":
        raise Exception("请提供有效的 query 参数。")
    maxResults = min(max(params.get("max_results") or 10, 1), MAX_RESULTS)
    language = params.get("language") or "en"
    url = buildUrl(GOOGLE_SCHOLAR_URL, {
        "q": params["query"],
        "hl": language,
        "as_sdt": "0,5",
        "num": str(maxResults)
    })

    return await performSearch(url, params.get("includeLinks"), "Google Scholar")


async def searchScholarMirror(params):
    if not params.get("query") or params.get("query", "").strip() == "":
        raise Exception("请提供有效的 query 参数。")
    maxResults = min(max(params.get("max_results") or 10, 1), MAX_RESULTS)
    language = params.get("language") or "en"

    mirrorUrls = [
        buildUrl(mirror, {
            "q": params["query"],
            "hl": language,
            "as_sdt": "0,5",
            "num": str(maxResults)
        })
        for mirror in GOOGLE_SCHOLAR_MIRRORS
    ]

    if len(mirrorUrls) == 0:
        return {
            "success": False,
            "message": "没有可用的 Google Scholar 镜像地址。"
        }

    lastError = None

    for currentUrl in mirrorUrls:
        try:
            searchResult = await performSearch(currentUrl, params.get("includeLinks"), f"Google Scholar 镜像 ({getHostname(currentUrl)})")
            if searchResult.get("success") and searchResult.get("data"):
                # Check for CAPTCHA in the content
                if "recaptcha" in searchResult["data"] or "人机身份验证" in searchResult["data"]:
                    raise Exception("CAPTCHA required")
                return searchResult
            # If performSearch itself fails, it will throw and be caught below.
        except Exception as error:
            lastError = error
            msg = str(getattr(error, "message", error))
            console.log(f"Attempt with {currentUrl} failed: {msg}")

    errMsg = str(getattr(lastError, "message", lastError)) if lastError else "Unknown error"
    return {
        "success": False,
        "message": f"Google Scholar 镜像搜索在尝试所有镜像后失败: {errMsg}"
    }


async def main():
    console.log("--- Testing Web Search ---")
    webResult = await searchWeb({"query": "TypeScript"})
    console.log(json.dumps(webResult, indent=2, ensure_ascii=False))

    console.log("\n--- Testing Scholar Search ---")
    scholarResult = await searchScholar({"query": "Large Language Models"})
    console.log(json.dumps(scholarResult, indent=2, ensure_ascii=False))

    console.log("\n--- Testing Scholar Mirror Search ---")
    scholarMirrorResult = await searchScholarMirror({"query": "Quantum Computing"})
    console.log(json.dumps(scholarMirrorResult, indent=2, ensure_ascii=False))


def wrap(coreFunction):
    async def wrapped(params):
        # The core function expects the params object directly.
        return await coreFunction(params)
    return wrapped


exports.search_web = wrap(searchWeb)
exports.search_scholar = wrap(searchScholar)
exports.search_scholar_mirror = wrap(searchScholarMirror)
exports.main = main
