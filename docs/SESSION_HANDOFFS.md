# Session Handoffs

> **Purpose**: Enable seamless continuity across chat windows, Claude Code sessions, and multi-agent workflows.
> **Format**: Append-only log. Each session appends a dated entry. Never delete or overwrite previous entries.
> **Authoritative for**: What was worked on, what's done, what's in progress, what's blocked, uncommitted decisions.

---

## How to Use This File

**Starting a new session**: Read the most recent entry to understand current state.
**Ending a session**: Append a new entry using the template below.
**Multi-agent workflow**: Each agent reads the latest entry before starting and appends its own entry when done.

### Entry Template

```
---

## YYYY-MM-DD — <Brief session description>

**Interface**: [Claude.ai WebUI | Claude Code | Claude API | Other]
**Duration**: ~Xh
**Branch**: <git branch name>

### Completed
- <What was finished and committed>

### In Progress
- <What was started but not finished — include file paths and current state>

### Blocked / Needs Decision
- <What can't proceed without input>

### Key Decisions Made
- <Any architectural or design decisions made this session>

### Refactor Candidates
- <2nd-instance patterns created this session: pattern name, file1, file2>
- <Empty section is fine — forces conscious check>

### Files Modified
- <List of files created, modified, or deleted>

### Next Steps (Priority Order)
1. <Most important next action>
2. <Second priority>
3. <Third priority>

### Notes for Next Session
- <Anything the next session needs to know that doesn't fit above>
```

---

## Session Log

## 2026-02-15 — DRY violation fixes: Items 1.1–1.5

**Interface**: Claude Code
**Branch**: main

### Completed
- Item 1.4: Generic config validation helper — `_required_type()` replaces `_required_decimal()` and `_required_int()` in orchestration/config.py (13 call sites)
- Item 1.2: Symbol mapping factory — `create_translator()` in venues/symbol_translator.py, used by both Kraken and Coinbase symbol modules
- Item 1.3: Fee schedule fixture factory — `fee_schedule_factory` in tests/conftest.py, 3 named fixtures refactored as thin wrappers
- Item 1.1: BaseAsyncConnector ABC — shared constructor, venue property, and `_fetch_with_retry()` in connectors/connector_base.py. KrakenClient and CoinbaseClient inherit from it. 13 new tests.
- Item 1.5: Deferred timestamp extraction with TODO comment per Coding Rule 10.1
- Documented: DEC-018, LL-059, CHANGELOG, SESSION_HANDOFFS

### In Progress
- Nothing

### Blocked / Needs Decision
- Nothing blocked

### Key Decisions Made
- DEC-018: BaseAsyncConnector returns raw httpx.Response from _fetch_with_retry(); subclasses handle parsing
- Unified 429 retry handling across both connectors (Kraken previously did not retry on 429)
- Pre-existing dead code in Coinbase client (LL-059) eliminated by design, not explicitly fixed

### Behavioral Changes
- Kraken connector now retries on HTTP 429 (previously did not). No test covered this case. Pure improvement.
- Both connectors now log retries at DEBUG level with venue name. Observable improvement.

### Files Created
- `tests/unit/test_connectors/test_base_connector.py` (13 tests)

### Files Modified
- `src/uscryptoarb/orchestration/config.py` (generic _required_type helper)
- `src/uscryptoarb/venues/symbol_translator.py` (create_translator factory)
- `src/uscryptoarb/connectors/kraken/symbols.py` (use factory)
- `src/uscryptoarb/connectors/coinbase/symbols.py` (use factory)
- `src/uscryptoarb/connectors/connector_base.py` (BaseAsyncConnector ABC + Protocol)
- `src/uscryptoarb/connectors/kraken/client.py` (inherit ABC, delegate retry)
- `src/uscryptoarb/connectors/coinbase/client.py` (inherit ABC, delegate retry)
- `src/uscryptoarb/connectors/coinbase/parser.py` (TODO comment for Item 1.5)
- `tests/conftest.py` (fee_schedule_factory + refactored wrappers)
- `tests/test_pairs_and_symbols.py` (2 new create_translator tests)
- `CHANGELOG.md`
- `docs/DECISION_LOG.md` (DEC-018)
- `docs/LESSONS_LEARNED.md` (LL-059)
- `docs/SESSION_HANDOFFS.md` (this entry)

### Next Steps (Priority Order)
1. Run `python -m uscryptoarb --dry-run` to verify spread output with real market data
2. Run continuous mode for a few cycles, verify Ctrl+C shutdown
3. End-to-end integration test with mocked exchange responses
4. Gemini exploration notebook (`notebooks/03_gemini_exploration.ipynb`)
5. Gemini production connector (`connectors/gemini/`) — will use BaseAsyncConnector + create_translator

### Notes for Next Session
- Pre-existing test failure: `test_load_config_happy_path` expects threshold `0.0055` but config.yaml has `0.001`. Fix either the test or config.yaml to match.
- BaseAsyncConnector is ready for Gemini: inherit, implement fetch_tickers(), done.
- The fee_schedule_factory makes it easy to add fixtures for new pairs/venues — just call with different params.
- The `import httpx  # noqa: E402` in client files is needed because callers construct httpx.AsyncClient and pass it to the connector. The import ensures httpx is re-exported for type checking purposes.

## 2026-02-14 — Documentation cleanup post-Coinbase completion

**Interface**: Claude Code
**Branch**: main

### Completed
- Fixed README.md Coinbase exchange status: 🔲 → ✅ Connector built (with all 8 pairs)
- Fixed truncated Next Steps in SESSION_HANDOFFS.md Coinbase connector entry
- Added DEC-011 to DECISION_LOG.md Document History table

### In Progress
- Nothing

### Blocked / Needs Decision
- Nothing blocked

### Key Decisions Made
- Next major work stream: Calculation layer (fee math, return calcs) before Gemini connector
- Rationale: Two exchanges (Kraken + Coinbase) are sufficient for end-to-end Type-2 arbitrage detection; proves the TopOfBook → calculation → strategy pipeline before adding a third connector

### Files Modified
- MODIFIED: `README.md` (Coinbase status updated)
- MODIFIED: `docs/SESSION_HANDOFFS.md` (fixed truncated entry + this entry)
- MODIFIED: `docs/DECISION_LOG.md` (Document History table updated)

### Next Steps (Priority Order)
1. Begin calculation layer — port `MarketBaseConvert[]`, `ReturnCalc[]`, fee math from Mathematica
2. Gemini exploration notebook (`notebooks/03_gemini_exploration.ipynb`)
3. Gemini production connector (`connectors/gemini/`)

### Notes for Next Session
- Kraken and Coinbase connectors are DONE. Both produce `TopOfBook` via `tob_from_raw()`.
- Calculation layer is the next logical step — see MATHEMATICA_MAP.md Sections 3, 6, 7 for functions to port.
- When implementing Gemini connector later, check if `_parse_iso_timestamp_ms()` should be extracted to shared utility (Coding Rule 10.1 — will have 2 callers if Gemini uses ISO 8601).
- DummyRateLimiter in test files: extract to shared conftest when Gemini tests make it 3 callers.

---

## 2026-02-14 — Coinbase production connector implementation

**Interface**: Claude Code
**Branch**: main

### Completed
- Implemented `connectors/coinbase/` (4 source files): __init__.py, symbols.py, parser.py, client.py
- Created 4 fixture JSON files: coinbase_product_book_btc_usd.json, coinbase_product_book_ltc_btc.json, coinbase_product_book_sol_btc.json, coinbase_error_not_found.json
- Created 3 test files + __init__.py: test_symbols.py (~5 tests), test_parser.py (~14 tests), test_client.py (~13 tests)
- Updated tests/conftest.py with Coinbase fixture loaders
- Updated CHANGELOG.md, MATHEMATICA_MAP.md, fixtures README, SESSION_HANDOFFS.md

### In Progress
- Nothing — Coinbase connector is complete

### Blocked / Needs Decision
- Nothing blocked

### Key Decisions Made
- No new architectural decisions — followed established Kraken pattern (DEC-011)
- Per-pair requests in fetch_tickers() loop (not batch) per LL-052
- Partial failure handling: individual pair errors logged+skipped, partial results returned
- ISO 8601 timestamp parser kept private to parser module — refactor to shared utility when Gemini needs it (Coding Rule 10.1)
- DummyRateLimiter duplicated in test_client.py (not extracted to shared conftest yet — Coding Rule 10.1, wait for 3rd caller)

### Key Differences from Kraken Connector
- No batch endpoint: N requests instead of 1 (rate limiter called per pair)
- Bids/asks are dicts not arrays: {"price": "...", "size": "..."} vs ["price", "whole_vol", "lot_vol"]
- Exchange timestamps available (ISO 8601 with microseconds)
- Coinbase error format: {"error": "NOT_FOUND", "message": "..."} vs {"error": ["EGeneral:..."]}
- Rate limiter interval: 100ms (vs Kraken 500ms)
- cache-control: no-cache header included (defense-in-depth per LL-051)

### Files Created
- `src/uscryptoarb/connectors/coinbase/__init__.py`
- `src/uscryptoarb/connectors/coinbase/symbols.py`
- `src/uscryptoarb/connectors/coinbase/parser.py`
- `src/uscryptoarb/connectors/coinbase/client.py`
- `tests/unit/test_connectors/test_coinbase/__init__.py`
- `tests/unit/test_connectors/test_coinbase/test_symbols.py`
- `tests/unit/test_connectors/test_coinbase/test_parser.py`
- `tests/unit/test_connectors/test_coinbase/test_client.py`
- `fixtures/coinbase_product_book_btc_usd.json`
- `fixtures/coinbase_product_book_ltc_btc.json`
- `fixtures/coinbase_product_book_sol_btc.json`
- `fixtures/coinbase_error_not_found.json`

### Files Modified
- `tests/conftest.py` (added Coinbase fixture loaders)
- `CHANGELOG.md` (added Coinbase connector entry)
- `docs/MATHEMATICA_MAP.md` (updated Section 5 BidAskData Coinbase: 📋→✅)
- `docs/README.md` (added Coinbase fixture provenance entries)
- `docs/SESSION_HANDOFFS.md` (this entry)

### Next Steps (Priority Order)
1. Begin calculation layer — fee math and return calcs (porting `ReturnCalc[]`, `MarketBaseConvert[]`)
2. Gemini exploration notebook (`notebooks/03_gemini_exploration.ipynb`)
3. Gemini production connector (`connectors/gemini/`)

### Notes for Next Session
- Coinbase connector is DONE. Pattern is established for connector #3 (Gemini).
- When implementing Gemini, check if _parse_iso_timestamp_ms() should be extracted to a shared utility (Coding Rule 10.1 — now has 2 potential callers if Gemini uses ISO 8601).
- DummyRateLimiter appears in both test_kraken/test_client.py and test_coinbase/test_client.py. Extract to conftest when Gemini tests make it 3 callers.
- The 100ms rate limiter interval means 8 pairs take ~800ms minimum. This is well within the 5s polling interval but worth noting for Phase 2 optimization.

---

## 2026-01-04 — Project initialization and infrastructure

**Interface**: Claude.ai WebUI + Claude Code
**Duration**: ~4h
**Branch**: main

### Completed
- Created PROJECT_INSTRUCTIONS.md (comprehensive coding standards, architecture, Mathematica mapping)
- Created CLAUDE_INSTRUCTIONS.md (condensed WebUI system prompt, under 8K chars)
- Created CHANGELOG.md (Keep a Changelog format)
- Set up GitHub Actions CI workflow (Ruff → mypy → pytest)
- Implemented `validation/guards.py` with `is_missing()`, `require_present()`, `require_positive()`, `require_non_negative()`
- Added 30+ unit tests for validation module
- Configured mypy strict mode in pyproject.toml
- Added `py.typed` marker for PEP 561 compliance
- Documented "Data Trust Boundaries" pattern across all instruction files

### In Progress
- Kraken exploration notebook (`notebooks/01_kraken_exploration.ipynb`) — created, needs to be run locally to verify API connectivity and capture live response data

### Blocked / Needs Decision
- None

### Key Decisions Made
- Boundary validation over scattered MissingCheck (see DECISION_LOG.md DEC-003)
- python-kraken-sdk for Kraken connector
- coinbase-advanced-py for Coinbase connector
- Frozen dataclasses as contracts between layers

### Files Modified
- CREATED: `.github/workflows/ci.yml`
- CREATED: `src/uscryptoarb/py.typed`
- CREATED: `src/uscryptoarb/validation/__init__.py`
- CREATED: `src/uscryptoarb/validation/guards.py`
- CREATED: `tests/unit/__init__.py`
- CREATED: `tests/unit/test_validation/__init__.py`
- CREATED: `tests/unit/test_validation/test_guards.py`
- CREATED: `CHANGELOG.md`
- CREATED: `CLAUDE_INSTRUCTIONS.md`
- MODIFIED: `pyproject.toml` (mypy config)
- MODIFIED: `PROJECT_INSTRUCTIONS.md` (validation docs)

### Next Steps (Priority Order)
1. Run Kraken exploration notebook locally — verify API connectivity
2. Fix any notebook issues found during execution
3. Build Kraken production connector based on notebook findings
4. Create Coinbase exploration notebook

### Notes for Next Session
- The notebook has some VS Code linter warnings that are false positives (cross-cell dependencies). See LESSONS_LEARNED.md LL-030.
- The notebook import cell was cleaned up to remove unused imports during a fix pass.

---

## 2026-01-04 — Notebook fixes and validation refinements

**Interface**: Claude.ai WebUI
**Duration**: ~1h
**Branch**: main

### Completed
- Fixed unused imports in Kraken notebook (asyncio, Decimal, to_decimal, is_missing, require_positive)
- Renamed shadowed variables (canonical → pair_name, market → async_market, data → ticker_info)
- Fixed markdown table formatting in notebook
- Confirmed remaining warnings are false positives (cross-cell deps, JSON parsing)

### In Progress
- Kraken notebook still needs local execution to validate against live API

### Blocked / Needs Decision
- None

### Key Decisions Made
- Notebook linter warnings for cross-cell dependencies are acceptable (see LESSONS_LEARNED.md LL-030)

### Files Modified
- MODIFIED: `notebooks/01_kraken_exploration.ipynb` (import cleanup, variable renames)

### Next Steps (Priority Order)
1. Run notebook locally
2. Commit results
3. Begin Kraken production connector

### Notes for Next Session
- `scripts/fix_notebook.py` was used and should be deleted if still present

---

## 2026-02-13 — Operational documentation creation

**Interface**: Claude.ai WebUI
**Duration**: ~1h
**Branch**: main

### Completed
- Created `docs/LESSONS_LEARNED.md` with seed entries from project history
- Created `docs/SESSION_HANDOFFS.md` (this file) with historical entries
- Created `docs/DECISION_LOG.md` with architectural decisions extracted from conversations
- Created `docs/MATHEMATICA_MAP.md` with comprehensive function inventory
- Created `tests/fixtures/README.md` with fixture conventions
- Updated references in PROJECT_INSTRUCTIONS.md, CLAUDE_INSTRUCTIONS.md, README.md

### In Progress
- None — documentation pass complete

### Blocked / Needs Decision
- None

### Key Decisions Made
- Operational docs live in `docs/` directory (not repo root) to reduce clutter
- MATHEMATICA_MAP.md is the single source of truth for porting status (replaces inline table in Section 12)
- Session handoffs use append-only format (historical entries preserved)

### Files Modified
- CREATED: `docs/LESSONS_LEARNED.md`
- CREATED: `docs/SESSION_HANDOFFS.md`
- CREATED: `docs/DECISION_LOG.md`
- CREATED: `docs/MATHEMATICA_MAP.md`
- CREATED: `tests/fixtures/README.md`
- MODIFIED: `PROJECT_INSTRUCTIONS.md` (Section 2, 12, new Section 14)
- MODIFIED: `CLAUDE_INSTRUCTIONS.md` (Reference section)
- MODIFIED: `README.md` (docs reference)
- MODIFIED: `CHANGELOG.md` (new entries)

### Next Steps (Priority Order)
1. Run Kraken exploration notebook locally (still pending from earlier sessions)
2. Build Kraken production connector
3. Create Coinbase exploration notebook

### Notes for Next Session
- All five new docs are ready for use. When starting any implementation task, search LESSONS_LEARNED.md and MATHEMATICA_MAP.md first.
- DECISION_LOG.md has 7 seed entries — add new decisions as they arise.

---

## 2026-02-13 — Status correction

**Interface**: Claude.ai WebUI
**Branch**: main

### Completed
- Kraken exploration notebook was run locally and committed (completed prior to this session)
- Kraken production connector fully built and tested based on notebook findings
- Confirmed: `connectors/kraken/` (client.py, parser.py, symbols.py) + full test coverage

### Next Steps (Priority Order)
1. Coinbase exploration notebook (`notebooks/02_coinbase_exploration.ipynb`)
2. Coinbase production connector (`connectors/coinbase/`)
3. Calculation layer — fee math and return calcs

### Notes for Next Session
- Kraken connector is DONE. Do not reference the notebook as pending.

---

## 2026-02-13 — Coinbase exploration notebook

**Interface**: Claude Code
**Branch**: main

### Completed
- Created `notebooks/02_coinbase_exploration.ipynb` with 10 sections:
  1. Setup & imports (reuses existing SymbolTranslator, tob_from_raw, to_decimal, require_present)
  2. Product discovery via SDK (all 8 target pairs)
  3. Symbol mapping (COINBASE_SYMBOL_MAP + SymbolTranslator instance)
  4. Best Bid/Ask via SDK public endpoints
  5. Raw httpx comparison (async compatibility, cache-control header)
  6. Parse to TopOfBook prototype parser
  7. Rate limit testing (10 req/sec by IP)
  8. Error handling scenarios
  9. Product details (precision, min sizes)
  10. Summary & production connector design recommendation
- Updated CHANGELOG.md, MATHEMATICA_MAP.md, README.md

### In Progress
- Notebook needs to be run locally to capture live API output

### Blocked / Needs Decision
- DEC-010 (proposed): Coinbase connector — SDK wrapper vs raw httpx.
  Notebook includes comparison section. Expectation: raw httpx (consistent with Kraken,
  async-native, header control). Final decision after running notebook.

### Key Decisions Made
- Notebook structure mirrors Kraken notebook (per DEC-008)
- Public endpoints used (no auth needed for Phase 1)
- USD ≠ USDC verification included (per DEC-001)

### Files Modified
- CREATED: `notebooks/02_coinbase_exploration.ipynb`
- MODIFIED: `CHANGELOG.md` (added notebook entry)
- MODIFIED: `docs/MATHEMATICA_MAP.md` (updated Coinbase BidAskData status)
- MODIFIED: `README.md` (updated Coinbase exchange status)
- MODIFIED: `docs/SESSION_HANDOFFS.md` (this entry)

### Next Steps (Priority Order)
1. Run Coinbase notebook locally — verify API connectivity and capture live output
2. Commit notebook with output
3. Make DEC-010 decision (SDK vs httpx) based on notebook findings
4. Build Coinbase production connector (`connectors/coinbase/`)
5. Begin calculation layer (fee math, return calcs)

### Notes for Next Session
- The notebook tests both SDK and raw httpx approaches. Section 5 has the comparison.
- Coinbase public endpoints have a 1s cache — use `cache-control: no-cache` header for fresh data.
- Rate limit is 10 req/sec by IP (more generous than Kraken). RateLimiter interval: 150ms.
- Coinbase SDK is sync-only. Raw httpx is the likely choice for production (consistent with Kraken connector).
- All 8 target pairs should be available on Coinbase, but verify when running the notebook.


---

## 2026-02-14 — Coinbase exploration notebook: complete run + API research

**Interface**: Claude.ai WebUI
**Duration**: ~2h
**Branch**: main

### Completed
- Fixed asyncio.run() error in notebook with nest_asyncio.apply() + top-level await
- Full notebook execution: all 20 cells, Sections 1–10 ran successfully
- Reviewed all outputs: symbol mapping, BBO data, SDK vs httpx comparison, TopOfBook parsing, rate limits, error handling, product details
- Researched batch BBO 404 root cause: confirmed no public `/market/best_bid_ask` endpoint exists (authenticated-only)
- Documented 3 new lessons learned (LL-050, LL-051, LL-052)
- Added DEC-011: raw httpx for Coinbase connector (partially supersedes DEC-005)

### In Progress
- Nothing — exploration phase is complete

### Blocked / Needs Decision
- Nothing blocked

### Key Decisions Made
- DEC-011: Use raw httpx (not SDK) for Coinbase production connector
- Production connector must use individual `/market/product_book` per pair (no batch endpoint available without auth)
- 100ms rate limit interval is safe (15 rapid requests with zero 429s observed)

### Key Findings (from notebook)
- 8/8 target pairs available, all status: online
- DEC-001 confirmed: USD ≠ USDC (distinct product_id, distinct quote_currency_id)
- Symbol mapping trivial: canonical `BTC/USD` → Coinbase `BTC-USD` (replace / with -)
- Response structure: `pricebook.bids[0].price` / `.size` as strings → clean for to_decimal()
- Timestamps: ISO 8601 with microseconds (e.g., `2026-02-14T17:23:44.194522Z`)
- Avg latency: 52ms (36ms after connection warmup)
- Rate limits: 15 requests in ~0.8s with zero 429s (more generous than documented 10 req/s)
- cache-control: no-cache does NOT bypass server-side 1s cache
- Batch `/market/best_bid_ask` returns 404 (public endpoints are a subset of authenticated)
- Error format: `{"error": "NOT_FOUND", "error_details": "...", "message": "..."}`
- TopOfBook parsing via tob_from_raw() works for all 8 pairs
- Product precision: most pairs have quote_increment=0.01, except LTC/BTC (0.000001) and SOL/BTC (0.0000001)
- SOL/BTC has coarser base_increment (0.001) and larger base_min_size (0.001) vs other pairs (0.00000001)

### Files Modified
- `notebooks/02_coinbase_exploration.ipynb` (async fix committed by Ray)
- `docs/LESSONS_LEARNED.md` (3 entries appended: LL-050, LL-051, LL-052)
- `docs/DECISION_LOG.md` (1 entry appended: DEC-011)
- `docs/SESSION_HANDOFFS.md` (this entry)
- `CHANGELOG.md` (1 line added under Unreleased)

### Next Steps (Priority Order)
1. Begin Coinbase production connector implementation (`connectors/coinbase/`)
2. Structure: `symbols.py` → `parser.py` → `client.py`, mirroring Kraken connector
3. After Coinbase connector: Gemini exploration notebook (`03_gemini_exploration.ipynb`)

### Notes for Next Session
- The notebook Section 10 summary cell still has placeholder text (e.g., "~Xms" latency). The cell outputs tell the real story, but the markdown could be updated for completeness in a future pass.
- `nest_asyncio` is a notebook-only dependency. Do not add it to pyproject.toml runtime deps.


---

## 2026-02-14 — Calculation layer Phase 1 implementation

**Interface**: Claude Code
**Branch**: main

### Completed
- Implemented `calculation/` package (6 source files): __init__.py, types.py, returns.py, fees.py, sizing.py, arb_calc.py
- Created `tests/unit/test_calculation/` (6 test files): __init__.py, conftest.py, test_returns.py, test_fees.py, test_sizing.py, test_arb_calc.py
- Created `tests/fixtures/fee_schedules.json` with hardcoded fee data for Kraken, Coinbase, Gemini
- All 50 tests pass
- Updated DECISION_LOG.md (DEC-013, DEC-014, DEC-015), MATHEMATICA_MAP.md (12 functions 📋→✅), CHANGELOG.md, fixtures README, SESSION_HANDOFFS.md

### In Progress
- Nothing — calculation layer Phase 1 is complete

### Blocked / Needs Decision
- Nothing blocked

### Key Decisions Made
- DEC-013: Hardcoded flat fee rates from config.yaml for Phase 1 (tiered lookup deferred)
- DEC-014: Kelly Criterion defaults: prob_success=0.95, kelly_multiplier=0.25 (industry standard)
- DEC-015: Withdrawal fees included now (critical for accurate net return calculation)
- ArbLeg design: tracks trading_fee_base and withdrawal_fee as separate absolute amounts for full traceability
- Withdrawal fee direction: buy-side withdrawal on market currency (BTC), sell-side withdrawal on base currency (USD/USDC)
- No validation code in calculation/ — per DEC-003, LL-020

### Files Created
- `src/uscryptoarb/calculation/__init__.py`
- `src/uscryptoarb/calculation/calc_types.py`
- `src/uscryptoarb/calculation/returns.py`
- `src/uscryptoarb/calculation/fees.py`
- `src/uscryptoarb/calculation/sizing.py`
- `src/uscryptoarb/calculation/arb_calc.py`
- `tests/unit/test_calculation/__init__.py`
- `tests/unit/test_calculation/conftest.py`
- `tests/unit/test_calculation/test_returns.py`
- `tests/unit/test_calculation/test_fees.py`
- `tests/unit/test_calculation/test_sizing.py`
- `tests/unit/test_calculation/test_arb_calc.py`
- `tests/fixtures/fee_schedules.json`

### Files Modified
- `docs/DECISION_LOG.md` (added DEC-013, DEC-014, DEC-015)
- `docs/MATHEMATICA_MAP.md` (12 functions 📋→✅, updated statistics)
- `CHANGELOG.md` (calculation layer entries)
- `tests/fixtures/README.md` (fee_schedules.json provenance)
- `docs/SESSION_HANDOFFS.md` (this entry)

### Next Steps (Priority Order)
1. Gemini exploration notebook (`notebooks/03_gemini_exploration.ipynb`)
2. Strategy layer — `select_trade()`, threshold check, `find_trades_to_execute()`
3. Gemini production connector (`connectors/gemini/`)

### Notes for Next Session
- Calculation layer is PURE — no I/O, no validation, no side effects. All money math uses Decimal.
- `parse_pair()` from `markets/pairs.py` is reused for market/base currency extraction (no duplication)
- `floor_to_step()` from `misc/decimals.py` is reused in `calc_position_size()` (no duplication)
- Withdrawal fee data in fee_schedules.json uses conservative estimates. Verify against live API when building fee config loader.
- The `TradingAccuracy` dataclass lives in `calculation/calc_types.py`. If connectors need to produce it (for live fee lookups), consider moving to `core/types.py` to avoid import direction issues.
- Kelly golden test: $1000 bankroll, returnGrs=0.008, threshold=0.0055 → $0.59375 position. Intentionally conservative.

---

## 2026-02-14 — Calculation layer review fixes and documentation sync

**Interface**: Claude Code
**Branch**: main

### Completed
- Fixed `calc_buy_leg()` / `calc_sell_leg()` to apply `flat_fee` from TradingFeeRate (was silently ignored)
- Updated `calc_arb_opportunity()` to pass flat_fee through to leg calculations
- Removed dead `CALC_CONTEXT_PREC` constant from returns.py
- Added 2 new tests for non-zero flat_fee (buy and sell sides)
- Synced PROJECT_INSTRUCTIONS.md Sections 5.3, 12, 13 with implemented code
- Synced MATHEMATICA_MAP.md Sections 1, 5 with actual porting status
- Fixed truncated Next Steps in SESSION_HANDOFFS.md calculation layer entry
- Added LL-053 (TradingAccuracy migration trigger) and LL-054 (flat_fee must be applied)
- Updated CHANGELOG.md with Fixed section

### In Progress
- Nothing

### Blocked / Needs Decision
- Nothing

### Key Decisions Made
- flat_fee added as optional parameter (default ZERO) for backward compatibility rather than refactoring to accept TradingFeeRate directly
- TradingAccuracy stays in calculation/calc_types.py for now; migration to core/types.py triggered when connectors need to produce it

### Files Modified
- MODIFIED: `src/uscryptoarb/calculation/fees.py` (flat_fee parameter added)
- MODIFIED: `src/uscryptoarb/calculation/arb_calc.py` (passes flat_fee through)
- MODIFIED: `src/uscryptoarb/calculation/returns.py` (removed dead constant)
- MODIFIED: `tests/unit/test_calculation/test_fees.py` (2 new tests)
- MODIFIED: `PROJECT_INSTRUCTIONS.md` (Sections 5.3, 12, 13)
- MODIFIED: `docs/MATHEMATICA_MAP.md` (Sections 1, 5)
- MODIFIED: `docs/SESSION_HANDOFFS.md` (fixed truncation + this entry)
- MODIFIED: `docs/LESSONS_LEARNED.md` (LL-053, LL-054)
- MODIFIED: `CHANGELOG.md` (Fixed section)

### Next Steps (Priority Order)
1. Strategy layer — `select_trade()`, threshold check, `find_trades_to_execute()`
2. Gemini exploration notebook (`notebooks/03_gemini_exploration.ipynb`)
3. Gemini production connector (`connectors/gemini/`)

### Notes for Next Session
- All 52 tests pass (50 original + 2 new flat_fee tests)
- flat_fee is now wired through but all exchanges still use 0. If an exchange introduces flat trading fees, the math is ready.
- TradingAccuracy migration to core/types.py is documented in LL-053. Trigger: when any connector needs to import it.

---

## 2026-02-14 — Strategy layer implementation

**Interface**: Claude Code
**Branch**: main

### Completed
- Implemented `strategy/` package (3 source files): __init__.py, selection.py, scanner.py
- Created `tests/unit/test_strategy/` (4 test files): __init__.py, conftest.py, test_selection.py, test_scanner.py
- Refactored shared TopOfBook/FeeSchedule fixtures from test_calculation/conftest.py up to tests/conftest.py
- Added Gemini BTC/USD fixtures (TopOfBook, FeeSchedule, TradingAccuracy) for 3-exchange tests
- Added stale_tob fixture for staleness filtering tests
- All new tests pass, all 50 existing calculation tests still pass
- Updated MATHEMATICA_MAP.md (3 functions: 📋→✅/🔧), CHANGELOG.md, SESSION_HANDOFFS.md

### In Progress
- Nothing — strategy layer is complete

### Blocked / Needs Decision
- Nothing blocked

### Key Decisions Made
- Threshold uses > (strictly greater) not >= — intentional improvement over Mathematica's >= (conservative: boundary values rejected)
- Only return_net checked (not returnRaw AND returnGrs) — since return_net <= return_grs <= return_raw, checking return_net implies the others
- Sort by return_net descending (not sellMarket size) — appropriate for Phase 1 detection; Phase 4 can add sizing-based selection
- filter_valid_exchanges skips filtering when max_staleness_ms=None OR current_time_ms=None — safest default, never accidentally blocks a venue
- fees_by_venue intersection with tobs_by_venue keys in find_trades_to_execute — defense-in-depth without adding validation to pure layer
- Shared fixtures refactored to tests/conftest.py — DRY, both test_calculation and test_strategy use them

### Files Created
- `src/uscryptoarb/strategy/__init__.py`
- `src/uscryptoarb/strategy/selection.py`
- `src/uscryptoarb/strategy/trade_finder.py`
- `tests/unit/test_strategy/__init__.py`
- `tests/unit/test_strategy/conftest.py`
- `tests/unit/test_strategy/test_selection.py`
- `tests/unit/test_strategy/test_scanner.py`

### Files Modified
- `tests/conftest.py` (added shared TopOfBook/FeeSchedule/Gemini/stale fixtures)
- `tests/unit/test_calculation/conftest.py` (removed fixtures, now in shared conftest)
- `docs/MATHEMATICA_MAP.md` (3 functions updated in Sections 6, 10)
- `CHANGELOG.md` (strategy layer entries)
- `docs/SESSION_HANDOFFS.md` (this entry)

### Next Steps (Priority Order)
1. Gemini exploration notebook (`notebooks/03_gemini_exploration.ipynb`)
2. Gemini production connector (`connectors/gemini/`)
3. Orchestration layer — wire up connectors + strategy into a polling loop
4. Email notification for detected opportunities

---

## 2026-02-14 — Post-strategy review: documentation sync + strategic pivot

**Interface**: Claude.ai WebUI → Claude Code
**Branch**: main

### Completed
- Systematic review of all documentation against implemented code
- Fixed `strategy/trade_finder.py`: removed redundant `sort_opportunities()` call in `find_trades_to_execute()` pipeline (Coding Rule 10.1 — `select_trade()` already sorts internally)
- Fixed `PROJECT_INSTRUCTIONS.md` Section 12: replaced stale inline table with pointer to MATHEMATICA_MAP.md (completing DEC-010, which was claimed done but hadn't actually been applied)
- Fixed `CLAUDE_INSTRUCTIONS.md`: updated stale function names in Key Functions (`calc_return()` → `calc_return_raw/grs/net()`, `calc_arb_final()` → `calc_arb_opportunity()`, added `find_trades_to_execute()`)
- Added DEC-016: orchestration before Gemini connector (strategic pivot)
- Added LL-055: CHANGELOG claims must be verified against actual file state
- Updated CHANGELOG.md with Fixed entries and Changed entry for DEC-016
- Confirmed README.md Coinbase status already correct (✅ Connector built)

### In Progress
- Nothing — review and fixes complete

### Blocked / Needs Decision
- Nothing blocked

### Key Decisions Made
- DEC-016: Build orchestration layer with 2 exchanges (Kraken + Coinbase) before adding Gemini as third connector. Rationale: proves end-to-end pipeline, surfaces integration bugs early, delivers working Phase 1 sooner, makes Gemini low-risk incremental add.

### Files Modified
- MODIFIED: `src/uscryptoarb/strategy/trade_finder.py` (removed redundant sort, updated docstring pipeline description)
- MODIFIED: `PROJECT_INSTRUCTIONS.md` (Section 12 → pointer to MATHEMATICA_MAP.md, Document History updated)
- MODIFIED: `CLAUDE_INSTRUCTIONS.md` (Key Functions updated with correct names + MATHEMATICA_MAP.md reference)
- MODIFIED: `CHANGELOG.md` (3 new Fixed entries, 1 Changed entry)
- MODIFIED: `docs/DECISION_LOG.md` (added DEC-016, Document History updated)
- MODIFIED: `docs/LESSONS_LEARNED.md` (added LL-055)
- MODIFIED: `docs/SESSION_HANDOFFS.md` (this entry)

### Next Steps (Priority Order)
1. Orchestration layer — config loader, polling loop, wire Kraken + Coinbase connectors to strategy pipeline
2. Email notification module for detected arbitrage opportunities
3. End-to-end integration test with mocked exchange responses
4. Gemini exploration notebook (`notebooks/03_gemini_exploration.ipynb`)
5. Gemini production connector (`connectors/gemini/`)

### Notes for Next Session
- The complete detection pipeline is proven in unit tests: TopOfBook → calculation → strategy → best opportunity. Orchestration needs to wire real connectors into this pipeline with a polling loop.
- `find_trades_to_execute()` operates on a single pair at a time. Orchestration will need to loop over all 8 configured pairs, running the pipeline for each. Plan the data flow: `dict[str, dict[str, TopOfBook]]` keyed by pair then venue.
- Key orchestration design questions: how to handle partial failures (1 of 2 connectors fails for a pair), how to structure the config loader (config.yaml → FeeSchedule objects), and how to wire email notifications to detected opportunities.
- CLAUDE_INSTRUCTIONS.md was updated — Ray must copy the complete file into the Claude.ai project instructions UI.
- All existing tests (52 calculation + strategy) continue to pass after the scanner.py change.

---

## 2026-02-15 — Orchestration layer implementation

**Interface**: Claude Code
**Branch**: main

### Completed
- Orchestration layer: config loader, async polling loop, connector wiring
- Notification layer: Gmail email alerts with STARTTLS
- CLI entry point: `python -m uscryptoarb` with --dry-run, --trace-pair, --log-level
- Package resources: fee_schedules.json for production use
- Config files: config.yaml, .env.example
- DummyRateLimiter extracted to tests/helpers.py (Coding Rule 10.1 — 3rd caller)
- ~41 new unit tests across orchestration and notification
- All operational docs updated (CHANGELOG, MATHEMATICA_MAP, SESSION_HANDOFFS, README)

### In Progress
- Nothing — orchestration layer is complete

### Blocked / Needs Decision
- Nothing blocked

### Key Decisions Made
- Per-pair trade amounts (configurable in config.yaml, not global)
- STARTTLS on port 587 (not SSL on 465 — current Gmail recommendation)
- Email credentials in .env via python-dotenv (not hardcoded)
- Package resources in src/uscryptoarb/resources/ (not data/ — gitignored)
- Config loader in orchestration/ (not config/ — orchestration can import everything per layer rules)
- DummyRateLimiter in tests/helpers.py (not conftest.py — it's a class, not a fixture)

### Files Created
- `src/uscryptoarb/orchestration/__init__.py`
- `src/uscryptoarb/orchestration/config.py`
- `src/uscryptoarb/orchestration/scan_loop.py`
- `src/uscryptoarb/notification/__init__.py`
- `src/uscryptoarb/notification/email.py`
- `src/uscryptoarb/__main__.py`
- `src/uscryptoarb/resources/__init__.py`
- `src/uscryptoarb/resources/fee_schedules.json`
- `config.yaml`
- `.env.example`
- `tests/helpers.py`
- `tests/unit/test_orchestration/__init__.py`
- `tests/unit/test_orchestration/test_config.py`
- `tests/unit/test_orchestration/test_scanner.py`
- `tests/unit/test_notification/__init__.py`
- `tests/unit/test_notification/test_email.py`

### Files Modified
- `pyproject.toml` (added pyyaml, python-dotenv, package-data, mypy overrides)
- `tests/unit/test_connectors/test_kraken/test_client.py` (DummyRateLimiter → tests.helpers)
- `tests/unit/test_connectors/test_coinbase/test_client.py` (DummyRateLimiter → tests.helpers)
- `README.md` (exchange status, Usage section)
- `CHANGELOG.md` (orchestration + notification entries)
- `docs/MATHEMATICA_MAP.md` (RunFinal ✅, SendEmail ✅, databases ✅)
- `docs/SESSION_HANDOFFS.md` (this entry)

### Next Steps (Priority Order)
1. End-to-end integration test with real exchange APIs (manual, not CI)
2. Gemini exploration notebook (notebooks/03_gemini_exploration.ipynb)
3. Gemini production connector (connectors/gemini/)
4. WebSocket integration for real-time data (Phase 2)

### Notes for Next Session
- The complete Phase 1 detection pipeline is now wired end-to-end: connectors → calculation → strategy → email alerts.
- Run `python -m uscryptoarb --dry-run` to verify with real market data.
- Email alerts require .env with SMTP_FROM_ADDR and SMTP_PASSWORD set.
- config.yaml `venues.primary` currently has [kraken, coinbase]. Add gemini after connector is built.
- Per-pair trade amounts are in config.yaml under arbitrage.trade_amounts. Adjust as needed.


---

## 2026-02-15 — Post-orchestration review: 7 fixes (bugs + doc sync)

**Interface**: Claude.ai WebUI → Claude Code
**Branch**: main

### Completed
- Fixed layering violation: EmailConfig moved from orchestration/config.py to notification/email.py (DEC-017)
- Fixed SMTP connection leak: _send_smtp() now uses context manager for socket cleanup
- Removed dead code: unreachable None checks in _required_decimal() and _required_int()
- Verified Section 12 has MATHEMATICA_MAP.md pointer (per LL-055 "trust but verify")
- Fixed MATHEMATICA_MAP.md Section 13 stale module paths (misc/decimals.py, markets/pairs.py)
- Updated PROJECT_INSTRUCTIONS.md Section 5.3 to match actual module structure
- Verified README.md has correct Coinbase status and Usage section
- Added DEC-017, LL-058, CHANGELOG entries

### In Progress
- Nothing — all 7 fixes complete

### Blocked / Needs Decision
- Nothing blocked

### Key Decisions Made
- DEC-017: EmailConfig defined in notification/email.py, imported by orchestration (types belong in the consuming layer)

### Files Modified
- `src/uscryptoarb/notification/email.py` (added EmailConfig definition, SMTP context manager)
- `src/uscryptoarb/notification/__init__.py` (exports EmailConfig)
- `src/uscryptoarb/orchestration/config.py` (removed EmailConfig, imports from notification, removed dead code)
- `tests/unit/test_notification/test_email.py` (updated EmailConfig import source)
- `PROJECT_INSTRUCTIONS.md` (Section 5.3 updated, Sections 2/12/13 verified)
- `docs/MATHEMATICA_MAP.md` (Section 13 paths corrected, Section 4 path corrected)
- `docs/DECISION_LOG.md` (added DEC-017)
- `docs/LESSONS_LEARNED.md` (added LL-058)
- `CHANGELOG.md` (5 Fixed entries)
- `docs/SESSION_HANDOFFS.md` (this entry)

### Next Steps (Priority Order)
1. **Ray manual action**: Copy updated CLAUDE_INSTRUCTIONS.md from repo into Claude.ai project instructions UI
2. End-to-end integration test with mocked exchange responses
3. Gemini exploration notebook (`notebooks/03_gemini_exploration.ipynb`)
4. Gemini production connector (`connectors/gemini/`)

### Notes for Next Session
- CLAUDE_INSTRUCTIONS.md in the project instructions UI still has stale function names. Ray must copy the repo version after this session.
- LL-053 flagged that calculation types (TradingFeeRate, etc.) should move to core/types.py when connectors need them. notification/email.py also imports ArbOpportunity from calculation — same pattern, tracked but not yet actionable.
- Legacy config/app_config.py still exists, referenced only by tests/test_registry_and_config.py. Consider removing in a future cleanup session.
- All ~93+ tests pass. All documentation is now aligned with code.

---

## 2026-02-15 — Verbose spread logging

**Interface**: Claude Code
**Branch**: main

### Completed
- Added `_log_pair_spreads()` helper to `orchestration/scan_loop.py` — logs per-pair bid/ask per venue and best raw cross-exchange spread on every scan cycle
- Reuses `calc_return_raw()` from calculation layer (Coding Rule 10.2 — no formula duplication)
- All Decimal arithmetic, no float conversion (DEC-007)
- 4 new tests covering: basic output, positive spread, negative spread, alphabetical venue ordering
- Works in both `--dry-run` (single cycle) and continuous polling mode

### In Progress
- Nothing

### Blocked / Needs Decision
- Nothing blocked

### Key Decisions Made
- Spread logging at INFO level (not gated behind debug.enabled) — visibility is more valuable than quiet in Phase 1
- Placed in orchestration layer (logging is I/O per DEC-002), not in strategy/calculation (pure layers)

### Files Modified
- MODIFIED: `src/uscryptoarb/orchestration/scan_loop.py` (added `_log_pair_spreads`, one import, one call site)
- MODIFIED: `tests/unit/test_orchestration/test_scanner.py` (4 new tests)
- MODIFIED: `CHANGELOG.md` (Added entry)
- MODIFIED: `docs/SESSION_HANDOFFS.md` (this entry)

### Next Steps (Priority Order)
1. Run `python -m uscryptoarb --dry-run` to verify spread output with real market data
2. Run continuous mode (`python -m uscryptoarb`) for a few cycles, verify Ctrl+C shutdown
3. End-to-end integration test with mocked exchange responses
4. Gemini exploration notebook (`notebooks/03_gemini_exploration.ipynb`)
5. Gemini production connector (`connectors/gemini/`)

### Notes for Next Session
- Expected output per pair: `[dryrun] BTC/USD: coinbase bid=X ask=Y | kraken bid=X ask=Y | best_spread=+0.023% (threshold=0.550%)`
- Spreads will almost always be negative or very small positive — real arb windows are rare and fleeting
- If log volume is too high in continuous mode (8 lines per 5s cycle), can gate behind `debug.enabled` in a future session

---

## 2026-02-15 — Decouple orchestration tests from production config.yaml

**Interface**: Claude Code
**Branch**: main

### Completed
- Created `tests/unit/test_orchestration/conftest.py` with `FULL_CFG` synthetic YAML and `full_config_path` fixture
- Refactored `test_config.py`: split `test_load_config_happy_path` into smoke test (no value assertions) + parsing test (synthetic fixture). Converted 5 tests total from `load_config("config.yaml")` to `full_config_path`.
- Refactored `test_scanner.py`: converted 4 tests from `load_config("config.yaml")` to `full_config_path`. `TestLogPairSpreads` was already decoupled (no changes needed).
- Documented as LL-061 in LESSONS_LEARNED.md

### In Progress
- Nothing

### Blocked / Needs Decision
- Nothing blocked

### Key Decisions Made
- Production config.yaml gets a single smoke test (loads without error, non-empty venues/pairs) — no value assertions
- All parsing/logic tests use synthetic YAML written to tmp_path via conftest fixture
- Synthetic fixture includes only 2 pairs (BTC/USD, LTC/USD) and 2 venues (kraken, coinbase) — minimal but complete

### Behavioral Changes
- None. All tests assert the same things, just against synthetic config instead of production file.

### Files Created
- `tests/unit/test_orchestration/conftest.py`

### Files Modified
- `tests/unit/test_orchestration/test_config.py` (full replacement)
- `tests/unit/test_orchestration/test_scanner.py` (full replacement)
- `CHANGELOG.md`
- `docs/LESSONS_LEARNED.md` (new entry)
- `docs/SESSION_HANDOFFS.md` (this entry)

### Next Steps (Priority Order)
1. Run `python -m uscryptoarb --dry-run` to verify spread output with real market data
2. Run continuous mode for a few cycles, verify Ctrl+C shutdown
3. End-to-end integration test with mocked exchange responses
4. Gemini exploration notebook (`notebooks/03_gemini_exploration.ipynb`)
5. Gemini production connector (`connectors/gemini/`)

### Notes for Next Session
- The `full_config_path` fixture is available to any test under `tests/unit/test_orchestration/` via conftest.py. Future orchestration tests should use it instead of the production config.yaml.

---

## 2026-02-15 — Gemini exploration notebook

**Interface**: Claude.ai WebUI
**Branch**: main

### Completed
- Created `notebooks/03_gemini_exploration.ipynb` with 11 sections:
  1. Setup & imports (httpx, nest_asyncio, reuses SymbolTranslator, tob_from_raw, to_decimal, require_present)
  2. Symbol discovery & mapping (all 8 target pairs, SymbolTranslator round-trip, USD ≠ USDC verification)
  3. Ticker endpoints V1 & V2 + pricefeed (documents that NONE provide bid/ask sizes)
  4. Order book endpoint — primary data source (`/v1/book/{symbol}?limit_bids=1&limit_asks=1`)
  5. Parse into TopOfBook (prototype `parse_gemini_book()` function, tested on all 8 pairs)
  6. Async httpx pattern (production preview with `fetch_all_books_async()`)
  7. Rate limit testing (burst + sustained, 120 req/min documented limit)
  8. Error handling (invalid symbol, bad params, wrong endpoint)
  9. Symbol details (precision, min sizes, USD vs USDC comparison)
  10. Timestamp format deep dive (Unix seconds as integer strings)
  11. Summary & connector design notes (comparison table, refactor candidates, fixture generation)
- Searched LESSONS_LEARNED.md, DECISION_LOG.md, SESSION_HANDOFFS.md, and MATHEMATICA_MAP.md for relevant context
- Researched Gemini API via official docs (docs.gemini.com/rest/market-data) and live API responses

### In Progress
- Notebook needs to be run locally to capture live API output (same as prior notebooks)

### Blocked / Needs Decision
- Nothing blocked

### Key Decisions Made
- No new architectural decisions — follows established patterns (DEC-008 exploration-first, DEC-011 raw httpx, DEC-018 BaseAsyncConnector)
- Production connector will use `/v1/book/{symbol}` (NOT ticker) because tickers lack bid/ask sizes
- Rate limiter interval: 500ms (matches Kraken; 8 pairs × 500ms = 4s, within 5s polling)

### Key Findings (from API research + docs)
- **Critical**: Neither ticker V1 nor V2 provides bid/ask sizes. Must use order book endpoint.
- 8/8 target pairs confirmed available (btcusd, btcusdc, ltcusd, ltcusdc, ltcbtc, solusd, solusdc, solbtc)
- DEC-001 confirmed: USD ≠ USDC (distinct quote_currency in symbol details)
- Symbol format: lowercase, no separator (e.g., `btcusd`, `solusdc`)
- Order book response: `{"bids": [{"price": str, "amount": str, "timestamp": str}], "asks": [...]}`
- Timestamps: Unix seconds as integer strings (not ms, not ISO 8601, not float)
- Rate limits: 120 req/min public, burst of 5 queued, 429 on exceed
- No batch endpoint — per-pair requests required (same as Coinbase)
- Ticker V2: OHLC + bid/ask prices + hourly changes (useful for reporting but not TopOfBook)
- Pricefeed endpoint (`/v1/pricefeed`): batch last-price only, no bid/ask/size

### Refactor Candidates (per Coding Rule 10.8)
- DummyRateLimiter: Now 3rd caller (Gemini tests) → extract to tests/helpers.py
- Unix timestamp parsing: Kraken (float) vs Gemini (int string) — similar but not identical

### Files Created
- `notebooks/03_gemini_exploration.ipynb`

### Files Modified
- `docs/SESSION_HANDOFFS.md` (this entry)
- `docs/LESSONS_LEARNED.md` (LL-060, LL-061)
- `CHANGELOG.md` (notebook entry)

### Next Steps (Priority Order)
1. Ray: Run notebook locally, verify API connectivity, capture live output
2. Build Gemini production connector (`connectors/gemini/`) using BaseAsyncConnector
3. Extract DummyRateLimiter to tests/helpers.py (3rd caller trigger)
4. End-to-end integration test with all 3 exchanges

### Notes for Next Session
- The notebook is ready to run but has no captured output yet. All cells use live API calls.
- Gemini connector will be simpler than Kraken/Coinbase: no SDK wrapping, straightforward JSON responses.
- BaseAsyncConnector handles retry/backoff — Gemini connector only needs `fetch_tickers()` and parsing.
- Timestamp parsing is simpler than Coinbase: `int(ts_str) * 1000` vs ISO 8601 parsing.
- The `/v1/book` endpoint returns strings for all fields (price, amount, timestamp) — clean for `to_decimal()`.
- Per-pair fetch with 500ms delay means 8 pairs take ~4s. Well within 5s polling interval.
- When building the connector, also update config.yaml `venues.primary` to include gemini.

---

## 2026-02-15 — Gemini production connector implementation

**Interface**: Claude.ai WebUI → Claude Code
**Branch**: main

### Completed
- Implemented `connectors/gemini/` (4 source files): __init__.py, symbols.py, parser.py, client.py
- Created 3 fixture JSON files from notebook Section 11: gemini_book_btc_usd.json, gemini_book_ltc_btc.json, gemini_book_sol_btc.json
- Created 4 test files: test_symbols.py (~5 tests), test_parser.py (~14 tests), test_client.py (~14 tests)
- Updated tests/conftest.py with 3 Gemini fixture loaders
- Wired GeminiClient into orchestration/scan_loop.py create_connectors()
- Verified `config.yaml` already had gemini enabled in venues.primary (no change needed)
- Added gemini to orchestration test synthetic FULL_CFG (conftest.py)
- Added LL-064 to LESSONS_LEARNED.md (nest_asyncio + Python 3.14)
- Updated MATHEMATICA_MAP.md Section 5 (Gemini: 📋→✅)
- Updated CHANGELOG.md (7 entries under Added + 1 Changed)
- Updated tests/fixtures/README.md (3 fixture entries)

### In Progress
- Nothing — Gemini connector is complete

### Blocked / Needs Decision
- Nothing blocked

### Key Decisions Made
- No new architectural decisions — followed established BaseAsyncConnector pattern (DEC-018)
- Rate limiter uses config.yaml value (200ms) passed through venue_cfg
- /v1/book endpoint (not ticker) because tickers lack bid/ask sizes (LL-062)
- Non-JSON error handling added (Gemini returns plain text on some 400s)

### Key Differences from Coinbase Connector
- No pricebook wrapper — bids/asks are top-level keys
- Size field is "amount" (not "size")
- Timestamps: Unix seconds as integer strings (not ISO 8601)
- Error format: {"result": "error", ...} or plain text (not {"error": "NOT_FOUND"})
- Symbol in URL path (/v1/book/btcusd) not query param (?product_id=BTC-USD)
- No cache-control header needed

### Refactor Candidates (per Coding Rule 10.8)
- `load_fixture()` helper: defined identically in test_kraken/test_parser.py, test_coinbase/test_parser.py, and now test_gemini/test_parser.py (3rd instance). Consider extracting to tests/helpers.py alongside DummyRateLimiter.
- Timestamp parsing: 3 exchange-specific formats, but each is a one-liner with different logic. No shared pattern to extract — explicitly deferred.

### Files Created
- `src/uscryptoarb/connectors/gemini/__init__.py`
- `src/uscryptoarb/connectors/gemini/symbols.py`
- `src/uscryptoarb/connectors/gemini/parser.py`
- `src/uscryptoarb/connectors/gemini/client.py`
- `tests/unit/test_connectors/test_gemini/__init__.py`
- `tests/unit/test_connectors/test_gemini/test_symbols.py`
- `tests/unit/test_connectors/test_gemini/test_parser.py`
- `tests/unit/test_connectors/test_gemini/test_client.py`
- `tests/fixtures/gemini_book_btc_usd.json`
- `tests/fixtures/gemini_book_ltc_btc.json`
- `tests/fixtures/gemini_book_sol_btc.json`

### Files Modified
- `config.yaml` (already had gemini in venues.primary; no edit in this session)
- `src/uscryptoarb/orchestration/scan_loop.py` (GeminiClient import + elif branch)
- `tests/conftest.py` (3 Gemini fixture loaders)
- `tests/unit/test_orchestration/conftest.py` (gemini in FULL_CFG)
- `tests/unit/test_orchestration/test_scanner.py` (updated connector count assertion)
- `CHANGELOG.md` (Gemini entries)
- `docs/LESSONS_LEARNED.md` (LL-064)
- `docs/MATHEMATICA_MAP.md` (Gemini row: 📋→✅)
- `tests/fixtures/README.md` (3 fixture entries)
- `docs/SESSION_HANDOFFS.md` (this entry)

### Next Steps (Priority Order)
1. Run `python -m pytest tests/unit/test_connectors/test_gemini/ -v` — verify all ~33 tests pass
2. Run `python -m pytest tests/ -v` — full suite, no regressions
3. Run `python -m mypy src/` and `python -m ruff check src/ tests/` — clean
4. Run `python -m uscryptoarb --dry-run` with all 3 exchanges — verify real data
5. End-to-end integration test with mocked exchange responses
6. WebSocket integration planning (Phase 2)

### Notes for Next Session
- All 3 Ohio-eligible exchange connectors are now COMPLETE: Kraken, Coinbase, Gemini.
- Phase 1 exchange coverage is 100%. The full detection pipeline now spans 3 exchanges.
- `load_fixture()` in test_parser files is a 3rd-instance refactor candidate (tests/helpers.py).
- Pre-existing test issue: `test_load_config_happy_path` may still expect threshold `0.0055` vs config.yaml. Check if this was resolved in a prior session.
- The orchestration test `test_create_connectors_both_venues` was updated to include gemini (now tests 3 venues).


## Session: 2026-02-16 (LL-065/LL-066 Naming + Doc Sync)

### Completed
- Renamed five source modules to remove basename collisions: `calculation/calc_types.py`, `connectors/connector_base.py`, `venues/symbol_translator.py`, `strategy/trade_finder.py`, `orchestration/scan_loop.py`.
- Updated all imports, tests, docs, and markdown references to post-rename paths.
- Renamed three test modules to preserve naming parity with source refactors.
- Updated `PROJECT_INSTRUCTIONS.md` with Rules 10.8 and 10.9, checklist updates, file-tree sync, Gemini entries, and history bump to 1.3.0.
- Regenerated long-format `CLAUDE_INSTRUCTIONS.md` from project instructions, including post-rename paths and complete rules set.
- Added LL-065/LL-066 and DEC-019 entries documenting naming policy and documentation authority hierarchy.

### Validation
- `PYTHONPATH=src python -m pytest tests/ -v --tb=short` passed.
- `PYTHONPATH=src python -m mypy src/uscryptoarb/` passed.
- `PYTHONPATH=src python -m ruff check src/ tests/` passed.
- `PYTHONPATH=src python -m uscryptoarb --dry-run` smoke run successful.

### Blocked / Follow-up
- Ray must copy current `CLAUDE_INSTRUCTIONS.md` into the Claude.ai project instructions UI to complete three-way sync.

### Refactor Candidates
- None newly introduced in this session.
