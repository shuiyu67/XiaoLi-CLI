"""
Provider 抽象层（opencode 式原生多 Provider 路由）

小狸核心是 OpenAI 兼容的统一连接器 ModelConnection（已支持 base_url，讯飞/xunfei 即借此接入）。
本模块在此基础上提供：
  - PROVIDER_PRESETS：主流 Provider 的默认 base_url / 模型前缀 / 协议族
  - resolve_provider()：从 config["providers"] 解析出 {api_key, base_url, model, headers}
  - convert_messages() / convert_tools()：OpenAI ↔ Anthropic ↔ Google 线缆格式互转（纯函数）
  - list_providers()：给 /providers 命令用的汇总

设计原则：纯函数 + 配置驱动，不触网、不强求真实 key，不改动现有 engine 行为。
真实调用仍由 ModelConnection 在用户填入 base_url/api_key 后完成（OpenAI 兼容族直接可用；
非兼容族可借助 convert_* 在 engine 层二次适配，本模块只负责「翻译」与「注册」）。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

# ───────────────────────── Provider 预设 ─────────────────────────
# protocol: openai 兼容 | anthropic | google
PROVIDER_PRESETS: Dict[str, Dict[str, Any]] = {
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "protocol": "openai",
        "models": ["gpt-4o", "gpt-4o-mini", "o1", "o3-mini"],
        "env_key": "OPENAI_API_KEY",
    },
    "anthropic": {
        "label": "Anthropic Claude",
        "base_url": "https://api.anthropic.com/v1",
        "protocol": "anthropic",
        "models": ["claude-opus-4", "claude-sonnet-4", "claude-3-5-sonnet"],
        "env_key": "ANTHROPIC_API_BASE",
    },
    "google": {
        "label": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "protocol": "google",
        "models": ["gemini-2.0-pro", "gemini-2.0-flash", "gemini-1.5-pro"],
        "env_key": "GEMINI_API_KEY",
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "protocol": "openai",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "env_key": "DEEPSEEK_API_KEY",
    },
    "moonshot": {
        "label": "Moonshot (Kimi)",
        "base_url": "https://api.moonshot.cn/v1",
        "protocol": "openai",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k"],
        "env_key": "MOONSHOT_API_KEY",
    },
    "qwen": {
        "label": "阿里通义千问",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "protocol": "openai",
        "models": ["qwen-max", "qwen-plus", "qwen-turbo"],
        "env_key": "DASHSCOPE_API_KEY",
    },
    "xunfei": {
        "label": "讯飞开放平台",
        "base_url": "https://spark-api-open.xf-yun.com/v1",
        "protocol": "openai",
        "models": ["generalv3.5", "generalv4"],
        "env_key": "XUNFEI_API_KEY",
    },
    "ollama": {
        "label": "Ollama (本地)",
        "base_url": "http://localhost:11434/v1",
        "protocol": "openai",
        "models": ["qwen2.5", "llama3.1", "deepseek-r1"],
        "env_key": "",
    },
}

# 协议族 → 该族内「消息格式」标识（转换时使用）
_PROTOCOL_FORMAT = {
    "openai": "openai",
    "anthropic": "anthropic",
    "google": "google",
}


def get_provider_preset(name: str) -> Optional[Dict[str, Any]]:
    return PROVIDER_PRESETS.get(name)


def list_providers() -> List[str]:
    return list(PROVIDER_PRESETS.keys())


def resolve_provider(name: str, providers_cfg: Optional[Dict[str, Any]] = None,
                     env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """从 config["providers"][name] 解析出连接参数。

    优先级：providers_cfg 显式字段 > 环境变量 > 预设默认值。
    返回：{name, label, base_url, api_key, model, protocol, headers}
    缺失 api_key 时 api_key 为空字符串（调用层据此判断是否配置完成）。
    """
    preset = PROVIDER_PRESETS.get(name)
    if preset is None:
        return {}
    env = env if env is not None else dict(os.environ)
    cfg = (providers_cfg or {}).get(name, {}) if providers_cfg else {}

    api_key = cfg.get("api_key") or (env.get(preset["env_key"]) if preset["env_key"] else "")
    base_url = cfg.get("base_url") or preset["base_url"]
    model = cfg.get("model") or (preset["models"][0] if preset["models"] else "")
    protocol = preset["protocol"]

    headers: Dict[str, str] = {}
    # Anthropic 需要 beta header与协议版本（即便走 OpenAI 代理也保留以便真实适配）
    if protocol == "anthropic":
        headers["anthropic-version"] = "2023-06-01"
    # Google 的 Gemini OpenAI 兼容端点需要把 key 放 query/header，这里统一放 header
    if protocol == "google" and api_key:
        headers["x-goog-api-key"] = api_key

    return {
        "name": name,
        "label": preset["label"],
        "base_url": base_url,
        "api_key": api_key or "",
        "model": model,
        "protocol": protocol,
        "headers": headers,
    }


def _wire_format(protocol: str) -> str:
    return _PROTOCOL_FORMAT.get(protocol, "openai")


# ───────────────────────── 消息格式互转 ─────────────────────────
def convert_messages(target: str, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """把小狸内部 OpenAI 风格 messages 转换为 target provider 的线缆格式。

    target ∈ {"openai", "anthropic", "google"}
    内部统一表示：[{"role": "system"|"user"|"assistant"|"tool", "content": ..., "tool_calls"?, "name"?}]
    - anthropic：system 抽成顶层；user/assistant 交替，content 包装为 blocks
    - google：system 抽成 systemInstruction；content 包装为 parts
    纯转换，不调用网络。
    """
    fmt = _wire_format(target) if target in _PROTOCOL_FORMAT.values() else _wire_format(target)
    if fmt == "openai":
        return [_normalize_openai(m) for m in messages]
    if fmt == "anthropic":
        return _to_anthropic(messages)
    if fmt == "google":
        return _to_google(messages)
    return [_normalize_openai(m) for m in messages]


def _normalize_openai(m: Dict[str, Any]) -> Dict[str, Any]:
    """确保 content 为字符串（统一线缆格式），保留 role/tool_calls/name。"""
    out = {"role": m.get("role", "user")}
    content = m.get("content")
    if content is None:
        content = ""
    if isinstance(content, list):
        # 多模态 blocks → 拼接文本
        text = "".join(p.get("text", "") for p in content if isinstance(p, dict))
        content = text
    out["content"] = content
    if "tool_calls" in m:
        out["tool_calls"] = m["tool_calls"]
    if "name" in m:
        out["name"] = m["name"]
    return out


def _to_anthropic(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Anthropic Messages API 格式：system 单独抽离，消息为 user/assistant 交替。"""
    out: List[Dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        if role == "system":
            continue  # 顶层 system 由调用方单独处理
        content = m.get("content", "")
        blocks = []
        if isinstance(content, list):
            for p in content:
                if isinstance(p, dict) and p.get("type") == "text":
                    blocks.append({"type": "text", "text": p.get("text", "")})
                elif isinstance(p, dict) and p.get("type") == "image":
                    blocks.append(p)
        else:
            blocks.append({"type": "text", "text": str(content)})
        out.append({"role": "user" if role in ("user", "tool") else "assistant",
                    "content": blocks})
    return out


def _to_google(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Google Gemini 格式：system 抽为 systemInstruction，消息为 content.parts。"""
    out: List[Dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        if role == "system":
            continue
        content = m.get("content", "")
        parts = []
        if isinstance(content, list):
            for p in content:
                if isinstance(p, dict) and p.get("type") == "text":
                    parts.append({"text": p.get("text", "")})
                elif isinstance(p, dict) and p.get("type") == "image":
                    parts.append(p)
        else:
            parts.append({"text": str(content)})
        out.append({"role": "user" if role in ("user", "tool") else "model",
                    "parts": parts})
    return out


def convert_tools(target: str, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """把 OpenAI FC tools([{type, function:{name,description,parameters}}]) 转目标格式。

    - openai：原样
    - anthropic：tools=[{name, description, input_schema}]
    - google：tools=[{functionDeclarations:[{name,description,parameters}]}]
    """
    fmt = _wire_format(target)
    if fmt == "openai":
        return tools
    if fmt == "anthropic":
        out = []
        for t in tools:
            fn = t.get("function", {})
            out.append({
                "name": fn.get("name", ""),
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
            })
        return out
    if fmt == "google":
        decls = []
        for t in tools:
            fn = t.get("function", {})
            decls.append({
                "name": fn.get("name", ""),
                "description": fn.get("description", ""),
                "parameters": fn.get("parameters", {"type": "object", "properties": {}}),
            })
        return [{"functionDeclarations": decls}] if decls else []
    return tools


def provider_summary(name: str, providers_cfg: Optional[Dict[str, Any]] = None,
                     env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """给 /providers 命令用的单条汇总（是否配置、协议、模型数）。"""
    preset = PROVIDER_PRESETS.get(name)
    if not preset:
        return {}
    resolved = resolve_provider(name, providers_cfg, env)
    configured = bool(resolved.get("api_key"))
    return {
        "name": name,
        "label": preset["label"],
        "protocol": preset["protocol"],
        "configured": configured,
        "model_count": len(preset["models"]),
        "base_url": resolved.get("base_url", ""),
    }
