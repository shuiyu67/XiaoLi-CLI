import os
import json
import requests
import threading
import time
from colorama import Fore, Style


class QwqAI:
    """基于QwQ-32B模型的AI引擎"""
    
    def get_help_info(self):
        """获取引擎帮助信息"""
        help_text = """
QwQ-32B AI引擎插件帮助信息
==========================

引擎名称: QwQ
描述: 基于QwQ-32B模型的AI引擎，支持复杂推理和数学计算

可用命令:
  无特定命令，直接与AI对话即可

使用说明:
1. 此引擎使用QwQ-32B云API
2. 使用/engine.switch qwq切换到此引擎
3. 直接输入自然语言与AI对话
4. 特别适合处理数学、逻辑推理等复杂任务
"""
        return help_text
    
    def __init__(self):
        self.name = "qwq"
        self.cli = None  # 引用CLI实例以访问插件
        
        # 直接从 config.json 读取配置
        import json
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_file = os.path.join(project_root, "config.json")
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                engine_config = config.get("api", {}).get("engines", {}).get("qwq", {})
                self.api_key = engine_config.get("api_key", "")
                self.url = engine_config.get("base_url", "")
                self.model = engine_config.get("model", "")
        except Exception as e:
            # 如果读取失败，使用空值
            print(f"{Fore.YELLOW}警告: 读取配置文件失败: {e}{Style.RESET_ALL}")
            self.api_key = ""
            self.url = ""
            self.model = ""
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        # 初始化对话历史
        self.conversation_history = []
        # 设置最大历史记录数
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.max_history = config.get("system", {}).get("max_history", 10)
        except:
            self.max_history = 10
        
        # 设置思考标记
        self.thinking_start_marker = ""
        self.thinking_end_marker = ""
        
        # 共享对话历史引用（由CLI设置）
        self.shared_conversation_history = None
    
    def generate_response(self, user_input, tool_results=None, system_prompt=None):
        """生成AI响应 - 使用QwQ API"""
        try:
            # 如果有工具结果，将其作为上下文返回给AI处理
            if tool_results:
                tool_result_text = f"工具执行结果: {tool_results.get('result', '无结果')}"
                # 构建消息列表
                messages = self._build_messages_with_history(system_prompt, tool_result_text)

                # 构建请求体
                body = {
                    "model": self.model,
                    "messages": messages,
                    "stream": False  # 使用非流式响应以便于处理
                }

                # 发送请求到QwQ API
                response = requests.post(url=self.url, json=body, headers=self.headers, timeout=None)

                if response.status_code == 200:
                    response_data = response.json()
                    if "choices" in response_data and len(response_data["choices"]) > 0:
                        ai_response = response_data["choices"][0]["message"]["content"]
                        
                        # 处理思考标记
                        processed_response = self._process_thinking_content(ai_response)
                        
                        # 返回处理后的AI回复
                        return processed_response
                    else:
                        return "QwQ API返回格式错误"
                else:
                    return f"QwQ API调用失败: {response.status_code} - {response.text}"

            # 构建消息列表
            messages = self._build_messages_with_history(system_prompt, user_input)

            # 构建请求体
            body = {
                "model": self.model,
                "messages": messages,
                "stream": False  # 使用非流式响应以便于处理
            }

            # 发送请求到QwQ API
            response = requests.post(url=self.url, json=body, headers=self.headers, timeout=None)

            if response.status_code == 200:
                response_data = response.json()
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    ai_response = response_data["choices"][0]["message"]["content"]
                    
                    # 处理思考标记
                    processed_response = self._process_thinking_content(ai_response)
                    
                    # 返回处理后的AI回复
                    return processed_response
                else:
                    return "QwQ API返回格式错误"
            else:
                return f"QwQ API调用失败: {response.status_code} - {response.text}"

        except Exception as e:
            # 如果API调用失败，返回错误信息
            return f"QwQ API调用失败: {str(e)}"
    
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
            "model": self.model,
            "messages": messages,
            "stream": False  # 使用非流式响应以便于处理
        }

        # 发送请求到QwQ API
        response = requests.post(url=self.url, json=body, headers=self.headers, timeout=None)

        if response.status_code == 200:
            response_data = response.json()
            if "choices" in response_data and len(response_data["choices"]) > 0:
                ai_response = response_data["choices"][0]["message"]["content"]
                
                # 处理思考标记
                processed_response = self._process_thinking_content(ai_response)
                
                return processed_response
            else:
                return "QwQ API返回格式错误"
        else:
            return f"QwQ API调用失败: {response.status_code} - {response.text}"
    
    def handle_command(self, command):
        """处理引擎特定命令"""
        # QwQ引擎目前不支持特定命令
        print(f"{Fore.RED}QwQ引擎不支持此命令{Style.RESET_ALL}")
        return False
    
    def _process_thinking_content(self, response):
        """处理思考内容，将思考部分以灰色文本显示，只返回回复部分"""
        from colorama import Fore, Style
        import re
        
        # 这里可以设置思考标记，由用户自己定义
        thinking_start_marker = "<think>"  # 用户可以设置开始标记
        thinking_end_marker = "</think>"    # 用户可以设置结束标记
        
        # 如果用户设置了思考标记，则处理思考内容
        if thinking_start_marker and thinking_end_marker and thinking_start_marker in response and thinking_end_marker in response:
            # 分离思考内容和回复内容
            parts = response.split(thinking_start_marker)
            if len(parts) > 1:
                # 获取包含结束标记的部分
                remaining = parts[1]
                thinking_content = ""
                reply_content = ""
                
                # 检查结束标记
                if thinking_end_marker in remaining:
                    thinking_part, reply_part = remaining.split(thinking_end_marker, 1)
                    thinking_content = thinking_part.strip()
                    reply_content = reply_part.strip()
                else:
                    # 如果没有找到结束标记，将剩余部分都视为思考内容
                    thinking_content = remaining.strip()
                    reply_content = ""
                
                # 显示思考内容为灰色文本
                if thinking_content:
                    print(f"{Fore.LIGHTBLACK_EX}[思考: {thinking_content}]{Style.RESET_ALL}")
                
                # 返回回复内容
                if reply_content:
                    return reply_content
                else:
                    return ""  # 如果没有回复内容，返回空字符串
        else:
            # 如果没有设置思考标记或没有找到标记，直接返回原始响应
            return response