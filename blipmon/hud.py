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


def write_state(path, state):
    """原子写：先写临时文件再 os.replace，避免读到半截 JSON。"""
    dirpath = os.path.dirname(path)
    if dirpath:                       # 裸文件名时 dirname 为 ""，makedirs 会报错
        os.makedirs(dirpath, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp, path)


def read_state(path):
    """读状态；文件缺失或损坏一律返回 None（渲染端据此显示启动中/兜底）。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def render_line(state, target_name, thresholds, scale_max,
                now=None, stale_after=STALE_AFTER, samples=HUD_SAMPLES):
    """组装 HUD 单行（含 ANSI）。state 为 read_state 的返回(可为 None)。

    - 无 state 或无该目标数据 -> "⟨blip⟩ <name> …启动中"
    - 数据过期(now-ts>stale_after) -> 整行变暗 + ⟨stale⟩ 标记
    - 正常 -> ⟨blip⟩ <name> <逐字符染色迷你图> <最新>ms
    """
    now = time.time() if now is None else now
    label = ansi.colorize("⟨blip⟩", ansi.GRAY)
    targets = (state or {}).get("targets", {})
    if target_name not in targets:
        return f"{label} {target_name} …启动中"

    series = targets[target_name][-samples:]
    if not series:                    # 已登记但还没样本(刚启动)：同样显示启动中
        return f"{label} {target_name} …启动中"
    ts = (state or {}).get("ts", 0)
    last = series[-1]
    last_txt = "--" if last is None else f"{last:.0f}"

    if now - ts > stale_after:
        plain_spark = "".join(block_for(v, scale_max) for v in series)
        plain = f"⟨blip⟩ {target_name} {plain_spark} {last_txt}ms ⟨stale⟩"
        return ansi.colorize(plain, ansi.DIM)

    spark = sparkline(series, scale_max, thresholds)
    last_col = color_for(last, thresholds)
    return (f"{label} {target_name} {spark} "
            f"{ansi.colorize(last_txt + 'ms', last_col)}")
