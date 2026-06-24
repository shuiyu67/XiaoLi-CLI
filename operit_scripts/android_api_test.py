# METADATA
# {
#     "name": "android_api_test",
#     "display_name": {"zh": "Android API 转译测试", "en": "Android API Translation Test"},
#     "description": {"zh": "测试 Android-pyApi 能否成功转译调用安卓 API 的脚本", "en": "Test if Android-pyApi can translate Android API scripts"},
#     "enabledByDefault": true,
#     "category": "Test",
#     "tools": [
#         {"name": "test_intent", "description": {"zh": "测试 Intent API", "en": "Test Intent API"}, "parameters": []},
#         {"name": "test_uri", "description": {"zh": "测试 Uri API", "en": "Test Uri API"}, "parameters": []},
#         {"name": "test_bundle", "description": {"zh": "测试 Bundle API", "en": "Test Bundle API"}, "parameters": []},
#         {"name": "test_file_io", "description": {"zh": "测试 java.io.File API", "en": "Test java.io.File API"}, "parameters": []},
#         {"name": "test_json", "description": {"zh": "测试 JSONObject API", "en": "Test JSONObject API"}, "parameters": []},
#         {"name": "test_collections", "description": {"zh": "测试 ArrayList/HashMap API", "en": "Test ArrayList/HashMap API"}, "parameters": []},
#         {"name": "test_environment", "description": {"zh": "测试 Environment API", "en": "Test Environment API"}, "parameters": []},
#         {"name": "test_log", "description": {"zh": "测试 Log API", "en": "Test Log API"}, "parameters": []},
#         {"name": "test_settings", "description": {"zh": "测试 Settings API", "en": "Test Settings API"}, "parameters": []},
#         {"name": "test_bitmap", "description": {"zh": "测试 Bitmap/Canvas/Color API", "en": "Test Bitmap/Canvas/Color API"}, "parameters": []},
#         {"name": "test_string_builder", "description": {"zh": "测试 StringBuilder API", "en": "Test StringBuilder API"}, "parameters": []},
#         {"name": "test_content_values", "description": {"zh": "测试 ContentValues API", "en": "Test ContentValues API"}, "parameters": []},
#         {"name": "test_run_all", "description": {"zh": "运行全部测试", "en": "Run all tests"}, "parameters": []}
#     ]
# }

import os
import sys
import json
import tempfile

async def test_intent(params):
    """测试 Intent — Android 最核心的 API"""
    results = []
    
    # 创建 Intent
    intent = Intent("android.intent.action.VIEW")
    results.append(f"Intent action: {intent.getAction()}")
    
    # 设置 Data Uri
    intent.setData(Uri.parse("https://www.example.com/path?key=value"))
    results.append(f"Intent data: {intent.getData()}")
    
    # 设置 Package
    intent.setPackage("com.example.app")
    results.append(f"Intent package: {intent.getPackage()}")
    
    # 添加 Category
    intent.addCategory("android.intent.category.DEFAULT")
    results.append(f"Intent categories: {intent.getCategories()}")
    
    # 设置 Flag
    intent.setFlags(0x10000000)  # FLAG_ACTIVITY_NEW_TASK
    results.append(f"Intent flags: {hex(intent.getFlags())}")
    
    # 添加 Extra
    intent.putExtra("extra_key", "extra_value")
    intent.putExtra("extra_int", 42)
    results.append(f"Intent extra string: {intent.getStringExtra('extra_key')}")
    results.append(f"Intent extra int: {intent.getIntExtra('extra_int', 0)}")
    
    return {"success": True, "results": results}

async def test_uri(params):
    """测试 Uri — Android URI 解析"""
    results = []
    
    uri = Uri.parse("content://com.example.provider/items/42?sort=desc#fragment")
    results.append(f"scheme: {uri.getScheme()}")
    results.append(f"authority: {uri.getAuthority()}")
    results.append(f"host: {uri.getHost()}")
    results.append(f"path: {uri.getPath()}")
    results.append(f"query: {uri.getQuery()}")
    results.append(f"fragment: {uri.getFragment()}")
    results.append(f"lastPathSegment: {uri.getLastPathSegment()}")
    
    # 测试 Uri.Builder
    builder = Uri.Builder()
    builder.scheme("https")
    builder.authority("api.example.com")
    builder.appendPath("v1")
    builder.appendPath("users")
    builder.appendQueryParameter("limit", "10")
    built_uri = builder.build()
    results.append(f"built uri: {built_uri.toString() if hasattr(built_uri, 'toString') else str(built_uri)}")
    
    return {"success": True, "results": results}

async def test_bundle(params):
    """测试 Bundle — Android 数据传递"""
    results = []
    
    bundle = Bundle()
    bundle.putString("name", "Test User")
    bundle.putInt("age", 25)
    bundle.putBoolean("active", True)
    bundle.putDouble("score", 95.5)
    
    results.append(f"name: {bundle.getString('name')}")
    results.append(f"age: {bundle.getInt('age')}")
    results.append(f"active: {bundle.getBoolean('active')}")
    results.append(f"score: {bundle.getDouble('score')}")
    
    # 测试 keySet
    keys = bundle.keySet()
    results.append(f"keys: {keys}")
    
    # 测试 containsKey
    results.append(f"has 'name': {bundle.containsKey('name')}")
    results.append(f"has 'missing': {bundle.containsKey('missing')}")
    
    return {"success": True, "results": results}

async def test_file_io(params):
    """测试 java.io.File — 文件操作"""
    results = []
    
    # 创建 File 对象
    f = File(tempfile.gettempdir(), "operit_test.txt")
    results.append(f"path: {f.getPath()}")
    results.append(f"absolutePath: {f.getAbsolutePath()}")
    results.append(f"name: {f.getName()}")
    results.append(f"parent: {f.getParent()}")
    results.append(f"exists before: {f.exists()}")
    
    # 创建文件
    f.createNewFile()
    results.append(f"exists after create: {f.exists()}")
    
    # 写入内容 (用 Python open)
    with open(f.getAbsolutePath(), "w") as fh:
        fh.write("Hello from Android-pyApi!")
    
    # 读取
    with open(f.getAbsolutePath(), "r") as fh:
        content = fh.read()
    results.append(f"content: {content}")
    
    # 文件大小
    results.append(f"length: {f.length()}")
    
    # 删除
    f.delete()
    results.append(f"exists after delete: {f.exists()}")
    
    # 测试目录
    d = File(tempfile.gettempdir(), "operit_test_dir")
    d.mkdirs()
    results.append(f"dir exists: {d.exists()}")
    results.append(f"isDirectory: {d.isDirectory()}")
    d.delete()
    
    return {"success": True, "results": results}

async def test_json(params):
    """测试 JSONObject/JSONArray — JSON 处理"""
    results = []
    
    # 创建 JSONObject
    obj = JSONObject()
    obj.put("name", "Test")
    obj.put("version", 3)
    obj.put("active", True)
    
    # 创建 JSONArray
    arr = JSONArray()
    arr.put("item1")
    arr.put("item2")
    arr.put("item3")
    obj.put("items", arr)
    
    # 读取
    results.append(f"name: {obj.getString('name')}")
    results.append(f"version: {obj.getInt('version')}")
    results.append(f"active: {obj.getBoolean('active')}")
    results.append(f"items length: {obj.getJSONArray('items').length()}")
    results.append(f"items[0]: {obj.getJSONArray('items').getString(0)}")
    
    # toString
    json_str = obj.toString()
    results.append(f"toString: {json_str}")
    
    # 从字符串解析
    parsed = JSONObject('{"key":"value","num":123}')
    results.append(f"parsed key: {parsed.getString('key')}")
    results.append(f"parsed num: {parsed.getInt('num')}")
    
    return {"success": True, "results": results}

async def test_collections(params):
    """测试 ArrayList/HashMap — Java 集合"""
    results = []
    
    # ArrayList
    lst = ArrayList()
    lst.add("first")
    lst.add("second")
    lst.add("third")
    results.append(f"ArrayList size: {lst.size()}")
    results.append(f"ArrayList[0]: {lst.get(0)}")
    results.append(f"ArrayList contains 'second': {lst.contains('second')}")
    lst.remove("second")
    results.append(f"After remove, size: {lst.size()}")
    
    # HashMap
    m = HashMap()
    m.put("key1", "value1")
    m.put("key2", "value2")
    m.put("key3", "value3")
    results.append(f"HashMap size: {m.size()}")
    results.append(f"HashMap[key1]: {m.get('key1')}")
    results.append(f"HashMap containsKey 'key2': {m.containsKey('key2')}")
    m.remove("key2")
    results.append(f"After remove, size: {m.size()}")
    
    # HashSet
    s = HashSet()
    s.add("a")
    s.add("b")
    s.add("a")  # 重复
    results.append(f"HashSet size: {s.size()}")
    results.append(f"HashSet contains 'a': {s.contains('a')}")
    
    return {"success": True, "results": results}

async def test_environment(params):
    """测试 Environment — Android 存储目录"""
    results = []
    
    # 外部存储目录
    external = Environment.getExternalStorageDirectory()
    results.append(f"externalStorage: {external.getPath() if hasattr(external, 'getPath') else str(external)}")
    
    # 数据目录
    data_dir = Environment.getDataDirectory()
    results.append(f"dataDirectory: {data_dir.getPath() if hasattr(data_dir, 'getPath') else str(data_dir)}")
    
    # 缓存目录
    cache_dir = Environment.getDownloadCacheDirectory()
    results.append(f"downloadCacheDirectory: {cache_dir.getPath() if hasattr(cache_dir, 'getPath') else str(cache_dir)}")
    
    # 状态检查
    results.append(f"externalStorageState: {Environment.getExternalStorageState()}")
    
    return {"success": True, "results": results}

async def test_log(params):
    """测试 Log — Android 日志"""
    results = []
    
    # 各种日志级别
    Log.v("TestTag", "Verbose message")
    Log.d("TestTag", "Debug message")
    Log.i("TestTag", "Info message")
    Log.w("TestTag", "Warning message")
    Log.e("TestTag", "Error message")
    
    results.append("All log levels executed (check stderr above)")
    
    # 测试 getStackTraceString
    try:
        raise Exception("Test exception")
    except Exception as e:
        stack = Log.getStackTraceString(e)
        results.append(f"stackTrace length: {len(stack)}")
    
    return {"success": True, "results": results}

async def test_settings(params):
    """测试 Settings — Android 系统设置"""
    results = []
    
    # Settings.System 常量
    results.append(f"Settings.System.SCREEN_BRIGHTNESS: {getattr(Settings.System, 'SCREEN_BRIGHTNESS', 'N/A') if hasattr(Settings, 'System') else 'Settings.System not available'}")
    
    # Settings.Global 常量
    results.append(f"Settings.Global.AIRPLANE_MODE_ON: {getattr(Settings.Global, 'AIRPLANE_MODE_ON', 'N/A') if hasattr(Settings, 'Global') else 'Settings.Global not available'}")
    
    # Settings.Secure 常量
    results.append(f"Settings.Secure.ADB_ENABLED: {getattr(Settings.Secure, 'ADB_ENABLED', 'N/A') if hasattr(Settings, 'Secure') else 'Settings.Secure not available'}")
    
    return {"success": True, "results": results}

async def test_bitmap(params):
    """测试 Bitmap/Canvas/Color — Android 图形"""
    results = []
    
    # Color 常量
    results.append(f"Color.RED: {hex(Color.RED)}")
    results.append(f"Color.GREEN: {hex(Color.GREEN)}")
    results.append(f"Color.BLUE: {hex(Color.BLUE)}")
    results.append(f"Color.BLACK: {hex(Color.BLACK)}")
    results.append(f"Color.WHITE: {hex(Color.WHITE)}")
    
    # Color 方法
    results.append(f"Color.rgb(255,128,0): {hex(Color.rgb(255, 128, 0))}")
    results.append(f"Color.red(0xFF8000): {Color.red(0xFF8000)}")
    results.append(f"Color.green(0xFF8000): {Color.green(0xFF8000)}")
    results.append(f"Color.blue(0xFF8000): {Color.blue(0xFF8000)}")
    
    # Paint
    paint = Paint()
    paint.setColor(Color.RED)
    paint.setTextSize(24)
    paint.setAntiAlias(True)
    results.append(f"Paint color: {hex(paint.getColor())}")
    results.append(f"Paint textSize: {paint.getTextSize()}")
    results.append(f"Paint antiAlias: {paint.isAntiAlias()}")
    
    # Rect
    rect = Rect(0, 0, 100, 200)
    results.append(f"Rect width: {rect.width()}")
    results.append(f"Rect height: {rect.height()}")
    results.append(f"Rect contains(50,50): {rect.contains(50, 50)}")
    
    return {"success": True, "results": results}

async def test_string_builder(params):
    """测试 StringBuilder — Java 字符串构建"""
    results = []
    
    sb = StringBuilder()
    sb.append("Hello")
    sb.append(" ")
    sb.append("World")
    sb.append("!")
    results.append(f"toString: {sb.toString()}")
    results.append(f"length: {sb.length()}")
    
    sb.insert(5, ",")
    results.append(f"after insert: {sb.toString()}")
    
    sb.delete(5, 6)
    results.append(f"after delete: {sb.toString()}")
    
    sb.reverse()
    results.append(f"after reverse: {sb.toString()}")
    
    return {"success": True, "results": results}

async def test_content_values(params):
    """测试 ContentValues — Android 数据库操作"""
    results = []
    
    cv = ContentValues()
    cv.put("name", "Test Item")
    cv.put("quantity", 10)
    cv.put("price", 9.99)
    cv.put("active", True)
    cv.putNull("description")
    
    results.append(f"name: {cv.get('name')}")
    results.append(f"quantity: {cv.get('quantity')}")
    results.append(f"price: {cv.get('price')}")
    results.append(f"active: {cv.get('active')}")
    results.append(f"description: {cv.get('description')}")
    results.append(f"size: {cv.size()}")
    results.append(f"keySet: {cv.keySet()}")
    
    return {"success": True, "results": results}

async def test_run_all(params):
    """运行全部测试"""
    all_results = {}
    tests = [
        ("test_intent", test_intent),
        ("test_uri", test_uri),
        ("test_bundle", test_bundle),
        ("test_file_io", test_file_io),
        ("test_json", test_json),
        ("test_collections", test_collections),
        ("test_environment", test_environment),
        ("test_log", test_log),
        ("test_settings", test_settings),
        ("test_bitmap", test_bitmap),
        ("test_string_builder", test_string_builder),
        ("test_content_values", test_content_values),
    ]
    
    passed = 0
    failed = 0
    
    for name, func in tests:
        try:
            result = await func({})
            if result.get("success"):
                passed += 1
                all_results[name] = "✅ PASS"
            else:
                failed += 1
                all_results[name] = f"❌ FAIL: {result.get('message', 'unknown')}"
        except Exception as e:
            failed += 1
            all_results[name] = f"❌ ERROR: {e}"
    
    return {
        "success": failed == 0,
        "passed": passed,
        "failed": failed,
        "total": len(tests),
        "details": all_results
    }

# 注册工具
exports["test_intent"] = test_intent
exports["test_uri"] = test_uri
exports["test_bundle"] = test_bundle
exports["test_file_io"] = test_file_io
exports["test_json"] = test_json
exports["test_collections"] = test_collections
exports["test_environment"] = test_environment
exports["test_log"] = test_log
exports["test_settings"] = test_settings
exports["test_bitmap"] = test_bitmap
exports["test_string_builder"] = test_string_builder
exports["test_content_values"] = test_content_values
exports["test_run_all"] = test_run_all
