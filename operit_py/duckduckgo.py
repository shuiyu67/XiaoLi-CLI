# METADATA
# {
#     "name": "duckduckgo",
#
#     "display_name": {
#         "zh": "DuckDuckGo 搜索",
#         "en": "DuckDuckGo Search"
#     },
#     "description": { "zh": "使用DuckDuckGo进行网络搜索和内容抓取。", "en": "Use DuckDuckGo for web search and content extraction." },
#     "category": "Search",
#     "tools": [
#         {
#             "name": "search",
#             "description": { "zh": "执行DuckDuckGo搜索并返回格式化的结果。", "en": "Run a DuckDuckGo search and return formatted results." },
#             "parameters": [
#                 {
#                     "name": "query",
#                     "description": { "zh": "搜索查询字符串", "en": "Search query string." },
#                     "type": "string",
#                     "required": true
#                 },
#                 {
#                     "name": "max_results",
#                     "description": { "zh": "返回的最大结果数 (默认: 10)", "en": "Maximum number of results to return (default: 10)." },
#                     "type": "string",
#                     "required": false
#                 }
#             ]
#         },
#         {
#             "name": "fetch_content",
#             "description": { "zh": "从网页URL抓取和解析内容。", "en": "Fetch and parse content from a webpage URL." },
#             "parameters": [
#                 {
#                     "name": "url",
#                     "description": { "zh": "要抓取内容的网页URL", "en": "Webpage URL to fetch and parse." },
#                     "type": "string",
#                     "required": true
#                 }
#             ]
#         }
#     ]
# }

import re
import time
import asyncio
import traceback
from urllib.parse import unquote

client = OkHttp.newClient()
BASE_URL = "https://html.duckduckgo.com/html/"


class RateLimiter:
    """A simple rate limiter to avoid sending too many requests."""

    def __init__(self, requestsPerMinute=30):
        self.requestsPerMinute = requestsPerMinute
        self.requests = []

    async def acquire(self):
        now = time.time() * 1000
        # Remove requests older than 1 minute (60000 ms)
        self.requests = [reqTime for reqTime in self.requests if now - reqTime < 60000]

        if len(self.requests) >= self.requestsPerMinute:
            timeSinceFirstRequest = now - self.requests[0]
            waitTime = 60000 - timeSinceFirstRequest
            if waitTime > 0:
                await asyncio.sleep(waitTime / 1000)

        self.requests.append(time.time() * 1000)


searchRateLimiter = RateLimiter(30)
fetchRateLimiter = RateLimiter(20)


def decodeHtmlEntities(text):
    """Decodes basic HTML entities."""
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    return text


async def search(params):
    query = params.get("query")
    max_results = 10
    if params.get("max_results"):
        try:
            parsedMaxResults = int(params["max_results"])
            max_results = parsedMaxResults
        except (ValueError, TypeError):
            pass

    if not query:
        raise Exception("查询不能为空")

    await searchRateLimiter.acquire()
    console.log(f"正在从DuckDuckGo搜索: {query}")

    request = client.newRequest()
    request = request.url(BASE_URL)
    request = request.method("POST")
    request = request.body({"q": query, "b": "", "kl": ""}, "form")
    request = request.headers({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    })

    response = await request.build().execute()
    if not response.isSuccessful():
        raise Exception(f"HTTP 错误! 状态码: {response.statusCode}")

    html = response.content
    results = []
    resultRegex = re.compile(
        r'<h2 class="result__title">.*?<a.*?href="([^"]+)".*?>(.*?)</a>.*?</h2>.*?<a class="result__snippet".*?>(.*?)</a>',
        re.DOTALL
    )

    for match in resultRegex.finditer(html):
        if len(results) >= max_results:
            break

        link = match.group(1)
        if "y.js" in link:
            continue  # Skip ads

        if link.startswith("//duckduckgo.com/l/?uddg="):
            try:
                link = unquote(link.split("uddg=")[1].split("&")[0])
            except Exception as e:
                console.error(f"URL 解码失败: {link}")

        title = decodeHtmlEntities(re.sub(r'<[^>]*>', '', match.group(2)).strip())
        snippet = decodeHtmlEntities(re.sub(r'<[^>]*>', '', match.group(3)).strip())

        results.append({"title": title, "link": link, "snippet": snippet, "position": len(results) + 1})

    console.log(f"成功找到 {len(results)} 个结果")
    return format_results_for_llm(results)


async def fetch_content(params):
    url = params.get("url")
    if not url:
        raise Exception("URL不能为空")

    await fetchRateLimiter.acquire()
    console.log(f"正在抓取内容: {url}")

    try:
        request = client.newRequest()
        request = request.url(url)
        request = request.method("GET")
        request = request.headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

        response = await request.build().execute()
        if not response.isSuccessful():
            raise Exception(f"无法访问网页 ({response.statusCode})")

        text = response.content
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<nav[^>]*>.*?</nav>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<header[^>]*>.*?</header>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<footer[^>]*>.*?</footer>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) > 8000:
            text = text[:8000] + "... [内容被截断]"

        console.log(f"成功抓取并解析内容 ({len(text)} 字符)")
        return text
    except Exception as error:
        msg = str(getattr(error, "message", error))
        console.error(f"从 {url} 抓取内容时出错: {msg}")
        return f"错误: 从网页抓取内容时发生意外错误 ({msg})"


def format_results_for_llm(results):
    if not results or len(results) == 0:
        return "没有为您的搜索查询找到结果。这可能是由于DuckDuckGo的机器人检测或查询没有匹配项。请尝试重新措辞您的搜索或在几分钟后重试。"

    output = [
        f"{r['position']}. {r['title']}\n   URL: {r['link']}\n   摘要: {r['snippet']}"
        for r in results
    ]

    return f"找到 {len(results)} 个搜索结果:\n\n" + "\n\n".join(output)


async def duckduckgo_wrap(func, params, successMessage, failMessage):
    try:
        console.log(f"开始执行函数: {func.__name__ or '匿名函数'}")
        result = await func(params)
        complete({"success": True, "message": successMessage, "data": result})
    except Exception as error:
        msg = str(getattr(error, "message", error))
        console.error(f"函数 {func.__name__ or '匿名函数'} 执行失败! 错误: {msg}")
        complete({"success": False, "message": f"{failMessage}: {msg}", "error_stack": traceback.format_exc()})


async def search_wrapper(params):
    await duckduckgo_wrap(search, params, "搜索完成", "搜索失败")


async def fetch_content_wrapper(params):
    await duckduckgo_wrap(fetch_content, params, "内容抓取完成", "内容抓取失败")


exports.search = search_wrapper
exports.fetch_content = fetch_content_wrapper
