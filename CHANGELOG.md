# 更新日志

所有重要更改都记录在此文件中。格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

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
