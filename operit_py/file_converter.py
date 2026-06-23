# METADATA
# {
#     "name": "file_converter",
#
#     "display_name": {
#         "zh": "文件转换器",
#         "en": "File Converter"
#     },
#     "description": {
#         "zh": "提供全面的文件格式转换功能。支持常见的音频/视频（如 MP4、MOV、MP3、WAV）、图像（如 JPG、PNG、WEBP）以及文档（如 Markdown、HTML、DOCX、PDF）之间的相互转换。",
#         "en": "Comprehensive file format conversion. Supports converting between common audio/video (MP4, MOV, MP3, WAV), images (JPG, PNG, WEBP), and documents (Markdown, HTML, DOCX, PDF)."
#     },
#     "enabledByDefault": true,
#     "category": "File",
#     "tools": [
#         {
#             "name": "convert_file",
#             "description": {
#                 "zh": "调用 FFmpeg、ImageMagick 和 Pandoc 等外部命令行工具，转换文件的格式。支持音视频、图像和文档等多种类型。如果检测到工具未安装，会尝试自动安装。",
#                 "en": "Convert files using external CLI tools such as FFmpeg, ImageMagick, and Pandoc. Supports audio/video, images, and documents. If a required tool is missing, it will attempt to install it automatically."
#             },
#             "parameters": [
#                 { "name": "input_path", "description": { "zh": "输入文件的路径。", "en": "Input file path." }, "type": "string", "required": true },
#                 { "name": "output_path", "description": { "zh": "输出文件的路径。扩展名决定了目标格式。", "en": "Output file path. The file extension determines the target format." }, "type": "string", "required": true },
#                 { "name": "options", "description": { "zh": "用于转换工具的可选命令行选项 (例如, 为 ImageMagick 设置 '-quality 80' )。", "en": "Optional CLI options for the conversion tool (e.g. set '-quality 80' for ImageMagick)." }, "type": "string", "required": false }
#             ]
#         }
#     ]
# }

import traceback

terminalSessionId = None


async def getTerminalSessionId():
    global terminalSessionId
    if terminalSessionId:
        return terminalSessionId
    session = await Tools.System.terminal.create("file_converter_session")
    terminalSessionId = session["sessionId"]
    return terminalSessionId


async def executeTerminalCommand(command, timeoutMs=None):
    sessionId = await getTerminalSessionId()
    return await Tools.System.terminal.exec(sessionId, command)


async def checkAndInstall(toolName, packageName):
    """Checks if a command-line tool is installed, and attempts to install it if not found."""
    console.log(f"Checking for {toolName}...")
    checkCmd = f"command -v {toolName}"
    checkResult = await executeTerminalCommand(checkCmd)

    if checkResult["exitCode"] == 0 and checkResult["output"].strip() != "":
        console.log(f"{toolName} is already installed at: {checkResult['output'].strip()}")
        return True

    console.log(f"{toolName} not found. Attempting to install package: {packageName}...")

    # Assuming an apt-based system (like Debian/Ubuntu).
    updateCmd = "apt-get update"
    console.log(f"Running: {updateCmd}")
    updateResult = await executeTerminalCommand(updateCmd)
    if updateResult["exitCode"] != 0:
        console.warn(f"'apt-get update' failed. This might be okay if caches are fresh, but installation may fail.\nOutput: {updateResult['output']}")

    installCmd = f"apt-get install -y {packageName}"
    console.log(f"Running: {installCmd}")
    installResult = await executeTerminalCommand(installCmd)

    if installResult["exitCode"] != 0:
        console.error(f"Failed to install {packageName}: {installResult['output']}")
        raise Exception(f"Failed to install required tool: {toolName} (package: {packageName}). Please try installing it manually.")

    console.log(f"{packageName} installed successfully.")
    return True


def getConverterInfo(inputPath, outputPath, options=None):
    """Determines the appropriate conversion tool and command based on file extensions."""
    def getExt(path):
        return path.split(".")[-1].lower()

    inputExt = getExt(inputPath)
    outputExt = getExt(outputPath)

    def isAudioVideo(ext):
        return ext in ["mp4", "mkv", "avi", "mov", "flv", "webm", "mp3", "wav", "ogg", "flac", "aac", "m4a", "wma", "wmv"]

    def isImage(ext):
        return ext in ["jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff", "ico", "svg"]

    def isDocument(ext):
        return ext in ["md", "html", "docx", "pdf", "txt", "epub", "odt", "rtf", "tex", "rst", "json", "csv"]

    if isAudioVideo(inputExt) or isAudioVideo(outputExt):
        return {
            "tool": "ffmpeg",
            "pkg": "ffmpeg",
            "command": f'ffmpeg -y -i "{inputPath}" {options or ""} "{outputPath}"'
        }

    if isImage(inputExt) or isImage(outputExt):
        return {
            "tool": "convert",
            "pkg": "imagemagick",
            "command": f'convert "{inputPath}" {options or ""} "{outputPath}"'
        }

    if isDocument(inputExt) or isDocument(outputExt):
        return {
            "tool": "pandoc",
            "pkg": "pandoc",
            "command": f'pandoc "{inputPath}" -o "{outputPath}" {options or ""}'
        }

    raise Exception(f"Unsupported or ambiguous file conversion from .{inputExt} to .{outputExt}.")


async def convert_file(params):
    """The core logic for the convert_file tool."""
    input_path = params["input_path"]
    output_path = params["output_path"]
    options = params.get("options")

    fileExists = await Tools.Files.exists(input_path)
    if not fileExists["exists"]:
        raise Exception(f"Input file not found: {input_path}")

    converter = getConverterInfo(input_path, output_path, options)

    await checkAndInstall(converter["tool"], converter["pkg"])

    console.log(f"Executing conversion command: {converter['command']}")
    result = await executeTerminalCommand(converter["command"])

    if result["exitCode"] != 0:
        raise Exception(f"Conversion failed. Exit code: {result['exitCode']}\nOutput:\n{result['output']}")

    outputExists = await Tools.Files.exists(output_path)
    if not outputExists["exists"]:
        # Sometimes a tool exits with 0 but fails, writing to stderr.
        raise Exception(f"Conversion process finished, but output file was not created at: {output_path}\nTerminal Output:\n{result['output']}")

    return {
        "output_path": output_path,
        "details": f"File converted successfully and saved to {output_path}.",
        "terminal_output": result["output"]
    }


async def wrap(func, params, successMessage, failMessage):
    """A wrapper function for executing tools to provide standardized success/error handling."""
    try:
        result = await func(params)
        complete({"success": True, "message": successMessage, "data": result})
    except Exception as error:
        msg = str(getattr(error, "message", error))
        console.error(f"Function {func.__name__} failed! Error: {msg}")
        complete({"success": False, "message": f"{failMessage}: {msg}", "error_stack": traceback.format_exc()})


async def main():
    """A main function for self-testing the capabilities of this tool package."""
    console.log("--- Starting File Converter Tool Test ---")
    testDir = "/sdcard/Download/converter_test"
    await Tools.Files.mkdir(testDir, True)

    # Test 1: Image conversion (PNG to JPG)
    try:
        console.log("\n[1/3] Testing Image Conversion (PNG -> JPG)")
        # A simple 1x1 red pixel PNG in base64
        pngBase64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/wcAAwAB/epv2AAAAABJRU5ErkJggg=="
        inputPng = f"{testDir}/test.png"
        outputJpg = f"{testDir}/test.jpg"
        await Tools.Files.writeBinary(inputPng, pngBase64)

        imageResult = await convert_file({"input_path": inputPng, "output_path": outputJpg})
        console.log("Image conversion success:", imageResult)
        if not (await Tools.Files.exists(outputJpg))["exists"]:
            raise Exception("JPG file not created.")

        # Verify that readBinary can read the converted image as Base64
        jpgBinary = await Tools.Files.readBinary(outputJpg)
        console.log("ReadBinary success: size=", jpgBinary["size"], "bytes, base64 length=", len(jpgBinary["contentBase64"]))
    except Exception as e:
        msg = str(getattr(e, "message", e))
        console.error("Image conversion test failed:", msg)

    # Test 2: Document conversion (MD to HTML)
    try:
        console.log("\n[2/3] Testing Document Conversion (MD -> HTML)")
        inputMd = f"{testDir}/test.md"
        outputHtml = f"{testDir}/test.html"
        await Tools.Files.write(inputMd, "# Hello World")

        docResult = await convert_file({"input_path": inputMd, "output_path": outputHtml})
        console.log("Document conversion success:", docResult)
        htmlContent = (await Tools.Files.read(outputHtml))["content"]
        if "<h1" not in htmlContent:
            raise Exception("HTML content is incorrect.")
    except Exception as e:
        msg = str(getattr(e, "message", e))
        console.error("Document conversion test failed:", msg)

    # Test 3: Unsupported conversion
    try:
        console.log("\n[3/3] Testing Unsupported Conversion (zip -> tar)")
        inputZip = f"{testDir}/test.zip"
        await Tools.Files.write(inputZip, "dummy content")
        await convert_file({"input_path": inputZip, "output_path": f"{testDir}/test.tar"})
        console.error("Unsupported conversion test FAILED: It should have thrown an error but didn't.")
    except Exception as e:
        msg = str(getattr(e, "message", e))
        console.log("Unsupported conversion test PASSED as expected:", msg)

    console.log("\n--- File Converter Tool Test Finished ---")
    await Tools.Files.deleteFile(testDir, True)
    console.log("Cleaned up test directory.")
    complete({"success": True, "message": "All tests finished."})


async def convert_file_wrapper(p):
    await wrap(convert_file, p, "File conversion successful.", "File conversion failed.")


exports.convert_file = convert_file_wrapper
exports.main = main
