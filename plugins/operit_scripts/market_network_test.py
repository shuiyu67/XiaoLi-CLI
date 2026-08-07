# METADATA
# {
#   "name": "network_test",
#   "display_name": { "zh": "网络测试", "en": "Network Test" },
#   "description": { "zh": "基于 OkHttp 的网络请求测试（GET/POST）", "en": "Network request testing via OkHttp." },
#   "category": "Network",
#   "tools": [
#     { "name": "http_get", "description": { "zh": "发送 HTTP GET 请求", "en": "Send HTTP GET" } },
#     { "name": "http_post", "description": { "zh": "发送 HTTP POST 请求", "en": "Send HTTP POST" } }
#   ]
# }
import json as _json


def getErrorMessage(error):
    return str(error) if error else "unknown"


def getErrorStack(error):
    import traceback
    return traceback.format_exc()


def format_response(resp):
    content = resp.content or ""
    result = {
        "status_code": resp.statusCode,
        "status_message": resp.statusMessage,
        "content_length": len(content),
        "headers": resp.headers(),
        "content": content[:12000],
    }
    try:
        result["json"] = _json.loads(content)
    except Exception:
        result["json"] = None
    return result


async def http_get(params):
    if not params.get("url"):
        return {"success": False, "message": "URL不能为空"}
    try:
        console.log(f"发送GET请求: {params['url']}")
        req = OkHttp.newClient().newRequest().url(params["url"]).method("GET")
        if params.get("headers"):
            req = req.headers(params["headers"])
        resp = await req.build().execute()
        return {"success": True, "message": "GET请求完成", "data": format_response(resp)}
    except Exception as e:
        return {"success": False, "message": f"GET请求失败: {getErrorMessage(e)}"}


async def http_post(params):
    if not params.get("url"):
        return {"success": False, "message": "URL不能为空"}
    if params.get("body") is None:
        return {"success": False, "message": "请求体不能为空"}
    try:
        req = OkHttp.newClient().newRequest().url(params["url"]).method("POST")
        if params.get("headers"):
            req = req.headers(params["headers"])
        body_type = params.get("body_type", "json")
        req = req.body(params["body"], body_type)
        resp = await req.build().execute()
        return {"success": True, "message": "POST请求完成", "data": format_response(resp)}
    except Exception as e:
        return {"success": False, "message": f"POST请求失败: {getErrorMessage(e)}"}


async def wrap(func, params, ok_msg="操作成功", err_msg="操作失败"):
    try:
        result = await func(params)
        complete({"success": True, "message": result.get("message", ok_msg),
                   "data": result.get("data"), **{k: v for k, v in result.items() if k not in ("success", "message", "data")}})
    except Exception as error:
        console.error(f"Error: {getErrorMessage(error)}")
        complete({"success": False, "message": getErrorMessage(error), "error_stack": getErrorStack(error)})


async def http_get_wrapper(params):
    await wrap(http_get, params, "GET请求完成", "GET请求失败")


async def http_post_wrapper(params):
    await wrap(http_post, params, "POST请求完成", "POST请求失败")


exports.http_get = http_get_wrapper
exports.http_post = http_post_wrapper
