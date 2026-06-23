# METADATA
# {
#     "name": "extended_file_tools",
#
#     "display_name": {
#         "zh": "增强文件工具",
#         "en": "Extended File Tools"
#     },
#     "description": {
#         "zh": "拓展文件工具包：提供 file_exists / move_file / copy_file / file_info / unzip_files / zip_files / open_file / share_file（默认文件工具中已移除这些项）。",
#         "en": "Extended file tools: file_exists / move_file / copy_file / file_info / unzip_files / zip_files / open_file / share_file (removed from default file tools)."
#     },
#     "category": "File",
#     "enabledByDefault": true,
#     "tools": [
#         {
#             "name": "file_exists",
#             "description": { "zh": "检查文件或目录是否存在。", "en": "Check if a file or directory exists." },
#             "parameters": [
#                 { "name": "path", "description": { "zh": "目标路径", "en": "Target path" }, "type": "string", "required": true },
#                 { "name": "environment", "description": { "zh": "可选：android/linux", "en": "Optional: android/linux" }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "move_file",
#             "description": { "zh": "移动或重命名文件/目录。", "en": "Move or rename a file/directory." },
#             "parameters": [
#                 { "name": "source", "description": { "zh": "源路径", "en": "Source path" }, "type": "string", "required": true },
#                 { "name": "destination", "description": { "zh": "目标路径", "en": "Destination path" }, "type": "string", "required": true },
#                 { "name": "environment", "description": { "zh": "可选：android/linux", "en": "Optional: android/linux" }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "copy_file",
#             "description": { "zh": "复制文件/目录（支持跨环境复制）。", "en": "Copy a file/directory (supports cross-environment copy)." },
#             "parameters": [
#                 { "name": "source", "description": { "zh": "源路径", "en": "Source path" }, "type": "string", "required": true },
#                 { "name": "destination", "description": { "zh": "目标路径", "en": "Destination path" }, "type": "string", "required": true },
#                 { "name": "recursive", "description": { "zh": "可选：是否递归，默认 false", "en": "Optional: recursive (default: false)" }, "type": "boolean", "required": false },
#                 { "name": "source_environment", "description": { "zh": "可选：源环境 android/linux", "en": "Optional: source environment android/linux" }, "type": "string", "required": false },
#                 { "name": "dest_environment", "description": { "zh": "可选：目标环境 android/linux", "en": "Optional: destination environment android/linux" }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "file_info",
#             "description": { "zh": "获取文件/目录信息。", "en": "Get file/directory info." },
#             "parameters": [
#                 { "name": "path", "description": { "zh": "目标路径", "en": "Target path" }, "type": "string", "required": true },
#                 { "name": "environment", "description": { "zh": "可选：android/linux", "en": "Optional: android/linux" }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "zip_files",
#             "description": { "zh": "压缩文件/目录。", "en": "Zip files/directories." },
#             "parameters": [
#                 { "name": "source", "description": { "zh": "源路径", "en": "Source path" }, "type": "string", "required": true },
#                 { "name": "destination", "description": { "zh": "输出 zip 文件路径", "en": "Destination zip path" }, "type": "string", "required": true },
#                 { "name": "environment", "description": { "zh": "可选：android/linux", "en": "Optional: android/linux" }, "type": "string", "required": false },
#                 { "name": "include_root_directory", "description": { "zh": "压缩目录时是否保留源目录名作为顶层目录，默认 true", "en": "When zipping a directory, keep the source directory name as the top-level folder, default true" }, "type": "boolean", "required": false }
#             ]
#         },
#         {
#             "name": "unzip_files",
#             "description": { "zh": "解压 zip 文件。", "en": "Unzip an archive." },
#             "parameters": [
#                 { "name": "source", "description": { "zh": "zip 文件路径", "en": "Zip file path" }, "type": "string", "required": true },
#                 { "name": "destination", "description": { "zh": "解压目录", "en": "Destination directory" }, "type": "string", "required": true },
#                 { "name": "environment", "description": { "zh": "可选：android/linux", "en": "Optional: android/linux" }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "open_file",
#             "description": { "zh": "用系统默认应用打开文件。", "en": "Open a file with system default app." },
#             "parameters": [
#                 { "name": "path", "description": { "zh": "文件路径", "en": "File path" }, "type": "string", "required": true },
#                 { "name": "environment", "description": { "zh": "可选：android/linux", "en": "Optional: android/linux" }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "share_file",
#             "description": { "zh": "分享文件给其他应用。", "en": "Share a file with other apps." },
#             "parameters": [
#                 { "name": "path", "description": { "zh": "文件路径", "en": "File path" }, "type": "string", "required": true },
#                 { "name": "title", "description": { "zh": "可选：分享标题", "en": "Optional: share title" }, "type": "string", "required": false },
#                 { "name": "environment", "description": { "zh": "可选：android/linux", "en": "Optional: android/linux" }, "type": "string", "required": false }
#             ]
#         }
#     ]
# }


async def file_exists(params):
    result = await Tools.Files.exists(params["path"], params.get("environment"))
    exists_val = result.get("exists") if isinstance(result, dict) else None
    success = bool(result) and (exists_val if exists_val is not None else True)
    return {"success": success, "message": "检查完成", "data": result}


async def move_file(params):
    result = await Tools.Files.move(params["source"], params["destination"], params.get("environment"))
    return {"success": bool(result), "message": "移动完成", "data": result}


async def copy_file(params):
    result = await Tools.Files.copy(
        params["source"],
        params["destination"],
        params.get("recursive"),
        params.get("source_environment"),
        params.get("dest_environment")
    )
    return {"success": bool(result), "message": "复制完成", "data": result}


async def file_info(params):
    result = await Tools.Files.info(params["path"], params.get("environment"))
    return {"success": bool(result), "message": "获取信息完成", "data": result}


async def zip_files(params):
    result = await Tools.Files.zip(
        params["source"],
        params["destination"],
        params.get("environment"),
        params.get("include_root_directory")
    )
    return {"success": bool(result), "message": "压缩完成", "data": result}


async def unzip_files(params):
    result = await Tools.Files.unzip(params["source"], params["destination"], params.get("environment"))
    return {"success": bool(result), "message": "解压完成", "data": result}


async def open_file(params):
    result = await Tools.Files.open(params["path"], params.get("environment"))
    return {"success": bool(result), "message": "打开文件完成", "data": result}


async def share_file(params):
    result = await Tools.Files.share(params["path"], params.get("title"), params.get("environment"))
    return {"success": bool(result), "message": "分享文件完成", "data": result}


async def wrapToolExecution(func, params):
    try:
        result = await func(params)
        complete(result)
    except Exception as error:
        console.error(f"Tool {func.__name__} failed unexpectedly", error)
        msg = getattr(error, "message", str(error))
        complete({
            "success": False,
            "message": f"工具执行时发生意外错误: {msg}",
        })


async def main():
    results = []
    results.append({"tool": "file_exists", "result": {"success": None, "message": "未测试"}})
    results.append({"tool": "move_file", "result": {"success": None, "message": "未测试（会移动/重命名文件）"}})
    results.append({"tool": "copy_file", "result": {"success": None, "message": "未测试（会复制文件）"}})
    results.append({"tool": "file_info", "result": {"success": None, "message": "未测试"}})
    results.append({"tool": "zip_files", "result": {"success": None, "message": "未测试（会写入zip文件）"}})
    results.append({"tool": "unzip_files", "result": {"success": None, "message": "未测试（会写入解压文件）"}})
    results.append({"tool": "open_file", "result": {"success": None, "message": "未测试（会拉起系统应用）"}})
    results.append({"tool": "share_file", "result": {"success": None, "message": "未测试（会弹出分享面板）"}})

    complete({
        "success": True,
        "message": "拓展文件工具包加载完成（未执行破坏性测试）",
        "data": {"results": results}
    })


async def file_exists_wrapper(params):
    await wrapToolExecution(file_exists, params)


async def move_file_wrapper(params):
    await wrapToolExecution(move_file, params)


async def copy_file_wrapper(params):
    await wrapToolExecution(copy_file, params)


async def file_info_wrapper(params):
    await wrapToolExecution(file_info, params)


async def zip_files_wrapper(params):
    await wrapToolExecution(zip_files, params)


async def unzip_files_wrapper(params):
    await wrapToolExecution(unzip_files, params)


async def open_file_wrapper(params):
    await wrapToolExecution(open_file, params)


async def share_file_wrapper(params):
    await wrapToolExecution(share_file, params)


exports.file_exists = file_exists_wrapper
exports.move_file = move_file_wrapper
exports.copy_file = copy_file_wrapper
exports.file_info = file_info_wrapper
exports.zip_files = zip_files_wrapper
exports.unzip_files = unzip_files_wrapper
exports.open_file = open_file_wrapper
exports.share_file = share_file_wrapper
exports.main = main
