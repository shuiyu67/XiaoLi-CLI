# METADATA
# {
#     "name": "system_tools",
#     "display_name": {"zh": "系统工具", "en": "System Tools"},
#     "description": {"zh": "提供系统级操作工具，包括设置管理、应用安装卸载与启动、通知获取、位置服务、设备信息查询，以及 Intent/广播调用。", "en": "System-level operations: settings management, app install/uninstall & launch, notification retrieval, location services, device info queries, plus Intent/broadcast execution."},
#     "enabledByDefault": True,
#     "category": "System",
#     "tools": [
#         {"name": "get_system_setting", "description": {"zh": "获取系统设置的值。需要用户授权。", "en": "Get the value of a system setting. Requires user authorization."}, "parameters": [
#             {"name": "setting", "description": {"zh": "设置名称", "en": "Setting key/name"}, "type": "string", "required": True},
#             {"name": "namespace", "description": {"zh": "命名空间：system/secure/global，默认system", "en": "Namespace: system/secure/global (default: system)"}, "type": "string", "required": False}
#         ]},
#         {"name": "modify_system_setting", "description": {"zh": "修改系统设置的值。需要用户授权。", "en": "Modify the value of a system setting. Requires user authorization."}, "parameters": [
#             {"name": "setting", "description": {"zh": "设置名称", "en": "Setting key/name"}, "type": "string", "required": True},
#             {"name": "value", "description": {"zh": "设置值", "en": "Setting value"}, "type": "string", "required": True},
#             {"name": "namespace", "description": {"zh": "命名空间：system/secure/global，默认system", "en": "Namespace: system/secure/global (default: system)"}, "type": "string", "required": False}
#         ]},
#         {"name": "install_app", "description": {"zh": "安装应用程序。需要用户授权。", "en": "Install an app. Requires user authorization."}, "parameters": [
#             {"name": "path", "description": {"zh": "APK文件路径", "en": "APK file path"}, "type": "string", "required": True}
#         ]},
#         {"name": "uninstall_app", "description": {"zh": "卸载应用程序。需要用户授权。", "en": "Uninstall an app. Requires user authorization."}, "parameters": [
#             {"name": "package_name", "description": {"zh": "应用包名", "en": "App package name"}, "type": "string", "required": True},
#             {"name": "keep_data", "description": {"zh": "是否保留数据，默认false", "en": "Whether to keep app data (default: false)"}, "type": "boolean", "required": False}
#         ]},
#         {"name": "list_installed_apps", "description": {"zh": "获取已安装应用程序列表。需要用户授权。", "en": "List installed apps. Requires user authorization."}, "parameters": [
#             {"name": "include_system_apps", "description": {"zh": "是否包含系统应用，默认false", "en": "Whether to include system apps (default: false)"}, "type": "boolean", "required": False}
#         ]},
#         {"name": "start_app", "description": {"zh": "启动应用程序。需要用户授权。", "en": "Launch an app. Requires user authorization."}, "parameters": [
#             {"name": "package_name", "description": {"zh": "应用包名", "en": "App package name"}, "type": "string", "required": True},
#             {"name": "activity", "description": {"zh": "可选活动名称", "en": "Optional activity name"}, "type": "string", "required": False}
#         ]},
#         {"name": "stop_app", "description": {"zh": "停止正在运行的应用程序。需要用户授权。", "en": "Force stop a running app. Requires user authorization."}, "parameters": [
#             {"name": "package_name", "description": {"zh": "应用包名", "en": "App package name"}, "type": "string", "required": True}
#         ]},
#         {"name": "send_broadcast", "description": {"zh": "发送广播（Broadcast Intent）。需要用户授权。", "en": "Send a broadcast (Broadcast Intent). Requires user authorization."}, "parameters": [
#             {"name": "action", "description": {"zh": "Intent action，例如 android.intent.action.VIEW", "en": "Intent action, e.g. android.intent.action.VIEW"}, "type": "string", "required": True},
#             {"name": "package_name", "description": {"zh": "可选：限制广播目标包名", "en": "Optional: restrict target package"}, "type": "string", "required": False},
#             {"name": "component", "description": {"zh": "可选：组件名 package/class，优先于package_name", "en": "Optional: component package/class, takes priority over package_name"}, "type": "string", "required": False},
#             {"name": "uri", "description": {"zh": "可选：data uri", "en": "Optional: data uri"}, "type": "string", "required": False},
#             {"name": "extras", "description": {"zh": "可选：extras（对象，可用于传参）", "en": "Optional: extras (object for parameters)"}, "type": "object", "required": False}
#         ]},
#         {"name": "execute_intent", "description": {"zh": "执行 Intent（Activity/Service/Broadcast），支持 extras 传参。需要用户授权。", "en": "Execute an Intent (Activity/Service/Broadcast) with extras parameters. Requires user authorization."}, "parameters": [
#             {"name": "type", "description": {"zh": "类型：activity/broadcast/service，默认activity", "en": "Type: activity/broadcast/service (default: activity)"}, "type": "string", "required": False},
#             {"name": "action", "description": {"zh": "Intent action（action 或 component 至少一个必填）", "en": "Intent action (either action or component is required)"}, "type": "string", "required": False},
#             {"name": "package_name", "description": {"zh": "可选：包名", "en": "Optional: package name"}, "type": "string", "required": False},
#             {"name": "component", "description": {"zh": "可选：组件名 package/class", "en": "Optional: component package/class"}, "type": "string", "required": False},
#             {"name": "uri", "description": {"zh": "可选：data uri", "en": "Optional: data uri"}, "type": "string", "required": False},
#             {"name": "flags", "description": {"zh": "可选：flags（整数或JSON数组字符串）", "en": "Optional: flags (integer or JSON array string)"}, "type": "string", "required": False},
#             {"name": "extras", "description": {"zh": "可选：extras（对象，可用于传参）", "en": "Optional: extras (object for parameters)"}, "type": "object", "required": False}
#         ]},
#         {"name": "get_notifications", "description": {"zh": "获取设备通知内容。", "en": "Retrieve device notifications."}, "parameters": [
#             {"name": "limit", "description": {"zh": "最大返回条数，默认10", "en": "Max number of entries to return (default: 10)"}, "type": "number", "required": False},
#             {"name": "include_ongoing", "description": {"zh": "是否包含常驻通知，默认false", "en": "Whether to include ongoing notifications (default: false)"}, "type": "boolean", "required": False}
#         ]},
#         {"name": "get_app_usage_time", "description": {"zh": "获取应用前台使用时长。需要授予"使用情况访问权限"。", "en": "Get app foreground usage time. Requires Usage Access permission."}, "parameters": [
#             {"name": "package_name", "description": {"zh": "可选：精确应用包名", "en": "Optional exact package name"}, "type": "string", "required": False},
#             {"name": "since_hours", "description": {"zh": "向前统计多少小时，默认24", "en": "How many hours to look back (default: 24)"}, "type": "number", "required": False},
#             {"name": "limit", "description": {"zh": "不传包名时最多返回多少个应用，默认10", "en": "Max apps to return when package_name is omitted (default: 10)"}, "type": "number", "required": False},
#             {"name": "include_system_apps", "description": {"zh": "不传包名时是否包含系统应用，默认false", "en": "Whether to include system apps when package_name is omitted (default: false)"}, "type": "boolean", "required": False}
#         ]},
#         {"name": "get_device_location", "description": {"zh": "获取设备当前位置信息。", "en": "Get current device location."}, "parameters": [
#             {"name": "high_accuracy", "description": {"zh": "是否使用高精度模式，默认false", "en": "Use high accuracy mode (default: false)"}, "type": "boolean", "required": False},
#             {"name": "timeout", "description": {"zh": "超时时间（秒），默认10", "en": "Timeout in seconds (default: 10)"}, "type": "number", "required": False}
#         ]},
#         {"name": "request_bluetooth_permission", "description": {"zh": "请求蓝牙附近设备权限。", "en": "Request Bluetooth nearby devices permission."}, "parameters": []},
#         {"name": "get_bluetooth_state", "description": {"zh": "获取蓝牙适配器状态。", "en": "Get Bluetooth adapter state."}, "parameters": []},
#         {"name": "request_enable_bluetooth", "description": {"zh": "打开系统蓝牙开启对话框。", "en": "Open the system dialog to enable Bluetooth."}, "parameters": []},
#         {"name": "list_bluetooth_bonded_devices", "description": {"zh": "列出已配对蓝牙设备。", "en": "List bonded Bluetooth devices."}, "parameters": []},
#         {"name": "scan_bluetooth_devices", "description": {"zh": "扫描附近蓝牙 Classic 与 BLE 设备。", "en": "Scan nearby Bluetooth classic and BLE devices."}, "parameters": [
#             {"name": "duration_ms", "description": {"zh": "扫描时长毫秒。", "en": "Scan duration in milliseconds."}, "type": "number", "required": False},
#             {"name": "include_ble", "description": {"zh": "是否包含 BLE 扫描。", "en": "Whether to include BLE scanning."}, "type": "boolean", "required": False}
#         ]},
#         {"name": "bluetooth_connect", "description": {"zh": "连接蓝牙 Classic 设备。", "en": "Connect to a Bluetooth classic device."}, "parameters": [
#             {"name": "address", "description": {"zh": "蓝牙 MAC 地址", "en": "Bluetooth MAC address"}, "type": "string", "required": True},
#             {"name": "uuid", "description": {"zh": "RFCOMM UUID。", "en": "RFCOMM UUID."}, "type": "string", "required": False}
#         ]},
#         {"name": "bluetooth_listen", "description": {"zh": "监听别人连接本机的蓝牙 Classic 通道。", "en": "Listen for another device connecting to this phone over Bluetooth classic."}, "parameters": [
#             {"name": "name", "description": {"zh": "服务名。", "en": "Service name."}, "type": "string", "required": False},
#             {"name": "uuid", "description": {"zh": "RFCOMM UUID。", "en": "RFCOMM UUID."}, "type": "string", "required": False}
#         ]},
#         {"name": "bluetooth_accept", "description": {"zh": "接受蓝牙 Classic 监听会话中的一个传入连接。", "en": "Accept one incoming connection from a Bluetooth classic listener."}, "parameters": [
#             {"name": "listener_session_id", "description": {"zh": "监听会话 ID", "en": "Listener session ID"}, "type": "string", "required": True},
#             {"name": "timeout_ms", "description": {"zh": "等待毫秒数。", "en": "Wait time in milliseconds."}, "type": "number", "required": False}
#         ]},
#         {"name": "bluetooth_send", "description": {"zh": "向蓝牙 Classic 会话发送文本或 base64 字节。", "en": "Send text or base64 bytes to a Bluetooth classic session."}, "parameters": [
#             {"name": "session_id", "description": {"zh": "会话 ID", "en": "Session ID"}, "type": "string", "required": True},
#             {"name": "text", "description": {"zh": "UTF-8 文本", "en": "UTF-8 text"}, "type": "string", "required": False},
#             {"name": "data_base64", "description": {"zh": "base64 字节", "en": "Base64 bytes"}, "type": "string", "required": False}
#         ]},
#         {"name": "bluetooth_read", "description": {"zh": "从蓝牙 Classic 会话读取文本或字节。", "en": "Read text or bytes from a Bluetooth classic session."}, "parameters": [
#             {"name": "session_id", "description": {"zh": "会话 ID", "en": "Session ID"}, "type": "string", "required": True},
#             {"name": "max_bytes", "description": {"zh": "最大读取字节数。", "en": "Maximum bytes to read."}, "type": "number", "required": False},
#             {"name": "timeout_ms", "description": {"zh": "等待毫秒数。", "en": "Wait time in milliseconds."}, "type": "number", "required": False}
#         ]},
#         {"name": "bluetooth_send_and_read", "description": {"zh": "向蓝牙 Classic 会话发送后读取响应。", "en": "Send to a Bluetooth classic session and read the response."}, "parameters": [
#             {"name": "session_id", "description": {"zh": "会话 ID", "en": "Session ID"}, "type": "string", "required": True},
#             {"name": "text", "description": {"zh": "UTF-8 文本", "en": "UTF-8 text"}, "type": "string", "required": False},
#             {"name": "data_base64", "description": {"zh": "base64 字节", "en": "Base64 bytes"}, "type": "string", "required": False},
#             {"name": "max_bytes", "description": {"zh": "最大读取字节数。", "en": "Maximum bytes to read."}, "type": "number", "required": False},
#             {"name": "timeout_ms", "description": {"zh": "等待毫秒数。", "en": "Wait time in milliseconds."}, "type": "number", "required": False}
#         ]},
#         {"name": "bluetooth_close", "description": {"zh": "关闭蓝牙 Classic、监听或 BLE 会话。", "en": "Close a Bluetooth classic, listener, or BLE session."}, "parameters": [
#             {"name": "session_id", "description": {"zh": "会话 ID", "en": "Session ID"}, "type": "string", "required": True}
#         ]},
#         {"name": "bluetooth_ble_connect", "description": {"zh": "连接 BLE 设备。", "en": "Connect to a BLE device."}, "parameters": [
#             {"name": "address", "description": {"zh": "蓝牙 MAC 地址", "en": "Bluetooth MAC address"}, "type": "string", "required": True},
#             {"name": "auto_connect", "description": {"zh": "是否自动连接。", "en": "Whether to use auto connect."}, "type": "boolean", "required": False}
#         ]},
#         {"name": "bluetooth_ble_discover_services", "description": {"zh": "发现 BLE 服务和 characteristic。", "en": "Discover BLE services and characteristics."}, "parameters": [
#             {"name": "session_id", "description": {"zh": "BLE 会话 ID", "en": "BLE session ID"}, "type": "string", "required": True},
#             {"name": "timeout_ms", "description": {"zh": "等待毫秒数。", "en": "Wait time in milliseconds."}, "type": "number", "required": False}
#         ]},
#         {"name": "bluetooth_ble_read_characteristic", "description": {"zh": "读取 BLE characteristic。", "en": "Read a BLE characteristic."}, "parameters": [
#             {"name": "session_id", "description": {"zh": "BLE 会话 ID", "en": "BLE session ID"}, "type": "string", "required": True},
#             {"name": "service_uuid", "description": {"zh": "Service UUID", "en": "Service UUID"}, "type": "string", "required": True},
#             {"name": "characteristic_uuid", "description": {"zh": "Characteristic UUID", "en": "Characteristic UUID"}, "type": "string", "required": True},
#             {"name": "timeout_ms", "description": {"zh": "等待毫秒数。", "en": "Wait time in milliseconds."}, "type": "number", "required": False}
#         ]},
#         {"name": "bluetooth_ble_write_characteristic", "description": {"zh": "写入 BLE characteristic。", "en": "Write a BLE characteristic."}, "parameters": [
#             {"name": "session_id", "description": {"zh": "BLE 会话 ID", "en": "BLE session ID"}, "type": "string", "required": True},
#             {"name": "service_uuid", "description": {"zh": "Service UUID", "en": "Service UUID"}, "type": "string", "required": True},
#             {"name": "characteristic_uuid", "description": {"zh": "Characteristic UUID", "en": "Characteristic UUID"}, "type": "string", "required": True},
#             {"name": "text", "description": {"zh": "UTF-8 文本", "en": "UTF-8 text"}, "type": "string", "required": False},
#             {"name": "data_base64", "description": {"zh": "base64 字节", "en": "Base64 bytes"}, "type": "string", "required": False}
#         ]},
#         {"name": "bluetooth_ble_write_and_read_characteristic", "description": {"zh": "写入 BLE characteristic 后读取另一个 characteristic 响应。", "en": "Write a BLE characteristic and read another characteristic response."}, "parameters": [
#             {"name": "session_id", "description": {"zh": "BLE 会话 ID", "en": "BLE session ID"}, "type": "string", "required": True},
#             {"name": "write_service_uuid", "description": {"zh": "写入 Service UUID", "en": "Write service UUID"}, "type": "string", "required": True},
#             {"name": "write_characteristic_uuid", "description": {"zh": "写入 Characteristic UUID", "en": "Write characteristic UUID"}, "type": "string", "required": True},
#             {"name": "read_service_uuid", "description": {"zh": "读取 Service UUID", "en": "Read service UUID"}, "type": "string", "required": True},
#             {"name": "read_characteristic_uuid", "description": {"zh": "读取 Characteristic UUID", "en": "Read characteristic UUID"}, "type": "string", "required": True},
#             {"name": "text", "description": {"zh": "UTF-8 文本", "en": "UTF-8 text"}, "type": "string", "required": False},
#             {"name": "data_base64", "description": {"zh": "base64 字节", "en": "Base64 bytes"}, "type": "string", "required": False},
#             {"name": "timeout_ms", "description": {"zh": "等待毫秒数。", "en": "Wait time in milliseconds."}, "type": "number", "required": False}
#         ]},
#         {"name": "bluetooth_ble_subscribe_characteristic", "description": {"zh": "订阅或取消订阅 BLE characteristic 通知。", "en": "Subscribe or unsubscribe BLE characteristic notifications."}, "parameters": [
#             {"name": "session_id", "description": {"zh": "BLE 会话 ID", "en": "BLE session ID"}, "type": "string", "required": True},
#             {"name": "service_uuid", "description": {"zh": "Service UUID", "en": "Service UUID"}, "type": "string", "required": True},
#             {"name": "characteristic_uuid", "description": {"zh": "Characteristic UUID", "en": "Characteristic UUID"}, "type": "string", "required": True},
#             {"name": "enable", "description": {"zh": "是否订阅。", "en": "Whether to subscribe."}, "type": "boolean", "required": False}
#         ]},
#         {"name": "bluetooth_ble_read_notifications", "description": {"zh": "读取已收到的 BLE 通知。", "en": "Read received BLE notifications."}, "parameters": [
#             {"name": "session_id", "description": {"zh": "BLE 会话 ID", "en": "BLE session ID"}, "type": "string", "required": True},
#             {"name": "limit", "description": {"zh": "读取条数。", "en": "Number of notifications to read."}, "type": "number", "required": False}
#         ]},
#         {"name": "get_device_info", "description": {"zh": "获取详细的设备信息，包括型号、操作系统版本、内存、存储、网络状态等。", "en": "Get detailed device information, including model, OS version, memory, storage, network status, etc."}, "parameters": []}
#     ]
# }

import json
import re
import time
import math
from urllib.parse import quote, unquote

Error = Exception

# 注意：以下工具大多依赖 Android 系统 API（Tools.System.*）。
# 在非 Android 平台上运行时，运行时会返回"不支持"提示。


async def get_system_setting(params):
    result = await Tools.System.getSetting(params.get("setting"), params.get("namespace") or "system")
    return {"success": True, "message": "成功获取系统设置", "data": result}


async def modify_system_setting(params):
    result = await Tools.System.setSetting(params.get("setting"), params.get("value"), params.get("namespace") or "system")
    success = result and result.value == params.get("value")
    return {"success": success, "message": "成功修改系统设置" if success else "修改系统设置失败", "data": result}


async def install_app(params):
    result = await Tools.System.installApp(params.get("path"))
    return {"success": result.success, "message": "应用安装成功" if result.success else "应用安装失败", "data": result}


async def uninstall_app(params):
    result = await Tools.System.uninstallApp(params.get("package_name"))
    return {"success": result.success, "message": "应用卸载成功" if result.success else "应用卸载失败", "data": result}


async def list_installed_apps(params):
    result = await Tools.System.listApps(params.get("include_system_apps") or False)
    return {"success": True, "message": "成功获取应用列表", "data": result}


async def start_app(params):
    result = await Tools.System.startApp(params.get("package_name"), params.get("activity"))
    return {"success": result.success, "message": "应用启动成功" if result.success else "应用启动失败", "data": result}


async def stop_app(params):
    result = await Tools.System.stopApp(params.get("package_name"))
    return {"success": result.success, "message": "应用停止成功" if result.success else "应用停止失败", "data": result}


async def send_broadcast(params):
    result = await Tools.System.sendBroadcast({
        "action": params.get("action"),
        "uri": params.get("uri"),
        "package": params.get("package_name"),
        "component": params.get("component"),
        "extras": params.get("extras"),
        "extra_key": params.get("extra_key"),
        "extra_value": params.get("extra_value"),
        "extra_key2": params.get("extra_key2"),
        "extra_value2": params.get("extra_value2"),
    })
    return {"success": True, "message": "广播发送成功", "data": result}


async def execute_intent(params):
    flags = params.get("flags")
    if isinstance(flags, list):
        flags = json.dumps(flags)
    result = await Tools.System.intent({
        "action": params.get("action"),
        "uri": params.get("uri"),
        "package": params.get("package_name"),
        "component": params.get("component"),
        "flags": flags,
        "extras": params.get("extras"),
        "type": params.get("type") or "activity",
    })
    return {"success": True, "message": "Intent 执行成功", "data": result}


async def get_notifications(params):
    result = await Tools.System.getNotifications(params.get("limit") or 10, params.get("include_ongoing") or False)
    return {"success": True, "message": "成功获取通知", "data": result}


async def get_app_usage_time(params):
    result = await Tools.System.getAppUsageTime({
        "packageName": params.get("package_name"),
        "sinceHours": params.get("since_hours") or 24,
        "limit": params.get("limit") or 10,
        "includeSystemApps": params.get("include_system_apps") or False,
    })
    return {"success": True, "message": "成功获取应用使用时长", "data": result}


async def get_device_location(params):
    result = await Tools.System.getLocation(params.get("high_accuracy") or False, params.get("timeout") or 10)
    return {"success": True, "message": "成功获取位置信息", "data": result}


async def request_bluetooth_permission(params):
    result = await Tools.System.bluetooth.requestPermission()
    return {"success": True, "message": "成功请求蓝牙权限", "data": result}


async def get_bluetooth_state(params):
    result = await Tools.System.bluetooth.getState()
    return {"success": True, "message": "成功获取蓝牙状态", "data": result}


async def request_enable_bluetooth(params):
    result = await Tools.System.bluetooth.requestEnable()
    return {"success": True, "message": "已打开蓝牙开启请求", "data": result}


async def list_bluetooth_bonded_devices(params):
    result = await Tools.System.bluetooth.listBondedDevices()
    return {"success": True, "message": "成功获取已配对蓝牙设备", "data": result}


async def scan_bluetooth_devices(params):
    result = await Tools.System.bluetooth.scan({
        "durationMs": params.get("duration_ms"),
        "includeBle": params.get("include_ble"),
    })
    return {"success": True, "message": "成功扫描蓝牙设备", "data": result}


async def bluetooth_connect(params):
    result = await Tools.System.bluetooth.connect({
        "address": params.get("address"),
        "uuid": params.get("uuid"),
    })
    return {"success": True, "message": "成功连接蓝牙设备", "data": result}


async def bluetooth_listen(params):
    result = await Tools.System.bluetooth.listen({
        "name": params.get("name"),
        "uuid": params.get("uuid"),
    })
    return {"success": True, "message": "成功创建蓝牙监听", "data": result}


async def bluetooth_accept(params):
    result = await Tools.System.bluetooth.accept(params.get("listener_session_id"), params.get("timeout_ms"))
    return {"success": True, "message": "成功接受蓝牙连接", "data": result}


async def bluetooth_send(params):
    result = await Tools.System.bluetooth.send(params.get("session_id"), {
        "text": params.get("text"),
        "dataBase64": params.get("data_base64"),
    })
    return {"success": True, "message": "成功发送蓝牙数据", "data": result}


async def bluetooth_read(params):
    result = await Tools.System.bluetooth.read(params.get("session_id"), {
        "maxBytes": params.get("max_bytes"),
        "timeoutMs": params.get("timeout_ms"),
    })
    return {"success": True, "message": "成功读取蓝牙数据", "data": result}


async def bluetooth_send_and_read(params):
    result = await Tools.System.bluetooth.sendAndRead(params.get("session_id"), {
        "text": params.get("text"),
        "dataBase64": params.get("data_base64"),
        "maxBytes": params.get("max_bytes"),
        "timeoutMs": params.get("timeout_ms"),
    })
    return {"success": True, "message": "成功发送并读取蓝牙数据", "data": result}


async def bluetooth_close(params):
    result = await Tools.System.bluetooth.close(params.get("session_id"))
    return {"success": True, "message": "成功关闭蓝牙会话", "data": result}


async def bluetooth_ble_connect(params):
    result = await Tools.System.bluetooth.ble.connect({
        "address": params.get("address"),
        "autoConnect": params.get("auto_connect"),
    })
    return {"success": True, "message": "成功连接 BLE 设备", "data": result}


async def bluetooth_ble_discover_services(params):
    result = await Tools.System.bluetooth.ble.discoverServices(params.get("session_id"), params.get("timeout_ms"))
    return {"success": True, "message": "成功发现 BLE 服务", "data": result}


async def bluetooth_ble_read_characteristic(params):
    result = await Tools.System.bluetooth.ble.readCharacteristic(params.get("session_id"), {
        "serviceUuid": params.get("service_uuid"),
        "characteristicUuid": params.get("characteristic_uuid"),
        "timeoutMs": params.get("timeout_ms"),
    })
    return {"success": True, "message": "成功读取 BLE characteristic", "data": result}


async def bluetooth_ble_write_characteristic(params):
    result = await Tools.System.bluetooth.ble.writeCharacteristic(params.get("session_id"), {
        "serviceUuid": params.get("service_uuid"),
        "characteristicUuid": params.get("characteristic_uuid"),
        "text": params.get("text"),
        "dataBase64": params.get("data_base64"),
    })
    return {"success": True, "message": "成功写入 BLE characteristic", "data": result}


async def bluetooth_ble_write_and_read_characteristic(params):
    result = await Tools.System.bluetooth.ble.writeAndReadCharacteristic(params.get("session_id"), {
        "writeServiceUuid": params.get("write_service_uuid"),
        "writeCharacteristicUuid": params.get("write_characteristic_uuid"),
        "readServiceUuid": params.get("read_service_uuid"),
        "readCharacteristicUuid": params.get("read_characteristic_uuid"),
        "text": params.get("text"),
        "dataBase64": params.get("data_base64"),
        "timeoutMs": params.get("timeout_ms"),
    })
    return {"success": True, "message": "成功写入并读取 BLE characteristic", "data": result}


async def bluetooth_ble_subscribe_characteristic(params):
    result = await Tools.System.bluetooth.ble.subscribe(params.get("session_id"), {
        "serviceUuid": params.get("service_uuid"),
        "characteristicUuid": params.get("characteristic_uuid"),
        "enable": params.get("enable"),
    })
    return {"success": True, "message": "成功更新 BLE 订阅", "data": result}


async def bluetooth_ble_read_notifications(params):
    result = await Tools.System.bluetooth.ble.readNotifications(params.get("session_id"), params.get("limit"))
    return {"success": True, "message": "成功读取 BLE 通知", "data": result}


async def get_device_info(params):
    result = await Tools.System.getDeviceInfo()
    return {"success": True, "message": "成功获取设备信息", "data": result}


async def wrapToolExecution(func, params):
    try:
        result = await func(params)
        complete(result)
    except Exception as error:
        console.error(f"Tool {func.__name__} failed unexpectedly", error)
        complete({
            "success": False,
            "message": f"工具执行时发生意外错误: {str(error)}",
        })


async def main():
    console.log("=== System Tools 全面测试开始 ===\n")
    results = []

    try:
        # 1. 测试 get_device_info
        console.log("1. 测试 get_device_info...")
        try:
            deviceInfoResult = await get_device_info({})
            results.append({"tool": "get_device_info", "result": deviceInfoResult})
            console.log("✓ get_device_info 测试完成")
            if deviceInfoResult.get("data"):
                console.log(f"  设备信息: {json.dumps(deviceInfoResult['data'], ensure_ascii=False)[:100]}...")
            console.log()
        except Exception as error:
            console.log(f"⚠ get_device_info 测试失败: {str(error)} \n")
            results.append({"tool": "get_device_info", "result": {"success": False, "message": str(error)}})

        # 2. 测试 get_notifications
        console.log("2. 测试 get_notifications...")
        try:
            notificationsResult = await get_notifications({"limit": 5, "include_ongoing": False})
            results.append({"tool": "get_notifications", "result": notificationsResult})
            console.log("✓ get_notifications 测试完成")
            if notificationsResult.get("data"):
                console.log(f"  获取到 {len(notificationsResult['data']) or 0} 条通知")
            console.log()
        except Exception as error:
            console.log(f"⚠ get_notifications 测试失败: {str(error)} \n")
            results.append({"tool": "get_notifications", "result": {"success": False, "message": str(error)}})

        # 3. 测试 get_app_usage_time
        console.log("3. 测试 get_app_usage_time...")
        try:
            usageResult = await get_app_usage_time({"since_hours": 24, "limit": 5, "include_system_apps": False})
            results.append({"tool": "get_app_usage_time", "result": usageResult})
            console.log("✓ get_app_usage_time 测试完成")
            if usageResult.get("data"):
                entries = usageResult["data"].get("entries") if isinstance(usageResult["data"], dict) else None
                console.log(f"  返回条目数: {len(entries) if entries else 0}")
            console.log()
        except Exception as error:
            console.log(f"⚠ get_app_usage_time 测试失败（可能需要使用情况访问权限）: {str(error)} \n")
            results.append({"tool": "get_app_usage_time", "result": {"success": False, "message": str(error)}})

        # 4. 测试 get_device_location
        console.log("4. 测试 get_device_location...")
        try:
            locationResult = await get_device_location({"high_accuracy": False, "timeout": 5})
            results.append({"tool": "get_device_location", "result": locationResult})
            console.log("✓ get_device_location 测试完成")
            if locationResult.get("data"):
                console.log(f"  位置: {json.dumps(locationResult['data'], ensure_ascii=False)}")
            console.log()
        except Exception as error:
            console.log(f"⚠ get_device_location 测试失败（可能需要位置权限）: {str(error)} \n")
            results.append({"tool": "get_device_location", "result": {"success": False, "message": str(error)}})

        # 5. 测试 list_installed_apps
        console.log("5. 测试 list_installed_apps...")
        try:
            appsResult = await list_installed_apps({"include_system_apps": False})
            results.append({"tool": "list_installed_apps", "result": appsResult})
            console.log("✓ list_installed_apps 测试完成")
            if appsResult.get("data"):
                console.log(f"  已安装应用数量: {len(appsResult['data']) or 0}")
            console.log()
        except Exception as error:
            console.log(f"⚠ list_installed_apps 测试失败（可能需要用户授权）: {str(error)} \n")
            results.append({"tool": "list_installed_apps", "result": {"success": False, "message": str(error)}})

        # 6. 测试 get_system_setting
        console.log("6. 测试 get_system_setting...")
        try:
            settingResult = await get_system_setting({"setting": "screen_brightness", "namespace": "system"})
            results.append({"tool": "get_system_setting", "result": settingResult})
            console.log("✓ get_system_setting 测试完成")
            if settingResult.get("data"):
                d = settingResult["data"]
                console.log(f"  screen_brightness = {d.get('value') if isinstance(d, dict) else d}")
            console.log()
        except Exception as error:
            console.log(f"⚠ get_system_setting 测试失败: {str(error)} \n")
            results.append({"tool": "get_system_setting", "result": {"success": False, "message": str(error)}})

        # 7-11. 其他需要用户授权或可能造成系统变更的工具，仅做说明不实际执行
        console.log("7-11. 跳过破坏性/需要特殊权限的工具测试:")
        console.log("  ⊘ modify_system_setting - 需要WRITE_SETTINGS权限，会修改系统设置")
        console.log("  ⊘ install_app - 需要INSTALL_PACKAGES权限")
        console.log("  ⊘ uninstall_app - 需要DELETE_PACKAGES权限")
        console.log("  ⊘ start_app - 需要应用包名，可能会启动应用")
        console.log("  ⊘ stop_app - 需要KILL_BACKGROUND_PROCESSES权限\n")

        results.append({"tool": "modify_system_setting", "result": {"success": None, "message": "未测试（避免修改系统）"}})
        results.append({"tool": "install_app", "result": {"success": None, "message": "未测试（需要APK文件）"}})
        results.append({"tool": "uninstall_app", "result": {"success": None, "message": "未测试（避免卸载应用）"}})
        results.append({"tool": "start_app", "result": {"success": None, "message": "未测试（避免启动应用）"}})
        results.append({"tool": "stop_app", "result": {"success": None, "message": "未测试（避免停止应用）"}})

        console.log("=== System Tools 测试完成 ===\n")
        console.log("测试结果汇总:")
        for i, r in enumerate(results):
            status = "✓" if r["result"]["success"] is True else ("✗" if r["result"]["success"] is False else "⊘")
            console.log(f"{i + 1}. {status} {r['tool']}: {r['result']['message']}")

        successCount = len([r for r in results if r["result"]["success"] is True])
        failCount = len([r for r in results if r["result"]["success"] is False])
        skipCount = len([r for r in results if r["result"]["success"] is None])

        console.log(f"\n总计: {successCount} 成功, {failCount} 失败, {skipCount} 跳过")

        complete({
            "success": True,
            "message": "系统工具全面测试完成",
            "data": {
                "results": results,
                "summary": {
                    "total": len(results),
                    "success": successCount,
                    "failed": failCount,
                    "skipped": skipCount,
                },
            },
        })
    except Exception as error:
        console.error("测试过程中发生错误:", error)
        complete({
            "success": False,
            "message": f"测试失败: {str(error)}",
            "data": results,
        })


def _make_wrapper(func):
    async def wrapper(params):
        await wrapToolExecution(func, params)
    return wrapper


exports.get_system_setting = _make_wrapper(get_system_setting)
exports.modify_system_setting = _make_wrapper(modify_system_setting)
exports.install_app = _make_wrapper(install_app)
exports.uninstall_app = _make_wrapper(uninstall_app)
exports.list_installed_apps = _make_wrapper(list_installed_apps)
exports.start_app = _make_wrapper(start_app)
exports.stop_app = _make_wrapper(stop_app)
exports.send_broadcast = _make_wrapper(send_broadcast)
exports.execute_intent = _make_wrapper(execute_intent)
exports.get_notifications = _make_wrapper(get_notifications)
exports.get_app_usage_time = _make_wrapper(get_app_usage_time)
exports.get_device_location = _make_wrapper(get_device_location)
exports.request_bluetooth_permission = _make_wrapper(request_bluetooth_permission)
exports.get_bluetooth_state = _make_wrapper(get_bluetooth_state)
exports.request_enable_bluetooth = _make_wrapper(request_enable_bluetooth)
exports.list_bluetooth_bonded_devices = _make_wrapper(list_bluetooth_bonded_devices)
exports.scan_bluetooth_devices = _make_wrapper(scan_bluetooth_devices)
exports.bluetooth_connect = _make_wrapper(bluetooth_connect)
exports.bluetooth_listen = _make_wrapper(bluetooth_listen)
exports.bluetooth_accept = _make_wrapper(bluetooth_accept)
exports.bluetooth_send = _make_wrapper(bluetooth_send)
exports.bluetooth_read = _make_wrapper(bluetooth_read)
exports.bluetooth_send_and_read = _make_wrapper(bluetooth_send_and_read)
exports.bluetooth_close = _make_wrapper(bluetooth_close)
exports.bluetooth_ble_connect = _make_wrapper(bluetooth_ble_connect)
exports.bluetooth_ble_discover_services = _make_wrapper(bluetooth_ble_discover_services)
exports.bluetooth_ble_read_characteristic = _make_wrapper(bluetooth_ble_read_characteristic)
exports.bluetooth_ble_write_characteristic = _make_wrapper(bluetooth_ble_write_characteristic)
exports.bluetooth_ble_write_and_read_characteristic = _make_wrapper(bluetooth_ble_write_and_read_characteristic)
exports.bluetooth_ble_subscribe_characteristic = _make_wrapper(bluetooth_ble_subscribe_characteristic)
exports.bluetooth_ble_read_notifications = _make_wrapper(bluetooth_ble_read_notifications)
exports.get_device_info = _make_wrapper(get_device_info)
exports.main = main
