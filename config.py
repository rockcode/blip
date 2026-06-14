"""TOML 配置：解析、默认值、首次运行生成。"""
import os
import tomllib
from dataclasses import dataclass, field


@dataclass
class Thresholds:
    bright: float = 100.0    # <bright: 亮绿(极佳)
    green: float = 200.0     # <green:  绿
    yellow: float = 400.0    # <yellow: 黄；>=yellow: 红


@dataclass
class Target:
    name: str
    host: str
    port: int = 443


VALID_MODES = ("tcp", "tls", "http")


@dataclass
class Config:
    interval: float = 1.0
    timeout: float = 2.0
    mode: str = "tls"
    scale_max: float = 800.0   # 示波器纵轴上限(ms)，超过只在表头显示数值
    thresholds: Thresholds = field(default_factory=Thresholds)
    targets: list = field(default_factory=list)


DEFAULT_TOML = """\
# blip 配置
interval  = 1.0         # 采样间隔(秒)
timeout   = 2.0         # 建连超时(秒)
mode      = "tls"       # 测量方式: tcp(建连,极快但TUN代理下失真) / tls(握手,推荐) / http(首字节)
scale_max = 800         # 示波器纵轴上限(ms)，超过只在表头显示数值，以保证波形可读

[thresholds]
bright = 100            # ms 以下: 亮绿(极佳)
green  = 200            # ms 以下: 绿
yellow = 400            # ms 以下: 黄, 以上: 红

[[targets]]
name = "anthropic"
host = "api.anthropic.com"
port = 443

[[targets]]
name = "openai"
host = "api.openai.com"
port = 443

[[targets]]
name = "google"
host = "generativelanguage.googleapis.com"
port = 443

[[targets]]
name = "deepseek"
host = "api.deepseek.com"
port = 443
"""


def parse_config(data):
    """从已解析的 TOML dict 构建 Config（纯函数）。"""
    th = data.get("thresholds", {})
    thresholds = Thresholds(
        bright=float(th.get("bright", 100.0)),
        green=float(th.get("green", 200.0)),
        yellow=float(th.get("yellow", 400.0)),
    )
    mode = str(data.get("mode", "tls"))
    if mode not in VALID_MODES:
        raise ValueError(f"无效的 mode: {mode!r}，可选 {VALID_MODES}")
    targets = []
    for t in data.get("targets", []):
        targets.append(Target(
            name=str(t["name"]),
            host=str(t["host"]),
            port=int(t.get("port", 443)),
        ))
    return Config(
        interval=float(data.get("interval", 1.0)),
        timeout=float(data.get("timeout", 2.0)),
        mode=mode,
        scale_max=float(data.get("scale_max", 800.0)),
        thresholds=thresholds,
        targets=targets,
    )


def default_config_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "blip", "config.toml")


def find_config_path(explicit=None):
    """返回存在的配置路径，找不到返回 None。"""
    candidates = []
    if explicit:
        candidates.append(explicit)
    candidates.append(os.path.join(os.getcwd(), "config.toml"))
    candidates.append(default_config_path())
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return None


def ensure_default(path):
    """若 path 不存在则写入 DEFAULT_TOML，返回 path。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(DEFAULT_TOML)
    return path


def load_config(explicit=None):
    """从磁盘加载配置；首次运行生成默认配置。

    若显式指定了 explicit 路径却不存在，直接报错而非静默回退。
    """
    if explicit and not os.path.isfile(explicit):
        raise FileNotFoundError(f"配置文件不存在: {explicit}")
    path = find_config_path(explicit)
    if path is None:
        path = ensure_default(default_config_path())
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return parse_config(data)
