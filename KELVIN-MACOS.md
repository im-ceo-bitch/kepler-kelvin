# Kelvin macOS v3 — Claude Code

Install from repository root: `bash founder_jarvis/macos/install.sh` as normal macOS user. Existing private configuration, job database, Ollama model and speech environment are retained. Normal text and voice requests use the installed Claude Code CLI under the existing local authentication, subject to Anthropic terms and usage limits. No credentials are copied from Claude or passed to Telegram. Normal Claude requests intentionally have no tools and do not load user/project customizations; prior completed conversation turns are supplied to Claude. `/local` and approved `/edit` use the existing OpenJarvis/Ollama scoped tools; their availability is not guaranteed. No unattended shell, publishing or GUI control is enabled. The local model is not downloaded during installation. Existing voice dependencies are reused; if unavailable voice may fail independently of text.

`/health` must show version v3 and `claude/default`. Test with a text message and then a new voice message. If the LaunchAgent is not registered, run `launchctl print gui/$(id -u)/com.kelvin.manager` and inspect its error log in `~/Library/Application Support/Kelvin/logs/` (redact secrets). Keep the Mac logged in, connected to power, lid open, and idle sleep disabled (`sudo pmset -c sleep 0 displaysleep 5`). No guarantee of execution while the Mac is asleep or off. Actual Claude authentication from launchd must be verified on the Mac.

## Current release
See [KELVIN-V4.md](KELVIN-V4.md) for installation and integration commands.
