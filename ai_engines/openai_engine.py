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

    def generate_response(self, user_input, tool_results=None, system_prompt=None):
        """生成 AI 响应"""
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
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    ai_response = response_data["choices"][0]["message"]["content"]
                    # 清理无效的 UTF-8 代理字符
                    ai_response = ai_response.encode('utf-8', 'replace').decode('utf-8')
                    # 处理思考内容
                    ai_response = self._process_thinking_content(ai_response)
                    return ai_response
                else:
                    return f"API 返回格式错误: {response_data}"
            elif response.status_code == 401:
                return "API 认证失败，请检查 api_key 是否正确"
            elif response.status_code == 404:
                return f"API 端点不存在，请检查 base_url 是否正确: {api_url}"
            else:
                return f"API 调用失败: {response.status_code} - {response.text}"

        except requests.exceptions.ConnectionError:
            return f"无法连接到 API 服务: {self.base_url}，请检查服务是否运行"
        except Exception as e:
            return f"API 调用失败: {str(e)}"

    def _build_messages_with_history(self, system_prompt, user_input):
        """构建包含历史记录的消息列表"""
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
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    clean_content = msg["content"].encode('utf-8', 'replace').decode('utf-8')
                    messages.append({"role": msg["role"], "content": clean_content})
                else:
                    continue

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
