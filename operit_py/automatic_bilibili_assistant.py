# METADATA
# {
#     "name": "Automatic_bilibili_assistant",
#     "display_name": {"zh": "Bilibili自动化助手", "en": "Bilibili Automation Assistant"},
#     "description": {"zh": "高级B站智能助手，通过UI自动化技术实现B站应用交互，支持视频搜索播放、评论互动、用户关注等功能，为AI赋予B站社交和内容消费能力。适用于自动追番、视频推荐、社交互动等场景。", "en": "Advanced Bilibili assistant powered by UI automation. Supports video search/playback, commenting, and following uploaders, enabling AI-driven content consumption and social interaction on Bilibili."},
#     "category": "Automatic",
#     "tools": [
#         {"name": "workflow_guide", "description": {"zh": "B站助手工具使用流程指南。", "en": "Workflow guide for the Bilibili assistant."}, "parameters": [], "advice": True},
#         {"name": "search_video", "description": {"zh": "在B站搜索视频内容", "en": "Search videos on Bilibili."}, "parameters": [
#             {"name": "keyword", "description": {"zh": "搜索关键词", "en": "Search keyword."}, "type": "string", "required": True},
#             {"name": "filter_type", "description": {"zh": "搜索结果过滤类型：comprehensive(综合)、new(最新)、hot(最多播放)、danmaku(最多弹幕)", "en": "Result filter: comprehensive, new, hot (most played), danmaku (most danmaku)."}, "type": "string", "required": False}
#         ]},
#         {"name": "play_video", "description": {"zh": "播放指定的视频，可以通过标题或位置选择", "en": "Play a specific video by title keyword or by index."}, "parameters": [
#             {"name": "video_title", "description": {"zh": "要播放的视频标题关键词", "en": "Keyword to match the video title."}, "type": "string", "required": False},
#             {"name": "video_index", "description": {"zh": "要播放的视频在搜索结果中的索引位置（从1开始）", "en": "Index of the video in the search results (1-based)."}, "type": "number", "required": False}
#         ]},
#         {"name": "return_to_video_list", "description": {"zh": "从视频播放界面返回到视频列表界面", "en": "Return from the video player page back to the video list."}, "parameters": []},
#         {"name": "send_comment", "description": {"zh": "在当前视频下发送评论", "en": "Post a comment under the current video."}, "parameters": [
#             {"name": "comment_text", "description": {"zh": "要发送的评论内容", "en": "Comment text to send."}, "type": "string", "required": True}
#         ]},
#         {"name": "like_video", "description": {"zh": "给当前视频点赞", "en": "Like the current video."}, "parameters": []},
#         {"name": "collect_video", "description": {"zh": "收藏当前视频", "en": "Save (favorite) the current video."}, "parameters": [
#             {"name": "folder_name", "description": {"zh": "收藏夹名称，留空则使用默认收藏夹", "en": "Favorite folder name (leave empty to use the default folder)."}, "type": "string", "required": False}
#         ]},
#         {"name": "follow_uploader", "description": {"zh": "关注当前视频的UP主", "en": "Follow the uploader (UP) of the current video."}, "parameters": []},
#         {"name": "get_video_info", "description": {"zh": "获取当前视频的详细信息", "en": "Get detailed info of the current video."}, "parameters": []},
#         {"name": "browse_comments", "description": {"zh": "浏览当前视频的评论", "en": "Browse comments of the current video."}, "parameters": [
#             {"name": "comment_count", "description": {"zh": "获取的评论数量，默认为5条", "en": "Number of comments to fetch (default: 5)."}, "type": "number", "required": False}
#         ]},
#         {"name": "navigate_to_home", "description": {"zh": "导航到B站首页", "en": "Navigate to the Bilibili home page."}, "parameters": []},
#         {"name": "navigate_to_following", "description": {"zh": "导航到关注页面", "en": "Navigate to the Following page."}, "parameters": []},
#         {"name": "navigate_to_history", "description": {"zh": "导航到观看历史页面", "en": "Navigate to the watch history page."}, "parameters": []},
#         {"name": "toggle_fullscreen", "description": {"zh": "切换视频全屏/非全屏状态", "en": "Toggle fullscreen / windowed mode."}, "parameters": []},
#         {"name": "adjust_playback_speed", "description": {"zh": "调整视频播放速度", "en": "Adjust video playback speed."}, "parameters": [
#             {"name": "speed", "description": {"zh": "播放速度：0.5x, 0.75x, 1.0x, 1.25x, 1.5x, 2.0x", "en": "Playback speed: 0.5x, 0.75x, 1.0x, 1.25x, 1.5x, 2.0x."}, "type": "string", "required": True}
#         ]}
#     ]
# }
# 注意：本脚本深度依赖 Android UI 自动化 API（UINode、Tools.UI），在非 Android 平台上运行时相关功能不可用。

import json
import re
import time
from urllib.parse import quote, unquote

Error = Exception

# B站应用包名和主要Activity
BILIBILI_PACKAGE = "tv.danmaku.bili"
MAIN_ACTIVITY = "tv.danmaku.bili.MainActivityV2"
VIDEO_ACTIVITY = "com.bilibili.ship.theseus.detail.UnitedBizDetailsActivity"


def createResponse(success, message, data=None):
    if data is None:
        data = {}
    if isinstance(data, str):
        return {"success": True, "message": message, "data": data}
    result = {"success": success, "message": message}
    if isinstance(data, dict):
        result.update(data)
    return result


async def findAndClick(finder):
    element = await finder()
    if element:
        await element.click()
        await Tools.System.sleep(1000)
        return True
    return False


async def findAndClickByText(text):
    async def _finder():
        page = await UINode.getCurrentPage()
        return page.findByText(text)
    return await findAndClick(_finder)


async def ensureMain(packageName=BILIBILI_PACKAGE):
    pageInfo = await Tools.UI.getPageInfo()

    if pageInfo.packageName == packageName and (getattr(pageInfo, "activityName", None) or "") and MAIN_ACTIVITY in (pageInfo.activityName or ""):
        console.log("Already on the main activity.")
        return True

    if pageInfo.packageName != packageName:
        console.log(f"Not in the correct app. Current: {pageInfo.packageName}. Starting {packageName}.")
        await Tools.System.startApp(packageName)
        await Tools.System.sleep(200)

    console.log("Attempting to go back to main activity.")
    for i in range(4):
        pageInfo = await Tools.UI.getPageInfo()
        if pageInfo.packageName == packageName and (getattr(pageInfo, "activityName", None) or "") and MAIN_ACTIVITY in (pageInfo.activityName or ""):
            console.log(f"Successfully returned to main activity on attempt {i + 1}.")
            return True
        if pageInfo.packageName != packageName:
            console.log("Exited the app while trying to go back.")
            break
        await Tools.UI.pressKey("KEYCODE_BACK")
        await Tools.System.sleep(500)

    console.log("Pressing back failed or exited app. Performing a full app restart.")
    await Tools.System.stopApp(packageName)
    await Tools.System.sleep(1000)
    await Tools.System.startApp(packageName)
    await Tools.System.sleep(4000)

    pageInfo = await Tools.UI.getPageInfo()
    if pageInfo.packageName == packageName and (getattr(pageInfo, "activityName", None) or "") and MAIN_ACTIVITY in (pageInfo.activityName or ""):
        console.log("Successfully reached main activity after restart.")
        return True

    console.error(f"Failed to navigate to the main activity of {packageName}.")
    return False


async def navigateToSearch():
    console.log("导航到搜索页面")
    if not await ensureMain():
        return False

    page = await UINode.getCurrentPage()
    searchContainer = page.findById('expand_search')
    if searchContainer:
        await searchContainer.click()
        await Tools.System.sleep(1000)
        return True

    return False


lastSearchResults = []


async def search_video(params):
    keyword = params.get("keyword")
    filter_type = params.get("filter_type")
    count = params.get("count", 20)

    global lastSearchResults

    console.log(f"搜索视频: {keyword}, 过滤类型: {filter_type}")

    if not await navigateToSearch():
        return createResponse(False, "无法进入搜索页面", {"keyword": keyword})

    await Tools.System.sleep(1000)

    searchInput = (await UINode.getCurrentPage()).findById('search_plate')
    if searchInput:
        await Tools.UI.setText(keyword)
        await Tools.System.sleep(500)
    else:
        await Tools.UI.setText(keyword)
        await Tools.System.sleep(500)

    searchButton = (await UINode.getCurrentPage()).findById('action_search')
    if searchButton:
        await searchButton.click()
    else:
        await Tools.UI.pressKey("KEYCODE_ENTER")

    await Tools.System.sleep(4000)

    if filter_type:
        await applySearchFilter(filter_type)

    results = await getSearchResults(count)
    lastSearchResults = results

    return createResponse(True, f"搜索到 {len(results)} 条有效视频结果", {
        "keyword": keyword,
        "filter_type": filter_type,
        "results": [{k: v for k, v in r.items() if k != 'element'} for r in results],
        "result_count": len(results),
    })


async def applySearchFilter(filterType):
    page = await UINode.getCurrentPage()
    filterButton = page.findByText("综合")
    if filterButton:
        await filterButton.click()
        await Tools.System.sleep(1000)

    if filterType == "new":
        await findAndClickByText("最新")
        await Tools.System.sleep(1000)
    elif filterType == "hot":
        await findAndClickByText("最多播放")
        await Tools.System.sleep(1000)
    elif filterType == "danmaku":
        await findAndClickByText("最多弹幕")
        await Tools.System.sleep(1000)


async def getSearchResults(desiredCount=20):
    global lastSearchResults
    page = await UINode.getCurrentPage()
    results = []
    seenTitles = set()

    resultsContainer = page.findById('tv.danmaku.bili:id/recycler_view')
    if not resultsContainer:
        console.log("Could not find search results container.")
        return results

    lastResultCount = -1
    maxScrolls = 10
    scrollCount = 0

    for i in range(maxScrolls):
        page = await UINode.getCurrentPage()
        currentContainer = page.findById('tv.danmaku.bili:id/recycler_view')
        if not currentContainer:
            break

        for item in (getattr(currentContainer, "children", None) or []):
            titleNode = item.findById('tv.danmaku.bili:id/title')
            title = titleNode.text if titleNode else None

            if not title or title in seenTitles:
                continue

            isAd = item.findById('tv.danmaku.bili:id/ad_tint_frame') or item.findById('tv.danmaku.bili:id/ad_tag')
            isUser = item.findById('tv.danmaku.bili:id/user_info')
            isGame = item.findById('tv.danmaku.bili:id/iv_background')
            isLive = item.findByText("直播")

            if isAd or isUser or isGame or isLive:
                continue

            seenTitles.add(title)

            uploaderNode = item.findById('tv.danmaku.bili:id/upper') or item.findById('tv.danmaku.bili:id/upuser')
            playCountNode = item.findById('tv.danmaku.bili:id/play_num')
            durationNode = item.findById('tv.danmaku.bili:id/duration')
            postTimeNode = item.findById('tv.danmaku.bili:id/post_time') or item.findById('tv.danmaku.bili:id/danmakus_num')

            results.append({
                "index": len(results) + 1,
                "title": title,
                "uploader": uploaderNode.text if uploaderNode else "N/A",
                "play_count": playCountNode.text if playCountNode else "N/A",
                "duration": durationNode.text if durationNode else "N/A",
                "post_time": postTimeNode.text if postTimeNode else "N/A",
                "element": item,
            })

            if len(results) >= desiredCount:
                break

        if len(results) >= desiredCount:
            console.log(f"Reached desired count of {desiredCount}.")
            break

        if len(results) == lastResultCount:
            console.log("Scrolling is not yielding new results. Stopping.")
            break
        lastResultCount = len(results)

        await Tools.UI.swipe(540, 1500, 540, 800)
        await Tools.System.sleep(1500)
        scrollCount += 1

    console.log(f"Scrolling back up {scrollCount} times.")
    for i in range(scrollCount):
        await Tools.UI.swipe(540, 800, 540, 1550)
        await Tools.System.sleep(1000)

    return results[:desiredCount]


async def play_video(params):
    video_title = params.get("video_title")
    video_index = params.get("video_index")

    if not video_title and not video_index:
        return createResponse(False, "请提供视频标题或索引。")

    console.log(f'尝试播放视频 - 标题: "{video_title}", 索引: {video_index}')

    page = await UINode.getCurrentPage()
    seenTitles = set()
    currentVideoCount = 0
    maxScrolls = 10
    videoFoundAndClicked = False
    foundVideoTitle = None

    initialContainer = page.findById('tv.danmaku.bili:id/recycler_view')
    if not initialContainer:
        return createResponse(False, "似乎不在搜索结果页面，无法播放视频。")

    lastSeenCount = -1
    scrollCount = 0

    for i in range(maxScrolls):
        page = await UINode.getCurrentPage()
        currentContainer = page.findById('tv.danmaku.bili:id/recycler_view')
        if not currentContainer:
            console.log("Could not find search results container during scroll.")
            break

        visibleItems = getattr(currentContainer, "children", None) or []

        for item in visibleItems:
            titleNode = item.findById('tv.danmaku.bili:id/title')
            title = titleNode.text if titleNode else None

            if not title or title in seenTitles:
                continue

            isAd = item.findById('tv.danmaku.bili:id/ad_tint_frame') or item.findById('tv.danmaku.bili:id/ad_tag')
            isUser = item.findById('tv.danmaku.bili:id/user_info')
            isGame = item.findById('tv.danmaku.bili:id/iv_background')
            isLive = item.findByText("直播")

            if isAd or isUser or isGame or isLive:
                continue

            seenTitles.add(title)
            currentVideoCount += 1

            shouldClick = False
            if video_index:
                if currentVideoCount == video_index:
                    shouldClick = True
            elif video_title:
                if video_title in title:
                    shouldClick = True

            if shouldClick:
                coverImage = item.findById('tv.danmaku.bili:id/cover')
                if coverImage:
                    console.log("Clicking on video cover image.")
                    await coverImage.click()
                else:
                    console.log("Cover image not found, clicking on the whole item.")
                    await item.click()
                await Tools.System.sleep(4000)
                videoFoundAndClicked = True
                foundVideoTitle = title
                break

        if videoFoundAndClicked:
            break

        if len(seenTitles) == lastSeenCount:
            console.log("Scrolling is not yielding new results. Stopping.")
            break
        lastSeenCount = len(seenTitles)

        if video_index and currentVideoCount >= video_index:
            break

        await Tools.UI.swipe(540, 1500, 540, 800)
        await Tools.System.sleep(1500)
        scrollCount += 1

    if not videoFoundAndClicked and scrollCount > 0:
        console.log(f"未找到视频，滚动回去 {scrollCount} 次")
        for i in range(scrollCount):
            await Tools.UI.swipe(540, 800, 540, 1550)
            await Tools.System.sleep(1000)

    if videoFoundAndClicked:
        return createResponse(True, f'成功开始播放视频: "{foundVideoTitle}"', {"video_title": video_title, "video_index": video_index})
    else:
        return createResponse(False, "未找到指定的视频", {"video_title": video_title, "video_index": video_index})


async def send_comment(params):
    commentText = params.get("comment_text") or ""

    if not await switch_to_comment_activity():
        return createResponse(False, "不在视频页面")

    console.log(f"发送评论: {commentText}")

    page = await UINode.getCurrentPage()
    commentArea = page.findById("input")
    if commentArea:
        await commentArea.click()
        await Tools.System.sleep(1000)

        await Tools.UI.setText(commentText)
        await Tools.System.sleep(500)

        sendButton = page.findByText("发送")
        if sendButton:
            await sendButton.click()
            await Tools.System.sleep(1000)

            return createResponse(True, "评论发送成功", {"comment_text": commentText})
    else:
        return createResponse(False, "未找到评论输入框", {"comment_text": commentText})


async def is_in_video_activity():
    pageInfo = await Tools.UI.getPageInfo()
    return VIDEO_ACTIVITY in (getattr(pageInfo, "activityName", "") or "")


async def is_on_search_results_page():
    page = await UINode.getCurrentPage()
    filterButton = page.findByText("综合") and page.findByText("搜索")
    return bool(filterButton)


async def return_to_video_list(params):
    console.log("Attempting to return to video list...")
    if await is_in_video_activity():
        await Tools.UI.pressKey("KEYCODE_BACK")
        await Tools.System.sleep(2000)
        if await is_on_search_results_page():
            return createResponse(True, "Successfully returned to video list.")
        else:
            return createResponse(False, "Failed to return to video list, did not land on search results page.")
    else:
        if await is_on_search_results_page():
            return createResponse(True, "Already on the video list page.")
        return createResponse(False, "Not in a video activity, no action taken.")


async def switch_to_comment_activity():
    if not await is_in_video_activity():
        return False
    console.log("切换到评论页面")
    await findAndClickByText("评论")
    await Tools.System.sleep(1000)
    return True


async def like_video(params):
    if not await is_in_video_activity():
        return createResponse(False, "不在视频页面")
    console.log("给视频点赞")

    async def _finder():
        return (await UINode.getCurrentPage()).findById("frame_like")

    if await findAndClick(_finder):
        return createResponse(True, "点赞成功")
    else:
        return createResponse(False, "未找到点赞按钮")


async def collect_video(params):
    if not await is_in_video_activity():
        return createResponse(False, "不在视频页面")
    folderName = params.get("folder_name")
    console.log(f"开始收藏视频, 文件夹: {folderName}")

    async def _finder():
        return (await UINode.getCurrentPage()).findById("frame_fav")

    if await findAndClick(_finder):
        return createResponse(True, "收藏成功", {"folder_name": folderName})
    else:
        return createResponse(False, "未找到收藏按钮", {"folder_name": folderName})


async def follow_uploader(params):
    if not await is_in_video_activity():
        return createResponse(False, "不在视频页面")
    console.log("开始关注UP主")

    async def _finder():
        return (await UINode.getCurrentPage()).findAllById("follow")

    if await findAndClick(_finder):
        return createResponse(True, "关注成功")
    else:
        return createResponse(False, "未找到关注按钮或已经关注")


async def get_video_info(params):
    if not await is_in_video_activity():
        return createResponse(False, "不在视频页面")

    console.log("获取视频信息")

    page = await UINode.getCurrentPage()
    videoInfo = {
        "title": "",
        "uploader": "",
        "play_count": "",
        "comment_count": "",
        "like_count": "",
        "coin_count": "",
        "collect_count": "",
        "forward_count": "",
    }

    titleElement = page.findById('title')
    if titleElement and getattr(titleElement, "text", None):
        videoInfo["title"] = titleElement.text

    likeElement = page.findById('frame_like')
    if likeElement and getattr(likeElement, "contentDesc", None):
        videoInfo["like_count"] = likeElement.contentDesc

    collectElement = page.findById('frame_fav')
    if collectElement and getattr(collectElement, "contentDesc", None):
        videoInfo["collect_count"] = collectElement.contentDesc

    coinElement = page.findById('frame_coin')
    if coinElement and getattr(coinElement, "contentDesc", None):
        videoInfo["coin_count"] = coinElement.contentDesc

    forwardElement = page.findById('frame_share')
    if forwardElement and getattr(forwardElement, "contentDesc", None):
        videoInfo["forward_count"] = forwardElement.contentDesc

    uploaderElements = page.findAllById("author_name")
    if uploaderElements and len(uploaderElements) > 0:
        videoInfo["uploader"] = "/".join([u.text for u in uploaderElements])

    return createResponse(True, "获取视频信息成功", {"video_info": videoInfo})


async def browse_comments(params):
    commentCount = params.get("comment_count") or 5
    if not await switch_to_comment_activity():
        return createResponse(False, "不在视频页面")

    console.log(f"浏览评论，获取{commentCount}条")

    page = await UINode.getCurrentPage()

    await Tools.UI.swipe(540, 1500, 540, 800)
    await Tools.System.sleep(2000)

    commentList = page.allTexts()

    return createResponse(True, "获取评论成功", {"all_texts": commentList})


async def navigate_to_home(params):
    console.log("导航到首页")
    if await ensureMain():
        return createResponse(True, "已导航到首页")
    else:
        return createResponse(False, "无法导航到首页")


async def navigate_to_following(params):
    console.log("导航到关注页面")
    page = await UINode.getCurrentPage()
    followingTab = page.findByText("关注")
    if followingTab:
        await followingTab.click()
        await Tools.System.sleep(2000)
        return createResponse(True, "已导航到关注页面")
    else:
        return createResponse(False, "未找到关注标签")


async def navigate_to_history(params):
    console.log("导航到历史页面")
    page = await UINode.getCurrentPage()
    historyButton = page.findByText("历史")
    if not historyButton:
        historyButton = page.findByText("观看历史")

    if historyButton:
        await historyButton.click()
        await Tools.System.sleep(2000)
        return createResponse(True, "已导航到历史页面")
    else:
        return createResponse(False, "未找到历史按钮")


async def toggle_fullscreen(params):
    console.log("切换全屏状态")
    await Tools.UI.tap(540, 960)
    await Tools.System.sleep(1000)

    page = await UINode.getCurrentPage()
    fullscreenButton = page.findByContentDesc("全屏")
    if not fullscreenButton:
        fullscreenButton = page.findByText("全屏")
    if not fullscreenButton:
        fullscreenButton = page.findById('fullscreen_button')

    if fullscreenButton:
        await fullscreenButton.click()
        await Tools.System.sleep(1000)
        return createResponse(True, "全屏状态切换成功")
    else:
        return createResponse(False, "未找到全屏按钮")


async def adjust_playback_speed(params):
    speed = params.get("speed") or "1.0x"
    console.log(f"调整播放速度为: {speed}")

    await Tools.UI.tap(540, 960)
    await Tools.System.sleep(1000)

    page = await UINode.getCurrentPage()
    speedButton = page.findByText("倍速")
    if not speedButton:
        speedButton = page.findByText("1.0x")
    if not speedButton:
        speedButton = page.findById('speed_button')

    if speedButton:
        await speedButton.click()
        await Tools.System.sleep(1000)

        targetSpeedButton = page.findByText(speed)
        if targetSpeedButton:
            await targetSpeedButton.click()
            await Tools.System.sleep(1000)
            return createResponse(True, f"播放速度已调整为 {speed}", {"speed": speed})
        else:
            return createResponse(False, f"未找到 {speed} 速度选项", {"speed": speed})
    else:
        return createResponse(False, "未找到速度设置按钮", {"speed": speed})


async def main():
    console.log("=== B站智能助手测试 ===")
    console.log(await search_video({"keyword": "原神"}))
    await play_video({"video_index": 4})
    console.log(await get_video_info({}))
    console.log(await browse_comments({}))


async def wrapToolExecution(func, params):
    try:
        result = await func(params)
        complete(dict(result))
    except Exception as error:
        console.error(f"Tool {func.__name__} failed unexpectedly", error)
        complete({
            "success": False,
            "message": f"工具执行时发生意外错误: {str(error)}",
        })


def _make_wrapper(func):
    async def wrapper(params):
        await wrapToolExecution(func, params)
    return wrapper


exports.search_video = _make_wrapper(search_video)
exports.play_video = _make_wrapper(play_video)
exports.return_to_video_list = _make_wrapper(return_to_video_list)
exports.send_comment = _make_wrapper(send_comment)
exports.like_video = _make_wrapper(like_video)
exports.collect_video = _make_wrapper(collect_video)
exports.follow_uploader = _make_wrapper(follow_uploader)
exports.get_video_info = _make_wrapper(get_video_info)
exports.browse_comments = _make_wrapper(browse_comments)
exports.navigate_to_home = _make_wrapper(navigate_to_home)
exports.navigate_to_following = _make_wrapper(navigate_to_following)
exports.navigate_to_history = _make_wrapper(navigate_to_history)
exports.toggle_fullscreen = _make_wrapper(toggle_fullscreen)
exports.adjust_playback_speed = _make_wrapper(adjust_playback_speed)
exports.main = main
