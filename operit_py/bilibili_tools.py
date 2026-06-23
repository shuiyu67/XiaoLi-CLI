# METADATA
# {
#     "name": "bilibili_tools",
#     "display_name": {"zh": "Bilibili 工具集", "en": "Bilibili Toolkit"},
#     "description": {"zh": "提供B站视频信息分析功能，包括获取字幕、弹幕、评论和搜索视频。", "en": "Analyze Bilibili video information, including subtitles, danmaku, comments, and video search."},
#     "enabledByDefault": True,
#     "category": "Media",
#     "tools": [
#         {"name": "get_subtitles", "description": {"zh": "从Bilibili视频中获取字幕。", "en": "Get subtitles from a Bilibili video."}, "parameters": [
#             {"name": "url", "description": {"zh": "Bilibili视频URL，例如：https://www.bilibili.com/video/BV1x341177NN", "en": "Bilibili video URL, e.g. https://www.bilibili.com/video/BV1x341177NN"}, "type": "string", "required": True}
#         ]},
#         {"name": "get_danmaku", "description": {"zh": "从Bilibili视频中获取弹幕。", "en": "Get danmaku (bullet comments) from a Bilibili video."}, "parameters": [
#             {"name": "url", "description": {"zh": "Bilibili视频URL，例如：https://www.bilibili.com/video/BV1x341177NN", "en": "Bilibili video URL, e.g. https://www.bilibili.com/video/BV1x341177NN"}, "type": "string", "required": True},
#             {"name": "count", "description": {"zh": "要获取的弹幕数量，默认500，最多1000", "en": "Number of danmaku items to fetch (default: 500, max: 1000)."}, "type": "number", "required": False}
#         ]},
#         {"name": "get_comments", "description": {"zh": "从Bilibili视频中获取热门评论。", "en": "Get hot comments from a Bilibili video."}, "parameters": [
#             {"name": "url", "description": {"zh": "Bilibili视频URL，例如：https://www.bilibili.com/video/BV1x341177NN", "en": "Bilibili video URL, e.g. https://www.bilibili.com/video/BV1x341177NN"}, "type": "string", "required": True}
#         ]},
#         {"name": "search_videos", "description": {"zh": "在Bilibili上搜索视频。", "en": "Search videos on Bilibili."}, "parameters": [
#             {"name": "keyword", "description": {"zh": "要搜索的关键词", "en": "Keyword to search for."}, "type": "string", "required": True},
#             {"name": "page", "description": {"zh": "页码，默认为1", "en": "Page number (default: 1)."}, "type": "number", "required": False},
#             {"name": "count", "description": {"zh": "返回结果的数量，默认10，最多20", "en": "Number of results to return (default: 10, max: 20)."}, "type": "number", "required": False}
#         ]},
#         {"name": "get_user_info", "description": {"zh": "获取B站用户的基本信息。", "en": "Get basic information for a Bilibili user."}, "parameters": [
#             {"name": "mid", "description": {"zh": "用户的数字ID (UID)", "en": "User numeric ID (UID)."}, "type": "number", "required": True}
#         ]}
#     ]
# }

# 参考了https://github.com/vruses/bili-api-interceptor/blob/master/dist/bili-api-interceptor.user.js 特此感谢

import json
import re
import time
import math
import random
import hashlib
import base64
import zlib
from urllib.parse import quote, unquote

Error = Exception

# Bilibili API endpoints
API_GET_VIEW_INFO = "https://api.bilibili.com/x/web-interface/view"
API_GET_SUBTITLE_LIST = "https://api.bilibili.com/x/player/v2"
API_GET_DANMAKU = "https://api.bilibili.com/x/v1/dm/list.so"
API_GET_COMMENTS = "https://api.bilibili.com/x/v2/reply/wbi/main"
API_SEARCH = "https://api.bilibili.com/x/web-interface/search/all/v2"
API_NAV = "https://api.bilibili.com/x/web-interface/nav"
API_GET_USER_INFO = "https://api.bilibili.com/x/space/wbi/acc/info"
API_GET_RELATION_STAT = "https://api.bilibili.com/x/relation/stat"

client = OkHttp.newClient()
SESSDATA = None
wbiKeys = None
buvid3 = None


def generateBuvid3():
    result = []
    template = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'
    for c in template:
        r = int(random.random() * 16)
        if c == 'x':
            v = r
        elif c == 'y':
            v = (r & 0x3) | 0x8
        else:
            v = c
        result.append(format(v, 'x') if c in 'xy' else c)
    return ''.join(result)


async def init():
    global SESSDATA, wbiKeys
    if SESSDATA is None:
        # SESSDATA 是B站的Cookie，用于访问一些需要登录的API。
        # 为了简单起见，这里我们不作强制要求。
        # 如果遇到请求失败的情况，可以尝试手动在这里设置你的SESSDATA值。
        # 例如: SESSDATA = "your_sessdata_cookie_value";
        SESSDATA = ""
        if not SESSDATA:
            console.log("SESSDATA 未设置，部分需要登录的请求可能会失败。")
    # Pre-fetch WBI keys if not already available.
    if not wbiKeys:
        wbiKeys = await get_wbi_keys()


def getHeaders():
    global buvid3
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Referer': 'https://www.bilibili.com/',
    }

    if not buvid3:
        buvid3 = generateBuvid3()

    cookies = [f'buvid3={buvid3}']
    if SESSDATA:
        cookies.append(f'SESSDATA={SESSDATA}')
    headers['Cookie'] = '; '.join(cookies)

    return headers


def unescapeXml(text):
    return (
        text.replace('&lt;', '<')
        .replace('&gt;', '>')
        .replace('&amp;', '&')
        .replace('&quot;', '"')
        .replace('&apos;', "'")
    )


mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]


def getMixinKey(orig):
    return ''.join([orig[n] for n in mixinKeyEncTab])[:32]


def encWbi(params, img_key, sub_key):
    mixin_key = getMixinKey(img_key + sub_key)
    curr_time = round(time.time())
    chr_filter = r"[!'()*]"

    new_params = dict(params)
    new_params['wts'] = curr_time

    query = '&'.join(
        [f"{quote(key)}={quote(re.sub(chr_filter, '', str(new_params[key])))}" for key in sorted(new_params.keys())]
    )

    w_rid = hashlib.md5((query + mixin_key).encode('utf-8')).hexdigest()
    return f"{query}&w_rid={w_rid}"


async def get_wbi_keys():
    try:
        response = await client.get(API_NAV, getHeaders())
        if not response.isSuccessful():
            console.error("Failed to get WBI keys, status: " + str(response.statusCode))
            return None
        navData = response.json()

        wbi_img = navData.get("data", {}).get("wbi_img", {}) if isinstance(navData.get("data"), dict) else {}
        if not wbi_img.get("img_url") or not wbi_img.get("sub_url"):
            console.error("Failed to get WBI keys: " + str(navData.get("message") or "No wbi_img in response"))
            return None

        imgUrl = wbi_img["img_url"]
        subUrl = wbi_img["sub_url"]

        img_key = imgUrl[imgUrl.rfind('/') + 1:imgUrl.rfind('.')]
        sub_key = subUrl[subUrl.rfind('/') + 1:subUrl.rfind('.')]

        return {"img_key": img_key, "sub_key": sub_key}
    except Exception as e:
        console.error(f"Error fetching WBI keys: {str(e)}")
        return None


async def extract_bvid(url):
    match = re.search(r"BV[a-zA-Z0-9_]+", url)
    if match:
        return match.group(0)

    if 'b23.tv' in url:
        try:
            request = client.newRequest().url(url).method("HEAD").build()
            response = await request.execute()
            finalUrl = response.raw.url
            if finalUrl:
                match = re.search(r"BV[a-zA-Z0-9_]+", finalUrl)
                if match:
                    return match.group(0)
        except Exception as e:
            console.error(f"Error resolving short URL: {e}")
    return None


async def get_video_basic_info(bvid):
    try:
        url = f"{API_GET_VIEW_INFO}?bvid={bvid}"
        response = await client.get(url, getHeaders())
        if not response.isSuccessful():
            return {"aid": None, "cid": None, "error": f"Failed to get video info, status: {response.statusCode}"}
        data = response.json()
        if data.get("code") != 0:
            return {"aid": None, "cid": None, "error": f"Failed to get video info: {data.get('message')}"}
        videoData = data.get("data", {})
        return {"aid": videoData.get("aid"), "cid": videoData.get("cid"), "error": None}
    except Exception as e:
        return {"aid": None, "cid": None, "error": f"Failed to fetch video details: {str(e)}"}


async def get_subtitles_from_api(aid, cid):
    subtitles = []
    try:
        url = f"{API_GET_SUBTITLE_LIST}?aid={aid}&cid={cid}"
        response = await client.get(url, getHeaders())
        if not response.isSuccessful():
            return {"subtitles": [], "error": f"Could not fetch subtitles list, status: {response.statusCode}"}
        subtitleListData = response.json()
        sub_data = subtitleListData.get("data", {}) if isinstance(subtitleListData.get("data"), dict) else {}
        sub_subtitles = sub_data.get("subtitle", {}).get("subtitles", []) if isinstance(sub_data.get("subtitle"), dict) else []
        if subtitleListData.get("code") == 0 and sub_subtitles:
            for sub_meta in sub_subtitles:
                if sub_meta.get("subtitle_url"):
                    try:
                        subtitle_json_url = f"https:{sub_meta['subtitle_url']}"
                        sub_content_response = await client.get(subtitle_json_url, getHeaders())
                        if sub_content_response.isSuccessful():
                            sub_content = sub_content_response.json()
                            subtitle_body = sub_content.get("body") or []
                            content_list = [item.get("content", '') for item in subtitle_body]
                            subtitles.append({
                                "lan": sub_meta.get("lan"),
                                "content": content_list,
                            })
                    except Exception as e:
                        console.error(f"Could not fetch or parse subtitle content from {sub_meta.get('subtitle_url')}: {str(e)}")
        return {"subtitles": subtitles, "error": None}
    except Exception as e:
        return {"subtitles": [], "error": f"Could not fetch subtitles: {str(e)}"}


async def get_danmaku_from_api(cid, count):
    danmaku_list = []
    try:
        url = f"{API_GET_DANMAKU}?oid={cid}"
        response = await client.get(url, getHeaders())

        if not response.isSuccessful():
            return {"danmaku": [], "error": f"Failed to get danmaku, status: {response.statusCode}"}

        compressedData = response.bodyAsBase64()
        console.log("base64" + str(compressedData))
        if not compressedData:
            return {"danmaku": [], "error": None}

        # pako.inflate 降级为 Python zlib 解压
        raw_bytes = base64.b64decode(compressedData)
        try:
            decompressed = zlib.decompress(raw_bytes, -zlib.MAX_WBITS)
        except Exception:
            decompressed = zlib.decompress(raw_bytes)
        danmaku_content = decompressed.decode('utf-8', errors='ignore')

        regex = re.compile(r'<d p=".*?">(.*?)</d>', re.DOTALL)
        for match in regex.finditer(danmaku_content):
            if len(danmaku_list) >= count:
                break
            danmaku_list.append(unescapeXml(match.group(1)))

        return {"danmaku": danmaku_list, "error": None}
    except Exception as e:
        return {"danmaku": [], "error": f"Failed to get or parse danmaku: {str(e)}"}


async def get_comments_from_api(aid):
    all_comments = []

    if not wbiKeys:
        return {"comments": "", "count": 0, "error": "获取 WBI keys 失败，无法请求评论 API"}

    page_num = 1
    total_pages = 1

    try:
        while page_num <= total_pages:
            params = {
                "type": 1,
                "oid": aid,
                "sort": 2,  # sort=2 for hot
                "pn": page_num,
            }

            signed_query = encWbi(params, wbiKeys["img_key"], wbiKeys["sub_key"])
            url = f"{API_GET_COMMENTS}?{signed_query}"

            response = await client.get(url, getHeaders())

            if not response.isSuccessful():
                console.error(f"Failed to get comments page {page_num}, status: {response.statusCode}")
                page_num += 1
                continue

            comments_data = response.json()

            if comments_data.get("code") != 0:
                console.error(f"API error on page {page_num}: {comments_data.get('message')}")
                page_num += 1
                continue

            cdata = comments_data.get("data", {}) if isinstance(comments_data.get("data"), dict) else {}
            if page_num == 1 and cdata.get("page"):
                total_pages = math.ceil(cdata["page"]["count"] / cdata["page"]["size"])

            if cdata.get("replies"):
                for comment in cdata["replies"]:
                    formatted_comment = format_comment(comment)
                    if formatted_comment:
                        all_comments.append(formatted_comment)
            page_num += 1
        comment_summary = format_comments_to_string(all_comments)
        return {"comments": comment_summary, "count": len(all_comments), "error": None}
    except Exception as e:
        comment_summary = format_comments_to_string(all_comments)
        return {"comments": comment_summary, "count": len(all_comments), "error": f"Failed to get comments: {str(e)}"}


def format_comment(comment_item):
    sub_comments = [fc for fc in (format_comment(r) for r in (comment_item.get("replies") or [])) if fc]
    return {
        "user": comment_item.get("member", {}).get("uname"),
        "content": comment_item.get("content", {}).get("message"),
        "likes": comment_item.get("like") or 0,
        "time": time.strftime("%Y/%m/%d", time.localtime(comment_item.get("ctime", 0) * 1000 / 1000)),
        "sub_comments": sub_comments,
    }


def format_comments_to_string(comments):
    result = []

    def format_single(comment, indent):
        result.append(f"{indent}- {comment['user']} (👍{comment['likes']}) [{comment['time']}]: {comment['content']}")
        if comment.get("sub_comments") and len(comment["sub_comments"]) > 0:
            for sub in comment["sub_comments"]:
                format_single(sub, indent + "  ")

    for comment in comments:
        format_single(comment, "")
    return '\n'.join(result)


async def get_subtitles(params):
    await init()
    bvid = await extract_bvid(params.get("url"))
    if not bvid:
        return {"success": False, "message": f"错误: 无法从 URL 提取 BV 号: {params.get('url')}"}

    info = await get_video_basic_info(bvid)
    aid = info["aid"]
    cid = info["cid"]
    infoError = info["error"]
    if infoError:
        return {"success": False, "message": f"获取视频信息失败: {infoError}"}
    if not aid or not cid:
        return {"success": False, "message": "获取视频 aid 或 cid 失败"}

    sub_result = await get_subtitles_from_api(aid, cid)
    subtitles = sub_result["subtitles"]
    subtitlesError = sub_result["error"]
    if subtitlesError:
        return {"success": False, "message": f"获取字幕失败: {subtitlesError}"}

    if len(subtitles) == 0:
        return {"success": True, "message": "该视频没有字幕", "data": []}

    return {"success": True, "message": f"成功获取 {len(subtitles)} 门语言的字幕", "data": subtitles}


async def get_danmaku(params):
    await init()
    url = params.get("url")
    count = params.get("count", 500)
    bvid = await extract_bvid(url)
    if not bvid:
        return {"success": False, "message": f"错误: 无法从 URL 提取 BV 号: {url}"}

    if count > 1000:
        return {"success": False, "message": "参数 'count' 不能超过 1000"}

    info = await get_video_basic_info(bvid)
    aid = info["aid"]
    cid = info["cid"]
    infoError = info["error"]
    if infoError:
        return {"success": False, "message": f"获取视频信息失败: {infoError}"}
    if not cid:
        return {"success": False, "message": "获取视频 cid 失败"}

    dm_result = await get_danmaku_from_api(cid, count)
    danmaku = dm_result["danmaku"]
    danmakuError = dm_result["error"]
    if danmakuError:
        return {"success": False, "message": f"获取弹幕失败: {danmakuError}"}

    if len(danmaku) == 0:
        return {"success": True, "message": "该视频没有弹幕", "data": []}

    return {"success": True, "message": f"成功获取 {len(danmaku)} 条弹幕", "data": danmaku}


async def get_comments(params):
    await init()
    bvid = await extract_bvid(params.get("url"))
    if not bvid:
        return {"success": False, "message": f"错误: 无法从 URL 提取 BV 号: {params.get('url')}"}

    info = await get_video_basic_info(bvid)
    aid = info["aid"]
    infoError = info["error"]
    if infoError:
        return {"success": False, "message": f"获取视频信息失败: {infoError}"}
    if not aid:
        return {"success": False, "message": "获取视频 aid 失败"}

    cmt_result = await get_comments_from_api(aid)
    comments = cmt_result["comments"]
    count = cmt_result["count"]
    commentsError = cmt_result["error"]

    if commentsError and count == 0:
        return {"success": False, "message": f"获取评论失败: {commentsError}"}

    if count == 0:
        return {"success": True, "message": "该视频没有热门评论", "data": ""}

    message = (
        f"成功获取 {count} 条热门评论，但过程中发生错误: {commentsError}"
        if commentsError
        else f"成功获取 {count} 条热门评论"
    )

    return {"success": True, "message": message, "data": comments}


async def search_videos_from_api(keyword, page):
    if not wbiKeys:
        return {"results": None, "error": "获取 WBI keys 失败，无法请求搜索 API"}

    try:
        params = {
            "keyword": keyword,
            "page": page,
            "search_type": "video",
        }

        signed_query = encWbi(params, wbiKeys["img_key"], wbiKeys["sub_key"])
        url = f"{API_SEARCH}?{signed_query}"

        response = await client.get(url, getHeaders())

        if not response.isSuccessful():
            return {"results": None, "error": f"搜索失败, status: {response.statusCode}"}

        search_data = response.json()
        if search_data.get("code") != 0:
            return {"results": None, "error": f"搜索 API 错误: {search_data.get('message')}"}

        return {"results": search_data.get("data"), "error": None}
    except Exception as e:
        return {"results": None, "error": f"搜索时发生异常: {str(e)}"}


def format_search_results_to_string(data, count):
    if not data or not data.get("result"):
        return {"formatted": "没有找到相关结果。", "result_count": 0, "total_count": 0}

    videoResults = None
    for item in data.get("result", []):
        if item.get("result_type") == "video":
            videoResults = item.get("data")
            break

    if not videoResults or len(videoResults) == 0:
        return {"formatted": "没有找到相关视频结果。", "result_count": 0, "total_count": data.get("numResults") or 0}

    slicedResults = videoResults[:count]

    formatted_parts = []
    for index, video in enumerate(slicedResults):
        cleanTitle = re.sub(r'<em class="keyword">|</em>', "", video.get("title", ""))
        cleanDescription = re.sub(r'<em class="keyword">|</em>', "", video.get("description", ""))
        desc_preview = cleanDescription[:100] if cleanDescription else ""
        desc_preview = desc_preview + ("..." if len(cleanDescription) > 100 else "")
        parts = [
            f'{index + 1}. "{cleanTitle}" - {video.get("author")}',
            f'   BV ID: {video.get("bvid")}',
            f'   播放: {format(video.get("play") or 0, ",")}',
            f'   弹幕: {format(video.get("danmaku") or 0, ",")}',
            f'   点赞: {format(video.get("like") or 0, ",")}',
            f'   时长: {video.get("duration")}',
            f'   发布于: {time.strftime("%Y/%m/%d", time.localtime(video.get("pubdate", 0)))}',
            f'   简介: {desc_preview}',
        ]
        formatted_parts.append("\n".join(parts))

    formattedResults = "\n\n".join(formatted_parts)

    return {"formatted": formattedResults, "result_count": len(slicedResults), "total_count": data.get("numResults") or 0}


async def search_videos(params):
    await init()
    keyword = params.get("keyword")
    page = params.get("page", 1)
    count = params.get("count", 10)

    if count > 20:
        return {"success": False, "message": "参数 'count' 不能超过 20"}

    sr = await search_videos_from_api(keyword, page)
    results = sr["results"]
    error = sr["error"]
    if error:
        return {"success": False, "message": f"搜索失败: {error}"}

    fmt = format_search_results_to_string(results, count)
    formatted = fmt["formatted"]
    result_count = fmt["result_count"]
    total_count = fmt["total_count"]

    if result_count == 0:
        return {"success": True, "message": "没有找到相关视频。", "data": ""}

    message = f'成功为 "{keyword}" 找到 {total_count} 个相关视频，当前显示第 {page} 页的 {result_count} 个结果。'
    return {"success": True, "message": message, "data": formatted}


def format_user_info_to_string(user):
    return '\n'.join([
        f"昵称: {user['name']} (UID: {user['mid']})",
        f"性别: {user['sex']}",
        f"等级: LV{user['level']}",
        f"生日: {user.get('birthday') or '未设置'}",
        f"粉丝数: {format(user['follower'], ',')}",
        f"关注数: {format(user['following'], ',')}",
        f"个人简介: {user.get('sign') or '这个UP主很懒，什么都没有写...'}",
        f"头像链接: {user['face']}",
    ])


async def get_user_info_from_api(mid):
    if not wbiKeys:
        return {"user_info": None, "error": "获取 WBI keys 失败，无法请求用户信息 API"}

    try:
        # Get user account info (WBI signed)
        params = {"mid": mid}
        signed_query = encWbi(params, wbiKeys["img_key"], wbiKeys["sub_key"])
        url = f"{API_GET_USER_INFO}?{signed_query}"
        response = await client.get(url, getHeaders())

        if not response.isSuccessful():
            return {"user_info": None, "error": f"获取用户信息失败, status: {response.statusCode}"}

        userData = response.json()
        if userData.get("code") != 0:
            return {"user_info": None, "error": f"用户信息 API 错误: {userData.get('message')}"}

        # Get user relation stat (not WBI signed)
        statUrl = f"{API_GET_RELATION_STAT}?vmid={mid}"
        statResponse = await client.get(statUrl, getHeaders())
        follower = -1
        following = -1
        if statResponse.isSuccessful():
            statData = statResponse.json()
            if statData.get("code") == 0:
                follower = statData.get("data", {}).get("follower")
                following = statData.get("data", {}).get("following")

        udata = userData.get("data", {})
        userInfo = {
            "mid": udata.get("mid"),
            "name": udata.get("name"),
            "sex": udata.get("sex"),
            "face": udata.get("face"),
            "sign": udata.get("sign"),
            "level": udata.get("level"),
            "birthday": udata.get("birthday"),
            "follower": follower,
            "following": following,
        }

        return {"user_info": userInfo, "error": None}
    except Exception as e:
        return {"user_info": None, "error": f"获取用户信息时发生异常: {str(e)}"}


async def get_user_info(params):
    await init()
    mid = params.get("mid")

    if not mid or not isinstance(mid, (int, float)) or mid <= 0:
        return {"success": False, "message": "参数 'mid' 必须是一个正整数"}

    ui = await get_user_info_from_api(mid)
    user_info = ui["user_info"]
    error = ui["error"]
    if error:
        return {"success": False, "message": f"获取用户信息失败: {error}"}

    if not user_info:
        return {"success": False, "message": "未能获取到用户信息"}

    formatted_info = format_user_info_to_string(user_info)
    message = f"成功获取 UID:{mid} 的用户信息。"

    return {"success": True, "message": message, "data": formatted_info}


async def wrapToolExecution(func, params):
    try:
        result = await func(params)
        complete(result)
    except Exception as error:
        console.error(f"Tool {func.__name__} failed unexpectedly", error)
        complete({
            "success": False,
            "message": f"工具执行时发生意外错误: {str(error)}",
        })


async def main():
    console.log("--- Bilibili Video Analysis Tool Test ---")
    testUrl = "https://www.bilibili.com/video/BV1NRE5zmE3W"
    testKeyword = "OpenAI"

    console.log("\n[1/4] Testing search_videos...")
    searchResult = await search_videos({"keyword": testKeyword, "count": 10})
    if searchResult["success"]:
        console.log(f"Success: {searchResult['message']}")
        console.log(f'---------- Search Results for "{testKeyword}" ----------')
        console.log(searchResult["data"])
        console.log("------------------------------------------")
    else:
        console.error(f"Failure: {searchResult['message']}")

    console.log("\n[2/4] Testing get_subtitles...")
    subtitlesResult = await get_subtitles({"url": testUrl})
    console.log(json.dumps(subtitlesResult, indent=2, ensure_ascii=False))

    console.log("\n[3/4] Testing get_danmaku with count limit...")
    danmakuResult = await get_danmaku({"url": testUrl, "count": 20})
    console.log(json.dumps(danmakuResult, indent=2, ensure_ascii=False))

    console.log("\n[4/4] Testing get_comments...")
    commentsResult = await get_comments({"url": testUrl})
    if commentsResult["success"]:
        console.log(f"Success: {commentsResult['message']}")
        console.log("---------- Comments ----------")
        console.log(commentsResult["data"])
        console.log("----------------------------")
    else:
        console.error(f"Failure: {commentsResult['message']}")

    console.log("\n[5/5] Testing get_user_info...")
    userInfoResult = await get_user_info({"mid": 2})
    if userInfoResult["success"]:
        console.log(f"Success: {userInfoResult['message']}")
        console.log("---------- User Info ----------")
        console.log(userInfoResult["data"])
        console.log("-----------------------------")
    else:
        console.error(f"Failure: {userInfoResult['message']}")

    complete({"success": True, "message": "Test finished."})


async def _get_subtitles_wrapper(params):
    await wrapToolExecution(get_subtitles, params)


async def _get_danmaku_wrapper(params):
    await wrapToolExecution(get_danmaku, params)


async def _get_comments_wrapper(params):
    await wrapToolExecution(get_comments, params)


async def _search_videos_wrapper(params):
    await wrapToolExecution(search_videos, params)


async def _get_user_info_wrapper(params):
    await wrapToolExecution(get_user_info, params)


exports.get_subtitles = _get_subtitles_wrapper
exports.get_danmaku = _get_danmaku_wrapper
exports.get_comments = _get_comments_wrapper
exports.search_videos = _search_videos_wrapper
exports.get_user_info = _get_user_info_wrapper
exports.main = main
