"""
安全层 - 统一的指令安全检查
拦截所有工具调用，通过 AI 识别风险并请求用户确认
"""
import json
import threading
from typing import Optional, Tuple


# ── 安全模式 ──
MODE_UNRESTRICTED = 0   # 无限制：直接执行
MODE_NORMAL = 1          # 普通：AI 识别风险
MODE_MANUAL = 2          # 人工：所有指令都确认

MODE_NAMES = {
    MODE_UNRESTRICTED: "无限制",
    MODE_NORMAL: "普通",
    MODE_MANUAL: "人工确认",
}

# ── 始终需要人工确认的指令（无论模式） ──
ALWAYS_CONFIRM = {
    ("cmd_executor", "run rm"),
    ("cmd_executor", "run chmod"),
    ("cmd_executor", "run chown"),
    ("file_manager", "delete"),
    ("git_tools", "checkout -b"),
}


class SafetyLayer:
    """统一安全检查层"""

    def __init__(self):
        self.mode = MODE_NORMAL
        self.cli = None
        self._analysis_cache = {}  # 缓存分析结果
        self._lock = threading.Lock()

    def set_cli(self, cli):
        self.cli = cli

    def get_mode(self) -> int:
        return self.mode

    def get_mode_name(self) -> str:
        return MODE_NAMES.get(self.mode, "未知")

    def set_mode(self, mode: int):
        self.mode = mode

    def cycle_mode(self) -> str:
        """切换到下一个模式，返回新模式名称"""
        self.mode = (self.mode + 1) % 3
        return self.get_mode_name()

    # ── 核心：拦截检查 ──

    def check(self, tool_name: str, tool_args: str) -> Tuple[bool, str]:
        """
        检查工具调用是否安全
        返回: (允许执行, 消息)
        """
        # 无限制模式：直接放行
        if self.mode == MODE_UNRESTRICTED:
            return True, ""

        # 检查是否是始终需要确认的指令
        args_lower = tool_args.strip().lower()
        for (t, pattern) in ALWAYS_CONFIRM:
            if tool_name == t and args_lower.startswith(pattern.split(" ", 1)[1] if " " in pattern else ""):
                return self._ask_user_confirm(
                    tool_name, tool_args,
                    risk_level="高",
                    impact="此操作始终需要人工确认",
                    reason="敏感指令"
                )

        # 人工确认模式：所有指令都确认
        if self.mode == MODE_MANUAL:
            return self._ask_user_confirm(
                tool_name, tool_args,
                risk_level="中",
                impact="当前为人工确认模式，所有指令需要确认",
                reason="模式要求"
            )

        # 普通模式：AI 识别风险
        return self._ai_analyze(tool_name, tool_args)

    # ── AI 风险识别 ──

    def _ai_analyze(self, tool_name: str, tool_args: str) -> Tuple[bool, str]:
        """使用当前引擎独立分析指令风险（不带历史对话）"""
        # 快速预检：明显安全的指令直接放行
        if self._is_quick_safe(tool_name, tool_args):
            return True, ""

        # 获取引擎
        engine = None
        if self.cli and hasattr(self.cli, 'current_engine'):
            engine = self.cli.current_engine

        if not engine:
            # 无引擎时降级为人工确认
            return self._ask_user_confirm(
                tool_name, tool_args,
                risk_level="未知",
                impact="无法进行 AI 风险分析",
                reason="无可用引擎"
            )

        # 检查缓存
        cache_key = f"{tool_name}:{tool_args[:100]}"
        with self._lock:
            if cache_key in self._analysis_cache:
                cached = self._analysis_cache[cache_key]
                if cached["safe"]:
                    return True, ""
                return self._ask_user_confirm(
                    tool_name, tool_args,
                    risk_level=cached["level"],
                    impact=cached["impact"],
                    reason=cached["reason"]
                )

        # 调用 AI 独立分析（不带任何历史对话）
        analysis_prompt = f"""你是一个安全分析器。分析以下工具调用是否存在安全风险。

工具: {tool_name}
参数: {tool_args}

只返回以下 JSON（不要其他内容）:
{{"safe": true/false, "level": "低/中/高", "reason": "风险原因", "impact": "执行后可能的影响"}}

判断标准:
- safe=true: 读取操作、查看信息、无害查询
- safe=false: 删除文件、执行系统命令、修改配置、网络请求、git 危险操作
- level 低: 只读操作但可能泄露信息
- level 中: 修改操作可撤销
- level 高: 不可逆操作、系统级操作"""

        try:
            response = engine.generate_response(analysis_prompt, system_prompt="你是安全分析器。只返回 JSON，不要其他内容。")

            if not response:
                return self._ask_user_confirm(
                    tool_name, tool_args,
                    risk_level="未知",
                    impact="AI 分析无响应",
                    reason="引擎未返回结果"
                )

            # 解析 JSON
            result = self._parse_analysis(response)

            if result and result.get("safe") is True:
                # 缓存安全结果
                with self._lock:
                    self._analysis_cache[cache_key] = result
                return True, ""

            # 不安全，请求用户确认
            level = result.get("level", "中") if result else "未知"
            reason = result.get("reason", "AI 识别到潜在风险") if result else "AI 分析失败"
            impact = result.get("impact", "未知影响") if result else "未知影响"

            return self._ask_user_confirm(
                tool_name, tool_args,
                risk_level=level,
                impact=impact,
                reason=reason
            )

        except Exception as e:
            return self._ask_user_confirm(
                tool_name, tool_args,
                risk_level="未知",
                impact=f"AI 分析异常: {e}",
                reason="分析过程出错"
            )

    def _parse_analysis(self, response: str) -> Optional[dict]:
        """解析 AI 返回的分析结果"""
        import re

        # 尝试直接解析 JSON
        response = response.strip()

        # 去掉 markdown 代码块
        if response.startswith("```"):
            response = response.split("\n", 1)[-1] if "\n" in response else response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 尝试从文本中提取 JSON
        match = re.search(r'\{[^{}]*"safe"[^{}]*\}', response)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        return None

    def _is_quick_safe(self, tool_name: str, tool_args: str) -> bool:
        """快速预检：明显安全的操作直接放行"""
        args = tool_args.strip().lower()

        # 纯读取操作
        safe_patterns = {
            "code_editor": ["read_range", "find ", "regex ", "symbols", "imports",
                            "ast_info", "stats", "structure", "context", "todo",
                            "callers", "diff ", "diff_text"],
            "git_tools": ["status", "log", "diff", "branch", "remote", "show",
                          "blame", "contributors", "summary"],
            "file_manager": ["list", "read", "info", "search"],
            "cmd_executor": [],  # 命令执行不跳过
            "auto_engineer": ["metrics", "security", "complexity", "duplicates",
                              "suggest", "info"],
            "task_manager": ["list"],
            "browser_auto": ["status", "title", "url", "text", "html", "attr",
                             "value", "eval", "query", "cookies"],
            "sub_agent": ["list", "status", "result", "stats"],
            "network_tools": ["ping", "status", "headers", "ip"],
            "tool_search": [],
        }

        patterns = safe_patterns.get(tool_name, [])
        for p in patterns:
            if args.startswith(p):
                return True

        return False

    # ── 用户交互 ──

    def _ask_user_confirm(self, tool_name: str, tool_args: str,
                          risk_level: str = "中", impact: str = "",
                          reason: str = "") -> Tuple[bool, str]:
        """向用户展示风险信息并请求确认"""
        from colorama import Fore, Style

        # 风险等级颜色
        level_colors = {
            "低": Fore.YELLOW,
            "中": Fore.LIGHTYELLOW_EX,
            "高": Fore.RED,
            "未知": Fore.LIGHTBLACK_EX,
        }
        level_color = level_colors.get(risk_level, Fore.YELLOW)

        # 截断过长的参数
        display_args = tool_args
        if len(display_args) > 200:
            display_args = display_args[:200] + "..."

        print()
        print(f"  {Fore.RED}{'═' * 50}{Style.RESET_ALL}")
        print(f"  {Fore.RED}⚠️  安全检查{Style.RESET_ALL}")
        print(f"  {Fore.RED}{'═' * 50}{Style.RESET_ALL}")
        print(f"  {Fore.CYAN}工具:{Style.RESET_ALL} {tool_name}")
        print(f"  {Fore.CYAN}指令:{Style.RESET_ALL} {display_args}")
        print(f"  {level_color}风险:{Style.RESET_ALL} {risk_level}")
        if reason:
            print(f"  {Fore.YELLOW}原因:{Style.RESET_ALL} {reason}")
        if impact:
            print(f"  {Fore.YELLOW}影响:{Style.RESET_ALL} {impact}")
        print(f"  {Fore.RED}{'─' * 50}{Style.RESET_ALL}")

        try:
            choice = input(f"  {Fore.WHITE}是否执行? (y/n): {Style.RESET_ALL}").strip().lower()
            if choice in ('y', 'yes', '是'):
                return True, "用户确认执行"
            else:
                return False, "用户取消执行"
        except (KeyboardInterrupt, EOFError):
            print()
            return False, "用户中断"


# ── 全局单例 ──
_safety = SafetyLayer()

def get_safety() -> SafetyLayer:
    return _safety
