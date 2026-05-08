"""
工作流插件 - YAML 定义的多步骤自动化流程

支持:
  - 顺序执行多步骤
  - 步骤间变量传递 ({{prev.output}})
  - 条件分支 (on_fail / on_success)
  - 错误处理 (continue_on_error)
  - 状态持久化 (断点续跑)
  - 调用其他插件作为步骤

用法:
  /workflow run <file.yaml>
  /workflow list
  /workflow status <workflow_id>
  /workflow resume <workflow_id>
  /workflow abort <workflow_id>
"""

import json
import os
import re
import time
import uuid
from datetime import datetime
from colorama import Fore, Style


# ── YAML 解析（内置轻量实现，不依赖 PyYAML） ──

def _parse_yaml(text: str) -> dict:
    """轻量 YAML 解析器，支持工作流所需的子集"""
    import yaml  # 延迟导入，失败时回退
    return yaml.safe_load(text)


def _parse_yaml_fallback(text: str) -> dict:
    """内置回退解析器，仅支持简单结构"""
    result = {}
    current_key = None
    current_list = None
    current_dict = None

    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        indent = len(line) - len(line.lstrip())

        if indent == 0 and ':' in stripped:
            key, _, val = stripped.partition(':')
            key = key.strip()
            val = val.strip()
            if val:
                result[key] = _yaml_value(val)
            else:
                result[key] = None
                current_key = key
                current_list = None
                current_dict = None
        elif indent > 0 and stripped.startswith('- '):
            if current_key:
                if not isinstance(result.get(current_key), list):
                    result[current_key] = []
                item_text = stripped[2:].strip()
                if ':' in item_text:
                    item = {}
                    k, _, v = item_text.partition(':')
                    item[k.strip()] = _yaml_value(v.strip())
                    current_dict = item
                    result[current_key].append(item)
                else:
                    result[current_key].append(_yaml_value(item_text))
        elif indent > 0 and ':' in stripped and current_dict is not None:
            key, _, val = stripped.partition(':')
            current_dict[key.strip()] = _yaml_value(val.strip())

    return result


def _yaml_value(s: str):
    """转换单个 YAML 值"""
    if not s:
        return None
    # 去除引号
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    if s.lower() in ('true', 'yes', 'on'):
        return True
    if s.lower() in ('false', 'no', 'off'):
        return False
    if s.lower() in ('null', 'none', '~'):
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _load_yaml_file(path: str) -> dict:
    """加载 YAML 文件"""
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    try:
        return _parse_yaml(text)
    except ImportError:
        return _parse_yaml_fallback(text)


# ── 变量替换引擎 ──

def _resolve_vars(text: str, context: dict) -> str:
    """
    替换 {{key}} 和 {{key.nested}} 形式的变量

    支持:
      {{var}}           → context['var']
      {{step.output}}   → context['steps']['step']['output']
      {{step.exit_code}} → context['steps']['step']['exit_code']
      {{env.HOME}}      → os.environ['HOME']
      {{args.name}}     → context['args']['name']
    """
    def replacer(match):
        path = match.group(1).strip()
        parts = path.split('.')

        if parts[0] == 'env':
            return os.environ.get('.'.join(parts[1:]), '')

        if parts[0] == 'args' and len(parts) > 1:
            val = context.get('args', {})
            for p in parts[1:]:
                if isinstance(val, dict):
                    val = val.get(p, '')
                else:
                    return ''
            return str(val)

        if parts[0] == 'steps' and len(parts) >= 3:
            step_name = parts[1]
            attr = parts[2]
            step_data = context.get('steps', {}).get(step_name, {})
            val = step_data.get(attr, '')
            # 支持 deeper nesting: {{steps.foo.output.field}}
            for p in parts[3:]:
                if isinstance(val, dict):
                    val = val.get(p, '')
                else:
                    return ''
            return str(val)

        # 顶层变量
        val = context
        for p in parts:
            if isinstance(val, dict):
                val = val.get(p, '')
            else:
                return ''
        return str(val)

    return re.sub(r'\{\{(.+?)\}\}', replacer, text)


def _resolve_value(val, context):
    """递归解析值中的变量（支持 dict/list/str）"""
    if isinstance(val, str):
        return _resolve_vars(val, context)
    elif isinstance(val, dict):
        return {k: _resolve_value(v, context) for k, v in val.items()}
    elif isinstance(val, list):
        return [_resolve_value(item, context) for item in val]
    return val


# ── 工作流引擎 ──

class WorkflowEngine:
    """工作流执行引擎"""

    def __init__(self, cli_instance=None):
        self.cli = cli_instance
        self.workflows_dir = "workflows"
        self.state_dir = os.path.join(self.workflows_dir, ".state")
        os.makedirs(self.state_dir, exist_ok=True)

    def run(self, path: str, args: dict = None) -> str:
        """执行工作流"""
        if not os.path.exists(path):
            return f"❌ 工作流文件不存在: {path}"

        try:
            wf = _load_yaml_file(path)
        except Exception as e:
            return f"❌ 解析工作流文件失败: {e}"

        wf_name = wf.get('name', os.path.basename(path).replace('.yaml', '').replace('.yml', ''))
        steps = wf.get('steps', [])
        if not steps:
            return f"❌ 工作流 '{wf_name}' 没有步骤"

        wf_id = f"{wf_name}-{uuid.uuid4().hex[:8]}"
        context = {
            'args': args or {},
            'steps': {},
            'workflow': {
                'id': wf_id,
                'name': wf_name,
                'path': path,
                'started_at': datetime.now().isoformat(),
            }
        }

        # 保存初始状态
        self._save_state(wf_id, {
            'workflow': wf_name,
            'path': path,
            'status': 'running',
            'current_step': 0,
            'context': context,
            'started_at': context['workflow']['started_at'],
        })

        print(f"\n{Fore.CYAN}🔄 工作流 '{wf_name}' 开始 (ID: {wf_id}){Style.RESET_ALL}")
        print(f"   共 {len(steps)} 个步骤\n")

        failed = False
        for i, step in enumerate(steps):
            step_name = step.get('name', f'step_{i+1}')
            step_type = step.get('type', 'tool')
            condition = step.get('if', None)
            continue_on_error = step.get('continue_on_error', False)

            # 检查条件
            if condition:
                resolved_condition = _resolve_vars(condition, context)
                if not self._eval_condition(resolved_condition):
                    print(f"  {Fore.YELLOW}⏭ [{step_name}] 条件不满足，跳过{Style.RESET_ALL}")
                    context['steps'][step_name] = {
                        'output': '', 'exit_code': 0, 'skipped': True
                    }
                    continue

            # 解析步骤参数
            resolved_step = _resolve_value(step, context)

            print(f"  {Fore.CYAN}▶ [{step_name}] {step_type}{Style.RESET_ALL}")

            # 更新状态
            self._save_state(wf_id, {
                'workflow': wf_name,
                'path': path,
                'status': 'running',
                'current_step': i,
                'current_step_name': step_name,
                'context': context,
                'started_at': context['workflow']['started_at'],
            })

            try:
                result = self._execute_step(resolved_step, context)
                context['steps'][step_name] = result

                if result.get('exit_code', 0) == 0:
                    output_preview = str(result.get('output', ''))[:100]
                    print(f"  {Fore.GREEN}✓ [{step_name}] 完成{Style.RESET_ALL}"
                          f"{' → ' + output_preview if output_preview else ''}")
                else:
                    failed = True
                    print(f"  {Fore.RED}✗ [{step_name}] 失败 (exit={result.get('exit_code')}){Style.RESET_ALL}")
                    print(f"    {result.get('error', result.get('output', ''))[:200]}")

                    if not continue_on_error:
                        # 检查 on_fail 分支
                        on_fail = resolved_step.get('on_fail')
                        if on_fail:
                            print(f"  {Fore.YELLOW}→ 执行 on_fail 分支{Style.RESET_ALL}")
                            self._execute_on_fail(on_fail, context)
                        break
                    else:
                        print(f"  {Fore.YELLOW}⚠ continue_on_error=true，继续{Style.RESET_ALL}")

            except Exception as e:
                failed = True
                context['steps'][step_name] = {
                    'output': '', 'exit_code': 1, 'error': str(e)
                }
                print(f"  {Fore.RED}✗ [{step_name}] 异常: {e}{Style.RESET_ALL}")
                if not continue_on_error:
                    break

        # 完成状态
        status = 'failed' if failed else 'completed'
        context['workflow']['finished_at'] = datetime.now().isoformat()
        context['workflow']['status'] = status

        self._save_state(wf_id, {
            'workflow': wf_name,
            'path': path,
            'status': status,
            'current_step': len(steps),
            'context': context,
            'started_at': context['workflow']['started_at'],
            'finished_at': context['workflow']['finished_at'],
        })

        icon = '✅' if not failed else '❌'
        print(f"\n{icon} 工作流 '{wf_name}' {status} (ID: {wf_id})")
        return f"{icon} 工作流 '{wf_name}' {status}"

    def resume(self, wf_id: str) -> str:
        """从断点恢复执行工作流"""
        state = self._load_state(wf_id)
        if not state:
            return f"❌ 未找到工作流状态: {wf_id}"

        if state.get('status') == 'completed':
            return f"ℹ️ 工作流已完成: {wf_id}"

        path = state.get('path', '')
        if not os.path.exists(path):
            return f"❌ 工作流文件不存在: {path}"

        try:
            wf = _load_yaml_file(path)
        except Exception as e:
            return f"❌ 解析工作流文件失败: {e}"

        steps = wf.get('steps', [])
        start_from = state.get('current_step', 0)
        context = state.get('context', {})

        print(f"\n{Fore.CYAN}🔄 恢复工作流 '{wf.get('name', wf_id)}' 从步骤 {start_from + 1}{Style.RESET_ALL}")

        failed = False
        for i in range(start_from, len(steps)):
            step = steps[i]
            step_name = step.get('name', f'step_{i+1}')
            step_type = step.get('type', 'tool')
            continue_on_error = step.get('continue_on_error', False)

            resolved_step = _resolve_value(step, context)
            print(f"  {Fore.CYAN}▶ [{step_name}] {step_type}{Style.RESET_ALL}")

            try:
                result = self._execute_step(resolved_step, context)
                context['steps'][step_name] = result

                if result.get('exit_code', 0) == 0:
                    print(f"  {Fore.GREEN}✓ [{step_name}] 完成{Style.RESET_ALL}")
                else:
                    failed = True
                    print(f"  {Fore.RED}✗ [{step_name}] 失败{Style.RESET_ALL}")
                    if not continue_on_error:
                        break
            except Exception as e:
                failed = True
                context['steps'][step_name] = {'output': '', 'exit_code': 1, 'error': str(e)}
                print(f"  {Fore.RED}✗ [{step_name}] 异常: {e}{Style.RESET_ALL}")
                if not continue_on_error:
                    break

        status = 'failed' if failed else 'completed'
        self._save_state(wf_id, {**state, 'status': status, 'current_step': len(steps)})

        return f"{'✅' if not failed else '❌'} 工作流 {status}"

    def list_workflows(self) -> str:
        """列出所有工作流文件"""
        if not os.path.exists(self.workflows_dir):
            return "📁 workflows/ 目录不存在"

        files = [f for f in os.listdir(self.workflows_dir)
                 if f.endswith(('.yaml', '.yml')) and not f.startswith('.')]

        if not files:
            return "📁 workflows/ 目录中没有工作流文件"

        result = f"📁 工作流列表 ({len(files)} 个):\n"
        for f in sorted(files):
            path = os.path.join(self.workflows_dir, f)
            try:
                wf = _load_yaml_file(path)
                name = wf.get('name', f.replace('.yaml', '').replace('.yml', ''))
                desc = wf.get('description', '')
                steps_count = len(wf.get('steps', []))
                result += f"  📄 {f}\n"
                result += f"     名称: {name}  步骤: {steps_count}\n"
                if desc:
                    result += f"     描述: {desc}\n"
            except Exception:
                result += f"  📄 {f} (解析失败)\n"
        return result

    def status(self, wf_id: str) -> str:
        """查看工作流状态"""
        state = self._load_state(wf_id)
        if not state:
            return f"❌ 未找到工作流: {wf_id}"

        ctx = state.get('context', {})
        wf_info = ctx.get('workflow', {})
        steps_done = ctx.get('steps', {})

        lines = [
            f"📋 工作流: {state.get('workflow', '?')}",
            f"   ID: {wf_id}",
            f"   状态: {state.get('status', '?')}",
            f"   进度: 步骤 {state.get('current_step', 0)}",
            f"   开始: {state.get('started_at', '?')}",
        ]
        if state.get('finished_at'):
            lines.append(f"   结束: {state['finished_at']}")

        if steps_done:
            lines.append(f"   已完成步骤:")
            for name, data in steps_done.items():
                icon = '✓' if data.get('exit_code', 0) == 0 else ('⏭' if data.get('skipped') else '✗')
                lines.append(f"     {icon} {name}")

        return '\n'.join(lines)

    def list_states(self) -> str:
        """列出所有工作流运行状态"""
        if not os.path.exists(self.state_dir):
            return "没有工作流运行记录"

        files = [f for f in os.listdir(self.state_dir) if f.endswith('.json')]
        if not files:
            return "没有工作流运行记录"

        result = f"📋 工作流运行记录 ({len(files)} 个):\n"
        for f in sorted(files, reverse=True)[:20]:
            wf_id = f.replace('.json', '')
            try:
                with open(os.path.join(self.state_dir, f), 'r') as fh:
                    state = json.load(fh)
                status_icon = {'running': '🔄', 'completed': '✅', 'failed': '❌'}.get(state.get('status'), '❓')
                result += f"  {status_icon} {wf_id} — {state.get('workflow', '?')} ({state.get('status', '?')})\n"
            except Exception:
                result += f"  ❓ {wf_id}\n"
        return result

    def abort(self, wf_id: str) -> str:
        """中止工作流"""
        state = self._load_state(wf_id)
        if not state:
            return f"❌ 未找到工作流: {wf_id}"

        state['status'] = 'aborted'
        self._save_state(wf_id, state)
        return f"🛑 工作流已中止: {wf_id}"

    # ── 步骤执行 ──

    def _execute_step(self, step: dict, context: dict) -> dict:
        """执行单个步骤"""
        step_type = step.get('type', 'tool')

        if step_type == 'tool':
            return self._exec_tool_step(step, context)
        elif step_type == 'shell':
            return self._exec_shell_step(step, context)
        elif step_type == 'set':
            return self._exec_set_step(step, context)
        elif step_type == 'echo':
            return self._exec_echo_step(step, context)
        elif step_type == 'wait':
            return self._exec_wait_step(step, context)
        elif step_type == 'if':
            return self._exec_if_step(step, context)
        else:
            return {'output': '', 'exit_code': 1, 'error': f'未知步骤类型: {step_type}'}

    def _exec_tool_step(self, step: dict, context: dict) -> dict:
        """执行插件工具步骤"""
        tool_name = step.get('tool', '')
        tool_args = step.get('args', '')

        if not tool_name:
            return {'output': '', 'exit_code': 1, 'error': '未指定 tool 名称'}

        if not self.cli:
            return {'output': '', 'exit_code': 1, 'error': 'CLI 实例不可用'}

        try:
            # 获取工具管理器
            tool_mgr = getattr(self.cli, 'tool_manager', None) or getattr(self.cli, 'liugin_manager', None)
            if not tool_mgr:
                return {'output': '', 'exit_code': 1, 'error': '工具管理器不可用'}

            # 解析参数
            args_str = str(tool_args) if tool_args else ''

            # 调用工具
            if hasattr(tool_mgr, 'execute'):
                result = tool_mgr.execute(tool_name, args_str)
                output = result.get('result', '') if isinstance(result, dict) else str(result)
            elif hasattr(tool_mgr, 'tools'):
                # LiuginManager 兼容
                tool = tool_mgr.get_tool_by_name(tool_name)
                if tool and 'handler' in tool:
                    output = tool['handler'](args_str)
                else:
                    return {'output': '', 'exit_code': 1, 'error': f'未找到工具: {tool_name}'}
            else:
                return {'output': '', 'exit_code': 1, 'error': '无法调用工具'}

            return {'output': str(output), 'exit_code': 0}

        except Exception as e:
            return {'output': '', 'exit_code': 1, 'error': str(e)}

    def _exec_shell_step(self, step: dict, context: dict) -> dict:
        """执行 shell 命令步骤"""
        import subprocess

        cmd = step.get('command', step.get('cmd', ''))
        if not cmd:
            return {'output': '', 'exit_code': 1, 'error': '未指定 command'}

        cwd = step.get('cwd', None)
        timeout = step.get('timeout', 60)

        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=cwd
            )
            return {
                'output': result.stdout.strip(),
                'error': result.stderr.strip(),
                'exit_code': result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {'output': '', 'exit_code': 1, 'error': f'命令超时 ({timeout}s)'}
        except Exception as e:
            return {'output': '', 'exit_code': 1, 'error': str(e)}

    def _exec_set_step(self, step: dict, context: dict) -> dict:
        """设置变量步骤"""
        variables = step.get('variables', step.get('vars', {}))
        for key, val in variables.items():
            context[key] = _resolve_value(val, context)
        return {'output': f'设置 {len(variables)} 个变量', 'exit_code': 0}

    def _exec_echo_step(self, step: dict, context: dict) -> dict:
        """打印步骤"""
        message = step.get('message', step.get('text', ''))
        resolved = _resolve_vars(str(message), context)
        print(f"    💬 {resolved}")
        return {'output': resolved, 'exit_code': 0}

    def _exec_wait_step(self, step: dict, context: dict) -> dict:
        """等待步骤"""
        seconds = step.get('seconds', step.get('time', 1))
        time.sleep(seconds)
        return {'output': f'等待 {seconds} 秒', 'exit_code': 0}

    def _exec_if_step(self, step: dict, context: dict) -> dict:
        """条件分支步骤"""
        condition = step.get('condition', '')
        resolved = _resolve_vars(str(condition), context)

        if self._eval_condition(resolved):
            then_steps = step.get('then', [])
            return self._run_sub_steps(then_steps, context)
        else:
            else_steps = step.get('else', [])
            if else_steps:
                return self._run_sub_steps(else_steps, context)
            return {'output': '条件不满足，无 else 分支', 'exit_code': 0}

    def _run_sub_steps(self, steps: list, context: dict) -> dict:
        """执行子步骤列表"""
        outputs = []
        for sub_step in steps:
            result = self._execute_step(sub_step, context)
            outputs.append(result.get('output', ''))
            if result.get('exit_code', 0) != 0:
                return result
        return {'output': '\n'.join(outputs), 'exit_code': 0}

    def _eval_condition(self, condition: str) -> bool:
        """评估条件表达式"""
        condition = condition.strip()
        if not condition:
            return True

        # 简单比较: "value == expected"
        for op in ['==', '!=', '>=', '<=', '>', '<']:
            if op in condition:
                left, _, right = condition.partition(op)
                left = left.strip().strip('"').strip("'")
                right = right.strip().strip('"').strip("'")
                try:
                    left_n, right_n = float(left), float(right)
                    if op == '==': return left_n == right_n
                    if op == '!=': return left_n != right_n
                    if op == '>=': return left_n >= right_n
                    if op == '<=': return left_n <= right_n
                    if op == '>': return left_n > right_n
                    if op == '<': return left_n < right_n
                except ValueError:
                    if op == '==': return left == right
                    if op == '!=': return left != right

        # 布尔值
        if condition.lower() in ('true', '1', 'yes'):
            return True
        if condition.lower() in ('false', '0', 'no', ''):
            return False

        # 非空即真
        return bool(condition)

    def _execute_on_fail(self, on_fail, context: dict):
        """执行 on_fail 处理"""
        if isinstance(on_fail, str):
            print(f"    💬 {on_fail}")
        elif isinstance(on_fail, list):
            for step in on_fail:
                self._execute_step(step, context)

    # ── 状态持久化 ──

    def _save_state(self, wf_id: str, state: dict):
        """保存工作流状态"""
        path = os.path.join(self.state_dir, f"{wf_id}.json")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"{Fore.YELLOW}⚠ 保存状态失败: {e}{Style.RESET_ALL}")

    def _load_state(self, wf_id: str) -> dict:
        """加载工作流状态"""
        path = os.path.join(self.state_dir, f"{wf_id}.json")
        if not os.path.exists(path):
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}


# ── Liugin 插件接口 ──

class Liugin:
    """工作流插件"""

    def __init__(self):
        self.engine = None
        self.usage = """工作流工具使用方法：

JSON格式示例：
{"action": "use_tool", "tool": "workflow", "args": "run deploy.yaml"} - 执行工作流
{"action": "use_tool", "tool": "workflow", "args": "list"} - 列出工作流文件
{"action": "use_tool", "tool": "workflow", "args": "states"} - 查看运行记录
{"action": "use_tool", "tool": "workflow", "args": "status <id>"} - 查看状态
{"action": "use_tool", "tool": "workflow", "args": "resume <id>"} - 恢复执行
{"action": "use_tool", "tool": "workflow", "args": "abort <id>"} - 中止工作流

工作流 YAML 格式示例：
name: deploy
description: 部署流程
steps:
  - name: lint
    type: shell
    command: "npm run lint"
  - name: test
    type: shell
    command: "npm test"
    continue_on_error: true
  - name: build
    type: shell
    command: "npm run build"
    if: "{{test.exit_code}} == 0"
  - name: notify
    type: echo
    message: "构建完成: {{build.output}}"

支持的步骤类型:
  - tool: 调用插件工具 (tool, args)
  - shell: 执行系统命令 (command, cwd, timeout)
  - echo: 打印消息 (message)
  - wait: 等待 (seconds)
  - set: 设置变量 (variables)
  - if: 条件分支 (condition, then, else)

变量引用:
  {{steps.step_name.output}}  - 步骤输出
  {{steps.step_name.exit_code}} - 步骤退出码
  {{env.VAR_NAME}} - 环境变量
  {{args.param}} - 工作流参数"""

    def set_cli(self, cli):
        self.cli = cli
        self.engine = WorkflowEngine(cli)
        cli.register_liugin_command('workflow', self.command_handler)
        cli.register_liugin_command('wf', self.command_handler)

    def command_handler(self, args):
        return self.handle(args)

    def get_tool_info(self):
        return {
            "name": "workflow",
            "description": "工作流引擎 - YAML 定义的多步骤自动化流程，支持变量传递、条件分支、断点续跑",
            "keywords": ["workflow", "工作流", "流程", "自动化", "pipeline", "deploy", "build", "run"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "workflow",
            "description": "工作流引擎 - 执行、管理 YAML 定义的自动化工作流",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["run", "list", "states", "status", "resume", "abort"],
                        "description": "操作类型"
                    },
                    "target": {
                        "type": "string",
                        "description": "工作流文件路径(run) 或工作流ID(status/resume/abort)"
                    },
                    "args": {
                        "type": "object",
                        "description": "工作流参数 (run 时使用)"
                    }
                },
                "required": ["operation"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        target = arguments.get("target", "")
        args = arguments.get("args", "")
        if args and isinstance(args, dict):
            args_str = ' '.join(f'{k}={v}' for k, v in args.items())
            return f"{op} {target} {args_str}".strip()
        return f"{op} {target}".strip()

    def handle(self, args):
        try:
            args = args.strip()
            if not args:
                return self.usage

            parts = args.split(None, 2)
            action = parts[0].lower()

            if action == 'run':
                if len(parts) < 2:
                    return "❌ 请指定工作流文件: workflow run <file.yaml>"
                path = parts[1]
                # 解析内联参数
                wf_args = {}
                if len(parts) > 2:
                    for part in parts[2].split():
                        if '=' in part:
                            k, v = part.split('=', 1)
                            wf_args[k] = v
                return self.engine.run(path, wf_args)

            elif action == 'list':
                return self.engine.list_workflows()

            elif action == 'states':
                return self.engine.list_states()

            elif action == 'status':
                if len(parts) < 2:
                    return "❌ 请指定工作流 ID: workflow status <id>"
                return self.engine.status(parts[1])

            elif action == 'resume':
                if len(parts) < 2:
                    return "❌ 请指定工作流 ID: workflow resume <id>"
                return self.engine.resume(parts[1])

            elif action == 'abort':
                if len(parts) < 2:
                    return "❌ 请指定工作流 ID: workflow abort <id>"
                return self.engine.abort(parts[1])

            else:
                # 默认当作 run
                if os.path.exists(action):
                    return self.engine.run(action)
                return f"❌ 未知操作: {action}\n\n{self.usage}"

        except Exception as e:
            return f"❌ 工作流操作错误: {e}"
