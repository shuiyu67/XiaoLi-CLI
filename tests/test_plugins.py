"""插件系统测试"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ═══════════════════════════════════════════════
# 1. code_editor 插件测试
# ═══════════════════════════════════════════════

class TestCodeEditor:
    """代码编辑器插件测试"""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_dir):
        sys.path.insert(0, os.path.join(PROJECT_ROOT, 'plugins'))
        from code_editor import Plugin
        self.plugin = Plugin()
        self.tmp_dir = tmp_dir

    def test_tool_info(self):
        info = self.plugin.get_tool_info()
        assert info['name'] == 'code_editor'
        assert 'description' in info

    def test_mcp_definition(self):
        mcp = self.plugin.get_mcp_definition()
        assert mcp['name'] == 'code_editor'
        assert 'inputSchema' in mcp
        assert 'operation' in mcp['inputSchema']['properties']

    def test_convert_mcp_args(self):
        args = self.plugin.convert_mcp_args({"operation": "edit", "path": "test.py"})
        assert 'edit' in args

    def test_create_file(self):
        filepath = os.path.join(self.tmp_dir, 'test.py')
        result = self.plugin.handle(f'create {filepath}\nprint("hello")')
        assert os.path.exists(filepath)
        with open(filepath) as f:
            assert 'print("hello")' in f.read()

    def test_read_range(self):
        filepath = os.path.join(self.tmp_dir, 'read_test.py')
        with open(filepath, 'w') as f:
            f.write('line1\nline2\nline3\nline4\nline5\n')
        result = self.plugin.handle(f'read_range {filepath} 2 4')
        assert 'line2' in result
        assert 'line3' in result

    def test_edit_file(self):
        filepath = os.path.join(self.tmp_dir, 'edit_test.py')
        with open(filepath, 'w') as f:
            f.write('def old():\n    pass\n')
        result = self.plugin.handle(f'edit {filepath} def old():\n    pass <<<>>> def new():\n    return True')
        with open(filepath) as f:
            content = f.read()
        assert 'def new():' in content
        assert 'return True' in content

    def test_diff_files(self):
        f1 = os.path.join(self.tmp_dir, 'a.py')
        f2 = os.path.join(self.tmp_dir, 'b.py')
        with open(f1, 'w') as f:
            f.write('hello\nworld\n')
        with open(f2, 'w') as f:
            f.write('hello\nuniverse\n')
        result = self.plugin.handle(f'diff {f1} {f2}')
        assert result is not None  # should produce diff output

    def test_search_code(self):
        filepath = os.path.join(self.tmp_dir, 'search.py')
        with open(filepath, 'w') as f:
            f.write('def foo():\n    return 42\ndef bar():\n    return foo()\n')
        result = self.plugin.handle(f'search {self.tmp_dir} main *.py')
        assert 'main' in result

    def test_write_file(self):
        filepath = os.path.join(self.tmp_dir, 'write.py')
        result = self.plugin.handle(f'write {filepath}\nresult = 42\n')
        assert os.path.exists(filepath)
        with open(filepath) as f:
            assert 'result = 42' in f.read()

    def test_append_file(self):
        filepath = os.path.join(self.tmp_dir, 'append.py')
        with open(filepath, 'w') as f:
            f.write('line1\n')
        self.plugin.handle(f'append {filepath}\nline2\n')
        with open(filepath) as f:
            content = f.read()
        assert 'line1' in content
        assert 'line2' in content


# ═══════════════════════════════════════════════
# 2. code_search 插件测试
# ═══════════════════════════════════════════════

class TestCodeSearch:
    """代码搜索插件测试"""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_dir):
        sys.path.insert(0, os.path.join(PROJECT_ROOT, 'plugins'))
        from code_search import Plugin
        self.plugin = Plugin()
        self.tmp_dir = tmp_dir

        # 创建测试文件
        with open(os.path.join(tmp_dir, 'main.py'), 'w') as f:
            f.write('import os\ndef main():\n    print("hello")\n\nif __name__ == "__main__":\n    main()\n')
        with open(os.path.join(tmp_dir, 'utils.py'), 'w') as f:
            f.write('def helper():\n    return 42\ndef process(data):\n    return [x*2 for x in data]\n')
        with open(os.path.join(tmp_dir, 'test_main.py'), 'w') as f:
            f.write('# TODO: add tests\ndef test_main():\n    assert True\n')

    def test_tool_info(self):
        info = self.plugin.get_tool_info()
        assert info['name'] == 'code_search'

    def test_structure(self):
        result = self.plugin.handle(f'structure {self.tmp_dir}')
        assert 'main.py' in result
        assert 'utils.py' in result

    def test_find(self):
        result = self.plugin.handle(f'find {self.tmp_dir} def *.py')
        assert 'main' in result or 'helper' in result or 'def' in result

    def test_symbols(self):
        result = self.plugin.handle(f'symbols {self.tmp_dir} main.py')
        assert 'main' in result

    def test_todo(self):
        result = self.plugin.handle(f'todo {self.tmp_dir}')
        assert 'TODO' in result

    def test_stats(self):
        result = self.plugin.handle(f'stats {self.tmp_dir}')
        assert result is not None

    def test_context(self):
        filepath = os.path.join(self.tmp_dir, 'main.py')
        result = self.plugin.handle(f'context {filepath} 2 2')
        assert 'main' in result or 'def' in result


# ═══════════════════════════════════════════════
# 3. git_tools 插件测试
# ═══════════════════════════════════════════════

class TestGitTools:
    """Git 工具插件测试"""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_dir):
        sys.path.insert(0, os.path.join(PROJECT_ROOT, 'plugins'))
        from git_tools import Plugin
        self.plugin = Plugin()
        self.tmp_dir = tmp_dir

    def test_tool_info(self):
        info = self.plugin.get_tool_info()
        assert info['name'] == 'git_tools'

    def test_mcp_definition(self):
        mcp = self.plugin.get_mcp_definition()
        assert mcp['name'] == 'git_tools'
        assert 'inputSchema' in mcp

    def test_status_non_git_dir(self):
        result = self.plugin.handle(f'status')
        # 在非 git 目录应返回错误或提示
        assert result is not None

    def test_help_text(self):
        assert 'git' in self.plugin.usage.lower() or 'Git' in self.plugin.usage


# ═══════════════════════════════════════════════
# 4. unified_tool_manager 测试
# ═══════════════════════════════════════════════

class TestUnifiedToolManager:
    """统一工具管理器测试"""

    @pytest.fixture(autouse=True)
    def setup(self, plugins_dir, skills_dir):
        from unified_tool_manager import UnifiedToolManager
        self.manager = UnifiedToolManager()
        self.plugins_dir = plugins_dir
        self.skills_dir = skills_dir

    def test_initialize(self):
        self.manager.initialize(self.plugins_dir, self.skills_dir)
        assert len(self.manager._tools) > 0

    def test_tools_registered(self):
        self.manager.initialize(self.plugins_dir, self.skills_dir)
        assert 'test_tool' in self.manager._tools

    def test_protocol_map(self):
        self.manager.initialize(self.plugins_dir, self.skills_dir)
        assert 'test_tool' in self.manager._protocol_map

    def test_execute_plugin(self):
        self.manager.initialize(self.plugins_dir, self.skills_dir)
        result = self.manager.execute('test_tool', 'hello')
        assert result is not None
        assert 'hello' in str(result) or 'test' in str(result).lower()

    def test_execute_nonexistent(self):
        self.manager.initialize(self.plugins_dir, self.skills_dir)
        result = self.manager.execute('nonexistent_tool', 'args')
        assert result is None or 'not found' in str(result).lower() or '未找到' in str(result)

    def test_mcp_cache(self):
        self.manager.initialize(self.plugins_dir, self.skills_dir)
        cache = self.manager._mcp_tools_cache
        assert cache is not None
        assert len(cache) > 0

    def test_empty_dirs(self, tmp_dir):
        empty_plugins = os.path.join(tmp_dir, 'empty_p')
        empty_skills = os.path.join(tmp_dir, 'empty_s')
        os.makedirs(empty_plugins)
        os.makedirs(empty_skills)
        with open(os.path.join(empty_plugins, '__init__.py'), 'w') as f:
            pass
        with open(os.path.join(empty_skills, '__init__.py'), 'w') as f:
            pass

        mgr = __import__('unified_tool_manager').UnifiedToolManager()
        mgr.initialize(empty_plugins, empty_skills)
        assert len(mgr._tools) == 0
