# METADATA
# {
#   "name": "tasker",
#
#   "display_name": {
#       "zh": "Tasker 触发器",
#       "en": "Tasker Trigger"
#   },
#   "description": {
#       "zh": "集成 Tasker 插件事件触发工具，通过本包可向 Tasker 发送事件。",
#       "en": "Integration for triggering Tasker plugin events. This package lets you send events to Tasker."
#   },
#   "enabledByDefault": false,
#   "category": "Workflow",
#   "tools": [
#     {
#       "name": "trigger_tasker_event",
#       "description": {
#         "zh": "触发一个 Tasker 事件。使用 task_type 指定事件类型，可传 arg1..arg5 或 args_json。",
#         "en": "Trigger a Tasker event. Use task_type to specify the event type. You can pass arg1..arg5 or args_json."
#       },
#       "parameters": [
#         { "name": "task_type", "description": { "zh": "事件类型标识", "en": "Event type identifier" }, "type": "string", "required": true },
#         { "name": "arg1", "description": { "zh": "可选参数1", "en": "Optional argument 1" }, "type": "string", "required": false },
#         { "name": "arg2", "description": { "zh": "可选参数2", "en": "Optional argument 2" }, "type": "string", "required": false },
#         { "name": "arg3", "description": { "zh": "可选参数3", "en": "Optional argument 3" }, "type": "string", "required": false },
#         { "name": "arg4", "description": { "zh": "可选参数4", "en": "Optional argument 4" }, "type": "string", "required": false },
#         { "name": "arg5", "description": { "zh": "可选参数5", "en": "Optional argument 5" }, "type": "string", "required": false },
#         { "name": "args_json", "description": { "zh": "以JSON形式传递任意参数", "en": "Pass arbitrary parameters as a JSON string" }, "type": "string", "required": false }
#       ]
#     }
#   ]
# }


async def trigger_tasker_event(params):
    data = await Tools.Tasker.triggerEvent(params)
    return {
        "success": True,
        "message": "Tasker 事件已触发",
        "data": data
    }


async def wrapToolExecution(func, params=None):
    try:
        result = await func(params if params is not None else {})
        complete(result)
    except Exception as error:
        console.error(f"Tool {func.__name__} failed unexpectedly", error)
        msg = str(getattr(error, "message", error))
        complete({"success": False, "message": msg})


async def trigger_tasker_event_wrapper(params=None):
    await wrapToolExecution(trigger_tasker_event, params)


exports.trigger_tasker_event = trigger_tasker_event_wrapper
