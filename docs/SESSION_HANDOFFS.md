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
