# 贡献指南

感谢你对Lix CLI 项目的关注！以下是参与贡献的方式和规范。

## 如何贡献

### 报告 Bug

1. 在 Gitee 上创建 [Issue](https://gitee.com/shuiyu1123/xiaoli-cli/issues)
2. 描述清楚问题的复现步骤、期望行为和实际行为
3. 附上相关的日志输出或截图
4. 注明你的 Python 版本和操作系统

### 提交功能建议

1. 创建 Issue，标题以 `[Feature]` 开头
2. 描述你想要的功能和使用场景
3. 如果可能，提供实现思路

### 提交代码

```bash
# 1. Fork 并克隆
git clone https://gitee.com/你的用户名/xiaoli-cli.git
cd xiaoli-cli

# 2. 创建特性分支
git checkout -b feat/你的功能名

# 3. 开发并测试
# ... 编写代码 ...
python -m pytest tests/

# 4. 提交
git add .
git commit -m "feat: 描述你的改动"

# 5. 推送并创建 PR
git push origin feat/你的功能名
```

## 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>(<scope>): <description>

[可选 body]

[可选 footer]
```

### Type 类型

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式（不影响功能） |
| `refactor` | 重构 |
| `perf` | 性能优化 |
| `test` | 测试相关 |
| `chore` | 构建/工具链 |
| `ci` | CI/CD |

### 示例

```
feat(plugins): 新增 Docker 管理插件
fix(sandbox): 修复超时后进程未正确终止
docs: 更新 README 安装说明
refactor(engines): 统一引擎初始化逻辑
```

## 插件开发

### 新建插件

1. 在 `plugins/` 目录创建 `your_plugin.py`
2. 实现 `Plugin` 类：

```python
class Plugin:
    """插件描述"""
    
    def __init__(self):
        self.usage = "使用说明"
        self.cli = None
    
    def set_cli(self, cli):
        self.cli = cli
    
    def get_tool_info(self):
        return {
            "name": "your_plugin",
            "description": "插件描述",
            "keywords": ["关键词1", "关键词2"],
            "usage": self.usage
        }
    
    def handle(self, args: str) -> str:
        try:
            # 实现逻辑
            return "结果"
        except Exception as e:
            return f"错误: {e}"
```

3. 可选：实现 `get_mcp_definition()` 支持 MCP 协议
4. 在 `tests/` 中添加对应测试

### 插件检查清单

- [ ] 类名是 `Plugin`（或 `Liugin`，加载器两者都支持）
- [ ] 实现了 `get_tool_info()`、`handle()`、`set_cli()`
- [ ] 返回值是字符串
- [ ] 所有异常被捕获
- [ ] 包含 `usage` 属性
- [ ] 通过基本测试

## 代码风格

- 遵循 PEP 8
- 使用 4 空格缩进
- 函数和变量使用 `snake_case`
- 类名使用 `PascalCase`
- 字符串优先使用双引号
- 添加必要的注释和 docstring

## 测试

```bash
# 运行全部测试 (113 用例)
python -m pytest tests/ -v --tb=short
```

新功能必须包含测试，Bug 修复应补充回归测试。

## 问题？

如有疑问，欢迎在 Gitee 上提 Issue 或通过以下方式联系：

-  仓库：https://gitee.com/shuiyu1123/xiaoli-cli
