"""
Agent Skills 协议实现
支持两种格式:
1. 标准开源格式: SKILL.md (YAML frontmatter + Markdown)
2. Python 类格式: Skill 子类 (用于需要代码执行的技能)
"""

from .base import (
    # 基础类
    Skill,
    SkillResult, 
    SkillParameter,
    ParameterType,
    SkillLoader,
    # Markdown 技能
    MarkdownSkill,
)

__all__ = [
    'Skill',
    'SkillResult', 
    'SkillParameter',
    'ParameterType',
    'SkillLoader',
    'MarkdownSkill',
]

__version__ = '1.0.0'
