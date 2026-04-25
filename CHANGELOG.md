# 更新日志

## v3.6.0-release (2026-04-25)

### 🚀 新增功能
- **精准代码编辑器** (`code_editor`) - 搜索替换、批量编辑、diff 对比、行级操作
- **代码搜索理解** (`code_search`) - 跨文件搜索、正则匹配、符号提取、依赖分析
- **Git 版本控制** (`git_tools`) - 完整 Git 操作支持
- **TUI 默认模式** - 图形化界面为默认启动方式
- **彩蛋** - 运行 `python easter_egg.py` 发现惊喜

### 🏗️ 架构重构
- 拆分 `ai_cli.py`（3860行）为模块化 `xiaoli/` 包
- 新增入口点: `python -m xiaoli [--cli] [--engine X]`
- 配置管理、引擎管理、对话处理、显示输出独立模块
- 响应解析器提取为独立组件

### 🐛 修复
- 修复 `requirements.txt` 包名（PIL→Pillow, cv2→opencv-python）
- 修复服务器环境可选导入（tkinter/cv2/PIL）
- 兼容 `Plugin` 和 `Liugin` 两种插件类名
- TUI 不可用时自动降级到 CLI 模式

### 📦 依赖
- colorama, openai, requests, Pillow, numpy
- textual (可选, TUI 模式)

---

## v3.5 (2026-02-12)
- 初始开源版本
