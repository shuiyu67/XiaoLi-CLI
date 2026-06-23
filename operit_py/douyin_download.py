# METADATA
# {
#     "name": "douyin_download",
#
#     "display_name": {
#         "zh": "抖音下载工具",
#         "en": "Douyin Download Tool"
#     },
#     "description": { "zh": "抖音工具包，提供从分享链接或分享口令中提取并下载无水印视频的功能。", "en": "Douyin toolkit for extracting and downloading watermark-free videos from share links or share codes." },
#     "enabledByDefault": true,
#     "category": "Media",
#     "tools": [
#         {
#             "name": "get_douyin_download_link",
#             "description": { "zh": "解析抖音分享链接或口令，下载无水印视频到本地", "en": "Parse a Douyin share link/code and download a watermark-free video to local storage." },
#             "parameters": [
#                 {
#                     "name": "input",
#                     "description": { "zh": "抖音分享链接或包含链接的分享口令文本", "en": "Douyin share link, or share-code text that contains a link." },
#                     "type": "string",
#                     "required": true
#                 }
#             ]
#         },
#         {
#             "name": "get_douyin_video_info",
#             "description": { "zh": "解析抖音分享链接或口令，仅获取视频信息和无水印下载链接，不下载视频", "en": "Parse a Douyin share link/code and return video info + watermark-free download URL (without downloading)." },
#             "parameters": [
#                 {
#                     "name": "input",
#                     "description": { "zh": "抖音分享链接或包含链接的分享口令文本", "en": "Douyin share link, or share-code text that contains a link." },
#                     "type": "string",
#                     "required": true
#                 }
#             ]
#         }
#     ]
# }

import re
import json
import traceback

client = OkHttp.newClient()

# 抖音相关URL模式
DOUYIN_URL_PATTERNS = [
    re.compile(r'https?://v\.douyin\.com/[^\s]+'),
    re.compile(r'https?://www\.douyin\.com/video/[0-9]+'),
    re.compile(r'https?://www\.douyin\.com/share/video/[0-9]+')
]


async def douyin_wrap(func, params, successMessage, failMessage):
    """包装函数调用，提供标准化的成功/错误处理"""
    try:
        console.log(f"开始执行函数: {func.__name__ or '匿名函数'}")
        result = await func(params)
        complete({"success": True, "message": successMessage, "data": result})
    except Exception as error:
        msg = str(error) if isinstance(error, Exception) else str(error)
        console.error(f"函数 {func.__name__ or '匿名函数'} 执行失败! 错误: {msg}")
        stack = traceback.format_exc() if isinstance(error, Exception) else None
        complete({"success": False, "message": f"{failMessage}: {msg}", "error_stack": stack})


def extractDouyinUrl(text):
    """从文本中提取抖音链接"""
    for pattern in DOUYIN_URL_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


async def resolveDouyinUrl(shareUrl):
    """解析抖音分享链接，获取视频信息"""
    try:
        console.log(f"正在解析抖音链接: {shareUrl}")

        request = client.newRequest()
        request = request.url(shareUrl)
        request = request.method("GET")
        request = request.headers({
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/121.0.2277.107 Version/17.0 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive"
        })

        response = await request.build().execute()

        if not response.isSuccessful():
            raise Exception(f"链接解析失败 ({response.statusCode})")

        html = response.content

        # 尝试从ROUTER_DATA中提取视频信息
        routerDataMatch = re.search(r'window\._ROUTER_DATA\s*=\s*({.*?})</script>', html, re.DOTALL)
        if routerDataMatch and routerDataMatch.group(1):
            try:
                routerData = json.loads(routerDataMatch.group(1))
                # The actual key might vary, let's find it dynamically
                loaderData = routerData.get("loaderData", {}) if isinstance(routerData, dict) else {}
                pageDataKey = next((k for k in loaderData.keys() if "/page" in k), None)
                if not pageDataKey:
                    raise Exception("无法在 _ROUTER_DATA 中找到页面数据")
                pageData = loaderData.get(pageDataKey) or {}
                videoInfoRes = pageData.get("videoInfoRes") or {}
                item_list = videoInfoRes.get("item_list") or []
                videoData = item_list[0] if len(item_list) > 0 else None

                if videoData:
                    videoId = videoData.get("aweme_id")
                    videoTitle = videoData.get("desc")
                    video = videoData.get("video") or {}
                    play_addr = video.get("play_addr") or {}
                    url_list = play_addr.get("url_list") or []
                    watermarkedUrl = url_list[0] if len(url_list) > 0 else None

                    if videoId and videoTitle and watermarkedUrl:
                        console.log(f"通过 _ROUTER_DATA 找到视频信息: ID={videoId}")
                        downloadUrl = watermarkedUrl.replace("playwm", "play")
                        return {"videoId": videoId, "downloadUrl": downloadUrl, "videoTitle": videoTitle}
            except Exception as e:
                msg = str(e) if isinstance(e, Exception) else str(e)
                console.error(f"解析 _ROUTER_DATA JSON 失败: {msg}")

        raise Exception("无法从HTML中解析出 _ROUTER_DATA")

    except Exception as error:
        msg = str(error) if isinstance(error, Exception) else str(error)
        console.error(f"解析抖音链接时出错: {msg}")
        raise error


async def get_douyin_download_link(params):
    """获取抖音视频的无水印下载链接并下载视频"""
    input_ = params.get("input")

    if not input_:
        raise Exception("输入内容不能为空")

    console.log("开始获取并下载抖音无水印视频...")

    try:
        # 1. 提取和解析URL
        douyinUrl = extractDouyinUrl(input_)
        if not douyinUrl:
            raise Exception("未找到有效的抖音链接")
        console.log(f"找到抖音链接: {douyinUrl}")

        # 2. 解析链接并获取所有需要的视频信息
        console.log("正在解析分享链接...")
        resolved = await resolveDouyinUrl(douyinUrl)
        videoId = resolved["videoId"]
        downloadUrl = resolved["downloadUrl"]
        rawVideoTitle = resolved["videoTitle"]
        console.log(f"解析到视频ID: {videoId}")
        console.log(f"获取到无水印下载链接: {downloadUrl}")

        # 获取视频标题（用于文件命名）
        videoTitle = (rawVideoTitle or f"douyin_{videoId}").strip()
        # 替换文件名中的非法字符
        videoTitle = re.sub(r'[\\/:*?"<>|]', '_', videoTitle)

        # 逐级创建目录并下载视频
        baseDir = getPluginConfigDir("douyin_download")
        destinationDir = f"{baseDir}/downloads"
        destinationPath = f"{destinationDir}/{videoTitle}_{videoId}.mp4"

        console.log(f"确保目录存在: {destinationDir}")
        # 逐级创建目录以确保路径存在
        dirsToCreate = [baseDir, destinationDir]
        for dir_ in dirsToCreate:
            mkdirResult = await Tools.Files.mkdir(dir_)
            if not mkdirResult.get("successful"):
                # 忽略"目录已存在"的错误，但记录其他可能的错误
                console.warn(f"创建目录 '{dir_}' 失败 (可能已存在): {mkdirResult.get('details')}")

        console.log(f"开始下载视频到: {destinationPath}")
        downloadResult = await Tools.Files.download(downloadUrl, destinationPath)

        if not downloadResult.get("successful"):
            raise Exception(f"视频下载失败: {downloadResult.get('details')}")

        successMessage = f'视频"{videoTitle}"成功下载到: {destinationPath}'
        console.log(successMessage)
        return successMessage

    except Exception as error:
        message = str(error) if isinstance(error, Exception) else str(error)
        console.error(f"处理失败: {message}")
        # 重新抛出错误，以便包装器可以捕获它
        raise Exception(message)


async def get_douyin_video_info(params):
    """获取抖音视频信息和无水印下载链接（不下载视频）"""
    input_ = params.get("input")

    if not input_:
        raise Exception("输入内容不能为空")

    console.log("开始解析抖音视频信息...")

    try:
        # 1. 提取URL
        douyinUrl = extractDouyinUrl(input_)
        if not douyinUrl:
            raise Exception("未找到有效的抖音链接")
        console.log(f"找到抖音链接: {douyinUrl}")

        # 2. 解析链接并获取视频信息
        console.log("正在解析分享链接...")
        resolved = await resolveDouyinUrl(douyinUrl)
        videoId = resolved["videoId"]
        downloadUrl = resolved["downloadUrl"]
        videoTitle = resolved["videoTitle"]
        console.log(f"解析到视频ID: {videoId}")
        console.log(f"获取到无水印下载链接: {downloadUrl}")
        console.log(f"视频标题: {videoTitle}")

        result = {
            "videoId": videoId,
            "videoTitle": videoTitle,
            "downloadUrl": downloadUrl,
            "originalUrl": douyinUrl
        }

        console.log("视频信息解析成功")
        return result

    except Exception as error:
        message = str(error) if isinstance(error, Exception) else str(error)
        console.error(f"解析失败: {message}")
        raise Exception(message)


async def main():
    """抖音工具功能测试主函数"""
    console.log("🚀 开始执行抖音工具功能测试...")
    await test_download_link()
    summary = "抖音下载工具测试完成！\n" + "✅ 下载功能已测试"
    console.log(f"\n{summary}")
    return summary


async def test_download_link():
    """测试下载功能"""
    testUrl = "3.00 05/24 Z@M.JI TLW:/ 这里有几首melodic dubstep，看你认识几个 # 电子音乐 # 音乐分享 # 顶级旋律 # 热门音乐🔥百听不厌 # 戴上耳机  https://v.douyin.com/AT8AfEbuP_k/ 复制此链接，打开Dou音搜索，直接观看视频！"  # 使用真实分享文本进行测试
    console.log("1. 测试视频下载功能 (使用真实分享文本)")
    # 我们预期这个调用会成功提取URL并尝试下载
    try:
        result = await get_douyin_download_link({"input": testUrl})
        console.log(f"✅ 下载功能测试成功, 结果: {result}")
        return result
    except Exception as e:
        errorMessage = str(e) if isinstance(e, Exception) else str(e)
        console.error(f"❌ 下载功能测试失败: {errorMessage}")
        # 在测试中，即使是预期的失败，也应该被视为一个需要注意的问题
        raise e


async def get_douyin_download_link_wrapper(params):
    await douyin_wrap(get_douyin_download_link, params, "抖音视频下载完成", "抖音视频下载失败")


async def get_douyin_video_info_wrapper(params):
    await douyin_wrap(get_douyin_video_info, params, "抖音视频信息获取成功", "抖音视频信息获取失败")


async def main_wrapper(params=None):
    await douyin_wrap(main, params, "抖音工具测试完成", "抖音工具测试失败")


async def test_download_link_wrapper(params=None):
    await douyin_wrap(test_download_link, params, "下载链接获取测试成功", "下载链接获取测试失败")


# 导出所有功能
exports.get_douyin_download_link = get_douyin_download_link_wrapper
exports.get_douyin_video_info = get_douyin_video_info_wrapper
exports.main = main_wrapper
exports.test_download_link = test_download_link_wrapper
