import os
import sys
import json
import hashlib
import hmac
import base64
import websocket
import time
import threading
from datetime import datetime
from time import mktime
from urllib.parse import urlparse, urlencode
from wsgiref.handlers import format_date_time
from colorama import Fore, Style

# 获取项目根目录
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)


class XfyunSparkAI:
    """基于讯飞星火深度推理X2模型的AI引擎（WebSocket接口）"""
    requires_api_key = True  # 讯飞引擎需要API密钥

    # X2深度推理版本固定配置
    URL = "wss://spark-api.xf-yun.com/x2"
    DOMAIN = "spark-x"
    MAX_TOKENS = 131072  # X2输出上限128K

    def __init__(self):
        self.name = "xfyun-spark"
        self.cli = None

        # 直接从 config.json 读取配置
        config_file = os.path.join(project_root, "config.json")
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                engine_config = config.get("api", {}).get("engines", {}).get("xfyun_spark", {})
                self.app_id = engine_config.get("app_id", "")
                self.api_key = engine_config.get("api_key", "")
                self.api_secret = engine_config.get("api_secret", "")
                self.max_history = config.get("system", {}).get("max_history", 10)
        except Exception as e:
            self.app_id = ""
            self.api_key = ""
            self.api_secret = ""
            self.max_history = 10

        # 初始化对话历史
        self.conversation_history = []
        self.shared_conversation_history = None
        self.chat_id = f"chat_{self.app_id}_{int(time.time())}"  # 固定会话ID，确保上下文连续性

        # 验证API密钥
        if not self.app_id or not self.api_key or not self.api_secret:
            print(f"{Fore.YELLOW}警告: xfyun-spark引擎的API配置未完整设置（需要app_id、api_key、api_secret）{Style.RESET_ALL}")

    def get_help_info(self):
        """获取引擎帮助信息"""
        help_text = f"""
讯飞星火深度推理X2引擎帮助信息
================================

引擎名称: xfyun-spark
描述: 基于讯飞星火深度推理X2模型的AI引擎，支持WebSocket流式输出

版本: X2深度推理 (输入64K, 输出128K)

配置要求:
  在config.json中配置:
  {{
    "api": {{
      "engines": {{
        "xfyun_spark": {{
          "app_id": "你的应用ID",
          "api_key": "你的API Key",
          "api_secret": "你的API Secret"
        }}
      }}
    }}
  }}

使用说明:
1. 使用/engine.switch xfyun-spark切换到此引擎
2. 直接输入自然语言与AI对话
3. 本引擎强制使用流式输出，AI回复会实时显示
4. 支持深度思考模式，思考过程会自动显示

注意: 本引擎使用WebSocket协议，需要app_id、api_key、api_secret三个参数
"""
        return help_text

    def _generate_url(self):
        """生成鉴权URL（使用官方示例的方式）"""
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 解析URL获取host和path
        parsed_url = urlparse(self.URL)
        host = parsed_url.netloc
        path = parsed_url.path

        # 拼接签名字符串
        signature_origin = "host: " + host + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + path + " HTTP/1.1"

        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_origin.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()

        signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding='utf-8')

        # 拼接authorization_origin
        authorization_origin = f'api_key="{self.api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'

        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')

        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": host
        }

        # 拼接鉴权参数，生成url
        url = self.URL + '?' + urlencode(v)

        return url

    def _build_messages_with_history(self, system_prompt, user_input):
        """构建包含历史记录的消息列表（传递完整历史对话）"""
        messages = []

        # 添加系统提示词
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        # 添加完整的历史对话（不限制数量，让API自己处理）
        if self.shared_conversation_history:
            for msg in self.shared_conversation_history:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    role = msg["role"]
                    content = msg["content"]
                    # 转换角色名称
                    if role == "user":
                        messages.append({"role": "user", "content": content})
                    elif role == "assistant":
                        messages.append({"role": "assistant", "content": content})

        # 添加当前用户输入
        messages.append({
            "role": "user",
            "content": user_input
        })

        return messages

    def generate_response(self, user_input, tool_results=None, system_prompt=None):
        """生成AI响应（非流式）"""
        try:
            # 处理工具结果
            if tool_results:
                tool_result_text = f"工具执行结果: {tool_results.get('result', '无结果')}"
                messages = self._build_messages_with_history(system_prompt, tool_result_text)
            else:
                messages = self._build_messages_with_history(system_prompt, user_input)

            # 构建请求数据
            request_data = {
                "header": {
                    "app_id": self.app_id,
                    "uid": str(time.time()).replace('.', '')[:32]
                },
                "parameter": {
                    "chat": {
                        "domain": self.DOMAIN,
                        "temperature": 0,
                        "max_tokens": 4096,
                        "presence_penalty": 1,
                        "frequency_penalty": 0.02,
                        "top_k": 5,
                        "chat_id": self.chat_id
                    }
                },
                "payload": {
                    "message": {
                        "text": messages
                    }
                }
            }

            # 生成鉴权URL
            auth_url = self._generate_url()

            # 收集完整响应
            full_response = ""
            thinking_content = ""
            ws = None
            result_queue = []
            done_event = threading.Event()

            def on_message(ws, message):
                nonlocal full_response, thinking_content
                try:
                    data = json.loads(message)
                    code = data.get("header", {}).get("code", -1)

                    if code != 0:
                        result_queue.append(("error", data.get('header', {}).get('message', '未知错误')))
                        done_event.set()
                        return

                    payload = data.get("payload", {})
                    choices = payload.get("choices", {})

                    # 处理文本响应
                    text_list = choices.get("text", [])
                    if text_list:
                        reasoning = text_list[0].get("reasoning_content", "")
                        if reasoning:
                            thinking_content += reasoning
                        content = text_list[0].get("content", "")
                        if content:
                            full_response += content

                    if choices.get("status") == 2:
                        done_event.set()

                except Exception as e:
                    result_queue.append(("error", str(e)))
                    done_event.set()

            def on_error(ws, error):
                result_queue.append(("error", str(error)))
                done_event.set()

            def on_close(ws, close_status_code, close_msg):
                pass

            def on_open(ws):
                ws.send(json.dumps(request_data))

            # 创建WebSocket连接
            ws = websocket.WebSocketApp(
                auth_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )

            # 在后台线程运行WebSocket
            ws_thread = threading.Thread(target=ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()

            # 等待完成
            done_event.wait(timeout=60)

            # 返回完整响应
            return full_response

        except Exception as e:
            print(f"\n{Fore.RED}讯飞星火API调用失败: {str(e)}{Style.RESET_ALL}")
            return f"讯飞星火API调用失败: {str(e)}"