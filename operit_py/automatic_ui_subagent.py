# METADATA
# {
#     "name": "Automatic_ui_subagent",
#     "display_name": {"zh": "自动化AutoGLM子代理", "en": "Automated AutoGLM Sub-agent"},
#     "description": {"zh": "兼容AutoGLM，提供基于独立UI控制器模型（例如 autoglm-phone-9b）的高层UI自动化子代理工具，用于根据自然语言意图自动规划并执行点击/输入/滑动等一系列界面操作。当用户提出需要帮忙完成某个界面操作任务（例如打开应用、搜索内容、在多个页面之间完成一套步骤）时，可以调用本包由子代理自动规划和执行具体步骤。", "en": "Compatible with AutoGLM. Provides a high-level UI automation sub-agent based on an independent UI-controller model (e.g. autoglm-phone-9b). It can plan and execute a sequence of UI actions (tap/type/swipe) from natural-language intent. When the user asks you to complete a UI task (e.g. open an app, search content, or finish a multi-step workflow across pages), you can call this package and let the sub-agent plan and execute the steps."},
#     "category": "Automatic",
#     "tools": [],
#     "states": [
#         {"id": "virtual_display", "condition": "ui.virtual_display", "inheritTools": True, "tools": [
#             {"name": "usage_advice", "description": {"zh": "UI子代理使用建议", "en": "UI sub-agent usage advice."}, "advice": True, "parameters": []},
#             {"name": "run_subagent_main", "description": {"zh": "在主屏幕运行 UI 子代理（强制主屏）。", "en": "Run the UI sub-agent on the main screen (forced main screen)."}, "parameters": [
#                 {"name": "intent", "description": {"zh": "任务意图描述", "en": "Task intent description"}, "type": "string", "required": True},
#                 {"name": "target_app", "description": {"zh": "目标应用名/包名（可选）", "en": "Target app name/package (optional)"}, "type": "string", "required": False},
#                 {"name": "max_steps", "description": {"zh": "最大执行步数（默认20）", "en": "Maximum execution steps (default: 20)"}, "type": "number", "required": False}
#             ]},
#             {"name": "run_subagent_virtual", "description": {"zh": "在虚拟屏幕会话运行 UI 子代理（强制虚拟屏）。", "en": "Run the UI sub-agent on a virtual-display session (forced virtual screen)."}, "parameters": [
#                 {"name": "intent", "description": {"zh": "任务意图描述", "en": "Task intent description"}, "type": "string", "required": True},
#                 {"name": "target_app", "description": {"zh": "目标应用名/包名（可选）", "en": "Target app name/package (optional)"}, "type": "string", "required": False},
#                 {"name": "max_steps", "description": {"zh": "最大执行步数（默认20）", "en": "Maximum execution steps (default: 20)"}, "type": "number", "required": False},
#                 {"name": "agent_id", "description": {"zh": "虚拟屏会话 agent_id（必须为非 'default'；可传入复用，或留空复用上次返回的 data.agentId）。", "en": "Virtual-screen session agent_id (must be non-'default'; pass to reuse, or omit to reuse returned data.agentId)."}, "type": "string", "required": False}
#             ]},
#             {"name": "run_subagent_parallel_virtual", "description": {"zh": "并行运行 1-4 个 UI 子代理（强制虚拟屏）。", "en": "Run 1-4 UI sub-agents in parallel (forced virtual screen)."}, "parameters": []},
#             {"name": "close_all_virtual_displays", "description": {"zh": "关闭所有虚拟屏幕。", "en": "Close all virtual displays."}, "parameters": []}
#         ]},
#         {"id": "main_screen", "condition": "!ui.virtual_display", "inheritTools": True, "tools": [
#             {"name": "usage_advice", "description": {"zh": "UI子代理使用建议（主屏模式）", "en": "UI sub-agent usage advice (main-screen mode)."}, "advice": True, "parameters": []},
#             {"name": "run_subagent_main", "description": {"zh": "在主屏幕运行 UI 子代理（强制主屏）。", "en": "Run the UI sub-agent on the main screen (forced main screen)."}, "parameters": [
#                 {"name": "intent", "description": {"zh": "任务意图描述", "en": "Task intent description"}, "type": "string", "required": True},
#                 {"name": "target_app", "description": {"zh": "目标应用名/包名（可选）", "en": "Target app name/package (optional)"}, "type": "string", "required": False},
#                 {"name": "max_steps", "description": {"zh": "最大执行步数（默认20）", "en": "Maximum execution steps (default: 20)"}, "type": "number", "required": False}
#             ]}
#         ]}
#     ]
# }

import json
import re
import asyncio
from urllib.parse import quote, unquote

Error = Exception

CACHE_KEY = '__operit_ui_subagent_cached_agent_id'
_global_cache = {}


def getCachedAgentId():
    try:
        return _global_cache.get(CACHE_KEY)
    except Exception:
        return None


def setCachedAgentId(value):
    try:
        if value is None or len(str(value)) == 0:
            _global_cache.pop(CACHE_KEY, None)
        else:
            _global_cache[CACHE_KEY] = str(value)
    except Exception:
        pass


def getPackageState():
    try:
        return getState()
    except Exception:
        return None


def errorMessage(e):
    if isinstance(e, Exception):
        return str(e)
    return str(e)


def getStringArrayFromUnknown(v):
    if not isinstance(v, list):
        return []
    return [str(x or '').strip() for x in v if str(x or '').strip()]


def parseInstalledAppEntry(raw):
    s = str(raw or '').strip()
    if not s:
        return {"name": '', "raw": ''}
    open_idx = s.rfind('(')
    close_idx = s.rfind(')')
    if open_idx >= 0 and close_idx == len(s) - 1 and open_idx < close_idx:
        name = s[:open_idx].strip()
        pkg = s[open_idx + 1:close_idx].strip()
        if name and pkg:
            return {"name": name, "pkg": pkg, "raw": s}
    return {"name": s, "raw": s}


async def getInstalledApps():
    appList = await Tools.System.listApps(False)
    rawItems = getStringArrayFromUnknown(getattr(appList, "packages", None) if appList else None)
    entries = [e for e in [parseInstalledAppEntry(r) for r in rawItems] if e["name"]]
    nameMap = {}
    for e in entries:
        nameMap[e["name"].lower()] = e["name"]
    names = sorted(nameMap.values())
    return {"entries": entries, "names": names}


def matchTarget(targetApp, installed):
    t = str(targetApp or '').strip()
    if not t:
        return None
    tl = t.lower()
    m = None
    for a in installed:
        if (a.get("pkg") or '').lower() == tl:
            m = a
            break
    if not m:
        for a in installed:
            if a["name"].lower() == tl:
                m = a
                break
    if not m:
        for a in installed:
            if a["raw"].lower() == tl:
                m = a
                break
    if not m:
        return None
    run = m.get("pkg") or m["name"]
    return {"run": run, "key": run.lower()}


async def usage_advice(params):
    state = getPackageState()
    isMainScreen = str(state).lower() == 'main_screen'
    return {
        "success": True,
        "message": 'UI子代理使用建议',
        "data": {
            "advice": (
                "主屏模式：不支持 agent_id，会话复用策略不适用；不支持并行工具，一次只做一个明确子目标（必要时拆多次）。\n"
                "屏幕选择规则：不传 agent_id 或传 'default' => 主屏幕；传入且不为 'default' => 虚拟屏（主屏模式下会忽略并强制主屏）。\n"
                "启动前置（非常重要）：当你第一次需要操作某个应用时，intent 开头必须写'启动XXX应用 ...'，让子代理直接执行 Launch，而不是在桌面自己找。\n"
                "对话无状态：每次调用是新对话，intent 写清 已完成/下一步/关键信息。\n"
                "自包含：别用'这五个/继续/同上'；多对象要么列清单+当前目标，要么先让子代理在当前页识别并复述清单。\n"
                "失败与完成：半成功不算完成；未达成目标继续推进，连续 2-3 次失败再停并说明原因。"
            ) if isMainScreen else (
                "虚拟屏模式：尽量复用 agent_id（沿用 data.agentId）保持同一虚拟屏/同一应用上下文。\n"
                "屏幕选择规则：不传 agent_id 或传 'default' => 主屏幕；传入且不为 'default' => 对应虚拟屏会话（虚拟屏必须可用，否则失败）。为避免误操作主屏，虚拟屏模式下首次调用建议显式传入 agent_id。\n"
                "启动前置（非常重要）：当你第一次使用某个 agent_id（新建或更换 agent_id）时，intent 开头必须写'启动XXX应用 ...'，让子代理直接执行 Launch，而不是在桌面自己找。\n"
                "对话无状态：每次调用是新对话，intent 写清 已完成/下一步/关键信息。\n"
                "自包含：别用'这五个/继续/同上'；多对象要么列清单+当前目标，要么先让子代理在当前页识别并复述清单。\n"
                "对齐+并行：先清单后逐项(A→B→C)；独立子任务/同一对象多入口优先并行(run_subagent_parallel_virtual)，只重试失败分支。\n"
                "并行资源约束：并行分支数必须受可用独立App/虚拟屏数量限制；同一个App/包名不能同时出现在两个虚拟屏/两个agent_id 中并行操作（会坏）。并行调用必须传 target_app_i=目标应用名，且各分支 target_app_i 不能重复；第2次/第N次并行不得擅自提高并行度，保持上限，只重试失败分支或改串行。\n"
                "失败与完成：半成功不算完成；未达成目标继续推进，连续 2-3 次失败再停并说明原因。"
            ),
        },
    }


async def run_subagent_internal(params):
    intent = params.get("intent")
    max_steps = params.get("max_steps")
    agent_id = params.get("agent_id")
    target_app = params.get("target_app")

    state = getPackageState()
    isMainScreen = str(state).lower() == 'main_screen'

    explicitAgentId = '' if agent_id is None else str(agent_id).strip()
    cachedAgentId = getCachedAgentId()

    if isMainScreen:
        agentIdToUse = 'default'
    else:
        agentIdToUse = explicitAgentId if len(explicitAgentId) > 0 else cachedAgentId
        if agentIdToUse is None or len(str(agentIdToUse).strip()) == 0:
            return {
                "success": False,
                "message": "虚拟屏模式下未指定 agent_id：为避免误操作主屏幕，请显式传入 agent_id（且不为 'default'）来使用虚拟屏会话；或先完成一次成功调用并复用返回的 data.agentId。",
            }

    targetAppForRun = target_app
    if target_app and len(str(target_app).strip()) > 0:
        installed = await getInstalledApps()
        matched = matchTarget(target_app, installed["entries"])
        if not matched:
            return {
                "success": False,
                "message": f"目标应用不存在：当前给定的 target_app='{str(target_app).strip()}' 未在已安装应用中找到。已返回已安装应用名列表。",
                "data": {
                    "target_app": str(target_app).strip(),
                    "installed_apps": installed["names"],
                },
            }
        targetAppForRun = matched["run"]

    result = await Tools.UI.runSubAgent(intent, max_steps, agentIdToUse, targetAppForRun)
    agentId = getattr(result, "agentId", None) if result else None
    if agentId and len(str(agentId).strip()) > 0 and str(agentId).strip().lower() != 'default':
        setCachedAgentId(agentId)
    return {
        "success": True,
        "message": 'UI子代理执行完成',
        "data": result,
    }


async def run_subagent_main(params):
    intent = params.get("intent")
    max_steps = params.get("max_steps")
    target_app = params.get("target_app")
    return await run_subagent_internal({"intent": intent, "max_steps": max_steps, "target_app": target_app, "agent_id": 'default'})


async def run_subagent_virtual(params):
    intent = params.get("intent")
    max_steps = params.get("max_steps")
    agent_id = params.get("agent_id")
    target_app = params.get("target_app")

    explicitAgentId = '' if agent_id is None else str(agent_id).strip()
    cachedAgentId = getCachedAgentId()
    agentIdToUse = explicitAgentId if len(explicitAgentId) > 0 else cachedAgentId

    if agentIdToUse is None or len(str(agentIdToUse).strip()) == 0 or str(agentIdToUse).strip().lower() == 'default':
        return {
            "success": False,
            "message": "虚拟屏模式必须使用非 'default' 的 agent_id：请显式传入 agent_id（非 'default'），或先完成一次成功调用并复用返回的 data.agentId。",
        }

    return await run_subagent_internal({"intent": intent, "max_steps": max_steps, "target_app": target_app, "agent_id": str(agentIdToUse)})


async def run_subagent_parallel_internal(params):
    state = getPackageState()
    isMainScreen = str(state).lower() == 'main_screen'
    if isMainScreen:
        return {
            "success": False,
            "message": "主屏模式不支持 run_subagent_parallel_virtual 并行调用。请改用 run_subagent_main 串行执行。",
        }

    slots = [1, 2, 3, 4]

    activeSlots = []
    for i in slots:
        intent = params.get(f"intent_{i}")
        if not intent or len(str(intent).strip()) == 0:
            continue
        targetApp = params.get(f"target_app_{i}")
        activeSlots.append({"index": i, "targetApp": targetApp})

    missingTargets = [s["index"] for s in activeSlots if s["targetApp"] is None or len(str(s["targetApp"]).strip()) == 0]
    if len(missingTargets) > 0:
        _missing_str = ', '.join(str(x) for x in missingTargets)
        return {
            "success": False,
            "message": f"并行参数错误：intent_{_missing_str} 缺少 target_app_{_missing_str}（目标应用名）。并行时必须为每个启用分支传入目标应用名，用于检测'同一应用不能出现在两个虚拟屏/agent_id'的冲突。",
        }

    missingAgentIds = []
    for s in activeSlots:
        v = params.get(f"agent_id_{s['index']}")
        id_ = '' if v is None else str(v).strip()
        if len(id_) == 0 or id_.lower() == 'default':
            missingAgentIds.append(s["index"])
    if len(missingAgentIds) > 0:
        return {
            "success": False,
            "message": f"并行参数错误：虚拟屏并行模式下，每个启用分支必须显式传入非 'default' 的 agent_id。缺少/非法 agent_id 的分支：{', '.join(f'#{i}' for i in missingAgentIds)}。",
        }

    installed = await getInstalledApps()
    resolvedBySlot = {}
    missingApps = []

    for s in activeSlots:
        t = str(s["targetApp"] or '').strip()
        m = matchTarget(t, installed["entries"])
        if not m:
            missingApps.append(t)
        else:
            resolvedBySlot[s["index"]] = m

    if len(missingApps) > 0:
        _apps_str = ', '.join(f"'{str(s).strip()}'" for s in missingApps)
        return {
            "success": False,
            "message": f"目标应用不存在：当前给定的 target_app 列表中包含未安装/不存在的应用：{_apps_str}。已返回已安装应用名列表。",
            "data": {
                "missing_apps": missingApps,
                "installed_apps": installed["names"],
            },
        }

    used = {}
    for s in activeSlots:
        key = (resolvedBySlot.get(s["index"]) or {}).get("key") or str(s["targetApp"]).strip().lower()
        prev = used.get(key)
        if prev is not None:
            return {
                "success": False,
                "message": f"并行参数错误：target_app_{prev} 与 target_app_{s['index']} 重复（同一目标应用='{str(s['targetApp']).strip()}'）。同一应用不能同时在两个虚拟屏/agent_id 中并行操作。",
            }
        used[key] = s["index"]

    async def runOne(i):
        intent = params.get(f"intent_{i}")
        if not intent or len(str(intent).strip()) == 0:
            return None
        maxSteps = params.get(f"max_steps_{i}")
        agentId = params.get(f"agent_id_{i}")
        targetApp = (resolvedBySlot.get(i) or {}).get("run") or params.get(f"target_app_{i}")
        try:
            result = await Tools.UI.runSubAgent(
                str(intent),
                maxSteps,
                None if agentId is None or len(str(agentId).strip()) == 0 else str(agentId).strip(),
                targetApp,
            )
            return {"index": i, "success": True, "result": result}
        except Exception as e:
            return {"index": i, "success": False, "error": errorMessage(e)}

    tasks = [runOne(i) for i in slots]
    raw_results = await asyncio.gather(*tasks)
    results = [r for r in raw_results if r is not None]
    okCount = len([r for r in results if r["success"]])
    return {
        "success": True,
        "message": f"并行UI子代理执行完成：成功 {okCount} 个 / 共 {len(results)} 个",
        "data": {"results": results},
    }


async def run_subagent_parallel_virtual(params):
    return await run_subagent_parallel_internal(params)


async def close_all_virtual_displays(params):
    result = await toolCall('close_all_virtual_displays', {})
    ok = getattr(result, "success", None) if result else None
    ok = ok is not False
    error = getattr(result, "error", None) if result else None
    return {
        "success": ok,
        "message": '已关闭所有虚拟屏幕。' if ok else f"关闭虚拟屏幕失败：{str(error) if error else 'unknown error'}",
        "data": result,
    }


async def wrapToolExecution(func, params):
    try:
        result = await func(params)
        complete(result)
    except Exception as error:
        console.error(f"Tool {func.__name__} failed unexpectedly", error)
        complete({
            "success": False,
            "message": f"工具执行时发生意外错误: {errorMessage(error)}",
        })


async def _usage_advice_wrapper(params):
    await wrapToolExecution(usage_advice, params)


async def _run_subagent_main_wrapper(params):
    await wrapToolExecution(run_subagent_main, params)


async def _run_subagent_virtual_wrapper(params):
    await wrapToolExecution(run_subagent_virtual, params)


async def _close_all_virtual_displays_wrapper(params):
    await wrapToolExecution(close_all_virtual_displays, params)


async def _run_subagent_parallel_virtual_wrapper(params):
    await wrapToolExecution(run_subagent_parallel_virtual, params)


exports.usage_advice = _usage_advice_wrapper
exports.run_subagent_main = _run_subagent_main_wrapper
exports.run_subagent_virtual = _run_subagent_virtual_wrapper
exports.close_all_virtual_displays = _close_all_virtual_displays_wrapper
exports.run_subagent_parallel_virtual = _run_subagent_parallel_virtual_wrapper
