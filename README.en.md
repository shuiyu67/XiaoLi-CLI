# XiaoLi Pro-CLI

<p align="center">
  <strong>AI Programming Assistant — Code Editing · Git · Browser Automation · Multi-Agent</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-5.1.1-blue" alt="version">
  <img src="https://img.shields.io/badge/python-3.10+-green" alt="python">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="license">
  <img src="https://img.shields.io/badge/tests-113%20passed-brightgreen" alt="tests">
</p>

---

##  Features

-  **Dual AI Engines** — Ollama local + OpenAI compatible (DeepSeek, Grok, SiliconFlow, etc.)
-  **Code Editing & Search** — Precise replace, batch edit, symbol extraction, regex search
-  **Git Integration** — Full Git operations + workflow automation
-  **Browser Automation** — Playwright-driven, navigate/interact/screenshot/JS execution
-  **Sub-Agent System** — Multi-agent parallel collaboration with task delegation
-  **Unified Safety** — AI risk analysis + 3-mode switching (Normal/Manual/Unrestricted)
-  **15 Plugins, 141 Operations** — Code, Git, browser, engineering, file management, etc.
-  **113 Automated Tests** — pytest coverage for all plugins and core modules

##  Quick Start

```bash
git clone https://gitee.com/shuiyu1123/xiaoli-cli.git
cd xiaoli-cli
pip install -r requirements.txt
python ai_cli.py
```

##  AI Engines

| Engine | Type | Description |
|--------|------|-------------|
| `ollama` | Local | Ollama local models, no API key needed |
| `openai` | Cloud/Local | OpenAI compatible: DeepSeek, Grok, SiliconFlow, local vLLM |

##  Plugins (15)

### Core Productivity

| Plugin | Ops | Description |
|--------|-----|-------------|
| `code_editor` | 23 | Code editing + search. replace/batch/find/regex/symbols/imports/callers/todo |
| `git_tools` | 20 | Git. status/diff/log/commit/branch + smart-commit/changelog/contributors |
| `cmd_executor` | 1 | Shell commands. Cross-platform, timeout, danger blocking |
| `file_manager` | 11 | File system. list/read/write/copy/move/delete/search/info/mkdir |
| `auto_engineer` | 16 | Engineering. lint/format/test/build/deps + complexity/security/metrics |
| `task_manager` | 7 | Task tracking. add/list/complete/delete/clear with JSON persistence |

### Advanced

| Plugin | Ops | Description |
|--------|-----|-------------|
| `sub_agent` | 8 | Sub-Agent system. spawn/list/status/result/send/kill, parallel collaboration |
| `browser_auto` | 31 | Browser automation. navigate/click/fill/screenshot/JS/PDF/cookies |
| `tool_search` | — | Tool discovery. Search available plugins by keyword |

### Utilities

| Plugin | Description |
|--------|-------------|
| `network_tools` | ping/get/status/headers/ip |
| `ai_search` | AI search via jina.ai + web content extraction |
| `frontend_tester` | HTML/CSS/JS syntax check, responsive validation |
| `speech_recognition` | Voice recording + speech-to-text |
| `audio_player` | Audio playback |
| `send_image` | Send images to phone (Clawli mode) |

##  Safety

Three modes (`/safe` to switch):

| Mode | Icon | Behavior |
|------|------|----------|
| **Normal** (default) |  | AI analyzes risk, confirms only when risk detected |
| **Manual** |  | All commands require user confirmation |
| **Unrestricted** |  | Execute directly, no checking |

##  Testing

```bash
python -m pytest tests/ -v   # 113 tests
```

##  License

[MIT License](LICENSE)
