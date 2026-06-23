"""Operit Bridge 插件测试"""
import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins.operit_bridge import (
    parse_operit_metadata,
    _localized,
    operit_tool_to_mcp,
    meta_to_tools,
    xiaoli_to_operit_js,
    Liugin,
)


SAMPLE_META = {
    "name": "WeatherQuery",
    "display_name": {"zh": "天气查询", "en": "Weather Query"},
    "description": "查询指定城市的天气信息",
    "author": ["TestAuthor"],
    "category": "Life",
    "env": ["WEATHER_API_KEY"],
    "tools": [
        {
            "name": "get_weather",
            "description": {"zh": "获取城市天气", "en": "Get city weather"},
            "parameters": [
                {"name": "city", "description": "城市名称", "type": "string", "required": True},
                {"name": "days", "description": "预报天数", "type": "integer", "required": False},
            ],
        },
        {
            "name": "get_alert",
            "description": "获取天气预警",
            "parameters": [
                {"name": "city", "description": "城市名称", "type": "string", "required": True},
            ],
        },
    ],
}

SAMPLE_JS = '''
/*
METADATA
''' + json.dumps(SAMPLE_META, ensure_ascii=False) + '''
*/

const WeatherQuery = (function () {
    async function wrap(func, params) {
        try { return await func(params); }
        catch (e) { return { success: false, message: e.message }; }
    }
    async function get_weather(params) { return { success: true }; }
    async function get_alert(params) { return { success: true }; }
    return {
        get_weather: function (p) { return wrap(get_weather, p); },
        get_alert: function (p) { return wrap(get_alert, p); }
    };
})();
exports.get_weather = WeatherQuery.get_weather;
exports.get_alert = WeatherQuery.get_alert;
'''


def test_parse_metadata():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8') as f:
        f.write(SAMPLE_JS)
        fpath = f.name
    try:
        meta = parse_operit_metadata(fpath)
        assert meta is not None
        assert meta["name"] == "WeatherQuery"
        assert len(meta["tools"]) == 2
        assert meta["category"] == "Life"
        assert "WEATHER_API_KEY" in meta["env"]
        print("✓ test_parse_metadata")
    finally:
        os.unlink(fpath)


def test_parse_no_metadata():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8') as f:
        f.write("console.log('hi');")
        fpath = f.name
    try:
        assert parse_operit_metadata(fpath) is None
        print("✓ test_parse_no_metadata")
    finally:
        os.unlink(fpath)


def test_localized():
    assert _localized("hello") == "hello"
    assert _localized({"zh": "你好", "en": "hi"}, "zh") == "你好"
    assert _localized({"zh": "你好", "en": "hi"}, "en") == "hi"
    assert _localized({"zh": "你好"}, "en") == "你好"  # fallback
    assert _localized({"default": "默认"}, "ja") == "默认"
    print("✓ test_localized")


def test_operit_to_mcp():
    td = SAMPLE_META["tools"][0]
    mcp = operit_tool_to_mcp(td, "WeatherQuery")
    assert mcp["name"] == "WeatherQuery__get_weather"
    assert mcp["inputSchema"]["properties"]["city"]["type"] == "string"
    assert mcp["inputSchema"]["properties"]["days"]["type"] == "integer"
    assert "city" in mcp["inputSchema"]["required"]
    assert "days" not in mcp["inputSchema"]["required"]
    print("✓ test_operit_to_mcp")


def test_meta_to_tools():
    tools = meta_to_tools(SAMPLE_META)
    assert len(tools) == 2
    assert tools[0]["name"] == "WeatherQuery__get_weather"
    assert tools[1]["name"] == "WeatherQuery__get_alert"
    assert tools[0]["source"] == "operit"
    assert "operit" in tools[0]["keywords"]
    assert "WeatherQuery" in tools[0]["keywords"]
    print("✓ test_meta_to_tools")


def test_plugin_auto_scan():
    """测试自动扫描 plugins/operit/ 目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建 operit 子目录
        operit_dir = os.path.join(tmpdir, "operit")
        os.makedirs(operit_dir)

        # 写入一个有效脚本
        with open(os.path.join(operit_dir, "weather.js"), 'w', encoding='utf-8') as f:
            f.write(SAMPLE_JS)
        # 写入一个无效文件
        with open(os.path.join(operit_dir, "bad.js"), 'w', encoding='utf-8') as f:
            f.write("no metadata here")

        # 创建插件实例，手动设置 operit 目录
        plugin = Liugin()
        # monkey-patch 目录路径
        plugin._get_operit_dir = lambda: operit_dir
        plugin._auto_scan()

        assert len(plugin._operit_tools) == 2, f"期望 2, 实际 {len(plugin._operit_tools)}"
        assert "WeatherQuery__get_weather" in plugin._operit_tools
        assert "WeatherQuery__get_alert" in plugin._operit_tools
        print("✓ test_plugin_auto_scan")


def test_plugin_list():
    plugin = Liugin()
    plugin._operit_tools["test__foo"] = {
        "name": "test__foo", "description": "test tool",
        "keywords": [], "usage": "", "mcp_definition": {},
    }
    result = plugin._h_list("")
    assert "test__foo" in result
    assert "1 个" in result
    print("✓ test_plugin_list")


def test_plugin_list_empty():
    plugin = Liugin()
    result = plugin._h_list("")
    assert "暂无" in result
    print("✓ test_plugin_list_empty")


def test_export_xiaoli_to_operit():
    class MockPlugin:
        def get_tool_info(self):
            return {"name": "test_tool", "description": "测试工具", "keywords": ["test"]}
        def get_mcp_definition(self):
            return {
                "name": "test_tool", "description": "测试工具",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "目标URL"},
                        "timeout": {"type": "integer", "description": "超时"},
                    },
                    "required": ["url"],
                },
            }

    js = xiaoli_to_operit_js(MockPlugin())
    assert "METADATA" in js
    assert "test_tool" in js
    assert "目标URL" in js
    assert "exports.execute" in js
    print("✓ test_export_xiaoli_to_operit")


def test_convert_mcp_roundtrip():
    tool_def = SAMPLE_META["tools"][0]
    mcp = operit_tool_to_mcp(tool_def, "WeatherQuery")
    assert mcp["inputSchema"]["properties"]["city"]["type"] == "string"
    assert "city" in mcp["inputSchema"]["required"]
    print("✓ test_convert_mcp_roundtrip")


def test_handler_parse_json():
    """测试 handler 解析 JSON 参数"""
    plugin = Liugin()
    plugin._operit_tools["Test__fn"] = {
        "name": "Test__fn", "description": "test",
        "keywords": [], "usage": "",
        "mcp_definition": {
            "name": "Test__fn", "description": "",
            "inputSchema": {
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": [],
            },
        },
        "original_tool_name": "fn",
        "_source_file": "/nonexist.js",
    }
    handler = plugin._make_handler("Test__fn")
    result = handler('{"x": "hello"}')
    parsed = json.loads(result)
    assert parsed["params"]["x"] == "hello"
    print("✓ test_handler_parse_json")


def test_handler_parse_kv():
    """测试 handler 解析 key=value 参数"""
    plugin = Liugin()
    plugin._operit_tools["Test__fn"] = {
        "name": "Test__fn", "description": "test",
        "keywords": [], "usage": "",
        "mcp_definition": {
            "name": "Test__fn", "description": "",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "days": {"type": "integer"},
                },
                "required": [],
            },
        },
        "original_tool_name": "fn",
        "_source_file": "/nonexist.js",
    }
    handler = plugin._make_handler("Test__fn")
    result = handler("city=北京 days=3")
    parsed = json.loads(result)
    assert parsed["params"]["city"] == "北京"
    assert parsed["params"]["days"] == "3"
    print("✓ test_handler_parse_kv")


if __name__ == "__main__":
    test_parse_metadata()
    test_parse_no_metadata()
    test_localized()
    test_operit_to_mcp()
    test_meta_to_tools()
    test_plugin_auto_scan()
    test_plugin_list()
    test_plugin_list_empty()
    test_export_xiaoli_to_operit()
    test_convert_mcp_roundtrip()
    test_handler_parse_json()
    test_handler_parse_kv()
    print("\n🎉 全部 12 个测试通过!")
