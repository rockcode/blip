import errno
import os
import tempfile
import unittest
from unittest import mock

from blipmon import daemon
from blipmon import hud as _hud
from blipmon.config import Config, Target, Thresholds


class TestPidAlive(unittest.TestCase):
    def test_current_process_is_alive(self):
        self.assertTrue(daemon._pid_alive(os.getpid()))

    def test_eperm_means_alive(self):
        # 进程存在但属于别的用户 -> 视为存活，不可抢锁
        with mock.patch("os.kill", side_effect=OSError(errno.EPERM, "denied")):
            self.assertTrue(daemon._pid_alive(1))

    def test_esrch_means_dead(self):
        # 进程不存在 -> 可抢锁
        with mock.patch("os.kill", side_effect=OSError(errno.ESRCH, "no proc")):
            self.assertFalse(daemon._pid_alive(424242))


class TestLock(unittest.TestCase):
    def test_first_acquires_second_rejected(self):
        p = os.path.join(tempfile.mkdtemp(), "daemon.lock")
        self.assertTrue(daemon.acquire_lock(p))      # 写入当前 pid(存活)
        self.assertFalse(daemon.acquire_lock(p))     # 当前 pid 仍存活 -> 拒

    def test_stale_pid_can_be_reacquired(self):
        p = os.path.join(tempfile.mkdtemp(), "daemon.lock")
        with open(p, "w") as f:
            f.write("424242")                        # pid 值不重要：alive 已注入为 False
        self.assertTrue(daemon.acquire_lock(p, alive=lambda pid: False))


class TestDaemonRunning(unittest.TestCase):
    def test_no_lock_means_not_running(self):
        p = os.path.join(tempfile.mkdtemp(), "daemon.lock")
        self.assertFalse(daemon.daemon_running(p))

    def test_live_pid_means_running(self):
        p = os.path.join(tempfile.mkdtemp(), "daemon.lock")
        with open(p, "w") as f:
            f.write(str(os.getpid()))
        self.assertTrue(daemon.daemon_running(p, alive=lambda pid: True))


class TestShouldExit(unittest.TestCase):
    def test_missing_heartbeat_exits(self):
        self.assertTrue(daemon.should_exit("/no/such/hb", 300, now=1000))

    def test_fresh_heartbeat_stays(self):
        p = os.path.join(tempfile.mkdtemp(), "heartbeat")
        open(p, "w").close()
        os.utime(p, (1000, 1000))
        self.assertFalse(daemon.should_exit(p, 300, now=1100))

    def test_old_heartbeat_exits(self):
        p = os.path.join(tempfile.mkdtemp(), "heartbeat")
        open(p, "w").close()
        os.utime(p, (1000, 1000))
        self.assertTrue(daemon.should_exit(p, 300, now=2000))


class TestDaemonCommand(unittest.TestCase):
    def test_command_shape(self):
        self.assertEqual(
            daemon.daemon_command(program="/x/blip.pyz", executable="/py"),
            ["/py", "/x/blip.pyz", "--daemon"])


class TestRunLoop(unittest.IsolatedAsyncioTestCase):
    async def test_writes_state_then_exits_when_idle(self):
        tmp = tempfile.mkdtemp()
        state_p = os.path.join(tmp, "state.json")
        hb = os.path.join(tmp, "heartbeat")   # 不创建 -> should_exit 立即为真
        cfg = Config(interval=0.0, timeout=0.1, mode="tcp",
                     targets=[Target("a", "h"), Target("b", "h")])

        async def fake_sampler(targets, buffers, timeout, mode):
            for t in targets:
                buffers[t.name].add(123.0)

        await daemon._run_loop(cfg, state_p, hb, idle_timeout=300,
                               sampler=fake_sampler)
        st = _hud.read_state(state_p)
        self.assertEqual(st["targets"]["a"], [123.0])
        self.assertEqual(st["targets"]["b"], [123.0])
        self.assertIn("ts", st)

    async def test_loop_output_renders_through_render_line(self):
        # 跨接缝集成：daemon 写的状态文件能被 render_line 正确渲染
        # (能抓到 writer/reader 间的 key 名漂移，如 targets vs target_samples)
        tmp = tempfile.mkdtemp()
        state_p = os.path.join(tmp, "state.json")
        hb = os.path.join(tmp, "heartbeat")
        cfg = Config(interval=0.0, timeout=0.1, mode="tcp",
                     targets=[Target("anthropic", "h")])

        async def fake_sampler(targets, buffers, timeout, mode):
            for t in targets:
                buffers[t.name].add(42.0)

        await daemon._run_loop(cfg, state_p, hb, idle_timeout=300,
                               sampler=fake_sampler)
        st = _hud.read_state(state_p)
        line = _hud.render_line(st, "anthropic", Thresholds(), 800,
                                now=st["ts"])
        self.assertIn("anthropic", line)
        self.assertIn("42ms", line)
        self.assertNotIn("启动中", line)


class TestDaemonMain(unittest.TestCase):
    def test_releases_lock_on_exit(self):
        # daemon_main 退出后必须删掉锁，否则会一直挡住后续守护进程启动
        tmp = tempfile.mkdtemp()
        lock = os.path.join(tmp, "daemon.lock")

        async def fake_sampler(targets, buffers, timeout, mode):
            for t in targets:
                buffers[t.name].add(1.0)

        with mock.patch("blipmon.hud.lock_path", return_value=lock), \
             mock.patch("blipmon.hud.state_path",
                        return_value=os.path.join(tmp, "state.json")), \
             mock.patch("blipmon.hud.heartbeat_path",
                        return_value=os.path.join(tmp, "heartbeat")), \
             mock.patch("blipmon.daemon.sample_tick", fake_sampler):
            cfg = Config(interval=0.0, timeout=0.1, mode="tcp",
                         targets=[Target("a", "h")])
            rc = daemon.daemon_main(cfg)   # 心跳缺失 -> 采样一轮即退出
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists(lock))


if __name__ == "__main__":
    unittest.main()
