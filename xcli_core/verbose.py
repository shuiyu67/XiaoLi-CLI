"""
启动详情开关

默认启动只报结论（加载了几个引擎/几个工具），不再逐条刷屏。
需要看每个插件/技能的加载明细时，加 --verbose（或 -v），
也可以设环境变量 XCLI_VERBOSE=1。
"""
import os
import sys

_TRUTHY = ('1', 'true', 'yes', 'on')


def is_verbose() -> bool:
    """是否输出启动明细"""
    if any(a in ('--verbose', '-v') for a in sys.argv[1:]):
        return True
    return str(os.environ.get('XCLI_VERBOSE', '')).lower() in _TRUTHY


def vprint(*args, **kwargs):
    """仅在 --verbose 时打印的 print"""
    if is_verbose():
        print(*args, **kwargs)
