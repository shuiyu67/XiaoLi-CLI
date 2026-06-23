# METADATA
# {
#     "name": "network_test",
#     "display_name": {"zh": "网络测试", "en": "Network Test"},
#     "category": "Network",
#     "description": {"zh": "网络测试工具集合，提供基于OkHttp3的网络请求功能，包括GET、POST、PUT、DELETE请求方法，以及请求超时设置、重定向控制和拦截器管理。支持多种数据格式，便于测试API接口和网络连接性能。", "en": "Network testing tools based on OkHttp3. Provides GET/POST/PUT/DELETE requests, timeout settings, redirect control, and interceptor management. Supports multiple data formats for API testing and connectivity diagnostics."},
#     "tools": [
#         {"name": "http_get", "description": {"zh": "发送HTTP GET请求", "en": "Send an HTTP GET request."}, "parameters": [
#             {"name": "url", "description": {"zh": "请求URL", "en": "Request URL."}, "type": "string", "required": True},
#             {"name": "headers", "description": {"zh": "请求头", "en": "Request headers."}, "type": "object", "required": False}
#         ]},
#         {"name": "http_post", "description": {"zh": "发送HTTP POST请求", "en": "Send an HTTP POST request."}, "parameters": [
#             {"name": "url", "description": {"zh": "请求URL", "en": "Request URL."}, "type": "string", "required": True},
#             {"name": "body", "description": {"zh": "请求体", "en": "Request body."}, "type": "object", "required": True},
#             {"name": "headers", "description": {"zh": "请求头", "en": "Request headers."}, "type": "object", "required": False},
#             {"name": "body_type", "description": {"zh": "请求体类型，支持'text'、'json'、'form'、'multipart'", "en": "Body type: 'text', 'json', 'form', or 'multipart'."}, "type": "string", "required": False}
#         ]},
#         {"name": "http_put", "description": {"zh": "发送HTTP PUT请求", "en": "Send an HTTP PUT request."}, "parameters": [
#             {"name": "url", "description": {"zh": "请求URL", "en": "Request URL."}, "type": "string", "required": True},
#             {"name": "body", "description": {"zh": "请求体", "en": "Request body."}, "type": "object", "required": True},
#             {"name": "headers", "description": {"zh": "请求头", "en": "Request headers."}, "type": "object", "required": False},
#             {"name": "body_type", "description": {"zh": "请求体类型，支持'text'、'json'、'form'、'multipart'", "en": "Body type: 'text', 'json', 'form', or 'multipart'."}, "type": "string", "required": False}
#         ]},
#         {"name": "http_delete", "description": {"zh": "发送HTTP DELETE请求", "en": "Send an HTTP DELETE request."}, "parameters": [
#             {"name": "url", "description": {"zh": "请求URL", "en": "Request URL."}, "type": "string", "required": True},
#             {"name": "headers", "description": {"zh": "请求头", "en": "Request headers."}, "type": "object", "required": False}
#         ]},
#         {"name": "config_client", "description": {"zh": "配置HTTP客户端", "en": "Configure the HTTP client."}, "parameters": [
#             {"name": "connect_timeout", "description": {"zh": "连接超时时间(毫秒)", "en": "Connection timeout (milliseconds)."}, "type": "number", "required": False},
#             {"name": "read_timeout", "description": {"zh": "读取超时时间(毫秒)", "en": "Read timeout (milliseconds)."}, "type": "number", "required": False},
#             {"name": "write_timeout", "description": {"zh": "写入超时时间(毫秒)", "en": "Write timeout (milliseconds)."}, "type": "number", "required": False},
#             {"name": "follow_redirects", "description": {"zh": "是否跟随重定向", "en": "Whether to follow redirects."}, "type": "boolean", "required": False},
#             {"name": "retry_on_failure", "description": {"zh": "是否在连接失败时重试", "en": "Whether to retry on connection failure."}, "type": "boolean", "required": False}
#         ]},
#         {"name": "ping_test", "description": {"zh": "测试与指定URL的网络连接", "en": "Test network connectivity to a specified URL."}, "parameters": [
#             {"name": "url", "description": {"zh": "要测试的URL", "en": "URL to test."}, "type": "string", "required": True},
#             {"name": "count", "description": {"zh": "测试次数", "en": "Number of test attempts."}, "type": "number", "required": False}
#         ]},
#         {"name": "test_all", "description": {"zh": "运行所有网络测试", "en": "Run all network tests."}, "parameters": []}
#     ]
# }

import json
import re
import time
import math
from datetime import datetime
from urllib.parse import quote, unquote

Error = Exception

# 默认客户端
defaultClient = OkHttp.newClient()

# 客户端配置
clientConfig = {
    "timeouts": {"connect": 10000, "read": 10000, "write": 10000},
    "followRedirects": True,
    "retryOnConnectionFailure": True,
    "interceptors": [],
}


async def config_client(params):
    global defaultClient
    try:
        if params.get("connect_timeout") is not None:
            clientConfig["timeouts"]["connect"] = params.get("connect_timeout")
        if params.get("read_timeout") is not None:
            clientConfig["timeouts"]["read"] = params.get("read_timeout")
        if params.get("write_timeout") is not None:
            clientConfig["timeouts"]["write"] = params.get("write_timeout")
        if params.get("follow_redirects") is not None:
            clientConfig["followRedirects"] = params.get("follow_redirects")
        if params.get("retry_on_failure") is not None:
            clientConfig["retryOnConnectionFailure"] = params.get("retry_on_failure")

        builder = (
            OkHttp.newBuilder()
            .connectTimeout(clientConfig["timeouts"]["connect"])
            .readTimeout(clientConfig["timeouts"]["read"])
            .writeTimeout(clientConfig["timeouts"]["write"])
            .followRedirects(clientConfig["followRedirects"])
            .retryOnConnectionFailure(clientConfig["retryOnConnectionFailure"])
        )

        if len(clientConfig["interceptors"]) > 0:
            for interceptor in clientConfig["interceptors"]:
                builder.addInterceptor(interceptor)

        defaultClient = builder.build()

        return {
            "success": True,
            "message": "HTTP客户端配置已更新",
            "config": dict(clientConfig),
        }
    except Exception as error:
        raise Error(f"配置HTTP客户端失败: {str(error)}")


async def http_get(params):
    try:
        if not params.get("url"):
            raise Error("URL不能为空")

        console.log(f"发送GET请求: {params.get('url')}")
        console.log(f"请求头: {json.dumps(params.get('headers') or {}, ensure_ascii=False)}")

        request = defaultClient.newRequest().url(params.get("url")).method("GET")

        if params.get("headers"):
            request.headers(params.get("headers"))

        response = await request.build().execute()

        result = await formatResponse(response)

        console.log(f"\n🟢 GET请求完成: {params.get('url')}")
        console.log(f"🟢 状态码: {result['status_code']} {result['status_message']}")
        if result.get("json"):
            j = result["json"]
            if isinstance(j, list):
                console.log("🟢 返回数据类型: 数组")
            elif isinstance(j, dict):
                console.log("🟢 返回数据类型: 对象")
            else:
                console.log(f"🟢 返回数据类型: {type(j).__name__}")
        console.log(f"🟢 响应大小: {result['content_length']} 字节\n")

        return result
    except Exception as error:
        raise Error(f"GET请求失败: {str(error)}")


async def http_post(params):
    try:
        if not params.get("url"):
            raise Error("URL不能为空")

        if params.get("body") is None:
            raise Error("请求体不能为空")

        console.log(f"发送POST请求: {params.get('url')}")

        request = defaultClient.newRequest().url(params.get("url")).method("POST")

        if params.get("headers"):
            request.headers(params.get("headers"))

        bodyType = params.get("body_type") or "json"
        request.body(params.get("body"), bodyType)

        response = await request.build().execute()

        return await formatResponse(response)
    except Exception as error:
        raise Error(f"POST请求失败: {str(error)}")


async def http_put(params):
    try:
        if not params.get("url"):
            raise Error("URL不能为空")

        if params.get("body") is None:
            raise Error("请求体不能为空")

        console.log(f"发送PUT请求: {params.get('url')}")

        request = defaultClient.newRequest().url(params.get("url")).method("PUT")

        if params.get("headers"):
            request.headers(params.get("headers"))

        bodyType = params.get("body_type") or "json"
        request.body(params.get("body"), bodyType)

        response = await request.build().execute()

        return await formatResponse(response)
    except Exception as error:
        raise Error(f"PUT请求失败: {str(error)}")


async def http_delete(params):
    try:
        if not params.get("url"):
            raise Error("URL不能为空")

        console.log(f"发送DELETE请求: {params.get('url')}")

        request = defaultClient.newRequest().url(params.get("url")).method("DELETE")

        if params.get("headers"):
            request.headers(params.get("headers"))

        response = await request.build().execute()

        return await formatResponse(response)
    except Exception as error:
        raise Error(f"DELETE请求失败: {str(error)}")


async def formatResponse(response):
    try:
        responseBody = ""
        jsonData = None

        responseBody = response.content
        console.log("\n===== 响应内容开始 =====")
        console.log(f"状态码: {response.statusCode} {getattr(response, 'statusMessage', '')}")
        console.log(f"内容类型: {getattr(response, 'contentType', None) or '未知'}")

        if responseBody and len(responseBody) < 1000:
            console.log(f"响应体:\n{responseBody}")
        elif responseBody:
            console.log(f"响应体(截断):\n{responseBody[:500]}...")
            console.log(f"[完整长度: {len(responseBody)} 字符]")
        else:
            console.log("响应体为空")

        contentType = getattr(response, "contentType", None) or ""
        if "application/json" in contentType:
            try:
                jsonData = response.json()
                if jsonData is not None:
                    if isinstance(jsonData, list):
                        console.log(f"- 数组数据, 长度: {len(jsonData)}")
                        if len(jsonData) > 0:
                            sample = json.dumps(jsonData[0], ensure_ascii=False)
                            console.log(f"- 第一项样本: {sample[:100]}{'...' if len(sample) > 100 else ''}")
                    elif isinstance(jsonData, dict):
                        keys = list(jsonData.keys())
                        console.log(f"- 对象数据, 字段数: {len(keys)}")
                        console.log(f"- 字段列表: {', '.join(keys[:5])}{'...' if len(keys) > 5 else ''}")
                        if len(keys) > 0:
                            sampleKey = keys[0]
                            sampleValue = json.dumps(jsonData[sampleKey], ensure_ascii=False)
                            console.log(f'- 示例 "{sampleKey}": {sampleValue[:60]}{"..." if len(sampleValue) > 60 else ""}')

                        console.log("\nJSON完整数据:")
                        console.log(json.dumps(jsonData, indent=2, ensure_ascii=False))
                    else:
                        console.log(f"- 基本类型数据: {json.dumps(jsonData, ensure_ascii=False)[:100]}")
            except Exception:
                console.warn("响应内容不是有效的JSON格式")

        console.log("===== 响应内容结束 =====\n")

        return {
            "success": response.isSuccessful(),
            "status_code": response.statusCode,
            "status_message": getattr(response, "statusMessage", ""),
            "headers": getattr(response, "headers", None),
            "content_type": getattr(response, "contentType", None),
            "content_length": getattr(response, "size", 0),
            "body": responseBody,
            "json": jsonData,
            "time_info": {"timestamp": datetime.now().isoformat()},
        }
    except Exception as error:
        console.error(f"格式化响应出错: {str(error)}")
        return {
            "success": False,
            "error": f"格式化响应出错: {str(error)}",
        }


async def ping_test(params):
    try:
        if not params.get("url"):
            raise Error("URL不能为空")

        count = params.get("count") or 3
        results = []
        totalTime = 0
        successCount = 0
        failCount = 0

        console.log(f"开始Ping测试: {params.get('url')}, 次数: {count}")

        for i in range(count):
            startTime = time.time() * 1000
            try:
                request = defaultClient.newRequest().url(params.get("url")).method("HEAD").build()
                response = await request.execute()
                endTime = time.time() * 1000
                elapsed = endTime - startTime

                totalTime += elapsed
                successCount += 1

                results.append({
                    "attempt": i + 1,
                    "success": True,
                    "time_ms": elapsed,
                    "status": response.statusCode,
                })

                console.log(f"Ping #{i + 1}: {elapsed}ms, 状态: {response.statusCode}")

                if i < count - 1:
                    await sleep(500)
            except Exception as error:
                endTime = time.time() * 1000
                elapsed = endTime - startTime
                failCount += 1

                results.append({
                    "attempt": i + 1,
                    "success": False,
                    "time_ms": elapsed,
                    "error": str(error),
                })

                console.log(f"Ping #{i + 1}: 失败, 错误: {str(error)}")

                if i < count - 1:
                    await sleep(500)

        avgTime = totalTime / successCount if successCount > 0 else 0

        return {
            "url": params.get("url"),
            "success": successCount > 0,
            "summary": {
                "total_count": count,
                "success_count": successCount,
                "fail_count": failCount,
                "success_rate": f"{(successCount / count * 100):.1f}%",
                "average_time": f"{avgTime:.2f}ms",
            },
            "detail_results": results,
        }
    except Exception as error:
        raise Error(f"Ping测试失败: {str(error)}")


async def sleep(ms):
    sleepTime = float(ms)
    if math.isnan(sleepTime):
        raise Error("无效的等待时间")
    await Tools.System.sleep(int(sleepTime))


async def test_all():
    try:
        console.log("开始网络功能测试...")

        results = {}

        # 1. 测试客户端配置
        console.log("测试客户端配置...")
        try:
            configResult = await config_client({
                "connect_timeout": 8000,
                "read_timeout": 8000,
                "write_timeout": 8000,
                "follow_redirects": True,
                "retry_on_failure": True,
            })
            results["config"] = configResult
            console.log("✓ 客户端配置成功")
        except Exception as error:
            results["config"] = {"error": f"客户端配置失败: {str(error)}"}
            console.log("✗ 客户端配置失败")

        # 2. 测试连接
        console.log("测试网络连接...")
        try:
            pingResult = await ping_test({"url": "https://httpbin.org", "count": 2})
            results["ping"] = pingResult
            console.log("✓ Ping测试成功")
        except Exception as error:
            results["ping"] = {"error": f"Ping测试失败: {str(error)}"}
            console.log("✗ Ping测试失败")

        # 3. 测试GET请求
        console.log("测试GET请求...")
        try:
            getResult = await http_get({
                "url": "https://httpbin.org/get",
                "headers": {"User-Agent": "OkHttp-Network-Tester/1.0"},
            })
            results["get"] = getResult
            console.log("✓ GET请求成功")

            console.log("\n====== GET请求结果摘要 ======")
            console.log(f"状态: {getResult['status_code']} {getResult['status_message']}")

            if getResult.get("json"):
                console.log("GET响应数据预览:")
                j = getResult["json"]
                if isinstance(j, dict):
                    if j.get("headers"):
                        console.log("- 发送的请求头:")
                        for key in j["headers"]:
                            console.log(f"  {key}: {j['headers'][key]}")
                    if j.get("url"):
                        console.log(f"- 请求URL: {j['url']}")
                    if j.get("origin"):
                        console.log(f"- 来源IP: {j['origin']}")
            console.log("===============================\n")
        except Exception as error:
            results["get"] = {"error": f"GET请求失败: {str(error)}"}
            console.log("✗ GET请求失败")

        # 4. 测试POST请求
        console.log("测试POST请求...")
        try:
            postResult = await http_post({
                "url": "https://httpbin.org/post",
                "body": {"name": "OkHttp网络测试", "timestamp": datetime.now().isoformat()},
                "headers": {"Content-Type": "application/json", "User-Agent": "OkHttp-Network-Tester/1.0"},
            })
            results["post"] = postResult
            console.log("✓ POST请求成功")
        except Exception as error:
            results["post"] = {"error": f"POST请求失败: {str(error)}"}
            console.log("✗ POST请求失败")

        # 5. 测试PUT请求
        console.log("测试PUT请求...")
        try:
            putResult = await http_put({
                "url": "https://httpbin.org/put",
                "body": {"name": "OkHttp网络测试", "timestamp": datetime.now().isoformat(), "action": "update"},
                "headers": {"Content-Type": "application/json", "User-Agent": "OkHttp-Network-Tester/1.0"},
            })
            results["put"] = putResult
            console.log("✓ PUT请求成功")
        except Exception as error:
            results["put"] = {"error": f"PUT请求失败: {str(error)}"}
            console.log("✗ PUT请求失败")

        # 6. 测试DELETE请求
        console.log("测试DELETE请求...")
        try:
            deleteResult = await http_delete({
                "url": "https://httpbin.org/delete",
                "headers": {"User-Agent": "OkHttp-Network-Tester/1.0"},
            })
            results["delete"] = deleteResult
            console.log("✓ DELETE请求成功")
        except Exception as error:
            results["delete"] = {"error": f"DELETE请求失败: {str(error)}"}
            console.log("✗ DELETE请求失败")

        return {
            "message": "网络功能测试完成",
            "test_results": results,
            "timestamp": datetime.now().isoformat(),
            "summary": "测试了各种网络功能，包括配置、Ping测试和HTTP请求。请查看各功能的测试结果。",
        }
    except Exception as error:
        return {
            "success": False,
            "message": f"测试过程中发生错误: {str(error)}",
        }


async def network_wrap(func, params, successMessage, failMessage, additionalInfo=""):
    try:
        console.log(f"开始执行函数: {func.__name__ or '匿名函数'}")
        console.log("参数:", json.dumps(params, indent=2, ensure_ascii=False, default=str))

        result = await func(params)

        console.log(f"函数 {func.__name__ or '匿名函数'} 执行结果:", json.dumps(result, indent=2, ensure_ascii=False, default=str))

        if result is None:
            return

        if isinstance(result, bool):
            complete({
                "success": result,
                "message": successMessage if result else failMessage,
                "additionalInfo": additionalInfo,
            })
        else:
            complete({
                "success": True,
                "message": successMessage,
                "additionalInfo": additionalInfo,
                "data": result,
            })
    except Exception as error:
        console.error(f"函数 {func.__name__ or '匿名函数'} 执行失败!")
        console.error(f"错误信息: {str(error)}")
        import traceback
        stack = traceback.format_exc()
        console.error(f"错误堆栈: {stack}")

        complete({
            "success": False,
            "message": f"{failMessage}: {str(error)}",
            "additionalInfo": additionalInfo,
            "error_stack": stack,
        })


async def _config_client_wrapper(params):
    await network_wrap(config_client, params, "配置HTTP客户端成功", "配置HTTP客户端失败")


async def _http_get_wrapper(params):
    await network_wrap(http_get, params, "GET请求成功", "GET请求失败")


async def _http_post_wrapper(params):
    await network_wrap(http_post, params, "POST请求成功", "POST请求失败")


async def _http_put_wrapper(params):
    await network_wrap(http_put, params, "PUT请求成功", "PUT请求失败")


async def _http_delete_wrapper(params):
    await network_wrap(http_delete, params, "DELETE请求成功", "DELETE请求失败")


async def _ping_test_wrapper(params):
    await network_wrap(ping_test, params, "网络连接测试成功", "网络连接测试失败")


async def _test_all_wrapper(params):
    await network_wrap(test_all, {}, "网络功能测试完成", "网络功能测试失败")


exports.config_client = _config_client_wrapper
exports.http_get = _http_get_wrapper
exports.http_post = _http_post_wrapper
exports.http_put = _http_put_wrapper
exports.http_delete = _http_delete_wrapper
exports.ping_test = _ping_test_wrapper
exports.test_all = _test_all_wrapper
exports.main = _test_all_wrapper
