"""Agents 体系化 - opencode 式 markdown 定义 + @委派

设计：
- agents/ 目录下的 *.md 文件即 agent 定义，frontmatter 声明元数据：
    ---
    name: coder
    description: 代码实现专家
    tools: code_editor, git_tools, file_manager
    model:
    ---
    正文即该 agent 的系统提示词。
- AgentManager 负责加载、匹配、委派。
- 委派执行通过注入的 runner 回调完成，便于测试（runner 不触真实引擎）。
"""
import os
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


@dataclass
class AgentDef:
    name: str
    description: str = ""
    tools: List[str] = field(default_factory=list)
    model: Optional[str] = None
    system_prompt: str = ""


class AgentManager:
    def __init__(self):
        self._agents: Dict[str, AgentDef] = {}

    # ── 加载 ──
    def load_dir(self, directory: str) -> int:
        """扫描目录下的 *.md，返回加载数量。目录不存在/为空则忽略。"""
        if not directory or not os.path.isdir(directory):
            return 0
        count = 0
        for fn in sorted(os.listdir(directory)):
            if not fn.endswith(".md"):
                continue
            path = os.path.join(directory, fn)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception:
                continue
            d = self._parse(text, name=os.path.splitext(fn)[0])
            if d:
                self._agents[d.name] = d
                count += 1
        return count

    @staticmethod
    def _parse(text: str, name: str) -> Optional[AgentDef]:
        meta: Dict[str, str] = {}
        body = text
        m = _FRONTMATTER_RE.match(text)
        if m:
            meta_block = m.group(1)
            body = m.group(2)
            for line in meta_block.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
        raw_tools = meta.get("tools", "")
        tools = [t.strip() for t in raw_tools.split(",") if t.strip()]
        return AgentDef(
            name=meta.get("name", name),
            description=meta.get("description", ""),
            tools=tools,
            model=meta.get("model") or None,
            system_prompt=body.strip(),
        )

    # ── 查询 ──
    def get(self, name: str) -> Optional[AgentDef]:
        return self._agents.get(name)

    def names(self) -> List[str]:
        return list(self._agents.keys())

    def list(self) -> List[AgentDef]:
        return list(self._agents.values())

    # ── 委派 ──
    def dispatch(self, name: str, task: str, runner: Callable[[str, str, List[str], Optional[str]], str]) -> str:
        """runner(system_prompt, task, tools, model) -> result 文本。"""
        d = self.get(name)
        if not d:
            raise KeyError(f"agent not found: {name}")
        return runner(d.system_prompt, task, d.tools, d.model)
