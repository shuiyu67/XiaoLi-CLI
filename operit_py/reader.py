# METADATA
# {
#   "name": "code_reader",
#   "display_name": {"zh": "代码读取器", "en": "Code Reader"},
#   "description": {"zh": "提供代码匹配抓取功能", "en": "Provide code searching and extraction utilities."},
#   "enabledByDefault": True,
#   "category": "File",
#   "tools": [
#     {"name": "search_code_in_folder", "description": {"zh": "在文件夹中搜索匹配的代码", "en": "Search for matching code in a folder."}, "parameters": [
#       {"name": "folder_path", "description": {"zh": "要搜索的文件夹路径", "en": "Folder path to search."}, "type": "string", "required": True},
#       {"name": "pattern", "description": {"zh": "要搜索的代码模式(字符串或正则表达式)", "en": "Pattern to search for (string or regular expression)."}, "type": "string", "required": True},
#       {"name": "file_extensions", "description": {"zh": "要搜索的文件扩展名列表(如 \".ts,.js\")", "en": "File extension list to include (e.g. \".ts,.js\")."}, "type": "string", "required": False},
#       {"name": "recursive", "description": {"zh": "是否递归搜索子文件夹(true/false)", "en": "Whether to search subfolders recursively (true/false)."}, "type": "string", "required": False}
#     ]},
#     {"name": "extract_functions", "description": {"zh": "提取文件夹中的所有函数定义", "en": "Extract all function definitions from a folder."}, "parameters": [
#       {"name": "folder_path", "description": {"zh": "要搜索的文件夹路径", "en": "Folder path to search."}, "type": "string", "required": True},
#       {"name": "function_name_pattern", "description": {"zh": "函数名匹配模式(可选)", "en": "Function name matching pattern (optional)."}, "type": "string", "required": False},
#       {"name": "file_extensions", "description": {"zh": "要搜索的文件扩展名列表(如 \".ts,.js\")", "en": "File extension list to include (e.g. \".ts,.js\")."}, "type": "string", "required": False},
#       {"name": "recursive", "description": {"zh": "是否递归搜索子文件夹(true/false)", "en": "Whether to search subfolders recursively (true/false)."}, "type": "string", "required": False}
#     ]},
#     {"name": "extract_function_block", "description": {"zh": "提取特定函数的代码块", "en": "Extract the code block for a specific function."}, "parameters": [
#       {"name": "file_path", "description": {"zh": "要读取的文件路径", "en": "File path to read."}, "type": "string", "required": True},
#       {"name": "function_name", "description": {"zh": "要提取的函数名称", "en": "Function name to extract."}, "type": "string", "required": True},
#       {"name": "include_line_numbers", "description": {"zh": "是否在结果中包含行号(true/false)", "en": "Whether to include line numbers in the result (true/false)."}, "type": "string", "required": False}
#     ]},
#     {"name": "find_code_blocks", "description": {"zh": "查找文件中的代码块", "en": "Find code blocks in a file."}, "parameters": [
#       {"name": "file_path", "description": {"zh": "要读取的文件路径", "en": "File path to read."}, "type": "string", "required": True},
#       {"name": "block_pattern", "description": {"zh": "代码块匹配模式(如类定义、接口等)", "en": "Code block matching pattern (e.g., class definition, interface, etc.)."}, "type": "string", "required": True},
#       {"name": "include_line_numbers", "description": {"zh": "是否在结果中包含行号(true/false)", "en": "Whether to include line numbers in the result (true/false)."}, "type": "string", "required": False}
#     ]},
#     {"name": "read_regex_matches", "description": {"zh": "读取文件中匹配正则表达式的内容", "en": "Read content in a file that matches a regular expression."}, "parameters": [
#       {"name": "file_path", "description": {"zh": "要读取的文件路径", "en": "File path to read."}, "type": "string", "required": True},
#       {"name": "regex", "description": {"zh": "正则表达式字符串", "en": "Regular expression string."}, "type": "string", "required": True},
#       {"name": "include_line_numbers", "description": {"zh": "是否在结果中包含行号(true/false)", "en": "Whether to include line numbers in the result (true/false)."}, "type": "string", "required": False}
#     ]}
#   ]
# }

import json
import re
import time
import math
from urllib.parse import quote, unquote

Error = Exception


def convertParamTypes(params, paramTypes):
    if not params or not paramTypes:
        return params

    result = {}

    for key in params:
        if params[key] is None:
            result[key] = params[key]
            continue

        expectedType = paramTypes.get(key)
        if not expectedType:
            result[key] = params[key]
            continue

        value = params[key]

        try:
            et = expectedType.lower()
            if et == 'number':
                if isinstance(value, str):
                    if '.' in value:
                        result[key] = float(value)
                    else:
                        result[key] = int(value, 10)
                    if isinstance(result[key], float) and math.isnan(result[key]):
                        raise Error(f"参数 {key} 无法转换为数字: {value}")
                else:
                    result[key] = value
            elif et == 'boolean':
                if isinstance(value, str):
                    lowerValue = value.lower()
                    if lowerValue in ('true', '1', 'yes'):
                        result[key] = True
                    elif lowerValue in ('false', '0', 'no'):
                        result[key] = False
                    else:
                        raise Error(f"参数 {key} 无法转换为布尔值: {value}")
                else:
                    result[key] = value
            elif et == 'array':
                if isinstance(value, str):
                    try:
                        result[key] = json.loads(value)
                        if not isinstance(result[key], list):
                            raise Error('解析结果不是数组')
                    except Exception:
                        raise Error(f"参数 {key} 无法转换为数组: {value}")
                else:
                    result[key] = value
            elif et == 'object':
                if isinstance(value, str):
                    try:
                        result[key] = json.loads(value)
                        if isinstance(result[key], list) or not isinstance(result[key], dict):
                            raise Error('解析结果不是对象')
                    except Exception:
                        raise Error(f"参数 {key} 无法转换为对象: {value}")
                else:
                    result[key] = value
            else:
                result[key] = value
        except Exception as error:
            console.error(f"参数类型转换错误: {str(error)}")
            result[key] = value

    return result


async def writer_wrap(func, params, successMessage, failMessage):
    try:
        console.log(f"开始执行函数: {func.__name__ or '匿名函数'}")
        console.log("参数:", json.dumps(params, indent=2, ensure_ascii=False))

        result = await func(params)

        console.log(f"函数 {func.__name__ or '匿名函数'} 执行结果:", json.dumps(result, indent=2, ensure_ascii=False, default=str))

        if result is None:
            return

        if isinstance(result, bool):
            complete({
                "success": result,
                "message": successMessage if result else failMessage,
            })
        else:
            complete({
                "success": True,
                "message": successMessage,
                "data": result,
            })
    except Exception as error:
        console.error(f"函数 {func.__name__ or '匿名函数'} 执行失败!")
        console.error(f"错误信息: {str(error)}")
        import traceback
        stack = traceback.format_exc()
        console.error(f"错误堆栈: {stack}")

        complete({
            "success": False,
            "message": f"{failMessage}: {str(error)}",
            "error_stack": stack,
        })


async def readFilesRecursively(dir_, fileList=None, extensions=None):
    if fileList is None:
        fileList = []
    try:
        listResult = await Tools.Files.list(dir_)
        entries = getattr(listResult, "entries", None) or []

        for entry in entries:
            filePath = f"{dir_}/{entry.name}"

            if getattr(entry, "isDirectory", False):
                await readFilesRecursively(filePath, fileList, extensions)
            else:
                if not extensions or len(extensions) == 0 or any(entry.name.lower().endswith(ext.lower()) for ext in extensions):
                    fileList.append(filePath)
    except Exception as error:
        console.error(f"读取目录失败: {str(error)}")

    return fileList


async def search_code_in_folder(params):
    paramTypes = {"recursive": "boolean"}
    params = convertParamTypes(params, paramTypes)

    folder_path = params.get("folder_path")
    pattern = params.get("pattern")
    file_extensions = params.get("file_extensions", ".js,.ts,.jsx,.tsx,.java,.cs,.py")
    recursive = params.get("recursive", True)

    if not folder_path:
        raise Error("文件夹路径不能为空")
    if not pattern:
        raise Error("搜索模式不能为空")

    try:
        patternRegex = re.compile(pattern, re.MULTILINE)
        extensions = file_extensions.split(",")

        if recursive:
            files = await readFilesRecursively(folder_path, [], extensions)
        else:
            listResult = await Tools.Files.list(folder_path)
            entries = getattr(listResult, "entries", None) or []
            files = [
                f"{folder_path}/{entry.name}"
                for entry in entries
                if not getattr(entry, "isDirectory", False)
                and any(entry.name.lower().endswith(ext.lower()) for ext in extensions)
            ]

        results = []

        for file in files:
            try:
                fileResult = await Tools.Files.read(file)
                content = getattr(fileResult, "content", "") or ""
                matches = []

                for match in patternRegex.finditer(content):
                    lineNumber = content[:match.start()].count("\n") + 1
                    lines = content.split("\n")
                    lineContent = lines[lineNumber - 1] if lineNumber - 1 < len(lines) else ""

                    matches.append({
                        "match": match.group(0),
                        "line": lineNumber,
                        "content": lineContent,
                    })

                if len(matches) > 0:
                    results.append({
                        "file": file,
                        "matches": matches,
                    })
            except Exception as error:
                console.error(f"处理文件 {file} 时出错: {str(error)}")

        return results
    except Exception as error:
        raise Error(f"搜索代码时出错: {str(error)}")


async def extract_functions(params):
    paramTypes = {"recursive": "boolean"}
    params = convertParamTypes(params, paramTypes)

    folder_path = params.get("folder_path")
    function_name_pattern = params.get("function_name_pattern", ".*")
    file_extensions = params.get("file_extensions", ".js,.ts,.jsx,.tsx")
    recursive = params.get("recursive", True)

    if not folder_path:
        raise Error("文件夹路径不能为空")

    try:
        functionPatterns = [
            f"function\\s+({function_name_pattern})\\s*\\([^)]*\\)\\s*\\{{",
            f"(?:const|let|var)\\s+({function_name_pattern})\\s*=\\s*function\\s*\\([^)]*\\)\\s*\\{{",
            f"(?:const|let|var)\\s+({function_name_pattern})\\s*=\\s*\\([^)]*\\)\\s*=>\\s*\\{{",
            f"(?:async\\s+)?({function_name_pattern})\\s*\\([^)]*\\)\\s*\\{{",
        ]

        combinedPattern = "|".join(functionPatterns)

        return await search_code_in_folder({
            "folder_path": folder_path,
            "pattern": combinedPattern,
            "file_extensions": file_extensions,
            "recursive": recursive,
        })
    except Exception as error:
        raise Error(f"提取函数时出错: {str(error)}")


async def extract_function_block(params):
    paramTypes = {"include_line_numbers": "boolean"}
    params = convertParamTypes(params, paramTypes)

    file_path = params.get("file_path")
    function_name = params.get("function_name")
    include_line_numbers = params.get("include_line_numbers", False)

    if not file_path:
        raise Error("文件路径不能为空")
    if not function_name:
        raise Error("函数名称不能为空")

    try:
        fileResult = await Tools.Files.read(file_path)
        content = getattr(fileResult, "content", "") or ""
        lines = content.split("\n")

        functionPatterns = [
            f"function\\s+{function_name}\\s*\\([^)]*\\)\\s*\\{{",
            f"(?:const|let|var)\\s+{function_name}\\s*=\\s*function\\s*\\([^)]*\\)\\s*\\{{",
            f"(?:const|let|var)\\s+{function_name}\\s*=\\s*\\([^)]*\\)\\s*=>\\s*\\{{",
            f"(?:async\\s+)?{function_name}\\s*\\([^)]*\\)\\s*\\{{",
        ]

        combinedPattern = "|".join(functionPatterns)
        functionRegex = re.compile(combinedPattern)

        startLine = -1
        for i in range(len(lines)):
            if functionRegex.search(lines[i]):
                startLine = i
                break

        if startLine == -1:
            return {"error": f"未找到函数: {function_name}"}

        bracesCount = 0
        endLine = startLine

        openingBraces = len(re.findall(r"{", lines[startLine]))
        closingBraces = len(re.findall(r"}", lines[startLine]))
        bracesCount = openingBraces - closingBraces

        for i in range(startLine + 1, len(lines)):
            openBraces = len(re.findall(r"{", lines[i]))
            closeBraces = len(re.findall(r"}", lines[i]))

            bracesCount += openBraces
            bracesCount -= closeBraces

            if bracesCount == 0:
                endLine = i
                break

        functionBlock = "\n".join(lines[startLine:endLine + 1])

        result = {
            "function_name": function_name,
            "code": functionBlock,
        }

        if include_line_numbers:
            result["start_line"] = startLine + 1
            result["end_line"] = endLine + 1

        return result
    except Exception as error:
        raise Error(f"提取函数代码块时出错: {str(error)}")


async def find_code_blocks(params):
    paramTypes = {"include_line_numbers": "boolean"}
    params = convertParamTypes(params, paramTypes)

    file_path = params.get("file_path")
    block_pattern = params.get("block_pattern")
    include_line_numbers = params.get("include_line_numbers", False)

    if not file_path:
        raise Error("文件路径不能为空")
    if not block_pattern:
        raise Error("代码块匹配模式不能为空")

    try:
        fileResult = await Tools.Files.read(file_path)
        content = getattr(fileResult, "content", "") or ""
        blockRegex = re.compile(block_pattern, re.MULTILINE)

        matches = []

        for match in blockRegex.finditer(content):
            matchText = match.group(0)
            startIndex = match.start()

            lines_before = content[:startIndex].split("\n")
            startLine = len(lines_before)

            endIndex = startIndex + len(matchText)
            bracesCount = 0

            if "{" in matchText:
                initialOpenBraces = len(re.findall(r"{", matchText))
                initialCloseBraces = len(re.findall(r"}", matchText))
                bracesCount = initialOpenBraces - initialCloseBraces

                if bracesCount > 0:
                    remainingContent = content[endIndex:]
                    currentPos = 0

                    for i in range(len(remainingContent)):
                        char = remainingContent[i]

                        if char == "{":
                            bracesCount += 1
                        elif char == "}":
                            bracesCount -= 1

                            if bracesCount == 0:
                                currentPos = i + 1
                                break

                    endIndex += currentPos

            codeBlock = content[startIndex:endIndex]

            blockLines = codeBlock.split("\n")
            endLine = startLine + len(blockLines) - 1

            result = {"block": codeBlock}

            if include_line_numbers:
                result["start_line"] = startLine
                result["end_line"] = endLine

            matches.append(result)

        return {
            "file": file_path,
            "blocks": matches,
        }
    except Exception as error:
        raise Error(f"查找代码块时出错: {str(error)}")


async def read_regex_matches(params):
    paramTypes = {"include_line_numbers": "boolean"}
    params = convertParamTypes(params, paramTypes)

    file_path = params.get("file_path")
    regex = params.get("regex")
    include_line_numbers = params.get("include_line_numbers", False)

    if not file_path:
        raise Error("文件路径不能为空")
    if not regex:
        raise Error("正则表达式不能为空")

    try:
        fileResult = await Tools.Files.read(file_path)
        content = getattr(fileResult, "content", "") or ""
        lines = content.split("\n")
        pattern = re.compile(regex, re.MULTILINE)

        matches = []

        for match in pattern.finditer(content):
            lineNumber = content[:match.start()].count("\n") + 1
            lineContent = lines[lineNumber - 1] if lineNumber - 1 < len(lines) else ""

            result = {
                "match": match.group(0),
                "content": lineContent,
            }

            if include_line_numbers:
                result["line"] = lineNumber

            if match.lastindex and match.lastindex >= 1:
                result["groups"] = [match.group(i) for i in range(1, match.lastindex + 1)]

            matches.append(result)

        return {
            "file": file_path,
            "matches": matches,
        }
    except Exception as error:
        raise Error(f"匹配正则表达式时出错: {str(error)}")


async def _search_code_in_folder_wrapper(params):
    await writer_wrap(search_code_in_folder, params, "代码搜索完成", "代码搜索失败")


async def _extract_functions_wrapper(params):
    await writer_wrap(extract_functions, params, "函数提取完成", "函数提取失败")


async def _extract_function_block_wrapper(params):
    await writer_wrap(extract_function_block, params, "函数代码块提取完成", "函数代码块提取失败")


async def _find_code_blocks_wrapper(params):
    await writer_wrap(find_code_blocks, params, "代码块查找完成", "代码块查找失败")


async def _read_regex_matches_wrapper(params):
    await writer_wrap(read_regex_matches, params, "正则表达式匹配完成", "正则表达式匹配失败")


exports.search_code_in_folder = _search_code_in_folder_wrapper
exports.extract_functions = _extract_functions_wrapper
exports.extract_function_block = _extract_function_block_wrapper
exports.find_code_blocks = _find_code_blocks_wrapper
exports.read_regex_matches = _read_regex_matches_wrapper
