# Content Factory / Block 01 — final local candidate, no Codex runtime

Owner decision: Codex is not part of the operating workflow. Claude Code is the primary intelligence provider. Ollama qwen2.5:3b may act as an explicitly enabled, narrow owner-chat fallback after a structured Claude HTTP 429. The fallback is labelled in the answer. The allowlist covers greetings, presence checks and synthetic acceptance probes, not offers, research, content generation or general business analysis. No fallback for authentication or transport failures. Existing explicit Ollama mode remains available in the underlying Kelvin code, but the activation command configures Claude primary. No new subscription, cloud service or model installation is required by this patch.

## Changes
- Based on the supplied final Kelvin core, Cloudflare User-Agent update, queue diagnostics update and the exact Codex-produced reserve patch from Block 01 evidence. The previous ChatGPT provider addition is superseded: runtime, advisor and native_advisor contain no Codex provider integration. Old optional Codex module files, if already copied, are inert and not required; this ZIP does not delete user files. Do not install the superseded provider patch after this update.
- Narrow fallback, explicit rate-limit error, queue completion + owner delivery receipt (probe IDs only, hash not answer text).
- Format-specific technical quality checks and review criteria; cannot authorize publication. Independent creative judgement remains required for Block 02.
- Added `founder_jarvis.macos.foundation_acceptance` for private config backup, explicit enablement of fallback, service restart and two unique owner-only synthetic messages. Does not use Telegram getUpdates, rotate pairing, modify existing business records, clear queues or deploy Workers. Refuses a busy queue and protocol mismatch. `--live` sends at most two test replies to the configured owner; checks persisted completion + successful Telegram send callback and exact expected word including history. This does not independently prove inbound Telegram update handling, which needs an actual owner message.
- Included an isolated candidate diff `compatibility/business-protocol7-candidate.patch` based on the archived v7 backend, NOT the newer Business Git HEAD described by Codex. Adds protocol in admin history and fenced release/bounded attempts when context assembly fails after claim. Never apply to a divergent revision without reviewing and retesting. Does not contain SwiftUI changes and is not a deployment ZIP.
- The complete local asset catalog, original canonical master spec, AGENTS.md, and prior creative documents remain untouched. This addendum supersedes previous provider instructions only. Block 02 not started.

## Independently executed here
- Kelvin 171/171 Python unittest tests, including actual upstream orchestrator with mocked Claude/Ollama completion, fallback scope, probe config and receipts. No real Claude/Ollama inference executed in this environment.
- Content Factory 10/10 Python tests.
- Archived Business v7 candidate 51/51 Node tests, including bounded context-failure retries and admin protocol.
- Actual Python Bridge ↔ JS Worker loopback fixture, pairing, memory, queue, idempotent finish, voice turn lookup, archive, revocation: PASS. Synthetic data only.
- Original FEM-8 MP4 SHA-256 a69fd4bc894ab171e26f39d32a324c81b450c7119e3c170543b25358fedb4c67. Full decode and format check PASS (1080×1920, 3 seconds, intentionally silent).

## Remaining real-world acceptance
The latest Mac working tree, active Claude quota, Ollama process, deployed Worker revision, Business UI and actual Telegram receipt cannot be directly accessed in this environment. Earlier Codex report confirmed local assets, actual inference on isolated Ollama, and live protocol 7, but not actual delivery. The exact Business HEAD 6fc543a is not supplied; its four failures are not claimed fixed. No production deployment was performed. Run the local acceptance command after installing this ZIP; if it reports passed, outbound owner delivery and shared queue are confirmed for two probe turns. Send an ordinary message to Kelvin to confirm real inbound delivery; a Claude limit still blocks professional work until it recovers. No claim of full production acceptance before these checks.

## Activation on Mac (explicit owner opt-in)
From the existing Kelvin checkout after updating:

```bash
cd ~/Kelvin
"$HOME/Library/Application Support/Kelvin/telegram-venv/bin/python" -m founder_jarvis.macos.foundation_acceptance --enable-reserve --live
```

The checker backs up private runtime.env when changing provider settings; leaves pairing and data intact. It stops on a busy queue, unknown protocol or failed probe; no retries of previous owner messages. The report contains only statuses/counts, not tokens. To avoid enabling fallback, use `--live` without `--enable-reserve` after restarting the existing service; this checks the currently configured provider.
