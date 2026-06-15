"""后台采样守护进程：周期测延迟写状态文件；单例锁；空闲自退。

statusline 脚本会在无守护进程时静默拉起它；它检测心跳文件，长时间
没人读(Claude Code 已关)就自退，不留僵尸进程。
"""
import asyncio
import errno
import os
import subprocess
import sys
import time

from . import hud
from .app import sample_tick
from .buffer import SampleBuffer


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
    except OSError as e:
        return e.errno == errno.EPERM   # EPERM=存在但非本用户；ESRCH=已消失
    return True


def acquire_lock(path, alive=_pid_alive):
    """取得单例锁。已有存活进程持锁则返回 False，否则写入本进程 pid 返回 True。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path) as f:
            old = int(f.read().strip())
        if alive(old):
            return False
    except (OSError, ValueError):
        pass
    with open(path, "w") as f:
        f.write(str(os.getpid()))
    return True


def daemon_running(path=None, alive=_pid_alive):
    """锁文件里的 pid 仍存活则认为守护进程在跑。"""
    path = path or hud.lock_path()
    try:
        with open(path) as f:
            pid = int(f.read().strip())
        return alive(pid)
    except (OSError, ValueError):
        return False


def should_exit(heartbeat_path, idle_timeout, now=None):
    """心跳文件不存在或 mtime 超过 idle_timeout 秒 -> 该退出。"""
    now = time.time() if now is None else now
    try:
        mtime = os.path.getmtime(heartbeat_path)
    except OSError:
        return True
    return (now - mtime) > idle_timeout


def daemon_command(program=None, executable=None):
    """重拉守护进程的命令：用当前解释器跑当前程序 + --daemon。"""
    program = program or sys.argv[0]
    executable = executable or sys.executable
    return [executable, program, "--daemon"]


def spawn_daemon():
    """以分离的后台进程启动 `blip --daemon`（输出全部丢弃）。"""
    subprocess.Popen(
        daemon_command(),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL, start_new_session=True)
