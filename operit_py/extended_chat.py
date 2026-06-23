# METADATA
# {
#     "name": "extended_chat",
#     "display_name": {
#         "zh": "增强对话",
#         "en": "Extended Chat"
#     },
#     "description": {
#         "zh": "对话工具包：列出/查找/重命名/删除对话、跨话题读取消息、绑定角色卡对话并发送消息。",
#         "en": "Chat toolkit: list/find/rename/delete chats, read messages across chats, bind character cards and send messages."
#     },
#     "enabledByDefault": true,
#     "category": "Chat",
#     "tools": [
#         {
#             "name": "list_chats",
#             "description": { "zh": "列出并筛选对话（用于获取 chat_id）。", "en": "List and filter chats (to discover chat_id)." },
#             "parameters": [
#                 { "name": "query", "description": { "zh": "可选：标题筛选关键字", "en": "Optional title keyword" }, "type": "string", "required": false },
#                 { "name": "match", "description": { "zh": "可选：contains/exact/regex（默认 contains）", "en": "Optional: contains/exact/regex (default contains)" }, "type": "string", "required": false },
#                 { "name": "limit", "description": { "zh": "可选：最多返回条数（默认 50）", "en": "Optional max results (default 50)" }, "type": "number", "required": false },
#                 { "name": "sort_by", "description": { "zh": "可选：updatedAt/createdAt/messageCount（默认 updatedAt）", "en": "Optional: updatedAt/createdAt/messageCount (default updatedAt)" }, "type": "string", "required": false },
#                 { "name": "sort_order", "description": { "zh": "可选：asc/desc（默认 desc）", "en": "Optional: asc/desc (default desc)" }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "find_chat",
#             "description": { "zh": "按标题查找一个对话并返回 chat_id。", "en": "Find a single chat by title and return chat_id." },
#             "parameters": [
#                 { "name": "query", "description": { "zh": "标题关键字/正则", "en": "Title keyword/regex" }, "type": "string", "required": true },
#                 { "name": "match", "description": { "zh": "可选：contains/exact/regex（默认 contains）", "en": "Optional: contains/exact/regex (default contains)" }, "type": "string", "required": false },
#                 { "name": "index", "description": { "zh": "可选：当匹配多个时选择第 N 个（默认 0）", "en": "Optional: pick Nth when multiple matches (default 0)" }, "type": "number", "required": false }
#             ]
#         },
#         {
#             "name": "read_messages",
#             "description": { "zh": "读取指定对话的消息（可按 chat_id 或 chat_title 指定）。", "en": "Read messages from a chat (by chat_id or chat_title)." },
#             "parameters": [
#                 { "name": "chat_id", "description": { "zh": "目标对话 ID（可选）", "en": "Target chat id (optional)" }, "type": "string", "required": false },
#                 { "name": "chat_title", "description": { "zh": "目标对话标题（可选；当 chat_id 为空时使用）", "en": "Target chat title (optional; used when chat_id is empty)" }, "type": "string", "required": false },
#                 { "name": "chat_query", "description": { "zh": "可选：标题筛选关键字（当 chat_id/chat_title 为空时使用）", "en": "Optional title keyword (used when chat_id/chat_title is empty)" }, "type": "string", "required": false },
#                 { "name": "chat_index", "description": { "zh": "可选：当筛选结果有多个时选择第 N 个（默认 0）", "en": "Optional: pick Nth when multiple matches (default 0)" }, "type": "number", "required": false },
#                 { "name": "match", "description": { "zh": "可选：contains/exact/regex（默认 contains）", "en": "Optional: contains/exact/regex (default contains)" }, "type": "string", "required": false },
#                 { "name": "order", "description": { "zh": "可选：asc/desc（默认 desc）", "en": "Optional: asc/desc (default desc)" }, "type": "string", "required": false },
#                 { "name": "limit", "description": { "zh": "可选：返回消息条数（默认 20）", "en": "Optional: max number of messages (default 20)" }, "type": "number", "required": false }
#             ]
#         },
#         {
#             "name": "rename_chat",
#             "description": { "zh": "重命名指定对话（可按 chat_id 或 chat_title 指定）。", "en": "Rename a chat (by chat_id or chat_title)." },
#             "parameters": [
#                 { "name": "new_title", "description": { "zh": "新的对话标题", "en": "New chat title" }, "type": "string", "required": true },
#                 { "name": "chat_id", "description": { "zh": "目标对话 ID（可选）", "en": "Target chat id (optional)" }, "type": "string", "required": false },
#                 { "name": "chat_title", "description": { "zh": "目标对话标题（可选；当 chat_id 为空时使用）", "en": "Target chat title (optional; used when chat_id is empty)" }, "type": "string", "required": false },
#                 { "name": "chat_query", "description": { "zh": "可选：标题筛选关键字（当 chat_id/chat_title 为空时使用）", "en": "Optional title keyword (used when chat_id/chat_title is empty)" }, "type": "string", "required": false },
#                 { "name": "chat_index", "description": { "zh": "可选：当筛选结果有多个时选择第 N 个（默认 0）", "en": "Optional: pick Nth when multiple matches (default 0)" }, "type": "number", "required": false },
#                 { "name": "match", "description": { "zh": "可选：contains/exact/regex（默认 contains）", "en": "Optional: contains/exact/regex (default contains)" }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "delete_chat",
#             "description": { "zh": "删除指定对话（可按 chat_id 或 chat_title 指定）。", "en": "Delete a chat (by chat_id or chat_title)." },
#             "parameters": [
#                 { "name": "chat_id", "description": { "zh": "目标对话 ID（可选）", "en": "Target chat id (optional)" }, "type": "string", "required": false },
#                 { "name": "chat_title", "description": { "zh": "目标对话标题（可选；当 chat_id 为空时使用）", "en": "Target chat title (optional; used when chat_id is empty)" }, "type": "string", "required": false },
#                 { "name": "chat_query", "description": { "zh": "可选：标题筛选关键字（当 chat_id/chat_title 为空时使用）", "en": "Optional title keyword (used when chat_id/chat_title is empty)" }, "type": "string", "required": false },
#                 { "name": "chat_index", "description": { "zh": "可选：当筛选结果有多个时选择第 N 个（默认 0）", "en": "Optional: pick Nth when multiple matches (default 0)" }, "type": "number", "required": false },
#                 { "name": "match", "description": { "zh": "可选：contains/exact/regex（默认 contains）", "en": "Optional: contains/exact/regex (default contains)" }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "chat_with_agent",
#             "description": { "zh": "与对应角色的 agent 对话：传入角色卡名称；chat_id 为空时自动创建新对话并返回新 ID。严格执行一角色一会话，不能多个角色共用同一会话。该工具可用于将任务分担给其他 agent 或与其他角色交流，但通常只有在用户明确表达此意图时使用；多数情况下，能自行完成的任务应优先直接完成。", "en": "Chat with the agent for the specified character card name; if chat_id is empty, create a new chat and return its ID. Enforces one role per chat (no sharing between roles). Use this tool to delegate tasks to other agents or communicate with other roles when the user explicitly intends it; otherwise, prefer completing tasks directly without using this tool." },
#             "parameters": [
#                 { "name": "message", "description": { "zh": "发送给 AI 的内容", "en": "Message to send to AI" }, "type": "string", "required": true },
#                 { "name": "character_card_name", "description": { "zh": "角色卡名称", "en": "Character card name" }, "type": "string", "required": true },
#                 { "name": "chat_id", "description": { "zh": "目标对话 ID（可选；为空时新建）", "en": "Target chat id (optional; create new if empty)" }, "type": "string", "required": false },
#                 { "name": "timeout", "description": { "zh": "可选：等待返回的超时秒数（默认 180）", "en": "Optional timeout seconds to wait for response (default 180)" }, "type": "number", "required": false },
#                 { "name": "persist_turn", "description": { "zh": "可选：是否持久化本轮用户消息和 AI 回复（默认 true）", "en": "Optional: whether to persist this turn's user message and AI reply (default true)" }, "type": "boolean", "required": false },
#                 { "name": "notify_reply", "description": { "zh": "可选：是否覆盖本轮回复通知开关", "en": "Optional: override reply notification for this turn" }, "type": "boolean", "required": false },
#                 { "name": "hide_user_message", "description": { "zh": "可选：是否在 UI 中隐藏用户消息正文并显示占位标记", "en": "Optional: hide the user message body in UI and show a placeholder marker" }, "type": "boolean", "required": false },
#                 { "name": "disable_warning", "description": { "zh": "可选：是否关闭本轮 AI 生成的 warning 标记", "en": "Optional: suppress AI-generated warning markup for this turn" }, "type": "boolean", "required": false }
#             ]
#         },
#         {
#             "name": "agent_status",
#             "description": { "zh": "查询对话的输入处理状态。", "en": "Check a chat's input processing status." },
#             "parameters": [
#                 { "name": "chat_id", "description": { "zh": "目标对话 ID", "en": "Target chat id" }, "type": "string", "required": true }
#             ]
#         },
#         {
#             "name": "list_character_cards",
#             "description": { "zh": "列出所有角色卡（用于获取 character_card_id）。", "en": "List all character cards (to discover character_card_id)." },
#             "parameters": []
#         }
#     ]
# }

import asyncio
import math


def _to_number(value, default=None):
    if value is None:
        return default
    try:
        n = float(value)
        if math.isnan(n):
            return default
        return n
    except (TypeError, ValueError):
        return default


def normalizeMatchMode(match=None):
    m = str(match or "").strip().lower()
    if m in ("exact", "regex", "contains"):
        return m
    return "contains"


async def list_chats_impl(params):
    params = params or {}
    query = str(params.get("query") if params.get("query") is not None else "").strip()
    matchMode = normalizeMatchMode(params.get("match"))
    limit = _to_number(params.get("limit"), None)
    sortBy = str(params.get("sort_by")).strip() if params.get("sort_by") else None
    sortOrder = str(params.get("sort_order")).strip().lower() if params.get("sort_order") else None

    listParams = {}
    if query:
        listParams["query"] = query
    if matchMode:
        listParams["match"] = matchMode
    if limit is not None:
        listParams["limit"] = limit
    if sortBy:
        listParams["sort_by"] = sortBy
    if sortOrder:
        listParams["sort_order"] = sortOrder

    listResult = await Tools.Chat.listChats(listParams)
    chats = listResult.get("chats") if isinstance(listResult, dict) else listResult
    if chats is None:
        chats = []
    return {
        "success": True,
        "message": "对话列表获取完成",
        "data": {
            "totalCount": (listResult.get("totalCount") if isinstance(listResult, dict) else None) or len(chats),
            "currentChatId": (listResult.get("currentChatId") if isinstance(listResult, dict) else None) or None,
            "matchedCount": (listResult.get("totalCount") if isinstance(listResult, dict) else None) or len(chats),
            "chats": chats,
        }
    }


async def find_chat_impl(params):
    params = params or {}
    query = str(params.get("query") if params.get("query") is not None else "").strip()
    if not query:
        raise Exception("Missing parameter: query")

    matchMode = normalizeMatchMode(params.get("match"))
    index = _to_number(params.get("index"), 0)
    if index is None:
        index = 0
    findParams = {"query": query}
    if matchMode:
        findParams["match"] = matchMode
    findParams["index"] = index
    findResult = await Tools.Chat.findChat(findParams)
    picked = (findResult.get("chat") if isinstance(findResult, dict) else None) or None
    if not picked:
        raise Exception(f"Chat not found by query: {query}")

    return {
        "success": True,
        "message": "对话查找完成",
        "data": {
            "chat": picked,
            "matchedCount": (findResult.get("matchedCount") if isinstance(findResult, dict) else None) or 1,
        }
    }


async def resolveChatId(params):
    params = params or {}
    if isinstance(params.get("chat_id"), str) and params.get("chat_id").strip():
        return params["chat_id"].strip()

    title = params.get("chat_title").strip() if isinstance(params.get("chat_title"), str) else ""
    query = params.get("chat_query").strip() if isinstance(params.get("chat_query"), str) else ""
    matchMode = normalizeMatchMode(params.get("match"))
    index = _to_number(params.get("chat_index"), 0)
    if index is None:
        index = 0

    if not title and not query:
        raise Exception("Missing parameter: chat_id or chat_title or chat_query is required")

    needle = title or query
    findParams = {"query": needle}
    findParams["match"] = "exact" if title else matchMode
    findParams["index"] = index
    findResult = await Tools.Chat.findChat(findParams)
    picked = (findResult.get("chat") if isinstance(findResult, dict) else None) or None
    if not picked or not picked.get("id"):
        raise Exception(f"Chat not found by query: {needle}")
    return picked.get("id")


async def read_messages_impl(params):
    params = params or {}
    chatId = await resolveChatId(params)

    orderRaw = str(params.get("order")).strip().lower() if params.get("order") is not None else ""
    order = orderRaw if orderRaw in ("asc", "desc") else "desc"

    limit = _to_number(params.get("limit"), 20)
    if limit is None:
        limit = 20

    result = await Tools.Chat.getMessages(chatId, {
        "order": order,
        "limit": limit,
    })

    rawMessages = result.get("messages") if isinstance(result, dict) else result
    if rawMessages is None:
        rawMessages = []

    def _format(m):
        role = str(m.get("roleName") if m.get("roleName") is not None else (m.get("sender") if m.get("sender") is not None else "")) or "message"
        ts = str(m.get("timestamp")) if m.get("timestamp") is not None else ""
        header = f"[{ts}] {role}" if ts else role
        return f"{header}:\n{str(m.get('content') if m.get('content') is not None else '')}"

    text = "\n\n".join(_format(m) for m in rawMessages)

    return {
        "success": True,
        "message": "读取对话消息完成",
        "data": {
            "result": result,
            "text": text,
        },
    }


async def rename_chat_impl(params):
    params = params or {}
    newTitle = str(params.get("new_title") if params.get("new_title") is not None else "").strip()
    if not newTitle:
        raise Exception("Missing parameter: new_title")

    chatId = await resolveChatId(params)
    result = await Tools.Chat.updateTitle(chatId, newTitle)

    return {
        "success": True,
        "message": "对话重命名完成",
        "data": {
            "chat_id": chatId,
            "title": newTitle,
            "result": result,
        },
    }


async def delete_chat_impl(params):
    params = params or {}
    chatId = await resolveChatId(params)
    result = await Tools.Chat.deleteChat(chatId)

    return {
        "success": True,
        "message": "对话删除完成",
        "data": {
            "chat_id": chatId,
            "result": result,
        },
    }


async def agent_status_impl(params):
    params = params or {}
    chatId = str(params.get("chat_id") if params.get("chat_id") is not None else "").strip()
    if not chatId:
        raise Exception("Missing parameter: chat_id")
    result = await Tools.Chat.agentStatus(chatId)
    return {
        "success": True,
        "message": "对话状态查询完成",
        "data": {
            "result": result,
        },
    }


async def list_character_cards_impl():
    result = await Tools.Chat.listCharacterCards()
    cards = result.get("cards") if isinstance(result, dict) else result
    if cards is None:
        cards = []
    return {
        "success": True,
        "message": "角色卡列表获取完成",
        "data": {
            "totalCount": (result.get("totalCount") if isinstance(result, dict) else None) or len(cards),
            "cards": cards,
        },
    }


async def chat_with_agent_impl(params):
    params = params or {}
    message = str(params.get("message") if params.get("message") is not None else "")
    characterCardNameInput = str(params.get("character_card_name") if params.get("character_card_name") is not None else "").strip()
    if not message.strip():
        raise Exception("Missing parameter: message")
    if not characterCardNameInput:
        raise Exception("Missing parameter: character_card_name")

    characterCardName = characterCardNameInput
    characterCardId = ""
    try:
        cardResult = await Tools.Chat.listCharacterCards()
        cards = cardResult.get("cards") if isinstance(cardResult, dict) else cardResult
        if cards is None:
            cards = []
        targetCard = next((card for card in cards if card.get("name") == characterCardNameInput), None)
        if not targetCard:
            raise Exception(f"Character card not found: {characterCardNameInput}")
        characterCardName = targetCard.get("name")
        characterCardId = targetCard.get("id")
    except Exception:
        if not characterCardId:
            raise Exception(f"Character card not found: {characterCardNameInput}")

    try:
        await Tools.Chat.startService()
    except Exception:
        # ignore service start errors to avoid blocking agent message
        pass

    chatId = str(params.get("chat_id") if params.get("chat_id") is not None else "").strip()
    if not chatId:
        lang = str(getLang() or "").lower()
        group = "子任务" if lang == "zh" else "subTask"
        creation = await Tools.Chat.createNew(
            group,
            False,
            characterCardId,
        )
        chatId = str(creation.get("chatId") if isinstance(creation, dict) and creation.get("chatId") is not None else "").strip()
        if not chatId:
            raise Exception("Failed to create new chat")
    else:
        findResult = await Tools.Chat.findChat({
            "query": chatId,
            "match": "exact",
            "index": 0,
        })
        boundName = (findResult.get("chat") if isinstance(findResult, dict) else {}).get("characterCardName") if isinstance(findResult, dict) else None
        if boundName and boundName != characterCardName:
            raise Exception(f"Chat {chatId} 已绑定角色 {boundName}，不能与 {characterCardName} 共用会话")

    timeoutRaw = _to_number(params.get("timeout"), 180)
    if timeoutRaw is None or timeoutRaw <= 0:
        timeoutSec = 180
    else:
        timeoutSec = timeoutRaw
    timeoutMs = timeoutSec * 1000

    sendMessageOptions = {}
    if params.get("persist_turn") is not None:
        sendMessageOptions["persist_turn"] = params.get("persist_turn")
    if params.get("notify_reply") is not None:
        sendMessageOptions["notify_reply"] = params.get("notify_reply")
    if params.get("hide_user_message") is not None:
        sendMessageOptions["hide_user_message"] = params.get("hide_user_message")
    if params.get("disable_warning") is not None:
        sendMessageOptions["disable_warning"] = params.get("disable_warning")
    sendMessageOptions["timeout_ms"] = timeoutMs

    sendResult = None
    timed_out = False
    try:
        sendResult = await asyncio.wait_for(
            Tools.Chat.sendMessage(
                message,
                chatId,
                characterCardId,
                getCallerName() or characterCardName,
                sendMessageOptions,
            ),
            timeout=timeoutMs / 1000
        )
    except asyncio.TimeoutError:
        timed_out = True

    if timed_out:
        return {
            "success": True,
            "message": f"已发送给 {characterCardName}，等待响应超时（{timeoutSec}s）",
            "data": {
                "chat_id": chatId,
                "timeout": True,
                "hint": "可以通过 agent_status 查看该 agent 是否已处理你的问题。",
            },
        }

    return {
        "success": True,
        "message": f"发消息给 {characterCardName}",
        "data": {
            "chat_id": chatId,
            "result": sendResult,
        },
    }


async def wrapToolExecution(func, params):
    try:
        result = await func(params)
        complete(result)
    except Exception as error:
        message = str(error)
        console.error(f"Tool {func.__name__} failed unexpectedly", error)
        complete({
            "success": False,
            "message": f"读取对话消息失败: {message}",
        })


async def wrapToolExecutionNoParams(func):
    try:
        result = await func()
        complete(result)
    except Exception as error:
        message = str(error)
        console.error(f"Tool {func.__name__} failed unexpectedly", error)
        complete({
            "success": False,
            "message": f"读取对话消息失败: {message}",
        })


async def read_messages(params):
    return await wrapToolExecution(read_messages_impl, params)


async def rename_chat(params):
    return await wrapToolExecution(rename_chat_impl, params)


async def delete_chat(params):
    return await wrapToolExecution(delete_chat_impl, params)


async def list_chats(params):
    return await wrapToolExecution(list_chats_impl, params)


async def find_chat(params):
    return await wrapToolExecution(find_chat_impl, params)


async def agent_status(params):
    return await wrapToolExecution(agent_status_impl, params)


async def list_character_cards(params=None):
    if params is None:
        params = {}
    return await wrapToolExecutionNoParams(list_character_cards_impl)


async def chat_with_agent(params):
    return await wrapToolExecution(chat_with_agent_impl, params)


async def main(params=None):
    if params is None:
        params = {}
    complete({
        "success": True,
        "message": "extended_chat 工具包已加载",
        "data": {
            "hint": "Use extended_chat:read_messages / rename_chat / delete_chat.",
        },
    })


exports.list_chats = list_chats
exports.find_chat = find_chat
exports.read_messages = read_messages
exports.rename_chat = rename_chat
exports.delete_chat = delete_chat
exports.chat_with_agent = chat_with_agent
exports.agent_status = agent_status
exports.list_character_cards = list_character_cards
exports.main = main
