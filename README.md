# 小狸 Pro-CLI

<p align="center">
  <img src="logo.png" width="120" alt="xiaoli-cli logo">
</p>

<p align="center">
  <strong>智能编程助手 — 代码编辑 · Git 集成 · 浏览器自动化 · 多 Agent 协作 · 图像生成 · 记忆系统</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-5.2.0-blue" alt="version">
  <img src="https://img.shields.io/badge/python-3.10+-green" alt="python">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="license">
  <img src="https://img.shields.io/badge/tests-150+%20passed-brightgreen" alt="tests">
  <img src="https://img.shields.io/badge/plugins-19-blueviolet" alt="plugins">
</p>

---

## 简介

小狸 Pro-CLI 是一款基于 Python 的智能编程助手，集成了代码编辑、版本控制、浏览器自动化、图像生成、记忆系统等功能，支持多种 AI 引擎，帮助开发者提升工作效率。

## 特性

- **双 AI 引擎** — Ollama 本地模型 + OpenAI 兼容格式（DeepSeek、Grok、硅基流动等）
- **代码编辑与搜索** — 精准替换、批量编辑、符号提取、依赖分析、正则搜索、自动语法检查
- **Git 版本控制** — 完整 Git 操作 + 工作流自动化（smart-commit、changelog）
- **浏览器自动化** — Playwright 驱动，导航、交互、截图、JS 执行、PDF 导出
- **子 Agent 系统** — 多 Agent 并行协作，独立任务分配与结果回收
- **图像生成** — 基于 ComfyUI 在线服务，自然语言/Tag 双模式，支持中文描述
- **记忆系统** — 长期记忆 + 每日日记 + AI 写日记 + 全局搜索 + 自动保存对话
- **远程通信** — PC 与手机 WebSocket 双向通信
- **定时任务** — 支持相对时间、绝对时间、重复任务，到期自动激活 AI
- **系统通知** — 跨平台任务完成通知（Windows / macOS / Linux）
- **MCP 协议** — 19 个插件全部实现 MCP 定义，支持 Function Calling 原生调用
- **19 个插件 161+ 个操作** — 代码编辑、Git、浏览器、工程化、文件管理、图像生成、记忆等
- **三模式界面** — TUI 图形化 + 传统命令行 + Web UI 浏览器界面
- **150+ 个自动化测试** — pytest 覆盖全部插件和核心模块

## 快速开始

### 安装

```bash
git clone https://gitee.com/shuiyu1123/xiaoli-cli.git
cd xiaoli-cli
pip install -r requirements.txt
```

### 启动

```bash
# CLI 模式
python ai_cli.py

# 指定引擎
python ai_cli.py --engine openai

# Windows 一键启动
launcher.exe
```

## AI 引擎

| 引擎 | 类型 | 说明 |
|------|------|------|
| `ollama` | 本地 | Ollama 本地模型，无需 API 密钥 |
| `openai` | 云端/本地 | OpenAI 兼容格式，支持 DeepSeek、Grok、硅基流动、本地 vLLM 等 |

### 配置示例 (config.json)

```json
{
  "api": {
    "engines": {
      "ollama": {
        "base_url": "http://localhost:11434",
        "model": "gemma4:31b"
      },
      "openai": {
        "api_key": "your-key",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat"
      }
    }
  },
  "system": {
    "default_engine": "ollama",
    "max_history": 50
  }
}
```

## 插件列表 (19 个)

> 更多社区插件请访问 [xiaoli-cli-plugins](https://gitee.com/shuiyu1123/xiaoli-cli-plugins)，使用 `/plugin install <插件码>` 一键安装。

### 核心生产力

| 插件 | 操作数 | 说明 |
|------|--------|------|
| `code_editor` | 24 | 代码编辑+搜索。精准替换、批量编辑、find/regex/symbols/imports/callers/todo/structure + 自动语法检查 |
| `git_tools` | 17 | Git 版本控制。status/diff/log/commit/branch + smart-commit/changelog/contributors/stale |
| `cmd_executor` | 1 | Shell 命令执行，跨平台，超时控制 |
| `file_manager` | 10 | 文件系统。list/read/write/copy/move/delete/search/info/mkdir/append |
| `auto_engineer` | 12 | 工程化。lint/format/test/build/deps + 复杂度/安全扫描/质量指标/项目初始化 |
| `task_manager` | 7 | 任务管理。add/list/complete/delete/clear，JSON 持久化 |

### 高级功能

| 插件 | 操作数 | 说明 |
|------|--------|------|
| `sub_agent` | 8 | 子 Agent 系统。spawn/list/status/result/send/kill，多 Agent 并行协作 |
| `browser_auto` | 28 | 浏览器自动化。导航/点击/填写/截图/JS执行/PDF/cookies（基于 Playwright） |
| `gui_auto` | 20 | 桌面 GUI 自动化。基于 Windows UIA，屏幕元素识别/点击/输入/截图（仅 Windows） |
| `ai_image` | — | AI 生图。基于 ai.2x.nz 自然语言生图，异步生成 + WebSocket 进度推送 |
| `image_generator` | 7 | 图像生成。基于 ComfyUI 在线服务，自然语言/Tag 双模式，28 个角色工作流 |
| `memory_plugin` | 11 | 记忆系统。AI 写日记/搜索记忆/管理聊天记录/长期记忆 |
| `scheduler` | 4 | 定时任务。支持相对时间/绝对时间/重复任务，到期自动激活 AI |
| `tool_search` | — | 工具搜索。按关键词发现可用插件 |

### 辅助工具

| 插件 | 说明 |
|------|------|
| `network_tools` | 网络工具。ping/get/status/headers/ip |
| `ai_search` | AI 搜索。jina.ai 智能搜索 + 网页内容提取 |
| `frontend_tester` | 前端测试。HTML/CSS/JS 语法检查、响应式验证 |
| `speech_recognition` | 语音识别。录音 + 语音转文字（Whisper） |
| `audio_player` | 音频播放 |
| `send_image` | 远程模式下发图片到手机 |

## 记忆系统

内置持久化记忆系统，AI 可以记住之前的工作：

| 功能 | 说明 |
|------|------|
| 长期记忆 | `MEMORY.md` — AI 自己维护的精华记忆 |
| 每日日记 | `memory/YYYY-MM-DD.md` — 带时间戳和标签 |
| AI 写日记 | `memory_plugin diary_ai` — 自动标记 [AI观察] |
| 自动保存对话 | 每轮对话后自动存 JSON |
| 上下文压缩 | 超过 50 条自动 AI 总结，保留最近 10 条 |
| 全局搜索 | 搜索 MEMORY + 日记 + 聊天记录 |

```
memory_plugin diary 今天完成了API对接
memory_plugin search 定时任务
memory_plugin remember 用户偏好深色主题
memory_plugin chat_search 图像生成
```

## 远程通信

通过 WebSocket 实现 PC 与手机双向通信：

```bash
/remote start 9079 mypassword    # 启动本地服务
/remote stop                      # 停止服务
/remote status                    # 查看状态
```

功能：手机发消息给 AI、AI 回复推到手机、文件传输、图片识别。

## 安全机制

### 模式切换 (`/safe`)

| 模式 | 说明 |
|------|------|
| **普通模式** (默认) | AI 识别风险，有风险才请求确认 |
| **人工确认** | 所有指令都需要用户确认 |

### 检查流程

```
工具调用 → safety.check()
  ├─ 快速预检（读取/查询类）→ 直接放行
  ├─ 普通模式 → AI 独立分析风险
  │   ├─ safe → 放行
  │   └─ unsafe → 展示风险等级+影响，y/n 确认
  └─ 特殊指令（rm/delete/chmod）→ 始终确认
```

### 代码执行

独立的安全代码执行环境：
- AST 级危险代码检测
- 模块白名单（阻断 25 个高危模块）
- 子进程隔离执行
- 内存限制

## MCP 协议支持

所有 19 个插件均实现 MCP (Model Context Protocol) 定义，支持三种工具调用协议：

| 协议 | 说明 |
|------|------|
| **MCP** | Model Context Protocol 标准定义 |
| **FC** | OpenAI Function Calling 原生调用 |
| **JSON** | 传统 `{"action": "use_tool", ...}` 格式 |

## 命令列表

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助 |
| `/safe` | 切换安全模式 |
| `/engine list` | 列出可用引擎 |
| `/engine switch <引擎>` | 切换引擎 |
| `/engine.openai models` | 列出 OpenAI 引擎模型 |
| `/chat save/list/open` | 聊天记录管理 |
| `/file.read <路径>` | 读取文件 |
| `/remote` | 远程连接帮助 |
| `/notify` | 切换任务完成通知 |
| `/scheduler` / `/remind` | 管理定时任务 |
| `/memory` | 管理记忆系统 |
| `/tui` | 切换 TUI 模式 |
| `/quit` | 退出 |

## Web UI

WebSocket 实时交互界面，支持完整的 AI 对话体验。

```bash
# 方式 1: 启动 WebSocket 后端（推荐）
python webui_server.py --port 8080
# 浏览器访问 http://localhost:8080

# 方式 2: 直接打开静态页面
start webui.html       # Windows
open webui.html        # macOS
xdg-open webui.html    # Linux
```

## 项目结构

```
xiaoli-cli/
├── ai_cli.py                   # 主入口
├── webui.html                  # Web UI 界面
├── webui_server.py             # Web UI 后端
├── launcher.py                 # 智能启动器
├── config.json.example         # 配置模板
├── easter_egg.py               # 彩蛋
├── xcli_core/                  # 核心模块
│   ├── cli_core.py             # 主循环 + 提示词构建
│   ├── cli_base.py             # 初始化 + 引擎/插件加载
│   ├── cli_tools.py            # 工具调用执行
│   ├── cli_clawli.py           # 远程模式
│   ├── cli_code_exec.py        # 代码执行
│   ├── cli_display.py          # 显示输出
│   ├── cli_history.py          # 聊天记录
│   ├── config.py               # 配置管理
│   ├── constants.py            # 常量定义
│   ├── fc_tools.py             # MCP → FC 格式转换
│   ├── memory.py               # 记忆系统
│   ├── notification.py         # 跨平台系统通知
│   ├── plugin_manager.py       # 插件管理器
│   ├── safety.py               # 统一安全层
│   ├── sandbox.py              # 代码安全沙箱
│   └── tui.py                  # TUI 界面
├── ai_engines/                 # AI 引擎
│   ├── ollama_engine.py
│   └── openai_engine.py
├── plugins/                    # 插件 (19 个)
│   ├── code_editor.py
│   ├── git_tools.py
│   ├── cmd_executor.py
│   ├── file_manager.py
│   ├── auto_engineer.py
│   ├── task_manager.py
│   ├── sub_agent.py
│   ├── browser_auto.py
│   ├── gui_auto.py
│   ├── ai_image.py
│   ├── image_generator.py
│   ├── memory_plugin.py
│   ├── scheduler.py
│   ├── tool_search.py
│   ├── network_tools.py
│   ├── ai_search.py
│   ├── frontend_tester.py
│   ├── speech_recognition.py
│   └── send_image.py
├── skills/                     # 技能
├── image_engine/               # 图像识别引擎
├── tests/                      # 测试套件 (150+ 用例)
├── love.txt                    # 彩蛋情话
└── about.txt                   # 关于信息
```

## 测试

```bash
# 运行全部测试
python -m pytest tests/ -v

# 语法检查
python -c "import py_compile; py_compile.compile('ai_cli.py', doraise=True)"
```

## 插件开发

小狸支持 `Liugin`（自研协议）和 `Plugin`（通用协议）两种类名，均可被插件管理器自动识别：

```python
class Plugin:
    """我的插件"""

    def __init__(self):
        self.usage = "使用说明"
        self.cli = None

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "my_tool",
            "description": "工具描述",
            "keywords": ["关键词"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "my_tool",
            "description": "工具描述",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "args": {"type": "string", "description": "参数"}
                }
            }
        }

    def handle(self, args: str) -> str:
        return "处理结果"
```

## 许可证

[MIT License](LICENSE)

## 链接

- Gitee: https://gitee.com/shuiyu1123/xiaoli-cli
- 插件仓库: https://gitee.com/shuiyu1123/xiaoli-cli-plugins
- [更新日志](CHANGELOG.md)
- [使用指南](HELP.md)
