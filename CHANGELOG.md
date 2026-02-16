# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
- `notebooks/03_gemini_exploration.ipynb`: Gemini API exploration notebook covering symbol mapping, order book endpoint (primary data source — tickers lack bid/ask sizes), rate limits, error handling, timestamp format, and production connector design notes

### Added
- `connectors/base.py`: `BaseAsyncConnector` ABC with shared constructor, venue property, and `_fetch_with_retry()` retry/backoff/rate-limit logic (DEC-018)
- `venues/symbols.py`: `create_translator()` factory function for validated SymbolTranslator construction
- `tests/conftest.py`: `fee_schedule_factory` parametrized fixture for building FeeSchedule objects with explicit per-field control
- `tests/unit/test_connectors/test_base_connector.py`: 13 tests for shared retry logic (timeout, 5xx, 429, 404, exhausted retries, rate limiting, header/param passthrough)
- **Orchestration layer** (`src/uscryptoarb/orchestration/`) — imperative shell wiring pure pipeline to real I/O
- **Verbose spread logging** in `orchestration/scanner.py` — per-pair bid/ask and best raw spread logged on every scan cycle for pipeline diagnostics
  - `config.py`: YAML + .env config loader with validation boundary, builds FeeSchedule objects for all (venue, pair) combinations
  - `scanner.py`: Async polling loop with concurrent venue fetching, per-pair arbitrage detection, graceful shutdown
- **Notification layer** (`src/uscryptoarb/notification/`) — email alerts for detected opportunities
  - `email.py`: Gmail STARTTLS email sender, async via `to_thread()`, best-effort (never crashes scanner)
- **CLI entry point** (`src/uscryptoarb/__main__.py`) — `python -m uscryptoarb` with `--dry-run`, `--trace-pair`, `--log-level`
- **Package resources** (`src/uscryptoarb/resources/fee_schedules.json`) — production fee data (copy of test fixtures)
- `config.yaml`: Default configuration file with per-pair trade amounts, per-venue connector settings
- `.env.example`: Template for sensitive environment variables (SMTP credentials, future API keys)
- `tests/helpers.py`: Shared test utilities (DummyRateLimiter extracted per Coding Rule 10.1)
- `pyyaml>=6.0` and `python-dotenv>=1.0` added as runtime dependencies
- **Calculation layer** (`src/uscryptoarb/calculation/`) — pure math layer for Type-2 arbitrage detection
  - `types.py`: TradingFeeRate, WithdrawalFee, TradingAccuracy, FeeSchedule, ArbLeg, ArbOpportunity dataclasses
  - `returns.py`: calc_return_raw, calc_return_grs, calc_return_net, calc_profit_base
  - `fees.py`: calc_buy_leg, calc_sell_leg, effective_buy_cost, effective_sell_proceeds, total_buy_cost, net_sell_proceeds
  - `sizing.py`: calc_kelly_fraction, calc_kelly_amount, calc_position_size (Kelly Criterion)
  - `arb_calc.py`: calc_arb_opportunity, calc_all_opportunities, sort_opportunities, filter_profitable
- **Strategy layer** (`src/uscryptoarb/strategy/`) — pure trade selection logic for Type-2 arbitrage detection
  - `selection.py`: passes_threshold, select_trade — threshold checking and best-trade picking
  - `scanner.py`: filter_valid_exchanges, find_trades_to_execute — top-level scan pipeline
- **Strategy layer tests** (`tests/unit/test_strategy/`) — 20+ unit tests covering threshold boundaries, staleness filtering, multi-exchange selection, and golden value verification
- Shared TopOfBook/FeeSchedule fixtures refactored to `tests/conftest.py` (available to all test packages)
- Gemini BTC/USD test fixtures (TopOfBook + FeeSchedule) for 3-exchange strategy tests
- **Fee schedules fixture** (`tests/fixtures/fee_schedules.json`) — hardcoded fee/accuracy data for Kraken, Coinbase, Gemini across all 8 pairs
- **50 unit tests** for calculation layer with deterministic Decimal fixtures
- `connectors/coinbase/`: Second exchange connector (Coinbase)
  - `symbols.py`: Verified symbol mapping for all 8 target pairs (canonical → BTC-USD format)
  - `parser.py`: Pure parsing for product_book responses → TopOfBook, with ISO 8601 timestamp conversion
  - `client.py`: Async httpx-based client with per-pair requests (no public batch endpoint — LL-052), rate limiting, retry with backoff, cache-control header (LL-051)
- `fixtures/coinbase_*.json`: Coinbase API response fixtures from live exploration notebook (2026-02-14)
- `notebooks/02_coinbase_exploration.ipynb`: Coinbase Advanced Trade API exploration notebook covering product discovery, symbol mapping, BBO fetching (SDK and raw httpx), TopOfBook parsing, rate limit testing, and SDK vs httpx comparison
- `docs/LESSONS_LEARNED.md`: Mistake prevention database with seed entries from project history
- `docs/SESSION_HANDOFFS.md`: Append-only session continuity log for multi-chat workflows
- `docs/DECISION_LOG.md`: Architectural decision records with rationale (10 seed entries)
- `docs/MATHEMATICA_MAP.md`: Comprehensive Mathematica→Python porting tracker (~58 functions)
- `tests/fixtures/README.md`: Test fixture conventions and provenance documentation
- PROJECT_INSTRUCTIONS.md Section 14: Operational Documents reference and workflow integration
- GitHub Actions CI workflow with Ruff, mypy, and pytest
- `validation/guards.py`: Runtime validation guards (`is_missing`, `require_present`, `require_positive`, `require_non_negative`)
- Unit tests for validation module (30+ test cases)
- mypy strict configuration in pyproject.toml
- `py.typed` marker for PEP 561 compliance
- `connectors/base.py`: `ExchangeConnector` Protocol defining the interface for all exchange connectors
- `connectors/kraken/`: First exchange connector (Kraken)
  - `symbols.py`: Verified symbol mapping for all 8 target pairs (BTC/USD, BTC/USDC, LTC/USD, LTC/USDC, LTC/BTC, SOL/USD, SOL/USDC, SOL/BTC)
  - `parser.py`: Pure parsing functions for ticker and orderbook responses → TopOfBook
  - `client.py`: Async httpx-based client with rate limiting, retry, and startup symbol validation
- `http/rate_limiter.py`: Async rate limiter for respecting exchange API limits
- `venues/symbols.py`: Added `to_canonical()` reverse lookup to SymbolTranslator
- `fixtures/`: Kraken API response fixtures from live exploration notebook
- `tests/conftest.py`: Shared pytest fixtures for API response data
- `httpx>=0.27` added as runtime dependency
- `notebooks/02_coinbase_exploration.ipynb`: Complete Coinbase API exploration — symbol mapping, BBO data, SDK vs httpx comparison, TopOfBook parsing, rate limits, error handling, product details

### Changed
- Decoupled orchestration tests from production `config.yaml` values. All parsing logic tests now use a synthetic YAML fixture. A single `test_production_config_loads` smoke test validates the real file loads without error.

- `connectors/kraken/client.py`: `KrakenClient` now extends `BaseAsyncConnector`; retry logic delegated to shared `_fetch_with_retry()`, Kraken-specific response validation preserved in `_request()`
- `connectors/coinbase/client.py`: `CoinbaseClient` now extends `BaseAsyncConnector`; retry logic delegated to shared `_fetch_with_retry()`, Coinbase-specific response validation preserved in `_fetch_product_book()`
- `connectors/kraken/symbols.py`: Uses `create_translator()` factory instead of direct `SymbolTranslator()` construction
- `connectors/coinbase/symbols.py`: Uses `create_translator()` factory instead of direct `SymbolTranslator()` construction
- `orchestration/config.py`: `_required_decimal()` and `_required_int()` replaced by generic `_required_type()` helper
- `tests/conftest.py`: Fee fixtures (`kraken_btc_usd_fees`, `coinbase_btc_usd_fees`, `gemini_btc_usd_fees`) refactored as thin wrappers around `fee_schedule_factory`; intermediate sub-fixtures (individual fee rates, withdrawals, accuracies) removed — factory handles construction directly
- `tests/unit/test_connectors/test_kraken/test_client.py`: DummyRateLimiter extracted to tests/helpers.py
- `tests/unit/test_connectors/test_coinbase/test_client.py`: DummyRateLimiter extracted to tests/helpers.py

### Fixed
- `connectors/base.py`: Unified 429 (rate limit) retry handling — Kraken connector previously did not retry on HTTP 429, now both connectors retry via shared logic (DEC-018)
- `notification/email.py`: Fixed layering violation — `EmailConfig` moved from `orchestration/config.py` to `notification/email.py` (DEC-017). Notification layer no longer imports from orchestration.
- `notification/email.py`: Fixed SMTP connection leak — `_send_smtp()` now uses context manager (`with smtplib.SMTP(...)`) to ensure socket cleanup on auth or send failures.
- `orchestration/config.py`: Removed dead code — unreachable `if raw is None` checks in `_required_decimal()` and `_required_int()` after `require_present()` already validates.
- `docs/MATHEMATICA_MAP.md`: Fixed stale module paths in Section 13 (`core/decimal_utils.py` → `misc/decimals.py`, `core/pair_utils.py` → `markets/pairs.py`)
- `PROJECT_INSTRUCTIONS.md`: Updated Section 5.3 file structure to match actual module layout (added orchestration/, notification/, resources/, http/, __main__.py; corrected module paths)
- `calculation/fees.py`: `calc_buy_leg()` and `calc_sell_leg()` now apply `flat_fee` from `TradingFeeRate` (was silently ignored; all exchanges currently use 0)
- `calculation/arb_calc.py`: `calc_arb_opportunity()` now passes `flat_fee` through to leg calculations
- `calculation/returns.py`: Removed unused `CALC_CONTEXT_PREC` constant
- Documentation sync: PROJECT_INSTRUCTIONS.md Sections 5.3, 12, 13 updated to match implemented calculation layer
- Documentation sync: MATHEMATICA_MAP.md Sections 1, 5 updated with correct statuses and module paths
- Documentation sync: SESSION_HANDOFFS.md calculation layer entry — restored truncated Next Steps
- `strategy/scanner.py`: Removed redundant `sort_opportunities()` call in `find_trades_to_execute()` — `select_trade()` already sorts internally (Coding Rule 10.1)
- `PROJECT_INSTRUCTIONS.md` Section 12: Actually replaced inline table with pointer to MATHEMATICA_MAP.md (per DEC-010; previous CHANGELOG entry was premature — the table had remained with stale function names like `calc_return()` and `calc_arb_final()`)
- `CLAUDE_INSTRUCTIONS.md`: Updated stale function names in Key Functions section to match actual implementations (`calc_return_raw/grs/net()`, `calc_arb_opportunity()`, added `find_trades_to_execute()`)

### Changed
- PROJECT_INSTRUCTIONS.md: Added operational docs to Source Documents (Section 2), Workflow (7.2), Propagation Rule (7.3), Deliverable Format (7.4), PR Checklist (10.3), Pre-Implementation and Propagation Checklists (13); replaced Section 12 inline table with pointer to MATHEMATICA_MAP.md
- CLAUDE_INSTRUCTIONS.md: Added doc searches to workflow, pre-implementation verification, deliverable format, and reference section
- README.md: Added Documentation section with links to all project docs
- Documented "Data Trust Boundaries" pattern (validate at boundaries, trust downstream) across PROJECT_INSTRUCTIONS.md (Section 6.2), CLAUDE_INSTRUCTIONS.md, and `validation/guards.py` module docstring
- `pyproject.toml`: Added httpx to runtime dependencies
- Development priority resequenced: orchestration layer before Gemini connector (DEC-016)

## [0.0.1] - 2025-01-04

### Added
- **Orchestration layer** (`src/uscryptoarb/orchestration/`) — imperative shell wiring pure pipeline to real I/O
  - `config.py`: YAML + .env config loader with validation boundary, builds FeeSchedule objects for all (venue, pair) combinations
  - `scanner.py`: Async polling loop with concurrent venue fetching, per-pair arbitrage detection, graceful shutdown
- **Notification layer** (`src/uscryptoarb/notification/`) — email alerts for detected opportunities
  - `email.py`: Gmail STARTTLS email sender, async via `to_thread()`, best-effort (never crashes scanner)
- **CLI entry point** (`src/uscryptoarb/__main__.py`) — `python -m uscryptoarb` with `--dry-run`, `--trace-pair`, `--log-level`
- **Package resources** (`src/uscryptoarb/resources/fee_schedules.json`) — production fee data (copy of test fixtures)
- `config.yaml`: Default configuration file with per-pair trade amounts, per-venue connector settings
- `.env.example`: Template for sensitive environment variables (SMTP credentials, future API keys)
- `tests/helpers.py`: Shared test utilities (DummyRateLimiter extracted per Coding Rule 10.1)
- `pyyaml>=6.0` and `python-dotenv>=1.0` added as runtime dependencies
- `notebooks/02_coinbase_exploration.ipynb`: Coinbase Advanced Trade API exploration notebook covering product discovery, symbol mapping, BBO fetching (SDK and raw httpx), TopOfBook parsing, rate limit testing, and SDK vs httpx comparison
- Initial project structure
- `misc/decimals.py`: `to_decimal()`, `floor_to_step()`, `ceil_to_step()`
- `markets/pairs.py`: `CanonicalPair`, `parse_pair()`
- `venues/registry.py`: `VenueInfo`, `ohio_eligible()`
- `venues/symbols.py`: `SymbolTranslator`
- `config/app_config.py`: `AppConfig`, `validate_config()`
- `marketdata/topofbook.py`: `TopOfBook`, `validate_tob()`, `tob_from_raw()`
- Basic test suite for registry and config validation
- PROJECT_INSTRUCTIONS.md with comprehensive coding standards

[Unreleased]: https://github.com/raytroy/uscryptoarb/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/raytroy/uscryptoarb/releases/tag/v0.0.1
