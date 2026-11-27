# Kelvin V5 — Personal + Business (MacBook)

Cumulative over V4. No VPS. Preserve local Telegram token, owner ID, Claude CLI authorization, memory, jobs, registered projects and V4 integrations. No secrets in Git. No workflow replacement. Install from the updated repo:

```sh
cd ~/Kelvin && git pull --ff-only && bash founder_jarvis/macos/install.sh
```

## Personal

Send natural text or voice, e.g. «Зайди в мою инсту», «Покажи список репозиториев», «Проверь состояние Mac», «Открой Safari», «Покажи деплои iumrah». One validated tool per request; external writes still need typed `/approve ID`. Existing slash commands remain. Instagram profile requires configured Meta access; opening a browser is separate from obtaining API data. No arbitrary desktop UI or unrestricted shell. Natural routing can misunderstand ambiguous requests, so check approvals. Model must return JSON; malformed output does not execute anything. Use `/health`, `/start`, `/projects` as needed. Voice input follows the same natural router; voice replies remain macOS TTS.

## First connect a separate customer Telegram bot

1. Create a bot in @BotFather for iumrah support (not @KelvinManagerBot).
2. On Mac in ~/Kelvin run `bash founder_jarvis/macos/connect.sh business telegram` and paste the new token privately. Validates getMe, refuses an existing webhook and the owner bot token.
3. Send `/start` or a question to the customer bot from a test account. The private owner bot receives a numbered inbox item. `/biz pending`, `/biz show ID`, `/biz reply ID текст`, `/biz approve ID`, `/biz dismiss ID`. Manual reply actually sends to the customer; approval sends the stored draft. Telegram polling is separate from the owner bot, using durable offsets. Only private text messages are ingested; voice and attachments for customers are not yet implemented. No group or personal-account automation.

## Connect Instagram

1. Use a professional account with a Meta app configured for Instagram Login (not Facebook Login). Obtain its professional account ID, API version and access token with required permissions, including `instagram_business_basic` and `instagram_business_manage_messages`; comments/insights require their own permissions. Depending on app/account roles and access level, review and verification may be required. See https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api and Meta App Dashboard. Do not use a password or copy browser cookies.
2. Run `bash founder_jarvis/macos/connect.sh instagram`. Enter the requested values locally. Test «Зайди в мою инсту» or `/ig profile` in the private bot.
3. Run `bash founder_jarvis/macos/connect.sh business instagram` and enter Meta App Secret. Save the generated webhook verification token privately; this command rotates it if repeated.
4. Restart `bash founder_jarvis/macos/control.sh restart`. `/biz status` should say webhook listens on localhost. Create a stable Cloudflare Tunnel route, for example a dedicated subdomain you own -> `http://127.0.0.1:8765`. Install the official cloudflared Intel macOS binary, follow the dashboard instructions and configure it as a persistent service. See https://developers.cloudflare.com/tunnel/get-started/ and https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/as-a-service/macos/. Tunnel setup is external and is not automatic in this update. Do not expose other ports or the private runtime. Configure webhook URL `https://YOUR-HOST/instagram` in Meta, provide the verification token and subscribe to messaging events for the Instagram account. The webhook verifies Meta HMAC signature before persisting inbound events. No Cloudflare Access login on the webhook route; signature is the origin authentication. Test using a second permitted account. Meta messaging rules apply: automatic standard replies only within 24 hours of the inbound event (local cutoff 23.9h). No bulk/unsolicited DMs. If a send fails or times out, review inbox manually; no blind retry. Text DMs only for automatic ingestion; comments remain V4 manual tools.

## Configure approved FAQ and optional AI

Run `bash founder_jarvis/macos/connect.sh business faq`, then edit the printed local JSON path. Start with an empty array; insert real verified business answers, not placeholder prices. Format:

```json
[{"questions":["Привет","Здравствуйте","Salom"],"answer":"Здравствуйте! Чем можем помочь?"}]
```

Use separate entries for each language and intent. Exact normalized question match only (case/punctuation ignored). By default all replies require owner review. When FAQ is reviewed, `bash founder_jarvis/macos/connect.sh business auto-on` allows automatic sending of the exact approved FAQ answers. `auto-off` disables it. In-flight requests may still finish. Unknown questions are handed to the owner. No autonomous invented prices, bookings or payments.

Optional free local AI drafts: `bash founder_jarvis/macos/connect.sh business local` uses the already installed qwen2.5:3b via localhost Ollama, only if Ollama is running. Intel CPU can be slow. Optional Claude API drafts: `bash founder_jarvis/macos/connect.sh business ai` requires a separate Anthropic API key and model ID from console. Customer traffic is not routed through the private Claude Code subscription. Both generate drafts only, not automatic free-form responses. Customer text and approved FAQ are sent to Anthropic only when that provider is enabled; review your privacy disclosures and lawful processing before enabling. Local mode avoids sending customer text to the model provider. The business database is separate from personal history, but runs under the same macOS user (not an OS-level security sandbox); restrict Mac access and protect backups. No secrets/customer documents in FAQ. Real pricing and bookings need a separate authenticated iumrah backend integration with explicit endpoints and business policy; not included.

## Cloudflare / GitHub / Mac

V4 integration instructions remain in KELVIN-V4.md. Configure Wrangler or `bash founder_jarvis/macos/connect.sh cloudflare`; register actual local repos with `... connect.sh project iumrah /actual/path`; authorize GitHub CLI locally. These are prerequisites, not automatic access to every account. Use least privilege. No auto-deploy/merge. Personal Claude Code authorization must stay valid and is subject to vendor terms/limits; do not use personal login to provide Claude-powered services to customers.

## Verification and rollback

`/health` shows V5, `/biz status` shows configuration and worker poll status, not proof that all APIs are authorized. Test actual owner text, voice, an approved safe tool action, customer Telegram inbound and outbound, then a signed Meta webhook and reply. Test auto-FAQ on a test account before enabling on public channels. No credentials or live APIs tested in CI. Keep Mac on AC, open lid, logged in, internet connected; LaunchAgent/caffeinate are retained. If Mac sleeps or loses connectivity both modes stop. No full production SLA or security audit. To disable customer automation use auto-off, or stop Kelvin with control.sh stop. Keep private data and don't delete databases to troubleshoot. Customer records remain local in business.sqlite3; establish retention and access policies before real client use. No automatic CRM/booking integration, account creation, publishing, or marketing campaigns included. 
