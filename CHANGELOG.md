# 更新日志

所有重要更改都记录在此文件中。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## v5.1.3 (2026-04-28)

###  新增功能
- **图像生成插件** (`image_generator`) — 基于 ai.2x.nz 的 ComfyUI 在线服务，自然语言/Tag 双模式，支持中文描述，28 个角色工作流可选，分辨率可调（最大 1344×1344）
- **记忆系统插件** (`memory_plugin`) — 包装 `xcli_core/memory.py` 的完整记忆工具，AI 可写日记、读日记、搜索记忆、管理聊天记录、操作长期记忆 MEMORY.md
- **AI 编程助手横评页面** (`compare.html`) — 7 款工具（Claude Code / Codex CLI / Gemini CLI / Aider / Copilot CLI / 小狸 / TG HELPER）25+ 维度同口径对比

###  修复
- 修复记忆系统插件（`Liugin` 类在 `xcli_core/memory.py` 中定义但未被插件管理器加载）导致 AI 无法调用记忆工具的问题，新增 `plugins/memory_plugin.py` 包装层

###  文档
- 全面更新 README.md 至 v5.1.3
- 新增记忆系统、Clawli 远程模式、MCP 协议支持、定时任务、系统通知等功能说明
- 更新插件列表：15 个 → 17 个（+image_generator, +memory_plugin）
- 更新操作数：141 → 141+
- 补充 MCP 协议支持说明（17 个插件全部实现 MCP 定义）
- 补充插件开发文档中 `Liugin` / `Plugin` 双协议说明

###  贡献者
- 感谢 **艾轮 卧壳** 对本版本的贡献 🖤

---

## v5.1.2 (2026-04-26)

###  新增功能
- **自动语法检查系统** — 编辑操作(edit/multi/insert/delete_lines/create/write/append)完成后自动检查代码语法，通过显示 ✓，失败显示详细错误信息（行号、列号、错误描述）
- **主动语法检查** — 新增 `syntax_check <文件>` / `check <文件>` 操作，AI 可随时主动检查任意文件语法
- **多语言支持** — 语法检查覆盖 Python (ast.parse + py_compile)、JavaScript、TypeScript、JSON、YAML、TOML、HTML/XML (标签匹配)、CSS (括号匹配)、Shell (bash -n)、SQL
- **Diff 弹窗** — 每次编辑操作完成后自动弹出新终端窗口，显示修改前/修改后的完整内容（带行号）、diff 差异、新增/删除行数统计。支持 `diff_popup on/off` 开关，默认开启。兼容 Windows (cmd)、macOS (Terminal.app)、Linux (gnome-terminal/xterm/konsole 等)
- **默认模型更新** — Ollama 默认模型从 qwen2.5 更新为 gemma4:31b
- **Web UI** — 新增纯静态 HTML 界面 (`webui.html`)，无需后端，浏览器直接打开。包含对话界面（气泡+快捷指令+打字动画）、代码编辑器（行号+Tab+Ctrl+S）、文件浏览器、系统状态面板、引擎/工具一览、实时日志
- **TUI 动画系统** — 为 TUI 模式添加流畅动画效果，包括启动过渡、消息淡入、光标呼吸等微交互
- **TUI 多行输入** — 支持 Shift+Enter 换行输入，长 prompt 不再受限于单行，编辑体验大幅提升
- **Windows EXE 启动器** — `launcher.exe` 一键启动，无需预装 Python 环境，解压即用
- **Gitee Go CI 流水线** — 新增 `.gitee/pipeline.yml`，支持 Gitee 平台自动化构建与测试

###  修复
- 修复 TUI 模式下部分终端不支持 256 色导致渲染异常的问题
- 修复 `launcher.py` 在 Python 3.12 环境下 `datetime.utcnow()` 弃用警告
- 修复 Gitee Go 流水线 YAML 格式错误导致 CI 失败的问题
- 修复插件加载时 `__pycache__` 缓存文件干扰模块发现的边界情况

###  优化
- TUI 渲染性能优化，减少不必要的屏幕重绘，输入响应延迟降低约 40%
- 启动器依赖检测逻辑重构，离线环境下启动速度提升 2-3 秒
- 终端宽度适配优化，80 列窄终端下不再出现排版错乱
- 移除全局 emoji 依赖，适配无 emoji 字体的终端环境

###  文档
- 全面更新 README.md / README.en.md 版本标识至 v5.1.2
- 更新 CHANGELOG.md 补充 v5.1.2 变更记录

###  贡献者
- 感谢 **艾轮 卧壳** 对本版本的贡献 🖤

---

## v5.1.1 (2026-04-26)

###  新增功能
- **浏览器自动化插件** (`browser_auto`) — 基于 Playwright 的无头浏览器操控，31 个操作：导航/交互/截图/JS 执行/PDF/cookies
- **子 Agent 系统** (`sub_agent`) — 多 Agent 并行协作，spawn/list/status/result/send/kill，独立任务分配与结果回收
- **统一安全层** (`safety.py`) — AI 风险识别 + 三模式切换（普通/人工/无限制），所有工具调用前统一拦截检查
- **OpenAI 兼容引擎** (`openai_engine`) — 支持 DeepSeek、Grok、硅基流动、本地 vLLM 等所有 OpenAI 格式 API
- **自动化测试套件** — 113 个 pytest 用例，覆盖全部 15 个插件 + 引擎 + 核心模块
- **CI 工作流** — GitHub Actions: 语法检查 + ruff lint + pytest (Python 3.10/3.11/3.12 矩阵) + 项目结构验证

###  重构
- **插件大优化** — 17 个插件 → 15 个，5689 行 → 4309 行
  - `code_editor` + `code_search` → `code_editor`（编辑+搜索统一）
  - `git_tools` + `git_workflow` → `git_tools`（基础+工作流统一）
  - `auto_engineer` + `project_analyzer` → `auto_engineer`（质量+分析统一）
  - 删除 `scheduler.py`（空文件）
- **引擎精简** — 移除 7 个旧引擎（MiMo/GLM/QwQ/讯飞/iFlow/MaaS/SDK_openAI），保留 ollama + 新增 openai
- **启动器重写** — `launcher.py` 从 1741 行精简到 666 行，修复重复方法和硬编码引擎名
- **cmd_executor 跨平台** — 移除 Windows-only 限制，支持 Linux/macOS/Windows

###  修复
- 修复 `code_editor` 的 `diff_text` 解析器被 `split(maxsplit=2)` 拆坏分隔符的问题
- 修复 `cmd_executor` 中坏掉的 `from ai_cli import` 循环导入
- 修复 `launcher.py` 中两个重复的 `run()` 和 `show_final_result()` 方法

###  文档
- 全面更新 README.md / README.en.md 适配 v5.1.1
- 新增 `config.json.example` 配置模板

---

## v5.0.0 (2026-04-25)

###  新增功能
- **TUI v2** — 全新 TUI 界面，暗色主题 + 现代布局
- **完整 MCP 协议支持** — 为所有插件添加 MCP (Model Context Protocol) 定义
- **代码统计 Skill** (`code_stats`) — 新增 Skill 协议示例
- **工程化自动化插件** — 新增 `auto_engineer`、`project_analyzer`、`git_workflow`
- **任务调度器** (`scheduler`) — 定时任务支持

###  架构改进
- **重写代码沙箱** — 全新的安全沙箱实现，支持超时控制和资源限制
- **完整测试套件** — 192 个测试用例，覆盖核心功能

---

## v3.6.0-release (2026-04-25)

###  新增功能
- **精准代码编辑器** (`code_editor`) — 搜索替换、批量编辑、diff 对比
- **代码搜索理解** (`code_search`) — 跨文件搜索、正则匹配、符号提取
- **Git 版本控制** (`git_tools`) — 完整 Git 操作支持
- **TUI 默认模式** — 图形化界面为默认启动方式

###  架构重构
- 拆分 `ai_cli.py`（3860行）为模块化 `xcli_core/` 包
- 新增入口点: `python ai_cli.py`

---

## v3.5 (2026-02-12)
- 初始开源版本
