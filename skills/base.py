"""
Agent Skills 协议基类
支持两种格式:
1. 标准开源格式: SKILL.md (YAML frontmatter + Markdown)
2. Python 类格式: Skill 子类 (用于需要代码执行的技能)
"""

import os
import re
import json
import threading
import importlib
import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Union


class ParameterType(Enum):
    """参数类型枚举 - 映射到 JSON Schema"""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class SkillParameter:
    """技能参数定义"""
    name: str
    param_type: ParameterType
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None
    
    def to_json_schema(self) -> Dict[str, Any]:
        """转换为 JSON Schema 格式"""
        schema = {
            "type": self.param_type.value,
            "description": self.description
        }
        if self.enum:
            schema["enum"] = self.enum
        return schema


@dataclass
class SkillResult:
    """技能执行结果"""
    success: bool
    data: Any = None
    message: str = ""
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        if self.success:
            return self.message or str(self.data)
        return f"Error: {self.error}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "error": self.error,
            "metadata": self.metadata
        }


class Skill(ABC):
    """技能基类 - 用于 Python 实现的技能"""
    
    def __init__(self):
        self.name: str = ""
        self.description: str = ""
        self.version: str = "1.0.0"
        self.author: str = ""
        self.tags: List[str] = []
        self._cli = None
    
    @property
    @abstractmethod
    def parameters(self) -> List[SkillParameter]:
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> SkillResult:
        pass
    
    def set_cli(self, cli) -> None:
        self._cli = cli
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """获取 OpenAI 格式的工具定义"""
        properties = {}
        required = []
        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }
    
    def get_anthropic_tool_definition(self) -> Dict[str, Any]:
        """获取 Anthropic 格式的工具定义"""
        properties = {}
        required = []
        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    
    def run(self, **kwargs) -> SkillResult:
        """执行技能（带参数验证）"""
        error = self._validate_parameters(**kwargs)
        if error:
            return SkillResult(success=False, error=error)
        return self.execute(**kwargs)
    
    def _validate_parameters(self, **kwargs) -> Optional[str]:
        """验证参数"""
        for param in self.parameters:
            if param.required and param.name not in kwargs:
                return f"缺少必需参数: {param.name}"
        return None


@dataclass
class MarkdownSkill:
    """Markdown 格式的技能 (标准 Agent Skills 格式)"""
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    license: str = "MIT"
    tools: List[str] = field(default_factory=list)
    instructions: str = ""
    file_path: str = ""
    scripts_dir: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)  # 从 frontmatter 解析
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """获取 OpenAI 格式的工具定义 - 从元数据动态生成"""
        properties = {}
        required = []
        
        if self.parameters:
            # 从 frontmatter 中的 parameters 生成
            for name, schema in self.parameters.items():
                if isinstance(schema, dict):
                    properties[name] = schema
                    if schema.get("required", False):
                        required.append(name)
        else:
            # 通用定义：operation + args
            properties = {
                "operation": {
                    "type": "string",
                    "description": f"要执行的操作（可用工具: {', '.join(self.tools)}）" if self.tools else "要执行的操作"
                },
                "args": {
                    "type": "string",
                    "description": "操作参数"
                }
            }
            required = ["operation"]
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }
    
    def get_anthropic_tool_definition(self) -> Dict[str, Any]:
        """获取 Anthropic 格式的工具定义"""
        tool_def = self.get_tool_definition()
        func = tool_def.get("function", {})
        return {
            "name": func.get("name", self.name),
            "description": func.get("description", self.description),
            "input_schema": func.get("parameters", {"type": "object", "properties": {}})
        }


class SkillLoader:
    """技能加载器 - 支持标准 SKILL.md 和 Python 类两种格式"""
    
    def __init__(self, skills_dir: str = None):
        self.skills_dir = skills_dir
        self._skills: Dict[str, Union[Skill, MarkdownSkill]] = {}
        self._lock = threading.RLock()
    
    @property
    def skills(self) -> Dict[str, Union[Skill, MarkdownSkill]]:
        return self._skills.copy()
    
    def discover_skills(self, skills_dir: str = None) -> List[Dict[str, str]]:
        """发现所有技能"""
        search_dir = skills_dir or self.skills_dir
        if not search_dir or not os.path.isdir(search_dir):
            return []
        
        discovered = []
        for item in os.listdir(search_dir):
            item_path = os.path.join(search_dir, item)
            
            # 跳过特殊文件
            if item in ('__init__.py', 'base.py') or item.startswith('_') or item.startswith('.'):
                continue
            
            # SKILL.md 格式 (目录)
            skill_md = os.path.join(item_path, "SKILL.md")
            if os.path.isdir(item_path) and os.path.isfile(skill_md):
                discovered.append({"name": item, "type": "markdown", "path": skill_md})
            
            # Python 单文件格式
            elif item.endswith('.py') and os.path.isfile(item_path):
                discovered.append({"name": item[:-3], "type": "python", "path": item_path})
        
        return discovered
    
    def parse_skill_md(self, file_path: str) -> Optional[MarkdownSkill]:
        """解析 SKILL.md 文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析 YAML frontmatter
            if not content.startswith('---'):
                return None
            
            end_idx = content.find('---', 3)
            if end_idx == -1:
                return None
            
            frontmatter = content[3:end_idx].strip()
            instructions = content[end_idx + 3:].strip()
            
            # 解析 YAML (简化版)
            metadata = {}
            current_list = None
            current_key = None
            
            for line in frontmatter.split('\n'):
                stripped = line.strip()
                if not stripped:
                    continue
                
                # 列表项
                if stripped.startswith('- '):
                    if current_key and current_key not in metadata:
                        metadata[current_key] = []
                    if current_key and isinstance(metadata.get(current_key), list):
                        metadata[current_key].append(stripped[2:])
                    continue
                
                # 键值对
                if ':' in line:
                    current_key = None
                    colon_idx = line.index(':')
                    key = line[:colon_idx].strip()
                    value = line[colon_idx + 1:].strip()
                    
                    if value:
                        # 处理列表格式 [a, b, c]
                        if value.startswith('[') and value.endswith(']'):
                            value = [v.strip() for v in value[1:-1].split(',') if v.strip()]
                        metadata[key] = value
                    else:
                        current_key = key
                        current_list = []
            
            skill_dir = os.path.dirname(file_path)
            scripts_dir = os.path.join(skill_dir, "scripts")
            
            # 解析参数定义 (从 frontmatter 中的 parameters 字段)
            parameters = {}
            if "parameters" in metadata and isinstance(metadata["parameters"], dict):
                parameters = metadata["parameters"]
            elif "params" in metadata and isinstance(metadata["params"], dict):
                parameters = metadata["params"]
            
            return MarkdownSkill(
                name=metadata.get('name', os.path.basename(skill_dir)),
                description=metadata.get('description', ''),
                version=metadata.get('version', '1.0.0'),
                author=metadata.get('author', ''),
                license=metadata.get('license', 'MIT'),
                tools=metadata.get('tools', []) if isinstance(metadata.get('tools'), list) else [],
                instructions=instructions,
                file_path=file_path,
                scripts_dir=scripts_dir if os.path.isdir(scripts_dir) else ""
            )
            
        except Exception as e:
            print(f"解析 SKILL.md 失败 ({file_path}): {e}")
            return None
    
    def load_skill(self, skill_info: Dict[str, str]) -> Optional[Union[Skill, MarkdownSkill]]:
        """加载单个技能"""
        skill_type = skill_info.get('type')
        skill_path = skill_info.get('path')
        skill_name = skill_info.get('name')
        
        if skill_type == "markdown":
            skill = self.parse_skill_md(skill_path)
            if skill:
                self._skills[skill.name] = skill
                return skill
        
        elif skill_type == "python":
            try:
                # 动态导入 Python 模块
                spec = importlib.util.spec_from_file_location(skill_name, skill_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 查找 Skill 子类
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, Skill) and obj is not Skill:
                        skill = obj()
                        self._skills[skill.name] = skill
                        return skill
                        
            except Exception as e:
                print(f"加载 Python 技能 '{skill_name}' 失败: {e}")
        
        return None
    
    def load_all_skills(self, skills_dir: str = None) -> Dict[str, Union[Skill, MarkdownSkill]]:
        """加载所有技能"""
        discovered = self.discover_skills(skills_dir)
        
        for skill_info in discovered:
            self.load_skill(skill_info)
        
        return self.skills
    
    def get_skill(self, name: str) -> Optional[Union[Skill, MarkdownSkill]]:
        """获取已加载的技能"""
        return self._skills.get(name)
    
    def get_all_tool_definitions(self, format: str = "openai") -> List[Dict]:
        """获取所有技能的工具定义"""
        definitions = []
        for skill in self._skills.values():
            if format == "anthropic":
                definitions.append(skill.get_anthropic_tool_definition())
            else:
                definitions.append(skill.get_tool_definition())
        return definitions