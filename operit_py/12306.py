# METADATA
# {
#     "name": "12306_ticket",
#     "display_name": {"zh": "12306 拓展", "en": "12306 Extension"},
#     "description": {"zh": "提供12306火车票信息查询功能，包括余票、中转、经停站等。", "en": "Query China Railway 12306 train ticket information, including availability, transfer routes, and stop stations."},
#     "enabledByDefault": True,
#     "category": "Life",
#     "tools": [
#         {"name": "get_current_date", "description": {"zh": "获取当前日期，以上海时区（Asia/Shanghai, UTC+8）为准，返回格式为 'yyyy-MM-dd'。", "en": "Get the current date in the Shanghai timezone (Asia/Shanghai, UTC+8). Returns format 'yyyy-MM-dd'."}, "parameters": []},
#         {"name": "get_stations_code_in_city", "description": {"zh": "通过中文城市名查询该城市所有火车站的名称及其对应的 station_code。", "en": "Given a Chinese city name, list all train stations in that city and their corresponding station_code."}, "parameters": [{"name": "city", "description": {"zh": "中文城市名称，例如：'北京', '上海'", "en": "Chinese city name, e.g. '北京', '上海'."}, "type": "string", "required": True}]},
#         {"name": "get_station_code_of_citys", "description": {"zh": "通过中文城市名查询代表该城市的 station_code。", "en": "Get the representative station_code for a Chinese city name."}, "parameters": [{"name": "citys", "description": {"zh": "要查询的城市，比如'北京'。若要查询多个城市，请用|分割。", "en": "City to query, e.g. '北京'. For multiple cities, separate with |."}, "type": "string", "required": True}]},
#         {"name": "get_station_code_by_names", "description": {"zh": "通过具体的中文车站名查询其 station_code 和车站名。", "en": "Given a specific Chinese station name, return its station_code and station name."}, "parameters": [{"name": "station_names", "description": {"zh": "具体的中文车站名称，例如：'北京南', '上海虹桥'。多个站点用|分割。", "en": "Specific Chinese station names, e.g. '北京南', '上海虹桥'. For multiple stations, separate with |."}, "type": "string", "required": True}]},
#         {"name": "get_station_by_telecode", "description": {"zh": "通过车站的 station_telecode 查询车站的详细信息。", "en": "Query station details by station_telecode."}, "parameters": [{"name": "station_telecode", "description": {"zh": "车站的 station_telecode (3位字母编码)", "en": "Station station_telecode (3-letter code)."}, "type": "string", "required": True}]},
#         {"name": "get_tickets", "description": {"zh": "查询12306余票信息。", "en": "Query 12306 ticket availability."}, "parameters": [
#             {"name": "date", "description": {"zh": "查询日期，格式为 'yyyy-MM-dd'。", "en": "Query date in 'yyyy-MM-dd'."}, "type": "string", "required": True},
#             {"name": "from_station", "description": {"zh": "出发地的 station_code。", "en": "Origin station_code."}, "type": "string", "required": True},
#             {"name": "to_station", "description": {"zh": "到达地的 station_code。", "en": "Destination station_code."}, "type": "string", "required": True},
#             {"name": "train_filter_flags", "description": {"zh": "车次筛选条件，默认为空。可选标志：[G,D,Z,T,K,O,F,S]", "en": "Train filter flags. Options: [G,D,Z,T,K,O,F,S]."}, "type": "string", "required": False},
#             {"name": "sort_flag", "description": {"zh": "排序方式。可选标志：[startTime, arriveTime, duration]", "en": "Sort mode. Options: startTime / arriveTime / duration."}, "type": "string", "required": False},
#             {"name": "sort_reverse", "description": {"zh": "是否逆向排序结果，默认为false。", "en": "Reverse sort order (default: false)."}, "type": "boolean", "required": False},
#             {"name": "limited_num", "description": {"zh": "返回的余票数量限制，默认为0，即不限制。", "en": "Limit number of returned results (default: 0, no limit)."}, "type": "number", "required": False}
#         ]},
#         {"name": "get_interline_tickets", "description": {"zh": "查询12306中转余票信息。尚且只支持查询前十条。", "en": "Query 12306 transfer (interline) ticket availability. Currently only supports the first 10 results."}, "parameters": [
#             {"name": "date", "description": {"zh": "查询日期，格式为 'yyyy-MM-dd'。", "en": "Query date in 'yyyy-MM-dd'."}, "type": "string", "required": True},
#             {"name": "from_station", "description": {"zh": "出发地的 station_code。", "en": "Origin station_code."}, "type": "string", "required": True},
#             {"name": "to_station", "description": {"zh": "到达地的 station_code。", "en": "Destination station_code."}, "type": "string", "required": True},
#             {"name": "middle_station", "description": {"zh": "中转地的 station_code，可选。", "en": "Optional transfer station station_code."}, "type": "string", "required": False},
#             {"name": "show_wz", "description": {"zh": "是否显示无座车，默认不显示无座车。", "en": "Whether to include no-seat tickets (default: false)."}, "type": "boolean", "required": False},
#             {"name": "train_filter_flags", "description": {"zh": "车次筛选条件，默认为空。", "en": "Train filter flags. Default empty."}, "type": "string", "required": False},
#             {"name": "sort_flag", "description": {"zh": "排序方式。", "en": "Sort mode."}, "type": "string", "required": False},
#             {"name": "sort_reverse", "description": {"zh": "是否逆向排序结果，默认为false。", "en": "Reverse sort order (default: false)."}, "type": "boolean", "required": False},
#             {"name": "limited_num", "description": {"zh": "返回的中转余票数量限制，默认为10。", "en": "Limit number of returned results (default: 10)."}, "type": "number", "required": False}
#         ]},
#         {"name": "get_train_route_stations", "description": {"zh": "查询特定列车车次在指定区间内的途径车站、到站时间、出发时间及停留时间等详细经停信息。", "en": "Query detailed stop information for a specific train within a segment."}, "parameters": [
#             {"name": "train_no", "description": {"zh": "要查询的实际车次编号 train_no，例如 '240000G10336'。", "en": "Actual train number train_no, e.g. '240000G10336'."}, "type": "string", "required": True},
#             {"name": "from_station_telecode", "description": {"zh": "出发站的 station_telecode (3位字母编码)。", "en": "station_telecode (3-letter code) of the origin station."}, "type": "string", "required": True},
#             {"name": "to_station_telecode", "description": {"zh": "到达站的 station_telecode (3位字母编码)。", "en": "station_telecode (3-letter code) of the destination station."}, "type": "string", "required": True},
#             {"name": "depart_date", "description": {"zh": "列车从出发站出发的日期 (格式: yyyy-MM-dd)。", "en": "Departure date from the origin station (format: yyyy-MM-dd)."}, "type": "string", "required": True}
#         ]}
#     ]
# }

import json
import re
import time
import math
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, unquote

Error = Exception

API_BASE = 'https://kyfw.12306.cn'
WEB_URL = 'https://www.12306.cn/index/'
LCQUERY_INIT_URL = 'https://kyfw.12306.cn/otn/lcQuery/init'

LCQUERY_PATH = None
MISSING_STATIONS = [
    {"station_id": "@cdd", "station_name": "成  都东", "station_code": "WEI", "station_pinyin": "chengdudong", "station_short": "cdd", "station_index": "", "code": "1707", "city": "成都", "r1": "", "r2": ""},
]

STATIONS = None
CITY_STATIONS = None
CITY_CODES = None
NAME_STATIONS = None

SEAT_SHORT_TYPES = {"swz": "商务座", "tz": "特等座", "zy": "一等座", "ze": "二等座", "gr": "高软卧", "srrb": "动卧", "rw": "软卧", "yw": "硬卧", "rz": "软座", "yz": "硬座", "wz": "无座", "qt": "其他", "gg": "", "yb": ""}
SEAT_TYPES = {
    '9': {"name": "商务座", "short": "swz"}, 'P': {"name": "特等座", "short": "tz"}, 'M': {"name": "一等座", "short": "zy"}, 'D': {"name": "优选一等座", "short": "zy"}, 'O': {"name": "二等座", "short": "ze"}, 'S': {"name": "二等包座", "short": "ze"}, '6': {"name": "高级软卧", "short": "gr"}, 'A': {"name": "高级动卧", "short": "gr"}, '4': {"name": "软卧", "short": "rw"}, 'I': {"name": "一等卧", "short": "rw"}, 'F': {"name": "动卧", "short": "rw"}, '3': {"name": "硬卧", "short": "yw"}, 'J': {"name": "二等卧", "short": "yw"}, '2': {"name": "软座", "short": "rz"}, '1': {"name": "硬座", "short": "yz"}, 'W': {"name": "无座", "short": "wz"}, 'WZ': {"name": "无座", "short": "wz"}, 'H': {"name": "其他", "short": "qt"},
}
DW_FLAGS = ['智能动车组', '复兴号', '静音车厢', '温馨动卧', '动感号', '支持选铺', '老年优惠']

TicketDataKeys = [
    'secret_Sstr', 'button_text_info', 'train_no', 'station_train_code', 'start_station_telecode',
    'end_station_telecode', 'from_station_telecode', 'to_station_telecode', 'start_time', 'arrive_time',
    'lishi', 'canWebBuy', 'yp_info', 'start_train_date', 'train_seat_feature',
    'location_code', 'from_station_no', 'to_station_no', 'is_support_card', 'controlled_train_flag',
    'gg_num', 'gr_num', 'qt_num', 'rw_num', 'rz_num',
    'tz_num', 'wz_num', 'yb_num', 'yw_num', 'yz_num',
    'ze_num', 'zy_num', 'swz_num', 'srrb_num', 'yp_ex',
    'seat_types', 'exchange_train_flag', 'houbu_train_flag', 'houbu_seat_limit', 'yp_info_new',
    '40', '41', '42', '43', '44',
    '45', 'dw_flag', '47', 'stopcheckTime', 'country_flag',
    'local_arrive_time', 'local_start_time', '52', 'bed_level_info', 'seat_discount_info',
    'sale_time', '56',
]

StationDataKeys = [
    'station_id', 'station_name', 'station_code', 'station_pinyin', 'station_short',
    'station_index', 'code', 'city', 'r1', 'r2',
]

client = OkHttp.newClient()
initPromise = None


def formatDate(date):
    year = date.year
    month = str(date.month).zfill(2)
    day = str(date.day).zfill(2)
    return f"{year}-{month}-{day}"


def parseDate(dateStr):
    year = int(dateStr[0:4])
    month = int(dateStr[4:6])
    day = int(dateStr[6:8])
    return datetime(year, month, day, tzinfo=timezone.utc)


def getCurrentShanghaiDate():
    now = datetime.now(timezone.utc)
    return now + timedelta(hours=8)


def checkDate(dateStr):
    todayInShanghai = getCurrentShanghaiDate()
    todayInShanghai = todayInShanghai.replace(hour=0, minute=0, second=0, microsecond=0)
    parts = [int(p) for p in dateStr.split('-')]
    inputDate = datetime(parts[0], parts[1], parts[2], tzinfo=timezone.utc)
    return inputDate >= todayInShanghai


def parseCookies(cookies):
    cookieRecord = {}
    if not cookies:
        return cookieRecord
    for cookie in cookies:
        keyValuePart = cookie.split(';')[0]
        if '=' in keyValuePart:
            key, value = keyValuePart.split('=', 1)
            if key and value:
                cookieRecord[key.strip()] = value.strip()
    return cookieRecord


def formatCookies(cookies):
    return '; '.join([f"{k}={v}" for k, v in cookies.items()])


async def getCookie():
    url = f"{API_BASE}/otn/leftTicket/init"
    try:
        response = await client.newRequest().url(url).build().execute()
        cookieHeader = None
        if response.headers:
            cookieHeader = response.headers.get('set-cookie') or response.headers.get('Set-Cookie')
        if cookieHeader:
            parsed = parseCookies(cookieHeader if isinstance(cookieHeader, list) else [cookieHeader])
            if len(parsed) > 0:
                return parsed
        return {}
    except Exception as error:
        console.error('Error getting 12306 cookie:', error)
        return None


async def make12306Request(url, params=None, headers=None):
    if params is None:
        params = {}
    if headers is None:
        headers = {}
    queryString = '&'.join([f"{quote(k)}={quote(str(v))}" for k, v in params.items()])
    fullUrl = f"{url}?{queryString}" if queryString else url
    try:
        finalHeaders = dict(headers)
        if finalHeaders.get('Cookie') == '':
            del finalHeaders['Cookie']
        request = client.newRequest().url(fullUrl).method("GET").headers(finalHeaders)
        response = await request.build().execute()
        if not response.isSuccessful():
            raise Error(f"HTTP error! status: {response.statusCode}")
        return json.loads(response.content)
    except Exception as error:
        console.error(f"Error making 12306 request to {fullUrl}:", error)
        return None


async def make12306RequestHtml(url):
    try:
        request = client.newRequest().url(url).method("GET")
        response = await request.build().execute()
        if not response.isSuccessful():
            raise Error(f"HTTP error! status: {response.statusCode}")
        return response.content
    except Exception as error:
        console.error(f"Error fetching HTML from {url}:", error)
        return None


def parseTicketsData(rawData):
    result = []
    for item in rawData:
        values = item.split('|')
        entry = {}
        for index, key in enumerate(TicketDataKeys):
            entry[key] = values[index] if index < len(values) else ""
        result.append(entry)
    return result


def extractPrices(yp_info, seat_discount_info, ticketData):
    PRICE_STR_LENGTH = 10
    DISCOUNT_STR_LENGTH = 5
    prices = []
    discounts = {}
    for i in range(int(len(seat_discount_info) / DISCOUNT_STR_LENGTH)):
        discount_str = seat_discount_info[i * DISCOUNT_STR_LENGTH:(i + 1) * DISCOUNT_STR_LENGTH]
        if len(discount_str) > 0:
            discounts[discount_str[0]] = int(discount_str[1:])

    for i in range(int(len(yp_info) / PRICE_STR_LENGTH)):
        price_str = yp_info[i * PRICE_STR_LENGTH:(i + 1) * PRICE_STR_LENGTH]
        if len(price_str) < 10:
            continue
        if int(price_str[6:10]) >= 3000:
            seat_type_code = 'W'
        elif price_str[0] not in SEAT_TYPES:
            seat_type_code = 'H'
        else:
            seat_type_code = price_str[0]
        seat_type = SEAT_TYPES.get(seat_type_code, {"name": "其他", "short": "qt"})
        price = int(price_str[1:6]) / 10
        discount = discounts.get(seat_type_code)
        prices.append({
            "seat_name": seat_type["name"],
            "short": seat_type["short"],
            "seat_type_code": seat_type_code,
            "num": ticketData.get(f"{seat_type['short']}_num", ""),
            "price": price,
            "discount": discount,
        })
    return prices


def extractDWFlags(dw_flag_str):
    dwFlagList = dw_flag_str.split('#')
    result = []
    if len(dwFlagList) > 0 and '5' == dwFlagList[0]:
        result.append(DW_FLAGS[0])
    if len(dwFlagList) > 1 and '1' == dwFlagList[1]:
        result.append(DW_FLAGS[1])
    if len(dwFlagList) > 2:
        if dwFlagList[2][:1] == 'Q':
            result.append(DW_FLAGS[2])
        elif dwFlagList[2][:1] == 'R':
            result.append(DW_FLAGS[3])
    if len(dwFlagList) > 5 and 'D' == dwFlagList[5]:
        result.append(DW_FLAGS[4])
    if len(dwFlagList) > 6 and 'z' != dwFlagList[6]:
        result.append(DW_FLAGS[5])
    if len(dwFlagList) > 7 and 'z' != dwFlagList[7]:
        result.append(DW_FLAGS[6])
    return result


def parseTicketsInfo(ticketsData, map_):
    result = []
    for ticket in ticketsData:
        prices = extractPrices(ticket.get("yp_info_new", ""), ticket.get("seat_discount_info", ""), ticket)
        dw_flag = extractDWFlags(ticket.get("dw_flag", ""))
        startDate = parseDate(ticket.get("start_train_date", "20000101"))
        startParts = [int(x) for x in ticket.get("start_time", "00:00").split(':')]
        durationParts = [int(x) for x in ticket.get("lishi", "00:00").split(':')]
        startHours, startMinutes = startParts[0], startParts[1]
        durationHours, durationMinutes = durationParts[0], durationParts[1]
        arriveDate = startDate + timedelta(hours=startHours + durationHours, minutes=startMinutes + durationMinutes)
        result.append({
            "train_no": ticket.get("train_no", ""),
            "start_date": formatDate(startDate),
            "arrive_date": formatDate(arriveDate),
            "start_train_code": ticket.get("station_train_code", ""),
            "start_time": ticket.get("start_time", ""),
            "arrive_time": ticket.get("arrive_time", ""),
            "lishi": ticket.get("lishi", ""),
            "from_station": map_.get(ticket.get("from_station_telecode", ""), ""),
            "to_station": map_.get(ticket.get("to_station_telecode", ""), ""),
            "from_station_telecode": ticket.get("from_station_telecode", ""),
            "to_station_telecode": ticket.get("to_station_telecode", ""),
            "prices": prices,
            "dw_flag": dw_flag,
        })
    return result


def formatTicketStatus(num):
    if num and re.match(r'^\d+$', str(num)):
        count = int(num)
        return '无票' if count == 0 else f'剩余{count}张票'
    if num in ('有', '充足'):
        return '有票'
    if num in ('无', '--', ''):
        return '无票'
    if num == '候补':
        return '无票需候补'
    return f'{num}票'


def formatTicketsInfo(ticketsInfo):
    if len(ticketsInfo) == 0:
        return '没有查询到相关车次信息'
    result = '车次 | 出发站 -> 到达站 | 出发时间 -> 到达时间 | 历时\n'
    for ticketInfo in ticketsInfo:
        infoStr = f"{ticketInfo['start_train_code']}(实际车次train_no: {ticketInfo['train_no']}) {ticketInfo['from_station']}(telecode: {ticketInfo['from_station_telecode']}) -> {ticketInfo['to_station']}(telecode: {ticketInfo['to_station_telecode']}) {ticketInfo['start_time']} -> {ticketInfo['arrive_time']} 历时：{ticketInfo['lishi']}"
        for price in ticketInfo["prices"]:
            infoStr += f"\n- {price['seat_name']}: {formatTicketStatus(price['num'])} {price['price']}元"
        result += f"{infoStr}\n"
    return result


def trainFilterG(t):
    return t["start_train_code"].startswith('G') or t["start_train_code"].startswith('C')


def trainFilterD(t):
    return t["start_train_code"].startswith('D')


def trainFilterZ(t):
    return t["start_train_code"].startswith('Z')


def trainFilterT(t):
    return t["start_train_code"].startswith('T')


def trainFilterK(t):
    return t["start_train_code"].startswith('K')


def trainFilterO(t):
    return not re.match(r'^[GDZTK]', t["start_train_code"])


def trainFilterF(t):
    if "dw_flag" in t:
        return '复兴号' in t["dw_flag"]
    return '复兴号' in t["ticketList"][0]["dw_flag"]


def trainFilterS(t):
    if "dw_flag" in t:
        return '智能动车组' in t["dw_flag"]
    return '智能动车组' in t["ticketList"][0]["dw_flag"]


TRAIN_FILTERS = {'G': trainFilterG, 'D': trainFilterD, 'Z': trainFilterZ, 'T': trainFilterT, 'K': trainFilterK, 'O': trainFilterO, 'F': trainFilterF, 'S': trainFilterS}


def timeCompareStartTime(a, b):
    da = datetime.strptime(f"{a['start_date']} {a['start_time']}", "%Y-%m-%d %H:%M")
    db = datetime.strptime(f"{b['start_date']} {b['start_time']}", "%Y-%m-%d %H:%M")
    return (da - db).total_seconds() * 1000


def timeCompareArriveTime(a, b):
    da = datetime.strptime(f"{a['arrive_date']} {a['arrive_time']}", "%Y-%m-%d %H:%M")
    db = datetime.strptime(f"{b['arrive_date']} {b['arrive_time']}", "%Y-%m-%d %H:%M")
    return (da - db).total_seconds() * 1000


def timeCompareDuration(a, b):
    hA, mA = [int(x) for x in a["lishi"].split(':')]
    hB, mB = [int(x) for x in b["lishi"].split(':')]
    return (hA * 60 + mA) - (hB * 60 + mB)


TIME_COMPARETOR = {"startTime": timeCompareStartTime, "arriveTime": timeCompareArriveTime, "duration": timeCompareDuration}


def filterTicketsInfo(ticketsInfo, trainFilterFlags, sortFlag='', sortReverse=False, limitedNum=0):
    if trainFilterFlags:
        flags = list(trainFilterFlags)
        result = [t for t in ticketsInfo if any(TRAIN_FILTERS.get(f, lambda x: False)(t) for f in flags)]
    else:
        result = list(ticketsInfo)
    if sortFlag in TIME_COMPARETOR:
        result.sort(key=lambda x: x)
        # Python sort with custom comparator
        import functools
        result = sorted(result, key=functools.cmp_to_key(TIME_COMPARETOR[sortFlag]))
        if sortReverse:
            result.reverse()
    return result[:limitedNum] if limitedNum > 0 else result


def parseRouteStationsInfo(routeStationsData):
    result = []
    for index, routeStationData in enumerate(routeStationsData):
        result.append({
            "arrive_time": routeStationData.get("start_time") if index == 0 else routeStationData.get("arrive_time", ""),
            "station_name": routeStationData.get("station_name", ""),
            "stopover_time": routeStationData.get("stopover_time", ""),
            "station_no": int(routeStationData.get("station_no", 0)),
        })
    return result


def parseInterlinesTicketInfo(interlineTicketsData):
    result = []
    for ticket in interlineTicketsData:
        prices = extractPrices(ticket.get("yp_info", ""), ticket.get("seat_discount_info", ""), ticket)
        startDate = parseDate(ticket.get("start_train_date", "20000101"))
        startParts = [int(x) for x in ticket.get("start_time", "00:00").split(':')]
        durationParts = [int(x) for x in ticket.get("lishi", "00:00").split(':')]
        startHours, startMinutes = startParts[0], startParts[1]
        durationHours, durationMinutes = durationParts[0], durationParts[1]
        arriveDate = startDate + timedelta(hours=startHours + durationHours, minutes=startMinutes + durationMinutes)
        result.append({
            "train_no": ticket.get("train_no", ""),
            "start_train_code": ticket.get("station_train_code", ""),
            "start_date": formatDate(startDate),
            "arrive_date": formatDate(arriveDate),
            "start_time": ticket.get("start_time", ""),
            "arrive_time": ticket.get("arrive_time", ""),
            "lishi": ticket.get("lishi", ""),
            "from_station": ticket.get("from_station_name", ""),
            "to_station": ticket.get("to_station_name", ""),
            "from_station_telecode": ticket.get("from_station_telecode", ""),
            "to_station_telecode": ticket.get("to_station_telecode", ""),
            "prices": prices,
            "dw_flag": extractDWFlags(ticket.get("dw_flag", "")),
        })
    return result


def extractLishi(all_lishi):
    match = re.search(r'(?:(\d+)小时)?(\d+)分钟', all_lishi)
    if not match:
        return '00:00'
    hours = (match.group(1) or '0').zfill(2)
    minutes = (match.group(2) or '0').zfill(2)
    return f"{hours}:{minutes}"


def parseInterlinesInfo(interlineData):
    result = []
    for ticket in interlineData:
        fullList = ticket.get("fullList") or []
        result.append({
            "lishi": extractLishi(ticket.get("all_lishi", "")),
            "start_time": ticket.get("start_time", ""),
            "start_date": ticket.get("train_date", ""),
            "middle_date": ticket.get("middle_date", ""),
            "arrive_date": ticket.get("arrive_date", ""),
            "arrive_time": ticket.get("arrive_time", ""),
            "from_station_code": ticket.get("from_station_code", ""),
            "from_station_name": ticket.get("from_station_name", ""),
            "middle_station_code": ticket.get("middle_station_code", ""),
            "middle_station_name": ticket.get("middle_station_name", ""),
            "end_station_code": ticket.get("end_station_code", ""),
            "end_station_name": ticket.get("end_station_name", ""),
            "start_train_code": fullList[0].get("station_train_code", "") if fullList else "",
            "first_train_no": ticket.get("first_train_no", ""),
            "second_train_no": ticket.get("second_train_no", ""),
            "train_count": ticket.get("train_count", 0),
            "ticketList": parseInterlinesTicketInfo(fullList),
            "same_station": ticket.get("same_station") == '0',
            "same_train": ticket.get("same_train") == 'Y',
            "wait_time": ticket.get("wait_time", ""),
        })
    return result


def formatInterlinesInfo(interlinesInfo):
    if len(interlinesInfo) == 0:
        return '没有查询到相关的中转车次信息'
    result = '出发时间 -> 到达时间 | 出发车站 -> 中转车站 -> 到达车站 | 换乘标志 | 换乘等待时间 | 总历时\n\n'
    for info in interlinesInfo:
        result += f"{info['start_date']} {info['start_time']} -> {info['arrive_date']} {info['arrive_time']} | "
        result += f"{info['from_station_name']} -> {info['middle_station_name']} -> {info['end_station_name']} | "
        transfer = '同车换乘' if info['same_train'] else ('同站换乘' if info['same_station'] else '换站换乘')
        result += f"{transfer} | {info['wait_time']} | {info['lishi']}\n\n"
        result += '\t' + formatTicketsInfo(info["ticketList"]).replace('\n', '\n\t') + '\n'
    return result


def parseStationsData(rawData):
    result = {}
    dataArray = rawData.split('|')
    for i in range(0, len(dataArray), 10):
        group = dataArray[i:i + 10]
        if len(group) < 10:
            continue
        station = {}
        for index, key in enumerate(StationDataKeys):
            station[key] = group[index]
        if station.get("station_code"):
            result[station["station_code"]] = station
    return result


async def getStationsInternal():
    stationNameJSUrl = "https://kyfw.12306.cn/otn/resources/js/framework/station_name.js"
    stationNameJS = await make12306RequestHtml(stationNameJSUrl)
    if not stationNameJS:
        raise Error('Error: get station name js file content failed.')
    rawDataMatch = re.search(r"var station_names\s*=\s*'(.*?)';", stationNameJS)
    if not rawDataMatch:
        raise Error('Error: could not find station data in JS file.')
    rawData = rawDataMatch.group(1)
    stationsData = parseStationsData(rawData)
    for station in MISSING_STATIONS:
        if station["station_code"] not in stationsData:
            stationsData[station["station_code"]] = station
    return stationsData


async def getLCQueryPath():
    html = await make12306RequestHtml(LCQUERY_INIT_URL)
    if html is None:
        raise Error('Error: get 12306 web page for LCQuery path failed.')
    match = re.search(r"var lc_search_url = '(.+?)'", html)
    if match is None:
        raise Error('Error: get LCQuery path failed.')
    return match.group(1)


async def init():
    global STATIONS, CITY_STATIONS, CITY_CODES, NAME_STATIONS, LCQUERY_PATH, initPromise
    if initPromise is not None:
        return
    if STATIONS is not None:
        return
    try:
        STATIONS = await getStationsInternal()
        LCQUERY_PATH = await getLCQueryPath()
        CITY_STATIONS = {}
        for station in STATIONS.values():
            city = station["city"]
            if city not in CITY_STATIONS:
                CITY_STATIONS[city] = []
            CITY_STATIONS[city].append({"station_code": station["station_code"], "station_name": station["station_name"]})
        CITY_CODES = {}
        for city, stations in CITY_STATIONS.items():
            for station in stations:
                if station["station_name"] == city:
                    CITY_CODES[city] = station
                    break
        NAME_STATIONS = {}
        for station in STATIONS.values():
            NAME_STATIONS[station["station_name"]] = {"station_code": station["station_code"], "station_name": station["station_name"]}
    except Exception as e:
        initPromise = None
        raise e


async def get_current_date(params):
    now = getCurrentShanghaiDate()
    return formatDate(now)


async def get_stations_code_in_city(params):
    await init()
    if params["city"] not in CITY_STATIONS:
        raise Error('City not found.')
    return CITY_STATIONS[params["city"]]


async def get_station_code_of_citys(params):
    await init()
    result = {}
    for city in params["citys"].split('|'):
        if city not in CITY_CODES:
            result[city] = {"error": "未检索到城市。"}
        else:
            result[city] = CITY_CODES[city]
    return result


async def get_station_code_by_names(params):
    await init()
    result = {}
    for stationName in params["station_names"].split('|'):
        sn = stationName[:-1] if stationName.endswith('站') else stationName
        if sn not in NAME_STATIONS:
            result[stationName] = {"error": "未检索到车站。"}
        else:
            result[stationName] = NAME_STATIONS[sn]
    return result


async def get_station_by_telecode(params):
    await init()
    if params["station_telecode"] not in STATIONS:
        raise Error('Station not found.')
    return STATIONS[params["station_telecode"]]


async def get_tickets(params):
    await init()
    if not checkDate(params["date"]):
        raise Error('The date cannot be earlier than today.')
    if params["from_station"] not in STATIONS or params["to_station"] not in STATIONS:
        raise Error('Station not found.')
    queryParams = {
        'leftTicketDTO.train_date': params["date"],
        'leftTicketDTO.from_station': params["from_station"],
        'leftTicketDTO.to_station': params["to_station"],
        'purpose_codes': 'ADULT',
    }
    queryUrl = f"{API_BASE}/otn/leftTicket/query"
    cookies = await getCookie()
    if not cookies:
        raise Error('Get cookie failed. Check your network.')
    response = await make12306Request(queryUrl, queryParams, {"Cookie": formatCookies(cookies)})
    if not response or not response.get("data") or not response["data"].get("result"):
        raise Error('Get tickets data failed.')
    ticketsData = parseTicketsData(response["data"]["result"])
    ticketsInfo = parseTicketsInfo(ticketsData, response["data"]["map"])
    filteredTicketsInfo = filterTicketsInfo(ticketsInfo, params.get("train_filter_flags") or '', params.get("sort_flag", ''), params.get("sort_reverse", False), params.get("limited_num", 0))
    return formatTicketsInfo(filteredTicketsInfo)


async def get_interline_tickets(params):
    await init()
    if not checkDate(params["date"]):
        raise Error('The date cannot be earlier than today.')
    if params["from_station"] not in STATIONS or params["to_station"] not in STATIONS:
        raise Error('Station not found.')
    cookies = await getCookie()
    if not cookies:
        raise Error('Get cookie failed. Check your network.')
    limited_num = params.get("limited_num") or 10
    interlineData = []
    queryParams = {
        'train_date': params["date"],
        'from_station_telecode': params["from_station"],
        'to_station_telecode': params["to_station"],
        'middle_station': params.get("middle_station") or '',
        'result_index': '0',
        'can_query': 'Y',
        'isShowWZ': 'Y' if params.get("show_wz") else 'N',
        'purpose_codes': '00',
        'channel': 'E',
    }
    while len(interlineData) < limited_num:
        response = await make12306Request(f"{API_BASE}{LCQUERY_PATH}", queryParams, {"Cookie": formatCookies(cookies)})
        if not response:
            raise Error('Request interline tickets data failed.')
        if isinstance(response.get("data"), str):
            return f"很抱歉，未查到相关的列车余票。({response.get('errorMsg')})"
        middleList = response["data"].get("middleList") or []
        interlineData.extend(middleList)
        if response["data"].get("can_query") == 'N' or not middleList:
            break
        queryParams['result_index'] = str(response["data"]["result_index"])
    interlineTicketsInfo = parseInterlinesInfo(interlineData)
    filtered = filterTicketsInfo(interlineTicketsInfo, params.get("train_filter_flags") or '', params.get("sort_flag", ''), params.get("sort_reverse", False), limited_num)
    return formatInterlinesInfo(filtered)


async def get_train_route_stations(params):
    await init()
    queryParams = {
        'train_no': params["train_no"],
        'from_station_telecode': params["from_station_telecode"],
        'to_station_telecode': params["to_station_telecode"],
        'depart_date': params["depart_date"],
    }
    queryUrl = f"{API_BASE}/otn/czxx/queryByTrainNo"
    cookies = await getCookie()
    if not cookies:
        raise Error('Get cookie failed.')
    response = await make12306Request(queryUrl, queryParams, {"Cookie": formatCookies(cookies)})
    if not response or not response.get("data") or not response["data"].get("data"):
        raise Error('Get train route stations failed.')
    routeStationsInfo = parseRouteStationsInfo(response["data"]["data"])
    if len(routeStationsInfo) == 0:
        return '未查询到相关车次信息。'
    return routeStationsInfo


async def wrap(func, params, successMessage, failMessage):
    try:
        result = await func(params)
        complete({"success": True, "message": successMessage, "data": result})
    except Exception as error:
        console.error(f"Function {func.__name__} failed! Error: {str(error)}")
        import traceback
        complete({"success": False, "message": f"{failMessage}: {str(error)}", "error_stack": traceback.format_exc()})


async def main():
    console.log("--- 开始测试 12306 工具包 ---")
    try:
        await init()
        console.log("\n[1/8] 测试 get_current_date...")
        dateResult = await get_current_date({})
        console.log("测试结果:", json.dumps(dateResult, indent=2, ensure_ascii=False))
        testDate = dateResult
        console.log("\n[2/8] 测试 get_stations_code_in_city (北京)...")
        cityStations = await get_stations_code_in_city({"city": "北京"})
        console.log("测试结果:", json.dumps(cityStations, indent=2, ensure_ascii=False))
        console.log("\n[3/8] 测试 get_station_code_of_citys (北京|上海)...")
        cityCodesResult = await get_station_code_of_citys({"citys": "北京|上海"})
        console.log("测试结果:", json.dumps(cityCodesResult, indent=2, ensure_ascii=False))
        console.log("\n--- 12306 工具包测试完成 ---")
        complete({"success": True, "message": "所有测试已成功或已记录错误。"})
    except Exception as e:
        console.error("测试主函数出现错误:", str(e))
        complete({"success": False, "message": f"测试失败: {str(e)}"})


async def _get_current_date(params):
    await wrap(get_current_date, params, '获取当前日期成功', '获取当前日期失败')


async def _get_stations_code_in_city(params):
    await wrap(get_stations_code_in_city, params, '查询成功', '查询失败')


async def _get_station_code_of_citys(params):
    await wrap(get_station_code_of_citys, params, '查询成功', '查询失败')


async def _get_station_code_by_names(params):
    await wrap(get_station_code_by_names, params, '查询成功', '查询失败')


async def _get_station_by_telecode(params):
    await wrap(get_station_by_telecode, params, '查询成功', '查询失败')


async def _get_tickets(params):
    await wrap(get_tickets, params, '查询余票成功', '查询余票失败')


async def _get_interline_tickets(params):
    await wrap(get_interline_tickets, params, '查询中转票成功', '查询中转票失败')


async def _get_train_route_stations(params):
    await wrap(get_train_route_stations, params, '查询经停站成功', '查询经停站失败')


exports.get_current_date = _get_current_date
exports.get_stations_code_in_city = _get_stations_code_in_city
exports.get_station_code_of_citys = _get_station_code_of_citys
exports.get_station_code_by_names = _get_station_code_by_names
exports.get_station_by_telecode = _get_station_by_telecode
exports.get_tickets = _get_tickets
exports.get_interline_tickets = _get_interline_tickets
exports.get_train_route_stations = _get_train_route_stations
exports.main = main
