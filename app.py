"""异步应用：探测调度、渲染循环、输入处理。"""
import argparse
import asyncio
import os
import sys
import termios
import tty

import ansi
import render
from buffer import SampleBuffer
from config import load_config
from probe import probe_tcp


async def probe_loop(target, buffer, interval, timeout, state):
    while True:
        if not state["paused"]:
            latency = await probe_tcp(target.host, target.port, timeout)
            buffer.add(latency)
        await asyncio.sleep(interval)


def _term_size():
    try:
        size = os.get_terminal_size()
        return size.columns, size.lines
    except OSError:
        return 80, 24


async def render_loop(config, buffers, state, out):
    while True:
        cols, rows = _term_size()
        lines = render.render_frame(config.targets, buffers,
                                    config.thresholds, cols, rows,
                                    paused=state["paused"])
        frame = ansi.HOME + "\r\n".join(
            line + ansi.CLEAR_LINE for line in lines) + ansi.CLEAR_BELOW
        out.write(frame)
        out.flush()
        await asyncio.sleep(config.interval)


def _handle_key(ch, state, stop):
    if ch in ("q", "\x03"):        # q 或 Ctrl-C
        stop.set()
    elif ch == "p":
        state["paused"] = not state["paused"]


async def run(config, out=None):
    out = out or sys.stdout
    buffers = {t.name: SampleBuffer(2000) for t in config.targets}
    state = {"paused": False}
    stop = asyncio.Event()

    tasks = [asyncio.create_task(
        probe_loop(t, buffers[t.name], config.interval,
                   config.timeout, state))
        for t in config.targets]
    tasks.append(asyncio.create_task(
        render_loop(config, buffers, state, out)))

    loop = asyncio.get_running_loop()

    def on_stdin():
        ch = sys.stdin.read(1)
        if ch:
            _handle_key(ch, state, stop)

    have_reader = sys.stdin.isatty()
    if have_reader:
        loop.add_reader(sys.stdin.fileno(), on_stdin)
    try:
        await stop.wait()
    finally:
        if have_reader:
            loop.remove_reader(sys.stdin.fileno())
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


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
