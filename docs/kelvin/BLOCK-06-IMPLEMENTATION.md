# Kelvin — Block 06: Voice Experience & iumrah Business

## Status and scope
Implementation prepared on reconstructed archives (original `kepler-maneger--main.zip`, `lattice-mobile-main 3.zip`, cumulative Block 02–05 patches). GitHub HEAD, production, Xcode build and real devices were not accessible. No changes were made to live services. Block 07 has not started. This is a foreground, turn-based voice session, not a full-duplex call or streamed LLM response. Speech quality acceptance is open.

## Architecture
- Single identity and agent: original OpenJarvis SystemBuilder / JarvisSystem / Orchestrator and shared D1 queue retained from earlier blocks; no new parallel agent or history.
- iOS/iPadOS/Catalyst: SwiftUI KelvinLiveView, SFSpeechRecognizer partial/final recognition, AVAudioEngine microphone input, AVSpeechSynthesizer PCM rendering, AVAudioPlayer playback with actual audio meter. Apple on-device recognition is mandatory; if the selected locale is unavailable, no silent cloud fallback. Text and Telegram are alternatives. Audio is not uploaded by the app; only the finalized transcript goes to the same existing owner-authenticated message endpoint. The device's selected TTS voice is used; no new paid API.
- Telegram: existing isolated faster-whisper subprocess and macOS `say` / ffmpeg voice path retained. Existing local `Voice` is adapted rather than replaced; original upstream OpenJarvis speech modules were inspected but not wired in this block because the current path already isolates heavy dependencies and controls CPU threads. `VoicePreferences` persists explicit RU/UZ preference in a 0600 local file. Runtime and speech subprocesses no longer inherit bot secrets on the synthesis path. `/language ru`, `/language uz`, `/language` (status); language controls current local STT/TTS setting, not a guaranteed supported installed voice. In-flight requests may use current preference at playback time.
- `/api/admin/hotels/kelvin/turn` (POST `{id}`): owner/session protected, exact ID lookup, no new schema or duplicate history. The `voice` boolean in history marks transcripts. Existing queue uses idempotent request IDs. No public inbound Mac port. The Mac continues processing requests after the UI is closed if they were accepted.
- The approved `Sources/Views/KelvinVoiceOrb.swift` is byte-identical to supplied standalone reference, SHA-256 `d15c1cf0fff40e698283fd7a506b75f71c23d0894d87c550f2537ce0f010ac59`. No animation changes. Audio levels reflect captured RMS or actual playback power, not timers. Running is shown only after backend status `running`; waiting remains idle. TTS preparation has distinct text status.

## Voice flow and failure policy
1. Owner opens Kelvin voice sheet, selects language and explicitly taps microphone. Permissions/capability checks precede recording. Partial text is displayed locally. Capture is bounded to 45 seconds and auto-ends after 1.6 seconds quiet following recognized text; no speech timeout stops it. User may end the phrase manually.
2. Only final recognition is auto-submitted. Incomplete recognition is not silently sent; a transcript review button permits explicit submission. Duplicate/retry uses same request ID. Polling is bounded by time and count, backs off after initial checks. Failure is visible; no simulated progress.
3. After a real `done` response for the active ID, native TTS renders up to the first 1800 characters into small chunks (maximum 240 characters per chunk), preserving full text in shared history. Playback meter drives orb. The device renders one chunk before playing it; no LLM token streaming, audio streaming over the network or voice identity cloning. If TTS fails, text remains available. A different language voice is not silently substituted.
4. User may tap microphone to stop current playback and begin a new phrase; old request completions do not automatically speak. This is tap-to-interrupt, not hands-free full-duplex barge-in. An already accepted server job is not cancelled by local pause. Optional auto-continue re-arms the microphone after completed playback only while the sheet is foreground and session is active. Pause, close, app leaving foreground, auth loss and audio interruption stop capture/playback. Permission dialogs may require pressing the mic again after returning to active state. Temporary PCM files are deleted on normal completion/cancel; crash leftovers may remain in app tmp until OS cleanup; add explicit startup cleanup in Block 07 if needed.
5. Telegram remains on standard activity indicator; no forced sticker/GIF. No changes to Care activation, Facebook/Instagram, payments or production write permissions.

## Changed files (delta from cumulative Block 05)
### Kelvin
- `founder_jarvis/runtime.py`: RU/UZ preference, voice status and sanitized TTS subprocess environment; cap fallback Whisper CPU threads.
- `founder_jarvis/voice_preferences.py`: atomic persisted language setting.
- `founder_jarvis/voice_benchmark.py`: local speech benchmark with WER, timings, real-time factor, peak child RSS; optional TTS generation check.
- `founder_jarvis/test_voice_preferences.py`: nine tests for settings, secrets, language forwarding and benchmark accounting.
- `founder_jarvis/macos/install.sh`: Block 06 label and test registration; existing setup retained.
- `docs/kelvin/voice-benchmark-phrases.json`: 20 RU and 20 UZ business phrases.
- `docs/kelvin/BLOCK-06-IMPLEMENTATION.md` and `docs/kelvin/evidence/block06-*`: this report and logs.
### iumrah Business
- `Sources/Views/KelvinSpeech.swift`: native speech and real playback meter.
- `Sources/Views/KelvinLiveView.swift`: foreground voice dialog, queue fencing, interruptions, UI language selector.
- `Sources/Views/KelvinVoicePolicy.swift`: pure bounded playback segmentation, meter normalization, exact-response matching.
- `Sources/Views/KelvinView.swift`: integrate voice sheet and history badge, retain old chat/memory/research views.
- `Sources/Networking/APIClient+Kelvin.swift`: exact-turn query and voice metadata.
- `Backend/HotelsWorker/src/kelvin.js`: owner-scoped exact-turn endpoint and voice metadata.
- `Backend/IumrahBackend/tests/kelvin.test.mjs`: added end-to-end local database test for voice queue/ownership/idempotency/history window.
- `Tests/KelvinVoice/VoicePolicyCheck.swift`: executable pure Swift checks (outside application target Sources).
- `KELVIN_VOICE_BLOCK_06.md`: integration notes.

## Validation results
Actual tests run in Linux reconstruction:
- `PYTHONPATH=src:. python -m unittest discover -s founder_jarvis -p 'test_*.py'`: 146 passed (prior 137 + 9 new); prior SQLite unclosed-resource warnings remain.
- `node --test tests/*.test.mjs` in Backend/IumrahBackend: 261 passed (prior 260 + 1 new), zero failures/skips. Uses SQLite test double, not live D1.
- `swiftc ... KelvinVoicePolicy.swift KelvinVoiceOrb.swift VoicePolicyCheck.swift`: executable built and passed pure checks (bounded RU/UZ text segmentation, meter edge cases, stale response matching, unchanged mathematical constants). These are not acoustic tests.
- Swift frontend syntax parse for changed Swift files succeeded; Linux lacks Apple SDK, full SwiftUI/AVFoundation typecheck and Xcode archive NOT performed. Original orb byte comparison succeeded. `bash -n` installer succeeded.
- Benchmark invoked with no recordings: 20+20 cases missing, measured 0/40, WER and latency null, exit 2 as intended. No claim of real voice quality or a validated optimal voice provider. No new external paid service selected. Previously chosen ElevenLabs voice is not activated by this patch.

## Real acceptance: Block 06 gate still open
On target iPhone and Intel Mac after cumulative install (or staging):
- Confirm Xcode iOS archive and Catalyst compile; verify owner-only voice and revoked-session failure. Confirm microphone/speech permissions, language support on installed OS, real synthesis callback behavior, audio route changes, interruption and cleanup. Test at least 20 consecutive turns and 10 interruptions; no previous response should start after a new turn begins; no duplicate queue entries. Verify background/close stops audio promptly and shared history remains accessible via both interfaces.
- Record each manifest phrase as `<id>.wav` (20 RU + 20 UZ) on real device. Run on Mac (no bot access needed): `cd ~/Kelvin && "$HOME/Library/Application Support/Kelvin/telegram-venv/bin/python" -m founder_jarvis.voice_benchmark /path/to/recordings --tts --output ~/kelvin-voice-benchmark.json`. Measure WER/latency and compare to target agreed in Block 01: propose WER <= 20% RU, <= 30% UZ as initial acceptance thresholds, user approves quality; measure p50/p95 end-to-end and RSS in real sessions. A missing locale/voice is a blocker, not a pass. For subjective voice quality, listen to all samples; verify intelligibility and naturalness with Uzbek speaker. Existing macOS TTS may lack UZ entirely. The `--tts` check tests generation, not naturalness.
- End-to-end latency includes queue wait, Claude and TTS. Current architecture returns completed text only; no claim of low-latency full duplex. Streaming LLM, true automatic barge-in, on-device UZ fallback through Mac STT, wake-up calls, and selected premium voice require additional implementation/evaluation; don't represent these as finished. Do not add paid services without approval.
- Block 07 should also cover full-stack security, load, long-run reliability, backup/restore, outstanding items from Blocks 02–05. Deploy only after snapshot comparison, D1 backup and staged testing; keep customer automation disabled until acceptance. No VPS required for current architecture, but Mac must be awake/connected for reasoning.
