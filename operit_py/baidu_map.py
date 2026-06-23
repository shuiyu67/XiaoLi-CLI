# METADATA
# {
#     "name": "baidu_map",
#     "display_name": { "zh": "百度地图工具", "en": "Baidu Map Tools" },
#     "description": { "zh": "百度地图工具集合，提供AOI（兴趣区域）数据获取接口。通过调用百度地图API，支持按地理范围查询AOI边界坐标，基于位置的路线规划，助力地理信息系统应用开发和空间数据分析。", "en": "A Baidu Maps toolkit that provides AOI (Area of Interest) data access. It supports querying AOI boundary coordinates by geographic range and location-based route planning, useful for GIS development and spatial data analysis." },
#     "enabledByDefault": true,
#     "category": "Map",
#     "tools": [
#         { "name": "search_aoi", "description": { "zh": "搜索百度地图兴趣区域(AOI)信息", "en": "Search AOI (Area of Interest) information from Baidu Maps." }, "parameters": [ { "name": "keyword", "description": { "zh": "搜索关键词，如商场、小区名称等", "en": "Search keyword, e.g. mall name, residential community name, etc." }, "type": "string", "required": true }, { "name": "city_name", "description": { "zh": "城市名称，如'北京'，默认全国范围", "en": "City name, e.g. '北京'. Defaults to nationwide." }, "type": "string", "required": false } ] },
#         { "name": "planRoute", "description": { "zh": "智能路线规划，从当前位置到指定目的地，并发返回驾车、步行、公交三种方式的路线规划。", "en": "Smart route planning from current location to a destination, returning driving/walking/transit plans in parallel." }, "parameters": [ { "name": "destination", "description": { "zh": "目的地名称", "en": "Destination name." }, "type": "string", "required": true }, { "name": "city_name", "description": { "zh": "城市名称，辅助目的地查找", "en": "City name to help resolve the destination (optional)." }, "type": "string", "required": false } ] }
#     ]
# }

import json
import math
import time
import asyncio
from datetime import datetime
from urllib.parse import quote, unquote

Error = Exception

# 常用城市编码
CITY_CODES = {
    "北京": "131",
    "上海": "289",
    "广州": "257",
    "深圳": "340",
    "杭州": "179",
    "南京": "315",
    "武汉": "218",
    "成都": "75",
    "重庆": "132",
    "西安": "233",
    "全国": "1"  # 默认值
}

# 请求头配置
HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Host': 'map.baidu.com',
    'Pragma': 'no-cache',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0',
    'sec-ch-ua': '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'Referer': 'https://map.baidu.com/'
}

# 日志级别配置
LOG_LEVELS = {
    'NONE': 0,
    'ERROR': 1,
    'WARN': 2,
    'INFO': 3,
    'DEBUG': 4,
    'TRACE': 5
}

# 默认日志级别
currentLogLevel = LOG_LEVELS['INFO']


def setLogLevel(level):
    global currentLogLevel
    if level >= LOG_LEVELS['NONE'] and level <= LOG_LEVELS['TRACE']:
        currentLogLevel = level


def logger(level, message, data=None):
    if level > currentLogLevel:
        return
    levelNames = {
        LOG_LEVELS['ERROR']: '[ERROR]',
        LOG_LEVELS['WARN']: '[WARN]',
        LOG_LEVELS['INFO']: '[INFO]',
        LOG_LEVELS['DEBUG']: '[DEBUG]',
        LOG_LEVELS['TRACE']: '[TRACE]'
    }
    levelName = levelNames.get(level, '[UNKNOWN]')
    timestamp = datetime.now().isoformat()
    logMessage = f"{timestamp} {levelName} {message}"
    console.log(logMessage)
    if data is not None:
        console.log(data)


def encodeURIComponentSafe(s):
    try:
        return quote(s, safe='')
    except Exception as e:
        logger(LOG_LEVELS['ERROR'], "编码失败:", e)
        return s


def createHttpClient():
    return OkHttp.newBuilder() \
        .connectTimeout(10000) \
        .readTimeout(30000) \
        .writeTimeout(15000) \
        .followRedirects(True) \
        .build()


async def httpGet(url):
    try:
        client = createHttpClient()
        response = await client.newRequest().url(url).method("GET").headers(HEADERS).build().execute()
        if not response.isSuccessful():
            raise Error(f"请求失败: {response.statusCode}")
        try:
            return json.loads(response.content)
        except Exception as e:
            logger(LOG_LEVELS['ERROR'], "解析JSON失败:", e)
            return response.content
    except Exception as e:
        logger(LOG_LEVELS['ERROR'], "网络请求错误:", e)
        raise e


async def getCityCode(cityName):
    try:
        logger(LOG_LEVELS['INFO'], f"开始查询城市编码: {cityName}")
        if cityName in CITY_CODES:
            logger(LOG_LEVELS['DEBUG'], f"本地映射表中找到城市\"{cityName}\"的编码:", CITY_CODES[cityName])
            return CITY_CODES[cityName]

        encodedCityName = encodeURIComponentSafe(cityName)
        url = f"https://map.baidu.com/?newmap=1&qt=s&wd={encodedCityName}&c=1"
        logger(LOG_LEVELS['INFO'], "发送请求获取城市编码:", url)
        result = await httpGet(url)

        cityCode = "1"

        if result and result.get("current_city") and result["current_city"].get("code"):
            cityCode = str(result["current_city"]["code"])
            logger(LOG_LEVELS['DEBUG'], "从current_city中找到城市编码:", cityCode)
        elif result and result.get("content") and isinstance(result["content"], list) and len(result["content"]) > 0:
            for item in result["content"]:
                if item.get("area_code"):
                    cityCode = str(item["area_code"])
                    logger(LOG_LEVELS['DEBUG'], "从content[].area_code中找到城市编码:", cityCode)
                    break
                elif item.get("city_id"):
                    cityCode = str(item["city_id"])
                    logger(LOG_LEVELS['DEBUG'], "从content[].city_id中找到城市编码:", cityCode)
                    break
        elif result and result.get("result") and result["result"].get("code"):
            cityCode = str(result["result"]["code"])
            logger(LOG_LEVELS['DEBUG'], "从result.code中找到城市编码:", cityCode)
        elif result and result.get("result") and result["result"].get("city_id"):
            cityCode = str(result["result"]["city_id"])
            logger(LOG_LEVELS['DEBUG'], "从result.city_id中找到城市编码:", cityCode)

        if cityCode == "1":
            secondUrl = f"https://map.baidu.com/?qt=cur&wd={encodedCityName}"
            logger(LOG_LEVELS['DEBUG'], "未找到编码，尝试第二个API端点:", secondUrl)
            try:
                await Tools.System.sleep(500)
                secondResult = await httpGet(secondUrl)
                if secondResult and secondResult.get("current_city") and secondResult["current_city"].get("code"):
                    cityCode = str(secondResult["current_city"]["code"])
                    logger(LOG_LEVELS['DEBUG'], "从第二个API获取到城市编码:", cityCode)
            except Exception as e:
                logger(LOG_LEVELS['ERROR'], "第二个API请求失败:", e)

        if cityCode == "1":
            logger(LOG_LEVELS['INFO'], f"未能找到城市\"{cityName}\"的编码，使用默认编码\"1\"(全国)")
        else:
            CITY_CODES[cityName] = cityCode
            logger(LOG_LEVELS['DEBUG'], f"已将城市\"{cityName}\"的编码{cityCode}添加到临时映射表")

        return cityCode
    except Exception as error:
        logger(LOG_LEVELS['ERROR'], "获取城市编码失败:", error)
        return "1"


async def search_aoi(params):
    try:
        keyword = params.get("keyword", "")
        if not keyword:
            raise Error("关键词不能为空")

        cityCode = "1"
        if params.get("city_name"):
            cityCode = await getCityCode(params["city_name"])
            logger(LOG_LEVELS['DEBUG'], f"城市 \"{params['city_name']}\" 对应的编码:", cityCode)

        encodedKeyword = encodeURIComponentSafe(keyword)
        url = f"https://map.baidu.com/?newmap=1&qt=s&da_src=searchBox.button&wd={encodedKeyword}&c={cityCode}"
        logger(LOG_LEVELS['INFO'], f"搜索AOI: {keyword}, 城市名称: {params.get('city_name', '全国')}")

        result = await httpGet(url)
        dataContent = result.get("content", []) if result else []

        if not dataContent or len(dataContent) == 0:
            logger(LOG_LEVELS['INFO'], "搜索结果为空或格式不符合预期")
            return {
                "success": True,
                "keyword": keyword,
                "city_name": params.get("city_name"),
                "total": 0,
                "aois": []
            }

        potentialAois = []
        for item in dataContent:
            uid = item.get("uid", "")
            name = item.get("name", "") or item.get("alias", "")
            address = item.get("addr", "")
            area_name = item.get("area_name")
            phone = item.get("tel")

            typeStr = ""
            if item.get("cla") and isinstance(item["cla"], list) and len(item["cla"]) > 0:
                typeStr = ", ".join([cla[1] for cla in item["cla"]])
            detail_type = item.get("std_tag")
            tags = item.get("di_tag")

            rating = None
            comment_count = None
            overallRating = item.get("overall_rating") or (item.get("ext", {}).get("detail_info", {}) or {}).get("overall_rating")
            if overallRating:
                rating = float(overallRating)
            commentNum = (item.get("ext", {}).get("detail_info", {}) or {}).get("comment_num")
            if commentNum:
                comment_count = int(commentNum)

            price = None
            ticket_info = None
            detail_info = (item.get("ext", {}) or {}).get("detail_info", {}) or {}
            if detail_info.get("price"):
                price = detail_info["price"]
            if detail_info.get("dk_ticket"):
                ticketData = detail_info["dk_ticket"]
                ticket_info = {
                    "title": ticketData.get("title"),
                    "price": ticketData.get("price"),
                    "market_price": ticketData.get("marketprice"),
                    "sold_info": ticketData.get("sold_info"),
                    "booking_tags": ticketData.get("bookingTimeTag", []),
                    "ticket_type": ticketData.get("ticket_type_name")
                }

            opening_hours = None
            opening_hours_detail = None
            business_time = item.get("business_time", {}) or {}
            if business_time.get("data") and len(business_time["data"]) > 0:
                timeData = business_time["data"][0]
                btt = timeData.get("business_time_text", {}) or {}
                opening_hours = btt.get("common")
                opening_hours_detail = {
                    "common_hours": btt.get("common"),
                    "festival_hours": btt.get("festival"),
                    "detailed_schedule": timeData.get("common", []),
                    "festival_schedule": timeData.get("festival", {})
                }

            rankings = []
            bangdan_head = detail_info.get("bangdan_head", {}) or {}
            if bangdan_head.get("ranking_show"):
                rankings = [{
                    "name": rank.get("ranking"),
                    "rank": rank.get("rank_s"),
                    "score": rank.get("score"),
                    "short_name": rank.get("short_name"),
                    "type": rank.get("ranking_type")
                } for rank in bangdan_head["ranking_show"]]

            events = []
            if detail_info.get("event_notice"):
                en = detail_info["event_notice"]
                events.append({
                    "title": en.get("title"),
                    "content": en.get("content"),
                    "img_url": en.get("img_url"),
                    "start_end": en.get("start_end")
                })

            shop_hours_simple = item.get("shop_hours_simple")
            photo_count = int(detail_info["photo_num"]) if detail_info.get("photo_num") else None
            has_indoor_map = detail_info.get("indoor_map") == '1'

            has_street_view = False
            street_view_info = None
            pano = item.get("pano")
            if isinstance(pano, str) and pano:
                firstPano = pano.split(';')[0]
                panoParts = firstPano.split(',')
                if len(panoParts) >= 2 and panoParts[0]:
                    has_street_view = True
                    street_view_info = {
                        "pid": panoParts[0],
                        "heading": int(panoParts[1] or '0')
                    }

            lng = 0
            lat = 0
            if detail_info.get("point"):
                lng = float(detail_info["point"].get("x", 0))
                lat = float(detail_info["point"].get("y", 0))
            elif item.get("x") and item.get("y"):
                lng = float(item["x"])
                lat = float(item["y"])
            elif item.get("point") and item["point"].get("x") and item["point"].get("y"):
                lng = float(item["point"]["x"])
                lat = float(item["point"]["y"])

            hasGeoData = bool(
                (item.get("geo") and len(item["geo"]) > 0) or
                (detail_info.get("guoke_geo") and detail_info["guoke_geo"].get("geo")) or
                item.get("geo_type") == 2
            )

            additional_info = {}
            if detail_info.get("aoi_src_id"):
                additional_info["aoi_src_id"] = detail_info["aoi_src_id"]
            if detail_info.get("navi_update_time"):
                additional_info["navi_update_time"] = detail_info["navi_update_time"]
            if detail_info.get("official_url"):
                additional_info["official_url"] = detail_info["official_url"]
            if detail_info.get("is_reservable"):
                additional_info["is_reservable"] = detail_info["is_reservable"] == '1'
            if detail_info.get("areaid"):
                additional_info["area_id"] = detail_info["areaid"]
            if detail_info.get("entrance_price"):
                additional_info["entrance_price"] = detail_info["entrance_price"]
            if detail_info.get("free"):
                additional_info["is_free"] = detail_info["free"]

            detailUrl = f"https://map.baidu.com/?qt=ext&uid={uid}" if uid else ""

            aoiItem = {
                "uid": uid,
                "name": name,
                "address": address,
                "area_name": area_name,
                "phone": phone,
                "tags": tags,
                "detail_type": detail_type,
                "rating": rating,
                "comment_count": comment_count,
                "price": price,
                "ticket_info": ticket_info,
                "opening_hours": opening_hours,
                "opening_hours_detail": opening_hours_detail,
                "shop_hours_simple": shop_hours_simple,
                "photo_count": photo_count,
                "has_street_view": has_street_view,
                "street_view_info": street_view_info,
                "has_indoor_map": has_indoor_map,
                "rankings": rankings,
                "events": events,
                "type": typeStr,
                "has_geo_data": hasGeoData,
                "center": {"lng": lng, "lat": lat},
                "detail_url": detailUrl,
                "additional_info": additional_info
            }
            if currentLogLevel >= LOG_LEVELS['DEBUG']:
                aoiItem["raw_data"] = {
                    "uid": item.get("uid"),
                    "name": item.get("name"),
                    "addr": item.get("addr"),
                    "x": item.get("x"),
                    "y": item.get("y"),
                    "geo_type": item.get("geo_type")
                }
            potentialAois.append(aoiItem)

        logger(LOG_LEVELS['DEBUG'], f"找到{len(potentialAois)}个AOI结果")
        return {
            "success": True,
            "keyword": keyword,
            "city_name": params.get("city_name"),
            "total": len(potentialAois),
            "aois": potentialAois
        }
    except Exception as error:
        logger(LOG_LEVELS['ERROR'], "[search_aoi] 错误:", error)
        import traceback
        logger(LOG_LEVELS['ERROR'], "错误堆栈:", traceback.format_exc())
        return {
            "success": False,
            "message": f"搜索AOI失败: {error}",
            "keyword": params.get("keyword"),
            "city_name": params.get("city_name"),
            "total": 0,
            "aois": []
        }


async def get_aoi_boundary(params):
    try:
        uid = params.get("uid", "")
        if not uid:
            raise Error("AOI的UID不能为空")

        url = f"https://map.baidu.com/?qt=ext&uid={uid}"
        logger(LOG_LEVELS['INFO'], f"获取AOI边界: {uid}")
        result = await httpGet(url)
        logger(LOG_LEVELS['DEBUG'], "AOI边界结果结构:", list(result.keys()) if result else {})

        if not result or not result.get("content") or (isinstance(result.get("content"), list) and len(result["content"]) == 0):
            return {"success": False, "message": "未找到AOI边界数据", "uid": uid}

        content = result["content"][0] if isinstance(result["content"], list) else result["content"]
        if not content:
            return {"success": False, "message": "AOI内容数据为空", "uid": uid}

        geoData = content.get("geo")
        if not geoData and content.get("ext") and content["ext"].get("geo"):
            geoData = content["ext"]["geo"]
        elif not geoData and content.get("geodata"):
            geoData = content["geodata"]
        elif not geoData and content.get("guoke_geo") and content["guoke_geo"].get("geo"):
            geoData = content["guoke_geo"]["geo"]

        boundary = []
        if isinstance(geoData, str):
            try:
                parts = geoData.split('|')
                if len(parts) >= 3:
                    boundaryPart = parts[2]
                    coordinatePairs = boundaryPart.split(',')
                    i = 0
                    while i < len(coordinatePairs) - 1:
                        lng = float(coordinatePairs[i])
                        lat = float(coordinatePairs[i + 1])
                        if not (math.isnan(lng) or math.isnan(lat)):
                            boundary.append({"lng": lng, "lat": lat})
                        i += 2
                    logger(LOG_LEVELS['DEBUG'], f"从geo字符串解析到{len(boundary)}个边界点")
            except Exception as e:
                logger(LOG_LEVELS['ERROR'], "解析geo字符串失败:", e)
        elif isinstance(geoData, list):
            for point in geoData:
                if isinstance(point, list):
                    boundary.append({"lng": float(point[0] or 0), "lat": float(point[1] or 0)})
                else:
                    boundary.append({"lng": float(point.get("x", 0) or 0), "lat": float(point.get("y", 0) or 0)})
            logger(LOG_LEVELS['DEBUG'], f"解析到{len(boundary)}个边界点")

        resultObj = {
            "success": True,
            "uid": uid,
            "name": content.get("name", ""),
            "address": content.get("addr", ""),
            "center": {
                "lng": float(content.get("x") or (content.get("point", {}) or {}).get("x") or '0'),
                "lat": float(content.get("y") or (content.get("point", {}) or {}).get("y") or '0')
            },
            "boundary": boundary,
            "point_count": len(boundary)
        }
        if currentLogLevel >= LOG_LEVELS['DEBUG']:
            resultObj["raw_data"] = {
                "uid": content.get("uid"),
                "name": content.get("name"),
                "addr": content.get("addr"),
                "x": content.get("x"),
                "y": content.get("y"),
                "geo_type": content.get("geo_type")
            }
        return resultObj
    except Exception as error:
        logger(LOG_LEVELS['ERROR'], "[get_aoi_boundary] 错误:", error)
        import traceback
        logger(LOG_LEVELS['ERROR'], "错误堆栈:", traceback.format_exc())
        return {"success": False, "message": f"获取AOI边界失败: {error}", "uid": params.get("uid")}


def formatAoiResultAsText(aoiResult):
    if not aoiResult.get("success"):
        return f"AOI搜索失败: {aoiResult.get('message', '未知错误')}"

    output = "=== AOI搜索结果 ===\n"
    output += f"搜索关键词: {aoiResult['keyword']}\n"
    output += f"搜索城市: {aoiResult.get('city_name', '全国')}\n"
    output += f"找到结果: {aoiResult['total']} 个\n\n"

    if aoiResult.get("aois") and len(aoiResult["aois"]) > 0:
        for index, aoi in enumerate(aoiResult["aois"]):
            output += f"--- 结果 {index + 1} ---\n"
            output += f"名称: {aoi['name']}\n"
            output += f"类型: {aoi.get('type', '未知')}\n"
            output += f"地址: {aoi['address']}\n"
            if aoi.get("area_name"):
                output += f"所属区域: {aoi['area_name']}\n"
            if aoi.get("phone"):
                output += f"联系电话: {aoi['phone']}\n"
            if aoi.get("tags"):
                output += f"标签: {aoi['tags']}\n"
            if aoi.get("rating") is not None:
                output += f"评分: {aoi['rating']}/5.0"
                if aoi.get("comment_count") is not None:
                    output += f" ({aoi['comment_count']}条评论)"
                output += "\n"
            if aoi.get("price"):
                output += f"价格信息: {aoi['price']}\n"
            if aoi.get("ticket_info"):
                output += "门票信息:\n"
                ti = aoi["ticket_info"]
                if ti.get("title"):
                    output += f"  - 门票名称: {ti['title']}\n"
                if ti.get("price"):
                    output += f"  - 门票价格: {ti['price']}\n"
                if ti.get("market_price"):
                    output += f"  - 市场价: {ti['market_price']}\n"
                if ti.get("sold_info"):
                    output += f"  - 销售信息: {ti['sold_info']}\n"
            if aoi.get("opening_hours"):
                output += f"开放时间: {aoi['opening_hours']}\n"
            elif aoi.get("shop_hours_simple"):
                output += f"当前状态: {aoi['shop_hours_simple']}\n"
            if aoi.get("opening_hours_detail"):
                detail = aoi["opening_hours_detail"]
                if detail.get("common_hours"):
                    output += f"常规时间: {detail['common_hours']}\n"
                if detail.get("festival_hours"):
                    output += f"节假日时间: {detail['festival_hours']}\n"
            if aoi.get("photo_count"):
                output += f"照片数量: {aoi['photo_count']} 张\n"
            features = []
            if aoi.get("has_street_view"):
                features.append("街景")
            if aoi.get("has_indoor_map"):
                features.append("室内地图")
            if aoi.get("has_geo_data"):
                features.append("边界数据")
            if len(features) > 0:
                output += f"可用功能: {', '.join(features)}\n"
            if aoi.get("rankings") and len(aoi["rankings"]) > 0:
                output += "排行榜信息:\n"
                for rank in aoi["rankings"][:3]:
                    if rank.get("name") and rank.get("rank"):
                        output += f"  - {rank['name']}: {rank['rank']}"
                        if rank.get("score"):
                            output += f" (评分: {rank['score']})"
                        output += "\n"
            if aoi.get("events") and len(aoi["events"]) > 0 and aoi["events"][0].get("title"):
                output += "当前活动:\n"
                for event in aoi["events"]:
                    if event.get("title"):
                        output += f"  - {event['title']}"
                        if event.get("start_end"):
                            output += f" ({event['start_end']})"
                        output += "\n"
                        if event.get("content"):
                            output += f"    {event['content']}\n"
            output += f"坐标: 经度 {aoi['center']['lng']}, 纬度 {aoi['center']['lat']}\n"
            output += f"详情链接: {aoi['detail_url']}\n"
            if aoi.get("additional_info") and len(aoi["additional_info"]) > 0:
                output += "其他信息: "
                info = []
                for key, value in aoi["additional_info"].items():
                    if key == 'is_free' and value == 2:
                        info.append("收费景点")
                    elif key == 'is_free' and value == 1:
                        info.append("免费景点")
                    elif key == 'area_id':
                        info.append(f"区域ID: {value}")
                    else:
                        info.append(f"{key}: {value}")
                output += ", ".join(info) + "\n"
            output += "\n"
        if aoiResult.get("boundary"):
            output += "=== 边界信息 ===\n"
            output += f"边界点数: {aoiResult['boundary'].get('point_count', 0)}\n"
            if aoiResult["boundary"].get("center"):
                output += f"中心坐标: 经度 {aoiResult['boundary']['center']['lng']}, 纬度 {aoiResult['boundary']['center']['lat']}\n"
            output += "\n"
    return output


def formatRouteResultAsText(routeResult):
    if not routeResult.get("success"):
        return f"路线规划失败: {routeResult.get('message', '未知错误')}"
    output = "=== 路线规划结果 ===\n"
    if routeResult.get("current_location"):
        output += f"当前位置: 经度 {routeResult['current_location']['lng']}, 纬度 {routeResult['current_location']['lat']}\n"
        if routeResult["current_location"].get("address"):
            output += f"当前地址: {routeResult['current_location']['address']}\n"
    if routeResult.get("destination"):
        output += f"目的地: {routeResult['destination']['name']}\n"
        output += f"目的地址: {routeResult['destination']['address']}\n"
        output += f"目的坐标: 经度 {routeResult['destination']['location']['lng']}, 纬度 {routeResult['destination']['location']['lat']}\n"
    output += "\n"
    if routeResult.get("all_routes"):
        output += "=== 所有交通方式 ===\n"
        if routeResult["all_routes"].get("driving"):
            driving = routeResult["all_routes"]["driving"]
            output += "驾车路线:\n"
            output += f"  距离: {driving['estimated_distance']}\n"
            output += f"  时间: {driving['estimated_duration']}\n"
            output += f"  建议: {driving['suggestion']}\n\n"
        if routeResult["all_routes"].get("walking"):
            walking = routeResult["all_routes"]["walking"]
            output += "步行路线:\n"
            output += f"  距离: {walking['estimated_distance']}\n"
            output += f"  时间: {walking['estimated_duration']}\n"
            output += f"  建议: {walking['suggestion']}\n\n"
        if routeResult["all_routes"].get("transit"):
            transit = routeResult["all_routes"]["transit"]
            output += "公共交通:\n"
            output += f"  距离: {transit['estimated_distance']}\n"
            output += f"  时间: {transit['estimated_duration']}\n"
            output += f"  建议: {transit['suggestion']}\n\n"
    return output


async def getCurrentLocation():
    try:
        logger(LOG_LEVELS['INFO'], "正在获取用户当前位置...")
        locationResult = await Tools.System.getLocation()
        if not locationResult:
            logger(LOG_LEVELS['ERROR'], "获取位置失败:", "未知错误")
            return None
        return {"lng": locationResult.longitude, "lat": locationResult.latitude}
    except Exception as error:
        logger(LOG_LEVELS['ERROR'], "获取位置出错:", str(error))
        return None


def convertMercatorToLatLng(mercatorLng, mercatorLat):
    lng = (mercatorLng / 20037508.34) * 180
    lat = (mercatorLat / 20037508.34) * 180
    lat = (180 / math.pi) * (2 * math.atan(math.exp(lat * math.pi / 180)) - math.pi / 2)
    return {"lng": lng, "lat": lat}


def calculateDistance(lat1, lng1, lat2, lng2):
    R = 6371000
    dLat = (lat2 - lat1) * math.pi / 180
    dLng = (lng2 - lng1) * math.pi / 180
    a = math.sin(dLat / 2) * math.sin(dLat / 2) + \
        math.cos(lat1 * math.pi / 180) * math.cos(lat2 * math.pi / 180) * \
        math.sin(dLng / 2) * math.sin(dLng / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def formatDuration(minutes):
    if minutes < 60:
        return f"约{math.ceil(minutes)}分钟"
    hours = int(minutes / 60)
    remainingMinutes = math.ceil(minutes % 60)
    if remainingMinutes == 0:
        return f"约{hours}小时"
    return f"约{hours}小时{remainingMinutes}分钟"


def estimateDuration(distance, mode):
    minutes = 0
    distanceInKm = distance / 1000
    if mode == "walking":
        minutes = distanceInKm * 15
    elif mode == "transit":
        if distanceInKm < 10:
            minutes = distanceInKm * 4
        elif distanceInKm < 100:
            minutes = distanceInKm * 2
        else:
            minutes = distanceInKm * 1
    else:  # driving
        if distanceInKm < 10:
            minutes = distanceInKm * 2
        elif distanceInKm < 100:
            minutes = distanceInKm * 1.2
        else:
            minutes = distanceInKm * 0.75
    return formatDuration(minutes)


def getSuggestion(distance, mode):
    if distance < 500:
        return "目的地非常近，步行即可到达"
    elif distance < 2000:
        return "距离适中，可步行或乘坐短途交通工具"
    elif distance < 5000:
        return "距离较远，建议使用公共交通工具"
    else:
        return "目的地较远，建议驾车或使用公共交通工具"


async def planRoute(params):
    try:
        currentLocation = await getCurrentLocation()
        if not currentLocation:
            return {"success": False, "message": "无法获取当前位置信息"}

        searchResults = await search_aoi({
            "keyword": params["destination"],
            "city_name": params.get("city_name")
        })

        if not searchResults.get("success") or not searchResults.get("aois") or len(searchResults["aois"]) == 0:
            return {
                "success": False,
                "message": f"未能找到目的地: {params['destination']}",
                "current_location": currentLocation
            }

        destination = searchResults["aois"][0]
        destLocation = destination["center"]
        if not destLocation or not destLocation.get("lng") or not destLocation.get("lat"):
            return {
                "success": False,
                "message": f"目的地坐标信息无效: {params['destination']}",
                "current_location": currentLocation
            }

        destLatLng = convertMercatorToLatLng(destLocation["lng"], destLocation["lat"])
        logger(LOG_LEVELS['DEBUG'], f"目的地 \"{destination['name']}\" 墨卡托坐标:", destLocation)
        logger(LOG_LEVELS['DEBUG'], "转换后的经纬度:", destLatLng)

        distance = calculateDistance(currentLocation["lat"], currentLocation["lng"], destLatLng["lat"], destLatLng["lng"])

        async def getRouteDetailsForMode(mode):
            cityCode = "1"
            if params.get("city_name"):
                cityCode = await getCityCode(params["city_name"])
            navUrl = f"https://api.map.baidu.com/direction?origin={currentLocation['lat']},{currentLocation['lng']}&destination={destLatLng['lat']},{destLatLng['lng']}&mode={mode}&region={cityCode}&output=html"
            return {
                "estimated_distance": f"{(distance / 1000):.2f}公里",
                "estimated_duration": estimateDuration(distance, mode),
                "transport_mode": mode,
                "navigation_url": navUrl,
                "suggestion": getSuggestion(distance, mode)
            }

        logger(LOG_LEVELS['INFO'], "获取所有模式的路线规划...")
        modes = ["driving", "walking", "transit"]
        routesResults = await asyncio.gather(*[getRouteDetailsForMode(mode) for mode in modes])

        all_routes = {
            "driving": routesResults[0],
            "walking": routesResults[1],
            "transit": routesResults[2]
        }

        return {
            "success": True,
            "current_location": currentLocation,
            "destination": {
                "name": destination["name"],
                "address": destination["address"],
                "location": destLatLng
            },
            "all_routes": all_routes
        }
    except Exception as error:
        logger(LOG_LEVELS['ERROR'], "[planRoute] 错误:", error)
        return {"success": False, "message": f"路线规划失败: {error}"}


async def main():
    output = ""
    output += "========== 百度地图格式化函数测试 ==========\n\n"
    try:
        output += "[1] 测试AOI搜索格式化...\n"
        aoiResult = await search_aoi({"keyword": "长安大学", "city_name": "西安"})
        output += formatAoiResultAsText(aoiResult) + "\n"
        await Tools.System.sleep(1000)
        output += "[3] 测试路径规划格式化...\n"
        routeResult = await planRoute({"destination": "长安大学", "city_name": "西安"})
        output += formatRouteResultAsText(routeResult) + "\n"
        output += "========== 格式化测试完成 ==========\n"
        logger(LOG_LEVELS['INFO'], output)
        return output
    except Exception as error:
        return f"测试过程中发生错误: {error}"


def wrap(coreFunction):
    async def wrapped(params):
        result = await coreFunction(params)
        complete(result)
        return result
    return wrapped


# 导出
async def _search_aoi_wrapper(param):
    return formatAoiResultAsText(await search_aoi(param))

async def _planRoute_wrapper(param):
    return formatRouteResultAsText(await planRoute(param))

exports.search_aoi = wrap(_search_aoi_wrapper)
exports.planRoute = wrap(_planRoute_wrapper)
exports.main = wrap(main)
