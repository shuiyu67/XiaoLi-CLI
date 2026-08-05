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
        return [implicit], (block.get("current") or m)
    current = block.get("current") or (models[0]["name"] if models else None)
    return models, current


def get_model(name=None, cfg=None):
    """取某模型配置；name=None 取 current。找不到返回 None。"""
    models, current = list_models(cfg)
    target = name or current
    if not target:
        return None
    for m in models:
        if m.get("name") == target:
            return dict(m)
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
