"""
WebSocket 服务端模块
用于 Clawli 安卓客户端连接

支持两种模式:
1. 本地模式 (/remote start) - 局域网直连，需要设置密码
2. 代理模式 (/remote proxy) - 通过中继服务器，需要设置密码

功能:
- 消息收发
- 工具调用状态推送
- 任意文件上传保存
- 图片识别
"""

import asyncio
import json
import threading
import time
import base64
import hashlib
import socket
import os
from datetime import datetime
from typing import Optional, Dict, List

# 全局变量
websocket_server = None  # 当前活动的服务器实例（供外部访问）
proxy_client = None

# 文件保存目录
CLAWLI_FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clawli_files")

# 确保目录存在
os.makedirs(CLAWLI_FILES_DIR, exist_ok=True)

try:
    import websockets
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False


def get_file_category(filename: str) -> str:
    """根据文件扩展名获取分类"""
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    
    # 图片
    if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg']:
        return 'image'
    # 视频
    if ext in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm']:
        return 'video'
    # 音频
    if ext in ['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a']:
        return 'audio'
    # 文档
    if ext in ['txt', 'md', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'json', 'csv', 'xml']:
        return 'document'
    # 代码
    if ext in ['py', 'js', 'ts', 'java', 'c', 'cpp', 'h', 'css', 'html', 'sql', 'sh']:
        return 'code'
    # 压缩包
    if ext in ['zip', 'rar', '7z', 'tar', 'gz']:
        return 'archive'
    return 'file'


def save_uploaded_file(file_base64: str, filename: str) -> dict:
    """
    保存上传的文件到 clawli_files 目录
    返回: {success: bool, path: str, error: str, size: int}
    """
    try:
        # 解码文件
        file_data = base64.b64decode(file_base64)
        
        # 生成唯一文件名（时间戳 + 原始文件名）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in '._-' else '_' for c in filename)
        unique_name = f"{timestamp}_{safe_name}"
        
        # 保存路径
        file_path = os.path.join(CLAWLI_FILES_DIR, unique_name)
        
        # 写入文件
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        return {
            'success': True,
            'path': file_path,
            'filename': unique_name,
            'original_name': filename,
            'size': len(file_data),
            'category': get_file_category(filename)
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


# ============== 本地服务器 ==============

class LocalServer:
    """本地WebSocket服务器"""
    
    DEFAULT_PORT = 9079
    
    def __init__(self, cli_instance=None, port=None):
        self.cli = cli_instance
        self.port = port or self.DEFAULT_PORT
        self.password = ""
        self.running = False
        self.server = None
        self.clients: Dict = {}
        self.loop = None
        self.thread = None
        
    def set_cli(self, cli_instance):
        self.cli = cli_instance
    
    def set_password(self, password: str):
        self.password = password
    
    def start(self, password: str = None):
        if password:
            self.password = password
        
        if not self.password:
            from colorama import Fore, Style
            print(f"{Fore.RED}错误: 请先设置PC密码{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}用法: /remote start <端口> <密码>{Style.RESET_ALL}")
            return False
        
        if self.running:
            from colorama import Fore, Style
            print(f"{Fore.YELLOW}服务器已在运行{Style.RESET_ALL}")
            return True
        
        self.running = True
        # 设置 Clawli 模式标志
        if self.cli:
            self.cli.is_clawli_mode = True
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        time.sleep(0.5)
        
        if self.running:
            self._print_status()
            return True
        return False
    
    def _run_server(self):
        try:
            async def handle_client(websocket):
                client_addr = websocket.remote_address
                authenticated = False
                
                try:
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            msg_type = data.get("type", "")
                            
                            if msg_type == "heartbeat":
                                await websocket.send(json.dumps({"type": "heartbeat_ack"}))
                                continue
                            
                            if msg_type == "auth":
                                client_password = data.get("password", "")
                                if client_password == self.password:
                                    authenticated = True
                                    self.clients[websocket] = {"address": client_addr}
                                    await websocket.send(json.dumps({
                                        "type": "auth_success",
                                        "message": "认证成功"
                                    }))
                                else:
                                    await websocket.send(json.dumps({
                                        "type": "auth_failed",
                                        "message": "密码错误"
                                    }))
                                continue
                            
                            if not authenticated:
                                await websocket.send(json.dumps({
                                    "type": "error",
                                    "message": "请先认证"
                                }))
                                continue
                            
                            # 文本消息
                            if msg_type == "message":
                                content = data.get("content", "")
                                files = data.get("files", [])  # 文件信息列表
                                response = await self._process_message(content, files, websocket)
                                await websocket.send(json.dumps({
                                    "type": "message",
                                    "content": response
                                }))
                            
                            # 单个文件上传（兼容旧版）
                            elif msg_type == "file":
                                file_base64 = data.get("file", "")
                                filename = data.get("filename", "file")
                                file_text = data.get("text", "")
                                
                                response = await self._process_single_file(
                                    file_base64, filename, file_text, websocket
                                )
                                await websocket.send(json.dumps({
                                    "type": "message",
                                    "content": response
                                }))
                        
                        except json.JSONDecodeError:
                            await websocket.send(json.dumps({
                                "type": "error",
                                "message": "JSON格式错误"
                            }))
                
                except Exception as e:
                    from colorama import Fore, Style
                    # 不打印断开连接的异常，避免不必要的错误提示
                    if "no close frame" not in str(e):
                        print(f"{Fore.RED}客户端连接异常 [{client_addr}]: {e}{Style.RESET_ALL}")
                finally:
                    if websocket in self.clients:
                        del self.clients[websocket]
                        from colorama import Fore, Style
                        print(f"{Fore.YELLOW}客户端断开连接 [{client_addr}], 等待新连接...{Style.RESET_ALL}")
            
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            async def start_async():
                # 使用外层已创建的事件循环
                self.server = await websockets.serve(
                    handle_client,
                    "0.0.0.0",
                    self.port,
                    ping_interval=None,  # 禁用 ping，保持永久连接
                    ping_timeout=None,
                    max_size=100 * 1024 * 1024  # 100MB
                )
                # 保持服务器运行
                try:
                    await asyncio.sleep(float('inf'))
                except (KeyboardInterrupt, SystemExit):
                    pass
                except Exception as e:
                    from colorama import Fore, Style
                    print(f"{Fore.RED}服务器运行异常: {e}{Style.RESET_ALL}")
            
            # 循环运行服务器，确保持续运行
            while self.running:
                try:
                    self.loop.run_until_complete(start_async())
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    from colorama import Fore, Style
                    if self.running:  # 只有在需要运行时才打印错误
                        print(f"{Fore.RED}服务器重启: {e}{Style.RESET_ALL}")
                        import time
                        time.sleep(1)  # 等待后重试
            
        except ImportError:
            from colorama import Fore, Style
            print(f"{Fore.RED}错误: websockets 库未安装{Style.RESET_ALL}")
            self.running = False
        except Exception as e:
            from colorama import Fore, Style
            # 只在非断连错误时打印
            if "no close frame" not in str(e) and "closed" not in str(e).lower():
                print(f"{Fore.RED}服务器异常: {e}{Style.RESET_ALL}")
            # 服务器异常时尝试保持运行状态
            # 不设置 running = False，让服务器继续等待连接
    
    async def _send_tool_status(self, websocket, tool_name: str, args: str, status: str, result: str = ""):
        """发送工具/文件处理状态"""
        try:
            # 确保所有值都不是 None，并转换为字符串
            data = {
                "type": "tool_status",
                "tool": str(tool_name) if tool_name else "",
                "args": str(args)[:100] if args else "",
                "status": str(status) if status else "",
                "result": str(result)[:500] if result else ""
            }
            json_str = json.dumps(data, ensure_ascii=False)
            await websocket.send(json_str)
        except Exception as e:
            print(f"[Clawli] 发送工具状态失败: {e}")
    
    async def _send_image(self, websocket, image_data: str, filename: str = "image.png", caption: str = ""):
        """发送图片到手机端
        
        Args:
            websocket: WebSocket连接
            image_data: 图片数据（文件路径或base64编码）
            filename: 图片文件名
            caption: 图片说明文字
        """
        try:
            # 判断是文件路径还是base64
            if os.path.isfile(image_data):
                # 是文件路径，读取并编码
                with open(image_data, 'rb') as f:
                    file_data = f.read()
                image_base64 = base64.b64encode(file_data).decode('utf-8')
                filename = os.path.basename(image_data)
            else:
                # 假设是base64编码
                image_base64 = image_data
            
            data = {
                "type": "image",
                "image": image_base64,
                "filename": filename,
                "caption": caption
            }
            json_str = json.dumps(data, ensure_ascii=False)
            await websocket.send(json_str)
            print(f"[Clawli] 图片已发送: {filename}")
            return True
        except Exception as e:
            print(f"[Clawli] 发送图片失败: {e}")
            return False
    
    def send_image_to_clients(self, image_path: str, caption: str = "") -> bool:
        """向所有连接的客户端发送图片（同步接口，供外部调用）
        
        Args:
            image_path: 图片文件路径
            caption: 图片说明文字
            
        Returns:
            bool: 是否成功发送
        """
        if not self.clients:
            print("[Clawli] 没有连接的客户端")
            return False
        
        if not os.path.isfile(image_path):
            print(f"[Clawli] 图片文件不存在: {image_path}")
            return False
        
        # 在事件循环中异步发送
        if self.loop:
            future = asyncio.run_coroutine_threadsafe(
                self._broadcast_image(image_path, caption),
                self.loop
            )
            try:
                return future.result(timeout=10)
            except Exception as e:
                print(f"[Clawli] 发送图片超时: {e}")
                return False
        return False
    
    async def _broadcast_image(self, image_path: str, caption: str = ""):
        """向所有客户端广播图片"""
        success = False
        for ws in list(self.clients.keys()):
            if await self._send_image(ws, image_path, caption=caption):
                success = True
        return success
    
    async def _process_single_file(self, file_base64: str, filename: str, text: str, websocket=None) -> str:
        """处理单个文件上传"""
        try:
            # 发送状态
            if websocket:
                await self._send_tool_status(websocket, "文件上传", filename, "calling")
            
            # 保存文件
            result = save_uploaded_file(file_base64, filename)
            
            if not result['success']:
                if websocket:
                    await self._send_tool_status(websocket, "文件上传", filename, "error", result.get('error', '未知错误'))
                return f"文件上传失败: {result.get('error', '未知错误')}"
            
            file_path = result['path']
            category = result['category']
            
            if websocket:
                size = result.get('size', 0)
                size_str = f"{size/1024:.1f}KB" if size < 1024*1024 else f"{size/1024/1024:.1f}MB"
                await self._send_tool_status(websocket, "文件上传", filename, "success", 
                    f"已保存: {result.get('filename', filename)} ({size_str})")
            
            # 根据文件类型处理
            if category == 'image':
                # 图片走图像识别
                return await self._process_image_file(file_path, text, websocket)
            else:
                # 其他文件，构建消息
                return await self._process_message(f"@{file_path}", [], websocket, text)
            
        except Exception as e:
            if websocket:
                await self._send_tool_status(websocket, "文件上传", filename, "error", str(e))
            return f"处理文件时出错: {str(e)}"
    
    async def _process_image_file(self, file_path: str, text: str, websocket=None) -> str:
        """处理图片文件（走图像识别）"""
        if not self.cli:
            return "错误: CLI未初始化"
        
        try:
            # 检查图像识别引擎
            image_engine = getattr(self.cli, 'image_engine', None)
            if not image_engine:
                try:
                    from image_engine import get_image_engine
                    image_engine = get_image_engine()
                except:
                    return f"@{file_path}"  # 没有图像引擎，直接返回路径
            
            if websocket:
                await self._send_tool_status(websocket, "图像识别", text or "分析图片", "calling")
            
            # 读取图片
            with open(file_path, 'rb') as f:
                image_data = f.read()
            
            # 调用图像识别
            try:
                result = image_engine.analyze(image_data, text or "请描述这张图片")
                
                if websocket:
                    await self._send_tool_status(websocket, "图像识别", text or "分析图片", "success", result[:200] if result else "无结果")
                
                # 返回识别结果 + 文件路径
                return await self._process_message(f"@{file_path}", [], websocket, 
                    f"图片内容: {result}\n\n{text}" if text else f"图片内容: {result}")
                
            except Exception as e:
                if websocket:
                    await self._send_tool_status(websocket, "图像识别", text or "分析图片", "error", str(e))
                return f"@{file_path}\n\n图像识别失败: {str(e)}"
            
        except Exception as e:
            return f"@{file_path}\n\n处理图片时出错: {str(e)}"
    
    async def _process_message(self, content: str, files: List[dict] = None, websocket=None, extra_text: str = "") -> str:
        """处理消息（支持工具调用循环）"""
        if not self.cli:
            return "错误: CLI未初始化"
        
        try:
            if not self.cli.current_engine:
                return "错误: 没有可用的AI引擎"
            
            # 构建完整消息
            full_content = content
            if extra_text:
                full_content = f"{content}\n{extra_text}"
            
            # 添加clawli标识
            full_content = f"{full_content}\n\n[此消息由clawli手机远程发送]"
            
            self.cli.shared_conversation_history.append({
                "role": "user",
                "content": full_content
            })
            
            max_loops = 10
            loop_count = 0
            current_input = full_content
            final_response = ""
            
            while loop_count < max_loops:
                loop_count += 1
                
                system_prompt = self.cli._build_system_prompt(
                    self.cli.get_liugin_usage_prompts()
                )
                
                response = self.cli.current_engine.generate_response(
                    current_input,
                    system_prompt=system_prompt
                )
                
                text_content, json_data = self.cli._parse_mixed_response(response)
                
                # 调试：打印原始响应和解析结果
                print(f"[Clawli] AI响应: {response[:200]}...")
                print(f"[Clawli] 解析结果: text={text_content[:50] if text_content else 'None'}..., json={json_data}")
                
                if json_data:
                    tool_calls = None
                    
                    # 支持多种JSON格式（MCP/Plugin/OpenAI/Anthropic）
                    if isinstance(json_data, dict):
                        # 小狸自有格式
                        if json_data.get('action') == 'use_tool':
                            tool_calls = [json_data]
                        elif 'tool' in json_data and 'args' in json_data:
                            tool_calls = [json_data]
                        # OpenAI function_call 格式
                        elif 'function_call' in json_data:
                            fc = json_data['function_call']
                            if isinstance(fc, dict):
                                args = fc.get('arguments', '')
                                # arguments 可能是 JSON 字符串，需要解析
                                if isinstance(args, str) and args.startswith('{'):
                                    try:
                                        args = json.loads(args)
                                    except:
                                        pass
                                tool_calls = [{
                                    'tool': fc.get('name', ''),
                                    'args': args if isinstance(args, str) else '',
                                    'arguments': args if isinstance(args, dict) else None
                                }]
                        # MCP/Anthropic 格式
                        elif 'name' in json_data and 'arguments' in json_data:
                            args = json_data.get('arguments', '')
                            # arguments 可能是 JSON 字符串，需要解析
                            if isinstance(args, str) and args.startswith('{'):
                                try:
                                    args = json.loads(args)
                                except:
                                    pass
                            tool_calls = [{
                                'tool': json_data.get('name', ''),
                                'args': args if isinstance(args, str) else '',
                                'arguments': args if isinstance(args, dict) else None
                            }]
                        # OpenAI tool_calls 格式
                        elif json_data.get('type') == 'function' and 'function' in json_data:
                            func = json_data['function']
                            args = func.get('arguments', '')
                            # arguments 可能是 JSON 字符串，需要解析
                            if isinstance(args, str) and args.startswith('{'):
                                try:
                                    args = json.loads(args)
                                except:
                                    pass
                            tool_calls = [{
                                'tool': func.get('name', ''),
                                'args': args if isinstance(args, str) else '',
                                'arguments': args if isinstance(args, dict) else None
                            }]
                    elif isinstance(json_data, list):
                        tool_calls = []
                        for item in json_data:
                            if isinstance(item, dict):
                                if item.get('action') == 'use_tool':
                                    tool_calls.append(item)
                                elif 'tool' in item and 'args' in item:
                                    tool_calls.append(item)
                                elif 'name' in item and 'arguments' in item:
                                    args = item.get('arguments', '')
                                    # arguments 可能是 JSON 字符串，需要解析
                                    if isinstance(args, str) and args.startswith('{'):
                                        try:
                                            args = json.loads(args)
                                        except:
                                            pass
                                    tool_calls.append({
                                        'tool': item.get('name', ''),
                                        'args': args if isinstance(args, str) else '',
                                        'arguments': args if isinstance(args, dict) else None
                                    })
                        if not tool_calls:
                            tool_calls = None
                    
                    if tool_calls:
                        print(f"[Clawli] 检测到工具调用: {tool_calls}")
                        results = []
                        for tool_data in tool_calls:
                            tool_name = tool_data.get('tool', '未知工具')
                            tool_args = tool_data.get('args', '')
                            
                            if websocket:
                                await self._send_tool_status(websocket, tool_name, tool_args, "calling")
                            
                            result = self.cli.process_tool_call(tool_data)
                            result_text = result.get('result', '无结果')
                            results.append(result_text)
                            
                            if websocket:
                                await self._send_tool_status(websocket, tool_name, tool_args, "success", result_text)
                        
                        self.cli.shared_conversation_history.append({
                            "role": "assistant",
                            "content": response
                        })
                        
                        tool_result_str = "\n".join([f"工具执行结果: {r}" for r in results])
                        current_input = f"{tool_result_str}\n请根据工具执行结果继续回答。\n\n[此消息由clawli手机远程发送]"
                        self.cli.shared_conversation_history.append({
                            "role": "user",
                            "content": current_input
                        })
                        continue
                    
                    if isinstance(json_data, dict) and json_data.get('message'):
                        final_response = json_data['message']
                        self.cli.shared_conversation_history.append({
                            "role": "assistant",
                            "content": final_response
                        })
                        return final_response
                
                final_response = text_content if text_content else response
                self.cli.shared_conversation_history.append({
                    "role": "assistant",
                    "content": final_response
                })
                return final_response
            
            return "错误: 工具调用次数超限"
            
        except Exception as e:
            return f"处理消息时出错: {str(e)}"
    
    def stop(self):
        if not self.running:
            return
        self.running = False
        # 清除 Clawli 模式标志
        if self.cli:
            self.cli.is_clawli_mode = False
        if self.server and self.loop:
            self.loop.call_soon_threadsafe(self.server.close)
        from colorama import Fore, Style
        print(f"{Fore.YELLOW}本地服务器已停止{Style.RESET_ALL}")
    
    def _print_status(self):
        from colorama import Fore, Style
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except:
            local_ip = "未知"
        
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}[本地模式] 远程服务已启动{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}本机IP: {Fore.YELLOW}{local_ip}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}端口: {Fore.YELLOW}{self.port}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}PC密码: {Fore.YELLOW}{'*' * len(self.password)}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}文件目录: {Fore.YELLOW}{CLAWLI_FILES_DIR}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}安卓端输入 {local_ip}:{self.port} 和PC密码即可连接{Style.RESET_ALL}\n")
    
    def get_status(self) -> dict:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except:
            local_ip = "未知"
        return {
            "running": self.running,
            "mode": "local",
            "port": self.port,
            "local_ip": local_ip,
            "connected_clients": len(self.clients),
            "files_dir": CLAWLI_FILES_DIR
        }


# ============== 代理客户端 ==============

class ProxyClient:
    """代理模式客户端"""
    
    def __init__(self, cli_instance=None):
        self.cli = cli_instance
        self.server_url = ""
        self.server_password = ""
        self.pc_password = ""
        self.port = 0
        self.websocket = None
        self.running = False
        self.loop = None
        self.thread = None
    
    def set_cli(self, cli_instance):
        self.cli = cli_instance
    
    def start(self, server_host: str, server_port: int, 
              server_password: str, pc_port: int, pc_password: str):
        self.server_url = f"ws://{server_host}:{server_port}"
        self.server_password = server_password
        self.port = pc_port
        self.pc_password = pc_password
        
        if not self.server_password or not self.pc_password:
            from colorama import Fore, Style
            print(f"{Fore.RED}错误: 请提供服务器密码和PC密码{Style.RESET_ALL}")
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._run_client, daemon=True)
        self.thread.start()
        time.sleep(1)
        return self.running
    
    def _run_client(self):
        try:
            async def connect():
                async with websockets.connect(self.server_url, max_size=100*1024*1024) as ws:
                    self.websocket = ws
                    
                    await ws.send(json.dumps({
                        "type": "auth_server",
                        "password": self.server_password
                    }))
                    
                    response = await ws.recv()
                    data = json.loads(response)
                    
                    if data.get("type") != "auth_server_success":
                        from colorama import Fore, Style
                        print(f"{Fore.RED}服务器认证失败{Style.RESET_ALL}")
                        self.running = False
                        return
                    
                    await ws.send(json.dumps({
                        "type": "register_pc",
                        "port": self.port,
                        "password": self.pc_password
                    }))
                    
                    response = await ws.recv()
                    data = json.loads(response)
                    
                    if data.get("type") == "register_success":
                        self.port = data.get("port", self.port)
                        self._print_status()
                        await self._main_loop(ws)
                    else:
                        from colorama import Fore, Style
                        print(f"{Fore.RED}注册失败{Style.RESET_ALL}")
                        self.running = False
            
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(connect())
            
        except Exception as e:
            from colorama import Fore, Style
            print(f"{Fore.RED}连接失败: {e}{Style.RESET_ALL}")
            self.running = False
    
    async def _main_loop(self, ws):
        try:
            async for message in ws:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type", "")
                    
                    if msg_type == "heartbeat_ack":
                        continue
                    if msg_type in ["android_connected", "android_disconnected"]:
                        continue
                    
                    if msg_type == "message":
                        content = data.get("content", "")
                        files = data.get("files", [])
                        response = await self._process_message(content, files)
                        await ws.send(json.dumps({"type": "message", "content": response}))
                    
                    if msg_type == "file":
                        file_base64 = data.get("file", "")
                        filename = data.get("filename", "file")
                        file_text = data.get("text", "")
                        response = await self._process_single_file(file_base64, filename, file_text, ws)
                        await ws.send(json.dumps({"type": "message", "content": response}))
                    
                    if msg_type == "disconnected":
                        break
                        
                except json.JSONDecodeError:
                    pass
        
        except Exception as e:
            from colorama import Fore, Style
            print(f"{Fore.RED}连接断开: {e}{Style.RESET_ALL}")
        finally:
            self.running = False
    
    async def _process_single_file(self, file_base64: str, filename: str, text: str) -> str:
        """处理单个文件"""
        result = save_uploaded_file(file_base64, filename)
        
        if not result['success']:
            return f"文件上传失败: {result['error']}"
        
        file_path = result['path']
        category = result['category']
        
        if category == 'image':
            return await self._process_image_file(file_path, text)
        else:
            return await self._process_message(f"@{file_path}", [], text)
    
    async def _process_image_file(self, file_path: str, text: str) -> str:
        """处理图片"""
        if not self.cli:
            return f"@{file_path}"
        
        try:
            image_engine = getattr(self.cli, 'image_engine', None)
            if not image_engine:
                try:
                    from image_engine import get_image_engine
                    image_engine = get_image_engine()
                except:
                    return f"@{file_path}"
            
            with open(file_path, 'rb') as f:
                image_data = f.read()
            
            result = image_engine.analyze(image_data, text or "请描述这张图片")
            return await self._process_message(f"@{file_path}", [], f"图片内容: {result}\n\n{text}" if text else f"图片内容: {result}")
            
        except Exception as e:
            return f"@{file_path}\n\n图像识别失败: {str(e)}"
    
    async def _process_message(self, content: str, files: List[dict] = None, extra_text: str = "") -> str:
        """处理消息"""
        if not self.cli:
            return "错误: CLI未初始化"
        
        try:
            if not self.cli.current_engine:
                return "错误: 没有可用的AI引擎"
            
            full_content = content
            if extra_text:
                full_content = f"{content}\n{extra_text}"
            
            full_content = f"{full_content}\n\n[此消息由clawli手机远程发送]"
            
            self.cli.shared_conversation_history.append({
                "role": "user",
                "content": full_content
            })
            
            max_loops = 10
            loop_count = 0
            current_input = full_content
            
            while loop_count < max_loops:
                loop_count += 1
                
                system_prompt = self.cli._build_system_prompt(
                    self.cli.get_liugin_usage_prompts()
                )
                
                response = self.cli.current_engine.generate_response(
                    current_input,
                    system_prompt=system_prompt
                )
                
                text_content, json_data = self.cli._parse_mixed_response(response)
                
                # 调试：打印原始响应和解析结果
                print(f"[Clawli] AI响应: {response[:200]}...")
                print(f"[Clawli] 解析结果: text={text_content[:50] if text_content else 'None'}..., json={json_data}")
                
                if json_data:
                    tool_calls = None
                    
                    # 支持多种JSON格式（MCP/Plugin/OpenAI/Anthropic）
                    if isinstance(json_data, dict):
                        # 小狸自有格式
                        if json_data.get('action') == 'use_tool':
                            tool_calls = [json_data]
                        elif 'tool' in json_data and 'args' in json_data:
                            tool_calls = [json_data]
                        # OpenAI function_call 格式
                        elif 'function_call' in json_data:
                            fc = json_data['function_call']
                            if isinstance(fc, dict):
                                args = fc.get('arguments', '')
                                # arguments 可能是 JSON 字符串，需要解析
                                if isinstance(args, str) and args.startswith('{'):
                                    try:
                                        args = json.loads(args)
                                    except:
                                        pass
                                tool_calls = [{
                                    'tool': fc.get('name', ''),
                                    'args': args if isinstance(args, str) else '',
                                    'arguments': args if isinstance(args, dict) else None
                                }]
                        # MCP/Anthropic 格式
                        elif 'name' in json_data and 'arguments' in json_data:
                            args = json_data.get('arguments', '')
                            # arguments 可能是 JSON 字符串，需要解析
                            if isinstance(args, str) and args.startswith('{'):
                                try:
                                    args = json.loads(args)
                                except:
                                    pass
                            tool_calls = [{
                                'tool': json_data.get('name', ''),
                                'args': args if isinstance(args, str) else '',
                                'arguments': args if isinstance(args, dict) else None
                            }]
                        # OpenAI tool_calls 格式
                        elif json_data.get('type') == 'function' and 'function' in json_data:
                            func = json_data['function']
                            args = func.get('arguments', '')
                            # arguments 可能是 JSON 字符串，需要解析
                            if isinstance(args, str) and args.startswith('{'):
                                try:
                                    args = json.loads(args)
                                except:
                                    pass
                            tool_calls = [{
                                'tool': func.get('name', ''),
                                'args': args if isinstance(args, str) else '',
                                'arguments': args if isinstance(args, dict) else None
                            }]
                    elif isinstance(json_data, list):
                        tool_calls = []
                        for item in json_data:
                            if isinstance(item, dict):
                                if item.get('action') == 'use_tool':
                                    tool_calls.append(item)
                                elif 'tool' in item and 'args' in item:
                                    tool_calls.append(item)
                                elif 'name' in item and 'arguments' in item:
                                    args = item.get('arguments', '')
                                    # arguments 可能是 JSON 字符串，需要解析
                                    if isinstance(args, str) and args.startswith('{'):
                                        try:
                                            args = json.loads(args)
                                        except:
                                            pass
                                    tool_calls.append({
                                        'tool': item.get('name', ''),
                                        'args': args if isinstance(args, str) else '',
                                        'arguments': args if isinstance(args, dict) else None
                                    })
                        if not tool_calls:
                            tool_calls = None
                    
                    if tool_calls:
                        print(f"[Clawli] 检测到工具调用: {tool_calls}")
                        results = []
                        for tool_data in tool_calls:
                            result = self.cli.process_tool_call(tool_data)
                            results.append(result.get('result', '无结果'))
                        
                        self.cli.shared_conversation_history.append({
                            "role": "assistant",
                            "content": response
                        })
                        
                        tool_result_str = "\n".join([f"工具执行结果: {r}" for r in results])
                        current_input = f"{tool_result_str}\n请根据工具执行结果继续回答。\n\n[此消息由clawli手机远程发送]"
                        self.cli.shared_conversation_history.append({
                            "role": "user",
                            "content": current_input
                        })
                        continue
                    
                    if isinstance(json_data, dict) and json_data.get('message'):
                        final_response = json_data['message']
                        self.cli.shared_conversation_history.append({
                            "role": "assistant",
                            "content": final_response
                        })
                        return final_response
                
                final_response = text_content if text_content else response
                self.cli.shared_conversation_history.append({
                    "role": "assistant",
                    "content": final_response
                })
                return final_response
            
            return "错误: 工具调用次数超限"
            
        except Exception as e:
            return f"处理消息时出错: {str(e)}"
    
    def stop(self):
        if not self.running:
            return
        self.running = False
        if self.websocket and self.loop:
            async def close():
                await self.websocket.close()
            self.loop.call_soon_threadsafe(lambda: asyncio.create_task(close()))
        from colorama import Fore, Style
        print(f"{Fore.YELLOW}代理连接已断开{Style.RESET_ALL}")
    
    async def _send_image(self, image_data: str, filename: str = "image.png", caption: str = ""):
        """发送图片到手机端（通过代理服务器）
        
        Args:
            image_data: 图片数据（文件路径或base64编码）
            filename: 图片文件名
            caption: 图片说明文字
        """
        try:
            if not self.websocket:
                print("[Clawli Proxy] 没有活动的 WebSocket 连接")
                return False
            
            # 判断是文件路径还是base64
            if os.path.isfile(image_data):
                with open(image_data, 'rb') as f:
                    file_data = f.read()
                image_base64 = base64.b64encode(file_data).decode('utf-8')
                filename = os.path.basename(image_data)
            else:
                image_base64 = image_data
            
            data = {
                "type": "image",
                "image": image_base64,
                "filename": filename,
                "caption": caption
            }
            await self.websocket.send(json.dumps(data, ensure_ascii=False))
            print(f"[Clawli Proxy] 图片已发送: {filename}")
            return True
        except Exception as e:
            print(f"[Clawli Proxy] 发送图片失败: {e}")
            return False
    
    def send_image_to_clients(self, image_path: str, caption: str = "") -> bool:
        """发送图片（同步接口，供外部调用）"""
        if not self.websocket or not self.running:
            print("[Clawli Proxy] 未连接到代理服务器")
            return False
        
        if not os.path.isfile(image_path):
            print(f"[Clawli Proxy] 图片文件不存在: {image_path}")
            return False
        
        if self.loop:
            future = asyncio.run_coroutine_threadsafe(
                self._send_image(image_path, caption=caption),
                self.loop
            )
            try:
                return future.result(timeout=10)
            except Exception as e:
                print(f"[Clawli Proxy] 发送图片超时: {e}")
                return False
        return False
    
    def _print_status(self):
        from colorama import Fore, Style
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}[代理模式] 已连接到中继服务器{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}服务器: {Fore.YELLOW}{self.server_url}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}端口: {Fore.YELLOW}{self.port}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}文件目录: {Fore.YELLOW}{CLAWLI_FILES_DIR}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}\n")
    
    def get_status(self) -> dict:
        return {
            "running": self.running,
            "mode": "proxy",
            "server": self.server_url,
            "port": self.port,
            "files_dir": CLAWLI_FILES_DIR
        }


# ============== 全局接口 ==============

_local_server: Optional[LocalServer] = None
_proxy_client: Optional[ProxyClient] = None


def start_local_server(cli_instance, port: int = None, password: str = None) -> bool:
    global _local_server, _proxy_client, websocket_server
    
    if _proxy_client:
        _proxy_client.stop()
        _proxy_client = None
    
    if _local_server is None:
        _local_server = LocalServer(cli_instance, port)
    else:
        _local_server.set_cli(cli_instance)
        if port:
            _local_server.port = port
    
    result = _local_server.start(password)
    
    # 更新全局 websocket_server 引用
    if result:
        websocket_server = _local_server
    else:
        websocket_server = None
    
    return result


def start_proxy_client(cli_instance, server_host: str, server_port: int,
                       server_password: str, pc_port: int, pc_password: str) -> bool:
    global _local_server, _proxy_client, websocket_server
    
    if _local_server:
        _local_server.stop()
        _local_server = None
    
    if _proxy_client is None:
        _proxy_client = ProxyClient(cli_instance)
    else:
        _proxy_client.set_cli(cli_instance)
    
    result = _proxy_client.start(server_host, server_port, server_password, pc_port, pc_password)
    
    # 更新全局 websocket_server 引用
    if result:
        websocket_server = _proxy_client
    else:
        websocket_server = None
    
    return result
    
    return _proxy_client.start(server_host, server_port, server_password, pc_port, pc_password)


def stop_all():
    global _local_server, _proxy_client, websocket_server
    
    if _local_server:
        _local_server.stop()
    if _proxy_client:
        _proxy_client.stop()
    websocket_server = None


def get_status() -> dict:
    if _local_server and _local_server.running:
        return _local_server.get_status()
    if _proxy_client and _proxy_client.running:
        return _proxy_client.get_status()
    return {"running": False}


def is_running() -> bool:
    return get_status().get("running", False)


def get_active_server():
    """获取当前活动的服务器实例（本地或代理）"""
    global _local_server, _proxy_client
    
    if _local_server and _local_server.running:
        return _local_server
    if _proxy_client and _proxy_client.running:
        return _proxy_client
    return None
