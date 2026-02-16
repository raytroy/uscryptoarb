# Lessons Learned

> **Purpose**: Prevent repeat mistakes. Every error, gotcha, and hard-won insight gets documented here.
> **Rule**: When a mistake is made, add it here BEFORE closing the issue. Future sessions must search this file before implementing.
> **Authoritative for**: Error patterns, API gotchas, tooling pitfalls, debugging techniques.

---

## How to Use This File

**Before implementing**: Search this file for keywords related to your task.
**After a mistake**: Add a new entry using the template below.
**During code review**: Check that relevant lessons were followed.

### Entry Template

```
### LL-NNN: <Short descriptive title>
- **Date**: YYYY-MM-DD
- **Category**: [API Gotcha | Type System | Testing | Architecture | Tooling | Exchange-Specific | Porting]
- **Severity**: [Critical | High | Medium | Low]
- **What happened**: <What went wrong>
- **Root cause**: <Why it happened>
- **Fix applied**: <What was done to fix it>
- **Rule going forward**: <What to always/never do>
- **Affected files**: <List of files>
```

---

## API Gotchas

### LL-001: Kraken uses XBT not BTC
- **Date**: 2026-01-04
- **Category**: Exchange-Specific
- **Severity**: Critical
- **What happened**: Symbol lookups failed because code used "BTC" in Kraken API calls.
- **Root cause**: Kraken uses ISO 4217 currency code XBT for Bitcoin, not the common BTC. Their symbol for BTC/USD is `XXBTZUSD` (with X-prefix for crypto assets and Z-prefix for fiat).
- **Fix applied**: SymbolTranslator maps canonical `BTC/USD` → Kraken `XXBTZUSD`.
- **Rule going forward**: Always use SymbolTranslator for exchange API calls. Never hardcode exchange-specific symbols. Test symbol translation for every new pair added.
- **Affected files**: `venues/symbol_translator.py`, `notebooks/01_kraken_exploration.ipynb`

### LL-002: Kraken ticker 'b' and 'a' arrays have 3 elements, not 2
- **Date**: 2026-01-04
- **Category**: API Gotcha
- **Severity**: Medium
- **What happened**: Parser initially expected `[price, volume]` but Kraken returns `[price, whole_lot_volume, lot_volume]`.
- **Root cause**: Kraken's ticker API returns three values per side. Index `[0]` is price, index `[2]` is lot volume (the useful one for our purposes). Index `[1]` is whole lot volume.
- **Fix applied**: Parser uses index `[0]` for price and `[2]` for lot volume.
- **Rule going forward**: When adding a new exchange connector, document the exact response structure in the exploration notebook BEFORE writing the parser. Never assume response shapes match documentation without verification.
- **Affected files**: `notebooks/01_kraken_exploration.ipynb`

### LL-003: Kraken rate limits decrease by 1 every 3 seconds
- **Date**: 2026-01-04
- **Category**: Exchange-Specific
- **Severity**: High
- **What happened**: Rapid API calls during testing hit rate limits.
- **Root cause**: Kraken's public endpoint rate limit counter decreases by 1 every 3 seconds, not per-request. Burst requests quickly exhaust the budget.
- **Fix applied**: Added 0.5s delay between requests in notebook. Production connector must implement proper rate limiting.
- **Rule going forward**: Every connector must implement per-exchange rate limiting. Use SDK built-in rate limiters where available. Test rate limit behavior in exploration notebook before building production connector.
- **Affected files**: `notebooks/01_kraken_exploration.ipynb`, `connectors/kraken/`

---

## Type System Pitfalls

### LL-010: Floats silently corrupt Decimal precision
- **Date**: 2026-01-04
- **Category**: Type System
- **Severity**: Critical
- **What happened**: `Decimal(0.1)` produces `Decimal('0.1000000000000000055511151231257827021181583404541015625')`, not `Decimal('0.1')`.
- **Root cause**: Python `float` uses IEEE 754 binary representation. Passing a float to `Decimal()` preserves the binary representation error.
- **Fix applied**: `to_decimal()` explicitly rejects `float` inputs with `TypeError`. Only accepts `str`, `int`, or `Decimal`.
- **Rule going forward**: NEVER use `float` for money, prices, fees, or quantities. Always use `Decimal` constructed from strings. The `to_decimal()` function is the single entry point for all numeric conversions. See DECISION_LOG.md DEC-007.
- **Affected files**: `misc/decimals.py`, `validation/guards.py`

---

## Architecture Mistakes

### LL-020: Scattered validation creates unmaintainable code
- **Date**: 2026-01-04
- **Category**: Architecture
- **Severity**: High
- **What happened**: Initial design considered putting `MissingCheck` inside every calculation function (mirroring the Mathematica pattern).
- **Root cause**: Mathematica doesn't have typed frozen dataclasses, so it needs runtime checks everywhere. Python can do better with boundary validation + frozen types.
- **Fix applied**: Adopted "validate at boundaries, trust downstream" pattern. Validation only in connectors, factories, `__post_init__`, and config loaders. Pure calculation/strategy layers have zero validation code.
- **Rule going forward**: If adding `require_*` or `if x is None` in `calculation/` or `strategy/`, STOP — fix the boundary instead. See PROJECT_INSTRUCTIONS.md Section 6.2 and DECISION_LOG.md DEC-003.
- **Affected files**: `validation/guards.py`, `marketdata/topofbook.py`, PROJECT_INSTRUCTIONS.md

---

## Tooling Traps

### LL-030: Notebook linter warnings are mostly false positives
- **Date**: 2026-01-04
- **Category**: Tooling
- **Severity**: Low
- **What happened**: VS Code reported multiple warnings in Jupyter notebook: "variable can be undefined", "shadows outer scope", "expression expected". Time was spent trying to fix them.
- **Root cause**: VS Code's static analyzer doesn't understand notebook cell execution order. Cross-cell variable dependencies are normal in notebooks. "Expression expected" errors were VS Code misinterpreting notebook JSON.
- **Fix applied**: Fixed genuine issues (unused imports, unnecessary shadowing) but accepted notebook-inherent warnings (cross-cell dependencies, JSON parsing false positives).
- **Rule going forward**: For exploration notebooks, fix: unused imports, genuine shadowing bugs, formatting errors. Ignore: cross-cell "undefined variable" warnings, VS Code JSON parsing errors. Production code in `src/` must have zero warnings.
- **Affected files**: `notebooks/01_kraken_exploration.ipynb`

### LL-031: Automated fix scripts should be one-shot and self-deleting
- **Date**: 2026-01-04
- **Category**: Tooling
- **Severity**: Low
- **What happened**: `scripts/fix_notebook.py` was created to batch-fix notebook issues, then needed manual cleanup.
- **Root cause**: Utility scripts for one-time fixes accumulate if not cleaned up. They can also be accidentally re-run.
- **Rule going forward**: One-time fix scripts go in `/tmp/` or are deleted immediately after successful use. Only persistent scripts belong in `scripts/`. Add cleanup instructions in the same message that creates the script.
- **Affected files**: `scripts/`

---

## Porting Lessons

### LL-040: Mathematica Missing[] has no direct Python equivalent
- **Date**: 2026-01-04
- **Category**: Porting
- **Severity**: High
- **What happened**: Mathematica's `Missing[]` is a first-class object that propagates through calculations. Python has `None` but it raises `TypeError` in arithmetic.
- **Root cause**: Different language paradigms. Mathematica is expression-based and `Missing[]` is just another expression. Python is typed and `None` is not numeric.
- **Fix applied**: Boundary validation ensures `Missing`/`None` never reaches calculation layer. `is_missing()` consolidates all missing-value detection at boundaries. Downstream functions receive guaranteed-valid `Decimal` values.
- **Rule going forward**: Never try to replicate Mathematica's Missing-propagation in Python. Validate at boundaries, reject missing values immediately with `ValueError`, let orchestration decide recovery.
- **Affected files**: `validation/guards.py`, `marketdata/topofbook.py`

---

## Testing Traps

_(No entries yet — add as encountered)_

---

## Exchange-Specific Issues

_(Additional entries beyond API gotchas — add as encountered)_

---


### LL-067: validate_tob must use strictly-positive checks for prices and sizes
- **Date**: 2026-02-16
- **Category**: Correctness
- **Severity**: High
- **What happened**: `validate_tob()` checked `if v < 0` which permitted `Decimal("0")` for bid_px, ask_px, bid_sz, ask_sz. Zero buy_price causes `ZeroDivisionError` in `calc_return_raw()`.
- **Root cause**: Boundary validation used "non-negative" (>= 0) instead of "strictly positive" (> 0). Prices and sizes of zero have no market meaning.
- **Fix applied**: Changed to `if v <= 0` with error message "must be > 0".
- **Rule going forward**: Prices and sizes at data boundaries must be strictly positive. Zero is never a valid market data value. Use `require_positive()` for explicit boundary checks.
- **Affected files**: `src/uscryptoarb/marketdata/topofbook.py`

### LL-068: Import shim files in src/ risk shadowing installed packages
- **Date**: 2026-02-16
- **Category**: Architecture / Dependencies
- **Severity**: Critical
- **What happened**: `src/yaml.py` contained a minimal YAML parser with `_parse_scalar()` that converted decimal strings to `float`. If resolved before the real PyYAML, all config values like `"0.0055"` would silently become floats, which `to_decimal()` rejects.
- **Root cause**: Shim files created for "offline test environments" but both packages are hard dependencies. Python's import resolution can prioritize `src/` over `site-packages/` depending on `sys.path` ordering.
- **Fix applied**: Deleted `src/yaml.py` and `src/dotenv/`.
- **Rule going forward**: NEVER create .py files in `src/` that share names with third-party packages. If a package is needed, add it to `pyproject.toml` dependencies. If offline use is needed, use a virtual environment with pre-installed packages.
- **Affected files**: Deleted `src/yaml.py`, `src/dotenv/`

### LL-069: Fee schedule JSON files must be structurally synchronized
- **Date**: 2026-02-16
- **Category**: Testing / Data Integrity
- **Severity**: Medium
- **What happened**: Gemini `trading_accuracy` was added to production `fee_schedules.json` plan but was missing from both files. No test caught the structural gap.
- **Root cause**: Two independently-maintained copies of fee data (production vs test) with no structural consistency check.
- **Fix applied**: Added `test_fee_data_consistency.py` that verifies both files cover the same venues, pairs, currencies, and field names (but not values — test data is intentionally deterministic).
- **Rule going forward**: When adding a venue, pair, or currency to either fee_schedules.json, the drift guard test will fail until both files are updated. Run the guard test after any fee data changes.
- **Affected files**: `tests/unit/test_orchestration/test_fee_data_consistency.py`

## Document History

| Date | Entry | Author |
|------|-------|--------|
| 2026-02-13 | Initial creation with seed entries from project history | Claude |


### LL-050: asyncio.run() fails inside Jupyter — use nest_asyncio or top-level await
- **Date**: 2026-02-14
- **Category**: Tooling
- **Severity**: Medium
- **What happened**: `asyncio.run()` raised `RuntimeError: cannot be called from a running event loop` in Coinbase exploration notebook.
- **Root cause**: Jupyter/IPykernel already runs an asyncio event loop. `asyncio.run()` tries to create a new one, which is forbidden from within a running loop.
- **Fix applied**: Added `nest_asyncio.apply()` at top of async cell, then used top-level `await` instead of `asyncio.run()`.
- **Rule going forward**: In exploration notebooks, always use `nest_asyncio.apply()` or top-level `await` for async code. Reserve `asyncio.run()` for production scripts only.
- **Affected files**: `notebooks/02_coinbase_exploration.ipynb`

### LL-051: Coinbase cache-control: no-cache does NOT bypass server-side cache
- **Date**: 2026-02-14
- **Category**: Exchange-Specific
- **Severity**: Medium
- **What happened**: Two requests 200ms apart with and without `cache-control: no-cache` header returned identical timestamps, indicating the same cached response.
- **Root cause**: Despite Coinbase docs stating "Set cache-control: no-cache header on the API requests to bypass caching," the server-side 1s cache appears to ignore this header on public endpoints. The header may only work on authenticated endpoints, or the docs may be inaccurate.
- **Fix applied**: Documented finding. Production connector should not rely on this header for fresh data.
- **Rule going forward**: Assume ~1s staleness on Coinbase public endpoints. For real-time data, use WebSocket (Phase 2). When testing cache behavior, use sleep >1s to distinguish cache from unchanged prices.
- **Affected files**: `notebooks/02_coinbase_exploration.ipynb`

### LL-052: Coinbase public endpoints are a subset — no public batch BBO
- **Date**: 2026-02-14
- **Category**: Exchange-Specific
- **Severity**: High
- **What happened**: `GET /api/v3/brokerage/market/best_bid_ask` returned 404 Not Found.
- **Root cause**: Coinbase has two parallel endpoint families. Authenticated endpoints live under `/api/v3/brokerage/` and include `best_bid_ask` (batch BBO). Public endpoints live under `/api/v3/brokerage/market/` but only include: `product_book`, `products`, `product_candles`, `trades`, `server_time`. There is no public mirror of the batch `best_bid_ask` endpoint.
- **Fix applied**: Production connector will use individual `/market/product_book` calls per pair (8 calls × ~36ms = ~300ms total, well within polling interval).
- **Rule going forward**: When building connectors for public (unauthenticated) use, verify each endpoint exists in the "Public" section of the Coinbase API docs. Do not assume URL pattern `/market/{endpoint}` mirrors every authenticated `/{endpoint}`. When API keys are added (Phase 2+), switch to batch `/best_bid_ask` for efficiency.
- **Affected files**: `notebooks/02_coinbase_exploration.ipynb`, future `connectors/coinbase/client.py`

### LL-053: TradingAccuracy lives in calculation/calc_types.py — must migrate if connectors need it
- **Date**: 2026-02-14
- **Category**: Architecture
- **Severity**: Medium
- **What happened**: During calculation layer review, noticed TradingAccuracy is defined in `calculation/calc_types.py`. Per layering rules (Section 5.2), connectors can only import from Domain/Core. If connectors ever need to produce TradingAccuracy (e.g., from live fee/accuracy API responses), the type must move to `core/types.py`.
- **Root cause**: TradingAccuracy was created as part of the calculation layer because that's where it's consumed. But it's fundamentally a domain type.
- **Fix applied**: None yet — currently only test fixtures create TradingAccuracy, so no import violation exists.
- **Rule going forward**: When building the config/fee loader or any connector that produces TradingAccuracy, move the type to a shared domain location first. Same applies to TradingFeeRate and WithdrawalFee if connectors need to create them.
- **Affected files**: `calculation/calc_types.py` → Target path TBD (core/ directory was deleted)

### LL-054: TradingFeeRate.flat_fee must be applied in fee math even if currently zero
- **Date**: 2026-02-14
- **Category**: Correctness
- **Severity**: Medium
- **What happened**: Code review found that `calc_buy_leg()` and `calc_sell_leg()` only applied `fee_pct` but never `flat_fee`, even though the `TradingFeeRate` dataclass has a `flat_fee` field. All current exchanges use flat_fee=0, so no live bug existed.
- **Root cause**: During initial implementation, flat_fee was set to 0 for all exchanges (matching Mathematica's pattern where flatTradingfee=0) and the calculation code only implemented the percentage path.
- **Fix applied**: Added `flat_fee: Decimal = ZERO` parameter to both leg functions. Updated arb_calc.py to pass it through from FeeSchedule. Added tests for non-zero flat_fee.
- **Rule going forward**: When a dataclass field exists, the math must use it — even if the current value is zero. Dormant code paths become live bugs when config changes.
- **Affected files**: `calculation/fees.py`, `calculation/arb_calc.py`, `tests/unit/test_calculation/test_fees.py`

### LL-055: CHANGELOG claims must be verified against actual file state
- **Date**: 2026-02-14
- **Category**: Documentation
- **Severity**: Low
- **What happened**: CHANGELOG.md stated "replaced Section 12 inline table with pointer to MATHEMATICA_MAP.md" but the actual PROJECT_INSTRUCTIONS.md Section 12 still contained the full inline table with stale function names (`calc_return()` instead of `calc_return_raw()`, `calc_arb_final()` instead of `calc_arb_opportunity()`). The CLAUDE_INSTRUCTIONS.md mirrored the same stale names. This went undetected across multiple sessions.
- **Root cause**: The CHANGELOG entry was written during the session that *created* MATHEMATICA_MAP.md and *intended* to replace Section 12, but the actual replacement was not performed or was lost. Subsequent sessions trusted the CHANGELOG without verifying the file.
- **Fix applied**: Actually replaced Section 12 with a pointer. Updated CLAUDE_INSTRUCTIONS.md Key Functions to match real function names. Added verification step to review workflow.
- **Rule going forward**: When a CHANGELOG entry claims a documentation change, verify the target file actually reflects the change before committing. "Trust but verify" applies to our own documentation, not just external data.
- **Affected files**: `PROJECT_INSTRUCTIONS.md`, `CLAUDE_INSTRUCTIONS.md`, `CHANGELOG.md`

### LL-056: Exchange withdrawal fees are dynamic and drift over time
- **Date**: 2026-02-16
- **Category**: Data Accuracy
- **Severity**: Medium
- **What happened**: Fee audit found Kraken BTC withdrawal fee had decreased from 0.00005 to ~0.00001 BTC, and SOL from 0.02 to ~0.005 SOL. All three exchanges now use dynamic (network-based) withdrawal fees rather than fixed schedules.
- **Root cause**: Withdrawal fees were captured once during initial development and never refreshed. Network fees change with blockchain congestion.
- **Fix applied**: Updated Kraken BTC and SOL withdrawal estimates. Added audit date to _sources.
- **Rule going forward**: Withdrawal fees should be re-audited quarterly or when adding a new exchange. Phase 2+ should implement live fee lookups from exchange APIs.
- **Affected files**: resources/fee_schedules.json, tests/fixtures/fee_schedules.json

### LL-057: Exchange fee tier structures change without notice to downstream consumers
- **Date**: 2026-02-16
- **Category**: Data Accuracy
- **Severity**: High
- **What happened**: Coinbase introduced "Intro 1" and "Intro 2" tiers with dramatically higher fees (1.20% taker) for low-volume traders. Our config used 0.60% which was the old taker rate / new Intro 1 maker rate — neither correct for our use case. Kraken's 0.26% didn't match any current tier.
- **Root cause**: Fee values were set during initial development and assumed to be stable. Exchange fee structures can change at any time.
- **Fix applied**: Full audit against primary exchange documentation. Updated all trading fee rates with source URLs and audit dates.
- **Rule going forward**: Fee rates must be re-verified against exchange documentation at least quarterly. Each fee value in config.yaml should have a comment with source URL and verification date.
- **Affected files**: config.yaml, docs/DECISION_LOG.md

### LL-058: Config dataclasses must be defined in the layer that owns their contract
- **Date**: 2026-02-15
- **Category**: Architecture
- **Severity**: Medium
- **What happened**: `EmailConfig` was defined in `orchestration/config.py` but imported by `notification/email.py`, creating an upward import from notification → orchestration. This violated Section 5.2 import rules.
- **Root cause**: During orchestration implementation, all config dataclasses were co-located in one file for convenience. The layering implication was missed because EmailConfig was created alongside other orchestration config types.
- **Fix applied**: Moved `EmailConfig` to `notification/email.py`. Orchestration imports it from there (allowed: orchestration can import everything).
- **Rule going forward**: When creating a config dataclass, ask: "Which layer consumes this type?" Define the type in that layer, not in the layer that happens to build/populate it. Builders import from consumers, not vice versa. See also LL-053 for the same pattern with calculation types.
- **Affected files**: `notification/email.py`, `orchestration/config.py`, `tests/unit/test_notification/test_email.py`


### LL-059: Coinbase _fetch_product_book dead code — ValueError caught by own except
- **Date**: 2026-02-15
- **Category**: Code Quality
- **Severity**: Low
- **What happened**: In `connectors/coinbase/client.py` (pre-refactor), lines 99-109 of `_fetch_product_book()` contained dead code. When HTTP status >= 400, the code tried to extract a Coinbase error message and raise ValueError, but the ValueError was immediately caught by the surrounding `except (ValueError, KeyError, TypeError): pass` block. The `raise_for_status()` on the next line always ran instead.
- **Root cause**: The `except` clause was intended to catch JSON parsing errors (ValueError from `.json()`, KeyError from missing keys), but it also caught the intentionally raised ValueError from the error message extraction.
- **Fix applied**: Not fixed in this session per Coding Rule 10.6 (preserve behavior unless explicitly changing). The BaseAsyncConnector refactor moves HTTP error handling to `_fetch_with_retry()` which calls `raise_for_status()` directly, so the dead code path is eliminated naturally. The Coinbase-specific `_fetch_product_book()` now only handles API errors in HTTP 200 responses.
- **Rule going forward**: When raising exceptions inside try/except blocks, ensure the except clause doesn't catch the intentionally raised exception. Use more specific exception types or restructure the try/except scope.
- **Affected files**: `connectors/coinbase/client.py` (historical), `connectors/connector_base.py` (fixed by design)


### LL-060: Second instance of a pattern = mandatory refactor flag
- **Date**: 2026-02-15
- **Category**: Process
- **Severity**: High
- **What happened**: Code review found 5 DRY violations (duplicated retry loops, config helpers, symbol construction, fixture boilerplate) that accumulated across sessions. Each duplication was defensible when created — Coding Rule 10.1 says "don't generalize until 2 real callers" — but no session flagged the 2nd instance for follow-up.
- **Root cause**: The workflow had no checkpoint between "2nd instance created" and "refactor needed." Sessions focused on delivering features vertically and never looked across the codebase horizontally.
- **Fix applied**: Added Coding Rule 10.8 (Refactor Checkpoint) and a mandatory "Refactor Candidates" section to the SESSION_HANDOFFS template. When a session creates a 2nd instance of a pattern, it must be flagged. The next session must either refactor or explicitly defer with rationale in DECISION_LOG.
- **Rule going forward**: When you create a 2nd connector, 2nd config helper, 2nd fixture shape, or any 2nd instance of a structural pattern — stop and add it to "Refactor Candidates" in SESSION_HANDOFFS before ending the session.
- **Affected files**: CLAUDE_INSTRUCTIONS.md (Rule 10.8), docs/SESSION_HANDOFFS.md (template), docs/LESSONS_LEARNED.md (this entry)

### LL-061: Don't assert production config values in unit tests
- **Date**: 2026-02-15
- **Context**: Multiple tests called `load_config("config.yaml")` and asserted hardcoded values like `threshold == Decimal("0.0055")`. Changing any config.yaml value broke tests.
- **Lesson**: Unit tests that verify parsing logic should use synthetic YAML fixtures with known values. A single smoke test can validate the production config loads without asserting specific values.
- **Pattern**: `conftest.py` provides `FULL_CFG` string and `full_config_path` fixture that writes it to `tmp_path`. Tests assert against the synthetic values they control.
- **Applies to**: Any test that calls `load_config()` — always pass a fixture path, never the production file, unless it's a smoke test.

### LL-062: Gemini ticker endpoints lack bid/ask sizes — must use order book
- **Date**: 2026-02-15
- **Category**: Exchange-Specific
- **Severity**: High
- **What happened**: Explored Gemini ticker V1 (`/v1/pubticker/{symbol}`), ticker V2 (`/v2/ticker/{symbol}`), and pricefeed (`/v1/pricefeed`). None include bid/ask sizes — only bid/ask prices.
- **Root cause**: Gemini's ticker endpoints are designed for price reporting, not order book depth. The V1 ticker returns `{bid, ask, last, volume}` and the V2 adds OHLC + hourly changes, but neither includes the quantity available at the best bid/ask.
- **Fix applied**: Production connector will use the order book endpoint (`/v1/book/{symbol}?limit_bids=1&limit_asks=1`) which returns price, amount, and timestamp per level.
- **Rule going forward**: Before building any exchange connector, verify the chosen endpoint provides ALL four TopOfBook fields (bid_px, bid_sz, ask_px, ask_sz). Do not assume ticker endpoints include sizes — Kraken does, but Coinbase and Gemini do not.
- **Affected files**: `notebooks/03_gemini_exploration.ipynb`, future `connectors/gemini/client.py`

### LL-063: Gemini order book timestamps are Unix seconds as integer strings
- **Date**: 2026-02-15
- **Category**: Exchange-Specific
- **Severity**: Medium
- **What happened**: Gemini order book `timestamp` field is a string containing Unix seconds as an integer (e.g., `"1547147541"`), not a float, not milliseconds, and not ISO 8601.
- **Root cause**: Gemini's API predates modern timestamp conventions. The value is seconds since epoch with integer precision (no sub-second granularity).
- **Fix applied**: Parser uses `int(timestamp_str) * 1000` to convert to milliseconds for consistency with TopOfBook's `ts_exchange_ms` field.
- **Rule going forward**: Each exchange has its own timestamp format. Document and handle explicitly in the parser: Kraken = Unix seconds (float in orderbook), Coinbase = ISO 8601 with microseconds, Gemini = Unix seconds (integer string). Never assume timestamp format transfers across exchanges.
- **Affected files**: `notebooks/03_gemini_exploration.ipynb`, future `connectors/gemini/parser.py`

### LL-064: Python 3.14 + nest_asyncio + anyio breaks httpx.AsyncClient in notebooks
- **Date**: 2026-02-15
- **Category**: Tooling
- **Severity**: Low
- **What happened**: In Gemini exploration notebook (03), `httpx.AsyncClient` inside `async with` raised `TypeError: cannot create weak reference to 'NoneType' object` on both `client.get()` calls and `__aexit__` cleanup. All 8 async fetches failed.
- **Root cause**: Python 3.14's asyncio + `nest_asyncio` + anyio (used by httpcore) interact badly. anyio's `CancelScope.__enter__` tries to look up current task in `WeakKeyDictionary`, but under `nest_asyncio` the task resolves to `None`, which can't be weak-referenced.
- **Fix applied**: Skipped async cell in notebook. Synchronous `httpx.get()` calls in Section 4 already proved all 8 endpoints work. Added error-printing fallback to diagnose silently-swallowed exceptions.
- **Rule going forward**: Exploration notebooks on Python 3.14 should test async patterns with try/except wrapper that prints errors, not silently swallows them. Production connector runs in real `asyncio.run()` event loop (not `nest_asyncio`) and is unaffected. If async testing needed in notebooks on 3.14, consider `asyncio.run()` in subprocess or downgrade to Python 3.13.
- **Affected files**: `notebooks/03_gemini_exploration.ipynb`


### LL-065: Duplicate module names across packages break AI-assisted navigation and project knowledge
- **Date**: 2026-02-16
- **Category**: Architecture / Naming
- **Severity**: High
- **What happened**: Multiple `.py` files shared basenames across packages, causing ambiguous search/navigation results for humans and coding agents.
- **Root cause**: No module-name uniqueness rule existed at the repository level.
- **Fix applied**: Renamed five modules and updated all importers/tests/docs. Added Coding Rule 10.8 and pre-implementation uniqueness verification.
- **Rule going forward**: Every new `.py` module name must be unique across `src/uscryptoarb/` (excluding `__init__.py`). Connector sub-packages are the explicit exception for `client.py`, `parser.py`, and `symbols.py`.
- **Affected files**: Renamed source modules/importers, renamed tests, `PROJECT_INSTRUCTIONS.md`, `CLAUDE_INSTRUCTIONS.md`.

### LL-066: Three-way instruction document drift — establish single source of truth
- **Date**: 2026-02-16
- **Category**: Documentation / Process
- **Severity**: Medium
- **What happened**: `PROJECT_INSTRUCTIONS.md`, `CLAUDE_INSTRUCTIONS.md`, and the Claude.ai UI instruction copy drifted. Canonical rules and file trees were inconsistent across locations.
- **Root cause**: Missing authority hierarchy and missing required regeneration step after instruction edits.
- **Fix applied**: Established hierarchy: `PROJECT_INSTRUCTIONS.md` (canonical) -> `CLAUDE_INSTRUCTIONS.md` (derived) -> Claude.ai UI (manual copy target). Added regeneration step to propagation checklist.
- **Rule going forward**: Always edit `PROJECT_INSTRUCTIONS.md` first, regenerate `CLAUDE_INSTRUCTIONS.md`, then copy into UI. Never update those three independently.
- **Affected files**: Instruction documents and session handoff process.

### LL-067: Integration tests need now_ms() patched in 3 separate modules
- **Date**: 2026-02-16
- **Category**: Testing
- **What happened**: `now_ms()` is imported directly in `connector_base.py`, `kraken/client.py`, and `scan_loop.py`. Patching only one or two leaves the others using real wall-clock time, causing staleness filtering to reject all data (since fixture timestamps are in the past).
- **Rule**: When patching utility functions for integration tests, search for ALL import sites with `grep -rn "from.*import now_ms" src/` and patch every one.
- **References**: tests/integration/test_end_to_end.py `_patch_now_ms` decorator

### LL-068: Integration tests should bypass create_connectors() and build connectors directly
- **Date**: 2026-02-16
- **Category**: Testing
- **What happened**: `create_connectors()` creates real `httpx.AsyncClient()` instances. Integration tests need MockTransport-backed clients. Building connectors manually is cleaner than monkeypatching the factory.
- **Rule**: For HTTP-level mocking, construct connector instances directly with `httpx.AsyncClient(transport=MockTransport(handler))`. Test `create_connectors()` separately in unit tests.
- **References**: DEC-018 (shared constructor signature makes this straightforward)

### LL-069: Kraken _request() unwraps the {"error":[], "result":{}} envelope — mocks must include it
- **Date**: 2026-02-16
- **Category**: Testing / Connectors
- **What happened**: Kraken mock responses must include the full `{"error": [], "result": {...}}` envelope because `KrakenClient._request()` validates and unwraps it before passing to the parser.
- **Rule**: Always match the full response envelope when mocking exchange APIs, not just the inner payload. Review the client's response validation code before writing mock responses.
