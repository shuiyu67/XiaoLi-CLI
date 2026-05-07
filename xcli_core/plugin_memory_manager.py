"""
插件内存管理器 - TTL 自动淘汰 + 懒加载

机制:
  1. 每个插件记录 last_used 时间戳
  2. 后台线程定期扫描，超过 TTL 未使用的插件从内存卸载
  3. AI 调用已卸载的插件时，自动重新加载
  4. 核心插件（tool_search 等）可钉住，永不淘汰

配置:
  - plugin_ttl: 插件空闲多久后淘汰（秒），默认 300（5分钟）
  - max_idle_plugins: 最多保留多少个空闲插件，超出后淘汰最久未用的，默认 10
  - check_interval: 后台扫描间隔（秒），默认 60
  - pinned_plugins: 钉住的插件名列表，永不淘汰
"""

import os
import time
import threading
import importlib.util
from typing import Dict, Optional, List, Any, Callable
from colorama import Fore, Style

from .config import logger


class PluginMemoryManager:
    """插件内存管理器 - 自动淘汰空闲插件，按需懒加载"""

    # 默认钉住的插件（核心工具，不淘汰）
    DEFAULT_PINNED = {'tool_search'}

    def __init__(self,
                 plugin_ttl: int = 300,
                 max_idle_plugins: int = 10,
                 check_interval: int = 60,
                 pinned_plugins: Optional[List[str]] = None):
        self.plugin_ttl = plugin_ttl
        self.max_idle_plugins = max_idle_plugins
        self.check_interval = check_interval
        self.pinned = set(pinned_plugins or self.DEFAULT_PINNED)

        # ── 插件元数据 ──
        # name -> {path, protocol, last_used, info_cache, ...}
        self._registry: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

        # ── 已加载的实例引用（由 UnifiedToolManager 提供注册/注销回调） ──
        self._load_callback: Optional[Callable] = None   # (name) -> tool_dict or None
        self._unload_callback: Optional[Callable] = None  # (name) -> None

        # ── 后台清理线程 ──
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False

        # ── 统计 ──
        self.stats = {
            'evictions': 0,
            'lazy_loads': 0,
            'pins_hit': 0,
        }

    # ==================== 生命周期 ====================

    def start(self) -> None:
        """启动后台清理线程"""
        if self._running:
            return
        self._running = True
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop, daemon=True, name="plugin-gc"
        )
        self._cleanup_thread.start()
        print(f"{Fore.CYAN}[插件内存管理] 已启动 (TTL={self.plugin_ttl}s, "
              f"最大空闲={self.max_idle_plugins}, 检查间隔={self.check_interval}s){Style.RESET_ALL}")

    def stop(self) -> None:
        """停止后台清理线程"""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
            self._cleanup_thread = None

    # ==================== 回调注册 ====================

    def set_callbacks(self,
                      load_fn: Callable[[str], Optional[Dict]],
                      unload_fn: Callable[[str], None]) -> None:
        """
        注册加载/卸载回调（由 UnifiedToolManager 提供）

        Args:
            load_fn: 加载插件函数，接收插件名，返回 tool_dict 或 None
            unload_fn: 卸载插件函数，接收插件名
        """
        self._load_callback = load_fn
        self._unload_callback = unload_fn

    # ==================== 插件注册 ====================

    def register(self, name: str, path: str, protocol: str = 'liugin',
                 info_cache: Optional[Dict] = None) -> None:
        """
        注册一个插件的元数据（加载时调用）

        Args:
            name: 插件名
            path: 插件文件路径
            protocol: 协议类型 (liugin/skill)
            info_cache: 缓存的工具信息（name, description, keywords 等）
        """
        with self._lock:
            self._registry[name] = {
                'path': path,
                'protocol': protocol,
                'last_used': time.time(),
                'loaded': True,
                'info_cache': info_cache or {},
            }

    def mark_used(self, name: str) -> None:
        """标记插件被使用（每次工具调用时）"""
        with self._lock:
            if name in self._registry:
                self._registry[name]['last_used'] = time.time()

    def mark_loaded(self, name: str) -> None:
        """标记插件已加载"""
        with self._lock:
            if name in self._registry:
                self._registry[name]['loaded'] = True
                self._registry[name]['last_used'] = time.time()

    def mark_unloaded(self, name: str) -> None:
        """标记插件已卸载"""
        with self._lock:
            if name in self._registry:
                self._registry[name]['loaded'] = False

    # ==================== 懒加载 ====================

    def ensure_loaded(self, name: str) -> Optional[Dict]:
        """
        确保插件已加载，如果已卸载则自动重新加载

        Args:
            name: 插件名

        Returns:
            tool_dict 如果加载成功，None 如果失败
        """
        with self._lock:
            entry = self._registry.get(name)
            if not entry:
                return None  # 未注册的插件，不管

            if entry['loaded']:
                # 已加载，更新时间戳
                entry['last_used'] = time.time()
                return None  # 返回 None 表示不需要重新加载

        # 需要重新加载（锁外执行，避免死锁）
        print(f"{Fore.CYAN}[插件内存管理] 懒加载插件: {name}{Style.RESET_ALL}")
        result = self._do_load(name)
        if result:
            self.stats['lazy_loads'] += 1
            print(f"{Fore.GREEN}[插件内存管理] 懒加载成功: {name}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[插件内存管理] 懒加载失败: {name}{Style.RESET_ALL}")
        return result

    def _do_load(self, name: str) -> Optional[Dict]:
        """执行实际的插件加载"""
        if not self._load_callback:
            return None

        with self._lock:
            entry = self._registry.get(name)
            if not entry:
                return None

        try:
            result = self._load_callback(name)
            if result:
                with self._lock:
                    if name in self._registry:
                        self._registry[name]['loaded'] = True
                        self._registry[name]['last_used'] = time.time()
                return result
        except Exception as e:
            logger.error(f"懒加载插件 '{name}' 失败: {e}")
        return None

    # ==================== 淘汰 ====================

    def evict(self, name: str) -> bool:
        """
        淘汰指定插件

        Args:
            name: 插件名

        Returns:
            是否成功淘汰
        """
        if name in self.pinned:
            self.stats['pins_hit'] += 1
            return False

        with self._lock:
            entry = self._registry.get(name)
            if not entry or not entry['loaded']:
                return False

        # 执行卸载（锁外）
        if self._unload_callback:
            try:
                self._unload_callback(name)
            except Exception as e:
                logger.error(f"卸载插件 '{name}' 失败: {e}")
                return False

        with self._lock:
            if name in self._registry:
                self._registry[name]['loaded'] = False

        self.stats['evictions'] += 1
        print(f"{Fore.YELLOW}[插件内存管理] 已淘汰: {name} "
              f"(空闲 {self._idle_time(name):.0f}s){Style.RESET_ALL}")
        return True

    def _idle_time(self, name: str) -> float:
        """获取插件空闲时间"""
        with self._lock:
            entry = self._registry.get(name)
            if not entry:
                return 0
            return time.time() - entry['last_used']

    # ==================== 后台清理 ====================

    def _cleanup_loop(self) -> None:
        """后台清理循环"""
        while self._running:
            try:
                time.sleep(self.check_interval)
                if not self._running:
                    break
                self._cleanup_once()
            except Exception as e:
                logger.error(f"插件清理线程异常: {e}")

    def _cleanup_once(self) -> None:
        """执行一次清理"""
        with self._lock:
            # 收集所有已加载且未钉住的插件
            candidates = []
            for name, entry in self._registry.items():
                if entry['loaded'] and name not in self.pinned:
                    idle = time.time() - entry['last_used']
                    if idle >= self.plugin_ttl:
                        candidates.append((name, idle))

        if not candidates:
            return

        # 按空闲时间排序，最久未用的优先淘汰
        candidates.sort(key=lambda x: x[1], reverse=True)

        # 也检查总数限制
        with self._lock:
            loaded_count = sum(1 for e in self._registry.values()
                              if e['loaded'] and e.get('name') not in self.pinned)

        evicted = 0
        for name, idle in candidates:
            # 如果已超过最大空闲数限制 或 超过 TTL
            if loaded_count - evicted > self.max_idle_plugins or idle >= self.plugin_ttl:
                if self.evict(name):
                    evicted += 1

        if evicted:
            print(f"{Fore.CYAN}[插件内存管理] 本轮淘汰 {evicted} 个插件, "
                  f"累计淘汰 {self.stats['evictions']} 次, "
                  f"懒加载 {self.stats['lazy_loads']} 次{Style.RESET_ALL}")

    # ==================== 查询接口 ====================

    def is_loaded(self, name: str) -> bool:
        """检查插件是否已加载"""
        with self._lock:
            entry = self._registry.get(name)
            return entry['loaded'] if entry else False

    def is_registered(self, name: str) -> bool:
        """检查插件是否已注册"""
        with self._lock:
            return name in self._registry

    def get_info_cache(self, name: str) -> Optional[Dict]:
        """获取插件的缓存信息（不需要加载实例）"""
        with self._lock:
            entry = self._registry.get(name)
            return entry.get('info_cache') if entry else None

    def get_all_registered(self) -> List[str]:
        """获取所有已注册的插件名"""
        with self._lock:
            return list(self._registry.keys())

    def get_loaded_names(self) -> List[str]:
        """获取当前已加载的插件名"""
        with self._lock:
            return [n for n, e in self._registry.items() if e['loaded']]

    def get_unloaded_names(self) -> List[str]:
        """获取当前已卸载的插件名"""
        with self._lock:
            return [n for n, e in self._registry.items() if not e['loaded']]

    def get_status(self) -> Dict[str, Any]:
        """获取内存管理状态"""
        with self._lock:
            loaded = sum(1 for e in self._registry.values() if e['loaded'])
            unloaded = sum(1 for e in self._registry.values() if not e['loaded'])
            return {
                'total': len(self._registry),
                'loaded': loaded,
                'unloaded': unloaded,
                'pinned': list(self.pinned),
                'ttl': self.plugin_ttl,
                'max_idle': self.max_idle_plugins,
                'check_interval': self.check_interval,
                'stats': dict(self.stats),
            }

    def format_status(self) -> str:
        """格式化状态信息（用于 /status 命令）"""
        s = self.get_status()
        lines = [
            f"  插件内存管理:",
            f"    总注册: {s['total']}  已加载: {s['loaded']}  已卸载: {s['unloaded']}",
            f"    TTL: {s['ttl']}s  最大空闲: {s['max_idle']}  扫描间隔: {s['check_interval']}s",
            f"    钉住: {', '.join(s['pinned']) or '无'}",
            f"    统计: 淘汰 {s['stats']['evictions']} 次, "
            f"懒加载 {s['stats']['lazy_loads']} 次, "
            f"钉住保护 {s['stats']['pins_hit']} 次",
        ]

        # 显示已卸载的插件
        unloaded = self.get_unloaded_names()
        if unloaded:
            lines.append(f"    已卸载: {', '.join(unloaded)}")

        return '\n'.join(lines)
