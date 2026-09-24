"""模型配置系统 —— "直接配置模型"（用户面对的单位是模型，引擎只是调用格式）

数据模型（config.json）:
  "models": {
    "deepseek-v3": {
      "engine": "openai",              # 调用格式（=引擎），自研引擎丢 ai_engines/ 即出现
      "fields": { "api_key": "...", "base_url": "...", "model": "deepseek-chat" },
      "default": true
    }
  }

引擎（=调用格式）声明自己的字段 schema（MODEL_FIELDS），由本模块的
ask_field() 统一收集（CLI 询问 / TUI 输入盒都走这个口），引擎作者不用写交互。
自研引擎契约（新式）：模块内定义
    MODEL_FIELDS = [{"key", "label", "hint", "secret", "default", "required"}, ...]
    def chat_completions(fields, messages, tools=None, stream=False):
        # 按 OpenAI chat.completions 语义返回 dict / SSE 事件行迭代器
旧式引擎（generate_response）继续被旧 agent 循环使用，不受影响。
"""

import importlib.util
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINES_DIR = os.path.join(PROJECT_ROOT, "ai_engines")
CONFIG_FILE = os.path.join(PROJECT_ROOT, "config.json")


# ── 内置调用格式的字段 schema（自研引擎用模块内 MODEL_FIELDS 覆盖）──

BUILTIN_FIELDS = {
    "openai": [
        {"key": "api_key", "label": "API 密钥", "secret": True, "required": True,
         "hint": "DeepSeek / Kimi / OpenAI 等服务发的密钥（形如 sk-...）"},
        {"key": "base_url", "label": "Base URL", "default": "https://api.deepseek.com/v1",
         "hint": "API 地址，不带 /chat/completions（DeepSeek 填 https://api.deepseek.com/v1）"},
        {"key": "model", "label": "模型名", "required": True,
         "hint": "服务上的模型标识，如 deepseek-chat / kimi-k2 / gpt-4o"},
    ],
    "ollama": [
        {"key": "base_url", "label": "Ollama 地址", "default": "http://localhost:11434",
         "hint": "本地 Ollama 服务地址，一般不用改"},
        {"key": "model", "label": "模型名", "required": True,
         "hint": "ollama list 里显示的名字，如 gemma4:31b"},
        {"key": "max_token_k", "label": "上下文(K)", "default": "32",
         "hint": "上下文窗口大小（K token），不知道就用默认 32"},
    ],
}

# 可走代理的调用格式（manual 是人工交互引擎，不进模型体系）
PROXY_ENGINES = {"openai", "ollama"}


# ── 配置读写 ──

def load_full_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_full_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def list_models():
    """返回 [(name, info)]，只含已配置好的模型"""
    cfg = load_full_config()
    models = cfg.get("models") or {}
    return sorted(models.items())


def get_model(name):
    cfg = load_full_config()
    return (cfg.get("models") or {}).get(name)


def default_model_name():
    for name, info in list_models():
        if info.get("default"):
            return name
    models = list_models()
    return models[0][0] if models else None


def save_model(name, engine, fields, is_default=False):
    cfg = load_full_config()
    models = cfg.setdefault("models", {})
    if is_default:
        for m in models.values():
            m.pop("default", None)
    models[name] = {"engine": engine, "fields": fields, "default": bool(is_default)}
    save_full_config(cfg)
    return models[name]


def remove_model(name):
    cfg = load_full_config()
    if (cfg.get("models") or {}).pop(name, None) is not None:
        save_full_config(cfg)
        return True
    return False


def migrate_legacy_engines():
    """旧 config 的 api.engines.<name> 自动迁移成 models 条目（幂等）"""
    cfg = load_full_config()
    engines = ((cfg.get("api") or {}).get("engines") or {})
    models = cfg.setdefault("models", {})
    changed = False
    for name, ecfg in engines.items():
        if name not in PROXY_ENGINES or name in models:
            continue
        fields = {k: v for k, v in (ecfg or {}).items()
                  if k in {f["key"] for f in get_engine_fields(name)}}
        if not fields.get("model"):
            continue
        is_first = not models
        models[f"{name}-{fields.get('model', 'default')}".replace(":", "-")] = {
            "engine": name, "fields": fields, "default": is_first}
        changed = True
    if changed:
        save_full_config(cfg)
    return changed


# ── 引擎（调用格式）发现 ──

def discover_engines():
    """扫描 ai_engines/：返回 [(engine_id, label)]，自研 *_engine.py 自动出现"""
    out = []
    if not os.path.isdir(ENGINES_DIR):
        return out
    for fn in sorted(os.listdir(ENGINES_DIR)):
        if not fn.endswith("_engine.py"):
            continue
        eid = fn[:-len("_engine.py")]
        if eid not in PROXY_ENGINES:
            continue          # 新式协议适配只放行已知格式；自研需带 chat_completions
        fields = get_engine_fields(eid)
        label = eid
        try:
            mod = _load_engine_module(eid)
            label = getattr(mod, "ENGINE_LABEL", eid)
        except Exception:
            pass
        out.append((eid, label, fields))
    return out


def discover_engines_with_custom():
    """含自研新式引擎（带 MODEL_FIELDS + chat_completions 的模块全收）"""
    out = []
    if not os.path.isdir(ENGINES_DIR):
        return out
    for fn in sorted(os.listdir(ENGINES_DIR)):
        if not fn.endswith("_engine.py"):
            continue
        eid = fn[:-len("_engine.py")]
        try:
            mod = _load_engine_module(eid)
        except Exception:
            continue
        fields = getattr(mod, "MODEL_FIELDS", BUILTIN_FIELDS.get(eid))
        has_chat = callable(getattr(mod, "chat_completions", None))
        if fields is None and not has_chat:
            continue
        label = getattr(mod, "ENGINE_LABEL", eid)
        out.append((eid, label, fields or [], has_chat))
    return out


def get_engine_fields(engine_id):
    """引擎字段 schema：模块 MODEL_FIELDS 优先，否则内置默认"""
    try:
        mod = _load_engine_module(engine_id)
        mf = getattr(mod, "MODEL_FIELDS", None)
        if mf:
            return list(mf)
    except Exception:
        pass
    return list(BUILTIN_FIELDS.get(engine_id, []))


_engine_mods = {}


def _load_engine_module(engine_id):
    if engine_id in _engine_mods:
        return _engine_mods[engine_id]
    path = os.path.join(ENGINES_DIR, f"{engine_id}_engine.py")
    spec = importlib.util.spec_from_file_location(f"ai_engines.{engine_id}_engine", path)
    mod = importlib.util.module_from_spec(spec)
    # 新式引擎模块可能是轻量协议适配（无旧式依赖），失败也允许只用字段
    spec.loader.exec_module(mod)
    _engine_mods[engine_id] = mod
    return mod


# ── 统一收集（CLI / TUI 都走这个口）──

def ask_field(field, ask=None):
    """按字段 schema 向用户收集一个值。
    ask(prompt, default, secret) -> str 可注入（TUI 用输入盒；缺省用 CLI input）。"""
    if ask is None:
        ask = _cli_ask
    while True:
        val = ask(field.get("hint") or field["label"],
                  str(field.get("default", "")), bool(field.get("secret")))
        val = (val or "").strip()
        if not val and field.get("default") is not None:
            val = str(field["default"])
        if field.get("required") and not val:
            print(f"  这项必填：{field['label']}")
            continue
        return val


def _cli_ask(prompt, default, secret):
    suffix = f" [{default}]" if default else ""
    try:
        if secret:
            import getpass
            return getpass.getpass(f"  ? {prompt}{suffix}: ")
        return input(f"  ? {prompt}{suffix}: ")
    except (EOFError, KeyboardInterrupt):
        return default


def add_model_wizard(ask=None, engine_id=None, model_name=None):
    """添加模型全流程：选格式 → 按 schema 填值 → 起名 → 测试 → 可设默认。
    返回 (ok, message)。参数留空则交互询问（新手化：全有默认可跳）。"""
    engines = discover_engines_with_custom()
    if not engines:
        return False, "ai_engines/ 里没有可用的调用格式"

    # 2. 选引擎（=调用格式）
    if engine_id is None:
        print("  可用调用格式（引擎）:")
        for i, (eid, label, _f, _c) in enumerate(engines, 1):
            print(f"    {i}. {eid} —— {label}")
        raw = (ask or _cli_ask)("选择格式（编号或名字，回车=1）", "1", False).strip()
        idx = int(raw) - 1 if raw.isdigit() and 1 <= int(raw) <= len(engines) else 0
        engine_id = engines[idx][0]
    fields_schema = get_engine_fields(engine_id)

    # 3. 按引擎 schema 收集字段（ask_field 统一口）
    print(f"\n  配置 [{engine_id}] 的连接信息（密钥输入隐藏，全有默认值）:")
    fields = {}
    for f in fields_schema:
        fields[f["key"]] = ask_field(f, ask)

    # 4.（补全步骤）起名 + 连通测试 + 设默认
    if model_name is None:
        guess = fields.get("model", "") or engine_id
        model_name = (ask or _cli_ask)("给这个模型起个显示名", guess, False).strip() or guess

    ok, msg = test_model(engine_id, fields)
    print(f"  连通测试: {'✓ ' + msg if ok else '✗ ' + msg + '（仍可保存，稍后可改）'}")

    is_default = False
    if not default_model_name():
        is_default = True
        print("  已设为默认模型（当前还没有其他模型）")
    else:
        ans = (ask or _cli_ask)("设为默认模型? (y/N)", "n", False).strip().lower()
        is_default = ans in ("y", "yes")

    save_model(model_name, engine_id, fields, is_default)
    return True, f"模型 [{model_name}] 创建成功（格式: {engine_id}）"


def test_model(engine_id, fields):
    """连通性测试：发一句最小问候，验证配置可用"""
    try:
        mod = _load_engine_module(engine_id)
        chat = getattr(mod, "chat_completions", None)
        if not callable(chat):
            return True, "该格式无内置测试，跳过"
        resp = chat(fields, [{"role": "user", "content": "你好"}], tools=None, stream=False)
        if isinstance(resp, dict) and (resp.get("choices") or resp.get("error")):
            if resp.get("error"):
                return False, str(resp["error"])[:120]
            return True, "连接正常"
        return True, "已发送测试请求"
    except Exception as e:
        return False, str(e)[:120]
