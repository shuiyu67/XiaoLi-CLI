"""
发送图片插件 - Clawli 模式下向手机端发送图片
支持独立进程服务器模式
"""
import os
import json
from typing import Dict, Any


def get_clawli_server():
    """获取 Clawli 服务器实例（优先使用独立进程服务器）"""
    try:
        import clawli_server
        if clawli_server.is_running():
            return clawli_server
    except ImportError:
        pass
    
    # 回退到旧的 WebSocket 服务器
    try:
        from websocket_server import websocket_server
        return websocket_server
    except ImportError:
        return None


class Liugin:
    """发送图片插件 - 在 Clawli 模式下发送图片到手机端"""
    
    def __init__(self):
        self.name = "send_image"
        self.cli = None
    
    def set_cli(self, cli_instance):
        """设置 CLI 引用"""
        self.cli = cli_instance
    
    def get_tool_info(self):
        """返回工具信息"""
        return {
            "name": "send_image",
            "description": "在 Clawli 模式下发送图片到手机端，支持 JPG、PNG、GIF、BMP、WEBP 格式",
            "keywords": ["图片", "发送", "手机", "clawli", "image", "send"],
            "usage": "send_image {\"image_path\": \"图片路径\", \"caption\": \"说明文字\"}"
        }
    
    def handle(self, args):
        """处理工具调用
        
        Args:
            args: 可以是 JSON 字符串或字典
        """
        # 解析参数
        if isinstance(args, str):
            try:
                params = json.loads(args)
            except json.JSONDecodeError:
                params = {"image_path": args.strip()}
        elif isinstance(args, dict):
            params = args
        else:
            return "错误: 参数格式无效"
        
        image_path = params.get("image_path", "")
        caption = params.get("caption", "")
        
        if not image_path:
            return "错误: 请提供图片路径"
        
        # 检查文件是否存在
        if not os.path.isfile(image_path):
            return f"错误: 图片文件不存在: {image_path}"
        
        # 检查是否是图片文件
        ext = image_path.lower().split('.')[-1] if '.' in image_path else ''
        supported_formats = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
        if ext not in supported_formats:
            return f"错误: 不支持的图片格式: {ext}，支持: {', '.join(supported_formats)}"
        
        # 获取服务器
        server = get_clawli_server()
        if not server:
            return "错误: Clawli 服务器未初始化"
        
        # 尝试使用独立进程服务器
        try:
            import clawli_server
            if clawli_server.is_running():
                success, msg = clawli_server.send_image(image_path, caption)
                if success:
                    file_size = os.path.getsize(image_path)
                    size_str = f"{file_size/1024:.1f}KB" if file_size < 1024*1024 else f"{file_size/1024/1024:.2f}MB"
                    return f"图片已发送到手机端: {os.path.basename(image_path)} ({size_str})"
                else:
                    return f"错误: {msg}"
        except ImportError:
            pass
        
        # 回退到旧的 WebSocket 服务器
        if hasattr(server, 'running') and not server.running:
            return "错误: Clawli 模式未启动，请先使用 /remote start 启动远程服务"
        
        if hasattr(server, 'clients') and not server.clients:
            return "错误: 没有连接的手机端，请确保手机已连接"
        
        if hasattr(server, 'send_image_to_clients'):
            success = server.send_image_to_clients(image_path, caption)
            if success:
                file_size = os.path.getsize(image_path)
                size_str = f"{file_size/1024:.1f}KB" if file_size < 1024*1024 else f"{file_size/1024/1024:.2f}MB"
                return f"图片已发送到手机端: {os.path.basename(image_path)} ({size_str})"
        
        return "错误: 发送图片失败"


# 工具定义
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "send_image",
            "description": "在 Clawli 模式下发送图片到手机端。支持 JPG、PNG、GIF、BMP、WEBP 格式。",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "图片文件的绝对路径"
                    },
                    "caption": {
                        "type": "string",
                        "description": "图片说明文字（可选）"
                    }
                },
                "required": ["image_path"]
            }
        }
    }
]


def get_tools():
    """返回工具定义列表"""
    return TOOLS