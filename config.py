"""TOML 配置：解析、默认值、首次运行生成。"""
import os
import tomllib
from dataclasses import dataclass, field


@dataclass
class Thresholds:
    green: float = 100.0
    yellow: float = 250.0


@dataclass
class Target:
    name: str
    host: str
    port: int = 443


@dataclass
class Config:
    interval: float = 1.0
    timeout: float = 2.0
    thresholds: Thresholds = field(default_factory=Thresholds)
    targets: list = field(default_factory=list)


DEFAULT_TOML = """\
# netwave 配置
interval = 1.0          # 采样间隔(秒)
timeout  = 2.0          # 建连超时(秒)

[thresholds]
green  = 100            # ms 以下为绿
yellow = 250            # green~yellow 为黄, 以上为红

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
        green=float(th.get("green", 100.0)),
        yellow=float(th.get("yellow", 250.0)),
    )
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
        thresholds=thresholds,
        targets=targets,
    )


def default_config_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "netwave", "config.toml")


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
