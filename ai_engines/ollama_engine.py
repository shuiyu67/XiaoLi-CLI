import os
import sys
import json
import requests
import threading
import time
from colorama import Fore, Style

# 延迟导入 ollama，避免程序启动时卡住
# 如果导入失败，ollama_client 将为 None
try:
    import ollama
    ollama_client = ollama
except Exception as e:
    print(f"{Fore.YELLOW}警告: 无法导入 ollama 库: {e}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}请确保已安装 ollama 包 (pip install ollama){Style.RESET_ALL}")
    ollama_client = None

# 添加项目根目录到sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)


class OllamaAI:
    """基于Ollama的本地AI引擎"""
    requires_api_key = False  # Ollama是本地引擎，不需要API密钥
    
    def get_help_info(self):
        """获取引擎帮助信息"""
        help_text = """
Ollama AI引擎插件帮助信息
========================

引擎名称: Ollama
描述: 基于Ollama的本地AI引擎,支持多种大型语言模型

可用命令:
  /engine.ollama models     - 列出本地可用的模型
  /engine.ollama remote-models - 显示可下载的模型列表
  /engine.ollama search <关键词> - 搜索可下载的模型
  /engine.ollama set <模型名> - 设置当前使用的模型
  /engine.ollama pull <模型名> - 从Ollama库拉取模型

注意: 本引擎强制使用流式输出，AI回复会实时显示。

使用说明:
1. 确保Ollama服务已在本地运行
2. 使用/engine.switch ollama切换到此引擎
3. 使用上述命令管理模型和与AI交互

思考模式:
  - 支持深度思考模型（如 QwQ、DeepSeek-R1）
  - 思考过程会自动以灰色文本显示
"""
        return help_text
    
    def __init__(self):
        self.name = "ollama"
        self.cli = None  # 引用CLI实例以访问插件
        # 初始化对话历史
        self.conversation_history = []
        
        # 直接从 config.json 读取配置
        config_file = os.path.join(project_root, "config.json")
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                engine_config = config.get("api", {}).get("engines", {}).get("ollama", {})
                self.api_key = engine_config.get("api_key", "")
                self.base_url = engine_config.get("base_url", "")
                self.model = engine_config.get("model", "")
                self.max_history = config.get("system", {}).get("max_history", 10)
        except Exception as e:
            # 如果读取失败，使用空值
            self.api_key = ""
            self.base_url = ""
            self.model = ""
            self.max_history = 10
        
        # 共享对话历史引用（由CLI设置）
        self.shared_conversation_history = None
        
        # 直接启用思考标记，由主程序自动处理深度思考模型的响应
        self.thinking_start_marker = "<thinking>"
        self.thinking_end_marker = "</thinking>"

        # 检测Ollama服务是否运行
        self.is_service_running = self.check_ollama_service()
        
        if self.is_service_running:
            print(f"{Fore.GREEN}Ollama服务检测成功,引擎已启用{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Ollama服务未运行,引擎将不可用{Style.RESET_ALL}")
    
    def check_ollama_service(self):
        """检测Ollama服务是否运行"""
        # 检查 ollama 库是否可用
        if ollama_client is None:
            return False
        try:
            # 尝试调用Ollama API获取版本信息
            response = ollama_client.list()
            # 如果没有异常,说明服务运行正常
            return True
        except Exception as e:
            # 如果出现异常,说明服务未运行
            return False
    
    def generate_response(self, user_input, tool_results=None, system_prompt=None):
        """生成AI响应 - 使用Ollama API"""
        try:
            # 检查Ollama服务是否运行
            if not self.is_service_running:
                return "错误:Ollama服务未运行,请启动Ollama服务后再使用此引擎."
            
            # 如果有工具结果,将其作为上下文返回给AI处理
            if tool_results:
                tool_result_text = f"工具执行结果: {tool_results.get('result', '无结果')}"
                # 构建包含历史记录的消息列表
                messages = self._build_messages_with_history(system_prompt, tool_result_text)
                
                # 使用Ollama Python库调用API
                response = ollama_client.chat(
                    model=self.model,
                    messages=messages,
                    stream=False
                )
                
                # 返回AI的回复
                return response["message"]["content"]
            
            # 构建包含历史记录的消息列表
            messages = self._build_messages_with_history(system_prompt, user_input)
            
            # 使用Ollama Python库调用API
            response = ollama_client.chat(
                model=self.model,
                messages=messages,
                stream=False
            )
            
            # 返回AI的回复
            content = response["message"]["content"]
            # 清理无效的 UTF-8 代理字符
            content = content.encode('utf-8', 'replace').decode('utf-8')
            return content
            
        except Exception as e:
            # 如果API调用失败,返回错误信息
            return f"Ollama API调用失败: {str(e)}"

    def _build_messages_with_history(self, system_prompt, user_input):
        """构建包含历史记录的消息列表"""
        messages = []
        
        # 添加系统提示词
        if system_prompt:
            # 清理代理字符
            clean_prompt = system_prompt.encode('utf-8', 'replace').decode('utf-8')
            messages.append({
                "role": "system",
                "content": clean_prompt
            })
        
# 添加历史对话记录（使用共享历史）
        if self.shared_conversation_history is not None:
            # 确保历史记录格式正确
            for msg in self.shared_conversation_history[-self.max_history:]:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    # 清理内容中的代理字符
                    clean_content = msg["content"].encode('utf-8', 'replace').decode('utf-8')
                    messages.append({"role": msg["role"], "content": clean_content})
                else:
                    # 如果格式不正确，跳过该条记录
                    continue
        
        # 清理用户输入
        if user_input:
            clean_input = user_input.encode('utf-8', 'replace').decode('utf-8')
            messages.append({
                "role": "user",
                "content": clean_input
            })
        
        return messages
    
    
    
    def _call_api_with_history(self, content, system_prompt=None):
        """使用对话历史调用API"""
        if not self.is_service_running:
            return "错误:Ollama服务未运行,请启动Ollama服务后再使用此引擎."
        
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
        
        # 使用Ollama Python库调用API
        response = ollama_client.chat(
            model=self.model,
            messages=messages,
            stream=False
        )
        
        return response["message"]["content"]
    
    def set_model(self, model_name):
        """设置要使用的模型"""
        if not self.is_service_running:
            print(f"{Fore.RED}错误:Ollama服务未运行,无法切换模型{Style.RESET_ALL}")
            return
        
        self.model = model_name
        print(f"{Fore.GREEN}已切换Ollama模型为: {model_name}{Style.RESET_ALL}")
    
    def list_models(self):
        """列出本地可用的模型"""
        if not self.is_service_running:
            return ["错误:Ollama服务未运行"]
        
        try:
            response = ollama_client.list()
            models = [model["name"] for model in response["models"]]
            return models
        except Exception as e:
            return [f"获取模型列表失败: {str(e)}"]
    
    def list_remote_models(self, limit=10):
        """获取可下载的模型列表(仅展示前N个)"""
        if not self.is_service_running:
            return ["错误:Ollama服务未运行"]
        
        try:
            # 使用Ollama Python库获取可下载的模型列表
            # 注意:Ollama库本身没有直接获取可下载模型列表的API
            # 这里返回一些常见的模型作为示例
            # 实际应用中可能需要从Ollama官网或其他来源获取此信息
            common_models = [
                "llama3.1:latest",
                "llama3:latest", 
                "mistral:latest",
                "gemma2:latest",
                "phi3:latest",
                "qwen2:latest",
                "command-r:latest",
                "dolphin-mistral:latest",
                "nous-hermes2:latest",
                "llava:latest",
                "codellama:latest",
                "mxbai-embed-large:latest",
                "all-minilm:latest",
                "stable-diffusion:latest",
                "moondream:latest"
            ]
            return common_models[:limit]
        except Exception as e:
            return [f"获取远程模型列表失败: {str(e)}"]
    
    def search_models(self, query, limit=10):
        """模糊搜索可下载的模型"""
        if not self.is_service_running:
            return ["错误:Ollama服务未运行"]
        
        try:
            # 使用Ollama Python库获取可下载的模型列表
            # 注意:Ollama库本身没有直接获取可下载模型列表的API
            all_models = [
                "llama3.1:latest", "llama3:latest", "llama2:latest",
                "mistral:latest", "mistral-openorca:latest",
                "gemma2:latest", "gemma:latest",
                "phi3:latest", "phi2:latest",
                "qwen2:latest", "qwen:latest",
                "command-r:latest", "command-r-plus:latest",
                "dolphin-mistral:latest", "dolphin-llama3:latest",
                "nous-hermes2:latest", "nous-hermes:latest",
                "llava:latest", "bakllava:latest",
                "codellama:latest", "codeup:latest",
                "mxbai-embed-large:latest", "nomic-embed-text:latest",
                "all-minilm:latest", "bge-m3:latest",
                "stable-diffusion:latest", "moondream:latest",
                "llama3-groq:latest", "eva-qwen2:latest"
            ]
            
            # 进行模糊搜索(简单匹配,包含查询词的模型)
            matched_models = [model for model in all_models if query.lower() in model.lower()]
            
            # 限制返回数量
            return matched_models[:limit]
        except Exception as e:
            return [f"搜索模型失败: {str(e)}"]
    
    def pull_model(self, model_name):
        """从Ollama库拉取模型"""
        if not self.is_service_running:
            print(f"{Fore.RED}错误:Ollama服务未运行,无法拉取模型{Style.RESET_ALL}")
            return False
        
        try:
            print(f"{Fore.YELLOW}正在拉取模型 {model_name}...{Style.RESET_ALL}")
            
            # 使用Ollama Python库拉取模型
            response = ollama_client.pull(model_name, stream=True)
            
            # 逐块处理响应
            for part in response:
                if 'status' in part:
                    status = part['status']
                    print(f"{Fore.YELLOW}{status}{Style.RESET_ALL}")
                    # 检查是否完成
                    if 'completed' in part and 'total' in part:
                        if part['completed'] == part['total']:
                            print(f"{Fore.GREEN}模型 {model_name} 拉取完成!{Style.RESET_ALL}")
            
            print(f"{Fore.GREEN}模型 {model_name} 拉取成功!{Style.RESET_ALL}")
            return True
        except Exception as e:
            print(f"{Fore.RED}拉取模型 {model_name} 失败: {str(e)}{Style.RESET_ALL}")
            return False
    
    def handle_command(self, command):
        """处理引擎特定命令"""
        if not self.is_service_running:
            print(f"{Fore.RED}Ollama服务未运行,无法执行命令{Style.RESET_ALL}")
            return False
        
        if command == "models":
            # 显示本地可用模型
            models = self.list_models()
            print(f"{Fore.GREEN}本地可用的Ollama模型:{Style.RESET_ALL}")
            for model in models:
                status = " (当前使用)" if model == self.model else ""
                print(f"{Fore.GREEN}  - {model}{status}{Style.RESET_ALL}")
            return True
        
        elif command == "remote-models":
            # 显示可下载的模型(前10个)
            models = self.list_remote_models()
            print(f"{Fore.GREEN}可下载的Ollama模型(前10个):{Style.RESET_ALL}")
            for i, model in enumerate(models, 1):
                print(f"{Fore.GREEN}  {i}. {model}{Style.RESET_ALL}")
            return True
        
        elif command.startswith("search "):
            # 搜索模型
            query = command[7:].strip()  # 移除 'search '
            if query:
                models = self.search_models(query)
                if models:
                    print(f"{Fore.GREEN}搜索 '{query}' 的结果(前10个):{Style.RESET_ALL}")
                    for i, model in enumerate(models, 1):
                        print(f"{Fore.GREEN}  {i}. {model}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}未找到与 '{query}' 匹配的模型{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.RED}请提供搜索关键词.用法: /engine.search <关键词>{Style.RESET_ALL}")
                return False
        
        elif command.startswith("set "):
            # 设置模型
            model_name = command[4:].strip()  # 移除 'set '
            if model_name:
                self.set_model(model_name)
                return True
            else:
                print(f"{Fore.RED}请提供模型名称.用法: /engine.set <模型名>{Style.RESET_ALL}")
                return False
        
        elif command.startswith("pull "):
            # 拉取模型
            model_name = command[5:].strip()  # 移除 'pull '
            if model_name:
                success = self.pull_model(model_name)
                return success
            else:
                print(f"{Fore.RED}请提供模型名称.用法: /engine.pull <模型名>{Style.RESET_ALL}")
                return False
        
        else:
            print(f"{Fore.RED}未知的Ollama命令.可用命令: models, remote-models, search, set, pull{Style.RESET_ALL}")
            return False