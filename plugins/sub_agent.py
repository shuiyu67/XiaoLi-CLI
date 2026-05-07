"""
子 Agent 插件 - 多 Agent 协作系统
主 AI 可以创建子 Agent、下达指令、获取结果
"""
import os
import json
import uuid
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional


class SubAgent:
    """单个子 Agent 实例"""

    def __init__(self, agent_id: str, name: str, task: str, system_prompt: str):
        self.id = agent_id
        self.name = name
        self.task = task
        self.status = "idle"          # idle / running / done / failed
        self.system_prompt = system_prompt
        self.conversation = []        # 独立对话历史
        self.result = None
        self.error = None
        self.created_at = datetime.now().strftime("%H:%M:%S")
        self.finished_at = None
        self.steps = 0                # 已执行步数
        self.max_steps = 20

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "task": self.task,
            "status": self.status,
            "steps": self.steps,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "has_result": self.result is not None,
            "has_error": self.error is not None,
        }


class Liugin:
    """子 Agent 系统 - 创建、管理、协作"""

    def __init__(self):
        self.usage = """子 Agent 系统 - 多 Agent 协作

管理:
  spawn <名称> <任务描述>        - 创建子 Agent 并分配任务
  spawn <名称> <任务> --system <提示词> - 创建并指定系统提示词
  list                           - 列出所有子 Agent
  status <ID>                    - 查看子 Agent 状态
  result <ID>                    - 获取子 Agent 执行结果
  send <ID> <消息>               - 向子 Agent 发送消息
  kill <ID>                      - 终止子 Agent
  clean                          - 清理已完成的 Agent
  stats                          - 统计信息

消息格式 (AI 调用):
  {"action": "use_tool", "tool": "sub_agent", "args": "spawn coder 请帮我重构 main.py"}
  {"action": "use_tool", "tool": "sub_agent", "args": "result agent_xxx"}
  {"action": "use_tool", "tool": "sub_agent", "args": "send agent_xxx 用户要求加上类型提示"}

说明:
  - 子 Agent 独立运行，有自己的对话历史
  - 子 Agent 可以使用 code_editor、git_tools 等工具
  - 主 AI 可以同时管理多个子 Agent
  - 子 Agent 完成后通过 result 获取结果
"""
        self.cli = None
        self.agents: Dict[str, SubAgent] = {}
        self._lock = threading.Lock()

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "sub_agent",
            "description": "子 Agent 系统 - 创建子 Agent 执行独立任务，支持并行多任务、结果回收、消息传递",
            "keywords": ["agent", "子agent", "并行", "任务", "协程", "多agent", "spawn", "sub"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "sub_agent",
            "description": "子 Agent 多任务协作系统",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "description": "操作: spawn/list/status/result/send/kill/clean/stats"},
                    "name": {"type": "string", "description": "Agent 名称"},
                    "task": {"type": "string", "description": "任务描述"},
                    "agent_id": {"type": "string", "description": "Agent ID"},
                    "message": {"type": "string", "description": "发送的消息"}
                },
                "required": ["operation"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        name = arguments.get("name", "")
        task = arguments.get("task", "")
        return f"{op} {name} {task}".strip()

    # ── 路由 ──

    def handle(self, args: str) -> str:
        try:
            parts = args.strip().split(maxsplit=1)
            if not parts:
                return "错误：请提供操作类型"

            op = parts[0].lower()
            rest = parts[1] if len(parts) > 1 else ""

            handlers = {
                "spawn": self._spawn,
                "list": self._list,
                "status": self._status,
                "result": self._result,
                "send": self._send,
                "kill": self._kill,
                "clean": self._clean,
                "stats": self._stats,
            }

            handler = handlers.get(op)
            if not handler:
                return f"错误：不支持的操作 '{op}'"
            return handler(rest)

        except Exception as e:
            return f"子 Agent 错误: {str(e)}"

    # ── 操作 ──

    def _spawn(self, args: str) -> str:
        """创建子 Agent"""
        # 解析 --system 参数
        system_prompt = ""
        if " --system " in args:
            args, system_prompt = args.split(" --system ", 1)
            system_prompt = system_prompt.strip()

        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            return "错误：格式: spawn <名称> <任务描述>"

        name = parts[0].strip()
        task = parts[1].strip()

        # 生成 ID
        agent_id = f"agent_{name}_{uuid.uuid4().hex[:6]}"

        # 默认系统提示词
        if not system_prompt:
            system_prompt = (
                f"你是子 Agent「{name}」，负责执行以下任务：\n"
                f"{task}\n\n"
                "你可以使用 code_editor、git_tools、cmd_executor、file_manager 等工具。\n"
                "完成任务后，用以下格式报告结果：\n"
                '{"status": "done", "summary": "简要总结", "details": "详细结果"}\n\n'
                "请开始执行任务。"
            )

        agent = SubAgent(agent_id, name, task, system_prompt)
        with self._lock:
            self.agents[agent_id] = agent

        # 在后台线程执行
        thread = threading.Thread(target=self._run_agent, args=(agent,), daemon=True)
        thread.start()

        return (f" 已创建子 Agent\n"
                f"  ID: {agent_id}\n"
                f"  名称: {name}\n"
                f"  任务: {task}\n"
                f"  状态: running")

    def _run_agent(self, agent: SubAgent):
        """在后台执行子 Agent"""
        agent.status = "running"

        try:
            engine = None
            if self.cli and hasattr(self.cli, 'current_engine'):
                engine = self.cli.current_engine

            if not engine:
                agent.status = "failed"
                agent.error = "无可用的 AI 引擎"
                agent.finished_at = datetime.now().strftime("%H:%M:%S")
                return

            # 第一轮：让子 Agent 开始执行任务
            current_input = agent.task
            max_steps = agent.max_steps

            while agent.steps < max_steps and agent.status == "running":
                agent.steps += 1

                # 调用引擎
                response = engine.generate_response(
                    current_input,
                    system_prompt=agent.system_prompt
                )

                if not response:
                    agent.status = "failed"
                    agent.error = "引擎返回空响应"
                    break

                # 记录对话
                agent.conversation.append({"role": "user", "content": current_input})
                agent.conversation.append({"role": "assistant", "content": response})

                # 检查是否包含完成信号
                if self._is_task_done(response):
                    agent.status = "done"
                    agent.result = response
                    break

                # 检查是否需要工具调用
                tool_result = self._try_execute_tool(response)
                if tool_result:
                    current_input = f"工具执行结果:\n{tool_result}\n\n请继续执行任务。"
                else:
                    # 没有工具调用，视为完成
                    agent.status = "done"
                    agent.result = response
                    break

            if agent.status == "running":
                agent.status = "done"
                agent.result = "已达到最大步数限制，任务暂停。"

        except Exception as e:
            agent.status = "failed"
            agent.error = str(e)

        agent.finished_at = datetime.now().strftime("%H:%M:%S")

    def _is_task_done(self, response: str) -> bool:
        """检查响应中是否包含完成信号"""
        done_markers = ['"status": "done"', '"status":"done"',
                        '任务完成', '已完成', '执行完毕']
        return any(m in response for m in done_markers)

    def _try_execute_tool(self, response: str) -> Optional[str]:
        """尝试从响应中提取并执行工具调用"""
        if not self.cli:
            return None

        # 查找 JSON 工具调用
        import re

        # 模式: {"action": "use_tool", "tool": "...", "args": "..."}
        patterns = [
            r'\{"action"\s*:\s*"use_tool"\s*,\s*"tool"\s*:\s*"([^"]+)"\s*,\s*"args"\s*:\s*"([^"]*(?:\\.[^"]*)*)"\s*\}',
            r'\{"action"\s*:\s*"use_tool"\s*,\s*"tool"\s*:\s*"([^"]+)"\s*,\s*"args"\s*:\s*(\{[^}]+\})\s*\}',
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                tool_name = match.group(1)
                tool_args = match.group(2)

                # 反转义
                tool_args = tool_args.replace('\\"', '"').replace('\\n', '\n')

                # 查找并执行工具
                if hasattr(self.cli, 'liugin_manager'):
                    for tool in self.cli.liugin_manager.tools:
                        if tool.get('name') == tool_name:
                            handler = tool.get('handler')
                            if handler:
                                try:
                                    result = handler(tool_args)
                                    return result
                                except Exception as e:
                                    return f"工具执行错误: {e}"
                            break

        # 模式2: 多个 JSON 指令 (数组)
        array_match = re.search(r'\[\s*\{.*?\}\s*\]', response, re.DOTALL)
        if array_match:
            try:
                commands = json.loads(array_match.group())
                if isinstance(commands, list):
                    results = []
                    for cmd in commands:
                        if isinstance(cmd, dict) and cmd.get('action') == 'use_tool':
                            tool_name = cmd.get('tool', '')
                            tool_args = cmd.get('args', '')
                            if isinstance(tool_args, dict):
                                tool_args = json.dumps(tool_args, ensure_ascii=False)

                            for tool in self.cli.liugin_manager.tools:
                                if tool.get('name') == tool_name:
                                    handler = tool.get('handler')
                                    if handler:
                                        try:
                                            r = handler(tool_args)
                                            results.append(f"[{tool_name}] {r}")
                                        except Exception as e:
                                            results.append(f"[{tool_name}] 错误: {e}")
                                    break
                    if results:
                        return '\n'.join(results)
            except json.JSONDecodeError:
                pass

        return None

    def _list(self, args: str) -> str:
        """列出所有子 Agent"""
        with self._lock:
            if not self.agents:
                return "没有子 Agent"

        result = [f"子 Agent 列表 ({len(self.agents)} 个):\n"]

        # 按状态分组
        running = [a for a in self.agents.values() if a.status == "running"]
        done = [a for a in self.agents.values() if a.status == "done"]
        failed = [a for a in self.agents.values() if a.status == "failed"]

        if running:
            result.append(f" 运行中 ({len(running)}):")
            for a in running:
                result.append(f"  {a.id}  [{a.name}] 步骤:{a.steps}  任务:{a.task[:40]}")

        if done:
            result.append(f" 已完成 ({len(done)}):")
            for a in done:
                result.append(f"  {a.id}  [{a.name}]  任务:{a.task[:40]}")

        if failed:
            result.append(f" 失败 ({len(failed)}):")
            for a in failed:
                result.append(f"  {a.id}  [{a.name}]  错误:{a.error[:40] if a.error else '?'}")

        return '\n'.join(result)

    def _status(self, args: str) -> str:
        """查看子 Agent 状态"""
        agent_id = args.strip()
        if not agent_id:
            return "错误：请提供 Agent ID"

        agent = self.agents.get(agent_id)
        if not agent:
            # 模糊匹配
            matches = [a for a in self.agents.values() if agent_id in a.id or agent_id == a.name]
            if matches:
                agent = matches[0]
            else:
                return f"错误：未找到 Agent '{agent_id}'"

        lines = [
            f"Agent: {agent.id}",
            f"  名称: {agent.name}",
            f"  任务: {agent.task}",
            f"  状态: {agent.status}",
            f"  步骤: {agent.steps}/{agent.max_steps}",
            f"  创建: {agent.created_at}",
        ]
        if agent.finished_at:
            lines.append(f"  完成: {agent.finished_at}")
        if agent.error:
            lines.append(f"  错误: {agent.error}")
        lines.append(f"  对话轮次: {len(agent.conversation)}")

        return '\n'.join(lines)

    def _result(self, args: str) -> str:
        """获取子 Agent 结果"""
        agent_id = args.strip()
        if not agent_id:
            return "错误：请提供 Agent ID"

        agent = self.agents.get(agent_id)
        if not agent:
            matches = [a for a in self.agents.values() if agent_id in a.id or agent_id == a.name]
            if matches:
                agent = matches[0]
            else:
                return f"错误：未找到 Agent '{agent_id}'"

        if agent.status == "running":
            return f"Agent {agent.id} 仍在运行中 (步骤 {agent.steps}/{agent.max_steps})"

        if agent.status == "failed":
            return f"Agent {agent.id} 执行失败: {agent.error}"

        if agent.result:
            result = agent.result
            if len(result) > 3000:
                result = result[:3000] + "\n... (截断)"
            return f"Agent {agent.id} 结果:\n{result}"

        return f"Agent {agent.id} 暂无结果"

    def _send(self, args: str) -> str:
        """向子 Agent 发送消息"""
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            return "错误：格式: send <ID> <消息>"

        agent_id = parts[0]
        message = parts[1]

        agent = self.agents.get(agent_id)
        if not agent:
            matches = [a for a in self.agents.values() if agent_id in a.id or agent_id == a.name]
            if matches:
                agent = matches[0]
            else:
                return f"错误：未找到 Agent '{agent_id}'"

        if agent.status != "running":
            return f"Agent {agent.id} 未在运行 (状态: {agent.status})"

        # 在后台线程处理消息
        thread = threading.Thread(target=self._process_message, args=(agent, message), daemon=True)
        thread.start()

        return f" 消息已发送给 {agent.id}"

    def _process_message(self, agent: SubAgent, message: str):
        """处理发送给子 Agent 的消息"""
        try:
            engine = None
            if self.cli and hasattr(self.cli, 'current_engine'):
                engine = self.cli.current_engine

            if not engine:
                return

            agent.conversation.append({"role": "user", "content": message})
            agent.steps += 1

            response = engine.generate_response(
                message,
                system_prompt=agent.system_prompt
            )

            if response:
                agent.conversation.append({"role": "assistant", "content": response})

                if self._is_task_done(response):
                    agent.status = "done"
                    agent.result = response
                    agent.finished_at = datetime.now().strftime("%H:%M:%S")
                else:
                    tool_result = self._try_execute_tool(response)
                    if tool_result:
                        # 继续执行
                        self._process_message(agent, f"工具结果:\n{tool_result}\n请继续。")

        except Exception as e:
            agent.error = str(e)

    def _kill(self, args: str) -> str:
        """终止子 Agent"""
        agent_id = args.strip()
        agent = self.agents.get(agent_id)
        if not agent:
            matches = [a for a in self.agents.values() if agent_id in a.id or agent_id == a.name]
            if matches:
                agent = matches[0]
            else:
                return f"错误：未找到 Agent '{agent_id}'"

        agent.status = "failed"
        agent.error = "被主 Agent 终止"
        agent.finished_at = datetime.now().strftime("%H:%M:%S")
        return f" 已终止 {agent.id}"

    def _clean(self, args: str) -> str:
        """清理已完成的 Agent"""
        with self._lock:
            to_remove = [aid for aid, a in self.agents.items()
                         if a.status in ("done", "failed")]
            for aid in to_remove:
                del self.agents[aid]

        return f" 已清理 {len(to_remove)} 个已完成的 Agent"

    def _stats(self, args: str) -> str:
        """统计信息"""
        with self._lock:
            total = len(self.agents)
            running = sum(1 for a in self.agents.values() if a.status == "running")
            done = sum(1 for a in self.agents.values() if a.status == "done")
            failed = sum(1 for a in self.agents.values() if a.status == "failed")
            total_steps = sum(a.steps for a in self.agents.values())

        return (f" 子 Agent 统计\n"
                f"  总数: {total}\n"
                f"  运行中: {running}\n"
                f"  已完成: {done}\n"
                f"  失败: {failed}\n"
                f"  总步数: {total_steps}")
