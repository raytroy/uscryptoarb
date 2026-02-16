# USCryptoArb — Claude Instructions

## Mission
Cross-exchange crypto arbitrage for Ohio. Build a Python arbitrage system using the proven Mathematica system (10,000+ trades) as reference and guide — improving architecture, algorithms, and strategies where Python's ecosystem or modern practices offer advantages. Type-2 (same pair, different exchanges) primary.

## Relationship to Mathematica
The Mathematica notebook is a **validated reference**, not gospel. It proves the arbitrage logic works and provides battle-tested patterns from 10,000+ real trades. However:
- Where Python idioms, modern libraries, or better algorithms exist, **prefer those over literal porting**.
- Where the Mathematica approach is clunky, over-engineered, or limited by Mathematica's language constraints, **redesign freely**.
- Where the Mathematica approach is elegant and proven, **adopt it gratefully**.
- When in doubt, **suggest the better approach** rather than defaulting to what Mathematica does.

## Exchanges
Primary: Kraken (custom httpx), Coinbase (custom httpx), Gemini (custom httpx)
Secondary: Bitstamp, bitFlyer, OKCoin

**Symbol formats**: Kraken=`XBTUSD` (XBT for BTC) | Coinbase=`BTC-USD` | Gemini=`btcusd`

All translation runs through `venues/symbol_translator.py` and connector-specific `symbols.py` modules.

## Pairs
BTC/USD, BTC/USDC, LTC/USD, LTC/USDC, LTC/BTC, SOL/USD, SOL/USDC, SOL/BTC
**USD ≠ USDC** (no implicit conversion)

## Key Mathematica Patterns (as reference, not mandate)
- **MissingCheck**: `is_missing(v)` - validate at every boundary
- **Limiting Reactant**: buyBalance, sellBalance, buyLiquidity, sellLiquidity
- **Returns**: returnRaw → returnGrs → returnNet
- **Fee Flow**: MktCurrAmt → BaseCurrAmt → MktCurrAmtGrs → BaseCurrAmtNet
- Databases: tradingFeesDB, withdrawalDB, tradingInfoDB

## Data Trust Boundaries
**Principle**: Validate once at boundaries, trust downstream. No validation code in `calculation/` or `strategy/`.

**Boundaries** (validation happens here):
- Connector `parse_*/fetch_*` functions → call `require_*` guards
- Factory functions: `tob_from_raw()`, not raw `TopOfBook()` constructor
- Dataclass `__post_init__` → critical invariants (crossed book, etc.)
- Config loaders → `require_present()` on required fields

**Trusted zones** (NO validation code):
- `calculation/` — receives validated types, just does math
- `strategy/` — receives validated types, just does logic

**Guards** (`validation/guards.py`):
- `is_missing(v)` — True for None, "", [], {}, NaN, Infinity
- `require_present(v, name)` — raise if missing, return v
- `require_positive(v, name)` — for prices/fees (must be > 0)
- `require_non_negative(v, name)` — for balances (can be 0)

**Pattern**: Factory + frozen dataclass = validated domain type
```python
# Boundary: connector calls factory
tob = tob_from_raw(venue="kraken", pair="BTC/USD", bid_px=raw["bid"], ...)

# Downstream: pure function trusts input
spread = tob.ask_px - tob.bid_px  # No validation needed
```

## Key Functions (Mathematica → Python)
`MarketBaseConvert[]`→`market_base_convert()`, `PairTranslator[]`→`pair_translator()`, `ReturnCalc[]`→`calc_return_raw()` / `calc_return_grs()` / `calc_return_net()`, `ArbCalcFinal[]`→`calc_arb_opportunity()`, `TradesToExecute[]`→`find_trades_to_execute()`, `SelectTradeToExecute[]`→`select_trade()`, `RunFinal[]`→`run_scan_loop()` in orchestration

See `docs/MATHEMATICA_MAP.md` for the complete mapping of all ~58 functions (DEC-010).

## Architecture
Orchestration (imperative) → Execution → Connectors
↓
Strategy (pure) → Calculation (pure) → Validation (pure) → Domain/Core (pure)
↓
Notification (imperative, best-effort)
Imports flow DOWN only. Circular imports = hard failure.

## File Structure (Post-Rename)
src/uscryptoarb/
main.py              # CLI entry point (python -m uscryptoarb)
config/
app_config.py          # Legacy AppConfig (superseded by orchestration/config.py)
misc/
decimals.py            # to_decimal, floor_to_step, ceil_to_step
markets/
pairs.py               # CanonicalPair, parse_pair
venues/
registry.py            # VenueInfo, ohio_eligible
symbol_translator.py   # SymbolTranslator, to_canonical, create_translator
marketdata/
topofbook.py           # TopOfBook, validate_tob, tob_from_raw
validation/
guards.py              # is_missing, require_present, require_positive, require_non_negative
http/
backoff.py             # Bounded retry with async backoff
rate_limiter.py        # RateLimiter for exchange API rate limiting
calculation/
calc_types.py          # TradingFeeRate, WithdrawalFee, TradingAccuracy, FeeSchedule, ArbLeg, ArbOpportunity
returns.py             # calc_return_raw, calc_return_grs, calc_return_net, calc_profit_base
fees.py                # calc_buy_leg, calc_sell_leg, effective_buy_cost, effective_sell_proceeds
sizing.py              # calc_kelly_fraction, calc_kelly_amount, calc_position_size
arb_calc.py            # calc_arb_opportunity, calc_all_opportunities, sort_opportunities, filter_profitable
strategy/
selection.py           # select_trade, passes_threshold
trade_finder.py        # find_trades_to_execute, filter_valid_exchanges
connectors/
connector_base.py      # ExchangeConnector Protocol, BaseAsyncConnector ABC
kraken/
symbols.py           # Kraken symbol mapping (BTC/USD → XXBTZUSD)
parser.py            # parse_ticker_response, parse_orderbook_response
client.py            # KrakenClient (async httpx)
coinbase/
symbols.py           # Coinbase symbol mapping (BTC/USD → BTC-USD)
parser.py            # parse_product_book_response
client.py            # CoinbaseClient (async httpx)
gemini/
symbols.py           # Gemini symbol mapping (BTC/USD → btcusd)
parser.py            # parse_book_response
client.py            # GeminiClient (async httpx)
notification/
email.py               # EmailConfig, send_alert, format_opportunity_email
orchestration/
config.py              # ScannerConfig, load_config, _build_fee_schedules
scan_loop.py           # run_scan_loop, run_scan_cycle, create_connectors, fetch_all_venues
resources/
fee_schedules.json     # Production fee data (withdrawal fees, trading accuracy)
tests/
conftest.py              # Shared fixtures (TopOfBook, FeeSchedule, etc.)
helpers.py               # Shared test utilities (DummyRateLimiter)
unit/
test_calculation/      # Fee math, return calcs, arb opportunity tests
test_connectors/
test_connector_base.py  # BaseAsyncConnector shared retry logic tests
test_kraken/         # Kraken parser, client, symbols tests
test_coinbase/       # Coinbase parser, client, symbols tests
test_gemini/         # Gemini parser, client, symbols tests
test_http/             # Rate limiter, backoff tests
test_notification/     # Email formatting and sending tests
test_orchestration/
test_scan_loop.py    # Scan loop, connector creation tests
test_strategy/
test_trade_finder.py # Trade finding, filtering tests
test_validation/       # Guard function tests
fixtures/
README.md              # Fixture provenance documentation
fee_schedules.json     # Test fee data
notebooks/                 # Exploration (01_kraken, 02_coinbase, 03_gemini)
docs/                      # LESSONS_LEARNED, SESSION_HANDOFFS, DECISION_LOG, MATHEMATICA_MAP

---
## CODING RULES

### 0. Prime Directive
Correct, testable, observable, cross-platform code. Reliability over cleverness. If uncertain, fail closed or ask.

### 1. Source of Truth & Workflow
**1.1** GitHub latest commit is single source of truth. Don't assume names/structure—verify.
**1.2** Permissioned: Analyze (search LESSONS_LEARNED, DECISION_LOG, MATHEMATICA_MAP) → Plan → **(User Approval)** → Implement → Validate → Summarize (update ops docs).
**1.3** Deliver copy-pasteable blocks: full file, full function, or exact block replacement. No unified diffs.

### 2. Programming Model
**2.1** Functional core, imperative shell. Pure functions for transforms/calcs, explicit I/O, composition over inheritance. Shell only for HTTP/WS/files/scheduling.
**2.2** Immutability default. Use `@dataclass(frozen=True, slots=True)`. Return new objects, don't mutate.
**2.3** All external I/O must be async/await. No blocking in event loop.
**2.4** NO HACKS. Always identify root cause. If uncertain, ask.

### 3. Correctness (Money & Markets)
**3.1** NO FLOATS for money/probabilities. Use `Decimal` with consistent rounding.
**3.2** Core computations must be deterministic from: input snapshots, config, fee model, code version.
**3.3** Validate invariants at boundaries: orderbook sorted, bids ≤ asks, non-negative sizes, monotonic timestamps. Unknown inputs block opportunity or produce UNVERIFIED result.

### 4. Data & Schema
- UTC for all timestamps
- Canonical schemas: OrderBookSnapshot, BestBidAsk, FeeModel, Opportunity, Leg
- Every opportunity includes: prices used, fee inputs/outputs, legs, sizing, validation outcomes

### 5. Observability
**5.1** Use `logging` not print. UTF-8 safe, no secrets, structured enough to trace pipeline. Include market ID, venue, run_id, timestamp.
**5.2** Debug logs for: orderbook sorting, fee calcs (in/out), validation failures. Explainable rejection over silent skip.

### 6. Error Handling
- Timeouts on all network calls
- Bounded retries with exponential backoff
- Rate limiting per exchange
- Graceful degradation: stale detection, reconnect logic, cancellation-safe async
- Idempotent ingestion where possible

### 7. Testing
**7.1** Required: fee math, BBO extraction, orderbook sorting, return calcs, validation gates. Bug fix = regression test.
**7.2** Tests must be deterministic: no live network, use fixtures, stable rounding.

### 8. Tooling
Lint: Ruff | Types: mypy | Package: pip + requirements.txt
CI: Ruff → mypy → pytest

### 9. Security
No secrets in code—use env vars/.env excluded from git. Never log credentials. Validate config at startup, fail fast.

### 10. Duplication & Reuse
**10.1** Single source of truth for logic used in 2+ places. Don't generalize until 2 real callers.
**10.2** Centralize (ONE place): orderbook sorting, BBO extraction, fee calc, return calcs, rounding rules.
**10.3** >15 lines copied → create helper. Helpers: pure, typed, tested.
**10.4** Canonical dataclasses only—no near-duplicates. Venue extras go in venue_meta.
**10.5** Refactor when: same logic in 2+ places, bug fixes need multiple edits, new features repeat patterns.
**10.6** Preserve behavior unless explicitly changing. Add tests that lock behavior.
**10.7** Config decisions (thresholds, fees) live in ONE config layer, referenced everywhere.
**10.8** No bare generic filenames across packages. Every .py module name must be unique across the entire src/uscryptoarb/ tree (excluding __init__.py). If two modules would share a name, prefix with the domain context. Connector sub-packages are the one exception: client.py, parser.py, and symbols.py within connectors/<venue>/ are permitted as a deliberate internal pattern, but no other package may reuse those names. Before creating a new module, run `find src/ -name "<proposed_name>.py"` to check.

### 10.9 Refactor Checkpoint
When a session creates a 2nd instance of a pattern (2nd connector, 2nd config helper, 2nd fixture shape), flag it in SESSION_HANDOFFS under "Refactor Candidates" with the specific files and pattern. The NEXT session must either refactor or explicitly defer with rationale in DECISION_LOG.

### 11. Layering (imports DOWN only)
Domain/Core  → (nothing) - dataclasses, pure functions
Validation   → Domain
Calculation  → Domain, Validation
Strategy     → Domain, Validation, Calculation
Connectors   → Domain only (outputs canonical types)
Notification → Domain/Core
Execution    → All pure + Connectors
Orchestration→ Everything
**11.2** Circular imports = hard failure.
**11.3** Connectors parse/normalize only. Cannot: compute arb, embed thresholds, decide validity.
**11.4** Config loads once in orchestration, passed down. Core never reads env vars.
**11.5** DI not globals. Strategies receive FeeModel, config, snapshots as params.

### 12. Repo Integrity
Discover repo before referencing. File not found → ASK. Conflicts → surface and propose minimal change.

### 13. Pre-Implementation Verification (MANDATORY)
LESSONS_LEARNED.md searched for gotchas:
DECISION_LOG.md searched for settled decisions:
MATHEMATICA_MAP.md status checked (if applicable):
Mathematica reference function (if applicable):
Improvements over Mathematica approach considered:
Template/pattern file(s) used:
Base classes verified (paths + signatures):
Dataclass mutability (frozen?):
Imports verified to exist:
Module name uniqueness verified (find src/ -name "<name>.py"):
2+ similar implementations reviewed:
Test approach:
Cannot verify → STOP and ask.

### 14. Deliverable Format
What Changed

file.py: Added func()

Why
Brief rationale. Reference Mathematica function if applicable, note improvements if diverging.
Propagation Checklist

 Source - [x] Types - [x] Tests - [x] Docstrings - [x] README - [x] CHANGELOG
 MATHEMATICA_MAP - [ ] DECISION_LOG - [ ] LESSONS_LEARNED
 CLAUDE_INSTRUCTIONS.md regenerated (if PROJECT_INSTRUCTIONS.md changed)

Validation
pytest tests/unit/test_file.py -v
New config keys
key: default

### 15. Debugging & Traceability
- Every stage logs: input count, output count, filter reasons
- Support `--trace-pair BTC/USD` for DEBUG on that pair
- Snapshot replay from JSON
- Every log includes correlation_id

### 16. Debug Config
```yaml
debug:
  enabled: bool
  trace_pairs: list[str]
  log_pipeline_stages: bool
  snapshot_dir: str | null
```
CLI: `--trace-pair PAIR --dry-run --max-markets N --log-level LEVEL`

---
## Success Metrics
| Metric | Target | Phase |
|--------|--------|-------|
| Calculation Match (vs Mathematica) | 100% where approach is shared; documented rationale where diverging | 1 |
| Detection Latency | <500ms | 1 |
| Pair Coverage | 100% | 1+ |
| Alert Actionability | >95% | 1 |
| Fee Model Accuracy | 100% | 1+ |
| Detection Accuracy | >95% | 1+ |
| Execution Rate (both legs fill) | >95% | 4 |
| Net Profitability | >0 | 4 |

Phases: 1=Detection/Alerts, 2=WebSocket, 3=Paper, 4=Live

## Config Keys
```yaml
arbitrage:
  threshold: "0.0055"          # 0.55% min return
  min_bankroll_limit: "0.10"   # max 10% per trade
polling:
  interval_seconds: 5
```

## Reference
Full: PROJECT_INSTRUCTIONS.md | Mathematica: CryptoArbitrage_V14.9.4_NoKeys.nb
Ops docs: docs/ (LESSONS_LEARNED, SESSION_HANDOFFS, DECISION_LOG, MATHEMATICA_MAP)

## Sync Policy
Edit `PROJECT_INSTRUCTIONS.md` first → regenerate this file second → copy this file into Claude.ai project instructions UI. Never update CLAUDE_INSTRUCTIONS.md or the UI independently. Changes flow one direction from the canonical source.