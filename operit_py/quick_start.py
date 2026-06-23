# 欢迎来到 Python AI 工具开发终极入门教程 (v2.0 详细版)
# ====================================================================
#
# 本教程为初学者设计，特别是那些熟悉其他脚本语言但对 Python 不熟悉的开发者。
# 我们将从最基础的语法开始，一步步带你构建一个功能完整、结构优雅的AI工具，并详细解释每一步背后的"为什么"。
#
# 注：本文件由 TypeScript 版本翻译而来，保留了原有的教学结构与注释。


# =================================================================
# Part 0: 关于运行环境 (A Note on the Environment)
# =================================================================
#
# 在开始之前，你需要知道，你的代码并不是在真空中运行。它在一个特殊的"沙箱"环境中执行。
# 这个环境为你预先提供了一些全局可用的函数和对象，最重要的有：
#
# 1. `complete(result: dict)`:
#    - 这是你的工具与AI系统沟通的【唯一】桥梁。
#    - 当你的工具执行完毕，无论成功还是失败，都必须调用这个函数来返回结果。
#    - AI会根据你传入这个函数的对象内容，来决定下一步的行为。
#
# 2. `exports`:
#    - 这是一个特殊的对象，你可以把它看作是你代码文件的"公开接口"。
#    - 你需要将你的工具函数"挂载"到 `exports` 对象上，AI才能找到并调用它们。
#    - 示例: `exports.myToolName = myToolFunction`
#
# 3. `Tools`:
#    - 这是一个内置的工具集，提供了很多实用的辅助功能，比如文件读写、网络请求、系统命令等。
#    - 我们在本教程中会用到 `Tools.System.sleep()` 来演示异步操作。


# =================================================================
# Part 1: Python 核心语法快速入门
# =================================================================

# --- 1.1 变量声明 (Variables) ---
def variable_example():
    tool_name = "My Greeter Tool"  # 一旦设定，tool_name 就不能再被赋值（对应 TS 的 const）
    execution_count = 0            # execution_count 的值可以改变（对应 TS 的 let）
    console.log(f"工具名称: {tool_name}")

    execution_count = execution_count + 1
    console.log(f"这是第 {execution_count} 次执行。")

    # 下面这行代码会报错，因为 tool_name 是一个常量
    # tool_name = "New Name"


# --- 1.2 数据类型 (Data Types) ---
def data_types_example():
    # Python 是动态类型语言，无需显式声明类型
    user_name = "Alice"
    user_age = 30
    is_active = True

    # 对象（字典），键值对的集合
    user_info = {
        "name": "Bob",
        "age": 25,
        "premium": False
    }
    console.log(f"{user_info['name']} 的年龄是 {user_info['age']}")

    # 列表（对应 JS 的数组）
    permissions = ["read", "write", "execute"]
    console.log(f"用户的第一个权限是: {permissions[0]}")

    # 遍历列表
    for permission in permissions:
        console.log(f"权限: {permission}")


# --- 1.3 函数 (Functions) 与 异步操作 (Async Operations) ---
# - `async def`: 这是定义AI工具函数的标准方式。`async` 关键字表明该函数内部可能包含需要"等待"的操作。
# - `await`: 必须在 `async` 函数内部使用。它会暂停函数的执行，直到其后的异步操作完成，然后返回结果。
async def async_function_example(name):
    console.log(f"开始向 {name} 发送问候...")

    # `await` 在这里暂停函数，等待 Tools.System.sleep(1500) 完成
    # 这模拟了一个耗时1.5秒的网络请求或文件操作
    await Tools.System.sleep(1500)

    greeting_message = f"你好, {name}! 异步问候已送达。"
    console.log(greeting_message)

    # async 函数通过 return 返回的值
    return greeting_message


# --- 1.4 错误处理 (Error Handling) ---
# - `try...except`: 这是处理潜在错误的标准方式，对于健壮的工具至关重要。
# - `raise Exception(...)`: 当函数执行不下去时，主动"抛出"一个错误，中断当前 `try` 块的执行，并被 `except` 块捕获。
def error_handling_example(user_input):
    try:
        console.log("尝试处理输入...")

        # 步骤1: 检查输入是否为非空字符串
        if not isinstance(user_input, str) or user_input.strip() == '':
            # 如果检查失败，就"抛出"一个错误对象
            raise Exception("输入必须是一个非空的字符串。")

        # 步骤2: 如果代码能执行到这里，说明没有错误发生
        console.log(f"输入有效，内容是: \"{user_input}\"")
        return {"success": True, "data": user_input}

    except Exception as error:
        # 步骤3: 如果 `try` 块中任何地方抛出了错误，程序会立即跳转到这里
        console.error("发生了一个错误!")
        console.error(f"错误详情: {str(error)}")  # str(error) 包含了我们抛出时提供的信息

        # 在实际工具中，这里我们会调用 complete() 来报告失败
        return {"success": False, "message": str(error)}


# =================================================================
# Part 2: AI工具的本质 与 `complete()` 函数
# =================================================================
#
# 如前所述，一个AI工具就是一个函数，它通过 `complete()` 函数与AI系统交互。
# 下面是一个最基础的、结构完整的AI工具示例，我们为其中的关键部分添加了注释。
async def simple_greeter_tool(params):
    # 典型的工具函数总是在一个大的 try...except 块中
    try:
        # 1. 从 AI 接收到的参数中解构出需要的值
        user_name = params.get("user_name")

        # 2. 参数校验：永远不要相信输入！
        if not user_name:
            raise Exception("参数 'user_name' 缺失，无法生成问候语。")

        # 3. 执行核心业务逻辑
        greeting = f"你好, {user_name}! 欢迎来到AI工具的世界。"

        # 4. 调用 complete()，报告成功
        #    - success: True 表示工具成功完成了它的任务。
        #    - data: 存放工具的执行结果，这是AI最关心的部分。
        complete({
            "success": True,
            "data": greeting
        })

    except Exception as error:
        # 5. 如果 try 块中任何地方出错（无论是参数校验还是业务逻辑），都会进入这里
        console.error("simple_greeter_tool 执行失败:", error)

        # 6. 调用 complete()，报告失败
        #    - success: False 告诉AI任务失败了。
        #    - message: 存放清晰的错误信息，帮助AI理解失败原因。
        complete({
            "success": False,
            "message": f"工具执行失败: {str(error)}"
        })


# =================================================================
# Part 3: Metadata 和 函数导出 - 连接AI与代码的桥梁
# =================================================================
#
# 我们已经写好了工具函数，但AI如何知道它的存在、功能和用法呢？
# 这需要两样东西：
# 1. `METADATA` (元数据): 就像是工具的"说明书"。
# 2. `exports` (导出): 像是把工具函数"注册"到系统里。
#
# --- 3.1 详解 METADATA ---
# 文件顶部的 `# METADATA ...` 注释块就是这份说明书。AI在加载时会解析它。
# - `name`: (string) 工具集的唯一ID。
# - `description`: (string) 对整个工具集的详细描述。
# - `tools`: (array) 一个数组，包含此文件中所有可用的工具。
#   - `name`: (string) 单个工具的函数名。这个名字【必须】和后面 `exports` 中使用的名字完全一致。
#   - `description`: (string) 对这个工具能做什么的清晰描述。AI会根据这个描述来决定何时调用它。
#   - `parameters`: (array) 定义了此工具需要哪些参数。
#     - `name`: (string) 参数名。
#     - `description`: (string) 对参数用途的描述。
#     - `type`: (string) 参数的类型 (e.g., 'string', 'number', 'boolean')。
#     - `required`: (boolean) 这个参数是否是必需的。

# METADATA
# {
#     "name": "greeter_tool_v2",
#     "display_name": {
#         "zh": "问候工具 V2",
#         "en": "Greeting Tool V2"
#     },
#     "description": { "zh": "一个提供多种问候方式的教学工具集。", "en": "A tutorial tool package that demonstrates multiple greeting methods." },
#     "category": "Utility",
#     "tools": [
#         {
#             "name": "greet",
#             "description": { "zh": "向指定的人发送一个标准的问候。", "en": "Send a standard greeting to a specified person." },
#             "parameters": [
#                 {
#                     "name": "user_name",
#                     "description": { "zh": "要问候的人的名字。", "en": "Name of the person to greet." },
#                     "type": "string",
#                     "required": true
#                 }
#             ]
#         },
#         {
#             "name": "system_inspector",
#             "description": { "zh": "获取设备摘要信息，并在用户的HOME目录下查找符合特定模式的文件。", "en": "Get device summary information and find files matching a pattern under the user's HOME directory." },
#             "parameters": [
#                 {
#                     "name": "search_pattern",
#                     "description": { "zh": "用于文件搜索的通配符模式，例如：'*.txt' 或 'documents/*.pdf'。", "en": "Glob pattern for file search, e.g. '*.txt' or 'documents/*.pdf'." },
#                     "type": "string",
#                     "required": true
#                 }
#             ]
#         }
#     ]
# }

# --- 3.2 详解 exports ---
#
# `exports` 是一个空对象，等待你来填充。
# 你必须将你的工具函数赋值给 `exports` 对象的一个属性，属性名必须和 `METADATA` 中定义的工具 `name` 完全一致。
# 只有这样，AI才能把"说明书"和"实际的函数实现"关联起来。
#
# `exports.greet = simple_greeter_tool`
#
# 上面这行代码的意思是：
# "当AI想要调用名为 'greet' 的工具时，请执行 `simple_greeter_tool` 这个函数。"
# (我们将在教程的最后进行统一导出，所以暂时注释掉这行)


# =================================================================
# Part 4: 模块作用域 - 隔离代码，避免冲突
# =================================================================
#
# 在 Python 中，每个 .py 文件本身就是一个模块，天然拥有独立的作用域。
# 在文件顶层声明的变量和函数不会污染其他模块，因此不需要像 JS 那样使用 IIFE。
# 我们可以通过定义函数来组织"私有"实现，再选择性地导出需要公开的接口。

# 使用模块作用域重构我们的问候工具
GREETER_VERSION = "2.0"


def log_with_timestamp(message):
    import datetime
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    console.log(f"[{timestamp}][v{GREETER_VERSION}] {message}")


# 这是我们真正的业务逻辑实现
async def perform_greeting(params):
    try:
        import json
        log_with_timestamp(f"开始执行问候工具，参数: {json.dumps(params, ensure_ascii=False)}")
        user_name = params.get("user_name")
        if not user_name:
            raise Exception("参数 'user_name' 缺失。")
        greeting = f"你好, {user_name}! (来自模块模式 v{GREETER_VERSION})"
        complete({"success": True, "data": greeting})
    except Exception as error:
        log_with_timestamp(f"问候工具失败: {str(error)}")
        complete({"success": False, "message": str(error)})


# =================================================================
# Part 5: Wrapper模式 - 终极形态，让代码更健壮、更简洁
# =================================================================
#
# 观察上面的代码，即使使用了模块作用域，`perform_greeting` 函数内部仍然有重复的 `try/except` 和 `complete()` 调用。
# 在软件工程中，重复的代码（boilerplate）是维护的噩梦。
#
# 我们可以创建一个 `wrapper` (包装器) 函数来终结这种重复。
# Wrapper 的职责非常清晰：
# 1. 接收一个"核心业务逻辑函数"作为输入。
# 2. 在内部建立 `try/except` 安全网。
# 3. 负责调用核心函数，并等待其结果。
# 4. 无论成功还是失败，都由它来调用 `complete()` 并返回标准格式的结果。
#
# 这样，我们编写的工具函数就可以变得非常纯粹：只关心输入、业务处理和输出（通过 `return` 和 `raise`），
# 完全不用理会 `try/except` 和 `complete` 这些模板代码。

# --- 最终的、最推荐的开发模式 ---


# 1. 定义我们的通用 Wrapper 函数
#    它接收一个核心逻辑函数和其所需的参数。
async def wrap(core_function, params):
    try:
        # 调用核心业务逻辑，并使用 await 等待其完成
        result = await core_function(params)

        # 核心逻辑成功返回，Wrapper负责包装成标准成功对象并调用complete
        complete({
            "success": True,
            "message": "工具执行成功。",
            "data": result  # 将核心函数的返回值放入data字段
        })

    except Exception as error:
        import traceback
        console.error(f"工具 [{core_function.__name__}] 执行时捕获到错误:", error)

        # 核心逻辑抛出异常，Wrapper负责捕获并包装成标准失败对象
        complete({
            "success": False,
            "message": f"错误: {str(error)}",  # 将错误信息放入message字段
            "error_stack": traceback.format_exc()  # 附带完整的错误堆栈以供调试
        })


# =================================================
#  核心业务逻辑区 (Core Logic Functions)
# =================================================

# 2a. "问候"工具的核心逻辑
async def greet_core_logic(params):
    user_name = params.get("user_name")
    if not user_name or user_name.strip() == '':
        raise Exception("user_name 不能为空。")
    greeting = f"你好, {user_name}! 这是一个采用终极Wrapper模式的工具。"
    return greeting


# 2b. "系统检查器"工具的核心逻辑
async def inspect_system_core_logic(params):
    search_pattern = params.get("search_pattern")
    if not search_pattern:
        raise Exception("search_pattern 不能为空。")

    console.log(f"开始系统检查，搜索模式: '{search_pattern}'")

    # 为了让逻辑更清晰，我们一步一步地、顺序地调用工具
    # 1. 首先，获取设备信息
    console.log("正在获取设备信息...")
    device_info = await Tools.System.getDeviceInfo()
    console.log("设备信息获取成功。")

    # 2. 然后，查找文件
    console.log(f"正在主目录 ('~') 下查找文件，模式: '{search_pattern}'")
    found_files = await Tools.Files.find('~', search_pattern)
    console.log("文件查找成功。")

    # 组合结果并返回一个结构化的对象
    return {
        "device": device_info,
        "files": found_files
    }


# =================================================
#  导出函数封装区 (Exported Functions)
# =================================================

# 3a. 暴露给AI的"问候"函数
async def greet_exported_function(params):
    await wrap(greet_core_logic, params)


# 3b. 暴露给AI的"系统检查器"函数
async def inspect_system_exported_function(params):
    await wrap(inspect_system_core_logic, params)


# =================================================================
# Part 6: 使用内置工具集 (Using the Built-in `Tools`)
# =================================================================
#
# 沙箱环境提供了一个强大的全局对象 `Tools`，它是你与外部世界交互的主要入口。
# `Tools` 对象被组织成多个模块，每个模块负责一类特定的功能。
#
# 主要的模块包括：
# - `Tools.System`: 系统级操作。
#   - `getDeviceInfo()`: 获取设备信息（型号、操作系统版本等）。
#   - `sleep(ms)`: 让工具暂停指定的毫秒数。
#   - `shell(command)`: 执行shell命令。
# - `Tools.Files`: 文件系统操作。
#   - `read(path)`: 读取文件内容。
#   - `write(path, content)`: 写入内容到文件。
#   - `find(directory, pattern)`: 在指定目录中查找匹配模式的文件。
#   - `deleteFile(path)`: 删除文件或目录。
# - `Tools.Net`: 网络操作。
#   - `fetch(url, options)`: 发起HTTP请求，类似于浏览器中的`fetch`。
# - `Tools.UI`: 与设备UI交互（高级功能）。
# - `Tools.Memory`: 记忆管理功能。
# - `Tools.FFmpeg`: 音视频处理（高级功能）。
#
# 所有的 `Tools` 函数都是【异步】的，意味着你必须使用 `await` 来调用它们，
# 并且调用它们的代码必须位于 `async` 函数内部。
#
# 在上面的 `Part 5` 中，我们已经为你演示了如何实现一个名为 `system_inspector` 的新工具。
# 它完美地展示了：
# 1. 如何在核心逻辑函数中调用 `Tools.System.getDeviceInfo()` 和 `Tools.Files.find()`。
# 2. 如何按顺序地调用多个异步工具，等待每一个操作完成后再进行下一步。
# 3. 如何将这些调用集成到我们健壮的 `Wrapper` 模式中。


# ==========================================
# 最终导出 (Final Export)
# ==========================================
# 将我们在最终模式中定义的函数，挂载到exports上。
# 这里的 `greet` 和 `system_inspector` 必须和METADATA中定义的工具 `name` 完全一致。
exports.greet = greet_exported_function
exports.system_inspector = inspect_system_exported_function

# 恭喜! 你已经学完了从零到一的完整开发流程。
#
# 现在回顾一下我们构建最终代码形态的旅程：
# 1. **基础语法**: 掌握了编写代码的基本工具。
# 2. **基础工具+complete()**: 理解了AI工具的本质和与系统的交互方式。
# 3. **Metadata+exports**: 学会了如何让AI"发现"并"使用"你的工具。
# 4. **模块作用域**: 学会了如何通过作用域隔离来组织代码，避免命名冲突，使代码更模块化。
# 5. **Wrapper模式**: 学会了如何通过分离"业务逻辑"和"模板代码"来编写更简洁、更健壮、更易于维护的工具代码。
# 6. **内置工具 `Tools`**: 学会了如何利用系统提供的强大工具与文件、网络和操作系统进行交互。
#
# 这套"Wrapper + 模块作用域 + Tools"的组合是经过实践检验的最佳实践，强烈建议你在开发自己的工具时采用它。
