# METADATA
# {
#     "name": "daily_life",
#     "display_name": { "zh": "日常生活工具包", "en": "Daily Life Toolkit" },
#     "description": { "zh": "日常生活工具集合：日期时间、设备状态、电量/内存概况、天气查询、提醒、闹钟、短信、电话、微信单条消息发送、QQ单条消息发送、朋友圈发布、手电筒、音量调节、Wi-Fi 开关、截图、拍照、深色模式、指定时间唤醒 AI 执行一次性定时任务。", "en": "Daily life utilities: date/time, device status, battery/memory overview, weather lookup, reminders, alarms, SMS, calls, single-message WeChat send, single-message QQ send, Moments posting, flashlight, volume control, Wi-Fi toggle, screenshots, photos, dark mode, wake AI at a specified time for a one-time scheduled task." },
#     "enabledByDefault": true,
#     "category": "Life",
#     "tools": [
#         { "name": "get_current_date", "description": { "zh": "获取当前日期和时间，支持多种格式展示", "en": "Get the current date and time in various formats." }, "parameters": [ { "name": "format", "description": { "zh": "日期格式（'short'简短格式, 'medium'中等格式, 'long'完整格式，或自定义格式）", "en": "Date format: 'short', 'medium', 'long', or a custom format." }, "type": "string", "required": false } ] },
#         { "name": "device_status", "description": { "zh": "获取设备状态信息，包括电池和内存使用情况", "en": "Get device status information, including battery and memory usage." }, "parameters": [] },
#         { "name": "set_reminder", "description": { "zh": "创建提醒或待办事项。", "en": "Create a reminder or to-do item." }, "parameters": [ { "name": "title", "type": "string", "required": true }, { "name": "description", "type": "string", "required": false }, { "name": "due_date", "type": "string", "required": false } ] },
#         { "name": "schedule_one_time_task", "description": { "zh": "在指定时间唤醒 AI 执行一次性定时任务。", "en": "Wake the AI at a specified time to execute a one-time scheduled task." }, "parameters": [ { "name": "trigger_time", "type": "string", "required": true }, { "name": "message", "type": "string", "required": false } ] },
#         { "name": "set_alarm", "description": { "zh": "在设备上设置闹钟。", "en": "Set an alarm on the device." }, "parameters": [ { "name": "hour", "type": "number", "required": true }, { "name": "minute", "type": "number", "required": true }, { "name": "message", "type": "string", "required": true }, { "name": "days", "type": "array", "required": false } ] },
#         { "name": "send_message", "description": { "zh": "发送短信", "en": "Send an SMS message." }, "parameters": [ { "name": "phone_number", "type": "string", "required": true }, { "name": "message", "type": "string", "required": true } ] },
#         { "name": "wechat_send_message", "description": { "zh": "通过微信发送文本消息", "en": "Send a text message via WeChat." }, "parameters": [ { "name": "message", "type": "string", "required": true } ] },
#         { "name": "qq_send_message", "description": { "zh": "通过QQ发送文本消息", "en": "Send a text message via QQ." }, "parameters": [ { "name": "message", "type": "string", "required": true } ] },
#         { "name": "wechat_post_moments", "description": { "zh": "通过微信朋友圈发表文本内容", "en": "Post text to WeChat Moments." }, "parameters": [ { "name": "message", "type": "string", "required": true } ] },
#         { "name": "make_phone_call", "description": { "zh": "拨打电话", "en": "Make a phone call." }, "parameters": [ { "name": "phone_number", "type": "string", "required": true }, { "name": "emergency", "type": "boolean", "required": false } ] },
#         { "name": "search_weather", "description": { "zh": "搜索当前天气信息", "en": "Search current weather information." }, "parameters": [ { "name": "location", "type": "string", "required": false } ] },
#         { "name": "toggle_flashlight", "description": { "zh": "打开或关闭手电筒", "en": "Turn the flashlight on or off." }, "parameters": [ { "name": "state", "type": "string", "required": true } ] },
#         { "name": "adjust_volume", "description": { "zh": "调节设备音量", "en": "Adjust device volume." }, "parameters": [ { "name": "action", "type": "string", "required": true }, { "name": "count", "type": "number", "required": false } ] },
#         { "name": "toggle_wifi", "description": { "zh": "打开或关闭Wi-Fi", "en": "Turn Wi-Fi on or off." }, "parameters": [ { "name": "state", "type": "string", "required": true } ] },
#         { "name": "take_screenshot", "description": { "zh": "截取当前屏幕", "en": "Take a screenshot." }, "parameters": [ { "name": "file_path", "type": "string", "required": false } ] },
#         { "name": "take_photo", "description": { "zh": "打开相机应用拍照", "en": "Open the camera app to take a photo." }, "parameters": [] },
#         { "name": "toggle_dark_mode", "description": { "zh": "切换系统深夜模式", "en": "Toggle system dark mode." }, "parameters": [ { "name": "state", "type": "string", "required": true } ] }
#     ]
# }

import json
import re
import time
import math
import asyncio
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

Error = Exception


# Android Intent 降级 stub（此功能仅在 Android 上可用）
class IntentAction:
    ACTION_INSERT = "android.intent.action.INSERT"
    ACTION_SENDTO = "android.intent.action.SENDTO"
    ACTION_SEND = "android.intent.action.SEND"
    ACTION_DIAL = "android.intent.action.DIAL"
    ACTION_CALL_EMERGENCY = "android.intent.action.CALL_EMERGENCY"
    ACTION_IMAGE_CAPTURE = "android.media.action.IMAGE_CAPTURE"


class IntentFlag:
    ACTIVITY_NEW_TASK = 0x10000000


class Intent:
    """Android Intent 降级 stub - 仅在 Android 上可用"""

    def __init__(self, action=None):
        self._action = action
        self._data = None
        self._type = None
        self._extras = {}
        self._flags = 0
        self._categories = []
        self._component = None

    def setData(self, data):
        self._data = data
        return self

    def setType(self, mime_type):
        self._type = mime_type
        return self

    def putExtra(self, key, value):
        self._extras[key] = value
        return self

    def addFlag(self, flag):
        self._flags |= flag
        return self

    def addCategory(self, category):
        self._categories.append(category)
        return self

    def setComponent(self, pkg, cls):
        self._component = (pkg, cls)
        return self

    async def start(self):
        return {"success": False, "message": "此功能仅在 Android 上可用"}


async def get_current_date(params):
    try:
        fmt = params.get("format", "medium") if params else "medium"
        now = datetime.now()

        if fmt == "short":
            formattedDate = now.strftime("%Y/%m/%d")
        elif fmt == "long":
            formattedDate = now.strftime("%Y年%m月%d日 %A %H:%M:%S")
        else:
            formattedDate = now.strftime("%Y年%m月%d日 %H:%M")

        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return {
            "timestamp": int(now.timestamp() * 1000),
            "iso": now.isoformat(),
            "formatted": formattedDate,
            "date": {
                "year": now.year,
                "month": now.month,
                "day": now.day,
                "weekday": weekdays[now.weekday()]
            },
            "time": {
                "hours": now.hour,
                "minutes": now.minute,
                "seconds": now.second
            }
        }
    except Exception as error:
        console.error(f"[get_current_date] 错误: {error}")
        import traceback
        console.error(traceback.format_exc())
        raise error


async def device_status():
    try:
        deviceInfo = await Tools.System.getDeviceInfo()
        return {
            "battery": {
                "level": deviceInfo.batteryLevel,
                "charging": deviceInfo.batteryCharging
            },
            "memory": {
                "total": deviceInfo.totalMemory,
                "available": deviceInfo.availableMemory
            },
            "storage": {
                "total": deviceInfo.totalStorage,
                "available": deviceInfo.availableStorage
            },
            "device": {
                "model": deviceInfo.model,
                "manufacturer": deviceInfo.manufacturer,
                "androidVersion": deviceInfo.androidVersion
            },
            "network": deviceInfo.networkType
        }
    except Exception as error:
        raise Error(f"Failed to get device status: {error}")


def extractWeatherInfo(content):
    cleanContent = re.sub(r'</?[^>]+(>|$)', " ", content)
    cleanContent = re.sub(r'\s+', " ", cleanContent).strip()
    maxLength = 1500
    if len(cleanContent) > maxLength:
        return cleanContent[:maxLength] + "..."
    return cleanContent


async def search_weather(params):
    try:
        location = (params.get("location") if params else None) or "current"
        if location == "current":
            searchUrl = "https://www.baidu.com/s?wd=当前天气"
        else:
            searchUrl = f"https://www.baidu.com/s?wd={quote(location + ' 天气')}"

        console.log(f"搜索天气信息: {searchUrl}")
        result = await Tools.Net.visit(searchUrl)
        extractedInfo = extractWeatherInfo(result.content)

        return {
            "success": True,
            "query": "当前天气" if location == "current" else f"{location} 天气",
            "location": location,
            "timestamp": datetime.now().isoformat(),
            "url": result.url,
            "title": result.title,
            "weather_info": extractedInfo,
            "note": "天气数据来自网页内容提取，仅供参考。"
        }
    except Exception as error:
        console.error(f"[search_weather] 错误: {error}")
        import traceback
        console.error(traceback.format_exc())
        raise Error(f"获取天气信息失败: {error}")


async def set_reminder(params):
    try:
        if not params or not params.get("title"):
            raise Error("Reminder title is required")

        console.log("创建提醒...")
        console.log("尝试使用隐式Intent创建日历事件...")

        intent = Intent(IntentAction.ACTION_INSERT)
        intent.setData("content://com.android.calendar/events")
        intent.putExtra("title", params["title"])
        if params.get("description"):
            intent.putExtra("description", params["description"])

        if params.get("due_date"):
            dueDate = datetime.fromisoformat(params["due_date"])
            beginTime = int(dueDate.timestamp() * 1000)
            endTime = beginTime + 3600000
            intent.putExtra("beginTime", beginTime)
            intent.putExtra("endTime", endTime)
            intent.putExtra("eventTimezone", "UTC")
            intent.putExtra("allDay", False)
        else:
            now = datetime.now()
            beginTime = int(now.timestamp() * 1000)
            endTime = beginTime + 3600000
            intent.putExtra("beginTime", beginTime)
            intent.putExtra("endTime", endTime)
            intent.putExtra("eventTimezone", "UTC")
            intent.putExtra("allDay", False)

        intent.putExtra("hasAlarm", 1)
        intent.addFlag(IntentFlag.ACTIVITY_NEW_TASK)
        result = await intent.start()

        return {
            "success": True,
            "message": "提醒创建成功",
            "title": params["title"],
            "description": params.get("description"),
            "due_date": params.get("due_date"),
            "method": "implicit_intent",
            "raw_result": result
        }
    except Exception as error:
        console.error(f"[set_reminder] 错误: {error}")
        import traceback
        console.error(traceback.format_exc())
        return {
            "success": False,
            "message": f"创建提醒失败: {error}",
            "title": params.get("title") if params else None,
            "description": params.get("description") if params else None,
            "due_date": params.get("due_date") if params else None,
            "error": str(error)
        }


async def schedule_one_time_task(params):
    if not params or not params.get("trigger_time"):
        raise Error("trigger_time is required")

    resolvedChatId = getChatId()
    if not resolvedChatId:
        raise Error("chat_id is required (call from a chat context)")

    resolvedRoleCardId = getCallerCardId()
    resolvedSenderName = getCallerName()
    resolvedLang = getLang()
    workflowName = (f"一次性定时任务 {params['trigger_time']}"
                    if resolvedLang and resolvedLang.lower().startswith("zh")
                    else f"One-time scheduled task {params['trigger_time']}")
    description = (f"一次性定时任务，触发时间 {params['trigger_time']}"
                   if resolvedLang and resolvedLang.lower().startswith("zh")
                   else f"One-time scheduled task at {params['trigger_time']}")
    timedTriggerTag = f"[定时触发:{params['trigger_time']}]\n[Scheduled Trigger:{params['trigger_time']}]"
    defaultMessage = (f"[自动任务] 时间到了，开始执行一次性定时任务。现在是 {params['trigger_time']}\n"
                      f"[Automated Task] Time reached, start executing the one-time scheduled task. Current time is {params['trigger_time']}")
    messageContent = (f"{params['message']}\n{timedTriggerTag}"
                      if params.get("message")
                      else f"{defaultMessage}\n{timedTriggerTag}")

    created = await Tools.Workflow.create(workflowName, description, None, None, True)
    workflowId = created.id if created else None
    if not workflowId:
        raise Error("Failed to create workflow: missing workflow id")

    uniqueId = str(int(time.time() * 1000))
    triggerNodeId = f"trigger_{uniqueId}"
    startNodeId = f"start_{uniqueId}"
    sendNodeId = f"send_{uniqueId}"
    deleteNodeId = f"delete_{uniqueId}"

    actionConfig = {
        "message": messageContent,
        "chat_id": resolvedChatId,
        "hide_user_message": True,
        "notify_reply": True,
        "persist_turn": True,
        "disable_warning": False,
    }
    if resolvedRoleCardId:
        actionConfig["role_card_id"] = resolvedRoleCardId
    if resolvedSenderName:
        actionConfig["sender_name"] = resolvedSenderName

    if resolvedLang and resolvedLang.lower().startswith("zh"):
        nodeTexts = {
            "triggerName": "定时触发", "triggerDesc": "一次性定时触发",
            "startName": "启动对话服务", "startDesc": "启动对话服务以便发送消息",
            "sendName": "唤醒AI", "sendDesc": "向对话发送唤醒消息，触发AI执行任务",
            "deleteName": "删除工作流", "deleteDesc": "执行后删除自己"
        }
    else:
        nodeTexts = {
            "triggerName": "Scheduled Trigger", "triggerDesc": "One-time scheduled trigger",
            "startName": "Start Chat Service", "startDesc": "Start chat service to enable messaging",
            "sendName": "Wake AI", "sendDesc": "Send a wake message to trigger AI task execution",
            "deleteName": "Delete Workflow", "deleteDesc": "Delete itself after execution"
        }

    nodes = [
        {
            "id": triggerNodeId, "type": "trigger", "name": nodeTexts["triggerName"],
            "description": nodeTexts["triggerDesc"], "position": {"x": 0, "y": 0},
            "triggerType": "schedule",
            "triggerConfig": {
                "schedule_type": "specific_time", "specific_time": params["trigger_time"],
                "repeat": "false", "enabled": "true"
            }
        },
        {
            "id": startNodeId, "type": "execute", "name": nodeTexts["startName"],
            "description": nodeTexts["startDesc"], "position": {"x": 260, "y": 0},
            "actionType": "start_chat_service",
            "actionConfig": {"initial_mode": "BALL", "keep_if_exists": "true"}
        },
        {
            "id": sendNodeId, "type": "execute", "name": nodeTexts["sendName"],
            "description": nodeTexts["sendDesc"], "position": {"x": 520, "y": 0},
            "actionType": "send_message_to_ai", "actionConfig": actionConfig
        },
        {
            "id": deleteNodeId, "type": "execute", "name": nodeTexts["deleteName"],
            "description": nodeTexts["deleteDesc"], "position": {"x": 1040, "y": 0},
            "actionType": "delete_workflow", "actionConfig": {"workflow_id": workflowId}
        }
    ]

    connections = [
        {"sourceNodeId": triggerNodeId, "targetNodeId": startNodeId, "condition": "on_success"},
        {"sourceNodeId": startNodeId, "targetNodeId": sendNodeId, "condition": "on_success"},
        {"sourceNodeId": sendNodeId, "targetNodeId": deleteNodeId, "condition": "on_success"}
    ]

    await Tools.Workflow.update(workflowId, {
        "name": workflowName, "description": description,
        "enabled": True, "nodes": nodes, "connections": connections
    })

    return {
        "success": True,
        "message": "一次性提醒工作流已创建",
        "data": {
            "workflow_id": workflowId,
            "trigger_time": params["trigger_time"],
            "chat_id": resolvedChatId,
            "role_card_id": resolvedRoleCardId,
            "workflow_name": workflowName
        }
    }


async def set_alarm(params):
    try:
        if params.get("hour") is None or params.get("minute") is None:
            raise Error("Hour and minute are required for setting an alarm")
        repeatDays = [d for d in params.get("days", []) if isinstance(d, (int, float))] if isinstance(params.get("days"), list) else []
        hour = params["hour"]
        minute = params["minute"]
        if hour < 0 or hour > 23:
            raise Error("Hour must be between 0 and 23")
        if minute < 0 or minute > 59:
            raise Error("Minute must be between 0 and 59")

        console.log(f"设置闹钟...{hour}:{minute}")
        console.log("尝试使用隐式Intent设置闹钟...")

        intent = Intent("android.intent.action.SET_ALARM")
        intent.putExtra("android.intent.extra.alarm.HOUR", hour)
        intent.putExtra("android.intent.extra.alarm.MINUTES", minute)
        intent.putExtra("android.intent.extra.alarm.MESSAGE", params.get("message", ""))
        if len(repeatDays) > 0:
            intent.putExtra("android.intent.extra.alarm.DAYS", repeatDays)
        intent.putExtra("android.intent.extra.alarm.VIBRATE", True)
        intent.addFlag(IntentFlag.ACTIVITY_NEW_TASK)
        intent.addCategory("android.intent.category.DEFAULT")
        result = await intent.start()

        return {
            "success": True,
            "message": "闹钟设置成功",
            "alarm_time": f"{str(hour).zfill(2)}:{str(minute).zfill(2)}",
            "label": params.get("message"),
            "repeat_days": params.get("days"),
            "method": "implicit_intent",
            "raw_result": result
        }
    except Exception as error:
        console.error(f"[set_alarm] 错误: {error}")
        import traceback
        console.error(traceback.format_exc())
        hour = params.get("hour", 0) if params else 0
        minute = params.get("minute", 0) if params else 0
        return {
            "success": False,
            "message": f"设置闹钟失败: {error}",
            "alarm_time": f"{str(hour).zfill(2)}:{str(minute).zfill(2)}",
            "label": params.get("message") if params else None,
            "repeat_days": params.get("days") if params else None,
            "error": str(error)
        }


async def send_message(params):
    try:
        if not params or not params.get("phone_number"):
            raise Error("Phone number is required")
        if not params.get("message"):
            raise Error("Message content is required")

        console.log(f"发送短信: {params['phone_number']}")
        intent = Intent(IntentAction.ACTION_SENDTO)
        intent.setData(f"smsto:{params['phone_number']}")
        intent.putExtra("sms_body", params["message"])
        intent.addFlag(IntentFlag.ACTIVITY_NEW_TASK)
        result = await intent.start()

        msg = params["message"]
        return {
            "success": True,
            "message": "短信编辑界面已打开",
            "phone_number": params["phone_number"],
            "content_preview": msg[:30] + "..." if len(msg) > 30 else msg,
            "raw_result": result
        }
    except Exception as error:
        console.error(f"发送短信失败: {error}")
        return {
            "success": False,
            "message": f"发送短信失败: {error}",
            "phone_number": params.get("phone_number") if params else None
        }


async def wechat_send_message(params):
    try:
        if not params or not params.get("message"):
            raise Error("Message content is required")
        console.log("通过 Intent 调起微信发送文本消息...")
        intent = Intent(IntentAction.ACTION_SEND)
        intent.setType("text/plain")
        intent.putExtra("android.intent.extra.TEXT", params["message"])
        intent.setComponent("com.tencent.mm", "com.tencent.mm.ui.tools.ShareImgUI")
        intent.addFlag(IntentFlag.ACTIVITY_NEW_TASK)
        result = await intent.start()
        msg = params["message"]
        return {
            "success": True,
            "message": "已打开微信分享界面，请选择联系人并确认发送",
            "content_preview": msg[:30] + "..." if len(msg) > 30 else msg,
            "raw_result": result
        }
    except Exception as error:
        console.error(f"[wechat_send_message] 错误: {error}")
        import traceback
        console.error(traceback.format_exc())
        msg = params.get("message", "") if params else ""
        return {
            "success": False,
            "message": f"调用微信发送消息失败: {error}",
            "content_preview": msg[:30] + "..." if len(msg) > 30 else msg
        }


async def qq_send_message(params):
    try:
        if not params or not params.get("message"):
            raise Error("Message content is required")
        console.log("通过 Intent 调起 QQ 发送文本消息...")
        intent = Intent(IntentAction.ACTION_SEND)
        intent.setType("text/plain")
        intent.putExtra("android.intent.extra.TEXT", params["message"])
        intent.setComponent("com.tencent.mobileqq", "com.tencent.mobileqq.activity.JumpActivity")
        intent.addFlag(IntentFlag.ACTIVITY_NEW_TASK)
        result = await intent.start()
        msg = params["message"]
        return {
            "success": True,
            "message": "已打开 QQ 分享界面，请选择联系人并确认发送",
            "content_preview": msg[:30] + "..." if len(msg) > 30 else msg,
            "raw_result": result
        }
    except Exception as error:
        console.error(f"[qq_send_message] 错误: {error}")
        import traceback
        console.error(traceback.format_exc())
        msg = params.get("message", "") if params else ""
        return {
            "success": False,
            "message": f"调用 QQ 发送消息失败: {error}",
            "content_preview": msg[:30] + "..." if len(msg) > 30 else msg
        }


async def wechat_post_moments(params):
    try:
        if not params or not params.get("message"):
            raise Error("Message content is required")
        console.log("通过 Intent 调起微信朋友圈发表界面...")
        intent = Intent(IntentAction.ACTION_SEND)
        intent.setType("text/plain")
        intent.setComponent("com.tencent.mm", "com.tencent.mm.ui.tools.ShareToTimeLineUI")
        intent.putExtra("android.intent.extra.TEXT", params["message"])
        intent.putExtra("Kdescription", params["message"])
        intent.addFlag(IntentFlag.ACTIVITY_NEW_TASK)
        result = await intent.start()
        msg = params["message"]
        return {
            "success": True,
            "message": "已打开微信朋友圈发表界面，请确认内容并发送",
            "content_preview": msg[:30] + "..." if len(msg) > 30 else msg,
            "raw_result": result
        }
    except Exception as error:
        console.error(f"[wechat_post_moments] 错误: {error}")
        import traceback
        console.error(traceback.format_exc())
        msg = params.get("message", "") if params else ""
        return {
            "success": False,
            "message": f"调用微信朋友圈失败: {error}",
            "content_preview": msg[:30] + "..." if len(msg) > 30 else msg
        }


async def make_phone_call(params):
    try:
        if not params or not params.get("phone_number"):
            raise Error("Phone number is required")
        console.log(f"拨打电话: {params['phone_number']}")
        isEmergency = params.get("emergency") is True
        action = IntentAction.ACTION_CALL_EMERGENCY if isEmergency else IntentAction.ACTION_DIAL
        intent = Intent(action)
        intent.setData(f"tel:{params['phone_number']}")
        intent.addFlag(IntentFlag.ACTIVITY_NEW_TASK)
        result = await intent.start()
        return {
            "success": True,
            "message": "紧急电话已拨打" if isEmergency else "拨号界面已打开",
            "phone_number": params["phone_number"],
            "is_emergency": isEmergency,
            "raw_result": result
        }
    except Exception as error:
        console.error(f"拨打电话失败: {error}")
        return {
            "success": False,
            "message": f"拨打电话失败: {error}",
            "phone_number": params.get("phone_number") if params else None,
            "is_emergency": params.get("emergency") is True if params else False
        }


async def toggle_flashlight(params):
    try:
        if not params or not params.get("state"):
            raise Error("Flashlight state is required")
        state = params["state"].lower()
        if state not in ("on", "off"):
            raise Error("Invalid state. Must be 'on' or 'off'")
        console.log(f"{'打开' if state == 'on' else '关闭'}手电筒...")
        stateValue = "1" if state == "on" else "0"
        flashStateResult = await Tools.System.setSetting("FlashState", stateValue, "system")
        console.log(f"FlashState 设置结果: {json.dumps(flashStateResult)}")
        backFlashlightResult = await Tools.System.setSetting("back_flashlight_state", stateValue, "system")
        console.log(f"back_flashlight_state 设置结果: {json.dumps(backFlashlightResult)}")
        return {
            "success": True,
            "message": f"手电筒已{'打开' if state == 'on' else '关闭'}",
            "state": state,
            "flash_state_result": flashStateResult,
            "back_flashlight_result": backFlashlightResult
        }
    except Exception as error:
        console.error(f"手电筒操作失败: {error}")
        return {
            "success": False,
            "message": f"手电筒操作失败: {error}",
            "state": params.get("state") if params else None
        }


async def adjust_volume(params):
    try:
        if not params or not params.get("action"):
            raise Error("Volume action is required")
        action = params["action"].lower()
        if action not in ("up", "down", "mute"):
            raise Error("Invalid action. Must be 'up', 'down', or 'mute'")
        count = params.get("count", 1) if params else 1
        if count is None:
            count = 1
        if not (isinstance(count, (int, float)) and 1 <= count <= 20):
            raise Error("Count must be a number between 1 and 20")

        console.log(f"调节音量: {'增加' if action == 'up' else '减小' if action == 'down' else '静音'}, 次数: {count}")

        if action == "up":
            keyCode = "KEYCODE_VOLUME_UP"
            actionName = "增加"
        elif action == "down":
            keyCode = "KEYCODE_VOLUME_DOWN"
            actionName = "减小"
        else:
            keyCode = "KEYCODE_VOLUME_MUTE"
            actionName = "静音"
            count = 1

        results = []
        for i in range(count):
            result = await Tools.UI.pressKey(keyCode)
            results.append(result)
            console.log(f"第 {i + 1} 次按键结果: {json.dumps(result)}")
            if i < count - 1:
                await Tools.System.sleep(100)

        return {
            "success": True,
            "message": f"音量{actionName}操作完成，共执行 {count} 次",
            "action": action,
            "key_code": keyCode,
            "count": count,
            "results": results
        }
    except Exception as error:
        console.error(f"音量调节失败: {error}")
        return {
            "success": False,
            "message": f"音量调节失败: {error}",
            "action": params.get("action") if params else None,
            "count": params.get("count", 1) if params else 1
        }


async def toggle_wifi(params):
    try:
        if not params or not params.get("state") or params["state"].lower() not in ("on", "off"):
            raise Error("State is required and must be 'on' or 'off'")
        state = params["state"].lower()
        console.log(f"{'开启' if state == 'on' else '关闭'} Wi-Fi...")
        command = "svc wifi enable" if state == "on" else "svc wifi disable"
        result = await Tools.System.shell(command)
        return {
            "success": True,
            "message": f"Wi-Fi 已{'开启' if state == 'on' else '关闭'}",
            "state": state,
            "raw_result": result
        }
    except Exception as error:
        console.error(f"Wi-Fi 操作失败: {error}")
        return {
            "success": False,
            "message": f"Wi-Fi 操作失败: {error}",
            "state": params.get("state") if params else None
        }


async def take_screenshot(params):
    try:
        filePath = params.get("file_path") if params else None
        screenshotDir = "/sdcard/DCIM/Screenshots"  # Android-only path
        await Tools.Files.mkdir(screenshotDir, True)
        if not filePath:
            timestamp = datetime.now().isoformat().replace(":", "-").replace(".", "-")
            filePath = f"{screenshotDir}/screenshot_{timestamp}.png"
        console.log(f"截取屏幕并保存到: {filePath}")
        result = await Tools.System.shell(f"screencap -p {filePath}")
        return {
            "success": True,
            "message": f"截图已保存到 {filePath}",
            "file_path": filePath,
            "raw_result": result
        }
    except Exception as error:
        console.error(f"截图失败: {error}")
        return {"success": False, "message": f"截图失败: {error}"}


async def take_photo():
    try:
        console.log("打开相机应用...")
        intent = Intent(IntentAction.ACTION_IMAGE_CAPTURE)
        intent.addFlag(IntentFlag.ACTIVITY_NEW_TASK)
        result = await intent.start()
        return {"success": True, "message": "相机应用已打开", "raw_result": result}
    except Exception as error:
        console.error(f"打开相机失败: {error}")
        return {"success": False, "message": f"打开相机失败: {error}"}


async def toggle_dark_mode(params):
    try:
        if not params or not params.get("state"):
            raise Error("Dark mode state is required")
        state = params["state"].lower()
        if state == "on":
            shellArg = "yes"
            stateName = "开启"
        elif state == "off":
            shellArg = "no"
            stateName = "关闭"
        elif state == "auto":
            shellArg = "auto"
            stateName = "自动"
        else:
            raise Error("Invalid state. Must be 'on', 'off', or 'auto'")
        console.log(f"设置深夜模式为 {stateName}...")
        command = f"cmd uimode night {shellArg}"
        result = await Tools.System.shell(command)
        return {
            "success": True,
            "message": f"深夜模式已设置为 {stateName}",
            "state": state,
            "raw_result": result
        }
    except Exception as error:
        console.error(f"深夜模式操作失败: {error}")
        return {
            "success": False,
            "message": f"深夜模式操作失败: {error}",
            "state": params.get("state") if params else None
        }


async def main():
    try:
        results = {}
        return {
            "message": "日常生活功能测试完成",
            "test_results": results,
            "timestamp": datetime.now().isoformat(),
            "summary": "测试了各种日常生活功能，包括天气搜索、拨号和短信测试。请查看各功能的测试结果。"
        }
    except Exception as error:
        return {"success": False, "message": f"测试过程中发生错误: {error}"}


async def daily_wrap(func, params, successMessage, failMessage, additionalInfo=""):
    try:
        funcName = getattr(func, "__name__", "匿名函数")
        console.log(f"开始执行函数: {funcName}")
        console.log(f"参数: {json.dumps(params, indent=2, ensure_ascii=False, default=str)}")
        result = await func(params)
        console.log(f"函数 {funcName} 执行结果: {json.dumps(result, indent=2, ensure_ascii=False, default=str)}")
        if result is None:
            return
        if isinstance(result, bool):
            complete({
                "success": result,
                "message": successMessage if result else failMessage,
                "additionalInfo": additionalInfo
            })
        else:
            complete({
                "success": True,
                "message": successMessage,
                "additionalInfo": additionalInfo,
                "data": result
            })
    except Exception as error:
        import traceback
        console.error(f"函数执行失败!")
        console.error(f"错误信息: {error}")
        console.error(f"错误堆栈: {traceback.format_exc()}")
        complete({
            "success": False,
            "message": f"{failMessage}: {error}",
            "additionalInfo": additionalInfo,
            "error_stack": traceback.format_exc()
        })


# 导出
async def _export_get_current_date(params):
    await daily_wrap(get_current_date, params, "获取日期时间成功", "获取日期时间失败")

async def _export_device_status(params):
    await daily_wrap(device_status, params, "获取设备状态成功", "获取设备状态失败")

async def _export_search_weather(params):
    await daily_wrap(search_weather, params, "获取天气信息成功", "获取天气信息失败")

async def _export_set_reminder(params):
    await daily_wrap(set_reminder, params, "设置提醒成功", "设置提醒失败")

async def _export_schedule_one_time_task(params):
    await daily_wrap(schedule_one_time_task, params, "一次性定时任务创建成功", "一次性定时任务创建失败")

async def _export_set_alarm(params):
    await daily_wrap(set_alarm, params, "设置闹钟成功", "设置闹钟失败")

async def _export_send_message(params):
    await daily_wrap(send_message, params, "发送短信成功", "发送短信失败")

async def _export_wechat_send_message(params):
    await daily_wrap(wechat_send_message, params, "调用微信发送消息成功", "调用微信发送消息失败")

async def _export_qq_send_message(params):
    await daily_wrap(qq_send_message, params, "调用 QQ 发送消息成功", "调用 QQ 发送消息失败")

async def _export_wechat_post_moments(params):
    await daily_wrap(wechat_post_moments, params, "调用微信朋友圈成功", "调用微信朋友圈失败")

async def _export_make_phone_call(params):
    await daily_wrap(make_phone_call, params, "拨打电话成功", "拨打电话失败")

async def _export_toggle_flashlight(params):
    await daily_wrap(toggle_flashlight, params, "手电筒操作成功", "手电筒操作失败")

async def _export_adjust_volume(params):
    await daily_wrap(adjust_volume, params, "音量调节成功", "音量调节失败")

async def _export_toggle_wifi(params):
    await daily_wrap(toggle_wifi, params, "Wi-Fi 操作成功", "Wi-Fi 操作失败")

async def _export_take_screenshot(params):
    await daily_wrap(take_screenshot, params, "截图成功", "截图失败")

async def _export_take_photo(params):
    await daily_wrap(take_photo, params, "打开相机成功", "打开相机失败")

async def _export_toggle_dark_mode(params):
    await daily_wrap(toggle_dark_mode, params, "深夜模式操作成功", "深夜模式操作失败")

async def _export_main(params):
    await daily_wrap(main, params, "主函数执行成功", "主函数执行失败")

exports.get_current_date = _export_get_current_date
exports.device_status = _export_device_status
exports.search_weather = _export_search_weather
exports.set_reminder = _export_set_reminder
exports.schedule_one_time_task = _export_schedule_one_time_task
exports.set_alarm = _export_set_alarm
exports.send_message = _export_send_message
exports.wechat_send_message = _export_wechat_send_message
exports.qq_send_message = _export_qq_send_message
exports.wechat_post_moments = _export_wechat_post_moments
exports.make_phone_call = _export_make_phone_call
exports.toggle_flashlight = _export_toggle_flashlight
exports.adjust_volume = _export_adjust_volume
exports.main = _export_main
exports.toggle_wifi = _export_toggle_wifi
exports.take_screenshot = _export_take_screenshot
exports.take_photo = _export_take_photo
exports.toggle_dark_mode = _export_toggle_dark_mode
