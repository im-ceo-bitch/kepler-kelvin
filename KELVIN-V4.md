# Kelvin V4 — local MacBook runtime

This cumulative update includes V2 and V3 runtime changes. Keep the current GitHub unpacker and GitHub Secrets. No VPS or Homebrew required. Use the existing Claude CLI login for personal use, subject to provider terms and limits. Do not share API keys in Telegram or commit them to Git.

## Install/update

Upload `jarvis-update-kelvin-v4.zip`, check that the unpack workflow succeeds, then on the Mac:

```sh
cd ~/Kelvin && git pull --ff-only && bash founder_jarvis/macos/install.sh
```

The installer retains `~/Library/Application Support/Kelvin/runtime.env`, `data/jobs.sqlite3` and the speech environment. It registers a LaunchAgent under the current user. `caffeinate -s` prevents idle system sleep on AC while the agent runs. To also configure AC sleep independent of the agent:

```sh
sudo pmset -c sleep 0 displaysleep 5
```

Leave the lid open, power and internet connected, user logged in. Display lock is OK; logout, closed lid, power loss, shutdown and OS updates can interrupt availability. LaunchAgent starts again after login, not before FileVault unlock. Existing interrupted jobs are not replayed automatically (avoids duplicate external side effects). Queued jobs and due times are retained. `/result ID` retrieves stored responses after a Telegram delivery failure.

## Telegram acceptance

1. `/health`: version v4, Claude path, installed components and integration config status. This does not prove live external authentication.
2. Send a normal text question; no queue notifications for chat. `/voice Привет, Kelvin` sends text and voice. Send a fresh 5–10-second voice note. `/diagnose` runs a local TTS/STT loop, which may download Whisper weights if absent.
3. `/remember Мой проект называется iumrah`, then ask about the project in a separate chat message. `/memory` lists notes, `/forget ID` removes a note but not related historical messages. Last 16 successful chat turns and up to 20 recent notes are included as context; not unlimited semantic retrieval. SQLite is local, but included context and prompts are sent to Claude. Don't store secrets in it.
4. `/schedule 1 Напомни проверить проект` queues a durable one-off task. `/schedule 5 /gh runs OWNER/REPO` supports read-only tools. Scheduled tasks wait for a running Mac and available queue slot. `/cancel ID` cancels pending/queued tasks, not an already-running external operation.
5. `/mac status` checks system uptime, power and disk. `/mac open safari` followed by `/approve ID` opens Safari. `/mac url https://example.com` opens HTTPS URLs with approval. Opening an app is not unrestricted UI automation, clicks, typing or screen control.
6. `/research запрос` uses Claude web tools if available under the account; tool availability is not guaranteed.

## Connect existing projects once

Register the actual local directory of each Git repository (not the Kelvin repo itself or the private data directory):

```sh
cd ~/Kelvin
bash founder_jarvis/macos/connect.sh project iumrah "$HOME/path/to/iumrah"
bash founder_jarvis/macos/connect.sh project spyder "$HOME/path/to/spyder"
```

Replace example paths. `/projects` shows names. `/review iumrah задача` or `/work iumrah задача` -> `/approve ID`. Development requires a clean Git working tree; Kelvin makes a separate `kelvin/*` branch and asks Claude to use file tools. It reports Git status. No arbitrary Bash, no automatic deploy, no push to main. `/check iumrah` runs a supported project's existing npm/pytest/Swift Package test command after explicit confirmation. For Xcode project builds, use local Xcode or configure a tested command in future. `/gh commit iumrah сообщение` commits tracked changes in a kelvin branch, but rejects untracked files until you manually review and stage them. `/gh publish iumrah` pushes the clean kelvin branch, `/gh pr iumrah` creates a draft PR; each requires approval. Project operations run as your macOS user. Claude's tool permissions and prompt restrictions are NOT an OS-level sandbox. Register only trusted repositories, review code and test scripts, and never authorize untrusted changes. No API credentials inherited by developer subprocesses except user-level local credentials accessible to their native CLI. 

## GitHub

Install GitHub CLI if absent (official release: https://github.com/cli/cli/releases ; select macOS amd64 for Intel). Make `gh` available in PATH, e.g. `~/.local/bin`, then `gh auth login` and `gh auth status`. Git push additionally needs normal Git credentials. `/gh repos`, `/gh runs OWNER/REPO`, `/gh prs OWNER/REPO`. API access depends on account permissions. No automatic merging.

## Cloudflare

Requires installed Wrangler in the registered project's `node_modules/.bin` or PATH, and an explicit wrangler.toml/json/jsonc. Use existing `wrangler login` authorization or add a narrowly scoped API token locally:

```sh
bash founder_jarvis/macos/connect.sh cloudflare
```

`/cf status iumrah` lists deployments, `/cf deploy iumrah` requires explicit approval and clean Git tree. Verify target account, Worker and environment in repository config before approving; it may deploy to production. No automatic DNS or billing changes. 

## Instagram

Requires a professional Instagram account and Meta app using Instagram Login, the account ID, API version from the app dashboard, a valid access token and approved permissions for each requested action. This is not a Facebook Login adapter. Setup locally:

```sh
bash founder_jarvis/macos/connect.sh instagram
```

`/ig profile`, `/ig media`, `/ig comments MEDIA_ID`, `/ig insights MEDIA_ID`, `/ig inbox`, `/ig messages CONVERSATION_ID`. `/ig reply COMMENT_ID text` and `/ig dm USER_ID text` require a separate approval. Meta messaging policies and messaging windows apply. No scraping passwords, bulk unsolicited DMs, automated comment/DM responder, publishing or webhook monitoring. API results use one page; permissions, metrics and account type can affect results. Never post secrets in chat. Access tokens stored in local 0600 file, not the repository. The live APIs have not been tested against your accounts.

## Voice actions and security

Normal voice notes go to Claude and receive a voice response. A voice command must use the explicit prefix `команда` + English tool command and arguments (recognition of mixed Russian/English is not guaranteed); use text commands if uncertain. Voice never approves writes. For ordinary chat, Claude has no tools. Use explicit commands for real actions; no claim of unrestricted autonomous desktop operation.

All external mutations require `/approve ID` on a private owner chat. Do not approve operations you haven't reviewed. Use separate least-privilege credentials. Telegram ID check remains unchanged. The system cannot work if the Mac is off. This is a local integration release, not a certified production security audit.

Diagnostics: `bash founder_jarvis/macos/control.sh logs`, `/health`, `/diagnose`. Never share unsanitized logs. If an update fails, don't delete the database or runtime.env. Check `launchctl print gui/$(id -u)/com.kelvin.manager` first.
