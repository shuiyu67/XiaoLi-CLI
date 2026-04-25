# 小狸 Pro-CLI 使用指南

## 基本操作

### 启动和退出
- 启动程序: 运行 `python ai_cli.py`
- 退出程序: 输入 `/quit`

### 帮助命令
- `/help` - 显示帮助信息

## AI引擎管理

### 切换AI引擎
- `/model spark` - 切换到讯飞星火AI引擎

## 聊天记录管理

### 保存聊天记录
- `/chat save <名称>` - 将当前对话保存为指定名称的聊天记录

### 查看聊天记录
- `/chat list` - 显示所有已保存的聊天记录

### 加载聊天记录
- `/chat open <名称>` - 加载指定名称的聊天记录并继续对话

## 插件工具

AI可以自动调用以下工具来帮助您完成各种任务：

### 文件管理工具
- 功能：读取、写入、追加、删除、复制、移动文件和目录操作
- 用法示例：
  - `file_manager list` - 列出当前目录内容
  - `file_manager read test.txt` - 读取文件内容
  - `file_manager write test.txt 内容` - 写入文件
  - `file_manager append test.txt 内容` - 追加内容到文件
  - `file_manager delete test.txt` - 删除文件
  - `file_manager create test.txt` - 创建空文件
  - `file_manager mkdir new_dir` - 创建目录
  - `file_manager copy source.txt dest.txt` - 复制文件
  - `file_manager move source.txt dest.txt` - 移动文件
  - `file_manager info test.txt` - 查看文件信息
  - `file_manager tree` - 显示目录树结构

### 音频播放工具
- 功能：播放音频文件
- 用法示例：
  - `audio_player play` - 播放Ciallo～(∠・ω- )⌒☆-.mp3音频文件
  - `/ciallo` - 播放音频文件

## 基本操作命令

### 系统信息命令
- `/about` - 显示程序信息和版本详情

## 使用技巧

1. **自然语言交互**：直接用自然语言与AI对话，AI会理解您的意图并自动调用相应工具。

2. **工具调用**：当AI需要执行特定任务时，会自动调用相应的插件工具，并在屏幕上显示执行结果。

3. **聊天记录管理**：可以随时保存当前对话，在需要时加载之前的对话继续交流。

4. **路径操作**：
   - 支持用户主目录下的绝对路径操作
   - 支持项目目录和当前目录下的相对路径操作
   - 文件大小限制为50MB

5. **等待动画**：AI思考时会显示随机的温馨句子，每5秒更换一次。

6. **插件命令**：可以使用 `/命令名` 直接调用插件功能，如 `/file`、`/read`、`/write`、`/ciallo` 等。

## 注意事项

- 请勿尝试访问系统关键目录（如Windows系统目录、/etc等）
- 文件操作大小限制为50MB
- 音频播放需要系统支持相应的音频格式
- 可以随时使用 `/help` 命令查看帮助信息