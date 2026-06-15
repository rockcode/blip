# 更新日志

版本遵循[语义化版本](https://semver.org/lang/zh-CN/)。查看版本：`python3 blip.py --version`。

## v1.0.0 — 2026-06-15

首个发布版本。

- 终端 Braille 示波器波形，实时监控本机到多个大模型 API 的连接延迟
- 测量方式可选 `tcp` / `tls`（默认）/ `http`；TLS 握手不受 TUN 代理就地应答的失真影响
- 四档颜色（亮绿 / 绿 / 黄 / 红）、丢包率、超时红色满格尖刺
- 纵轴固定上限、各单元同拍采样时间轴锁步对齐，便于横向对比
- TOML 配置（预置 Anthropic / OpenAI / Google / DeepSeek），首次运行自动生成
- 命令行单目标过滤：`python3 blip.py anthropic`（也可写 `-anthropic`）
- 流量监控（macOS）：检测到 `nettop` 自动显示每个 API 的实时上/下行速率（fake-IP 环境下准确）
- 纯 Python 标准库，零依赖；`q` 退出、`p` 暂停 / 继续
