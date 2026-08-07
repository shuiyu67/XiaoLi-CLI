# METADATA
# {
#     "name": "market_time",
#     "display_name": {
#         "zh": "时间(市场插件翻译)",
#         "en": "Time (translated from operit market)"
#     },
#     "description": {
#         "zh": "从 operit 市场 time.ts 忠实翻译：获取/格式化当前时间。",
#         "en": "Faithful translation of operit market time.ts: get/format current time."
#     },
#     "category": "Utility",
#     "tools": [
#         {
#             "name": "get_time",
#             "description": {
#                 "zh": "获取当前时间各字段",
#                 "en": "Get current time fields"
#             },
#             "parameters": []
#         },
#         {
#             "name": "format_time",
#             "description": {
#                 "zh": "格式化当前时间为 24h/12h 字符串",
#                 "en": "Format current time as 24h/12h strings"
#             },
#             "parameters": []
#         }
#     ]
# }

import datetime


def getErrorMessage(error):
    return str(error) if error else "unknown"


def getErrorStack(error):
    import traceback
    return traceback.format_exc()


async def wrap(func, params, ok_msg="操作成功", err_msg="操作失败"):
    try:
        result = await func(params)
        complete({"success": True, "message": ok_msg, "data": result})
    except Exception as error:
        console.error(f"Error: {getErrorMessage(error)}")
        complete({"success": False, "message": getErrorMessage(error), "error_stack": getErrorStack(error)})


async def get_time(params):
    """获取当前时间各字段（忠实于 time.ts get_time）"""
    now = datetime.datetime.now()
    return {
        "timestamp": int(now.timestamp() * 1000),
        "iso": now.isoformat(),
        "local": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": {
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "weekday": now.strftime("%A"),
        },
        "time": {
            "hours": now.hour,
            "minutes": now.minute,
            "seconds": now.second,
        },
    }


async def format_time(params):
    """格式化当前时间为 24h/12h 字符串（忠实于 time.ts format_time）"""
    now = datetime.datetime.now()
    pad = lambda n: str(n).zfill(2)
    hours = now.hour
    minutes = now.minute
    seconds = now.second
    time24h = f"{pad(hours)}:{pad(minutes)}:{pad(seconds)}"
    suffix = "PM" if hours >= 12 else "AM"
    hour12 = 12 if hours % 12 == 0 else hours % 12
    time12h = f"{pad(hour12)}:{pad(minutes)}:{pad(seconds)} {suffix}"
    return {
        "iso": now.isoformat(),
        "date": f"{now.year}-{pad(now.month)}-{pad(now.day)}",
        "time24h": time24h,
        "time12h": time12h,
    }


async def get_time_wrapper(params):
    await wrap(get_time, params, "时间获取完成", "时间获取失败")


async def format_time_wrapper(params):
    await wrap(format_time, params, "时间格式化完成", "时间格式化失败")


exports.get_time = get_time_wrapper
exports.format_time = format_time_wrapper
