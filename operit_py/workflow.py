# METADATA
# {
#   "name": "workflow",
#   "display_name": {
#     "zh": "工作流管理",
#     "en": "Workflow Management"
#   },
#   "description": {
#     "zh": "工作流管理工具：创建/查询/更新/启用/禁用/删除/触发执行；支持 on_success/on_error 分支；支持语音触发（speech）。",
#     "en": "Workflow management tools for creating/querying/updating/enabling/disabling/deleting workflows, triggering execution, and branching via on_success/on_error. Supports speech trigger (speech)."
#   },
#   "category": "Workflow",
#   "enabledByDefault": true,
#   "tools": [
#     {
#       "name": "usage_advice",
#       "description": {
#         "zh": "工作流工具使用建议（给 AI）：\n\n- 核心概念（请优先对齐这些语义）：\n  - 节点类型：trigger/execute/condition/logic/extract\n  - 触发节点类型：manual/schedule/tasker/intent/speech\n  - 参数引用（ParameterValue）：静态值 vs 引用其他节点输出\n  - 分支连线 condition 的语义：on_success/on_error/true/false/regex\n\n- 重要：create_workflow/update_workflow 的 nodes/connections 参数底层类型是 string（JSON 数组字符串）。\n  - 本示例封装允许你直接传对象数组，封装层会自动 JSON.stringify。\n\n- 推荐流程：\n  1) 先 get_all_workflows 找到候选 workflow_id。\n  2) 再 get_workflow 获取 nodes/connections 全量结构。\n  3) 如果你要“整体替换” nodes/connections：构造完整的新数组后用 update_workflow 一次性覆盖。\n  4) 如果你只想“增量修改” nodes/connections：优先使用 patch_workflow（node_patches/connection_patches）。\n\n- 节点与连线的 ID：\n  - 节点 id 可省略（服务端会生成），但如果你要创建 connections，强烈建议你在 nodes 里显式写好 id。\n  - connections 里 source/target 可以用：\n    - sourceNodeId/targetNodeId（推荐）\n    - 或 source/target/from/to\n    - 或 sourceIndex/targetIndex（按 nodes 数组下标）\n    - 或 sourceNodeName/targetNodeName（不推荐：同名会歧义）\n\n- 分支连线 condition（核心）：\n  - 通用关键字（适用于任何节点类型）：\n    - condition = \"on_success\" | \"success\" | \"ok\"：源节点成功时触发\n    - condition = \"on_error\" | \"error\" | \"failed\"：源节点失败时触发（失败分支/补救逻辑）\n  - 对 ConditionNode / LogicNode：\n    - condition 为空：默认代表 true 分支（相当于 \"true\"）\n    - condition = \"false\"：false 分支\n    - condition = 其它字符串：当作 Regex 匹配源节点输出字符串\n  - 对非 Condition/Logic 节点：\n    - condition 为空：等价于 on_success（表示“源节点执行成功就走”）\n    - condition = on_error：表示“源节点失败就走”（失败分支）\n\n- 参数引用（ParameterValue）：\n  - 静态值：直接写字符串/数字/布尔值即可（会被当作 StaticValue）\n  - 引用某节点输出：写对象 { nodeId: \"<node-id>\" }\n    - 兼容字段：nodeId / ref / refNodeId\n\n- 触发节点类型（TriggerNode.triggerType）：\n  - manual：手动触发（UI 点“触发工作流”）\n  - schedule：定时触发（由 WorkManager 调度）\n  - tasker：Tasker 事件触发\n  - intent：系统广播 Intent 触发\n  - speech：语音识别事件触发（当识别文本命中正则时触发；可多工作流同时触发）\n\n  触发配置 TriggerNode.triggerConfig（注意：值全是 string）：\n  - schedule：\n    - schedule_type: interval | specific_time | cron\n    - interval_ms: \"900000\"  (15分钟)\n    - specific_time: \"2026-01-04 10:30\"  (格式依实现)\n    - cron_expression: \"15 * * * *\"  (简化 cron)\n    - repeat: \"true\"/\"false\"\n    - enabled: \"true\"/\"false\"\n  - tasker：\n    - command: \"start_meeting\"  (当 Tasker params 中包含该字符串则触发)\n  - intent：\n    - action: \"com.example.MY_ACTION\"  (当收到该 action 的 Intent 则触发)\n  - speech：\n    - pattern: \".*(打开|启动).*(对话|聊天|悬浮窗).*\"  (正则；匹配识别文本)\n    - ignore_case: \"true\"/\"false\"  (可选，默认 true)\n    - require_final: \"true\"/\"false\"  (可选，默认 true；true 表示仅 final 结果触发)\n    - cooldown_ms: \"3000\"  (可选，默认 3000；每个节点的触发冷却)",
#         "en": "Workflow tool usage advice (for the AI):\n\n- Core concepts (align your reasoning with these semantics):\n  - Node types: trigger/execute/condition/logic/extract\n  - Trigger node types: manual/schedule/tasker/intent/speech\n  - Parameter references (ParameterValue): static values vs references to another node output\n  - Connection \"condition\" meaning: on_success/on_error/true/false/regex\n\n- Important: in create_workflow/update_workflow, nodes/connections are strings (JSON array strings) at the API layer.\n  - This example wrapper lets you pass object arrays directly; it will JSON.stringify automatically.\n\n- Recommended flow:\n  1) Call get_all_workflows to find the candidate workflow_id.\n  2) Call get_workflow to retrieve the full nodes/connections structure.\n  3) If you want to replace nodes/connections entirely: build the full new arrays and use update_workflow once to overwrite.\n  4) If you only want incremental changes: prefer patch_workflow (node_patches/connection_patches).\n\n- Node and connection IDs:\n  - Node id can be omitted (server will generate it), but if you need to create connections, strongly recommend explicitly setting node ids in nodes.\n  - In connections, source/target can be provided as:\n    - sourceNodeId/targetNodeId (recommended)\n    - or source/target/from/to\n    - or sourceIndex/targetIndex (index within nodes array)\n    - or sourceNodeName/targetNodeName (not recommended: duplicates are ambiguous)\n\n- Connection condition (core):\n  - Global keywords (works for any node type):\n    - condition = \"on_success\" | \"success\" | \"ok\": trigger when the source node succeeds\n    - condition = \"on_error\" | \"error\" | \"failed\": trigger when the source node fails (error branch / recovery)\n  - For ConditionNode / LogicNode:\n    - empty condition: defaults to true branch (equivalent to \"true\")\n    - condition = \"false\": false branch\n    - other string: treated as a Regex to match the source node output string\n  - For non-Condition/Logic nodes:\n    - empty condition: equivalent to on_success (proceed if the source node succeeded)\n    - condition = on_error: proceed if the source node failed (error branch)\n\n- Parameter references (ParameterValue):\n  - Static value: write a string/number/boolean directly (treated as StaticValue)\n  - Reference another node output: write an object { nodeId: \"<node-id>\" }\n    - compatible fields: nodeId / ref / refNodeId\n\n- Trigger node types (TriggerNode.triggerType):\n  - manual: manual trigger (tap \"trigger workflow\" in UI)\n  - schedule: scheduled trigger (WorkManager)\n  - tasker: triggered by Tasker events\n  - intent: triggered by Android broadcast intents\n  - speech: triggered by speech recognition events (fires when recognized text matches a regex; multiple workflows can match)\n\n  Trigger configuration TriggerNode.triggerConfig (note: all values are strings):\n  - schedule:\n    - schedule_type: interval | specific_time | cron\n    - interval_ms: \"900000\" (15 minutes)\n    - specific_time: \"2026-01-04 10:30\" (format depends on implementation)\n    - cron_expression: \"15 * * * *\" (simplified cron)\n    - repeat: \"true\"/\"false\"\n    - enabled: \"true\"/\"false\"\n  - tasker:\n    - command: \"start_meeting\" (triggered when Tasker params contains this string)\n  - intent:\n    - action: \"com.example.MY_ACTION\" (triggered when receiving this action)\n  - speech:\n    - pattern: \".*(open|start).*(chat|floating).*\" (regex; matches recognized text)\n    - ignore_case: \"true\"/\"false\" (optional, default true)\n    - require_final: \"true\"/\"false\" (optional, default true; if true, only final results trigger)\n    - cooldown_ms: \"3000\" (optional, default 3000; per-node cooldown)"
#       },
#       "parameters": []
#     },
#     {
#       "name": "get_all_workflows",
#       "description": { "zh": "获取所有工作流列表（只含概要信息：ID/名称/启用/统计等）。", "en": "List all workflows (summary only: id/name/enabled/stats, etc.)." },
#       "parameters": []
#     },
#     {
#       "name": "get_workflow",
#       "description": { "zh": "获取指定工作流完整详情（nodes + connections）。", "en": "Get full details of a specific workflow (nodes + connections)." },
#       "parameters": [
#         { "name": "workflow_id", "description": { "zh": "工作流 ID", "en": "Workflow ID" }, "type": "string", "required": true }
#       ]
#     },
#     {
#       "name": "create_workflow",
#       "description": { "zh": "创建工作流。\n\n参数说明：\n- nodes: JSON 数组字符串（推荐传对象数组，让封装自动 stringify）\n- connections: JSON 数组字符串（同上）\n\n节点类型（node.type）：\n- trigger / execute / condition / logic / extract\n\nExecute 节点：\n- actionType: 工具名（如 \"visit_web\" / \"list_files\" / \"get_system_setting\" ...）\n- actionConfig: 工具参数对象，支持 ParameterValue（静态值/节点引用）\n\nCondition 节点：\n- left/right: ParameterValue\n- operator: EQ/NE/GT/GTE/LT/LTE/CONTAINS/NOT_CONTAINS/IN/NOT_IN\n\nLogic 节点：\n- operator: AND/OR\n\nExtract（运算）节点：\n- 说明：node.type 仍然是 \"extract\"（兼容旧数据），但语义更接近“运算器/计算节点”。\n- source: ParameterValue（部分模式不需要，例如 RANDOM_INT）\n- mode:\n  - REGEX：正则提取\n    - expression: 正则表达式\n    - group/defaultValue 可选\n  - JSON：JSON 路径提取\n    - expression: JSON 路径（简化实现）\n    - defaultValue 可选\n  - SUB：字符串截取\n    - startIndex: 起始下标\n    - length: 长度（-1 表示到结尾）\n    - defaultValue 可选\n  - CONCAT：字符串拼接\n    - others: ParameterValue[]（被拼接项列表）\n  - RANDOM_INT：随机整数\n    - randomMin/randomMax\n    - useFixed: 是否使用固定值（可选）\n    - fixedValue: 固定整数（可选，仅 useFixed=true 时生效；输出仍为数字字符串）\n  - RANDOM_STRING：随机字符串\n    - randomStringLength: 长度\n    - randomStringCharset: 字符集（可选，默认字母数字）\n    - useFixed: 是否使用固定值（可选）\n    - fixedValue: 固定字符串（可选，仅 useFixed=true 时生效）", "en": "Create a workflow.\n\nParameter notes:\n- nodes: JSON array string (recommended: pass object arrays and let the wrapper stringify)\n- connections: JSON array string (same as above)\n\nNode types (node.type):\n- trigger / execute / condition / logic / extract\n\nExecute node:\n- actionType: tool name (e.g. \"visit_web\" / \"list_files\" / \"get_system_setting\" ...)\n- actionConfig: tool parameter object, supports ParameterValue (static value / node reference)\n\nCondition node:\n- left/right: ParameterValue\n- operator: EQ/NE/GT/GTE/LT/LTE/CONTAINS/NOT_CONTAINS/IN/NOT_IN\n\nLogic node:\n- operator: AND/OR\n\nExtract (operator) node:\n- Note: node.type is still \"extract\" for backward compatibility, but it behaves like an \"operator\" node.\n- source: ParameterValue (not required for some modes like RANDOM_INT)\n- mode:\n  - REGEX: regex extraction\n    - expression: regex pattern\n    - group/defaultValue are optional\n  - JSON: JSON path extraction\n    - expression: JSON path (simplified)\n    - defaultValue optional\n  - SUB: substring\n    - startIndex\n    - length (-1 means to end)\n    - defaultValue optional\n  - CONCAT: string concatenation\n    - others: ParameterValue[]\n  - RANDOM_INT: random integer\n    - randomMin/randomMax\n    - useFixed: whether to use a fixed value (optional)\n    - fixedValue: fixed integer (optional, only effective when useFixed=true; output is still a numeric string)\n  - RANDOM_STRING: random string\n    - randomStringLength\n    - randomStringCharset (optional, default: alphanumeric)\n    - useFixed: whether to use a fixed value (optional)\n    - fixedValue: fixed string (optional, only effective when useFixed=true)" },
#       "parameters": [
#         { "name": "name", "description": { "zh": "工作流名称", "en": "Workflow name" }, "type": "string", "required": true },
#         { "name": "description", "description": { "zh": "工作流描述（可选）", "en": "Workflow description (optional)" }, "type": "string", "required": false },
#         { "name": "nodes", "description": { "zh": "可选，节点 JSON 数组字符串（或直接传节点数组，由封装 stringify）", "en": "Optional. Nodes JSON array string (or pass an array and the wrapper will stringify)." }, "type": "string", "required": false },
#         { "name": "connections", "description": { "zh": "可选，连线 JSON 数组字符串（或直接传连线数组，由封装 stringify）", "en": "Optional. Connections JSON array string (or pass an array and the wrapper will stringify)." }, "type": "string", "required": false },
#         { "name": "enabled", "description": { "zh": "可选，是否启用（默认 true）", "en": "Optional. Whether to enable (default: true)." }, "type": "boolean", "required": false }
#       ]
#     },
#     {
#       "name": "update_workflow",
#       "description": { "zh": "更新工作流。\n\n注意：update_workflow 的 nodes / connections 是“整体覆盖”。\n- 若你只改其中一部分，推荐使用 patch_workflow。\n- 或者：get_workflow 取回旧结构 -> 本地构造新数组（保留未改部分）-> update_workflow 一次性传回。", "en": "Update a workflow.\n\nNote: nodes/connections in update_workflow are full overwrites.\n- If you only change part of them, prefer patch_workflow.\n- Or: call get_workflow to fetch the old structure -> build new arrays locally (keeping unchanged parts) -> call update_workflow once." },
#       "parameters": [
#         { "name": "workflow_id", "description": { "zh": "工作流 ID", "en": "Workflow ID" }, "type": "string", "required": true },
#         { "name": "name", "description": { "zh": "可选，新名称", "en": "Optional. New name." }, "type": "string", "required": false },
#         { "name": "description", "description": { "zh": "可选，新描述", "en": "Optional. New description." }, "type": "string", "required": false },
#         { "name": "nodes", "description": { "zh": "可选，节点 JSON 数组字符串（整体覆盖）", "en": "Optional. Nodes JSON array string (full overwrite)." }, "type": "string", "required": false },
#         { "name": "connections", "description": { "zh": "可选，连线 JSON 数组字符串（整体覆盖）", "en": "Optional. Connections JSON array string (full overwrite)." }, "type": "string", "required": false },
#         { "name": "enabled", "description": { "zh": "可选，是否启用", "en": "Optional. Whether to enable." }, "type": "boolean", "required": false }
#       ]
#     },
#     {
#       "name": "patch_workflow",
#       "description": { "zh": "差异更新工作流（增量 patch）。\n\n使用 node_patches / connection_patches 传入 JSON 数组字符串：\n- op: add | update | remove\n- id: 可选\n- node / connection: 对象\n\n说明：\n- add：必须提供 node/connection\n- update：必须提供 id 或 node.id/connection.id\n- remove：必须提供 id", "en": "Patch a workflow (incremental update).\n\nUse node_patches / connection_patches as JSON array strings:\n- op: add | update | remove\n- id: optional\n- node / connection: object\n\nNotes:\n- add: must provide node/connection\n- update: must provide id OR node.id/connection.id\n- remove: must provide id" },
#       "parameters": [
#         { "name": "workflow_id", "description": { "zh": "工作流 ID", "en": "Workflow ID" }, "type": "string", "required": true },
#         { "name": "name", "description": { "zh": "可选，新名称", "en": "Optional. New name." }, "type": "string", "required": false },
#         { "name": "description", "description": { "zh": "可选，新描述", "en": "Optional. New description." }, "type": "string", "required": false },
#         { "name": "enabled", "description": { "zh": "可选，是否启用", "en": "Optional. Whether to enable." }, "type": "boolean", "required": false },
#         { "name": "node_patches", "description": { "zh": "可选，节点 patch JSON 数组字符串", "en": "Optional. Node patch JSON array string." }, "type": "string", "required": false },
#         { "name": "connection_patches", "description": { "zh": "可选，连线 patch JSON 数组字符串", "en": "Optional. Connection patch JSON array string." }, "type": "string", "required": false }
#       ]
#     },
#     {
#       "name": "enable_workflow",
#       "description": { "zh": "启用指定工作流。", "en": "Enable a specific workflow." },
#       "parameters": [
#         { "name": "workflow_id", "description": { "zh": "工作流 ID", "en": "Workflow ID" }, "type": "string", "required": true }
#       ]
#     },
#     {
#       "name": "disable_workflow",
#       "description": { "zh": "禁用指定工作流。", "en": "Disable a specific workflow." },
#       "parameters": [
#         { "name": "workflow_id", "description": { "zh": "工作流 ID", "en": "Workflow ID" }, "type": "string", "required": true }
#       ]
#     },
#     {
#       "name": "delete_workflow",
#       "description": { "zh": "删除指定工作流。", "en": "Delete a specific workflow." },
#       "parameters": [
#         { "name": "workflow_id", "description": { "zh": "工作流 ID", "en": "Workflow ID" }, "type": "string", "required": true }
#       ]
#     },
#     {
#       "name": "trigger_workflow",
#       "description": { "zh": "触发指定工作流执行（相当于 UI 手动触发）。", "en": "Trigger execution of a workflow (equivalent to manual trigger in UI)." },
#       "parameters": [
#         { "name": "workflow_id", "description": { "zh": "工作流 ID", "en": "Workflow ID" }, "type": "string", "required": true }
#       ]
#     }
#   ]
# }


async def usage_advice(params):
    return {
        "success": True,
        "message": "请阅读 workflow 工具 METADATA 中的 usage_advice 说明：包含节点/连线 schema、分支 condition 规则、触发类型与配置示例。建议在脚本里直接使用 Tools.Workflow.getAll/get/create/update/patch/setEnabled/enable/disable/delete/trigger 等封装方法。"
    }


# 获取所有工作流
async def get_all_workflows(params=None):
    if params is None:
        params = {}
    data = await Tools.Workflow.getAll()
    return {
        "success": True,
        "message": "成功获取工作流列表",
        "data": data
    }


# 创建新工作流
async def create_workflow(params):
    data = await Tools.Workflow.create(
        params.get("name"),
        params.get("description") or "",
        params.get("nodes") if params.get("nodes") is not None else None,
        params.get("connections") if params.get("connections") is not None else None,
        params.get("enabled")
    )
    return {
        "success": True,
        "message": "成功创建工作流",
        "data": data
    }


# 获取工作流详情
async def get_workflow(params):
    data = await Tools.Workflow.get(params["workflow_id"])
    return {
        "success": True,
        "message": "成功获取工作流详情",
        "data": data
    }


# 更新工作流
async def update_workflow(params):
    workflow_id = params.get("workflow_id")
    updates = {k: v for k, v in params.items() if k != "workflow_id"}
    data = await Tools.Workflow.update(workflow_id, updates)
    return {
        "success": True,
        "message": "成功更新工作流",
        "data": data
    }


# 差异更新工作流（增量 patch）
async def patch_workflow(params):
    workflow_id = params.get("workflow_id")
    patch = {k: v for k, v in params.items() if k != "workflow_id"}
    data = await Tools.Workflow.patch(workflow_id, patch)
    return {
        "success": True,
        "message": "成功差异更新工作流",
        "data": data
    }


# 启用工作流
async def enable_workflow(params):
    data = await Tools.Workflow.enable(params["workflow_id"])
    return {
        "success": True,
        "message": "成功启用工作流",
        "data": data
    }


# 禁用工作流
async def disable_workflow(params):
    data = await Tools.Workflow.disable(params["workflow_id"])
    return {
        "success": True,
        "message": "成功禁用工作流",
        "data": data
    }


# 删除工作流
async def delete_workflow(params):
    data = await getattr(Tools.Workflow, "delete")(params["workflow_id"])
    return {
        "success": True,
        "message": "成功删除工作流",
        "data": data
    }


# 触发工作流执行
async def trigger_workflow(params):
    data = await Tools.Workflow.trigger(params["workflow_id"])
    return {
        "success": True,
        "message": "成功触发工作流",
        "data": data
    }


# 包装工具执行，处理错误和结果
async def wrapToolExecution(func, params):
    try:
        result = await func(params)
        complete(result)
    except Exception as error:
        console.error(f"Tool {func.__name__} failed unexpectedly", error)
        complete({"success": False, "message": str(getattr(error, "message", None) or error)})


async def _exported_usage_advice(params=None):
    if params is None:
        params = {}
    await wrapToolExecution(usage_advice, params)


async def _exported_get_all_workflows(params=None):
    if params is None:
        params = {}
    await wrapToolExecution(get_all_workflows, {})


async def _exported_create_workflow(params):
    await wrapToolExecution(create_workflow, params)


async def _exported_get_workflow(params):
    await wrapToolExecution(get_workflow, params)


async def _exported_update_workflow(params):
    await wrapToolExecution(update_workflow, params)


async def _exported_patch_workflow(params):
    await wrapToolExecution(patch_workflow, params)


async def _exported_enable_workflow(params):
    await wrapToolExecution(enable_workflow, params)


async def _exported_disable_workflow(params):
    await wrapToolExecution(disable_workflow, params)


async def _exported_delete_workflow(params):
    await wrapToolExecution(delete_workflow, params)


async def _exported_trigger_workflow(params):
    await wrapToolExecution(trigger_workflow, params)


exports.usage_advice = _exported_usage_advice
exports.get_all_workflows = _exported_get_all_workflows
exports.create_workflow = _exported_create_workflow
exports.get_workflow = _exported_get_workflow
exports.update_workflow = _exported_update_workflow
exports.patch_workflow = _exported_patch_workflow
exports.enable_workflow = _exported_enable_workflow
exports.disable_workflow = _exported_disable_workflow
exports.delete_workflow = _exported_delete_workflow
exports.trigger_workflow = _exported_trigger_workflow
