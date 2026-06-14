"""异步应用：同拍采样调度、渲染、输入处理。"""
import argparse
import asyncio
import os
import sys
import termios
import time
import tty

import ansi
import render
from buffer import SampleBuffer
from config import load_config
from probe import measure


async def sample_tick(targets, buffers, timeout, mode):
    """同一拍并发探测所有目标，给每个缓冲区各追加一个采样（锁步对齐）。"""
    results = await asyncio.gather(*(
        measure(t.host, t.port, timeout, mode) for t in targets))
    for t, r in zip(targets, results):
        buffers[t.name].add(r)


def _term_size():
    try:
        size = os.get_terminal_size()
        return size.columns, size.lines
    except OSError:
        return 80, 24


def _draw(config, buffers, state, out):
    cols, rows = _term_size()
    lines = render.render_frame(config.targets, buffers,
                                config.thresholds, cols, rows,
                                paused=state["paused"],
                                scale_max=config.scale_max)
    frame = ansi.HOME + "\r\n".join(
        line + ansi.CLEAR_LINE for line in lines) + ansi.CLEAR_BELOW
    out.write(frame)
    out.flush()


def _handle_key(ch, state, stop):
    if ch in ("q", "\x03"):        # q 或 Ctrl-C
        stop.set()
    elif ch == "p":
        state["paused"] = not state["paused"]


async def tick_loop(config, buffers, state, out, stop):
    """主循环：每 interval 一拍。同拍并发采样所有目标后统一渲染一帧。

    所有目标在同一拍采样、各缓冲区锁步增长，因此各单元时间轴对齐——同一列
    在所有面板代表同一时刻，可横向对比不同目标的延迟，且快目标不会滚得更快。
    睡眠扣除本拍耗时，周期 = max(interval, 本拍最慢测量)。
    """
    while not stop.is_set():
        started = time.monotonic()
        if not state["paused"]:
            await sample_tick(config.targets, buffers,
                              config.timeout, config.mode)
        _draw(config, buffers, state, out)
        remaining = config.interval - (time.monotonic() - started)
        if remaining > 0:
            try:                       # 可被 stop 提前唤醒，按 q 即时退出
                await asyncio.wait_for(stop.wait(), timeout=remaining)
            except asyncio.TimeoutError:
                pass


async def run(config, out=None):
    out = out or sys.stdout
    buffers = {t.name: SampleBuffer(2000) for t in config.targets}
    state = {"paused": False}
    stop = asyncio.Event()

    loop = asyncio.get_running_loop()

    def on_stdin():
        ch = sys.stdin.read(1)
        if ch:
            _handle_key(ch, state, stop)

    have_reader = sys.stdin.isatty()
    if have_reader:
        loop.add_reader(sys.stdin.fileno(), on_stdin)
    try:
        await tick_loop(config, buffers, state, out, stop)
    finally:
        if have_reader:
            loop.remove_reader(sys.stdin.fileno())


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="blip", description="终端 API 延迟电波图")
    parser.add_argument("-c", "--config", help="配置文件路径")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    if not config.targets:
        print("配置中没有 targets，请在配置文件中添加。", file=sys.stderr)
        return 1

    fd = sys.stdin.fileno()
    is_tty = sys.stdin.isatty()
    old = termios.tcgetattr(fd) if is_tty else None
    try:
        if is_tty:
            tty.setcbreak(fd)
        sys.stdout.write(ansi.HIDE_CURSOR + ansi.CLEAR_SCREEN)
        sys.stdout.flush()
        asyncio.run(run(config))
    except KeyboardInterrupt:
        pass
    finally:
        if old is not None:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write(ansi.SHOW_CURSOR + ansi.RESET +
                         ansi.CLEAR_SCREEN + ansi.HOME)
        sys.stdout.flush()
    return 0
