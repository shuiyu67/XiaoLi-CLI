# METADATA
# {
#     "name": "crossref",
#     "display_name": {
#         "zh": "Crossref 学术文献查询",
#         "en": "Crossref Academic Literature Search"
#     },
#     "description": {
#         "zh": "Crossref 学术文献查询工具，提供 DOI 查询、关键词搜索、作者搜索等功能，帮助用户查找和获取学术文章元数据。",
#         "en": "Crossref scholarly literature search tools: query by DOI, keyword, author, title, ISSN, and retrieve publication metadata."
#     },
#     "category": "Search",
#     "enabledByDefault": true,
#     "tools": [
#         {
#             "name": "search_by_doi",
#             "description": { "zh": "通过 DOI (Digital Object Identifier) 查询文章的详细信息", "en": "Query article details by DOI (Digital Object Identifier)." },
#             "parameters": [
#                 { "name": "doi", "description": { "zh": "文章的 DOI 标识符，例如 '10.1038/nature12373'", "en": "DOI identifier, e.g. '10.1038/nature12373'" }, "type": "string", "required": true }
#             ]
#         },
#         {
#             "name": "search_by_keyword",
#             "description": { "zh": "通过关键词搜索学术文章", "en": "Search scholarly articles by keyword." },
#             "parameters": [
#                 { "name": "query", "description": { "zh": "搜索关键词", "en": "Search query keyword(s)" }, "type": "string", "required": true },
#                 { "name": "rows", "description": { "zh": "返回结果数量，默认 10，最大 100", "en": "Number of results to return (default: 10, max: 100)" }, "type": "number", "required": false },
#                 { "name": "sort", "description": { "zh": "排序方式，可选值：'relevance'(相关性), 'score'(评分), 'updated'(更新时间), 'deposited'(提交时间), 'indexed'(索引时间), 'published'(发布时间)", "en": "Sort mode. Options: 'relevance', 'score', 'updated', 'deposited', 'indexed', 'published'." }, "type": "string", "required": false },
#                 { "name": "order", "description": { "zh": "排序顺序，可选值：'asc'(升序), 'desc'(降序)，默认 'desc'", "en": "Sort order: 'asc' or 'desc' (default: 'desc')." }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "search_by_author",
#             "description": { "zh": "通过作者名字搜索文章", "en": "Search articles by author name." },
#             "parameters": [
#                 { "name": "author", "description": { "zh": "作者名字", "en": "Author name" }, "type": "string", "required": true },
#                 { "name": "rows", "description": { "zh": "返回结果数量，默认 10，最大 100", "en": "Number of results to return (default 10, max 100)" }, "type": "number", "required": false }
#             ]
#         },
#         {
#             "name": "search_by_title",
#             "description": { "zh": "通过文章标题搜索", "en": "Search articles by title." },
#             "parameters": [
#                 { "name": "title", "description": { "zh": "文章标题或标题关键词", "en": "Article title or title keyword(s)" }, "type": "string", "required": true },
#                 { "name": "rows", "description": { "zh": "返回结果数量，默认 10，最大 100", "en": "Number of results to return (default 10, max 100)" }, "type": "number", "required": false }
#             ]
#         },
#         {
#             "name": "search_by_issn",
#             "description": { "zh": "通过期刊 ISSN 查询该期刊发表的文章", "en": "Search articles published in a journal by ISSN." },
#             "parameters": [
#                 { "name": "issn", "description": { "zh": "期刊的 ISSN 标识符，例如 '1476-4687'", "en": "Journal ISSN identifier, e.g. '1476-4687'" }, "type": "string", "required": true },
#                 { "name": "rows", "description": { "zh": "返回结果数量，默认 10，最大 100", "en": "Number of results to return (default 10, max 100)" }, "type": "number", "required": false }
#             ]
#         }
#     ]
# }

import json
import re
from urllib.parse import quote

BASE_URL = "https://api.crossref.org"
DEFAULT_ROWS = 10
MAX_ROWS = 100


def buildQueryString(params):
    return "&".join(f"{quote(str(key))}={quote(str(value))}" for key, value in params.items())


# 格式化作者信息
def formatAuthors(authors):
    if not authors or len(authors) == 0:
        return "N/A"
    names = []
    for author in authors[:5]:  # 只显示前5个作者
        given = author.get("given") or ""
        family = author.get("family") or ""
        name = f"{given} {family}".strip()
        if len(name) > 0:
            names.append(name)
    return ", ".join(names)


# 格式化日期
def formatDate(dateParts):
    if not dateParts or len(dateParts) == 0 or not dateParts[0]:
        return "N/A"
    parts = dateParts[0]
    if len(parts) == 1:
        return f"{parts[0]}"
    if len(parts) == 2:
        return f"{parts[0]}-{str(parts[1]).rjust(2, '0')}"
    if len(parts) == 3:
        return f"{parts[0]}-{str(parts[1]).rjust(2, '0')}-{str(parts[2]).rjust(2, '0')}"
    return "N/A"


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


# 格式化单篇文章信息
def formatArticle(item, index=None):
    lines = []

    if index is not None:
        lines.append(f"\n=== Article {index + 1} ===")

    # 标题
    title = (item.get("title")[0] if item.get("title") and len(item.get("title")) > 0 else "No Title")
    lines.append(f"Title: {title}")

    # DOI
    if item.get("DOI"):
        lines.append(f"DOI: {item['DOI']}")
        lines.append(f"URL: https://doi.org/{item['DOI']}")

    # 作者
    authors = formatAuthors(item.get("author"))
    lines.append(f"Authors: {authors}")

    # 发表日期
    published = _get(item, "published") or {}
    publishedPrint = _get(item, "published-print") or {}
    publishedOnline = _get(item, "published-online") or {}
    publishedDate = formatDate(
        _get(published, "date-parts") or _get(publishedPrint, "date-parts") or _get(publishedOnline, "date-parts")
    )
    lines.append(f"Published: {publishedDate}")

    # 期刊/会议
    containerTitle = item.get("container-title")
    if containerTitle and len(containerTitle) > 0:
        lines.append(f"Journal/Conference: {containerTitle[0]}")

    # ISSN
    issn = item.get("ISSN")
    if issn and len(issn) > 0:
        lines.append(f"ISSN: {', '.join(issn)}")

    # 出版商
    if item.get("publisher"):
        lines.append(f"Publisher: {item['publisher']}")

    # 类型
    if item.get("type"):
        lines.append(f"Type: {item['type']}")

    # 引用次数
    if item.get("is-referenced-by-count") is not None:
        lines.append(f"Citations: {item['is-referenced-by-count']}")

    # 摘要（如果有）
    if item.get("abstract"):
        # 移除 HTML 标签
        abstractText = re.sub(r"<[^>]*>", "", item["abstract"])
        lines.append(f"Abstract: {abstractText[:500]}{'...' if len(abstractText) > 500 else ''}")

    return "\n".join(lines)


async def _httpGet(url, headers):
    client = OkHttp.newBuilder().build()
    response = await client.newRequest().url(url).method("GET").headers(headers).build().execute()
    return response


# 通过 DOI 查询文章
async def searchByDoi(params):
    doi = params.get("doi")

    if not doi or doi.strip() == "":
        return {
            "success": False,
            "message": "请提供有效的 DOI"
        }

    try:
        url = f"{BASE_URL}/works/{quote(doi, safe='')}"
        response = await _httpGet(url, {
            "User-Agent": "Operit/1.0 (mailto:support@example.com)"
        })

        if not response.isSuccessful():
            return {
                "success": False,
                "message": f"查询失败: HTTP {response.statusCode} - {getattr(response, 'statusMessage', '')}"
            }

        data = json.loads(response.content)

        if data.get("status") == "ok" and data.get("message"):
            article = formatArticle(data["message"])
            return {
                "success": True,
                "message": "查询成功",
                "data": article
            }
        else:
            return {
                "success": False,
                "message": "未找到该 DOI 对应的文章"
            }
    except Exception as error:
        return {
            "success": False,
            "message": f"查询失败: {str(error)}"
        }


# 通过关键词搜索文章
async def searchByKeyword(params):
    query = params.get("query")
    rows = params.get("rows") if params.get("rows") is not None else DEFAULT_ROWS
    sort = params.get("sort") if params.get("sort") is not None else "relevance"
    order = params.get("order") if params.get("order") is not None else "desc"

    if not query or query.strip() == "":
        return {
            "success": False,
            "message": "请提供有效的搜索关键词"
        }

    actualRows = min(max(int(rows), 1), MAX_ROWS)

    try:
        queryString = buildQueryString({
            "query": query,
            "rows": str(actualRows),
            "sort": sort,
            "order": order
        })

        url = f"{BASE_URL}/works?{queryString}"
        response = await _httpGet(url, {
            "User-Agent": "Operit/1.0 (mailto:support@example.com)"
        })

        if not response.isSuccessful():
            return {
                "success": False,
                "message": f"搜索失败: HTTP {response.statusCode} - {getattr(response, 'statusMessage', '')}"
            }

        data = json.loads(response.content)

        if data.get("status") == "ok" and data.get("message") and data["message"].get("items"):
            items = data["message"]["items"]
            totalResults = data["message"].get("total-results")

            results = [formatArticle(item, index) for index, item in enumerate(items)]

            summary = f"Found {totalResults} results (showing {len(items)}):\n" + "\n\n".join(results)

            return {
                "success": True,
                "message": "搜索成功",
                "data": summary,
                "total": totalResults,
                "count": len(items)
            }
        else:
            return {
                "success": False,
                "message": "未找到相关文章"
            }
    except Exception as error:
        return {
            "success": False,
            "message": f"搜索失败: {str(error)}"
        }


# 通过作者搜索文章
async def searchByAuthor(params):
    author = params.get("author")
    rows = params.get("rows") if params.get("rows") is not None else DEFAULT_ROWS

    if not author or author.strip() == "":
        return {
            "success": False,
            "message": "请提供有效的作者名字"
        }

    actualRows = min(max(int(rows), 1), MAX_ROWS)

    try:
        queryString = buildQueryString({
            "query.author": author,
            "rows": str(actualRows)
        })

        url = f"{BASE_URL}/works?{queryString}"
        response = await _httpGet(url, {
            "User-Agent": "Operit/1.0 (mailto:support@example.com)"
        })

        if not response.isSuccessful():
            return {
                "success": False,
                "message": f"搜索失败: HTTP {response.statusCode} - {getattr(response, 'statusMessage', '')}"
            }

        data = json.loads(response.content)

        if data.get("status") == "ok" and data.get("message") and data["message"].get("items"):
            items = data["message"]["items"]
            totalResults = data["message"].get("total-results")

            results = [formatArticle(item, index) for index, item in enumerate(items)]

            summary = f"Found {totalResults} results for author \"{author}\" (showing {len(items)}):\n" + "\n\n".join(results)

            return {
                "success": True,
                "message": "搜索成功",
                "data": summary,
                "total": totalResults,
                "count": len(items)
            }
        else:
            return {
                "success": False,
                "message": f"未找到该作者 \"{author}\" 的文章"
            }
    except Exception as error:
        return {
            "success": False,
            "message": f"搜索失败: {str(error)}"
        }


# 通过标题搜索文章
async def searchByTitle(params):
    title = params.get("title")
    rows = params.get("rows") if params.get("rows") is not None else DEFAULT_ROWS

    if not title or title.strip() == "":
        return {
            "success": False,
            "message": "请提供有效的文章标题"
        }

    actualRows = min(max(int(rows), 1), MAX_ROWS)

    try:
        queryString = buildQueryString({
            "query.title": title,
            "rows": str(actualRows)
        })

        url = f"{BASE_URL}/works?{queryString}"
        response = await _httpGet(url, {
            "User-Agent": "Operit/1.0 (mailto:support@example.com)"
        })

        data = json.loads(response.content)

        if data.get("status") == "ok" and data.get("message") and data["message"].get("items"):
            items = data["message"]["items"]
            totalResults = data["message"].get("total-results")

            results = [formatArticle(item, index) for index, item in enumerate(items)]

            summary = f"Found {totalResults} results matching title \"{title}\" (showing {len(items)}):\n" + "\n\n".join(results)

            return {
                "success": True,
                "message": "搜索成功",
                "data": summary,
                "total": totalResults,
                "count": len(items)
            }
        else:
            return {
                "success": False,
                "message": f"未找到标题包含 \"{title}\" 的文章"
            }
    except Exception as error:
        return {
            "success": False,
            "message": f"搜索失败: {str(error)}"
        }


# 通过 ISSN 查询期刊文章
async def searchByISSN(params):
    issn = params.get("issn")
    rows = params.get("rows") if params.get("rows") is not None else DEFAULT_ROWS

    if not issn or issn.strip() == "":
        return {
            "success": False,
            "message": "请提供有效的 ISSN"
        }

    actualRows = min(max(int(rows), 1), MAX_ROWS)

    try:
        url = f"{BASE_URL}/journals/{quote(issn, safe='')}/works?rows={actualRows}"
        response = await _httpGet(url, {
            "User-Agent": "Operit/1.0 (mailto:support@example.com)"
        })

        if not response.isSuccessful():
            return {
                "success": False,
                "message": f"查询失败: HTTP {response.statusCode} - {getattr(response, 'statusMessage', '')}"
            }

        data = json.loads(response.content)

        if data.get("status") == "ok" and data.get("message") and data["message"].get("items"):
            items = data["message"]["items"]
            totalResults = data["message"].get("total-results")

            results = [formatArticle(item, index) for index, item in enumerate(items)]

            summary = f"Found {totalResults} articles from journal ISSN {issn} (showing {len(items)}):\n" + "\n\n".join(results)

            return {
                "success": True,
                "message": "查询成功",
                "data": summary,
                "total": totalResults,
                "count": len(items)
            }
        else:
            return {
                "success": False,
                "message": f"未找到 ISSN \"{issn}\" 对应期刊的文章"
            }
    except Exception as error:
        return {
            "success": False,
            "message": f"查询失败: {str(error)}"
        }


# 包装函数，统一处理错误
async def wrapToolExecution(func, params):
    try:
        result = await func(params)
        complete(result)
    except Exception as error:
        console.error("工具执行失败", error)
        complete({
            "success": False,
            "message": f"工具执行时发生意外错误: {str(error)}",
        })


# 测试函数
async def main(params=None):
    if params is None:
        params = {}
    console.log("=== Crossref API 测试 ===\n")

    # 测试 1: 通过 DOI 查询
    console.log("1. 测试通过 DOI 查询...")
    doiResult = await searchByDoi({"doi": "10.1038/nature12373"})
    console.log(json.dumps(doiResult, ensure_ascii=False, indent=2))
    console.log("\n")

    # 测试 2: 通过关键词搜索
    console.log("2. 测试通过关键词搜索...")
    keywordResult = await searchByKeyword({"query": "machine learning", "rows": 3})
    console.log(json.dumps(keywordResult, ensure_ascii=False, indent=2))
    console.log("\n")

    # 测试 3: 通过作者搜索
    console.log("3. 测试通过作者搜索...")
    authorResult = await searchByAuthor({"author": "John Smith", "rows": 3})
    console.log(json.dumps(authorResult, ensure_ascii=False, indent=2))
    console.log("\n")

    # 测试 4: 通过标题搜索
    console.log("4. 测试通过标题搜索...")
    titleResult = await searchByTitle({"title": "neural networks", "rows": 3})
    console.log(json.dumps(titleResult, ensure_ascii=False, indent=2))
    console.log("\n")

    console.log("=== 测试完成 ===")


async def _exported_search_by_doi(params):
    await wrapToolExecution(searchByDoi, params)


async def _exported_search_by_keyword(params):
    await wrapToolExecution(searchByKeyword, params)


async def _exported_search_by_author(params):
    await wrapToolExecution(searchByAuthor, params)


async def _exported_search_by_title(params):
    await wrapToolExecution(searchByTitle, params)


async def _exported_search_by_issn(params):
    await wrapToolExecution(searchByISSN, params)


exports.search_by_doi = _exported_search_by_doi
exports.search_by_keyword = _exported_search_by_keyword
exports.search_by_author = _exported_search_by_author
exports.search_by_title = _exported_search_by_title
exports.search_by_issn = _exported_search_by_issn
exports.main = main
