# netwave

终端里的 API 延迟「电波图」——用 Braille 示波器波形实时监控本机到多个大模型 API 的 TCP 建连延迟。纯 Python 标准库，零依赖。

## 运行

    python3 netwave.py            # 用默认/已有配置
    python3 netwave.py -c my.toml # 指定配置文件

首次运行会在 `~/.config/netwave/config.toml` 生成默认配置（含 Anthropic / OpenAI / Google / DeepSeek）。

## 操作

- `q` 或 `Ctrl-C` 退出
- `p` 暂停 / 继续

## 配置

查找顺序：`-c 指定` → `./config.toml` → `~/.config/netwave/config.toml`。

    interval = 1.0          # 采样间隔(秒)
    timeout  = 2.0          # 建连超时(秒)

    [thresholds]
    green  = 100            # ms 以下为绿
    yellow = 250            # green~yellow 为黄, 以上为红

    [[targets]]
    name = "anthropic"
    host = "api.anthropic.com"
    port = 443

颜色：`<green` 绿、`green~yellow` 黄、`>yellow` 红；超时/失败显示红色满格尖刺并计入 loss。

## 测试

    python3 -m unittest discover -s tests -v
