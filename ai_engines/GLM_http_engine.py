import os
import json
import requests
from colorama import Fore, Style
from openai import OpenAI

# 获取项目根目录
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)


class Glm_http_engineAI:
    """基于HTTP协议的智谱AI GLM引擎"""
    requires_api_key = True  # GLM HTTP引擎需要API密钥
    
    def get_help_info(self):
        """获取引擎帮助信息"""
        help_text = """
GLM HTTP AI引擎插件帮助信息
==========================

引擎名称: glm_http
描述: 基于HTTP协议的智谱AI GLM（GLM-4.5-Flash）引擎，支持智谱AI服务

可用命令:
  无特定命令，直接与AI对话即可

使用说明:
1. 此引擎使用HTTP协议调用智谱AI API
2. 使用/engine.switch glm_http切换到此引擎
3. 直接输入自然语言与AI对话
4. 支持普通对话、流式对话、JSON模式等多种调用方式
"""
        return help_text
    
    def __init__(self):
        self.name = "glm_http"
        self.cli = None
        
        # 直接从 config.json 读取配置
        config_file = os.path.join(project_root, "config.json")
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                engine_config = config.get("api", {}).get("engines", {}).get("GLM_http", {})
                self.api_key = engine_config.get("api_key", "")
                self.base_url = engine_config.get("base_url", "")
                self.model_id = engine_config.get("model", "")
        except Exception as e:
            # 如果读取失败，使用空值
            self.api_key = ""
            self.base_url = ""
            self.model_id = ""
        
        # 初始化对话历史
        self.conversation_history = []
        # 共享对话历史引用（由CLI设置）
        self.shared_conversation_history = None
        # 设置最大历史记录数
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.max_history = config.get("system", {}).get("max_history", 10)
        except:
            self.max_history = 10

        # 初始化 OpenAI 客户端（配置从 config.json 动态读取）
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url if self.base_url else None,
                timeout=None
            )
        except Exception as e:
            print(f"初始化 OpenAI 客户端失败: {e}")
            self.client = None
    
    def generate_response(self, user_input, tool_results=None, system_prompt=None):
        """生成AI響應 - 使用智谱AI HTTP API"""
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
                    return "智谱AI HTTP API調用失敗"
            
            # 構建包含歷史記錄的消息列表
            messages = self._build_messages_with_history(system_prompt, user_input)
            
            # 調用API
            response = self._call_api(messages)
            
            if response:
                return response
            else:
                return "智谱AI HTTP API調用失敗"
            
        except Exception as e:
            # 如果API調用失敗,返回錯誤信息
            return f"智谱AI HTTP API調用失敗: {str(e)}"
    
    def _call_api(self, messages, use_stream=False, extra_body=None):
        """調用API的核心方法"""
        if extra_body is None:
            extra_body = {}
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                stream=use_stream,
                temperature=0.7,
                max_tokens=4096,
                extra_headers={"lora_id": "0"},  # 調用微調大模型時,對應替換為模型服務卡片上的resourceId
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
            print(f"智谱AI HTTP API請求出錯: {e}")
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
            return "智谱AI HTTP API調用失敗"
    
    def handle_command(self, command):
        """處理引擎特定命令"""
        # GLM HTTP引擎目前不支持特定命令
        print(f"{Fore.RED}GLM HTTP引擎不支持此命令{Style.RESET_ALL}")
        return False