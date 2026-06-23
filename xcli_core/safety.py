"""
工作模式 - 统一的安全检查 + 工作流控制
整合安全模式与计划模式，控制 AI 的执行策略
"""
import json
import threading
from typing import Optional, Tuple


# ── 工作模式 ──
MODE_UNRESTRICTED = 0   # 无限制：直接执行
MODE_NORMAL = 1          # 普通：AI 识别风险
MODE_MANUAL = 2          # 人工：所有指令确认
MODE_PLAN = 3            # 计划：全自动 + 审查 + 重试 + 引擎切换

MODE_NAMES = {
    MODE_UNRESTRICTED: "无限制",
    MODE_NORMAL: "普通",
    MODE_MANUAL: "人工确认",
    MODE_PLAN: "计划模式",
}

MODE_ICONS = {
    MODE_UNRESTRICTED: "",
    MODE_NORMAL: "",
    MODE_MANUAL: "",
    MODE_PLAN: "",
}


class WorkMode:
    """统一工作模式控制"""

    def __init__(self):
        self.mode = MODE_NORMAL
        self.cli = None
        self._analysis_cache = {}
        self._lock = threading.Lock()

        # ── 计划模式状态 ──
        self.plan_engine_errors = 0       # 当前引擎连续错误次数
        self.plan_engine_error_limit = 10 # 触发引擎切换的错误阈值
        self.plan_retry_count = 0         # 当前重试次数
        self.plan_max_retries = 3         # 单步最大重试
        self.plan_review_pending = False  # 是否有待审查的任务
        self.plan_last_task = ""          # 最近一次任务描述

    def set_cli(self, cli):
        self.cli = cli

    def get_mode(self) -> int:
        return self.mode

    def get_mode_name(self) -> str:
        return MODE_NAMES.get(self.mode, "未知")

    def get_mode_icon(self) -> str:
        return MODE_ICONS.get(self.mode, "")

    def set_mode(self, mode: int):
        old = self.mode
        self.mode = mode
        # 切换模式时重置计划模式状态
        if mode != old:
            self.plan_engine_errors = 0
            self.plan_retry_count = 0
            self.plan_review_pending = False

    def cycle_mode(self) -> str:
        """循环切换: 普通 → 人工 → 无限制 → 计划 → 普通"""
        self.mode = (self.mode + 1) % 4
        return self.get_mode_name()

    def is_plan_mode(self) -> bool:
        return self.mode == MODE_PLAN

    # ── 计划模式：引擎错误管理 ──

    def record_engine_error(self) -> bool:
        """
        记录一次引擎错误。
        返回 True 表示应该切换引擎。
        """
        self.plan_engine_errors += 1
        return self.plan_engine_errors >= self.plan_engine_error_limit

    def reset_engine_errors(self):
        """引擎成功响应后重置错误计数"""
        self.plan_engine_errors = 0

    def should_switch_engine(self) -> bool:
        return self.plan_engine_errors >= self.plan_engine_error_limit

    def get_available_engines(self) -> list:
        """获取当前可用的其他引擎列表"""
        if not self.cli:
            return []
        engines = []
        for name, engine in getattr(self.cli, 'engines', {}).items():
            if engine != self.cli.current_engine:
                engines.append((name, engine))
        return engines

    def try_switch_engine(self) -> Optional[str]:
        """
        尝试切换到另一个可用引擎。
        返回新引擎名称，或 None 表示无其他引擎。
        """
        available = self.get_available_engines()
        if not available:
            return None
        name, engine = available[0]
        old_name = getattr(self.cli.current_engine, 'name', '?')
        self.cli.current_engine = engine
        self.plan_engine_errors = 0
        return name

    # ── 计划模式：任务审查 ──

    def request_review(self, task_description: str):
        """标记需要审查的任务"""
        self.plan_review_pending = True
        self.plan_last_task = task_description

    def get_review_prompt(self, task_result: str) -> str:
        """生成审查提示词"""
        return (
            f"你刚才完成了以下任务：\n"
            f"任务：{self.plan_last_task}\n"
            f"结果：{task_result[:500]}\n\n"
            f"请审查执行结果：\n"
            f"1. 任务是否完整完成？\n"
            f"2. 结果是否正确？\n"
            f"3. 是否有遗漏或需要修正的地方？\n\n"
            f"如果发现问题，请说明并重新执行。如果没问题，请确认完成。"
        )

    # ── 核心：安全检查 ──

    def check(self, tool_name: str, tool_args: str) -> Tuple[bool, str]:
        """
        检查工具调用是否安全。
        计划模式下自动放行（全自动）。
        """
        # 计划模式：自动放行，不问用户
        if self.mode == MODE_PLAN:
            return True, ""

        # 无限制模式：直接放行
        if self.mode == MODE_UNRESTRICTED:
            return True, ""

        # 人工确认模式：所有指令确认
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
        """使用当前引擎独立分析指令风险"""
        if self._is_quick_safe(tool_name, tool_args):
            return True, ""

        engine = None
        if self.cli and hasattr(self.cli, 'current_engine'):
            engine = self.cli.current_engine

        if not engine:
            return self._ask_user_confirm(
                tool_name, tool_args,
                risk_level="未知", impact="无法进行 AI 风险分析", reason="无可用引擎"
            )

        cache_key = f"{tool_name}:{tool_args[:100]}"
        with self._lock:
            if cache_key in self._analysis_cache:
                cached = self._analysis_cache[cache_key]
                if cached["safe"]:
                    return True, ""
                return self._ask_user_confirm(
                    tool_name, tool_args,
                    risk_level=cached["level"], impact=cached["impact"], reason=cached["reason"]
                )

        analysis_prompt = f"""你是一个安全分析器。分析以下工具调用是否存在安全风险。

工具: {tool_name}
参数: {tool_args}

只返回以下 JSON（不要其他内容）:
{{"safe": true/false, "level": "低/中/高", "reason": "风险原因", "impact": "执行后可能的影响"}}

判断标准:
- safe=true: 读取操作、查看信息、无害查询
- safe=false: 删除文件、执行系统命令、修改配置、网络请求、git 危险操作"""

        try:
            response = engine.generate_response(
                analysis_prompt,
                system_prompt="你是安全分析器。只返回 JSON，不要其他内容。"
            )
            if not response:
                return self._ask_user_confirm(
                    tool_name, tool_args,
                    risk_level="未知", impact="AI 分析无响应", reason="引擎未返回结果"
                )

            result = self._parse_analysis(response)
            if result and result.get("safe") is True:
                with self._lock:
                    self._analysis_cache[cache_key] = result
                return True, ""

            level = result.get("level", "中") if result else "未知"
            reason = result.get("reason", "AI 识别到潜在风险") if result else "AI 分析失败"
            impact = result.get("impact", "未知影响") if result else "未知影响"
            return self._ask_user_confirm(
                tool_name, tool_args, risk_level=level, impact=impact, reason=reason
            )
        except Exception as e:
            return self._ask_user_confirm(
                tool_name, tool_args,
                risk_level="未知", impact=f"AI 分析异常: {e}", reason="分析过程出错"
            )

    def _parse_analysis(self, response: str) -> Optional[dict]:
        import re
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[-1] if "\n" in response else response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            match = re.search(r'\{[^{}]*"safe"[^{}]*\}', response)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return None

    def _is_quick_safe(self, tool_name: str, tool_args: str) -> bool:
        args = tool_args.strip().lower()
        safe_patterns = {
            "code_editor": ["read_range", "find ", "regex ", "symbols", "imports",
                            "ast_info", "stats", "structure", "context", "todo",
                            "callers", "diff ", "diff_text"],
            "git_tools": ["status", "log", "diff", "branch", "remote", "show",
                          "blame", "contributors", "summary"],
            "file_manager": ["list", "read", "info", "search"],
            "cmd_executor": [],
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
        return any(args.startswith(p) for p in patterns)

    # ── 用户交互 ──

    def _ask_user_confirm(self, tool_name: str, tool_args: str,
                          risk_level: str = "中", impact: str = "",
                          reason: str = "") -> Tuple[bool, str]:
        from colorama import Fore, Style

        level_colors = {
            "低": Fore.YELLOW, "中": Fore.LIGHTYELLOW_EX,
            "高": Fore.RED, "未知": Fore.LIGHTBLACK_EX,
        }
        level_color = level_colors.get(risk_level, Fore.YELLOW)

        display_args = tool_args[:200] + "..." if len(tool_args) > 200 else tool_args

        print()
        print(f"  {Fore.RED}{'═' * 50}{Style.RESET_ALL}")
        print(f"  {Fore.RED}  安全检查{Style.RESET_ALL}")
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
            return (choice in ('y', 'yes', '是'), "用户确认执行" if choice in ('y', 'yes', '是') else "用户取消执行")
        except (KeyboardInterrupt, EOFError):
            print()
            return False, "用户中断"


# ── 兼容旧接口 ──
MODE_UNRESTRICTED = MODE_UNRESTRICTED
MODE_NORMAL = MODE_NORMAL
MODE_MANUAL = MODE_MANUAL

# ── 全局单例 ──
_work_mode = WorkMode()

def get_safety() -> WorkMode:
    """兼容旧接口：返回 WorkMode 实例"""
    return _work_mode
