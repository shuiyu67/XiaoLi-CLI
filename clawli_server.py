"""
Clawli WebSocket Server - 独立进程 WebSocket 服务器
用于 PC-手机端通信
"""

import multiprocessing
from multiprocessing import Process, Queue
from typing import Optional, List
import threading
import time
import json
import base64
import os
import asyncio


class ClawliWebSocketServer:
    """Clawli WebSocket 服务器管理类"""
    
    def __init__(self):
        self.process: Optional[Process] = None
        self.input_queue: Optional[Queue] = None
        self.output_queue: Optional[Queue] = None
        self.running = False
        self.host = "0.0.0.0"
        self.port = 9079
        self.password = ""
    
    def start(self, host: str = "0.0.0.0", port: int = 9079, password: str = "") -> bool:
        """启动 WebSocket 服务器进程"""
        if self.running:
            print("[Clawli] 服务器已在运行")
            return True
        
        self.host = host
        self.port = int(port)
        self.password = password
        
        self.input_queue = Queue()
        self.output_queue = Queue()
        
        self.process = Process(
            target=_ws_server_main,
            args=(self.host, self.port, self.password, self.input_queue, self.output_queue)
        )
        self.process.daemon = True
        self.process.start()
        self.running = True
        
        print(f"[Clawli] WebSocket 服务器已启动: ws://{host}:{self.port}")
        return True
    
    def stop(self):
        """停止服务器"""
        if not self.running:
            return
        
        self.running = False
        if self.process:
            self.process.terminate()
            self.process.join(timeout=2)
            if self.process.is_alive():
                self.process.kill()
            self.process = None
        
        self.input_queue = None
        self.output_queue = None
        print("[Clawli] WebSocket 服务器已停止")
    
    def send_message(self, content: str, msg_type: str = "text", **kwargs) -> tuple:
        """发送消息到手机"""
        if not self.running or not self.input_queue:
            print(f"[Clawli] 发送失败: 服务器未运行")
            return False, "服务器未运行"
        
        try:
            msg = {
                "type": msg_type,
                "content": content,
                "timestamp": time.time(),
                **kwargs
            }
            self.input_queue.put(msg)
            print(f"[Clawli] 消息已放入队列: type={msg_type}, len={len(content)}")
            return True, "消息已发送"
        except Exception as e:
            print(f"[Clawli] 发送异常: {e}")
            return False, f"发送失败: {e}"
    
    def send_image(self, image_path: str = None, image_data: str = None, 
                   filename: str = "", caption: str = "") -> tuple:
        """发送图片到手机"""
        if not self.running or not self.input_queue:
            return False, "服务器未运行"
        
        try:
            if image_path and os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    image_bytes = f.read()
                image_data = base64.b64encode(image_bytes).decode('utf-8')
                filename = filename or os.path.basename(image_path)
            
            if not image_data:
                return False, "无图片数据"
            
            msg = {
                "type": "image",
                "image": image_data,
                "filename": filename,
                "caption": caption,
                "timestamp": time.time()
            }
            self.input_queue.put(msg)
            print(f"[Clawli] 图片已放入队列: {filename}")
            return True, "图片已发送"
            
        except Exception as e:
            return False, f"发送失败: {e}"
    
    def send_tool_status(self, tool_name: str, args: str, status: str, result: str = ""):
        """发送工具状态"""
        return self.send_message(
            content=result,
            msg_type="tool_status",
            tool=tool_name,
            args=args,
            status=status,
            result=result
        )
    
    def get_messages(self) -> List[dict]:
        """获取从手机收到的消息"""
        messages = []
        if self.output_queue:
            while True:
                try:
                    msg = self.output_queue.get(timeout=0.01)
                    messages.append(msg)
                except:
                    break
        return messages
    
    def is_running(self) -> bool:
        return self.running and self.process is not None and self.process.is_alive()


def _ws_server_main(host: str, port: int, password: str, 
                    input_queue: Queue, output_queue: Queue):
    """WebSocket 服务器主进程"""
    import websockets
    from websockets.server import serve
    
    port = int(port)
    running = [True]  # 用列表包装以便在闭包中修改
    
    async def handler(websocket):
        """WebSocket 连接处理器"""
        # 认证
        try:
            auth_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            auth_data = json.loads(auth_msg)
            
            if auth_data.get("type") != "auth" or auth_data.get("password") != password:
                await websocket.send(json.dumps({"type": "auth_failed", "message": "密码错误"}))
                return
            
            await websocket.send(json.dumps({"type": "auth_success"}))
            print(f"[Clawli WS] 客户端认证成功")
            
        except Exception as e:
            print(f"[Clawli WS] 认证失败: {e}")
            return
        
        print(f"[Clawli WS] 开始处理消息循环")
        
        try:
            # 接收任务
            async def receiver():
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        output_queue.put(data)
                        print(f"[Clawli WS] 收到: {data.get('type', 'unknown')}")
                    except Exception as e:
                        print(f"[Clawli WS] 解析失败: {e}")
            
            # 发送任务
            async def sender():
                while running[0]:
                    try:
                        # 从队列获取消息（非阻塞）
                        msg = await asyncio.get_event_loop().run_in_executor(
                            None, lambda: input_queue.get(timeout=0.2)
                        )
                        await websocket.send(json.dumps(msg, ensure_ascii=False))
                        print(f"[Clawli WS] 发送: {msg.get('type', 'unknown')}")
                    except:
                        pass  # 超时，继续循环
            
            # 并行运行两个任务
            await asyncio.gather(receiver(), sender())
            
        except websockets.exceptions.ConnectionClosed:
            print("[Clawli WS] 客户端断开")
        except Exception as e:
            print(f"[Clawli WS] 连接错误: {e}")
    
    async def main():
        print(f"[Clawli WS] 服务器启动于 ws://{host}:{port}")
        async with serve(handler, host, port):
            await asyncio.Future()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        running[0] = False
        print("[Clawli WS] 服务器关闭")


# 全局实例
_server_instance = ClawliWebSocketServer()


def start_server(host: str = "0.0.0.0", port: int = 9079, password: str = "") -> bool:
    return _server_instance.start(host, port, password)


def stop_server():
    _server_instance.stop()


def send_message(content: str, msg_type: str = "text", **kwargs) -> tuple:
    return _server_instance.send_message(content, msg_type, **kwargs)


def send_image(image_path: str = None, image_data: str = None,
               filename: str = "", caption: str = "") -> tuple:
    return _server_instance.send_image(image_path, image_data, filename, caption)


def send_tool_status(tool_name: str, args: str, status: str, result: str = ""):
    return _server_instance.send_tool_status(tool_name, args, status, result)


def get_messages() -> List[dict]:
    return _server_instance.get_messages()


def is_running() -> bool:
    return _server_instance.is_running()


if __name__ == "__main__":
    start_server("0.0.0.0", 9079, "test")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_server()