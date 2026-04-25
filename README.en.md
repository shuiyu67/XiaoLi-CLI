# XiaoLi Pro-CLI

<p align="center">
  <strong>Intelligent Programming Assistant — Precise Code Editing, Code Search, Git Integration, Multi-AI Engine Support</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-5.0.0-blue" alt="version">
  <img src="https://img.shields.io/badge/python-3.8+-green" alt="python">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="license">
</p>

---

## ✨ Features

- 🤖 **Multi AI Engines** — Ollama local models + OpenAI compatible format (DeepSeek, Grok, SiliconFlow, etc.)
- 🔧 **Precise Code Editing** — Search & replace, batch edits, diff comparison, line-level operations
- 🔍 **Code Search & Understanding** — Cross-file search, regex matching, symbol extraction, dependency analysis
- 🔄 **Git Integration** — Full Git workflow support
- 🎨 **Dual UI Modes** — TUI graphical interface (default) + traditional CLI mode
- 🧩 **Triple Protocol Plugin System** — Plugin / Skill / MCP protocols
- 🌐 **WebSocket Remote** — Remote connections and QQ bot integration
- 🛡️ **Code Sandbox** — Secure code execution environment

## 📦 Quick Start

### Installation

```bash
git clone https://gitee.com/shuiyu1123/xiaoli-cli.git
cd xiaoli-cli
pip install -r requirements.txt
```

### Usage

```bash
# TUI mode (default, requires textual)
python -m xiaoli

# CLI mode
python -m xiaoli --cli

# Specify engine
python -m xiaoli --engine openai

# Show version
python -m xiaoli --version
```

### Dependencies

**Core:**

| Package | Purpose |
|---------|---------|
| `colorama` | Terminal colored output |
| `openai` | OpenAI compatible API |
| `requests` | HTTP requests |
| `Pillow` | Image processing |
| `numpy` | Numerical computation |

**Optional:**

| Package | Purpose |
|---------|---------|
| `textual` | TUI mode |
| `opencv-python` | Enhanced image processing |
| `pygame` | Audio playback |
| `websockets` | WebSocket remote |

## 🏗️ Architecture

```
xiaoli-cli/
├── xiaoli/                     # Core package (v3.6+ modular architecture)
│   ├── __main__.py             # Entry point (python -m xiaoli)
│   ├── app.py                  # Main application (orchestration layer)
│   ├── config.py               # Configuration management
│   ├── engines.py              # AI engine management
│   ├── sandbox.py              # Code execution sandbox
│   ├── prompt.py               # System prompts
│   ├── tui.py                  # TUI interface
│   ├── conversation/           # Conversation handling
│   └── display/                # Display output (CLI/TUI dual mode)
│
├── plugins/                    # Plugins (Plugin protocol)
│   ├── code_editor.py          # Precise code editor ⭐
│   ├── code_search.py          # Code search & understanding ⭐
│   ├── git_tools.py            # Git version control ⭐
│   └── ...                     # 20+ plugins
│
├── skills/                     # Skills (Skill protocol)
├── ai_engines/                 # AI engine implementations
├── image_engine/               # Image processing engines
├── tests/                      # Test suite
└── requirements.txt            # Dependencies
```

## 🎮 Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/quit` | Exit |
| `/about` | Show version info |
| `/model <engine>` | Switch AI engine |
| `/engine list` | List available engines |
| `/chat save <name>` | Save conversation |
| `/chat list` | List conversations |
| `/chat open <name>` | Load conversation |
| `/tui` | Toggle TUI mode |

## 🔌 Plugin Development

XiaoLi supports three plugin protocols. See [Development Documentation](开发文档/开发文档.md) for details.

### Plugin Protocol

```python
class Plugin:
    def get_tool_info(self):
        return {"name": "my_tool", "description": "...", "keywords": [...]}
    
    def handle(self, args: str) -> str:
        return "result"
```

### Skill Protocol

```python
from skills.base import Skill, SkillResult

class MySkill(Skill):
    name = "my_skill"
    def run(self, **kwargs) -> SkillResult:
        return SkillResult(success=True, message="Done")
```

### MCP Protocol

Supports Anthropic/OpenAI Model Context Protocol for seamless external tool integration.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Create a Pull Request

## 📄 License

This project is licensed under the [MIT License](LICENSE).

## 🔗 Links

- 📦 Gitee: https://gitee.com/shuiyu1123/xiaoli-cli
- 📖 [Development Docs](开发文档/开发文档.md)
- 📋 [Changelog](CHANGELOG.md)
