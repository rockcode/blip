# 更新日志

版本遵循[语义化版本](https://semver.org/lang/zh-CN/)。查看版本：`python3 blip.py --version`。

## v1.2.1 — 2026-06-15

- 修复插件 manifest：`plugin.json` 的 `author` 须为对象（`{"name": "rockcode"}`）而非字符串，否则 `/plugin install blip-hud@blip` 会因校验失败而装不上

## v1.2.0 — 2026-06-15

- 支持从 Claude Code **插件市场**安装：`/plugin marketplace add rockcode/blip` → `/plugin install blip-hud@blip`
- 插件**自包含**：捆绑 `blip.pyz` + `bin/blip-statusline` 入口，装上即用，无需 clone 仓库或手填路径（机器需 Python 3.11+）
- `/blip-hud` 安装命令改为指向插件内捆绑入口（经 `${CLAUDE_PLUGIN_ROOT}` 解析），并在检测到已有状态栏时询问替换 / 叠加
- 新增根 `.claude-plugin/marketplace.json`；`release.sh` 发版时同步重建 `plugin/blip.pyz`
- README 增加插件市场安装说明（中英）

## v1.1.1 — 2026-06-15

- 新增 MIT 开源协议（`LICENSE`、README 许可章节 + 徽章、`plugin.json` license 字段）
- README 增加状态栏 HUD 实际使用截图
- HUD 文档补充 `refreshInterval` 提醒：不设它状态栏只在事件后刷新、迷你图不会自动走
- 修复 `release.sh`：CJK 标点紧贴 `$VERSION` 在某些 locale 下导致变量名解析错误

## v1.1.0 — 2026-06-15

- 新增 Claude Code 状态栏 HUD：一行单目标延迟迷你波形（`blip --statusline`）
- 新增后台采样守护进程 `blip --daemon`：写 `~/.cache/blip/state.json`，单例锁、空闲自退、由状态栏脚本自动拉起
- 随附 `blip-hud` 插件壳（含半自动写入 `settings.json` 的安装命令）

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
