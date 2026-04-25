import os
import sys
import json
import requests
import threading
import time
from colorama import Fore, Style
import logging

# 设置日志
logger = logging.getLogger(__name__)

# 添加项目根目录到sys.path，以便正确导入
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # 获取项目根目录
sys.path.insert(0, project_root)


class IflowAPIAI:
    """基于Qwen3-Coder-Plus模型的AI引擎"""
    
    def get_help_info(self):
        """获取引擎帮助信息"""
        help_text = """
iflow API AI引擎插件帮助信息
==========================

引擎名称: iflow-api
描述: 基于Qwen3-Coder-Plus模型的AI引擎，支持复杂推理和代码生成

可用命令:
  无特定命令，直接与AI对话即可

使用说明:
1. 此引擎使用Qwen3-Coder-Plus云API
2. 使用/engine.switch iflow-api切换到此引擎
3. 直接输入自然语言与AI对话
4. 特别适合处理代码生成、技术问题等复杂任务
"""
        return help_text
    
    def __init__(self):
        self.name = "iflow-api"
        self.cli = None  # 引用CLI实例以访问插件
        
        # 直接从 config.json 读取配置（一次性读取）
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_file = os.path.join(project_root, "config.json")
        
        # 默认值
        self.api_key = ""
        self.url = ""
        self.model = ""
        self.max_history = 10
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                engine_config = config.get("api", {}).get("engines", {}).get("iflow_api", {})
                self.api_key = engine_config.get("api_key", "")
                self.url = engine_config.get("base_url", "")
                self.model = engine_config.get("model", "")
                self.max_history = config.get("system", {}).get("max_history", 10)
        except Exception as e:
            # 如果读取失败，使用默认值
            logger.warning(f"警告: 读取配置文件失败: {e}")
            print(f"{Fore.YELLOW}警告: 读取配置文件失败: {e}{Style.RESET_ALL}")
        
        # 验证API密钥
        if not self.api_key:
            logger.warning("警告: iflow-api引擎的API密钥未设置")
            print(f"{Fore.YELLOW}警告: iflow-api引擎的API密钥未设置{Style.RESET_ALL}")
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # 初始化对话历史
        self.conversation_history = []
        
        # 设置思考标记
        self.thinking_start_marker = ""
        self.thinking_end_marker = ""
        
        # 共享对话历史引用（由CLI设置）
        self.shared_conversation_history = None
    
    def generate_response(self, user_input, tool_results=None, system_prompt=None):
        """生成AI响应 - 使用 qwen3-coder-plus"""
        try:
            # 如果有工具结果，将其作为上下文返回给AI处理
            if tool_results:
                tool_result_text = f"工具执行结果: {tool_results.get('result', '无结果')}"
                # 构建消息列表

                messages = self._build_messages_with_history(system_prompt, tool_result_text)

                

                # 构建请求体

                body = {

                    "model": self.model or "qwen3-coder-plus",

                    "messages": messages,

                    "stream": False  # 使用非流式响应以便于处理

                }

                

                # 发送请求到qwen3-coder-plus API

                response = requests.post(url=self.url, json=body, headers=self.headers, timeout=None)

                

                if response.status_code == 200:

                    response_data = response.json()
                    
                    # 检查是否是API错误响应（例如认证失败）
                    if isinstance(response_data, dict) and "status" in response_data:
                        # 检查是否是认证错误
                        if response_data.get("status") in ["434", "401", "403"]:
                            error_msg = response_data.get("msg", "API认证失败")
                            return f"qwen3-coder-plus API错误: {error_msg}"
                        elif "body" in response_data and response_data["body"] is None:
                            error_msg = response_data.get("msg", "API请求失败")
                            return f"qwen3-coder-plus API错误: {error_msg}"
                    
                    if "choices" in response_data and len(response_data["choices"]) > 0:

                        # 改进错误处理以适应不同的API响应格式
                        choice = response_data["choices"][0]
                        if "message" in choice and "content" in choice["message"]:
                            ai_response = choice["message"]["content"]
                            
                            # 处理思考标记
                            processed_response = self._process_thinking_content(ai_response)

                            # 返回处理后的AI回复
                            return processed_response
                        else:
                            # 尝试其他可能的字段名
                            if "text" in choice:
                                return choice["text"]
                            elif "delta" in choice and "content" in choice["delta"]:
                                return choice["delta"]["content"]
                            else:
                                return f" qwen3-coder-plus返回格式错误: 缺少预期的响应字段 - {response_data}"

                    else:

                        return f" qwen3-coder-plus返回格式错误: {response_data}"

                else:

                    return f" qwen3-coder-plus调用失败: {response.status_code} - {response.text}"

            

            # 构建消息列表

            messages = self._build_messages_with_history(system_prompt, user_input)

            

            # 构建请求体

            body = {

                "model": self.model or "qwen3-coder-plus",

                "messages": messages,

                "stream": False  # 使用非流式响应以便于处理

            }

            

            # 发送请求到qwen3-coder-plus

            response = requests.post(url=self.url, json=body, headers=self.headers, timeout=None)

            

            if response.status_code == 200:

                response_data = response.json()
                
                # 检查是否是API错误响应（例如认证失败）
                if isinstance(response_data, dict) and "status" in response_data:
                    # 检查是否是认证错误
                    if response_data.get("status") in ["434", "401", "403"]:
                        error_msg = response_data.get("msg", "API认证失败")
                        return f"qwen3-coder-plus API错误: {error_msg}"
                    elif "body" in response_data and response_data["body"] is None:
                        error_msg = response_data.get("msg", "API请求失败")
                        return f"qwen3-coder-plus API错误: {error_msg}"
                
                if "choices" in response_data and len(response_data["choices"]) > 0:

                    # 改进错误处理以适应不同的API响应格式
                    choice = response_data["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        ai_response = choice["message"]["content"]
                        
                        # 处理思考标记
                        processed_response = self._process_thinking_content(ai_response)

                        # 返回处理后的AI回复
                        return processed_response
                    else:
                        # 尝试其他可能的字段名
                        if "text" in choice:
                            return choice["text"]
                        elif "delta" in choice and "content" in choice["delta"]:
                            return choice["delta"]["content"]
                        else:
                            return f"qwen3-coder-plus返回格式错误: 缺少预期的响应字段 - {response_data}"

                else:

                    return f"qwen3-coder-plus返回格式错误: {response_data}"

            else:

                return f"qwen3-coder-plus调用失败: {response.status_code} - {response.text}"

            

        except Exception as e:

            # 如果API调用失败，返回错误信息

            return f"qwen3-coder-plus调用失败: {str(e)}"
    
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
    
    
    
    def _call_api_with_history(self, content, system_prompt=None):
        """使用对话历史调用API"""
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

            "role": "tool",

            "content": content

        })

        

        # 构建请求体
        body = {
            "model": self.model or "qwen3-coder-plus",
            "messages": messages,
            "stream": False  # 使用非流式响应以便于处理
        }
        

        # 发送请求到qwen3-coder-plus

        response = requests.post(url=self.url, json=body, headers=self.headers, timeout=None)

        

        if response.status_code == 200:

            response_data = response.json()
            
            # 检查是否是API错误响应（例如认证失败）
            if isinstance(response_data, dict) and "status" in response_data:
                # 检查是否是认证错误
                if response_data.get("status") in ["434", "401", "403"]:
                    error_msg = response_data.get("msg", "API认证失败")
                    return f"qwen3-coder-plus API错误: {error_msg}"
                elif "body" in response_data and response_data["body"] is None:
                    error_msg = response_data.get("msg", "API请求失败")
                    return f"qwen3-coder-plus API错误: {error_msg}"
            
            if "choices" in response_data and len(response_data["choices"]) > 0:

                # 改进错误处理以适应不同的API响应格式
                choice = response_data["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    ai_response = choice["message"]["content"]
                    
                    # 处理思考标记
                    processed_response = self._process_thinking_content(ai_response)

                    return processed_response
                else:
                    # 尝试其他可能的字段名
                    if "text" in choice:
                        return choice["text"]
                    elif "delta" in choice and "content" in choice["delta"]:
                        return choice["delta"]["content"]
                    else:
                        return f"qwen3-coder-plus返回格式错误: 缺少预期的响应字段 - {response_data}"

            else:

                return f"qwen3-coder-plus返回格式错误: {response_data}"

        else:

            return f"qwen3-coder-plus调用失败: {response.status_code} - {response.text}"
    
    def handle_command(self, command):
        """处理引擎特定命令"""
        # qwen3-coder-plus引擎目前不支持特定命令
        print(f"{Fore.RED}qwen3-coder-plus引擎不支持此命令{Style.RESET_ALL}")
        return False
    
    def _process_thinking_content(self, response):
        """处理思考内容，将思考部分以灰色文本显示，只返回回复部分"""
        from colorama import Fore, Style
        import re
        
        # 这里可以设置思考标记，由用户自己定义
        thinking_start_marker = ""
        thinking_end_marker = ""
        
        if self.thinking_start_marker and self.thinking_end_marker:
            # 使用正则表达式查找思考内容
            pattern = f"{re.escape(self.thinking_start_marker)}(.*?){re.escape(self.thinking_end_marker)}"
            matches = re.findall(pattern, response, re.DOTALL)
            
            if matches:
                for match in matches:
                    # 用灰色文本显示思考内容
                    thinking_text = f"{Fore.LIGHTBLACK_EX}[思考: {match}]{Style.RESET_ALL}"
                    # 替换思考标记之间的内容，保留思考内容但以灰色显示
                    response = re.sub(pattern, thinking_text, response, 1)
        
        return response