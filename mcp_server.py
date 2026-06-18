#!/usr/bin/env python3
"""
小狸 MCP Stdio Server
=====================
标准 MCP (Model Context Protocol) stdio 传输层入口。
通过 stdin/stdout 以 JSON-RPC 2.0 格式通信，
可被 Claude Desktop、Cursor、OpenClaw 等标准 MCP 客户端直接连接。

用法:
    python mcp_server.py [--plugins-dir plugins] [--skills-dir skills]

Claude Desktop 配置示例:
    {
      "mcpServers": {
        "xiaoli": {
          "command": "python",
          "args": ["/path/to/xiaoli-cli/mcp_server.py"]
        }
      }
    }
"""

import sys
import os
import json
import argparse
import logging

# 确保当前目录在 sys.path 中，以便导入项目模块
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# 日志输出到 stderr，不干扰 stdout 上的 JSON-RPC 通信
logging.basicConfig(
    level=logging.INFO,
    format="[xiaoli-mcp] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("xiaoli-mcp")


def main():
    parser = argparse.ArgumentParser(description="小狸 MCP Stdio Server")
    parser.add_argument("--plugins-dir", default="plugins", help="插件目录 (默认: plugins)")
    parser.add_argument("--skills-dir", default="skills", help="技能目录 (默认: skills)")
    args = parser.parse_args()

    # 切换到脚本所在目录，保证相对路径正确
    os.chdir(SCRIPT_DIR)

    # 初始化 UnifiedToolManager
    # 将 initialize() 中的 print 重定向到 stderr，避免污染 stdout JSON-RPC 通道
    import io
    from contextlib import redirect_stdout

    from unified_tool_manager import UnifiedToolManager

    manager = UnifiedToolManager()
    captured_output = io.StringIO()
    with redirect_stdout(captured_output):
        manager.initialize(
            plugins_dir=args.plugins_dir,
            skills_dir=args.skills_dir,
        )

    # 将初始化时的 print 输出转发到 stderr
    init_output = captured_output.getvalue()
    if init_output:
        for line in init_output.strip().split('\n'):
            logger.info(line)

    tool_count = len(manager._tools)
    logger.info(f"MCP Server 已启动，共加载 {tool_count} 个工具")
    logger.info("等待 stdin JSON-RPC 请求...")

    # 主循环：从 stdin 逐行读取 JSON-RPC 请求
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
            except json.JSONDecodeError as e:
                # 无法解析的 JSON，返回解析错误
                error_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {e}"},
                }
                _send(error_resp)
                continue

            # 处理通知（没有 id 字段的请求）— MCP 规范中通知不需要响应
            req_id = request.get("id")
            method = request.get("method", "")

            # 特殊处理 notifications/initialized — 客户端初始化完成通知
            if method == "notifications/initialized":
                logger.info("客户端已发送 initialized 通知")
                continue

            # 特殊处理 $/cancelRequest
            if method == "$/cancelRequest":
                logger.info(f"收到取消请求: {request.get('params', {}).get('id')}")
                continue

            # 委托给 UnifiedToolManager 处理
            # 拦截插件可能产生的 stdout 输出，转发到 stderr
            captured = io.StringIO()
            try:
                with redirect_stdout(captured):
                    response = manager.handle_mcp_request(request)
                plugin_output = captured.getvalue()
                if plugin_output:
                    for p_line in plugin_output.strip().split('\n'):
                        logger.info(f"[plugin] {p_line}")
            except Exception as e:
                logger.error(f"处理请求异常: {e}")
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32603, "message": f"Internal error: {e}"},
                }

            _send(response)

    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭...")
    except EOFError:
        logger.info("stdin 已关闭，正在退出...")
    finally:
        manager.shutdown()
        logger.info("MCP Server 已关闭")


def _send(response: dict):
    """将 JSON-RPC 响应写入 stdout 并刷新"""
    text = json.dumps(response, ensure_ascii=False)
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
