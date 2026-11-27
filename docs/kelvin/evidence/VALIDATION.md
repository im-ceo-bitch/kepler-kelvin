# Evidence — Block 01
Date: 2026-11-27. Tests executed on temporary reconstructed snapshots, Linux, Python 3.13.5, Node v22.16.0. No production credentials or network calls to user accounts. Logs are test output, not real client data. All runtime changes were only prior uploaded patches overlaid in temporary copies; no code produced in block 01.

## Snapshot checksums (SHA-256)
```
3ec6eeb6e4b22921be137fbaf5c71e224c00dec81a568969e46d3710d11a2f8a  OpenJarvis-main.zip
36d83bd94adfd066ead268df8a757b5886f9e792ef218659fe0e3f9041d6ba12  kepler-maneger--main.zip
3b7bccbdd7ab819d62b3fa9fe7a50fe18817a2c019e289656161e1ff7dcf88fd  jarvis-update-kelvin-strategic-advisor.zip
fda66687415fbfadb21a961b77f1512072b43834c678f99554ae4e7d70f85b74  lattice-mobile-main 3.zip
24ac039eccaaa6ba2dd22016ce8cad8560b4aa7c2f019dde3f3ccf7f73c67331  iumrah-business-kelvin-sync-20261127.zip
de534204f35eb12563dfdad834fcc0efa5841be5dfa9732836da50c1081beb1b  iumrah-business-build-hotfix-20261127.zip
```
Original ZIP invalid central directory. Parsed 2501 local records sequentially through offset 44166935, size/CRC OK; remaining bytes begin central directory. 14 original workflow paths absent from recovered bootstrap; 0 content differences for corresponding files; 958 original `src/` files match user Kelvin snapshot. Other selected ZIPs passed Python ZipFile.testzip(). Full Git SHA not asserted. User's actual GitHub HEAD and runtime revision unknown.

## Tests actually run
From reconstructed Kelvin root:
```
PYTHONPATH=src:. python -m unittest discover -s founder_jarvis -p 'test_*.py' -v
# Ran 58 tests in 1.904s; OK. ResourceWarning unclosed SQLite connections seen.
PYTHONPATH=src:. python -m pytest -q tests/agents/test_orchestrator.py tests/scheduler/test_scheduler.py tests/memory/test_memory_service.py tests/security/test_security_wiring.py
# 127 passed, 2 failed in 4.28s; exit 1.
```
Failures: `TestComputeNextRun::test_cron_fallback`, `TestComputeNextRun::test_cron_honors_metadata_timezone` both because `croniter` unavailable. This establishes missing dependency in audit environment, not necessarily Mac defect. `ddgs`, `telegram`, `faster_whisper` also absent in this environment. Current test suite uses mocks for model/API; no real provider or voice test. `test_real_orchestrator_dispatch` invokes original Orchestrator with Mock completion/search. `test_real_scheduler` runs actual native scheduler with synthetic dispatch. Legacy tests cover code paths not all registered in current advisor mode. Do not equate test counts with all features live.

From reconstructed business `Backend/IumrahBackend`:
```
node --test tests/*.test.mjs
# 224 tests, 224 pass, 0 fail, 0 skipped; 4296.54 ms.
```
These include 4 Kelvin tests for isolated SQLite-backed mock D1, scoped role/device, shared turns, rotation/revoke, aggregate query coverage. They do not prove D1 production, actual cloud quota, Apple SDK or end-to-end synchronization. No iOS build executed here.

Logs: `kelvin-unit.log`, `openjarvis-selected.log`, `backend-summary.log` (summary plus test names, no production data).

## Reproduced observations (isolated temporary store; no live calls)
- `due_reports(datetime(..., hour, tzinfo=ZONE))`: h=7 none; 8 morning; 12 market; 17 market; 21 evening. Dispatcher dedup ID; all report slots set voice=True, runtime sends text chunks then voice. Late start after midday selects latest slot. This confirms report policy, not actual Telegram logs from user.
- `runtime.Store`: insert/finish 25 unique jobs; history returns 16; first visible `question 9`. Mark another as running and close/reopen Store; state becomes `interrupted` (not requeued).
- `business.safe_customer_reply`: identical clarification output for “Сколько стоит?” and “Сколько стоит из Ташкента 4 человека 10 декабря?”; automatic branch does not consult historical slots.
- Video files inspected: 10 distributed sampled frames per video, 80 total; no full audio transcription. The eight examples are requirements inspiration, not independently verified business outcomes.

## Not run / blockers
No live Telegram credentials, actual Claude/Ollama, internet market research from Kelvin, macOS launchd, target resource benchmark, actual D1, iOS SDK/TestFlight, RU/UZ speech listening test, or 72h soak. Existing screenshots from earlier turns demonstrate a working V3/V4 exchange but do not prove current reconstructed runtime is deployed. No real Instagram/Facebook integration performed. All future production assertions remain gated.
