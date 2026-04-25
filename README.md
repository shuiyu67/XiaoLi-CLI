# 小狸 Pro-CLI

<p align="center">
  <strong>智能编程助手 — 支持精准代码编辑、代码搜索、Git 版本控制、多 AI 引擎切换</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-5.1.1-blue" alt="version">
  <img src="https://img.shields.io/badge/python-3.8+-green" alt="python">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="license">
</p>

---

## ✨ 特性

- 🤖 **多 AI 引擎** — 支持 Ollama 本地模型 + OpenAI 兼容格式（DeepSeek、Grok、硅基流动等），随时切换
- 🔧 **精准代码编辑** — 搜索替换、批量编辑、diff 对比、行级操作
- 🔍 **代码搜索理解** — 跨文件搜索、正则匹配、符号提取、依赖分析
- 🔄 **Git 版本控制** — 完整 Git 操作支持
- 🎨 **双模式界面** — TUI 图形化界面（默认）+ 传统命令行模式
- 🧩 **三协议插件系统** — Plugin 协议 / Skill 协议 / MCP 协议
- 🌐 **WebSocket 远程** — 支持远程连接
- 🛡️ **代码沙箱** — 安全的代码执行环境

## 📦 快速开始

### 安装

```bash
# 克隆仓库
git clone https://gitee.com/shuiyu1123/xiaoli-cli.git
cd xiaoli-cli

# 安装依赖
pip install -r requirements.txt
```

### 启动

```bash
# TUI 模式（默认，需 textual）
python -m xiaoli

# CLI 模式
python -m xiaoli --cli

# 指定引擎
python -m xiaoli --engine openai

# 查看版本
python -m xiaoli --version
```

### 依赖

**核心依赖：**

| 包名 | 用途 |
|------|------|
| `colorama` | 终端彩色输出 |
| `openai` | OpenAI 兼容接口 |
| `requests` | HTTP 请求 |
| `Pillow` | 图像处理 |
| `numpy` | 数值计算 |

**可选依赖：**

| 包名 | 用途 |
|------|------|
| `textual` | TUI 模式 |
| `opencv-python` | 图像处理增强 |
| `pygame` | 音频播放 |
| `websockets` | WebSocket 远程 |

## 🏗️ 项目结构

```
xiaoli-cli/
├── xiaoli/                     # 核心包（v3.6+ 模块化架构）
│   ├── __init__.py             # 版本信息
│   ├── __main__.py             # 入口点 (python -m xiaoli)
│   ├── app.py                  # 主应用（编排层）
│   ├── config.py               # 配置管理
│   ├── engines.py              # AI 引擎管理
│   ├── sandbox.py              # 代码安全沙箱
│   ├── prompt.py               # 系统提示词
│   ├── tui.py                  # TUI 界面
│   ├── conversation/           # 对话处理
│   │   ├── __init__.py         # 响应解析器
│   │   └── history.py          # 聊天记录
│   └── display/                # 显示输出
│       └── __init__.py         # CLI/TUI 双模式
│
├── plugins/                    # 插件（Plugin 协议）
│   ├── code_editor.py          # 精准代码编辑器 ⭐
│   ├── code_search.py          # 代码搜索理解 ⭐
│   ├── git_tools.py            # Git 版本控制 ⭐
│   ├── file_manager.py         # 文件管理
│   ├── cmd_executor.py         # 命令执行
│   ├── ai_search.py            # AI 搜索
│   ├── auto_engineer.py        # 自动工程化
│   ├── project_analyzer.py     # 项目分析
│   ├── git_workflow.py         # Git 工作流
│   ├── scheduler.py            # 任务调度
│   └── ...
│
├── skills/                     # 技能（Skill 协议）
│   ├── base.py                 # 技能基类
│   ├── code_stats.py           # 代码统计
│   └── file-manager/           # 文件管理技能
│
├── ai_engines/                 # AI 引擎
│   ├── ollama_engine.py        # Ollama 本地模型
│   └── openai_engine.py        # OpenAI 兼容格式（DeepSeek/Grok/硅基流动等）
│
├── image_engine/               # 图像引擎
├── core/                       # 旧版核心模块（兼容）
├── tests/                      # 测试套件
├── 开发文档/                    # 开发文档
├── ai_cli.py                   # 旧版入口（兼容）
├── launcher.py                 # 启动器
├── websocket_server.py         # WebSocket 服务
└── requirements.txt            # 依赖清单
```

## 🎮 使用指南

### 内置命令

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助信息 |
| `/quit` | 退出程序 |
| `/about` | 显示版本信息 |
| `/model <引擎>` | 切换 AI 引擎 |
| `/engine list` | 列出可用引擎 |
| `/chat save <名称>` | 保存聊天记录 |
| `/chat list` | 列出聊天记录 |
| `/chat open <名称>` | 加载聊天记录 |
| `/file.read <路径>` | 读取文件 |
| `/tui` | 切换 TUI 模式 |

### 核心工具

#### 代码编辑器 (`code_editor`)

```bash
# 精准替换
{"action":"use_tool","tool":"code_editor","args":"edit src/app.py
def old():
    pass
<<<>>>
def new():
    return True"}

# 批量编辑
{"action":"use_tool","tool":"code_editor","args":"multi src/app.py [{\"old\":\"old1\",\"new\":\"new1\"}]"}

# 查看代码
{"action":"use_tool","tool":"code_editor","args":"read_range src/app.py 10 20"}
```

#### 代码搜索 (`code_search`)

```bash
# 项目结构
{"action":"use_tool","tool":"code_search","args":"structure ."}

# 搜索代码
{"action":"use_tool","tool":"code_search","args":"find . process *.py"}

# 符号提取
{"action":"use_tool","tool":"code_search","args":"symbols ."}

# 代码统计
{"action":"use_tool","tool":"code_search","args":"stats ."}
```

#### Git 操作 (`git_tools`)

```bash
{"action":"use_tool","tool":"git_tools","args":"status"}
{"action":"use_tool","tool":"git_tools","args":"diff"}
{"action":"use_tool","tool":"git_tools","args":"log --oneline 10"}
{"action":"use_tool","tool":"git_tools","args":"commit 修复bug"}
```

### AI 引擎

| 引擎 | 类型 | 说明 |
|------|------|------|
| `ollama` | 本地 | Ollama 本地模型，无需 API 密钥 |
| `openai` | 云端/本地 | OpenAI 兼容格式，支持 DeepSeek、Grok、硅基流动、本地 vLLM 等 |

#### OpenAI 兼容引擎配置示例

```json
{
  "api": {
    "engines": {
      "openai": {
        "api_key": "你的API密钥",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat"
      }
    }
  }
}
```

### 远程连接

```bash
# 启动 WebSocket 服务
/remote start 9079 your_password

# 代理模式
/remote proxy relay.example.com:9079 server_pwd 12345 pc_pwd
```

## 🔌 插件开发

小狸支持三种插件协议，详见 [开发文档](开发文档/开发文档.md)。

### Plugin 协议

```python
class Plugin:
    """我的插件"""
    
    def __init__(self):
        self.usage = "使用说明"
        self.cli = None
    
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

### Skill 协议

```python
from skills.base import Skill, SkillResult

class MySkill(Skill):
    name = "my_skill"
    description = "技能描述"
    
    def run(self, **kwargs) -> SkillResult:
        return SkillResult(success=True, message="完成")
```

### MCP 协议

支持 Anthropic/OpenAI 标准的 Model Context Protocol，可与外部工具无缝集成。

## 🧪 测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行特定测试
python -m pytest tests/test_sandbox.py
```

## 🤝 贡献

欢迎贡献！请阅读 [贡献指南](CONTRIBUTING.md)。

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feat/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送分支 (`git push origin feat/amazing-feature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

## 🔗 链接

- 📦 Gitee: https://gitee.com/shuiyu1123/xiaoli-cli
- 📖 [开发文档](开发文档/开发文档.md)
- 📋 [更新日志](CHANGELOG.md)
- ❓ [使用指南](HELP.md)
