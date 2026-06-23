# METADATA
# {
#     "name": "Automatic_baiduMap_assistant",
#     "display_name": {
#         "zh": "百度地图自动化助手",
#         "en": "Baidu Map Automation Assistant"
#     },
#     "description": { "zh": "高级百度地图智能助手，通过UI自动化技术实现地图交互，支持地点搜索、路线规划、周边查询等功能，为AI提供强大的地理位置服务能力。适用于出行规划、信息查询、智能问答等场景。", "en": "Advanced Baidu Maps assistant powered by UI automation. Supports place search, navigation/route planning, and nearby discovery, enabling AI-driven location services. Useful for trip planning, information lookup, and Q&A." },
#     "category": "Automatic",
#     "tools": [
#         {
#             "name": "workflow_guide",
#             "description": { "zh": "百度地图助手工具使用流程指南。要完成复杂任务，请按以下顺序组合使用工具：\n1. **搜索地点**: 使用 `search_location` 查找地点、餐馆、公司等，这是多数操作的起点。\n2. **选择地点**: 如果 `search_location` 返回多个结果，使用 `select_location_from_list` 从列表中选择一个。\n3. **开始导航**: 搜索到唯一地点或从列表中选择地点后，使用 `go_to_location` 来规划到该地的路线。\n4. **周边搜索**: 使用 `search_nearby` 查找当前位置或指定地点附近的设施。\n- **随时导航**: `navigate_to_home` 可随时返回地图主页。", "en": "Workflow guide for the Baidu Maps assistant. For complex tasks, combine tools in this order:\n1. **Search**: use `search_location` to find places/restaurants/companies (starting point for most tasks).\n2. **Select**: if `search_location` returns multiple results, use `select_location_from_list` to pick one from the list.\n3. **Navigate**: after a unique result is found or selected, use `go_to_location` to plan a route.\n4. **Nearby**: use `search_nearby` to find facilities near your current location or a specified place.\n- **Go home anytime**: use `navigate_to_home` to return to the map home screen." },
#             "parameters": [],
#             "advice": true
#         },
#         {
#             "name": "search_location",
#             "description": { "zh": "在百度地图中搜索地点、餐馆、公司等信息。", "en": "Search places, restaurants, companies, and other POIs in Baidu Maps." },
#             "parameters": [
#                 { "name": "keyword", "description": { "zh": "要搜索的地点关键词", "en": "Keyword of the place to search for." }, "type": "string", "required": true }
#             ]
#         },
#         {
#             "name": "get_directions",
#             "description": { "zh": "规划从起点到终点的路线。", "en": "Plan a route from a start point to a destination." },
#             "parameters": [
#                 { "name": "start_point", "description": { "zh": "路线起点，默认为'我的位置'", "en": "Route start point (default: 'My location')." }, "type": "string", "required": false },
#                 { "name": "end_point", "description": { "zh": "路线终点", "en": "Route destination." }, "type": "string", "required": true },
#                 { "name": "transport_mode", "description": { "zh": "交通方式：driving(驾车), transit(公交), walking(步行), cycling(骑行)", "en": "Transport mode: driving, transit, walking, cycling." }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "select_location_from_list",
#             "description": { "zh": "从 'search_location' 返回的搜索结果列表中选择一个地点。", "en": "Select a place from the result list returned by `search_location`." },
#             "parameters": [
#                 { "name": "keyword", "description": { "zh": "要选择的地点名称关键词", "en": "Keyword to match the place name to select." }, "type": "string", "required": false },
#                 { "name": "index", "description": { "zh": "要选择的地点在列表中的索引位置（从1开始）", "en": "Index of the item in the list (1-based)." }, "type": "number", "required": false }
#             ]
#         },
#         {
#             "name": "go_to_location",
#             "description": { "zh": "在地点详情页点击“到这去”，以开启导航或路线规划。可以选择交通方式。", "en": "On the place detail page, tap \"Go\" (到这去) to start navigation/route planning. You can optionally select a transport mode." },
#             "parameters": [
#                 { "name": "transport_mode", "description": { "zh": "交通方式：新能源, 驾车, 打车, 公共交通, 代驾, 骑行, 步行, 拼车, 飞机, 火车, 客车, 摩托车", "en": "Transport mode tab label in the app (e.g., 新能源, 驾车, 打车, 公共交通, 代驾, 骑行, 步行, 拼车, 飞机, 火车, 客车, 摩托车)." }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "search_nearby",
#             "description": { "zh": "搜索中心点附近的地点信息。", "en": "Search places around a center point." },
#             "parameters": [
#                 { "name": "keyword", "description": { "zh": "要搜索的周边设施关键词（如：银行, 加油站）", "en": "Nearby keyword (e.g., bank, gas station)." }, "type": "string", "required": true },
#                 { "name": "center_point", "description": { "zh": "搜索的中心点，默认为'我的位置'", "en": "Center point for the search (default: 'My location')." }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "navigate_to_home",
#             "description": { "zh": "返回百度地图的主界面。", "en": "Return to the Baidu Maps home screen." },
#             "parameters": []
#         },
#         {
#             "name": "activate_voice_assistant",
#             "description": { "zh": "在主界面点击语音搜索按钮，启动“小度”语音助手。", "en": "Tap the voice search button on the home screen to launch the Xiaodu voice assistant." },
#             "parameters": []
#         }
#     ]
# }

import re

# 百度地图应用包名
BAIDU_MAP_PACKAGE = "com.baidu.BaiduMap"
MAIN_ACTIVITY = "com.baidu.baidumaps.MapsActivity"


# Helper to create response objects
def createResponse(success, message, data=None):
    if data is None:
        data = {}
    if isinstance(data, str):
        return {"success": success, "message": message, "data": data}
    result = {"success": success, "message": message}
    result.update(data)
    return result


def _y_of(tv):
    try:
        bounds = tv.bounds
        if not bounds:
            return 0
        m = re.search(r"\[\d+,(\d+)\]", bounds)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return 0


def _dedup_by_title(items):
    seen = {}
    for item in items:
        t = item.get("title")
        if t not in seen:
            seen[t] = item
    return list(seen.values())


# Helper to find a UI element and click it
async def findAndClick(finder):
    element = await finder()
    if element:
        await element.click()
        await Tools.System.sleep(1000)
        return True
    return False


# Helper to find a UI element by text and click it
async def findAndClickByText(text):
    async def _finder():
        return (await UINode.getCurrentPage()).findByText(text)
    return await findAndClick(_finder)


async def isOnMainPage():
    page = await UINode.getCurrentPage()
    # Check for the presence of key elements that indicate the main map screen.
    drivingButton = page.findByText("驾车")
    transitButton = page.findByText("公共交通")
    taxiButton = page.findByText("打车")
    hotelButton = page.findByText("订酒店")

    if drivingButton and transitButton and taxiButton and hotelButton:
        console.log("Detected Baidu Map main page by key elements.")
        return True
    console.log("Not on main page, key elements not found.")
    return False


async def ensureMain(packageName=BAIDU_MAP_PACKAGE):
    pageInfo = await Tools.UI.getPageInfo()

    # 1. If not in the correct app, start it.
    if pageInfo.get("packageName") != packageName:
        console.log(f"Not in the correct app. Current: {pageInfo.get('packageName')}. Starting {packageName}.")
        await Tools.System.startApp(packageName)
        await Tools.System.sleep(5000)  # Wait for app to load
        pageInfo = await Tools.UI.getPageInfo()  # Re-check page info
        if pageInfo.get("packageName") != packageName:
            console.error(f"Failed to start {packageName}.")
            return False

    # 2. Check if we are already on the main page.
    if await isOnMainPage():
        console.log("Already on the main page.")
        return True

    # 3. If not on the main page, try pressing back up to 4 times.
    console.log("Not on the main page. Attempting to go back.")
    for i in range(4):
        await Tools.UI.pressKey("KEYCODE_BACK")
        await Tools.System.sleep(1000)  # Wait for UI to settle

        pageInfo = await Tools.UI.getPageInfo()
        # If we have exited the app, stop trying.
        if pageInfo.get("packageName") != packageName:
            console.log("Exited the app while trying to go back.")
            break  # Exit the loop, will proceed to restart

        if await isOnMainPage():
            console.log(f"Successfully returned to main page on attempt {i + 1}.")
            return True

    # 4. If pressing back failed, perform a full app restart.
    console.log("Pressing back failed or exited app. Performing a full app restart.")
    await Tools.System.stopApp(packageName)
    await Tools.System.sleep(1000)
    await Tools.System.startApp(packageName)
    await Tools.System.sleep(5000)  # Longer wait for cold start

    pageInfo = await Tools.UI.getPageInfo()
    if pageInfo.get("packageName") != packageName:
        console.error(f"Failed to restart {packageName}.")
        return False

    if await isOnMainPage():
        console.log("Successfully reached main page after restart.")
        return True

    console.error(f"Failed to navigate to the main page of {packageName} even after restart.")
    return False


async def search_location(params):
    keyword = params.get("keyword")
    console.log(f"Searching for location: {keyword}")

    # 确保百度地图已在前台运行
    if not await ensureMain():
        return createResponse(False, "无法启动或切换到百度地图")

    await Tools.System.sleep(2000)  # 等待首页完全加载

    # 查找并点击搜索框
    page = await UINode.getCurrentPage()
    searchBox = page.findById('serachbox_container')
    if not searchBox:
        return createResponse(False, "在地图主页未找到搜索框 (ID: serachbox_container)")
    await searchBox.click()
    await Tools.System.sleep(300)
    await Tools.UI.setText(keyword)
    await Tools.System.sleep(300)

    # 点击搜索按钮
    searchButton = (await UINode.getCurrentPage()).findByText("搜索")
    if searchButton:
        await searchButton.click()

    await Tools.System.sleep(5000)  # 等待搜索结果加载

    # 上拉以显示完整的结果列表，这在某些情况下是必要的
    console.log("执行上拉手势以确保结果列表完全可见...")
    await Tools.UI.swipe(540, 1800, 540, 900)  # 从屏幕底部向上滑动
    await Tools.System.sleep(1500)  # 等待动画完成

    # 检查页面是唯一结果还是列表
    pageAfterSearch = await UINode.getCurrentPage()
    listContainer = pageAfterSearch.findById("com.baidu.BaiduMap:id/talosListContainer")

    if listContainer:
        # 情况2: 结果列表
        console.log("检测到列表容器，开始解析结果列表...")
        results = await get_map_search_results()

        return createResponse(True, f"搜索到 {len(results)} 个相关地点。请使用 'select_location_from_list' 选择一个。", {
            "keyword": keyword,
            "results": [{k: v for k, v in r.items() if k != "element"} for r in results],  # 移除 element 属性
            "result_count": len(results)
        })

    goToButton = pageAfterSearch.findByText("到这去")
    if goToButton:
        # 情况1: 唯一结果
        return createResponse(True, f"已找到唯一结果 \"{keyword}\"。您现在可以使用 'go_to_location' 进行导航。", {"keyword": keyword})
    else:
        return createResponse(False, f"搜索 \"{keyword}\" 后既未找到结果列表，也未找到唯一结果。")


async def get_map_search_results(desiredCount=20):
    results = []
    seenTitles = set()
    maxScrolls = 1
    lastResultCount = -1

    for i in range(maxScrolls):
        page = await UINode.getCurrentPage()
        resultsContainer = page.findById('com.baidu.BaiduMap:id/talosListContainer')
        if not resultsContainer:
            console.log("未找到搜索结果容器 (ID: com.baidu.BaiduMap:id/talosListContainer)")
            break

        recyclerView = resultsContainer.findByClass("RecyclerView")
        if not recyclerView:
            console.log("未在结果容器中找到 RecyclerView。")
            break

        # 通过查找所有“到这去”按钮来定位每个列表项
        goToButtons = recyclerView.findAllByText("到这去")

        for button in goToButtons:
            # 找到按钮所属的、作为RecyclerView直接子节点的那个父节点
            item = button.closest(lambda node: getattr(node, "parent", None) is not None and node.parent.equals(recyclerView))
            if not item:
                continue

            textViews = item.findAllByClass('TextView')
            relevantTextViews = [tv for tv in textViews if tv.text and tv.text.strip() != '到这去' and tv.text.strip() != '']

            if len(relevantTextViews) == 0:
                continue

            # 按纵坐标排序，最上面的通常是标题
            relevantTextViews.sort(key=_y_of)

            title = relevantTextViews[0].text
            if not title or title in seenTitles:
                continue
            seenTitles.add(title)

            # 查找包含地址特征的文本作为地址
            addressNode = next((tv for tv in relevantTextViews if tv.text and ('省' in tv.text or '市' in tv.text or '区' in tv.text or '路' in tv.text or '号' in tv.text)), None)
            address = addressNode.text if addressNode else "N/A"

            results.append({
                "index": len(results) + 1,  # 临时索引
                "title": title,
                "address": address,
                "element": item
            })

        # 滚动前去重并检查是否需要停止
        uniqueResults = _dedup_by_title(results)

        if len(uniqueResults) >= desiredCount:
            console.log(f"已找到 {len(uniqueResults)} 条不重复结果，满足要求。")
            break
        if len(uniqueResults) == lastResultCount:
            console.log("滚动未产生新结果，停止滚动。")
            break
        lastResultCount = len(uniqueResults)

        # 向下滚动加载更多
        await Tools.UI.swipe(540, 1800, 540, 600)
        await Tools.System.sleep(2000)  # 增加等待时间以确保加载

    # 最终去重并重新编号索引
    finalResults = _dedup_by_title(results)
    for index, item in enumerate(finalResults):
        item["index"] = index + 1

    return finalResults[:desiredCount]


# --- Placeholder functions for other tools ---
async def select_location_from_list(params):
    keyword = params.get("keyword")
    index = params.get("index")

    if not keyword and not index:
        return createResponse(False, "请提供地点关键词或索引。")
    console.log(f"尝试从列表中选择 - 关键词: \"{keyword}\", 索引: {index}")

    seenTitles = set()
    currentItemCount = 0
    maxScrolls = 10
    lastSeenCount = -1

    for i in range(maxScrolls):
        page = await UINode.getCurrentPage()
        # In Baidu Maps, the results are often inside a RecyclerView
        recyclerView = page.findByClass("RecyclerView")
        if not recyclerView:
            console.log("未找到 RecyclerView, 无法选择项目。")
            return createResponse(False, "未找到结果列表容器 (RecyclerView)。")

        goToButtons = recyclerView.findAllByText("到这去")

        for button in goToButtons:
            item = button.closest(lambda node: getattr(node, "parent", None) is not None and node.parent.equals(recyclerView))
            if not item:
                continue

            textViews = item.findAllByClass('TextView')
            relevantTextViews = [tv for tv in textViews if tv.text and tv.text.strip() != '到这去' and tv.text.strip() != '']
            if len(relevantTextViews) == 0:
                continue

            relevantTextViews.sort(key=_y_of)

            title = relevantTextViews[0].text
            if not title or title in seenTitles:
                continue

            seenTitles.add(title)
            currentItemCount += 1

            shouldClick = False
            if index:
                if currentItemCount == index:
                    shouldClick = True
            elif keyword:
                if keyword in title:
                    shouldClick = True

            if shouldClick:
                await item.click()
                await Tools.System.sleep(2000)
                return createResponse(True, f"已成功选择地点: \"{title}\"")

        if len(seenTitles) == lastSeenCount:
            console.log("滚动未产生新结果，停止。")
            break
        lastSeenCount = len(seenTitles)

        if index and currentItemCount >= index:
            # If we're looking for an index and have passed it, no need to scroll more.
            break

        await Tools.UI.swipe(540, 1800, 540, 600)  # Swipe up
        await Tools.System.sleep(2000)

    return createResponse(False, "在列表中未找到或无法选择指定的地点。", {"keyword": keyword, "index": index})


async def go_to_location(params):
    transportMode = params.get("transport_mode") or "驾车"  # 默认为驾车
    console.log("尝试点击 '到这去' 按钮...")
    page = await UINode.getCurrentPage()
    goToButton = page.findByText("到这去")
    if goToButton:
        await goToButton.click()
        await Tools.System.sleep(3000)  # 等待路线规划页面加载

        if transportMode:
            console.log(f"尝试选择交通方式: {transportMode}")
            pageAfterClick = await UINode.getCurrentPage()

            # 尝试直接点击可见的交通方式按钮
            try:
                modeButton = pageAfterClick.findByText(transportMode)
                if modeButton:
                    await modeButton.click()
                    await Tools.System.sleep(1000)
                    return createResponse(True, f"已点击“到这去”，并成功切换到“{transportMode}”模式。")
            except Exception:
                console.log("直接点击失败，按钮可能在屏幕外。尝试滚动查找。")

            # 如果未直接找到，尝试展开更多选项
            console.log(f"未直接找到 \"{transportMode}\"，尝试展开更多选项...")
            moreModesButton = pageAfterClick.findById('route_tab_group')
            if moreModesButton:
                await moreModesButton.click()
                await Tools.System.sleep(1500)  # 等待展开动画
                pageAfterClick = await UINode.getCurrentPage()  # 刷新页面节点
                modeButton = pageAfterClick.findByText(transportMode)
                if modeButton:
                    await modeButton.click()
                    await Tools.System.sleep(1500)
                    return createResponse(True, f"已点击“到这去”，并成功切换到“{transportMode}”模式。")

            return createResponse(False, f"已点击“到这去”，但无法找到交通方式“{transportMode}”。")

        return createResponse(True, "已点击“到这去”，进入路线规划页面。")
    else:
        return createResponse(False, "在当前页面未找到“到这去”按钮。")


async def get_directions(params):
    return createResponse(False, "功能 'get_directions' 尚未实现。")


async def search_nearby(params):
    return createResponse(False, "功能 'search_nearby' 尚未实现。")


async def navigate_to_home(params=None):
    if params is None:
        params = {}
    console.log("Navigating to home screen.")
    if await ensureMain():
        # 在地图应用中，通常按返回键可以回到主图区
        # 这里可以根据实际情况增加返回逻辑
        await Tools.UI.pressKey("KEYCODE_BACK")
        await Tools.System.sleep(500)
        await Tools.UI.pressKey("KEYCODE_BACK")
        return createResponse(True, "已尝试返回主界面。")
    else:
        return createResponse(False, "无法导航到主界面，因为无法启动百度地图。")


async def activate_voice_assistant(params=None):
    if params is None:
        params = {}
    console.log("正在激活语音助手“小度”...")
    if not await ensureMain():
        return createResponse(False, "无法启动或切换到百度地图主页，因此无法激活语音助手。")
    await Tools.System.sleep(1000)  # 等待UI稳定

    page = await UINode.getCurrentPage()
    voiceButton = page.findById('voice_search')

    if voiceButton:
        await voiceButton.click()
        await Tools.System.sleep(2000)  # 等待语音助手界面弹出
        return createResponse(True, "已成功激活“小度”语音助手。")
    else:
        return createResponse(False, "在主界面上未找到语音搜索按钮 (ID: voice_search)。")


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


async def main(params=None):
    if params is None:
        params = {}
    console.log("Running main for testing...")
    # 这是一个用于测试的函数，它会搜索一个默认位置
    # Navigate back to home for the next test
    await navigate_to_home({})
    await Tools.System.sleep(3000)

    console.log("--- Test Case 2: Searching for '长安大学' to test multiple results ---")
    await search_location({"keyword": "长安大学"})
    await Tools.System.sleep(2000)
    await select_location_from_list({"index": 1})
    await Tools.System.sleep(2000)
    await go_to_location({"transport_mode": "飞机"})
    await Tools.System.sleep(2000)


async def _exported_search_location(params):
    await wrapToolExecution(search_location, params)


async def _exported_select_location_from_list(params):
    await wrapToolExecution(select_location_from_list, params)


async def _exported_go_to_location(params):
    await wrapToolExecution(go_to_location, params)


async def _exported_get_directions(params):
    await wrapToolExecution(get_directions, params)


async def _exported_search_nearby(params):
    await wrapToolExecution(search_nearby, params)


async def _exported_navigate_to_home(params=None):
    if params is None:
        params = {}
    await wrapToolExecution(navigate_to_home, params)


async def _exported_activate_voice_assistant(params=None):
    if params is None:
        params = {}
    await wrapToolExecution(activate_voice_assistant, params)


async def _exported_main(params=None):
    if params is None:
        params = {}
    await wrapToolExecution(main, params)


exports.search_location = _exported_search_location
exports.select_location_from_list = _exported_select_location_from_list
exports.go_to_location = _exported_go_to_location
exports.get_directions = _exported_get_directions
exports.search_nearby = _exported_search_nearby
exports.navigate_to_home = _exported_navigate_to_home
exports.activate_voice_assistant = _exported_activate_voice_assistant
exports.main = _exported_main
