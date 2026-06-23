# METADATA
# {
#     "name": "jmcomic_downloader",
#     "display_name": {"zh": "JMComic 下载器", "en": "JMComic Downloader"},
#     "description": {"zh": "提供JMComic漫画下载功能，支持搜索、获取信息和下载，包括对新漫画的图片反爬解码。", "en": "JMComic downloader: search comics, fetch details, and download albums. Includes anti-crawling image decoding for newer comics."},
#     "category": "Media",
#     "tools": [
#         {"name": "main", "description": {"zh": "运行一个内置的测试函数，以验证JMComic工具的基本功能（搜索和获取信息）是否正常工作。", "en": "Run a built-in test to verify basic JMComic functionality (search and info retrieval)."}, "parameters": []},
#         {"name": "search_comics", "description": {"zh": "搜索JMComic漫画", "en": "Search JMComic comics."}, "parameters": [
#             {"name": "query", "description": {"zh": "搜索关键词", "en": "Search keyword."}, "type": "string", "required": True},
#             {"name": "page", "description": {"zh": "页码 (默认: 1)", "en": "Page number (default: 1)."}, "type": "number", "required": False},
#             {"name": "order_by", "description": {"zh": "排序方式 (latest, view, picture, like, 默认: view)", "en": "Sort mode: latest/view/picture/like (default: view)."}, "type": "string", "required": False},
#             {"name": "time", "description": {"zh": "时间范围 (today, week, month, all, 默认: all)", "en": "Time range: today/week/month/all (default: all)."}, "type": "string", "required": False}
#         ]},
#         {"name": "get_album_info", "description": {"zh": "获取漫画（本子）的详细信息", "en": "Get detailed information for a comic album."}, "parameters": [
#             {"name": "album_id", "description": {"zh": "漫画ID", "en": "Album ID."}, "type": "string", "required": True}
#         ]},
#         {"name": "download_album", "description": {"zh": "下载指定ID的单本漫画，包含图片解码功能。", "en": "Download a single comic album by ID, including image decoding."}, "parameters": [
#             {"name": "album_id", "description": {"zh": "要下载的漫画ID", "en": "Album ID to download."}, "type": "string", "required": True},
#             {"name": "download_dir", "description": {"zh": "下载目录 (可选, 默认: /sdcard/Download/Operit/plugins/jmcomic_downloader/downloads) (Android-only 路径)", "en": "Download directory (optional)."}, "type": "string", "required": False}
#         ]},
#         {"name": "batch_download_albums", "description": {"zh": "批量下载多本漫画，包含图片解码功能。", "en": "Batch download multiple comic albums, including image decoding."}, "parameters": [
#             {"name": "album_ids", "description": {"zh": "要下载的漫画ID列表，用逗号分隔", "en": "Comma-separated list of album IDs to download."}, "type": "string", "required": True},
#             {"name": "download_dir", "description": {"zh": "下载目录 (可选)", "en": "Download directory (optional)."}, "type": "string", "required": False}
#         ]}
#     ],
#     "enabledByDefault": False
# }

import json
import re
import time
import math
import random
import hashlib
import base64
import asyncio
from urllib.parse import quote, unquote

Error = Exception

# AES 解密依赖（跨平台）
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding as _padding
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False

# 图片处理依赖（跨平台，替代 Jimp）
try:
    from PIL import Image
    import io as _io
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

DEFAULT_DOWNLOAD_DIR = f"{getPluginConfigDir('jmcomic_downloader')}/downloads"
TEST_DOWNLOAD_DIR = f"{getPluginConfigDir('jmcomic_downloader')}/test_downloads"

__version__ = '2.6.4-py-adapted'


def shuffleDomains(domains):
    shuffled = list(domains)
    for i in range(len(shuffled) - 1, 0, -1):
        j = int(random.random() * (i + 1))
        shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
    return shuffled


JmMagicConstants = {
    "APP_TOKEN_SECRET": '18comicAPP',
    "APP_TOKEN_SECRET_2": '18comicAPPContent',
    "APP_DATA_SECRET": '185Hcomic3PAPP7R',
    "APP_VERSION": '1.8.0',
    "SCRAMBLE_220980": 220980,
    "SCRAMBLE_268850": 268850,
    "SCRAMBLE_421926": 421926,
}

JmModuleConfig = {
    "PROT": 'https://',
    "DOMAIN_API_LIST": shuffleDomains([
        'www.cdnmhwscc.vip',
        'www.cdnplaystation6.club',
        'www.cdnplaystation6.org',
        'www.cdnuc.vip',
        'www.cdn-mspjmapiproxy.xyz',
    ]),
    "DOMAIN_IMAGE_LIST": shuffleDomains([
        'cdn-msp.jmapiproxy1.cc',
        'cdn-msp.jmapiproxy2.cc',
        'cdn-msp2.jmapiproxy2.cc',
        'cdn-msp3.jmapiproxy2.cc',
    ]),
    "APP_HEADERS_TEMPLATE": {
        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'X-Requested-With': 'com.jiaohua_browser',
        'user-agent': 'Mozilla/5.0 (Linux; Android 9; V1938CT Build/PQ3A.190705.11211812; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Safari/537.36',
    },
    "APP_HEADERS_IMAGE": {
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'X-Requested-With': 'com.jiaohua_browser',
    },
}


def joinPath(*segments):
    return re.sub(r'/+', '/', '/'.join(segments))


def dirname(filePath):
    lastSlashPos = filePath.rfind('/')
    if lastSlashPos == -1:
        return "."
    if lastSlashPos == 0:
        return "/"
    return filePath[:lastSlashPos]


def basename(filePath):
    return filePath[filePath.rfind('/') + 1:]


async def ensureDirExists(dirPath):
    if not dirPath or dirPath == '/' or dirPath == '.':
        return
    dirExists = await Tools.Files.exists(dirPath)
    if dirExists.exists:
        return
    parentDir = dirname(dirPath)
    await ensureDirExists(parentDir)
    dirStillNotExists = await Tools.Files.exists(dirPath)
    if not dirStillNotExists.exists:
        await Tools.Files.mkdir(dirPath)


async def runTasksWithConcurrency(tasks, limit):
    results = [None] * len(tasks)
    currentIndex = [0]

    async def runner():
        while currentIndex[0] < len(tasks):
            taskIndex = currentIndex[0]
            currentIndex[0] += 1
            if taskIndex < len(tasks):
                try:
                    results[taskIndex] = await tasks[taskIndex]()
                except Exception as e:
                    console.error(f"并发任务 {taskIndex} 执行失败: {str(e)}")
                    results[taskIndex] = e

    numRunners = min(limit, len(tasks))
    await asyncio.gather(*[runner() for _ in range(numRunners)])
    return [r for r in results if not isinstance(r, Exception)]


class JmImageTool:
    @staticmethod
    def getNum(scrambleId, photoId, imageName):
        scrambleIdNum = int(str(scrambleId))
        photoIdNum = int(str(photoId))

        if photoIdNum < scrambleIdNum:
            return 0
        elif photoIdNum < JmMagicConstants["SCRAMBLE_268850"]:
            return 10
        else:
            x = 10 if photoIdNum < JmMagicConstants["SCRAMBLE_421926"] else 8
            imageNameWithoutExt = JmImageTool.getFileNameFromUrl(imageName, True)
            s = f"{photoIdNum}{imageNameWithoutExt}"
            hash_str = hashlib.md5(s.encode('utf-8')).hexdigest()
            lastChar = ord(hash_str[-1])
            num = lastChar % x
            return (num * 2) + 2

    @staticmethod
    def getFileNameFromUrl(url, withoutExtension=True):
        queryIndex = url.find('?')
        if queryIndex != -1:
            url = url[:queryIndex]
        filename = basename(url)
        if withoutExtension:
            lastDotIndex = filename.rfind('.')
            return filename[:lastDotIndex] if lastDotIndex != -1 else filename
        return filename

    @staticmethod
    async def decodeAndSave(num, imageBase64, decodedSavePath):
        if num == 0:
            await Tools.Files.writeBinary(decodedSavePath, imageBase64)
            return

        if not _HAS_PIL:
            console.warn("PIL/Pillow 不可用，跳过图片解码，保存原始图片。")
            await Tools.Files.writeBinary(decodedSavePath, imageBase64)
            return

        try:
            raw_bytes = base64.b64decode(imageBase64)
            srcImage = Image.open(_io.BytesIO(raw_bytes))
            w, h = srcImage.size
            over = h % num
            resultImage = Image.new(srcImage.mode, (w, h))

            for i in range(num):
                move = int(h / num)
                ySrc = h - (move * (i + 1)) - over
                yDst = move * i

                if i == 0:
                    move += over
                else:
                    yDst += over

                if ySrc < 0 or move <= 0 or (ySrc + move > h):
                    continue

                strip = srcImage.crop((0, ySrc, w, ySrc + move))
                resultImage.paste(strip, (0, yDst))

            buf = _io.BytesIO()
            resultImage.save(buf, format='JPEG')
            pureBase64 = base64.b64encode(buf.getvalue()).decode('ascii')
            await Tools.Files.writeBinary(decodedSavePath, pureBase64)
        except Exception as e:
            console.error(f"图片解码失败，将保存原始图片: {str(e)}")
            await Tools.Files.writeBinary(decodedSavePath, imageBase64)


class JmCryptoTool:
    @staticmethod
    def md5hex(key):
        return hashlib.md5(key.encode('utf-8')).hexdigest()

    @staticmethod
    def tokenAndTokenparam(ts, secret=None):
        if secret is None:
            secret = JmMagicConstants["APP_TOKEN_SECRET"]
        tokenparam = f"{ts},{JmMagicConstants['APP_VERSION']}"
        token = JmCryptoTool.md5hex(f"{ts}{secret}")
        return [token, tokenparam]

    @staticmethod
    def decodeRespData(data, ts, secret=None):
        if secret is None:
            secret = JmMagicConstants["APP_DATA_SECRET"]
        try:
            keyHex = JmCryptoTool.md5hex(f"{ts}{secret}")
            if not _HAS_CRYPTO:
                raise Error("cryptography 库不可用，无法进行 AES 解密。")
            key = bytes.fromhex(keyHex)
            cipher = Cipher(algorithms.AES(key), modes.ECB())
            decryptor = cipher.decryptor()
            # data 是 base64 编码的密文
            ciphertext = base64.b64decode(data)
            decrypted_padded = decryptor.update(ciphertext) + decryptor.finalize()
            # 移除 PKCS7 填充
            unpadder = _padding.PKCS7(128).unpadder()
            decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
            decryptedText = decrypted.decode('utf-8')
            if not decryptedText:
                raise Error("AES decryption returned an empty result.")
            return decryptedText
        except Exception as error:
            if isinstance(error, Error):
                raise error
            raise Error(f"AES Decryption failed. Original error: {str(error)}")


class JmApiResp:
    def __init__(self, resp, ts):
        self.resp = resp
        self.ts = ts

    @property
    def isSuccess(self):
        return self.resp.isSuccessful()

    @property
    def json(self):
        try:
            return json.loads(self.resp.content)
        except Exception as error:
            raise Error(f"JSON解析失败: {str(error)}")

    @property
    def isSuccessful(self):
        return self.isSuccess and self.json.get("code") == 200

    @property
    def encodedData(self):
        return self.json.get("data")

    @property
    def decodedData(self):
        return JmCryptoTool.decodeRespData(self.encodedData, self.ts)

    @property
    def resData(self):
        if not self.isSuccessful:
            raise Error(f"API请求失败: code={self.json.get('code')}")
        decoded = self.decodedData
        try:
            if not isinstance(decoded, str) or not decoded:
                raise Error(f"Cannot parse non-string or empty value. Type: {type(decoded).__name__}")
            return json.loads(decoded)
        except Exception as error:
            if isinstance(error, Error):
                raise error
            preview = str(decoded or 'N/A')[:80]
            raise Error(f"Failed to parse decrypted response. Error: {str(error)}.")

    @property
    def modelData(self):
        return self.resData


class DirRuleImpl:
    def __init__(self, baseDir):
        self.baseDir = baseDir

    def decideImageSaveDir(self, album, photo):
        return joinPath(self.baseDir, self.sanitize(album["title"]))

    def decideAlbumRootDir(self, album):
        return joinPath(self.baseDir, self.sanitize(album["title"]))

    def sanitize(self, name):
        return re.sub(r'[\\?%*:|"<>]', '_', name)


class JmOptionImpl:
    def __init__(self, baseDir=None):
        if baseDir is None:
            baseDir = DEFAULT_DOWNLOAD_DIR
        self.dirRule = DirRuleImpl(baseDir)

    @staticmethod
    def default(baseDir=None):
        return JmOptionImpl(baseDir)

    def buildJmClient(self):
        return JmApiClientImpl()


class JmApiClientImpl:
    def __init__(self):
        self.domainList = JmModuleConfig["DOMAIN_API_LIST"]
        self.retryTimes = 3
        self.client = OkHttp.newClient()
        self.API_ALBUM = '/album'
        self.API_CHAPTER = '/chapter'
        self.API_SEARCH = '/search'
        self.API_CATEGORIES_FILTER = '/categories/filter'

    async def getAlbumDetail(self, albumId):
        resp = await self.reqApi(f"{self.API_ALBUM}?id={albumId}")
        data = resp.resData
        if not data or not data.get("name"):
            raise Error(f"本子 {albumId} 不存在或数据无效")
        return self.parseAlbumData(albumId, data)

    async def getPhotoDetail(self, photoId):
        resp = await self.reqApi(f"{self.API_CHAPTER}?id={photoId}")
        data = resp.resData
        if not data or not data.get("name"):
            raise Error(f"章节 {photoId} 不存在或数据无效")
        return self.parsePhotoData(photoId, data)

    async def searchComics(self, params):
        query = params.get("query")
        page = params.get("page", 1)
        order_by = params.get("order_by", "view")
        time_range = params.get("time", "all")

        orderMap = {"latest": "mr", "view": "mv", "picture": "mp", "like": "tf"}
        timeMap = {"today": "t", "week": "w", "month": "m", "all": "a"}
        apiParams = {
            "search_query": query,
            "page": page,
            "o": orderMap.get(order_by.lower(), orderMap["view"]),
            "t": timeMap.get(time_range.lower(), timeMap["all"]),
        }
        resp = await self.reqApi(f"{self.API_SEARCH}?{self.toUrlSearchParams(apiParams)}")
        data = resp.resData
        results = [
            {"id": str(item.get("id") or item.get("album_id")), "title": item.get("name") or item.get("title")}
            for item in (data.get("content") or [])
        ]
        return {
            "search_params": params,
            "results": results,
            "total_results": len(results),
        }

    async def reqApi(self, url, method="GET", data=None):
        ts = int(time.time())
        for i in range(len(self.domainList)):
            domain = self.domainList[i]
            for retry in range(self.retryTimes):
                try:
                    fullUrl = f"{JmModuleConfig['PROT']}{domain}{url}"
                    token, tokenparam = JmCryptoTool.tokenAndTokenparam(ts)
                    headers = dict(JmModuleConfig["APP_HEADERS_TEMPLATE"])
                    headers["token"] = token
                    headers["tokenparam"] = tokenparam

                    requestBuilder = self.client.newRequest().url(fullUrl).headers(headers)
                    if method == "POST":
                        requestBuilder.method("POST").jsonBody(data)

                    resp = await requestBuilder.build().execute()

                    if resp.isSuccessful():
                        return JmApiResp(resp, ts)
                except Exception as error:
                    console.log(f"[API] 请求失败: {str(error)} 域名: {domain}")
                    if retry == self.retryTimes - 1 and i == len(self.domainList) - 1:
                        raise Error(f"所有域名和重试都失败: {str(error)}")
        raise Error("请求失败")

    async def downloadImage(self, imageUrl, savePath, scrambleId, photoId):
        try:
            response = await self.client.newRequest().url(imageUrl).headers(JmModuleConfig["APP_HEADERS_IMAGE"]).build().execute()
            if not response.isSuccessful():
                raise Error(f"HTTP error! status: {response.statusCode}")
            imageBase64 = response.bodyAsBase64()
            dir_ = dirname(savePath)
            await ensureDirExists(dir_)

            imageName = JmImageTool.getFileNameFromUrl(imageUrl, False)
            num = JmImageTool.getNum(scrambleId, photoId, imageName)
            await JmImageTool.decodeAndSave(num, imageBase64, savePath)
            return True
        except Exception as error:
            console.error(f"[图片] 下载失败: {imageUrl}, 错误: {str(error)}")
            return False

    def toUrlSearchParams(self, obj):
        return '&'.join([f"{quote(str(k))}={quote(str(obj[k]))}" for k in obj])

    def parseAlbumData(self, albumId, data):
        episodeList = data.get("series") if data.get("series") and len(data.get("series")) > 0 else [{"id": albumId, "title": data.get("name")}]
        return {
            "id": albumId,
            "title": data.get("name") or f"本子 {albumId}",
            "author": (data.get("author") and data["author"][0]) or "未知作者",
            "episodeList": episodeList,
            "scrambleId": data.get("scramble_id") or JmMagicConstants["SCRAMBLE_220980"],
            "length": len(episodeList),
        }

    def parsePhotoData(self, photoId, data):
        return {
            "id": photoId,
            "title": data.get("name") or f"章节 {photoId}",
            "pageArr": data.get("images") or [],
            "albumId": data.get("album_id") or photoId,
            "scrambleId": data.get("scramble_id") or JmMagicConstants["SCRAMBLE_220980"],
            "length": len(data.get("images") or []),
        }


class JmDownloaderImpl:
    def __init__(self, option):
        self.option = option
        self.client = option.buildJmClient()

    async def downloadAlbum(self, albumId):
        album = await self.client.getAlbumDetail(albumId)
        await self.downloadByAlbumDetail(album)
        return album

    async def downloadByAlbumDetail(self, album):
        albumDir = self.option.dirRule.decideAlbumRootDir(album)
        await ensureDirExists(albumDir)
        console.log(f"[专辑: {album['title']}] 发现 {album['episodeList'].__len__()} 个章节, 开始下载...")

        chapterConcurrency = 5

        def make_task(episode, i):
            async def _task():
                console.log(f"  [章节 {i + 1}/{len(album['episodeList'])}] 开始下载: {episode['title']} ({episode['id']})")
                try:
                    photo = await self.client.getPhotoDetail(episode["id"])
                    await self.downloadPhotoImages(photo, albumDir, album["id"])
                    console.log(f"  [章节 {i + 1}/{len(album['episodeList'])}] 下载完成: {episode['title']}")
                except Exception as e:
                    console.error(f"  [章节 {i + 1}/{len(album['episodeList'])}] 下载失败: {episode['title']}, 错误: {str(e)}")
            return _task

        tasks = [make_task(episode, i) for i, episode in enumerate(album["episodeList"])]
        await runTasksWithConcurrency(tasks, chapterConcurrency)

    async def downloadPhotoImages(self, photo, albumDir, albumId):
        if not photo["pageArr"] or len(photo["pageArr"]) == 0:
            return

        console.log(f"    [图片集: {photo['title']}] 发现 {len(photo['pageArr'])} 张图片, 开始下载...")
        concurrencyLimit = 10

        def make_task(imageName, i):
            async def _task():
                finalFileName = f"{str(i + 1).zfill(5)}.jpg"
                filePath = joinPath(albumDir, finalFileName)
                fileExists = await Tools.Files.exists(filePath)
                if fileExists.exists:
                    return
                imageUrl = self.buildImageUrl(photo, imageName)
                try:
                    await self.client.downloadImage(imageUrl, filePath, photo["scrambleId"], photo["id"])
                except Exception as e:
                    console.error(f"      [图片下载失败] {finalFileName} from {photo['title']}: {str(e)}")
            return _task

        tasks = [make_task(imageName, i) for i, imageName in enumerate(photo["pageArr"])]
        await runTasksWithConcurrency(tasks, concurrencyLimit)
        console.log(f"    [图片集: {photo['title']}] 所有图片下载任务已处理。")

    def buildImageUrl(self, photo, imageName):
        domain = JmModuleConfig["DOMAIN_IMAGE_LIST"][int(random.random() * len(JmModuleConfig["DOMAIN_IMAGE_LIST"]))]
        return f"{JmModuleConfig['PROT']}{domain}/media/photos/{photo['albumId']}/{imageName}"


class SimpleJMDownloader:
    def __init__(self, downloadDir=None):
        if downloadDir is None:
            downloadDir = DEFAULT_DOWNLOAD_DIR
        self.option = JmOptionImpl.default(downloadDir)
        self.downloader = JmDownloaderImpl(self.option)
        self.client = self.option.buildJmClient()
        console.log(f"JM下载器初始化成功, 下载目录: {self.option.dirRule.baseDir}")

    async def searchComics(self, params):
        console.log(f"搜索漫画: {params.get('query')}")
        return await self.client.searchComics(params)

    async def getAlbumInfo(self, albumId):
        album = await self.client.getAlbumDetail(albumId)
        return {
            "id": album["id"],
            "title": album["title"],
            "author": album["author"],
            "chapterCount": album["length"],
            "success": True,
        }

    async def downloadAlbum(self, albumId):
        console.log(f"获取本子信息: {albumId}")
        try:
            info = await self.getAlbumInfo(albumId)
            if not info["success"]:
                return {"success": False, "albumId": albumId, "error": "获取信息失败"}
            console.log(f"开始下载本子: {info['title']}")
            await self.downloader.downloadAlbum(albumId)
            downloadedFiles = await self._checkDownloadedFiles(info["title"])
            return {
                "success": True,
                "albumId": albumId,
                "title": info["title"],
                "downloadedFiles": downloadedFiles,
            }
        except Exception as error:
            return {"success": False, "albumId": albumId, "error": str(error)}

    async def batchDownload(self, albumIds):
        results = []
        console.log(f"开始批量下载 {len(albumIds)} 个本子")
        concurrencyLimit = 3

        def make_task(albumId, i):
            async def _task():
                console.log(f"\n[{i + 1}/{len(albumIds)}] 开始处理本子: {albumId}")
                result = await self.downloadAlbum(albumId)
                if result["success"]:
                    console.log(f"[{i + 1}/{len(albumIds)}] 下载成功: {result.get('title')}")
                else:
                    console.log(f"[{i + 1}/{len(albumIds)}] 下载失败: {albumId}, {result.get('error') or 'Unknown error'}")
                return result
            return _task

        tasks = [make_task(albumId, i) for i, albumId in enumerate(albumIds)]
        return await runTasksWithConcurrency(tasks, concurrencyLimit)

    async def _checkDownloadedFiles(self, title):
        albumDir = self.option.dirRule.decideAlbumRootDir({"title": title})
        dirExists = await Tools.Files.exists(albumDir)
        if dirExists.exists:
            listResult = await Tools.Files.list(albumDir)
            entries = getattr(listResult, "entries", None) or []
            files = [e.name for e in entries]
            return {
                "directory": albumDir,
                "fileCount": len(files),
                "files": files[:10],
            }
        return {"directory": None, "fileCount": 0, "files": []}


async def main():
    console.log("开始执行JMComic工具功能测试...")
    downloader = SimpleJMDownloader(TEST_DOWNLOAD_DIR)
    testQuery = "原神"

    console.log(f'1. 测试搜索功能，关键词: "{testQuery}"')
    searchResult = await downloader.searchComics({"query": testQuery})

    if not searchResult or not searchResult.get("results") or len(searchResult["results"]) == 0:
        raise Error(f'搜索测试失败: 未能找到关于 "{testQuery}" 的任何结果。')

    console.log(f"搜索成功, 找到 {searchResult['total_results']} 个结果。")
    firstAlbum = searchResult["results"][0]
    console.log(f"2. 测试获取作品信息功能, 作品ID: {firstAlbum['id']} ({firstAlbum['title']})")

    albumInfo = await downloader.getAlbumInfo(firstAlbum["id"])

    if not albumInfo or not albumInfo["success"]:
        raise Error(f"获取作品信息失败, ID: {firstAlbum['id']}")

    console.log(f"作品信息获取成功:")
    console.log(f"   - 标题: {albumInfo['title']}")
    console.log(f"   - 作者: {albumInfo['author']}")
    console.log(f"   - 章节数: {albumInfo['chapterCount']}")

    console.log(f"3. 测试下载功能, 作品ID: {firstAlbum['id']} ({firstAlbum['title']})")
    downloadResult = await downloader.downloadAlbum(firstAlbum["id"])

    if not downloadResult or not downloadResult["success"]:
        raise Error(f"下载作品失败, ID: {firstAlbum['id']}")

    console.log(f"下载成功:")
    dl = downloadResult.get("downloadedFiles") or {}
    console.log(f"   - 保存目录: {dl.get('directory')}")
    console.log(f"   - 文件数量: {dl.get('fileCount')}")

    summary = f"JMComic工具测试完成。成功搜索、获取信息并下载了作品《{albumInfo['title']}》。"
    console.log(f"\n{summary}")
    return summary


async def search_comics(params):
    downloader = SimpleJMDownloader()
    return await downloader.searchComics(params)


async def get_album_info(params):
    downloader = SimpleJMDownloader()
    return await downloader.getAlbumInfo(params.get("album_id"))


async def download_album(params):
    downloader = SimpleJMDownloader(params.get("download_dir"))
    return await downloader.downloadAlbum(params.get("album_id"))


async def batch_download_albums(params):
    albumIds = [id_.strip() for id_ in params.get("album_ids", "").split(",") if id_.strip()]
    if len(albumIds) == 0:
        raise Error("album_ids不能为空")
    downloader = SimpleJMDownloader(params.get("download_dir"))
    return await downloader.batchDownload(albumIds)


async def jmcomic_wrap(func, params, successMessage, failMessage):
    try:
        console.log(f"开始执行: {func.__name__}")
        result = await func(params)
        complete({"success": True, "message": successMessage, "data": result})
    except Exception as error:
        import traceback
        console.error(f"{func.__name__} 执行失败: {str(error)}")
        complete({"success": False, "message": f"{failMessage}: {str(error)}", "error_stack": traceback.format_exc()})


async def _main_wrapper(params):
    await jmcomic_wrap(main, params, '功能测试完成', '功能测试失败')


async def _search_comics_wrapper(params):
    await jmcomic_wrap(search_comics, params, '搜索完成', '搜索失败')


async def _get_album_info_wrapper(params):
    await jmcomic_wrap(get_album_info, params, '信息获取完成', '信息获取失败')


async def _download_album_wrapper(params):
    await jmcomic_wrap(download_album, params, '下载完成', '下载失败')


async def _batch_download_albums_wrapper(params):
    await jmcomic_wrap(batch_download_albums, params, '批量下载完成', '批量下载失败')


exports.main = _main_wrapper
exports.search_comics = _search_comics_wrapper
exports.get_album_info = _get_album_info_wrapper
exports.download_album = _download_album_wrapper
exports.batch_download_albums = _batch_download_albums_wrapper
