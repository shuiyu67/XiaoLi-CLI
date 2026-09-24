"""任务提示音体系（对标 opencode attention sounds）

三个事件三种音色（assets/sounds/，音效素材来源：爱给网 aigei.com）：
  done.mp3    — Steam 成就音：任务/AI 回复完成
  notify.mp3  — 微信气泡音：需要你看一眼（PLAN 待批准等）
  special.mp3 — 隐藏要素发现音：特殊节点（PLAN 批准开工 / 向导完成）

pygame 异步播放（后台线程，不阻塞 UI）；pygame 缺失/音频设备不可用时静默降级，
绝不影响主流程。配置走 config.json 的 sound 段：
  {"sound": {"enabled": true, "volume": 0.5}}
TUI 里 /sound 命令随时开关。
"""

import os
import threading

_SOUNDS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sounds")

FILES = {
    "done": "done.mp3",
    "notify": "notify.mp3",
    "special": "special.mp3",
}

_mixer_state = {"init": None}   # None=未探测 / True=可用 / False=不可用


def _ensure_mixer():
    if _mixer_state["init"] is None:
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            _mixer_state["init"] = True
        except Exception:
            _mixer_state["init"] = False
    return _mixer_state["init"]


def _sound_cfg():
    """读配置：(enabled, volume)；无配置/读失败 → (True, 0.5)"""
    enabled, volume = True, 0.5
    try:
        from .config import get_system_config
        sc = get_system_config('sound', None)
        if isinstance(sc, dict):
            enabled = bool(sc.get('enabled', True))
            volume = max(0.0, min(1.0, float(sc.get('volume', 0.5))))
    except Exception:
        pass
    return enabled, volume


def set_enabled(on: bool):
    """开关提示音（持久化到 config）"""
    try:
        from .config import get_system_config, set_system_config
        sc = get_system_config('sound', None)
        if not isinstance(sc, dict):
            sc = {}
        sc['enabled'] = bool(on)
        _, vol = _sound_cfg()
        sc.setdefault('volume', vol)
        set_system_config('sound', sc)
    except Exception:
        pass


def is_enabled() -> bool:
    return _sound_cfg()[0]


def play(event: str = "done", enabled=None):
    """异步播放事件提示音。enabled=None 时按配置；任何失败静默。"""
    if enabled is None:
        enabled, _ = _sound_cfg()
    if not enabled:
        return
    fname = FILES.get(event)
    if not fname:
        return
    path = os.path.join(_SOUNDS_DIR, fname)
    if not os.path.exists(path):
        return
    _, volume = _sound_cfg()

    def _run():
        try:
            if not _ensure_mixer():
                return
            import pygame
            snd = pygame.mixer.Sound(path)
            snd.set_volume(volume)
            snd.play()
        except Exception:
            pass  # 静默降级：提示音永远不打断主流程

    try:
        threading.Thread(target=_run, daemon=True).start()
    except Exception:
        pass
