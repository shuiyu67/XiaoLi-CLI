# METADATA
# {
#     "name": "Automatic_xiaohongshu_assistant",
#     "display_name": {"zh": "小红书自动化助手", "en": "Xiaohongshu Automation Assistant"},
#     "description": {"zh": "高级小红书智能助手，通过UI自动化技术实现小红书应用交互，支持内容浏览、搜索查看、评论互动、内容发布等功能，为AI赋予小红书社交和内容创作能力。适用于内容营销、社交互动、生活分享等场景。", "en": "Advanced Xiaohongshu (RED) assistant powered by UI automation. Supports browsing feeds, searching and viewing content, commenting and interactions, and publishing posts, enabling AI-driven social interaction and content creation. Useful for content marketing and social engagement."},
#     "category": "Automatic",
#     "tools": [
#         {"name": "workflow_guide", "description": {"zh": "小红书助手工具使用流程指南。", "en": "Workflow guide for the Xiaohongshu assistant."}, "parameters": []},
#         {"name": "browse_home_feed", "description": {"zh": "浏览小红书主页信息流，获取推荐内容", "en": "Browse the Xiaohongshu home feed and collect recommended content."}, "parameters": [
#             {"name": "scroll_count", "description": {"zh": "滚动次数，控制浏览的内容量，默认为3次", "en": "Number of scrolls (default: 3)."}, "type": "number", "required": False},
#             {"name": "collect_posts", "description": {"zh": "是否收集帖子信息，默认为true", "en": "Whether to collect post info (default: true)."}, "type": "boolean", "required": False}
#         ]},
#         {"name": "search_content", "description": {"zh": "在小红书中搜索内容、用户或话题", "en": "Search content, users, or topics in Xiaohongshu."}, "parameters": [
#             {"name": "keyword", "description": {"zh": "搜索关键词", "en": "Search keyword."}, "type": "string", "required": True},
#             {"name": "search_type", "description": {"zh": "搜索类型：comprehensive(综合)、note(笔记)、user(用户)、topic(话题)", "en": "Search type: comprehensive, note, user, topic."}, "type": "string", "required": False}
#         ]},
#         {"name": "view_post", "description": {"zh": "查看指定的帖子详情", "en": "View details of a specific post."}, "parameters": [
#             {"name": "post_title", "description": {"zh": "要查看的帖子标题关键词", "en": "Keyword to match the post title (optional)."}, "type": "string", "required": False},
#             {"name": "post_index", "description": {"zh": "要查看的帖子在列表中的索引位置（从1开始）", "en": "Index of the post in the list (1-based, optional)."}, "type": "number", "required": False}
#         ]},
#         {"name": "like_post", "description": {"zh": "给当前帖子点赞", "en": "Like the current post."}, "parameters": []},
#         {"name": "collect_post", "description": {"zh": "收藏当前帖子", "en": "Save (collect) the current post."}, "parameters": [
#             {"name": "collection_name", "description": {"zh": "收藏夹名称，留空则使用默认收藏夹", "en": "Collection name (leave empty to use the default collection)."}, "type": "string", "required": False}
#         ]},
#         {"name": "follow_user", "description": {"zh": "关注当前帖子的作者", "en": "Follow the author of the current post."}, "parameters": []},
#         {"name": "unfollow_user", "description": {"zh": "取消关注当前帖子的作者", "en": "Unfollow the author of the current post."}, "parameters": []},
#         {"name": "comment_post", "description": {"zh": "在当前帖子下发表评论", "en": "Post a comment under the current post."}, "parameters": [
#             {"name": "comment_text", "description": {"zh": "要发表的评论内容", "en": "Comment text to post."}, "type": "string", "required": True}
#         ]},
#         {"name": "get_post_info", "description": {"zh": "获取当前帖子的详细信息", "en": "Get detailed info of the current post."}, "parameters": []},
#         {"name": "publish_post", "description": {"zh": "发布新的帖子内容", "en": "Publish a new post."}, "parameters": [
#             {"name": "content_text", "description": {"zh": "帖子文字内容", "en": "Post text content."}, "type": "string", "required": True},
#             {"name": "image_paths", "description": {"zh": "图片文件路径列表，用逗号分隔", "en": "Comma-separated list of image file paths (optional)."}, "type": "string", "required": False},
#             {"name": "tags", "description": {"zh": "话题标签，用逗号分隔", "en": "Comma-separated topic tags (optional)."}, "type": "string", "required": False},
#             {"name": "location", "description": {"zh": "地理位置信息", "en": "Location information (optional)."}, "type": "string", "required": False}
#         ]},
#         {"name": "navigate_to_home", "description": {"zh": "导航到小红书首页", "en": "Navigate to the Xiaohongshu home page."}, "parameters": []},
#         {"name": "navigate_to_profile", "description": {"zh": "导航到个人主页", "en": "Navigate to the profile page."}, "parameters": []},
#         {"name": "navigate_to_search", "description": {"zh": "导航到搜索页面", "en": "Navigate to the search page."}, "parameters": []},
#         {"name": "navigate_to_publish", "description": {"zh": "导航到发布页面", "en": "Navigate to the publish page."}, "parameters": []},
#         {"name": "back_to_feed", "description": {"zh": "从帖子详情页返回到信息流列表", "en": "Return from the post detail page back to the feed list."}, "parameters": []}
#     ]
# }
# 注意：本脚本深度依赖 Android UI 自动化 API（UINode、Tools.UI），在非 Android 平台上运行时相关功能不可用。

import json
import re
from urllib.parse import quote, unquote

Error = Exception

XIAOHONGSHU_PACKAGE = "com.xingin.xhs"
MAIN_ACTIVITY = "com.xingin.xhs.activity.SplashActivity"
HOME_ACTIVITY = "com.xingin.xhs.index.v2.IndexActivityV2"

lastBrowseResults = []


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
        return (await UINode.getCurrentPage()).findByText(text)
    return await findAndClick(_finder)


async def ensureMain(packageName=XIAOHONGSHU_PACKAGE):
    pageInfo = await Tools.UI.getPageInfo()

    if pageInfo.packageName != packageName:
        await Tools.System.startApp(packageName)
        await Tools.System.sleep(3000)
        pageInfo = await Tools.UI.getPageInfo()

    async def isAlreadyOnHome():
        page = await UINode.getCurrentPage()
        followButton = page.findByContentDesc("关注")
        discoverButton = page.findByContentDesc("发现")
        searchButton = page.findByContentDesc("搜索")
        return followButton and discoverButton and searchButton

    if await isAlreadyOnHome():
        console.log("已经在首页。")
        return True

    console.log("尝试返回到首页。")
    for i in range(4):
        await Tools.UI.pressKey("KEYCODE_BACK")
        await Tools.System.sleep(1000)
        if await isAlreadyOnHome():
            console.log("成功回到首页。")
            return True
        pageInfo = await Tools.UI.getPageInfo()
        if pageInfo.packageName != packageName:
            console.log("返回时退出了app。")
            break

    console.log("返回失败，重启app。")
    await Tools.System.stopApp(packageName)
    await Tools.System.sleep(1000)
    await Tools.System.startApp(packageName)
    await Tools.System.sleep(5000)

    pageInfo = await Tools.UI.getPageInfo()
    if pageInfo.packageName == packageName:
        console.log("App重启成功。")
        return True

    console.error(f"无法导航到 {packageName} 的首页。")
    return False


async def browse_home_feed(params):
    scroll_count = params.get("scroll_count", 5)
    collect_posts = params.get("collect_posts", False)
    posts = []
    console.log(f"开始浏览, 滑动次数: {scroll_count}, 是否收集帖子: {collect_posts}")

    for i in range(scroll_count):
        console.log(f"第 {i + 1} 次滑动...")

        if collect_posts:
            currentPage = await UINode.getCurrentPage()
            searchScopeNode = currentPage
            console.log("将在整个页面范围内查找帖子。")

            allFrameLayouts = searchScopeNode.findAll(lambda n: n.className == 'FrameLayout')
            console.log(f"[调试] 在查找范围内找到了 {len(allFrameLayouts)} 个 FrameLayout 节点。")
            for frame in allFrameLayouts:
                if getattr(frame, "contentDesc", None):
                    console.log(f'[调试] FrameLayout contentDesc: "{frame.contentDesc}"')

            postNodes = [n for n in allFrameLayouts if getattr(n, "contentDesc", None) and ' 来自' in n.contentDesc]

            console.log(f"本次查找共发现 {len(postNodes)} 个帖子。")

            for postNode in postNodes:
                desc = getattr(postNode, "contentDesc", None)
                if desc:
                    try:
                        parts = desc.split(' 来自')
                        if len(parts) > 1:
                            authorAndLikesStr = parts.pop().strip()
                            title = ' 来自'.join(parts).strip()
                            title = re.sub(r'^(?:笔\s*记|视\s*频)\s*', '', title)

                            words = authorAndLikesStr.split()
                            if len(words) > 0:
                                likesWithSuffix = words.pop()
                                author = ' '.join(words)

                                if title and likesWithSuffix and likesWithSuffix.endswith('赞'):
                                    post = {
                                        "title": title,
                                        "author": author or "未知作者",
                                        "likes": likesWithSuffix.replace('赞', '').strip(),
                                    }
                                    if not any(p["title"] == post["title"] and p["author"] == post["author"] for p in posts):
                                        console.log(f" -> 收集到新帖子: {post['title']} | 作者: {post['author']} | 赞: {post['likes']}")
                                        posts.append(post)
                    except Exception as e:
                        console.log(f'解析时出现异常: "{desc}"', e)

        await Tools.UI.swipe(500, 1800, 500, 500)
        await Tools.System.sleep(2500)

    console.log(f"浏览结束, 共收集到 {len(posts)} 个独立帖子。")
    return createResponse(True, "成功浏览主页信息流", {"posts": posts})


async def applySearchFilter(filterType):
    console.log(f"应用搜索过滤器: {filterType}")
    page = await UINode.getCurrentPage()
    filterButton = None
    if filterType == "note":
        filterButton = page.findByText("笔记")
    elif filterType == "user":
        filterButton = page.findByText("用户")
    elif filterType == "topic":
        filterButton = page.findByText("话题")

    if filterButton:
        await filterButton.click()
        await Tools.System.sleep(2000)


def extractPostInfoFromNode(node, index):
    relativeLayout = node.findByClass("RelativeLayout")
    if relativeLayout:
        directImageViews = [child for child in (getattr(relativeLayout, "children", None) or []) if child.className == "ImageView"]
        if len(directImageViews) > 1:
            return None

    allTextViews = node.findAllByClass("TextView")

    if any(tv.text == "广告" for tv in allTextViews if getattr(tv, "text", None)):
        return None

    if len(allTextViews) < 2:
        return None

    sortedByLength = sorted(allTextViews, key=lambda tv: len(tv.text or ""), reverse=True)
    titleNode = sortedByLength[0]
    if not titleNode or not getattr(titleNode, "text", None) or len(titleNode.text) < 5:
        return None
    title = titleNode.text

    otherTextViews = [tv for tv in allTextViews if tv != titleNode]

    likesRegex = re.compile(r'^\s*\d+(\.\d+)?\s*万?\s*$')
    likesNode = next((tv for tv in otherTextViews if getattr(tv, "text", None) and likesRegex.match(tv.text.strip())), None)
    likes = likesNode.text.strip() if likesNode and getattr(likesNode, "text", None) else "未知"

    dateRegex = re.compile(r'^\d{2,4}-\d{2}(-\d{2})?$')
    authorNode = next((tv for tv in otherTextViews if getattr(tv, "text", None) and tv != likesNode and not dateRegex.match(tv.text.strip())), None)
    author = authorNode.text.strip() if authorNode and getattr(authorNode, "text", None) else "未知作者"

    if title == author:
        return None

    return {"index": index, "title": title, "author": author, "likes": likes, "element": node}


async def getSearchResults(desiredCount=15):
    results = []
    seenTitles = set()
    maxScrolls = 5
    lastResultCount = -1
    scrollCount = 0

    for i in range(maxScrolls):
        if len(results) >= desiredCount:
            break
        page = await UINode.getCurrentPage()
        resultsContainer = page.findByClass("RecyclerView")

        if not resultsContainer:
            console.log("未找到搜索结果容器 (RecyclerView)")
            if i == 0:
                return []
            break

        for item in (getattr(resultsContainer, "children", None) or []):
            postInfo = extractPostInfoFromNode(item, len(results) + 1)
            if postInfo and postInfo["title"] not in seenTitles:
                seenTitles.add(postInfo["title"])
                results.append(postInfo)
                if len(results) >= desiredCount:
                    break

        if len(results) >= desiredCount:
            break

        if len(results) == lastResultCount:
            console.log("滚动未产生新结果，停止滚动")
            break
        lastResultCount = len(results)

        await Tools.UI.swipe(540, 1500, 540, 800)
        await Tools.System.sleep(2000)
        scrollCount += 1

    console.log(f"Scrolling back up {scrollCount} times.")
    for i in range(scrollCount):
        await Tools.UI.swipe(540, 800, 540, 1550)
        await Tools.System.sleep(1000)
    return results


async def search_content(params):
    keyword = params.get("keyword")
    search_type = params.get("search_type", "comprehensive")
    console.log(f"搜索内容: {keyword}, 类型: {search_type}")

    if not await ensureMain():
        return createResponse(False, "无法启动或切换到小红书")

    page = await UINode.getCurrentPage()
    searchIcon = page.findByContentDesc("搜索")

    if not searchIcon:
        return createResponse(False, "在主页上找不到带 '搜索' contentDesc 的图标")
    await searchIcon.click()
    await Tools.System.sleep(2000)

    page = await UINode.getCurrentPage()
    searchInput = page.findByClass("EditText")

    if not searchInput:
        return createResponse(False, "在搜索页面找不到输入框")

    await searchInput.click()
    await Tools.System.sleep(1000)
    await Tools.UI.setText(keyword)
    await Tools.System.sleep(500)

    page = await UINode.getCurrentPage()
    searchButtons = page.findAllByText("搜索")
    searchButton = searchButtons[-1] if searchButtons else None

    if not searchButton:
        console.log("找不到文本为'搜索'的按钮，尝试按回车键")
        await Tools.UI.pressKey("KEYCODE_ENTER")
    else:
        await searchButton.click()
    await Tools.System.sleep(3000)

    if search_type != "comprehensive":
        await applySearchFilter(search_type)

    results = await getSearchResults()

    return createResponse(True, f"搜索到 {len(results)} 条相关内容", {
        "keyword": keyword,
        "search_type": search_type,
        "results": [{k: v for k, v in r.items() if k != "element"} for r in results],
        "result_count": len(results),
    })


async def view_post(params):
    post_title = params.get("post_title")
    post_index = params.get("post_index")

    if not post_title and not post_index:
        return createResponse(False, "请提供帖子标题或索引")

    console.log(f'尝试查看帖子 - 标题: "{post_title}", 索引: {post_index}')

    targetPost = None
    currentIndex = 0
    seenTitles = set()
    maxScrolls = 5

    for i in range(maxScrolls):
        page = await UINode.getCurrentPage()
        resultsContainer = page.findByClass("RecyclerView")

        if not resultsContainer:
            if i == 0:
                return createResponse(False, "未找到帖子列表容器 (RecyclerView)")
            break

        for item in (getattr(resultsContainer, "children", None) or []):
            postInfo = extractPostInfoFromNode(item, 0)
            if postInfo and postInfo["title"] not in seenTitles:
                seenTitles.add(postInfo["title"])
                currentIndex += 1

                shouldClick = False
                if post_index and currentIndex == post_index:
                    shouldClick = True
                elif post_title and post_title in postInfo["title"]:
                    shouldClick = True

                if shouldClick:
                    targetPost = {"title": postInfo["title"], "item": postInfo["element"]}
                    break

        if targetPost:
            break

        await Tools.UI.swipe(540, 1500, 540, 800)
        await Tools.System.sleep(2000)

    if targetPost:
        await targetPost["item"].click()
        await Tools.System.sleep(3000)
        res = await get_post_info({})
        return createResponse(True, f'成功打开帖子并完成内容加载: "{targetPost["title"]}"', res)
    else:
        return createResponse(False, "未找到指定的帖子", {"post_title": post_title, "post_index": post_index})


async def isInPostDetail():
    page = await UINode.getCurrentPage()
    likeButton = page.findByContentDesc("点赞") or page.findByText("赞") or page.find(lambda n: getattr(n, "contentDesc", None) and "点赞" in n.contentDesc)
    commentButton = page.findByContentDesc("评论") or page.findByText("评论") or page.find(lambda n: getattr(n, "contentDesc", None) and "评论" in n.contentDesc)
    return bool(likeButton or commentButton)


async def findLikeButton():
    page = await UINode.getCurrentPage()
    button = page.findByContentDesc("点赞") or page.findByText("赞") or page.find(lambda n: getattr(n, "contentDesc", None) and "点赞" in n.contentDesc)
    return button or None


async def findCollectButton():
    page = await UINode.getCurrentPage()
    button = page.findByContentDesc("收藏") or page.findByText("收藏") or page.find(lambda n: getattr(n, "contentDesc", None) and "收藏" in n.contentDesc)
    return button or None


async def findCommentButton():
    page = await UINode.getCurrentPage()
    button = page.findByContentDesc("评论") or page.findByText("评论") or page.find(lambda n: getattr(n, "contentDesc", None) and "评论" in n.contentDesc)
    return button or None


async def like_post(params):
    if not await isInPostDetail():
        return createResponse(False, "当前不在帖子详情页")
    console.log("给帖子点赞")
    likeButton = await findLikeButton()
    if likeButton:
        await likeButton.click()
        await Tools.System.sleep(1000)
        return createResponse(True, "点赞成功")
    else:
        return createResponse(False, "未找到点赞按钮")


async def collect_post(params):
    if not await isInPostDetail():
        return createResponse(False, "当前不在帖子详情页")
    collection_name = params.get("collection_name")
    console.log(f"收藏帖子到: {collection_name or '默认收藏夹'}")
    collectButton = await findCollectButton()
    if collectButton:
        await collectButton.click()
        await Tools.System.sleep(2000)
        if collection_name:
            collectionPage = await UINode.getCurrentPage()
            targetCollection = collectionPage.findByText(collection_name)
            if targetCollection:
                await targetCollection.click()
                await Tools.System.sleep(1000)
        return createResponse(True, "收藏成功", {"collection_name": collection_name})
    else:
        return createResponse(False, "未找到收藏按钮", {"collection_name": collection_name})


async def follow_user(params):
    if not await isInPostDetail():
        return createResponse(False, "当前不在帖子详情页")
    console.log("关注用户")
    page = await UINode.getCurrentPage()
    followButton = page.findByText("关注")
    if followButton:
        await followButton.click()
        await Tools.System.sleep(1000)
        return createResponse(True, "关注成功")
    else:
        return createResponse(False, "未找到关注按钮或已经关注")


async def unfollow_user(params):
    if not await isInPostDetail():
        return createResponse(False, "当前不在帖子详情页")
    console.log("不关注用户")
    page = await UINode.getCurrentPage()
    followButton = page.findByText("已关注")
    if followButton:
        await followButton.click()
        await Tools.System.sleep(1000)
        node = (await UINode.getCurrentPage()).findByText("不再关注")
        if node:
            await node.click()
        return createResponse(True, "取消关注成功")
    else:
        return createResponse(False, "未找到不关注按钮或已经不关注")


async def comment_post(params):
    if not await isInPostDetail():
        return createResponse(False, "当前不在帖子详情页")
    comment_text = params.get("comment_text")
    console.log(f"发表评论: {comment_text}")
    page = await UINode.getCurrentPage()
    commentBox = page.findByContentDesc("评论框")
    if commentBox:
        await commentBox.click()
        await Tools.System.sleep(1000)
        await Tools.UI.setText(comment_text)
        await Tools.System.sleep(500)
        sendButton = (await UINode.getCurrentPage()).findByText("发送")
        if sendButton:
            await sendButton.click()
            await Tools.System.sleep(2000)
            return createResponse(True, "评论发表成功", {"comment_text": comment_text})
        else:
            return createResponse(False, "未找到发送按钮", {"comment_text": comment_text})
    else:
        return createResponse(False, "未找到评论输入框", {"comment_text": comment_text})


async def get_post_info(params):
    if not await isInPostDetail():
        return createResponse(False, "当前不在帖子详情页")
    console.log("获取帖子信息...")

    await Tools.UI.swipe(540, 1600, 540, 1000)
    await Tools.System.sleep(1500)

    page = await UINode.getCurrentPage()
    postInfo = {
        "title": "未知", "author": "未知", "content": "",
        "like_count": "未知", "comment_count": "未知", "collect_count": "未知",
        "publish_date": "未知", "comments": [],
    }

    authorButton = page.find(lambda n: getattr(n, "contentDesc", None) and n.contentDesc.startswith("作者,"))
    authorTextView = None
    if authorButton:
        authorTextView = authorButton.findByClass("TextView")
        if authorTextView and getattr(authorTextView, "text", None):
            postInfo["author"] = authorTextView.text
        elif getattr(authorButton, "contentDesc", None):
            parts = authorButton.contentDesc.split(',')
            if len(parts) > 1:
                postInfo["author"] = parts[1].strip()

    allNodesWithDesc = page.findAll(lambda n: bool(getattr(n, "contentDesc", None)))
    dateNode = next((n for n in allNodesWithDesc if getattr(n, "contentDesc", None) and re.match(r'^\d{2}-\d{2}$', n.contentDesc.strip())), None)
    if dateNode and getattr(dateNode, "contentDesc", None):
        postInfo["publish_date"] = dateNode.contentDesc.strip()

    def findCountFromButton(button):
        if not button:
            return "未知"
        if getattr(button, "contentDesc", None):
            match = re.search(r'(\d+(\.\d+)?[万wW]?)', button.contentDesc)
            if match and match.group(1):
                return match.group(1)
        countNode = button.findByClass("TextView")
        if countNode and getattr(countNode, "text", None) and re.match(r'^\d+(\.\d+)?[万wW]?$', countNode.text.strip()):
            return countNode.text.strip()
        return "未知"

    postInfo["like_count"] = findCountFromButton(await findLikeButton())
    postInfo["comment_count"] = findCountFromButton(await findCommentButton())
    postInfo["collect_count"] = findCountFromButton(await findCollectButton())

    allRecyclerViews = page.findAllByClass("RecyclerView")
    commentListInitial = next((rv for rv in allRecyclerViews if not (getattr(rv, "parent", None) and rv.parent.className == 'FrameLayout' and getattr(rv.parent, "contentDesc", None) and ("图片" in rv.parent.contentDesc or "视频" in rv.parent.contentDesc))), None)

    commentTextViews = set(commentListInitial.findAllByClass("TextView") if commentListInitial else [])
    allTextViews = page.findAllByClass("TextView")
    mainTextViews = [tv for tv in allTextViews if tv and tv not in commentTextViews]

    ignoredTexts = {'关注', '赞', '评论', '收藏', '翻译', '说点什么...', postInfo["author"]}
    if postInfo["author"] == '未知':
        ignoredTexts.discard('未知')

    contentTextNodes = [tv for tv in mainTextViews if getattr(tv, "text", None) and tv.text.strip() and tv.text.strip() not in ignoredTexts and not re.match(r'^\d+(\.\d+)?[万wW]?$', tv.text) and tv != authorTextView]

    if len(contentTextNodes) > 0:
        postInfo["title"] = contentTextNodes[0].text.strip()
        if len(contentTextNodes) > 1:
            postInfo["content"] = '\n'.join([tv.text.strip() for tv in contentTextNodes[1:]])

    console.log("开始滚动并解析评论...")
    seenComments = set()
    stableScrolls = 0
    maxScrolls = 10

    for i in range(maxScrolls):
        currentCommentCount = len(postInfo["comments"])
        currentPage = await UINode.getCurrentPage()

        commentList = next((rv for rv in currentPage.findAllByClass("RecyclerView") if not (getattr(rv, "parent", None) and rv.parent.className == 'FrameLayout' and getattr(rv.parent, "contentDesc", None) and ("图片" in rv.parent.contentDesc or "视频" in rv.parent.contentDesc))), None)

        if commentList:
            for item in (getattr(commentList, "children", None) or []):
                if len(postInfo["comments"]) >= 20:
                    break
                textViews = item.findAllByClass("TextView")
                if len(textViews) < 2:
                    continue

                comment = {"author": "未知", "content": "未知", "likes": "0", "date": "未知"}
                likesRegex = re.compile(r'^\d+(\.\d+)?[万wW]?$')
                likesNode = item.find(lambda n: n.className == 'TextView' and getattr(n, "text", None) and likesRegex.match(n.text))
                comment["likes"] = likesNode.text if likesNode and getattr(likesNode, "text", None) else "0"

                contentCandidates = [tv for tv in textViews if getattr(tv, "text", None) and tv != likesNode]
                if len(contentCandidates) == 0:
                    continue
                contentCandidates.sort(key=lambda tv: len(tv.text or ""), reverse=True)

                contentText = contentCandidates[0].text or ""
                authorNode = contentCandidates[1] if len(contentCandidates) > 1 else None

                comment["author"] = authorNode.text.replace("作者", "").strip() if authorNode and getattr(authorNode, "text", None) else "未知"

                dateRegex = re.compile(r'(\d{2}-\d{2}( \d{2}:\d{2})?|\d+天前|昨天 \d{2}:\d{2})')
                dateMatch = dateRegex.search(contentText)
                if dateMatch:
                    comment["date"] = dateMatch.group(0)
                    comment["content"] = dateRegex.sub(' ', contentText).replace('回复', '').strip()
                else:
                    comment["content"] = contentText.replace('回复', '').strip()

                if comment["content"].startswith(comment["author"]):
                    comment["content"] = comment["content"][len(comment["author"]):].strip()

                if comment["content"] == comment["author"] or not comment["content"]:
                    continue

                uniqueKey = f'{comment["author"]}:{comment["content"]}'
                if comment["content"] and comment["content"] != "未知" and uniqueKey not in seenComments:
                    seenComments.add(uniqueKey)
                    postInfo["comments"].append(comment)

        if len(postInfo["comments"]) >= 20:
            console.log("已收集到20条评论，停止滚动。")
            break

        if len(postInfo["comments"]) == currentCommentCount:
            stableScrolls += 1
            if stableScrolls >= 2:
                console.log("滚动两次未发现新评论，停止。")
                break
        else:
            stableScrolls = 0

        console.log(f"第 {i + 1}/{maxScrolls} 次滚动... 当前评论数: {len(postInfo['comments'])}")
        await Tools.UI.swipe(540, 1600, 540, 800)
        await Tools.System.sleep(2000)

    return createResponse(True, "获取帖子信息成功", {"post_info": postInfo})


async def publish_post(params):
    content_text = params.get("content_text")
    image_paths = params.get("image_paths")
    tags = params.get("tags")
    location = params.get("location")

    console.log(f"发布帖子: {content_text[:20]}...")

    if not await ensureMain():
        return createResponse(False, "无法启动或切换到小红书")

    page = await UINode.getCurrentPage()
    publishButton = page.findByText("发布") or page.findByText("+") or page.findByContentDesc("发布")

    if not publishButton:
        return createResponse(False, "未找到发布按钮")

    await publishButton.click()
    await Tools.System.sleep(3000)

    noteOption = (await UINode.getCurrentPage()).findByText("笔记") or (await UINode.getCurrentPage()).findByText("图文")
    if noteOption:
        await noteOption.click()
        await Tools.System.sleep(2000)

    if image_paths:
        imagePaths = image_paths.split(',')
        for imagePath in imagePaths:
            console.log(f"添加图片: {imagePath.strip()}")

    pageForInput = await UINode.getCurrentPage()
    textInput = pageForInput.findByClass("EditText") or pageForInput.findByText("分享你的生活...")

    if textInput:
        await textInput.click()
        await Tools.System.sleep(1000)
        await Tools.UI.setText(content_text)
        await Tools.System.sleep(1000)

    if tags:
        tagList = tags.split(',')
        for tag in tagList:
            tagText = tag.strip()
            if tagText:
                await Tools.UI.setText(f" #{tagText}")
                await Tools.System.sleep(500)

    if location:
        locationButton = (await UINode.getCurrentPage()).findByText("添加地点")
        if locationButton:
            await locationButton.click()
            await Tools.System.sleep(2000)
            await Tools.UI.setText(location)
            await Tools.System.sleep(1000)
            firstLocation = (await UINode.getCurrentPage()).findByClass("TextView")
            if firstLocation and getattr(firstLocation, "text", None) and location in firstLocation.text:
                await firstLocation.click()
                await Tools.System.sleep(1000)

    finalPublishButton = (await UINode.getCurrentPage()).findByText("发布")
    if finalPublishButton:
        await finalPublishButton.click()
        await Tools.System.sleep(5000)
        return createResponse(True, "帖子发布成功", {"content_text": content_text, "image_paths": image_paths, "tags": tags, "location": location})
    else:
        return createResponse(False, "未找到最终发布按钮", {"content_text": content_text})


async def navigate_to_home(params):
    console.log("导航到首页")
    if await ensureMain():
        page = await UINode.getCurrentPage()
        homeTab = page.findByText("首页")
        if homeTab:
            await homeTab.click()
            await Tools.System.sleep(1000)
        return createResponse(True, "已导航到首页")
    else:
        return createResponse(False, "无法导航到首页")


async def navigate_to_profile(params):
    console.log("导航到个人主页")
    if await ensureMain():
        page = await UINode.getCurrentPage()
        profileTab = page.findByText("我") or page.findByText("个人主页")
        if profileTab:
            await profileTab.click()
            await Tools.System.sleep(2000)
            return createResponse(True, "已导航到个人主页")
        else:
            return createResponse(False, "未找到个人主页标签")
    else:
        return createResponse(False, "无法导航到个人主页")


async def navigate_to_search(params):
    console.log("导航到搜索页面")
    if await ensureMain():
        page = await UINode.getCurrentPage()
        searchTab = page.findByText("搜索") or page.findByContentDesc("搜索")
        if searchTab:
            await searchTab.click()
            await Tools.System.sleep(1500)
            return createResponse(True, "已导航到搜索页面")
        else:
            await Tools.UI.tap(540, 200)
            await Tools.System.sleep(1500)
            return createResponse(True, "已打开搜索页面")
    else:
        return createResponse(False, "无法导航到搜索页面")


async def navigate_to_publish(params):
    console.log("导航到发布页面")
    if await ensureMain():
        page = await UINode.getCurrentPage()
        publishTab = page.findByText("发布") or page.findByText("+")
        if publishTab:
            await publishTab.click()
            await Tools.System.sleep(2000)
            return createResponse(True, "已导航到发布页面")
        else:
            return createResponse(False, "未找到发布按钮")
    else:
        return createResponse(False, "无法导航到发布页面")


async def back_to_feed(params):
    console.log("从帖子详情页返回到信息流")
    if await isInPostDetail():
        await Tools.UI.pressKey("KEYCODE_BACK")
        await Tools.System.sleep(2000)
        return createResponse(True, "已返回到信息流列表")
    else:
        return createResponse(True, "当前不在帖子详情页，无需返回")


async def main(params):
    console.log("=== 小红书智能助手测试 ===")
    console.log("测试搜索功能...")
    console.log(json.dumps(await get_post_info({}), indent=2, ensure_ascii=False, default=str))


async def wrapToolExecution(func, params):
    try:
        result = await func(params)
        if result:
            complete(dict(result))
        else:
            complete({"success": True, "message": "操作成功完成但无返回数据。"})
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


exports.browse_home_feed = _make_wrapper(browse_home_feed)
exports.search_content = _make_wrapper(search_content)
exports.view_post = _make_wrapper(view_post)
exports.like_post = _make_wrapper(like_post)
exports.collect_post = _make_wrapper(collect_post)
exports.follow_user = _make_wrapper(follow_user)
exports.unfollow_user = _make_wrapper(unfollow_user)
exports.comment_post = _make_wrapper(comment_post)
exports.get_post_info = _make_wrapper(get_post_info)
exports.publish_post = _make_wrapper(publish_post)
exports.navigate_to_home = _make_wrapper(navigate_to_home)
exports.navigate_to_profile = _make_wrapper(navigate_to_profile)
exports.navigate_to_search = _make_wrapper(navigate_to_search)
exports.navigate_to_publish = _make_wrapper(navigate_to_publish)
exports.back_to_feed = _make_wrapper(back_to_feed)
exports.main = _make_wrapper(main)
