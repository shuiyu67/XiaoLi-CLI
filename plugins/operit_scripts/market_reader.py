# METADATA
# {
#   "name": "reader",
#   "display_name": { "zh": "代码读取器", "en": "Code Reader" },
#   "description": { "zh": "在文件夹中搜索匹配的代码（本地文件，无需 Android）", "en": "Search matching code in a folder." },
#   "category": "File",
#   "tools": [
#     { "name": "search_code_in_folder", "description": { "zh": "在文件夹中搜索匹配的代码", "en": "Search matching code in a folder" } }
#   ]
# }
import os
import re


def getErrorMessage(error):
    return str(error) if error else "unknown"


def getErrorStack(error):
    import traceback
    return traceback.format_exc()


async def search_code_in_folder(params):
    folder_path = params.get("folder_path")
    pattern = params.get("pattern")
    file_extensions = params.get("file_extensions", ".js,.ts,.jsx,.tsx,.java,.cs,.py")
    recursive = str(params.get("recursive", "true")).lower() in ("true", "1", "yes")
    if not folder_path:
        return {"success": False, "message": "文件夹路径不能为空"}
    if not pattern:
        return {"success": False, "message": "搜索模式不能为空"}
    try:
        exts = [e.strip().lower() for e in file_extensions.split(",") if e.strip()]
        rx = re.compile(pattern, re.MULTILINE)
        files = []
        if recursive:
            for root, _, fnames in os.walk(folder_path):
                for fn in fnames:
                    if any(fn.lower().endswith(e) for e in exts):
                        files.append(os.path.join(root, fn))
        else:
            for fn in os.listdir(folder_path):
                fp = os.path.join(folder_path, fn)
                if os.path.isfile(fp) and any(fn.lower().endswith(e) for e in exts):
                    files.append(fp)

        results = []
        for fp in files:
            try:
                with open(fp, "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
            except Exception as e:
                console.error(f"处理文件 {fp} 时出错: {getErrorMessage(e)}")
                continue
            matches = []
            for m in rx.finditer(content):
                ln = content.count("\n", 0, m.start()) + 1
                matches.append({"match": m.group(0), "line": ln,
                                 "content": content.split("\n")[ln - 1] if ln - 1 < len(content.split("\n")) else ""})
            if matches:
                results.append({"file": fp, "matches": matches})
        total = sum(len(r["matches"]) for r in results)
        return {"success": True, "message": f"在 {len(files)} 个文件中找到 {total} 处匹配",
                "data": {"files_searched": len(files), "files_with_matches": len(results),
                         "total_matches": total, "results": results[:50]}}
    except Exception as e:
        return {"success": False, "message": f"搜索失败: {getErrorMessage(e)}"}


async def wrap(func, params, ok_msg="操作成功", err_msg="操作失败"):
    try:
        result = await func(params)
        complete({"success": True, "message": result.get("message", ok_msg),
                   "data": result.get("data"), **{k: v for k, v in result.items() if k not in ("success", "message", "data")}})
    except Exception as error:
        console.error(f"Error: {getErrorMessage(error)}")
        complete({"success": False, "message": getErrorMessage(error), "error_stack": getErrorStack(error)})


async def search_code_in_folder_wrapper(params):
    await wrap(search_code_in_folder, params, "代码搜索完成", "代码搜索失败")


exports.search_code_in_folder = search_code_in_folder_wrapper
