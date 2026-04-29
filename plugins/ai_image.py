"""
AI 生图插件 - 基于 ai.2x.nz 自然语言生图接口
支持自然语言描述、直接 Tag、工作流切换、画风选择等
"""

import os
import json
import time
import threading
import hashlib
import re
from datetime import datetime
from urllib.parse import quote

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import websocket
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False


class Plugin:
    """AI 生图插件 - 调用 ai.2x.nz 接口生成图片"""

    BASE_URL = "https://ai.2x.nz"
    WS_URL = "wss://ai.2x.nz/ws/run"
    API_URL = "https://ai.2x.nz/api"

    # 保存目录
    DEFAULT_SAVE_DIR = "generated_images"

    def __init__(self):
        self.usage = """AI 生图工具 - 基于自然语言描述生成图片

基本用法:
  generate <描述>                     - 用自然语言描述生成图片
  tag <直接Tag>                       - 用 Danbooru Tag 生成图片
  both <Tag> <<<>>> <描述>            - 同时使用 Tag 和自然语言

高级用法:
  workflows                           - 列出所有可用工作流
  switch <工作流名>                   - 切换工作流
  width <数值>                        - 设置图片宽度 (最大1344)
  height <数值>                       - 设置图片高度 (最大1344)
  size <宽> <高>                      - 同时设置宽高
  rewrite on|off                      - 改写模式开关
  override on|off                     - 覆写模式开关
  status                              - 查看当前状态和配置

示例:
  ai_image generate 一个可爱的猫耳少女，樱花背景
  ai_image tag 1girl, cat_ears, cherry_blossoms, smile
  ai_image both 1girl, cat_ears <<<>>> 一个可爱的猫耳少女在樱花树下微笑
  ai_image workflows
  ai_image switch WAI - 37.json
  ai_image size 1024 1024
  ai_image rewrite on
"""
        self.cli = None
        self.save_dir = self.DEFAULT_SAVE_DIR

        # 配置状态
        self.current_workflow = None
        self.direct_prompt = ""
        self.nl_prompt = ""
        self.rewrite = False
        self.override = False
        self.width = None
        self.height = None
        self.workflows_cache = None
        self.is_generating = False

    def set_cli(self, cli):
        """设置 CLI 实例引用"""
        self.cli = cli
        # 注册插件命令
        if hasattr(cli, 'register_liugin_command'):
            cli.register_liugin_command('ai_image', self.command_handler)

    def get_tool_info(self):
        return {
            "name": "ai_image",
            "description": "AI 生图工具 — 基于 ai.2x.nz 接口，支持自然语言描述和 Danbooru Tag 生成图片。当用户想要生成图片、画图、AI绘画、生图时使用此工具。",
            "keywords": [
                "生图", "画图", "图片", "AI绘画", "生成图片", "image", "generate",
                "draw", "绘画", "插画", "二次元", "动漫", "Danbooru", "tag",
                "工作流", "workflow", "ComfyUI"
            ],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "ai_image",
            "description": "AI 生图工具，基于 ai.2x.nz 接口生成图片",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["generate", "tag", "both", "workflows", "switch", "size", "status"],
                        "description": "操作类型"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "生成提示词"
                    }
                },
                "required": ["operation"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        prompt = arguments.get("prompt", "")
        return f"{op} {prompt}"

    def command_handler(self, args):
        """处理 /ai_image 命令"""
        return self.handle(args)

    def handle(self, args):
        """处理 AI 生图请求"""
        if not REQUESTS_AVAILABLE:
            return "❌ 缺少 requests 库，请运行: pip install requests"

        args = args.strip()
        if not args:
            return self.usage

        # 解析操作
        parts = args.split(maxsplit=1)
        operation = parts[0].lower()
        remaining = parts[1] if len(parts) > 1 else ""

        try:
            if operation in ["generate", "gen", "g"]:
                return self._cmd_generate(remaining)
            elif operation in ["tag", "t", "direct", "d"]:
                return self._cmd_tag(remaining)
            elif operation in ["both", "b"]:
                return self._cmd_both(remaining)
            elif operation in ["workflows", "wf", "list"]:
                return self._cmd_workflows()
            elif operation in ["switch", "sw"]:
                return self._cmd_switch(remaining)
            elif operation in ["width", "w"]:
                return self._cmd_set_width(remaining)
            elif operation in ["height", "h"]:
                return self._cmd_set_height(remaining)
            elif operation in ["size", "s"]:
                return self._cmd_set_size(remaining)
            elif operation in ["rewrite", "rw"]:
                return self._cmd_set_rewrite(remaining)
            elif operation in ["override", "ov"]:
                return self._cmd_set_override(remaining)
            elif operation in ["status", "st"]:
                return self._cmd_status()
            elif operation in ["help", "?"]:
                return self.usage
            else:
                # 尝试当作自然语言描述处理
                return self._cmd_generate(args)
        except Exception as e:
            return f"❌ 操作失败: {str(e)}"

    # ── 命令实现 ──

    def _cmd_generate(self, prompt):
        """自然语言生成图片"""
        if not prompt.strip():
            return "❌ 请提供描述内容。示例: ai_image generate 一个可爱的猫耳少女"

        self.nl_prompt = prompt.strip()
        self.direct_prompt = ""
        self.override = False
        return self._run_generation()

    def _cmd_tag(self, tags):
        """使用直接 Tag 生成图片"""
        if not tags.strip():
            return "❌ 请提供 Tag 内容。示例: ai_image tag 1girl, cat_ears, smile"

        self.direct_prompt = tags.strip()
        self.nl_prompt = ""
        self.override = True
        return self._run_generation()

    def _cmd_both(self, args):
        """同时使用 Tag 和自然语言"""
        if "<<<>>>" in args:
            parts = args.split("<<<>>>", 1)
            self.direct_prompt = parts[0].strip()
            self.nl_prompt = parts[1].strip()
        else:
            # 尝试用 || 分隔
            if "||" in args:
                parts = args.split("||", 1)
                self.direct_prompt = parts[0].strip()
                self.nl_prompt = parts[1].strip()
            else:
                return "❌ 格式错误。用法: ai_image both <Tag> <<<>>> <描述>"

        self.override = False
        return self._run_generation()

    def _cmd_workflows(self):
        """列出所有工作流"""
        workflows = self._fetch_workflows()
        if not workflows:
            return "❌ 获取工作流列表失败"

        result = f"📂 共 {len(workflows)} 个工作流:\n\n"
        for i, wf in enumerate(workflows, 1):
            name = wf.get("path", "未知")
            current = " ← [当前]" if name == self.current_workflow else ""
            result += f"  {i:2d}. {name}{current}\n"

        result += f"\n💡 使用 'ai_image switch <工作流名>' 切换工作流"
        return result

    def _cmd_switch(self, name):
        """切换工作流"""
        if not name.strip():
            return "❌ 请提供工作流名称。先用 'ai_image workflows' 查看列表"

        # 模糊匹配
        workflows = self._fetch_workflows()
        if not workflows:
            return "❌ 获取工作流列表失败"

        matched = None
        name_lower = name.strip().lower()
        for wf in workflows:
            wf_path = wf.get("path", "")
            if name_lower == wf_path.lower():
                matched = wf_path
                break
            if name_lower in wf_path.lower():
                matched = wf_path

        if not matched:
            # 尝试数字索引
            try:
                idx = int(name.strip()) - 1
                if 0 <= idx < len(workflows):
                    matched = workflows[idx].get("path", "")
            except ValueError:
                pass

        if not matched:
            return f"❌ 未找到匹配的工作流: {name}\n💡 先用 'ai_image workflows' 查看列表"

        self.current_workflow = matched
        return f"✅ 已切换工作流: {matched}"

    def _cmd_set_width(self, val):
        """设置宽度"""
        try:
            w = int(val.strip())
            if w < 64 or w > 1344:
                return "❌ 宽度范围: 64 ~ 1344"
            self.width = w
            return f"✅ 宽度已设置为: {w}"
        except ValueError:
            return "❌ 请输入有效数字"

    def _cmd_set_height(self, val):
        """设置高度"""
        try:
            h = int(val.strip())
            if h < 64 or h > 1344:
                return "❌ 高度范围: 64 ~ 1344"
            self.height = h
            return f"✅ 高度已设置为: {h}"
        except ValueError:
            return "❌ 请输入有效数字"

    def _cmd_set_size(self, val):
        """同时设置宽高"""
        parts = val.strip().split()
        if len(parts) < 2:
            return "❌ 用法: ai_image size <宽> <高>"
        try:
            w, h = int(parts[0]), int(parts[1])
            if w < 64 or w > 1344 or h < 64 or h > 1344:
                return "❌ 宽高范围: 64 ~ 1344"
            self.width = w
            self.height = h
            return f"✅ 尺寸已设置为: {w} x {h}"
        except ValueError:
            return "❌ 请输入有效数字"

    def _cmd_set_rewrite(self, val):
        """设置改写模式"""
        val = val.strip().lower()
        if val in ["on", "开", "1", "true", "yes"]:
            self.rewrite = True
            return "✅ 改写模式已开启 — LLM 将智能重写 prompt"
        elif val in ["off", "关", "0", "false", "no"]:
            self.rewrite = False
            return "✅ 改写模式已关闭 — 普通翻译/追加模式"
        else:
            self.rewrite = not self.rewrite
            status = "开启" if self.rewrite else "关闭"
            return f"✅ 改写模式已{status}"

    def _cmd_set_override(self, val):
        """设置覆写模式"""
        val = val.strip().lower()
        if val in ["on", "开", "1", "true", "yes"]:
            self.override = True
            return "✅ 覆写模式已开启 — 忽略工作流内置 prompt"
        elif val in ["off", "关", "0", "false", "no"]:
            self.override = False
            return "✅ 覆写模式已关闭 — 保留工作流内置 prompt"
        else:
            self.override = not self.override
            status = "开启" if self.override else "关闭"
            return f"✅ 覆写模式已{status}"

    def _cmd_status(self):
        """查看当前状态"""
        result = " AI 生图状态:\n\n"
        result += f"  工作流: {self.current_workflow or '(默认)'}\n"
        result += f"  直接 Tag: {self.direct_prompt or '(未设置)'}\n"
        result += f"  自然语言: {self.nl_prompt or '(未设置)'}\n"
        result += f"  改写模式: {'✅ 开启' if self.rewrite else '❌ 关闭'}\n"
        result += f"  覆写模式: {'✅ 开启' if self.override else '❌ 关闭'}\n"
        result += f"  宽度: {self.width or '(默认)'}\n"
        result += f"  高度: {self.height or '(默认)'}\n"
        result += f"  保存目录: {self.save_dir}\n"
        result += f"  生成中: {'是' if self.is_generating else '否'}\n"
        return result

    # ── 核心生图逻辑 ──

    def _fetch_workflows(self):
        """获取工作流列表"""
        if self.workflows_cache:
            return self.workflows_cache

        try:
            resp = requests.get(f"{self.API_URL}/workflows", timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                self.workflows_cache = data.get("workflows", [])
                return self.workflows_cache
        except Exception as e:
            pass
        return []

    def _run_generation(self):
        """执行图片生成"""
        if self.is_generating:
            return "⚠️ 已有生成任务在进行中，请等待完成"

        if not self.direct_prompt and not self.nl_prompt:
            return "❌ 请提供至少一种 prompt（直接 Tag 或自然语言描述）"

        self.is_generating = True
        result_lines = []
        image_paths = []

        try:
            # 获取默认工作流（如果未指定则使用列表中第一个）
            workflow = self.current_workflow
            if not workflow:
                workflows = self._fetch_workflows()
                if workflows:
                    # 优先选 "无Lora" 工作流，否则用第一个
                    for wf in workflows:
                        if "无lora" in wf.get("path", "").lower():
                            workflow = wf["path"]
                            break
                    if not workflow:
                        workflow = workflows[0].get("path", "")

            # 构建 payload
            payload = {
                "workflow_path": workflow or "",
                "inline_workflow": None,
                "direct_prompt": self.direct_prompt,
                "nl_prompt": self.nl_prompt,
                "rewrite": self.rewrite,
                "override": self.override,
                "width": self.width,
                "height": self.height,
            }

            result_lines.append("  正在连接 ai.2x.nz ...")
            result_lines.append(f"  直接 Tag: {self.direct_prompt[:80] or '(无)'}")
            result_lines.append(f"  自然语言: {self.nl_prompt[:80] or '(无)'}")
            result_lines.append(f"  工作流: {workflow or '(默认)'}")
            result_lines.append("")

            # 使用同步方式通过 REST + 轮询获取结果
            # 由于 websocket-client 可能未安装，提供降级方案
            if WEBSOCKET_AVAILABLE:
                images = self._generate_via_ws(payload, result_lines)
            else:
                # 降级：尝试使用 requests + SSE 或提示安装
                result_lines.append("⚠️ websocket-client 未安装，尝试安装...")
                images = self._generate_via_ws_fallback(payload, result_lines)

            if images:
                image_paths = images
                result_lines.append(f"\n✅ 生成完成！共 {len(images)} 张图片")
                for i, path in enumerate(images, 1):
                    result_lines.append(f"   {i}. {path}")
            else:
                result_lines.append("\n❌ 未生成任何图片")

        except Exception as e:
            result_lines.append(f"\n❌ 生成失败: {str(e)}")
        finally:
            self.is_generating = False

        return "\n".join(result_lines)

    def _generate_via_ws(self, payload, result_lines):
        """通过 WebSocket 生成图片"""
        images = []
        final_prompt = ""
        error_msg = None

        ws_result = {"images": [], "error": None, "final_prompt": "", "done": False}

        def on_message(ws, message):
            try:
                m = json.loads(message)
                msg_type = m.get("type", "")

                if msg_type == "log":
                    result_lines.append(f"  {m.get('message', '')}")
                elif msg_type == "llm_start":
                    result_lines.append(" LLM 正在处理 prompt...")
                elif msg_type == "llm_chunk":
                    pass  # 流式输出，不逐块显示
                elif msg_type == "llm_done":
                    result_lines.append(" LLM 处理完成")
                elif msg_type == "progress":
                    node = m.get("node", "")
                    value = m.get("value", 0)
                    max_val = m.get("max", 0)
                    if max_val and max_val > 1:
                        pct = int(value * 100 / max_val)
                        result_lines.append(f"⏳ 进度: {node} {value}/{max_val} ({pct}%)")
                    else:
                        result_lines.append(f"⏳ 执行: {node}")
                elif msg_type == "prompt_id":
                    fp = m.get("final_prompt", "")
                    if fp:
                        ws_result["final_prompt"] = fp
                        result_lines.append(f"\n  最终 Prompt:\n{fp[:300]}{'...' if len(fp) > 300 else ''}\n")
                elif msg_type == "image":
                    url = m.get("url", "")
                    filename = m.get("filename", "")
                    if url:
                        # 下载图片
                        saved = self._download_image(url, filename)
                        if saved:
                            ws_result["images"].append(saved)
                            result_lines.append(f"  收到图片: {filename}")
                elif msg_type == "done":
                    count = m.get("count", 0)
                    result_lines.append(f"✅ 服务端完成，共 {count} 张")
                    ws_result["done"] = True
                    ws.close()
                elif msg_type == "error":
                    ws_result["error"] = m.get("message", "未知错误")
                    result_lines.append(f"❌ 错误: {ws_result['error']}")
                    ws.close()
            except Exception as e:
                result_lines.append(f"⚠️ 解析消息出错: {e}")

        def on_error(ws, error):
            ws_result["error"] = str(error)
            result_lines.append(f"❌ WebSocket 错误: {error}")

        def on_close(ws, close_status_code, close_msg):
            ws_result["done"] = True

        def on_open(ws):
            ws.send(json.dumps(payload))

        try:
            ws = websocket.WebSocketApp(
                self.WS_URL,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )

            # 在独立线程中运行 WebSocket
            ws_thread = threading.Thread(target=ws.run_forever, kwargs={"ping_timeout": 10})
            ws_thread.daemon = True
            ws_thread.start()

            # 等待完成（最多 5 分钟）
            timeout = 300
            start = time.time()
            while not ws_result["done"] and (time.time() - start) < timeout:
                time.sleep(1)

            if ws_result["error"]:
                raise Exception(ws_result["error"])

            if not ws_result["done"]:
                ws.close()
                raise Exception("生成超时（超过 5 分钟）")

            return ws_result["images"]

        except Exception as e:
            raise Exception(f"WebSocket 连接失败: {e}")

    def _generate_via_ws_fallback(self, payload, result_lines):
        """降级方案：尝试自动安装 websocket-client"""
        try:
            import subprocess
            result_lines.append("  正在安装 websocket-client ...")
            subprocess.run(
                ["pip", "install", "websocket-client"],
                capture_output=True, timeout=60
            )
            import importlib
            global websocket
            websocket = importlib.import_module("websocket")
            global WEBSOCKET_AVAILABLE
            WEBSOCKET_AVAILABLE = True
            result_lines.append("✅ websocket-client 安装成功")
            return self._generate_via_ws(payload, result_lines)
        except Exception as e:
            result_lines.append(f"❌ 无法安装 websocket-client: {e}")
            result_lines.append("💡 请手动运行: pip install websocket-client")
            return []

    def _download_image(self, url, filename):
        """下载图片到本地"""
        try:
            # 确保 URL 是完整的
            if url.startswith("/"):
                url = f"{self.BASE_URL}{url}"
            elif not url.startswith("http"):
                url = f"{self.BASE_URL}/api/output/file?path={quote(url)}"

            # 创建保存目录
            os.makedirs(self.save_dir, exist_ok=True)

            # 生成文件名
            if not filename:
                filename = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

            # 清理文件名
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            save_path = os.path.join(self.save_dir, filename)

            # 如果文件已存在，添加序号
            if os.path.exists(save_path):
                name, ext = os.path.splitext(filename)
                for i in range(1, 100):
                    new_path = os.path.join(self.save_dir, f"{name}_{i}{ext}")
                    if not os.path.exists(new_path):
                        save_path = new_path
                        break

            # 下载
            resp = requests.get(url, timeout=60, stream=True)
            if resp.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                return save_path
            else:
                return None

        except Exception as e:
            return None


# 兼容 Liugin 类名
Liugin = Plugin
