# METADATA
# {
#     "name": "Experimental_qq_intelligent",
#     "display_name": {
#         "zh": "实验性 QQ 智能助手",
#         "en": "Experimental QQ Intelligent Assistant"
#     },
#     "description": { "zh": "高级QQ智能助手，通过UI自动化技术实现QQ应用交互，支持消息自动回复、历史记录读取、联系人搜索与通讯等功能，为AI赋予QQ社交能力。适用于智能客服、自动回复、社交辅助等场景。", "en": "Advanced QQ assistant powered by UI automation. Supports sending messages, reading chat history, searching contacts/groups, and basic communication workflows, enabling AI-driven social messaging scenarios." },
#     "category": "Media",
#     "tools": [
#         {
#             "name": "reply",
#             "description": { "zh": "在当前聊天窗口输入消息并发送。一般情况下，用户想要ai帮忙发送消息时，需要ai自己去生成回复的消息，如果不确定发送的内容，请不要调用工具。只要是停留在聊天界面，就可以直接调用这个。", "en": "Type and send a message in the current chat window. Usually the AI should generate the message content by itself; if you are unsure what to send, do not call this tool. As long as you are staying on a chat page, you can call it directly." },
#             "parameters": [
#                 { "name": "message", "description": { "zh": "要发送的消息", "en": "Message text to send." }, "type": "string", "required": true },
#                 { "name": "click_send", "description": { "zh": "是否点击发送按钮", "en": "Whether to tap the Send button." }, "type": "boolean", "required": false }
#             ]
#         },
#         {
#             "name": "find_user",
#             "description": { "zh": "在QQ联系人或群成员中查找用户", "en": "Find a user in QQ contacts or group chats." },
#             "parameters": [
#                 { "name": "user_name", "description": { "zh": "搜索用户名称", "en": "User name keyword to search." }, "type": "string", "required": true },
#                 { "name": "user_type", "description": { "zh": "搜索类型（contacts/groups）", "en": "Search type: contacts or groups." }, "type": "string", "required": true }
#             ]
#         },
#         {
#             "name": "find_and_reply",
#             "description": { "zh": "查找用户并发送消息", "en": "Find a user and send a message." },
#             "parameters": [
#                 { "name": "message", "description": { "zh": "要发送的消息", "en": "Message text to send." }, "type": "string", "required": true },
#                 { "name": "user_name", "description": { "zh": "发送目标用户名称", "en": "Target user name keyword." }, "type": "string", "required": true },
#                 { "name": "user_type", "description": { "zh": "用户类型（contacts/groups）", "en": "Target type: contacts or groups." }, "type": "string", "required": true },
#                 { "name": "click_send", "description": { "zh": "是否点击发送按钮", "en": "Whether to tap the Send button." }, "type": "boolean", "required": false }
#             ]
#         },
#         {
#             "name": "get_history",
#             "description": { "zh": "获取当前聊天窗口的历史消息。如果用户要求读取聊天记录，那么可以用这个工具或者find_and_get_history。", "en": "Get chat history from the current chat window. If the user asks to read chat history, you can use this tool or `find_and_get_history`." },
#             "parameters": [
#                 { "name": "message_num", "description": { "zh": "获取的消息数量", "en": "Number of messages to retrieve." }, "type": "number", "required": false }
#             ]
#         },
#         {
#             "name": "find_and_get_history",
#             "description": { "zh": "查找用户并获取聊天历史记录。一般情况下，用户想要让ai帮忙回消息的时候，需要先调用这个，得到历史记录后直接调用reply。", "en": "Find a user and retrieve chat history. Typically, when the user wants the AI to reply, call this first to get context, then call `reply`." },
#             "parameters": [
#                 { "name": "user_name", "description": { "zh": "搜索用户名称", "en": "User name keyword to search." }, "type": "string", "required": true },
#                 { "name": "user_type", "description": { "zh": "搜索类型（contacts/groups）", "en": "Search type: contacts or groups." }, "type": "string", "required": true },
#                 { "name": "message_num", "description": { "zh": "获取的消息数量", "en": "Number of messages to retrieve." }, "type": "number", "required": false }
#             ]
#         }
#     ]
# }


def _at(arr, index):
    if index < 0:
        index = len(arr) + index
    if 0 <= index < len(arr):
        return arr[index]
    return None


async def close_keyboard():
    await Tools.UI.pressKey("KEYCODE_BACK")


async def is_in_group():
    page = await UINode.getCurrentPage()
    elements = page.findAllByContentDesc('语音')
    idx = -1
    for i, e in enumerate(elements):
        className = e.className or ""
        center = e.centerPoint or {}
        if 'ImageButton' in className and (center.get('y') or 0) > 1000:
            idx = i
            break
    return idx == -1


async def get_history(params):
    message_num = int(params.get("message_num")) if params.get("message_num") else 10
    if not message_num:
        message_num = 10
    page = await UINode.getCurrentPage()

    # 获取群名称
    title_node = page.findById('com.tencent.mobileqq:id/ivTitleBtnLeft')
    chat_title = ""
    if title_node is not None:
        parent = getattr(title_node, "parent", None)
        if parent is not None:
            texts = parent.allTexts()
            chat_title = texts[0] if texts else ""
    console.log("chat_title", chat_title)

    # 先滑动到最底部
    tryMax = 0
    while tryMax < 1:
        tryMax += 1
        await Tools.UI.swipe(100, 1000, 100, 200)
        await Tools.System.sleep(500)

    messageList = []
    allMessages = []

    # 获取历史消息
    tryMax = 0
    while tryMax < 5:
        tryMax += 1

        page = await UINode.getCurrentPage()
        console.log("page", page.toFormattedString())
        list_view = page.findByClass('RecyclerView')
        if not list_view:
            return None

        # 清空临时消息列表
        messageList = []

        # 获取当前可见的消息列表
        for message in list_view.children:
            message_text = '/'.join(message.allTexts())

            sender = "other"
            # 判断头像在左边还是右边
            avatar = message.findByClass('ImageView')
            if avatar:
                center = avatar.centerPoint or {}
                if (center.get('x') or 0) < 300:
                    sender = "other"
                    console.log("other", center.get('x'))
                else:
                    sender = "self"
                    console.log("self", center.get('x'))
            else:
                sender = "self"
                console.log("self")
            messageList.append({"message": message_text, "sender": sender})

        # 将当前视图中的消息添加到总集合中，保持顺序
        # 从下往上滑动时，将新获取的消息放在前面（保持旧消息在前，新消息在后的顺序）
        allMessages = messageList + allMessages

        # 如果已经获取了足够多的消息，停止滚动
        if len(allMessages) >= message_num:
            break
        await Tools.UI.swipe(100, 300, 100, 1000)
        await Tools.System.sleep(500)

    # 删除重复的消息，但保持原始顺序
    uniqueMessages = []
    seen = set()

    for msg in allMessages:
        key = f"{msg['message']}-{msg['sender']}"
        if key not in seen:
            seen.add(key)
            uniqueMessages.append(msg)

    # 返回符合数量要求的消息列表（保持原始顺序）
    return {"messages": uniqueMessages[:message_num], "chat_title": chat_title}


async def reply(params):
    # 提取参数
    message = params.get("message") or ""
    click_send = params.get("click_send") or False
    await Tools.UI.setText(message)
    await Tools.System.sleep(500)

    if click_send:
        await Tools.UI.clickElement({
            "resourceId": "com.tencent.mobileqq:id/send_btn",
            "index": "0"
        })
    return True


async def find_and_reply(params):
    # 提取参数
    message = params.get("message") or ""
    user_name = params.get("user_name") or ""
    user_type = params.get("user_type") or "contacts"
    click_send = params.get("click_send") or False
    result = await find_user({"user_name": user_name, "user_type": user_type})
    if not result:
        return False
    await Tools.System.sleep(1000)
    return await reply({"message": message, "click_send": click_send})


async def ensureActivity(activityName="", packageName="com.tencent.mobileqq", enterActivity=None, tryMax=1):
    if enterActivity is None:
        async def enterActivity():
            return True
    android = Android()
    activity = await Tools.UI.getPageInfo()
    if (activity.get("activityName") or "").find(activityName) != -1 if activityName else False:
        return True

    while tryMax > 0:
        tryMax -= 1
        await Tools.System.stopApp(packageName)
        await Tools.System.sleep(2000)
        await Tools.System.startApp(packageName)
        await Tools.System.sleep(3000)  # Give some time for app to launch
        if await enterActivity():
            activity = await Tools.UI.getPageInfo()
            if (activity.get("activityName") or "").find(activityName) != -1 if activityName else False:
                return True
    return False


async def find_user(params):
    # 提取参数
    user_name = params.get("user_name") or ""
    user_type = params.get("user_type") or "contacts"

    async def _enter_activity():
        search_btn = (await UINode.getCurrentPage()).findByText("搜索")
        if search_btn:
            await search_btn.click()
            return True
        return False

    if not await ensureActivity("com.tencent.mobileqq.search.activity.UniteSearchActivity", "com.tencent.mobileqq", _enter_activity):
        return False

    firstTarget = None
    tryMax = 0
    while tryMax < 2:
        tryMax += 1
        search_btn = (await UINode.getCurrentPage()).findByText("搜索")
        if search_btn:
            await search_btn.click()
            await Tools.System.sleep(500)
        # 输入搜索内容
        await Tools.UI.setText(user_name)
        await Tools.System.sleep(3000 * tryMax)
        await close_keyboard()

        currentPage = await UINode.getCurrentPage()
        searchResult = currentPage.findAllById('com.tencent.mobileqq:id/title')

        isNeedToCatch = False
        for child in (searchResult or []):
            if isNeedToCatch:
                firstTarget = child
                break
            title = child
            if title:
                if user_type == "contacts" and title.text == "联系人":
                    isNeedToCatch = True
                elif user_type == "groups" and title.text == "群聊":
                    isNeedToCatch = True

        if firstTarget:
            await firstTarget.click()
            return True

    return False


async def find_and_get_history(params):
    user_name = params.get("user_name") or ""
    user_type = params.get("user_type") or "contacts"
    message_num = params.get("message_num") or 10
    result = await find_user({"user_name": user_name, "user_type": user_type})
    if not result:
        return None
    await Tools.System.sleep(1000)
    return await get_history({"message_num": message_num})


async def main():
    result = await find_and_get_history({"user_name": "Dec", "user_type": "groups", "message_num": 20})
    console.log(result)
    complete({
        "success": result
    })


async def wrap_bool(func, params, successMessage, failMessage, additionalMessage=""):
    if await func(params):
        complete({
            "success": True,
            "message": successMessage,
            "additionalMessage": additionalMessage
        })
    else:
        complete({
            "success": False,
            "message": failMessage,
            "additionalMessage": additionalMessage
        })


async def wrap_data(func, params, successMessage, failMessage, additionalMessage=""):
    result = await func(params)
    complete({
        "success": True,
        "message": successMessage,
        "additionalMessage": additionalMessage,
        "data": result
    })


async def _exported_reply(params):
    await wrap_bool(reply, params, "发送成功", "发送失败")


async def _exported_find_user(params):
    additionalMessage = (await UINode.getCurrentPage()).toFormattedString()
    await wrap_bool(find_user, params, "查找成功", "查找失败，停留在界面", additionalMessage)


async def _exported_find_and_reply(params):
    additionalMessage = (await UINode.getCurrentPage()).toFormattedString()
    await wrap_bool(find_and_reply, params, "发送成功", "发送失败，停留在界面", additionalMessage)


async def _exported_get_history(params):
    await wrap_data(get_history, params, "获取历史消息成功", "获取历史消息失败")


async def _exported_find_and_get_history(params):
    await wrap_data(find_and_get_history, params, "获取历史消息成功", "获取历史消息失败")


exports.reply = _exported_reply
exports.find_user = _exported_find_user
exports.find_and_reply = _exported_find_and_reply
exports.get_history = _exported_get_history
exports.find_and_get_history = _exported_find_and_get_history
exports.main = main
