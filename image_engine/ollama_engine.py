"""
Ollama 视觉引擎
使用本地 Ollama 服务进行图像识别
"""

import os
from colorama import Fore, Style
from . import BaseImageEngine

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False


class OllamaImageEngine(BaseImageEngine):
    """Ollama 视觉引擎"""
    
    name = "ollama"
    description = "Ollama本地视觉模型（支持多种视觉模型）"
    requires_api_key = False
    
    # 预设提示词
    PROMPTS = {
        "analyze": """请详细分析这张图片：
1. 图像类型：照片/截图/插画/图表/文档等
2. 主要内容：描述核心元素和场景
3. 文字内容：如有文字，请完整转录
4. 视觉细节：颜色、构图、风格等
5. 总结：一句话概括
请用中文简洁回答。""",
        
        "ocr": "请识别图片中的所有文字内容，按原文格式输出。如果没有文字，请描述图片内容。",
        
        "quick": "请用中文简要描述这张图片的内容。",
        
        "describe": "请详细描述这张图片的内容，包括所有可见的元素、颜色、文字等。"
    }
    
    # 推荐的视觉模型列表
    VISION_MODELS = [
        'qwen3-vl:4b', 'qwen3-vl:latest',
        'llava:7b', 'llava:13b', 'llava:34b',
        'llava-llama3:latest',
        'minicpm-v:latest',
        'deepseek-ocr:latest',
        'moondream:latest',
        'bakllava:latest',
    ]
    
    def __init__(self):
        super().__init__()
        self.model = "qwen3-vl:4b"
        self.installed_models = []
        self._refresh_models()
    
    def set_config(self, config):
        """设置引擎配置"""
        super().set_config(config)
        if 'model' in config:
            self.model = config['model']
    
    def _refresh_models(self):
        """刷新已安装模型列表"""
        if not OLLAMA_AVAILABLE:
            self.installed_models = []
            return
        
        try:
            result = ollama.list()
            self.installed_models = [m['model'] for m in result.get('models', [])]
        except Exception:
            self.installed_models = []
    
    def is_available(self):
        """检查引擎是否可用"""
        if not OLLAMA_AVAILABLE:
            return False
        try:
            ollama.list()
            return True
        except Exception:
            return False
    
    def _find_model(self, model_name):
        """查找模型（处理版本标签）"""
        for m in self.installed_models:
            if m == model_name or m.startswith(model_name + ':') or model_name in m:
                return m
        return None
    
    def get_model_list(self):
        """获取可用模型列表"""
        self._refresh_models()
        
        result = f"{Fore.CYAN}已安装的模型:{Style.RESET_ALL}\n"
        for m in self.installed_models:
            marker = f"{Fore.GREEN}*{Style.RESET_ALL}" if any(vm.split(':')[0] in m for vm in ['vl', 'llava', 'vision', 'ocr', 'minicpm', 'moondream', 'qwen3-vl']) else " "
            result += f"  {marker} {m}\n"
        
        result += f"\n{Fore.CYAN}推荐的视觉模型:{Style.RESET_ALL}\n"
        for vm in self.VISION_MODELS:
            status = f"{Fore.GREEN}[已安装]{Style.RESET_ALL}" if self._find_model(vm) else f"{Fore.YELLOW}[未安装]{Style.RESET_ALL}"
            result += f"  - {vm} {status}\n"
        
        return result
    
    def set_model(self, model_name):
        """设置当前使用的模型"""
        actual = self._find_model(model_name)
        if actual:
            self.model = actual
            return True, f"已切换到模型: {actual}"
        
        # 如果没找到，直接使用用户指定的名称（可能还没安装）
        self.model = model_name
        return True, f"已设置模型: {model_name} (未安装? 运行 ollama pull {model_name})"
    
    def analyze(self, image_path, prompt="请描述这张图片"):
        """分析图片（非流式）"""
        if not OLLAMA_AVAILABLE:
            raise Exception("ollama 库未安装，请运行: pip install ollama")
        
        if not os.path.exists(image_path):
            raise Exception(f"文件不存在: {image_path}")
        
        # 使用预设提示词或自定义提示词
        actual_prompt = self.PROMPTS.get(prompt, prompt)
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{
                    'role': 'user',
                    'content': actual_prompt,
                    'images': [image_path]
                }]
            )
            return response.get('message', {}).get('content', '')
        except Exception as e:
            raise Exception(f"Ollama识别失败: {str(e)}")
    
    def stream_analyze(self, image_path, prompt="请描述这张图片"):
        """流式分析图片"""
        if not OLLAMA_AVAILABLE:
            raise Exception("ollama 库未安装，请运行: pip install ollama")
        
        if not os.path.exists(image_path):
            raise Exception(f"文件不存在: {image_path}")
        
        # 使用预设提示词或自定义提示词
        actual_prompt = self.PROMPTS.get(prompt, prompt)
        
        # 检查模型是否已安装
        actual_model = self._find_model(self.model)
        if not actual_model:
            raise Exception(f"模型 {self.model} 未安装。请运行: ollama pull {self.model}")
        
        try:
            response = ollama.chat(
                model=actual_model,
                messages=[{
                    'role': 'user',
                    'content': actual_prompt,
                    'images': [image_path]
                }],
                stream=False
            )
            
            content = response.get('message', {}).get('content', '')
            if content:
                yield content
            else:
                raise Exception("模型返回空内容")
                    
        except Exception as e:
            error_msg = str(e)
            if "connection" in error_msg.lower():
                raise Exception("无法连接到 Ollama 服务，请确保服务正在运行 (ollama serve)")
            raise Exception(f"Ollama识别失败: {error_msg}")
    
    def get_help(self):
        """获取引擎帮助信息"""
        return f"""
Ollama 视觉引擎帮助
==================
当前模型: {self.model}

使用说明:
1. 确保 Ollama 服务正在运行
2. 安装视觉模型: ollama pull qwen3-vl:4b
3. 使用 /image model <模型名> 切换模型

支持的操作:
- analyze  详细分析
- ocr      文字识别
- quick    快速描述
- describe 完整描述

模型管理:
- /image models    列出模型
- /image model <名> 切换模型
"""
