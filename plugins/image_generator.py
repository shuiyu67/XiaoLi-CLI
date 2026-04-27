"""
图像生成插件 - 基于 ai.2x.nz 的 ComfyUI 在线服务
支持自然语言描述和英文 Tag 两种模式
"""
import os
import json
import asyncio
import urllib.request
import time
from typing import Optional


class Plugin:
    """图像生成工具 — 自然语言/Tag 生图，基于 ComfyUI 在线服务"""

    def __init__(self):
        self.usage = """图像生成工具 — 基于 ai.2x.nz 的 ComfyUI 在线服务

操作:
  generate <描述>                 - 自然语言描述生成图片（中文/英文均可）
  tag <英文tags>                  - 直接 Tag 模式（逗号分隔的英文标签）
  list                            - 列出可用的工作流/角色
  status                          - 查看 GPU 状态

示例:
  image_generator generate 一个白发蓝眼的猫耳少女在写代码
  image_generator tag masterpiece, 1girl, white hair, blue eyes, cat ears, coding
  image_generator generate 画一个赛博朋克风格的城市夜景 --width 1024 --height 768

说明:
  - 自然语言模式会经过 LLM 翻译为 Tag，效果更好
  - 直接 Tag 模式适合熟悉 Danbooru 标签的用户
  - 默认分辨率 1024x1344（WAI 推荐）
  - 最大分辨率 1344x1344
  - 生成的图片保存在 screenshots/ 目录
"""
        self.cli = None
        self.api_base = "https://ai.2x.nz"
        self.ws_url = "wss://ai.2x.nz/ws/run"
        self.default_workflow = "WAI - 无Lora.json"
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "screenshots")

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "image_generator",
            "description": "图像生成 — 自然语言/Tag 生图，基于 ComfyUI 在线服务（ai.2x.nz），支持中文描述",
            "keywords": ["图像", "生成", "画图", "绘图", "AI画", "生图", "image", "generate", "draw", "paint",
                         "diffusion", "comfyui", "stable", "sd", "文生图", "text2img"],
            "usage": self.usage
        }

    def handle(self, args: str) -> str:
        try:
            parts = args.strip().split(maxsplit=1)
            if not parts:
                return "错误：请提供操作类型\n\n" + self.usage

            op = parts[0].lower()
            rest = parts[1] if len(parts) > 1 else ""

            handlers = {
                "generate": self._generate,
                "tag": self._generate_tag,
                "gen": self._generate,
                "g": self._generate,
                "list": self._list_workflows,
                "ls": self._list_workflows,
                "status": self._gpu_status,
            }

            handler = handlers.get(op)
            if not handler:
                # 如果没有指定操作，把整个 args 当作自然语言描述
                return self._generate(args)

            return handler(rest)

        except Exception as e:
            return f"图像生成错误: {e}"

    def _generate(self, args: str) -> str:
        """自然语言模式生成图片"""
        # 解析 --width 和 --height 参数
        width, height = 1024, 1344
        prompt = args.strip()

        if "--width" in prompt or "--height" in prompt or "--w" in prompt or "--h" in prompt:
            import re
            w_match = re.search(r'--w(?:idth)?\s+(\d+)', prompt)
            h_match = re.search(r'--h(?:eight)?\s+(\d+)', prompt)
            if w_match:
                width = int(w_match.group(1))
                prompt = prompt[:w_match.start()] + prompt[w_match.end():]
            if h_match:
                height = int(h_match.group(1))
                prompt = prompt[:h_match.start()] + prompt[h_match.end():]
            prompt = prompt.strip()

        if not prompt:
            return "错误：请提供图片描述\n示例: image_generator generate 一个白发猫耳少女"

        # 限制分辨率
        width = min(width, 1344)
        height = min(height, 1344)

        return self._run_generation(prompt, "", width, height, rewrite=True, override=False)

    def _generate_tag(self, args: str) -> str:
        """直接 Tag 模式"""
        width, height = 1024, 1344
        prompt = args.strip()

        if "--width" in prompt or "--height" in prompt or "--w" in prompt or "--h" in prompt:
            import re
            w_match = re.search(r'--w(?:idth)?\s+(\d+)', prompt)
            h_match = re.search(r'--h(?:eight)?\s+(\d+)', prompt)
            if w_match:
                width = int(w_match.group(1))
                prompt = prompt[:w_match.start()] + prompt[w_match.end():]
            if h_match:
                height = int(h_match.group(1))
                prompt = prompt[:h_match.start()] + prompt[h_match.end():]
            prompt = prompt.strip()

        if not prompt:
            return "错误：请提供 Tag\n示例: image_generator tag masterpiece, 1girl, white hair, blue eyes"

        width = min(width, 1344)
        height = min(height, 1344)

        return self._run_generation("", prompt, width, height, rewrite=False, override=False)

    def _run_generation(self, nl_prompt: str, direct_prompt: str, width: int, height: int,
                        rewrite: bool = False, override: bool = False) -> str:
        """执行图像生成（同步包装）"""
        try:
            import websocket as ws_lib
        except ImportError:
            # 回退：用 urllib 的方式不行，WebSocket 必须用专用库
            # 尝试用 subprocess 调用 python 脚本
            return self._run_generation_subprocess(nl_prompt, direct_prompt, width, height, rewrite, override)

        try:
            start_time = time.time()
            ws = ws_lib.create_connection(self.ws_url, timeout=180)

            payload = {
                "workflow_path": self.default_workflow,
                "inline_workflow": None,
                "direct_prompt": direct_prompt,
                "nl_prompt": nl_prompt,
                "rewrite": rewrite,
                "override": override,
                "width": width,
                "height": height,
            }
            ws.send(json.dumps(payload))

            image_path = None
            final_prompt = ""
            error_msg = ""

            while True:
                try:
                    raw = ws.recv()
                    data = json.loads(raw)
                    msg_type = data.get("type", "")

                    if msg_type == "image":
                        url = data.get("url", "")
                        filename = data.get("filename", "")
                        if url:
                            image_path = self._download_image(url, filename)
                    elif msg_type == "final_prompt":
                        final_prompt = data.get("final_prompt", "") if isinstance(data.get("final_prompt"), str) else data.get("prompt", "")
                    elif msg_type == "done":
                        break
                    elif msg_type == "error":
                        error_msg = data.get("message", "未知错误")
                        break
                except Exception as e:
                    error_msg = str(e)
                    break

            ws.close()
            elapsed = time.time() - start_time

            if error_msg:
                return f"  生成失败: {error_msg}"

            if image_path:
                size = os.path.getsize(image_path)
                size_str = f"{size/1024:.0f}KB" if size < 1024*1024 else f"{size/1024/1024:.1f}MB"
                result = f"  图片生成成功！\n"
                result += f"  路径: {image_path}\n"
                result += f"  大小: {size_str}\n"
                result += f"  分辨率: {width}x{height}\n"
                result += f"⏱  耗时: {elapsed:.1f}s\n"
                if final_prompt:
                    result += f"  Prompt: {final_prompt[:120]}...\n"
                result += f"\n💡 提示: 用 'send_image {image_path}' 可以推送到手机"
                return result
            else:
                return "  生成完成但未收到图片数据"

        except Exception as e:
            return f"  连接失败: {e}\n💡 请检查网络连接或稍后重试"

    def _run_generation_subprocess(self, nl_prompt: str, direct_prompt: str, width: int, height: int,
                                    rewrite: bool, override: bool) -> str:
        """用子进程执行 WebSocket 生成（无需 websocket 库）"""
        import subprocess
        import tempfile

        script = f'''
import json, asyncio, urllib.request, os, sys

async def main():
    try:
        import websockets
    except ImportError:
        print("ERROR:需要安装 websockets: pip install websockets")
        sys.exit(1)

    uri = "wss://ai.2x.nz/ws/run"
    async with websockets.connect(uri) as ws:
        payload = {{
            "workflow_path": "{self.default_workflow}",
            "inline_workflow": None,
            "direct_prompt": {json.dumps(direct_prompt)},
            "nl_prompt": {json.dumps(nl_prompt)},
            "rewrite": {"true" if rewrite else "false"},
            "override": {"true" if override else "false"},
            "width": {width},
            "height": {height},
        }}
        await ws.send(json.dumps(payload))

        image_url = None
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=180)
                data = json.loads(msg)
                t = data.get("type", "")
                if t == "image":
                    image_url = data.get("url", "")
                elif t == "done":
                    break
                elif t == "error":
                    print(f"ERROR:{{data.get('message','')}}")
                    break
            except asyncio.TimeoutError:
                print("ERROR:超时")
                break

    if image_url:
        full_url = f"https://ai.2x.nz{{image_url}}"
        out_path = os.path.join("{self.output_dir}", f"generated_{{os.path.basename(image_url)}}")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        urllib.request.urlretrieve(full_url, out_path)
        print(f"OK:{{out_path}}")

asyncio.run(main())
'''

        script_path = os.path.join(self.output_dir, "_gen_temp.py")
        os.makedirs(self.output_dir, exist_ok=True)
        with open(script_path, 'w') as f:
            f.write(script)

        try:
            result = subprocess.run(
                ["python3", script_path],
                capture_output=True, text=True, timeout=200
            )
            output = result.stdout.strip()

            if output.startswith("OK:"):
                image_path = output[3:]
                size = os.path.getsize(image_path)
                size_str = f"{size/1024:.0f}KB" if size < 1024*1024 else f"{size/1024/1024:.1f}MB"
                res = f"  图片生成成功！\n"
                res += f"  路径: {image_path}\n"
                res += f"  大小: {size_str}\n"
                res += f"  分辨率: {width}x{height}\n"
                res += f"\n💡 提示: 用 'send_image {image_path}' 可以推送到手机"
                return res
            elif output.startswith("ERROR:"):
                return f"  {output[6:]}"
            else:
                return f"  生成异常:\n{result.stdout}\n{result.stderr}"
        except subprocess.TimeoutExpired:
            return "  生成超时（>200s），请稍后重试"
        finally:
            try:
                os.remove(script_path)
            except:
                pass

    def _download_image(self, url: str, filename: str) -> str:
        """下载生成的图片"""
        full_url = f"{self.api_base}{url}"
        os.makedirs(self.output_dir, exist_ok=True)
        out_path = os.path.join(self.output_dir, f"gen_{filename}")
        urllib.request.urlretrieve(full_url, out_path)
        return out_path

    def _list_workflows(self, args: str) -> str:
        """列出可用的工作流"""
        try:
            import urllib.request
            req = urllib.request.Request(f"{self.api_base}/api/workflows")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())

            workflows = data.get("workflows", [])
            result = f"  可用工作流 ({len(workflows)} 个):\n\n"

            lora_workflows = []
            no_lora = []
            for w in workflows:
                name = w.get("path", "")
                if "无Lora" in name or "no" in name.lower():
                    no_lora.append(name)
                else:
                    lora_workflows.append(name)

            if no_lora:
                result += "  通用（无角色绑定）:\n"
                for w in no_lora:
                    result += f"    • {w}\n"

            if lora_workflows:
                result += "\n  角色工作流:\n"
                for w in lora_workflows:
                    result += f"    • {w}\n"

            result += "\n💡 使用 'image_generator generate <描述>' 自然语言生图"
            result += "\n💡 使用 'image_generator tag <tags>' 直接 Tag 生图"
            return result

        except Exception as e:
            return f"  获取工作流列表失败: {e}"

    def _gpu_status(self, args: str) -> str:
        """查看 GPU 状态"""
        try:
            import urllib.request
            req = urllib.request.Request(f"{self.api_base}/api/gpu")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())

            result = "  服务器 GPU 状态:\n"
            for gpu in data.get("gpus", []):
                name = gpu.get("name", "未知")
                util = gpu.get("utilization", 0)
                mem_used = gpu.get("memory_used", 0)
                mem_total = gpu.get("memory_total", 0)
                temp = gpu.get("temperature", 0)
                result += f"  {name}\n"
                result += f"    GPU 负载: {util}%\n"
                result += f"    显存: {mem_used}/{mem_total} MiB\n"
                result += f"    温度: {temp}°C\n"
            return result

        except Exception as e:
            return f"  获取 GPU 状态失败: {e}"
