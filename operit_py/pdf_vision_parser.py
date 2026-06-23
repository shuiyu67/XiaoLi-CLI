# METADATA
# {
#     "name": "pdf_vision_parser",
#     "display_name": {"zh": "PDF 逐页识图解析", "en": "PDF Vision Parser"},
#     "description": {"zh": "将 PDF 逐页渲染为图片，并调用用户当前配置的识图模型进行解析，最后按页拼接结果。", "en": "Render a PDF page by page into images, send each image to the user's configured vision model, and merge the results."},
#     "enabledByDefault": False,
#     "category": "File",
#     "tools": [
#         {"name": "parse_pdf_with_vision", "description": {"zh": "将 PDF 逐页拆成图片，逐页调用 IMAGE_RECOGNITION 功能模型识图，并返回分页索引与输出文件路径。", "en": "Split a PDF into page images, analyze each page with the IMAGE_RECOGNITION function model, and return per-page indexes plus output file paths."}, "parameters": [
#             {"name": "pdf_path", "description": {"zh": "PDF 文件路径。", "en": "Path to the PDF file."}, "type": "string", "required": True},
#             {"name": "page_prompt", "description": {"zh": "每页识图提示词；不传则使用默认的尽量转文字提示词。", "en": "Vision prompt for each page; defaults to a text-extraction-oriented prompt."}, "type": "string", "required": False},
#             {"name": "start_page", "description": {"zh": "起始页码，1-based，默认 1。", "en": "Start page number, 1-based, default 1."}, "type": "number", "required": False},
#             {"name": "end_page", "description": {"zh": "结束页码，1-based，默认文档最后一页。", "en": "End page number, 1-based, default is the last page."}, "type": "number", "required": False}
#         ]}
#     ]
# }

import json
import re
import time
import math
import os
from urllib.parse import quote, unquote

Error = Exception

DEFAULT_PAGE_PROMPT = (
    "尽量完整提取本页可见文字与结构，保留标题、列表、表格顺序，不做总结，不补充页外信息；公式和图表转成可读文本描述"
)
TOOL_NAME = "parse_pdf_with_vision"
TOOL_FUNCTION_TYPE = "IMAGE_RECOGNITION"
RENDER_SCALE = 2
PAGE_CONCURRENCY = 4
IMAGE_FORMAT = "png"
MERGED_OUTPUT_FILE_NAME = "parsed_output.txt"

# Android 专属 Java 类降级为 stub（跨平台不支持）
# 原 TypeScript 使用 Java.type("java.io.File") 等 Android API，此处降级


class AndroidUnsupportedStub:
    """Android 专属 Java 类的降级 stub，调用任何方法均返回不支持提示。"""

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        def _unsupported(*args, **kwargs):
            raise Error("此功能仅在 Android 上可用")

        return _unsupported


# 降级：原 Java.type(...) 调用
File = AndroidUnsupportedStub
FileOutputStream = AndroidUnsupportedStub
OutputStreamWriter = AndroidUnsupportedStub
BufferedWriter = AndroidUnsupportedStub
ParcelFileDescriptor = AndroidUnsupportedStub
PdfRenderer = AndroidUnsupportedStub
PdfRendererPage = AndroidUnsupportedStub
Bitmap = AndroidUnsupportedStub
BitmapConfig = AndroidUnsupportedStub
BitmapCompressFormat = AndroidUnsupportedStub
Color = AndroidUnsupportedStub
StandardCharsets = AndroidUnsupportedStub
EnhancedAIService = AndroidUnsupportedStub


def isBlank(value):
    return len(str(value if value is not None else "").strip()) == 0


def toTrimmedString(value):
    return str(value if value is not None else "").strip()


def parsePositiveInteger(value, fieldName, options=None):
    options = options or {}
    if value is None:
        if options.get("allowUndefined"):
            return None
        raise Error(f"{fieldName} 不能为空。")

    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise Error(f"{fieldName} 必须是大于 0 的整数。")
    return value


def buildMergedText(pages):
    return "\n\n".join(
        [f"===== Page {page['page_number']} =====\n{page['analysis']}" for page in pages]
    )


def buildVisionModelInfo(binding):
    return {
        "function_type": TOOL_FUNCTION_TYPE,
        "config_id": str(getattr(binding, "configId", "") or ""),
        "config_name": str(getattr(binding, "configName", "") or ""),
        "selected_model": str(getattr(binding, "selectedModel", "") or ""),
    }


def buildData(pdfPath, imageDir, outputPath, totalPageCount, pages, visionModel, failedPage=None):
    data = {
        "pdf_path": pdfPath,
        "image_dir": imageDir,
        "output_path": outputPath,
        "total_page_count": totalPageCount,
        "processed_page_count": len(pages),
        "pages": [
            {
                "page_number": page["page_number"],
                "image_path": page["image_path"],
                "image_link": page["image_link"],
                "output_path": page["output_path"],
            }
            for page in pages
        ],
        "vision_model": visionModel,
    }

    if failedPage:
        data["failed_page"] = failedPage

    return data


def buildPrecheckFailure(message):
    return {
        "success": False,
        "message": message,
        "data": {
            "pdf_path": "",
            "image_dir": "",
            "output_path": "",
            "total_page_count": 0,
            "processed_page_count": 0,
            "pages": [],
            "vision_model": {
                "function_type": TOOL_FUNCTION_TYPE,
                "config_id": "",
                "config_name": "",
                "selected_model": "",
            },
            "failed_page": {
                "page_number": 0,
                "stage": "precheck",
                "error": message,
            },
        },
    }


def safeClose(resource, label):
    if not resource:
        return
    try:
        resource.close()
    except Exception as error:
        console.warn(f"[{TOOL_NAME}] 关闭 {label} 失败: {str(error)}")


def safeRecycle(bitmap):
    if not bitmap:
        return
    try:
        bitmap.recycle()
    except Exception as error:
        console.warn(f"[{TOOL_NAME}] 回收 bitmap 失败: {str(error)}")


def ensureDirectoryExists(dir_):
    if dir_.exists():
        if not dir_.isDirectory():
            raise Error(f"目标路径不是目录: {str(dir_.getAbsolutePath())}")
        return
    created = dir_.mkdirs()
    if not created:
        raise Error(f"无法创建目录: {str(dir_.getAbsolutePath())}")


def resolveAppContext():
    if hasattr(Java, "getApplicationContext") and callable(getattr(Java, "getApplicationContext", None)):
        return Java.getApplicationContext()
    if hasattr(Java, "getContext") and callable(getattr(Java, "getContext", None)):
        return Java.getContext()
    raise Error("无法获取应用 Context。")


def createOutputDirectory():
    parserRootDir = File(OPERIT_CLEAN_ON_EXIT_DIR, "pdf_vision_parser")
    ensureDirectoryExists(parserRootDir)

    timestamp = time.strftime("%Y-%m-%dT%H-%M-%S", time.gmtime())
    runDir = File(parserRootDir, timestamp)
    ensureDirectoryExists(runDir)
    return runDir


def writeTextFile(targetFile, content):
    outputStream = None
    writer = None
    bufferedWriter = None
    try:
        outputStream = FileOutputStream(targetFile)
        writer = OutputStreamWriter(outputStream, StandardCharsets.UTF_8)
        bufferedWriter = BufferedWriter(writer)
        bufferedWriter.write(str(content if content is not None else ""))
        bufferedWriter.flush()
        return str(targetFile.getAbsolutePath())
    finally:
        safeClose(bufferedWriter, "bufferedWriter")
        safeClose(writer, "writer")
        safeClose(outputStream, "outputStream")


def writePageOutputFile(outputDir, pageNumber, content):
    textFile = File(outputDir, f"page-{padPageNumber(pageNumber)}.txt")
    return writeTextFile(textFile, content)


def writeMergedOutputFile(outputDir, pages):
    if not outputDir:
        return ""
    mergedFile = File(outputDir, MERGED_OUTPUT_FILE_NAME)
    return writeTextFile(mergedFile, buildMergedText(pages))


def padPageNumber(pageNumber):
    return str(pageNumber).rjust(4, "0")


def assertVisionBinding(binding):
    if not binding or isBlank(getattr(binding, "configId", None)):
        raise Error("IMAGE_RECOGNITION 当前没有可用绑定。")
    config = getattr(binding, "config", None)
    if not config or getattr(config, "enableDirectImageProcessing", None) is not True:
        raise Error("IMAGE_RECOGNITION 当前绑定的模型未启用识图能力。")


def validatePdfFile(pdfPath):
    if isBlank(pdfPath):
        raise Error("pdf_path 不能为空。")

    pdfFile = File(pdfPath)
    if not pdfFile.exists() or not pdfFile.isFile():
        raise Error(f"PDF 文件不存在: {pdfPath}")

    if not str(pdfFile.getName()).lower().endswith(".pdf"):
        raise Error(f"文件不是 PDF: {pdfPath}")

    return pdfFile


def stripThinkingContent(content):
    result = str(content if content is not None else "")
    result = re.sub(r"<think(?:ing)?>[\s\S]*?(</think(?:ing)?>|\Z)", "", result, flags=re.IGNORECASE)
    result = re.sub(r"<search>[\s\S]*?(</search>|\Z)", "", result, flags=re.IGNORECASE)
    return result.strip()


def sortPageResults(pages):
    return sorted([p for p in pages], key=lambda p: p["page_number"])


def normalizeErrorMessage(error):
    return str(error.message if isinstance(error, Exception) else error)


async def analyzePageImage(service, imagePath, prompt):
    rawAnalysis = str(await service.callSuspend("analyzeImageWithIntent", imagePath, prompt)).strip()
    analysis = stripThinkingContent(rawAnalysis)

    if len(analysis) == 0:
        raise Error("识图模型返回了空结果。")
    if re.match(r"^Image recognition failed:", rawAnalysis, re.IGNORECASE) or re.match(r"^Image recognition failed:", analysis, re.IGNORECASE):
        raise Error(rawAnalysis or analysis)

    return analysis


async def processSinglePage(pdfFile, outputDir, pageNumber, prompt, service):
    console.log(f"[{TOOL_NAME}] 开始处理第 {pageNumber} 页")

    zeroBasedPageIndex = pageNumber - 1
    imageFile = File(outputDir, f"page-{padPageNumber(pageNumber)}.{IMAGE_FORMAT}")
    imagePath = str(imageFile.getAbsolutePath())

    fileDescriptor = None
    pdfRenderer = None
    page = None
    bitmap = None
    outputStream = None
    stage = "render"

    try:
        fileDescriptor = ParcelFileDescriptor.open(pdfFile, ParcelFileDescriptor.MODE_READ_ONLY)
        pdfRenderer = PdfRenderer(fileDescriptor)
        page = pdfRenderer.openPage(zeroBasedPageIndex)

        width = int(Number(page.getWidth()) * RENDER_SCALE)
        height = int(Number(page.getHeight()) * RENDER_SCALE)

        bitmap = Bitmap.createBitmap(width, height, BitmapConfig.ARGB_8888)
        bitmap.eraseColor(Color.WHITE)
        page.render(bitmap, None, None, PdfRendererPage.RENDER_MODE_FOR_DISPLAY)

        outputStream = FileOutputStream(imageFile)
        compressed = bitmap.compress(BitmapCompressFormat.PNG, 100, outputStream)
        if not compressed:
            raise Error(f"页面 {pageNumber} 图片写入失败。")

        safeClose(outputStream, f"page-{pageNumber} output stream")
        outputStream = None

        imageLink = str(NativeInterface.registerImageFromPath(imagePath) or "").strip()
        if not imageLink:
            raise Error(f"页面 {pageNumber} 图片链接注册失败。")

        stage = "vision"
        analysis = await analyzePageImage(service, imagePath, prompt)
        pageOutputPath = writePageOutputFile(outputDir, pageNumber, analysis)

        console.log(f"[{TOOL_NAME}] 第 {pageNumber} 页处理完成")
        return {
            "page_number": pageNumber,
            "image_path": imagePath,
            "image_link": imageLink,
            "output_path": pageOutputPath,
            "analysis": analysis,
        }
    except Exception as error:
        raise PageProcessingFailure(
            page_number=pageNumber,
            stage=stage,
            error=normalizeErrorMessage(error),
            partial_results=[],
        )
    finally:
        safeClose(outputStream, f"page-{pageNumber} output stream")
        safeRecycle(bitmap)
        safeClose(page, f"page-{pageNumber}")
        safeClose(pdfRenderer, f"page-{pageNumber} pdfRenderer")
        safeClose(fileDescriptor, f"page-{pageNumber} parcelFileDescriptor")


class PageProcessingFailure(Exception):
    def __init__(self, page_number, stage, error, partial_results=None):
        self.page_number = page_number
        self.stage = stage
        self.error = error
        self.partial_results = partial_results or []
        super().__init__(error)


async def processPagesWithConcurrency(pageNumbers, limit, worker):
    results = [None] * len(pageNumbers)
    nextIndex = [0]
    failure = [None]

    async def runWorker():
        while True:
            if failure[0]:
                return

            currentIndex = nextIndex[0]
            nextIndex[0] += 1

            if currentIndex >= len(pageNumbers):
                return

            pageNumber = pageNumbers[currentIndex]
            try:
                results[currentIndex] = await worker(pageNumber)
            except Exception as error:
                if not failure[0]:
                    if isinstance(error, PageProcessingFailure):
                        failure[0] = {
                            "page_number": error.page_number,
                            "stage": error.stage,
                            "error": normalizeErrorMessage(error.error),
                        }
                    else:
                        failure[0] = {
                            "page_number": pageNumber,
                            "stage": "render",
                            "error": normalizeErrorMessage(error),
                        }
                return

    workerCount = max(1, min(limit, len(pageNumbers)))
    await Promise.all([runWorker() for _ in range(workerCount)])

    partialResults = sortPageResults([page for page in results if page])
    if failure[0]:
        failureInfo = failure[0]
        raise PageProcessingFailure(
            page_number=failureInfo["page_number"],
            stage=failureInfo["stage"],
            error=failureInfo["error"],
            partial_results=partialResults,
        )

    return partialResults


async def parsePdfWithVisionInternal(params):
    try:
        binding = await Tools.SoftwareSettings.getFunctionModelConfig(TOOL_FUNCTION_TYPE)
        assertVisionBinding(binding)
    except Exception as error:
        message = str(error.message if isinstance(error, Exception) else error)
        return buildPrecheckFailure(message)

    visionModel = buildVisionModelInfo(binding)
    rawPdfPath = toTrimmedString(params.get("pdf_path") if params else None)

    resolvedPrompt = toTrimmedString(params.get("page_prompt") if params else None) or DEFAULT_PAGE_PROMPT

    try:
        pdfFile = validatePdfFile(rawPdfPath)
        startPage = parsePositiveInteger(params.get("start_page") if params else None, "start_page", {"allowUndefined": True}) or 1
        endPageInput = parsePositiveInteger(params.get("end_page") if params else None, "end_page", {"allowUndefined": True})
    except Exception as error:
        message = str(error.message if isinstance(error, Exception) else error)
        return {
            "success": False,
            "message": message,
            "data": {
                "pdf_path": rawPdfPath,
                "image_dir": "",
                "output_path": "",
                "total_page_count": 0,
                "processed_page_count": 0,
                "pages": [],
                "vision_model": visionModel,
                "failed_page": {
                    "page_number": 0,
                    "stage": "precheck",
                    "error": message,
                },
            },
        }

    pages = []
    context = resolveAppContext()
    enhancedAiService = EnhancedAIService.getInstance(context)
    outputDir = None
    imageDir = ""
    outputPath = ""

    fileDescriptor = None
    pdfRenderer = None
    totalPageCount = 0

    try:
        fileDescriptor = ParcelFileDescriptor.open(pdfFile, ParcelFileDescriptor.MODE_READ_ONLY)
        pdfRenderer = PdfRenderer(fileDescriptor)
        totalPageCount = int(Number(pdfRenderer.getPageCount()))

        if not isinstance(totalPageCount, int) or totalPageCount <= 0:
            error = "PDF 没有可处理的页面。"
            return {
                "success": False,
                "message": error,
                "data": buildData(rawPdfPath, imageDir, outputPath, 0, pages, visionModel, {
                    "page_number": 0,
                    "stage": "render",
                    "error": error,
                }),
            }

        resolvedEndPage = min(endPageInput if endPageInput is not None else totalPageCount, totalPageCount)
        if (startPage or 1) > resolvedEndPage:
            error = (
                f"start_page 超出了总页数，文档总页数为 {totalPageCount}。"
                if (startPage or 1) > totalPageCount
                else "start_page 不能大于 end_page。"
            )
            return {
                "success": False,
                "message": error,
                "data": buildData(rawPdfPath, imageDir, outputPath, totalPageCount, pages, visionModel, {
                    "page_number": 0,
                    "stage": "precheck",
                    "error": error,
                }),
            }

        outputDir = createOutputDirectory()
        imageDir = str(outputDir.getAbsolutePath())
        pageNumbers = []
        pageNumber = startPage or 1
        while pageNumber <= resolvedEndPage:
            pageNumbers.append(pageNumber)
            pageNumber += 1

        try:
            async def _worker(currentPageNumber):
                return await processSinglePage(pdfFile, outputDir, currentPageNumber, resolvedPrompt, enhancedAiService)

            processedPages = await processPagesWithConcurrency(pageNumbers, PAGE_CONCURRENCY, _worker)
            pages.extend(processedPages)
        except Exception as error:
            failedPage = error
            partialResults = getattr(failedPage, "partial_results", []) or []
            pages.extend(sortPageResults(partialResults))
            outputPath = writeMergedOutputFile(outputDir, pages)

            return {
                "success": False,
                "message": f"第 {failedPage.page_number} 页处理失败: {failedPage.error}",
                "data": buildData(rawPdfPath, imageDir, outputPath, totalPageCount, pages, visionModel, {
                    "page_number": failedPage.page_number,
                    "stage": failedPage.stage,
                    "error": failedPage.error,
                }),
            }

        outputPath = writeMergedOutputFile(outputDir, pages)
        return {
            "success": True,
            "message": f"成功解析 {len(pages)} 页 PDF 并完成识图，结果已写入 {outputPath}。",
            "data": buildData(rawPdfPath, imageDir, outputPath, totalPageCount, pages, visionModel),
        }
    except Exception as error:
        message = str(error.message if isinstance(error, Exception) else error)
        outputPath = writeMergedOutputFile(outputDir, pages)
        return {
            "success": False,
            "message": message,
            "data": buildData(rawPdfPath, imageDir, outputPath, totalPageCount, pages, visionModel, {
                "page_number": 0,
                "stage": "render",
                "error": message,
            }),
        }
    finally:
        safeClose(pdfRenderer, "pdfRenderer")
        safeClose(fileDescriptor, "parcelFileDescriptor")


async def wrapToolExecution(func, params):
    try:
        result = await func(params if params else {})
        complete(result)
    except Exception as error:
        message = str(error.message if isinstance(error, Exception) else error)
        complete({
            "success": False,
            "message": message,
            "data": {
                "pdf_path": toTrimmedString(params.get("pdf_path") if params else None),
                "image_dir": "",
                "output_path": "",
                "total_page_count": 0,
                "processed_page_count": 0,
                "pages": [],
                "vision_model": {
                    "function_type": TOOL_FUNCTION_TYPE,
                    "config_id": "",
                    "config_name": "",
                    "selected_model": "",
                },
                "failed_page": {
                    "page_number": 0,
                    "stage": "precheck",
                    "error": message,
                },
            },
        })


async def parse_pdf_with_vision(params):
    await wrapToolExecution(parsePdfWithVisionInternal, params)


async def main(params):
    await wrapToolExecution(parsePdfWithVisionInternal, params)


exports.parse_pdf_with_vision = parse_pdf_with_vision
exports.main = main
