# METADATA
# {
#     "name": "system_info",
#     "display_name": {
#         "zh": "系统信息查看器",
#         "en": "System Info Viewer"
#     },
#     "description": {
#         "zh": "通过 Android API 转译层获取系统信息：存储目录、构建信息、平台环境，并用 Log 输出日志。",
#         "en": "Get system info via Android API translation layer: storage dirs, build info, platform. Log via android.util.Log."
#     },
#     "category": "System",
#     "tools": [
#         {
#             "name": "get_info",
#             "description": {
#                 "zh": "获取系统信息",
#                 "en": "Get system info"
#             },
#             "parameters": []
#         }
#     ]
# }

import platform
import sys

TAG = "SystemInfo"


def getErrorMessage(error):
    return str(error) if error else "unknown"


def getErrorStack(error):
    return traceback.format_exc()


async def wrap(func, params):
    try:
        result = await func(params)
        complete({"success": True, "message": "操作成功", "data": result})
    except Exception as error:
        console.error(f"Error: {getErrorMessage(error)}")
        complete({"success": False, "message": getErrorMessage(error), "error_stack": getErrorStack(error)})


async def get_info(params):
    """通过 Android API 转译层采集系统信息"""
    try:
        info = {
            "storage_external": Environment.getExternalStorageDirectory(),
            "storage_data": Environment.getDataDirectory(),
            "storage_root": Environment.getRootDirectory(),
            "storage_public_pictures": Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES),
            "build_brand": getattr(Build, "BRAND", "unknown"),
            "build_model": getattr(Build, "MODEL", "unknown"),
            "build_version": getattr(Build, "VERSION", {}).get("RELEASE", "unknown") if isinstance(getattr(Build, "VERSION", {}), dict) else "unknown",
            "os_name": os.name,
            "sys_platform": sys.platform,
            "python_version": platform.python_version(),
            "python_platform": platform.platform(),
            "sdcard_mounted": Environment.getExternalStorageState() == Environment.MEDIA_MOUNTED,
        }
        Log.i(TAG, f"采集完成: external={info['storage_external']}")
        complete({"success": True, "message": "系统信息采集完成", "data": info})
        return info
    except Exception as error:
        console.error(f"{TAG} 错误: {getErrorMessage(error)}")
        complete({"success": False, "message": f"采集失败: {getErrorMessage(error)}", "error_stack": getErrorStack(error)})
        raise


async def get_info_wrapper(params):
    await wrap(get_info, params)


exports.get_info = get_info_wrapper
