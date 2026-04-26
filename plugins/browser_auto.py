"""
浏览器自动化插件 - 无头浏览器操控
基于 Playwright，支持页面导航、元素交互、截图、JS 执行
"""
import os
import json
import base64
import time
from typing import Optional


class Plugin:
    """浏览器自动化 - 网页操控、表单填写、数据抓取、截图"""

    def __init__(self):
        self.usage = """浏览器自动化工具

连接:
  start                          - 启动浏览器实例
  stop                           - 关闭浏览器
  status                         - 查看浏览器状态

导航:
  open <URL>                     - 打开网页
  back                           - 后退
  forward                        - 前进
  reload                         - 刷新页面
  title                          - 获取页面标题
  url                            - 获取当前 URL

交互:
  click <选择器>                 - 点击元素
  fill <选择器> <文本>           - 填写输入框
  select <选择器> <值>           - 下拉选择
  check <选择器>                 - 勾选复选框
  uncheck <选择器>               - 取消勾选
  hover <选择器>                 - 鼠标悬停
  press <按键>                   - 按键 (Enter/Tab/Escape 等)

提取:
  text [选择器]                  - 获取元素文本 (默认 body)
  html [选择器]                  - 获取元素 HTML
  attr <选择器> <属性名>         - 获取元素属性
  value <选择器>                 - 获取输入框值
  eval <JS代码>                  - 执行 JavaScript
  query <选择器>                 - 查询匹配元素列表

截图:
  screenshot [路径]              - 页面截图 (默认 screenshot.png)
  screenshot --selector <选择器> - 元素截图

等待:
  wait <选择器> [超时秒数]       - 等待元素出现
  wait-gone <选择器> [超时秒数]  - 等待元素消失
  wait-url <URL片段> [超时秒数]  - 等待 URL 变化

高级:
  pdf [路径]                     - 保存页面为 PDF
  cookies                        - 获取所有 cookies
  set-cookie <JSON>              - 设置 cookie
  viewport <宽> <高>             - 设置视口大小
  download <URL> [保存路径]      - 下载文件
"""
        self.cli = None
        self._browser = None
        self._context = None
        self._page = None
        self._pw = None

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "browser_auto",
            "description": "浏览器自动化 - 网页导航、元素交互、表单填写、数据抓取、截图、JS执行",
            "keywords": ["浏览器", "browser", "网页", "点击", "截图", "screenshot", "爬虫",
                         "playwright", "自动化", "表单", "抓取", "导航", "puppeteer"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "browser_auto",
            "description": "浏览器自动化工具",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "description": "操作类型"},
                    "url": {"type": "string", "description": "网页 URL"},
                    "selector": {"type": "string", "description": "CSS 选择器"},
                    "value": {"type": "string", "description": "输入值"},
                    "script": {"type": "string", "description": "JavaScript 代码"},
                    "path": {"type": "string", "description": "保存路径"}
                },
                "required": ["operation"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        url = arguments.get("url", "")
        selector = arguments.get("selector", "")
        return f"{op} {url} {selector}".strip()

    # ── 路由 ──

    def handle(self, args: str) -> str:
        try:
            parts = args.strip().split(maxsplit=1)
            if not parts:
                return "错误：请提供操作类型"

            op = parts[0].lower()
            rest = parts[1] if len(parts) > 1 else ""

            handlers = {
                "start": self._start,
                "stop": self._stop,
                "status": self._status,
                "open": self._open,
                "back": self._back,
                "forward": self._forward,
                "reload": self._reload,
                "title": self._title,
                "url": self._url,
                "click": self._click,
                "fill": self._fill,
                "select": self._select,
                "check": self._check,
                "uncheck": self._uncheck,
                "hover": self._hover,
                "press": self._press,
                "text": self._text,
                "html": self._html,
                "attr": self._attr,
                "value": self._value,
                "eval": self._eval,
                "query": self._query,
                "screenshot": self._screenshot,
                "wait": self._wait,
                "wait-gone": self._wait_gone,
                "wait-url": self._wait_url,
                "pdf": self._pdf,
                "cookies": self._cookies,
                "set-cookie": self._set_cookie,
                "viewport": self._viewport,
                "download": self._download,
            }

            handler = handlers.get(op)
            if not handler:
                return f"错误：不支持的操作 '{op}'"
            return handler(rest)

        except Exception as e:
            return f"浏览器自动化错误: {str(e)}"

    # ── 浏览器生命周期 ──

    def _ensure_playwright(self):
        """确保 Playwright 已安装并可用"""
        try:
            from playwright.sync_api import sync_playwright
            return sync_playwright
        except ImportError:
            return None

    def _start(self, args: str) -> str:
        if self._browser and self._page:
            return "浏览器已在运行中"

        sync_playwright = self._ensure_playwright()
        if not sync_playwright:
            return (" 未安装 Playwright。安装步骤:\n"
                    "  pip install playwright\n"
                    "  playwright install chromium")

        try:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=True)
            self._context = self._browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            self._page = self._context.new_page()
            return " 浏览器已启动 (headless Chromium, 1280×720)"
        except Exception as e:
            return f" 启动失败: {e}"

    def _stop(self, args: str) -> str:
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._pw:
                self._pw.stop()
        except Exception:
            pass
        self._page = None
        self._context = None
        self._browser = None
        self._pw = None
        return " 浏览器已关闭"

    def _status(self, args: str) -> str:
        if self._page and not self._page.is_closed():
            url = self._page.url
            title = self._page.title()
            return f" 运行中\n  URL: {url}\n  标题: {title}"
        return " 未运行"

    def _require_page(self):
        """确保页面可用，否则自动启动"""
        if self._page and not self._page.is_closed():
            return self._page
        self._start("")
        return self._page

    # ── 导航 ──

    def _open(self, args: str) -> str:
        url = args.strip()
        if not url:
            return "错误：请提供 URL"
        if not url.startswith(("http://", "https://", "file://")):
            url = "https://" + url

        page = self._require_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            title = page.title()
            return f" 已打开: {url}\n  标题: {title}"
        except Exception as e:
            return f" 打开失败: {e}"

    def _back(self, args: str) -> str:
        page = self._require_page()
        page.go_back()
        return f" 后退 → {page.url}"

    def _forward(self, args: str) -> str:
        page = self._require_page()
        page.go_forward()
        return f" 前进 → {page.url}"

    def _reload(self, args: str) -> str:
        page = self._require_page()
        page.reload()
        return f" 已刷新: {page.url}"

    def _title(self, args: str) -> str:
        page = self._require_page()
        return page.title() or "(无标题)"

    def _url(self, args: str) -> str:
        page = self._require_page()
        return page.url

    # ── 交互 ──

    def _click(self, selector: str) -> str:
        selector = selector.strip()
        if not selector:
            return "错误：请提供 CSS 选择器"
        page = self._require_page()
        try:
            page.click(selector, timeout=10000)
            return f" 已点击: {selector}"
        except Exception as e:
            return f" 点击失败: {e}"

    def _fill(self, args: str) -> str:
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            return "错误：格式: fill <选择器> <文本>"
        selector, text = parts[0], parts[1]
        page = self._require_page()
        try:
            page.fill(selector, text, timeout=10000)
            return f" 已填写: {selector}"
        except Exception as e:
            return f" 填写失败: {e}"

    def _select(self, args: str) -> str:
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            return "错误：格式: select <选择器> <值>"
        selector, value = parts[0], parts[1]
        page = self._require_page()
        try:
            page.select_option(selector, value, timeout=10000)
            return f" 已选择: {selector} = {value}"
        except Exception as e:
            return f" 选择失败: {e}"

    def _check(self, selector: str) -> str:
        page = self._require_page()
        try:
            page.check(selector.strip(), timeout=10000)
            return f" 已勾选: {selector}"
        except Exception as e:
            return f" 勾选失败: {e}"

    def _uncheck(self, selector: str) -> str:
        page = self._require_page()
        try:
            page.uncheck(selector.strip(), timeout=10000)
            return f" 已取消勾选: {selector}"
        except Exception as e:
            return f" 取消勾选失败: {e}"

    def _hover(self, selector: str) -> str:
        page = self._require_page()
        try:
            page.hover(selector.strip(), timeout=10000)
            return f" 悬停: {selector}"
        except Exception as e:
            return f" 悬停失败: {e}"

    def _press(self, key: str) -> str:
        page = self._require_page()
        page.keyboard.press(key.strip())
        return f" 按键: {key}"

    # ── 提取 ──

    def _text(self, selector: str) -> str:
        selector = selector.strip() or "body"
        page = self._require_page()
        try:
            el = page.query_selector(selector)
            if el:
                text = el.inner_text()
                if len(text) > 3000:
                    text = text[:3000] + f"\n... (截断，共 {len(text)} 字符)"
                return text
            return f"未找到元素: {selector}"
        except Exception as e:
            return f" 获取文本失败: {e}"

    def _html(self, selector: str) -> str:
        selector = selector.strip() or "body"
        page = self._require_page()
        try:
            el = page.query_selector(selector)
            if el:
                html = el.inner_html()
                if len(html) > 5000:
                    html = html[:5000] + "\n... (截断)"
                return html
            return f"未找到元素: {selector}"
        except Exception as e:
            return f" 获取 HTML 失败: {e}"

    def _attr(self, args: str) -> str:
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            return "错误：格式: attr <选择器> <属性名>"
        selector, attr_name = parts[0], parts[1]
        page = self._require_page()
        try:
            el = page.query_selector(selector)
            if el:
                val = el.get_attribute(attr_name)
                return f"{attr_name} = {val}"
            return f"未找到元素: {selector}"
        except Exception as e:
            return f" 获取属性失败: {e}"

    def _value(self, selector: str) -> str:
        page = self._require_page()
        try:
            el = page.query_selector(selector.strip())
            if el:
                return el.input_value()
            return f"未找到元素: {selector}"
        except Exception as e:
            return f" 获取值失败: {e}"

    def _eval(self, script: str) -> str:
        script = script.strip()
        if not script:
            return "错误：请提供 JavaScript 代码"
        page = self._require_page()
        try:
            result = page.evaluate(script)
            if isinstance(result, (dict, list)):
                return json.dumps(result, ensure_ascii=False, indent=2)
            return str(result)
        except Exception as e:
            return f" JS 执行失败: {e}"

    def _query(self, selector: str) -> str:
        selector = selector.strip()
        if not selector:
            return "错误：请提供 CSS 选择器"
        page = self._require_page()
        try:
            elements = page.query_selector_all(selector)
            if not elements:
                return f"未找到匹配 '{selector}' 的元素"

            result = [f"找到 {len(elements)} 个元素:\n"]
            for i, el in enumerate(elements[:20]):
                tag = el.evaluate("el => el.tagName.toLowerCase()")
                text = el.inner_text()[:80].replace('\n', ' ').strip()
                result.append(f"  [{i}] <{tag}> {text}")
            if len(elements) > 20:
                result.append(f"  ... 还有 {len(elements) - 20} 个")
            return '\n'.join(result)
        except Exception as e:
            return f" 查询失败: {e}"

    # ── 截图 ──

    def _screenshot(self, args: str) -> str:
        page = self._require_page()

        # 解析参数
        path = "screenshot.png"
        selector = None
        parts = args.strip().split()
        i = 0
        while i < len(parts):
            if parts[i] == "--selector" and i + 1 < len(parts):
                selector = parts[i + 1]
                i += 2
            elif not parts[i].startswith("-"):
                path = parts[i]
                i += 1
            else:
                i += 1

        try:
            if selector:
                el = page.query_selector(selector)
                if not el:
                    return f"未找到元素: {selector}"
                el.screenshot(path=path)
            else:
                page.screenshot(path=path, full_page=True)

            size = os.path.getsize(path)
            return f" 截图已保存: {path} ({size/1024:.1f} KB)"
        except Exception as e:
            return f" 截图失败: {e}"

    # ── 等待 ──

    def _wait(self, args: str) -> str:
        parts = args.strip().split()
        if not parts:
            return "错误：请提供选择器"
        selector = parts[0]
        timeout = int(parts[1]) * 1000 if len(parts) > 1 else 30000
        page = self._require_page()
        try:
            page.wait_for_selector(selector, timeout=timeout)
            return f" 元素已出现: {selector}"
        except Exception:
            return f" 等待超时: {selector}"

    def _wait_gone(self, args: str) -> str:
        parts = args.strip().split()
        if not parts:
            return "错误：请提供选择器"
        selector = parts[0]
        timeout = int(parts[1]) * 1000 if len(parts) > 1 else 30000
        page = self._require_page()
        try:
            page.wait_for_selector(selector, state="hidden", timeout=timeout)
            return f" 元素已消失: {selector}"
        except Exception:
            return f" 等待超时: {selector}"

    def _wait_url(self, args: str) -> str:
        parts = args.strip().split()
        if not parts:
            return "错误：请提供 URL 片段"
        url_part = parts[0]
        timeout = int(parts[1]) * 1000 if len(parts) > 1 else 30000
        page = self._require_page()
        try:
            page.wait_for_url(f"**{url_part}**", timeout=timeout)
            return f" URL 已变化: {page.url}"
        except Exception:
            return f" 等待超时: URL 未变化"

    # ── 高级 ──

    def _pdf(self, args: str) -> str:
        path = args.strip() or "page.pdf"
        page = self._require_page()
        try:
            page.pdf(path=path)
            size = os.path.getsize(path)
            return f" PDF 已保存: {path} ({size/1024:.1f} KB)"
        except Exception as e:
            return f" PDF 生成失败: {e}"

    def _cookies(self, args: str) -> str:
        page = self._require_page()
        cookies = page.context.cookies()
        if not cookies:
            return "无 cookies"
        result = [f"Cookies ({len(cookies)} 个):\n"]
        for c in cookies[:20]:
            result.append(f"  {c['name']}: {c['value'][:50]}  (domain: {c.get('domain', '-')})")
        return '\n'.join(result)

    def _set_cookie(self, args: str) -> str:
        try:
            cookie = json.loads(args.strip())
        except json.JSONDecodeError:
            return "错误：cookie 必须是 JSON 格式: {\"name\": \"...\", \"value\": \"...\", \"domain\": \"...\"}"
        page = self._require_page()
        page.context.add_cookies([cookie])
        return f" 已设置 cookie: {cookie.get('name', '?')}"

    def _viewport(self, args: str) -> str:
        parts = args.strip().split()
        if len(parts) < 2:
            return "错误：格式: viewport <宽> <高>"
        try:
            w, h = int(parts[0]), int(parts[1])
        except ValueError:
            return "错误：宽高必须是整数"
        page = self._require_page()
        page.set_viewport_size({"width": w, "height": h})
        return f" 视口已设置: {w}×{h}"

    def _download(self, args: str) -> str:
        parts = args.strip().split()
        if not parts:
            return "错误：格式: download <URL> [保存路径]"
        url = parts[0]
        save_path = parts[1] if len(parts) > 1 else os.path.basename(url) or "download"
        page = self._require_page()
        try:
            with page.expect_download() as download_info:
                page.evaluate(f"window.open('{url}')")
            download = download_info.value
            download.save_as(save_path)
            size = os.path.getsize(save_path)
            return f" 已下载: {save_path} ({size/1024:.1f} KB)"
        except Exception as e:
            return f" 下载失败: {e}"
