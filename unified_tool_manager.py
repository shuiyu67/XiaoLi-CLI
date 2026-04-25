"""
统一工具管理器 - 协调 Liugin、Skill 和 MCP 三套协议
自动判断并路由到正确的处理器
"""

import os
import json
import threading
from typing import Dict, List, Any, Optional, Union, Callable
from colorama import Fore, Style


class UnifiedToolManager:
    """
    统一工具管理器
    
    协调三种协议:
    1. Liugin 协议 (plugins/) - 小狸自有协议
    2. Skill 协议 (skills/) - Agent Skills 开源协议
    3. MCP 协议 - Model Context Protocol (Anthropic/OpenAI 标准)
    
    路由策略:
    - 优先使用 Skill 协议（如果存在同名技能）
    - 回退到 Liugin 协议
    - 支持强制指定协议
    - MCP 格式调用统一入口
    """
    
    def __init__(self, cli_instance=None):
        self.cli = cli_instance
        self._lock = threading.RLock()
        
        # 两个独立的加载器
        self._liugin_manager = None
        self._skill_loader = None
        
        # 统一的工具注册表
        self._tools: Dict[str, Dict[str, Any]] = {}
        
        # 协议映射: tool_name -> protocol_type
        self._protocol_map: Dict[str, str] = {}
        
        # MCP 工具定义缓存
        self._mcp_tools_cache: Optional[List[Dict]] = None
    
    def initialize(self, plugins_dir: str = "plugins", skills_dir: str = "skills") -> None:
        """
        初始化并加载所有工具
        
        Args:
            plugins_dir: Liugin 目录
            skills_dir: Skill 目录
        """
        # 加载 Liugins
        self._load_plugins(plugins_dir)
        
        # 加载 Skills
        self._load_skills(skills_dir)
        
        # 构建缓存
        self._build_mcp_cache()
        
        print(f"{Fore.GREEN}[统一工具管理器] 加载完成: {len(self._tools)} 个工具{Style.RESET_ALL}")
        print(f"  - Liugin 协议: {sum(1 for p in self._protocol_map.values() if p == 'liugin')}")
        print(f"  - Skill 协议: {sum(1 for p in self._protocol_map.values() if p == 'skill')}")
    
    def _load_plugins(self, plugins_dir: str) -> None:
        """加载 Liugin 协议工具"""
        import importlib.util
        
        if not os.path.exists(plugins_dir):
            return
        
        # 获取启用的插件列表
        enabled_plugins = self._get_enabled_plugins(plugins_dir)
        
        for filename in os.listdir(plugins_dir):
            if not filename.endswith('.py') or filename == '__init__.py':
                continue
            
            plugin_name = filename[:-3]
            
            # 检查是否启用
            if enabled_plugins is not None and plugin_name.lower() not in enabled_plugins:
                continue
            
            plugin_path = os.path.join(plugins_dir, filename)
            
            try:
                spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 兼容 Plugin 和 Liugin 两种类名
                plugin_class = None
                if hasattr(module, 'Liugin'):
                    plugin_class = module.Liugin
                elif hasattr(module, 'Plugin'):
                    plugin_class = module.Plugin

                if plugin_class:
                    plugin_instance = plugin_class()
                    
                    # 设置 CLI 引用
                    if hasattr(plugin_instance, 'set_cli') and self.cli:
                        plugin_instance.set_cli(self.cli)
                    
                    tool_info = plugin_instance.get_tool_info()
                    tool_name = tool_info.get('name', plugin_name)
                    
                    # 获取 MCP 工具定义（如果插件提供）
                    mcp_definition = None
                    if hasattr(plugin_instance, 'get_mcp_definition'):
                        mcp_definition = plugin_instance.get_mcp_definition()
                    
                    # 注册到统一工具表
                    self._tools[tool_name] = {
                        'name': tool_name,
                        'description': tool_info.get('description', ''),
                        'keywords': tool_info.get('keywords', []),
                        'usage': tool_info.get('usage', ''),
                        'handler': plugin_instance.handle,
                        'protocol': 'liugin',
                        'instance': plugin_instance,
                        'mcp_definition': mcp_definition
                    }
                    self._protocol_map[tool_name] = 'liugin'
                    
            except Exception as e:
                print(f"{Fore.RED}加载 Liugin '{plugin_name}' 失败: {e}{Style.RESET_ALL}")
    
    def _load_skills(self, skills_dir: str) -> None:
        """加载 Skill 协议工具 (支持 Markdown 和 Python 两种格式)"""
        if not os.path.exists(skills_dir):
            print(f"{Fore.YELLOW}Skills 目录不存在: {skills_dir}{Style.RESET_ALL}")
            return
        
        try:
            from skills.base import SkillLoader, MarkdownSkill, Skill
            
            self._skill_loader = SkillLoader(skills_dir)
            
            # 先发现所有技能
            discovered = self._skill_loader.discover_skills(skills_dir)
            print(f"{Fore.CYAN}发现 {len(discovered)} 个技能: {[s['name'] for s in discovered]}{Style.RESET_ALL}")
            
            # 加载所有技能
            self._skill_loader.load_all_skills(skills_dir)
            
            loaded_count = len(self._skill_loader.skills)
            if loaded_count == 0:
                print(f"{Fore.YELLOW}未加载任何 Skill 技能{Style.RESET_ALL}")
                return
            
            for skill_name, skill in self._skill_loader.skills.items():
                # 设置 CLI 引用 (仅 Python 类技能)
                if hasattr(skill, 'set_cli') and self.cli:
                    skill.set_cli(self.cli)
                
                # 获取工具定义
                tool_def = skill.get_tool_definition()
                func_def = tool_def.get('function', {})
                
                # 检查是否已有同名 Plugin，Skill 优先覆盖
                if skill_name in self._tools:
                    old_protocol = self._protocol_map[skill_name]
                    print(f"{Fore.YELLOW}工具 '{skill_name}' 已存在({old_protocol})，使用 Skill 协议覆盖{Style.RESET_ALL}")
                
                # 判断技能格式
                is_markdown = isinstance(skill, MarkdownSkill)
                skill_format = "markdown" if is_markdown else "python"
                
                # 注册到统一工具表
                self._tools[skill_name] = {
                    'name': skill_name,
                    'description': func_def.get('description', ''),
                    'keywords': getattr(skill, 'tags', []),
                    'usage': getattr(skill, 'instructions', '')[:500] if is_markdown else getattr(skill, 'usage', ''),
                    'handler': self._create_skill_handler(skill),
                    'protocol': 'skill',
                    'format': skill_format,
                    'instance': skill,
                    'tool_definition': tool_def,
                    'anthropic_definition': skill.get_anthropic_tool_definition(),
                    'mcp_definition': tool_def  # Skill 的 OpenAI 格式就是 MCP 格式
                }
                self._protocol_map[skill_name] = 'skill'
                print(f"{Fore.GREEN}已加载 Skill ({skill_format}): {skill_name}{Style.RESET_ALL}")
                
        except ImportError as e:
            print(f"{Fore.YELLOW}Skill 协议模块未找到: {e}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}加载 Skills 失败: {e}{Style.RESET_ALL}")
    
    def _create_skill_handler(self, skill) -> callable:
        """
        为 Skill 创建兼容 Plugin 的 handler
        
        支持 Markdown 和 Python 两种技能格式
        """
        from skills.base import MarkdownSkill, Skill
        
        def handler(args: str) -> str:
            import json
            
            kwargs = {}
            
            # 解析参数
            if args.strip().startswith('{'):
                try:
                    kwargs = json.loads(args)
                except json.JSONDecodeError:
                    kwargs = {'operation': args}
            else:
                kwargs = {'operation': args}
            
            # Markdown 技能: 返回指令供 AI 执行
            if isinstance(skill, MarkdownSkill):
                return f"[Skill: {skill.name}]\n{skill.instructions}"
            
            # Python 技能: 直接执行
            if hasattr(skill, 'run'):
                result = skill.run(**kwargs)
                if result.success:
                    return result.message or str(result.data)
                else:
                    return f"错误: {result.error}"
            
            return f"未知的技能类型: {type(skill)}"
        
        return handler
    
    def _get_enabled_plugins(self, plugins_dir: str) -> Optional[List[str]]:
        """获取启用的插件列表"""
        # 检查环境变量
        enabled_env = os.environ.get("XIAOLI_ENABLED_PLUGINS")
        if enabled_env is not None:
            if enabled_env == "":
                return []
            return [p.lower() for p in enabled_env.split(",")]
        
        # 检查配置文件
        config_file = os.path.join(os.path.dirname(plugins_dir), "plugins_config.py")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if "# 不启用任何插件" in content:
                    return []
                
                enabled = []
                for line in content.split('\n'):
                    if line.startswith('ENABLE_') and '= True' in line:
                        name = line.split('=')[0].replace('ENABLE_', '').strip().lower()
                        enabled.append(name)
                return enabled
            except Exception:
                pass
        
        return None  # 加载全部
    
    def _build_mcp_cache(self) -> None:
        """构建 MCP 工具定义缓存（线程安全）"""
        with self._lock:
            self._mcp_tools_cache = []
            for tool in self._tools.values():
                mcp_def = tool.get('mcp_definition')
                if mcp_def:
                    # 确保符合 MCP 标准
                    normalized = self._normalize_mcp_definition(mcp_def)
                    self._mcp_tools_cache.append(normalized)
                else:
                    # 为没有 MCP 定义的 Plugin 生成默认定义
                    self._mcp_tools_cache.append(self._generate_mcp_definition(tool))
    
    def _normalize_mcp_definition(self, mcp_def: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化 MCP 工具定义
        
        支持多种输入格式并转换为标准 MCP 格式
        """
        # 如果已经是 MCP 格式（有 name 或 inputSchema）
        if 'name' in mcp_def and ('inputSchema' in mcp_def or 'description' in mcp_def):
            return mcp_def
        
        # 如果是 OpenAI Function Calling 格式，转换
        if mcp_def.get('type') == 'function' and 'function' in mcp_def:
            func = mcp_def['function']
            return {
                "name": func.get('name', ''),
                "description": func.get('description', ''),
                "inputSchema": func.get('parameters', {
                    "type": "object",
                    "properties": {}
                })
            }
        
        # 其他情况，直接返回
        return mcp_def
    
    def _generate_mcp_definition(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """
        为 Plugin 生成符合 MCP 标准的工具定义
        
        MCP 官方格式 (2025-03-26):
        {
            "name": "tool_name",
            "title": "Human Readable Name",  // optional
            "description": "Human-readable description",
            "inputSchema": {
                "type": "object",
                "properties": {...},
                "required": [...]
            },
            "outputSchema": {...},  // optional
            "annotations": {...}    // optional
        }
        """
        return {
            "name": tool['name'],
            "description": tool.get('description', ''),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "args": {
                        "type": "string",
                        "description": f"命令参数。用法:\\n{tool.get('usage', '')[:1000]}"
                    }
                },
                "required": ["args"]
            }
        }
    
    # ==================== 公共 API ====================
    
    @property
    def tools(self) -> List[Dict[str, Any]]:
        """获取所有工具列表（兼容 LiuginManager 接口）"""
        return list(self._tools.values())
    
    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """获取指定工具"""
        return self._tools.get(name)
    
    def get_protocol(self, name: str) -> Optional[str]:
        """获取工具使用的协议"""
        return self._protocol_map.get(name)
    
    def execute(self, tool_name: str, args: str = "", **kwargs) -> Dict[str, Any]:
        """
        执行工具调用
        
        Args:
            tool_name: 工具名称
            args: 参数字符串（Plugin 格式）
            **kwargs: 关键字参数（Skill 格式或 MCP arguments）
        
        Returns:
            {"result": "..."} 格式的结果
        """
        tool = self._tools.get(tool_name)
        
        if not tool:
            return {"result": f"未找到工具: {tool_name}"}
        
        try:
            handler = tool['handler']
            protocol = tool['protocol']
            instance = tool.get('instance')
            
            if protocol == 'skill' and kwargs:
                # Skill 协议，使用 kwargs
                skill = tool['instance']
                result = skill.run(**kwargs)
                return {"result": result.message or str(result.data) if result.success else f"错误: {result.error}"}
            
            elif protocol == 'liugin' and kwargs and not args:
                # Liugin 协议但有 MCP 结构化参数，需要转换
                # 检查插件是否有 convert_mcp_args 方法
                if instance and hasattr(instance, 'convert_mcp_args'):
                    args = instance.convert_mcp_args(kwargs)
                else:
                    args = self._convert_mcp_args_to_plugin_args(tool_name, kwargs, instance)
            
            # 执行 handler
            result = handler(args)
            return {"result": result if result is not None else "无结果"}
                
        except Exception as e:
            return {"result": f"工具执行错误: {e}"}
    
    # ==================== MCP 协议支持 ====================
    
    def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """
        获取 MCP 格式的工具定义列表
        
        MCP (Model Context Protocol) 使用 OpenAI Function Calling 格式
        作为标准工具定义格式
        
        Returns:
            List of MCP tool definitions
        """
        with self._lock:
            if self._mcp_tools_cache is None:
                self._build_mcp_cache()
            return self._mcp_tools_cache.copy()  # 返回副本，避免外部修改
    
    def mcp_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP 格式的工具调用入口
        
        这是 MCP 协议的主要调用接口，接收结构化参数并返回结果
        
        Args:
            tool_name: 工具名称
            arguments: 结构化参数 (JSON对象)
        
        Returns:
            MCP 标准响应格式:
            {
                "content": [
                    {
                        "type": "text",
                        "text": "结果内容"
                    }
                ],
                "isError": false
            }
        """
        tool = self._tools.get(tool_name)
        
        if not tool:
            return self._mcp_error(f"未找到工具: {tool_name}")
        
        try:
            protocol = tool['protocol']
            instance = tool.get('instance')
            
            if protocol == 'liugin':
                # Liugin 协议: 将 arguments 转换为 args 字符串
                args = self._convert_mcp_args_to_plugin_args(tool_name, arguments, instance)
                result = tool['handler'](args)
                return self._mcp_success(result if result else "执行完成")
            
            elif protocol == 'skill':
                # Skill 协议: 直接传递 arguments 作为 kwargs
                from skills.base import MarkdownSkill
                
                if isinstance(instance, MarkdownSkill):
                    return self._mcp_success(f"[Skill: {instance.name}]\n{instance.instructions}")
                
                if hasattr(instance, 'run'):
                    result = instance.run(**arguments)
                    if result.success:
                        return self._mcp_success(result.message or str(result.data))
                    else:
                        return self._mcp_error(f"执行失败: {result.error}")
            
            return self._mcp_error(f"未知协议类型: {protocol}")
            
        except Exception as e:
            return self._mcp_error(f"工具执行错误: {str(e)}")
    
    def _convert_mcp_args_to_plugin_args(self, tool_name: str, arguments: Dict[str, Any], 
                                          instance: Any) -> str:
        """
        将 MCP 结构化参数转换为 Plugin 的 args 字符串
        
        Args:
            tool_name: 工具名称
            arguments: MCP 参数对象
            instance: 插件实例（可能有自定义转换方法）
        
        Returns:
            args 字符串
        """
        # 检查插件是否有自定义的 MCP 参数转换方法
        if instance and hasattr(instance, 'convert_mcp_args'):
            return instance.convert_mcp_args(arguments)
        
        # 默认转换策略
        if 'args' in arguments:
            # 如果有 args 字段，直接使用
            return arguments['args']
        
        # 将 arguments 转换为命令行格式
        parts = []
        
        # 第一个参数通常是操作/命令
        if 'operation' in arguments:
            parts.append(arguments['operation'])
        elif 'action' in arguments:
            parts.append(arguments['action'])
        
        # 添加其他参数
        for key, value in arguments.items():
            if key in ('operation', 'action'):
                continue
            
            if isinstance(value, bool):
                if value:
                    parts.append(f"-{key}")
            elif isinstance(value, (list, tuple)):
                for v in value:
                    parts.append(f"--{key}")
                    parts.append(self._quote_if_needed(str(v)))
            else:
                parts.append(f"--{key}")
                parts.append(self._quote_if_needed(str(value)))
        
        return ' '.join(parts)
    
    def _quote_if_needed(self, s: str) -> str:
        """如果字符串包含空格，添加引号"""
        if ' ' in s or '"' in s:
            return f'"{s}"'
        return s
    
    def _mcp_success(self, text: str) -> Dict[str, Any]:
        """生成 MCP 成功响应"""
        return {
            "content": [
                {
                    "type": "text",
                    "text": text
                }
            ],
            "isError": False
        }
    
    def _mcp_error(self, error_msg: str) -> Dict[str, Any]:
        """生成 MCP 错误响应"""
        return {
            "content": [
                {
                    "type": "text",
                    "text": error_msg
                }
            ],
            "isError": True
        }
    
    # ==================== 兼容性 API ====================
    
    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """
        获取 OpenAI Function Calling 格式的工具定义
        
        OpenAI 格式:
        {
            "type": "function",
            "function": {
                "name": "...",
                "description": "...",
                "parameters": {...}
            }
        }
        """
        tools = []
        for mcp_def in self.get_mcp_tools():
            tools.append({
                "type": "function",
                "function": {
                    "name": mcp_def.get("name", ""),
                    "description": mcp_def.get("description", ""),
                    "parameters": mcp_def.get("inputSchema", {
                        "type": "object",
                        "properties": {}
                    })
                }
            })
        return tools
    
    def get_anthropic_tools(self) -> List[Dict[str, Any]]:
        """
        获取 Anthropic Tool Use 格式的工具定义
        
        Anthropic 格式:
        {
            "name": "tool_name",
            "description": "...",
            "input_schema": {...}
        }
        """
        tools = []
        for mcp_def in self.get_mcp_tools():
            tools.append({
                "name": mcp_def.get("name", ""),
                "description": mcp_def.get("description", ""),
                "input_schema": mcp_def.get("inputSchema", {
                    "type": "object",
                    "properties": {}
                })
            })
        return tools
    
    def search_tools(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        搜索工具
        
        Args:
            query: 搜索关键词
            limit: 返回数量限制
        
        Returns:
            匹配的工具列表
        """
        query_lower = query.lower()
        # 标准化：移除所有分隔符（连字符、下划线、空格）
        query_normalized = query_lower.replace('-', '').replace('_', '').replace(' ', '')
        matches = []
        
        for tool in self._tools.values():
            score = 0
            name = tool['name'].lower()
            name_normalized = name.replace('-', '').replace('_', '')
            desc = tool['description'].lower()
            keywords = [kw.lower() for kw in tool.get('keywords', [])]
            
            # 名称完全匹配（忽略分隔符差异）
            if query_lower == name or query_normalized == name_normalized:
                score += 100
            # 名称包含（标准化后匹配）
            elif query_normalized in name_normalized or query_lower in name:
                score += 50
            # 描述包含
            if query_lower in desc:
                score += 30
            # 关键词匹配
            for kw in keywords:
                kw_normalized = kw.replace('-', '').replace('_', '')
                if query_lower in kw or query_normalized in kw_normalized:
                    score += 20
                    break
            
            if score > 0:
                matches.append({
                    'name': tool['name'],
                    'description': tool['description'],
                    'usage': tool.get('usage', ''),
                    'keywords': keywords,
                    'protocol': tool['protocol'],
                    'instance': tool.get('instance'),
                    'score': score
                })
        
        # 按分数排序
        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches[:limit]
    
    def register_tool(self, name: str, handler: callable, description: str = "", 
                      protocol: str = "custom", mcp_definition: Dict = None, **kwargs) -> None:
        """
        动态注册工具
        
        Args:
            name: 工具名称
            handler: 处理函数
            description: 描述
            protocol: 协议类型
            mcp_definition: MCP 工具定义（可选）
        """
        with self._lock:
            self._tools[name] = {
                'name': name,
                'description': description,
                'handler': handler,
                'protocol': protocol,
                'mcp_definition': mcp_definition,
                **kwargs
            }
            self._protocol_map[name] = protocol
            
            # 更新缓存
            if self._mcp_tools_cache is not None:
                if mcp_definition:
                    self._mcp_tools_cache.append(mcp_definition)
                else:
                    self._mcp_tools_cache.append(self._generate_mcp_definition(self._tools[name]))
    
    def unregister_tool(self, name: str) -> bool:
        """注销工具"""
        with self._lock:
            if name in self._tools:
                del self._tools[name]
                del self._protocol_map[name]
                # 重建缓存
                self._build_mcp_cache()
                return True
            return False
    
    def get_skills_system_prompt(self) -> str:
        """
        获取所有技能的系统提示词
        
        用于注入到 AI 的 system prompt 中，
        让 AI 了解如何使用这些技能
        """
        skill_prompts = []
        
        for name, tool in self._tools.items():
            if tool['protocol'] == 'skill':
                instance = tool.get('instance')
                if instance:
                    # 获取技能指令
                    instructions = getattr(instance, 'instructions', '')
                    scripts_dir = getattr(instance, 'scripts_dir', '')
                    
                    prompt_parts = [f"## 技能: {name}"]
                    prompt_parts.append(f"描述: {tool['description']}")
                    
                    if instructions:
                        # 截取关键部分，避免过长
                        prompt_parts.append(f"\n{instructions}")
                    
                    if scripts_dir:
                        prompt_parts.append(f"\n脚本目录: {scripts_dir}")
                    
                    skill_prompts.append('\n'.join(prompt_parts))
        
        if skill_prompts:
            header = "# 已加载的 Agent Skills\n以下技能可用于执行特定任务，调用方式与工具相同：\n"
            return header + '\n\n---\n\n'.join(skill_prompts)
        
        return ""
    
    def get_tools_prompt(self) -> str:
        """
        获取工具使用提示词（兼容旧接口）
        
        包含 Plugin 和 Skill 两种协议的工具说明
        """
        prompts = []
        
        # Liugin 协议工具
        plugin_tools = [t for t in self._tools.values() if t['protocol'] == 'liugin']
        if plugin_tools:
            prompts.append("## Liugin 工具")
            for tool in plugin_tools:
                usage = tool.get('usage', '')
                if usage:
                    prompts.append(f"### {tool['name']}\n{usage}\n")
        
        # Skill 协议工具（使用系统提示词）
        skills_prompt = self.get_skills_system_prompt()
        if skills_prompt:
            prompts.append(skills_prompt)
        
        return '\n\n'.join(prompts)
    
    # ==================== MCP Server 模式支持 ====================
    
    def get_mcp_server_info(self) -> Dict[str, Any]:
        """
        获取 MCP Server 信息
        
        用于 MCP 客户端连接时的初始化响应
        """
        return {
            "name": "xiaoli-tool-server",
            "version": "1.0.0",
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {
                    "listChanged": True
                }
            }
        }
    
    def handle_mcp_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理 MCP 协议请求
        
        统一处理 MCP 客户端的各种请求
        
        Args:
            request: MCP 请求对象
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list" | "tools/call" | ...,
                "params": {...}
            }
        
        Returns:
            MCP 响应对象
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {...}
            }
        """
        method = request.get('method', '')
        params = request.get('params', {})
        req_id = request.get('id')
        
        result = None
        error = None
        
        try:
            if method == 'tools/list':
                result = {"tools": self.get_mcp_tools()}
            
            elif method == 'tools/call':
                tool_name = params.get('name')
                arguments = params.get('arguments', {})
                if not tool_name:
                    error = {"code": -32602, "message": "Missing tool name"}
                else:
                    result = self.mcp_call(tool_name, arguments)
            
            elif method == 'initialize':
                result = self.get_mcp_server_info()
            
            elif method == 'ping':
                result = {}
            
            else:
                error = {"code": -32601, "message": f"Method not found: {method}"}
        
        except Exception as e:
            error = {"code": -32603, "message": str(e)}
        
        response = {"jsonrpc": "2.0", "id": req_id}
        if error:
            response["error"] = error
        else:
            response["result"] = result
        
        return response