import os
import json
import requests
from colorama import Fore, Style
from openai import OpenAI

# 获取项目根目录
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)


class Maas_http_engineAI:
    """基于HTTP协议的MaaS（Model as a Service）AI引擎"""
    requires_api_key = True  # MaaS HTTP引擎需要API密钥
    
    def get_help_info(self):
        """获取引擎帮助信息"""
        help_text = """
MaaS HTTP AI引擎插件帮助信息
==========================

引擎名称: maas_http
描述: 基于HTTP协议的MaaS（Model as a Service）AI引擎，支持多种大模型推理服务

可用命令:
  无特定命令，直接与AI对话即可

使用说明:
1. 此引擎使用HTTP协议调用MaaS API
2. 使用/engine.switch maas_http切换到此引擎
3. 直接输入自然语言与AI对话
4. 支持普通对话、流式对话、JSON模式等多种调用方式
"""
        return help_text
    
    def __init__(self):
        self.name = "maas_http"
        self.cli = None  # 引用CLI实例以訪問插件
        
        # 直接从 config.json 读取配置
        config_file = os.path.join(project_root, "config.json")
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                engine_config = config.get("api", {}).get("engines", {}).get("maas_http", {})
                self.api_key = engine_config.get("api_key", "")
                self.base_url = engine_config.get("base_url", "")
                self.model_id = engine_config.get("model", "")
        except Exception as e:
            # 如果读取失败，使用空值
            self.api_key = ""
            self.base_url = ""
            self.model_id = ""        
        # 初始化客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # 初始化对话历史
        self.conversation_history = []
        # 设置最大历史记录数
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.max_history = config.get("system", {}).get("max_history", 10)
        except:
            self.max_history = 10
        
        # 共享對話歷史引用（由CLI設置）
        self.shared_conversation_history = None
    
    def generate_response(self, user_input, tool_results=None, system_prompt=None):
        """生成AI響應 - 使用MaaS HTTP API"""
        try:
            # 如果有工具結果,將其作為上下文返回給AI處理
            if tool_results:
                tool_result_text = f"工具執行結果: {tool_results.get('result', '無結果')}"
                
                # 構建包含歷史記錄的消息列表
                messages = self._build_messages_with_history(system_prompt, tool_result_text)
                
                # 調用API
                response = self._call_api(messages)
                
                if response:
                    return response
                else:
                    return "MaaS HTTP API調用失敗"
            
            # 構建包含歷史記錄的消息列表
            messages = self._build_messages_with_history(system_prompt, user_input)
            
            # 調用API
            response = self._call_api(messages)
            
            if response:
                return response
            else:
                return "MaaS HTTP API調用失敗"
            
        except Exception as e:
            # 如果API調用失敗,返回錯誤信息
            return f"MaaS HTTP API調用失敗: {str(e)}"
    
    def _call_api(self, messages, use_stream=False, extra_body=None):
        """調用API的核心方法"""
        if extra_body is None:
            extra_body = {}

        try:
            response = self.client.chat.completions.create(
                model=self.model_id or self.default_model,
                messages=messages,
                stream=use_stream,
                temperature=0.7,
                max_tokens=4096,
                extra_headers={"lora_id": "0"},
                stream_options={"include_usage": True},
                extra_body=extra_body
            )

            if use_stream:
                # 處理流式響應
                full_response = ""
                for chunk in response:
                    if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                return full_response
            else:
                # 處理非流式響應
                return response.choices[0].message.content

        except Exception as e:
            print(f"MaaS HTTP API請求出錯: {e}")
            return None
    
    def _build_messages_with_history(self, system_prompt, user_input):
        """構建包含歷史記錄的消息列表"""
        messages = []
        
        # 添加系統提示詞
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # 添加歷史對話記錄（使用共享歷史）
        if self.shared_conversation_history is not None:
            # 確保歷史記錄格式正確
            for msg in self.shared_conversation_history[-self.max_history:]:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    messages.append(msg)
                else:
                    # 如果格式不正確，跳過該條記錄
                    continue
        
        # 添加當前用戶輸入
        messages.append({
            "role": "user",
            "content": user_input
        })
        
        return messages
    
    def _call_api_with_history(self, content, system_prompt=None):
        """使用對話歷史調用API"""
        # 構建消息列表
        messages = []
        # 添加系統提示詞(如果提供)
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        # 添加歷史對話記錄（使用共享歷史）
        if self.shared_conversation_history is not None:
            # 確保歷史記錄格式正確
            for msg in self.shared_conversation_history[-self.max_history:]:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    messages.append(msg)
                else:
                    # 如果格式不正確，跳過該條記錄
                    continue
        # 添加當前內容
        messages.append({
            "role": "tool",
            "content": content
        })
        
        # 調用API
        response = self._call_api(messages)
        
        if response:
            return response
        else:
            return "MaaS HTTP API調用失敗"
    
    def handle_command(self, command):
        """處理引擎特定命令"""
        # MaaS HTTP引擎目前不支持特定命令
        print(f"{Fore.RED}MaaS HTTP引擎不支持此命令{Style.RESET_ALL}")
        return False