"""OpenAI 兼容本地代理 —— 把「已配置模型」以 /v1/chat/completions 暴露给外部 TUI

供 Crush 等支持自定义 OpenAI 兼容端点的客户端使用：
  GET  /v1/models            → 已配置模型列表（模型配置系统里那些，别的一概不显示）
  POST /v1/chat/completions  → 按 model 名路由到对应调用格式（引擎）的 chat_completions

用法:
    python -m xcli_core.openai_proxy [--port 8787]
仅绑定 127.0.0.1，不做鉴权（本机回环）。
"""

import argparse
import json
import sys
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xcli_core.model_config import (  # noqa: E402
    get_model, list_models, migrate_legacy_engines, _load_engine_module,
)

PORT_DEFAULT = 8787


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # 安静
        pass

    def _json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.rstrip("/").endswith("/v1/models") or self.path == "/models":
            migrate_legacy_engines()
            data = [
                {"id": name, "object": "model", "owned_by": f"xiaoli/{info.get('engine', '?')}",
                 "created": 0}
                for name, info in list_models()
            ]
            self._json(200, {"object": "list", "data": data})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if not (self.path.rstrip("/").endswith("/v1/chat/completions")
                or self.path.rstrip("/").endswith("/chat/completions")):
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except Exception as e:
            self._json(400, {"error": f"bad request: {e}"})
            return

        model_name = body.get("model", "")
        info = get_model(model_name)
        if not info:
            self._json(404, {"error": f"模型 [{model_name}] 未配置。已配置: "
                                      f"{[n for n, _ in list_models()]}"} )
            return
        try:
            mod = _load_engine_module(info["engine"])
            chat = mod.chat_completions
        except Exception as e:
            self._json(500, {"error": f"引擎 [{info['engine']}] 加载失败: {e}"})
            return

        messages = body.get("messages", [])
        tools = body.get("tools")
        stream = bool(body.get("stream"))
        try:
            result = chat(info.get("fields", {}), messages, tools=tools, stream=stream)
        except Exception as e:
            self._json(500, {"error": f"上游调用失败: {e}"})
            return

        if isinstance(result, dict) and result.get("error"):
            self._json(502, result)
            return

        if stream:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            try:
                for ev in result:
                    if not ev:
                        continue
                    self.wfile.write((ev + "\n\n").encode("utf-8"))
                    self.wfile.flush()
            except Exception:
                pass
            return

        # 非流式：补齐 OpenAI 对象字段
        if isinstance(result, dict):
            result.setdefault("id", "chatcmpl-xiaoli")
            result.setdefault("object", "chat.completion")
            result.setdefault("model", model_name)
            result.setdefault("created", 0)
        self._json(200, result)


def serve(port=PORT_DEFAULT):
    migrate_legacy_engines()
    server = ThreadingHTTPServer(("127.0.0.1", port), ProxyHandler)
    print(f"[xiaoli-proxy] OpenAI 兼容代理: http://127.0.0.1:{port}/v1  "
          f"(已配置模型: {[n for n, _ in list_models()] or '无'})", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main():
    ap = argparse.ArgumentParser(description="xiaoli OpenAI 兼容代理")
    ap.add_argument("--port", type=int, default=PORT_DEFAULT)
    args = ap.parse_args()
    serve(args.port)


if __name__ == "__main__":
    main()
