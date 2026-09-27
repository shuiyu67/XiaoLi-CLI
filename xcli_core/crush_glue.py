"""Crush 夺舍 glue —— 一条命令拉起「Crush TUI + xiaoli 代理 + xiaoli MCP 工具」

  python -m xcli_core.crush_glue            # 起代理(线程) → 写 crush.json → 拉起 Crush
  python -m xcli_core.crush_glue --port 8790

自动写入（Windows: %LOCALAPPDATA%/crush/crush.json）：
  providers.xiaoli  = openai-compat → http://127.0.0.1:<port>/v1（模型 = 已配置模型）
  mcp.xiaoli        = stdio → python mcp_server.py（py_detect 等 25 工具）
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xcli_core import model_registry  # noqa: E402
from xcli_core.openai_proxy import serve as serve_proxy, PORT_DEFAULT  # noqa: E402

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def crush_config_path():
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser(
            r"~\AppData\Local")
        return os.path.join(base, "crush", "crush.json")
    return os.path.expanduser("~/.config/crush/crush.json")


def write_crush_config(port):
    """写 crush.json：xiaoli 模型 provider + xiaoli MCP 工具（幂等合并）"""
    path = crush_config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}

    model_registry.migrate_legacy()
    _entries, _cur = model_registry.list_models()
    models = [{"id": m.get("name"), "name": m.get("name")} for m in _entries]
    cfg.setdefault("providers", {})["xiaoli"] = {
        "type": "openai-compat",
        "name": "Lix xiaoli",
        "base_url": f"http://127.0.0.1:{port}/v1",
        "api_key": "xiaoli-local",
        "models": models,
    }
    py = sys.executable or "python"
    cfg.setdefault("mcp", {})["xiaoli"] = {
        "type": "stdio",
        "command": py,
        "args": [os.path.join(PROJECT_ROOT, "mcp_server.py")],
        "timeout": 30,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return path, models


def find_crush():
    exe = shutil.which("crush")
    if exe:
        return exe
    # npm 全局/工作区包装
    for cand in (
        os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "npm", "crush.cmd"),
        os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "npm", "crush"),
    ):
        if os.path.exists(cand):
            return cand
    return None


def launch(port=PORT_DEFAULT):
    t = threading.Thread(target=serve_proxy, args=(port,), daemon=True)
    t.start()

    path, models = write_crush_config(port)
    names = [m["id"] for m in models]
    print(f"[xiaoli] 代理: http://127.0.0.1:{port}/v1  模型: {names or '无（先 /model add）'}")
    print(f"[xiaoli] crush 配置已写入: {path}")

    crush = find_crush()
    if not crush:
        print("[xiaoli] 找不到 crush 可执行（winget install charmbracelet.crush 或 "
              "npm install -g @charmland/crush）。配置已就绪，装好后直接运行 crush 即可。")
        return 2
    print(f"[xiaoli] 启动 Crush: {crush}")
    os.chdir(PROJECT_ROOT)
    os.execv(crush, [crush] + sys.argv[1:] if os.name != "nt" else [crush])


def main():
    ap = argparse.ArgumentParser(description="xiaoli × Crush 夺舍启动器")
    ap.add_argument("--port", type=int, default=PORT_DEFAULT)
    args, extra = ap.parse_known_args()
    sys.argv = [sys.argv[0]] + extra
    code = launch(args.port)
    if code:
        sys.exit(code)


if __name__ == "__main__":
    main()
