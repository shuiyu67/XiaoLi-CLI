"""
工具搜索助手 - 支持按需发现工具
"""


class Liugin:
    """工具搜索助手 - 允许 AI 按需搜索和发现可用工具"""

    def __init__(self):
        self.usage = """工具搜索使用方法：
tool_search <关键词> - 根据关键词搜索可用工具

例如:
- tool_search 文件 - 搜索与文件相关的工具
- tool_search 网络 - 搜索与网络相关的工具
- tool_search 图片 - 搜索与图片相关的工具

此工具帮助 AI 在需要特定功能时快速找到合适的工具，
而不是预加载所有工具到上下文中。"""
        self.cli = None

    def set_cli(self, cli):
        """设置 CLI 实例引用"""
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "tool_search",
            "description": "工具搜索助手，支持按需发现和搜索可用工具。当你不确定有哪些工具可用时，可以使用此工具搜索相关功能的工具。",
            "keywords": ["搜索", "工具", "发现", "search", "tool", "find", "可用工具", "工具列表"],
            "usage": """tool_search 工具使用说明：
JSON格式示例：
{"action": "use_tool", "tool": "tool_search", "args": "文件"} - 搜索与文件相关的工具
{"action": "use_tool", "tool": "tool_search", "args": "网络"} - 搜索与网络相关的工具
{"action": "use_tool", "tool": "tool_search", "args": "图片"} - 搜索与图片相关的工具

功能说明：
- 支持关键词匹配（工具名称、描述、关键词）
- 返回匹配度最高的前 5 个工具
- 包含工具的详细使用说明
- 帮助 AI 快速找到合适的工具而不需要预加载所有工具"""
        }

    def get_mcp_definition(self):
        return {
            "name": "tool_search",
            "description": "工具搜索助手，搜索可用工具的用法和信息",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词或工具名"
                    }
                },
                "required": ["query"]
            }
        }

    def convert_mcp_args(self, arguments):
        return arguments.get("query", "")

    def handle(self, args):
        """处理工具搜索请求"""
        try:
            # 解析参数
            query = args.strip()
            
            if not query:
                return "错误：请提供搜索关键词。格式: tool_search <关键词>"
            
            # 搜索工具
            if self.cli and hasattr(self.cli, 'liugin_manager'):
                matches = self.cli.liugin_manager.search_tools(query, limit=5)
                
                if not matches:
                    return f"未找到与 '{query}' 相关的工具。"
                
                # 格式化搜索结果
                result_lines = [f"找到 {len(matches)} 个与 '{query}' 相关的工具:\n"]
                
                for i, match in enumerate(matches, 1):
                    result_lines.append(f"{i}. {match['name']}")
                    result_lines.append(f"   描述: {match['description']}")
                    
                    # 显示协议类型
                    protocol = match.get('protocol', 'liugin')
                    result_lines.append(f"   协议: {protocol}")
                    
                    # 关键词
                    keywords = match.get('keywords', [])
                    if keywords:
                        result_lines.append(f"   关键词: {', '.join(keywords)}")
                    
                    # 根据协议类型显示不同的使用说明
                    if protocol == 'skill':
                        # Skill 协议：显示完整指令
                        instance = match.get('instance')
                        if instance:
                            instructions = getattr(instance, 'instructions', '')
                            if instructions:
                                # 限制长度
                                if len(instructions) > 1500:
                                    instructions = instructions[:1500] + "\n...(内容已截断)"
                                result_lines.append(f"   指令:\n{instructions}")
                            else:
                                usage = match.get('usage', '')
                                if usage:
                                    result_lines.append(f"   用法: {usage}")
                    else:
                        # Plugin 协议：显示 usage
                        if match.get('usage'):
                            usage = match['usage']
                            if len(usage) > 500:
                                usage = usage[:500] + "..."
                            result_lines.append(f"   用法: {usage}")
                    
                    result_lines.append("")
                
                return "\n".join(result_lines)
            else:
                return "错误：无法访问工具管理器。"
                
        except Exception as e:
            return f"工具搜索失败: {str(e)}"