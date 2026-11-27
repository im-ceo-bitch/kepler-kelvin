# KELVIN — Personal Intelligence System
## Блок 01. Архитектурный аудит и проектирование
**Дата:** 27.11.2026 | **Статус:** аудит завершён в пределах доступного снимка; production readiness НЕ подтверждена. | **Scope:** только блок 1. Код runtime, workflows, базы и production не изменены.

### 1. Executive summary
Kelvin уже располагает работающим транспортным слоем, локальным сервисом macOS и адаптером к штатному Orchestrator. Однако он ещё не является непрерывным персональным интеллектом. Причина — использование отдельных классов OpenJarvis вместо связанного системного жизненного цикла, отсутствие семантической/структурированной памяти, устойчивого конвейера исследований и отдельного решения о том, что стоит сообщить владельцу. Новые функции нельзя добавлять поверх старых без устранения этих дефектов.

Цель: один личный советник основателя iumrah, действующий в пределах read-only аналитики и клиентского информирования. Не CEO, не программист, не платёжный агент. Telegram и Business — интерфейсы одного owner scope, а клиентские диалоги изолированы. Instagram/Facebook предусмотрены в архитектуре, но остаются отключёнными до отдельной авторизации и приёмки. Никаких обязательных новых расходов/VPS. Пользовательский приоритет — низкий уровень шума: исследовать много, сообщать только полезное.

**Решение:** сохранить оригинальное ядро, перейти на SystemBuilder/JarvisSystem там, где это подтверждено совместимостью; переиспользовать нативные memory, security, scheduler, tools и agents через узкие адаптеры. Не делать полную замену работающего Telegram/runtime за один релиз. Каждый этап вводится под feature flag и проверяется на тестовом профиле.

### 2. Происхождение и проверяемость
- `OpenJarvis-main.zip`: центральный каталог повреждён, но последовательно разобраны 2501 локальные ZIP-записи, проверены размеры и CRC32 каждой. Сравнение с `jarvis-repository-bootstrap.zip`: 0 различий для совпадающих путей; 14 оригинальных workflow отсутствуют по исходным путям (не считать их утратой ядра). Все 958 файлов `src/` восстановленной копии побайтово равны в `kepler-maneger--main.zip`.
- `kepler-maneger--main.zip`: исходный снимок пользовательского репозитория (2521 ZIP-запись). На отдельную временную копию наложен последний предоставленный накопительный `jarvis-update-kelvin-strategic-advisor.zip` (34 файла). Не утверждается, что это точный HEAD GitHub или текущая запущенная версия Mac.
- `lattice-mobile-main 3.zip` (1248 записей): отдельная временная копия, наложены `iumrah-business-kelvin-sync-20261127.zip` и `iumrah-business-build-hotfix-20261127.zip`. Это реконструкция доступного состояния приложения и backend, а не свежая копия production.
- Проверены исходники и локальная документация `docs/architecture/{overview,agents,memory,security,engine}.md`, `docs/user-guide/`, соответствующие реализации и целевые тесты. Внешняя документация использована для подтверждения архитектурного назначения и ограничений провайдеров, а не подмены проверенного снимка.
- Оригинальный проект называет себя research framework; `pyproject.toml` содержит `Development Status :: 3 - Alpha` и Python >=3.11,<3.14. Apache-2.0 (`LICENSE`): сохранить текст лицензии, применимые copyright/attribution и NOTICE, если присутствует; помечать изменённые upstream-файлы при распространении. Лицензии сторонних моделей/голосов/библиотек проверяются отдельно. Нельзя считать название/лицензию разрешением на сторонние API.
- Контрольные суммы исходников и результаты тестов — `evidence/VALIDATION.md`. Не проверены реальные секреты, аккаунты, Mac, состояние production, облачные тарифы пользователя, Xcode. Не запускались деплой, изменения D1 или API клиентов.

### 3. Видеореференсы (наблюдаемые сценарии, не доказательства реализации)
Из каждого видео извлечено и визуально изучено 10 кадров, распределённых по всему хронометражу (80 кадров). Смысл основан на видимых экранах, субтитрах и действиях; аудиодорожки не расшифрованы, точный полный диалог не подтверждён. Цифры на экранах авторов не считаются проверенной статистикой.

| Файл | Длительность | Что видно | Требование для Kelvin |
|---|---:|---|---|
| `-3601923450638992559.mp4` | 23.4 с | 3–21 с: приветствие, отчёт за ночь, показатели Reels/Telegram, подготовленные сценарии | Брифинг по результатам фактически завершённых задач и 1–3 приоритетам, ссылки/детали по запросу |
| `-3978724654095347106.mp4` | 28.5 с | 1–26 с: голосовое поручение, экран редактора, отчёт о публикациях и следующий вопрос | Сохранение состояния задачи, подтверждённые действия, естественное продолжение диалога. Монтаж и автопубликация вне scope |
| `-8333875040764747078.mp4` | 107.0 с | Заголовок о звонке в 2 AM; далее компьютер, панели бизнеса/рекламы | Событийная инициатива только при важном сигнале; не будить без критического повода. Технология звонка из видео не установлена |
| `3676276893286454582.mp4` | 71.9 с | 3–70 с: вопрос о продукте, данные за семь дней, реклама, результаты работы, ранее согласованное направление, выбор следующего действия | Метрики с периодом и источником; Decision Memory; рекомендация/вопрос вместо бесконтрольного управления |
| `437603588387363505.mp4` | 38.9 с | 1–38 с: интерфейс вызова Jarvis, беседа с узбекскими субтитрами, упоминание клиентов | RU/UZ, естественный диалог, follow-up, быстрый переход к клиентскому контексту. Обычный телефонный вызов отложен |
| `5626308994417756055.mp4` | 34.0 с | 5–31 с: голосовой интерфейс, запрос по контенту, упоминание количества комментариев и ключевого слова | Анализ содержания и аудитории, обоснованные выводы; не копировать цифры и не подключать Meta до согласования |
| `6739101813911960077.mp4` | 49.5 с | 2–48 с: панель контент-производства, отчёт за сутки, текущие потоки и результаты | Отслеживание фоновой деятельности и реальных результатов; не добавлять автономный контент-завод |
| `6959742332438456015.mp4` | 36.1 с | 9–21 с: `adewaskar/jarvis`, Claude Code, ElevenLabs; 25–33 с: пример вопроса о расписании | Интерфейс естественной речи и доступа к расписанию. Это иной репозиторий, не доказательство возможностей OpenJarvis |

Вывод: ценность — предварительная осведомлённость, естественная речь, завершённые действия с доказательством, выбор владельца. Не имитировать демонстрацию таймерами, не копировать панель, не обещать автоматические звонки или публикации. Полная расшифровка роликов не выполнялась.

### 4. Карта фактической архитектуры
```
Owner Telegram -> founder_jarvis/runtime.py -> Store SQLite (jobs, memory)
                    | если связан с iumrah
                    +-> shared_business.Bridge -> Cloudflare D1 (kelvin_turns/memory)
Business SwiftUI -> APIClient+Kelvin -> тот же D1 -> Mac poll/claim
                    | (обе ветки доходят до advisor.respond)
                    v
         новый subprocess native_advisor.py на запрос
                    -> OrchestratorAgent(mode=structured, max_turns=4)
                    -> ClaudeTransport -> execute_claude -> Claude CLI (cloud)
                    -> MarketSearch -> upstream WebSearchTool (4 фиксированные темы)
TaskScheduler -> 60-секундный tick -> due_reports -> очередь 08/12/21
Отдельный клиентский bot -> business.Service / Inbox SQLite -> FAQ/шаблон -> Telegram
                    -> owner_notices -> приватный Telegram (ручной перехват)
Голос: Faster Whisper subprocess -> текст; macOS say -> ffmpeg/OGG -> Telegram
```
Исходный OpenJarvis не заменён, но запускается только часть классов. `native_advisor.py` не создаёт `JarvisSystem`; `runtime.config_file()` явно выключает memory context, skills, MCP, learning, telemetry для старого CLI-пути; direct adapter не читает автоматически этот config. Профиль SOUL/USER/MEMORY, если создан вручную, не подключён к hardcoded SYSTEM в native_advisor. Подписка на Claude не равна локальным вычислениям.

### 5. Матрица функций (наличие кода ≠ activation ≠ acceptance)
Статусы: A — используется в реконструированном коде; P — частично/параллельная реализация; N — upstream есть, не подключён; G — нужна предметная интеграция; D — намеренно отключено. Ни один статус не подразумевает проверенный live production.

| Область | Оригинальный код | Текущее использование | Решение |
|---|---|---|---|
| Сборка системы | `system/builder.py`, `system/core.py`, `system/orchestrator.py`, `sdk.py` | N: прямой Orchestrator | Адаптировать `engine_instance`, `JarvisSystem.ask`; проверить совместимость в блоке 2 |
| Модели/движки | `engine/_stubs.py`, `engine/ollama.py`, `engine/cloud.py`, `_discovery.py`, `core/registry.py` | P: ClaudeTransport; Ollama резерв, не стандартный router | Один provider contract, выбор явно разрешённого движка, тест `generate/stream/health`, без тихого перехода в облако |
| Оркестрация | `agents/orchestrator.py`, `_stubs.py`, `loop_guard.py` | A: structured, 4 turns, один инструмент | Сохранить цикл и LoopGuard, добавить governed tools через системную сборку |
| Продвинутый research | `agents/deep_research.py`, `research_loop.py`, `tools/web_search.py`, `tools/browser.py` | P: только WebSearchTool/фиксированные темы | Не включать DeepResearch вслепую: ожидает `tool_calls`; проверить capability provider и public-only retrieval |
| Оперативные агенты | `agents/operative.py`, `monitor_operative.py`, `proactive_agent.py` | N | Использовать для ограниченных заданий с сохранением состояния и policy, а не автономного доступа ко всем инструментам |
| Утренний доклад | `agents/morning_digest.py`, `digest_store.py`, `tools/digest_collect.py` | N: отчёт через собственный prompt | Использовать upstream сбор/синтез после проверки источников, общий briefing delivery policy |
| Планировщик | `scheduler/{scheduler,store,tools}.py`, `agents/scheduler.py` | A: TaskScheduler как минутный tick; local due в Store | Один авторитетный scheduler; отдельные cron задачи с timezone, lease и idem-key; без двух dispatchers |
| События | `core/events.py`, `workflow/engine.py`, `agents/manager.py`, `executor.py` | N/P | EventBus + durable journal; EventBus сам по себе не durable. Переиспользовать lifecycle; workflow только при необходимости |
| Личность | `prompt/builder.py`, `core/config.py`, `cli/_bootstrap.py` | N: статический SYSTEM | SystemPromptBuilder + SOUL/USER/MEMORY как политика, не копии всех данных |
| Фактическая память | `memory/service.py`, `extractor.py`, `store.py`; `tools/memory_manage.py` | N: Store/D1 заметки вручную | FactExtractor/MemoryService + typed facts, подтверждение и lifecycle; no auto-facts из непроверенного ответа |
| Поисковая память | `tools/storage/sqlite.py`, `context.py`, `hybrid.py`, `connectors/retriever.py` | N | SQLite FTS5 сначала; retrieval с owner scope, проверка RU/UZ; не FAISS по умолчанию |
| Сессии | `sessions/session.py`, `compression.py`, `system/builder.py` | P: локальная/удалённая история | Одна логическая owner session; импорт локального прошлого с consent, курсор/идентификаторы, не двойная история |
| Безопасность | `security/{runtime,audit,boundary,injection_scanner,capabilities,rate_limiter,ssrf}.py`, `sandbox/` | P: owner check, env cleanup, regex redaction, whitelist; полный upstream stack не связан | `setup_security`, `wire_agent_security`, audit, rate limit, egress policy; default deny на все write tools |
| Skills/MCP | `skills/`, `mcp/`, `tools/mcp_adapter.py` | D/N | Только проверенные read-only skills и узкие tools; не импортировать неизвестный код автоматически |
| Trace/learning | `traces/`, `learning/`, `telemetry/` | D/N | Локальные обезличенные traces для диагностики; learning/самоизменение выключены до отдельного этапа |
| Telegram | `channels/telegram.py` (text handler), `channels/_stubs.py` | P: custom PTB transport с авторизацией/voice | Оставить тонкий адаптер PTB, один poller; связать с system channel contracts; штатный typing |
| Голос | `speech/faster_whisper.py`, `speech/voice_io.py`, `speech/kokoro_tts.py`, `tts.py` | P: Whisper subprocess + say/ffmpeg, iOS Speech | Переиспользовать discovery и backends, benchmark RU/UZ, потоковый session adapter отсутствует |
| API/UI | `server/`, `frontend/`, `desktop/`, `daemon/` | P: собственные iumrah SwiftUI и LaunchAgent | Не копировать весь upstream GUI; сохранить native iumrah UI, штатные API контракты и health lifecycle где подходят |
| iumrah данные | доменные API отсутствуют в OpenJarvis | P: фиксированные aggregate SQL в `Backend/HotelsWorker/src/kelvin.js` | Read-only бизнес tools, версионированные schemas/metrics и авторизация |
| Клиентский Telegram | upstream channel != готовый CRM | P: локальный Inbox, отдельный бот; в backend уже `core/telegram/care.js` | Использовать существующие Care thread/messages/mode, уведомления, approved KB; тестовый бот только стенд |
| Meta | `channels/messenger_channel.py` и custom `ig_events` не равны полноценной IG интеграции | D: IG отправка запрещена, FB нет | Отдельные официальные адаптеры после авторизации; не в текущем релизе |
| Звонки, WebRTC | `speech/` не содержит готового Kelvin live-call протокола | G | iOS streaming session сначала; звонки будущая опция, не обещать Bot API calls |
| Код/платежи/деплой | shell, file_write, claude_code, integrations | D: legacy код на диске, owner worker блокирует неподходящий mode | Не регистрировать, не давать сервисных ключей записи. Не удалять исходники upstream |

### 6. Реестр дефектов, рисков и доказательств
P0 — блокирует безопасный production; P1 — блокирует обещанную функциональность/стабильность; P2 — UX/оптимизация. Файл/функция указывают конкретное место в реконструированном снимке. «Воспроизведено» означает локальный тест; «статический риск» — вывод из кода, не подтверждённый инцидент.

| ID | Приоритет | Наблюдение и источник | Следствие / требуемое исправление |
|---|---|---|---|
| A01 | P1 | `native_advisor.answer`: создаёт новый Orchestrator на каждый запрос, `tools=[MarketSearch]`, hardcoded SYSTEM. `ClaudeTransport.generate` отбрасывает kwargs и возвращает лишь `content,usage={}`; `stream` выдаёт один полный результат | Нет общего tool calling/streaming provider contract; DeepResearch ожидает native `tool_calls`. Сборка через SystemBuilder, capability tests; structured fallback только для совместимых агентов |
| A02 | P0 | `native_advisor.py`, `advisor.respond`: прямой конструктор, нет системной wiring `setup_security` (ср. `system/builder.py:184–186`); `config_file` не передаётся в direct path | Whitelist защищает один tool, но нет полной data-boundary/audit/rate policy. Включить upstream security, enforce scope вне модели |
| A03 | P1 | `runtime.Store.history` LIMIT 16 по 1200 символов; `shared_business.answer_context` 20 обменов по 4000, 30 shared notes + 20 local; backend возвращает 40 прошлых turns | Воспроизведено: после 25 exchanges первый видимый — #9 (0-based). Забываются ранние решения, typed retrieval и управление устареванием отсутствуют |
| A04 | P1 | `runtime.remember/forget` и `kelvin.js:108–112`: две базы; INSERT OR IGNORE на ID без проверки несовпадающего content; delete notes не удаляет исходную переписку, нет edit | Единая логическая память, immutable source + versioned facts, явная correction/forget semantics, согласованная миграция и tombstones |
| A05 | P1 | `advisor.REPORTS`, `due_reports`, `runtime.dispatch` и `send`: 08/12/21; `want_voice=True`, полный текст порциями 1800 + голос (первые 1800), отдельный TTS error; startup notice при каждом init; scheduler выбирает последний прошедший слот | Воспроизведены три слота и late-start catchup. Статический источник шума. Нет relevance gate/digest cap/quiet hours/dedupe по смыслу, voice дублирует текст. Разделить research/report/delivery; утром короткий текст, вечер по результату, полдень молча, voice по запросу; startup только health log |
| A06 | P1 | `native_advisor.MarketSearch` кэширует 4 темы на один запрос, max_results=5, fixed queries, `re.findall` добавляет до 12 ссылок без сопоставления с утверждениями | Нет источников с датой/снимком/claim mapping, конкуренты не отслеживаются по списку и изменениям. Не считать search snippets независимой верификацией |
| A07 | P1 | `macos/install.sh` при отсутствующей .venv ставит httpx, но не гарантирует ddgs/croniter; upstream `web_search.py` импортирует ddgs, scheduler cron требует croniter | 2 upstream-теста упали в среде аудита из-за отсутствия croniter. Search может вернуть failure вместо результата, мок теста проходит. Pin/install capability manifest; fail visibly per feature, Telegram остаётся доступен |
| A08 | P1 | `runtime.Store.__init__` переводит running в interrupted; `advisor_dispatch` отметка после enqueue, не после delivery; shared finish -> notify с `except Exception: pass` | Воспроизведён interrupted после reopen. Локальные задачи не возобновляются, потеря исходящего уведомления возможна. Durable outbox/reconcile, lease/attempt/backoff и recovery semantics |
| A09 | P1 | `shared_business.loop` держит `model_lock` при claim/answer/finish; backend lease 900000 мс, без renew, при полной цепочке возможна потеря lease; heartbeat отдельно и ошибки подавлены | Нет приоритетов, интерактив может ждать фоновую работу; нужен deadline, ограничение размеров, renew/fencing и отдельный сигнал online/healthy |
| A10 | P1 | `kelvin.js:snapshot` 13 fixed aggregate queries + ID; нет выручки/конверсии/тренда/дат спроса, каталог != availability, coverage unknown | Не рассчитывать бизнес выводы из неполных данных. Metrics catalog: source, denominator, time window, missingness, freshness, coverage; контрактные тесты схем |
| A11 | P0 | Backend Care уже `Backend/IumrahBackend/core/telegram/care.js`: threads/messages, mode, staff send, dedup; Kelvin `business.Service.loop` отдельный getUpdates и Inbox | Конкурирующие источники истины. Не подключать existing Care токен к второму poller; интегрировать на уровне backend event + текущий send/handoff. Стенд изолировать |
| A12 | P1 | `business.safe_customer_reply` по regex; `Service._process` auto не использует `Inbox.history`, нет iumrah backend; `approved_local_reply` LLM выбирает FAQ без независимого confidence check | Воспроизведено: тот же вопрос про город/дату/число повторяется даже когда они уже указаны. Нужен structured slot context, approved KB retrieval + проверка фактов; неизвестные вопросы handoff |
| A13 | P0 | `business.Inbox.send`: отправка в состоянии sending, неопределённый результат -> uncertain; `Service.guard` serializes process/commands только внутри процесса; `owner_notices` ack после TG send | Полезная fail-closed основа; при неизвестном ack не повторять send, при аварии может потеряться или дублироваться уведомление. Backend transactional claim/fence, ручной/auto один authority; тест конкурентного перехвата и crash boundary |
| A14 | P1 | `thinking.py`: `send_message_draft` с пустым текстом, fallback typing. `runtime.send` chunks и TTS warning. iOS `KelvinView` pending включая queued | Принудительных GIF нет, но user требует исключительно sendChatAction; queued != thinking. Реальный статус очереди/ошибки/паузы; не показывать ложную активность |
| A15 | P1 | `runtime.Voice` язык `JARVIS_LANGUAGE` по умолчанию ru, STT отдельный процесс, TTS say; Swift `SFSpeechRecognizer(ru-RU)` + `requiresOnDeviceRecognition`, AVSpeechSynthesizer ru-RU | UZ качество не доказано, streaming не реализован, полудуплекс/без полноценного barge-in. Бенчмарк на Intel, codec/timeouts/cancel/permissions, деградация в текст |
| A16 | P0 | `execute_claude` передаёт owner history/snapshot удалённому CLI; `tools.clean_env`/redact не являются полным DLP. `ClaudeTransport.health` только env flag | Минимизировать передаваемые данные, прослеживаемость источников и egress, запрет клиентских PII/личных токенов; согласовать provider и terms, не обещать безлимитность |
| A17 | P1 | `service.py` LaunchAgent + caffeinate -s, KeepAlive, 30s throttle; install-status текст вместо end-to-end; `runtime.health` CLI existence | Не работает при выключении/до login, не гарантирует закрытую крышку. Health checks реальных компонент, watchdog с backoff и измерение RSS, log rotation/backup restore |
| A18 | P1 | `kelvin.js:75–94`: setup schema до проверки hash токена, claim всегда читает все агрегаты; D1 poll 6s/heartbeat15s, UI poll4s | Расход D1 при idle/лишние запросы; миграция схемы вне hot path, rate limit и backoff, lazy snapshot on demand, метрики запросов. Квоты аккаунта не проверены |
| A19 | P1 | `shared_business.Bridge.load` invalid link -> local mode; при рабочей связи, но недоступном backend owner enqueue error; no durable retry | Split-brain памяти/потеря запросов; явный degraded режим, local ingress/outbox с dedup, только один владелец состояния |
| A20 | P2 | `unpack-final.yml`: применяет распознанные архивы по лексикографическому имени, не проверяет base revision для update; workflow protection есть | Не загружать старые/новые патчи одновременно, нужен manifest expected base и rollback/runbook; в блоке 1 распаковщик не менять |

### 7. Ограничения источников и окружения
Отдельно от кода проверены официальные источники 27.11.2026:
- OpenJarvis: https://open-jarvis.github.io/OpenJarvis/architecture/overview/ и https://github.com/open-jarvis/OpenJarvis — framework и реестр компонентов; локальный снимок определяет версии.
- Anthropic: https://code.claude.com/docs/en/legal-and-compliance — продукты/сервисы должны соблюдать условия, API key рекомендуется разработчикам; локальная авторизация CLI пользователя не означает разрешение проксировать его подписку клиентам. Не использовать её для клиентского обслуживания. Разрешённость private programmatic сценария — условие выбора provider, не гарантируется этим аудитом.
- Ollama: https://github.com/ollama/ollama/blob/main/docs/macos.mdx — macOS Intel CPU only; GPU/Apple Silicon инструкции нельзя переносить на x86.
- Telegram: https://core.telegram.org/bots/api и https://core.telegram.org/bots/faq — Bot API для messages/actions, offset semantics; Telegram не является хранилищем безграничной очереди; звонки не объявлять рабочей функцией без поддерживаемого механизма.

### 8. Итог блока 1
Изменены только новые документы `docs/kelvin/`. Реализация ещё не начата. Результаты: 58/58 Kelvin, 224/224 backend, 127/129 выборочных upstream тестов (2 env failures). Четыре наблюдения локально воспроизведены: ограничение истории, interruption при рестарте, отчётные слоты, повторный шаблон вопросов. Полного анализа каждой из 958 исходных файлов как отдельных line-by-line review не проводилось; проверена целостность всех и глубоко изучены релевантные компоненты. Нет доступа к Mac/аккаунтам, поэтому ни один E2E критерий не принят. Следующий блок — Intelligence Core и долговременная память согласно ROADMAP. Не начинать его до сверки текущего HEAD и бэкапа локального состояния.
