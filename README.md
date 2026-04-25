# 小狸 Pro-CLI

<p align="center">
  <strong>智能编程助手 — 代码编辑 · Git 集成 · 浏览器自动化 · 多 Agent 协作</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-5.1.1-blue" alt="version">
  <img src="https://img.shields.io/badge/python-3.10+-green" alt="python">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="license">
  <img src="https://img.shields.io/badge/tests-113%20passed-brightgreen" alt="tests">
</p>

---

## ✨ 特性

- 🤖 **双 AI 引擎** — Ollama 本地模型 + OpenAI 兼容格式（DeepSeek、Grok、硅基流动等）
- 🔧 **代码编辑与搜索** — 精准替换、批量编辑、符号提取、依赖分析、正则搜索
- 🔄 **Git 版本控制** — 完整 Git 操作 + 工作流自动化（smart-commit、changelog）
- 🌐 **浏览器自动化** — Playwright 驱动，导航/交互/截图/JS 执行/PDF
- 🤖 **子 Agent 系统** — 多 Agent 并行协作，独立任务分配与结果回收
- 🛡️ **统一安全层** — AI 风险识别 + 三模式切换（普通/人工/无限制）
- 🧩 **15 个插件 141 个操作** — 代码编辑、Git、浏览器、工程化、文件管理、任务管理等
- 🎨 **双模式界面** — TUI 图形化界面 + 传统命令行模式
- 🧪 **113 个自动化测试** — pytest 覆盖全部插件和核心模块

## 📦 快速开始

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
```

## 🤖 AI 引擎

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
        "model": "qwen2.5:latest"
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

## 🔌 插件列表 (15 个)

### 核心生产力

| 插件 | 操作数 | 说明 |
|------|--------|------|
| `code_editor` | 23 | 代码编辑+搜索。精准替换、批量编辑、find/regex/symbols/imports/callers/todo/structure |
| `git_tools` | 20 | Git 版本控制。status/diff/log/commit/branch + smart-commit/changelog/contributors |
| `cmd_executor` | 1 | Shell 命令执行。跨平台，超时控制，危险命令拦截 |
| `file_manager` | 11 | 文件系统。list/read/write/copy/move/delete/search/info/mkdir |
| `auto_engineer` | 16 | 工程化。lint/format/test/build/deps + 复杂度/安全扫描/质量指标 |
| `task_manager` | 7 | 任务管理。add/list/complete/delete/clear，JSON 持久化 |

### 高级功能

| 插件 | 操作数 | 说明 |
|------|--------|------|
| `sub_agent` | 8 | 子 Agent 系统。spawn/list/status/result/send/kill，多 Agent 并行协作 |
| `browser_auto` | 31 | 浏览器自动化。导航/点击/填写/截图/JS执行/PDF/cookies（基于 Playwright） |
| `tool_search` | — | 工具搜索。按关键词发现可用插件（供 AI 按需调用） |

### 辅助工具

| 插件 | 说明 |
|------|------|
| `network_tools` | 网络工具。ping/get/status/headers/ip |
| `ai_search` | AI 搜索。jina.ai 智能搜索 + 网页内容提取 |
| `frontend_tester` | 前端测试。HTML/CSS/JS 语法检查、响应式验证 |
| `speech_recognition` | 语音识别。录音 + 语音转文字 |
| `audio_player` | 音频播放 |
| `send_image` | Clawli 模式下发图片到手机 |

## 🛡️ 安全机制

### 三模式切换 (`/safe`)

| 模式 | 图标 | 说明 |
|------|------|------|
| **普通模式** (默认) | 🟢 | AI 识别风险，有风险才请求确认 |
| **人工确认** | 🟡 | 所有指令都需要用户确认 |
| **无限制** | 🔴 | 直接执行，不检查 |

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

## 🎮 命令列表

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助 |
| `/safe` | 切换安全模式（普通→人工→无限制） |
| `/safe off` | 直接切换到无限制模式 |
| `/safe manual` | 直接切换到人工确认模式 |
| `/engine list` | 列出可用引擎 |
| `/engine switch <引擎>` | 切换引擎 |
| `/engine.openai models` | 列出 OpenAI 引擎模型 |
| `/chat save/list/open` | 聊天记录管理 |
| `/file.read <路径>` | 读取文件 |
| `/tui` | 切换 TUI 模式 |
| `/quit` | 退出 |

## 🏗️ 项目结构

```
xiaoli-cli/
├── ai_cli.py                   # 主入口
├── launcher.py                 # 智能启动器
├── config.json.example         # 配置模板
│
├── xcli_core/                  # 核心模块
│   ├── cli_core.py             # 主循环 + 提示词构建
│   ├── cli_base.py             # 初始化 + 引擎/插件加载
│   ├── cli_tools.py            # 工具调用执行
│   ├── cli_display.py          # 显示输出
│   ├── cli_history.py          # 聊天记录
│   ├── cli_code_exec.py        # 代码执行
│   ├── config.py               # 配置管理
│   ├── constants.py            # 常量定义
│   ├── safety.py               # 统一安全层 ⭐
│   ├── sandbox.py              # 代码安全沙箱
│   ├── plugin_manager.py       # 插件管理器
│   └── tui.py                  # TUI 界面
│
├── ai_engines/                 # AI 引擎
│   ├── ollama_engine.py        # Ollama 本地模型
│   └── openai_engine.py        # OpenAI 兼容格式
│
├── plugins/                    # 插件 (15 个)
│   ├── code_editor.py          # 代码编辑+搜索
│   ├── git_tools.py            # Git 版本控制
│   ├── cmd_executor.py         # Shell 命令执行
│   ├── file_manager.py         # 文件管理
│   ├── auto_engineer.py        # 工程化自动化
│   ├── task_manager.py         # 任务管理
│   ├── sub_agent.py            # 子 Agent 系统
│   ├── browser_auto.py         # 浏览器自动化
│   ├── tool_search.py          # 工具搜索
│   ├── network_tools.py        # 网络工具
│   ├── ai_search.py            # AI 搜索
│   ├── frontend_tester.py      # 前端测试
│   ├── speech_recognition.py   # 语音识别
│   ├── audio_player.py         # 音频播放
│   └── send_image.py           # 图片发送
│
├── skills/                     # 技能 (Skill 协议)
├── image_engine/               # 图像识别引擎
├── tests/                      # 测试套件 (113 用例)
├── love.txt                    # 彩蛋情话
└── about.txt                   # 关于信息
```

## 🧪 测试

```bash
# 运行全部测试 (113 用例)
python -m pytest tests/ -v

# 语法检查
python -c "import py_compile; py_compile.compile('ai_cli.py', doraise=True)"
```

## 🔌 插件开发

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

    def handle(self, args: str) -> str:
        return "处理结果"
```

## 📄 许可证

[MIT License](LICENSE)

## 🔗 链接

- 📦 Gitee: https://gitee.com/shuiyu1123/xiaoli-cli
- 📋 [更新日志](CHANGELOG.md)
- ❓ [使用指南](HELP.md)
