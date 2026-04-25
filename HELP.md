# 小狸 Pro-CLI 使用指南

## 快速上手

### 启动

```bash
python ai_cli.py
```

### 基本操作

- **退出**: `/quit` 或 `Ctrl+C`
- **帮助**: `/help`
- **版本**: `/about`

---

## AI 引擎

### 切换引擎

```
/engine switch ollama    # 切换到 Ollama 本地模型
/engine switch openai    # 切换到 OpenAI 兼容引擎
```

### 查看可用引擎

```
/engine list
```

### OpenAI 引擎管理

```
/engine.openai models    # 列出可用模型
/engine.openai set gpt-4o  # 切换模型
/engine.openai info      # 查看配置
```

---

## 安全模式

### 切换模式

```
/safe            # 循环切换: 普通 → 人工确认 → 无限制
/safe off        # 直接切换到无限制模式
/safe on         # 切换到普通模式
/safe manual     # 切换到人工确认模式
```

### 三种模式

| 模式 | 图标 | 说明 |
|------|------|------|
| **普通模式** (默认) | 🟢 | AI 自动识别风险，有风险才请求确认 |
| **人工确认** | 🟡 | 所有指令都需要用户 y/n 确认 |
| **无限制** | 🔴 | 直接执行，不检查 |

### 风险检查流程

当 AI 调用工具时，安全层会：
1. 快速预检 — 读取/查询类操作直接放行
2. AI 分析 — 调用引擎独立评估风险（不带历史对话）
3. 展示风险 — 如果有风险，显示指令、风险等级、可能影响
4. 用户确认 — 输入 y 执行，n 取消

特殊指令（`rm`、`delete`、`chmod` 等）无论哪个模式都需要确认。

---

## 核心工具

### 代码编辑 (`code_editor`)

| 操作 | 说明 | 示例 |
|------|------|------|
| `edit` | 精准替换 | `edit file.py old_code <<<>>> new_code` |
| `multi` | 批量编辑 | `multi file.py [{"old":"a","new":"b"}]` |
| `read_range` | 按行读取 | `read_range file.py 10 20` |
| `find` | 关键词搜索 | `find . keyword *.py` |
| `regex` | 正则搜索 | `regex . def\\s+\\w+ *.py` |
| `symbols` | 符号提取 | `symbols .` |
| `imports` | 导入分析 | `imports file.py` |
| `callers` | 调用查找 | `callers . func_name` |
| `structure` | 项目结构 | `structure .` |
| `stats` | 代码统计 | `stats .` |
| `ast_info` | AST 摘要 | `ast_info file.py` |
| `diff` | 文件对比 | `diff file1.py file2.py` |
| `create` | 创建文件 | `create new.py content` |
| `write` | 写入文件 | `write file.py content` |

### Git 操作 (`git_tools`)

| 操作 | 说明 |
|------|------|
| `status` | 查看状态 |
| `diff` | 查看变更 |
| `log --oneline 10` | 提交历史 |
| `add .` | 暂存所有 |
| `commit message` | 提交 |
| `branch` | 查看分支 |
| `checkout -b name` | 创建分支 |
| `smart-commit` | 智能提交（自动 add + 规范化消息） |
| `changelog` | 生成 CHANGELOG |
| `contributors` | 贡献者统计 |
| `summary` | 变更摘要 |

### 文件管理 (`file_manager`)

| 操作 | 说明 |
|------|------|
| `list . -p "*.py"` | 列出目录 |
| `read file.txt -n 50` | 读取前 50 行 |
| `write file.txt -c "内容"` | 写入文件 |
| `copy src dst` | 复制文件 |
| `move src dst` | 移动/重命名 |
| `delete file.txt` | 删除文件 |
| `delete dir -r` | 递归删除目录 |
| `search . -c "keyword"` | 搜索文件内容 |
| `info file.txt` | 文件详情 |
| `mkdir newdir` | 创建目录 |

### 命令执行 (`cmd_executor`)

```
run ls -la                    # 执行命令
run make build --timeout 60   # 60秒超时
```

### 浏览器自动化 (`browser_auto`)

| 操作 | 说明 |
|------|------|
| `start` | 启动浏览器 |
| `open https://example.com` | 打开网页 |
| `click .btn-primary` | 点击元素 |
| `fill #search keyword` | 填写输入框 |
| `text body` | 获取页面文本 |
| `screenshot page.png` | 页面截图 |
| `eval document.title` | 执行 JS |
| `wait .loaded` | 等待元素 |
| `pdf page.pdf` | 保存 PDF |
| `stop` | 关闭浏览器 |

### 子 Agent (`sub_agent`)

| 操作 | 说明 |
|------|------|
| `spawn coder 重构 main.py` | 创建子 Agent 并分配任务 |
| `list` | 列出所有子 Agent |
| `status agent_xxx` | 查看状态 |
| `result agent_xxx` | 获取结果 |
| `send agent_xxx 继续优化` | 发送消息 |
| `kill agent_xxx` | 终止 |
| `clean` | 清理已完成的 |

### 工程化 (`auto_engineer`)

| 操作 | 说明 |
|------|------|
| `lint .` | 代码检查 (ruff/flake8) |
| `format .` | 代码格式化 |
| `test .` | 运行测试 (pytest) |
| `build` | 构建项目 |
| `deps` | 检查过时依赖 |
| `complexity .` | 圈复杂度分析 |
| `security .` | 安全风险扫描 |
| `metrics .` | 代码质量指标 |
| `suggest .` | 改进建议 |
| `info` | 项目信息摘要 |

### 任务管理 (`task_manager`)

| 操作 | 说明 |
|------|------|
| `add 任务描述` | 添加任务 |
| `list` | 列出所有任务 |
| `complete 1` | 标记完成 |
| `in_progress 1` | 标记进行中 |
| `delete 1` | 删除任务 |
| `clear` | 清除已完成的 |

### 工具搜索 (`tool_search`)

```
tool_search 文件        # 搜索与文件相关的工具
tool_search git         # 搜索 Git 相关工具
tool_search 浏览器      # 搜索浏览器相关工具
```

---

## 聊天记录

```
/chat save my-session    # 保存当前对话
/chat list               # 列出所有对话
/chat open my-session    # 加载历史对话
```

---

## 自然语言交互

不需要记住命令格式，直接用自然语言：

```
"帮我看看 src/app.py 的第 10 到 20 行"
"搜索项目里所有用到 requests.get 的地方"
"提交代码，消息是修复登录bug"
"统计一下这个项目的代码量"
"打开百度搜索 Python 教程"
"创建一个子agent帮我重构utils.py"
```

AI 会自动选择合适的工具执行。

---

## 使用技巧

1. **引擎选择** — 本地开发用 `ollama`，云端用 `openai`（配 DeepSeek 等）
2. **安全模式** — 日常开发用普通模式，生产环境用人工确认模式
3. **子 Agent** — 复杂任务拆分给多个子 Agent 并行处理
4. **浏览器** — 自动化测试、网页抓取、表单填写
5. **工具搜索** — 不确定用什么工具时，先 `tool_search` 查一下
