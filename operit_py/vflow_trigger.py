# METADATA
# {
#   name: "vflow_trigger"
#   display_name: {
#     zh: "VFlow 触发器"
#     en: "VFlow Trigger"
#   }
#   description: {
#     zh: "触发vflow app的工作流。"
#     en: "Trigger VFlow app workflows."
#   }
#   enabledByDefault: false
#   category: "Workflow"
#   tools: [
#     {
#       name: "trigger_vflow_workflow"
#       description: {
#         zh: "根据 workflow_id 触发 VFlow 工作流（需安装 com.chaomixian.vflow）。"
#         en: "Trigger a VFlow workflow by workflow_id (requires com.chaomixian.vflow installed)."
#       }
#       parameters: [
#         { name: "workflow_id", description: { zh: "工作流 ID", en: "Workflow ID" }, type: "string", required: true }
#       ]
#     }
#   ]
# }

DEFAULT_ACTION = "com.chaomixian.vflow.EXECUTE_WORKFLOW_SHORTCUT"
DEFAULT_COMPONENT = "com.chaomixian.vflow/.ui.common.ShortcutExecutorActivity"


async def trigger_vflow_workflow(params):
    if not params or not params.get("workflow_id"):
        return {"success": False, "message": "workflow_id 不能为空"}

    result = await Tools.System.intent({
        "type": "activity",
        "action": DEFAULT_ACTION,
        "component": DEFAULT_COMPONENT,
        "extras": {
            "workflow_id": params["workflow_id"]
        }
    })

    return {
        "success": True,
        "message": "已触发 VFlow 工作流",
        "data": result
    }


async def wrapToolExecution(func, params):
    try:
        result = await func(params)
        complete(result)
    except Exception as error:
        console.error(f"Tool {func.__name__} failed unexpectedly", error)
        msg = str(getattr(error, "message", error))
        complete({"success": False, "message": msg})


async def trigger_vflow_workflow_wrapper(params):
    await wrapToolExecution(trigger_vflow_workflow, params)


exports.trigger_vflow_workflow = trigger_vflow_workflow_wrapper
