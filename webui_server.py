#!/usr/bin/env python3
"""
小狸 Pro-CLI Web UI 后端
WebSocket 服务器 + 静态文件服务

启动:
  python webui_server.py [--port 8080] [--host 0.0.0.0]

依赖:
  pip install websockets
"""

import asyncio
import json
import os
import sys
import time
import argparse
import mimetypes
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

# 添加项目根目录
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("⚠️  websockets 未安装，WebSocket 功能不可用")
    print("   安装: pip install websockets")


# ═══════════════════════════════════════════
#  AI 引擎桥接
# ═══════════════════════════════════════════

class AIEngineBridge:
    """桥接到小狸的 AI 引擎和插件系统"""

    def __init__(self):
        self.cli = None
        self._initialized = False

    def initialize(self):
        """延迟初始化小狸核心"""
        if self._initialized:
            return True
        try:
            from xcli_core import AICLI
            self.cli = AICLI()
            self._initialized = True
            return True
        except Exception as e:
            print(f"⚠️  小狸核心初始化失败: {e}")
            return False

    def get_status(self):
        """获取系统状态"""
        if not self.cli:
            return {
                "engine": "未连接",
                "engine_type": "none",
                "plugins": 0,
                "operations": 0,
                "safety_mode": "普通",
                "tools": [],
                "engines": [],
            }

        engine_name = getattr(self.cli.current_engine, 'name', '未知') if self.cli.current_engine else '无'
        tools = []
        if hasattr(self.cli, 'liugin_manager') and self.cli.liugin_manager:
            for t in self.cli.liugin_manager.tools:
                tools.append({
                    "name": t.get('name', ''),
                    "description": t.get('description', ''),
                    "ops": len(t.get('usage', '').split('\n')) if t.get('usage') else 0,
                })

        from xcli_core.safety import get_safety
        safety = get_safety()

        return {
            "engine": engine_name,
            "engine_type": "local" if engine_name == "ollama" else "cloud",
            "plugins": len(tools),
            "operations": sum(t.get('ops', 0) for t in tools),
            "safety_mode": safety.get_mode_name(),
            "tools": tools,
            "engines": list(self.cli.engines.keys()) if self.cli.engines else [],
        }

    def chat(self, message: str, callback=None):
        """发送消息到 AI 并获取回复（支持工具调用循环）"""
        if not self.cli:
            return {"type": "error", "message": "小狸核心未初始化，请检查配置"}

        results = []  # 收集所有事件

        try:
            # 添加用户消息到历史
            self.cli.shared_conversation_history.append({
                "role": "user", "content": message
            })

            liugin_prompts = self.cli.get_liugin_usage_prompts()
            system_prompt = self.cli._build_system_prompt(liugin_prompts)

            loop_count = 0
            max_loops = 15
            current_input = message

            while loop_count < max_loops:
                # 生成 AI 响应
                if not self.cli.current_engine:
                    return {"type": "error", "message": "没有可用的 AI 引擎"}

                response = self.cli.current_engine.generate_response(
                    current_input, system_prompt=system_prompt
                )

                if not response:
                    return {"type": "reply", "message": "(无响应)"}

                # 检查 FC 响应（Ollama Function Calling）
                fc_result = self.cli._handle_fc_response(response, message)
                if fc_result:
                    # FC 工具已执行，结果作为下一轮输入
                    results.append({"type": "fc_tool_done", "message": fc_result[:200]})
                    current_input = fc_result
                    loop_count += 1
                    continue

                # 解析混合响应（文本 + JSON 工具调用）
                try:
                    text_content, json_data = self.cli._parse_mixed_response(response)
                except Exception:
                    text_content, json_data = response, None

                if json_data and isinstance(json_data, dict):
                    if json_data.get('action') == 'use_tool':
                        tool_name = json_data.get('tool', '')
                        tool_args = json_data.get('args', '')
                        results.append({"type": "tool_call", "name": tool_name, "args": tool_args[:200]})

                        # 执行工具
                        try:
                            tool_result = self.cli._execute_tool_by_name(tool_name, tool_args)
                        except Exception as e:
                            tool_result = f"工具执行错误: {e}"

                        results.append({"type": "tool_result", "name": tool_name, "result": str(tool_result)[:500]})

                        # 把工具结果加入历史并继续循环
                        self.cli.shared_conversation_history.append({
                            "role": "tool", "content": str(tool_result),
                            "name": tool_name
                        })
                        current_input = f"工具 {tool_name} 的执行结果:\n{tool_result}"
                        loop_count += 1
                        continue

                    elif json_data.get('continue') or json_data.get('need_continue'):
                        msg = json_data.get('message', text_content or '')
                        if msg:
                            results.append({"type": "partial_reply", "message": msg})
                            self.cli.shared_conversation_history.append({"role": "assistant", "content": msg})
                            current_input = "继续"
                            loop_count += 1
                            continue

                    elif json_data.get('message'):
                        final = json_data.get('message')
                        self.cli.shared_conversation_history.append({"role": "assistant", "content": final})
                        results.append({"type": "reply", "message": final})
                        break

                # 纯文本响应
                display = text_content if text_content else response
                self.cli.shared_conversation_history.append({"role": "assistant", "content": display})
                results.append({"type": "reply", "message": display})
                break

            if not results:
                results.append({"type": "reply", "message": response or "(无响应)"})

            return {"type": "multi", "events": results}

        except Exception as e:
            return {"type": "error", "message": f"错误: {e}"}

    def execute_tool(self, tool_name: str, tool_args: str):
        """直接执行工具"""
        if not self.cli:
            return "❌ 小狸核心未初始化"

        try:
            result = self.cli._execute_tool_by_name(tool_name, tool_args)
            return result or "(无结果)"
        except Exception as e:
            return f"❌ 工具执行错误: {e}"

    def list_tools(self):
        """列出所有工具"""
        if not self.cli or not hasattr(self.cli, 'liugin_manager'):
            return []
        return [
            {
                "name": t.get('name', ''),
                "description": t.get('description', ''),
                "keywords": t.get('keywords', []),
            }
            for t in self.cli.liugin_manager.tools
        ]


# ═══════════════════════════════════════════
#  WebSocket 处理
# ═══════════════════════════════════════════

bridge = AIEngineBridge()
connected_clients = set()


async def ws_handler(websocket):
    """处理 WebSocket 连接"""
    connected_clients.add(websocket)
    client_addr = websocket.remote_address
    print(f"✅ 客户端已连接: {client_addr}")

    try:
        # 发送初始状态
        status = bridge.get_status()
        await websocket.send(json.dumps({
            "type": "status",
            "data": status,
        }, ensure_ascii=False))

        async for raw_message in websocket:
            try:
                msg = json.loads(raw_message)
                msg_type = msg.get("type", "")
                msg_data = msg.get("data", {})

                if msg_type == "chat":
                    # 用户聊天消息
                    user_msg = msg_data.get("message", "").strip()
                    if not user_msg:
                        continue

                    # 发送"正在思考"状态
                    await websocket.send(json.dumps({
                        "type": "thinking",
                        "data": {"message": user_msg},
                    }, ensure_ascii=False))

                    # 在线程中执行 AI 调用（避免阻塞事件循环）
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, bridge.chat, user_msg
                    )

                    # 处理返回结果
                    if isinstance(result, dict):
                        if result.get("type") == "multi":
                            # 多事件：逐个发送
                            for event in result.get("events", []):
                                await websocket.send(json.dumps({
                                    "type": event.get("type", "reply"),
                                    "data": event,
                                }, ensure_ascii=False))
                        else:
                            await websocket.send(json.dumps({
                                "type": result.get("type", "reply"),
                                "data": result,
                            }, ensure_ascii=False))
                    else:
                        # 兼容旧格式
                        await websocket.send(json.dumps({
                            "type": "reply",
                            "data": {"message": str(result)},
                        }, ensure_ascii=False))

                elif msg_type == "tool":
                    # 直接工具调用
                    tool_name = msg_data.get("name", "")
                    tool_args = msg_data.get("args", "")

                    await websocket.send(json.dumps({
                        "type": "tool_executing",
                        "data": {"name": tool_name, "args": tool_args},
                    }, ensure_ascii=False))

                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, bridge.execute_tool, tool_name, tool_args
                    )

                    await websocket.send(json.dumps({
                        "type": "tool_result",
                        "data": {"name": tool_name, "result": result},
                    }, ensure_ascii=False))

                elif msg_type == "status":
                    # 请求状态更新
                    status = bridge.get_status()
                    await websocket.send(json.dumps({
                        "type": "status",
                        "data": status,
                    }, ensure_ascii=False))

                elif msg_type == "tools":
                    # 请求工具列表
                    tools = bridge.list_tools()
                    await websocket.send(json.dumps({
                        "type": "tools",
                        "data": {"tools": tools},
                    }, ensure_ascii=False))

                elif msg_type == "switch_engine":
                    # 切换引擎
                    engine_name = msg_data.get("engine", "")
                    if bridge.cli and engine_name in bridge.cli.engines:
                        bridge.cli.switch_engine(engine_name)
                        await websocket.send(json.dumps({
                            "type": "engine_switched",
                            "data": {"engine": engine_name},
                        }, ensure_ascii=False))

                elif msg_type == "switch_safety":
                    # 切换安全模式
                    mode = msg_data.get("mode", "")
                    if bridge.cli:
                        from xcli_core.safety import get_safety, MODE_NORMAL, MODE_MANUAL, MODE_UNRESTRICTED
                        safety = get_safety()
                        if mode == "normal":
                            safety.set_mode(MODE_NORMAL)
                        elif mode == "manual":
                            safety.set_mode(MODE_MANUAL)
                        elif mode == "unrestricted":
                            safety.set_mode(MODE_UNRESTRICTED)
                        await websocket.send(json.dumps({
                            "type": "safety_switched",
                            "data": {"mode": safety.get_mode_name()},
                        }, ensure_ascii=False))

            except json.JSONDecodeError:
                await websocket.send(json.dumps({
                    "type": "error",
                    "data": {"message": "无效的 JSON 格式"},
                }, ensure_ascii=False))
            except Exception as e:
                await websocket.send(json.dumps({
                    "type": "error",
                    "data": {"message": str(e)},
                }, ensure_ascii=False))

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.discard(websocket)
        print(f"❌ 客户端已断开: {client_addr}")


# ═══════════════════════════════════════════
#  静态文件服务
# ═══════════════════════════════════════════

class WebUIHandler(SimpleHTTPRequestHandler):
    """自定义 HTTP 处理器"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PROJECT_DIR, **kwargs)

    def do_GET(self):
        # 根路径返回 webui.html
        if self.path == '/' or self.path == '/index.html':
            self.path = '/webui.html'
        return super().do_GET()

    def log_message(self, format, *args):
        # 静默日志
        pass


# ═══════════════════════════════════════════
#  启动
# ═══════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="小狸 Pro-CLI Web UI 服务器")
    parser.add_argument("--host", default="0.0.0.0", help="绑定地址")
    parser.add_argument("--port", type=int, default=8080, help="HTTP 端口")
    parser.add_argument("--ws-port", type=int, default=8079, help="WebSocket 端口")
    parser.add_argument("--no-ai", action="store_true", help="不初始化 AI 引擎（纯 UI 模式）")
    args = parser.parse_args()

    print()
    print("╔══════════════════════════════════════════╗")
    print("║       小狸 Pro-CLI · Web UI 服务器       ║")
    print("╚══════════════════════════════════════════╝")
    print()

    # 初始化 AI 引擎
    if not args.no_ai:
        print("⏳ 正在初始化小狸核心...")
        if bridge.initialize():
            status = bridge.get_status()
            print(f"✅ AI 引擎: {status['engine']}")
            print(f"✅ 插件: {status['plugins']} 个")
            print(f"✅ 安全模式: {status['safety_mode']}")
        else:
            print("⚠️  AI 引擎初始化失败，将以纯 UI 模式运行")
    else:
        print("ℹ️  纯 UI 模式（不连接 AI 引擎）")

    print()
    print(f"🌐 HTTP:      http://localhost:{args.port}")
    print(f"🔌 WebSocket: ws://localhost:{args.ws_port}")
    print(f"📂 项目目录:  {PROJECT_DIR}")
    print()
    print("按 Ctrl+C 停止服务器")
    print()

    # 启动 HTTP 服务器（在单独线程中）
    http_server = HTTPServer((args.host, args.port), WebUIHandler)
    http_thread = threading.Thread(target=http_server.serve_forever, daemon=True)
    http_thread.start()

    # 启动 WebSocket 服务器
    if WEBSOCKETS_AVAILABLE:
        async def run_ws():
            async with websockets.serve(ws_handler, args.host, args.ws_port):
                await asyncio.Future()  # 永远运行

        try:
            asyncio.run(run_ws())
        except KeyboardInterrupt:
            print("\n🛑 服务器已停止")
    else:
        print("⚠️  WebSocket 不可用，仅启动 HTTP 服务")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 服务器已停止")

    http_server.shutdown()


if __name__ == "__main__":
    main()
