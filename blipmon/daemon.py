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
    """取得单例锁。无锁时原子独占创建(赢得冷启动竞争)；锁属存活进程则让步；
    锁主已死或锁损坏则抢占。返回是否取得。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "x") as f:        # O_EXCL：原子独占创建，两进程只一个能赢
            f.write(str(os.getpid()))
        return True
    except FileExistsError:
        pass
    try:                                   # 锁已存在：持有者还活着就让步
        with open(path) as f:
            if alive(int(f.read().strip())):
                return False
    except (OSError, ValueError):
        pass
    with open(path, "w") as f:             # 锁主已死/锁损坏：抢占
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


async def _run_loop(config, state_path, heartbeat_path, idle_timeout,
                    stop=None, sampler=None):
    """每 interval 采样一次写状态文件；每轮检查是否该空闲自退。

    sampler 可注入以便测试（默认用 app.sample_tick 真实探测）。
    """
    sampler = sampler or sample_tick
    # 每目标留 60 个样本(约 60s 历史)；HUD 只读末 7 个，多出的备趋势/容错
    buffers = {t.name: SampleBuffer(60) for t in config.targets}
    while stop is None or not stop.is_set():
        await sampler(config.targets, buffers, config.timeout, config.mode)
        state = {
            "ts": time.time(),
            "targets": {t.name: buffers[t.name].values()
                        for t in config.targets},
        }
        hud.write_state(state_path, state)
        if should_exit(heartbeat_path, idle_timeout):
            return
        await asyncio.sleep(config.interval)


def daemon_main(config, idle_timeout=300.0):
    """取锁后跑采样循环（阻塞，供 `blip --daemon` 调用）。已有守护进程则直接退出。"""
    lock = hud.lock_path()             # 取一次，确保 finally 删的就是取的那把锁
    if not acquire_lock(lock):
        return 0
    try:
        asyncio.run(_run_loop(config, hud.state_path(),
                              hud.heartbeat_path(), idle_timeout))
    finally:
        try:
            os.remove(lock)
        except OSError:
            pass
    return 0
