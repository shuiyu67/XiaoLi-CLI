"""OpenAI 格式模型连接器 —— 全系统唯一的模型调用路径。

引擎架构已删除（openai/ollama/manual 多引擎、MODEL_FIELDS、引擎发现都没了）。
一切模型都以 OpenAI 兼容格式配置（api_key / base_url / model + 限额 5+3），
ollama 等本地服务走其自带的 /v1 兼容口（如 http://localhost:11434/v1）。

本模块承接原 ai_engines/openai_engine.py 的全部调用逻辑（FC 探测缓存、
思考内容解析、历史构建、友好报错），对外保持旧引擎接口
（generate_response / current_model_name / set_registry_model ...），
使 cli_base / cli_core / tui / websocket / webui 的既有调用面零改动。
"""

import json
import logging
import os

import requests
from colorama import Fore, Style

try:
    from xcli_core.config import get_system_config
except Exception:
    def get_system_config(key, default=None):
        return default

try:
    from xcli_core import model_registry
except Exception:
    model_registry = None

try:
    from xcli_core.verbose import vprint
except Exception:
    def vprint(*args, **kwargs):
        pass

try:
    from xcli_core.tool_result import normalize_tool_text
except Exception:
    def normalize_tool_text(result, default="无结果"):
        if result is None:
            return default
        if isinstance(result, dict):
            return str(result.get("result", default))
        return str(result)

logger = logging.getLogger(__name__)

# ── 常见模型的上下文窗口（token 数）——仅当条目没填 max_input 时兜底查表 ──
MODEL_CONTEXT_WINDOWS = {
    "spark-4.0": 128000, "spark-max": 8192, "spark-pro": 8192, "spark-lite": 8192,
    "spark": 8192, "generalv3.5": 8192, "generalv3": 8192, "general": 4096,
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


class ModelConnection:
    """一个已配置模型 = 一条 OpenAI 格式连接。"""

    def __init__(self, name="default", entry=None):
        # entry 为空时应用注册表的当前模型（启动即用，对应旧引擎"init 吃注册表"语义）
        if entry is None and model_registry:
            try:
                cur = model_registry.get_model()
                if cur:
                    entry = cur
                    name = name or cur.get("name")
            except Exception:
                pass
        entry = entry or {}
        self.name = name or entry.get("name", "default")
        self.cli = None

        self.api_key = entry.get("api_key", "")
        self.base_url = (entry.get("base_url") or "").rstrip("/")
        self.model = entry.get("model", "")

        # ── 5+3 必填限额/能力（用户添加模型时录入）──
        try:
            self.max_input = int(entry.get("max_input") or 0)
        except (TypeError, ValueError):
            self.max_input = 0
        try:
            self.max_output = int(entry.get("max_output") or 0)
        except (TypeError, ValueError):
            self.max_output = 0
        self.image_input = bool(entry.get("image_input", False))
        self.video_input = bool(entry.get("video_input", False))
        self.audio_input = bool(entry.get("audio_input", False))

        # 对话历史
        self.conversation_history = []
        self.shared_conversation_history = None
        try:
            self.max_history = get_system_config("max_history", 10) or 10
        except Exception:
            self.max_history = 10

        # 最近一次请求的 token 用量（供 token 感知压缩使用）
        self.last_prompt_tokens = None

        # 思考标记（兼容深度思考模型）
        self.thinking_start_marker = "<think>"
        self.thinking_end_marker = "</think>"

        if not self.api_key and not self.base_url:
            vprint(f"{Fore.YELLOW}模型 [{self.name}] 未配置 api_key/base_url{Style.RESET_ALL}")

    # ── 模型注册表（多模型在线切换）──

    def current_model_name(self):
        """当前激活模型在注册表中的名称"""
        if not model_registry:
            return self.model
        try:
            models, current = model_registry.list_models()
            return current or self.model
        except Exception:
            return self.model

    def list_registry_models(self):
        if not model_registry:
            return [], None
        return model_registry.list_models()

    def set_registry_model(self, name):
        """切换到注册表中指定模型（含 base_url/api_key/model/限额）并持久化 current。"""
        if not model_registry:
            return False
        m = model_registry.get_model(name)
        if not m:
            return False
        self.name = m.get("name", name)
        self.api_key = m.get("api_key", "")
        self.base_url = (m.get("base_url") or "").rstrip("/")
        self.model = m.get("model", "")
        self.max_input = int(m.get("max_input") or 0)
        self.max_output = int(m.get("max_output") or 0)
        self.image_input = bool(m.get("image_input", False))
        self.video_input = bool(m.get("video_input", False))
        self.audio_input = bool(m.get("audio_input", False))
        model_registry.set_current(name)
        return True

    def add_model(self, entry):
        """新增/更新模型并持久化。entry: {name, base_url, api_key, model, max_input, ...}"""
        if not model_registry:
            return None
        return model_registry.add_model(entry)

    def remove_model(self, name):
        if not model_registry:
            return False
        return model_registry.remove_model(name)

    # ── 请求基础件 ──

    def _get_headers(self):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _get_api_url(self):
        url = self.base_url
        if not url:
            return ""
        if not url.endswith("/chat/completions"):
            url = url.rstrip("/") + "/chat/completions"
        return url

    # ── FC 能力探测缓存 ──

    def _fc_supported(self):
        """当前 (base_url, model) 是否支持 function calling（未探测过默认支持）"""
        try:
            from xcli_core.fc_tools import supports_fc
            return supports_fc(self.base_url, self.model)
        except Exception:
            return True

    def _mark_fc_unsupported(self):
        """降级成功后记住该模型不支持 FC，后续请求不再带 tools"""
        try:
            from xcli_core.fc_tools import mark_fc_unsupported
            if mark_fc_unsupported(self.base_url, self.model):
                print(f"{Fore.CYAN}已记住 {self.model} 不支持 FC，后续请求将跳过工具字段"
                      f"{Style.RESET_ALL}")
        except Exception:
            pass

    # ── 主调用 ──

    def generate_response(self, user_input, tool_results=None, system_prompt=None, tools=None):
        """生成 AI 响应（OpenAI chat.completions 格式，含 FC 与降级重试）"""
        try:
            if not self.base_url:
                return "错误: 模型的 base_url 未配置，请用 /model add 添加模型"

            if tool_results:
                tool_result_text = f"工具执行结果: {normalize_tool_text(tool_results)}"
                messages = self._build_messages_with_history(system_prompt, tool_result_text)
            else:
                messages = self._build_messages_with_history(system_prompt, user_input)

            body = {
                "model": self.model,
                "messages": messages,
                "stream": False,
            }
            if self.max_output:
                body["max_tokens"] = self.max_output

            # Function Calling：注入工具定义（已探测不支持的模型直接跳过）
            if tools and self._fc_supported():
                pure_tools = []
                for t in tools:
                    if not isinstance(t, dict):
                        continue
                    if t.get("type") == "function" and isinstance(t.get("function"), dict):
                        pure_tools.append(t)
                    elif isinstance(t.get("function"), dict):
                        pure_tools.append({"type": "function", "function": t["function"]})
                if pure_tools:
                    body["tools"] = pure_tools
                    body["tool_choice"] = "auto"

            api_url = self._get_api_url()
            response = requests.post(
                url=api_url,
                json=body,
                headers=self._get_headers(),
                timeout=None,
            )

            if response.status_code == 200:
                response_data = response.json()
                usage = response_data.get("usage", {})
                if isinstance(usage, dict) and usage.get("prompt_tokens"):
                    try:
                        self.last_prompt_tokens = int(usage["prompt_tokens"])
                    except (TypeError, ValueError):
                        self.last_prompt_tokens = None
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    message = response_data["choices"][0].get("message", {})

                    tool_calls_raw = message.get("tool_calls")
                    if tool_calls_raw:
                        from xcli_core.fc_tools import parse_fc_response
                        fc_calls = parse_fc_response(response_data)
                        if fc_calls:
                            return json.dumps({
                                "_fc": True,
                                "tool_calls": fc_calls,
                                "raw_message": message,
                            }, ensure_ascii=False)

                    ai_response = message.get("content", "")
                    if ai_response:
                        ai_response = ai_response.encode("utf-8", "replace").decode("utf-8")
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
                if body.get("tools") and "tools" in str(response.text).lower():
                    print(f"{Fore.YELLOW}FC 不支持，降级为普通模式{Style.RESET_ALL}")
                    body.pop("tools", None)
                    body.pop("tool_choice", None)
                    retry = requests.post(url=api_url, json=body, headers=self._get_headers(), timeout=None)
                    if retry.status_code == 200:
                        self._mark_fc_unsupported()
                        rd = retry.json()
                        if "choices" in rd and rd["choices"]:
                            ai_response = rd["choices"][0].get("message", {}).get("content", "")
                            return ai_response.encode("utf-8", "replace").decode("utf-8") if ai_response else ""
                return self._friendly_error(response.status_code, response)
            else:
                # 500 等错误：部分服务不支持 FC 工具会直接报 Invalid Params —— 去 tools 重试一次
                lower = str(response.text).lower()
                if body.get("tools") and ("xunfei" in lower or "invalid params" in lower or "requestparamserror" in lower):
                    print(f"{Fore.YELLOW}该接口可能不支持 FC 工具，降级为普通模式重试...{Style.RESET_ALL}")
                    body.pop("tools", None)
                    body.pop("tool_choice", None)
                    retry = requests.post(url=api_url, json=body, headers=self._get_headers(), timeout=None)
                    if retry.status_code == 200:
                        self._mark_fc_unsupported()
                        rd = retry.json()
                        retry_usage = rd.get("usage", {})
                        if isinstance(retry_usage, dict) and retry_usage.get("prompt_tokens"):
                            try:
                                self.last_prompt_tokens = int(retry_usage["prompt_tokens"])
                            except (TypeError, ValueError):
                                pass
                        if "choices" in rd and rd["choices"]:
                            ai_response = rd["choices"][0].get("message", {}).get("content", "")
                            ai_response = self._process_thinking_content(ai_response)
                            return ai_response.encode("utf-8", "replace").decode("utf-8") if ai_response else ""
                return self._friendly_error(response.status_code, response)

        except requests.exceptions.ConnectionError:
            return f"无法连接到 API 服务: {self.base_url}，请检查服务是否运行"
        except Exception as e:
            return f"API 调用失败: {str(e)}"

    def chat_completions(self, messages, tools=None, stream=False):
        """OpenAI 兼容代理用的直通口：messages 原样转发，流式原样透传 SSE 事件。"""
        base = self.base_url
        if not base:
            return {"error": "base_url 未配置"}
        body = {"model": self.model, "messages": messages, "stream": bool(stream)}
        if self.max_output:
            body["max_tokens"] = self.max_output
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        r = requests.post(base + "/chat/completions", json=body, headers=self._get_headers(),
                          stream=bool(stream), timeout=None)
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
        if stream:
            def events():
                for line in r.iter_lines(decode_unicode=True):
                    if line and line.startswith("data:"):
                        yield line
            return events()
        return r.json()

    def _build_messages_with_history(self, system_prompt, user_input):
        """构建包含历史记录的消息列表（支持 FC tool 消息）"""
        messages = []

        if system_prompt:
            clean_prompt = system_prompt.encode("utf-8", "replace").decode("utf-8")
            messages.append({"role": "system", "content": clean_prompt})

        if self.shared_conversation_history is not None:
            for msg in self.shared_conversation_history[-self.max_history:]:
                if not isinstance(msg, dict) or "role" not in msg:
                    continue

                role = msg["role"]

                if role == "tool":
                    tool_msg = {"role": "tool", "content": msg.get("content", "")}
                    if "tool_call_id" in msg:
                        tool_msg["tool_call_id"] = msg["tool_call_id"]
                    messages.append(tool_msg)
                    continue

                if role == "assistant" and "tool_calls" in msg:
                    messages.append({
                        "role": "assistant",
                        "content": msg.get("content") or "",
                        "tool_calls": self._pure_tool_calls(msg["tool_calls"]),
                    })
                    continue

                if "content" in msg:
                    clean_content = msg["content"]
                    if isinstance(clean_content, str):
                        clean_content = clean_content.encode("utf-8", "replace").decode("utf-8")
                    messages.append({"role": role, "content": clean_content})

        if user_input:
            clean_input = user_input.encode("utf-8", "replace").decode("utf-8")
            messages.append({"role": "user", "content": clean_input})

        return messages

    def _process_thinking_content(self, response):
        """处理思考内容，将思考部分以灰色文本显示"""
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

    @staticmethod
    def _friendly_error(status_code, response):
        """把错误响应里的可读信息提取出来，附带常见原因提示"""
        try:
            data = response.json()
            err = data.get("error", {})
            msg = err.get("message", "") if isinstance(err, dict) else ""
        except Exception:
            msg = ""
        if not msg:
            return f"API 调用失败: {status_code} - {response.text}"

        hint = ""
        low = str(msg).lower()
        if "invalid params" in low or "requestparamserror" in low or "xunfei" in low:
            hint = ("\n提示: 讯飞星火接口报'参数错误'，常见原因:"
                    "\n  1) model 名与 one-api/new-api 渠道里的模型映射不一致"
                    "\n  2) 该模型/渠道不支持 function calling（已尝试去掉 tools 重试）"
                    "\n  3) base_url 需为 OpenAI 兼容转发地址（如 one-api 的 https://域名/v1）")
        return f"API 调用失败: {status_code} - {msg}{hint}"

    @staticmethod
    def _pure_tool_calls(tool_calls):
        """把历史里的 tool_calls 重建成官方 OpenAI 格式，arguments 统一为字符串。"""
        pure = []
        for tc in (tool_calls or []):
            if not isinstance(tc, dict):
                continue
            func = tc.get("function")
            if isinstance(func, dict):
                name = func.get("name", tc.get("name", ""))
                args = func.get("arguments", "{}")
            else:
                name = tc.get("name", "")
                args = tc.get("arguments", "{}")
            if isinstance(args, str):
                args_str = args
            else:
                try:
                    args_str = json.dumps(args, ensure_ascii=False)
                except (TypeError, ValueError):
                    args_str = "{}"
            pure.append({
                "id": tc.get("id", f"call_{name}"),
                "type": "function",
                "function": {"name": name, "arguments": args_str},
            })
        return pure

    def set_model(self, model_name):
        """设置上游模型名（不是注册表条目名）"""
        self.model = model_name
        print(f"{Fore.GREEN}已切换模型为: {model_name}{Style.RESET_ALL}")

    def context_window(self):
        """最大输入（token）—— 用户添加模型时必填；旧条目兜底查表/128000。"""
        if self.max_input:
            return self.max_input
        model = (self.model or "").lower()
        for key, win in MODEL_CONTEXT_WINDOWS.items():
            if key and key in model:
                return win
        return 128000

    @property
    def max_input_tokens(self):
        """统一 API，供上下文压缩使用"""
        return self.context_window()

    def list_models(self):
        """列出上游服务可用模型（调用 /models 端点）"""
        if not self.base_url:
            return ["错误: base_url 未配置"]

        try:
            models_url = self.base_url.rstrip("/")
            if models_url.endswith("/chat/completions"):
                models_url = models_url[:-len("/chat/completions")]
            models_url = models_url.rstrip("/") + "/models"

            response = requests.get(url=models_url, headers=self._get_headers(), timeout=10)

            if response.status_code == 200:
                data = response.json()
                if "data" in data:
                    return [m.get("id", "unknown") for m in data["data"]]
                return ["API 返回格式不标准，无法解析模型列表"]
            return [f"获取模型列表失败: {response.status_code}"]
        except Exception as e:
            return [f"获取模型列表失败: {str(e)}"]

    def handle_command(self, command):
        """处理连接特定命令（/engine.<名> ... 兼容口）"""
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
            print(f"{Fore.RED}请提供模型名称. 用法: /engine.{self.name} set <模型名>{Style.RESET_ALL}")
            return False

        elif command == "info":
            print(f"{Fore.GREEN}模型连接配置:{Style.RESET_ALL}")
            print(f"  名称:     {self.name}")
            print(f"  base_url: {self.base_url}")
            print(f"  model:    {self.model}")
            print(f"  api_key:  {'已设置' if self.api_key else '未设置'}")
            print(f"  限额:     输入 {self.context_window()} / 输出 {self.max_output or '默认'}")
            caps = [n for n, on in (("图片", self.image_input), ("视频", self.video_input),
                                    ("音频", self.audio_input)) if on]
            print(f"  能力:     {'/'.join(caps) if caps else '纯文本'}")
            return True

        else:
            print(f"{Fore.RED}未知命令. 可用命令: models, set, info{Style.RESET_ALL}")
            return False
