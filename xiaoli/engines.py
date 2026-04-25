"""AI 引擎管理 - 动态加载和切换"""
import os
import importlib.util
import logging
from colorama import Fore, Style

logger = logging.getLogger(__name__)


class EngineManager:
    """AI 引擎管理器"""

    def __init__(self):
        self.engines = {}
        self.current = None

    def load_all(self, engines_dir: str) -> dict:
        """加载目录中所有引擎"""
        print(f"{Fore.GREEN}正在加载AI引擎...{Style.RESET_ALL}")

        if not os.path.exists(engines_dir):
            print(f"{Fore.YELLOW}引擎目录不存在{Style.RESET_ALL}")
            return self.engines

        for fn in sorted(os.listdir(engines_dir)):
            if not fn.endswith('.py') or fn == '__init__.py':
                continue

            name = fn[:-3]
            path = os.path.join(engines_dir, fn)

            try:
                spec = importlib.util.spec_from_file_location(name, path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                cls = self._find_class(module, name)
                if not cls:
                    continue

                instance = getattr(module, cls)()
                key = getattr(instance, 'name', name)

                if key not in self.engines:
                    self.engines[key] = instance
                    print(f"{Fore.GREEN}  ✓ {key} ({cls}){Style.RESET_ALL}")

            except Exception as e:
                logger.error(f"加载引擎失败 {fn}: {e}")
                print(f"{Fore.RED}  ✗ {fn}: {e}{Style.RESET_ALL}")

        print(f"{Fore.GREEN}共 {len(self.engines)} 个引擎{Style.RESET_ALL}")
        return self.engines

    def _find_class(self, module, engine_name):
        """查找引擎类"""
        patterns = [
            engine_name.capitalize() + "AI",
            engine_name.replace('_', '').replace('-', '').capitalize() + "AI",
            ''.join(w.capitalize() for w in engine_name.replace('-', ' ').replace('_', ' ').split()) + "AI",
        ]
        for name in patterns:
            if hasattr(module, name):
                return name
        for attr in dir(module):
            obj = getattr(module, attr)
            if (isinstance(obj, type) and attr.endswith('AI') and
                    hasattr(obj, 'generate_response')):
                return attr
        return None

    def set_default(self, name: str) -> bool:
        if name in self.engines:
            self.current = self.engines[name]
            return True
        return False

    def switch(self, name: str) -> bool:
        if name not in self.engines:
            return False
        self.current = self.engines[name]
        return True

    def current_name(self) -> str:
        return getattr(self.current, 'name', '未设置') if self.current else '未设置'

    def names(self) -> list:
        return list(self.engines.keys())

    def generate(self, user_input: str, system_prompt: str = None) -> str:
        if not self.current:
            return "错误: 没有可用的AI引擎"
        return self.current.generate_response(user_input, system_prompt=system_prompt)
