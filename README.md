# 小狸 Pro-CLI

智能编程助手 — 支持精准代码编辑、代码搜索、Git 版本控制、多 AI 引擎切换。

## 快速开始

```bash
# 安装依赖
pip install colorama openai requests Pillow numpy

# 启动 CLI
python -m xiaoli

# 或指定引擎
python -m xiaoli --engine mimo

# 启动 TUI 模式（需要 textual）
python -m xiaoli --tui
```

## 核心能力

### 代码编辑 (code_editor)
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

### 代码搜索 (code_search)
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

### Git 操作 (git_tools)
```bash
{"action":"use_tool","tool":"git_tools","args":"status"}
{"action":"use_tool","tool":"git_tools","args":"diff"}
{"action":"use_tool","tool":"git_tools","args":"log --oneline 10"}
{"action":"use_tool","tool":"git_tools","args":"commit 修复bug"}
```

## 命令

| 命令 | 说明 |
|------|------|
| `/help` | 帮助信息 |
| `/quit` | 退出 |
| `/model <引擎>` | 切换 AI 引擎 |
| `/engine list` | 列出可用引擎 |
| `/chat save/list/open` | 聊天记录管理 |
| `/file.read <路径>` | 读取文件 |
| `/tui` | 切换 TUI 模式 |

## AI 引擎

| 引擎 | 类型 | 说明 |
|------|------|------|
| ollama | 本地 | Ollama 本地模型 |
| mimo | 云端 | 小米 MiMo |
| glm_http | 云端 | 智谱 GLM |
| qwq | 云端 | QwQ 深度思考 |
| maas_http | 云端 | MaaS |

## 架构

```
xiaoli/                  # 新架构（v3.6）
├── __init__.py          # 版本信息
├── __main__.py          # 入口点 (python -m xiaoli)
├── app.py               # 主应用（薄编排层）
├── config.py            # 配置管理
├── engines.py           # AI 引擎管理
├── sandbox.py           # 代码安全沙箱
├── prompt.py            # 系统提示词
├── conversation/        # 对话处理
│   ├── __init__.py      # 响应解析器
│   └── history.py       # 聊天记录
└── display/             # 显示输出
    └── __init__.py      # CLI/TUI 双模式

plugins/                 # 插件（Liugin 协议）
├── code_editor.py       # 精准代码编辑器 ⭐
├── code_search.py       # 代码搜索理解 ⭐
├── git_tools.py         # Git 版本控制 ⭐
├── file_manager.py      # 文件管理
├── ai_search.py         # AI 搜索
├── cmd_executor.py      # 命令执行
└── ...

ai_engines/              # AI 引擎
├── ollama_engine.py
├── mimo_engine.py
├── GLM_http_engine.py
└── ...
```

## 开发

```bash
# 克隆
git clone https://gitee.com/shuiyu1123/xiaoli-cli.git

# 安装依赖
pip install -r requirements.txt

# 运行
python -m xiaoli
```

## 许可证

MIT License
