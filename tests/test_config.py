import os
import tempfile
import tomllib
import unittest

import config


class TestParseConfig(unittest.TestCase):
    def test_defaults_when_empty(self):
        c = config.parse_config({})
        self.assertEqual(c.interval, 1.0)
        self.assertEqual(c.timeout, 2.0)
        self.assertEqual(c.thresholds.green, 100.0)
        self.assertEqual(c.thresholds.yellow, 250.0)
        self.assertEqual(c.targets, [])

    def test_parses_targets_and_thresholds(self):
        data = {
            "interval": 2.0,
            "thresholds": {"green": 50, "yellow": 150},
            "targets": [{"name": "x", "host": "h", "port": 8443},
                        {"name": "y", "host": "h2"}],
        }
        c = config.parse_config(data)
        self.assertEqual(c.interval, 2.0)
        self.assertEqual(c.thresholds.green, 50.0)
        self.assertEqual(len(c.targets), 2)
        self.assertEqual(c.targets[0].port, 8443)
        self.assertEqual(c.targets[1].port, 443)   # 默认端口

    def test_default_toml_is_valid(self):
        data = tomllib.loads(config.DEFAULT_TOML)
        c = config.parse_config(data)
        self.assertGreater(len(c.targets), 0)


class TestLoadConfig(unittest.TestCase):
    def test_ensure_default_creates_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "netwave", "config.toml")
            config.ensure_default(path)
            self.assertTrue(os.path.isfile(path))
            config.ensure_default(path)   # 幂等，不报错

    def test_load_explicit_path(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "c.toml")
            with open(path, "w", encoding="utf-8") as f:
                f.write('interval = 5.0\n[[targets]]\nname="a"\nhost="b"\n')
            c = config.load_config(explicit=path)
            self.assertEqual(c.interval, 5.0)
            self.assertEqual(c.targets[0].name, "a")


if __name__ == "__main__":
    unittest.main()
