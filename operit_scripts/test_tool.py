# METADATA
# {
#     "name": "test_tool",
#     "display_name": {"zh": "测试工具", "en": "Test Tool"},
#     "description": {"zh": "测试 operit_loader 转译层", "en": "Test operit_loader translation layer"},
#     "enabledByDefault": true,
#     "category": "Utility",
#     "tools": [
#         {"name": "echo", "description": {"zh": "回显消息", "en": "Echo message"}, "parameters": [
#             {"name": "message", "description": {"zh": "消息内容", "en": "Message content"}, "type": "string", "required": true}
#         ]},
#         {"name": "get_device_info", "description": {"zh": "获取设备信息", "en": "Get device info"}, "parameters": []}
#     ]
# }

import os
import json

async def echo(params):
    message = params.get("message", "hello")
    return {"success": True, "message": f"Echo: {message}"}

async def get_device_info(params):
    result = await Tools.System.getDeviceInfo()
    return result

exports["echo"] = echo
exports["get_device_info"] = get_device_info
