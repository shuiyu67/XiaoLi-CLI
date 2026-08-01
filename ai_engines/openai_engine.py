"""
OpenAI 兼容格式引擎
支持所有兼容 OpenAI API 格式的服务（如 DeepSeek、Grok、硅基流动、本地 vLLM 等）
"""

import os
import sys
import json
import requests
from colorama import Fore, Style
import logging

# 设置日志
logger = logging.getLogger(__name__)

try:
    from xcli_core.config import get_system_config
except Exception:
    def get_system_config(key, default=None):
        return default

# ── 常见模型的上下文窗口（token 数）──
# OpenAI /chat/completions 协议本身不返回模型窗口，需本地维护。
MODEL_CONTEXT_WINDOWS = {
    "gpt-4o": 128000, "gpt-4o-mini": 128000, "gpt-4": 8192, "gpt-4-turbo": 128000,
    "gpt-3.5-turbo": 16385,
    "deepseek-chat": 64000, "deepseek-reasoner": 64000,
    "qwen2.5": 32768, "qwen2": 32768, "qwen-max": 32768, "qwen-plus": 32768,
    "llama3": 8192, "llama3.1": 128000, "llama3.2": 128000, "llama2": 4096,
    "claude-3": 200000, "claude-3.5": 200000, "claude-3.7": 200000, "claude": 200000,
    "grok": 131072, "grok-2": 131072, "grok-3": 131072,
    "glm-4": 128000, "glm-4v": 128000,
    "mistral": 32768, "mixtral": 32768, "mistral-large": 128000,
    "gemini": 1000000, "gemini-1.5": 1000000, "gemini-2.0": 1000000, "gemini-2.5": 1000000,
    "yi": 200000, "yi-large": 200000,
    "kimi": 200000, "moonshot": 200000,
    "abab": 200000, "minimax": 200000,
    "baichuan": 192000, "chatglm": 32768,
}

# 添加项目根目录到sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)


class OpenaiAI:
    """OpenAI 兼容格式 AI 引擎 - 支持所有兼容 OpenAI API 的服务"""
    requires_api_key = True

    def get_help_info(self):
        """获取引擎帮助信息"""
        help_text = """
OpenAI 兼容格式引擎帮助信息
============================

引擎名称: openai
描述: 通用 OpenAI API 兼容引擎，支持所有兼容 OpenAI 格式的服务

支持的服务:
  - OpenAI 官方 API
  - DeepSeek API
  - Grok (xAI) API
  - 硅基流动 (SiliconFlow) API
  - 本地 vLLM / LiteLLM / OneAPI 等转发服务
  - 任何兼容 /chat/completions 接口的服务

配置方式 (config.json):
  {
    "api": {
      "engines": {
        "openai": {
          "api_key": "你的API密钥",
          "base_url": "https://api.openai.com/v1",
          "model": "gpt-4o"
        }
      }
    }
  }

可用命令:
  /engine.openai models       - 列出可用模型（需要服务端支持）
  /engine.openai set <模型名> - 切换模型
  /engine.openai info         - 显示当前配置信息

使用说明:
1. 在 config.json 中配置 api_key、base_url、model
2. 使用 /engine switch openai 切换到此引擎
3. 直接输入自然语言与 AI 对话

注意:
  - base_url 填写 API 的基础地址，无需包含 /chat/completions
  - 例如 OpenAI 官方填 https://api.openai.com/v1
  - 本地服务填 http://localhost:8000/v1
"""
        return help_text

    def __init__(self):
        self.name = "openai"
        self.cli = None

        # 从 config.json 读取配置
        config_file = os.path.join(project_root, "config.json")
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                engine_config = config.get("api", {}).get("engines", {}).get("openai", {})
                self.api_key = engine_config.get("api_key", "")
                self.base_url = engine_config.get("base_url", "").rstrip('/')
                self.model = engine_config.get("model", "")
                self.max_history = config.get("system", {}).get("max_history", 10)
        except Exception as e:
            logger.warning(f"读取配置文件失败: {e}")
            self.api_key = ""
            self.base_url = ""
            self.model = ""
            self.max_history = 10

        # 初始化对话历史
        self.conversation_history = []
        self.shared_conversation_history = None

        # 最近一次请求的 token 用量（供 token 感知压缩使用）
        self.last_prompt_tokens = None

        # 思考标记（兼容深度思考模型）
        self.thinking_start_marker = "<think>"
        self.thinking_end_marker = "</think>"

        # 检查配置
        if not self.api_key:
            print(f"{Fore.YELLOW}警告: openai 引擎的 API 密钥未设置{Style.RESET_ALL}")
        if not self.base_url:
            print(f"{Fore.YELLOW}警告: openai 引擎的 base_url 未设置{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}OpenAI 兼容引擎已启用 (base_url: {self.base_url}){Style.RESET_ALL}")

    def _get_headers(self):
        """构建请求头"""
        headers = {
            'Content-Type': 'application/json'
        }
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers

    def _get_api_url(self):
        """获取完整的 API 地址"""
        url = self.base_url
        if not url:
            return ""
        if not url.endswith('/chat/completions'):
            url = url.rstrip('/') + '/chat/completions'
        return url

    def generate_response(self, user_input, tool_results=None, system_prompt=None, tools=None):
        """
        生成 AI 响应

        Args:
            user_input: 用户输入
            tool_results: 工具执行结果
            system_prompt: 系统提示词
            tools: OpenAI FC 工具定义列表 (可选)
        """
        try:
            if not self.base_url:
                return "错误: openai 引擎的 base_url 未配置，请在 config.json 中设置"

            # 处理工具结果
            if tool_results:
                tool_result_text = f"工具执行结果: {tool_results.get('result', '无结果')}"
                messages = self._build_messages_with_history(system_prompt, tool_result_text)
            else:
                messages = self._build_messages_with_history(system_prompt, user_input)

            # 构建请求体
            body = {
                "model": self.model,
                "messages": messages,
                "stream": False
            }

            # ── Function Calling: 注入工具定义 ──
            if tools:
                body["tools"] = tools
                body["tool_choice"] = "auto"

            # 发送请求
            api_url = self._get_api_url()
            response = requests.post(
                url=api_url,
                json=body,
                headers=self._get_headers(),
                timeout=None
            )

            if response.status_code == 200:
                response_data = response.json()
                # ── 记录 token 用量（供 token 感知压缩）──
                usage = response_data.get("usage", {})
                if isinstance(usage, dict) and usage.get("prompt_tokens"):
                    try:
                        self.last_prompt_tokens = int(usage["prompt_tokens"])
                    except (TypeError, ValueError):
                        self.last_prompt_tokens = None
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    message = response_data["choices"][0].get("message", {})

                    # ── Function Calling: 检查 tool_calls ──
                    tool_calls_raw = message.get("tool_calls")
                    if tool_calls_raw:
                        # 返回 FC 结果（由调用方处理工具执行）
                        from xcli_core.fc_tools import parse_fc_response
                        fc_calls = parse_fc_response(response_data)
                        if fc_calls:
                            # 返回一个特殊的 JSON 字符串，标记为 FC 调用
                            return json.dumps({
                                "_fc": True,
                                "tool_calls": fc_calls,
                                "raw_message": message
                            }, ensure_ascii=False)

                    # 普通文本响应
                    ai_response = message.get("content", "")
                    if ai_response:
                        # 清理无效的 UTF-8 代理字符
                        ai_response = ai_response.encode('utf-8', 'replace').decode('utf-8')
                        # 处理思考内容
                        ai_response = self._process_thinking_content(ai_response)
                    return ai_response or ""
                else:
                    return f"API 返回格式错误: {response_data}"
            elif response.status_code == 401:
                return "API 认证失败，请检查 api_key 是否正确"
            elif response.status_code == 404:
                return f"API 端点不存在，请检查 base_url 是否正确: {api_url}"
            elif response.status_code == 400:
                # 工具定义可能不兼容，降级为无工具重试
                if tools and "tools" in str(response.text).lower():
                    print(f"{Fore.YELLOW}FC 不支持，降级为普通模式{Style.RESET_ALL}")
                    body.pop("tools", None)
                    body.pop("tool_choice", None)
                    retry = requests.post(url=api_url, json=body, headers=self._get_headers(), timeout=None)
                    if retry.status_code == 200:
                        rd = retry.json()
                        if "choices" in rd and rd["choices"]:
                            ai_response = rd["choices"][0].get("message", {}).get("content", "")
                            return ai_response.encode('utf-8', 'replace').decode('utf-8') if ai_response else ""
                return f"API 调用失败: {response.status_code} - {response.text}"
            else:
                return f"API 调用失败: {response.status_code} - {response.text}"

        except requests.exceptions.ConnectionError:
            return f"无法连接到 API 服务: {self.base_url}，请检查服务是否运行"
        except Exception as e:
            return f"API 调用失败: {str(e)}"

    def _build_messages_with_history(self, system_prompt, user_input):
        """构建包含历史记录的消息列表（支持 FC tool 消息）"""
        messages = []

        # 添加系统提示词
        if system_prompt:
            clean_prompt = system_prompt.encode('utf-8', 'replace').decode('utf-8')
            messages.append({
                "role": "system",
                "content": clean_prompt
            })

        # 添加历史对话记录（使用共享历史）
        if self.shared_conversation_history is not None:
            for msg in self.shared_conversation_history[-self.max_history:]:
                if not isinstance(msg, dict) or "role" not in msg:
                    continue

                role = msg["role"]

                # tool 角色消息（FC 工具结果）
                if role == "tool":
                    tool_msg = {"role": "tool", "content": msg.get("content", "")}
                    if "tool_call_id" in msg:
                        tool_msg["tool_call_id"] = msg["tool_call_id"]
                    if "name" in msg:
                        tool_msg["name"] = msg["name"]
                    messages.append(tool_msg)
                    continue

                # assistant 消息可能包含 tool_calls
                if role == "assistant" and "tool_calls" in msg:
                    assistant_msg = {
                        "role": "assistant",
                        "content": msg.get("content"),
                        "tool_calls": msg["tool_calls"]
                    }
                    messages.append(assistant_msg)
                    continue

                # 普通 user/assistant 消息
                if "content" in msg:
                    clean_content = msg["content"]
                    if isinstance(clean_content, str):
                        clean_content = clean_content.encode('utf-8', 'replace').decode('utf-8')
                    messages.append({"role": role, "content": clean_content})

        # 添加当前用户输入
        if user_input:
            clean_input = user_input.encode('utf-8', 'replace').decode('utf-8')
            messages.append({
                "role": "user",
                "content": clean_input
            })

        return messages

    def _call_api_with_history(self, content, system_prompt=None):
        """使用对话历史调用 API"""
        if not self.base_url:
            return "错误: openai 引擎的 base_url 未配置"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if self.shared_conversation_history is not None:
            for msg in self.shared_conversation_history[-self.max_history:]:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    messages.append(msg)
        messages.append({"role": "user", "content": content})

        body = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }

        try:
            response = requests.post(
                url=self._get_api_url(),
                json=body,
                headers=self._get_headers(),
                timeout=None
            )

            if response.status_code == 200:
                response_data = response.json()
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    ai_response = response_data["choices"][0]["message"]["content"]
                    ai_response = ai_response.encode('utf-8', 'replace').decode('utf-8')
                    return self._process_thinking_content(ai_response)
            return f"API 调用失败: {response.status_code} - {response.text}"
        except Exception as e:
            return f"API 调用失败: {str(e)}"

    def _process_thinking_content(self, response):
        """处理思考内容，将思考部分以灰色文本显示"""
        import re

        if not self.thinking_start_marker or not self.thinking_end_marker:
            return response

        if self.thinking_start_marker in response and self.thinking_end_marker in response:
            parts = response.split(self.thinking_start_marker)
            if len(parts) > 1:
                remaining = parts[1]
                if self.thinking_end_marker in remaining:
                    thinking_part, reply_part = remaining.split(self.thinking_end_marker, 1)
                    thinking_content = thinking_part.strip()
                    reply_content = reply_part.strip()
                    if thinking_content:
                        print(f"{Fore.LIGHTBLACK_EX}[思考: {thinking_content}]{Style.RESET_ALL}")
                    return reply_content if reply_content else ""

        return response

    def set_model(self, model_name):
        """设置模型"""
        self.model = model_name
        print(f"{Fore.GREEN}已切换模型为: {model_name}{Style.RESET_ALL}")

    def context_window(self):
        """
        返回当前模型的上下文窗口（token 数）。
        优先级: config.system.context_window > 模型名查表 > 默认 128000。
        注: OpenAI /chat/completions 协议本身不返回模型窗口，需本地维护。
        """
        cfg = get_system_config("context_window", None)
        if cfg:
            try:
                return int(cfg)
            except (TypeError, ValueError):
                pass
        model = (self.model or "").lower()
        for key, win in MODEL_CONTEXT_WINDOWS.items():
            if key and key in model:
                return win
        return 128000

    def list_models(self):
        """列出可用模型（调用 API 的 /models 端点）"""
        if not self.base_url:
            return ["错误: base_url 未配置"]

        try:
            models_url = self.base_url.rstrip('/')
            if models_url.endswith('/chat/completions'):
                models_url = models_url[:-len('/chat/completions')]
            models_url = models_url.rstrip('/') + '/models'

            response = requests.get(
                url=models_url,
                headers=self._get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if "data" in data:
                    models = [m.get("id", "unknown") for m in data["data"]]
                    return models
                else:
                    return ["API 返回格式不标准，无法解析模型列表"]
            else:
                return [f"获取模型列表失败: {response.status_code}"]
        except Exception as e:
            return [f"获取模型列表失败: {str(e)}"]

    def handle_command(self, command):
        """处理引擎特定命令"""
        if command == "models":
            models = self.list_models()
            print(f"{Fore.GREEN}可用模型列表:{Style.RESET_ALL}")
            for model in models:
                status = " (当前使用)" if model == self.model else ""
                print(f"{Fore.GREEN}  - {model}{status}{Style.RESET_ALL}")
            return True

        elif command.startswith("set "):
            model_name = command[4:].strip()
            if model_name:
                self.set_model(model_name)
                return True
            else:
                print(f"{Fore.RED}请提供模型名称. 用法: /engine.openai set <模型名>{Style.RESET_ALL}")
                return False

        elif command == "info":
            print(f"{Fore.GREEN}OpenAI 兼容引擎配置:{Style.RESET_ALL}")
            print(f"  base_url: {self.base_url}")
            print(f"  model:    {self.model}")
            print(f"  api_key:  {'已设置' if self.api_key else '未设置'}")
            return True

        else:
            print(f"{Fore.RED}未知命令. 可用命令: models, set, info{Style.RESET_ALL}")
            return False
