---
description: 把 blip 一行延迟 HUD 接进 Claude Code 状态栏
---

把本插件自带的 blip 状态栏 HUD 装进用户的 Claude Code。插件已捆绑 `blip.pyz`
和入口脚本 `bin/blip-statusline`，**用户无需另外下载 blip**。按顺序做：

1. 入口命令：本插件的状态栏入口是 `${CLAUDE_PLUGIN_ROOT}/bin/blip-statusline`
   （`${CLAUDE_PLUGIN_ROOT}` 在本命令运行时已被替换成插件安装的绝对路径）。它跑
   捆绑的 `blip.pyz`，需要机器上有 Python 3.11+。

2. 选定要盯的目标：读 `~/.config/blip/config.toml` 取**第一个** target 名作默认
   （首次运行 blip 会自动生成含 anthropic / openai / google / deepseek 的默认配置，
   所以默认用 `anthropic` 也安全）；用户有偏好就问一下。

3. 读取用户的 `~/.claude/settings.json`（不存在则视为 `{}`）。如果里面**已有**
   `statusLine`（比如另一个 HUD 插件），先问清是**替换**还是**叠加**——叠加需要
   写个包装脚本同时跑两者、把两边输出拼成多行，别直接覆盖掉人家原有的。

4. 在**保留所有已有键**的前提下，写入/覆盖 `statusLine` 字段（用 JSON 安全合并，
   不要破坏文件其余内容）：

   ```json
   {
     "type": "command",
     "command": "${CLAUDE_PLUGIN_ROOT}/bin/blip-statusline <目标名>",
     "refreshInterval": 2
   }
   ```

   把 `${CLAUDE_PLUGIN_ROOT}` 写成真实绝对路径、`<目标名>` 换成第 2 步选的目标。
   **`refreshInterval` 不能省**：没有它，状态栏只在「有回复 / 切模式」等事件后刷新
   一次，迷你图不会自己往前走。

5. 写回 `~/.claude/settings.json`。

6. 告诉用户：
   - 已装好，**重开 / 刷新 Claude Code** 即可看到 `⟨blip⟩ <目标名> …`；
   - 换目标：改 `statusLine.command` 末尾的目标名；
   - 关闭：删掉 `settings.json` 里的 `statusLine` 字段；
   - 插件更新后安装路径可能变，重跑一次 `/blip-hud` 即可。

注意：Claude Code 插件无法直接注册状态栏，本命令是平台允许的半自动写入（把
statusLine 写进用户的 `settings.json`）。
