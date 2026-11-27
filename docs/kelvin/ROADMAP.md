# Kelvin — технический план блоков 2–7
Дата 27.11.2026. Все пороги ниже — предлагаемые критерии приёмки, не текущие измерения. Каждый блок выполняется последовательно, отдельным коммитом/архивом с regression tests. Не объявлять следующий блок выполненным до получения его результатов. Блок 1 — документация, ни один production компонент не изменён.

## Правила этапов и gates
Перед блоком 2: получить актуальный snapshot двух репозиториев/commit SHA с Mac, проверить `git status`, сравнить с манифестом аудита, инвентаризировать активные services и feature flags без чтения секретов, снять backup локальных SQLite и план безопасной migration D1. Сохранить прежний рабочий runtime как rollback. Если текущий HEAD отличается, обновить аудит соответствующих файлов. Сборка upstream через lockfile, не менять оригинальный код без выявленного дефекта. Строго один Telegram poller. Все новые network calls только на тестовой среде и по авторизации. Интеграционный тест с настоящей моделью — только на Mac, со scoped тестовыми данными, в пределах утверждённого бюджета. Фикстуры разрешены только в тестах; в production отсутствующие данные обозначаются unknown.

Для каждого блока документировать: список файлов/новых адаптеров, upstream reuse, решение ADR и альтернативы, unit/contract/integration tests с raw counts/exit code, security review, resource delta, migration/rollback, remaining limitations. Gate: no open P0 for scope, tests green except documented environment blocker, acceptance matrix status PASS/FAIL/BLOCKED/NOT RUN with evidence. Реальные аккаунты/устройства не заменять mock-результатами.

## Блок 2. Intelligence Core + Persistent Memory
**Цель:** одна реальная agent session, общая память и проверяемая замена модели. Исправляет A01–A04, A16, A19.

1. Создать минимальный spike на `SystemBuilder.engine_instance`, `JarvisSystem.ask` и `OrchestratorAgent` со штатными tool resolver и security. Проверить standard engine `generate`, `stream`, `tool_calls`, timeout, usage, health. Для Claude CLI только утверждённый и соответствующий условиям личный режим; client-facing — approved local engine / отдельный согласованный provider. Не использовать native function-calling агент при отсутствии capability.
2. Подключить `SystemPromptBuilder` и существующий SOUL/USER/MEMORY. Зафиксировать role/policy, register только allowed tools. Модель не принимает решение о security.
3. Реализовать canonical owner identity + typed memory APIs в существующем backend; использовать upstream `FactExtractor`, `MemoryService`, `FactStore`, `SQLite/FTS5` для extraction/retrieval/projection. Durable decision/task/evidence records, источники, trust, version, supersedes, timestamps, delete semantics. Customer scope пока закрыт для owner extraction.
4. Сохранить историю Telegram и Business, предложить consented dry-run import legacy local history с дедупликацией. Без изменения бизнес-данных. Синхронизировать новые записи, выдавать offline state и исключить silent split-brain. UI/API list/correct/delete and audit. Событие удаления исключает повторное извлечение и учитывает retention/backups.
5. Миграция в staging; shadow сравнение с текущим runtime; переключение feature flag, rollback без потери истории.

**Файлы-кандидаты:** `founder_jarvis/native_advisor.py`, `advisor.py`, `runtime.py`, `shared_business.py`, thin memory/provider adapter, `Backend/HotelsWorker/src/kelvin.js`, migration SQL, Swift APIClient+Kelvin (контракт памяти только). Не менять native orb, workflow, customer bot.

**Критерии:**
- 40 сценариев natural intent и tool/no-tool: ≥38 корректных маршрутизаций; 0 denied/write tools executed; 0 ложных утверждений о выполнении.
- 100 typed facts + 100 distractor messages, минимум 20 cross-channel questions RU/UZ: ≥90% correct recall; 100% exact recall для owner-approved decisions и 20 corrections; source/time показаны по запросу. 20 forget сценариев — 0 recall удалённых записей после синхронизации и rebuild.
- 20 alternating Telegram ↔ Business exchanges, same owner session, 10 duplicate events, 3 simulated disconnects: 0 lost/duplicate canonical turns, offline state visible. 10 restarts restore tasks/notes. Не обещать message delivery exactly once при неопределённом ack.
- 30 cross-scope/secret/injection attempts: 0 leaks or denied tool execution. Audit all attempted tool calls; no raw credentials in logs.
- Switch local/cloud adapter in tests without editing core; provider failure explicit, no implicit paid fallback. Real Mac provider smoke in owner's test session required.

## Блок 3. Автономность, события, исследования
**Цель:** проактивность без информационного шума. Исправляет A05–A09, A14, часть A17–A19.

1. Использовать `TaskScheduler/SchedulerStore`, native `EventBus` и `LoopGuard` с durable job ledger; один scheduler, cron timezone, owner priority, retry/backoff/jitter, lease/fencing, cancellation. Native event bus не durable, добавить journal только для этого gap. Приоритетные owner interactive requests не голодают за research. Cap runtime and persisted model budget; provider usage unknown tracked as unknown.
2. Включить `Operative`/`MonitorOperative`/`ProactiveAgent` как policy-limited профили после проверки capabilities; `DeepResearchAgent` только при совместимом provider tool_calls. Иначе проверенный штатный structured loop + source retrieval. Не дублировать loop, не включать все агенты параллельно.
3. Создать конфиг research topics и competitor watchlist: рынок UZ, Umrah/Hajj, конкуренты, seasonal demand, travel tech, публичные соцсигналы. WebSearchTool, vetted fetch/Browser after security test, source metadata, independent evidence, dedup, diff, freshness; сохранить research and tasks в канонической памяти. Не использовать данные владельца как public query. No private account automation. User-defined watchlist can be edited.
4. Morning Digest pipeline and delivery gate; утренний 08:00, midday research internal, evening 21:00 computed but normally archived unless actionable or opt-in. Critical events policy, quiet hours, no startup noise, one catch-up. Standard typing only. Separate customer notices and explicit user replies from proactive cap.
5. Scheduler health metrics, daily cost quota and manual pause. Research result unavailable != negative finding. Never present snippets as verified claim.

**Файлы-кандидаты:** `founder_jarvis/advisor.py`, `native_advisor.py`, `thinking.py`, `runtime.py`, thin event/delivery adapters, existing upstream scheduler/research config, D1 task/outbox migration if needed. Upstream source unchanged unless necessary.

**Критерии:**
- 24h simulated clock, 08/12/21, sleep 6h, missed slots, duplicate ticks, time-zone change, 10 crash/restarts: exactly one scheduled job per slot, ≤1 catch-up, 0 report floods, safe read tasks resume, uncertain send not retried blindly.
- 100 synthetic ordinary/important/critical events + 20 duplicates: ordinary queued/digested only, every verified critical routed once or marked uncertain, no duplicates within cooldown, quiet-hours obeyed; cap automatic non-customer routine notifications ≤2/day, morning ≤900 chars, midday zero, voice not duplicated. Important rule precision ≥90% on owner-reviewed set.
- 30 research claims: 100% linked source or explicit hypothesis/unknown; ≥90% source supports claim by human review, 0 invented citations or numbers. ≥5 monitored competitors with baseline + verified diff, not fabricated results. No-data/network-failure tests.
- Daily budget ≤ configured cap (proposed 20 autonomous calls), per-task turn cap and no runaway loops, 100 idle ticks cause 0 inference calls unless due job. 20 retry/failure cases bounded. p95 dispatch due delay ≤60s when Mac idle and online (test on target).

## Блок 4. Бизнес-аналитика и стратегическое мышление
**Цель:** знания о реальном iumrah, а не общие советы. Исправляет A10, A18 и бизнес-часть A16.

1. Review existing `Backend/IumrahBackend`, `Backend/HotelsWorker`, booking/chat/Care/events schemas; define read-only scoped metric contracts. Compute counts, cohorts, status movement, demand by dates, package category, support topics, conversion and refusal reasons only where schema/evidence exists. Avoid PII, avoid duplicate overlapping chat events. Expose metric metadata and freshness; snapshot only needed fields, cache bounded TTL, not every question.
2. Create governed iumrah tools via upstream BaseTool/registry; no arbitrary SQL, service token not D1 admin. Connect existing package estimate endpoint only if read-only verified, returns quote validity/constraints; not booking tool.
3. Decision/Recommendation workflow: compare goals to observed KPI, identify bottlenecks and alternative explanations, propose one concrete action/metric/timeframe. Store owner decisions and follow-up outcomes, evaluate previous recommendation instead of repeating it. If no real statistics, ask a targeted question.
4. Integrate research evidence with business metric data; brief output short, detailed report stored in Business. Sources/date available on demand. Guard against relying on unconfirmed prices or availability.

**Файлы-кандидаты:** backend `kelvin.js`, `router.js`, existing read-only queries, metrics contract/test fixtures, Kelvin business tool adapter and retrieval config. No writes to booking/payment/inventory tables. Migrate only Kelvin-specific state on staged database.

**Критерии:**
- 25 fixed metric fixtures with independently calculated expected values: 100% correct or explicit unknown; period, source, as_of and denominator valid. 10 missing/partial/overlap cases: no double count/no fabricated zero. Real read-only staging snapshot compared to existing dashboard (same filter/period) for at least 5 metrics, mismatch explained before release.
- 20 scenario evaluations: ≥18 actionable recommendations linked to evidence and KPI; 0 unsupported claims/prices/commitments; at least 5 scenarios challenge a wrong owner assumption with evidence. 10 decision follow-ups recall prior reasoning and outcome or mark unknown.
- 50 denied attempts (SQL injection, arbitrary paths, mutations, PII, cross-owner): 0 forbidden responses or writes. DB read queries measured; no full aggregate snapshot for casual greeting. Validate D1 quota/usage estimate and idle polling before production.

## Блок 5. Коммуникации и передача диалога
**Цель:** Kelvin — коммуникационный мост, не управляющий. Исправляет A11–A13.

1. First Telegram Care test environment: reuse `core/telegram/care.js`, existing thread/message tables, current staff reply/handoff and official Telegram API. Implement event adapter and durable reply/outbox using existing authoritative mode; do not switch existing bot webhook without explicit staged cutover. No separate production SQLite client inbox. Keep test bot as isolated fixture.
2. Scoped customer policy; local model intent/slot extraction + verified FAQ/backend evidence. Answer naturally RU/UZ, contextual clarifications, no repeat questions when answered, unknowns escalate. Customer text is untrusted, no tools/owner memory. Safe fallback; only confirmed facts can be sent.
3. Notification after confirmed meaningful answer: client message, exact sent reply, channel, summary, Take/Resume/History. Manual reply uses existing Care and flips auto off. Generation fencing and atomic claim, race tests; already in-flight cannot be unsent, notify honestly. Outbox retry uncertain notice separately from customer send; avoid stale/duplicate prompts. New events while held no automatic reply. Explicit resume only.
4. Instagram/Facebook adapters later via official API, permission review, signature, message/comment rules, rate limit and scopes. Not connected now, default off, credentials absent not error. User must separately authorize activation; if disabled, production-readiness for Telegram can be accepted without claiming Meta live.

**Файлы-кандидаты:** `Backend/IumrahBackend/core/telegram/care.js`, existing staff endpoints (review exact routes), Kelvin customer adapter `founder_jarvis/business.py`, `shared_business.py`, notification outbox. Separate integration tests; no modification of live conversations during implementation.

**Критерии:**
- 60 scripted customer conversations (30 RU, 30 UZ), multi-turn price/dates/unknown/service questions: ≥90% appropriate grounded reply/clarification, 100% no invented price/availability/booking, 0 repeat slot requests when provided, all uncertain facts escalated. Bilingual human review; threshold on quality not just exact templates.
- 30 repeated events/restarts/failed sends: ≤1 attempted automatic external send for same event; no blind retry on unknown ack. 20 takeover races: 0 new automated sends after confirmed human takeover, correct in-flight status; 20 resume cases only new events. Every confirmed meaningful response has matching persisted owner notice. Any notification failure tracked, not swallowed. 30 client injection/cross-customer tests: 0 leaks/forbidden action.
- Real test bot end-to-end: client send -> reply -> owner notification -> takeover -> manual reply -> no auto -> resume. At least 10 conversations and owner approval before real Care activation. Existing Care continues to operate; rollback restores its normal routing without lost events.

## Блок 6. Голос и iumrah Business
**Цель:** естественное, общее для каналов общение, не анимация вместо интеллекта. Исправляет A14–A15 и UI/reliability части.

1. Benchmark candidate STT/TTS on Intel Mac and iPhone. Reuse upstream `speech/faster_whisper.py`, discovery, native speech where supported; compare RU and UZ real samples, noise and names, latency, quality, RAM and licensing. No obligatory paid provider. If Uzbek natural TTS not supported, explicit text/available voice fallback; no false claim.
2. Voice messages: audio download/limits/codec, STT language identification or selectable language, shared text turns, TTS bounded, failures visible, cancellation. Voice briefing optional. Raw audio retention minimal, user consent.
3. Live session: streaming STT partial/final, streaming LLM tokens or honest non-streaming fallback, TTS chunks, VAD/end-of-turn, cancellation/barge-in, backpressure, auth/sequence/reconnect. Use existing gateway, no public Mac port. Native SwiftUI/AVAudioEngine UI, approved `KelvinVoiceOrb.swift` kept identical for reference mode; real audio/state values only. Owner identity/history same in Telegram and Business.
4. Business UI: conversations, tasks, research, decision recommendations, briefings and state; proper offline/queued/running/researching/speaking/error. Actual activity events, accessibility, retry/abort. Telegram plain typing, no forced GIF/stickers/draft. VoIP/phone call design only; no Telegram Bot API direct calls assumed.

**Файлы-кандидаты:** `founder_jarvis/speech_worker.py`, `runtime.py`, upstream speech adapter config, voice-session endpoints, `Sources/Networking/APIClient+Kelvin.swift`, `Sources/Views/KelvinView.swift`, `KelvinVoiceOrb.swift` only if audio input wiring needed (geometry unchanged), platform entitlements/privacy descriptions. No new dependencies without review.

**Критерии:**
- 40 consented reference utterances (20 RU/20 UZ, mix dates/numbers/names and noise), targets WER ≤20% RU, ≤30% UZ; critical date/amount exact match ≥95% or request confirmation; ≥4/5 median intelligibility for TTS from owner/bilingual listener; report raw scores and limits. Benchmark p50/p95 latency/RSS on Intel Mac; if unmet, documented choice/owner approval, not pretend.
- Target STT 10s utterance p95 ≤8s on Mac; live first transcript p95 ≤1.5s and first spoken response after end-of-turn p95 ≤5s on stable network with selected model; barge-in stops output ≤300ms p95. 20 interruption/reconnection tests, no stale speech after cancel. Targets measured, revise only with owner approval.
- 10 alternating voice/text turns across Telegram/iOS preserve context; 20 microphone permission/offline/error scenarios reflect real state. iOS build/testflight green on actual SDK and real devices, no orphaned audio session, no forced background recording. Visual parity checked separately at same sizes/phase, 60fps target with thermal/energy measurement; not promised without run.

## Блок 7. Интеграционное тестирование и эксплуатация
**Цель:** доказать качество, стабильность, безопасность на фактическом Mac and iumrah staging. All remaining A01–A20 checked.

1. Full dependency reproducibility, installed capability report, licenses, pinned upstream revision/hash, signed/verified patch manifest and rollback runbook. No Homebrew hard requirement Intel. `launchd` regular user, service lock, backoff, graceful shutdown, log rotation, no secret logs; inspect actual registered PID and heartbeat. Backup encryption/retention, restore drill; staged migration dry-run.
2. Run all unit, upstream relevant suites, backend contract and adversarial tests, iOS build, real Telegram/Claude/search/Cloudflare staging smoke. Evaluate memory, research, recommendation quality with test rubrics. Budget and quotas check. No production write actions. User authorizes activation of client auto replies separately.
3. 72h soak with screen locked, AC, user logged in, network interruptions, process kill and restart, sleep/resume and reboot (login). Measure RSS/CPU/thermal/battery and app responsiveness, queue lag, number of LLM calls, delivery counts, faults. No claims of availability during power-off. Keep model resident only if measurements justify.
4. Gate review: owner validates behavior (concise advisory, trustworthy suggestions, no noise), release with canary mode, read-only fallback, manual disable and rollback. Daily reports archived and critical exceptions only. No external paid service without approval.

**Критерии:**
- 0 P0/P1 open defects in release scope; 100% required tests pass on target environment; optional Meta and future phone calls clearly disabled/not accepted. Full regression ≥58 Kelvin + ≥224 backend existing (new test counts increase, do not count old dead tests as coverage); selected upstream suite all pass once dependencies installed.
- 72h online test: ≥99% service availability during *Mac awake + network reachable* eligible time, no unplanned manual intervention; 0 critical lost accepted tasks; 0 duplicated confirmed customer responses; restart recovery target ≤60s after login/service dependencies ready; backlog recovery bounded, no stale flood. Measure actual outage windows.
- RAM budget initial target idle Kelvin resident ≤600 MB excluding model, total peak Kelvin + local model ≤4 GB (measure aggregate process tree), no sustained swap thrash, no uncontrolled CPU loop; if target not feasible, lower concurrency/change model. No guarantee that Intel GPU is supported. No new recurring mandatory paid infra. Quota exhaustion yields graceful degraded state.
- ≥50 security attempts across scopes, credential redaction and SSRF; 0 successful unauthorized action/secret leaks; audit chain verify where upstream logger supports it. 3 restore drills, 0 missing accepted committed records within defined RPO; proposed RPO ≤24h backups, local task recovery from persisted state, RTO ≤30m, verify actual.
- 3 full days of user-reviewed briefings; ≥80% recommendations marked useful/actionable, 0 unsupported factual claims, notification cap respected, owner can disagree and system remembers decision. This subjective gate supplements objective tests, does not substitute for them.

## Status board
| Block | State | Gate |
|---|---|---|
| 1 Audit | Documented; snapshot reconstructed | Review baseline + remaining access gaps |
| 2 Core/memory | NOT STARTED | Provider contract, cross-channel retrieval, scoped safety |
| 3 Autonomy/research | NOT STARTED | Recovery, no spam, factual evidence, budget |
| 4 BI | NOT STARTED | Verified metric contracts and advice |
| 5 Communications | NOT STARTED | Telegram Care E2E and takeover; Meta disabled |
| 6 Voice/UI | NOT STARTED | RU/UZ benchmark, real streaming, Xcode/device tests |
| 7 QA | NOT STARTED | 72h soak, security, restore, owner acceptance |

Next action: validate exact snapshot + backup before implementing block 2. Do not launch new production code from the audit archive.

## Статус блока 2 (27.11.2026)
Реализация-кандидат подготовлена; локальные тесты пройдены, реальные acceptance gates открыты. См. BLOCK-02-IMPLEMENTATION.md. Блок 3 не начат.

## Статус накопительного выпуска 02–03 (27.11.2026)
См. BLOCK-03-IMPLEMENTATION.md. Локальная реализация и регрессии блоков 02–03 завершены в пределах описанного scope; остатки (нативная семантическая память, verified page diff, human review, croniter environment, live integration и target resource metrics) остаются открытыми gates. Блоки 04–07 не начаты. Не считать production-ready.

## Статус накопительного выпуска 02–04 (27.11.2026)
Блок 04: реализация-кандидат, локальные регрессии 127 Python / 245 backend PASS. См. BLOCK-04-IMPLEMENTATION.md и evidence/block04-*.log. Реальный D1, модельные стратегические сценарии, производительность Mac и production gates открыты. Блоки 05–07 не начаты. Промежуточная установка не требуется для следующего локального этапа.

## Статус накопительного выпуска 02–05 (27.11.2026)
Блок 05: реализация-кандидат. 137 Python / 260 backend PASS (локальные тесты). Канонический Telegram Care, ручной перехват и уведомления. Полный живой диалог RU/UZ, реальная интеграция и критерии приёмки открыты; Meta отключены. См. BLOCK-05-IMPLEMENTATION.md. Блоки 06–07 не начаты; промежуточная установка не требуется.

### Block 06 implementation update
See `BLOCK-06-IMPLEMENTATION.md`. Turn-based foreground conversation, shared exact-turn lookup and local playback/recognition are implemented in the patch. The acceptance gate is open (real-device build, 40 real RU/UZ recordings, latency, interruption and quality). Full token streaming/full-duplex are not implemented; no production deployment. Block 07 not started.
