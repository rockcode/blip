"""Claude Code 状态栏 HUD：迷你延迟波形渲染 + 运行时状态文件读写。

与全屏交互模式解耦：daemon 写状态文件，statusline 脚本读并渲染成一行。
"""
import json
import os
import time

from . import ansi
from .render import color_for

BLOCKS = "▁▂▃▄▅▆▇█"      # 8 级方块，索引 0..7
HUD_SAMPLES = 7           # HUD 迷你图取最近几个样本
STALE_AFTER = 5.0         # state.json 超过这么多秒算过期


def cache_dir():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(base, "blip")


def state_path():
    return os.path.join(cache_dir(), "state.json")


def heartbeat_path():
    return os.path.join(cache_dir(), "heartbeat")


def lock_path():
    return os.path.join(cache_dir(), "daemon.lock")


def block_for(latency, scale_max):
    """把单个延迟映射到一个方块字符；None(超时/失败)渲成满格尖刺。"""
    if latency is None:
        return BLOCKS[-1]
    frac = 0.0 if scale_max <= 0 else min(1.0, latency / scale_max)
    idx = round(frac * (len(BLOCKS) - 1))
    return BLOCKS[idx]


def sparkline(values, scale_max, thresholds):
    """把延迟列表渲成逐字符染色的方块迷你图（含 ANSI）。"""
    return "".join(
        ansi.colorize(block_for(v, scale_max), color_for(v, thresholds))
        for v in values)
