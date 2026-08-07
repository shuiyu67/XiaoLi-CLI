# METADATA
# {
#     "name": "market_duckduckgo",
#     "display_name": {
#         "zh": "DuckDuckGo 搜索(市场插件翻译)",
#         "en": "DuckDuckGo Search (translated from operit market)"
#     },
#     "description": {
#         "zh": "从 operit 市场 duckduckgo.ts 忠实翻译：搜索与网页内容抓取。",
#         "en": "Faithful translation of operit market duckduckgo.ts: search & fetch."
#     },
#     "category": "Search",
#     "tools": [
#         {
#             "name": "search",
#             "description": {
#                 "zh": "搜索 DuckDuckGo 并返回格式化结果",
#                 "en": "Search DuckDuckGo and return formatted results"
#             },
#             "parameters": [
#                 {"name": "query", "type": "string", "required": true},
#                 {"name": "max_results", "type": "string", "required": false}
#             ]
#         },
#         {
#             "name": "fetch_content",
#             "description": {
#                 "zh": "抓取并解析网页内容为纯文本",
#                 "en": "Fetch and parse webpage content to plain text"
#             },
#             "parameters": [
#                 {"name": "url", "type": "string", "required": true}
#             ]
#         }
#     ]
# }

import re
import html
import asyncio


BASE_URL = "https://html.duckduckgo.com/html/"

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"


class RateLimiter:
    """轻量异步令牌桶，忠实于 TS 版 RateLimiter.acquire()"""
    def __init__(self, max_concurrent: int):
        self._sem = asyncio.Semaphore(max_concurrent)

    async def acquire(self):
        await self._sem.acquire()

    def release(self):
        self._sem.release()


_search_limiter = RateLimiter(20)
_fetch_limiter = RateLimiter(20)


def getErrorMessage(error):
    return str(error) if error else "unknown"


def getErrorStack(error):
    import traceback
    return traceback.format_exc()


def _decode_entities(text: str) -> str:
    return html.unescape(text)


def _format_results_for_llm(results: list) -> str:
    lines = []
    for r in results:
        lines.append(f"{r['position']}. {r['title']}")
        lines.append(f"   URL: {r['link']}")
        lines.append(f"   {r['snippet']}")
        lines.append("")
    return "\n".join(lines).strip()


async def wrap(func, params, ok_msg="操作成功", err_msg="操作失败"):
    try:
        result = await func(params)
        complete({"success": True, "message": ok_msg, "data": result})
    except Exception as error:
        console.error(f"Error: {getErrorMessage(error)}")
        complete({"success": False, "message": getErrorMessage(error), "error_stack": getErrorStack(error)})


async def search(params):
    """忠实翻译 duckduckgo.ts search()"""
    query = params.get("query", "")
    max_results = 10
    if params.get("max_results"):
        try:
            parsed = int(params["max_results"])
            if not str(parsed).startswith("NaN"):
                max_results = parsed
        except (ValueError, TypeError):
            pass

    if not query:
        raise ValueError("查询不能为空")

    await _search_limiter.acquire()
    try:
        console.log(f"正在从DuckDuckGo搜索: {query}")
        client = OkHttp.newClient()
        request = (client.newRequest()
                   .url(BASE_URL)
                   .method("POST")
                   .body({"q": query, "b": "", "kl": ""}, "form")
                   .headers({"User-Agent": _UA}))

        response = await request.build().execute()
        if not response.isSuccessful():
            raise RuntimeError(f"HTTP 错误! 状态码: {response.statusCode}")

        html_text = response.content
        results = []
        result_regex = re.compile(
            r'<h2 class="result__title">[\s\S]*?<a.*?href="([^"]+)".*?>([\s\S]+?)</a>'
            r'[\s\S]*?</h2>[\s\S]*?<a class="result__snippet".*?>([\s\S]+?)</a>',
            re.IGNORECASE,
        )
        for m in result_regex.finditer(html_text):
            if len(results) >= max_results:
                break
            link = m.group(1)
            if "y.js" in link:
                continue  # 跳过广告
            if link.startswith("//duckduckgo.com/l/?uddg="):
                try:
                    link = _decode_entities(link.split("uddg=")[1].split("&")[0])
                except Exception:
                    console.error(f"URL 解码失败: {link}")
            title = _decode_entities(re.sub(r"<[^>]*>", "", m.group(2)).strip())
            snippet = _decode_entities(re.sub(r"<[^>]*>", "", m.group(3)).strip())
            results.append({"title": title, "link": link, "snippet": snippet,
                            "position": len(results) + 1})

        console.log(f"成功找到 {len(results)} 个结果")
        return _format_results_for_llm(results)
    finally:
        _search_limiter.release()


async def fetch_content(params):
    """忠实翻译 duckduckgo.ts fetch_content()"""
    url = params.get("url", "")
    if not url:
        raise ValueError("URL不能为空")

    await _fetch_limiter.acquire()
    try:
        console.log(f"正在抓取内容: {url}")
        client = OkHttp.newClient()
        request = (client.newRequest()
                   .url(url)
                   .method("GET")
                   .headers({"User-Agent": _UA}))

        response = await request.build().execute()
        if not response.isSuccessful():
            raise RuntimeError(f"无法访问网页 ({response.statusCode})")

        text = response.content
        for tag in ("style", "script", "nav", "header", "footer"):
            text = re.sub(rf"<{tag}[^>]*>[\s\S]*?</{tag}>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > 8000:
            text = text[:8000] + "... [内容被截断]"
        console.log(f"成功抓取并解析内容 ({len(text)} 字符)")
        return text
    finally:
        _fetch_limiter.release()


async def search_wrapper(params):
    await wrap(search, params, "搜索完成", "搜索失败")


async def fetch_content_wrapper(params):
    await wrap(fetch_content, params, "抓取完成", "抓取失败")


exports.search = search_wrapper
exports.fetch_content = fetch_content_wrapper
