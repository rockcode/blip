import os
import tempfile
import unittest

from blipmon import daemon


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


if __name__ == "__main__":
    unittest.main()
