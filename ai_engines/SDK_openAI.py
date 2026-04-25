"""
小狸 Pro-CLI AI 引擎开发 SDK
提供快速开发 AI 引擎的工具包
"""
import os
import sys
import json
import requests
from colorama import Fore, Style
from openai import OpenAI
import logging

# 设置日志
logger = logging.getLogger(__name__)

# 添加项目根目录到sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)


class _AIEngineSDK:
    """AI 引擎 SDK 内部实现"""
    
    def __init__(self):
        self.name = ""
        self.api_key = ""
        self.base_url = ""
        self.model = ""
        self.is_online = True
        self.max_history = 10
        self.conversation_history = []
        self.shared_conversation_history = None
        self.cli = None
        
        # 深度思考引擎配置
        self.is_thinking_engine = False  # 是否是深度思考引擎
        self.thinking_start_marker = ""  # 思考开始标记
        self.thinking_end_marker = ""  # 思考结束标记
        self.show_thinking = True  # 是否显示思考过程
        
        # 配置文件路径
        self.config_file = os.path.join(project_root, "config.json")
        
    def _load_config(self):
        """从配置文件加载配置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                engine_config = config.get("api", {}).get("engines", {}).get(self.name, {})
                
                if not self.api_key:
                    self.api_key = engine_config.get("api_key", "")
                if not self.base_url:
                    self.base_url = engine_config.get("base_url", "")
                if not self.model:
                    self.model = engine_config.get("model", "")
                    
                self.max_history = config.get("system", {}).get("max_history", 10)
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            self.max_history = 10
    
    def _call_openai_api(self, messages):
        """调用 OpenAI 格式的 API"""
        try:
            self._load_config()
            
            # 构建请求体
            body = {
                "model": self.model,
                "messages": messages,
                "stream": False
            }
            
            # 构建请求头
            headers = {
                'Content-Type': 'application/json'
            }
            
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            # 确定 API 地址
            api_url = self.base_url
            if not api_url.endswith("/chat/completions"):
                api_url = api_url.rstrip('/') + "/chat/completions"
            
            # 发送请求
            response = requests.post(
                url=api_url,
                json=body,
                headers=headers,
                timeout=None
            )
            
            # 处理响应
            if response.status_code == 200:
                response_data = response.json()
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    ai_response = response_data["choices"][0]["message"]["content"]
                    
                    # 如果是深度思考引擎，处理思考内容
                    if self.is_thinking_engine:
                        ai_response = self._process_thinking_content(ai_response)
                    
                    return ai_response
                else:
                    return f"AI 返回格式错误: {response_data}"
            else:
                return f"AI 调用失败: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"AI 调用失败: {str(e)}"
    
    def _build_messages(self, system_prompt, user_input):
        """构建消息列表"""
        messages = []
        
        # 添加系统提示词
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # 添加历史对话记录
        if self.shared_conversation_history is not None:
            for msg in self.shared_conversation_history[-self.max_history:]:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    messages.append(msg)
        
        # 添加当前用户输入
        messages.append({
            "role": "user",
            "content": user_input
        })
        
        return messages
    
    def generate_response(self, user_input, tool_results=None, system_prompt=None):
        """生成 AI 响应"""
        try:
            # 如果有工具结果，将其作为上下文返回给AI处理
            if tool_results:
                tool_result_text = f"工具执行结果: {tool_results.get('result', '无结果')}"
                messages = self._build_messages(system_prompt, tool_result_text)
            else:
                messages = self._build_messages(system_prompt, user_input)
            
            # 调用 API
            return self._call_openai_api(messages)
            
        except Exception as e:
            return f"AI 调用失败: {str(e)}"
    
    def _process_thinking_content(self, response):
        """处理思考内容，将思考部分以灰色文本显示，只返回回复部分"""
        import re
        
        if not self.thinking_start_marker or not self.thinking_end_marker:
            # 如果没有设置标记，直接返回
            return response
        
        # 使用正则表达式查找思考内容
        pattern = f"{re.escape(self.thinking_start_marker)}(.*?){re.escape(self.thinking_end_marker)}"
        matches = re.findall(pattern, response, re.DOTALL)
        
        if matches and self.show_thinking:
            for match in matches:
                # 用灰色文本显示思考内容
                thinking_text = f"{Fore.LIGHTBLACK_EX}[思考: {match}]{Style.RESET_ALL}"
                # 替换思考标记之间的内容，保留思考内容但以灰色显示
                response = re.sub(pattern, thinking_text, response, 1)
        elif matches and not self.show_thinking:
            # 如果不显示思考内容，直接删除
            for match in matches:
                response = re.sub(pattern, "", response, 1)
        
        return response


# 全局 SDK 实例
_sdk_instance = _AIEngineSDK()


def engine_Online(mode):
    """
    设置引擎模式
    
    Args:
        mode: "on" - 云模式（在线 API）
              "off" - 本地模式（如 Ollama）
    """
    _sdk_instance.is_online = (mode.lower() == "on")


def ai_name(name):
    """设置引擎名称"""
    _sdk_instance.name = name


def ai_api_url(url):
    """设置 API 地址"""
    _sdk_instance.base_url = url


def ai_api_key(key):
    """设置 API 密钥"""
    _sdk_instance.api_key = key


def ai_model_id(model):
    """设置模型名称"""
    _sdk_instance.model = model


def ai_thinking_engine(enable=True, start_marker="<thinking>", end_marker="</thinking>", show_thinking=True):
    """
    设置深度思考引擎配置
    
    Args:
        enable: 是否启用深度思考引擎模式
        start_marker: 思考开始标记，默认为 "<thinking>"
        end_marker: 思考结束标记，默认为 "</thinking>"
        show_thinking: 是否显示思考过程，默认为 True
    """
    _sdk_instance.is_thinking_engine = enable
    _sdk_instance.thinking_start_marker = start_marker
    _sdk_instance.thinking_end_marker = end_marker
    _sdk_instance.show_thinking = show_thinking


def set_cli(cli):
    """设置 CLI 引用"""
    _sdk_instance.cli = cli


def set_shared_history(history):
    """设置共享对话历史"""
    _sdk_instance.shared_conversation_history = history


def generate_response(user_input, tool_results=None, system_prompt=None):
    """生成 AI 响应"""
    return _sdk_instance.generate_response(user_input, tool_results, system_prompt)


def get_sdk_instance():
    """获取 SDK 实例（用于高级用法）"""
    return _sdk_instance


# 导出
__all__ = [
    'engine_Online',
    'ai_name',
    'ai_api_url',
    'ai_api_key',
    'ai_model_id',
    'ai_thinking_engine',
    'set_cli',
    'set_shared_history',
    'generate_response',
    'get_sdk_instance'
]