"""AI 引擎管理器测试"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xiaoli.engines import EngineManager


class TestEngineManager:
    """EngineManager 测试"""

    def test_init_empty(self):
        mgr = EngineManager()
        assert mgr.engines == {}
        assert mgr.current is None

    def test_set_default_existing(self):
        mgr = EngineManager()
        mgr.engines = {'test': 'fake_engine'}
        assert mgr.set_default('test')
        assert mgr.current == 'fake_engine'

    def test_set_default_missing(self):
        mgr = EngineManager()
        assert not mgr.set_default('nonexistent')

    def test_switch_existing(self):
        mgr = EngineManager()
        mgr.engines = {'a': 'engine_a', 'b': 'engine_b'}
        assert mgr.switch('b')
        assert mgr.current == 'engine_b'

    def test_switch_missing(self):
        mgr = EngineManager()
        assert not mgr.switch('nope')

    def test_current_name_none(self):
        mgr = EngineManager()
        assert mgr.current_name() == '未设置'

    def test_current_name_set(self):
        mgr = EngineManager()
        mgr.current = type('E', (), {'name': 'ollama'})()
        assert mgr.current_name() == 'ollama'

    def test_names(self):
        mgr = EngineManager()
        mgr.engines = {'a': 1, 'b': 2, 'c': 3}
        names = mgr.names()
        assert set(names) == {'a', 'b', 'c'}

    def test_generate_no_engine(self):
        mgr = EngineManager()
        result = mgr.generate("hello")
        assert '错误' in result or 'error' in result.lower()

    def test_generate_with_engine(self):
        mgr = EngineManager()

        class FakeEngine:
            name = 'fake'
            def generate_response(self, user_input, system_prompt=None):
                return f"echo: {user_input}"

        mgr.current = FakeEngine()
        result = mgr.generate("test input")
        assert 'test input' in result

    def test_load_all_missing_dir(self):
        mgr = EngineManager()
        result = mgr.load_all('/tmp/nonexistent_engines_dir_12345')
        assert result == {}

    def test_find_class_patterns(self):
        mgr = EngineManager()
        import types
        mod = types.ModuleType('test')

        class TestAI:
            def generate_response(self, **kw):
                pass
        mod.TestAI = TestAI

        found = mgr._find_class(mod, 'test')
        assert found == 'TestAI'

    def test_find_class_no_match(self):
        mgr = EngineManager()
        import types
        mod = types.ModuleType('test')
        mod.Foo = 42  # not a class ending in AI
        found = mgr._find_class(mod, 'test')
        assert found is None

    def test_load_all_real_engines(self):
        """测试加载实际引擎目录（不验证引擎可用性，只验证不崩溃）"""
        mgr = EngineManager()
        engines_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'ai_engines'
        )
        if os.path.exists(engines_dir):
            mgr.load_all(engines_dir)
            # 至少应该尝试加载（可能因缺少依赖而失败）
            # 但不应崩溃
