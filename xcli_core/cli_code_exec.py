import os
import sys
import time
import json
import subprocess
import traceback
from datetime import datetime
from colorama import Fore, Style

from .config import logger
from .sandbox import (
    _sandbox_checker, _make_sandbox_worker, _sandbox_work_dir,
    _HAS_RESOURCE, _SAFE_WHITELIST, _resource_mod,
)


class CodeExecMixin:
    """代码沙箱执行相关方法"""

    def request_code_execution(self, liugin_name, code, timeout=None, variables=None, context=None):
        """
        插件代码执行请求接口
        """
        if not self.code_execution_enabled:
            return {
                'success': False,
                'result': '代码执行功能已禁用',
                'stdout': '',
                'stderr': '',
                'execution_time': 0,
                'memory_usage': 0
            }

        if not self._is_code_safe(code):
            return {
                'success': False,
                'result': '代码包含潜在危险操作，已阻止执行',
                'stdout': '',
                'stderr': '',
                'execution_time': 0,
                'memory_usage': 0
            }

        exec_timeout = timeout if timeout is not None else self.code_execution_timeout

        execution_id = f"{liugin_name}_{int(time.time())}"
        execution_record = {
            'id': execution_id,
            'liugin_name': liugin_name,
            'code': code,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'context': context
        }

        try:
            result = self._execute_code_safely(code, exec_timeout, variables)

            execution_record.update({
                'success': result['success'],
                'execution_time': result['execution_time'],
                'memory_usage': result['memory_usage']
            })

            self.code_execution_history.append(execution_record)
            if len(self.code_execution_history) > 100:
                self.code_execution_history.pop(0)

            if result['success']:
                logger.info(f"代码执行成功 - 插件: {liugin_name}, 耗时: {result['execution_time']:.3f}s")
            else:
                logger.warning(f"代码执行失败 - 插件: {liugin_name}, 错误: {result['result']}")

            return result

        except Exception as e:
            error_msg = f"代码执行异常: {str(e)}"
            logger.error(f"{error_msg} - 插件: {liugin_name}")
            return {
                'success': False,
                'result': error_msg,
                'stdout': '',
                'stderr': error_msg,
                'execution_time': 0,
                'memory_usage': 0
            }

    def _is_code_safe(self, code):
        """检查代码是否安全（使用 v2 AST+正则 沙箱检查器）"""
        safe, violations = _sandbox_checker.check(code)
        if not safe:
            logger.warning(f"代码安全检查失败: {violations}")
        return safe

    def _execute_code_safely(self, code, timeout, variables=None):
        """
        在安全沙箱中执行代码（v2 子进程隔离）
        """
        safe, violations = _sandbox_checker.check(code)
        if not safe:
            return {
                'success': False,
                'result': '代码包含潜在危险操作，已阻止执行',
                'stdout': '', 'stderr': '; '.join(violations[:5]),
                'execution_time': 0, 'memory_usage': 0
            }

        vars_json = json.dumps(variables or {}, ensure_ascii=False, default=str)
        wl = getattr(self, 'code_execution_whitelist', None) or _SAFE_WHITELIST
        whitelist_json = json.dumps(wl)
        script = _make_sandbox_worker(code, vars_json, whitelist_json, _sandbox_work_dir)

        safe_env = {
            'PATH': '/usr/bin:/bin',
            'LANG': 'en_US.UTF-8', 'LC_ALL': 'en_US.UTF-8',
            'HOME': _sandbox_work_dir,
            'TMPDIR': _sandbox_work_dir, 'TEMP': _sandbox_work_dir, 'TMP': _sandbox_work_dir,
            'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1',
        }
        for key in ('TERM', 'COLUMNS', 'LINES', 'SHELL'):
            val = os.environ.get(key)
            if val:
                safe_env[key] = val

        start_time = time.time()
        try:
            proc = subprocess.run(
                [sys.executable, '-c', script],
                capture_output=True, timeout=timeout,
                cwd=_sandbox_work_dir, env=safe_env,
                preexec_fn=CodeExecMixin._sandbox_set_limits if _HAS_RESOURCE else None,
            )
            elapsed = time.time() - start_time
            stdout = proc.stdout.decode('utf-8', errors='replace')[:1000000]
            stderr = proc.stderr.decode('utf-8', errors='replace')[:1000000]

            try:
                data = json.loads(stdout)
                return {
                    'success': data.get('success', False),
                    'result': data.get('result', ''),
                    'stdout': data.get('stdout', ''),
                    'stderr': data.get('stderr', ''),
                    'execution_time': elapsed,
                    'memory_usage': 0
                }
            except json.JSONDecodeError:
                return {
                    'success': proc.returncode == 0,
                    'result': stdout[:2000] if stdout else 'no output',
                    'stdout': stdout, 'stderr': stderr,
                    'execution_time': elapsed, 'memory_usage': 0
                }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'result': f'代码执行超时（超过{timeout}秒）',
                'stdout': '', 'stderr': '',
                'execution_time': timeout, 'memory_usage': 0
            }
        except Exception as e:
            return {
                'success': False,
                'result': f'代码执行异常: {str(e)}',
                'stdout': '', 'stderr': traceback.format_exc(),
                'execution_time': time.time() - start_time, 'memory_usage': 0
            }

    @staticmethod
    def _sandbox_set_limits():
        """子进程资源限制"""
        if not _HAS_RESOURCE or not _resource_mod:
            return
        try:
            mem = 256 * 1024 * 1024  # 256MB
            _resource_mod.setrlimit(_resource_mod.RLIMIT_AS, (mem, mem))
            _resource_mod.setrlimit(_resource_mod.RLIMIT_CPU, (30, 35))
            _resource_mod.setrlimit(_resource_mod.RLIMIT_NPROC, (0, 0))
            _resource_mod.setrlimit(_resource_mod.RLIMIT_FSIZE, (50*1024*1024, 50*1024*1024))
        except (ValueError, OSError):
            pass

    def get_code_execution_history(self, limit=10):
        """获取代码执行历史"""
        return self.code_execution_history[-limit:]

    def clear_code_execution_history(self):
        """清空代码执行历史"""
        self.code_execution_history = []
        logger.info("代码执行历史已清空")

    def set_code_execution_timeout(self, timeout):
        """设置代码执行超时时间"""
        if timeout > 0:
            self.code_execution_timeout = timeout
            logger.info(f"代码执行超时时间已设置为 {timeout} 秒")

    def set_code_execution_whitelist(self, modules):
        """设置允许导入的模块白名单"""
        self.code_execution_whitelist = modules
        logger.info(f"代码执行模块白名单已更新: {modules}")
