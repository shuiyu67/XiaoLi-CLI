"""终端模拟器插件测试"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from plugins.terminal import Liugin, TerminalSession


def test_basic_open_close():
    """打开和关闭终端"""
    p = Liugin()
    r = p.handle("open")
    assert "✓" in r
    assert "s1" in r or "main" in r

    r = p.handle("list")
    assert "终端" in r

    r = p.handle("close")
    assert "✓" in r

    r = p.handle("list")
    assert "暂无" in r
    print("✓ test_basic_open_close")


def test_send_command():
    """发送命令并获取输出"""
    p = Liugin()
    p.handle("open")

    r = p.handle("send echo hello_world")
    assert "hello_world" in r, f"期望 hello_world，实际: {r}"

    r = p.handle("send echo 42")
    assert "42" in r

    p.handle("close")
    print("✓ test_send_command")


def test_cwd():
    """切换目录"""
    p = Liugin()
    p.handle("open")

    r = p.handle("cwd /tmp")
    assert "✓" in r

    r = p.handle("send pwd")
    assert "/tmp" in r

    p.handle("close")
    print("✓ test_cwd")


def test_env():
    """环境变量"""
    p = Liugin()
    p.handle("open")

    r = p.handle("env MY_TEST_VAR hello123")
    assert "✓" in r

    r = p.handle("send echo $MY_TEST_VAR")
    assert "hello123" in r

    p.handle("close")
    print("✓ test_env")


def test_multiple_sessions():
    """多会话管理"""
    p = Liugin()

    p.handle("open bash session1")
    p.handle("open bash session2")

    r = p.handle("list")
    assert "2 个" in r

    # 第一个会话是 main
    p.handle("send echo AAA")  # 当前是 s2，发给 s2
    p.handle("switch main")
    p.handle("send echo BBB")  # 发给 main

    r = p.handle("close main")
    assert "✓" in r

    r = p.handle("list")
    assert "1 个" in r

    p.handle("close s2")
    print("✓ test_multiple_sessions")


def test_keys():
    """特殊按键"""
    p = Liugin()
    p.handle("open")

    r = p.handle("keys")
    assert "ctrl+c" in r

    # 发送 Ctrl+C（不应该报错）
    r = p.handle("keys ctrl+c")
    assert "←" in r

    p.handle("close")
    print("✓ test_keys")


def test_input():
    """纯文本输入"""
    p = Liugin()
    p.handle("open")

    p.handle("send cat << 'EOF'")
    p.handle("input line1")
    p.handle("input line2")
    p.handle("input EOF")

    p.handle("close")
    print("✓ test_input")


def test_status():
    """状态查询"""
    p = Liugin()
    p.handle("open")

    r = p.handle("status")
    assert "终端状态" in r
    assert "运行中" in r

    p.handle("close")
    print("✓ test_status")


def test_read_output():
    """读取输出"""
    p = Liugin()
    p.handle("open")

    p.handle("send echo AAA")
    p.handle("send echo BBB")
    p.handle("send echo CCC")

    r = p.handle("read")
    # read 返回最近一次 send_cmd 的结果
    assert "CCC" in r, f"read 结果: {r[:100]}"

    p.handle("close")
    print("✓ test_read_output")


def test_python_repl():
    """Python REPL 交互"""
    p = Liugin()
    p.handle("open python3 Python-REPL")
    import time; time.sleep(1)

    # REPL 用 input 发送（不触发哨兵），用 read 拿输出
    p.handle('input print(2 + 3)')
    time.sleep(0.8)
    r = p.handle('read')
    assert "5" in r, f"Python REPL 输出: {r[:200]}"

    p.handle("close")
    print("✓ test_python_repl")


def test_session_persistence():
    """会话持久性 — 环境变量在命令间保持"""
    p = Liugin()
    p.handle("open")

    p.handle("send export FOO=bar123")
    r = p.handle("send echo $FOO")
    assert "bar123" in r, f"环境变量未保持: {r}"

    p.handle("send cd /var")
    r = p.handle("send pwd")
    assert "/var" in r, f"目录未保持: {r}"

    p.handle("close")
    print("✓ test_session_persistence")


def test_auto_create_session():
    """无会话时自动创建"""
    p = Liugin()
    # 不 open，直接 send
    r = p.handle("send echo auto_created")
    assert "auto_created" in r

    p.handle("close")
    print("✓ test_auto_create_session")


def test_long_output():
    """长输出处理"""
    p = Liugin()
    p.handle("open")

    # 生成长输出
    r = p.handle("send seq 1 200")
    assert "200" in r or "1" in r

    p.handle("close")
    print("✓ test_long_output")


if __name__ == "__main__":
    test_basic_open_close()
    test_send_command()
    test_cwd()
    test_env()
    test_multiple_sessions()
    test_keys()
    test_input()
    test_status()
    test_read_output()
    test_python_repl()
    test_session_persistence()
    test_auto_create_session()
    test_long_output()
    print("\n🎉 全部 13 个测试通过!")
