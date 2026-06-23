# METADATA
# {
#   "name": "various_search",
#   "display_name": {"zh": "多平台搜索", "en": "Multi-Platform Search"},
#   "category": "Search",
#   "description": {"zh": "提供多平台搜索功能（含图片搜索），支持从必应、百度、搜狗、夸克等平台获取搜索结果。", "en": "Multi-platform search tools (including image search) that fetch results from Bing, Baidu, Sogou, Quark, and more."},
#   "enabledByDefault": True,
#   "tools": [
#     {"name": "search_bing", "description": {"zh": "使用必应搜索引擎进行搜索", "en": "Search using the Bing search engine."}, "parameters": [
#       {"name": "query", "description": {"zh": "搜索查询关键词", "en": "Search query keywords."}, "type": "string", "required": True},
#       {"name": "includeLinks", "description": {"zh": "是否在结果中包含可点击的链接列表，默认为false。", "en": "Whether to include a clickable link list in results (default: false)."}, "type": "boolean", "required": False}
#     ]},
#     {"name": "search_baidu", "description": {"zh": "使用百度搜索引擎进行搜索", "en": "Search using the Baidu search engine."}, "parameters": [
#       {"name": "query", "description": {"zh": "搜索查询关键词", "en": "Search query keywords."}, "type": "string", "required": True},
#       {"name": "page", "description": {"zh": "搜索结果页码，默认为1", "en": "Result page number (default: 1)."}, "type": "string", "required": False},
#       {"name": "includeLinks", "description": {"zh": "是否在结果中包含可点击的链接列表，默认为false。", "en": "Whether to include a clickable link list in results (default: false)."}, "type": "boolean", "required": False}
#     ]},
#     {"name": "search_sogou", "description": {"zh": "使用搜狗搜索引擎进行搜索", "en": "Search using the Sogou search engine."}, "parameters": [
#       {"name": "query", "description": {"zh": "搜索查询关键词", "en": "Search query keywords."}, "type": "string", "required": True},
#       {"name": "page", "description": {"zh": "搜索结果页码，默认为1", "en": "Result page number (default: 1)."}, "type": "string", "required": False},
#       {"name": "includeLinks", "description": {"zh": "是否在结果中包含可点击的链接列表，默认为false。", "en": "Whether to include a clickable link list in results (default: false)."}, "type": "boolean", "required": False}
#     ]},
#     {"name": "search_quark", "description": {"zh": "使用夸克搜索引擎进行搜索", "en": "Search using the Quark search engine."}, "parameters": [
#       {"name": "query", "description": {"zh": "搜索查询关键词", "en": "Search query keywords."}, "type": "string", "required": True},
#       {"name": "page", "description": {"zh": "搜索结果页码，默认为1", "en": "Result page number (default: 1)."}, "type": "string", "required": False},
#       {"name": "includeLinks", "description": {"zh": "是否在结果中包含可点击的链接列表，默认为false。", "en": "Whether to include a clickable link list in results (default: false)."}, "type": "boolean", "required": False}
#     ]},
#     {"name": "combined_search", "description": {"zh": "在多个平台同时执行搜索。建议用户要求搜索的时候默认使用这个工具。", "en": "Run searches across multiple platforms. Use this tool by default when the user asks to search."}, "parameters": [
#       {"name": "query", "description": {"zh": "搜索查询关键词", "en": "Search query keywords."}, "type": "string", "required": True},
#       {"name": "platforms", "description": {"zh": "搜索平台列表字符串，可选值包括\"bing\",\"baidu\",\"sogou\",\"quark\"，多个平台用逗号分隔", "en": "Comma-separated platform list."}, "type": "string", "required": True},
#       {"name": "includeLinks", "description": {"zh": "是否在结果中包含可点击的链接列表，默认为false。", "en": "Whether to include a clickable link list in results (default: false)."}, "type": "boolean", "required": False}
#     ]},
#     {"name": "search", "description": {"zh": "兼容工具名：等同于 combined_search。", "en": "Compatibility alias: equivalent to combined_search."}, "parameters": [
#       {"name": "query", "description": {"zh": "搜索查询关键词", "en": "Search query keywords."}, "type": "string", "required": True},
#       {"name": "platforms", "description": {"zh": "可选平台列表，默认 bing,baidu,sogou,quark", "en": "Optional platform list, default bing,baidu,sogou,quark."}, "type": "string", "required": False},
#       {"name": "includeLinks", "description": {"zh": "是否返回链接列表，默认 false", "en": "Whether to include links in result, default false."}, "type": "boolean", "required": False}
#     ]},
#     {"name": "search_web", "description": {"zh": "兼容工具名：网页搜索别名。", "en": "Compatibility alias for web search."}, "parameters": [
#       {"name": "query", "description": {"zh": "搜索查询关键词", "en": "Search query keywords."}, "type": "string", "required": True},
#       {"name": "platforms", "description": {"zh": "可选平台列表，默认 bing,baidu,sogou,quark", "en": "Optional platform list."}, "type": "string", "required": False},
#       {"name": "includeLinks", "description": {"zh": "是否返回链接列表，默认 false", "en": "Whether to include links in result, default false."}, "type": "boolean", "required": False}
#     ]},
#     {"name": "search_bing_images", "description": {"zh": "使用必应图片搜索引擎进行图片搜索。", "en": "Search images using Bing Images."}, "parameters": [{"name": "query", "description": {"zh": "搜索关键词", "en": "Search query keywords."}, "type": "string", "required": True}]},
#     {"name": "search_wikimedia_images", "description": {"zh": "使用 Wikimedia Commons 进行图片搜索。", "en": "Search images using Wikimedia Commons."}, "parameters": [{"name": "query", "description": {"zh": "搜索关键词", "en": "Search query keywords."}, "type": "string", "required": True}]},
#     {"name": "search_duckduckgo_images", "description": {"zh": "使用 DuckDuckGo Images 进行图片搜索。", "en": "Search images using DuckDuckGo Images."}, "parameters": [{"name": "query", "description": {"zh": "搜索关键词", "en": "Search query keywords."}, "type": "string", "required": True}]},
#     {"name": "search_ecosia_images", "description": {"zh": "使用 Ecosia Images 进行图片搜索。", "en": "Search images using Ecosia Images."}, "parameters": [{"name": "query", "description": {"zh": "搜索关键词", "en": "Search query keywords."}, "type": "string", "required": True}]},
#     {"name": "search_pexels_images", "description": {"zh": "使用 Pexels 进行图片搜索。", "en": "Search images using Pexels."}, "parameters": [{"name": "query", "description": {"zh": "搜索关键词", "en": "Search query keywords."}, "type": "string", "required": True}]},
#     {"name": "search_pixabay_images", "description": {"zh": "使用 Pixabay 进行图片搜索。", "en": "Search images using Pixabay."}, "parameters": [{"name": "query", "description": {"zh": "搜索关键词", "en": "Search query keywords."}, "type": "string", "required": True}]}
#   ]
# }

import json
import re
import asyncio
from urllib.parse import quote, unquote

Error = Exception


def normalizeText(input_):
    if not input_:
        return ""
    return re.sub(r'[\s\-_.,;:!?()\[\]{}"\'`~@#$%^&*+=|\\/<>]+', '', str(input_).lower())


OUTBOUND_PATH_HINTS = ["/link", "/url", "/redirect", "/jump", "/out", "/outlink", "/ulink", "/aladdin.php"]
OUTBOUND_QUERY_KEYS = ["url", "u", "target", "targeturl", "target_url", "to", "dest", "destination", "redirect", "redirect_url"]
MULTI_PART_TLDS = ["ac.uk", "co.jp", "co.uk", "com.au", "com.cn", "com.hk", "gov.cn", "net.au", "net.cn", "org.au", "org.cn", "org.uk"]


def normalizePath(pathname):
    normalized = re.sub(r'/+$', '', str(pathname or ""))
    return normalized or "/"


def parseUrlParts(rawUrl, baseUrl):
    rawText = str(rawUrl or "").strip()
    if not rawText:
        return None
    absoluteText = rawText
    if absoluteText.startswith("//"):
        absoluteText = f"https:{absoluteText}"
    elif not re.match(r'^[a-z]+://', absoluteText, re.IGNORECASE):
        if not absoluteText.startswith("/"):
            return None
        base = parseUrlParts(baseUrl, "") if baseUrl else None
        if not base:
            return None
        absoluteText = f"{base['protocol']}//{base['host']}{absoluteText}"
    match = re.match(r'^(https?)://([^/?#]+)([^?#]*)(\?[^#]*)?(?:#.*)?$', absoluteText, re.IGNORECASE)
    if not match:
        return None
    protocol = f"{match.group(1).lower()}:"
    host = match.group(2).lower()
    hostname = re.sub(r':\d+$', '', host)
    pathname = normalizePath(match.group(3) or "/")
    search = match.group(4) or ""
    return {
        "href": f"{protocol}//{host}{pathname}{search}",
        "protocol": protocol,
        "host": host,
        "hostname": hostname,
        "pathname": pathname,
        "search": search,
    }


def normalizeUrl(rawUrl, baseUrl):
    parsed = parseUrlParts(rawUrl, baseUrl)
    return parsed["href"] if parsed else ""


def parseSearchEntries(searchText):
    search = re.sub(r'^\?', '', str(searchText or ""))
    if not search:
        return []
    result = []
    for item in search.split("&"):
        item = item.strip()
        if not item:
            continue
        equalIndex = item.find("=")
        if equalIndex == -1:
            result.append([item, ""])
        else:
            result.append([item[:equalIndex], item[equalIndex + 1:]])
    return result


def getSiteDomain(hostname):
    parts = [p for p in str(hostname or "").lower().split(".") if p]
    if len(parts) <= 2:
        return str(hostname or "").lower()
    lastTwo = ".".join(parts[-2:])
    if lastTwo in MULTI_PART_TLDS and len(parts) >= 3:
        return ".".join(parts[-3:])
    return lastTwo


def countPathSegments(pathname):
    return len([s for s in normalizePath(pathname).split("/") if s])


def getSortedSearch(searchText):
    entries = sorted(parseSearchEntries(searchText), key=lambda x: (x[0], x[1]))
    return "&".join([f"{k}={v}" for k, v in entries])


def toComparableUrl(rawUrl):
    if not rawUrl:
        return ""
    parsed = parseUrlParts(rawUrl, "")
    if not parsed:
        return str(rawUrl).strip()
    search = getSortedSearch(parsed["search"])
    return f"{parsed['protocol']}//{parsed['host']}{parsed['pathname']}" + (f"?{search}" if search else "")


def getLinkText(link):
    text = link and (link.get("text") or link.get("title") or link.get("name"))
    return re.sub(r'\s+', ' ', str(text)).strip() if text else ""


def looksLikeUiText(text):
    raw = re.sub(r'\s+', ' ', str(text or "")).strip()
    normalized = normalizeText(text)
    if not normalized:
        return True
    if re.match(r'^\d+$', normalized):
        return True
    if not re.search(r'[a-z0-9\u4e00-\u9fa5]', raw, re.IGNORECASE):
        return True
    if len(normalized) == 1:
        return True
    if len(normalized) == 2 and re.match(r'^[a-z0-9]+$', normalized, re.IGNORECASE):
        return True
    return False


def looksLikeSearchLandingUrl(rawUrl, sourceUrl):
    if not rawUrl or not sourceUrl:
        return False
    candidate = parseUrlParts(rawUrl, sourceUrl)
    source = parseUrlParts(sourceUrl, "")
    if not candidate or not source:
        return False
    if toComparableUrl(candidate["href"]) == toComparableUrl(source["href"]):
        return True
    if candidate["host"] != source["host"]:
        return False
    candidateSearch = getSortedSearch(candidate["search"])
    sourceSearch = getSortedSearch(source["search"])
    if candidate["pathname"] == "/" and not candidateSearch:
        return True
    return candidate["pathname"] == source["pathname"] and (not candidateSearch or candidateSearch == sourceSearch)


def looksLikeOutboundWrapper(rawUrl, sourceUrl):
    candidate = parseUrlParts(rawUrl, sourceUrl)
    source = parseUrlParts(sourceUrl, "")
    if not candidate or not source or candidate["host"] != source["host"]:
        return False
    path = candidate["pathname"].lower()
    if any(path == hint or path.endswith(hint) for hint in OUTBOUND_PATH_HINTS):
        return True
    search = re.sub(r'^\?', '', candidate["search"])
    return any(re.search(r'(?:^|&)' + key + r'(?:=|&|$)', search, re.IGNORECASE) for key in OUTBOUND_QUERY_KEYS)


def looksLikeSameSiteSectionUrl(rawUrl, sourceUrl):
    candidate = parseUrlParts(rawUrl, sourceUrl)
    source = parseUrlParts(sourceUrl, "")
    if not candidate or not source:
        return False
    if candidate["host"] == source["host"]:
        return False
    if getSiteDomain(candidate["hostname"]) != getSiteDomain(source["hostname"]):
        return False
    if looksLikeOutboundWrapper(candidate["href"], source["href"]):
        return False
    return countPathSegments(candidate["pathname"]) <= 1


def classifyLinkTarget(rawUrl, sourceUrl):
    text = str(rawUrl or "").strip()
    if not text:
        return "invalid"
    lowered = text.lower()
    if lowered.startswith("javascript:") or lowered.startswith("#"):
        return "invalid"
    candidate = parseUrlParts(rawUrl, sourceUrl)
    source = parseUrlParts(sourceUrl, "")
    if not candidate or not source:
        return "invalid"
    if looksLikeSearchLandingUrl(candidate["href"], source["href"]):
        return "landing"
    if looksLikeOutboundWrapper(candidate["href"], source["href"]):
        return "wrapper"
    if candidate["host"] == source["host"]:
        return "internal"
    if looksLikeSameSiteSectionUrl(candidate["href"], source["href"]):
        return "internal"
    if getSiteDomain(candidate["hostname"]) == getSiteDomain(source["hostname"]):
        return "internal"
    return "external"


def extractUrlsFromText(rawText):
    if not rawText:
        return []
    text = str(rawText)
    matches = re.findall(r'https?://[^\s)\]>"\']+', text)
    unique = []
    for url in matches:
        if url not in unique:
            unique.append(url)
    return unique


def extractBestUrlFromText(rawText, sourceUrl):
    urls = extractUrlsFromText(rawText)
    for item in urls:
        if classifyLinkTarget(item, sourceUrl) in ("external", "wrapper"):
            return item
    return urls[0] if urls else ""


def stripLeadingLinkDump(rawContent):
    lines = re.split(r'\r?\n', str(rawContent or ""))
    index = 0
    while index < len(lines) and not lines[index].strip():
        index += 1
    dumpedLinkCount = 0
    while index < len(lines) and re.match(r'^\[\d+\]\s', lines[index].strip()):
        dumpedLinkCount += 1
        index += 1
    if dumpedLinkCount == 0:
        return str(rawContent or "")
    while index < len(lines) and not lines[index].strip():
        index += 1
    return "\n".join(lines[index:])


def collectLinkCandidates(link, sourceUrl):
    if not link:
        link = {}
    keys = ["realUrl", "real_url", "targetUrl", "target_url", "originUrl", "origin_url", "href", "url", "target", "rawUrl", "link"]
    unique = []
    for key in keys:
        value = link.get(key)
        normalized = normalizeUrl(str(value).strip() if value else "", sourceUrl)
        if normalized and normalized not in unique:
            unique.append(normalized)
    return unique


def pickBestLinkUrl(link, sourceUrl):
    candidates = collectLinkCandidates(link, sourceUrl)
    for item in candidates:
        if classifyLinkTarget(item, sourceUrl) in ("external", "wrapper"):
            return item
    fromText = extractBestUrlFromText(getLinkText(link), sourceUrl)
    if fromText:
        return fromText
    return candidates[0] if candidates else ""


def scoreStructuralCandidate(text, url, sourceUrl, relativeIndex):
    score = 0
    if not text or looksLikeUiText(text):
        score -= 6
    else:
        score += 2
    linkType = classifyLinkTarget(url, sourceUrl)
    if linkType == "external":
        score += 5
    elif linkType == "wrapper":
        score += 4
    elif linkType in ("landing", "internal"):
        score -= 8
    else:
        score -= 4
    score -= relativeIndex * 0.15
    return score


def findResultBlockStart(links, sourceUrl, scanLimit=48, windowSize=6, minCandidates=3):
    upperBound = min(len(links), scanLimit)
    for start in range(upperBound):
        candidateCount = 0
        hosts = []
        for offset in range(windowSize):
            if start + offset >= upperBound:
                break
            link = links[start + offset]
            text = getLinkText(link)
            url = pickBestLinkUrl(link, sourceUrl)
            if not text or looksLikeUiText(text):
                continue
            linkType = classifyLinkTarget(url, sourceUrl)
            if linkType not in ("external", "wrapper"):
                continue
            candidateCount += 1
            parsed = parseUrlParts(url, sourceUrl)
            host = parsed["hostname"] if parsed else ""
            if host and host not in hosts:
                hosts.append(host)
        if candidateCount >= minCandidates and len(hosts) >= 2:
            return start
    return 0


def isClusteredResultLink(links, sourceUrl, targetIndex, radius=3, minCandidates=3):
    candidateCount = 0
    hosts = []
    start = max(0, targetIndex - radius)
    end = min(len(links) - 1, targetIndex + radius)
    for index in range(start, end + 1):
        link = links[index]
        text = getLinkText(link)
        url = pickBestLinkUrl(link, sourceUrl)
        if not text or looksLikeUiText(text):
            continue
        linkType = classifyLinkTarget(url, sourceUrl)
        if linkType not in ("external", "wrapper"):
            continue
        candidateCount += 1
        parsed = parseUrlParts(url, sourceUrl)
        host = parsed["hostname"] if parsed else ""
        if host and host not in hosts:
            hosts.append(host)
    return candidateCount >= minCandidates and len(hosts) >= 2


def buildProbeIndexes(links, sourceUrl, maxCount=8, probeWindow=24):
    resultStart = findResultBlockStart(links, sourceUrl)
    result = []
    for relativeIndex, link in enumerate(links[resultStart:resultStart + probeWindow]):
        index = resultStart + relativeIndex
        text = getLinkText(link)
        url = pickBestLinkUrl(link, sourceUrl)
        score = scoreStructuralCandidate(text, url, sourceUrl, relativeIndex)
        if score > -4 and isClusteredResultLink(links, sourceUrl, index):
            result.append(index)
        if len(result) >= maxCount:
            break
    return result


def chooseBestUrl(directUrl, resolvedUrl, sourceUrl):
    candidates = [resolvedUrl, directUrl]
    for candidate in candidates:
        if candidate and classifyLinkTarget(candidate, sourceUrl) == "external":
            return normalizeUrl(candidate, sourceUrl)
    return ""


def shouldKeepLink(links, index, text, url, sourceUrl):
    if not url:
        return False
    if not text or looksLikeUiText(text):
        return False
    if classifyLinkTarget(url, sourceUrl) != "external":
        return False
    return isClusteredResultLink(links, sourceUrl, index)


async def resolveLinkUrlsByVisitKey(response, sourceUrl, maxCount=8):
    if not response or not response.get("visitKey") or not response.get("links") or not isinstance(response.get("links"), list):
        return {}
    resolved = {}
    indexes = buildProbeIndexes(response["links"], sourceUrl, maxCount)

    async def resolveOne(index):
        try:
            follow = await Tools.Net.visit({"visit_key": response["visitKey"], "link_number": index + 1})
            followUrl = normalizeUrl(str(follow.get("url")), sourceUrl) if follow and follow.get("url") else ""
            followContent = str(follow.get("content")) if follow and follow.get("content") else ""
            contentUrl = extractBestUrlFromText(followContent, sourceUrl)
            resolved[index] = {"url": chooseBestUrl("", followUrl, sourceUrl) or chooseBestUrl("", contentUrl, sourceUrl)}
        except Exception as error:
            console.error(f"[resolveLinkUrlsByVisitKey] link {index + 1} failed: {str(error)}")
            resolved[index] = {"url": ""}

    await asyncio.gather(*[resolveOne(index) for index in indexes])
    return resolved


async def buildLinkLines(response, sourceUrl, maxItems=20):
    resultStart = findResultBlockStart(response["links"], sourceUrl)
    resolvedByIndex = await resolveLinkUrlsByVisitKey(response, sourceUrl)
    lines = []
    seen = set()
    for index in range(resultStart, len(response["links"])):
        link = response["links"][index]
        text = getLinkText(link)
        directUrl = pickBestLinkUrl(link, sourceUrl)
        resolved = resolvedByIndex.get(index)
        bestUrl = chooseBestUrl(directUrl, resolved["url"] if resolved and resolved.get("url") else "", sourceUrl)
        if not shouldKeepLink(response["links"], index, text, bestUrl, sourceUrl):
            continue
        key = toComparableUrl(bestUrl)
        if not key or key in seen:
            continue
        seen.add(key)
        lines.append(f"[{index + 1}] {text} - {bestUrl}")
        if len(lines) >= maxItems:
            break
    return lines


async def performSearch(platform, url, includeLinks=False):
    try:
        response = await Tools.Net.visit({"url": url})
        if not response:
            raise Error(f"无法获取 {platform} 搜索结果")

        parts = []
        hasFilteredLinks = False
        if response.get("visitKey") is not None:
            parts.append(str(response["visitKey"]))
        if includeLinks and response.get("links") and isinstance(response.get("links"), list) and len(response["links"]) > 0:
            linksLines = await buildLinkLines(response, url)
            if len(linksLines) > 0:
                parts.append("\n".join(linksLines))
                hasFilteredLinks = True
        elif includeLinks and response.get("content"):
            extractedUrls = extractUrlsFromText(response["content"])
            if len(extractedUrls) > 0:
                lines = [f"[{i + 1}] {item}" for i, item in enumerate(extractedUrls[:20])]
                parts.append("\n".join(lines))
        if response.get("content") is not None and (not includeLinks or not hasFilteredLinks):
            contentText = stripLeadingLinkDump(response["content"]) if includeLinks and response.get("links") and isinstance(response.get("links"), list) else str(response["content"])
            parts.append(str(contentText))

        return {"platform": platform, "content": "\n".join(parts)}
    except Exception as error:
        return {"platform": platform, "content": f"{platform} 搜索失败: {str(error)}"}


async def performImageSearch(platform, url):
    try:
        response = await Tools.Net.visit({"url": url, "include_image_links": True})
        if not response:
            raise Error(f"无法获取 {platform} 图片搜索结果")

        parts = []
        if response.get("visitKey") is not None:
            parts.append(str(response["visitKey"]))

        if response.get("imageLinks") and isinstance(response.get("imageLinks"), list) and len(response["imageLinks"]) > 0:
            maxItems = 20
            imagesLines = []
            for index, link in enumerate(response["imageLinks"][:maxItems]):
                lastSeg = str(link).split("/")[-1] or "image"
                name = lastSeg.split("?")[0] or "image"
                imagesLines.append(f"[{index + 1}] {name}")
            parts.append("Images:")
            parts.append("\n".join(imagesLines))

        if response.get("content") is not None:
            parts.append(str(response["content"]))

        return {"platform": platform, "content": "\n".join(parts)}
    except Exception as error:
        return {"platform": platform, "content": f"{platform} 图片搜索失败: {str(error)}"}


async def search_bing(query, includeLinks=False):
    encodedQuery = quote(query)
    url = f"https://cn.bing.com/search?q={encodedQuery}&FORM=HDRSC1"
    return await performSearch('bing', url, includeLinks)


async def search_baidu(query, pageStr=None, includeLinks=False):
    page = 1
    if pageStr:
        page = int(str(pageStr), 10)
    pn = (page - 1) * 10
    encodedQuery = quote(query)
    url = f"https://www.baidu.com/s?wd={encodedQuery}&pn={pn}"
    return await performSearch('baidu', url, includeLinks)


async def search_sogou(query, pageStr=None, includeLinks=False):
    page = 1
    if pageStr:
        page = int(str(pageStr), 10)
    encodedQuery = quote(query)
    url = f"https://www.sogou.com/web?query={encodedQuery}&page={page}"
    return await performSearch('sogou', url, includeLinks)


async def search_quark(query, pageStr=None, includeLinks=False):
    page = 1
    if pageStr:
        page = int(str(pageStr), 10)
    encodedQuery = quote(query)
    url = f"https://quark.sm.cn/s?q={encodedQuery}&page={page}"
    return await performSearch('quark', url, includeLinks)


async def search_bing_images(query):
    encodedQuery = quote(query)
    url = f"https://www.bing.com/images/search?q={encodedQuery}"
    return await performImageSearch('bing_images', url)


async def search_wikimedia_images(query):
    encodedQuery = quote(query)
    url = f"https://commons.wikimedia.org/wiki/Special:MediaSearch?type=image&search={encodedQuery}"
    return await performImageSearch('wikimedia_images', url)


async def search_duckduckgo_images(query):
    encodedQuery = quote(query)
    url = f"https://duckduckgo.com/?q={encodedQuery}&iax=images&ia=images"
    return await performImageSearch('duckduckgo_images', url)


async def search_ecosia_images(query):
    encodedQuery = quote(query)
    url = f"https://www.ecosia.org/images?q={encodedQuery}"
    return await performImageSearch('ecosia_images', url)


async def search_pexels_images(query):
    encodedQuery = quote(query)
    url = f"https://www.pexels.com/search/{encodedQuery}/"
    return await performImageSearch('pexels_images', url)


async def search_pixabay_images(query):
    encodedQuery = quote(query)
    url = f"https://pixabay.com/images/search/{encodedQuery}/"
    return await performImageSearch('pixabay_images', url)


searchFunctions = {
    "bing": search_bing,
    "baidu": search_baidu,
    "sogou": search_sogou,
    "quark": search_quark,
}


async def combined_search(query, platforms, includeLinks=True):
    platformKeysRaw = platforms.split(',')
    platformKeys = [p.strip() for p in platformKeysRaw if p.strip()]

    async def runPlatform(platform):
        searchFn = searchFunctions.get(platform)
        if searchFn:
            if platform == 'bing':
                return await searchFn(query, includeLinks)
            else:
                return await searchFn(query, '1', includeLinks)
        else:
            return {"platform": platform, "success": False, "message": f"不支持的搜索平台: {platform}"}

    return await asyncio.gather(*[runPlatform(p) for p in platformKeys])


async def search(query, platforms=None, includeLinks=False):
    return await combined_search(query, platforms or "bing,baidu,sogou,quark", includeLinks)


async def search_web(query, platforms=None, includeLinks=False):
    return await search(query, platforms, includeLinks)


async def main():
    result = await combined_search('如何学习编程', 'bing,baidu,sogou,quark')
    console.log(json.dumps(result, indent=2, ensure_ascii=False, default=str))


def wrap(coreFunction, parameterNames):
    async def wrapped(params):
        args = [params.get(name) for name in parameterNames]
        return await coreFunction(*args)
    return wrapped


async def _complete_wrapper(func):
    async def wrapper(params):
        try:
            result = await func(params)
            complete({"success": True, "message": "搜索完成", "data": result})
        except Exception as error:
            complete({"success": False, "message": f"搜索失败: {str(error)}"})
    return wrapper


async def _make_export(coreFunction, parameterNames):
    wrapped = wrap(coreFunction, parameterNames)

    async def exportFn(params):
        try:
            result = await wrapped(params)
            if isinstance(result, list):
                complete({"success": True, "message": "搜索完成", "data": result})
            else:
                complete({"success": True, "message": "搜索完成", "data": result})
        except Exception as error:
            complete({"success": False, "message": f"搜索失败: {str(error)}"})
    return exportFn


# 由于 Python 无法在模块加载时 await，这里直接构造同步包装器
def _make_sync_export(coreFunction, parameterNames):
    def wrapped_sync(params):
        async def _run():
            args = [params.get(name) for name in parameterNames]
            result = await coreFunction(*args)
            if isinstance(result, list):
                complete({"success": True, "message": "搜索完成", "data": result})
            else:
                complete({"success": True, "message": "搜索完成", "data": result})
        try:
            import asyncio
            asyncio.get_event_loop().run_until_complete(_run())
        except Exception as error:
            complete({"success": False, "message": f"搜索失败: {str(error)}"})
    return wrapped_sync


# 导出：保持 async def 接口，由运行时调度
async def _search_bing_export(params):
    result = await search_bing(params.get("query"), params.get("includeLinks", False))
    complete({"success": True, "message": "搜索完成", "data": result})


async def _search_baidu_export(params):
    result = await search_baidu(params.get("query"), params.get("page"), params.get("includeLinks", False))
    complete({"success": True, "message": "搜索完成", "data": result})


async def _search_sogou_export(params):
    result = await search_sogou(params.get("query"), params.get("page"), params.get("includeLinks", False))
    complete({"success": True, "message": "搜索完成", "data": result})


async def _search_quark_export(params):
    result = await search_quark(params.get("query"), params.get("page"), params.get("includeLinks", False))
    complete({"success": True, "message": "搜索完成", "data": result})


async def _search_export(params):
    result = await search(params.get("query"), params.get("platforms"), params.get("includeLinks", False))
    complete({"success": True, "message": "搜索完成", "data": result})


async def _search_web_export(params):
    result = await search_web(params.get("query"), params.get("platforms"), params.get("includeLinks", False))
    complete({"success": True, "message": "搜索完成", "data": result})


async def _search_bing_images_export(params):
    result = await search_bing_images(params.get("query"))
    complete({"success": True, "message": "图片搜索完成", "data": result})


async def _search_wikimedia_images_export(params):
    result = await search_wikimedia_images(params.get("query"))
    complete({"success": True, "message": "图片搜索完成", "data": result})


async def _search_duckduckgo_images_export(params):
    result = await search_duckduckgo_images(params.get("query"))
    complete({"success": True, "message": "图片搜索完成", "data": result})


async def _search_ecosia_images_export(params):
    result = await search_ecosia_images(params.get("query"))
    complete({"success": True, "message": "图片搜索完成", "data": result})


async def _search_pexels_images_export(params):
    result = await search_pexels_images(params.get("query"))
    complete({"success": True, "message": "图片搜索完成", "data": result})


async def _search_pixabay_images_export(params):
    result = await search_pixabay_images(params.get("query"))
    complete({"success": True, "message": "图片搜索完成", "data": result})


async def _combined_search_export(params):
    result = await combined_search(params.get("query"), params.get("platforms"), params.get("includeLinks", True))
    complete({"success": True, "message": "聚合搜索完成", "data": result})


async def _main_export(params):
    await main()


exports.search_bing = _search_bing_export
exports.search_baidu = _search_baidu_export
exports.search_sogou = _search_sogou_export
exports.search_quark = _search_quark_export
exports.search = _search_export
exports.search_web = _search_web_export
exports.search_bing_images = _search_bing_images_export
exports.search_wikimedia_images = _search_wikimedia_images_export
exports.search_duckduckgo_images = _search_duckduckgo_images_export
exports.search_ecosia_images = _search_ecosia_images_export
exports.search_pexels_images = _search_pexels_images_export
exports.search_pixabay_images = _search_pixabay_images_export
exports.combined_search = _combined_search_export
exports.main = _main_export
