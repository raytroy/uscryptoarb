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
- **Affected files**: `venues/symbols.py`, `notebooks/01_kraken_exploration.ipynb`

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
- **Affected files**: `core/decimal_utils.py`, `validation/guards.py`

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
