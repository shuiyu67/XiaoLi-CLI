# METADATA
# {
#   "name": "operit_editor",
#   "display_name": { "zh": "Operit平台编辑器", "en": "Operit Platform Editor" },
#   "description": { "zh": "Operit 平台配置直改工具包：提供一组可直接读取与修改 Operit 平台设置的工具，覆盖 MCP、Skill、Sandbox Package、功能模型绑定、模型参数、上下文总结与 TTS/STT 语音服务配置。", "en": "Direct Operit platform configuration toolkit: a collection of tools for reading and directly modifying Operit platform settings, covering MCP, Skill, Sandbox Package, function-model bindings, model parameters, context-summary settings, and TTS/STT speech-service configuration." },
#   "enabledByDefault": true,
#   "category": "Chat",
#   "tools": [
#     { "name": "operit_editor", "description": "配置排查手册", "parameters": [], "advice": true },
#     { "name": "how_make_skill", "description": "返回如何制作 skill 的双语说明", "parameters": [] },
#     { "name": "list_sandbox_packages", "description": "获取沙盒包列表（内置+外部）及当前启用状态", "parameters": [] },
#     { "name": "set_sandbox_package_enabled", "description": "设置沙盒包开关状态", "parameters": [ { "name": "package_name", "type": "string", "required": true }, { "name": "enabled", "type": "boolean", "required": true } ] },
#     { "name": "debug_install_js_package", "description": "将 Android 侧的普通 .js 沙盒包直接烧录到外部 packages 目录", "parameters": [ { "name": "source_path", "type": "string", "required": true }, { "name": "enable_after_install", "type": "boolean", "required": false }, { "name": "activate_after_install", "type": "boolean", "required": false } ] },
#     { "name": "debug_install_toolpkg", "description": "根据 Android 侧的 ToolPkg 目录、manifest 或现成 .toolpkg，直接打包/烧录到外部 packages 目录", "parameters": [ { "name": "source_path", "type": "string", "required": true }, { "name": "reset_subpackage_states", "type": "boolean", "required": false }, { "name": "activate_subpackages", "type": "string", "required": false }, { "name": "wait_ms", "type": "integer", "required": false } ] },
#     { "name": "debug_run_sandbox_script", "description": "直接运行一段 sandbox script", "parameters": [ { "name": "source_path", "type": "string", "required": false }, { "name": "source_code", "type": "string", "required": false }, { "name": "params_json", "type": "string", "required": false }, { "name": "env_file_path", "type": "string", "required": false }, { "name": "script_label", "type": "string", "required": false }, { "name": "wait_ms", "type": "integer", "required": false } ] },
#     { "name": "read_environment_variable", "description": "读取指定环境变量当前值", "parameters": [ { "name": "key", "type": "string", "required": true } ] },
#     { "name": "write_environment_variable", "description": "写入指定环境变量", "parameters": [ { "name": "key", "type": "string", "required": true }, { "name": "value", "type": "string", "required": false } ] },
#     { "name": "restart_mcp_with_logs", "description": "触发一次 MCP 重启流程，返回每个插件的启动日志与状态摘要", "parameters": [ { "name": "timeout_ms", "type": "integer", "required": false } ] },
#     { "name": "get_speech_services_config", "description": "获取当前 TTS/STT 语音服务配置快照", "parameters": [] },
#     { "name": "set_speech_services_config", "description": "按字段更新 TTS/STT 语音服务配置", "parameters": [] },
#     { "name": "test_tts_playback", "description": "按当前 TTS 配置播放一次测试文本", "parameters": [ { "name": "text", "type": "string", "required": true }, { "name": "interrupt", "type": "boolean", "required": false }, { "name": "speech_rate", "type": "number", "required": false }, { "name": "pitch", "type": "number", "required": false } ] },
#     { "name": "list_model_configs", "description": "列出全部模型配置及功能模型绑定关系", "parameters": [] },
#     { "name": "create_model_config", "description": "新增模型配置", "parameters": [] },
#     { "name": "update_model_config", "description": "按 config_id 修改模型配置", "parameters": [ { "name": "config_id", "type": "string", "required": true } ] },
#     { "name": "delete_model_config", "description": "删除模型配置", "parameters": [ { "name": "config_id", "type": "string", "required": true } ] },
#     { "name": "list_function_model_configs", "description": "列出功能 -> 配置绑定关系", "parameters": [] },
#     { "name": "get_function_model_config", "description": "查看某个功能当前绑定的单个配置详情", "parameters": [ { "name": "function_type", "type": "string", "required": true } ] },
#     { "name": "get_context_summary_config", "description": "查看上下文总结参数", "parameters": [ { "name": "function_type", "type": "string", "required": false } ] },
#     { "name": "set_context_summary_config", "description": "设置上下文总结参数", "parameters": [ { "name": "function_type", "type": "string", "required": false } ] },
#     { "name": "set_function_model_config", "description": "为功能指定配置与模型索引", "parameters": [ { "name": "function_type", "type": "string", "required": true }, { "name": "config_id", "type": "string", "required": true }, { "name": "model_index", "type": "number", "required": false } ] },
#     { "name": "test_model_config_connection", "description": "按设置页同等逻辑测试配置连通与多模态能力", "parameters": [ { "name": "config_id", "type": "string", "required": true }, { "name": "model_index", "type": "number", "required": false } ] },
#     { "name": "ping_mcp", "description": "快速探测指定包是否可被加载", "parameters": [ { "name": "package_name", "type": "string", "required": true } ] }
#   ]
# }

import json
import re
import time
import math
from datetime import datetime

Error = Exception

# Android 专属常量（Android-only paths）
SANDBOX_EXTERNAL_PACKAGES_DIR = "/sdcard/Android/data/com.ai.assistance.operit/files/packages"  # Android-only
TOOLPKG_DEBUG_INSTALL_ACTION = "com.ai.assistance.operit.DEBUG_INSTALL_TOOLPKG"
TOOLPKG_DEBUG_INSTALL_COMPONENT = "com.ai.assistance.operit/.core.tools.packTool.ToolPkgDebugInstallReceiver"
SANDBOX_SCRIPT_EXECUTION_ACTION = "com.ai.assistance.operit.EXECUTE_JS"
SANDBOX_SCRIPT_EXECUTION_COMPONENT = "com.ai.assistance.operit/com.ai.assistance.operit.core.tools.javascript.ScriptExecutionReceiver"
SANDBOX_SCRIPT_EXECUTION_MODE_SCRIPT = "script"
SANDBOX_SCRIPT_EXECUTION_MODE_CODE = "code"
SANDBOX_JS_TEMP_DIR = "/sdcard/Android/data/com.ai.assistance.operit/js_temp"  # Android-only
DEFAULT_SANDBOX_REFRESH_TIMEOUT_MS = 1500
DEFAULT_TOOLPKG_INSTALL_WAIT_MS = 1500
DEFAULT_SANDBOX_SCRIPT_WAIT_MS = 15000

JS_METADATA_BLOCK_PATTERN = re.compile(r'/\*\s*METADATA([\s\S]*?)\*/', re.MULTILINE)
JS_PACKAGE_NAME_PATTERN = re.compile(r'^\s*["\']?name["\']?\s*:\s*["\']([^"\']+)["\']', re.MULTILINE)
TOOLPKG_ID_PATTERN = re.compile(r'^\s*["\']?toolpkg_id["\']?\s*:\s*["\']([^"\']+)["\']', re.MULTILINE)
TOOLPKG_MAIN_PATTERN = re.compile(r'^\s*["\']?main["\']?\s*:\s*["\']([^"\']+)["\']', re.MULTILINE)
TOOLPKG_SUBPACKAGE_ID_PATTERN = re.compile(r'^\s*["\']?id["\']?\s*:\s*["\']([^"\']+)["\']', re.MULTILINE)
TOOLPKG_SKIP_DIR_NAMES = {".git", "__pycache__"}
TOOLPKG_SKIP_FILE_NAMES = {".DS_Store", "Thumbs.db"}


def get_error_message(error):
    return str(error) if isinstance(error, Exception) else "Unknown error"


def normalize_android_path(raw=None):
    normalized = str(raw if raw is not None else "").strip().replace("\\", "/")
    if not normalized:
        return ""
    if re.match(r'^[a-zA-Z]+://', normalized):
        return normalized
    if normalized.startswith("/"):
        return normalized
    if normalized.startswith("sdcard/"):
        return f"/{normalized}"
    if normalized.startswith("Android/") or normalized.startswith("Download/"):
        return f"/sdcard/{normalized}"
    return normalized


def normalize_package_key(raw=None):
    return str(raw if raw is not None else "").strip().lower()


def normalize_directory_path(path):
    normalized = normalize_android_path(path)
    normalized = re.sub(r'/+', '/', normalized)
    if normalized == "/":
        return normalized
    return normalized.rstrip("/")


def same_android_path(left, right):
    return normalize_directory_path(left) == normalize_directory_path(right)


def path_dirname(path):
    normalized = normalize_directory_path(path)
    index = normalized.rfind("/")
    if index < 0:
        return ""
    if index == 0:
        return "/"
    return normalized[:index]


def path_basename(path):
    normalized = normalize_directory_path(path)
    index = normalized.rfind("/")
    return normalized[index + 1:] if index >= 0 else normalized


def path_join(*parts):
    filtered = [str(p if p is not None else "").strip().replace("\\", "/") for p in parts]
    filtered = [p for p in filtered if p]
    if len(filtered) == 0:
        return ""
    leadingSlash = filtered[0].startswith("/")
    joined = "/".join([re.sub(r'^/+|/+$', '', p) for p in filtered if p])
    return f"/{joined}" if leadingSlash else joined


def safe_debug_file_stem(raw, fallback):
    normalized = re.sub(r'[^A-Za-z0-9._-]+', '_', str(raw if raw is not None else "").strip())
    normalized = re.sub(r'^[_.]+|[_.]+$', '', normalized)
    return normalized or fallback


def parse_boolean_like(value, defaultValue):
    if value is None or value == "":
        return defaultValue
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    normalized = str(value).strip().lower()
    if not normalized:
        return defaultValue
    if normalized in ("true", "1", "yes", "on"):
        return True
    if normalized in ("false", "0", "no", "off"):
        return False
    return defaultValue


def parse_integer_like(value, defaultValue):
    if value is None or value == "":
        return defaultValue
    try:
        parsed = float(value)
        if math.isfinite(parsed) and parsed >= 0:
            return int(parsed)
        return defaultValue
    except (ValueError, TypeError):
        return defaultValue


async def android_path_exists(path):
    result = await Tools.Files.exists(path, "android")
    return result.exists


async def get_android_file_type(path):
    result = await Tools.Files.info(path, "android")
    return result.fileType.strip().lower()


async def ensure_android_directory(path):
    await Tools.Files.mkdir(path, True, "android")


async def delete_android_path_if_exists(path):
    if not path:
        return
    if not await android_path_exists(path):
        return
    await Tools.Files.deleteFile(path, True, "android")


async def cleanup_android_paths(paths):
    uniquePaths = list(set(normalize_android_path(p) for p in paths if normalize_android_path(p)))
    uniquePaths.sort(key=lambda x: len(x), reverse=True)
    for path in uniquePaths:
        try:
            await delete_android_path_if_exists(path)
        except Exception:
            pass


async def read_android_text_file(path):
    result = await Tools.Files.read({"path": path, "environment": "android"})
    return result.content


def parse_json_record(raw):
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        if not parsed or not isinstance(parsed, dict) or isinstance(parsed, list):
            return None
        return parsed
    except Exception:
        return None


def find_sandbox_package_entry(payload, packageName):
    if not payload:
        return None
    targetKey = normalize_package_key(packageName)
    packages = payload.get("packages", []) if payload else []
    for entry in packages:
        if normalize_package_key(entry.get("packageName", "") if entry else "") == targetKey:
            return entry
    return None


def collect_related_package_load_errors(payload, packageName, *relatedPaths):
    normalizedPackageName = normalize_package_key(packageName)
    normalizedPaths = [str(p or "").strip() for p in relatedPaths if str(p or "").strip()]
    packageLoadErrors = payload.get("packageLoadErrors") if payload else None
    if not packageLoadErrors:
        return {}
    result = {}
    for key, value in packageLoadErrors.items():
        normalizedKey = normalize_package_key(key)
        message = str(value or "")
        if (normalizedKey == normalizedPackageName or
                message.lower().find(normalizedPackageName) >= 0 or
                any(p in message for p in normalizedPaths)):
            result[key] = value
    return result


async def refresh_sandbox_packages_until(packageName, timeoutMs):
    deadline = time.time() * 1000 + max(0, timeoutMs)
    lastPayload = None
    lastEntry = None
    while True:
        lastPayload = await Tools.SoftwareSettings.listSandboxPackages()
        lastEntry = find_sandbox_package_entry(lastPayload, packageName)
        if lastEntry:
            return {"payload": lastPayload, "packageEntry": lastEntry}
        if time.time() * 1000 >= deadline:
            return {"payload": lastPayload, "packageEntry": lastEntry}
        await Tools.System.sleep(min(300, max(50, deadline - time.time() * 1000)))


async def wait_for_android_file(path, timeoutMs):
    deadline = time.time() * 1000 + max(0, timeoutMs)
    while True:
        if await android_path_exists(path):
            return True
        if time.time() * 1000 >= deadline:
            return False
        await Tools.System.sleep(min(300, max(50, deadline - time.time() * 1000)))


def parse_json_text(raw):
    text = str(raw if raw is not None else "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def extract_js_metadata_block(sourceText, sourcePath):
    match = JS_METADATA_BLOCK_PATTERN.search(sourceText)
    if not match:
        raise Error(f"Missing METADATA block: {sourcePath}")
    return match.group(1).strip()


def parse_js_package_source(sourceText, sourcePath):
    metadataBlock = extract_js_metadata_block(sourceText, sourcePath)
    match = JS_PACKAGE_NAME_PATTERN.search(metadataBlock)
    packageName = match.group(1).strip() if match else ""
    if not packageName:
        raise Error(f"Missing package metadata name: {sourcePath}")
    return {"packageName": packageName, "metadataBlock": metadataBlock}


async def delete_duplicate_external_js_package_files(packageName, keepPath):
    removedPaths = []
    listing = await Tools.Files.list(SANDBOX_EXTERNAL_PACKAGES_DIR, "android")
    entries = listing.entries if listing and hasattr(listing, "entries") else []
    for entry in entries:
        entryName = str(entry.get("name", "") if isinstance(entry, dict) else getattr(entry, "name", "")).strip()
        if not entryName:
            continue
        isDir = entry.get("isDirectory", False) if isinstance(entry, dict) else getattr(entry, "isDirectory", False)
        if isDir or not entryName.lower().endswith(".js"):
            continue
        candidatePath = path_join(SANDBOX_EXTERNAL_PACKAGES_DIR, entryName)
        if same_android_path(candidatePath, keepPath):
            continue
        try:
            candidateText = await read_android_text_file(candidatePath)
            candidateInfo = parse_js_package_source(candidateText, candidatePath)
            if normalize_package_key(candidateInfo["packageName"]) != normalize_package_key(packageName):
                continue
            await Tools.Files.deleteFile(candidatePath, False, "android")
            removedPaths.append(candidatePath)
        except Exception:
            pass
    return removedPaths


def parse_toolpkg_manifest_text(text, manifestPath):
    packageId = ""
    mainEntry = ""
    subpackageIds = []

    try:
        parsed = json.loads(text)
        if parsed and isinstance(parsed, dict) and not isinstance(parsed, list):
            packageId = str(parsed.get("toolpkg_id", "")).strip()
            mainEntry = str(parsed.get("main", "")).strip()
            if isinstance(parsed.get("subpackages"), list):
                subpackageIds = [str(sp.get("id", "")).strip() for sp in parsed["subpackages"] if str(sp.get("id", "")).strip()]
    except Exception:
        pass

    if not packageId:
        match = TOOLPKG_ID_PATTERN.search(text)
        packageId = match.group(1).strip() if match else ""
    if not mainEntry:
        match = TOOLPKG_MAIN_PATTERN.search(text)
        mainEntry = match.group(1).strip() if match else ""
    if len(subpackageIds) == 0:
        matches = []
        for m in TOOLPKG_SUBPACKAGE_ID_PATTERN.finditer(text):
            subpackageId = m.group(1).strip()
            if subpackageId:
                matches.append(subpackageId)
        subpackageIds = matches

    if not packageId:
        raise Error(f"manifest.toolpkg_id is required: {manifestPath}")
    if not mainEntry:
        raise Error(f"manifest.main is required: {manifestPath}")

    return {
        "packageId": packageId,
        "mainEntry": mainEntry.replace("\\", "/").lstrip("/"),
        "subpackageIds": list(set(subpackageIds))
    }


async def find_toolpkg_manifest_in_folder(folderPath):
    manifestJson = path_join(folderPath, "manifest.json")
    if await android_path_exists(manifestJson):
        return manifestJson
    manifestHjson = path_join(folderPath, "manifest.hjson")
    if await android_path_exists(manifestHjson):
        return manifestHjson
    raise Error(f"Missing manifest.json or manifest.hjson in folder: {folderPath}")


async def resolve_toolpkg_source(rawSourcePath):
    sourcePath = normalize_android_path(rawSourcePath)
    if not sourcePath:
        raise Error("Missing required parameter: source_path")
    if not await android_path_exists(sourcePath):
        raise Error(f"Source path does not exist: {sourcePath}")

    sourceType = await get_android_file_type(sourcePath)
    sourceKind = "folder"
    folderPath = sourcePath
    archivePath = None
    temporaryPaths = []

    lowerBaseName = path_basename(sourcePath).lower()
    if sourceType == "directory":
        folderPath = sourcePath
    elif sourceType == "file" and lowerBaseName in ("manifest.json", "manifest.hjson"):
        folderPath = path_dirname(sourcePath)
    elif sourceType == "file" and lowerBaseName.endswith(".toolpkg"):
        sourceKind = "archive"
        archivePath = sourcePath
        _safe_stem = safe_debug_file_stem(re.sub(r'\.toolpkg$', '', lowerBaseName, flags=re.IGNORECASE), 'toolpkg')
        tempExtractDir = path_join(
            OPERIT_CLEAN_ON_EXIT_DIR,
            f"operit_editor_toolpkg_extract_{_safe_stem}_{int(time.time() * 1000)}"
        )
        await ensure_android_directory(tempExtractDir)
        await Tools.Files.unzip(sourcePath, tempExtractDir, "android")
        folderPath = tempExtractDir
        temporaryPaths.append(tempExtractDir)
    else:
        raise Error("ToolPkg source must be a folder, manifest.json/manifest.hjson, or an existing .toolpkg file")

    manifestPath = await find_toolpkg_manifest_in_folder(folderPath)
    manifestText = await read_android_text_file(manifestPath)
    manifest = parse_toolpkg_manifest_text(manifestText, manifestPath)
    mainPath = path_join(folderPath, manifest["mainEntry"])
    if not await android_path_exists(mainPath):
        raise Error(f"manifest.main file does not exist: {manifestPath} -> {manifest['mainEntry']}")

    return {
        "sourceKind": sourceKind,
        "sourcePath": sourcePath,
        "folderPath": folderPath,
        "manifestPath": manifestPath,
        "packageId": manifest["packageId"],
        "mainEntry": manifest["mainEntry"],
        "subpackageIds": manifest["subpackageIds"],
        "archivePath": archivePath,
        "temporaryPaths": temporaryPaths
    }


async def build_toolpkg_archive_from_folder(source):
    tempBuildDir = path_join(
        OPERIT_CLEAN_ON_EXIT_DIR,
        f"operit_editor_toolpkg_build_{safe_debug_file_stem(source['packageId'], 'toolpkg')}_{int(time.time() * 1000)}"
    )
    await ensure_android_directory(tempBuildDir)
    archivePath = path_join(tempBuildDir, f"{safe_debug_file_stem(source['packageId'], 'toolpkg')}.toolpkg")
    await Tools.Files.zip(source["folderPath"], archivePath, "android", False)
    if not await android_path_exists(archivePath):
        raise Error(f"Failed to create ToolPkg archive: {archivePath}")
    return {"archivePath": archivePath, "temporaryPaths": [tempBuildDir]}


def parse_requested_package_ids(raw=None):
    input_str = str(raw if raw is not None else "").strip()
    if not input_str:
        return []
    return list(set(item.strip() for item in re.split(r'[\r\n,]+', input_str) if item.strip()))


async def operit_editor(params):
    try:
        query = (params or {}).get("query", "")
        complete({
            "success": True,
            "message": "配置排查手册已加载（MCP/Skill/Sandbox Package/沙盒包调试烧录/功能模型与模型配置/TTS-STT语音服务），将按配置链路执行排查。",
            "data": {"query": query}
        })
    except Exception as error:
        complete({"success": False, "message": get_error_message(error)})


async def how_make_skill():
    try:
        locale = (getLang() or "").lower()
        lang = "zh" if locale.startswith("zh") else ("en" if locale.startswith("en") else "both")

        zh = """如何制作 skill（简版）
1. 先创建目录：/sdcard/Download/Operit/skills/<skill_name>/
2. 必备文件：SKILL.md
3. 在 SKILL.md 顶部用 Markdown 元数据（frontmatter）写 name、description
4. 元数据后再写正文：适用场景、执行步骤、约束边界、期望输出
5. 可选内容：scripts/、templates/、examples/、assets/
6. 实践建议：优先下载现成 skill，直接解压过来，并确保目录下有 SKILL.md。"""

        en = """How to make a skill (quick guide)
1. Create a directory: /sdcard/Download/Operit/skills/<skill_name>/
2. Required file: SKILL.md
3. At the top of SKILL.md, use Markdown metadata (frontmatter) for name and description
4. After metadata, write the main sections: use cases, workflow steps, constraints, expected outputs
5. Optional content: scripts/, templates/, examples/, assets/
6. Practical tip: download an existing skill, extract it directly, and ensure the directory contains SKILL.md"""

        message = zh if lang == "zh" else (en if lang == "en" else f"{zh}\n\n---\n\n{en}")
        complete({"success": True, "message": message, "data": {"lang": lang, "zh": zh, "en": en}})
    except Exception as error:
        complete({"success": False, "message": get_error_message(error)})


async def list_sandbox_packages():
    try:
        result = await Tools.SoftwareSettings.listSandboxPackages()
        complete({
            "success": True,
            "message": f"Sandbox package list fetched: {result.totalCount} package(s).",
            "data": result
        })
    except Exception as error:
        complete({"success": False, "message": get_error_message(error)})


async def set_sandbox_package_enabled(params=None):
    try:
        packageName = (params or {}).get("package_name", "")
        enabled = (params or {}).get("enabled", False)
        result = await Tools.SoftwareSettings.setSandboxPackageEnabled(packageName, enabled)
        complete({
            "success": True,
            "message": result.message or "Sandbox package switch updated.",
            "data": result
        })
    except Exception as error:
        complete({"success": False, "message": get_error_message(error)})


async def debug_install_js_package(params=None):
    logs = []
    def logStep(message):
        logs.append(message)
    def finish(payload):
        data = dict(payload.get("data", {}))
        data["logs"] = logs
        complete({**payload, "data": data})

    try:
        sourcePath = normalize_android_path((params or {}).get("source_path"))
        logStep(f"Resolved source_path -> {sourcePath or '<empty>'}")
        if not sourcePath:
            finish({"success": False, "message": "Missing required parameter: source_path"})
            return

        sourceType = await get_android_file_type(sourcePath)
        logStep(f"Source type detected -> {sourceType}")
        if sourceType != "file":
            finish({"success": False, "message": f"JS source must be a file: {sourcePath}"})
            return
        if not sourcePath.lower().endswith(".js"):
            finish({"success": False, "message": f"JS debug install only supports .js files: {sourcePath}"})
            return

        sourceText = await read_android_text_file(sourcePath)
        packageInfo = parse_js_package_source(sourceText, sourcePath)
        logStep(f"Parsed package info -> packageName={packageInfo['packageName']}")
        enableAfterInstall = parse_boolean_like((params or {}).get("enable_after_install"), True)
        activateAfterInstall = parse_boolean_like((params or {}).get("activate_after_install"), True)
        shouldEnable = enableAfterInstall or activateAfterInstall
        logStep(f"Install options -> enableAfterInstall={enableAfterInstall}, activateAfterInstall={activateAfterInstall}, shouldEnable={shouldEnable}")

        await ensure_android_directory(SANDBOX_EXTERNAL_PACKAGES_DIR)
        targetPath = path_join(SANDBOX_EXTERNAL_PACKAGES_DIR, f"{safe_debug_file_stem(packageInfo['packageName'], 'debug_js_package')}.js")
        logStep(f"Target install path -> {targetPath}")
        copied = not same_android_path(sourcePath, targetPath)
        if copied:
            logStep("Source and target differ; replacing target file before copy.")
            await delete_android_path_if_exists(targetPath)
            await Tools.Files.copy(sourcePath, targetPath, False, "android", "android")
            logStep("Package file copied to external sandbox directory.")
        else:
            logStep("Source path already matches target path; skipping file copy.")
        if not await android_path_exists(targetPath):
            finish({"success": False, "message": f"Installed JS package file is missing after copy: {targetPath}"})
            return
        logStep("Verified installed JS package file exists.")

        removedDuplicateFiles = await delete_duplicate_external_js_package_files(packageInfo["packageName"], targetPath)
        logStep(f"Duplicate cleanup completed -> removed {len(removedDuplicateFiles)} file(s).")
        refresh = await refresh_sandbox_packages_until(packageInfo["packageName"], DEFAULT_SANDBOX_REFRESH_TIMEOUT_MS)
        logStep(f"Sandbox refresh completed -> found={bool(refresh['packageEntry'])}, builtIn={refresh['packageEntry'].get('isBuiltIn', False) if refresh['packageEntry'] else False}")
        if not refresh["packageEntry"]:
            finish({"success": False, "message": f"Sandbox package did not appear after refresh: {packageInfo['packageName']}",
                    "data": {"package_name": packageInfo["packageName"], "source_path": sourcePath, "target_path": targetPath, "refresh_result": refresh["payload"]}})
            return
        if refresh["packageEntry"].get("isBuiltIn"):
            finish({"success": False, "message": f"External JS package '{packageInfo['packageName']}' did not take precedence over a built-in package with the same name.",
                    "data": {"package": refresh["packageEntry"], "source_path": sourcePath, "target_path": targetPath}})
            return

        enableResult = None
        if shouldEnable:
            logStep(f"Enabling sandbox package -> {packageInfo['packageName']}")
            enableResult = await Tools.SoftwareSettings.setSandboxPackageEnabled(packageInfo["packageName"], True)
            logStep(f"Enable result -> {enableResult.message or '<empty>'}")
        else:
            logStep("Enable step skipped by configuration.")

        activateResult = None
        if activateAfterInstall:
            logStep(f"Activating package via use_package -> {packageInfo['packageName']}")
            activateResult = await Tools.System.usePackage(packageInfo["packageName"])
            logStep(f"Activation result -> {activateResult or '<empty>'}")
        else:
            logStep("Activation step skipped by configuration.")

        finish({"success": True, "message": f"Debug JS package installed: {packageInfo['packageName']}",
               "data": {"package_name": packageInfo["packageName"], "source_path": sourcePath, "target_path": targetPath,
                        "copied": copied, "removed_duplicate_files": removedDuplicateFiles, "package": refresh["packageEntry"],
                        "enable_after_install": shouldEnable, "activate_after_install": activateAfterInstall,
                        "enable_result": enableResult, "activate_result": activateResult, "refresh_result": refresh["payload"]}})
    except Exception as error:
        logStep(f"Execution failed -> {get_error_message(error)}")
        finish({"success": False, "message": get_error_message(error)})


async def debug_install_toolpkg(params=None):
    cleanupPaths = []
    logs = []
    def logStep(message):
        logs.append(message)
    def finish(payload):
        data = dict(payload.get("data", {}))
        data["logs"] = logs
        complete({**payload, "data": data})
    finalPayload = None

    try:
        resolvedSource = await resolve_toolpkg_source((params or {}).get("source_path", ""))
        logStep(f"Resolved ToolPkg source -> kind={resolvedSource['sourceKind']}, packageId={resolvedSource['packageId']}, sourcePath={resolvedSource['sourcePath']}")
        cleanupPaths.extend(resolvedSource["temporaryPaths"])
        if len(resolvedSource["temporaryPaths"]) > 0:
            logStep(f"Registered temporary paths -> {', '.join(resolvedSource['temporaryPaths'])}")

        archivePath = resolvedSource.get("archivePath") or ""
        if resolvedSource["sourceKind"] == "folder":
            logStep("Source is a folder; building temporary .toolpkg archive.")
            builtArchive = await build_toolpkg_archive_from_folder(resolvedSource)
            archivePath = builtArchive["archivePath"]
            cleanupPaths.extend(builtArchive["temporaryPaths"])
            logStep(f"Built archive -> {archivePath}")

        await ensure_android_directory(SANDBOX_EXTERNAL_PACKAGES_DIR)
        targetPath = path_join(SANDBOX_EXTERNAL_PACKAGES_DIR, f"{safe_debug_file_stem(resolvedSource['packageId'], 'toolpkg')}.toolpkg")
        logStep(f"Target install path -> {targetPath}")
        if not same_android_path(archivePath, targetPath):
            logStep("Archive path differs from target; replacing target archive before copy.")
            await delete_android_path_if_exists(targetPath)
            await Tools.Files.copy(archivePath, targetPath, False, "android", "android")
            logStep("ToolPkg archive copied to external sandbox directory.")
        else:
            logStep("Archive path already matches target path; skipping archive copy.")
        if not await android_path_exists(targetPath):
            finalPayload = {"success": False, "message": f"Installed ToolPkg archive is missing after copy: {targetPath}"}
            return
        logStep("Verified installed ToolPkg archive exists.")

        resetSubpackageStates = parse_boolean_like((params or {}).get("reset_subpackage_states"), True)
        waitMs = parse_integer_like((params or {}).get("wait_ms"), DEFAULT_TOOLPKG_INSTALL_WAIT_MS)
        logStep(f"Install options -> resetSubpackageStates={resetSubpackageStates}, waitMs={waitMs}")
        broadcastResult = await Tools.System.sendBroadcast({
            "action": TOOLPKG_DEBUG_INSTALL_ACTION,
            "component": TOOLPKG_DEBUG_INSTALL_COMPONENT,
            "extras": {"package_name": resolvedSource["packageId"], "file_path": targetPath, "reset_subpackage_states": resetSubpackageStates}
        })
        logStep(f"Debug install broadcast dispatched -> {broadcastResult.result or '<empty>'}")

        refresh = await refresh_sandbox_packages_until(resolvedSource["packageId"], waitMs)
        relatedLoadErrors = collect_related_package_load_errors(refresh["payload"], resolvedSource["packageId"], resolvedSource["sourcePath"], archivePath, targetPath)
        logStep(f"Sandbox refresh completed -> found={bool(refresh['packageEntry'])}, builtIn={refresh['packageEntry'].get('isBuiltIn', False) if refresh['packageEntry'] else False}")
        if len(relatedLoadErrors) > 0:
            logStep(f"Related load errors -> {json.dumps(relatedLoadErrors)}")
        if not refresh["packageEntry"]:
            finalPayload = {"success": False, "message": f"ToolPkg container did not appear after debug install: {resolvedSource['packageId']}",
                           "data": {"package_name": resolvedSource["packageId"], "source_path": resolvedSource["sourcePath"], "archive_path": targetPath,
                                    "broadcast_result": broadcastResult, "refresh_result": refresh["payload"], "related_load_errors": relatedLoadErrors}}
            return
        if refresh["packageEntry"].get("isBuiltIn"):
            finalPayload = {"success": False, "message": f"Debug ToolPkg '{resolvedSource['packageId']}' is shadowed by a built-in package with the same name.",
                           "data": {"package": refresh["packageEntry"], "broadcast_result": broadcastResult, "refresh_result": refresh["payload"], "related_load_errors": relatedLoadErrors}}
            return

        requestedSubpackages = parse_requested_package_ids((params or {}).get("activate_subpackages"))
        knownSubpackageKeys = set(normalize_package_key(sid) for sid in resolvedSource["subpackageIds"])
        unknownRequestedSubpackages = ([] if len(knownSubpackageKeys) == 0
                                       else [sid for sid in requestedSubpackages if normalize_package_key(sid) not in knownSubpackageKeys])
        activationTargets = [sid for sid in requestedSubpackages if sid not in unknownRequestedSubpackages]
        logStep(f"Subpackage activation plan -> requested={', '.join(requestedSubpackages) or '<none>'}, targets={', '.join(activationTargets) or '<none>'}, unknown={', '.join(unknownRequestedSubpackages) or '<none>'}")

        subpackageResults = []
        for subpackageId in activationTargets:
            logStep(f"Enabling subpackage -> {subpackageId}")
            enableResult = await Tools.SoftwareSettings.setSandboxPackageEnabled(subpackageId, True)
            logStep(f"Subpackage enable result [{subpackageId}] -> {enableResult.message or '<empty>'}")
            activateResult = await Tools.System.usePackage(subpackageId)
            logStep(f"Subpackage activate result [{subpackageId}] -> {activateResult or '<empty>'}")
            subpackageResults.append({"subpackage_id": subpackageId, "enable_result": enableResult, "activate_result": activateResult})

        finalPayload = {"success": True, "message": f"Debug ToolPkg installed: {resolvedSource['packageId']}",
                       "data": {"package_name": resolvedSource["packageId"], "source_kind": resolvedSource["sourceKind"], "source_path": resolvedSource["sourcePath"],
                                "manifest_path": resolvedSource["manifestPath"], "main_entry": resolvedSource["mainEntry"], "archive_path": targetPath,
                                "subpackage_ids": resolvedSource["subpackageIds"], "reset_subpackage_states": resetSubpackageStates,
                                "requested_activate_subpackages": requestedSubpackages, "unknown_requested_subpackages": unknownRequestedSubpackages,
                                "subpackage_results": subpackageResults, "package": refresh["packageEntry"], "broadcast_result": broadcastResult,
                                "refresh_result": refresh["payload"], "related_load_errors": relatedLoadErrors}}
    except Exception as error:
        logStep(f"Execution failed -> {get_error_message(error)}")
        finalPayload = {"success": False, "message": get_error_message(error)}
    finally:
        if len(cleanupPaths) > 0:
            logStep(f"Cleaning temporary paths -> {', '.join(cleanupPaths)}")
        await cleanup_android_paths(cleanupPaths)
        if len(cleanupPaths) > 0:
            logStep("Temporary path cleanup completed.")
        if finalPayload:
            finish(finalPayload)


async def debug_run_sandbox_script(params=None):
    logs = []
    def logStep(message):
        logs.append(message)
    def finish(payload):
        data = dict(payload.get("data", {}))
        data["logs"] = logs
        complete({**payload, "data": data})
    finalPayload = None

    try:
        sourcePath = normalize_android_path((params or {}).get("source_path"))
        sourceCode = params.get("source_code", "") if params and isinstance(params.get("source_code"), str) else ""
        hasInlineCode = len(sourceCode.strip()) > 0
        waitMs = parse_integer_like((params or {}).get("wait_ms"), DEFAULT_SANDBOX_SCRIPT_WAIT_MS)
        paramsJson = str((params or {}).get("params_json", "{}")).strip() or "{}"
        parsedParams = parse_json_text(paramsJson)
        envFilePath = normalize_android_path((params or {}).get("env_file_path"))
        scriptLabel = safe_debug_file_stem(str((params or {}).get("script_label", "")).strip(), "sandbox_script")

        logStep(f"Resolved input -> sourcePath={sourcePath or '<empty>'}, hasInlineCode={hasInlineCode}, waitMs={waitMs}")

        if not sourcePath and not hasInlineCode:
            finalPayload = {"success": False, "message": "Either source_path or source_code is required."}
            return

        if sourcePath:
            sourceType = await get_android_file_type(sourcePath)
            logStep(f"Source type detected -> {sourceType}")
            if sourceType != "file":
                finalPayload = {"success": False, "message": f"Sandbox script source must be a file: {sourcePath}"}
                return

        if not parsedParams or not isinstance(parsedParams, dict) or isinstance(parsedParams, list):
            finalPayload = {"success": False, "message": f"params_json must be a JSON object: {paramsJson}"}
            return
        logStep("params_json parsed successfully.")

        if envFilePath:
            envType = await get_android_file_type(envFilePath)
            logStep(f"Env file type detected -> {envType}")
            if envType != "file":
                finalPayload = {"success": False, "message": f"env_file_path must be a file: {envFilePath}"}
                return

        executionMode = SANDBOX_SCRIPT_EXECUTION_MODE_CODE if hasInlineCode else SANDBOX_SCRIPT_EXECUTION_MODE_SCRIPT
        scriptIdentityPath = sourcePath or path_join(SANDBOX_JS_TEMP_DIR, f"{scriptLabel}_{int(time.time() * 1000)}.inline.js")
        logStep(f"Execution mode -> {executionMode}")
        logStep(f"Execution target -> {scriptIdentityPath}")

        executionResult = await Tools.SoftwareSettings.executeSandboxScriptDirect({
            "source_path": sourcePath or None,
            "source_code": sourceCode if hasInlineCode else None,
            "params_json": paramsJson,
            "env_file_path": envFilePath or None,
            "script_label": scriptLabel,
            "wait_ms": waitMs
        })
        logStep(f"Direct execution tool completed -> success={bool(executionResult.success)}, durationMs={executionResult.durationMs if hasattr(executionResult, 'durationMs') else ''}")

        finalPayload = {
            "success": executionResult.success,
            "message": "Sandbox script executed successfully." if executionResult.success else str(getattr(executionResult, "error", "Sandbox script execution failed.")),
            "data": {"execution_mode": executionMode, "source_path": sourcePath, "has_inline_code": hasInlineCode,
                     "env_file_path": envFilePath or None, "params_json": paramsJson, "execution_result": executionResult}
        }
    except Exception as error:
        logStep(f"Execution failed -> {get_error_message(error)}")
        finalPayload = {"success": False, "message": get_error_message(error)}
    finally:
        finish(finalPayload or {"success": False, "message": "Sandbox script execution did not produce a final result."})


async def read_environment_variable(params=None):
    try:
        key = ((params or {}).get("key", "") or "").strip()
        if not key:
            complete({"success": False, "message": "Missing required parameter: key"})
            return
        result = await Tools.SoftwareSettings.readEnvironmentVariable(key)
        complete({
            "success": True,
            "message": f"Environment variable read: {key}" if result.exists else f"Environment variable not set: {key}",
            "data": result
        })
    except Exception as error:
        complete({"success": False, "message": get_error_message(error)})


async def write_environment_variable(params=None):
    try:
        key = ((params or {}).get("key", "") or "").strip()
        if not key:
            complete({"success": False, "message": "Missing required parameter: key"})
            return
        value = (params or {}).get("value", "")
        result = await Tools.SoftwareSettings.writeEnvironmentVariable(key, str(value))
        complete({
            "success": True,
            "message": f"Environment variable cleared: {key}" if result.cleared else f"Environment variable written: {key}",
            "data": result
        })
    except Exception as error:
        complete({"success": False, "message": get_error_message(error)})


async def restart_mcp_with_logs(params=None):
    try:
        timeoutMs = (params or {}).get("timeout_ms") if params else None
        result = await Tools.SoftwareSettings.restartMcpWithLogs(timeoutMs)
        complete({
            "success": True,
            "message": (f"MCP restart timed out after {result.elapsedMs}ms." if result.timedOut
                        else f"MCP restart completed: {result.successCount} success, {result.failedCount} failed."),
            "data": result
        })
    except Exception as error:
        complete({"success": False, "message": get_error_message(error)})


async def get_speech_services_config():
    try:
        result = await Tools.SoftwareSettings.getSpeechServicesConfig()
        complete({"success": True, "message": "Speech services config fetched.", "data": {"parsed": result}})
    except Exception as error:
        complete({"success": False, "message": get_error_message(error)})


async def set_speech_services_config(params=None):
    try:
        updates = dict(params or {})
        result = await Tools.SoftwareSettings.setSpeechServicesConfig(updates)
        complete({"success": True, "message": "Speech services config updated.", "data": {"updates": updates, "parsed": result}})
    except Exception as error:
        complete({"success": False, "message": get_error_message(error)})


async def test_tts_playback(params=None):
    try:
        text = ((params or {}).get("text", "") or "").strip()
        if not text:
            complete({"success": False, "message": "Missing required parameter: text"})
            return
        options = dict(params or {})
        options.pop("text", None)
        result = await Tools.SoftwareSettings.testTtsPlayback(text, options)
        success = result.playbackTriggered
        detailMessage = (result.errorMessage or "").strip() or "TTS playback test failed."
        complete({"success": success, "message": "TTS playback test triggered." if success else detailMessage, "data": result})
    except Exception as error:
        complete({"success": False, "message": get_error_message(error)})


async def list_model_configs():
    try:
        result = await Tools.SoftwareSettings.listModelConfigs()
        complete({"success": True, "message": "Model configs listed.", "data": result})
    except Exception as error:
        complete({"success": False, "message": get_error_message(error)})


async def create_model_config(params=None):
    try:
        options = dict(params or {})
        result = await Tools.SoftwareSettings.createModelConfig(options)
        complete({"success": True, "message": "Model config created.", "data": result})
    except Exception as error:
        complete({"success": False, "message": get_error_message(error)})


async def update_model_config(params=None):
    try:
        configId = ((params or {}).get("config_id", "") or "").strip()
        if not configId:
            complete({"success": False, "message": "Missing required parameter: config_id"})
            return
        updates = dict(params or {})
        updates.pop("config_id", None)
        result = await Tools.SoftwareSettings.updateModelConfig(configId, updates)
        complete({"success": True, "message": "Model config updated.", "data": result})
    except Exception as error:
        complete({"success": False, "message": get_error_message(error)})


async def delete_model_config(params=None):
    try:
        configId = ((params or {}).get("config_id", "") or "").strip()
        if not configId:
            complete({"success": False, "message": "Missing required parameter: config_id"})
            return
        result = await Tools.SoftwareSettings.deleteModelConfig(configId)
        complete({"success": True, "message": "Model config deleted.", "data": result})
    except Exception as error:
        complete({"success": False, "message": get_error_message(error)})


async def list_function_model_configs():
    try:
        result = await Tools.SoftwareSettings.listFunctionModelConfigs()
        complete({"success": True, "message": "Function model bindings listed.", "data": result})
    except Exception as error:
        complete({"success": False, "message": get_error_message(error)})


def pick_context_summary_fields(config):
    if not config:
        config = {}
    return {
        "context_length": config.get("contextLength"),
        "max_context_length": config.get("maxContextLength"),
        "enable_max_context_mode": config.get("enableMaxContextMode"),
        "summary_token_threshold": config.get("summaryTokenThreshold"),
        "enable_summary": config.get("enableSummary"),
        "enable_summary_by_message_count": config.get("enableSummaryByMessageCount"),
        "summary_message_count_threshold": config.get("summaryMessageCountThreshold")
    }


async def get_function_model_config(params=None):
    try:
        functionType = ((params or {}).get("function_type", "") or "").strip()
        if not functionType:
            complete({"success": False, "message": "Missing required parameter: function_type"})
            return
        result = await Tools.SoftwareSettings.getFunctionModelConfig(functionType)
        config = (result.config if result and hasattr(result, "config") else {}) or {}
        contextSummaryKeys = {"contextLength", "maxContextLength", "enableMaxContextMode", "summaryTokenThreshold",
                              "enableSummary", "enableSummaryByMessageCount", "summaryMessageCountThreshold"}
        configWithoutContextSummary = {k: v for k, v in config.items() if k not in contextSummaryKeys}
        filteredResult = {**result.__dict__} if hasattr(result, "__dict__") else dict(result)
        filteredResult["config"] = configWithoutContextSummary
        complete({"success": True, "message": "Function model config fetched.", "data": filteredResult})
    except Exception as error:
        complete({"success": False, "message": get_error_message(error)})


async def get_context_summary_config(params=None):
    try:
        functionType = ((params or {}).get("function_type", "CHAT") or "CHAT").strip().upper()
        if not functionType:
            complete({"success": False, "message": "Missing required parameter: function_type"})
            return
        result = await Tools.SoftwareSettings.getFunctionModelConfig(functionType)
        config = (result.config if result and hasattr(result, "config") else {}) or {}
        if not config:
            complete({"success": False, "message": f"No bound config found for function_type: {functionType}", "data": result})
            return
        complete({
            "success": True,
            "message": f"Context summary config fetched for {functionType}.",
            "data": {
                "function_type": functionType,
                "config_id": getattr(result, "configId", "") or config.get("id", ""),
                "config_name": getattr(result, "configName", "") or config.get("name", ""),
                "model_index": getattr(result, "modelIndex", 0),
                "actual_model_index": getattr(result, "actualModelIndex", 0),
                "selected_model": getattr(result, "selectedModel", ""),
                "context_summary": pick_context_summary_fields(config),
                "raw": result
            }
        })
    except Exception as error:
        complete({"success": False, "message": get_error_message(error)})


async def set_context_summary_config(params=None):
    try:
        functionType = ((params or {}).get("function_type", "CHAT") or "CHAT").strip().upper()
        if not functionType:
            complete({"success": False, "message": "Missing required parameter: function_type"})
            return
        binding = await Tools.SoftwareSettings.getFunctionModelConfig(functionType)
        bindingConfig = (binding.config if binding and hasattr(binding, "config") else {}) or {}
        configId = (getattr(binding, "configId", "") or bindingConfig.get("id", "") or "").strip()
        if not configId:
            complete({"success": False, "message": f"No bound config found for function_type: {functionType}", "data": binding})
            return

        defaultUpdates = {
            "context_length": 48, "max_context_length": 128, "enable_max_context_mode": True,
            "summary_token_threshold": 0.7, "enable_summary": True,
            "enable_summary_by_message_count": True, "summary_message_count_threshold": 16
        }
        updates = dict(defaultUpdates)
        p = params or {}
        for key in ["context_length", "max_context_length", "enable_max_context_mode", "summary_token_threshold",
                     "enable_summary", "enable_summary_by_message_count", "summary_message_count_threshold"]:
            if key in p and p[key] is not None:
                updates[key] = p[key]

        updateResult = await Tools.SoftwareSettings.updateModelConfig(configId, updates)
        updateResultConfig = (updateResult.config if updateResult and hasattr(updateResult, "config") else {}) or {}
        complete({
            "success": True,
            "message": f"Context summary config updated for {functionType}.",
            "data": {
                "function_type": functionType, "config_id": configId, "applied_updates": updates,
                "before": pick_context_summary_fields(bindingConfig),
                "after": pick_context_summary_fields(updateResultConfig),
                "update_result": updateResult
            }
        })
    except Exception as error:
        complete({"success": False, "message": get_error_message(error)})


async def set_function_model_config(params=None):
    try:
        functionType = ((params or {}).get("function_type", "") or "").strip()
        configId = ((params or {}).get("config_id", "") or "").strip()
        if not functionType:
            complete({"success": False, "message": "Missing required parameter: function_type"})
            return
        if not configId:
            complete({"success": False, "message": "Missing required parameter: config_id"})
            return
        result = await Tools.SoftwareSettings.setFunctionModelConfig(functionType, configId, (params or {}).get("model_index"))
        complete({"success": True, "message": "Function model binding updated.", "data": result})
    except Exception as error:
        complete({"success": False, "message": get_error_message(error)})


async def test_model_config_connection(params=None):
    try:
        configId = ((params or {}).get("config_id", "") or "").strip()
        if not configId:
            complete({"success": False, "message": "Missing required parameter: config_id"})
            return
        result = await Tools.SoftwareSettings.testModelConfigConnection(configId, (params or {}).get("model_index"))
        success = bool(result and result.success)
        complete({
            "success": success,
            "message": "Model config connection tests passed." if success else "Model config connection tests have failures.",
            "data": result
        })
    except Exception as error:
        complete({"success": False, "message": get_error_message(error)})


async def ping_mcp(params=None):
    try:
        packageName = ((params or {}).get("package_name", "") or "").strip()
        if not packageName:
            complete({"success": False, "message": "Missing required parameter: package_name"})
            return
        result = await Tools.System.usePackage(packageName)
        complete({"success": True, "message": f"Package probe finished: {packageName}", "data": result})
    except Exception as error:
        complete({"success": False, "message": get_error_message(error)})


# 导出
exports.operit_editor = operit_editor
exports.how_make_skill = how_make_skill
exports.list_sandbox_packages = list_sandbox_packages
exports.set_sandbox_package_enabled = set_sandbox_package_enabled
exports.debug_install_js_package = debug_install_js_package
exports.debug_install_toolpkg = debug_install_toolpkg
exports.debug_run_sandbox_script = debug_run_sandbox_script
exports.read_environment_variable = read_environment_variable
exports.write_environment_variable = write_environment_variable
exports.restart_mcp_with_logs = restart_mcp_with_logs
exports.get_speech_services_config = get_speech_services_config
exports.set_speech_services_config = set_speech_services_config
exports.test_tts_playback = test_tts_playback
exports.list_model_configs = list_model_configs
exports.create_model_config = create_model_config
exports.update_model_config = update_model_config
exports.delete_model_config = delete_model_config
exports.list_function_model_configs = list_function_model_configs
exports.get_function_model_config = get_function_model_config
exports.get_context_summary_config = get_context_summary_config
exports.set_context_summary_config = set_context_summary_config
exports.set_function_model_config = set_function_model_config
exports.test_model_config_connection = test_model_config_connection
exports.ping_mcp = ping_mcp
