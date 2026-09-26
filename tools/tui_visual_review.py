# -*- coding: utf-8 -*-
"""视觉审查：解剖 TUI 截图 SVG → 字符网格 + 色板对照 + opencode 规格清单逐项 PASS/FAIL"""
import re
import sys
from collections import Counter, defaultdict

CW, LH = 12.2, 24.4  # 字符宽 / 行高（rich SVG 导出常量）
X0, Y0 = 8.0, 20.0   # 首字符基线

GROUND = {
    "#121212": "主背景(会话)",
    "#000000": "纯黑(Home底/footer)",
    "#1c1c1c": "面板",
    "#272727": "边框",
    "#5b8def": "蓝accent(竖条/键帽)",
    "#d98d5f": "橙(Tip/点缀)",
    "#6e6e6e": "logo上段灰",
    "#f0f0f0": "logo下段白",
}


def parse(path):
    import html
    import unicodedata
    src = open(path, encoding="utf-8").read()
    fills = dict(re.findall(r"(r\d+) \{ fill: (#[0-9a-f]{6})", src))
    fills = {k: v.lower() for k, v in fills.items()}
    # 文本网格（实体解码 + 东亚双宽字符占 2 列）
    grid = {}
    colors = {}
    for m in re.finditer(r'<text class="[^"]*-?(r\d+)" x="([\d.]+)" y="([\d.]+)"[^>]*>([^<]*)</text>', src):
        cls, x, y, txt = m.group(1), float(m.group(2)), float(m.group(3)), m.group(4)
        txt = html.unescape(txt)
        if not txt or cls not in fills:
            continue
        row = round((y - Y0) / LH)
        col = round((x - X0) / CW)
        for ch in txt:
            grid[(row, col)] = ch
            colors[(row, col)] = fills[cls]
            wide = unicodedata.east_asian_width(ch) in ("W", "F") or ord(ch) > 0x1F000
            col += 2 if wide else 1
    # 背景 rect 覆盖统计
    bg = Counter()
    for m in re.finditer(r'<rect [^>]*fill="(#[0-9a-f]{6})"', src):
        bg[m.group(1).lower()] += 1
    fg = Counter(colors.values())
    return grid, colors, fg, bg


def rows_of(grid, maxcol=120):
    if not grid:
        return []
    maxr = max(r for r, _ in grid)
    out = []
    for r in range(maxr + 1):
        line = "".join(grid.get((r, c), " ") for c in range(maxcol)).rstrip()
        out.append(line)
    return out


def flat_rows(grid):
    """紧凑文本行（不含双宽字符的占位空格）——供子串匹配用"""
    by_row = defaultdict(list)
    for (r, c), ch in grid.items():
        by_row[r].append((c, ch))
    out = []
    for r in sorted(by_row):
        out.append("".join(ch for _, ch in sorted(by_row[r])))
    return out


def check(name, cond, note=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  ← {note}" if note and not cond else ""))
    return cond


def main():
    results = {}
    for tag in ("home", "session", "palette", "leader"):
        path = f"tui_v_{tag}.svg"
        grid, colors, fg, bg = parse(path)
        # 文字依据 = ANSI 文本导出（终端真实字符；rich SVG 序列化会丢部分 CJK）
        rows = open(f"tui_v_{tag}.txt", encoding="utf-8").read().splitlines()
        flat = [ln.rstrip() for ln in rows]
        text_all = "\n".join(flat)
        results[tag] = (rows, colors, fg, bg, text_all)

        print(f"\n{'='*76}\n## {tag.upper()} 屏：字符网格（终端真实所见）\n{'='*76}")
        show = rows if tag in ("home", "session") else rows[:18]
        for i, ln in enumerate(show):
            print(f"{i:2d}|{ln}")

        print(f"  -- 前景色覆盖(字符数): {dict(fg.most_common(10))}")
        print(f"  -- 背景rect: {dict(bg)}")

    fails = 0
    print(f"\n{'='*76}\n## 规格清单（opencode ground truth 逐项核对）\n{'='*76}")

    rows_h, colors_h, fg_h, bg_h, t_h = results["home"]
    print("[Home 屏]")
    fails += not check("像素 logo 双色调(█ 块，#6e6e6e 上段 + #f0f0f0 下段)",
                       fg_h.get("#6e6e6e", 0) > 30 and fg_h.get("#f0f0f0", 0) > 30 and any("█" in r for r in rows_h))
    fails += not check("品牌/版本 tagline", "小狸" in t_h and "v8.0.4" in t_h)
    fails += not check("键帽提示行(键亮/标签暗: ctrl+t/tab/ctrl+p)",
                       "ctrl+t" in t_h and "tab" in t_h and "ctrl+p" in t_h and fg_h.get("#d4d4d4", 0) > 0)
    fails += not check("橙色 ● Tip 行", "Tip" in t_h and fg_h.get("#d98d5f", 0) > 3)
    fails += not check("composer 蓝竖条(#5b8def rect)", bg_h.get("#5b8def", 0) >= 1)
    fails += not check("composer 盒内状态行(Build/模型/来源)", "Build" in t_h and ("本地" in t_h or "云端" in t_h or "openai" in t_h))
    fails += not check("Home 纯黑底(#000000 主导)", bg_h.get("#000000", 0) > bg_h.get("#121212", 0))

    rows_s, colors_s, fg_s, bg_s, t_s = results["session"]
    print("[会话屏]")
    fails += not check("用户消息带 You · 时间 meta", "You" in t_s and ":" in t_s)
    fails += not check("用户消息蓝竖条(#5b8def rect 在消息区)", bg_s.get("#5b8def", 0) >= 1)
    fails += not check("AI markdown: 标题渲染(修复方案)", "修复方案" in t_s)
    fails += not check("代码块渲染(多色语法高亮)", fg_s.get("#5b8def", 0) > 0 and len([c for c in fg_s if fg_s[c] > 3]) >= 5)
    fails += not check("工具行 InlineToolRow(⚙ + ✓)", ("⚙" in t_s) and ("✓" in t_s))
    fails += not check("侧栏分节(会话/文件/引擎/状态)", all(k in t_s for k in ("会话", "文件", "引擎", "状态")))
    fails += not check("footer 纯黑 + 模型名", bg_s.get("#000000", 0) > 0 and "openai" in t_s)
    fails += not check("无 GitHub 蓝黑残留(#0d1117/#58a6ff 等)",
                       not any(c in ("#0d1117", "#58a6ff", "#30363d", "#c9d1d9", "#8b949e") for c in list(fg_s) + list(bg_s)))

    rows_p, colors_p, fg_p, bg_p, t_p = results["palette"]
    print("[命令面板]")
    fails += not check("标题行", "命令面板" in t_p)
    fails += not check("搜索输入", "搜索" in t_p or "模糊" in t_p)
    fails += not check("列表行带类型标记(›/⚙/◈/≡)", any(m in t_p for m in ("›", "⚙", "◈", "≡")))
    fails += not check("选中高亮实色块", bg_p.get("#26456b", 0) >= 1 or bg_p.get("#5b8def", 0) >= 1)

    rows_l, colors_l, fg_l, bg_l, t_l = results["leader"]
    print("[leader chord]")
    fails += not check("chord 提示(ctrl+x)", "ctrl+x" in t_l)
    fails += not check("chord 项(新会话/模型/退出)", "新会话" in t_l and "模型" in t_l)

    print("[全局视觉纪律]")
    import re as _re
    emoji_pat = _re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u2705\u274C\u274E\u2611\u2610\u2714\u2718]")
    # ✓✗›⚙◈≡❯● 属设计符号（允许）；只禁彩色 emoji
    emoji_pat = _re.compile("[\U0001F000-\U0001FAFF\u2B00-\u2BFF\uFE0F\u2705\u274C\u274E]")
    for tag in ("home", "session", "palette", "leader"):
        t = results[tag][4]
        bad = sorted(set(emoji_pat.findall(t)))
        fails += not check(f"[{tag}] 无彩色 emoji", not bad, f"残留 {bad}")
    fails += not check("footer 无模型名重复", "openai openai" not in t_h and "openai openai" not in t_s)
    # 面板浮层：标题行应在上半（浮层居中），侧栏内容（文件名 marker）被遮
    pal_lines = [ln.rstrip() for ln in open("tui_v_palette.txt", encoding="utf-8").read().splitlines()]
    title_row = next((i for i, ln in enumerate(pal_lines) if "命令面板" in ln), 99)
    fails += not check("面板浮层居中(标题行 < 16)", title_row < 16, f"标题行在第 {title_row} 行")
    fails += not check("面板浮层覆盖全屏(侧栏被遮)", "capture_shots.py" not in t_p and "命令面板" in t_p)
    # Home 构图居中：logo 首个 █ 列位 > 20（120 列下居中而非贴左）
    h_lines = [ln.rstrip() for ln in open("tui_v_home.txt", encoding="utf-8").read().splitlines()]
    logo_cols = [ln.index("█") for ln in h_lines[:25] if "█" in ln]
    fails += not check("Home 居中构图(logo 列位 > 20)", bool(logo_cols) and min(logo_cols) > 20,
                       f"logo 起始列 {min(logo_cols) if logo_cols else '?'}")

    print(f"\n## 色板对照（全部 4 屏合计）")
    allc = Counter()
    for tag in results:
        _, _, fg, bg, _ = results[tag]
        allc.update(fg)
        allc.update(bg)
    for c, n in allc.most_common(20):
        tagv = GROUND.get(c, "")
        print(f"  {c}  ×{n:<5} {tagv}")
    unknown = [c for c in allc if c not in GROUND and allc[c] > 5]
    if unknown:
        print(f"  非基准色(>5): {unknown}")

    print(f"\n结论: {'全部通过' if fails == 0 else str(fails) + ' 项 FAIL'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
