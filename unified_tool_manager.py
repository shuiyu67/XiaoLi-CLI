"""
统一工具管理器 - 协调 Liugin、Skill 和 MCP 三套协议
自动判断并路由到正确的处理器
"""

import os
import json
import logging
import threading
from typing import Dict, List, Any, Optional, Union, Callable
from colorama import Fore, Style
from xcli_core.tool_result import ToolResult, ErrorCode
from xcli_core.verbose import vprint

logger = logging.getLogger(__name__)


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
        """初始化并加载所有工具"""
        self._plugins_dir = plugins_dir
        self._skills_dir = skills_dir
        self._load_plugins(plugins_dir)
        self._load_skills(skills_dir)
        self._build_mcp_cache()

        n_liugin = sum(1 for p in self._protocol_map.values() if p == 'liugin')
        n_skill = sum(1 for p in self._protocol_map.values() if p == 'skill')
        print(f"{Fore.GREEN}已加载 {len(self._tools)} 个工具{Style.RESET_ALL}"
              f"{Fore.BLACK}{Style.BRIGHT} (Liugin {n_liugin} · Skill {n_skill}"
              f"，--verbose 看明细){Style.RESET_ALL}")

    def shutdown(self) -> None:
        """关闭管理器，清理所有插件实例"""
        with self._lock:
            for name, tool in self._tools.items():
                instance = tool.get('instance')
                if instance and hasattr(instance, 'cleanup'):
                    try:
                        instance.cleanup()
                    except Exception:
                        pass
            self._tools.clear()
            self._protocol_map.clear()
            self._mcp_tools_cache = None

    def _load_plugins(self, plugins_dir: str) -> None:
        """加载 Liugin 协议工具"""
        import importlib.util

        if not os.path.exists(plugins_dir):
            return

        enabled_plugins = self._get_enabled_plugins(plugins_dir)

        for filename in os.listdir(plugins_dir):
            if not filename.endswith('.py') or filename == '__init__.py':
                continue

            plugin_name = filename[:-3]

            if enabled_plugins is not None and plugin_name.lower() not in enabled_plugins:
                continue

            plugin_path = os.path.join(plugins_dir, filename)

            try:
                spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                plugin_class = None
                if hasattr(module, 'Liugin'):
                    plugin_class = module.Liugin
                elif hasattr(module, 'Plugin'):
                    plugin_class = module.Plugin

                if plugin_class:
                    plugin_instance = plugin_class()

                    if hasattr(plugin_instance, 'set_cli') and self.cli:
                        plugin_instance.set_cli(self.cli)

                    tool_info = plugin_instance.get_tool_info()
                    tool_name = tool_info.get('name', plugin_name)

                    mcp_definition = None
                    if hasattr(plugin_instance, 'get_mcp_definition'):
                        mcp_definition = plugin_instance.get_mcp_definition()

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

            discovered = self._skill_loader.discover_skills(skills_dir)
            vprint(f"{Fore.CYAN}发现 {len(discovered)} 个技能: {[s['name'] for s in discovered]}{Style.RESET_ALL}")

            self._skill_loader.load_all_skills(skills_dir)

            loaded_count = len(self._skill_loader.skills)
            if loaded_count == 0:
                print(f"{Fore.YELLOW}未加载任何 Skill 技能{Style.RESET_ALL}")
                return

            for skill_name, skill in self._skill_loader.skills.items():
                if hasattr(skill, 'set_cli') and self.cli:
                    skill.set_cli(self.cli)

                tool_def = skill.get_tool_definition()
                func_def = tool_def.get('function', {})

                if skill_name in self._tools:
                    old_protocol = self._protocol_map[skill_name]
                    print(f"{Fore.YELLOW}工具 '{skill_name}' 已存在({old_protocol})，使用 Skill 协议覆盖{Style.RESET_ALL}")

                is_markdown = isinstance(skill, MarkdownSkill)
                skill_format = "markdown" if is_markdown else "python"

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
                    'mcp_definition': tool_def
                }
                self._protocol_map[skill_name] = 'skill'

                vprint(f"{Fore.GREEN}已加载 Skill ({skill_format}): {skill_name}{Style.RESET_ALL}")

        except ImportError as e:
            print(f"{Fore.YELLOW}Skill 协议模块未找到: {e}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}加载 Skills 失败: {e}{Style.RESET_ALL}")

    def _create_skill_handler(self, skill) -> callable:
        """为 Skill 创建兼容 Plugin 的 handler"""
        from skills.base import MarkdownSkill, Skill

        def handler(args: str):
            """Skill handler - 返回 ToolResult"""
            kwargs = {}

            args = args.strip()
            if args.startswith('{'):
                try:
                    kwargs = json.loads(args)
                except json.JSONDecodeError:
                    kwargs = {'operation': args}
            elif '=' in args:
                for part in args.split():
                    if '=' in part:
                        k, v = part.split('=', 1)
                        kwargs[k.strip()] = v.strip()
                    else:
                        kwargs.setdefault('operation', part)
            else:
                kwargs = {'operation': args}

            if isinstance(skill, MarkdownSkill):
                return ToolResult.ok(f"[Skill: {skill.name}]\n{skill.instructions}")

            if hasattr(skill, 'run'):
                result = skill.run(**kwargs)
                if result.success:
                    return ToolResult.ok(result.message or str(result.data))
                else:
                    return ToolResult.fail(str(result.error), ErrorCode.EXEC_FAILED)

            return ToolResult.fail(f"未知的技能类型: {type(skill)}", ErrorCode.NOT_IMPLEMENTED)

        return handler

    def _get_enabled_plugins(self, plugins_dir: str) -> Optional[List[str]]:
        """获取启用的插件列表"""
        enabled_env = os.environ.get("XIAOLI_ENABLED_PLUGINS")
        if enabled_env is not None:
            if enabled_env == "":
                return []
            return [p.lower() for p in enabled_env.split(",")]

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

        return None

    def _build_mcp_cache(self) -> None:
        """构建 MCP 工具定义缓存（线程安全）"""
        with self._lock:
            self._mcp_tools_cache = []
            for tool in self._tools.values():
                mcp_def = tool.get('mcp_definition')
                if mcp_def:
                    normalized = self._normalize_mcp_definition(mcp_def)
                    self._mcp_tools_cache.append(normalized)
                else:
                    self._mcp_tools_cache.append(self._generate_mcp_definition(tool))

    def _normalize_mcp_definition(self, mcp_def: Dict[str, Any]) -> Dict[str, Any]:
        """标准化 MCP 工具定义"""
        if 'name' in mcp_def and ('inputSchema' in mcp_def or 'description' in mcp_def):
            return mcp_def

        if mcp_def.get('type') == 'function' and 'function' in mcp_def:
            func = mcp_def['function']
            return {
                "name": func.get('name', ''),
                "description": func.get('description', ''),
                "inputSchema": func.get('parameters', {"type": "object", "properties": {}})
            }

        return mcp_def

    def _generate_mcp_definition(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """为 Plugin 生成符合 MCP 标准的工具定义"""
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

    def execute(self, tool_name: str, args: str = "", **kwargs) -> ToolResult:
        """执行工具调用，返回 ToolResult"""
        with self._lock:
            tool = self._tools.get(tool_name)

        if not tool:
            return ToolResult.fail(f"未找到工具: {tool_name}", ErrorCode.NOT_FOUND, tool_name=tool_name)

        try:
            handler = tool['handler']
            protocol = tool['protocol']
            instance = tool.get('instance')

            if protocol == 'skill' and kwargs:
                skill = tool['instance']
                result = skill.run(**kwargs)
                if result.success:
                    return ToolResult.ok(result.message or str(result.data), tool_name=tool_name)
                else:
                    return ToolResult.fail(str(result.error), ErrorCode.EXEC_FAILED, tool_name=tool_name)

            elif protocol == 'liugin' and kwargs and not args:
                if instance and hasattr(instance, 'convert_mcp_args'):
                    args = instance.convert_mcp_args(kwargs)
                else:
                    args = self._convert_mcp_args_to_plugin_args(tool_name, kwargs, instance)

            result = handler(args)
            # 兼容：handler 可能返回 ToolResult 或字符串
            if isinstance(result, ToolResult):
                result.tool_name = tool_name
                return result
            return ToolResult.ok(result if result is not None else "执行完成", tool_name=tool_name)

        except Exception as e:
            logger.exception(f"工具 {tool_name} 执行异常")
            return ToolResult.fail(str(e), ErrorCode.INTERNAL_ERROR, tool_name=tool_name)

    def execute_dict(self, tool_name: str, args: str = "", **kwargs) -> Dict[str, Any]:
        """执行工具调用，返回 dict（兼容旧接口）"""
        return self.execute(tool_name, args, **kwargs).to_dict()

    # ==================== MCP 协议支持 ====================

    def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """获取 MCP 格式的工具定义列表"""
        with self._lock:
            if self._mcp_tools_cache is None:
                self._build_mcp_cache()
            return self._mcp_tools_cache.copy()

    def mcp_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """MCP 格式的工具调用入口"""
        tool = self._tools.get(tool_name)

        if not tool:
            return ToolResult.fail(f"未找到工具: {tool_name}", ErrorCode.NOT_FOUND, tool_name=tool_name).to_mcp()

        try:
            protocol = tool['protocol']
            instance = tool.get('instance')

            if protocol == 'liugin':
                args = self._convert_mcp_args_to_plugin_args(tool_name, arguments, instance)
                result = tool['handler'](args)
                # 兼容：handler 可能返回 ToolResult 或字符串
                if isinstance(result, ToolResult):
                    result.tool_name = tool_name
                    return result.to_mcp()
                return ToolResult.ok(result or "执行完成", tool_name=tool_name).to_mcp()

            elif protocol == 'skill':
                from skills.base import MarkdownSkill

                if isinstance(instance, MarkdownSkill):
                    return ToolResult.ok(f"[Skill: {instance.name}]\n{instance.instructions}", tool_name=tool_name).to_mcp()

                if hasattr(instance, 'run'):
                    result = instance.run(**arguments)
                    if result.success:
                        return ToolResult.ok(result.message or str(result.data), tool_name=tool_name).to_mcp()
                    else:
                        return ToolResult.fail(str(result.error), ErrorCode.EXEC_FAILED, tool_name=tool_name).to_mcp()

            return ToolResult.fail(f"未知协议类型: {protocol}", ErrorCode.INTERNAL_ERROR, tool_name=tool_name).to_mcp()

        except Exception as e:
            logger.exception(f"MCP 调用 {tool_name} 异常")
            return ToolResult.fail(str(e), ErrorCode.INTERNAL_ERROR, tool_name=tool_name).to_mcp()

    def _convert_mcp_args_to_plugin_args(self, tool_name: str, arguments: Dict[str, Any],
                                          instance: Any) -> str:
        """将 MCP 结构化参数转换为 Plugin 的 args 字符串"""
        if instance and hasattr(instance, 'convert_mcp_args'):
            return instance.convert_mcp_args(arguments)

        if 'args' in arguments:
            return arguments['args']

        parts = []

        if 'operation' in arguments:
            parts.append(arguments['operation'])
        elif 'action' in arguments:
            parts.append(arguments['action'])

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
        if ' ' in s or '"' in s:
            return f'"{s}"'
        return s

    def _mcp_success(self, text: str) -> Dict[str, Any]:
        """MCP 成功响应（兼容旧接口，推荐用 ToolResult.ok().to_mcp()）"""
        return ToolResult.ok(text).to_mcp()

    def _mcp_error(self, error_msg: str) -> Dict[str, Any]:
        """MCP 错误响应（兼容旧接口，推荐用 ToolResult.fail().to_mcp()）"""
        return ToolResult.fail(error_msg).to_mcp()

    # ==================== 兼容性 API ====================

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """获取 OpenAI Function Calling 格式的工具定义"""
        tools = []
        for mcp_def in self.get_mcp_tools():
            tools.append({
                "type": "function",
                "function": {
                    "name": mcp_def.get("name", ""),
                    "description": mcp_def.get("description", ""),
                    "parameters": mcp_def.get("inputSchema", {"type": "object", "properties": {}})
                }
            })
        return tools

    def get_anthropic_tools(self) -> List[Dict[str, Any]]:
        """获取 Anthropic Tool Use 格式的工具定义"""
        tools = []
        for mcp_def in self.get_mcp_tools():
            tools.append({
                "name": mcp_def.get("name", ""),
                "description": mcp_def.get("description", ""),
                "input_schema": mcp_def.get("inputSchema", {"type": "object", "properties": {}})
            })
        return tools

    def search_tools(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """搜索工具"""
        query_lower = query.lower()
        query_normalized = query_lower.replace('-', '').replace('_', '').replace(' ', '')
        matches = []

        for tool in self._tools.values():
            score = self._score_tool_match(tool, query_lower, query_normalized)
            if score > 0:
                matches.append({
                    'name': tool['name'],
                    'description': tool['description'],
                    'usage': tool.get('usage', ''),
                    'keywords': [kw.lower() for kw in tool.get('keywords', [])],
                    'protocol': tool['protocol'],
                    'instance': tool.get('instance'),
                    'score': score
                })

        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches[:limit]

    def _score_tool_match(self, tool: Dict, query_lower: str, query_normalized: str) -> int:
        """计算工具匹配分数"""
        score = 0
        name = tool.get('name', '').lower()
        name_normalized = name.replace('-', '').replace('_', '')
        desc = tool.get('description', '').lower()
        keywords = [kw.lower() for kw in tool.get('keywords', [])]

        if query_lower == name or query_normalized == name_normalized:
            score += 100
        elif query_normalized in name_normalized or query_lower in name:
            score += 50
        if query_lower in desc:
            score += 30
        for kw in keywords:
            kw_normalized = kw.replace('-', '').replace('_', '')
            if query_lower in kw or query_normalized in kw_normalized:
                score += 20
                break
        return score

    def register_tool(self, name: str, handler: callable, description: str = "",
                      protocol: str = "custom", mcp_definition: Dict = None, **kwargs) -> None:
        """动态注册工具"""
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

            if self._mcp_tools_cache is not None:
                if mcp_definition:
                    self._mcp_tools_cache.append(mcp_definition)
                else:
                    self._mcp_tools_cache.append(self._generate_mcp_definition(self._tools[name]))

    def unregister_tool(self, name: str) -> bool:
        """注销工具"""
        with self._lock:
            if name in self._tools:
                instance = self._tools[name].get('instance')
                if instance and hasattr(instance, 'cleanup'):
                    try:
                        instance.cleanup()
                    except Exception:
                        pass
                del self._tools[name]
                del self._protocol_map[name]
                self._build_mcp_cache()
                return True
            return False

    def get_all_tools_info(self) -> List[Dict[str, Any]]:
        """获取所有工具的简要信息，用于系统提示词"""
        result = []
        for tool in self._tools.values():
            result.append({
                'name': tool['name'],
                'description': tool.get('description', ''),
                'keywords': tool.get('keywords', []),
                'protocol': tool.get('protocol', ''),
            })
        return result

    def get_tool_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取工具（兼容 LiuginManager 接口）"""
        return self._tools.get(name)

    def get_skills_system_prompt(self) -> str:
        """获取所有技能的系统提示词"""
        skill_prompts = []

        for name, tool in self._tools.items():
            if tool['protocol'] == 'skill':
                instance = tool.get('instance')
                if instance:
                    instructions = getattr(instance, 'instructions', '')
                    scripts_dir = getattr(instance, 'scripts_dir', '')

                    prompt_parts = [f"## 技能: {name}"]
                    prompt_parts.append(f"描述: {tool['description']}")

                    if instructions:
                        prompt_parts.append(f"\n{instructions}")

                    if scripts_dir:
                        prompt_parts.append(f"\n脚本目录: {scripts_dir}")

                    skill_prompts.append('\n'.join(prompt_parts))

        if skill_prompts:
            header = "# 已加载的 Agent Skills\n以下技能可用于执行特定任务，调用方式与工具相同：\n"
            return header + '\n\n---\n\n'.join(skill_prompts)

        return ""

    def get_tools_prompt(self) -> str:
        """获取工具使用提示词（兼容旧接口）"""
        prompts = []

        plugin_tools = [t for t in self._tools.values() if t['protocol'] == 'liugin']
        if plugin_tools:
            prompts.append("## Liugin 工具")
            for tool in plugin_tools:
                usage = tool.get('usage', '')
                if usage:
                    prompts.append(f"### {tool['name']}\n{usage}\n")

        skills_prompt = self.get_skills_system_prompt()
        if skills_prompt:
            prompts.append(skills_prompt)

        return '\n\n'.join(prompts)

    # ==================== MCP Server 模式支持 ====================

    def get_mcp_server_info(self) -> Dict[str, Any]:
        """获取 MCP Server 信息"""
        return {
            "name": "xiaoli-tool-server",
            "version": "1.0.0",
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": True}}
        }

    def handle_mcp_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理 MCP 协议请求"""
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
