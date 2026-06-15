---
description: 把 blip 一行延迟 HUD 接进 Claude Code 状态栏
---

帮用户把 blip 的状态栏 HUD 装好。按顺序做：

1. 确认 blip 的调用方式：优先用单文件 `blip.pyz`（若存在），否则用
   `python3 <仓库>/blip.py`。把它解析成一个**绝对路径**的命令字符串，
   形如 `python3 "/abs/blip.py" --statusline anthropic`
   或 `"/abs/blip.pyz" --statusline anthropic`。
2. 读取用户的 `~/.claude/settings.json`（不存在则视为 `{}`）。
3. 在**保留所有已有键**的前提下，写入/覆盖 `statusLine` 字段：
   `{"type":"command","command":<上一步命令>,"refreshInterval":2}`。
   用 JSON 安全地合并，不要破坏文件其余内容。
4. 写回 `~/.claude/settings.json`。
5. 告诉用户：状态栏 HUD 已装好，重开或刷新 Claude Code 即可看到
   `⟨blip⟩ anthropic …`；要换目标就把命令末尾的 `anthropic` 改成别的
   目标名；要关闭就删掉 `settings.json` 里的 `statusLine` 字段。

注意：Claude Code 插件无法直接注册状态栏，这一步是平台允许的半自动写入。
