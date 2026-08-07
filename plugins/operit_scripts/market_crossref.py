# METADATA
# {
#   "name": "crossref",
#   "display_name": { "zh": "Crossref 学术文献查询", "en": "Crossref Academic Literature Search" },
#   "description": { "zh": "Crossref 学术文献查询（DOI/关键词/作者/标题/ISSN）", "en": "Crossref scholarly literature search." },
#   "category": "Search",
#   "tools": [
#     { "name": "search_by_doi", "description": { "zh": "通过 DOI 查询文章", "en": "Query by DOI" } },
#     { "name": "search_by_keyword", "description": { "zh": "通过关键词搜索", "en": "Search by keyword" } },
#     { "name": "search_by_author", "description": { "zh": "通过作者搜索", "en": "Search by author" } },
#     { "name": "search_by_title", "description": { "zh": "通过标题搜索", "en": "Search by title" } },
#     { "name": "search_by_issn", "description": { "zh": "通过 ISSN 查询", "en": "Search by ISSN" } }
#   ]
# }
import json as _json
from urllib.parse import quote_plus

HEADERS = {'User-Agent': 'Operit/1.0 (mailto:support@example.com)'}
BASE_URL = "https://api.crossref.org"
DEFAULT_ROWS = 10
MAX_ROWS = 100


def getErrorMessage(error):
    return str(error) if error else "unknown"


def getErrorStack(error):
    import traceback
    return traceback.format_exc()


def format_authors(authors):
    if not authors:
        return "N/A"
    return ", ".join(
        f"{a.get('given', '')} {a.get('family', '')}".strip()
        for a in authors[:5] if a.get('given') or a.get('family')
    ) or "N/A"


def format_date(date_parts):
    if not date_parts or not date_parts[0]:
        return "N/A"
    p = date_parts[0]
    if len(p) == 1:
        return str(p[0])
    if len(p) == 2:
        return f"{p[0]}-{str(p[1]).zfill(2)}"
    if len(p) == 3:
        return f"{p[0]}-{str(p[1]).zfill(2)}-{str(p[2]).zfill(2)}"
    return "N/A"


def format_article(item, index=None):
    lines = []
    if index is not None:
        lines.append(f"\n=== Article {index + 1} ===")
    title = item.get("title", ["No Title"])[0] if item.get("title") else "No Title"
    lines.append(f"Title: {title}")
    if item.get("DOI"):
        lines.append(f"DOI: {item['DOI']}")
        lines.append(f"URL: https://doi.org/{item['DOI']}")
    lines.append(f"Authors: {format_authors(item.get('author'))}")
    dp = (item.get("published") or item.get("published-print") or item.get("published-online") or {}).get("date-parts")
    lines.append(f"Published: {format_date(dp)}")
    if item.get("container-title"):
        lines.append(f"Journal/Conference: {item['container-title'][0]}")
    if item.get("ISSN"):
        lines.append(f"ISSN: {', '.join(item['ISSN'])}")
    if item.get("publisher"):
        lines.append(f"Publisher: {item['publisher']}")
    if item.get("type"):
        lines.append(f"Type: {item['type']}")
    if item.get("is-referenced-by-count") is not None:
        lines.append(f"Citations: {item['is-referenced-by-count']}")
    if item.get("abstract"):
        ab = __import__("re").sub(r"<[^>]*>", "", item["abstract"])
        lines.append(f"Abstract: {ab[:500]}{'...' if len(ab) > 500 else ''}")
    return "\n".join(lines)


async def _get_json(url):
    client = OkHttp.newClient()
    resp = await client.newRequest().url(url).method("GET").headers(HEADERS).build().execute()
    if not resp.isSuccessful():
        raise RuntimeError(f"HTTP {resp.statusCode} - {resp.statusMessage}")
    return resp.json()


async def search_by_doi(params):
    doi = (params.get("doi") or "").strip()
    if not doi:
        return {"success": False, "message": "请提供有效的 DOI"}
    try:
        data = await _get_json(f"{BASE_URL}/works/{quote_plus(doi)}")
        if data.get("status") == "ok" and data.get("message"):
            return {"success": True, "message": "查询成功", "data": format_article(data["message"])}
        return {"success": False, "message": "未找到该 DOI 对应的文章"}
    except Exception as e:
        return {"success": False, "message": f"查询失败: {getErrorMessage(e)}"}


async def search_by_keyword(params):
    query = (params.get("query") or "").strip()
    if not query:
        return {"success": False, "message": "请提供有效的搜索关键词"}
    rows = max(1, min(int(params.get("rows", DEFAULT_ROWS) or DEFAULT_ROWS), MAX_ROWS))
    sort = params.get("sort", "relevance")
    order = params.get("order", "desc")
    qs = "&".join(f"{k}={quote_plus(v)}" for k, v in
                  {"query": query, "rows": str(rows), "sort": sort, "order": order}.items())
    try:
        data = await _get_json(f"{BASE_URL}/works?{qs}")
        return _summarize(data, query, f'关键词 "{query}"')
    except Exception as e:
        return {"success": False, "message": f"搜索失败: {getErrorMessage(e)}"}


async def search_by_author(params):
    author = (params.get("author") or "").strip()
    if not author:
        return {"success": False, "message": "请提供有效的作者名字"}
    rows = max(1, min(int(params.get("rows", DEFAULT_ROWS) or DEFAULT_ROWS), MAX_ROWS))
    qs = "&".join(f"{k}={quote_plus(v)}" for k, v in
                  {"query.author": author, "rows": str(rows)}.items())
    try:
        data = await _get_json(f"{BASE_URL}/works?{qs}")
        return _summarize(data, author, f'作者 "{author}"')
    except Exception as e:
        return {"success": False, "message": f"搜索失败: {getErrorMessage(e)}"}


async def search_by_title(params):
    title = (params.get("title") or "").strip()
    if not title:
        return {"success": False, "message": "请提供有效的文章标题"}
    rows = max(1, min(int(params.get("rows", DEFAULT_ROWS) or DEFAULT_ROWS), MAX_ROWS))
    qs = "&".join(f"{k}={quote_plus(v)}" for k, v in
                  {"query.title": title, "rows": str(rows)}.items())
    try:
        data = await _get_json(f"{BASE_URL}/works?{qs}")
        return _summarize(data, title, f'标题 "{title}"')
    except Exception as e:
        return {"success": False, "message": f"搜索失败: {getErrorMessage(e)}"}


async def search_by_issn(params):
    issn = (params.get("issn") or "").strip()
    if not issn:
        return {"success": False, "message": "请提供有效的 ISSN"}
    rows = max(1, min(int(params.get("rows", DEFAULT_ROWS) or DEFAULT_ROWS), MAX_ROWS))
    try:
        data = await _get_json(f"{BASE_URL}/journals/{quote_plus(issn)}/works?rows={rows}")
        return _summarize(data, issn, f'ISSN {issn}')
    except Exception as e:
        return {"success": False, "message": f"查询失败: {getErrorMessage(e)}"}


def _summarize(data, key, label):
    if data.get("status") == "ok" and data.get("message") and data.get("message", {}).get("items"):
        items = data["message"]["items"]
        total = data["message"].get("total-results")
        results = [format_article(it, i) for i, it in enumerate(items)]
        return {"success": True, "message": "搜索成功",
                "data": f"Found {total} results for {label} (showing {len(items)}):\n\n" + "\n\n".join(results),
                "total": total, "count": len(items)}
    return {"success": False, "message": f"未找到匹配 {label} 的文章"}


async def wrap(func, params, ok_msg="操作成功", err_msg="操作失败"):
    try:
        result = await func(params)
        complete({"success": True, "message": result.get("message", ok_msg), "data": result.get("data"),
                   **{k: v for k, v in result.items() if k not in ("success", "message", "data")}})
    except Exception as error:
        console.error(f"Error: {getErrorMessage(error)}")
        complete({"success": False, "message": getErrorMessage(error), "error_stack": getErrorStack(error)})


async def search_by_doi_wrapper(params):
    await wrap(search_by_doi, params, "查询成功", "查询失败")


async def search_by_keyword_wrapper(params):
    await wrap(search_by_keyword, params, "搜索成功", "搜索失败")


async def search_by_author_wrapper(params):
    await wrap(search_by_author, params, "搜索成功", "搜索失败")


async def search_by_title_wrapper(params):
    await wrap(search_by_title, params, "搜索成功", "搜索失败")


async def search_by_issn_wrapper(params):
    await wrap(search_by_issn, params, "查询成功", "查询失败")


exports.search_by_doi = search_by_doi_wrapper
exports.search_by_keyword = search_by_keyword_wrapper
exports.search_by_author = search_by_author_wrapper
exports.search_by_title = search_by_title_wrapper
exports.search_by_issn = search_by_issn_wrapper
