# Operit 脚本目录

此目录存放 **Operit AI 格式**的第三方工具脚本（`.js` / `.ts`）。

`operit_bridge` 插件会自动扫描此目录，解析所有带 `METADATA` 块的脚本，
并将它们注册为 xiaoli-cli 可调用的工具。

## 如何使用

### 1. 放入 Operit 脚本

将 Operit 格式的 `.js` 或 `.ts` 文件放入此目录即可。脚本必须包含 `/* METADATA ... */` 块。

```bash
# 从 Operit 社区下载脚本
cp ~/Downloads/some_tool.js plugins/operit/

# 或从 Operit 仓库克隆
git clone https://github.com/AAswordman/Operit.git /tmp/operit-repo
cp /tmp/operit-repo/examples/*.ts plugins/operit/
```

### 2. 脚本格式要求

每个脚本头部必须有 METADATA 块：

```javascript
/*
METADATA
{
    "name": "ToolName",
    "display_name": { "zh": "工具名", "en": "Tool Name" },
    "description": "工具描述",
    "author": ["作者"],
    "category": "Utility",
    "tools": [
        {
            "name": "function_name",
            "description": "功能描述",
            "parameters": [
                {
                    "name": "param1",
                    "description": "参数说明",
                    "type": "string",
                    "required": true
                }
            ]
        }
    ]
}
*/
```

### 3. 在 xiaoli-cli 中使用

```
operit_bridge list              # 查看已加载的 Operit 工具
operit_bridge scan plugins/operit  # 手动重新扫描
operit_bridge info ToolName__function_name  # 查看工具详情
```

AI 也可以直接通过 Function Calling 调用这些工具。

## 支持的 category

- `Automatic` - 自动化
- `Chat` - 对话
- `Development` - 开发
- `Draw` - 绘图
- `File` - 文件
- `Life` - 生活
- `Map` - 地图
- `Media` - 媒体
- `Memory` - 记忆
- `Network` - 网络
- `Search` - 搜索
- `System` - 系统
- `Utility` - 工具
- `Workflow` - 工作流

## 参考

- Operit 脚本开发指南: https://github.com/AAswordman/Operit/blob/main/docs/SCRIPT_DEV_GUIDE.md
- Operit 示例脚本: https://github.com/AAswordman/Operit/tree/main/examples
