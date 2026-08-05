"""TUI 深度功能测试：文件树 / 会话相对时间 / Plan 状态（纯函数可测部分）"""
import os
import tempfile
from datetime import datetime, timedelta

import pytest

from xcli_core.tui import XiaoliTUI, TEXTUAL_AVAILABLE

pytestmark = pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual 未安装")


def test_build_file_tree_lists_dirs_and_files():
    with tempfile.TemporaryDirectory() as d:
        os.mkdir(os.path.join(d, "sub"))
        open(os.path.join(d, "a.py"), "w").close()
        open(os.path.join(d, "b.txt"), "w").close()
        items = XiaoliTUI._build_file_tree(d)
        names = [n for n, _ in items]
        assert "sub" in names and "a.py" in names and "b.txt" in names
        dirs = [n for n, is_dir in items if is_dir]
        assert "sub" in dirs


def test_build_file_tree_skips_noise():
    with tempfile.TemporaryDirectory() as d:
        os.mkdir(os.path.join(d, ".git"))
        os.mkdir(os.path.join(d, "__pycache__"))
        open(os.path.join(d, "real.py"), "w").close()
        items = XiaoliTUI._build_file_tree(d)
        names = [n for n, _ in items]
        assert ".git" not in names and "__pycache__" not in names
        assert "real.py" in names


def test_build_file_tree_max_items():
    with tempfile.TemporaryDirectory() as d:
        for i in range(100):
            open(os.path.join(d, f"f{i}.txt"), "w").close()
        items = XiaoliTUI._build_file_tree(d, max_items=10)
        assert any(n == "…" for n, _ in items)
        real = [n for n, _ in items if n != "…"]
        assert len(real) <= 10


def test_format_rel_time():
    now = datetime.now()
    assert "刚刚" in XiaoliTUI._format_rel_time(now.isoformat())
    assert "分钟前" in XiaoliTUI._format_rel_time((now - timedelta(minutes=5)).isoformat())
    assert "小时前" in XiaoliTUI._format_rel_time((now - timedelta(hours=3)).isoformat())
    assert "天前" in XiaoliTUI._format_rel_time((now - timedelta(days=2)).isoformat())
    assert XiaoliTUI._format_rel_time("") == ""


def test_tui_has_plan_and_sidebar_hooks():
    """TUI 深度接入点存在（方法/反应变量/侧栏节点 id）。"""
    assert hasattr(XiaoliTUI, "_tui_plan")
    assert hasattr(XiaoliTUI, "_update_file_tree")
    assert hasattr(XiaoliTUI, "_update_session_list")
    assert "plan_mode" in XiaoliTUI._reactives if hasattr(XiaoliTUI, "_reactives") else True
