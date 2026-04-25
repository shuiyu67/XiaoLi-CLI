"""
图像识别引擎模块
支持多种图像识别引擎的切换和管理
"""

import os
import sys
import importlib
import json
from colorama import Fore, Style

# 添加项目根目录到sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)


class BaseImageEngine:
    """图像识别引擎基类"""
    
    name = "base"
    description = "基础图像识别引擎"
    requires_api_key = False
    
    def __init__(self):
        self.config = {}
    
    def set_config(self, config):
        """设置引擎配置"""
        self.config = config
    
    def is_available(self):
        """检查引擎是否可用（子类实现）"""
        return False
    
    def analyze(self, image_path, prompt="请描述这张图片"):
        """分析图片（子类实现）"""
        raise NotImplementedError("子类必须实现 analyze 方法")
    
    def stream_analyze(self, image_path, prompt="请描述这张图片"):
        """流式分析图片（子类实现，可选）"""
        # 默认实现：调用 analyze 并一次性返回
        result = self.analyze(image_path, prompt)
        yield result
    
    def get_model_list(self):
        """获取可用模型列表（子类实现，可选）"""
        return []
    
    def set_model(self, model_name):
        """设置当前使用的模型（子类实现，可选）"""
        pass
    
    def get_help(self):
        """获取引擎帮助信息"""
        return f"{self.name}: {self.description}"


class ImageEngineManager:
    """图像识别引擎管理器"""
    
    def __init__(self):
        self.engines = {}
        self.current_engine = None
        self.current_engine_name = None
        self.config = self._load_config()
        
        # 自动加载所有引擎
        self._load_engines()
        
        # 设置默认引擎
        self._set_default_engine()
    
    def _load_config(self):
        """加载配置文件"""
        config_file = os.path.join(project_root, "config.json")
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"image": {"engines": {}, "default_engine": "ollama"}}
    
    def _save_config(self):
        """保存配置文件"""
        config_file = os.path.join(project_root, "config.json")
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                full_config = json.load(f)
        except:
            full_config = {"api": {"engines": {}}, "system": {}, "image": {}}
        
        # 确保image配置存在
        if "image" not in full_config:
            full_config["image"] = {}
        full_config["image"]["default_engine"] = self.current_engine_name
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(full_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"{Fore.RED}保存配置失败: {e}{Style.RESET_ALL}")
    
    def _load_engines(self):
        """加载所有引擎"""
        engine_dir = os.path.dirname(__file__)
        
        for filename in os.listdir(engine_dir):
            if filename.endswith('_engine.py') and filename != '__init__.py':
                engine_name = filename[:-11]  # 移除 _engine.py
                try:
                    # 动态导入模块
                    module_path = os.path.join(engine_dir, filename)
                    spec = importlib.util.spec_from_file_location(f"image_engine.{engine_name}", module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # 获取引擎类
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, BaseImageEngine) and 
                            attr != BaseImageEngine):
                            engine_instance = attr()
                            # 加载引擎配置
                            engine_config = self.config.get("image", {}).get("engines", {}).get(engine_name, {})
                            engine_instance.set_config(engine_config)
                            self.engines[engine_name] = engine_instance
                            print(f"{Fore.GREEN}已加载图像引擎: {engine_name}{Style.RESET_ALL}")
                            break
                except Exception as e:
                    print(f"{Fore.RED}加载图像引擎 {engine_name} 失败: {e}{Style.RESET_ALL}")
    
    def _set_default_engine(self):
        """设置默认引擎"""
        # 从配置读取默认引擎
        default = self.config.get("image", {}).get("default_engine", "ollama")
        
        if default in self.engines:
            engine = self.engines[default]
            if engine.is_available():
                self.current_engine = engine
                self.current_engine_name = default
                print(f"{Fore.GREEN}当前图像引擎: {default}{Style.RESET_ALL}")
                return
        
        # 如果配置的默认引擎不可用，找第一个可用的
        for name, engine in self.engines.items():
            if engine.is_available():
                self.current_engine = engine
                self.current_engine_name = name
                print(f"{Fore.GREEN}当前图像引擎: {name}{Style.RESET_ALL}")
                return
        
        print(f"{Fore.YELLOW}警告: 没有可用的图像引擎{Style.RESET_ALL}")
    
    def get_engine(self, name=None):
        """获取指定引擎或当前引擎"""
        if name:
            return self.engines.get(name)
        return self.current_engine
    
    def switch_engine(self, name):
        """切换引擎"""
        if name not in self.engines:
            available = list(self.engines.keys())
            return False, f"引擎 '{name}' 不存在。可用引擎: {', '.join(available)}"
        
        engine = self.engines[name]
        if not engine.is_available():
            return False, f"引擎 '{name}' 不可用，请检查配置"
        
        self.current_engine = engine
        self.current_engine_name = name
        self._save_config()
        return True, f"已切换到图像引擎: {name}"
    
    def list_engines(self):
        """列出所有引擎"""
        result = f"{Fore.CYAN}图像识别引擎列表:{Style.RESET_ALL}\n"
        for name, engine in self.engines.items():
            status = f"{Fore.GREEN}✓ 可用{Style.RESET_ALL}" if engine.is_available() else f"{Fore.RED}✗ 不可用{Style.RESET_ALL}"
            current = f" {Fore.YELLOW}[当前]{Style.RESET_ALL}" if name == self.current_engine_name else ""
            result += f"  - {name}: {engine.description} {status}{current}\n"
        return result
    
    def analyze(self, image_path, prompt="请描述这张图片", stream=True):
        """使用当前引擎分析图片"""
        if not self.current_engine:
            raise Exception("没有可用的图像引擎")
        
        if stream and hasattr(self.current_engine, 'stream_analyze'):
            return self.current_engine.stream_analyze(image_path, prompt)
        else:
            return self.current_engine.analyze(image_path, prompt)
    
    def get_current_engine_name(self):
        """获取当前引擎名称"""
        return self.current_engine_name


# 全局引擎管理器实例
_engine_manager = None

def get_engine_manager():
    """获取全局引擎管理器实例"""
    global _engine_manager
    if _engine_manager is None:
        _engine_manager = ImageEngineManager()
    return _engine_manager
