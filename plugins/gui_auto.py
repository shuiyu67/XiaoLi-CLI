"""
Windows GUI 自动化插件 - 屏幕元素识别与控制
基于 Windows UI Automation (UIA)，获取屏幕 UI 元素树并自动操控桌面应用
支持：元素发现、点击、输入、截图、元素树遍历、窗口管理
"""

import os
import sys
import json
import time
from typing import Optional, List, Dict, Any

# ── 平台检测 ──
IS_WINDOWS = sys.platform == "win32"


class Plugin:
    """Windows GUI 自动化 - 屏幕元素识别、点击、输入、截图、元素树遍历"""

    def __init__(self):
        self.usage = """Windows GUI 自动化工具

屏幕信息:
  snapshot [深度]              - 获取屏幕 UI 元素树 (默认深度 5)
  snapshot --window <标题>     - 获取指定窗口的元素树
  screenshot [路径]            - 全屏截图 (默认 gui_screenshot.png)
  windows                      - 列出所有顶层窗口
  focus <窗口标题>             - 聚焦指定窗口

元素操作:
  click <名称>                 - 点击元素 (支持模糊匹配)
  click --xy <x> <y>          - 点击屏幕坐标
  rightclick <名称>            - 右键点击元素
  doubleclick <名称>           - 双击元素
  type <名称> <文本>           - 在元素中输入文本
  clear <名称>                 - 清空输入框
  keys <按键序列>              - 发送按键 (如: keys ctrl+a, keys enter)
  scroll <方向> [数量]         - 滚动 (up/down/left/right)

元素查询:
  find <名称>                  - 查找元素 (返回位置和属性)
  findall <名称>               - 查找所有匹配元素
  info <名称>                  - 获取元素详细信息
  value <名称>                 - 获取元素的值
  tree <名称> [深度]           - 以某元素为根的子树

高级:
  wait <名称> [超时秒数]       - 等待元素出现
  exists <名称>                - 检查元素是否存在
  highlight <名称>             - 高亮闪烁元素 (视觉定位)
  state <名称>                 - 获取元素状态 (enabled/visible/focused等)
"""
        self.cli = None
        self._uia = None
        self._root = None
        self._comtypes = None
        self._pyautogui = None

    def set_cli(self, cli):
        self.cli = cli

    def get_tool_info(self):
        return {
            "name": "gui_auto",
            "description": "Windows GUI 自动化 - 屏幕UI元素识别、点击、输入、截图、元素树遍历、桌面应用操控",
            "keywords": ["GUI", "屏幕", "桌面", "窗口", "控件", "点击", "输入",
                         "自动化", "UIA", "Windows", "截图", "元素", "按钮",
                         "菜单", "桌面应用", "桌面自动化", "computer use", "UI"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "gui_auto",
            "description": "Windows GUI 自动化工具，可识别和操控屏幕上的 UI 元素，获取元素树，执行点击/输入/按键等操作",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "操作类型",
                        "enum": ["snapshot", "screenshot", "windows", "focus",
                                 "click", "rightclick", "doubleclick", "type",
                                 "clear", "keys", "scroll", "find", "findall",
                                 "info", "value", "tree", "wait", "exists",
                                 "highlight", "state"]
                    },
                    "target": {"type": "string", "description": "目标元素名称"},
                    "value": {"type": "string", "description": "输入的文本"},
                    "x": {"type": "integer", "description": "X 坐标"},
                    "y": {"type": "integer", "description": "Y 坐标"},
                    "path": {"type": "string", "description": "保存路径"},
                    "depth": {"type": "integer", "description": "遍历深度"}
                },
                "required": ["operation"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        target = arguments.get("target", "")
        value = arguments.get("value", "")
        x = arguments.get("x")
        y = arguments.get("y")
        depth = arguments.get("depth")

        parts = [op]
        if x is not None and y is not None:
            parts.append(f"--xy {x} {y}")
        elif target:
            parts.append(target)
        if value:
            parts.append(value)
        if depth is not None and op == "snapshot":
            parts = [op, str(depth)]
            if target:
                parts.extend(["--window", target])
        return " ".join(str(p) for p in parts)

    # ══════════════════════════════════════════════
    #  路由分发
    # ══════════════════════════════════════════════

    def handle(self, args: str) -> str:
        try:
            parts = args.strip().split(maxsplit=1)
            if not parts:
                return "错误：请提供操作类型"

            op = parts[0].lower()
            rest = parts[1] if len(parts) > 1 else ""

            handlers = {
                "snapshot": self._snapshot,
                "screenshot": self._screenshot,
                "windows": self._list_windows,
                "focus": self._focus_window,
                "click": self._click,
                "rightclick": self._rightclick,
                "doubleclick": self._doubleclick,
                "type": self._type,
                "clear": self._clear,
                "keys": self._keys,
                "scroll": self._scroll,
                "find": self._find,
                "findall": self._findall,
                "info": self._info,
                "value": self._value,
                "tree": self._tree,
                "wait": self._wait,
                "exists": self._exists,
                "highlight": self._highlight,
                "state": self._state,
            }

            handler = handlers.get(op)
            if not handler:
                return f"错误：不支持的操作 '{op}'\n可用: {', '.join(handlers.keys())}"
            return handler(rest)

        except Exception as e:
            return f"GUI 自动化错误: {str(e)}"

    # ══════════════════════════════════════════════
    #  平台检查
    # ══════════════════════════════════════════════

    def _check_platform(self) -> Optional[str]:
        """检查是否在 Windows 平台，返回错误信息或 None"""
        if not IS_WINDOWS:
            return ("❌ 此插件仅支持 Windows 系统\n"
                    "  Windows UI Automation 是 Windows 专有 API\n"
                    "  其他平台请使用 browser_auto 插件进行网页自动化")
        return None

    # ══════════════════════════════════════════════
    #  UIA 初始化
    # ══════════════════════════════════════════════

    def _ensure_uia(self) -> bool:
        """确保 UIA COM 接口已初始化"""
        if self._uia is not None:
            return True

        err = self._check_platform()
        if err:
            return False

        try:
            import comtypes
            import comtypes.client
            self._comtypes = comtypes

            # IUIAutomation CLSID
            self._uia = comtypes.client.CreateObject(
                "{ff48dba4-60ef-4201-aa87-54103eef594e}",
                interface=comtypes.gen.UIAutomationClient.IUIAutomation
            )
            self._root = self._uia.GetRootElement()
            return True
        except ImportError:
            return False
        except Exception:
            return False

    def _ensure_pyautogui(self):
        """确保 pyautogui 可用，返回模块或 None"""
        if self._pyautogui is not None:
            return self._pyautogui

        try:
            import pyautogui
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.05
            self._pyautogui = pyautogui
            return pyautogui
        except ImportError:
            return None

    def _uia_error(self) -> str:
        """返回 UIA 初始化失败的错误信息"""
        err = self._check_platform()
        if err:
            return err

        missing = []
        try:
            import comtypes
        except ImportError:
            missing.append("comtypes")
        try:
            import pyautogui
        except ImportError:
            missing.append("pyautogui")

        if missing:
            return (f"缺少依赖: {', '.join(missing)}\n"
                    f"安装: pip install {' '.join(missing)}")
        return "UI Automation 初始化失败，请确认在 Windows 环境下运行"

    # ══════════════════════════════════════════════
    #  元素遍历核心
    # ══════════════════════════════════════════════

    def _element_to_dict(self, element, include_ref=False) -> Optional[Dict[str, Any]]:
        """将 UIA 元素转换为字典"""
        try:
            name = element.CurrentName or ""
            ctrl_type = element.CurrentLocalizedControlType or ""
            automation_id = element.CurrentAutomationId or ""
            class_name = element.CurrentClassName or ""
            is_enabled = element.CurrentIsEnabled
            has_focus = element.CurrentHasKeyboardFocus

            try:
                rect = element.CurrentBoundingRectangle
                bounds = {
                    "left": int(rect.left), "top": int(rect.top),
                    "right": int(rect.right), "bottom": int(rect.bottom),
                    "width": int(rect.right - rect.left),
                    "height": int(rect.bottom - rect.top)
                }
            except Exception:
                bounds = None

            # 尝试读取 ValuePattern
            value = ""
            try:
                vp = element.GetCurrentPattern(0xA)  # ValuePattern
                if vp:
                    value = vp.CurrentValue or ""
            except Exception:
                pass

            result = {
                "name": name, "type": ctrl_type,
                "automation_id": automation_id, "class": class_name,
                "enabled": is_enabled, "focused": has_focus,
                "bounds": bounds,
            }
            if value:
                result["value"] = value
            if include_ref:
                result["_element"] = element
            return result
        except Exception:
            return None

    def _walk_tree(self, element, depth=0, max_depth=5, prefix="") -> str:
        """遍历元素树，返回格式化字符串"""
        if element is None or depth > max_depth:
            return ""

        lines = []
        self._walk_recursive(element, depth, max_depth, prefix, lines)
        return "\n".join(lines)

    def _walk_recursive(self, element, depth, max_depth, prefix, lines):
        """递归遍历元素树"""
        if depth > max_depth:
            return
        try:
            info = self._element_to_dict(element)
            if not info:
                return

            indent = "  " * depth
            name_part = f'"{info["name"]}"' if info["name"] else "(无名)"
            type_part = f'[{info["type"]}]' if info["type"] else ""
            id_part = f' id={info["automation_id"]}' if info["automation_id"] else ""

            bounds_part = ""
            if info.get("bounds"):
                b = info["bounds"]
                bounds_part = f' @({b["left"]},{b["top"]},{b["width"]}x{b["height"]})'

            state_parts = []
            if info.get("focused"):
                state_parts.append("FOCUSED")
            if not info.get("enabled", True):
                state_parts.append("DISABLED")
            state_str = f' {" ".join(state_parts)}' if state_parts else ""

            lines.append(f"{indent}{prefix}{type_part} {name_part}{id_part}{bounds_part}{state_str}")

            children = element.FindAll(
                self._uia.CreatePropertyCondition(30000, 0),  # TreeScope_Children
                self._uia.CreateTrueCondition()
            )
            if children:
                count = min(children.Length, 50)  # 限制单层最多 50 个子元素
                for i in range(count):
                    child = children.GetElement(i)
                    self._walk_recursive(child, depth + 1, max_depth, f"[{i}] ", lines)
        except Exception:
            pass

    def _find_elements_by_name(self, name: str, root=None, max_results=20) -> List[Dict]:
        """通过名称查找元素（支持模糊匹配）"""
        if not self._ensure_uia():
            return []
        if root is None:
            root = self._root

        results = []
        name_lower = name.lower()
        self._search_recursive(root, name_lower, results, max_results, 0, 8)
        return results

    def _search_recursive(self, element, name_lower, results, max_results, depth, max_depth):
        """递归搜索元素"""
        if depth > max_depth or len(results) >= max_results:
            return
        try:
            el_name = (element.CurrentName or "").lower()
            el_aid = (element.CurrentAutomationId or "").lower()

            if name_lower in el_name or name_lower in el_aid:
                info = self._element_to_dict(element, include_ref=True)
                if info:
                    results.append(info)

            children = element.FindAll(
                self._uia.CreatePropertyCondition(30000, 0),
                self._uia.CreateTrueCondition()
            )
            if children:
                for i in range(min(children.Length, 100)):
                    child = children.GetElement(i)
                    self._search_recursive(child, name_lower, results, max_results, depth + 1, max_depth)
        except Exception:
            pass

    def _find_element_by_name(self, name: str) -> Optional[Dict]:
        """查找单个元素，精确匹配优先"""
        results = self._find_elements_by_name(name)
        if not results:
            return None
        # 精确匹配优先
        for r in results:
            if r.get("name", "").lower() == name.lower():
                return r
        return results[0]

    def _click_at(self, x: int, y: int, button="left", clicks=1, label="") -> str:
        """通过坐标点击"""
        pg = self._ensure_pyautogui()
        if not pg:
            return "错误：未安装 pyautogui。运行: pip install pyautogui"

        try:
            if button == "left":
                pg.click(x, y, clicks=clicks)
            elif button == "right":
                pg.rightClick(x, y)
            else:
                pg.click(x, y, clicks=clicks, button=button)

            btn = "左键" if button == "left" else "右键"
            act = "双击" if clicks == 2 else "点击"
            label_str = f' "{label}"' if label else ""
            return f"✅ {act}{label_str} @ ({x}, {y})"
        except Exception as e:
            return f"❌ 点击失败: {e}"

    def _click_element(self, el_info: Dict, button="left", clicks=1) -> str:
        """点击元素（自动计算中心坐标）"""
        bounds = el_info.get("bounds")
        if not bounds:
            return f"❌ 元素 '{el_info.get('name')}' 没有位置信息"

        cx = (bounds["left"] + bounds["right"]) // 2
        cy = (bounds["top"] + bounds["bottom"]) // 2
        return self._click_at(cx, cy, button, clicks, el_info.get("name", ""))

    def _format_element_info(self, el: Dict, detailed=False) -> str:
        """格式化元素信息"""
        lines = []
        lines.append(f'  名称: "{el.get("name", "(无名)")}"')
        lines.append(f'  类型: {el.get("type", "未知")}')
        lines.append(f'  类名: {el.get("class", "未知")}')
        if el.get("automation_id"):
            lines.append(f'  自动化ID: {el["automation_id"]}')
        bounds = el.get("bounds")
        if bounds:
            lines.append(f'  位置: ({bounds["left"]}, {bounds["top"]})')
            lines.append(f'  大小: {bounds["width"]} x {bounds["height"]}')
        if el.get("value"):
            lines.append(f'  值: {el["value"]}')
        lines.append(f'  启用: {"是" if el.get("enabled", True) else "否"}')
        lines.append(f'  聚焦: {"是" if el.get("focused") else "否"}')

        if detailed and el.get("_element"):
            element = el["_element"]
            for attr, label in [
                ("CurrentHelpText", "帮助文本"),
                ("CurrentAccessKey", "访问键"),
                ("CurrentAcceleratorKey", "快捷键"),
            ]:
                try:
                    val = getattr(element, attr, None)
                    if val:
                        lines.append(f'  {label}: {val}')
                except Exception:
                    pass

            # 支持的 Pattern
            patterns = []
            pattern_ids = {
                0: "Invoke", 1: "Selection", 2: "Value", 3: "RangeValue",
                5: "Scroll", 6: "ExpandCollapse", 7: "Grid", 8: "GridItem",
                9: "MultipleView", 10: "Window", 11: "SelectionItem",
                12: "Dock", 13: "Table", 14: "TableItem", 15: "Text",
                16: "Toggle", 17: "Transform", 18: "ScrollItem"
            }
            for pid, pname in pattern_ids.items():
                try:
                    element.GetCurrentPattern(pid)
                    patterns.append(pname)
                except Exception:
                    pass
            if patterns:
                lines.append(f'  支持模式: {", ".join(patterns)}')

        return "\n".join(lines)

    def _type_unicode(self, text: str):
        """输入 Unicode 文本（中文等）"""
        import ctypes
        import ctypes.wintypes

        INPUT_KEYBOARD = 1
        KEYEVENTF_UNICODE = 0x0004
        KEYEVENTF_KEYUP = 0x0002

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", ctypes.wintypes.WORD),
                ("wScan", ctypes.wintypes.WORD),
                ("dwFlags", ctypes.wintypes.DWORD),
                ("time", ctypes.wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
            ]

        class INPUT(ctypes.Structure):
            _fields_ = [("type", ctypes.wintypes.DWORD), ("ki", KEYBDINPUT)]

        for char in text:
            for flags in [KEYEVENTF_UNICODE, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP]:
                inp = INPUT(type=INPUT_KEYBOARD)
                inp.ki.wScan = ord(char)
                inp.ki.dwFlags = flags
                ctypes.windll.user32.SendInput(
                    1, ctypes.byref(inp), ctypes.sizeof(INPUT)
                )
            time.sleep(0.02)

    # ══════════════════════════════════════════════
    #  操作实现
    # ══════════════════════════════════════════════

    def _snapshot(self, args: str) -> str:
        """获取屏幕元素树"""
        if not self._ensure_uia():
            return self._uia_error()

        parts = args.strip().split() if args.strip() else []
        max_depth = 5
        window_title = None

        i = 0
        while i < len(parts):
            if parts[i] == "--window" and i + 1 < len(parts):
                window_title = parts[i + 1]
                i += 2
            elif parts[i].isdigit():
                max_depth = int(parts[i])
                i += 1
            else:
                i += 1

        try:
            if window_title:
                condition = self._uia.CreatePropertyCondition(30005, window_title)
                windows = self._root.FindAll(
                    self._uia.CreatePropertyCondition(30000, 2), condition
                )
                if windows.Length == 0:
                    return f"❌ 未找到窗口: {window_title}"
                element = windows.GetElement(0)
            else:
                element = self._root

            tree_str = self._walk_tree(element, max_depth=max_depth)
            header = f"📍 屏幕 UI 元素树 (深度={max_depth})"
            if window_title:
                header += f" - 窗口: {window_title}"

            line_count = len([l for l in tree_str.strip().split("\n") if l.strip()]) if tree_str.strip() else 0
            return f"{header}\n{'=' * 60}\n{tree_str}\n{'=' * 60}\n共 {line_count} 个元素"

        except Exception as e:
            return f"❌ 获取元素树失败: {e}"

    def _screenshot(self, args: str) -> str:
        """全屏截图"""
        err = self._check_platform()
        if err:
            return err

        try:
            from PIL import ImageGrab
        except ImportError:
            return "❌ 需要 Pillow。运行: pip install Pillow"

        path = args.strip() if args.strip() else "gui_screenshot.png"
        try:
            screenshot = ImageGrab.grab()
            screenshot.save(path)
            w, h = screenshot.size
            size_kb = os.path.getsize(path) / 1024
            return f"✅ 截图已保存: {path} ({w}x{h}, {size_kb:.1f} KB)"
        except Exception as e:
            return f"❌ 截图失败: {e}"

    def _list_windows(self, args: str) -> str:
        """列出所有顶层窗口"""
        if not self._ensure_uia():
            return self._uia_error()

        try:
            children = self._root.FindAll(
                self._uia.CreatePropertyCondition(30000, 2),
                self._uia.CreateTrueCondition()
            )

            windows = []
            for i in range(children.Length):
                el = children.GetElement(i)
                try:
                    name = el.CurrentName or "(无标题)"
                    ctrl_type = el.CurrentLocalizedControlType or ""
                    class_name = el.CurrentClassName or ""
                    rect = el.CurrentBoundingRectangle
                    bounds = f"({rect.left},{rect.top},{rect.right - rect.left}x{rect.bottom - rect.top})"
                    windows.append(f"  [{i}] [{ctrl_type}] \"{name}\" class={class_name} {bounds}")
                except Exception:
                    continue

            if not windows:
                return "📍 未找到任何窗口"
            return f"📍 顶层窗口 (共 {len(windows)} 个)\n{'=' * 60}\n" + "\n".join(windows)

        except Exception as e:
            return f"❌ 列出窗口失败: {e}"

    def _focus_window(self, args: str) -> str:
        """聚焦窗口"""
        title = args.strip()
        if not title:
            return "❌ 请提供窗口标题"

        if not self._ensure_uia():
            return self._uia_error()

        try:
            condition = self._uia.CreatePropertyCondition(30005, title)
            windows = self._root.FindAll(
                self._uia.CreatePropertyCondition(30000, 2), condition
            )
            if windows.Length == 0:
                return f"❌ 未找到窗口: {title}"

            window = windows.GetElement(0)
            rect = window.CurrentBoundingRectangle

            # 使用 Win32 API 设置焦点
            try:
                import ctypes
                import ctypes.wintypes
                hwnd = ctypes.windll.user32.WindowFromPoint(
                    ctypes.wintypes.POINT(rect.left + 10, rect.top + 10)
                )
                if hwnd:
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            except Exception:
                # 备用方案：点击标题栏
                pg = self._ensure_pyautogui()
                if pg:
                    pg.click(rect.left + (rect.right - rect.left) // 2, rect.top + 10)

            return f"✅ 已聚焦窗口: \"{title}\""

        except Exception as e:
            return f"❌ 聚焦失败: {e}"

    def _click(self, args: str) -> str:
        """点击元素"""
        args = args.strip()

        # --xy 模式
        if args.startswith("--xy"):
            parts = args.split()
            if len(parts) >= 3:
                try:
                    x, y = int(parts[1]), int(parts[2])
                    return self._click_at(x, y, "left", 1)
                except ValueError:
                    return "❌ 坐标格式: click --xy <x> <y>"
            return "❌ 格式: click --xy <x> <y>"

        if not args:
            return "❌ 请提供元素名称或 --xy <x> <y>"

        if not self._ensure_uia():
            return self._uia_error()

        el = self._find_element_by_name(args)
        if not el:
            return f"❌ 未找到元素: {args}"
        return self._click_element(el, "left", 1)

    def _rightclick(self, args: str) -> str:
        """右键点击"""
        name = args.strip()
        if not name:
            return "❌ 请提供元素名称"
        if not self._ensure_uia():
            return self._uia_error()

        el = self._find_element_by_name(name)
        if not el:
            return f"❌ 未找到元素: {name}"
        return self._click_element(el, "right", 1)

    def _doubleclick(self, args: str) -> str:
        """双击"""
        name = args.strip()
        if not name:
            return "❌ 请提供元素名称"
        if not self._ensure_uia():
            return self._uia_error()

        el = self._find_element_by_name(name)
        if not el:
            return f"❌ 未找到元素: {name}"
        return self._click_element(el, "left", 2)

    def _type(self, args: str) -> str:
        """在元素中输入文本"""
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            return "❌ 格式: type <元素名称> <文本>"

        name, text = parts[0], parts[1]
        if not self._ensure_uia():
            return self._uia_error()

        el = self._find_element_by_name(name)
        if not el:
            return f"❌ 未找到元素: {name}"

        # 尝试 ValuePattern 直接设置值
        element = el.get("_element")
        if element:
            try:
                vp = element.GetCurrentPattern(0xA)  # ValuePattern
                if vp:
                    vp.SetValue(text)
                    return f'✅ 已输入 "{text}" → "{name}" (ValuePattern)'
            except Exception:
                pass

        # 备用方案：聚焦 + pyautogui 输入
        self._click_element(el, "left", 1)
        time.sleep(0.15)

        pg = self._ensure_pyautogui()
        if not pg:
            return "❌ 需要 pyautogui。运行: pip install pyautogui"

        try:
            if text.isascii():
                pg.typewrite(text, interval=0.02)
            else:
                self._type_unicode(text)
            return f'✅ 已输入 "{text}" → "{name}"'
        except Exception as e:
            return f"❌ 输入失败: {e}"

    def _clear(self, args: str) -> str:
        """清空输入框"""
        name = args.strip()
        if not name:
            return "❌ 请提供元素名称"
        if not self._ensure_uia():
            return self._uia_error()

        el = self._find_element_by_name(name)
        if not el:
            return f"❌ 未找到元素: {name}"

        # 尝试 ValuePattern 清空
        element = el.get("_element")
        if element:
            try:
                vp = element.GetCurrentPattern(0xA)
                if vp:
                    vp.SetValue("")
                    return f'✅ 已清空: "{name}" (ValuePattern)'
            except Exception:
                pass

        # 备用方案：Ctrl+A + Delete
        self._click_element(el, "left", 1)
        time.sleep(0.1)

        pg = self._ensure_pyautogui()
        if not pg:
            return "❌ 需要 pyautogui"

        try:
            pg.hotkey('ctrl', 'a')
            time.sleep(0.05)
            pg.press('delete')
            return f'✅ 已清空: "{name}"'
        except Exception as e:
            return f"❌ 清空失败: {e}"

    def _keys(self, args: str) -> str:
        """发送按键"""
        keys_str = args.strip()
        if not keys_str:
            return "❌ 请提供按键。格式: keys ctrl+a, keys enter, keys alt+f4"

        pg = self._ensure_pyautogui()
        if not pg:
            return "❌ 需要 pyautogui。运行: pip install pyautogui"

        try:
            for combo in keys_str.split(","):
                combo = combo.strip()
                if not combo:
                    continue
                parts = combo.lower().split("+")
                if len(parts) > 1:
                    pg.hotkey(*parts)
                else:
                    pg.press(parts[0])
            return f"✅ 已发送按键: {keys_str}"
        except Exception as e:
            return f"❌ 按键发送失败: {e}"

    def _scroll(self, args: str) -> str:
        """滚动"""
        parts = args.strip().split()
        direction = parts[0] if parts else "down"
        amount = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 3

        pg = self._ensure_pyautogui()
        if not pg:
            return "❌ 需要 pyautogui。运行: pip install pyautogui"

        try:
            if direction == "down":
                pg.scroll(-amount * 3)
            elif direction == "up":
                pg.scroll(amount * 3)
            elif direction == "left":
                pg.hscroll(-amount * 3)
            elif direction == "right":
                pg.hscroll(amount * 3)
            else:
                return f"❌ 不支持的方向 '{direction}'。可用: up/down/left/right"
            return f"✅ 已滚动 {direction} x{amount}"
        except Exception as e:
            return f"❌ 滚动失败: {e}"

    def _find(self, args: str) -> str:
        """查找元素"""
        name = args.strip()
        if not name:
            return "❌ 请提供元素名称"
        if not self._ensure_uia():
            return self._uia_error()

        el = self._find_element_by_name(name)
        if not el:
            return f"❌ 未找到元素: {name}"
        return f"✅ 找到元素:\n{self._format_element_info(el)}"

    def _findall(self, args: str) -> str:
        """查找所有匹配元素"""
        name = args.strip()
        if not name:
            return "❌ 请提供元素名称"
        if not self._ensure_uia():
            return self._uia_error()

        elements = self._find_elements_by_name(name)
        if not elements:
            return f"❌ 未找到匹配 \"{name}\" 的元素"

        result = f"✅ 找到 {len(elements)} 个匹配元素:\n{'=' * 50}\n"
        for i, el in enumerate(elements):
            result += f"\n[{i}] {self._format_element_info(el)}\n"
        return result

    def _info(self, args: str) -> str:
        """获取元素详细信息"""
        name = args.strip()
        if not name:
            return "❌ 请提供元素名称"
        if not self._ensure_uia():
            return self._uia_error()

        el = self._find_element_by_name(name)
        if not el:
            return f"❌ 未找到元素: {name}"
        return f"✅ 元素信息:\n{self._format_element_info(el, detailed=True)}"

    def _value(self, args: str) -> str:
        """获取元素的值"""
        name = args.strip()
        if not name:
            return "❌ 请提供元素名称"
        if not self._ensure_uia():
            return self._uia_error()

        el = self._find_element_by_name(name)
        if not el:
            return f"❌ 未找到元素: {name}"

        element = el.get("_element")
        if not element:
            return "❌ 无法获取元素引用"

        # ValuePattern
        try:
            vp = element.GetCurrentPattern(0xA)
            if vp:
                return f"值: {vp.CurrentValue}"
        except Exception:
            pass

        # TextPattern
        try:
            tp = element.GetCurrentPattern(0x1E)
            if tp:
                return f"文本: {tp.DocumentRange.GetText(-1)}"
        except Exception:
            pass

        val = el.get("value", "")
        if val:
            return f"值: {val}"
        return f"元素 \"{name}\" 没有可读取的值"

    def _tree(self, args: str) -> str:
        """以某元素为根的子树"""
        parts = args.strip().split() if args.strip() else []
        name = parts[0] if parts else ""
        depth = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 3

        if not name:
            return "❌ 请提供元素名称"
        if not self._ensure_uia():
            return self._uia_error()

        el = self._find_element_by_name(name)
        if not el:
            return f"❌ 未找到元素: {name}"

        element = el.get("_element")
        if not element:
            return "❌ 无法获取元素引用"

        tree_str = self._walk_tree(element, max_depth=depth)
        return f"📍 元素 \"{name}\" 的子树 (深度={depth}):\n{'=' * 50}\n{tree_str}"

    def _wait(self, args: str) -> str:
        """等待元素出现"""
        parts = args.strip().split()
        if not parts:
            return "❌ 请提供元素名称"
        name = parts[0]
        timeout = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10

        if not self._ensure_uia():
            return self._uia_error()

        start_time = time.time()
        while time.time() - start_time < timeout:
            el = self._find_element_by_name(name)
            if el:
                elapsed = time.time() - start_time
                return f"✅ 元素 \"{name}\" 已出现 ({elapsed:.1f}s)"
            time.sleep(0.5)

        return f"⏰ 超时：等待 {timeout}s 后仍未找到 \"{name}\""

    def _exists(self, args: str) -> str:
        """检查元素是否存在"""
        name = args.strip()
        if not name:
            return "❌ 请提供元素名称"
        if not self._ensure_uia():
            return self._uia_error()

        el = self._find_element_by_name(name)
        if el:
            bounds = el.get("bounds", {})
            return f'✅ 存在: "{name}" [{el.get("type", "")}] @({bounds.get("left",0)},{bounds.get("top",0)})'
        return f'❌ 不存在: "{name}"'

    def _highlight(self, args: str) -> str:
        """高亮闪烁元素"""
        name = args.strip()
        if not name:
            return "❌ 请提供元素名称"

        err = self._check_platform()
        if err:
            return err

        if not self._ensure_uia():
            return self._uia_error()

        el = self._find_element_by_name(name)
        if not el:
            return f"❌ 未找到元素: {name}"

        bounds = el.get("bounds")
        if not bounds:
            return f"❌ 元素 \"{name}\" 没有位置信息"

        try:
            import ctypes
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32
            hdc = user32.GetDC(0)

            pen = gdi32.CreatePen(0, 3, 0x0000FF)  # 红色实线
            old_pen = gdi32.SelectObject(hdc, pen)
            old_brush = gdi32.SelectObject(hdc, gdi32.GetStockObject(5))  # NULL_BRUSH

            x1, y1 = bounds["left"], bounds["top"]
            x2, y2 = bounds["right"], bounds["bottom"]

            for _ in range(3):
                gdi32.Rectangle(hdc, x1, y1, x2, y2)
                time.sleep(0.3)
                import ctypes.wintypes
                user32.InvalidateRect(
                    0, ctypes.byref(ctypes.wintypes.RECT(x1 - 2, y1 - 2, x2 + 2, y2 + 2)), True
                )
                user32.UpdateWindow(0)
                time.sleep(0.2)

            gdi32.SelectObject(hdc, old_pen)
            gdi32.SelectObject(hdc, old_brush)
            gdi32.DeleteObject(pen)
            user32.ReleaseDC(0, hdc)

            return f'✅ 高亮: "{name}" @({x1},{y1})-({x2},{y2})'
        except Exception as e:
            return f"❌ 高亮失败: {e}"

    def _state(self, args: str) -> str:
        """获取元素状态"""
        name = args.strip()
        if not name:
            return "❌ 请提供元素名称"
        if not self._ensure_uia():
            return self._uia_error()

        el = self._find_element_by_name(name)
        if not el:
            return f"❌ 未找到元素: {name}"

        element = el.get("_element")
        if not element:
            return "❌ 无法获取元素引用"

        states = []
        try:
            states.append("✅ enabled" if element.CurrentIsEnabled else "❌ disabled")
            if element.CurrentHasKeyboardFocus:
                states.append("🎯 focused")
            if element.CurrentIsKeyboardFocusable:
                states.append("⌨️ focusable")
        except Exception as e:
            return f"❌ 获取状态失败: {e}"

        return f' "{name}" 状态:\n' + "\n".join(f"  {s}" for s in states)
