# METADATA
# {
#   name: time
#
#   display_name: {
#     zh: "时间"
#     en: "Time"
#   }
#   description: {
#     zh: "提供时间相关功能。实际上，激活本包的同时已经能够获取时间了。"
#     en: "Provides time-related utilities. In practice, current time is already available once this package is enabled."
#   }
#   enabledByDefault: true
#   category: "Utility"
#   tools: [
#     {
#       name: get_time
#       description: {
#         zh: "获取当前时间。当使用此包时，AI已经自动获取了当前的时间信息。"
#         en: "Get the current time. When using this package, the AI may already have the current time context."
#       }
#       parameters: []
#     },
#     {
#       name: format_time
#       description: {
#         zh: "格式化时间。提供各种时间格式化选项。"
#         en: "Format time. Provides various time formatting options."
#       }
#       parameters: []
#     }
#   ]
# }

import time
import datetime


async def get_time():
    now = datetime.datetime.now()

    return {
        "timestamp": int(time.time() * 1000),
        "iso": now.isoformat(),
        "local": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": {
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "weekday": now.strftime("%A")
        },
        "time": {
            "hours": now.hour,
            "minutes": now.minute,
            "seconds": now.second
        }
    }


async def format_time():
    now = datetime.datetime.now()

    def pad(n):
        return str(n).zfill(2)

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
        "time12h": time12h
    }


exports.get_time = get_time
exports.format_time = format_time
