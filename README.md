# 小狸 Pro-CLI

<p align="center">
  <strong>智能编程助手 — 代码编辑 · Git 集成 · 浏览器自动化 · 多 Agent 协作 · 图像生成 · 记忆系统</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-5.1.3-blue" alt="version">
  <img src="https://img.shields.io/badge/python-3.10+-green" alt="python">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="license">
  <img src="https://img.shields.io/badge/tests-113%20passed-brightgreen" alt="tests">
  <img src="https://img.shields.io/badge/plugins-17-blueviolet" alt="plugins">
  <img src="https://img.shields.io/badge/MCP-supported-brightgreen" alt="mcp">
</p>

---

##  特性

-  **双 AI 引擎** — Ollama 本地模型 + OpenAI 兼容格式（DeepSeek、Grok、硅基流动等）
-  **代码编辑与搜索** — 精准替换、批量编辑、符号提取、依赖分析、正则搜索、**自动语法检查**
-  **Git 版本控制** — 完整 Git 操作 + 工作流自动化（smart-commit、changelog）
-  **浏览器自动化** — Playwright 驱动，导航/交互/截图/JS 执行/PDF
-  **子 Agent 系统** — 多 Agent 并行协作，独立任务分配与结果回收
-  **统一安全层** — AI 风险识别 + 三模式切换（普通/人工/无限制）
-  **图像生成** — 基于 ComfyUI 在线服务，自然语言/Tag 双模式，支持中文描述
-  **记忆系统** — 长期记忆 + 每日日记 + AI 写日记 + 全局搜索 + 自动保存对话
-  **Clawli 远程模式** — PC-手机 WebSocket 双向通信，支持内网穿透代理
-  **定时任务** — 支持相对时间、绝对时间、重复任务，到期自动激活 AI
-  **系统通知** — 跨平台任务完成通知（Windows / macOS / Linux）
-  **MCP 协议** — 17 个插件全部实现 MCP 定义，支持 Function Calling 原生调用
-  **17 个插件 141+ 个操作** — 代码编辑、Git、浏览器、工程化、文件管理、图像生成、记忆等
-  **三模式界面** — TUI 图形化 + 传统命令行 + **Web UI 浏览器界面**
-  **113 个自动化测试** — pytest 覆盖全部插件和核心模块

##  快速开始

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

# Windows 一键启动（无需 Python 环境）
launcher.exe
```

##  AI 引擎

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

##  插件列表 (17 个)

### 核心生产力

| 插件 | 操作数 | 说明 |
|------|--------|------|
| `code_editor` | 24 | 代码编辑+搜索。精准替换、批量编辑、find/regex/symbols/imports/callers/todo/structure + 自动语法检查 + diff 弹窗 |
| `git_tools` | 17 | Git 版本控制。status/diff/log/commit/branch + smart-commit/changelog/contributors/stale |
| `cmd_executor` | 1 | Shell 命令执行。跨平台，超时控制，危险命令拦截 |
| `file_manager` | 10 | 文件系统。list/read/write/copy/move/delete/search/info/mkdir/append |
| `auto_engineer` | 12 | 工程化。lint/format/test/build/deps + 复杂度/安全扫描/质量指标/项目初始化 |
| `task_manager` | 7 | 任务管理。add/list/complete/delete/clear，JSON 持久化 |

### 高级功能

| 插件 | 操作数 | 说明 |
|------|--------|------|
| `sub_agent` | 8 | 子 Agent 系统。spawn/list/status/result/send/kill，多 Agent 并行协作 |
| `browser_auto` | 28 | 浏览器自动化。导航/点击/填写/截图/JS执行/PDF/cookies（基于 Playwright） |
| `image_generator` | 7 | **图像生成**。基于 ComfyUI 在线服务，自然语言/Tag 双模式，28 个角色工作流 |
| `memory_plugin` | 11 | **记忆系统**。AI 写日记/搜索记忆/管理聊天记录/长期记忆 MEMORY.md |
| `scheduler` | 4 | **定时任务**。支持相对时间/绝对时间/重复任务，到期自动激活 AI |
| `tool_search` | — | 工具搜索。按关键词发现可用插件（供 AI 按需调用） |

### 辅助工具

| 插件 | 说明 |
|------|------|
| `network_tools` | 网络工具。ping/get/status/headers/ip |
| `ai_search` | AI 搜索。jina.ai 智能搜索 + 网页内容提取 |
| `frontend_tester` | 前端测试。HTML/CSS/JS 语法检查、响应式验证 |
| `speech_recognition` | 语音识别。录音 + 语音转文字（Whisper） |
| `audio_player` | 音频播放 |
| `send_image` | Clawli 模式下发图片到手机 |

##  记忆系统

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

##  Clawli 远程模式

通过 WebSocket 实现 PC-手机双向通信：

```bash
/remote start 9079 mypassword    # 启动本地服务
/remote proxy relay.example.com  # 通过中继服务器穿透内网
/remote stop                      # 停止服务
/remote status                    # 查看状态
```

功能：手机发消息给 AI、AI 回复推到手机、文件传输、图片识别。

##  安全机制

### 三模式切换 (`/safe`)

| 模式 | 图标 | 说明 |
|------|------|------|
| **普通模式** (默认) |  | AI 识别风险，有风险才请求确认 |
| **人工确认** |  | 所有指令都需要用户确认 |
| **无限制** |  | 直接执行，不检查 |

### 检查流程

```
工具调用 → safety.check()
  ├─ 快速预检（读取/查询类）→ 直接放行
  ├─ 普通模式 → AI 独立分析风险
  │   ├─ safe=true → 放行
  │   └─ safe=false → 展示风险等级+影响，y/n 确认
  └─ 特殊指令（rm/delete/chmod）→ 始终确认
```

### 代码沙箱

独立的安全代码执行环境：
- AST 级危险代码检测
- 模块白名单（阻断 os/subprocess/socket 等 25 个模块）
- 子进程隔离执行
- 内存限制

##  MCP 协议支持

所有 17 个插件均实现 MCP (Model Context Protocol) 定义，支持三种工具调用协议：

| 协议 | 说明 |
|------|------|
| **MCP** | Model Context Protocol 标准定义 |
| **FC** | OpenAI Function Calling 原生调用 |
| **JSON** | 传统 `{"action": "use_tool", ...}` 格式 |

`fc_tools.py` 自动将 MCP 定义转换为 OpenAI FC 格式，支持混合响应解析。

##  命令列表

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助 |
| `/safe` | 切换安全模式（普通→人工→无限制） |
| `/engine list` | 列出可用引擎 |
| `/engine switch <引擎>` | 切换引擎 |
| `/engine.openai models` | 列出 OpenAI 引擎模型 |
| `/chat save/list/open` | 聊天记录管理 |
| `/file.read <路径>` | 读取文件 |
| `/remote` | Clawli 远程连接帮助 |
| `/notify` | 切换任务完成通知 |
| `/scheduler` / `/remind` | 管理定时任务 |
| `/memory` | 管理记忆系统 |
| `/tui` | 切换 TUI 模式 |
| `/quit` | 退出 |

##  Web UI

纯静态 HTML 界面，无需后端，浏览器直接打开。

```bash
open webui.html        # macOS
xdg-open webui.html    # Linux
start webui.html       # Windows
```

##  项目结构

```
xiaoli-cli/
├── ai_cli.py                   # 主入口
├── webui.html                  # Web UI 界面 (纯静态 HTML)
├── launcher.py                 # 智能启动器（自动检测环境/安装依赖）
├── config.json.example         # 配置模板
├── easter_egg.py               #  彩蛋
│
├── xcli_core/                  # 核心模块
│   ├── cli_core.py             # 主循环 + 提示词构建
│   ├── cli_base.py             # 初始化 + 引擎/插件加载
│   ├── cli_tools.py            # 工具调用执行（支持 MCP/FC/JSON）
│   ├── cli_clawli.py           # Clawli 远程模式
│   ├── cli_code_exec.py        # 代码沙箱执行
│   ├── cli_display.py          # 显示输出
│   ├── cli_history.py          # 聊天记录
│   ├── config.py               # 配置管理
│   ├── constants.py            # 常量定义
│   ├── fc_tools.py             # MCP → FC 格式转换
│   ├── memory.py               # 记忆系统（长期记忆+日记+搜索+压缩）
│   ├── notification.py         # 跨平台系统通知
│   ├── plugin_manager.py       # 插件管理器（Liugin/Plugin 双协议）
│   ├── safety.py               # 统一安全层（AI 风险分析）
│   ├── sandbox.py              # 代码安全沙箱（AST 级检测）
│   └── tui.py                  # TUI 界面（Textual + 动画）
│
├── ai_engines/                 # AI 引擎
│   ├── ollama_engine.py        # Ollama 本地模型
│   └── openai_engine.py        # OpenAI 兼容格式
│
├── plugins/                    # 插件 (17 个)
│   ├── code_editor.py          # 代码编辑+搜索 (24 操作)
│   ├── git_tools.py            # Git 版本控制 (17 操作)
│   ├── cmd_executor.py         # Shell 命令执行
│   ├── file_manager.py         # 文件管理 (10 操作)
│   ├── auto_engineer.py        # 工程化自动化 (12 操作)
│   ├── task_manager.py         # 任务管理
│   ├── sub_agent.py            # 子 Agent 系统 (8 操作)
│   ├── browser_auto.py         # 浏览器自动化 (28 操作)
│   ├── image_generator.py      # 图像生成 (7 操作) ⭐ NEW
│   ├── memory_plugin.py        # 记忆系统 (11 操作) ⭐ NEW
│   ├── scheduler.py            # 定时任务
│   ├── tool_search.py          # 工具搜索
│   ├── network_tools.py        # 网络工具
│   ├── ai_search.py            # AI 搜索
│   ├── frontend_tester.py      # 前端测试
│   ├── speech_recognition.py   # 语音识别
│   └── send_image.py           # 图片发送
│
├── skills/                     # 技能 (Skill 协议)
├── image_engine/               # 图像识别引擎（Ollama 视觉模型）
├── tests/                      # 测试套件 (113 用例)
├── love.txt                    # 彩蛋情话
└── about.txt                   # 关于信息
```

##  测试

```bash
# 运行全部测试 (113 用例)
python -m pytest tests/ -v

# 语法检查
python -c "import py_compile; py_compile.compile('ai_cli.py', doraise=True)"
```

##  插件开发

小狸支持 `Liugin`（自研协议）和 `Plugin`（通用协议）两种类名，均可被插件管理器自动识别：

```python
class Plugin:  # 或 class Liugin
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

##  许可证

[MIT License](LICENSE)

##  链接

-  Gitee: https://gitee.com/shuiyu1123/xiaoli-cli
-  [更新日志](CHANGELOG.md)
-  [使用指南](HELP.md)
-  [AI 编程助手横评](compare.html)
