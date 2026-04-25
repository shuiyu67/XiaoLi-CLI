"""配置管理测试"""
import os
import sys
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xiaoli import config as cfg


class TestConfig:
    """配置加载/保存测试"""

    def setup_method(self):
        """重置缓存"""
        cfg._cache = None

    def test_default_config(self):
        """无配置文件时使用默认值"""
        # 临时指向不存在的文件
        original = cfg.CONFIG_FILE
        cfg.CONFIG_FILE = '/tmp/nonexistent_config.json'
        cfg._cache = None

        result = cfg.load()
        assert 'system' in result
        assert result['system']['default_engine'] == 'ollama'

        cfg.CONFIG_FILE = original
        cfg._cache = None

    def test_load_existing_config(self, config_file):
        """加载现有配置文件"""
        original = cfg.CONFIG_FILE
        cfg.CONFIG_FILE = config_file
        cfg._cache = None

        result = cfg.load()
        assert result['system']['default_engine'] == 'ollama'
        assert result['system']['max_history'] == 100
        assert 'mimo' in result['api']['engines']

        cfg.CONFIG_FILE = original
        cfg._cache = None

    def test_get_specific_key(self, config_file):
        """获取特定配置项"""
        original = cfg.CONFIG_FILE
        cfg.CONFIG_FILE = config_file
        cfg._cache = None

        assert cfg.get('default_engine') == 'ollama'
        assert cfg.get('max_history') == 100
        assert cfg.get('nonexistent', 'fallback') == 'fallback'

        cfg.CONFIG_FILE = original
        cfg._cache = None

    def test_set_and_save(self, tmp_dir):
        """设置并保存配置"""
        config_path = os.path.join(tmp_dir, "config.json")
        original = cfg.CONFIG_FILE
        cfg.CONFIG_FILE = config_path
        cfg._cache = None

        cfg.set('default_engine', 'mimo')
        assert cfg.get('default_engine') == 'mimo'

        # 验证文件持久化
        with open(config_path, 'r') as f:
            saved = json.load(f)
        assert saved['system']['default_engine'] == 'mimo'

        cfg.CONFIG_FILE = original
        cfg._cache = None

    def test_reload(self, config_file):
        """强制重新加载"""
        original = cfg.CONFIG_FILE
        cfg.CONFIG_FILE = config_file
        cfg._cache = None

        cfg.load()
        assert cfg._cache is not None

        reloaded = cfg.reload()
        assert cfg._cache is not None
        assert 'system' in reloaded

        cfg.CONFIG_FILE = original
        cfg._cache = None

    def test_caching(self, config_file):
        """配置缓存机制"""
        original = cfg.CONFIG_FILE
        cfg.CONFIG_FILE = config_file
        cfg._cache = None

        r1 = cfg.load()
        r2 = cfg.load()
        assert r1 is r2  # 同一对象（缓存）

        cfg.CONFIG_FILE = original
        cfg._cache = None

    def test_corrupted_json(self, tmp_dir):
        """损坏的 JSON 文件处理"""
        config_path = os.path.join(tmp_dir, "config.json")
        with open(config_path, 'w') as f:
            f.write("{invalid json")

        original = cfg.CONFIG_FILE
        cfg.CONFIG_FILE = config_path
        cfg._cache = None

        result = cfg.load()
        assert 'system' in result  # 应回退到默认值

        cfg.CONFIG_FILE = original
        cfg._cache = None

    def test_missing_system_section(self, tmp_dir):
        """缺少 system 节时的行为"""
        config_path = os.path.join(tmp_dir, "config.json")
        with open(config_path, 'w') as f:
            json.dump({"api": {}}, f)

        original = cfg.CONFIG_FILE
        cfg.CONFIG_FILE = config_path
        cfg._cache = None

        assert cfg.get('default_engine') is None
        assert cfg.get('default_engine', 'ollama') == 'ollama'

        cfg.CONFIG_FILE = original
        cfg._cache = None
