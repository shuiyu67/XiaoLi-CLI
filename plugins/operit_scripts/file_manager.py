# METADATA
# {
#     "name": "file_manager",
#     "display_name": {
#         "zh": "Android 文件管理器",
#         "en": "Android File Manager"
#     },
#     "description": {
#         "zh": "通过 Environment 获取外部存储目录，支持列目录、读文本、写文本（真实文件系统操作）。",
#         "en": "Use Environment to get external storage dir; list dir, read/write text files on real filesystem."
#     },
#     "category": "Files",
#     "tools": [
#         {
#             "name": "list_dir",
#             "description": {
#                 "zh": "列出目录内容",
#                 "en": "List directory contents"
#             },
#             "parameters": [
#                 { "name": "path", "description": { "zh": "目录路径（默认外部存储根）", "en": "Dir path (default external storage root)" }, "type": "string", "required": false }
#             ]
#         },
#         {
#             "name": "write_text",
#             "description": {
#                 "zh": "写入文本文件",
#                 "en": "Write text file"
#             },
#             "parameters": [
#                 { "name": "file_path", "description": { "zh": "文件绝对路径", "en": "Absolute file path" }, "type": "string", "required": true },
#                 { "name": "content", "description": { "zh": "文本内容", "en": "Text content" }, "type": "string", "required": true }
#             ]
#         },
#         {
#             "name": "read_text",
#             "description": {
#                 "zh": "读取文本文件",
#                 "en": "Read text file"
#             },
#             "parameters": [
#                 { "name": "file_path", "description": { "zh": "文件绝对路径", "en": "Absolute file path" }, "type": "string", "required": true }
#             ]
#         }
#     ]
# }

TAG = "FileManager"


def _resolve(path):
    """解析路径：默认落到外部存储根"""
    if path and path.strip():
        return os.path.abspath(path.strip())
    return Environment.getExternalStorageDirectory()


async def list_dir(params):
    path = _resolve((params or {}).get("path", ""))
    if not os.path.isdir(path):
        raise Exception(f"目录不存在: {path}")
    entries = []
    for name in sorted(os.listdir(path)):
        full = os.path.join(path, name)
        entries.append({
            "name": name,
            "type": "dir" if os.path.isdir(full) else "file",
            "size": os.path.getsize(full) if os.path.isfile(full) else None,
        })
    Log.i(TAG, f"列出 {path}: {len(entries)} 项")
    result = {"path": path, "count": len(entries), "entries": entries[:100]}
    complete({"success": True, "message": f"已列出 {len(entries)} 项", "data": result})
    return result


async def write_text(params):
    file_path = os.path.abspath((params or {}).get("file_path", ""))
    content = (params or {}).get("content", "")
    if not file_path:
        raise Exception("file_path 不能为空")
    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as fh:
        fh.write(content)
    size = os.path.getsize(file_path)
    Log.w(TAG, f"已写入 {file_path} ({size} 字节)")
    result = {"file_path": file_path, "bytes": size}
    complete({"success": True, "message": f"写入成功 ({size} 字节)", "data": result})
    return result


async def read_text(params):
    file_path = os.path.abspath((params or {}).get("file_path", ""))
    if not file_path:
        raise Exception("file_path 不能为空")
    if not os.path.isfile(file_path):
        raise Exception(f"文件不存在: {file_path}")
    with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
        content = fh.read()
    result = {"file_path": file_path, "bytes": len(content.encode("utf-8")), "content": content[:20000]}
    complete({"success": True, "message": f"读取成功 ({len(content)} 字符)", "data": result})
    return result


async def _dispatch(params):
    action = (params or {}).get("action", "list_dir")
    func = {"list_dir": list_dir, "write_text": write_text, "read_text": read_text}.get(action)
    if not func:
        raise Exception(f"未知操作: {action}（支持 list_dir/write_text/read_text）")
    return await func(params)


exports.list_dir = list_dir
exports.write_text = write_text
exports.read_text = read_text
