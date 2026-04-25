import os
import sys
import json
import requests
from colorama import Fore, Style
from openai import OpenAI
import logging
from datetime import datetime

# 设置日志
logger = logging.getLogger(__name__)

# 添加项目根目录到sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)


class MimoAI:
    """小米MiMoAI引擎 - 使用MiMo-v2-flash模型 - OpenAI格式"""
    requires_api_key = True  # MiMo引擎需要API密钥
    
    def get_help_info(self):
        """获取引擎帮助信息"""
        help_text = """
MiMo AI引擎插件帮助信息
==========================

引擎名称: MiMo
描述: 基于MiMo模型的AI引擎，由小米公司开发

可用命令:
  无特定命令，直接与AI对话即可

使用说明:
1. 此引擎使用小米MiMo云API
2. 使用/engine.switch mimo切换到此引擎
3. 直接输入自然语言与AI对话
4. 支持思考模式和多轮对话
"""
        return help_text
    
    def __init__(self):
        self.name = "mimo"
        self.cli = None
        
        # 直接从 config.json 读取配置
        config_file = os.path.join(project_root, "config.json")
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                engine_config = config.get("api", {}).get("engines", {}).get("mimo", {})
                self.api_key = engine_config.get("api_key", "")
                base_url_raw = engine_config.get("base_url", "")
                self.base_url = base_url_raw.rstrip('/') + '/chat/completions' if base_url_raw else ""
                self.model = engine_config.get("model", "")
        except Exception as e:
            # 如果读取失败，使用空值
            self.api_key = ""
            self.base_url = ""
            self.model = ""
        
        # 初始化对话历史
        self.conversation_history = []
        # 设置最大历史记录数
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.max_history = config.get("system", {}).get("max_history", 10)
        except:
            self.max_history = 10
        
        # 初始化 headers（用于 API 请求）
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # 初始化 OpenAI 客户端
        try:
            if self.api_key and self.base_url:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url.replace('/chat/completions', ''),
                    timeout=None
                )
            else:
                self.client = None
        except Exception as e:
            logger.warning(f"初始化 MiMo OpenAI 客户端失败: {e}")
            self.client = None
    
    def generate_response(self, user_input, tool_results=None, system_prompt=None):
        """生成AI响应 - 使用MiMo-v2-flash - OpenAI格式"""
        if not self.client:
            return "MiMo引擎未正确初始化，无法调用API"
        
        try:
            # 获取当前日期和星期
            now = datetime.now()
            date_str = now.strftime("%Y年%m月%d日")
            week_str = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()]
            current_datetime = f"{date_str} {week_str}"
            
            # 设置默认系统提示词（如果未提供）
            if not system_prompt:
                system_prompt = f"You are MiMo, an AI assistant developed by Xiaomi. Today is date: {current_datetime}. Your knowledge cutoff date is December 2024."
            
            # 如果有工具结果，将其作为上下文返回给AI处理
            if tool_results:
                tool_result_text = f"工具执行结果: {tool_results.get('result', '无结果')}"
                
                # 构建包含历史记录的消息列表
                messages = self._build_messages_with_history(system_prompt, tool_result_text)
                
                # 构建请求体，使用MiMo特定参数
                body = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2048,
                    "top_p": 0.95,
                    "frequency_penalty": 0,
                    "presence_penalty": 0,
                    # MiMo特定参数
                    "extra_body": {
                        "thinking": {"type": "disabled"}  # 禁用思考模式
                    }
                }

                # 直接使用requests调用MiMo API，因为需要特定的header格式
                import requests
                response = requests.post(
                    url=self.base_url, 
                    json=body, 
                    headers=self.headers,
                    timeout=None
                )

                if response.status_code == 200:
                    response_data = response.json()
                    if "choices" in response_data and len(response_data["choices"]) > 0:
                        ai_response = response_data["choices"][0]["message"]["content"]
                        
                        # 处理思考标记
                        processed_response = self._process_thinking_content(ai_response)
                        
                        # 更新对话历史
                        self._update_conversation_history(user_input if not tool_results else tool_result_text, ai_response)
                        
                        # 返回处理后的AI回复，前面加上✦
                        return processed_response
                    else:
                        return "MiMo-v2-flash API返回格式错误"
                elif response.status_code == 401:
                    return "MiMo-v2-flash API认证失败，请检查API密钥是否正确配置"
                else:
                    return f"MiMo-v2-flash API调用失败: {response.status_code} - {response.text}"

            # 构建包含历史记录的消息列表
            messages = self._build_messages_with_history(system_prompt, user_input)
            
            # 构建请求体，使用MiMo特定参数
            body = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2048,
                "top_p": 0.95,
                "frequency_penalty": 0,
                "presence_penalty": 0,
                # MiMo特定参数
                "extra_body": {
                    "thinking": {"type": "disabled"}  # 禁用思考模式
                }
            }

            # 直接使用requests调用MiMo API，因为需要特定的header格式
            import requests
            response = requests.post(
                url=self.base_url, 
                json=body, 
                headers=self.headers,
                timeout=None
            )

            if response.status_code == 200:
                response_data = response.json()
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    ai_response = response_data["choices"][0]["message"]["content"]
                    
                    # 处理思考标记
                    processed_response = self._process_thinking_content(ai_response)
                    
                    # 更新对话历史
                    self._update_conversation_history(user_input, ai_response)
                    
                    # 返回处理后的AI回复
                    return processed_response
                else:
                    return "MiMo-v2-flash API返回格式错误"
            elif response.status_code == 401:
                return "MiMo-v2-flash API认证失败，请检查API密钥是否正确配置"
            else:
                return f"MiMo-v2-flash API调用失败: {response.status_code} - {response.text}"

        except Exception as e:
            # 如果API调用失败，返回错误信息
            return f"MiMo-v2-flash API调用失败: {str(e)}"
    
    def _build_messages_with_history(self, system_prompt, user_input):
        """构建包含历史记录的消息列表"""
        messages = []
        
        # 添加系统提示词
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # 添加历史对话记录（使用共享历史）
        if self.shared_conversation_history is not None:
            # 确保历史记录格式正确
            for msg in self.shared_conversation_history[-self.max_history:]:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    messages.append(msg)
                else:
                    # 如果格式不正确，跳过该条记录
                    continue
        
        # 添加当前用户输入
        messages.append({
            "role": "user",
            "content": user_input
        })
        
        return messages
    
    def _update_conversation_history(self, user_input, ai_response):
        """更新对话历史"""
        # 添加用户输入到历史记录
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })
        # 添加AI回复到历史记录
        self.conversation_history.append({
            "role": "assistant",
            "content": ai_response
        })
        # 限制历史记录数量
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history * 2:]
    
    def _call_api_with_history(self, content, system_prompt=None):
        """使用对话历史调用API"""
        # 获取当前日期和星期
        now = datetime.now()
        date_str = now.strftime("%Y年%m月%d日")
        week_str = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()]
        current_datetime = f"{date_str} {week_str}"
        
        # 设置默认系统提示词（如果未提供）
        if not system_prompt:
            system_prompt = f"You are MiMo, an AI assistant developed by Xiaomi. Today is date: {current_datetime}. Your knowledge cutoff date is December 2024."
            
        # 构建消息列表
        messages = []

        # 添加系统提示词(如果提供)
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        # 添加历史对话记录（使用共享历史）
        if self.shared_conversation_history is not None:
            # 确保历史记录格式正确
            for msg in self.shared_conversation_history[-self.max_history:]:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    messages.append(msg)
                else:
                    # 如果格式不正确，跳过该条记录
                    continue

        # 添加当前内容
        messages.append({
            "role": "user",
            "content": content
        })

        # 构建请求体
        body = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens": 1024,
            "temperature": 0.3,
            "top_p": 0.95,
            "stream": False,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "extra_body": {
                "thinking": {"type": "disabled"}
            }
        }

        # 发送请求到MiMo-v2-flash API
        response = requests.post(url=self.base_url, json=body, headers=self.headers, timeout=None)

        if response.status_code == 200:
            response_data = response.json()
            if "choices" in response_data and len(response_data["choices"]) > 0:
                ai_response = response_data["choices"][0]["message"]["content"]
                
                # 处理思考标记
                processed_response = self._process_thinking_content(ai_response)
                
                return processed_response
            else:
                return "MiMo-v2-flash API返回格式错误"
        else:
            return f"MiMo-v2-flash API调用失败: {response.status_code} - {response.text}"
    
    def handle_command(self, command):
        """处理引擎特定命令"""
        # MiMo引擎目前不支持特定命令
        print(f"{Fore.RED}MiMo引擎不支持此命令{Style.RESET_ALL}")
        return False
    
    def _process_thinking_content(self, response):
        """处理思考内容，将思考部分以灰色文本显示，只返回回复部分"""
        from colorama import Fore, Style
        import re
        
        # 这里可以设置思考标记，由用户自己定义
        thinking_start_marker = "<thinking>"
        thinking_end_marker = "</thinking>"
        
        # 如果响应中包含思考标记，则提取思考内容和回复内容
        if thinking_start_marker in response and thinking_end_marker in response:
            # 提取思考内容
            thinking_match = re.search(f'{thinking_start_marker}(.*?){thinking_end_marker}', response, re.DOTALL)
            if thinking_match:
                thinking_content = thinking_match.group(1).strip()
                # 打印思考内容（灰色）
                print(f"{Fore.LIGHTBLACK_EX}思考: {thinking_content}{Style.RESET_ALL}")
            
            # 提取回复内容
            response_content = re.split(f'{thinking_end_marker}', response, maxsplit=1)[-1].strip()
            return response_content
        
        # 如果没有思考标记，直接返回响应
        return response
