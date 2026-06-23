"""终端模拟器 v2 测试"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from plugins.terminal import Liugin, Terminal


def test_basic_open_close():
    p = Liugin()
    r = p.handle("open")
    assert "已打开" in r
    r = p.handle("list")
    assert "main" in r
    r = p.handle("close")
    assert "已关闭" in r
    r = p.handle("list")
    assert "无终端" in r
    print("✓ test_basic_open_close")


def test_type_and_enter():
    p = Liugin()
    p.handle("open")
    p.handle("type echo hello_v2")
    p.handle("key enter")
    time.sleep(0.5)
    r = p.handle("read")
    assert "hello_v2" in r
    p.handle("close")
    print("✓ test_type_and_enter")


def test_last_n():
    p = Liugin()
    p.handle("open")
    for i in range(10):
        p.handle(f"type echo line_{i}")
        p.handle("key enter")
        time.sleep(0.15)
    time.sleep(0.5)
    r = p.handle("last 3")
    assert "line_9" in r
    # last 3 不应该包含 line_0
    assert "line_0" not in r
    p.handle("close")
    print("✓ test_last_n")


def test_read_shortcut():
    """read 5 等同 last 5"""
    p = Liugin()
    p.handle("open")
    p.handle("type echo aaa")
    p.handle("key enter")
    time.sleep(0.3)
    p.handle("type echo bbb")
    p.handle("key enter")
    time.sleep(0.3)
    r = p.handle("read 5")
    assert "bbb" in r
    p.handle("close")
    print("✓ test_read_shortcut")


def test_env_persist():
    p = Liugin()
    p.handle("open")
    p.handle("type export MYVAR=hello")
    p.handle("key enter")
    time.sleep(0.3)
    p.handle("type echo val=$MYVAR")
    p.handle("key enter")
    time.sleep(0.5)
    r = p.handle("read")
    assert "val=hello" in r
    p.handle("close")
    print("✓ test_env_persist")


def test_python_repl():
    p = Liugin()
    p.handle("open python3")
    time.sleep(1)
    p.handle("type print(2+3)")
    p.handle("key enter")
    time.sleep(0.5)
    r = p.handle("read")
    assert "5" in r
    p.handle("close")
    print("✓ test_python_repl")


def test_ctrl_c():
    p = Liugin()
    p.handle("open")
    p.handle("type python3 -c 'import time; time.sleep(99)'")
    p.handle("key enter")
    time.sleep(0.5)
    p.handle("key ctrl+c")
    time.sleep(0.3)
    # 终端应该还活着
    r = p.handle("list")
    assert "●" in r
    p.handle("close")
    print("✓ test_ctrl_c")


def test_multi_session():
    p = Liugin()
    p.handle("open")
    p.handle("open python3")
    r = p.handle("list")
    assert "main" in r
    assert "s2" in r
    p.handle("switch main")
    p.handle("type echo from_bash")
    p.handle("key enter")
    time.sleep(0.3)
    r = p.handle("read")
    assert "from_bash" in r
    p.handle("close s2")
    p.handle("close main")
    print("✓ test_multi_session")


def test_cwd():
    p = Liugin()
    p.handle("open")
    p.handle("type cd /tmp")
    p.handle("key enter")
    time.sleep(0.3)
    p.handle("type pwd")
    p.handle("key enter")
    time.sleep(0.5)
    r = p.handle("read")
    assert "/tmp" in r
    p.handle("close")
    print("✓ test_cwd")


def test_long_output():
    p = Liugin()
    p.handle("open")
    p.handle("type seq 1 100")
    p.handle("key enter")
    time.sleep(1)
    r = p.handle("last 5")
    assert "100" in r
    p.handle("close")
    print("✓ test_long_output")


def test_auto_create():
    """不 open 直接 type，自动创建终端"""
    p = Liugin()
    p.handle("type echo auto")
    p.handle("key enter")
    time.sleep(0.5)
    r = p.handle("read")
    assert "auto" in r
    p.handle("close")
    print("✓ test_auto_create")


if __name__ == "__main__":
    test_basic_open_close()
    test_type_and_enter()
    test_last_n()
    test_read_shortcut()
    test_env_persist()
    test_python_repl()
    test_ctrl_c()
    test_multi_session()
    test_cwd()
    test_long_output()
    test_auto_create()
    print("\n🎉 全部 11 个测试通过!")
