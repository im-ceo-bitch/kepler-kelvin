# Kelvin — local macOS deployment

Kelvin is the private Telegram interface built on OpenJarvis. This update leaves upstream files and GitHub workflows intact. The module name `founder_jarvis` and `JARVIS_*` configuration keys remain for compatibility.

## Requirements

- Intel or Apple Silicon Mac, macOS 14 or newer for current Ollama, enough free disk for Python dependencies and model weights, internet access to Telegram and model downloads.
- Git, uv, ffmpeg; Ollama installed from https://ollama.com/download/mac. If Homebrew is already present: `brew install uv ffmpeg`. Install Xcode Command Line Tools if needed. On Intel, Ollama uses CPU only; 3B is a starting choice, not a performance guarantee.
- Existing Telegram bot token and numeric owner ID. GitHub Actions secrets are not readable on the Mac. Stop any live test workflow before local polling.
- Ensure a Russian macOS system voice (Milena) is installed via Accessibility → Spoken Content/Read & Speak settings, or choose another installed Russian voice by editing `JARVIS_MAC_VOICE` in the local config. `say -v '?'` lists voices.

## Install

Clone the private repo to a permanent path or update the existing clone with `git pull --ff-only`. From the repo root:

```bash
bash founder_jarvis/macos/install.sh
sudo pmset -c sleep 0 displaysleep 5
```

Do not run the installer with sudo. Enter the bot token (hidden) and owner ID when asked. Existing private configuration is reused. Install checks dependencies and runs unit tests, local inference, TTS and a speech recognition round-trip before enabling the bot. It installs two user LaunchAgents: `com.kelvin.ollama` and `com.kelvin.manager`. Ollama binds to localhost when managed by Kelvin; an already-running local Ollama is reused.

Keep the lid open, AC adapter connected, and the user logged in. Screen may turn off or lock. LaunchAgents restart after a crash or login; they cannot start before login after a cold reboot or FileVault unlock. No service runs during actual sleep, loss of power or connectivity. Do not disable FileVault or enable auto-login just for this.

## Control

```bash
bash founder_jarvis/macos/control.sh status
bash founder_jarvis/macos/control.sh logs
bash founder_jarvis/macos/control.sh restart
bash founder_jarvis/macos/control.sh stop
bash founder_jarvis/macos/control.sh start
```

Stop command stops the bot only; Ollama remains available. To remove Ollama's user agent, run `launchctl bootout gui/$(id -u)/com.kelvin.ollama` and delete its plist if no longer needed. To undo sleep changes, restore prior power settings via System Settings or `pmset` (check `pmset -g custom` first). For future repository updates, stop Kelvin, pull the approved commit and rerun installer. No automatic execution of arbitrary new Git commits.

Private config, SQLite, logs and workspace are under `~/Library/Application Support/Kelvin/`. Do not commit them. Logs may contain sensitive diagnostics; do not publish without redaction. Back up data locally. SQLite retains queued jobs; interrupted jobs are marked interrupted rather than silently replayed. No cross-restart guarantee for Telegram messages interrupted before persistence.

## Acceptance in Telegram

1. `/start` and `/health` respond; send a text question and verify its content.
2. Send a Russian voice message and check the actual audio reply.
3. Ask to create a file with `/edit Создай test.txt со словом Kelvin`, then `/approve ID`. Confirm the file exists in the local workspace and request its content. `/gitstatus` is read-only; workspace defaults to an empty folder.
4. Restart the service, verify history and queued tasks remain. Test with the display locked and AC attached.

This update does not connect Claude Code, Xcode builds, full desktop controls, GitHub write APIs, Instagram, Cloudflare or scheduled business tasks. The original OpenJarvis source remains available for later audited integrations. No unrestricted shell execution or production publishing is enabled. The local model and its tools may make mistakes. The supplied unit tests and archive validation are not an actual macOS/Telegram integration run.
