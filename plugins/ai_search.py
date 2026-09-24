from urllib.parse import quote
import requests


class Liugin:
    """AI搜索插件 - 使用jina.ai进行智能搜索"""

    def __init__(self):
        self.usage = """AI搜索工具使用方法：/r
ai_search <操作> <参数>/r
例如:/r
- ai_search url https://www.example.com - 搜索网址内容/r
- ai_search search Python教程 - 普通搜索/r
- ai_search web 什么是人工智能 - 搜索网络内容/r
/r
详细说明:/r
- url操作: ai_search url <网址> - 提取并搜索指定网址的内容/r
- search操作: ai_search search <搜索词> - 使用必应搜索指定内容/r
- web操作: ai_search web <搜索词> - 使用必应搜索指定内容（与search相同）/r
/r
使用工具的JSON格式示例:/r
{"action": "use_tool", "tool": "ai_search", "args": "url https://www.example.com"} - 搜索网址内容/r
{"action": "use_tool", "tool": "ai_search", "args": "search Python教程"} - 普通搜索/r
{"action": "use_tool", "tool": "ai_search", "args": "web 什么是人工智能"} - 搜索网络内容/r
"""
        self.cli = None  # CLI实例引用
        self.timeout = 30  # 请求超时时间（秒）

    def set_cli(self, cli):
        """设置CLI实例引用"""
        self.cli = cli
        # 注册插件命令
        self.cli.register_liugin_command('ai_search', self.command_handler)
        self.cli.register_liugin_command('search', self.search_command_handler)
        self.cli.register_liugin_command('web', self.web_command_handler)

    def command_handler(self, args):
        """处理 /ai_search 命令"""
        # 解析参数
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 1:
            return "请提供操作类型: url, search, web"

        operation = parts[0].lower()
        remaining_args = parts[1] if len(parts) > 1 else ""

        # 调用实际的AI搜索功能
        return self.handle(f"{operation} {remaining_args}")

    def search_command_handler(self, args):
        """处理 /search 命令"""
        return self.handle(f"search {args}")

    def web_command_handler(self, args):
        """处理 /web 命令"""
        return self.handle(f"search {args}")

    def get_tool_info(self):
        return {
            "name": "ai_search",
            "description": "AI搜索工具，使用jina.ai服务进行智能搜索，支持网址内容提取和实时网络搜索。当用户询问天气、新闻、汇率、股票、航班、实时信息、网络内容搜索等问题时，应该直接使用此工具。使用格式：ai_search search <搜索词> 或 ai_search url <网址>",
            "keywords": ["搜索", "search", "网址", "url", "web", "AI搜索", "网络搜索", "内容提取", "天气", "新闻", "实时信息"],
            "usage": """ai_search 工具使用说明：
JSON格式示例：
{\"action\": \"use_tool\", \"tool\": \"ai_search\", \"args\": \"url https://www.example.com\"} - 搜索网址内容
{\"action\": \"use_tool\", \"tool\": \"ai_search\", \"args\": \"search Python教程\"} - 普通搜索
{\"action\": \"use_tool\", \"tool\": \"ai_search\", \"args\": \"web 什么是人工智能\"} - 搜索网络内容"""
        }

    def get_mcp_definition(self):
        return {
            "name": "ai_search",
            "description": "AI搜索工具，支持网址内容提取和网络搜索",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["search", "url", "web"],
                        "description": "操作类型: search(搜索), url(提取网址内容), web(网络搜索)"
                    },
                    "query": {
                        "type": "string",
                        "description": "搜索词或网址"
                    }
                },
                "required": ["operation", "query"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        query = arguments.get("query", "")
        return f"{op} {query}"

    def handle(self, args):
        """处理AI搜索请求"""
        try:
            # 解析参数
            parts = args.strip().split(maxsplit=1)
            if len(parts) < 1:
                return "错误：参数不足。请提供操作类型。\n可用操作: url, search, web"

            operation = parts[0].lower()

            if operation == "url":
                # 搜索网址内容
                if len(parts) < 2:
                    return "错误：请提供URL。格式: url <网址>"

                url = parts[1].strip()
                return self._search_url(url)

            elif operation in ["search", "web"]:
                # 普通搜索
                if len(parts) < 2:
                    return "错误：请提供搜索词。格式: search <搜索词>"

                query = parts[1].strip()
                return self._search_web(query)

            else:
                return f"错误：不支持的操作 '{operation}'。支持的操作有: url, search, web。"

        except Exception as e:
            return f"AI搜索操作错误: {str(e)}"

    def _search_url(self, url):
        """搜索网址内容（使用jina.ai提取）"""
        try:
            # 构建jina.ai的URL - 直接使用URL
            jina_url = f"https://r.jina.ai/{url}"

            result = self._execute_curl(jina_url)

            if result.startswith("错误："):
                return result

            return f" 网址内容 (来自 {url}):\n\n{result}"

        except Exception as e:
            return f"网址搜索错误: {str(e)}"

    def _search_web(self, query):
        """普通搜索（使用 jina.ai 搜索端点 s.jina.ai，返回实时结果）"""
        try:
            encoded_query = quote(query, safe='')
            # s.jina.ai 是 jina.ai 的搜索端点，直接返回实时搜索结果
            # 不再嵌套必应URL，避免返回旧时间戳的缓存内容
            jina_url = f"https://s.jina.ai/{encoded_query}"

            result = self._execute_curl(jina_url)

            if result.startswith("错误："):
                return result

            return f" 搜索结果 (搜索词: {query}):\n\n{result}"

        except Exception as e:
            return f"网络搜索错误: {str(e)}"

    def _execute_curl(self, url):
        """使用 requests 库获取内容（替代 curl 命令）"""
        try:
            # 使用 requests 库发送请求
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; AI-Search-Bot)'}
            )
            
            # 检查状态码
            if response.status_code != 200:
                return f"错误：HTTP请求失败，状态码: {response.status_code}"

            # 获取内容
            content = response.text.strip()

            if not content:
                return "错误：未获取到任何内容"

            # 限制输出长度以避免过长输出
            if len(content) > 5000:
                content = content[:5000] + f"\n\n... (内容已截断，完整内容共{len(content)}字符)"

            return content

        except requests.Timeout:
            return f"错误：请求超时 (>{self.timeout}秒)"
        except requests.ConnectionError:
            return "错误：网络连接失败，请检查网络"
        except Exception as e:
            return f"错误：请求时发生错误: {str(e)}"