"""模型注册表 + /model 命令的回归测试。

不污染真实 config.json：所有读写都指向临时文件。
"""
import os
import json
import tempfile

import pytest

from xcli_core import model_registry as mr
import xcli_core.config as cfgmod
import ai_engines.openai_engine as oe_mod


@pytest.fixture
def tmp_config():
    """准备临时 config.json，并把注册表与 openai 引擎的读取都重定向过去。"""
    d = tempfile.mkdtemp()
    path = os.path.join(d, "config.json")
    payload = {
        "api": {"engines": {
            "openai": {"api_key": "K0", "base_url": "https://old/v1", "model": "old-model"}
        }},
        "system": {},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    saved_path = mr._CONFIG_PATH
    saved_proj = oe_mod.project_root
    mr._set_config_path(path)
    oe_mod.project_root = d
    try:
        yield path
    finally:
        mr._set_config_path(saved_path)
        oe_mod.project_root = saved_proj


# ── 注册表单元 ──

def test_legacy_flat_config_is_single_implicit_model(tmp_config):
    models, current = mr.list_models()
    assert len(models) == 1
    assert models[0]["model"] == "old-model"
    assert current == "old-model"


def test_add_first_model_migrates_flat_and_keeps_current(tmp_config):
    mr.add_model({"name": "gpt4o", "base_url": "https://api.openai.com/v1",
                  "api_key": "sk", "model": "gpt-4o"})
    models, current = mr.list_models()
    names = [m["name"] for m in models]
    assert names == ["old-model", "gpt4o"]
    # current 不应跳变到新加的模型
    assert current == "old-model"


def test_add_duplicate_name_updates_in_place(tmp_config):
    mr.add_model({"name": "gpt4o", "base_url": "u1", "api_key": "k1", "model": "gpt-4o"})
    mr.add_model({"name": "gpt4o", "base_url": "u2", "api_key": "k2", "model": "gpt-4o-mini"})
    models, _ = mr.list_models()
    assert len(models) == 2  # 未重复追加
    assert models[1]["base_url"] == "u2"


def test_set_current_and_get_model(tmp_config):
    mr.add_model({"name": "gpt4o", "base_url": "https://api.openai.com/v1",
                  "api_key": "sk", "model": "gpt-4o"})
    assert mr.set_current("gpt4o") is True
    m = mr.get_model()
    assert m["model"] == "gpt-4o"
    assert mr.set_current("ghost") is False  # 越权返回 False


def test_remove_current_falls_back_to_first(tmp_config):
    mr.add_model({"name": "gpt4o", "base_url": "u", "api_key": "k", "model": "gpt-4o"})
    mr.set_current("gpt4o")
    assert mr.remove_model("gpt4o") is True
    _, current = mr.list_models()
    assert current == "old-model"


def test_remove_missing_returns_false(tmp_config):
    assert mr.remove_model("nope") is False


def test_persisted_to_disk(tmp_config):
    mr.add_model({"name": "gpt4o", "base_url": "u", "api_key": "k", "model": "gpt-4o"})
    mr.set_current("gpt4o")
    with open(tmp_config, "r", encoding="utf-8") as f:
        saved = json.load(f)
    block = saved["api"]["engines"]["openai"]
    assert block["current"] == "gpt4o"
    assert any(m["name"] == "gpt4o" for m in block["models"])


# ── 引擎接入 ──

def test_engine_init_applies_registry_current(tmp_config):
    mr.add_model({"name": "gpt4o", "base_url": "https://api.openai.com/v1",
                  "api_key": "sk", "model": "gpt-4o"})
    mr.set_current("gpt4o")
    eng = oe_mod.OpenaiAI()
    assert eng.model == "gpt-4o"
    assert "api.openai.com" in eng.base_url
    assert eng.current_model_name() == "gpt4o"


def test_engine_set_registry_model(tmp_config):
    eng = oe_mod.OpenaiAI()
    eng.add_model({"name": "gpt4o", "base_url": "https://api.openai.com/v1",
                   "api_key": "sk", "model": "gpt-4o"})
    assert eng.set_registry_model("gpt4o") is True
    assert eng.model == "gpt-4o"
    assert eng.set_registry_model("ghost") is False


def test_engine_does_not_clobber_existing_set_model(tmp_config):
    """原有轻量 set_model（只改 model 名）必须仍然可用，不被注册表方法覆盖。"""
    eng = oe_mod.OpenaiAI()
    eng.set_model("gpt-4o-mini")  # 原有方法：只改 self.model
    assert eng.model == "gpt-4o-mini"
    # 注册表方法仍在
    assert hasattr(eng, "set_registry_model")
    assert hasattr(eng, "list_registry_models")


# ── CLI 命令路由 ──

def _make_fake_cli(eng):
    """复制 cli_base 的模型命令方法到轻量对象，避免实例化整个 CliBase。"""
    from xcli_core import cli_base
    cls = type("FakeCli", (), {})
    cls.handle_model_command = cli_base.BaseAICLI.handle_model_command
    cls._model_list = cli_base.BaseAICLI._model_list
    cls._model_switch = cli_base.BaseAICLI._model_switch
    cls._model_add_interactive = cli_base.BaseAICLI._model_add_interactive
    return cls()


def test_cli_model_list_and_switch(tmp_config, monkeypatch):
    from xcli_core import cli_base
    eng = oe_mod.OpenaiAI()
    eng.add_model({"name": "gpt4o", "base_url": "u", "api_key": "k", "model": "gpt-4o"})

    cli = _make_fake_cli(eng)
    cli.current_engine = eng
    cli.current_model = None

    # 列出
    captured = {}
    monkeypatch.setattr("builtins.print", lambda *a, **k: captured.setdefault("out", []).append(a))
    cli.handle_model_command("list")
    assert any("gpt4o" in str(x) for x in captured["out"])

    # 切换
    cli.handle_model_command("gpt4o")
    assert cli.current_model == "gpt4o"
    assert eng.model == "gpt-4o"


def test_cli_model_switch_missing(tmp_config, monkeypatch):
    eng = oe_mod.OpenaiAI()
    cli = _make_fake_cli(eng)
    cli.current_engine = eng
    cli.current_model = None
    captured = {}
    monkeypatch.setattr("builtins.print", lambda *a, **k: captured.setdefault("out", []).append(a))
    cli.handle_model_command("ghost")
    assert any("未找到" in str(x) for x in captured["out"])
    assert cli.current_model is None


def test_cli_model_add_interactive(tmp_config, monkeypatch):
    eng = oe_mod.OpenaiAI()
    cli = _make_fake_cli(eng)
    cli.current_engine = eng
    cli.current_model = None
    answers = iter(["mygpt", "https://x/v1", "sk-1", "gpt-x"])
    monkeypatch.setattr("builtins.input", lambda *a, **k: next(answers))
    captured = {}
    monkeypatch.setattr("builtins.print", lambda *a, **k: captured.setdefault("out", []).append(a))
    cli.handle_model_command("add")
    models, current = eng.list_registry_models()
    assert any(m["name"] == "mygpt" for m in models)
    assert cli.current_model == "mygpt"
