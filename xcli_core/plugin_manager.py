import os
import importlib.util
from colorama import Fore, Style
from .config import logger


class LiuginManager:
    """插件管理器"""

    def __init__(self, liugins_dir="plugins"):
        self.liugins_dir = liugins_dir
        self.tools = []

    def get_enabled_liugins(self):
        """获取启用的插件列表"""
        # 检查环境变量中是否有启用的插件列表
        enabled_liugins_env = os.environ.get("XIAOLI_ENABLED_PLUGINS")
        if enabled_liugins_env is not None:
            # 特殊处理：空字符串表示不启用任何插件
            if enabled_liugins_env == "":
                return []
            return enabled_liugins_env.split(",")
        # 检查是否有插件配置文件
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_file = os.path.join(project_dir, "plugins_config.py")
        if os.path.exists(config_file):
            try:
                # 读取配置文件
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_content = f.read()
                # 检查是否明确表示不启用任何插件
                if "# 不启用任何插件" in config_content:
                    return []
                # 解析启用的插件
                enabled_liugins = []
                for line in config_content.split('\n'):
                    if line.startswith('ENABLE_') and '= True' in line:
                        liugin_name = line.split('=')[0].replace('ENABLE_', '').strip().lower()
                        enabled_liugins.append(liugin_name)
                return enabled_liugins
            except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
                logger.error(f"读取插件配置文件失败: {e}")
                print(f"{Fore.RED}读取插件配置文件失败: {e}{Style.RESET_ALL}")
            except Exception as e:
                logger.error(f"读取插件配置时发生未知错误: {e}")
                print(f"{Fore.RED}读取插件配置文件失败: {e}{Style.RESET_ALL}")
        # 如果没有配置，则返回None表示加载所有插件
        return None

    def load_liugins(self):
        """加载liugin"""
        self.tools = []
        # 获取启用的插件列表
        enabled_liugins = self.get_enabled_liugins()
        # 加载工具插件
        if os.path.exists(self.liugins_dir):
            for filename in os.listdir(self.liugins_dir):
                if filename.endswith('.py') and filename != '__init__.py':
                    liugin_name = filename[:-3]  # 移除.py扩展名
                    # 如果有启用的插件列表，检查当前插件是否在其中
                    if enabled_liugins is not None and liugin_name.lower() not in enabled_liugins:
                        print(f"{Fore.YELLOW}跳过liugin: {liugin_name} (未启用){Style.RESET_ALL}")
                        continue
                    plugin_path = os.path.join(self.liugins_dir, filename)
                    try:
                        spec = importlib.util.spec_from_file_location(liugin_name, plugin_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        # 获取插件信息 - 兼容 Liugin 和 Plugin 两种类名
                        plugin_class = getattr(module, 'Liugin', None) or getattr(module, 'Plugin', None)
                        if plugin_class:
                            plugin_instance = plugin_class()
                            tool_info = plugin_instance.get_tool_info()
                            tool_info['handler'] = plugin_instance.handle
                            self.tools.append(tool_info)
                            print(f"{Fore.GREEN}已加载liugin: {liugin_name}{Style.RESET_ALL}")
                    except (ImportError, AttributeError, TypeError) as e:
                        logger.error(f"加载liugin失败 {filename}: {e}")
                        print(f"{Fore.RED}加载liugin失败 {filename}: {e}{Style.RESET_ALL}")
                    except FileNotFoundError as e:
                        logger.error(f"liugin文件未找到 {filename}: {e}")
                        print(f"{Fore.RED}liugin文件未找到 {filename}: {e}{Style.RESET_ALL}")
                    except Exception as e:
                        logger.error(f"加载liugin时发生未知错误 {filename}: {e}")
                        print(f"{Fore.RED}加载liugin失败 {filename}: {e}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}总共加载了 {len(self.tools)} 个工具插件{Style.RESET_ALL}")

    def search_tools(self, query, limit=5):
        """
        搜索工具，支持关键词匹配
        """
        if not self.tools:
            return []

        query_lower = query.lower()
        matches = []

        for tool in self.tools:
            score = 0
            tool_name = tool.get('name', '').lower()
            tool_desc = tool.get('description', '').lower()
            tool_keywords = [kw.lower() for kw in tool.get('keywords', [])]

            if query_lower == tool_name:
                score += 100
            if query_lower in tool_name:
                score += 50
            if query_lower in tool_desc:
                score += 30
            for keyword in tool_keywords:
                if query_lower in keyword:
                    score += 20
                    break

            if score > 0:
                matches.append({
                    'score': score,
                    'name': tool.get('name', ''),
                    'description': tool.get('description', ''),
                    'usage': tool.get('usage', ''),
                    'keywords': tool.get('keywords', [])
                })

        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches[:limit]

    def get_tool_by_name(self, tool_name):
        """根据名称获取工具"""
        for tool in self.tools:
            if tool.get('name', '').lower() == tool_name.lower():
                return tool
        return None
