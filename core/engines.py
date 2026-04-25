"""
AI 引擎管理模块 - 动态加载和切换 AI 引擎
"""
import os
import importlib.util
import logging
from colorama import Fore, Style

logger = logging.getLogger(__name__)


class EngineManager:
    """AI 引擎管理器"""

    def __init__(self):
        self.engines = {}
        self.current_engine = None

    def load_engines(self, engines_dir: str) -> dict:
        """动态加载所有 AI 引擎"""
        print(f"{Fore.GREEN}正在加载AI引擎插件...{Style.RESET_ALL}")

        if not os.path.exists(engines_dir):
            print(f"{Fore.YELLOW}引擎目录不存在: {engines_dir}{Style.RESET_ALL}")
            return self.engines

        for filename in os.listdir(engines_dir):
            if not filename.endswith('.py') or filename == '__init__.py':
                continue

            engine_name = filename[:-3]
            engine_path = os.path.join(engines_dir, filename)

            try:
                spec = importlib.util.spec_from_file_location(engine_name, engine_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                class_name = self._find_engine_class(module, engine_name)
                if class_name and hasattr(module, class_name):
                    engine_instance = getattr(module, class_name)()
                    engine_key = getattr(engine_instance, 'name', engine_name)

                    if engine_key not in self.engines:
                        self.engines[engine_key] = engine_instance
                        print(f"{Fore.GREEN}已加载AI引擎: {engine_key} ({class_name}){Style.RESET_ALL}")
                    else:
                        print(f"{Fore.YELLOW}AI引擎 {engine_key} 已存在，跳过{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}引擎插件 {filename} 中未找到合适的引擎类{Style.RESET_ALL}")

            except Exception as e:
                logger.error(f"加载引擎失败 {filename}: {e}")
                print(f"{Fore.RED}加载引擎失败 {filename}: {e}{Style.RESET_ALL}")

        print(f"{Fore.GREEN}总共加载了 {len(self.engines)} 个AI引擎{Style.RESET_ALL}")
        return self.engines

    def _find_engine_class(self, module, engine_name):
        """查找引擎类"""
        possible_names = [
            engine_name.capitalize() + "AI",
            engine_name.replace('_', '').replace('-', '').capitalize() + "AI",
            ''.join(w.capitalize() for w in engine_name.replace('-', ' ').replace('_', ' ').split()) + "AI",
            ''.join(w.capitalize() for w in engine_name.replace('_engine', '').replace('-', ' ').replace('_', ' ').split()) + "AI",
        ]

        for name in possible_names:
            if hasattr(module, name):
                return name

        # 通用查找
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and
                attr_name.endswith('AI') and
                hasattr(attr, 'generate_response')):
                return attr_name
        return None

    def set_default(self, name: str) -> bool:
        """设置默认引擎"""
        if name in self.engines:
            self.current_engine = self.engines[name]
            return True
        return False

    def switch(self, name: str) -> bool:
        """切换引擎"""
        if name not in self.engines:
            return False

        old_engine = self.current_engine
        self.current_engine = self.engines[name]

        if hasattr(self.current_engine, 'cli'):
            self.current_engine.cli = getattr(old_engine, 'cli', None)

        return True

    def get_current_name(self) -> str:
        """获取当前引擎名称"""
        if self.current_engine:
            return getattr(self.current_engine, 'name', '未设置')
        return '未设置'

    def list_engines(self) -> list:
        """列出所有引擎"""
        return list(self.engines.keys())

    def generate_response(self, user_input: str, system_prompt: str = None) -> str:
        """使用当前引擎生成响应"""
        if not self.current_engine:
            return "错误: 没有可用的AI引擎"
        return self.current_engine.generate_response(user_input, system_prompt=system_prompt)
