import requests
import time
import socket
from urllib.parse import urlparse


class Liugin:
    """网络工具插件"""
    
    def __init__(self):
        self.usage = """网络工具使用方法：/r
network_tools <操作> <参数>/r
例如:/r
- network_tools ping www.baidu.com - 测试网站连通性和延迟/r
- network_tools get https://www.example.com - 获取网页内容/r
- network_tools status https://www.example.com - 检查网站状态/r
- network_tools headers https://www.example.com - 获取网站响应头/r
- network_tools ip www.example.com - 获取网站IP地址/r
/r
详细说明:/r
- ping操作: network_tools ping <域名或IP> - 测试连通性和延迟/r
- get操作: network_tools get <URL> - 获取网页内容/r
- status操作: network_tools status <URL> - 检查网站HTTP状态码/r
- headers操作: network_tools headers <URL> - 获取网站响应头信息/r
- ip操作: network_tools ip <域名> - 获取域名对应的IP地址/r
/r
使用工具的JSON格式示例:/r
{"action": "use_tool", "tool": "network_tools", "args": "ping www.baidu.com"} - 测试百度连通性/r
{"action": "use_tool", "tool": "network_tools", "args": "get https://www.example.com"} - 获取网页内容/r
{"action": "use_tool", "tool": "network_tools", "args": "status https://www.example.com"} - 检查网站状态/r
{"action": "use_tool", "tool": "network_tools", "args": "headers https://www.example.com"} - 获取响应头/r
{"action": "use_tool", "tool": "network_tools", "args": "ip www.example.com"} - 获取IP地址/r
"""
        self.cli = None  # CLI实例引用
        self.timeout = 10  # 请求超时时间（秒）
    
    def set_cli(self, cli):
        """设置CLI实例引用"""
        self.cli = cli
        # 注册插件命令
        self.cli.register_liugin_command('net', self.command_handler)
        self.cli.register_liugin_command('ping', self.ping_command_handler)
        self.cli.register_liugin_command('website', self.website_command_handler)
    
    def command_handler(self, args):
        """处理 /net 命令"""
        # 解析参数
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 1:
            return "请提供操作类型: ping, get, status, headers, ip 等"
        
        operation = parts[0].lower()
        remaining_args = parts[1] if len(parts) > 1 else ""
        
        # 调用实际的网络工具功能
        return self.handle(f"{operation} {remaining_args}")
    
    def ping_command_handler(self, args):
        """处理 /ping 命令"""
        return self.handle(f"ping {args}")
    
    def website_command_handler(self, args):
        """处理 /website 命令"""
        return self.handle(f"status {args}")
    
    def get_tool_info(self):
        return {
            "name": "network_tools",
            "description": "网络工具，用于测试网站连通性、获取网页内容、检查网站状态、获取响应头、解析IP地址等",
            "keywords": ["网络", "ping", "网站", "状态", "网页", "IP", "headers", "get", "网络工具", "连通性", "延迟"],
            "usage": """network_tools 工具使用说明：
JSON格式示例：
{"action": "use_tool", "tool": "network_tools", "args": "ping www.baidu.com"} - 测试百度连通性
{"action": "use_tool", "tool": "network_tools", "args": "get https://www.example.com"} - 获取网页内容
{"action": "use_tool", "tool": "network_tools", "args": "status https://www.example.com"} - 检查网站状态
{"action": "use_tool", "tool": "network_tools", "args": "headers https://www.example.com"} - 获取网站响应头
{"action": "use_tool", "tool": "network_tools", "args": "ip www.example.com"} - 获取网站IP地址"""
        }
    
    def get_mcp_definition(self):
        return {
            "name": "network_tools",
            "description": "网络工具，用于测试连通性、获取网页内容、解析IP等",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["ping", "website", "headers", "ip"],
                        "description": "操作类型"
                    },
                    "target": {
                        "type": "string",
                        "description": "目标网址或IP"
                    }
                },
                "required": ["operation", "target"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        target = arguments.get("target", "")
        return f"{op} {target}"

    def handle(self, args):
        """处理网络工具请求"""
        try:
            # 解析参数
            parts = args.strip().split(maxsplit=1)
            if len(parts) < 1:
                return "错误：参数不足。请提供操作类型。\n可用操作: ping, get, status, headers, ip"
            
            operation = parts[0].lower()
            
            if operation == "ping":
                # 测试网站连通性和延迟
                if len(parts) < 2:
                    return "错误：请提供要测试的域名或IP地址。格式: ping <域名或IP>"
                
                target = parts[1].strip()
                return self._ping(target)
            
            elif operation == "get":
                # 获取网页内容
                if len(parts) < 2:
                    return "错误：请提供URL。格式: get <URL>"
                
                url = parts[1].strip()
                return self._get_content(url)
            
            elif operation == "status":
                # 检查网站状态码
                if len(parts) < 2:
                    return "错误：请提供URL。格式: status <URL>"
                
                url = parts[1].strip()
                return self._check_status(url)
            
            elif operation == "headers":
                # 获取网站响应头
                if len(parts) < 2:
                    return "错误：请提供URL。格式: headers <URL>"
                
                url = parts[1].strip()
                return self._get_headers(url)
            
            elif operation == "ip":
                # 获取域名IP地址
                if len(parts) < 2:
                    return "错误：请提供域名。格式: ip <域名>"
                
                domain = parts[1].strip()
                return self._get_ip(domain)
            
            else:
                return f"错误：不支持的操作 '{operation}'。支持的操作有: ping, get, status, headers, ip。"
        
        except Exception as e:
            return f"网络工具操作错误: {str(e)}"
    
    def _ping(self, target):
        """测试网站连通性和延迟"""
        try:
            # 确保URL格式正确
            if not target.startswith(('http://', 'https://')):
                test_url = 'http://' + target
            else:
                test_url = target
            
            # 添加协议如果缺失
            if not test_url.startswith(('http://', 'https://')):
                test_url = 'http://' + test_url
            
            start_time = time.time()
            response = requests.get(test_url, timeout=self.timeout)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000  # 转换为毫秒
            
            result = f".ping 测试结果:\n"
            result += f"目标: {target}\n"
            result += f"HTTP状态码: {response.status_code}\n"
            result += f"响应时间: {response_time:.2f} ms\n"
            result += f"连接状态: {'成功' if response.status_code < 400 else '失败'}\n"
            
            if response.status_code >= 400:
                result += f"错误信息: {response.reason if hasattr(response, 'reason') else '请求失败'}\n"
            
            return result
            
        except requests.exceptions.Timeout:
            return f".ping 测试结果:\n目标: {target}\n错误: 请求超时 (>{self.timeout}秒)\n连接状态: 失败"
        except requests.exceptions.ConnectionError:
            return f".ping 测试结果:\n目标: {target}\n错误: 连接失败 (无法连接到服务器)\n连接状态: 失败"
        except requests.exceptions.RequestException as e:
            return f".ping 测试结果:\n目标: {target}\n错误: {str(e)}\n连接状态: 失败"
        except Exception as e:
            return f".ping 测试结果:\n目标: {target}\n错误: {str(e)}\n连接状态: 失败"
    
    def _get_content(self, url):
        """获取网页内容"""
        try:
            # 确保URL格式正确
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                content = response.text
                # 限制内容长度以避免过长输出
                if len(content) > 2000:
                    content = content[:2000] + f"\n... (内容已截断，完整内容共{len(content)}字符)"
                
                result = f"网页内容 (来自 {url}):\n"
                result += content
                return result
            else:
                return f"获取网页内容失败，状态码: {response.status_code}, 原因: {response.reason if hasattr(response, 'reason') else ''}"
                
        except requests.exceptions.Timeout:
            return f"获取网页内容超时 (>{self.timeout}秒)"
        except requests.exceptions.ConnectionError:
            return f"无法连接到 {url}，请检查URL是否正确"
        except requests.exceptions.RequestException as e:
            return f"请求失败: {str(e)}"
        except Exception as e:
            return f"获取网页内容时发生错误: {str(e)}"
    
    def _check_status(self, url):
        """检查网站状态码"""
        try:
            # 确保URL格式正确
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            response = requests.get(url, timeout=self.timeout)
            
            result = f"网站状态 (来自 {url}):\n"
            result += f"HTTP状态码: {response.status_code}\n"
            result += f"状态描述: {response.reason if hasattr(response, 'reason') else 'Unknown'}\n"
            result += f"响应时间: {response.elapsed.total_seconds():.2f} 秒\n"
            result += f"内容长度: {len(response.content)} 字节\n"
            result += f"服务器: {response.headers.get('Server', '未知')}\n"
            result += f"内容类型: {response.headers.get('Content-Type', '未知')}\n"
            
            return result
            
        except requests.exceptions.Timeout:
            return f"检查网站状态超时 (>{self.timeout}秒)"
        except requests.exceptions.ConnectionError:
            return f"无法连接到 {url}，请检查URL是否正确"
        except requests.exceptions.RequestException as e:
            return f"请求失败: {str(e)}"
        except Exception as e:
            return f"检查网站状态时发生错误: {str(e)}"
    
    def _get_headers(self, url):
        """获取网站响应头"""
        try:
            # 确保URL格式正确
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            response = requests.get(url, timeout=self.timeout)
            
            headers = dict(response.headers)
            
            result = f"响应头 (来自 {url}):\n"
            for key, value in headers.items():
                result += f"{key}: {value}\n"
            
            return result
            
        except requests.exceptions.Timeout:
            return f"获取响应头超时 (>{self.timeout}秒)"
        except requests.exceptions.ConnectionError:
            return f"无法连接到 {url}，请检查URL是否正确"
        except requests.exceptions.RequestException as e:
            return f"请求失败: {str(e)}"
        except Exception as e:
            return f"获取响应头时发生错误: {str(e)}"
    
    def _get_ip(self, domain):
        """获取域名对应的IP地址"""
        try:
            # 如果域名包含协议，去掉协议部分
            if domain.startswith(('http://', 'https://')):
                parsed = urlparse(domain)
                domain = parsed.netloc
            
            ip_address = socket.gethostbyname(domain)
            
            result = f"域名解析结果:\n"
            result += f"域名: {domain}\n"
            result += f"IP地址: {ip_address}\n"
            
            return result
            
        except socket.gaierror:
            return f"无法解析域名: {domain}，请检查域名是否正确"
        except Exception as e:
            return f"域名解析失败: {str(e)}"
