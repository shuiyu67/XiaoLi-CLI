"""OpenAI 格式模型注册表。

把「多个 OpenAI 格式模型」从 config.json 的单槽位升级为可管理的列表，
支持在线增删、切换、持久化，免去每次手改配置文件。

配置结构（api.engines.openai）:
    {
      "models": [
        {"name": "讯飞xop", "base_url": "...", "api_key": "...", "model": "xophunyuan7bmt"},
        {"name": "gpt4o",   "base_url": "https://api.openai.com/v1", "api_key": "...", "model": "gpt-4o"}
      ],
      "current": "讯飞xop"
    }

向后兼容：若没有 models 列表，把扁平的 api_key/base_url/model 当作单条隐式模型，
其 name 取 model 值（空则 "default"）。
"""

from xcli_core.config import load_config, save_config

# ── 模型能力/限额字段（添加模型时必须由用户输入；旧条目自动补默认）──

MODEL_EXTRA_DEFAULTS = {
    "max_input": 32768,        # 最大输入（token）
    "max_output": 4096,        # 最大输出（token）
    "image_input": False,      # 支持图片输入
    "video_input": False,      # 支持视频输入
    "audio_input": False,      # 支持音频输入
}


def with_defaults(m):
    """补齐新字段（不动已有值）"""
    out = dict(m)
    for k, v in MODEL_EXTRA_DEFAULTS.items():
        out.setdefault(k, v)
    return out


def migrate_legacy():
    """把旧『引擎架构』时代的配置迁移成扁平 OpenAI 格式模型条目（幂等）。

    覆盖两种旧形：
      1) cfg["models"] = {name: {engine, fields, default}}（已删的 model_config 形态）
      2) api.engines.<engine> 扁平单槽（含 ollama 的旧地址/max_token_k）
    ollama 条目统一改走 /v1 兼容口。迁移完成后旧数据移除。
    """
    cfg = _load()
    changed = False

    # ── 1) model_config 形态：cfg["models"] 是 dict ──
    old_models = cfg.get("models")
    if isinstance(old_models, dict) and old_models:
        block = _openai_block(cfg)
        items = block.get("models") or []
        names = {m.get("name") for m in items}
        for name, info in old_models.items():
            if not isinstance(info, dict) or name in names:
                continue
            fields = dict(info.get("fields") or {})
            engine = info.get("engine", "")
            entry = {
                "name": name,
                "base_url": fields.get("base_url", ""),
                "api_key": fields.get("api_key", ""),
                "model": fields.get("model", ""),
            }
            if engine == "ollama":
                base = (entry["base_url"] or "http://localhost:11434").rstrip("/")
                if not base.endswith("/v1"):
                    base += "/v1"
                entry["base_url"] = base
                try:
                    entry["max_input"] = int(float(fields.get("max_token_k", 32)) * 1024)
                except (TypeError, ValueError):
                    pass
            if entry["model"]:
                items.append(with_defaults(entry))
                names.add(name)
                if info.get("default") and not block.get("current"):
                    block["current"] = name
                changed = True
        block["models"] = items
        if items and not block.get("current"):
            block["current"] = items[0]["name"]
        cfg.pop("models", None)
        changed = True

    # ── 2) api.engines.<engine> 扁平单槽（openai/ollama 之外的引擎不管）──
    engines = ((cfg.get("api") or {}).get("engines") or {})
    for eng_name in ("openai", "ollama"):
        ecfg = engines.get(eng_name) or {}
        if not isinstance(ecfg, dict) or not ecfg.get("model"):
            continue
        if ecfg.get("models"):
            continue        # 已是注册表形态
        block = _openai_block(cfg)
        items = block.get("models") or []
        if any(m.get("model") == ecfg.get("model") and m.get("base_url") for m in items):
            continue
        base = ecfg.get("base_url", "")
        if eng_name == "ollama":
            base = (base or "http://localhost:11434").rstrip("/")
            if not base.endswith("/v1"):
                base += "/v1"
        entry = {
            "name": f"{eng_name}-{ecfg.get('model')}".replace(":", "-"),
            "base_url": base,
            "api_key": ecfg.get("api_key", ""),
            "model": ecfg.get("model", ""),
        }
        if eng_name == "ollama":
            try:
                entry["max_input"] = int(float(ecfg.get("max_token_k", 32)) * 1024)
            except (TypeError, ValueError):
                pass
        items.append(with_defaults(entry))
        block["models"] = items
        if not block.get("current"):
            block["current"] = entry["name"]
        changed = True

    if changed:
        _persist(cfg)
    return changed

# 测试可临时覆盖配置路径
_CONFIG_PATH = None


def _set_config_path(path):
    """仅供测试：指向临时 config.json"""
    global _CONFIG_PATH
    _CONFIG_PATH = path


def _load():
    if _CONFIG_PATH:
        try:
            with open(_CONFIG_PATH, 'r', encoding='utf-8') as f:
                return __import__('json').load(f)
        except (FileNotFoundError, __import__('json').JSONDecodeError):
            return {"api": {"engines": {}}, "system": {}}
    return load_config()


def _persist(cfg):
    if _CONFIG_PATH:
        with open(_CONFIG_PATH, 'w', encoding='utf-8') as f:
            __import__('json').dump(cfg, f, ensure_ascii=False, indent=2)
        return
    save_config(cfg)


def _openai_block(cfg):
    return cfg.setdefault("api", {}).setdefault("engines", {}).setdefault("openai", {})


def list_models(cfg=None):
    """返回 (models:list[dict], current:str|None)。

    无 models 列表时返回单条隐式模型（由扁平 api_key/base_url/model 构成）。
    """
    cfg = cfg or _load()
    block = _openai_block(cfg)
    models = block.get("models")
    if not models:
        m = block.get("model") or "default"
        implicit = {
            "name": m,
            "base_url": block.get("base_url", ""),
            "api_key": block.get("api_key", ""),
            "model": block.get("model", ""),
        }
        return [with_defaults(implicit)], (block.get("current") or m)
    current = block.get("current") or (models[0]["name"] if models else None)
    return [with_defaults(m) for m in models], current


def get_model(name=None, cfg=None):
    """取某模型配置；name=None 取 current。找不到返回 None。"""
    models, current = list_models(cfg)
    target = name or current
    if not target:
        return None
    for m in models:
        if m.get("name") == target:
            return with_defaults(m)
    return None


def set_current(name):
    """把 current 指针指向 name 并落盘。name 必须存在，否则返回 False。"""
    cfg = _load()
    block = _openai_block(cfg)
    models = block.get("models") or []
    if not any(m.get("name") == name for m in models):
        return False
    block["current"] = name
    _persist(cfg)
    return True


def add_model(entry):
    """新增或更新模型，落盘并返回其 name。

    entry: {"name", "base_url", "api_key", "model"}。同名则更新。
    首次添加会从扁平配置迁移出第一条隐式模型，且保持 current 不跳变。
    """
    name = (entry.get("name") or "").strip()
    if not name:
        raise ValueError("模型 name 不能为空")
    cfg = _load()
    block = _openai_block(cfg)
    models = block.get("models")
    if not models:
        old_name = block.get("model") or "default"
        models = [{
            "name": old_name,
            "base_url": block.get("base_url", ""),
            "api_key": block.get("api_key", ""),
            "model": block.get("model", ""),
        }]
        block["models"] = models
        if not block.get("current"):
            block["current"] = old_name
    for m in models:
        if m.get("name") == name:
            m.update(entry)
            _persist(cfg)
            return name
    models.append(dict(entry))
    _persist(cfg)
    return name


def remove_model(name):
    """删除模型，返回是否成功（找不到返回 False）。
    若删除的是 current，则 current 回退到列表第一个。
    """
    cfg = _load()
    block = _openai_block(cfg)
    models = block.get("models") or []
    new = [m for m in models if m.get("name") != name]
    if len(new) == len(models):
        return False
    block["models"] = new
    if block.get("current") == name:
        block["current"] = new[0]["name"] if new else None
    _persist(cfg)
    return True
