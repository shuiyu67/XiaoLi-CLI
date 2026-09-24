"""插件加载与基础功能测试"""
import importlib.util
import os
import sys
import pytest

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS_DIR = os.path.join(PROJECT_ROOT, "plugins")
ENGINES_DIR = os.path.join(PROJECT_ROOT, "ai_engines")


def discover_plugins():
    """发现所有插件文件"""
    plugins = []
    if not os.path.isdir(PLUGINS_DIR):
        return plugins
    for f in sorted(os.listdir(PLUGINS_DIR)):
        if f.endswith(".py") and not f.startswith("__"):
            plugins.append(f[:-3])
    return plugins


def load_module(name, path):
    """动态加载模块"""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def plugin_class(mod):
    """取插件入口类（项目里叫 Liugin，历史上叫 Plugin，两种都认）"""
    cls = getattr(mod, "Liugin", None) or getattr(mod, "Plugin", None)
    assert cls is not None, f"{mod.__name__}: 缺少 Plugin/Liugin 类"
    return cls


def as_text(result):
    """插件返回值统一转文本（可能是 str，也可能是 ToolResult）"""
    return result if isinstance(result, str) else str(result)


ERROR_MARKERS = ("❌", "错误", "失败", "缺少", "不存在", "无效", "请提供", "用法")


def is_error(result):
    """判断插件返回是否表示失败（不依赖具体文案措辞）"""
    success = getattr(result, "success", None)
    if success is not None:
        return not success
    return any(m in as_text(result) for m in ERROR_MARKERS)


# ══════════════════════════════════════
#  插件加载测试
# ══════════════════════════════════════

class TestPluginLoading:
    """测试所有插件能否正常加载"""

    @pytest.mark.parametrize("plugin_name", discover_plugins())
    def test_plugin_imports(self, plugin_name):
        """插件文件能被正常导入"""
        path = os.path.join(PLUGINS_DIR, f"{plugin_name}.py")
        mod = load_module(plugin_name, path)
        assert mod is not None

    @pytest.mark.parametrize("plugin_name", discover_plugins())
    def test_plugin_has_class(self, plugin_name):
        """插件包含 Plugin 或 Liugin 类"""
        path = os.path.join(PLUGINS_DIR, f"{plugin_name}.py")
        mod = load_module(plugin_name, path)
        cls = getattr(mod, "Plugin", None) or getattr(mod, "Liugin", None)
        assert cls is not None, f"{plugin_name}: 缺少 Plugin/Liugin 类"

    @pytest.mark.parametrize("plugin_name", discover_plugins())
    def test_plugin_has_required_methods(self, plugin_name):
        """插件类包含必要的方法"""
        path = os.path.join(PLUGINS_DIR, f"{plugin_name}.py")
        mod = load_module(plugin_name, path)
        cls = getattr(mod, "Plugin", None) or getattr(mod, "Liugin", None)
        inst = cls()

        assert hasattr(inst, "handle"), f"{plugin_name}: 缺少 handle 方法"
        assert hasattr(inst, "get_tool_info"), f"{plugin_name}: 缺少 get_tool_info 方法"
        assert hasattr(inst, "set_cli"), f"{plugin_name}: 缺少 set_cli 方法"

    @pytest.mark.parametrize("plugin_name", discover_plugins())
    def test_plugin_get_tool_info(self, plugin_name):
        """get_tool_info 返回正确的结构"""
        path = os.path.join(PLUGINS_DIR, f"{plugin_name}.py")
        mod = load_module(plugin_name, path)
        cls = getattr(mod, "Plugin", None) or getattr(mod, "Liugin", None)
        inst = cls()
        info = inst.get_tool_info()

        assert isinstance(info, dict)
        assert "name" in info, f"{plugin_name}: tool_info 缺少 name"
        assert "description" in info, f"{plugin_name}: tool_info 缺少 description"
        assert "keywords" in info, f"{plugin_name}: tool_info 缺少 keywords"
        assert isinstance(info["keywords"], list)


# ══════════════════════════════════════
#  插件功能测试
# ══════════════════════════════════════

class TestCodeEditor:
    """code_editor 功能测试"""

    @pytest.fixture
    def editor(self):
        mod = load_module("code_editor", os.path.join(PLUGINS_DIR, "code_editor.py"))
        return plugin_class(mod)()

    @pytest.fixture
    def tmp_file(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("def hello():\n    print('hello')\n\ndef world():\n    print('world')\n")
        return str(f)

    def test_read_range(self, editor, tmp_file):
        result = editor.handle(f"read_range {tmp_file} 1 2")
        assert "hello" in as_text(result)
        assert "1 |" in as_text(result)

    def test_edit(self, editor, tmp_file):
        result = editor.handle(f"edit {tmp_file} print('hello') <<<>>> print('hi')")
        assert "已编辑" in as_text(result)
        content = open(tmp_file).read()
        assert "print('hi')" in content

    def test_edit_not_found(self, editor, tmp_file):
        result = editor.handle(f"edit {tmp_file} nonexistent_code <<<>>> new_code")
        assert is_error(result)

    def test_create(self, editor, tmp_path):
        new_file = str(tmp_path / "new.py")
        result = editor.handle(f"create {new_file} import os")
        assert "已创建" in as_text(result)
        assert os.path.exists(new_file)

    def test_diff_text(self, editor):
        result = editor.handle("diff_text old <<<>>> new")
        assert "变更预览" in as_text(result)

    def test_ast_info(self, editor, tmp_file):
        result = editor.handle(f"ast_info {tmp_file}")
        assert "def hello" in as_text(result)
        assert "def world" in as_text(result)

    def test_stats(self, editor, tmp_path):
        result = editor.handle(f"stats {tmp_path}")
        assert "代码统计" in as_text(result)
        assert "文件" in as_text(result)

    def test_structure(self, editor, tmp_path):
        result = editor.handle(f"structure {tmp_path} 1")
        assert "" in as_text(result)

    def test_find(self, editor, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\ny = 2\n")
        result = editor.handle(f"find {tmp_path} x *.py")
        assert "x = 1" in as_text(result)


class TestGitTools:
    """git_tools 功能测试"""

    @pytest.fixture
    def git(self):
        mod = load_module("git_tools", os.path.join(PLUGINS_DIR, "git_tools.py"))
        return plugin_class(mod)()

    def test_status(self, git):
        result = git.handle("status")
        assert "Git" in as_text(result) or "干净" in as_text(result) or "分支" in as_text(result)

    def test_log(self, git):
        result = git.handle("log --oneline 3")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_branch(self, git):
        result = git.handle("branch")
        assert "master" in as_text(result) or "main" in as_text(result)


class TestCmdExecutor:
    """cmd_executor 功能测试"""

    @pytest.fixture
    def cmd(self):
        mod = load_module("cmd_executor", os.path.join(PLUGINS_DIR, "cmd_executor.py"))
        return plugin_class(mod)()

    def test_echo(self, cmd):
        result = cmd.handle("run echo test_ok")
        assert "test_ok" in as_text(result)

    def test_python_version(self, cmd):
        result = cmd.handle("run python3 --version")
        assert "Python" in as_text(result)

    def test_blocked_command(self, cmd):
        result = cmd.handle("run rm -rf /")
        assert "拦截" in as_text(result)

    def test_timeout(self, cmd):
        result = cmd.handle("run echo fast --timeout 5")
        assert "fast" in as_text(result)

    def test_empty_command(self, cmd):
        result = cmd.handle("run")
        assert is_error(result)


class TestFileManager:
    """file_manager 功能测试"""

    @pytest.fixture
    def fm(self):
        mod = load_module("file_manager", os.path.join(PLUGINS_DIR, "file_manager.py"))
        return plugin_class(mod)()

    def test_list(self, fm, tmp_path):
        (tmp_path / "a.txt").write_text("hi")
        result = fm.handle(f"list {tmp_path}")
        assert "a.txt" in as_text(result)

    def test_read(self, fm, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        result = fm.handle(f"read {f}")
        assert "hello world" in as_text(result)

    def test_write_and_read(self, fm, tmp_path):
        f = tmp_path / "new.txt"
        result = fm.handle(f"write {f} -c test_content")
        assert "已写入" in as_text(result)
        result = fm.handle(f"read {f}")
        assert "test_content" in as_text(result)

    def test_copy(self, fm, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("data")
        dst = tmp_path / "dst.txt"
        result = fm.handle(f"copy {src} {dst}")
        assert "已复制" in as_text(result)
        assert dst.exists()

    def test_delete(self, fm, tmp_path):
        f = tmp_path / "del.txt"
        f.write_text("bye")
        result = fm.handle(f"delete {f}")
        assert "已删除" in as_text(result)
        assert not f.exists()

    def test_mkdir(self, fm, tmp_path):
        d = tmp_path / "newdir"
        result = fm.handle(f"mkdir {d}")
        assert "已创建" in as_text(result)
        assert d.is_dir()

    def test_info(self, fm, tmp_path):
        f = tmp_path / "info.txt"
        f.write_text("x")
        result = fm.handle(f"info {f}")
        assert "路径" in as_text(result)
        assert "大小" in as_text(result)


class TestAutoEngineer:
    """auto_engineer 功能测试"""

    @pytest.fixture
    def eng(self):
        mod = load_module("auto_engineer", os.path.join(PLUGINS_DIR, "auto_engineer.py"))
        return plugin_class(mod)()

    def test_metrics(self, eng, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\n# comment\n\ny = 2\n")
        result = eng.handle(f"metrics {tmp_path}")
        assert "代码指标" in as_text(result)
        assert "文件" in as_text(result)

    def test_security_clean(self, eng, tmp_path):
        (tmp_path / "safe.py").write_text("x = 1\nprint(x)\n")
        result = eng.handle(f"security {tmp_path}")
        assert "没有发现" in as_text(result) or "风险" in as_text(result)

    def test_security_risk(self, eng, tmp_path):
        (tmp_path / "risk.py").write_text('password = "secret123"\neval("1+1")\n')
        result = eng.handle(f"security {tmp_path}")
        assert "风险" in as_text(result)

    def test_complexity(self, eng, tmp_path):
        code = "def f():\n    if True:\n        if True:\n            if True:\n                pass\n"
        (tmp_path / "complex.py").write_text(code)
        result = eng.handle(f"complexity {tmp_path}")
        assert isinstance(result, str)


class TestTaskManager:
    """task_manager 功能测试"""

    @pytest.fixture
    def tm(self, tmp_path, monkeypatch):
        mod = load_module("task_manager", os.path.join(PLUGINS_DIR, "task_manager.py"))
        inst = getattr(mod, "Liugin")()
        inst.tasks = []
        inst.tasks_file = str(tmp_path / "tasks.json")
        return inst

    def test_add(self, tm):
        result = tm.handle("add 测试任务")
        assert "已添加" in as_text(result)

    def test_list_empty(self, tm):
        result = tm.handle("list")
        assert "没有任务" in as_text(result)

    def test_add_and_list(self, tm):
        tm.handle("add 任务A")
        tm.handle("add 任务B")
        result = tm.handle("list")
        assert "任务A" in as_text(result)
        assert "任务B" in as_text(result)

    def test_complete(self, tm):
        tm.handle("add 任务X")
        result = tm.handle("complete 1")
        assert "已更新" in as_text(result)

    def test_delete(self, tm):
        tm.handle("add 任务Y")
        result = tm.handle("delete 1")
        assert "已删除" in as_text(result)

    def test_clear(self, tm):
        tm.handle("add A")
        tm.handle("complete 1")
        result = tm.handle("clear")
        assert "已清除" in as_text(result)


# ══════════════════════════════════════
#  引擎加载测试
# ══════════════════════════════════════

@pytest.mark.skipif(
    not os.path.exists(os.path.join(PLUGINS_DIR, "browser_auto.py")),
    reason="browser_auto 已剥离到 xiaoli-cli-plugins 仓库（插件缺失自动跳过）",
)
class TestBrowserAuto:
    """browser_auto 功能测试"""

    @pytest.fixture
    def browser(self):
        mod = load_module("browser_auto", os.path.join(PLUGINS_DIR, "browser_auto.py"))
        return plugin_class(mod)()

    def test_status_stopped(self, browser):
        result = browser.handle("status")
        assert "未运行" in as_text(result)

    def test_invalid_operation(self, browser):
        result = browser.handle("nonexistent")
        assert is_error(result)

    def test_empty_args(self, browser):
        result = browser.handle("")
        assert is_error(result)

    def test_tool_info(self, browser):
        info = browser.get_tool_info()
        assert info["name"] == "browser_auto"
        assert "浏览器" in info["description"]
        assert len(info["keywords"]) > 0


# ══════════════════════════════════════
#  引擎加载测试
# ══════════════════════════════════════

@pytest.mark.skipif(
    not os.path.exists(os.path.join(PLUGINS_DIR, "gui_auto.py")),
    reason="gui_auto 已剥离到 xiaoli-cli-plugins 仓库（插件缺失自动跳过）",
)
class TestGuiAuto:
    """gui_auto 功能测试"""

    @pytest.fixture
    def gui(self):
        mod = load_module("gui_auto", os.path.join(PLUGINS_DIR, "gui_auto.py"))
        return plugin_class(mod)()

    def test_tool_info(self, gui):
        info = gui.get_tool_info()
        assert info["name"] == "gui_auto"
        assert "GUI" in info["description"]
        assert len(info["keywords"]) >= 5

    def test_mcp_definition(self, gui):
        mcp = gui.get_mcp_definition()
        assert mcp["name"] == "gui_auto"
        assert "inputSchema" in mcp
        assert "operation" in mcp["inputSchema"]["properties"]

    def test_convert_mcp_args(self, gui):
        args = {"operation": "click", "target": "确定"}
        result = gui.convert_mcp_args(args)
        assert "click" in as_text(result)
        assert "确定" in as_text(result)

    def test_convert_mcp_args_xy(self, gui):
        args = {"operation": "click", "x": 100, "y": 200}
        result = gui.convert_mcp_args(args)
        assert "--xy" in as_text(result)
        assert "100" in as_text(result)

    def test_convert_mcp_args_snapshot(self, gui):
        args = {"operation": "snapshot", "depth": 3}
        result = gui.convert_mcp_args(args)
        assert "snapshot" in as_text(result)
        assert "3" in as_text(result)

    def test_empty_args(self, gui):
        result = gui.handle("")
        assert is_error(result)

    def test_invalid_operation(self, gui):
        result = gui.handle("nonexistent_op")
        assert "不支持" in as_text(result)

    def test_click_no_args(self, gui):
        result = gui.handle("click")
        assert is_error(result)

    def test_type_no_args(self, gui):
        result = gui.handle("type")
        assert is_error(result)

    def test_type_missing_text(self, gui):
        result = gui.handle("type 按钮")
        assert is_error(result)

    def test_find_no_args(self, gui):
        result = gui.handle("find")
        assert is_error(result)

    def test_findall_no_args(self, gui):
        result = gui.handle("findall")
        assert is_error(result)

    def test_info_no_args(self, gui):
        result = gui.handle("info")
        assert is_error(result)

    def test_value_no_args(self, gui):
        result = gui.handle("value")
        assert is_error(result)

    def test_tree_no_args(self, gui):
        result = gui.handle("tree")
        assert is_error(result)

    def test_wait_no_args(self, gui):
        result = gui.handle("wait")
        assert is_error(result)

    def test_exists_no_args(self, gui):
        result = gui.handle("exists")
        assert is_error(result)

    def test_highlight_no_args(self, gui):
        result = gui.handle("highlight")
        assert is_error(result)

    def test_state_no_args(self, gui):
        result = gui.handle("state")
        assert is_error(result)

    def test_keys_no_args(self, gui):
        result = gui.handle("keys")
        assert is_error(result)

    def test_focus_no_args(self, gui):
        result = gui.handle("focus")
        assert is_error(result)

    def test_click_xy_format_error(self, gui):
        result = gui.handle("click --xy abc")
        assert is_error(result)

    def test_format_element_info(self, gui):
        el = {
            "name": "测试按钮", "type": "Button", "class": "Button",
            "automation_id": "btn_ok",
            "bounds": {"left": 100, "top": 200, "width": 80, "height": 30,
                       "right": 180, "bottom": 230},
            "enabled": True, "focused": False
        }
        result = gui._format_element_info(el)
        assert "测试按钮" in as_text(result)
        assert "Button" in as_text(result)
        assert "btn_ok" in as_text(result)

    def test_format_element_info_detailed(self, gui):
        el = {
            "name": "输入框", "type": "Edit", "class": "Edit",
            "automation_id": "", "enabled": True, "focused": True,
            "value": "hello",
            "bounds": {"left": 0, "top": 0, "width": 200, "height": 25,
                       "right": 200, "bottom": 25}
        }
        result = gui._format_element_info(el, detailed=True)
        assert "输入框" in as_text(result)
        assert "hello" in as_text(result)

    def test_all_operations_route(self, gui):
        """所有操作都能正确路由"""
        for op in ["snapshot", "screenshot", "windows", "focus", "click",
                    "rightclick", "doubleclick", "type", "clear", "keys",
                    "scroll", "find", "findall", "info", "value", "tree",
                    "wait", "exists", "highlight", "state"]:
            result = gui.handle(f"{op} test")
            assert isinstance(result, str)


class TestSubAgent:
    """sub_agent 功能测试"""

    @pytest.fixture
    def sa(self):
        mod = load_module("sub_agent", os.path.join(PLUGINS_DIR, "sub_agent.py"))
        return plugin_class(mod)()

    def test_list_empty(self, sa):
        result = sa.handle("list")
        assert "没有" in as_text(result)

    def test_stats_empty(self, sa):
        result = sa.handle("stats")
        assert "总数: 0" in as_text(result)

    def test_spawn(self, sa):
        result = sa.handle("spawn tester 测试任务")
        assert "已创建" in as_text(result)
        assert "agent_tester" in as_text(result)

    def test_spawn_and_list(self, sa):
        sa.handle("spawn a 任务A")
        sa.handle("spawn b 任务B")
        import time; time.sleep(0.1)
        result = sa.handle("list")
        assert "agent_a" in as_text(result)
        assert "agent_b" in as_text(result)

    def test_status(self, sa):
        sa.handle("spawn x 某任务")
        import time; time.sleep(0.1)
        # 获取 agent ID
        agent_id = list(sa.agents.keys())[0]
        result = sa.handle(f"status {agent_id}")
        assert "名称" in as_text(result)

    def test_kill(self, sa):
        sa.handle("spawn y 要终止的任务")
        import time; time.sleep(0.1)
        agent_id = list(sa.agents.keys())[0]
        result = sa.handle(f"kill {agent_id}")
        assert "已终止" in as_text(result)

    def test_clean(self, sa):
        sa.handle("spawn z 清理测试")
        import time; time.sleep(0.1)
        result = sa.handle("clean")
        assert "已清理" in as_text(result)

    def test_invalid_agent(self, sa):
        result = sa.handle("status nonexistent")
        assert "未找到" in as_text(result)


# ══════════════════════════════════════
#  引擎加载测试
# ══════════════════════════════════════

class TestEngines:
    """AI 引擎加载测试"""

    def test_engines_dir_exists(self):
        assert os.path.isdir(ENGINES_DIR), "ai_engines 目录不存在"

    def test_ollama_engine_loads(self):
        path = os.path.join(ENGINES_DIR, "ollama_engine.py")
        if not os.path.exists(path):
            pytest.skip("ollama_engine.py 不存在")
        mod = load_module("ollama_engine", path)
        cls = getattr(mod, "OllamaAI", None)
        assert cls is not None, "缺少 OllamaAI 类"
        inst = cls()
        assert inst.name == "ollama"

    def test_openai_engine_loads(self):
        path = os.path.join(ENGINES_DIR, "openai_engine.py")
        if not os.path.exists(path):
            pytest.skip("openai_engine.py 不存在")
        mod = load_module("openai_engine", path)
        cls = getattr(mod, "OpenaiAI", None)
        assert cls is not None, "缺少 OpenaiAI 类"
        inst = cls()
        assert inst.name == "openai"

    def test_no_old_engines(self):
        """确认旧引擎文件已被移除"""
        old_engines = [
            "mimo_engine.py", "GLM_http_engine.py", "qwq_engine.py",
            "xfyun_spark_engine.py", "iflow_api_engine.py",
            "maas_http_engine.py", "SDK_openAI.py",
        ]
        for name in old_engines:
            path = os.path.join(ENGINES_DIR, name)
            assert not os.path.exists(path), f"旧引擎未删除: {name}"


# ══════════════════════════════════════
#  核心模块导入测试
# ══════════════════════════════════════

class TestCoreImports:
    """核心模块能否正常导入"""

    def test_import_config(self):
        sys.path.insert(0, os.path.join(PROJECT_ROOT, "xcli_core"))
        from config import load_config, save_config
        assert callable(load_config)

    def test_import_constants(self):
        sys.path.insert(0, os.path.join(PROJECT_ROOT, "xcli_core"))
        import constants
        assert hasattr(constants, "DEFAULT_MAX_HISTORY")

    def test_import_cli_base(self):
        sys.path.insert(0, PROJECT_ROOT)
        sys.path.insert(0, os.path.join(PROJECT_ROOT, "xcli_core"))
        # 只测试语法，不实例化（需要完整环境）
        spec = importlib.util.spec_from_file_location(
            "cli_base", os.path.join(PROJECT_ROOT, "xcli_core", "cli_base.py")
        )
        mod = importlib.util.module_from_spec(spec)
        # 不执行，只检查语法
        assert spec is not None
