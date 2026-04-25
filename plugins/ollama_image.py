"""
Ollama图像识别插件
支持多种图像识别引擎的切换
"""

import os
import sys
from colorama import Fore, Style

# 添加项目根目录到sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from image_engine import get_engine_manager


class Liugin:
    """图像识别插件 - 支持多引擎切换"""
    
    def __init__(self):
        self.usage = """图像识别插件使用方法：
/image <操作> <参数>

操作命令：
- analyze <图片路径>     - 详细分析图片
- ocr <图片路径>        - 快速OCR文字识别
- quick <图片路径>      - 快速图片描述
- describe <图片路径>   - 完整描述图片
- model [模型名]        - 查看/切换模型
- models               - 列出可用的视觉模型
- engine [引擎名]       - 查看/切换识别引擎
- engines              - 列出所有识别引擎

示例：
- image analyze C:\\photo.png
- image ocr C:\\screenshot.png
- image model llava:13b
- image engine openai

JSON调用示例：
{"action": "use_tool", "tool": "image", "args": "analyze c:\\\\test.png"}
"""
        self.cli = None
        self.engine_manager = None
        
        # 支持的图片格式
        self.supported_formats = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp']
    
    def set_cli(self, cli):
        """设置CLI实例引用"""
        self.cli = cli
        # 注册插件命令
        self.cli.register_liugin_command('image', self.command_handler)
        self.cli.register_liugin_command('img', self.command_handler)
    
    def command_handler(self, args):
        """处理命令"""
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 1:
            return self._get_help()
        
        operation = parts[0].lower()
        remaining_args = parts[1] if len(parts) > 1 else ""
        return self.handle(f"{operation} {remaining_args}")
    
    def get_tool_info(self):
        return {
            "name": "image",
            "description": "图像识别工具，支持多引擎切换，使用本地或云端模型进行图像分析",
            "keywords": ["图像", "图片", "image", "analyze", "分析", "视觉", "识别", "OCR"],
            "usage": """image 工具使用说明：
- analyze <图片路径> - 详细分析
- ocr <图片路径> - OCR文字识别  
- quick <图片路径> - 快速描述
- engine <引擎名> - 切换引擎
- engines - 列出所有引擎
支持格式：PNG, JPG, JPEG, GIF, WEBP, BMP"""
        }
    
    def handle(self, args):
        """处理请求"""
        # 延迟初始化引擎管理器
        if self.engine_manager is None:
            self.engine_manager = get_engine_manager()
        
        try:
            parts = args.strip().split(maxsplit=1)
            if len(parts) < 1:
                return self._get_help()
            
            operation = parts[0].lower()
            image_path = parts[1].strip() if len(parts) > 1 else ""
            
            # 引擎管理命令
            if operation == "engines":
                return self.engine_manager.list_engines()
            
            elif operation == "engine":
                if image_path:
                    success, msg = self.engine_manager.switch_engine(image_path)
                    return msg
                return f"当前引擎: {self.engine_manager.get_current_engine_name()}"
            
            elif operation == "models":
                engine = self.engine_manager.get_engine()
                if engine and hasattr(engine, 'get_model_list'):
                    return engine.get_model_list()
                return "当前引擎不支持模型列表"
            
            elif operation == "model":
                engine = self.engine_manager.get_engine()
                if not image_path:
                    if engine and hasattr(engine, 'model'):
                        return f"当前模型: {engine.model}"
                    return "当前引擎不支持模型切换"
                if engine and hasattr(engine, 'set_model'):
                    success, msg = engine.set_model(image_path)
                    return msg
                return "当前引擎不支持模型切换"
            
            # 图像分析命令
            elif operation in ["analyze", "ocr", "quick", "describe"]:
                if not image_path:
                    return f"错误：请提供图片路径。用法: {operation} <图片路径>"
                return self._analyze_image(image_path, operation)
            
            else:
                # 兼容旧用法，直接当作图片路径处理
                return self._analyze_image(operation, "analyze")
        
        except Exception as e:
            return f"错误: {str(e)}"
    
    def _get_help(self):
        """获取帮助信息"""
        current = self.engine_manager.get_current_engine_name() if self.engine_manager else "未初始化"
        return f"""图像识别插件命令:
- analyze <图片路径>  详细分析图片
- ocr <图片路径>     OCR文字识别
- quick <图片路径>   快速描述
- describe <图片路径> 完整描述
- model [模型名]     查看/切换模型
- models            列出视觉模型
- engine [引擎名]    查看/切换引擎
- engines           列出所有引擎

当前引擎: {current}"""
    
    def _analyze_image(self, image_path, mode="analyze"):
        """使用引擎分析图片"""
        # 检查文件
        if not os.path.exists(image_path):
            return f"文件不存在: {image_path}"
        
        ext = os.path.splitext(image_path)[1].lower().lstrip('.')
        if ext not in self.supported_formats:
            return f"不支持的图片格式: {ext}。支持: {', '.join(self.supported_formats)}"
        
        # 检查引擎
        engine = self.engine_manager.get_engine()
        if not engine:
            return "没有可用的图像引擎"
        
        file_size = os.path.getsize(image_path)
        engine_name = self.engine_manager.get_current_engine_name()
        
        # 获取模型名（如果支持）
        model_info = ""
        if hasattr(engine, 'model'):
            model_info = f" | 模型: {engine.model}"
        
        # 文件大小警告
        size_warning = ""
        if file_size > 1024 * 1024:  # 大于1MB
            size_warning = f" {Fore.YELLOW}(较大图片，处理可能需要较长时间){Style.RESET_ALL}"
        
        print(f"{Fore.CYAN}📷 图像识别: {os.path.basename(image_path)}{Style.RESET_ALL}{size_warning}")
        print(f"{Fore.YELLOW}📦 大小: {file_size/1024:.1f}KB | 引擎: {engine_name}{model_info}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}⏳ 正在识别，请耐心等待...{Style.RESET_ALL}")
        
        try:
            # 使用引擎分析
            full_response = ""
            for chunk in self.engine_manager.analyze(image_path, mode, stream=True):
                if chunk:
                    print(chunk, end='', flush=True)
                    full_response += chunk
            
            print()  # 换行
            print(f"{Fore.GREEN}✓ 识别完成{Style.RESET_ALL}")
            
            return full_response if full_response else "识别结果为空"
            
        except Exception as e:
            error_msg = str(e)
            print(f"{Fore.RED}✗ {error_msg}{Style.RESET_ALL}")
            return f"识别失败: {error_msg}"