# 更新日志

## v6.0.0 (2026-06-23)

**重大更新：插件生态 + 深度思考 + 工作模式**

### 新增插件

- **terminal** (终端模拟器 v2)：AI 的虚拟键盘和屏幕
  - 极简接口：open / type / key / read / last / wait
  - 持久 Shell 会话，环境变量跨命令保持
  - Python REPL 交互，多会话并行
  - `last [N]` 只看最近 N 行，避免上下文爆炸
  - 纯标准库，零外部依赖，全平台

- **operit_bridge** (Operit 双向工具桥接)：兼容 Operit AI 生态
  - 自动扫描 plugins/operit/ 加载 Operit 脚本
  - 解析 47 个真实 Operit 脚本，288 个工具
  - 兼容标准 JSON + HJSON（自研逐字符解析器）
  - 双向格式转换：Operit METADATA ↔ MCP ↔ FC

- **image_reader** (图片读取)：从图片中提取文字
  - OCR 文字识别（Tesseract / Windows PowerShell）
  - ASCII 字符画、图片信息、Base64、哈希

### 深度思考

- OpenAI 引擎支持 `/engine.openai think [on|off|low|medium|high]`
- 原生支持：DeepSeek、MiMo、OpenAI o-series、Claude、Grok、Gemini thinking
- 提示词兜底：不支持原生的模型自动注入思考提示词
  - low: 无额外提示词
  - medium: 逐步思考提示
  - high: 工程级深度推理框架

### 工作模式

- `/mode` 或 `/safe` 切换四种工作模式
- 普通：AI 识别风险，有风险才确认
- 人工确认：所有指令都需确认
- 无限制：直接执行
- **计划模式（新增）**：全自动 + 审查 + 重试 + 引擎切换
  - 引擎错误 10 次自动切换引擎
  - 无其他引擎继续重试，错误不入上下文
  - 任务完成后自动审查，发现问题自动重试

### 系统提示词

- 新增兜底策略：插件仓库 → 网上搜索 → 自己写插件
- 放弃是最后的选择

### 插件整理

- 删除图像类插件：ai_image、image_generator、send_image
- 移至插件仓库：audio_player、bookmark_manager、color_picker
- 主仓库保留 24 个必备生产力插件

### 配置更新

- config.json.example 新增 deep_think / reasoning_effort 配置
- plugins_config.py 重写，统一启用所有核心插件
- plugin_registry.json 同步更新

---

## v5.4.2 (2026-06-23)

**新增插件：**

- **terminal** (终端模拟器)：纯标准库实现的持久交互式终端
  - 持久 Shell 会话，环境变量/目录跨命令保持
  - Python REPL 交互 (`-i` 模式，`PYTHONUNBUFFERED`)
  - 多会话管理（open/switch/list/close）
  - 特殊按键支持（Ctrl+C/D/Z、Tab、方向键等 18 种）
  - 文件哨兵机制（避免 stdout 提示符污染）
  - Windows/Linux/macOS 全平台，零外部依赖
  - 13 个单元测试

**其他变更：**

所有重要更改都记录在此文件中。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## v5.4.0 (2026-05-09) — Release

### ✨ 新增功能

- **跨平台进程保护模块** (`xcli_core/process_protection.py`)
  - **单实例保护** — 防止重复启动，Windows 使用命名 Mutex，macOS/Linux 使用 fcntl 文件锁（自动清理残留锁文件）
  - **进程优先级提升** — Windows: `SetPriorityClass` (ABOVE_NORMAL/HIGH/REALTIME)，macOS/Linux: `os.nice()` + `renice`
  - **Windows PPL 风格保护** — `SetErrorMode` 抑制系统错误弹窗 (SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX)、`faulthandler` 崩溃堆栈捕获
  - **POSIX 信号保护** — macOS/Linux 忽略 SIGHUP（终端关闭不退出）、注册 SIGTERM 优雅关闭、macOS 忽略 SIGPIPE
  - **看门狗监控** — 后台线程监控父进程状态，父进程退出时自动清理并退出
  - **关闭钩子系统** — 注册自定义清理函数，进程退出时自动执行
  - **一键启用** — `enable_process_protection()` 单函数调用启用全部保护
  - **`/protect` 命令** — CLI 中查看保护状态，`/protect test` 重新测试所有保护

###  改进

- `platform_utils.py` 新增 `is_process_running()`、`get_process_priority()`、`set_process_priority()` 跨平台工具函数
- `cli_base.py` 启动时自动初始化进程保护，退出时自动清理
- `cli_core.py` 启动 banner 显示保护状态图标（单实例/优先级/PPL/看门狗）
- 全版本号统一更新至 v5.4.0

---

## v5.2.0 (2026-05-08)

### ✨ 新增功能

- **插件内存管理器** (`plugin_memory_manager.py`) — TTL 自动淘汰 + 懒加载机制
  - 后台线程定期扫描空闲插件，超过 TTL（默认 5 分钟）自动从内存卸载，释放资源
  - AI 调用已卸载的插件时自动重新加载（懒加载），对用户完全透明
  - 核心插件（`tool_search`）可钉住永不淘汰，保障基础功能可用
  - 可配置参数：TTL 时间、最大空闲插件数、扫描间隔、钉住列表
  - `/status` 命令和 TUI 侧栏实时显示内存管理状态（已加载/已卸载/统计）
  - `search_tools` 支持搜索已卸载插件（使用缓存的元数据，无需加载实例）

###  统一插件格式

- **统一自研插件入口类名为 `Liugin`** — 18 个插件从 `class Plugin` 统一为 `class Liugin`
  - 加载器保留 `Plugin` 回退兼容，第三方插件仍可用旧格式
  - 测试块中 `Plugin()` 调用同步更新为 `Liugin()`

###  TUI 修复

- **修复消息分类失效** — `_write_raw` 中空字符串 `'' in msg` 永远为 True，导致所有消息显示为工具成功样式；替换为正确的 emoji 标记（✅/❌/🤖）
- **修复侧栏切换失效** — Textual 无 `.visible` 布尔属性，改用 `has_class("hidden")` + CSS 类控制显隐
- **修复侧栏隐藏动画** — CSS `display: none` 阻止过渡动画，改用 `width: 0` + `opacity: 0` 方案
- **修复 TextArea 导入缺失** — `constants.py` 可用性检查未导入 `TextArea`、`Rule`
- **修复 `set_timer(0)` 崩溃** — 欢迎动画首行延迟为 0.0 导致 Textual 8.x 除零错误（`ZeroDivisionError`），使用 `max(0.01, delay)` 修复

###  改进

- `UnifiedToolManager` 重构：集成 `PluginMemoryManager`，所有工具访问统一走 `_ensure_loaded` 路径
- 新增 `get_all_tools_info()` 方法，系统提示词可列出所有注册工具（含已卸载）
- 新增 `get_tool_by_name()` / `memory_manager` 属性，兼容旧 `LiuginManager` 接口

---

## v5.1.4 (2026-04-29)

###  新增功能

- **桌面GUI自动化插件** (`gui_auto`, 20 操作) — 基于 Windows UI Automation (UIA) API，AI 可识别和操控桌面应用
  - 元素树获取 (`snapshot`) — 获取整个屏幕或指定窗口的 UI 元素树，支持自定义遍历深度
  - 元素交互 — 点击/右键/双击（名称模糊匹配 + 坐标点击），文本输入（中文 Unicode）、清空、发送按键
  - 窗口管理 — 列出所有窗口 (`windows`)、聚焦指定窗口 (`focus`)
  - 元素查询 — 查找/查找所有/详情/值/子树/存在检查/状态，共 8 个查询操作
  - 高级功能 — 等待元素出现（带超时）、高亮闪烁元素（GDI 红色边框）、滚动
  - MCP/FC 完整定义，AI 通过 Function Calling 直接调用，非 Windows 环境优雅降级

- **AI 生图插件** (`ai_image`) — 基于 ai.2x.nz 自然语言生图接口
  - 自然语言描述 + 直接 Tag 双模式
  - 工作流切换、画风选择、分辨率调整
  - 异步生成 + WebSocket 进度推送
  - 生成历史记录

- **Web UI 后端** (`webui_server.py`) — WebSocket 实时通信 + 静态文件服务
  - 纯 Python 实现，基于 `websockets` 库
  - 支持命令行参数 (`--port` / `--host`)
  - 与前端 `webui.html` 配合，提供完整的浏览器端 AI 交互体验

###  改进

- **Web UI 前端重写** (`webui.html`) — 从纯静态页面升级为 WebSocket 实时交互
  - 大厂设计感 UI，响应式布局
  - 实时消息流、打字机效果
  - 支持工具调用结果展示

###  文档

- 更新 README.md: 插件列表、项目结构、badge 版本号
- 更新 CHANGELOG.md: v5.1.4 完整变更记录
- 更新 HELP.md: 新增 GUI 自动化使用说明

###  测试

- 新增 gui_auto 插件 30 个单元测试（工具信息、MCP 定义、参数转换、错误处理、操作路由）

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
