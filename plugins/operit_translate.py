"""operit 市场插件 (.ts) → xiaoli-cli 可运行 .py 的脚手架生成器。

设计原则（不需要 android_pyapi）：
  operit 插件使用的是「通用平台 API」(OkHttp / Tools / toolCall /
  NativeInterface / complete / console / exports)，不是 Android API。
  xiaoli-cli 的 operit_loader 已经 1:1 镜像了这套 API（全部用 requests/
  httpx 在 Python 端原生实现），所以「翻译」只是把 TS 语法换成 Python 语法，
  全局名原样保留 —— 不存在 Android 依赖。

本工具只做「可靠」的样板自动化：
  1. 从 /* METADATA {json} */ 提取插件元数据，生成为 Python 友好的 # METADATA 块
  2. 生成 run_tool 契约所需的胶水：getErrorMessage / getErrorStack / wrap /
     exports.x = wrapper
  3. 为每个工具生成 async def 骨架，并把原 .ts 函数体作为 `/// TS 参考` 注释嵌入
  4. 复杂逻辑用 TODO 标注，绝不像「全量 TS→PY 编译器」那样产生半坏代码

用法：
  python operit_translate.py <市场插件.ts> [-o <输出.py>] [-n <插件名>]
"""
import sys
import json
import re
import os


def extract_metadata(ts: str):
    """从 /* METADATA ... */ 提取 JSON 元数据，返回 (meta_dict, cleaned_ts)。"""
    m = re.search(r"/\*\s*METADATA\s*(.*?)\*/", ts, re.DOTALL)
    if not m:
        return None, ts
    raw = m.group(1)
    try:
        meta = json.loads(raw)
    except json.JSONDecodeError:
        # 宽松：去注释后重试
        try:
            meta = json.loads(re.sub(r"//.*", "", raw))
        except json.JSONDecodeError:
            meta = None
    cleaned = ts[:m.start()] + ts[m.end():]
    return meta, cleaned


def py_meta_block(meta: dict) -> str:
    """把元数据渲染成 # METADATA 块（operit_loader 逐行解析的格式）。"""
    js = json.dumps(meta, ensure_ascii=False, indent=2)
    lines = ["# METADATA", "# {"] + ["#     " + ln for ln in js[1:-1].split("\n")] + ["# }", ""]
    return "\n".join(lines)


def strip_ts_types_and_comments(ts: str) -> str:
    """去掉类型注解与注释，仅用于把 .ts 体作为参考注释嵌入（不参与执行）。"""
    # 去块注释 / 行注释
    ts = re.sub(r"/\*.*?\*/", "", ts, flags=re.DOTALL)
    ts = re.sub(r"//[^\n]*", "", ts)
    # as 断言
    ts = re.sub(r"\bas\s+[\w\[\]]+", "", ts)
    # 泛型
    ts = re.sub(r"\b\w+<[^>]+>", lambda m: m.group(0).split("<")[0], ts)
    # 修饰符
    ts = re.sub(r"\b(private|public|protected|readonly|static|export|async|const|let|var)\b", "", ts)
    # 参数/返回类型
    ts = re.sub(r"\)\s*:\s*[^{]+?(\{)", r")\1", ts)
    ts = re.sub(r"\(([^()]*)\)\s*:\s*[^{]+", r"(\1)", ts)
    return ts


def indented(block: str, prefix: str = "    ") -> str:
    return "\n".join((prefix + ln if ln.strip() else ln) for ln in block.split("\n"))


def generate(py_name: str, ts_path: str) -> str:
    with open(ts_path, "r", encoding="utf-8") as f:
        ts = f.read()

    meta, cleaned = extract_metadata(ts)
    if not meta:
        meta = {"name": py_name, "display_name": {"zh": py_name, "en": py_name},
                "description": {"zh": "从 operit 市场翻译", "en": "Translated from operit market"},
                "category": "Utility", "tools": []}

    tools = meta.get("tools", [])
    if not tools:
        # 退路：从 exports.x = 猜测工具名
        for mm in re.finditer(r"exports\.(\w+)\s*=", cleaned):
            tools.append({"name": mm.group(1)})

    out = []
    out.append(py_meta_block(meta))
    out.append("import re")
    out.append("import html")
    out.append("import asyncio")
    out.append("")
    out.append("")
    out.append("def getErrorMessage(error):")
    out.append("    return str(error) if error else \"unknown\"")
    out.append("")
    out.append("")
    out.append("def getErrorStack(error):")
    out.append("    import traceback")
    out.append("    return traceback.format_exc()")
    out.append("")
    out.append("")
    out.append("async def wrap(func, params, ok_msg=\"操作成功\", err_msg=\"操作失败\"):")
    out.append("    \"\"\"operit 的 complete({success,message,data}) 契约封装\"\"\"")
    out.append("    try:")
    out.append("        result = await func(params)")
    out.append("        complete({\"success\": True, \"message\": ok_msg, \"data\": result})")
    out.append("    except Exception as error:")
    out.append("        console.error(f\"Error: {getErrorMessage(error)}\")")
    out.append("        complete({\"success\": False, \"message\": getErrorMessage(error),")
    out.append("                 \"error_stack\": getErrorStack(error)})")
    out.append("")
    out.append("")
    # 参考注释：原 .ts 去类型后的体
    ref = strip_ts_types_and_comments(cleaned).strip()
    if ref:
        out.append("# ==================== 原 .ts 参考（去类型/注释，仅供翻译对照） ====================")
        for ln in ref.split("\n"):
            out.append("# " + ln)
        out.append("# ========================================================================================")
        out.append("")

    # 每个工具：骨架 + wrapper + exports
    for t in tools:
        name = t.get("name", "tool")
        desc = t.get("description", {})
        desc_zh = desc.get("zh", "") if isinstance(desc, dict) else str(desc)
        out.append("")
        out.append(f"async def {name}(params):")
        out.append(f"    \"\"\"{desc_zh or name}（译自 operit 市场 {meta.get('name','?')}.ts）\"\"\"")
        out.append("    # TODO: 用下面的 1:1 API 映射把 .ts 逻辑补全（参考上方 /// TS 参考）")
        out.append("    # OkHttp.newClient().newRequest().url(u).method('GET'/'POST')")
        out.append("    #        .body(payload, 'json'|'form').headers({...}).build().execute()  # async")
        out.append("    # response.isSuccessful() / response.statusCode / response.content")
        out.append("    # Tools.System.sleep(ms) -> {'requestedMs':, 'sleptMs':}")
        out.append("    # console.log / console.error / complete({success,message,data})")
        out.append(f'    raise NotImplementedError("{name} 待翻译")')
        out.append("")
        out.append("")
        out.append(f"async def {name}_wrapper(params):")
        out.append(f"    await wrap({name}, params, \"{name} 完成\", \"{name} 失败\")")
        out.append("")
        out.append("")
        out.append(f"exports.{name} = {name}_wrapper")
        out.append("")

    return "\n".join(out)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    ts_path = sys.argv[1]
    py_name = None
    out_path = None
    if "-n" in sys.argv:
        py_name = sys.argv[sys.argv.index("-n") + 1]
    if "-o" in sys.argv:
        out_path = sys.argv[sys.argv.index("-o") + 1]
    if not py_name:
        py_name = os.path.splitext(os.path.basename(ts_path))[0].replace("-", "_")
    if not out_path:
        out_path = os.path.join(os.path.dirname(ts_path), py_name + ".py")

    code = generate(py_name, ts_path)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"已生成脚手架: {out_path}  ({len(code)} 字节)")
    print("下一步: 打开文件，把 TODO 处按 1:1 API 映射补全即可（无需 android_pyapi）。")


if __name__ == "__main__":
    main()
